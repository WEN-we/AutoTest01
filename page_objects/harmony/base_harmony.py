from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

class BaseHarmonyPage:
    def __init__(self, driver):
        self.driver = driver

    def find_element(self, locator, timeout=10):
        return WebDriverWait(self.driver, timeout).until(
            EC.presence_of_element_located(locator)
        )

    def click(self, locator):
        self.find_element(locator).click()

    def input(self, locator, text):
        el = self.find_element(locator)
        el.clear()
        el.send_keys(text)