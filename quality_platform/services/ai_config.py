"""
质量工程平台 - AI 配置服务（管理员在页面配置 AI 密钥 / 本地模型）

能力：
- 密钥加密存储：api_key 用 Fernet 加密后入库（密钥由 PLATFORM_SECRET 派生，不落明文）
- 多服务商模板：DeepSeek / 通义千问(Qwen) / 豆包(火山方舟) / Ollama(本地) / 自定义(OpenAI 兼容)
- 优先级：平台配置(enabled=1) > 环境变量 LLM_BASE_URL/LLM_API_KEY/LLM_MODEL > config/ai_tools.yaml
- build_llm_client()：平台侧所有 AI 调用统一入口（失败归因/用例生成/flaky），
  有平台配置就用平台配置，否则回退环境变量 —— 保证「页面配了就走页面」
- 无 Key / 本地模型不需要 Key（Ollama）：api_key 可留空，available 判定自动适配

安全说明：
- PLATFORM_SECRET 未配置时用随机密钥（重启后历史密文无法解密，需重新保存）——生产建议固定
"""
import base64
import hashlib
from datetime import datetime

from cryptography.fernet import Fernet

from quality_platform.models import db
from quality_platform.security import get_platform_secret
from utils.tools.logger import log

# 服务商预设模板（前端下拉 + 试连默认值）
PROVIDER_PRESETS = {
    "deepseek": {
        "label": "DeepSeek",
        "base_url": "https://api.deepseek.com/v1",
        "model": "deepseek-chat",
        "need_key": True,
    },
    "qwen": {
        "label": "通义千问（阿里云百炼）",
        "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "model": "qwen3.7-flash",   # Flash 免费档（qwen-plus 需付费额度）
        "need_key": True,
    },
    "doubao": {
        "label": "豆包（火山方舟）",
        "base_url": "https://ark.cn-beijing.volces.com/api/v3",
        "model": "doubao-1-5-pro-32k-250115",
        "need_key": True,
    },
    "zhipu": {
        "label": "智谱 GLM（OpenAI 兼容）",
        "base_url": "https://open.bigmodel.cn/api/paas/v4",
        "model": "glm-4-flash",
        "need_key": True,
    },
    "ollama": {
        "label": "Ollama 本地模型",
        "base_url": "http://127.0.0.1:11434/v1",
        "model": "qwen2.5:7b",
        "need_key": False,
    },
    "custom": {
        "label": "自定义（OpenAI 兼容）",
        "base_url": "",
        "model": "",
        "need_key": False,
    },
}


def _fernet(secret: str | None = None) -> Fernet:
    """由平台统一密钥派生 Fernet 密钥（确定性，重启后可解密）。"""
    secret = secret or get_platform_secret()
    digest = hashlib.sha256(secret.encode("utf-8")).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


# 历史遗留密钥（仅用于一次性迁移旧密文，绝不用于任何新加密）：
# 平台早期未统一密钥源时用硬编码常量派生 Fernet，导致历史 ai_settings.api_key_enc
# 无法用新平台密钥解密。decrypt_key 检测到旧格式密文时自动重加密为当前密钥后返回明文。
_LEGACY_SECRET = "quality-platform-insecure-secret"


def encrypt_key(plain: str) -> str:
    """加密 API Key（空值直接返回空串）。"""
    if not plain:
        return ""
    try:
        return _fernet().encrypt(plain.encode("utf-8")).decode("utf-8")
    except Exception as exc:
        log.warning(f"[AI配置] 密钥加密失败：{exc}")
        return ""


def _decrypt_with(secret: str, token: str) -> str | None:
    try:
        return _fernet(secret).decrypt(token.encode("utf-8")).decode("utf-8")
    except Exception:
        return None


def decrypt_key(token: str) -> str:
    """解密 API Key（解密失败返回空串，避免异常外泄）。
    优先当前平台密钥；失败则尝试历史遗留密钥，命中后自动迁移密文为当前密钥。"""
    if not token:
        return ""
    plain = _decrypt_with(get_platform_secret(), token)
    if plain is not None:
        return plain
    legacy_plain = _decrypt_with(_LEGACY_SECRET, token)
    if legacy_plain is not None:
        # 历史密文：用当前密钥重新加密并落库（无感迁移，旧密钥即刻弃用）
        try:
            new_enc = encrypt_key(legacy_plain)
            with db._conn() as conn:
                conn.execute("UPDATE ai_settings SET api_key_enc=? WHERE api_key_enc=?",
                             (new_enc, token))
            log.info("[AI配置] 历史密钥密文已迁移到当前平台密钥")
        except Exception as exc:  # 迁移失败不影响本次返回明文
            log.warning(f"[AI配置] 密钥密文迁移失败：{exc}")
        return legacy_plain
    log.warning("[AI配置] 密钥解密失败（平台密钥变更或密文损坏，请重新保存 API Key）")
    return ""


def mask_key(api_key: str) -> str:
    """脱敏展示：保留前 4 与后 4 位（sk-****abcd）。"""
    if not api_key:
        return ""
    if len(api_key) <= 8:
        return "*" * len(api_key)
    return f"{api_key[:4]}{'*' * (len(api_key) - 8)}{api_key[-4:]}"


def get_active_config() -> dict | None:
    """
    获取当前生效的 AI 配置（enabled=1）。
    返回 {provider, base_url, api_key, model}，供 build_llm_client / 试连使用。
    """
    row = db.get_ai_settings()
    if not row or not row.get("enabled"):
        return None
    return {
        "provider": row["provider"],
        "base_url": row["base_url"],
        "api_key": decrypt_key(row.get("api_key_enc") or ""),
        "model": row["model"],
    }


def build_llm_client():
    """
    平台 AI 调用统一入口：平台配置优先，回退环境变量。
    返回 utils.ai.llm_client.LLMClient 实例（惰性导入，避免循环依赖）。
    """
    from utils.ai.llm_client import LLMClient

    cfg = get_active_config()
    if cfg:
        log.info(f"[AI配置] 使用平台配置：{cfg['provider']} / {cfg['model']} @ {cfg['base_url']}")
        return LLMClient(base_url=cfg["base_url"], api_key=cfg["api_key"],
                         model=cfg["model"])
    client = LLMClient()
    log.info(f"[AI配置] 未启用平台配置，回退环境变量：{client.base_url} / {client.model}")
    return client


def test_connection(base_url: str, api_key: str, model: str) -> dict:
    """试连：用给定参数发起一句话对话。返回 {ok, message}。"""
    from utils.ai.llm_client import LLMClient

    client = LLMClient(base_url=base_url, api_key=api_key, model=model)
    if not client.available:
        return {"ok": False,
                "message": "未配置 API Key（本地模型如 Ollama 可留空，但需确认服务已启动）"}
    reply = client.try_chat("请只回复两个字：连通")
    if reply:
        return {"ok": True, "message": f"连通成功，模型回复：{reply[:30]}"}
    return {"ok": False, "message": "调用失败（服务不可达 / Key 无效 / 模型名错误），请查看平台日志"}
