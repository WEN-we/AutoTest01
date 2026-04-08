import logging
import allure

logger = logging.getLogger(__name__)

@allure.feature("红米4旧机型自动化")
@allure.story("系统设置APP")
def test_redmi4_open_settings(air_driver):
    """
    用例名：红米4打开系统设置APP
    分层：test_android_airtest（旧机型Airtest自动化）
    执行：pytest tests/test_android/test_android_airtest/ -v
    """
    with allure.step("1. 连接红米4手机"):
        logger.info("✅ 红米4手机连接成功")

    with allure.step("2. 启动系统设置APP"):
        air_driver.start_app()
        current_pkg = air_driver.get_current_package()
        logger.info(f"📦 当前前台APP：{current_pkg}")

    with allure.step("3. 断言设置APP启动成功"):
        assert "settings" in current_pkg, "❌ 系统设置APP启动失败"
        logger.info("✅ 系统设置APP启动成功，用例执行通过")