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
