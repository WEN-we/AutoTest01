from time import sleep
import pytest
from page_objects.web.login_page import LoginPage
from page_objects.web.home_page import HomePage
from utils.tools.config_reader import ConfigReader
from utils.tools.logger import log

test_data = ConfigReader.read_yaml("test_data/ui/ui_test_data.yaml")["login_syzy_smoken_web"]

class TestUserUI:
    """用户模块UI用例（最终版：用首页元素文字断言成功）"""

    @pytest.mark.parametrize("case", test_data)
    def test_login(self, ui_driver, case):
        log.info(f"执行用例：{case['case_name']}")

        login_page = LoginPage(ui_driver)
        home_page = HomePage(ui_driver)

        login_page.open_login_page()
        sleep(2)

        login_page.login(case["username"], case["password"])
        sleep(3)

        # 失败提示
        alert_text = login_page.get_alert_text()
        error_tip = ""
        try:
            error_tip = login_page.get_error_tip().strip()
        except:
            error_tip = ""

        # ===========================
        # 核心判断
        # ===========================
        username = case["username"]
        password = case["password"]
        expected_alert = case.get("expected_alert", "")
        expected_text= case.get("expected_text", "")

        # 1. 登录成功 → 取首页元素文字断言
        if case["expected_result"] == "登录成功":
            actual_text = home_page.get_home_text()  # 获取真实文字

            # 🔥 真正的断言：文字必须一致
            assert expected_text in actual_text, f"登录成功断言失败！预期：{expected_text}，实际：{actual_text}"

            # 获取文字
            actual_text1 = home_page.get_desktop_text()
            # ✅ 断言：包含关系（企业最常用）
            assert "我的桌面" in actual_text1, f"登录失败，当前文字：{actual_text1}"


            log.info(f"✅ 登录成功，元素文字校验正确：[{actual_text}]")

        # 2. 为空 → 弹窗
        elif username == "" or password == "":
            assert expected_alert in alert_text
            log.info(f"✅ 空值弹窗：{alert_text}")

        # 3. 错误账号 → 页面提示
        else:
            assert case["expected_result"] in error_tip
            log.info(f"✅ 错误提示：{error_tip}")

        log.info(f"✅ 用例完成：{case['case_name']}")