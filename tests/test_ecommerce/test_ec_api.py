import pytest
import allure
from utils.tools.config_reader import ConfigReader
from utils.tools.logger import log
from utils.tools.api_client import APIClient

login_api_data = ConfigReader.read_yaml("test_data/api/ecommerce_api_test_data.yaml")["ec_user_login_api"]
product_list_api_data = ConfigReader.read_yaml("test_data/api/ecommerce_api_test_data.yaml")["ec_product_list_api"]
product_search_api_data = ConfigReader.read_yaml("test_data/api/ecommerce_api_test_data.yaml")["ec_product_search_api"]


@allure.feature("电商用户登录API")
@pytest.mark.ecommerce
class TestEcUserLoginApi:
    """电商用户登录API测试"""

    def setup_class(self):
        self.api_client = APIClient()
        # 关闭代理，本地必加
        self.api_client.session.trust_env = False

    @pytest.mark.parametrize("case", login_api_data)
    def test_ec_login(self, case):
        log.info(f"执行用例：{case['case_name']}")
        response = self.api_client.post(url=case["url"], json=case.get("json"))

        # 1. 状态码断言
        assert response.status_code == case["expected_code"], (
            f"状态码断言失败：预期[{case['expected_code']}]，实际[{response.status_code}]"
        )

        # 2. 业务消息断言
        res_json = response.json()
        expected_msg = case.get("expected_msg", "")
        if expected_msg:
            actual_msg = (
                res_json.get("message")
                or res_json.get("msg")
                or res_json.get("errorMessage")
                or ""
            )
            assert expected_msg in actual_msg, (
                f"消息断言失败：预期包含[{expected_msg}]，实际[{actual_msg}]"
            )

        log.info(f"✅ 用例通过：{case['case_name']}")


@allure.feature("电商商品列表API")
@pytest.mark.ecommerce
class TestEcProductListApi:
    """电商商品列表API测试"""

    def setup_class(self):
        self.api_client = APIClient()
        self.api_client.session.trust_env = False

    @pytest.mark.parametrize("case", product_list_api_data)
    def test_product_list(self, case):
        log.info(f"执行用例：{case['case_name']}")
        response = self.api_client.get(url=case["url"], params=case.get("params"))

        # 1. 状态码断言
        assert response.status_code == case["expected_code"], (
            f"状态码断言失败：预期[{case['expected_code']}]，实际[{response.status_code}]"
        )

        # 2. 业务消息断言
        res_json = response.json()
        expected_msg = case.get("expected_msg", "")
        if expected_msg:
            actual_msg = res_json.get("message") or res_json.get("msg") or ""
            assert expected_msg in actual_msg, (
                f"消息断言失败：预期包含[{expected_msg}]，实际[{actual_msg}]"
            )

        log.info(f"✅ 用例通过：{case['case_name']}")


@allure.feature("电商商品搜索API")
@pytest.mark.ecommerce
class TestEcProductSearchApi:
    """电商商品搜索API测试"""

    def setup_class(self):
        self.api_client = APIClient()
        self.api_client.session.trust_env = False

    @pytest.mark.parametrize("case", product_search_api_data)
    def test_product_search(self, case):
        log.info(f"执行用例：{case['case_name']}")
        response = self.api_client.get(url=case["url"], params=case.get("params"))

        # 1. 状态码断言
        assert response.status_code == case["expected_code"], (
            f"状态码断言失败：预期[{case['expected_code']}]，实际[{response.status_code}]"
        )

        # 2. 业务消息断言
        res_json = response.json()
        expected_msg = case.get("expected_msg", "")
        if expected_msg:
            actual_msg = res_json.get("message") or res_json.get("msg") or ""
            assert expected_msg in actual_msg, (
                f"消息断言失败：预期包含[{expected_msg}]，实际[{actual_msg}]"
            )

        log.info(f"✅ 用例通过：{case['case_name']}")
