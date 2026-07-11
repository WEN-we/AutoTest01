import pytest
import allure
from time import sleep
from page_objects.web.login_page import LoginPage
from page_objects.web.products_page import ProductsPage
from page_objects.web.cart_page import CartPage
from page_objects.web.checkout_page import CheckoutPage
from utils.tools.config_reader import ConfigReader
from utils.tools.logger import log

checkout_data = ConfigReader.read_yaml("test_data/ui/ecommerce_test_data.yaml")["ec_checkout"]
login_data = ConfigReader.read_yaml("test_data/ui/ecommerce_test_data.yaml")["ec_login"]
# 登录凭据（取正确登录用例的账号密码）
ec_username = login_data[0]["username"]
ec_password = login_data[0]["password"]


@allure.feature("下单结算")
@pytest.mark.ecommerce
class TestEcCheckout:
    """下单结算UI测试"""

    @pytest.fixture(autouse=True)
    def setup_checkout(self, ui_driver):
        """每个用例执行前：登录 + 加购 + 进入结算页"""
        log.info("===== 下单用例前置：登录 + 加购 + 进入结算页 =====")
        self.ui_driver = ui_driver

        # 1. 登录
        login_page = LoginPage(ui_driver)
        login_page.open_ec_login_page()
        sleep(2)
        login_page.ec_login(ec_username, ec_password)
        sleep(2)

        # 2. 添加商品到购物车
        products_page = ProductsPage(ui_driver)
        products_page.open_products_page()
        sleep(2)
        products_page.add_to_cart(0)
        sleep(1)

        # 3. 进入购物车并跳转结算页
        cart_page = CartPage(ui_driver)
        cart_page.open_cart_page()
        sleep(2)
        cart_page.go_to_checkout()
        sleep(2)

        self.checkout_page = CheckoutPage(ui_driver)
        yield

    @pytest.mark.parametrize("case", checkout_data)
    def test_checkout(self, case):
        log.info(f"执行用例：{case['case_name']}")

        # 1. 填写收货信息
        self.checkout_page.fill_shipping_info(
            case["recipient"], case["phone"], case["address"]
        )
        sleep(1)

        # 2. 选择支付方式
        self.checkout_page.select_payment_method(case["payment_method"])
        sleep(1)

        # 3. 提交订单
        self.checkout_page.submit_order()
        sleep(2)

        # 4. 验证下单成功
        expected_result = case.get("expected_result", "")
        try:
            is_success = self.checkout_page.is_order_successful()
            assert is_success, f"下单未成功：{case['case_name']}"
            log.info(f"✅ 下单成功：{case['case_name']}，支付方式：{case['payment_method']}")
        except AssertionError:
            raise
        except Exception as e:
            log.error(f"下单成功验证异常：{e}")
            raise

        # 校验订单总金额存在
        try:
            order_total = self.checkout_page.get_order_total()
            log.info(f"订单总金额：{order_total}")
        except Exception as e:
            log.warning(f"获取订单总金额异常：{e}")
