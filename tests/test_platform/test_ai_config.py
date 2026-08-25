"""
AI 配置服务 单元测试
覆盖：密钥加解密/脱敏/配置读写/LLM 客户端构建降级/试连
"""
import os
import sys

import pytest

sys.path.insert(0, r"D:\Pthon.Object\PythonProject3")
os.environ["PLATFORM_SECRET"] = "test-ai-secret"

from quality_platform.services import ai_config  # noqa: E402


class TestKeyEncryption:
    def test_encrypt_decrypt_roundtrip(self):
        enc = ai_config.encrypt_key("sk-real-key-123")
        assert enc and enc != "sk-real-key-123"
        assert ai_config.decrypt_key(enc) == "sk-real-key-123"

    def test_empty_key(self):
        assert ai_config.encrypt_key("") == ""
        assert ai_config.decrypt_key("") == ""

    def test_bad_ciphertext_returns_empty(self):
        assert ai_config.decrypt_key("garbage-not-fernet") == ""

    def test_mask(self):
        assert ai_config.mask_key("") == ""
        # sk-1234abcd 共 11 字符：前4 + 3星 + 后4
        assert ai_config.mask_key("sk-1234abcd") == "sk-1***abcd"
        assert len(ai_config.mask_key("short")) == 5


class TestActiveConfig:
    @pytest.fixture
    def fake_db(self, monkeypatch):
        """隔离真实 DB：用内存实现替换 db.get_ai_settings/save_ai_settings，
        避免测试污染真实 AI 配置（本地平台在用的智谱配置不能被覆盖）。"""
        from quality_platform.models import db
        store: dict = {}

        def fake_get():
            return store.get("row")

        def fake_save(provider, base_url, api_key_enc, model, enabled):
            store["row"] = {"provider": provider, "base_url": base_url,
                            "api_key_enc": api_key_enc, "model": model,
                            "enabled": enabled}
            return 1

        monkeypatch.setattr(db, "get_ai_settings", fake_get)
        monkeypatch.setattr(db, "save_ai_settings", fake_save)
        return store

    def test_not_configured_returns_none(self, fake_db):
        """未保存配置 -> get_active_config() 为 None（走环境变量兜底）。"""
        assert ai_config.get_active_config() is None

    def test_save_and_read(self, fake_db):
        db = fake_db
        db["row"] = {"provider": "deepseek", "base_url": "https://api.deepseek.com/v1",
                     "api_key_enc": ai_config.encrypt_key("sk-test"),
                     "model": "deepseek-chat", "enabled": True}
        cfg = ai_config.get_active_config()
        assert cfg["provider"] == "deepseek"
        assert cfg["api_key"] == "sk-test"
        assert cfg["model"] == "deepseek-chat"

    def test_build_llm_client_fallback_env(self, fake_db):
        """无启用配置 -> LLMClient 读环境变量（不抛异常）。"""
        client = ai_config.build_llm_client()
        assert client is not None
        assert hasattr(client, "chat") and hasattr(client, "try_chat")


class TestTestConnection:
    def test_connection_invalid(self):
        """不可达服务 -> ok=False（不抛异常）。"""
        r = ai_config.test_connection("http://127.0.0.1:1/v1", "sk-x", "model")
        assert r["ok"] is False
