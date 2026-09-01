"""
质量工程平台 - 统一密钥源（安全基础）

背景修复（CWE-798 硬编码凭证）：
- 此前 sso.py / ai_config.py 各自持有硬编码回退密钥 "quality-platform-insecure-secret"，
  若生产未设置 PLATFORM_SECRET，攻击者可凭公开常量伪造 role=admin 的 SSO 令牌直接接管平台；
  且 app.py 的会话密钥与 SSO/Fernet 密钥三处不一致，安全体系分裂。
- 现在统一由本模块提供平台密钥，优先级：
    1. 环境变量 PLATFORM_SECRET（生产推荐，固定值）
    2. 持久化文件 quality_platform/data/secret.key（首次启动自动生成随机密钥，
       重启可解 Fernet 密文、SSO 令牌跨重启有效）
    3. 进程内随机密钥（仅当 data 目录不可写时兜底，重启后密文/令牌失效，启动时警告）

用法：
    from quality_platform.security import get_platform_secret
    app.secret_key = get_platform_secret()
"""
import os
import secrets
from pathlib import Path

_SECRET_FILE = Path(__file__).resolve().parent / "data" / "secret.key"
_cached: str | None = None


def get_platform_secret() -> str:
    """返回平台统一密钥（环境变量 > 持久化文件 > 进程内随机，带缓存）。"""
    global _cached
    if _cached:
        return _cached

    # 1) 环境变量（生产推荐）
    env = os.getenv("PLATFORM_SECRET", "").strip()
    if env:
        _cached = env
        return env

    # 2) 持久化文件：不存在则生成随机密钥落盘（重启不解锁历史密文/令牌）
    try:
        _SECRET_FILE.parent.mkdir(parents=True, exist_ok=True)
        if _SECRET_FILE.exists():
            val = _SECRET_FILE.read_text(encoding="utf-8").strip()
            if val:
                _cached = val
                return val
        val = secrets.token_hex(32)
        _SECRET_FILE.write_text(val, encoding="utf-8")
        print("[安全] 已生成平台密钥文件 quality_platform/data/secret.key "
              "（生产环境请设置环境变量 PLATFORM_SECRET 固定密钥）")
        _cached = val
        return val
    except Exception as exc:  # 只读文件系统等极端情况：进程内随机
        _cached = secrets.token_hex(32)
        print(f"[安全警告] 无法持久化平台密钥（{exc}），本次使用进程内随机密钥，"
              "重启后会话/SSO 令牌/加密配置将失效")
        return _cached
