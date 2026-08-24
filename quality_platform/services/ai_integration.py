"""
质量工程平台 - AI 集成服务

职责：把 utils/ai 工具链接入平台
- 失败归因：对单个失败用例调用 FailureAnalyzer，结果缓存到 ai_analysis 表
- flaky 检测：聚合最近运行记录，调用 FlakyDetector 输出 flaky 清单
"""
from utils.ai.failure_analyzer import FailureAnalyzer
from utils.ai.flaky_detector import FlakyDetector
from utils.tools.logger import log
from quality_platform.models import db


def _load_flaky_cfg() -> dict:
    """读取 config/ai_tools.yaml 的 flaky_detector 段（缺失时返回空 dict 走默认值）。"""
    try:
        from utils.tools.config_reader import ConfigReader
        return ConfigReader.read_yaml("config/ai_tools.yaml").get("flaky_detector", {})
    except Exception:
        return {}


class AIIntegration:
    """平台侧 AI 能力封装"""

    def __init__(self):
        self.analyzer = FailureAnalyzer()
        cfg = _load_flaky_cfg()
        self.detector = FlakyDetector(
            window=int(cfg.get("window", 10)),
            low=float(cfg.get("low", 0.3)),
            high=float(cfg.get("high", 0.7)),
        )

    # ---------- 失败归因 ----------
    def analyze_failure(self, case_result_id: int) -> dict:
        """分析单个失败用例并缓存结果（重复调用直接返回缓存）。"""
        cached = db.get_analysis(case_result_id)
        if cached:
            return cached

        case = db.get_case_result(case_result_id)
        if not case:
            return {"category": "未知", "suggestion": "用例不存在", "source": "rule"}

        result = self.analyzer.analyze(
            nodeid=case["nodeid"],
            error_message=case.get("error_message") or "",
            screenshot=case.get("screenshot") or "",
        )
        db.upsert_analysis(case_result_id, result)
        return result

    # ---------- flaky 识别 ----------
    def detect_flaky(self) -> dict:
        records = db.recent_records(limit=2000)
        report = self.detector.detect(records)
        log.info(f"[平台] flaky 识别：flaky={report['summary']['detected_flaky']} "
                 f"稳定失败={report['summary']['stable_fail']}")
        return report


ai = AIIntegration()
