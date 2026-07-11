import pytest
import allure
from time import sleep
from page_objects.web.login_page import LoginPage
from utils.tools.config_reader import ConfigReader
from utils.tools.logger import log

test_data = ConfigReader.read_yaml("test_data/ui/ecommerce_test_data.yaml")["ec_login"]


@allure.feature("电商登录")
@pytest.mark.ecommerce
class TestEcLogin:
    """电商平台登录UI测试"""

    @pytest.mark.parametrize("case", test_data)
    def test_ec_login(self, ui_driver, case):
        log.info(f"执行用例：{case['case_name']}")

        expected_result = case.get("expected_result", "")

        # 正确登录场景需要验证码，跳过自动执行
        if "登录成功" in expected_result:
            pytest.skip("登录需要验证码，需手动验证")

        login_page = LoginPage(ui_driver)
        login_page.open_ec_login_page()
        sleep(2)

        login_page.ec_login(case["username"], case["password"])
        sleep(2)

        # 错误场景：检查页面错误提示
        try:
            error_tip = login_page.get_error_tip().strip()
        except Exception:
            error_tip = ""

        assert expected_result in error_tip, (
            f"错误提示断言失败：预期[{expected_result}]，实际[{error_tip}]"
        )
        log.info(f"✅ 错误场景验证成功：{error_tip}")
