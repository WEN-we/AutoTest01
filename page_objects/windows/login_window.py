from page_objects.windows.base_window import BaseWindow

class LoginWindow(BaseWindow):
    def __init__(self):
        super().__init__()
        self.username_input = (100, 120)
        self.password_input = (100, 170)
        self.login_btn = (120, 220)

    def login(self, username, password):
        self.click(*self.username_input)
        self.input(username)
        self.click(*self.password_input)
        self.input(password)
        self.click(*self.login_btn)