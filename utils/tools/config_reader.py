"""
配置读取工具类（项目唯一配置入口）

说明（2026-08-22 收敛）：
- 历史迁移目标 backend.config.settings 已随旧 web_platform 删除，本类收敛为唯一配置入口
- 能力：多环境 yaml（config/*.yaml）+ 环境变量覆盖（${VAR} / ${VAR:-default}）
- 设计：配置与代码分离（大厂标准），敏感信息走环境变量，禁止硬编码

用法：
    from utils.tools.config_reader import ConfigReader
    cfg = ConfigReader.get_ui_config()
    env = ConfigReader.get_env_config()
"""
import yaml
import os
import re
from pathlib import Path

# 导入路径管理工具
from utils.tools.path_manager import get_path

# 获取项目根目录（使用路径管理工具）
PROJECT_ROOT = Path(get_path())


class ConfigReader:
    """配置读取工具类（唯一配置入口）"""

    @staticmethod
    def _warn_deprecated():
        """历史遗留方法（保留空实现以兼容旧调用，不再发废弃警告）"""
        pass

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
    def _resolve_env_var(value):
        """递归解析字符串中的环境变量占位符，支持 ${VAR} 和 ${VAR:-default}"""
        if isinstance(value, str):
            # 匹配 ${VAR:-default} 格式
            m = re.match(r'^\$\{(\w+):-(.+)\}$', value)
            if m:
                return os.environ.get(m.group(1), m.group(2))
            # 匹配 ${VAR} 格式
            m = re.match(r'^\$\{(\w+)\}$', value)
            if m:
                return os.environ.get(m.group(1), '')
            return value
        elif isinstance(value, dict):
            return {k: ConfigReader._resolve_env_var(v) for k, v in value.items()}
        elif isinstance(value, list):
            return [ConfigReader._resolve_env_var(item) for item in value]
        return value

    @staticmethod
    def get_env_config():
        """获取当前激活环境的配置"""
        ConfigReader._warn_deprecated()
        env_config = ConfigReader.read_yaml("config/env_config.yaml")
        active_env = env_config["active_env"]
        raw = env_config[active_env]
        return ConfigReader._resolve_env_var(raw)

    @staticmethod
    def get_db_config():
        """获取数据库配置"""
        ConfigReader._warn_deprecated()
        env = ConfigReader.get_env_config()
        return env["db"]

    @staticmethod
    def get_ui_config():
        """获取UI自动化配置"""
        ConfigReader._warn_deprecated()
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
