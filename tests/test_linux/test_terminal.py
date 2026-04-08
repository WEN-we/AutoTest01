"""Linux GUI 桌面终端测试（PO模式）"""
from page_objects.linux_gui.terminal_page import TerminalPage

def test_linux_run_command():
    terminal = TerminalPage()
    terminal.run_command("ls -l")