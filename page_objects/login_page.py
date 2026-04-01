from page_objects.base_page import BasePage
from utils.config_reader import ConfigReader


class LoginPage(BasePage):
    """登录页面对象"""

    # 元素定位符（统一管理，改定位只需改这里）
    USERNAME_INPUT = "[name='userName']"
    PASSWORD_INPUT = "[name='password']"
    LOGIN_BUTTON = ".el-button.el-button--primary.el-button--large"
    ERROR_TIP = ".el-form-item__error"

    def __init__(self, page):
        super().__init__(page)
        self.login_url = ConfigReader.get_ui_config()["login_url"]

    def open_login_page(self):
        """打开登录页面"""
        self.goto_url(self.login_url, "登录页面")

    def login(self, username, password):
        """执行登录操作"""
        self.input_text(self.USERNAME_INPUT, username, "用户名")
        self.input_text(self.PASSWORD_INPUT, password, "密码")
        self.click(self.LOGIN_BUTTON, "登录按钮")

    def get_error_tip(self):
        """获取错误提示"""
        self.wait_for_element(self.ERROR_TIP)
        return self.get_text(self.ERROR_TIP, "登录错误提示")
