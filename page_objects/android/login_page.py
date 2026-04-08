from page_objects.android.base_android import BaseAndroid
from airtest.core.api import Template

class LoginPage(BaseAndroid):
    def __init__(self):
        super().__init__()
        self.username = Template(r"images/android/username.png")
        self.password = Template(r"images/android/password.png")
        self.login_btn = Template(r"images/android/login.png")

    def login(self, user, pwd):
        self.click(self.username)
        self.input(user)
        self.click(self.password)
        self.input(pwd)
        self.click(self.login_btn)