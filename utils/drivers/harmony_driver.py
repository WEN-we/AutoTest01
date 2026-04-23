import yaml
import os
from appium import webdriver
from appium.options.android import UiAutomator2Options

class HarmonyDriver:
    @staticmethod
    def get_driver():
        config_path = os.path.join(os.path.dirname(__file__), "../../config/harmony_config.yaml")
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