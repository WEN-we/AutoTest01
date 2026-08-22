"""
轻量 LLM 客户端（OpenAI 兼容协议）

设计目标（大厂 AI 工具链的底座）：
- 支持任意 OpenAI 兼容服务：通义千问、DeepSeek、OpenAI、本地 vLLM/Ollama 等
- 配置来源（按优先级）：
    1. 环境变量：LLM_BASE_URL / LLM_API_KEY / LLM_MODEL
    2. config/ai_tools.yaml 中的 llm 段
    3. 内置默认值（OpenAI 官方）
- API Key 一律从环境变量/配置文件读取，绝不硬编码进代码

用法：
    from utils.ai.llm_client import LLMClient
    client = LLMClient()
    reply = client.chat("分析这条失败原因：...")
"""
import os

import requests

from utils.tools.logger import log
from utils.tools.config_reader import ConfigReader

DEFAULT_TIMEOUT = 60  # 秒


class LLMClient:
    """OpenAI 兼容 LLM 客户端"""

    def __init__(self, base_url: str = None, api_key: str = None, model: str = None):
        cfg = self._load_config()
        self.base_url = (base_url or os.getenv("LLM_BASE_URL") or cfg.get("base_url")
                         or "https://api.openai.com/v1")
        self.api_key = (api_key or os.getenv("LLM_API_KEY") or cfg.get("api_key") or "")
        self.model = (model or os.getenv("LLM_MODEL") or cfg.get("model")
                      or "gpt-4o-mini")
        self.timeout = cfg.get("timeout", DEFAULT_TIMEOUT)
        self._chat_url = f"{self.base_url.rstrip('/')}/chat/completions"

    @staticmethod
    def _load_config() -> dict:
        """读取 config/ai_tools.yaml（缺失时返回空 dict，不抛异常）"""
        try:
            return ConfigReader.read_yaml("config/ai_tools.yaml").get("llm", {})
        except Exception:
            return {}

    @property
    def available(self) -> bool:
        """是否已配置 API Key（无 Key 时工具链应降级为规则分析）"""
        return bool(self.api_key)

    def chat(self, prompt: str, system: str = "You are a senior QA engineer.",
             temperature: float = 0.2, max_tokens: int = 1200) -> str:
        """发起单轮对话，返回回复文本。未配置 Key 或调用失败时抛异常。"""
        if not self.api_key:
            raise RuntimeError("未配置 LLM_API_KEY / LLM_BASE_URL，请检查环境变量或 config/ai_tools.yaml")
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        log.debug(f"LLM 请求 -> {self.model} @ {self.base_url}")
        resp = requests.post(self._chat_url, json=payload, headers=headers, timeout=self.timeout)
        resp.raise_for_status()
        try:
            return resp.json()["choices"][0]["message"]["content"].strip()
        except (KeyError, IndexError) as exc:
            raise RuntimeError(f"LLM 响应格式异常：{resp.text[:200]}") from exc

    def try_chat(self, prompt: str, system: str = "You are a senior QA engineer.") -> str:
        """容错版：失败返回空串（供上层降级）"""
        try:
            return self.chat(prompt, system=system)
        except Exception as exc:
            log.warning(f"LLM 调用失败：{exc}")
            return ""
