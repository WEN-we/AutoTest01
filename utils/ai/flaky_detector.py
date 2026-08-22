"""
Flaky 用例识别器（大厂 flaky 治理闭环第一步：识别）

判定标准（业界通用）：
- 最近 N 次运行中失败率在 [LOW, HIGH] 区间（默认 30%~70%）→ 疑似 flaky
- 失败率高于 HIGH → 稳定失败（真实缺陷或已坏），不归为 flaky
- 失败率低于 LOW → 稳定通过

用法（喂入历史运行记录）：
    from utils.ai.flaky_detector import FlakyDetector
    detector = FlakyDetector()
    records = [{"nodeid": "test_x", "status": "failed"}, ...]   # 最近 N 次全部记录
    report = detector.detect(records)
    # report = {"flaky": [{"nodeid": ..., "run_count": 10, "fail_rate": 0.5}], "summary": {...}}
"""
from collections import Counter
from typing import Iterable


class FlakyDetector:
    """基于历史运行结果识别 flaky 用例"""

    def __init__(self, window: int = 10, low: float = 0.3, high: float = 0.7):
        self.window = window      # 统计窗口（最近多少次运行）
        self.low = low            # flaky 判定下界
        self.high = high          # flaky 判定上界

    def detect(self, records: Iterable[dict], min_runs: int = 3) -> dict:
        """
        records: 每条 {"nodeid": str, "status": "passed"|"failed"|"skipped"}，
                 建议按时间倒序或正序均可（内部只计数）。
        返回: {"flaky": [...], "stable_fail": [...], "summary": {...}}
        """
        stat: dict[str, dict] = {}
        for r in records:
            nodeid = r.get("nodeid", "")
            if not nodeid:
                continue
            s = stat.setdefault(nodeid, {"total": 0, "fail": 0})
            s["total"] += 1
            if r.get("status") == "failed":
                s["fail"] += 1

        flaky, stable_fail, stable_pass = [], [], []
        for nodeid, s in stat.items():
            if s["total"] < min_runs:
                continue  # 样本不足，不判定
            rate = s["fail"] / s["total"]
            item = {
                "nodeid": nodeid,
                "run_count": s["total"],
                "fail_count": s["fail"],
                "fail_rate": round(rate, 3),
            }
            if self.low <= rate <= self.high:
                flaky.append(item)
            elif rate > self.high:
                stable_fail.append(item)
            else:
                stable_pass.append(item)

        flaky.sort(key=lambda x: x["fail_rate"], reverse=True)
        return {
            "flaky": flaky,
            "stable_fail": stable_fail,
            "stable_pass": stable_pass,
            "summary": {
                "window": self.window,
                "detected_flaky": len(flaky),
                "stable_fail": len(stable_fail),
                "stable_pass": len(stable_pass),
            },
        }
