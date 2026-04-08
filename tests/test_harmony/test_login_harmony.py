import pytest
from utils.harmony_driver import HarmonyDriver
from page_objects.harmony.login_page import LoginPageHarmony

class TestHarmonyLogin:
    def setup_class(self):
        self.driver = HarmonyDriver.get_driver()
        self.login_page = LoginPageHarmony(self.driver)

    def test_login(self):
        self.login_page.login("test_user", "123456")

    def teardown_class(self):
        self.driver.quit()