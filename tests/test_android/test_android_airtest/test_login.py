"""Android APP 登录测试（PO模式）"""
from page_objects.android.login_page import LoginPage
from utils.tools.config_reader import ConfigReader

def test_android_login():
    data = ConfigReader().read_yaml("test_data/ui/ui_test_data.yaml")
    user = data["android"]["username"]
    pwd = data["android"]["password"]

    page = LoginPage()
    page.login(user, pwd)