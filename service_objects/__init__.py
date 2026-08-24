"""服务层（Service Objects）包

懒加载（PEP 562）：只有真正用到对应服务时才导入子模块，
避免 `service_objects.ec_login_service` 等轻依赖被迫拉起
paramiko（linux_service 专用，仅在 ENABLE_SERVICE=1 时需要）。

用法（两种等价，均不触发 linux 依赖）：
    from service_objects.ec_login_service import EcLoginService
    from service_objects import EcLoginService   # 懒加载，同样支持
"""
from typing import Any

_LAZY_EXPORTS = {
    "BaseService": ("service_objects.base_service", "BaseService"),
    "EcLoginService": ("service_objects.ec_login_service", "EcLoginService"),
    "LinuxService": ("service_objects.linux_service", "LinuxService"),
}


def __getattr__(name: str) -> Any:
    if name in _LAZY_EXPORTS:
        import importlib
        module_path, attr = _LAZY_EXPORTS[name]
        return getattr(importlib.import_module(module_path), attr)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = list(_LAZY_EXPORTS)
