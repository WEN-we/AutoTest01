"""
Windows GUI基础页面类
提供统一的Windows桌面应用操作封装
"""
import pyautogui
import pygetwindow as gw
import time
import os
from utils.tools.logger import log
from utils.tools.config_reader import ConfigReader
from utils.tools.path_manager import get_config_path, get_log_path


class BaseWindowsPage:
    """Windows GUI基础页面类"""

    def __init__(self):
        self.cfg = ConfigReader.read_yaml(get_config_path("windows_config.yaml"))
        self.win_cfg = self.cfg.get("windows_gui", {})
        self.screenshot_dir = get_log_path("screenshots")
        os.makedirs(self.screenshot_dir, exist_ok=True)
        
        pyautogui.FAILSAFE = self.win_cfg.get("failsafe", True)
        pyautogui.PAUSE = self.win_cfg.get("default_wait", 0.5)
        log.info("Windows GUI页面初始化完成")

    def get_window(self, title: str):
        """获取窗口对象"""
        try:
            windows = gw.getWindowsWithTitle(title)
            if windows:
                return windows[0]
        except Exception as e:
            log.warning(f"获取窗口失败: {title}, {e}")
        return None

    def activate_window(self, title: str):
        """激活窗口"""
        win = self.get_window(title)
        if win:
            win.activate()
            time.sleep(0.5)
            log.info(f"激活窗口: {title}")
        return self

    def maximize_window(self, title: str):
        """最大化窗口"""
        win = self.get_window(title)
        if win:
            win.maximize()
            log.info(f"最大化窗口: {title}")
        return self

    def minimize_window(self, title: str):
        """最小化窗口"""
        win = self.get_window(title)
        if win:
            win.minimize()
            log.info(f"最小化窗口: {title}")
        return self

    def close_window(self, title: str):
        """关闭窗口"""
        win = self.get_window(title)
        if win:
            win.close()
            log.info(f"关闭窗口: {title}")
        return self

    def get_window_rect(self, title: str) -> tuple:
        """获取窗口位置和大小
        
        Returns:
            (left, top, width, height)
        """
        win = self.get_window(title)
        if win:
            return (win.left, win.top, win.width, win.height)
        return None

    def click(self, x: int, y: int, description: str = ""):
        """点击坐标"""
        pyautogui.click(x, y)
        log.info(f"点击: {description or f'({x}, {y})'}")
        return self

    def double_click(self, x: int, y: int, description: str = ""):
        """双击坐标"""
        pyautogui.doubleClick(x, y)
        log.info(f"双击: {description or f'({x}, {y})'}")
        return self

    def right_click(self, x: int, y: int, description: str = ""):
        """右键点击"""
        pyautogui.rightClick(x, y)
        log.info(f"右键点击: {description or f'({x}, {y})'}")
        return self

    def click_relative(self, title: str, rel_x: int, rel_y: int, description: str = ""):
        """相对于窗口点击"""
        rect = self.get_window_rect(title)
        if rect:
            abs_x = rect[0] + rel_x
            abs_y = rect[1] + rel_y
            self.click(abs_x, abs_y, description)
        return self

    def drag_to(self, start_x: int, start_y: int, end_x: int, end_y: int, duration: float = 0.5):
        """拖拽"""
        pyautogui.moveTo(start_x, start_y)
        pyautogui.drag(end_x - start_x, end_y - start_y, duration=duration)
        log.info(f"拖拽: ({start_x},{start_y}) -> ({end_x},{end_y})")
        return self

    def input_text(self, text: str, interval: float = 0.05):
        """输入文本"""
        pyautogui.typewrite(text, interval=interval)
        log.info(f"输入文本: {text}")
        return self

    def input_chinese(self, text: str):
        """输入中文（使用剪贴板）"""
        import pyperclip
        pyperclip.copy(text)
        pyautogui.hotkey('ctrl', 'v')
        log.info(f"输入中文: {text}")
        return self

    def press(self, key: str):
        """按键"""
        pyautogui.press(key)
        log.info(f"按键: {key}")
        return self

    def hotkey(self, *keys: str):
        """快捷键"""
        pyautogui.hotkey(*keys)
        log.info(f"快捷键: {'+'.join(keys)}")
        return self

    def press_enter(self):
        """按回车"""
        return self.press('enter')

    def press_tab(self):
        """按Tab"""
        return self.press('tab')

    def press_esc(self):
        """按Esc"""
        return self.press('escape')

    def press_backspace(self):
        """按退格"""
        return self.press('backspace')

    def select_all(self):
        """全选"""
        return self.hotkey('ctrl', 'a')

    def copy(self):
        """复制"""
        return self.hotkey('ctrl', 'c')

    def paste(self):
        """粘贴"""
        return self.hotkey('ctrl', 'v')

    def cut(self):
        """剪切"""
        return self.hotkey('ctrl', 'x')

    def save(self):
        """保存"""
        return self.hotkey('ctrl', 's')

    def find(self):
        """查找"""
        return self.hotkey('ctrl', 'f')

    def wait(self, seconds: float = None):
        """等待"""
        wait_time = seconds or self.win_cfg.get("default_wait", 1.0)
        time.sleep(wait_time)
        log.info(f"等待 {wait_time} 秒")
        return self

    def wait_for_window(self, title: str, timeout: float = 10.0) -> bool:
        """等待窗口出现"""
        start_time = time.time()
        while time.time() - start_time < timeout:
            if self.get_window(title):
                log.info(f"窗口出现: {title}")
                return True
            time.sleep(0.5)
        log.warning(f"等待窗口超时: {title}")
        return False

    def wait_for_image(self, image_path: str, timeout: float = 10.0, confidence: float = 0.9) -> tuple:
        """等待图片出现
        
        Returns:
            图片中心坐标 (x, y) 或 None
        """
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                location = pyautogui.locateOnScreen(image_path, confidence=confidence)
                if location:
                    center = pyautogui.center(location)
                    log.info(f"图片出现: {image_path} at {center}")
                    return center
            except Exception:
                pass
            time.sleep(0.5)
        log.warning(f"等待图片超时: {image_path}")
        return None

    def click_image(self, image_path: str, timeout: float = 10.0, confidence: float = 0.9):
        """点击图片"""
        center = self.wait_for_image(image_path, timeout, confidence)
        if center:
            pyautogui.click(center)
            log.info(f"点击图片: {image_path}")
        else:
            raise Exception(f"未找到图片: {image_path}")
        return self

    def take_screenshot(self, name: str = None) -> str:
        """截图"""
        if name is None:
            from datetime import datetime
            name = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = os.path.join(self.screenshot_dir, f"{name}.png")
        pyautogui.screenshot(path)
        log.info(f"截图保存: {path}")
        return path

    def get_screen_size(self) -> tuple:
        """获取屏幕大小"""
        return pyautogui.size()

    def get_mouse_position(self) -> tuple:
        """获取鼠标位置"""
        return pyautogui.position()

    def move_to(self, x: int, y: int, duration: float = 0.0):
        """移动鼠标"""
        pyautogui.moveTo(x, y, duration=duration)
        log.info(f"移动鼠标到: ({x}, {y})")
        return self

    def scroll_up(self, clicks: int = 3):
        """向上滚动"""
        pyautogui.scroll(clicks)
        log.info(f"向上滚动: {clicks}")
        return self

    def scroll_down(self, clicks: int = 3):
        """向下滚动"""
        pyautogui.scroll(-clicks)
        log.info(f"向下滚动: {clicks}")
        return self

    def start_program(self, exe_path: str):
        """启动程序"""
        import subprocess
        subprocess.Popen(exe_path)
        log.info(f"启动程序: {exe_path}")
        return self

    def alert(self, title: str, message: str):
        """显示提示框"""
        pyautogui.alert(text=message, title=title)
        return self
