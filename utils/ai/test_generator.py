"""
AI 用例生成器（大厂 AI 时代提效：需求/描述 → 用例骨架）

能力：
- LLM 模式：根据目标描述（页面/接口/业务场景）生成 pytest 用例骨架代码
- 模板模式：未配置 LLM 时，输出可编辑的 pytest 用例模板（带步骤占位）

用法：
    from utils.ai.test_generator import TestGenerator
    gen = TestGenerator()
    code = gen.generate_case(target="登录接口：输入正确账号密码返回 token",
                             test_type="api")   # api | ui
"""
from utils.ai.llm_client import LLMClient
from utils.tools.logger import log

_SYSTEM_PROMPT = (
    "你是一名资深测试开发工程师，擅长编写 pytest 自动化测试用例。"
    "根据用户描述的目标，生成完整、可直接运行的 pytest 用例代码。"
    "要求：使用数据驱动风格、显式等待/断言、代码简洁、中文注释。"
    "只输出 Python 代码，不要解释。"
)

_API_TEMPLATE = '''\
"""TODO: 用例说明（由 AI 生成器创建）"""
import pytest
import allure
from utils.tools.api_client import APIClient
from utils.tools.logger import log


@allure.feature("TODO: 模块名")
class TestTodoModule:

    def test_todo_scenario(self, api_client: APIClient):
        """TODO: 场景描述"""
        log.info("执行：TODO")
        # Step 1: 准备数据（从 test_data/ 读取或构造）
        # Step 2: 发送请求
        # response = api_client.post("/api/path", json={...})
        # Step 3: 断言
        # assert response.status_code == 200
        # assert response.json()["code"] == 0
        pass
'''

_UI_TEMPLATE = '''\
"""TODO: 用例说明（由 AI 生成器创建）"""
import pytest
import allure
from page_objects.web.login_page import LoginPage
from utils.tools.logger import log


@allure.feature("TODO: 模块名")
class TestTodoUi:

    def test_todo_flow(self, ui_driver):
        """TODO: 场景描述"""
        log.info("执行：TODO")
        # page = LoginPage(ui_driver)
        # page.open_login_page()
        # Step 1: 操作
        # Step 2: 断言（PO 不写断言，断言放用例层）
        pass
'''


class TestGenerator:
    """AI 测试用例生成器"""

    def __init__(self, llm_client: LLMClient = None):
        self.llm = llm_client or LLMClient()

    def generate_case(self, target: str, test_type: str = "api") -> dict:
        """
        生成用例代码。
        test_type: api（接口）/ ui（Web UI）
        返回: {"code": str, "source": "llm"|"template"}
        """
        if self.llm.available:
            code = self._generate_by_llm(target, test_type)
            if code:
                return {"code": code, "source": "llm"}
        log.info("LLM 不可用，使用模板用例")
        return {"code": _UI_TEMPLATE if test_type == "ui" else _API_TEMPLATE,
                "source": "template"}

    def _generate_by_llm(self, target: str, test_type: str) -> str:
        prompt = (
            f"请为以下目标生成 pytest 测试用例代码。\n"
            f"测试类型：{'UI（使用 Playwright/Selenium 风格 page object，不写断言以外的逻辑）' if test_type == 'ui' else 'API（使用 APIClient）'}\n"
            f"目标描述：{target}\n"
        )
        code = self.llm.try_chat(prompt, system=_SYSTEM_PROMPT)
        return code.strip().strip("```python").strip("```").strip() if code else ""
