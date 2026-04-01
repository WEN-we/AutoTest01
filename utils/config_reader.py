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

    @staticmethod
    def get_ui_config():
        """获取UI自动化配置（替换占位符）"""
        ui_config = ConfigReader.read_yaml("config/ui_config.yaml")
        env_config = ConfigReader.get_env_config()
        # 替换base_ui_url占位符
        ui_config["login_url"] = ui_config["login_url"].format(
            base_ui_url=env_config["base_ui_url"]
        )
        return ui_config


# 测试代码（可删除，验证用）
if __name__ == "__main__":
    # 获取测试环境的API地址
    env_config = ConfigReader.get_env_config()
    print("测试环境API地址：", env_config["base_api_url"])
    # 获取UI配置
    ui_config = ConfigReader.get_ui_config()
    print("登录页面URL：", ui_config["login_url"])
