"""
质量工程平台 - AI 集成服务

职责：把 utils/ai 工具链接入平台
- 失败归因：对单个失败用例调用 FailureAnalyzer，结果缓存到 ai_analysis 表
- flaky 检测：聚合最近运行记录，调用 FlakyDetector 输出 flaky 清单
- LLM 通道：统一走 ai_config.build_llm_client()（平台 AI 配置优先，回退环境变量），
  管理员在「AI 配置」页维护密钥 / 本地模型，保存即生效、无需重启
"""
from utils.ai.failure_analyzer import FailureAnalyzer
from utils.ai.flaky_detector import FlakyDetector
from utils.ai.test_generator import TestGenerator
from utils.tools.logger import log
from quality_platform.models import db
from quality_platform.services import ai_config


def _load_flaky_cfg() -> dict:
    """读取 config/ai_tools.yaml 的 flaky_detector 段（缺失时返回空 dict 走默认值）。"""
    try:
        from utils.tools.config_reader import ConfigReader
        return ConfigReader.read_yaml("config/ai_tools.yaml").get("flaky_detector", {})
    except Exception:
        return {}


class AIIntegration:
    """平台侧 AI 能力封装（LLM 通道每次调用动态构建 → 配置热更新，保存即生效）"""

    def __init__(self):
        cfg = _load_flaky_cfg()
        self.detector = FlakyDetector(
            window=int(cfg.get("window", 10)),
            low=float(cfg.get("low", 0.3)),
            high=float(cfg.get("high", 0.7)),
        )

    @staticmethod
    def _llm():
        """当前生效的 LLM 客户端（每次调用构建：管理员在 AI 配置页改完立即生效，无需重启）。"""
        return ai_config.build_llm_client()

    # ---------- 失败归因 ----------
    def analyze_failure(self, case_result_id: int) -> dict:
        """分析单个失败用例并缓存结果（重复调用直接返回缓存）。"""
        cached = db.get_analysis(case_result_id)
        if cached:
            return cached

        case = db.get_case_result(case_result_id)
        if not case:
            return {"category": "未知", "suggestion": "用例不存在", "source": "rule"}

        analyzer = FailureAnalyzer(llm_client=self._llm())
        result = analyzer.analyze(
            nodeid=case["nodeid"],
            error_message=case.get("error_message") or "",
            screenshot=case.get("screenshot") or "",
        )
        db.upsert_analysis(case_result_id, result)
        return result

    # ---------- AI 用例生成（平台预留，供后续接入） ----------
    def generate_case(self, spec: str, kind: str = "api") -> dict:
        generator = TestGenerator(llm_client=self._llm())
        return generator.generate_case(spec, kind)

    # ---------- flaky 识别 ----------
    def detect_flaky(self) -> dict:
        records = db.recent_records(limit=2000)
        report = self.detector.detect(records)
        log.info(f"[平台] flaky 识别：flaky={report['summary']['detected_flaky']} "
                 f"稳定失败={report['summary']['stable_fail']}")
        return report


ai = AIIntegration()
