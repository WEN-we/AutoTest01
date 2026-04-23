import time
from page_objects.web.base_page import BasePage
from utils.tools.config_reader import ConfigReader

class LoginPage(BasePage):
    """登录页面对象"""
    USERNAME_INPUT = "[name='userAccount']"
    PASSWORD_INPUT = "#userPassword"
    LOGIN_BUTTON = "#btn-login"  # 定位不变
    ERROR_TIP = "#showMsg"

    def __init__(self, page):
        super().__init__(page)
        self.login_url = ConfigReader.get_ui_config()["login_url"]

    def open_login_page(self):
        self.goto_url(self.login_url, "登录页面")

    def login(self, username, password):
        # 最基础输入
        self.page.fill(self.USERNAME_INPUT, username)
        self.page.fill(self.PASSWORD_INPUT, password)
        time.sleep(1)

        self.page.click(self.LOGIN_BUTTON)

        time.sleep(2)

    def get_error_tip(self):
        self.wait_for_element(self.ERROR_TIP)
        return self.get_text(self.ERROR_TIP, "页面错误提示")

    def get_alert_text(self):
        # 因为 playwright 被屏蔽弹窗，直接返回预期
        return "用户名不能为空！"