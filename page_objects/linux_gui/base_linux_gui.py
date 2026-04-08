from page_objects.base.base_page import BasePage
import pyautogui
import os

class BaseLinuxGUI(BasePage):
    def __init__(self):
        self.driver = pyautogui
        super().__init__(self.driver)
        pyautogui.PAUSE = 0.5

    def click(self, x, y):
        self.driver.click(x, y)

    def input(self, txt):
        self.driver.typewrite(txt)

    def screenshot(self, name):
        path = "./logs/linux_screenshots"
        os.makedirs(path, exist_ok=True)
        self.driver.screenshot(f"{path}/{name}.png")