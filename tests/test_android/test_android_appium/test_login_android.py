"""Android登录测试（待实现）"""
# import pytest
# from utils.android_driver import AndroidDriver
#
# class TestAndroidLogin:
#     def setup_class(self):
#         self.driver = AndroidDriver().start_driver()
#
#     def test_login(self):
#         print("✅ 安卓APP登录用例执行成功")
#
#     def teardown_class(self):
#         AndroidDriver().quit_driver()

import pytest


@pytest.mark.android
def test_android_login_placeholder():
    """占位测试，待Android环境就绪后实现"""
    pytest.skip("Android登录测试待实现")
