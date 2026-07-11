"""
配置读取工具类（已废弃，请使用 backend.config.settings.Config）

保留原因：
1. 向后兼容：tests/ 目录下的测试代码可能仍在使用
2. 逐步迁移：建议新项目使用 backend.config.settings.Config

迁移指南：
- 旧：from utils.tools.config_reader import ConfigReader; ConfigReader.get_env_config()
- 新：from backend.config.settings import config; config.get_env_config()
"""
import warnings
import yaml
import os
from pathlib import Path

# 导入路径管理工具
from utils.tools.path_manager import get_path

# 获取项目根目录（使用路径管理工具）
PROJECT_ROOT = Path(get_path())


class ConfigReader:
    """配置读取工具类（已废弃，请使用 backend.config.settings.Config）"""

    @staticmethod
    def _warn_deprecated():
        """发出废弃警告"""
        warnings.warn(
            "ConfigReader 已废弃，请使用 backend.config.settings.Config",
            DeprecationWarning,
            stacklevel=3
        )

    @staticmethod
    def read_yaml(file_path):
        """读取YAML文件"""
        ConfigReader._warn_deprecated()
        full_path = get_path(file_path)
        try:
            with open(full_path, "r", encoding="utf-8") as f:
                return yaml.safe_load(f)
        except FileNotFoundError:
            raise Exception(f"配置文件不存在：{full_path}")
        except Exception as e:
            raise Exception(f"读取YAML配置失败：{e}")

    @staticmethod
    def get_env_config():
        """获取当前激活环境的配置"""
        ConfigReader._warn_deprecated()
        # 优先使用新的配置系统
        try:
            from backend.config.settings import config
            return config.get_env_config()
        except ImportError:
            pass

        env_config = ConfigReader.read_yaml("config/env_config.yaml")
        active_env = env_config["active_env"]
        return env_config[active_env]

    @staticmethod
    def get_db_config():
        """获取数据库配置"""
        ConfigReader._warn_deprecated()
        try:
            from backend.config.settings import config
            db_config = config.get_database_config()
            return {
                'host': db_config.get('host'),
                'port': db_config.get('port'),
                'user': db_config.get('username'),
                'pwd': db_config.get('password'),
                'database': db_config.get('database')
            }
        except ImportError:
            pass

        env = ConfigReader.get_env_config()
        return env["db"]

    @staticmethod
    def get_ui_config():
        """获取UI自动化配置"""
        ConfigReader._warn_deprecated()
        try:
            from backend.config.settings import config
            ui_config = config.get_ui_config()
            env_config = config.get_env_config()
            if ui_config and env_config:
                ui_config["login_url"] = ui_config.get("login_url", "").format(
                    base_ui_url=env_config.get("base_ui_url", "")
                )
            return ui_config
        except ImportError:
            pass

        ui_config = ConfigReader.read_yaml("config/ui_config.yaml")
        env_config = ConfigReader.get_env_config()
        ui_config["login_url"] = ui_config["login_url"].format(
            base_ui_url=env_config["base_ui_url"]
        )
        return ui_config

    @staticmethod
    def get_android_config():
        """获取Android配置"""
        ConfigReader._warn_deprecated()
        env = ConfigReader.get_env_config()
        return {
            "base_api_url": env.get("android_api_url", env["base_api_url"]),
            "login_url": f"{env.get('android_api_url')}/login"
        }

    @staticmethod
    def get_ios_config():
        """获取iOS配置"""
        ConfigReader._warn_deprecated()
        env = ConfigReader.get_env_config()
        return {
            "base_api_url": env.get("ios_api_url", env["base_api_url"]),
            "login_url": f"{env.get('ios_api_url')}/login"
        }

    @staticmethod
    def get_harmony_config():
        """获取鸿蒙配置"""
        ConfigReader._warn_deprecated()
        env = ConfigReader.get_env_config()
        return {
            "base_api_url": env.get("harmony_api_url", env["base_api_url"]),
            "login_url": f"{env.get('harmony_api_url')}/login"
        }

    @staticmethod
    def get_windows_config():
        """获取Windows配置"""
        ConfigReader._warn_deprecated()
        env = ConfigReader.get_env_config()
        return {
            "base_api_url": env.get("windows_api_url", env["base_api_url"]),
            "login_url": f"{env.get('windows_api_url')}/login"
        }

    @staticmethod
    def get_linux_config():
        """获取Linux配置"""
        ConfigReader._warn_deprecated()
        return ConfigReader.read_yaml("config/linux_config.yaml")

    @staticmethod
    def get_test_data(module: str):
        """获取测试数据"""
        ConfigReader._warn_deprecated()
        if module in ["web", "android", "ios", "harmony", "windows", "linux_gui"]:
            data = ConfigReader.read_yaml("test_data/ui_test_data.yaml")
            key_map = {
                "web": "login_web",
                "android": "login_android",
                "ios": "login_ios",
                "harmony": "login_harmony",
                "windows": "login_windows",
                "linux_gui": "login_linux_gui"
            }
            return data[key_map[module]]

        elif module in ["api_web", "api_android", "api_ios", "api_harmony", "api_windows"]:
            api_data = ConfigReader.read_yaml("test_data/api_test_data.yaml")
            key_map = {
                "api_web": "user_login_api",
                "api_android": "user_login_android_api",
                "api_ios": "user_login_ios_api",
                "api_harmony": "user_login_harmony_api",
                "api_windows": "user_login_windows_api"
            }
            return api_data[key_map[module]]

        return None
