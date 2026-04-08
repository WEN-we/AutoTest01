from page_objects.linux_gui.base_linux_gui import BaseLinuxGUI

class TerminalPage(BaseLinuxGUI):
    def __init__(self):
        super().__init__()
        self.input_area = (50, 100)

    def run_command(self, cmd):
        self.click(*self.input_area)
        self.input(cmd)
        self.driver.press("enter")