from page_objects.web.base_page import BasePage

class UserPage(BasePage):
    """用户中心页面对象"""
    USER_PROFILE = ".user-profile"
    USERNAME_DISPLAY = ".username"
    USER_EMAIL = ".user-email"
    USER_AVATAR = ".user-avatar"
    EDIT_PROFILE_BUTTON = "button:has-text('编辑资料')"
    MY_ORDERS_LINK = "text='我的订单'"
    MY_CART_LINK = "text='购物车'"
    MY_ADDRESS_LINK = "text='收货地址'"
    LOGOUT_BUTTON = "button:has-text('退出登录')"

    def __init__(self, page):
        super().__init__(page)

    def open_user_center(self):
        from utils.tools.config_reader import ConfigReader
        env = ConfigReader.get_env_config()
        self.goto_url(f"{env['base_ui_url']}/user", "用户中心")

    def get_username(self):
        element = self.page.query_selector(self.USERNAME_DISPLAY)
        return element.inner_text() if element else ""

    def get_email(self):
        element = self.page.query_selector(self.USER_EMAIL)
        return element.inner_text() if element else ""

    def go_to_my_orders(self):
        self.page.click(self.MY_ORDERS_LINK)
        self.page.wait_for_load_state("networkidle")

    def go_to_my_cart(self):
        self.page.click(self.MY_CART_LINK)
        self.page.wait_for_load_state("networkidle")

    def go_to_my_address(self):
        self.page.click(self.MY_ADDRESS_LINK)
        self.page.wait_for_load_state("networkidle")

    def edit_profile(self):
        self.page.click(self.EDIT_PROFILE_BUTTON)
        self.page.wait_for_timeout(1000)

    def logout(self):
        self.page.click(self.LOGOUT_BUTTON)
        self.page.wait_for_load_state("networkidle")
