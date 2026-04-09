import time
from time import sleep

import pytest
from page_objects.web.login_page import LoginPage
from page_objects.web.home_page import HomePage
from utils.config_reader import ConfigReader
from utils.logger import log

# 读取UI测试数据
test_data = ConfigReader.read_yaml("test_data/ui_test_data.yaml")["login_web"]


class TestUserUI:
    """用户模块UI用例"""

    @pytest.mark.parametrize("case", test_data)
    def test_login(self, ui_driver, case):
        """登录UI测试"""
        log.info(f"执行用例：{case['case_name']}")
        # 初始化页面
        login_page = LoginPage(ui_driver)
        home_page = HomePage(ui_driver)
        time.sleep(3)
        # 执行登录操作
        login_page.open_login_page()
        login_page.login(case["username"], case["password"])
        sleep(3)
        # 断言结果
        # 断言结果（最终正确版！）
        if case["expected_result"] == "登录成功":
            # 等待页面跳转到后台，最多等10秒
            ui_driver.wait_for_url("**/dashboard", timeout=10000)
            assert "dashboard" in ui_driver.url, "登录失败"
        else:
            error_tip = login_page.get_error_tip()
            assert case["expected_result"] in error_tip, f"错误提示错误：{error_tip}"

        log.info(f"用例{case['case_name']}执行成功")
