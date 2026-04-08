from selenium.webdriver.common.by import By
from .base_harmony import BaseHarmonyPage

class LoginPageHarmony(BaseHarmonyPage):
    USERNAME = (By.ID, "com.example.app:id/username")
    PASSWORD = (By.ID, "com.example.app:id/password")
    LOGIN_BTN = (By.ID, "com.example.app:id/login")

    def login(self, username, password):
        self.input(self.USERNAME, username)
        self.input(self.PASSWORD, password)
        self.click(self.LOGIN_BTN)