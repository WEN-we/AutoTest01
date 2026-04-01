import pytest
from utils.config_reader import ConfigReader
from utils.logger import log

test_data = ConfigReader.read_yaml("test_data/api_test_data.yaml")["user_login_api"]

class TestUserApi:
    @pytest.mark.parametrize("case", test_data)
    def test_user_login(self, api_client, case):
        log.info(f"执行用例：{case['case_name']}")

        response = api_client.post(
            url=case["url"],
            json=case["json"]
        )

        # 断言
        assert response.status_code == case["expected_code"]
        # 【修复】返回字段是 message，不是 msg！
        assert response.json()["message"] == case["expected_msg"]

        log.info(f"✅ 用例执行成功：{case['case_name']}")