"""通知服务 + 定时调度器 + AI 集成服务 单元测试（mock 外部依赖）"""
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest

import quality_platform.services.notifier as notifier_mod
from quality_platform.models import db
from quality_platform.services import ai_integration
from quality_platform.services.notifier import _build_payload, send_execution_summary
from quality_platform.services.scheduler import Scheduler


# ==============================
# 通知服务
# ==============================
class TestNotifier:
    def _exec(self):
        return {"id": 7, "test_path": "tests/x/", "status": "finished",
                "passed": 8, "failed": 2, "skipped": 0, "total": 10, "duration": 12.5}

    def test_build_payload_markdown(self):
        failures = [{"nodeid": "t::a", "error_type": "TimeoutError"},
                    {"nodeid": "t::b", "error_type": None}]
        payload = _build_payload(self._exec(), failures)
        assert payload["msgtype"] == "markdown"
        text = payload["markdown"]["text"]
        assert "通过 8/10（80.0%）" in text
        assert "t::a" in text and "t::b" in text
        assert "80.0%" in payload["markdown"]["title"]

    def test_build_payload_no_failures(self):
        payload = _build_payload(self._exec(), [])
        assert "- 无" in payload["markdown"]["text"]

    def test_build_payload_with_analysis(self):
        """失败行带自动归因结论（ana_category）时在通知中展示"""
        failures = [
            {"nodeid": "t::a", "error_type": "TimeoutError",
             "ana_category": "环境波动/页面加载慢"},
            {"nodeid": "t::b", "error_type": "AssertionError"},  # 未归因
        ]
        text = _build_payload(self._exec(), failures)["markdown"]["text"]
        assert "**环境波动/页面加载慢**" in text
        assert "t::a" in text and "t::b" in text

    def test_disabled_returns_false(self, monkeypatch):
        monkeypatch.setattr(notifier_mod, "_load_notify_cfg",
                            lambda: {"enabled": False, "webhook_url": "http://x"})
        assert send_execution_summary(1) is False

    def test_no_webhook_returns_false(self, monkeypatch):
        monkeypatch.setattr(notifier_mod, "_load_notify_cfg",
                            lambda: {"enabled": True, "webhook_url": ""})
        assert send_execution_summary(1) is False

    def test_send_success(self, monkeypatch):
        monkeypatch.setattr(notifier_mod, "_load_notify_cfg",
                            lambda: {"enabled": True, "webhook_url": "http://hook"})
        monkeypatch.setattr(db, "get_execution", lambda i: self._exec())
        monkeypatch.setattr(db, "list_case_results", lambda i: [])
        with patch.object(notifier_mod.requests, "post") as mock_post:
            mock_post.return_value = MagicMock(status_code=200)
            assert send_execution_summary(7) is True

    def test_send_http_error_not_raise(self, monkeypatch):
        """通知失败不阻塞主流程"""
        monkeypatch.setattr(notifier_mod, "_load_notify_cfg",
                            lambda: {"enabled": True, "webhook_url": "http://hook"})
        monkeypatch.setattr(db, "get_execution", lambda i: self._exec())
        monkeypatch.setattr(db, "list_case_results", lambda i: [])
        with patch.object(notifier_mod.requests, "post") as mock_post:
            mock_post.return_value = MagicMock(status_code=500, text="err")
            assert send_execution_summary(7) is False

    def test_send_exception_not_raise(self, monkeypatch):
        monkeypatch.setattr(notifier_mod, "_load_notify_cfg",
                            lambda: {"enabled": True, "webhook_url": "http://hook"})
        monkeypatch.setattr(db, "get_execution", lambda i: self._exec())
        monkeypatch.setattr(db, "list_case_results", lambda i: [])
        with patch.object(notifier_mod.requests, "post",
                          side_effect=ConnectionError("boom")):
            assert send_execution_summary(7) is False


# ==============================
# 调度器（纯判定逻辑，不启动线程）
# ==============================
class TestSchedulerShouldRun:
    def _sched(self, kind, cron_value, last_run=None, enabled=1):
        return {"id": 1, "name": "n", "kind": kind, "cron_value": cron_value,
                "test_path": "t", "reruns": 0, "parallel": 0,
                "enabled": enabled, "last_run": last_run}

    @pytest.fixture
    def fixed_clock(self, monkeypatch):
        """固定调度器时钟（每分钟第 10 秒），消除真实时间边界导致的 flaky"""
        import quality_platform.services.scheduler as sched_mod
        from datetime import datetime as real_dt
        fixed = real_dt.now().replace(second=10, microsecond=0)

        class FakeDatetime(real_dt):
            @classmethod
            def now(cls, tz=None):
                return fixed

        monkeypatch.setattr(sched_mod, "datetime", FakeDatetime)
        return fixed

    def test_daily_in_window(self, fixed_clock):
        """当前时间落在目标点后的轮询窗口内 → 触发"""
        s = Scheduler()
        sched = self._sched("daily", fixed_clock.strftime("%H:%M"))
        assert s._should_run(sched) is True

    def test_daily_already_ran_today(self, fixed_clock):
        """今天已跑过 → 不触发"""
        s = Scheduler()
        sched = self._sched("daily", fixed_clock.strftime("%H:%M"),
                            last_run=fixed_clock.isoformat(timespec="seconds"))
        assert s._should_run(sched) is False

    def test_daily_far_from_target(self, fixed_clock):
        """目标时间已过很久（错过窗口）→ 不触发"""
        s = Scheduler()
        # 相对固定时刻的 2 小时前，必然在窗口外
        target = (fixed_clock - timedelta(hours=2)).strftime("%H:%M")
        sched = self._sched("daily", target)
        assert s._should_run(sched) is False

    def test_interval_first_run(self):
        """interval 无历史记录 → 立即触发"""
        s = Scheduler()
        assert s._should_run(self._sched("interval", "6")) is True

    def test_interval_not_due(self):
        """距上次运行未满间隔 → 不触发"""
        s = Scheduler()
        last = (datetime.now() - timedelta(hours=1)).isoformat(timespec="seconds")
        assert s._should_run(self._sched("interval", "6", last_run=last)) is False

    def test_interval_due(self):
        """距上次运行超过间隔 → 触发"""
        s = Scheduler()
        last = (datetime.now() - timedelta(hours=7)).isoformat(timespec="seconds")
        assert s._should_run(self._sched("interval", "6", last_run=last)) is True

    def test_invalid_last_run_safe(self):
        """损坏的 last_run 不崩溃"""
        s = Scheduler()
        assert s._should_run(self._sched("interval", "6", last_run="garbage")) is False


# ==============================
# AI 集成服务
# ==============================
class TestAIIntegration:
    def test_analyze_failure_missing_case(self, monkeypatch):
        monkeypatch.setattr(db, "get_analysis", lambda i: None)
        monkeypatch.setattr(db, "get_case_result", lambda i: None)
        result = ai_integration.ai.analyze_failure(999)
        assert result["source"] == "rule"
        assert result["category"] == "未知"

    def test_analyze_failure_uses_cache(self, monkeypatch):
        cached = {"category": "产品缺陷", "confidence": 0.9, "suggestion": "s",
                  "key_evidence": "e", "source": "llm"}
        monkeypatch.setattr(db, "get_analysis", lambda i: cached)
        assert ai_integration.ai.analyze_failure(1)["category"] == "产品缺陷"

    def test_analyze_failure_persists_result(self, monkeypatch):
        case = {"id": 5, "nodeid": "t::x", "error_message": "TimeoutException: x",
                "screenshot": ""}
        saved = {}

        def fake_upsert(cid, result):
            saved["cid"], saved["result"] = cid, result

        monkeypatch.setattr(db, "get_analysis", lambda i: None)
        monkeypatch.setattr(db, "get_case_result", lambda i: case)
        monkeypatch.setattr(db, "upsert_analysis", fake_upsert)
        result = ai_integration.ai.analyze_failure(5)
        # 无 LLM Key → 规则引擎归因
        assert result["source"] == "rule"
        assert saved["cid"] == 5
        assert saved["result"]["category"] == "环境波动/页面加载慢"

    def test_detect_flaky_aggregates_records(self, monkeypatch):
        records = ([{"nodeid": "t::a", "status": "failed"}] * 5
                   + [{"nodeid": "t::a", "status": "passed"}] * 5)
        monkeypatch.setattr(db, "recent_records", lambda limit=2000: records)
        report = ai_integration.ai.detect_flaky()
        assert report["summary"]["detected_flaky"] == 1

    def test_flaky_detector_config_wired(self):
        """ai_tools.yaml 的 flaky 参数已接线到检测器（非写死默认值）"""
        d = ai_integration.ai.detector
        assert d.window == 10 and d.low == 0.3 and d.high == 0.7
