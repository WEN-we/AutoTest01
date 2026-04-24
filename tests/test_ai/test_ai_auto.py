"""
AI 自主测试用例
可直接运行的 Pytest 用例
"""
import time

import pytest
import allure
from tests.test_ai.ai_test_engine import AITestEngine
from ai_page_objects.base.ai_base_page import AIBasePage
from utils.tools.logger import log as logger
from utils.tools.config_reader import ConfigReader


class TestAIAuto:
    """AI 自主测试用例"""

    @pytest.fixture(scope="class")
    def setup(self, web_driver):
        """测试前置条件"""
        logger.info("开始AI自主测试")
        yield web_driver
        logger.info("AI自主测试完成")

    @allure.feature("AI自主测试")
    @allure.story("登录页面测试")
    def test_ai_login(self, setup):
        """AI自主测试登录页面"""
        driver = setup

        # 1. 初始化页面
        page = AIBasePage(driver)

        # 2. 导航到登录页面
        try:
            ai_config = ConfigReader.read_yaml("config/ai_config.yaml")
            login_url = ai_config.get("test_scenarios", {}).get("login_page", {}).get("url", "https://example.com/login")
        except Exception:
            login_url = " http://127.0.0.1:8080"
        page.open(login_url)
        logger.info(f"导航到登录页面: {login_url}")

        # 3. 初始化AI测试引擎（从配置文件读取模型配置）
        ai_engine = AITestEngine()

        # 5. 运行自主测试
        result = ai_engine.run_autonomous_test(page)
        time.sleep(3)
        # 6. 验证测试结果
        assert result["final_result"]["status"] == "success", \
            f"测试失败: {result['final_result']['message']}"

        # 7. 记录测试结果
        allure.attach(
            str(result),
            name="测试结果",
            attachment_type=allure.attachment_type.JSON
        )

        logger.info("AI自主测试登录页面成功")

    # @allure.feature("AI自主测试")
    # @allure.story("首页测试")
    # def test_ai_homepage(self, setup):
    #     """AI自主测试首页"""
    #     driver = setup

    #     # 1. 初始化页面
    #     page = AIBasePage(driver)

    #     # 2. 导航到首页
    #     try:
    #         ai_config = ConfigReader.read_yaml("config/ai_config.yaml")
    #         home_url = ai_config.get("test_scenarios", {}).get("home_page", {}).get("url", "https://example.com")
    #     except Exception:
    #         home_url = "https://example.com"
    #     page.open(home_url)
    #     logger.info(f"导航到首页: {home_url}")

    #     # 3. 初始化AI测试引擎（从配置文件读取模型配置）
    #     ai_engine = AITestEngine()

    #     # 5. 运行自主测试
    #     result = ai_engine.run_autonomous_test(page)

    #     # 6. 验证测试结果
    #     assert result["final_result"]["status"] == "success", \
    #         f"测试失败: {result['final_result']['message']}"

    #     # 7. 记录测试结果
    #     allure.attach(
    #         str(result),
    #         name="测试结果",
    #         attachment_type=allure.attachment_type.JSON
    #     )

    #     logger.info("AI自主测试首页成功")