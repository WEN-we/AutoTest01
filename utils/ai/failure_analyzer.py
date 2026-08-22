"""
失败智能分析器（大厂稳定性治理核心：失败即证据 + 智能归因）

能力：
- LLM 模式：把失败上下文（错误信息/堆栈/截图路径/日志/测试名）喂给大模型，
  输出结构化归因：类别（产品缺陷 / 测试缺陷 / 环境波动 / 定位器失效）+ 建议
- 规则降级：未配置 LLM Key 或调用失败时，用关键词规则快速分类（常见异常类型映射）

用法：
    from utils.ai.failure_analyzer import FailureAnalyzer
    analyzer = FailureAnalyzer()
    result = analyzer.analyze(nodeid="test_login::test_empty_password",
                              error_message="TimeoutException...",
                              traceback="...", screenshot="reports/screenshots/xxx.png")
    # result = {"category": "...", "confidence": ..., "suggestion": "...", "source": "llm|rule"}
"""
import json
import re

from utils.ai.llm_client import LLMClient
from utils.tools.logger import log

# 规则引擎：异常类型 -> (类别, 建议关键词)
_RULE_MAP = [
    (re.compile(r"TimeoutException|ElementClickInterceptedException|等待.*超时|timed? ?out", re.I),
     ("环境波动/页面加载慢", "多为偶发：检查显式等待是否足够，可依赖 --reruns 自动重试")),
    (re.compile(r"NoSuchElementException|ElementNotFound|no such element|not found", re.I),
     ("定位器失效/元素缺失", "页面结构可能变更：核对定位器，建议用 data-testid 契约属性")),
    (re.compile(r"AssertionError|断言失败|assert ", re.I),
     ("产品缺陷或断言错误", "核对预期值与实际值：真实缺陷则提单；断言写错则修正用例")),
    (re.compile(r"ConnectionError|Connection refused|ConnectTimeout|网络|connection", re.I),
     ("环境波动/网络", "被测服务未启动或网络抖动：检查服务可用性后重跑")),
    (re.compile(r"StaleElementReferenceException|stale element", re.I),
     ("页面已刷新", "操作前元素已过期：改用等待可点击后立即操作")),
    (re.compile(r"TypeError|NameError|ImportError|ModuleNotFoundError|AttributeError", re.I),
     ("测试代码缺陷", "用例/封装代码报错：修复代码问题，非被测产品问题")),
    (re.compile(r"KeyError|ValueError|IndexError|JSONDecodeError|解析", re.I),
     ("测试代码缺陷或数据问题", "检查测试数据/响应结构是否与用例预期一致")),
]

_SYSTEM_PROMPT = (
    "你是一名资深测试开发工程师。请根据提供的自动化测试失败信息，判断失败根因类别，"
    "并给出可执行的修复建议。只输出 JSON，格式："
    '{"category": "产品缺陷|测试缺陷|环境波动|定位器失效", "confidence": 0-1, '
    '"suggestion": "具体建议", "key_evidence": "关键证据一句话"}'
)


class FailureAnalyzer:
    """自动化用例失败智能分析器"""

    def __init__(self, llm_client: LLMClient = None):
        self.llm = llm_client or LLMClient()

    # ---------- 对外接口 ----------
    def analyze(self, nodeid: str = "", error_message: str = "", traceback: str = "",
                screenshot: str = "", log_tail: str = "") -> dict:
        """分析失败原因。优先 LLM，失败/未配置时走规则引擎。"""
        context = self._build_context(nodeid, error_message, traceback, screenshot, log_tail)

        if self.llm.available:
            llm_result = self._analyze_by_llm(context)
            if llm_result:
                return llm_result

        rule_result = self._analyze_by_rule(error_message or traceback)
        rule_result["screenshot"] = screenshot
        rule_result["nodeid"] = nodeid
        return rule_result

    # ---------- LLM 模式 ----------
    def _build_context(self, nodeid, error_message, traceback, screenshot, log_tail) -> str:
        parts = [f"测试用例: {nodeid or '未知'}"]
        if error_message:
            parts.append(f"错误信息: {error_message[:500]}")
        if traceback:
            parts.append(f"堆栈(尾部): {traceback[-1500:]}")
        if log_tail:
            parts.append(f"日志(尾部): {log_tail[-1000:]}")
        if screenshot:
            parts.append(f"失败截图: {screenshot}（请结合常见 UI 问题推断）")
        return "\n".join(parts)

    def _analyze_by_llm(self, context: str) -> dict | None:
        """调用 LLM 归因，解析 JSON 结果；任何失败返回 None 以便降级。"""
        try:
            raw = self.llm.chat(context, system=_SYSTEM_PROMPT)
            raw_clean = raw.strip().strip("```json").strip("```").strip()
            start, end = raw_clean.find("{"), raw_clean.rfind("}")
            data = json.loads(raw_clean[start:end + 1]) if start >= 0 else {}
            category = data.get("category", "未知")
            return {
                "category": category,
                "confidence": float(data.get("confidence", 0.5)),
                "suggestion": data.get("suggestion", ""),
                "key_evidence": data.get("key_evidence", ""),
                "source": "llm",
            }
        except Exception as exc:
            log.warning(f"LLM 归因解析失败，降级规则引擎：{exc}")
            return None

    # ---------- 规则降级 ----------
    def _analyze_by_rule(self, text: str) -> dict:
        for pattern, (category, suggestion) in _RULE_MAP:
            if pattern.search(text or ""):
                return {"category": category, "confidence": 0.5,
                        "suggestion": suggestion, "key_evidence": pattern.pattern,
                        "source": "rule"}
        return {"category": "未知", "confidence": 0.2,
                "suggestion": "无法自动归因，请结合截图与日志人工排查。",
                "key_evidence": "", "source": "rule"}
