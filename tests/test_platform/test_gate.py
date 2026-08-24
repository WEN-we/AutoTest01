"""质量门禁 / 质量分 / 测试金字塔 单元测试（mock 数据层）"""
import pytest

from quality_platform.models import db
from quality_platform.services import ai_integration
from quality_platform.services.gate import evaluate_gate, quality_score, test_pyramid


def _run(exec_id, total, passed, failed, status="finished", path="tests/x/"):
    skipped = total - passed - failed
    return {"id": exec_id, "test_path": path, "status": status, "total": total,
            "passed": passed, "failed": failed, "skipped": skipped}


def _flaky_report(flaky=0, stable_fail=0):
    return {"summary": {"detected_flaky": flaky, "stable_fail": stable_fail,
                        "stable_pass": 0}}


@pytest.fixture
def mock_deps(monkeypatch):
    """mock 执行记录 / 用例记录 / flaky 报告，聚焦门禁判定逻辑"""
    state = {"runs": [], "flaky": _flaky_report(), "records": []}

    monkeypatch.setattr(db, "list_executions", lambda limit=20: state["runs"])
    monkeypatch.setattr(db, "recent_records", lambda limit=500: state["records"])
    monkeypatch.setattr(ai_integration.ai, "detect_flaky",
                        lambda: state["flaky"])
    return state


class TestEvaluateGate:
    def test_no_data(self, mock_deps):
        assert evaluate_gate()["status"] == "no_data"

    def test_pass(self, mock_deps):
        mock_deps["runs"] = [_run(1, 100, 97, 3)]
        result = evaluate_gate()
        assert result["status"] == "PASS"
        assert result["latest_run"]["pass_rate"] == 97.0

    def test_warn_on_low_pass_rate(self, mock_deps):
        # 88% 通过率（>80 不 FAIL、<90 触发 WARN），失败数 2（≤5 不触发硬卡点）
        mock_deps["runs"] = [_run(1, 100, 88, 2)]
        assert evaluate_gate()["status"] == "WARN"

    def test_fail_on_pass_rate(self, mock_deps):
        mock_deps["runs"] = [_run(1, 100, 75, 25)]
        assert evaluate_gate()["status"] == "FAIL"

    def test_fail_on_fail_count(self, mock_deps):
        mock_deps["runs"] = [_run(1, 100, 94, 6)]  # 通过率94 但失败6个 > 5
        assert evaluate_gate()["status"] == "FAIL"

    def test_warn_on_flaky_rate(self, mock_deps):
        mock_deps["runs"] = [_run(1, 10, 9, 1)]
        mock_deps["flaky"] = _flaky_report(flaky=5)  # 5/10 = 0.5 > 0.3
        result = evaluate_gate()
        assert result["status"] == "WARN"
        # flaky 规则被标记违反
        flaky_rule = next(r for r in result["rules"] if r["name"] == "flaky 占比")
        assert flaky_rule["violated"] is True

    def test_running_runs_ignored(self, mock_deps):
        mock_deps["runs"] = [_run(1, 0, 0, 0, status="running"),
                             _run(2, 10, 10, 0)]
        result = evaluate_gate()
        assert result["status"] == "PASS"
        assert result["latest_run"]["id"] == 2


class TestQualityScore:
    def test_no_data_zero(self, mock_deps):
        assert quality_score()["score"] == 0

    def test_full_score_bounds(self, mock_deps):
        mock_deps["runs"] = [_run(i, 100, 100, 0) for i in range(1, 11)]
        score = quality_score()
        assert 0 <= score["score"] <= 100
        assert score["parts"]["pass_rate"] == 100.0

    def test_flaky_reduces_stability(self, mock_deps):
        mock_deps["runs"] = [_run(i, 100, 100, 0) for i in range(1, 11)]
        clean = quality_score()
        mock_deps["flaky"] = _flaky_report(flaky=20)
        dirty = quality_score()
        assert dirty["parts"]["stability"] < clean["parts"]["stability"]
        assert dirty["score"] < clean["score"]


class TestTestPyramid:
    def test_distribution(self, mock_deps):
        mock_deps["records"] = (
            [{"nodeid": f"tests/test_api/a.py::t{i}", "status": "passed"} for i in range(5)]
            + [{"nodeid": f"tests/test_ui/b.py::t{i}", "status": "passed"} for i in range(3)]
            + [{"nodeid": "tests/test_smoke/c.py::t1", "status": "passed"}]
            + [{"nodeid": "tests/other/d.py::t1", "status": "passed"}]
        )
        result = test_pyramid()
        assert result["distribution"]["api"] == 5
        assert result["distribution"]["ui"] == 3
        assert result["distribution"]["smoke"] == 1
        assert result["distribution"]["other"] == 1
        assert result["total"] == 10

    def test_junit_style_nodeid_compatible(self, mock_deps):
        """junit 点分式 classname（tests.test_api.x.TestX::t）也能归类"""
        mock_deps["records"] = [
            {"nodeid": "tests.test_api.test_user.TestUser::test_login", "status": "passed"}]
        result = test_pyramid()
        assert result["distribution"].get("api") == 1
