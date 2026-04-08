from page_objects.base.base_page import BasePage
from airtest.core.api import *

class BaseAndroid(BasePage):
    def __init__(self):
        self.driver = device()
        super().__init__(self.driver)

    def click(self, img):
        touch(img)

    def input(self, text):
        text(text)

    def exists(self, img):
        return exists(img)