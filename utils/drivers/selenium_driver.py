"""
Selenium Web驱动封装
支持Chrome、Firefox、Edge浏览器
配置与代码分离，从ui_config.yaml读取配置
"""
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.firefox.service import Service as FirefoxService
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from selenium.webdriver.edge.service import Service as EdgeService
from selenium.webdriver.edge.options import Options as EdgeOptions
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from utils.tools.config_reader import ConfigReader
from utils.tools.logger import log
from utils.tools.path_manager import get_config_path
import os


class SeleniumDriver:
    """Selenium Web驱动封装类"""

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

    def get(self, url: str):
        """访问URL"""
        log.info(f"访问URL: {url}")
        self.driver.get(url)

    def find_element(self, locator: tuple, timeout: int = None):
        """查找单个元素
        
        Args:
            locator: 定位器元组，如 (By.ID, 'username') 或 ('id', 'username')
            timeout: 超时时间
        """
        timeout = timeout or self.timeout
        locator = self._normalize_locator(locator)
        try:
            element = WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located(locator)
            )
            return element
        except TimeoutException:
            log.error(f"元素定位超时: {locator}")
            raise

    def find_elements(self, locator: tuple, timeout: int = None):
        """查找多个元素"""
        timeout = timeout or self.timeout
        locator = self._normalize_locator(locator)
        try:
            elements = WebDriverWait(self.driver, timeout).until(
                EC.presence_of_all_elements_located(locator)
            )
            return elements
        except TimeoutException:
            log.warning(f"元素定位超时(返回空列表): {locator}")
            return []

    def _normalize_locator(self, locator: tuple) -> tuple:
        """标准化定位器"""
        by, value = locator
        if isinstance(by, str):
            by_map = {
                'id': By.ID,
                'name': By.NAME,
                'class': By.CLASS_NAME,
                'class_name': By.CLASS_NAME,
                'tag': By.TAG_NAME,
                'tag_name': By.TAG_NAME,
                'link': By.LINK_TEXT,
                'link_text': By.LINK_TEXT,
                'partial_link': By.PARTIAL_LINK_TEXT,
                'partial_link_text': By.PARTIAL_LINK_TEXT,
                'css': By.CSS_SELECTOR,
                'css_selector': By.CSS_SELECTOR,
                'xpath': By.XPATH,
            }
            by = by_map.get(by.lower(), by)
        return (by, value)

    def click(self, locator: tuple, timeout: int = None):
        """点击元素"""
        timeout = timeout or self.timeout
        locator = self._normalize_locator(locator)
        try:
            element = WebDriverWait(self.driver, timeout).until(
                EC.element_to_be_clickable(locator)
            )
            element.click()
            log.info(f"点击元素: {locator}")
        except TimeoutException:
            log.error(f"元素不可点击: {locator}")
            raise

    def input_text(self, locator: tuple, text: str, clear: bool = True, timeout: int = None):
        """输入文本"""
        element = self.find_element(locator, timeout)
        if clear:
            element.clear()
        element.send_keys(text)
        log.info(f"输入文本: {locator} <- '{text}'")

    def get_text(self, locator: tuple, timeout: int = None) -> str:
        """获取元素文本"""
        element = self.find_element(locator, timeout)
        text = element.text
        log.info(f"获取文本: {locator} -> '{text}'")
        return text

    def get_attribute(self, locator: tuple, attribute: str, timeout: int = None) -> str:
        """获取元素属性"""
        element = self.find_element(locator, timeout)
        return element.get_attribute(attribute)

    def is_displayed(self, locator: tuple, timeout: int = None) -> bool:
        """判断元素是否可见"""
        timeout = timeout or self.timeout
        locator = self._normalize_locator(locator)
        try:
            element = WebDriverWait(self.driver, timeout).until(
                EC.visibility_of_element_located(locator)
            )
            return element.is_displayed()
        except TimeoutException:
            return False

    def wait_for_element(self, locator: tuple, timeout: int = None):
        """等待元素可见"""
        timeout = timeout or self.timeout
        locator = self._normalize_locator(locator)
        WebDriverWait(self.driver, timeout).until(
            EC.visibility_of_element_located(locator)
        )
        log.info(f"元素可见: {locator}")

    def wait_for_element_clickable(self, locator: tuple, timeout: int = None):
        """等待元素可点击"""
        timeout = timeout or self.timeout
        locator = self._normalize_locator(locator)
        WebDriverWait(self.driver, timeout).until(
            EC.element_to_be_clickable(locator)
        )
        log.info(f"元素可点击: {locator}")

    def switch_to_frame(self, locator: tuple = None, index: int = None, name: str = None):
        """切换到iframe"""
        if locator:
            frame = self.find_element(locator)
            self.driver.switch_to.frame(frame)
        elif index is not None:
            self.driver.switch_to.frame(index)
        elif name:
            self.driver.switch_to.frame(name)
        log.info(f"切换到iframe: {locator or index or name}")

    def switch_to_default_content(self):
        """切换回主文档"""
        self.driver.switch_to.default_content()
        log.info("切换回主文档")

    def execute_script(self, script: str, *args):
        """执行JavaScript脚本"""
        return self.driver.execute_script(script, *args)

    def take_screenshot(self, filename: str):
        """截图"""
        self.driver.save_screenshot(filename)
        log.info(f"截图保存: {filename}")

    def get_current_url(self) -> str:
        """获取当前URL"""
        return self.driver.current_url

    def get_title(self) -> str:
        """获取页面标题"""
        return self.driver.title

    def refresh(self):
        """刷新页面"""
        self.driver.refresh()
        log.info("页面已刷新")

    def back(self):
        """后退"""
        self.driver.back()
        log.info("页面后退")

    def forward(self):
        """前进"""
        self.driver.forward()
        log.info("页面前进")

    def add_cookie(self, name: str, value: str, domain: str = None, path: str = '/'):
        """添加Cookie"""
        cookie = {'name': name, 'value': value, 'path': path}
        if domain:
            cookie['domain'] = domain
        self.driver.add_cookie(cookie)
        log.info(f"添加Cookie: {name}={value}")

    def get_cookies(self) -> list:
        """获取所有Cookie"""
        return self.driver.get_cookies()

    def delete_all_cookies(self):
        """删除所有Cookie"""
        self.driver.delete_all_cookies()
        log.info("已删除所有Cookie")


if __name__ == "__main__":
    driver = SeleniumDriver()
    d = driver.start_driver()
    d.get("https://www.baidu.com")
    driver.input_text(('id', 'kw'), 'selenium')
    driver.click(('id', 'su'))
    import time
    time.sleep(2)
    driver.quit_driver()
