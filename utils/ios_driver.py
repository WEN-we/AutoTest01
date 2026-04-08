from appium import webdriver
from appium.options.ios import XCUITestOptions
from utils.config_reader import ConfigReader
from utils.logger import logger

class IosDriver:
    """iOS 真机驱动 · XCUITest · 企业规范版"""
    def __init__(self):
        self.config = ConfigReader.read_yaml("config/app_config.yaml")
        self.ios_cfg = self.config["ios"]

    def start_driver(self):
        options = XCUITestOptions()
        caps = {
            "deviceName": self.ios_cfg["deviceName"],
            "udid": self.ios_cfg["udid"],
            "platformVersion": self.ios_cfg["platformVersion"],
            "app": self.ios_cfg["app"],
            "automationName": "XCUITest",
            "noReset": True,
            "useNewWDA": False
        }

        for k, v in caps.items():
            options.set_capability(k, v)

        logger.info("===== iOS 驱动启动中 =====")
        self.driver = webdriver.Remote(
            command_executor="http://127.0.0.1:4723",
            options=options
        )
        self.driver.implicitly_wait(10)
        return self.driver

    def quit_driver(self):
        if hasattr(self, "driver"):
            self.driver.quit()
            logger.info("===== iOS 驱动已退出 =====")