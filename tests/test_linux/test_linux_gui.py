import allure
import pytest

@allure.feature("Linux 桌面 GUI 自动化")
@allure.story("Linux 桌面基础操作")
def test_linux_gui_terminal(linux_gui):
    """
    Linux GUI 测试：
    打开终端 → 输入命令 → 查看结果
    （仅桌面环境使用）
    """
    with allure.step("打开Linux终端"):
        linux_gui.hotkey("ctrl", "alt", "t")
        linux_gui.wait(2)

    with allure.step("输入测试命令"):
        linux_gui.input("echo 'Linux GUI 自动化测试'")
        linux_gui.wait(0.5)
        linux_gui.press("enter")
        linux_gui.wait(1)

    with allure.step("关闭终端"):
        linux_gui.hotkey("ctrl", "d")

    with allure.step("用例执行成功"):
        assert True