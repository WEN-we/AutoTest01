import pytest
from utils.tools.config_reader import ConfigReader
from utils.tools.logger import log
from utils.tools.db_util import Database
from utils.tools.api_client import APIClient

test_data = ConfigReader.read_yaml("test_data/api/api_test_data.yaml")["user_smoken_login_api"]


# 🔥 标记为冒烟用例（企业标准）
@pytest.mark.smoke
class TestUserApi:
    def setup_class(self):
        self.db = Database()
        self.api_client = APIClient()
        # 关闭代理，本地必加
        self.api_client.session.trust_env = False

    @pytest.mark.parametrize("case", test_data)
    def test_user_login(self, case):
        log.info(f"执行冒烟用例：{case['case_name']}")
        username = case["json"]["account"]

        # 发送请求
        response = self.api_client.post(
            url=case["url"],
            json=case["json"]
        )

        # 1. 状态码断言（严格匹配，企业标准）
        assert response.status_code == case["expected_code"], f"状态码不符：{response.status_code}"

        res_json = response.json()

        # 2. 失败用例：校验错误信息
        expected_msg = case.get("errorMessage", "")
        if expected_msg:
            actual_msg = res_json.get("errorMessage") or res_json.get("message") or ""
            assert expected_msg in actual_msg, f"消息不匹配！预期包含：{expected_msg}"

        # 3. 成功用例：必须做的断言（企业标准）
        else:
            assert res_json["status"] is True, "登录成功业务状态错误"
            assert res_json.get("token") is not None, "登录成功未返回token"
            assert res_json.get("user") is not None, "登录成功未返回用户信息"
            # 修复：账号字段是 phoneNumber
            assert res_json["user"]["phoneNumber"] == username, "返回账号与登录账号不一致"

        log.info(f"✅ 冒烟用例通过：{case['case_name']}")