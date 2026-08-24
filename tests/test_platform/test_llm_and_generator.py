"""LLM 客户端 + 用例生成器 单元测试（mock requests，不发真实请求）"""
from unittest.mock import MagicMock, patch

import pytest

import utils.ai.llm_client as llm_mod
from utils.ai.llm_client import LLMClient
# 别名避免 pytest 把 Test* 类误收集为测试类
from utils.ai.test_generator import TestGenerator as AITestGenerator


@pytest.fixture(autouse=True)
def clean_env(monkeypatch):
    """隔离环境变量，避免宿主配置影响测试"""
    for var in ("LLM_BASE_URL", "LLM_API_KEY", "LLM_MODEL"):
        monkeypatch.delenv(var, raising=False)


class TestLLMClientConfig:
    def test_explicit_params_win(self, monkeypatch):
        monkeypatch.setenv("LLM_API_KEY", "env-key")
        c = LLMClient(base_url="https://x/v1", api_key="explicit", model="m1")
        assert c.api_key == "explicit"
        assert c.base_url == "https://x/v1"
        assert c.model == "m1"

    def test_env_overrides_config(self, monkeypatch):
        monkeypatch.setenv("LLM_API_KEY", "env-key")
        monkeypatch.setenv("LLM_MODEL", "env-model")
        c = LLMClient()
        assert c.api_key == "env-key"
        assert c.model == "env-model"

    def test_defaults_without_key(self):
        c = LLMClient()
        assert c.api_key == ""
        assert c.available is False

    def test_available_with_key(self, monkeypatch):
        monkeypatch.setenv("LLM_API_KEY", "k")
        assert LLMClient().available is True

    def test_chat_url_built_from_base(self):
        c = LLMClient(base_url="https://api.test/v1/")
        assert c._chat_url == "https://api.test/v1/chat/completions"


class TestLLMClientChat:
    def _client(self):
        return LLMClient(base_url="https://x/v1", api_key="k", model="m")

    @patch.object(llm_mod.requests, "post")
    def test_chat_success(self, mock_post):
        resp = MagicMock()
        resp.json.return_value = {"choices": [{"message": {"content": "  hi  "}}]}
        mock_post.return_value = resp
        assert self._client().chat("p") == "hi"
        # 请求头带 Bearer Key
        _, kwargs = mock_post.call_args
        assert kwargs["headers"]["Authorization"] == "Bearer k"

    def test_chat_without_key_raises(self):
        c = LLMClient(base_url="https://x/v1")  # 无 Key
        with pytest.raises(RuntimeError, match="未配置"):
            c.chat("p")

    @patch.object(llm_mod.requests, "post")
    def test_chat_bad_response_format(self, mock_post):
        """响应缺 choices → 明确报错（而非 KeyError 裸抛）"""
        resp = MagicMock()
        resp.json.return_value = {"unexpected": True}
        resp.text = '{"unexpected": true}'
        mock_post.return_value = resp
        with pytest.raises(RuntimeError, match="响应格式异常"):
            self._client().chat("p")

    @patch.object(llm_mod.requests, "post")
    def test_try_chat_degrades_to_empty(self, mock_post):
        """try_chat 失败返回空串（供上层降级），不抛异常"""
        mock_post.side_effect = ConnectionError("network down")
        assert self._client().try_chat("p") == ""

    @patch.object(llm_mod.time, "sleep")
    @patch.object(llm_mod.requests, "post")
    def test_retry_on_429_then_success(self, mock_post, mock_sleep):
        """429 限流 → 指数退避重试后成功"""
        ok_resp = MagicMock()
        ok_resp.json.return_value = {"choices": [{"message": {"content": "ok"}}]}
        mock_post.side_effect = [llm_mod.requests.HTTPError(response=MagicMock(status_code=429)), ok_resp]
        c = self._client()
        c.retries = 3
        assert c.chat("p") == "ok"
        # 指数退避：1s（首次失败后）
        mock_sleep.assert_called_once_with(1.0)

    @patch.object(llm_mod.time, "sleep")
    @patch.object(llm_mod.requests, "post")
    def test_retry_on_connection_error(self, mock_post, mock_sleep):
        """网络异常（requests.ConnectionError）→ 重试；重试成功即返回"""
        ok_resp = MagicMock()
        ok_resp.json.return_value = {"choices": [{"message": {"content": "ok"}}]}
        net_err = llm_mod.requests.ConnectionError("down")
        mock_post.side_effect = [net_err, net_err, ok_resp]
        c = self._client()
        c.retries = 3
        assert c.chat("p") == "ok"
        assert mock_sleep.call_count == 2
        # 退避序列 1s, 2s
        mock_sleep.assert_any_call(1.0)
        mock_sleep.assert_any_call(2.0)

    @patch.object(llm_mod.time, "sleep")
    @patch.object(llm_mod.requests, "post")
    def test_no_retry_on_401(self, mock_post, mock_sleep):
        """4xx 鉴权失败 → 不重试快速失败"""
        mock_post.side_effect = llm_mod.requests.HTTPError(
            response=MagicMock(status_code=401))
        c = self._client()
        c.retries = 3
        with pytest.raises(llm_mod.requests.HTTPError):
            c.chat("p")
        mock_sleep.assert_not_called()
        assert mock_post.call_count == 1

    @patch.object(llm_mod.time, "sleep")
    @patch.object(llm_mod.requests, "post")
    def test_retry_exhausted_raises(self, mock_post, mock_sleep):
        """重试耗尽后抛最后异常"""
        mock_post.side_effect = llm_mod.requests.HTTPError(
            response=MagicMock(status_code=503))
        c = self._client()
        c.retries = 2
        with pytest.raises(llm_mod.requests.HTTPError):
            c.chat("p")
        assert mock_post.call_count == 2   # 首次 + 1 次重试

    @patch.object(llm_mod.time, "sleep")
    @patch.object(llm_mod.requests, "post")
    def test_no_retry_on_malformed_response(self, mock_post, mock_sleep):
        """响应格式异常（业务错误）→ 不重试"""
        bad_resp = MagicMock()
        bad_resp.json.return_value = {"unexpected": True}
        bad_resp.text = "{}"
        mock_post.return_value = bad_resp
        c = self._client()
        c.retries = 3
        with pytest.raises(RuntimeError, match="响应格式异常"):
            c.chat("p")
        mock_sleep.assert_not_called()


class TestGeneratorBehavior:
    def test_template_fallback_without_key(self):
        gen = AITestGenerator(llm_client=LLMClient())  # 无 Key
        result = gen.generate_case("登录接口返回 token", test_type="api")
        assert result["source"] == "template"
        assert "import pytest" in result["code"]
        assert "APIClient" in result["code"]

    def test_template_ui(self):
        gen = AITestGenerator(llm_client=LLMClient())
        result = gen.generate_case("登录页流程", test_type="ui")
        assert result["source"] == "template"
        assert "LoginPage" in result["code"]

    def test_llm_generation(self):
        class FakeLLM:
            available = True

            def chat(self, prompt, system=""):
                return "```python\ndef test_x():\n    assert True\n```"

            def try_chat(self, prompt, system=""):
                return self.chat(prompt, system)

        gen = AITestGenerator(llm_client=FakeLLM())
        result = gen.generate_case("登录接口", test_type="api")
        assert result["source"] == "llm"
        assert result["code"].startswith("def test_x")  # 代码块标记被剥离

