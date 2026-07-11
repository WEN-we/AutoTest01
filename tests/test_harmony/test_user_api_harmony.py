"""Harmony用户API测试（待实现）"""
# import pytest
#
# from utils.config_reader import ConfigReader
# from utils.logger import log
#
#
# test_data = ConfigReader.get_test_data("api_harmony")
#
#
# class TestHarmonyApi:
#     @pytest.mark.parametrize("case", test_data)
#     def test_harmony_login(self, harmony_api_client, case):
#         log.info(f"[Harmony] 执行用例：{case['case_name']}")
#
#         response = harmony_api_client.post(
#             url=case["url"],
#             json=case["json"],
#         )
#
#         assert response.status_code == case["expected_code"]
#         assert response.json().get("message") == case["expected_msg"]
#

import pytest


@pytest.mark.harmony
def test_harmony_user_api_placeholder():
    """占位测试，待Harmony环境就绪后实现"""
    pytest.skip("Harmony用户API测试待实现")
