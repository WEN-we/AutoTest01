"""可观测性单元测试：健康检查 / 执行指标 / 告警规则。"""
from datetime import datetime

from quality_platform.services import observability


class TestDailyStats:
    def test_empty_db(self, tmp_db):
        stats = observability.daily_stats(days=7)
        assert len(stats) == 7
        assert stats[-1]["date"] == datetime.now().strftime("%Y-%m-%d")
        assert all(s["runs"] == 0 and s["pass_rate"] == 0 for s in stats)

    def test_with_executions(self, tmp_db):
        eid = tmp_db.insert_execution("tests/x/")
        tmp_db.finish_execution(eid, 10, 9, 1, 0, 5.0)
        stats = observability.daily_stats(days=1)
        today = stats[-1]
        assert today["runs"] == 1
        assert today["total"] == 10 and today["passed"] == 9
        assert today["pass_rate"] == 90.0


class TestCumulativeStats:
    def test_basic(self, tmp_db):
        eid = tmp_db.insert_execution("tests/x/")
        tmp_db.finish_execution(eid, 20, 18, 2, 0, 8.0)
        c = observability.cumulative_stats()
        assert c["runs"] >= 1
        assert c["total_cases"] >= 20
        assert c["pass_rate"] >= 90.0
        assert c["backend"] == tmp_db.backend


class TestCheckAlerts:
    def test_no_alerts_when_pass(self, tmp_db):
        eid = tmp_db.insert_execution("tests/x/")
        tmp_db.finish_execution(eid, 10, 10, 0, 0, 2.0)
        assert observability.check_alerts(fail_rate_threshold=80.0) == []

    def test_alert_on_high_fail_rate(self, tmp_db):
        eid = tmp_db.insert_execution("tests/x/")
        tmp_db.finish_execution(eid, 10, 1, 9, 0, 2.0)  # 90% 失败
        alerts = observability.check_alerts(fail_rate_threshold=80.0)
        assert len(alerts) == 1
        assert alerts[0]["type"] == "fail_rate"
        assert alerts[0]["fail_rate"] == 90.0
        assert alerts[0]["level"] == "critical"
