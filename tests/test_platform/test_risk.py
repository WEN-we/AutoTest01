"""AI 发布风控（risk.py）单元测试：各信号扣分、评级边界、趋势计算。

全部通过 monkeypatch 注入信号，不依赖真实执行数据（可重复、无环境依赖）。
"""
import pytest

from quality_platform.services import risk


@pytest.fixture
def base_signals(monkeypatch):
    """默认全健康信号（100 分 / low），测试按需覆盖单项。"""
    monkeypatch.setattr(risk, "evaluate_gate", lambda: {"status": "passed"})
    monkeypatch.setattr(risk, "cluster_failures", lambda: [])
    monkeypatch.setattr(risk, "_failure_rate_trend", lambda: 0.0)
    monkeypatch.setattr(
        "quality_platform.services.ai_integration.ai.detect_flaky",
        lambda: {"summary": {"detected_flaky": 0, "stable_fail": 0}})
    return monkeypatch


class TestGateSignal:
    def test_healthy_is_low_risk(self, base_signals):
        r = risk.assess_release_risk()
        assert r["score"] == 100.0 and r["level"] == "low"
        assert "各信号均正常" in r["reasons"][0]

    def test_gate_fail_deducts_45(self, base_signals):
        base_signals.setattr(risk, "evaluate_gate", lambda: {"status": "FAIL"})
        r = risk.assess_release_risk()
        assert r["score"] == 55.0 and r["level"] == "high"
        assert any("门禁 FAIL" in x for x in r["reasons"])

    def test_gate_warn_deducts_20(self, base_signals):
        base_signals.setattr(risk, "evaluate_gate", lambda: {"status": "WARN"})
        r = risk.assess_release_risk()
        assert r["score"] == 80.0 and r["level"] == "low"

    def test_gate_no_data_deducts_10(self, base_signals):
        base_signals.setattr(risk, "evaluate_gate", lambda: {"status": "no_data"})
        r = risk.assess_release_risk()
        assert r["score"] == 90.0
        assert any("无已完成执行" in x for x in r["reasons"])


class TestStabilitySignal:
    def test_flaky_five_or_more(self, base_signals):
        base_signals.setattr(
            "quality_platform.services.ai_integration.ai.detect_flaky",
            lambda: {"summary": {"detected_flaky": 5, "stable_fail": 0}})
        r = risk.assess_release_risk()
        assert r["score"] == 80.0
        assert any("≥5" in x for x in r["reasons"])

    def test_flaky_each_costs_3(self, base_signals):
        base_signals.setattr(
            "quality_platform.services.ai_integration.ai.detect_flaky",
            lambda: {"summary": {"detected_flaky": 2, "stable_fail": 0}})
        assert risk.assess_release_risk()["score"] == 94.0

    def test_stable_fail_capped_at_30(self, base_signals):
        base_signals.setattr(
            "quality_platform.services.ai_integration.ai.detect_flaky",
            lambda: {"summary": {"detected_flaky": 0, "stable_fail": 5}})
        r = risk.assess_release_risk()
        assert r["score"] == 70.0          # 5*10=50 但封顶 30
        assert any("稳定失败" in x for x in r["reasons"])

    def test_flaky_detection_exception_degrades(self, base_signals):
        """flaky 检测异常 -> 视为无信号，不阻断评估。"""
        def boom():
            raise RuntimeError("ai down")
        base_signals.setattr("quality_platform.services.ai_integration.ai.detect_flaky", boom)
        r = risk.assess_release_risk()
        assert r["score"] == 100.0
        assert r["signals"]["flaky"] == {"detected": 0, "stable_fail": 0}


class TestClusterSignal:
    def test_big_cluster_deducts_15(self, base_signals):
        base_signals.setattr(risk, "cluster_failures",
                             lambda: [{"count": 5, "fingerprint": "x"}])
        r = risk.assess_release_risk()
        assert r["score"] == 85.0 and r["signals"]["failure_cluster_top"] == 5

    def test_medium_cluster_deducts_8(self, base_signals):
        base_signals.setattr(risk, "cluster_failures", lambda: [{"count": 3}])
        assert risk.assess_release_risk()["score"] == 92.0

    def test_cluster_exception_degrades(self, base_signals):
        def boom():
            raise RuntimeError("cluster down")
        base_signals.setattr(risk, "cluster_failures", boom)
        assert risk.assess_release_risk()["score"] == 100.0


class TestTrendSignal:
    def test_trend_up_10_deducts_15(self, base_signals):
        base_signals.setattr(risk, "_failure_rate_trend", lambda: 10.0)
        r = risk.assess_release_risk()
        assert r["score"] == 85.0 and r["signals"]["failure_rate_trend_delta"] == 10.0

    def test_trend_up_5_deducts_8(self, base_signals):
        base_signals.setattr(risk, "_failure_rate_trend", lambda: 5.0)
        assert risk.assess_release_risk()["score"] == 92.0

    def test_trend_calculation(self, monkeypatch):
        """近 3 天失败率 - 前 4 天失败率。"""
        days_data = [{"total": 10, "failed": 0} for _ in range(4)] \
            + [{"total": 10, "failed": 2} for _ in range(3)]
        monkeypatch.setattr("quality_platform.services.observability.daily_stats",
                            lambda days=7: days_data)
        assert risk._failure_rate_trend() == 20.0

    def test_trend_no_data_returns_zero(self, monkeypatch):
        monkeypatch.setattr("quality_platform.services.observability.daily_stats",
                            lambda days=7: [{"total": 0, "failed": 0}] * 7)
        assert risk._failure_rate_trend() == 0.0


class TestRatingBoundaries:
    def test_critical_when_score_below_40(self, base_signals):
        base_signals.setattr(risk, "evaluate_gate", lambda: {"status": "FAIL"})
        base_signals.setattr(
            "quality_platform.services.ai_integration.ai.detect_flaky",
            lambda: {"summary": {"detected_flaky": 5, "stable_fail": 1}})
        base_signals.setattr(risk, "cluster_failures", lambda: [{"count": 5}])
        base_signals.setattr(risk, "_failure_rate_trend", lambda: 12.0)
        r = risk.assess_release_risk()     # 100-45-20-10-15-15 = -5 -> 0
        assert r["score"] == 0.0 and r["level"] == "critical"

    def test_medium_range(self, base_signals):
        base_signals.setattr(risk, "evaluate_gate", lambda: {"status": "FAIL"})
        base_signals.setattr(risk, "cluster_failures", lambda: [{"count": 3}])
        r = risk.assess_release_risk()     # 100-45-8 = 47 -> high
        assert r["score"] == 47.0 and r["level"] == "high"

    def test_advice_texts_all_levels(self):
        for level in ("low", "medium", "high", "critical"):
            assert risk._advice(level)

    def test_signals_present(self, base_signals):
        r = risk.assess_release_risk()
        assert set(r["signals"]) >= {"gate", "flaky", "failure_cluster_top",
                                     "failure_rate_trend_delta"}
        assert r["advice"]
