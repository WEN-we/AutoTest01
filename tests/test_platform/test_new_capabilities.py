"""审计日志 + 影响面分析 + 自愈定位器 + 视觉回归 单元测试"""
import json
import os
from unittest.mock import MagicMock, patch

import pytest

import quality_platform.services.impact_analysis as impact_mod
import quality_platform.models as models
from quality_platform.models import db as models_db
from utils.tools.self_heal import (derive_candidates, record_heal_event,
                                   set_current_nodeid, get_current_nodeid)
from utils.tools.visual_diff import compare_images, update_baseline


@pytest.fixture
def tmp_db(tmp_path, monkeypatch):
    """临时 SQLite（同 test_models.py，本文件独立可运行）"""
    monkeypatch.setattr(models_db, "path", str(tmp_path / "test.db"))
    models_db.init_db()
    return models_db


# ==============================
# 审计日志（数据层）
# ==============================
class TestAuditStore:
    def test_insert_and_list(self, tmp_db):
        tmp_db.insert_audit("alice", "login", ip="127.0.0.1")
        tmp_db.insert_audit("bob", "case_delete", target="3", ok=False)
        logs = tmp_db.list_audit(limit=10)
        assert len(logs) == 2
        # 倒序：最新在前
        assert logs[0]["username"] == "bob"
        assert logs[0]["ok"] == 0
        assert logs[1]["action"] == "login"

    def test_list_filter_by_action(self, tmp_db):
        tmp_db.insert_audit("a", "login")
        tmp_db.insert_audit("a", "run_start", target="1")
        tmp_db.insert_audit("b", "login")
        assert len(tmp_db.list_audit(action="login")) == 2
        assert len(tmp_db.list_audit(action="run_start")) == 1

    def test_list_filter_by_username(self, tmp_db):
        tmp_db.insert_audit("alice", "login")
        tmp_db.insert_audit("bob", "login")
        assert {l["username"] for l in tmp_db.list_audit(username="alice")} == {"alice"}

    def test_anonymous_fallback(self, tmp_db):
        tmp_db.insert_audit("", "login")
        assert tmp_db.list_audit()[0]["username"] == "anonymous"

    def test_detail_truncated(self, tmp_db):
        tmp_db.insert_audit("a", "case_import", detail="x" * 1000)
        assert len(tmp_db.list_audit()[0]["detail"]) == 500


# ==============================
# 影响面分析（精准测试）
# ==============================
def _mock_git(monkeypatch, files: list[str]):
    proc = MagicMock(returncode=0, stdout="\n".join(files), stderr="")
    monkeypatch.setattr(impact_mod.subprocess, "run", lambda *a, **k: proc)


class TestImpactAnalysis:
    def test_sut_change_maps_to_api_smoke_whitebox(self, monkeypatch):
        """被测系统变更 → API + 冒烟 + 白盒（大厂精准测试：变更 → 直接消费方）"""
        _mock_git(monkeypatch, ["local_web_login/backend_server.py"])
        r = impact_mod.analyze_changes()
        assert "tests/test_api/" in r["suggested_tests"]
        assert "tests/test_smoke/" in r["suggested_tests"]
        assert "tests/test_whitebox/" in r["suggested_tests"]

    def test_platform_change_maps_to_platform_tests(self, monkeypatch):
        _mock_git(monkeypatch, ["quality_platform/app.py", "utils/ai/llm_client.py"])
        r = impact_mod.analyze_changes()
        assert r["suggested_tests"] == ["tests/test_platform/"]

    def test_po_change_maps_to_ui_tests(self, monkeypatch):
        _mock_git(monkeypatch, ["page_objects/web/velmart_login_page.py"])
        r = impact_mod.analyze_changes()
        assert "tests/test_ui/" in r["suggested_tests"]
        assert "tests/test_ecommerce/" in r["suggested_tests"]

    def test_test_file_change_direct_mapping(self, monkeypatch):
        """测试文件自身变更 → 精确到所在测试目录（最短路径）"""
        _mock_git(monkeypatch, ["tests/test_ecommerce/test_ec_cart.py"])
        r = impact_mod.analyze_changes()
        assert r["suggested_tests"] == ["tests/test_ecommerce/"]
        assert "测试文件变更" in r["reasons"]["tests/test_ecommerce/"][0]

    def test_tests_root_file_maps_to_base_runnable_set(self, monkeypatch):
        """tests/ 根文件（conftest.py）影响全局 → 基础可跑集（而非误判为目录）"""
        _mock_git(monkeypatch, ["tests/conftest.py"])
        r = impact_mod.analyze_changes()
        # 不再出现错误的 "tests/conftest.py/" 目录
        assert "tests/conftest.py/" not in r["suggested_tests"]
        assert set(r["suggested_tests"]) == {
            "tests/test_smoke/", "tests/test_api/",
            "tests/test_platform/", "tests/test_whitebox/"}
        assert "全局影响" in r["reasons"]["tests/test_smoke/"][0]
        assert r["fallback_used"] is False

    def test_unmatched_falls_back_to_smoke(self, monkeypatch):
        _mock_git(monkeypatch, ["README.md", "docs/notes.txt"])
        r = impact_mod.analyze_changes()
        assert r["suggested_tests"] == ["tests/test_smoke/"]
        assert r["fallback_used"] is True
        assert set(r["unmatched"]) == {"README.md", "docs/notes.txt"}

    def test_no_changes(self, monkeypatch):
        _mock_git(monkeypatch, [])
        r = impact_mod.analyze_changes()
        assert r["changed_files"] == []
        assert r["suggested_tests"] == []

    def test_git_failure_returns_empty(self, monkeypatch):
        proc = MagicMock(returncode=128, stdout="", stderr="fatal: bad revision")
        monkeypatch.setattr(impact_mod.subprocess, "run", lambda *a, **k: proc)
        r = impact_mod.analyze_changes()
        assert r["changed_files"] == []

    def test_dedup_multiple_changes_same_target(self, monkeypatch):
        """多个文件命中同一测试集 → 测试集去重，原因聚合"""
        _mock_git(monkeypatch, ["local_web_login/a.py", "local_web_login/b.py"])
        r = impact_mod.analyze_changes()
        assert r["suggested_tests"].count("tests/test_api/") == 1
        assert len(r["reasons"]["tests/test_api/"]) == 2

    def test_backslash_paths_normalized(self, monkeypatch):
        _mock_git(monkeypatch, ["local_web_login\\backend_server.py"])
        r = impact_mod.analyze_changes()
        assert "tests/test_api/" in r["suggested_tests"]


# ==============================
# 自愈定位器
# ==============================
class TestDeriveCandidates:
    def test_id_locator(self):
        assert derive_candidates("#login-btn") == [
            '[data-testid="login-btn"]', '[name="login-btn"]', '[id="login-btn"]']

    def test_class_locator(self):
        candidates = derive_candidates(".submit-btn")
        assert '[class*="submit-btn"]' in candidates
        assert '[data-testid="submit-btn"]' in candidates

    def test_text_locator(self):
        candidates = derive_candidates('button:has-text("登录")')
        assert "text=登录" in candidates
        assert '[aria-label="登录"]' in candidates

    def test_placeholder_locator(self):
        candidates = derive_candidates('input[placeholder="用户名"]')
        assert '[aria-label="用户名"]' in candidates

    def test_no_candidates_for_css_selector(self):
        """复杂 CSS 选择器无语义变换 → 空候选（不做模糊猜测，防误点）"""
        assert derive_candidates("div > span:nth-child(2)") == []

    def test_empty_locator(self):
        assert derive_candidates("") == []


class TestHealEvent:
    def test_record_and_persist(self, tmp_path, monkeypatch):
        event_file = tmp_path / "self_heal_events.json"
        monkeypatch.setattr("utils.tools.self_heal.HEAL_EVENT_FILE", str(event_file))
        record_heal_event("tests/x::test_a", "#btn", '[data-testid="btn"]', "登录按钮")
        record_heal_event("tests/x::test_b", "#user", '[name="user"]')
        with open(event_file, encoding="utf-8") as f:
            records = json.load(f)
        assert len(records) == 2
        assert records[0]["nodeid"] == "tests/x::test_a"
        assert records[0]["healed_locator"] == '[data-testid="btn"]'

    def test_nodeid_fallback_to_current(self, tmp_path, monkeypatch):
        """未显式传 nodeid 时回退 conftest 注入的当前用例"""
        event_file = tmp_path / "events.json"
        monkeypatch.setattr("utils.tools.self_heal.HEAL_EVENT_FILE", str(event_file))
        set_current_nodeid("tests/y::test_now")
        record_heal_event("", "#a", '[data-testid="a"]')
        with open(event_file, encoding="utf-8") as f:
            assert json.load(f)[0]["nodeid"] == "tests/y::test_now"


class FakePlaywrightPage:
    """Playwright page 桩：指定 locator 成功，其余抛超时异常"""

    def __init__(self, working_locators: set[str]):
        self.working = working_locators
        self.calls: list[str] = []

    def click(self, locator, timeout=None):
        self.calls.append(locator)
        if locator in self.working:
            return None
        raise TimeoutError(f"Timeout {locator}")


class TestSelfHealInPage:
    """自愈集成语义测试（用 self_heal 核心 API + 桩页面复刻业务 PO 内建的自愈流程；
    不依赖 page_objects/web/velmart_web_base_page.py——该文件为用户在研未入库，
    CI 全新 checkout 无此文件，引用会导致 import 失败）"""

    def _heal_click(self, page, locator, description=""):
        """模拟自愈定位器流程：主定位器失败 → 派生候选依次尝试 → 命中记录事件。"""
        from utils.tools import self_heal
        try:
            page.click(locator)
            return None  # 主定位器成功，无自愈
        except TimeoutError:
            pass
        for cand in self_heal.derive_candidates(locator):
            try:
                page.click(cand)
                self_heal.record_heal_event("", locator, cand, description)
                return cand
            except TimeoutError:
                continue
        raise TimeoutError(f"Timeout {locator}")  # 全部候选失败 → 抛原始异常（不吞错）

    def test_primary_locator_works_no_heal(self, tmp_path, monkeypatch):
        monkeypatch.setattr("utils.tools.self_heal.HEAL_EVENT_FILE",
                            str(tmp_path / "e.json"))
        page = FakePlaywrightPage({"#btn"})
        healed = self._heal_click(page, "#btn")
        assert healed is None
        assert not (tmp_path / "e.json").exists()   # 无自愈事件

    def test_heal_falls_back_to_testid(self, tmp_path, monkeypatch):
        """#btn 失效 → 自动自愈到 [data-testid="btn"]，用例不中断"""
        event_file = tmp_path / "e.json"
        monkeypatch.setattr("utils.tools.self_heal.HEAL_EVENT_FILE", str(event_file))
        page = FakePlaywrightPage({'[data-testid="btn"]'})
        healed = self._heal_click(page, "#btn", description="登录按钮")
        assert healed == '[data-testid="btn"]'
        assert event_file.exists()
        with open(event_file, encoding="utf-8") as f:
            event = json.load(f)[0]
        assert event["original_locator"] == "#btn"
        assert event["healed_locator"] == '[data-testid="btn"]'
        assert event["description"] == "登录按钮"

    def test_all_candidates_fail_raises_original(self, tmp_path, monkeypatch):
        """所有候选都失败 → 抛原始异常（不吞错，保证用例真实性）"""
        monkeypatch.setattr("utils.tools.self_heal.HEAL_EVENT_FILE",
                            str(tmp_path / "e.json"))
        page = FakePlaywrightPage(set())   # 全部失效
        with pytest.raises(TimeoutError):
            self._heal_click(page, "#btn")


# ==============================
# 视觉回归
# ==============================
def _make_png(path, color, size=(100, 100), patch_box=None, patch_color=(255, 0, 0)):
    from PIL import Image, ImageDraw
    os.makedirs(os.path.dirname(str(path)), exist_ok=True)
    img = Image.new("RGB", size, color)
    if patch_box:
        ImageDraw.Draw(img).rectangle(patch_box, fill=patch_color)
    img.save(str(path))
    return path


class TestVisualDiff:
    def test_first_run_when_no_baseline(self, tmp_path):
        cur = _make_png(tmp_path / "cur.png", (255, 255, 255))
        r = compare_images(str(tmp_path / "baseline.png"), str(cur))
        assert r["first_run"] is True
        assert r["passed"] is True

    def test_identical_images_pass(self, tmp_path):
        base = _make_png(tmp_path / "base.png", (30, 30, 30))
        cur = _make_png(tmp_path / "cur.png", (30, 30, 30))
        r = compare_images(str(base), str(cur))
        assert r["passed"] is True
        assert r["diff_ratio"] == 0.0

    def test_minor_noise_within_tolerance_passes(self, tmp_path):
        """通道差 ≤ 容差（抗锯齿噪声）不计为差异"""
        base = _make_png(tmp_path / "base.png", (30, 30, 30))
        cur = _make_png(tmp_path / "cur.png", (35, 35, 35))
        r = compare_images(str(base), str(cur))
        assert r["passed"] is True
        assert r["diff_ratio"] == 0.0

    def test_real_diff_fails_and_highlights(self, tmp_path):
        base = _make_png(tmp_path / "base.png", (30, 30, 30))
        cur = _make_png(tmp_path / "cur.png", (30, 30, 30),
                        patch_box=(10, 10, 30, 30), patch_color=(255, 0, 0))
        diff_out = tmp_path / "diff.png"
        r = compare_images(str(base), str(cur), diff_output=str(diff_out))
        # 400/10000 = 4% > 1% 阈值
        assert r["passed"] is False
        assert 0.03 < r["diff_ratio"] < 0.05
        assert os.path.exists(diff_out)

    def test_size_mismatch_resized(self, tmp_path):
        base = _make_png(tmp_path / "base.png", (30, 30, 30), size=(100, 100))
        cur = _make_png(tmp_path / "cur.png", (30, 30, 30), size=(120, 100))
        r = compare_images(str(base), str(cur))
        assert r["size_mismatch"] is True
        assert r["passed"] is True   # 内容一致，仅尺寸不同 → 缩放后无差异

    def test_missing_current_fails(self, tmp_path):
        base = _make_png(tmp_path / "base.png", (0, 0, 0))
        r = compare_images(str(base), str(tmp_path / "nope.png"))
        assert r["passed"] is False

    def test_update_baseline(self, tmp_path):
        cur = _make_png(tmp_path / "cur.png", (10, 200, 10))
        target = tmp_path / "baselines" / "login.png"
        assert update_baseline(str(cur), str(target)) is True
        assert target.exists()
        # 更新后对比应通过
        r = compare_images(str(target), str(cur))
        assert r["passed"] is True
