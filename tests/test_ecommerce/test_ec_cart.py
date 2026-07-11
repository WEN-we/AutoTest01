import pytest
import allure
from time import sleep
from page_objects.web.login_page import LoginPage
from page_objects.web.products_page import ProductsPage
from page_objects.web.cart_page import CartPage
from utils.tools.config_reader import ConfigReader
from utils.tools.logger import log

cart_data = ConfigReader.read_yaml("test_data/ui/ecommerce_test_data.yaml")["ec_cart"]
login_data = ConfigReader.read_yaml("test_data/ui/ecommerce_test_data.yaml")["ec_login"]
# 登录凭据（取正确登录用例的账号密码）
ec_username = login_data[0]["username"]
ec_password = login_data[0]["password"]


@allure.feature("购物车管理")
@pytest.mark.ecommerce
class TestEcCart:
    """购物车UI测试"""

    @pytest.fixture(autouse=True)
    def setup_cart(self, ui_driver):
        """每个用例执行前：登录并添加商品到购物车"""
        log.info("===== 购物车用例前置：登录并添加商品 =====")
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

        # 3. 打开购物车页
        self.cart_page = CartPage(ui_driver)
        self.cart_page.open_cart_page()
        sleep(2)
        yield

    @pytest.mark.parametrize("case", cart_data)
    def test_cart_operation(self, case):
        log.info(f"执行用例：{case['case_name']}")
        case_name = case["case_name"]

        if "添加商品" in case_name:
            # 验证购物车中有商品
            count = self.cart_page.get_cart_item_count()
            assert count >= 1, f"添加商品后购物车为空，实际数量：{count}"
            titles = self.cart_page.get_cart_item_titles()
            log.info(f"✅ 添加商品成功，购物车商品数量：{count}，商品：{titles}")

        elif "增加" in case_name:
            item_index = case.get("item_index", 0)
            expected_qty = case.get("expected_qty", 2)
            self.cart_page.increase_quantity(item_index)
            sleep(1)
            log.info(f"✅ 商品数量增加操作执行完成，预期数量：{expected_qty}")

        elif "减少" in case_name:
            item_index = case.get("item_index", 0)
            expected_qty = case.get("expected_qty", 1)
            # 先增加一次以便有减少的空间
            self.cart_page.increase_quantity(item_index)
            sleep(1)
            self.cart_page.decrease_quantity(item_index)
            sleep(1)
            log.info(f"✅ 商品数量减少操作执行完成，预期数量：{expected_qty}")

        elif "删除" in case_name:
            item_index = case.get("item_index", 0)
            count_before = self.cart_page.get_cart_item_count()
            self.cart_page.remove_item(item_index)
            sleep(2)
            count_after = self.cart_page.get_cart_item_count()
            assert count_after < count_before, (
                f"删除商品后数量未减少：删除前[{count_before}]，删除后[{count_after}]"
            )
            log.info(
                f"✅ 删除商品成功，删除前[{count_before}]，删除后[{count_after}]"
            )

        else:
            log.warning(f"未识别的用例类型：{case_name}")
