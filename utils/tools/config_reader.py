import yaml
import os
from pathlib import Path

# 获取项目根目录（自动识别，不用硬编码路径）
PROJECT_ROOT = Path(__file__).parent.parent


class ConfigReader:
    """配置读取工具类（通用，无需修改）"""

    @staticmethod
    def read_yaml(file_path):
        """读取YAML文件"""
        full_path = PROJECT_ROOT / file_path
        try:
            with open(full_path, "r", encoding="utf-8") as f:
                return yaml.safe_load(f)
        except FileNotFoundError:
            raise Exception(f"配置文件不存在：{full_path}")
        except Exception as e:
            raise Exception(f"读取YAML配置失败：{e}")

    @staticmethod
    def get_env_config():
        """获取当前激活环境的配置（核心：一键切换环境）"""
        env_config = ConfigReader.read_yaml("config/env_config.yaml")
        active_env = env_config["active_env"]
        return env_config[active_env]

    # ====================== 【新增：数据库配置】只需加这一个方法 ======================
    @staticmethod
    def get_db_config():
        env = ConfigReader.get_env_config()
        return env["db"]

    @staticmethod
    def get_ui_config():
        """获取UI自动化配置（替换占位符）"""
        ui_config = ConfigReader.read_yaml("config/ui_config.yaml")
        env_config = ConfigReader.get_env_config()
        ui_config["login_url"] = ui_config["login_url"].format(
            base_ui_url=env_config["base_ui_url"]
        )
        return ui_config

    # ====================== 全平台统一配置方法 ======================
    @staticmethod
    def get_android_config():
        env = ConfigReader.get_env_config()
        return {
            "base_api_url": env.get("android_api_url", env["base_api_url"]),
            "login_url": f"{env.get('android_api_url')}/login"
        }

    @staticmethod
    def get_ios_config():
        env = ConfigReader.get_env_config()
        return {
            "base_api_url": env.get("ios_api_url", env["base_api_url"]),
            "login_url": f"{env.get('ios_api_url')}/login"
        }

    @staticmethod
    def get_harmony_config():
        env = ConfigReader.get_env_config()
        return {
            "base_api_url": env.get("harmony_api_url", env["base_api_url"]),
            "login_url": f"{env.get('harmony_api_url')}/login"
        }

    @staticmethod
    def get_windows_config():
        env = ConfigReader.get_env_config()
        return {
            "base_api_url": env.get("windows_api_url", env["base_api_url"]),
            "login_url": f"{env.get('windows_api_url')}/login"
        }

    @staticmethod
    def get_linux_config():
        return ConfigReader.read_yaml("config/linux_config.yaml")

    # ====================== 全平台测试数据读取 ======================
    @staticmethod
    def get_test_data(module: str):
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

        # API 数据
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


# 测试代码（可删除，验证用）
if __name__ == "__main__":
    env_config = ConfigReader.get_env_config()
    print("测试环境API地址：", env_config["base_api_url"])
    print("数据库配置：", ConfigReader.get_db_config())  # 测试数据库配置