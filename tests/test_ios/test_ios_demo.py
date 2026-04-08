import allure

@allure.feature("iOS 自动化")
@allure.story("APP启动测试")
def test_ios_app_start(ios_driver):
    """iOS 真机启动用例"""
    with allure.step("1. 检查APP是否启动"):
        assert ios_driver.is_app_installed("com.xxx.app")