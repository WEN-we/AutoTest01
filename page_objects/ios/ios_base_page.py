"""
iOS Appium基础页面类
提供统一的iOS移动端操作封装
"""
from appium.webdriver.common.appiumby import AppiumBy
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from utils.tools.logger import log
import time


class BaseIosPage:
    """iOS Appium基础页面类"""

    def __init__(self, driver):
        self.driver = driver
        self.timeout = 10

    def find_element(self, locator: tuple, timeout: int = None):
        """查找单个元素
        
        Args:
            locator: 定位器元组，支持以下格式:
                ('id', 'element_id')  # iOS使用accessibility identifier
                ('xpath', '//xpath')
                ('class', 'class_name')
                ('accessibility_id', 'accessibility_id')
                ('ios_predicate', 'predicate_string')
                ('ios_class_chain', 'class_chain')
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
                'ios_predicate': AppiumBy.IOS_PREDICATE,
                'ios_class_chain': AppiumBy.IOS_CLASS_CHAIN,
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

    def wait_for_visible(self, locator: tuple, timeout: int = None):
        """等待元素可见"""
        timeout = timeout or self.timeout
        locator = self._normalize_locator(locator)
        WebDriverWait(self.driver, timeout).until(
            EC.visibility_of_element_located(locator)
        )
        log.info(f"元素可见: {locator}")

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

    def mobile_swipe(self, direction: str = 'up', distance: float = 1.0):
        """iOS专用滑动方法
        
        Args:
            direction: 'up', 'down', 'left', 'right'
            distance: 滑动距离比例 0-1
        """
        self.driver.execute_script('mobile: swipe', {
            'direction': direction,
            'distance': distance
        })
        log.info(f"iOS滑动: {direction}")

    def mobile_scroll(self, direction: str = 'down', element: str = None):
        """iOS专用滚动方法"""
        params = {'direction': direction}
        if element:
            params['element'] = element
        self.driver.execute_script('mobile: scroll', params)
        log.info(f"iOS滚动: {direction}")

    def mobile_tap(self, x: int, y: int):
        """iOS专用点击方法"""
        self.driver.execute_script('mobile: tap', {'x': x, 'y': y})
        log.info(f"iOS点击: ({x}, {y})")

    def mobile_double_tap(self, x: int, y: int):
        """iOS双击"""
        self.driver.execute_script('mobile: doubleTap', {'x': x, 'y': y})
        log.info(f"iOS双击: ({x}, {y})")

    def mobile_long_press(self, x: int, y: int, duration: float = 1.0):
        """iOS长按"""
        self.driver.execute_script('mobile: touchAndHold', {
            'x': x, 'y': y, 'duration': duration
        })
        log.info(f"iOS长按: ({x}, {y})")

    def mobile_drag(self, from_x: int, from_y: int, to_x: int, to_y: int, duration: float = 1.0):
        """iOS拖拽"""
        self.driver.execute_script('mobile: dragFromToWithDuration', {
            'fromX': from_x, 'fromY': from_y,
            'toX': to_x, 'toY': to_y,
            'duration': duration
        })
        log.info(f"iOS拖拽: ({from_x},{from_y}) -> ({to_x},{to_y})")

    def mobile_pinch(self, scale: float = 0.5, velocity: float = -1.0):
        """iOS捏合手势
        
        Args:
            scale: 缩放比例，<1缩小，>1放大
        """
        self.driver.execute_script('mobile: pinch', {
            'scale': scale, 'velocity': velocity
        })
        log.info(f"iOS捏合: scale={scale}")

    def hide_keyboard(self):
        """隐藏键盘"""
        try:
            self.driver.hide_keyboard()
            log.info("隐藏键盘")
        except Exception:
            pass

    def press_home(self):
        """按Home键"""
        self.driver.execute_script('mobile: pressButton', {'name': 'home'})
        log.info("按Home键")

    def take_screenshot(self, filename: str):
        """截图"""
        self.driver.save_screenshot(filename)
        log.info(f"截图保存: {filename}")

    def get_current_activity(self) -> str:
        """获取当前Activity"""
        return self.driver.current_activity

    def launch_app(self):
        """启动应用"""
        self.driver.launch_app()
        log.info("启动应用")

    def close_app(self):
        """关闭应用"""
        self.driver.close_app()
        log.info("关闭应用")

    def wait(self, seconds: float):
        """强制等待"""
        time.sleep(seconds)
        log.info(f"等待 {seconds} 秒")
