from airtest.core.api import connect_device, start_app, stop_app, sleep
from airtest.core.android import Android

class AirtestDriver:
    """Airtest 驱动 · 旧安卓（红米4）专用 · 企业规范版"""
    def __init__(self):
        self.device = connect_device("Android:///")
        self.driver: Android = self.device

    def start_app(self, package_name="com.android.settings"):
        """启动APP"""
        start_app(package_name)
        sleep(2)
        return self

    def get_current_package(self) -> str:
        """
        正确获取当前APP包名（Airtest 标准写法）
        修复：AttributeError: 'Android' object has no attribute 'get_top_package'
        """
        try:
            # Airtest 正确获取顶层APP
            return self.driver.adb.get_top_activity()[0]
        except:
            return self.driver.get_top_package()  # 兼容写法

    def quit(self):
        stop_app("com.android.settings")