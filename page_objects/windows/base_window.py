from page_objects.base.base_page import BasePage
import pyautogui
import os

class BaseWindow(BasePage):
    def __init__(self):
        self.driver = pyautogui
        super().__init__(self.driver)
        pyautogui.PAUSE = 0.5
        pyautogui.FAILSAFE = True

    def click(self, x, y):
        self.driver.click(x, y)

    def input(self, text):
        self.driver.typewrite(text)

    def screenshot(self, name):
        path = f"./logs/screenshots/{name}.png"
        os.makedirs(os.path.dirname(path), exist_ok=True)
        self.driver.screenshot(path)