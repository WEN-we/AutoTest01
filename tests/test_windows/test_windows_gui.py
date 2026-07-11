"""Windows桌面GUI测试（待实现）"""
# from utils.windows_driver import WindowsDriver
#
# def test_windows_gui():
#     driver = WindowsDriver()
#     driver.click(200, 200)
#     driver.input("Windows 自动化")
#     driver.screenshot("demo")
#     print("✅ Windows 桌面用例执行成功")

import pytest


@pytest.mark.windows
def test_windows_gui_placeholder():
    """占位测试，待Windows环境就绪后实现"""
    pytest.skip("Windows桌面GUI测试待实现")
