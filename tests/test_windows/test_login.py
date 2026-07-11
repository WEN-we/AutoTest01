"""Windows 桌面登录测试（PO模式）"""
from page_objects.windows.login_window import LoginWindow
from utils.tools.config_reader import ConfigReader

def test_windows_login():
    # 读取测试数据（YAML）
    data = ConfigReader().read_yaml("test_data/ui/ui_test_data.yaml")
    user = data["windows"]["username"]
    pwd = data["windows"]["password"]

    # PO 调用
    login = LoginWindow()
    login.login(user, pwd)