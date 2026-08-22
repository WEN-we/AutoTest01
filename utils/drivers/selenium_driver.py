"""
Selenium 驱动生命周期封装（大厂分层规范：驱动层只负责"启动/退出"，元素操作统一在 PO 基类）

职责边界：
- SeleniumDriver（本文件）        ：浏览器生命周期管理（启动/配置/退出），配置从 ui_config.yaml 读取
- SeleniumBasePage（page_objects/web/selenium_base_page.py）：元素定位与页面操作（唯一操作封装）
- 用例层通过 fixture 获取 driver，再注入 PO 使用（依赖注入）

升级记录（2026-08-22）：移除原 SeleniumDriver 中与 SeleniumBasePage 重复的元素操作方法
（find_element/click/input_text 等约 30 个），消除约 90% 代码重复。
"""
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.firefox.service import Service as FirefoxService
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from selenium.webdriver.edge.service import Service as EdgeService
from selenium.webdriver.edge.options import Options as EdgeOptions
from utils.tools.config_reader import ConfigReader
from utils.tools.logger import log


class SeleniumDriver:
    """Selenium Web驱动生命周期封装（Chrome/Firefox/Edge）"""

    BROWSER_MAP = {
        'chrome': (webdriver.Chrome, ChromeOptions, ChromeService),
        'firefox': (webdriver.Firefox, FirefoxOptions, FirefoxService),
        'edge': (webdriver.Edge, EdgeOptions, EdgeService),
    }

    def __init__(self, browser: str = None):
        self.ui_config = ConfigReader.get_ui_config()
        self.browser_name = browser or self.ui_config.get("browser", "chrome")
        self.timeout = self.ui_config.get("timeout", 10)
        self.headless = self.ui_config.get("headless", False)
        self.window_size = self.ui_config.get("window_size", "1920x1080")
        self.driver = None

    def start_driver(self):
        """启动浏览器"""
        browser_key = self.browser_name.lower()
        if browser_key not in self.BROWSER_MAP:
            log.warning(f"不支持的浏览器: {self.browser_name}，使用默认Chrome")
            browser_key = 'chrome'

        driver_class, options_class, service_class = self.BROWSER_MAP[browser_key]
        options = options_class()

        if browser_key == 'chrome':
            self._set_chrome_options(options)
        elif browser_key == 'firefox':
            self._set_firefox_options(options)
        elif browser_key == 'edge':
            self._set_edge_options(options)

        try:
            self.driver = driver_class(options=options)
        except Exception as e:
            log.error(f"启动{self.browser_name}失败: {e}，尝试使用默认配置")
            self.driver = driver_class()

        self._set_window_size()
        self.driver.implicitly_wait(self.timeout)
        log.info(f"Selenium浏览器启动成功: {self.browser_name}, headless={self.headless}")
        return self.driver

    def _set_chrome_options(self, options: ChromeOptions):
        """设置Chrome选项"""
        if self.headless:
            options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        options.add_argument('--disable-extensions')
        options.add_argument('--disable-popup-blocking')
        options.add_argument('--ignore-certificate-errors')
        options.add_argument('--window-size=' + self.window_size.replace('x', ','))
        options.add_experimental_option('excludeSwitches', ['enable-logging'])
        prefs = {
            'credentials_enable_service': False,
            'profile.password_manager_enabled': False
        }
        options.add_experimental_option('prefs', prefs)

    def _set_firefox_options(self, options: FirefoxOptions):
        """设置Firefox选项"""
        if self.headless:
            options.add_argument('--headless')
        width, height = self.window_size.split('x')
        options.add_argument(f'--width={width}')
        options.add_argument(f'--height={height}')

    def _set_edge_options(self, options: EdgeOptions):
        """设置Edge选项"""
        if self.headless:
            options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        options.add_argument('--window-size=' + self.window_size.replace('x', ','))

    def _set_window_size(self):
        """设置窗口大小"""
        try:
            width, height = map(int, self.window_size.split('x'))
            self.driver.set_window_size(width, height)
        except Exception:
            self.driver.maximize_window()

    def quit_driver(self):
        """关闭浏览器"""
        if self.driver:
            self.driver.quit()
            log.info("Selenium浏览器已关闭")


if __name__ == "__main__":
    # 演示：驱动生命周期（SeleniumDriver）与元素操作（SeleniumBasePage）职责分离
    from page_objects.web.selenium_base_page import SeleniumBasePage

    sd = SeleniumDriver()
    driver = sd.start_driver()
    page = SeleniumBasePage(driver)
    page.goto_url("https://www.baidu.com", "百度首页")
    page.input_text(('id', 'kw'), 'selenium', '搜索框')
    page.click(('id', 'su'), '搜索按钮')
    page.wait_for_visible(('css', '#content_left'), timeout=10)
    sd.quit_driver()
