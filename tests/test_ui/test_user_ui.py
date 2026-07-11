from time import sleep
import pytest
from page_objects.web.login_page import LoginPage
from utils.tools.config_reader import ConfigReader
from utils.tools.logger import log

test_data = ConfigReader.read_yaml("test_data/ui/ui_test_data.yaml")["login_web"]

class TestUserUI:
    """用户模块UI用例（最终正确版）"""

    @pytest.mark.parametrize("case", test_data)
    def test_login(self, ui_driver, case):
        log.info(f"执行用例：{case['case_name']}")

        # 初始化
        login_page = LoginPage(ui_driver)

        # 1. 打开页面
        login_page.open_login_page()
        sleep(2)

        # 2. 执行登录
        login_page.login(case["username"], case["password"])
        sleep(2)

        # 3. 获取弹窗
        alert_text = login_page.get_alert_text()

        # 4. 获取页面提示
        error_tip = ""
        try:
            error_tip = login_page.get_error_tip().strip()
        except:
            error_tip = ""

        # ===========================
        # 🔥 核心修复：根据场景判断
        # ===========================
        username = case["username"]
        password = case["password"]
        expected_alert = case.get("expected_alert", "")
        expected_result = case["expected_result"]

        # 情况1：用户名为空 或 密码为空 → 只校验弹窗
        if username == "" or password == "":
            assert expected_alert in alert_text, f"弹窗断言失败：预期[{expected_alert}]，实际[{alert_text}]"
            log.info(f"✅ 空值场景：弹窗校验成功 → {alert_text}")

        # 情况2：用户名密码都不为空（错误账号）→ 只校验页面文字
        else:
            assert expected_result in error_tip, f"页面提示断言失败：预期[{expected_result}]，实际[{error_tip}]"
            log.info(f"✅ 错误账号场景：页面提示校验成功 → {error_tip}")

        log.info(f"✅ 用例执行成功：{case['case_name']}")