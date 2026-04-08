def test_notepad_auto(windows_driver):
    # 1. 启动exe（企业标准）
    windows_driver.start_exe(r"C:\Windows\notepad.exe")
    windows_driver.wait(5)

    # 2. 输入（模拟人）
    windows_driver.input("企业级自动化测试")

    # 3. 保存（软件内部快捷键是允许的）
    windows_driver.hotkey("ctrl", "s")