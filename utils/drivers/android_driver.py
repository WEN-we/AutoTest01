from appium import webdriver
from appium.options.android import UiAutomator2Options
from utils.tools.config_reader import ConfigReader
from utils.tools.path_manager import get_config_path

class AndroidDriver:
    def __init__(self):
        # 使用路径管理工具获取配置文件路径
        self.config = ConfigReader.read_yaml(get_config_path("app_config.yaml"))
        self.android_cfg = self.config["android"]

    def start_driver(self):
        # 新版必须用 options 模式，不能传 dict！
        options = UiAutomator2Options()
        options.load_capabilities(self.android_cfg)

        driver = webdriver.Remote(
            command_executor="http://127.0.0.1:4723",
            options=options
        )
        driver.implicitly_wait(10)
        return driver