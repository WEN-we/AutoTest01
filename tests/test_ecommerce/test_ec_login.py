import pytest
import allure
from service_objects.ec_login_service import EcLoginService
from utils.tools.config_reader import ConfigReader
from utils.tools.logger import log

test_data = ConfigReader.read_yaml("test_data/ui/ecommerce_test_data.yaml")["ec_login"]


@allure.feature("电商登录")
@pytest.mark.ecommerce
class TestEcLogin:
    """电商平台登录UI测试（三层架构：用例层 → 服务层 → PO 层）"""

    @pytest.mark.parametrize("case", test_data)
    def test_ec_login(self, ui_driver, case):
        log.info(f"执行用例：{case['case_name']}")

        expected_result = case.get("expected_result", "")

        # 正确登录场景需要验证码，跳过自动执行
        if "登录成功" in expected_result:
            pytest.skip("登录需要验证码，需手动验证")

        # 通过服务层执行业务流（登录 → 获取错误提示），用例层只写断言
        service = EcLoginService(ui_driver)
        error_tip = service.login_and_get_error(case["username"], case["password"])

        assert expected_result in error_tip, (
            f"错误提示断言失败：预期[{expected_result}]，实际[{error_tip}]"
        )
        log.info(f"✅ 错误场景验证成功：{error_tip}")
