import os
import time
import pyautogui
from utils.tools.config_reader import ConfigReader
from utils.tools.logger import logger

class LinuxDriver:
    def __init__(self):
        self.cfg = ConfigReader().read_yaml("config/linux_config.yaml")["linux_gui"]
        self.screenshot_dir = self.cfg["screenshot_dir"]
        os.makedirs(self.screenshot_dir, exist_ok=True)
        pyautogui.FAILSAFE = True
        pyautogui.PAUSE = 0.5
        logger.info("✅ Linux GUI 驱动初始化完成")

    def click(self, x, y):
        pyautogui.click(x, y)
        logger.info(f"点击坐标 ({x}, {y})")

    def input_text(self, text):
        pyautogui.typewrite(text)
        logger.info(f"输入内容: {text}")
        return self

    # 兼容 tests 中的统一调用风格（和 WindowsDriver 对齐）
    def input(self, text):
        return self.input_text(text)

    def press(self, key):
        pyautogui.press(key)
        return self

    def hotkey(self, *keys):
        pyautogui.hotkey(*keys)
        logger.info(f"快捷键: {'+'.join(keys)}")
        return self

    def wait(self, sec=1.0):
        time.sleep(sec)
        return self

    def take_screenshot(self, name):
        path = os.path.join(self.screenshot_dir, f"{name}.png")
        pyautogui.screenshot(path)
        logger.info(f"截图已保存: {path}")
        return path