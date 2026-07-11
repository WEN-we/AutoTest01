"""
Android Appium基础页面类
提供统一的App移动端操作封装
"""
from appium.webdriver.common.appiumby import AppiumBy
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from utils.tools.logger import log
import time


class BaseAndroidPage:
    """Android Appium基础页面类"""

    def __init__(self, driver):
        self.driver = driver
        self.timeout = 10

    def find_element(self, locator: tuple, timeout: int = None):
        """查找单个元素
        
        Args:
            locator: 定位器元组，支持以下格式:
                ('id', 'element_id')
                ('xpath', '//xpath')
                ('class', 'class_name')
                ('accessibility_id', 'accessibility_id')
                ('android_uiautomator', 'uiautomator_code')
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
            return WebDriverWait(self.driver, timeout).until(
                EC.presence_of_all_elements_located(locator)
            )
        except TimeoutException:
            return []

    def _normalize_locator(self, locator: tuple) -> tuple:
        """标准化定位器"""
        by, value = locator
        if isinstance(by, str):
            by_map = {
                'id': AppiumBy.ID,
                'xpath': AppiumBy.XPATH,
                'class': AppiumBy.CLASS_NAME,
                'class_name': AppiumBy.CLASS_NAME,
                'accessibility_id': AppiumBy.ACCESSIBILITY_ID,
                'android_uiautomator': AppiumBy.ANDROID_UIAUTOMATOR,
                'css': AppiumBy.CSS_SELECTOR,
            }
            by = by_map.get(by.lower(), by)
        return (by, value)

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

    def click_by_coordinates(self, x: int, y: int):
        """通过坐标点击"""
        self.driver.tap([(x, y)])
        log.info(f"点击坐标: ({x}, {y})")

    def input_text(self, locator: tuple, text: str, description: str = "", 
                   clear: bool = True, timeout: int = None):
        """输入文本"""
        element = self.find_element(locator, timeout)
        if clear:
            element.clear()
        element.send_keys(text)
        log.info(f"输入文本: {description or locator} <- '{text}'")

    def input_text_by_ime(self, text: str):
        """通过IME输入法输入文本（解决中文输入问题）"""
        self.driver.set_value(text)
        log.info(f"IME输入文本: {text}")

    def get_text(self, locator: tuple, description: str = "", timeout: int = None) -> str:
        """获取元素文本"""
        element = self.find_element(locator, timeout)
        text = element.text
        log.info(f"获取文本: {description or locator} -> '{text}'")
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

    def is_enabled(self, locator: tuple, timeout: int = None) -> bool:
        """判断元素是否可用"""
        element = self.find_element(locator, timeout)
        return element.is_enabled()

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

    def swipe(self, start_x: int, start_y: int, end_x: int, end_y: int, duration: int = 500):
        """滑动屏幕"""
        self.driver.swipe(start_x, start_y, end_x, end_y, duration)
        log.info(f"滑动: ({start_x},{start_y}) -> ({end_x},{end_y})")

    def swipe_up(self, duration: int = 500):
        """向上滑动"""
        size = self.driver.get_window_size()
        x = size['width'] // 2
        start_y = size['height'] * 0.8
        end_y = size['height'] * 0.2
        self.swipe(x, start_y, x, end_y, duration)
        log.info("向上滑动")

    def swipe_down(self, duration: int = 500):
        """向下滑动"""
        size = self.driver.get_window_size()
        x = size['width'] // 2
        start_y = size['height'] * 0.2
        end_y = size['height'] * 0.8
        self.swipe(x, start_y, x, end_y, duration)
        log.info("向下滑动")

    def swipe_left(self, duration: int = 500):
        """向左滑动"""
        size = self.driver.get_window_size()
        start_x = size['width'] * 0.8
        end_x = size['width'] * 0.2
        y = size['height'] // 2
        self.swipe(start_x, y, end_x, y, duration)
        log.info("向左滑动")

    def swipe_right(self, duration: int = 500):
        """向右滑动"""
        size = self.driver.get_window_size()
        start_x = size['width'] * 0.2
        end_x = size['width'] * 0.8
        y = size['height'] // 2
        self.swipe(start_x, y, end_x, y, duration)
        log.info("向右滑动")

    def scroll_to_element(self, locator: tuple, max_swipes: int = 10):
        """滚动到元素"""
        for _ in range(max_swipes):
            if self.is_displayed(locator, timeout=1):
                return True
            self.swipe_up()
        return False

    def long_press(self, locator: tuple, duration: int = 1000, timeout: int = None):
        """长按元素"""
        from appium.webdriver.common.touch_action import TouchAction
        element = self.find_element(locator, timeout)
        TouchAction(self.driver).long_press(element, duration=duration).release().perform()
        log.info(f"长按元素: {locator}")

    def pinch(self, locator: tuple, direction: str = 'in', percent: int = 200, step: int = 50):
        """捏合手势
        
        Args:
            locator: 元素定位器
            direction: 'in'缩小, 'out'放大
        """
        from appium.webdriver.common.touch_action import TouchAction
        element = self.find_element(locator)
        action = TouchAction(self.driver)
        if direction == 'in':
            action.pinch(element, percent, step)
        else:
            action.zoom(element, percent, step)
        action.perform()
        log.info(f"捏合手势: {direction}")

    def hide_keyboard(self):
        """隐藏键盘"""
        try:
            self.driver.hide_keyboard()
            log.info("隐藏键盘")
        except Exception:
            pass

    def press_back(self):
        """按返回键"""
        self.driver.press_keycode(4)
        log.info("按返回键")

    def press_home(self):
        """按Home键"""
        self.driver.press_keycode(3)
        log.info("按Home键")

    def press_enter(self):
        """按回车键"""
        self.driver.press_keycode(66)
        log.info("按回车键")

    def take_screenshot(self, filename: str):
        """截图"""
        self.driver.save_screenshot(filename)
        log.info(f"截图保存: {filename}")

    def get_screenshot_as_base64(self) -> str:
        """获取截图Base64"""
        return self.driver.get_screenshot_as_base64()

    def get_current_activity(self) -> str:
        """获取当前Activity"""
        return self.driver.current_activity

    def get_current_package(self) -> str:
        """获取当前包名"""
        return self.driver.current_package

    def start_activity(self, package: str, activity: str):
        """启动Activity"""
        self.driver.start_activity(package, activity)
        log.info(f"启动Activity: {package}/{activity}")

    def install_app(self, app_path: str):
        """安装应用"""
        self.driver.install_app(app_path)
        log.info(f"安装应用: {app_path}")

    def remove_app(self, package: str):
        """卸载应用"""
        self.driver.remove_app(package)
        log.info(f"卸载应用: {package}")

    def is_app_installed(self, package: str) -> bool:
        """检查应用是否已安装"""
        return self.driver.is_app_installed(package)

    def launch_app(self):
        """启动应用"""
        self.driver.launch_app()
        log.info("启动应用")

    def close_app(self):
        """关闭应用"""
        self.driver.close_app()
        log.info("关闭应用")

    def reset_app(self):
        """重置应用（清除数据）"""
        self.driver.reset()
        log.info("重置应用")

    def wait(self, seconds: float):
        """强制等待"""
        time.sleep(seconds)
        log.info(f"等待 {seconds} 秒")
