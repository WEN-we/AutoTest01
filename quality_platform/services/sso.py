"""
轻量 SSO 单点登录（信任令牌模式，个人/团队平台形态）

设计（对齐大厂 SSO 的最小可信闭环，不引第三方依赖）：
- 外部系统用共享密钥（PLATFORM_SECRET）签发 HMAC-SHA256 签名令牌
  -> 用户跳转 /sso/login?token=xxx -> 平台验签 + 过期校验 -> 建立会话 -> 免密进入平台
- 令牌结构：base64url(payload).base64url(hmac_sha256(payload))
  payload = {"sub": 用户名, "role": 角色, "iat": 签发时间, "exp": 过期时间}
- 一次性/短时令牌（默认 5 分钟），防重放靠 exp
- 与平台既有鉴权（session + RBAC）无缝衔接：SSO 只负责「建立信任」，权限仍走角色

安全说明：
- 生产必须固定 PLATFORM_SECRET（.env），令牌签名密钥即会话密钥，泄露等于放行登录
- 仅用于受信任系统间跳转；企业级 OIDC/OAuth2 属架构代差项（见 README 差距清单）
"""
import base64
import hashlib
import hmac
import json
import time
from typing import Any

from quality_platform.security import get_platform_secret

DEFAULT_TTL = 300  # 秒（5 分钟，短时有效防重放）

# 统一密钥源（环境变量 PLATFORM_SECRET > data/secret.key > 进程内随机），
# 修复 CWE-798：此前硬编码公开常量，未设置密钥时任何人都可伪造 admin 令牌。
_secret = get_platform_secret()


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64url_decode(s: str) -> bytes:
    pad = "=" * (-len(s) % 4)
    return base64.urlsafe_b64decode(s + pad)


def _sign(payload_b64: str) -> str:
    return _b64url(hmac.new(_secret.encode("utf-8"), payload_b64.encode("ascii"),
                            hashlib.sha256).digest())


def issue_token(username: str, role: str = "user", ttl: int = DEFAULT_TTL) -> dict:
    """签发 SSO 令牌。返回 {"token", "expires_at"}。"""
    now = int(time.time())
    payload = {"sub": username, "role": role, "iat": now, "exp": now + ttl}
    payload_b64 = _b64url(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    token = f"{payload_b64}.{_sign(payload_b64)}"
    return {"token": token, "expires_at": now + ttl}


def verify_token(token: str) -> dict | None:
    """验签 + 过期校验。合法返回 {"username", "role"}，否则 None。"""
    try:
        payload_b64, sig = token.split(".")
        if not hmac.compare_digest(_sign(payload_b64), sig):
            return None
        payload = json.loads(_b64url_decode(payload_b64))
        now = int(time.time())
        if now > int(payload.get("exp", 0)):
            return None  # 过期
        if now < int(payload.get("iat", 0)) - 60:
            return None  # 时钟偏移容差内
        return {"username": payload.get("sub", ""), "role": payload.get("role", "user")}
    except Exception:
        return None
