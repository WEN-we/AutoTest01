import yaml
import os
from appium import webdriver
from appium.options.android import UiAutomator2Options

# 导入路径管理工具
from utils.tools.path_manager import get_config_path

class HarmonyDriver:
    @staticmethod
    def get_driver():
        # 使用路径管理工具获取配置文件路径
        config_path = get_config_path("harmony_config.yaml")
        with open(config_path, "r", encoding="utf-8") as f:
            cfg = yaml.safe_load(f)

        options = UiAutomator2Options()
        options.load_capabilities({
            "platformName": "Harmony",
            "deviceName": cfg["device_name"],
            "udid": cfg["udid"],
            "appPackage": cfg["app_package"],
            "appActivity": cfg["app_activity"],
            "noReset": True,
            "automationName": "UiAutomator2"
        })

        driver = webdriver.Remote("http://127.0.0.1:4723", options=options)
        driver.implicitly_wait(10)
        return driver