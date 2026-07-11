from page_objects.web.base_page import BasePage

class HomePage(BasePage):
    """首页对象"""

    # 你自己定位一个【登录后一定存在、且有固定文字】的元素
    # 比如：首页标题、用户名、欢迎语、菜单名称都行
    HOME_TITLE = ".card-title"       # 你自己改成真实定位符
    MY_DESKTOP = "text='欢迎使用测试平台'"

    def __init__(self, page):
        super().__init__(page)

    def get_home_text(self):
        """获取首页固定文字，用来断言登录成功"""
        return self.get_text(self.HOME_TITLE, "导航栏标签").strip()

    def get_desktop_text(self):
        """获取"我的桌面"文字，用于断言登录成功"""
        text = self.page.text_content(self.MY_DESKTOP)
        return text.strip() if text else ""