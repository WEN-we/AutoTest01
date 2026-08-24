"""FlakyDetector 单元测试：区间判定 / 最少样本 / 窗口截取"""
from utils.ai.flaky_detector import FlakyDetector


def _records(nodeid, statuses):
    """构造按时间倒序（最新在前）的运行记录"""
    return [{"nodeid": nodeid, "status": s} for s in statuses]


class TestFlakyDetect:
    def test_flaky_in_range(self):
        """失败率 30%~70% → 疑似 flaky"""
        d = FlakyDetector(window=10, low=0.3, high=0.7)
        report = d.detect(_records("t1", ["failed"] * 5 + ["passed"] * 5))
        assert report["flaky"][0]["nodeid"] == "t1"
        assert report["flaky"][0]["fail_rate"] == 0.5
        assert report["summary"]["detected_flaky"] == 1

    def test_stable_fail_high_rate(self):
        """失败率 > 70% → 稳定失败（不归为 flaky）"""
        d = FlakyDetector(window=10, low=0.3, high=0.7)
        report = d.detect(_records("t2", ["failed"] * 8 + ["passed"] * 2))
        assert report["flaky"] == []
        assert report["stable_fail"][0]["nodeid"] == "t2"
        assert report["summary"]["stable_fail"] == 1

    def test_stable_pass_low_rate(self):
        """失败率 < 30% → 稳定通过"""
        d = FlakyDetector(window=10, low=0.3, high=0.7)
        report = d.detect(_records("t3", ["failed"] * 1 + ["passed"] * 9))
        assert report["flaky"] == []
        assert report["summary"]["stable_pass"] == 1

    def test_min_runs_not_enough_samples(self):
        """样本不足 min_runs 不判定"""
        d = FlakyDetector(window=10, low=0.3, high=0.7)
        report = d.detect(_records("t4", ["failed", "passed"]))
        assert report["flaky"] == []
        assert report["summary"]["detected_flaky"] == 0

    def test_window_limits_records(self):
        """窗口截取：只统计最近 window 条（旧记录不参与）"""
        d = FlakyDetector(window=3, low=0.3, high=0.7)
        # 倒序传入：最近3条 = 2 failed + 1 passed（旧的 7 条 passed 被忽略）
        report = d.detect(_records("t5", ["failed", "failed", "passed"] + ["passed"] * 7))
        assert report["flaky"][0]["run_count"] == 3
        assert report["flaky"][0]["fail_count"] == 2
        assert report["flaky"][0]["fail_rate"] == 0.667

    def test_window_recent_trend_wins(self):
        """近期表现决定结论：长期失败后最近全绿（窗口内）→ 稳定通过"""
        d = FlakyDetector(window=4, low=0.3, high=0.7)
        # 最近4条全 passed，窗口外6条 failed 不参与
        report = d.detect(_records("t6", ["passed"] * 4 + ["failed"] * 6))
        assert report["flaky"] == []
        assert report["summary"]["stable_pass"] == 1

    def test_skipped_not_counted_as_fail(self):
        """skipped 不计为失败"""
        d = FlakyDetector(window=10, low=0.3, high=0.7)
        report = d.detect(_records("t7", ["skipped"] * 5 + ["passed"] * 5))
        assert report["summary"]["stable_pass"] == 1

    def test_empty_records(self):
        d = FlakyDetector()
        report = d.detect([])
        assert report["summary"]["detected_flaky"] == 0

    def test_sorted_by_fail_rate_desc(self):
        """flaky 列表按失败率降序"""
        d = FlakyDetector(window=10, low=0.3, high=0.7)
        records = (_records("a", ["failed"] * 4 + ["passed"] * 6)     # 0.4
                   + _records("b", ["failed"] * 6 + ["passed"] * 4))  # 0.6
        report = d.detect(records)
        rates = [f["fail_rate"] for f in report["flaky"]]
        assert rates == sorted(rates, reverse=True)
