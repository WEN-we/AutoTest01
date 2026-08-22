"""
电商登录服务对象（SO）—— 三层架构落地示范

调用链：用例层（tests/test_ecommerce/test_ec_login.py）
        → 服务层（本文件）：组合 PO，执行业务流
        → PO 层（page_objects/web/login_page.py）：元素定位与操作

业务规则说明：
- 本服务只负责"登录并取回页面错误提示"，不写断言（断言归用例层）；
- 步骤通过 BaseService.log_step 记录，Allure/日志中可回溯执行轨迹。
"""
from service_objects.base_service import BaseService
from page_objects.web.login_page import LoginPage


class EcLoginService(BaseService):
    """电商平台登录服务"""

    def __init__(self, page):
        super().__init__()
        self.login_page = LoginPage(page)

    def login_and_get_error(self, username: str, password: str) -> str:
        """执行登录并返回页面错误提示（无错误提示返回空串）"""
        self.log_step("打开电商平台首页")
        self.login_page.open_ec_login_page()

        self.log_step(f"提交登录表单（{username}）")
        self.login_page.ec_login(username, password)

        try:
            tip = self.login_page.get_error_tip().strip()
        except Exception:
            tip = ""
        self.log_step(f"页面错误提示：{tip or '无'}")
        return tip
