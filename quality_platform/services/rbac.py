"""
细粒度 RBAC（角色访问控制，P2 身份安全升级）。

角色三级（大厂平台常见最小集）：
- admin   平台管理员：全部权限（含 AI 配置密钥、SSO 签发、用户角色管理）
- engineer 测试工程师：执行测试、用例库管理、审计查看（不含密钥/用户管理）
- viewer  只读访客：查看看板/执行/失败/指标

权限点：
- view        查看（登录即有）
- run         触发测试执行
- case_edit   用例库增删改
- audit       审计日志查看
- ai_config   AI 配置（密钥）读写
- user_admin  用户角色管理
"""
from __future__ import annotations

ROLES = ("admin", "engineer", "viewer")

# 角色 -> 权限集合（admin 用通配）
PERMISSIONS: dict[str, set[str]] = {
    "admin": {"*"},
    "engineer": {"view", "run", "case_edit", "audit"},
    "viewer": {"view"},
}

ALL_PERMISSIONS = ("view", "run", "case_edit", "audit", "ai_config", "user_admin")


def has_permission(role: str | None, perm: str) -> bool:
    """角色是否拥有权限（admin 通配所有；未知角色视为 viewer）。"""
    role = (role or "viewer").strip().lower()
    perms = PERMISSIONS.get(role)
    if not perms:
        perms = PERMISSIONS["viewer"]
    return "*" in perms or perm in perms


def role_label(role: str | None) -> str:
    return {
        "admin": "管理员",
        "engineer": "测试工程师",
        "viewer": "只读访客",
        "user": "只读访客",   # 历史 role='user' 按只读展示
    }.get((role or "viewer").lower(), (role or "viewer"))
