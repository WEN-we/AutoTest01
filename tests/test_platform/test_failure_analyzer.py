"""FailureAnalyzer 单元测试：规则引擎分类 / LLM 归因 / LLM 失败降级"""
import pytest

from utils.ai.failure_analyzer import FailureAnalyzer


class FakeLLM:
    """可控的 LLM 桩：预设回复或抛异常"""

    def __init__(self, reply="", available=True, raise_exc=None):
        self.reply = reply
        self.available = available
        self.raise_exc = raise_exc
        self.last_prompt = ""

    def chat(self, prompt, system=""):
        self.last_prompt = prompt
        if self.raise_exc:
            raise self.raise_exc
        return self.reply


class TestRuleEngine:
    """未配置 LLM（available=False）时走规则引擎"""

    def _analyzer(self):
        return FailureAnalyzer(llm_client=FakeLLM(available=False))

    @pytest.mark.parametrize("message,expect_category", [
        ("TimeoutException: timed out after 30s", "环境波动/页面加载慢"),
        ("NoSuchElementException: no such element", "定位器失效/元素缺失"),
        ("AssertionError: assert 200 == 500", "产品缺陷或断言错误"),
        ("ConnectionError: connection refused", "环境波动/网络"),
        ("StaleElementReferenceException: stale element", "页面已刷新"),
        ("TypeError: unsupported operand", "测试代码缺陷"),
        ("KeyError: 'token'", "测试代码缺陷或数据问题"),
    ])
    def test_rule_categories(self, message, expect_category):
        result = self._analyzer().analyze(nodeid="t::x", error_message=message)
        assert result["category"] == expect_category
        assert result["source"] == "rule"
        assert result["suggestion"]

    def test_rule_unknown_fallback(self):
        result = self._analyzer().analyze(nodeid="t::x", error_message="完全无法识别的错误")
        assert result["category"] == "未知"
        assert result["confidence"] == 0.2

    def test_rule_result_carries_nodeid_screenshot(self):
        result = self._analyzer().analyze(nodeid="a::b", error_message="TimeoutException",
                                           screenshot="reports/s.png")
        assert result["nodeid"] == "a::b"
        assert result["screenshot"] == "reports/s.png"


class TestLLMMode:
    def test_llm_structured_result(self):
        """LLM 返回带 markdown 代码块的 JSON → 正确解析"""
        reply = ('```json\n{"category": "产品缺陷", "confidence": 0.9, '
                 '"suggestion": "提单", "key_evidence": "断言失败"}\n```')
        analyzer = FailureAnalyzer(llm_client=FakeLLM(reply=reply))
        result = analyzer.analyze(nodeid="t::x", error_message="AssertionError")
        assert result["source"] == "llm"
        assert result["category"] == "产品缺陷"
        assert result["confidence"] == 0.9
        assert result["key_evidence"] == "断言失败"

    def test_llm_json_with_noise(self):
        """LLM 回复夹带说明文字 → 仍能提取 JSON"""
        reply = ('好的，分析如下：{"category": "环境波动", "confidence": 0.7, '
                 '"suggestion": "重跑", "key_evidence": "超时"} 以上。')
        analyzer = FailureAnalyzer(llm_client=FakeLLM(reply=reply))
        result = analyzer.analyze(nodeid="t::x", error_message="TimeoutException")
        assert result["source"] == "llm"
        assert result["category"] == "环境波动"

    def test_llm_invalid_json_fallback_to_rule(self):
        """LLM 返回非法 JSON → 降级规则引擎"""
        analyzer = FailureAnalyzer(llm_client=FakeLLM(reply="这不是JSON"))
        result = analyzer.analyze(nodeid="t::x", error_message="TimeoutException")
        assert result["source"] == "rule"
        assert result["category"] == "环境波动/页面加载慢"

    def test_llm_exception_fallback_to_rule(self):
        """LLM 调用异常 → 降级规则引擎"""
        analyzer = FailureAnalyzer(
            llm_client=FakeLLM(raise_exc=RuntimeError("网络错误")))
        result = analyzer.analyze(nodeid="t::x", error_message="TimeoutException")
        assert result["source"] == "rule"

    def test_context_includes_evidence(self):
        """上下文应包含用例名 / 错误信息 / 截图路径"""
        llm = FakeLLM(reply='{"category":"产品缺陷","confidence":0.5,'
                            '"suggestion":"s","key_evidence":"e"}')
        FailureAnalyzer(llm_client=llm).analyze(
            nodeid="tests/test_login.py::test_ok",
            error_message="AssertionError boom",
            screenshot="reports/s.png",
        )
        assert "tests/test_login.py::test_ok" in llm.last_prompt
        assert "AssertionError boom" in llm.last_prompt
        assert "reports/s.png" in llm.last_prompt

    def test_traceback_fallback_to_error_message_tail(self):
        """未单独提供 traceback 时，上下文回退用 error_message 尾部"""
        llm = FakeLLM(reply='{"category":"产品缺陷","confidence":0.5,'
                            '"suggestion":"s","key_evidence":"e"}')
        long_error = "E" * 2000 + "TAIL_MARKER"
        FailureAnalyzer(llm_client=llm).analyze(nodeid="t::x",
                                                error_message=long_error)
        # 尾部 1500 字符应包含 TAIL_MARKER，且不重复出现头部内容
        assert "TAIL_MARKER" in llm.last_prompt
