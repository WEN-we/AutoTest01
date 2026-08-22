import pytest
from utils.tools.config_reader import ConfigReader
from utils.tools.logger import log
from utils.tools.api_client import APIClient

# 本地 SUT（local_web_login）登录接口用例集：
# - 参数校验用例（空用户名/密码）不依赖数据库，本地稳定可跑
# - 云班课外部用例（user_login_api 段）保留在 yaml，需外部网络环境
test_data = ConfigReader.read_yaml("test_data/api/api_test_data.yaml")["user_local_login_api"]


class TestUserApi:
    def setup_class(self):
        self.api_client = APIClient()
        # 关闭代理，本地必加
        self.api_client.session.trust_env = False

    @pytest.mark.parametrize("case", test_data)
    def test_user_login(self, case):
        log.info(f"执行用例：{case['case_name']}")
        payload = case["json"]

        # 发送请求
        response = self.api_client.post(
            url=case["url"],
            json=payload
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
            assert res_json.get("code") == 200, "登录成功业务状态错误"
            assert res_json.get("data", {}).get("token") is not None, "登录成功未返回token"

        log.info(f"✅ 用例通过：{case['case_name']}")