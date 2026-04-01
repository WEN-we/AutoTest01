from page_objects.base_page import BasePage


class HomePage(BasePage):
    """首页对象"""

    # 元素定位符
    #USER_AVATAR = "[name='sidebar-logo']"
    GOODS_LIST = "[name='sidebar-logo']"

    def __init__(self, page):
        super().__init__(page)

    def is_login_success(self):
        """判断登录成功：URL包含dashboard即可"""
        return "dashboard" in self.page.url

    def goto_goods_list(self):
        """进入商品列表"""
        self.click(self.GOODS_LIST, "商品列表")
