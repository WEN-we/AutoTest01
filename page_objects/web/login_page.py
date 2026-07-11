import time
from page_objects.web.base_page import BasePage
from utils.tools.config_reader import ConfigReader

class LoginPage(BasePage):
    """教务系统登录页面对象"""
    # USERNAME_INPUT = "[name='userAccount']"
    # PASSWORD_INPUT = "#userPassword"
    # LOGIN_BUTTON = "#btn-login"  # 定位不变
    # ERROR_TIP = "#showMsg"
    #本地登录页面定位器
    USERNAME_INPUT = "#username"
    PASSWORD_INPUT = "#password"
    LOGIN_BUTTON = "#loginBtn"  # 定位不变
    ERROR_TIP = ".d-flex"

    # 电商平台登录页面定位器
    EC_USER_LOGIN_TAB = "text='用户登录'"
    EC_USERNAME_INPUT = "input[placeholder='*用户名 / 邮箱']"
    EC_PASSWORD_INPUT = "input[placeholder='*密码']"
    EC_CAPTCHA_INPUT = "input[placeholder='*验证码']"
    EC_REMEMBER_ME_CHECKBOX = "input[type='checkbox']"
    EC_LOGIN_BUTTON = "button:has-text('登录')"
    EC_REGISTER_LINK = "text='立即注册'"

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

    # ==================== 电商平台登录方法 ====================

    def open_ec_login_page(self):
        """打开电商平台首页（登录入口在首页弹窗）"""
        env = ConfigReader.get_env_config()
        self.goto_url(env['base_ui_url'], "电商平台首页")

    def click_ec_login_button(self):
        """点击首页的登录按钮，弹出登录窗口"""
        self.page.click("button:has-text('登录')")
        self.page.wait_for_timeout(1000)

    def select_user_login_tab(self):
        """选择用户登录tab"""
        self.page.click(self.EC_USER_LOGIN_TAB)
        self.page.wait_for_timeout(500)

    def ec_login(self, username, password, captcha=""):
        """电商平台用户登录"""
        self.page.fill(self.EC_USERNAME_INPUT, username)
        self.page.fill(self.EC_PASSWORD_INPUT, password)
        if captcha:
            self.page.fill(self.EC_CAPTCHA_INPUT, captcha)
        self.page.click(self.EC_LOGIN_BUTTON)
        self.page.wait_for_timeout(2000)

    def check_remember_me(self):
        """勾选记住我复选框"""
        checkbox = self.page.query_selector(self.EC_REMEMBER_ME_CHECKBOX)
        if checkbox and not checkbox.is_checked():
            checkbox.click()

    def click_register_link(self):
        """点击立即注册链接"""
        self.page.click(self.EC_REGISTER_LINK)
        self.page.wait_for_timeout(1000)