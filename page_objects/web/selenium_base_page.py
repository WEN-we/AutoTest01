"""
Selenium Web测试基础页面类
提供统一的页面操作封装
"""
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from utils.tools.logger import log
import time


class SeleniumBasePage:
    """Selenium基础页面类"""

    def __init__(self, driver):
        self.driver = driver
        self.timeout = 10

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

    def find_element(self, locator: tuple, timeout: int = None):
        """查找单个元素"""
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
            return WebDriverWait(self.driver, timeout).until(
                EC.presence_of_all_elements_located(locator)
            )
        except TimeoutException:
            return []

    def click(self, locator: tuple, description: str = "", timeout: int = None):
        """点击元素"""
        timeout = timeout or self.timeout
        locator = self._normalize_locator(locator)
        try:
            element = WebDriverWait(self.driver, timeout).until(
                EC.element_to_be_clickable(locator)
            )
            element.click()
            log.info(f"点击元素: {description or locator}")
        except TimeoutException:
            log.error(f"元素不可点击: {locator}")
            raise

    def double_click(self, locator: tuple, description: str = "", timeout: int = None):
        """双击元素"""
        element = self.find_element(locator, timeout)
        ActionChains(self.driver).double_click(element).perform()
        log.info(f"双击元素: {description or locator}")

    def right_click(self, locator: tuple, description: str = "", timeout: int = None):
        """右键点击元素"""
        element = self.find_element(locator, timeout)
        ActionChains(self.driver).context_click(element).perform()
        log.info(f"右键点击元素: {description or locator}")

    def hover(self, locator: tuple, description: str = "", timeout: int = None):
        """鼠标悬停"""
        element = self.find_element(locator, timeout)
        ActionChains(self.driver).move_to_element(element).perform()
        log.info(f"鼠标悬停: {description or locator}")

    def input_text(self, locator: tuple, text: str, description: str = "", 
                   clear: bool = True, timeout: int = None):
        """输入文本"""
        element = self.find_element(locator, timeout)
        if clear:
            element.clear()
        element.send_keys(text)
        log.info(f"输入文本: {description or locator} <- '{text}'")

    def input_and_enter(self, locator: tuple, text: str, description: str = "", 
                        clear: bool = True, timeout: int = None):
        """输入文本并按回车"""
        element = self.find_element(locator, timeout)
        if clear:
            element.clear()
        element.send_keys(text)
        element.send_keys(Keys.ENTER)
        log.info(f"输入文本并回车: {description or locator} <- '{text}'")

    def get_text(self, locator: tuple, description: str = "", timeout: int = None) -> str:
        """获取元素文本"""
        element = self.find_element(locator, timeout)
        text = element.text
        log.info(f"获取文本: {description or locator} -> '{text}'")
        return text

    def get_value(self, locator: tuple, timeout: int = None) -> str:
        """获取输入框的值"""
        element = self.find_element(locator, timeout)
        return element.get_attribute('value')

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

    def is_enabled(self, locator: tuple, timeout: int = None) -> bool:
        """判断元素是否可用"""
        element = self.find_element(locator, timeout)
        return element.is_enabled()

    def is_selected(self, locator: tuple, timeout: int = None) -> bool:
        """判断元素是否被选中"""
        element = self.find_element(locator, timeout)
        return element.is_selected()

    def wait_for_visible(self, locator: tuple, timeout: int = None):
        """等待元素可见"""
        timeout = timeout or self.timeout
        locator = self._normalize_locator(locator)
        WebDriverWait(self.driver, timeout).until(
            EC.visibility_of_element_located(locator)
        )
        log.info(f"元素可见: {locator}")

    def wait_for_clickable(self, locator: tuple, timeout: int = None):
        """等待元素可点击"""
        timeout = timeout or self.timeout
        locator = self._normalize_locator(locator)
        WebDriverWait(self.driver, timeout).until(
            EC.element_to_be_clickable(locator)
        )
        log.info(f"元素可点击: {locator}")

    def wait_for_invisible(self, locator: tuple, timeout: int = None):
        """等待元素不可见"""
        timeout = timeout or self.timeout
        locator = self._normalize_locator(locator)
        WebDriverWait(self.driver, timeout).until(
            EC.invisibility_of_element_located(locator)
        )
        log.info(f"元素已不可见: {locator}")

    def wait_for_text(self, locator: tuple, text: str, timeout: int = None):
        """等待元素文本等于指定值"""
        timeout = timeout or self.timeout
        locator = self._normalize_locator(locator)
        WebDriverWait(self.driver, timeout).until(
            EC.text_to_be_present_in_element(locator, text)
        )
        log.info(f"元素文本等于: {text}")

    def select_by_value(self, locator: tuple, value: str, timeout: int = None):
        """通过value选择下拉框选项"""
        from selenium.webdriver.support.ui import Select
        element = self.find_element(locator, timeout)
        Select(element).select_by_value(value)
        log.info(f"选择下拉框选项: {value}")

    def select_by_text(self, locator: tuple, text: str, timeout: int = None):
        """通过可见文本选择下拉框选项"""
        from selenium.webdriver.support.ui import Select
        element = self.find_element(locator, timeout)
        Select(element).select_by_visible_text(text)
        log.info(f"选择下拉框选项: {text}")

    def select_by_index(self, locator: tuple, index: int, timeout: int = None):
        """通过索引选择下拉框选项"""
        from selenium.webdriver.support.ui import Select
        element = self.find_element(locator, timeout)
        Select(element).select_by_index(index)
        log.info(f"选择下拉框选项索引: {index}")

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

    def switch_to_default(self):
        """切换回主文档"""
        self.driver.switch_to.default_content()
        log.info("切换回主文档")

    def switch_to_alert(self, action: str = 'accept', text: str = None):
        """处理弹窗
        
        Args:
            action: 'accept'(确认), 'dismiss'(取消), 'send_keys'(输入)
            text: 当action='send_keys'时输入的文本
        """
        alert = WebDriverWait(self.driver, self.timeout).until(EC.alert_is_present())
        if action == 'accept':
            alert.accept()
            log.info("确认弹窗")
        elif action == 'dismiss':
            alert.dismiss()
            log.info("取消弹窗")
        elif action == 'send_keys' and text:
            alert.send_keys(text)
            alert.accept()
            log.info(f"弹窗输入文本: {text}")

    def execute_script(self, script: str, *args):
        """执行JavaScript脚本"""
        return self.driver.execute_script(script, *args)

    def scroll_to_element(self, locator: tuple, timeout: int = None):
        """滚动到元素位置"""
        element = self.find_element(locator, timeout)
        self.driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth'});", element)
        log.info(f"滚动到元素: {locator}")

    def scroll_to_top(self):
        """滚动到页面顶部"""
        self.driver.execute_script("window.scrollTo(0, 0);")
        log.info("滚动到页面顶部")

    def scroll_to_bottom(self):
        """滚动到页面底部"""
        self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        log.info("滚动到页面底部")

    def take_screenshot(self, filename: str):
        """截图"""
        self.driver.save_screenshot(filename)
        log.info(f"截图保存: {filename}")

    def goto_url(self, url: str, description: str = ""):
        """访问URL"""
        log.info(f"访问URL: {description or url}")
        self.driver.get(url)

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

    def wait(self, seconds: float):
        """强制等待"""
        time.sleep(seconds)
        log.info(f"等待 {seconds} 秒")
