import subprocess

import pyautogui
import pygetwindow as gw
import time
from utils.logger import logger
from utils.config_reader import ConfigReader  # 你的配置工具

class WindowsDriver:
    """
    Windows 桌面自动化驱动
    严格遵循：配置与逻辑分离
    读取：config/windows_config.yaml
    """
    def __init__(self):
        # 从配置文件读取 → 完全分层
        self.cfg = ConfigReader.read_yaml("config/windows_config.yaml")
        self.win_cfg = self.cfg["windows_gui"]

        # 从配置加载，不写死
        pyautogui.FAILSAFE = self.win_cfg["failsafe"]
        pyautogui.PAUSE = self.win_cfg["default_wait"]

        logger.info("✅ Windows 驱动初始化完成（配置分离版）")

    # ==================== 窗口 ====================
    def get_window(self, title):
        try:
            return gw.getWindowsWithTitle(title)[0]
        except Exception:
            return None

    def activate(self, title):
        win = self.get_window(title)
        if win:
            win.activate()
            time.sleep(0.5)
        return self

    # ==================== 鼠标 ====================
    def click(self, x, y):
        pyautogui.click(x, y)
        logger.info(f"点击 ({x}, {y})")
        return self

    def double_click(self, x, y):
        pyautogui.doubleClick(x, y)
        return self

    # ==================== 键盘 ====================
    def input(self, text):
        pyautogui.typewrite(text, interval=0.05)
        logger.info(f"输入: {text}")
        return self

    def press(self, key):
        pyautogui.press(key)
        return self

    def hotkey(self, *keys):
        pyautogui.hotkey(*keys)
        logger.info(f"快捷键: {'+'.join(keys)}")
        return self

    # ==================== 等待 ====================
    def wait(self, sec=None):
        wait_time = sec or self.win_cfg["default_wait"]
        time.sleep(wait_time)
        return self

    # 在 WindowsDriver 里加这个方法
    def start_exe(self, exe_path):
        """企业标准：通过路径启动exe"""
        subprocess.Popen(exe_path)
        logger.info(f"启动程序：{exe_path}")
        return self
