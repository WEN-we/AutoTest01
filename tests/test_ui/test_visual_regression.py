"""
视觉回归用例（挂接 UI 用例执行流）

能力链路：UI 用例执行 → visual_check fixture 截图 → utils/tools/visual_diff.py
像素级对比基线 → 差异超阈值失败 + 差异图证据 → Allure/CI 报告可见。

说明：
- 首次运行自动生成基线（reports/baselines/）并通过；后续运行开始真实对比
- 人工确认页面正确后，删除对应基线文件即可重新定基线（大厂基线管理惯例）
- 阈值默认 2%（headless 渲染差异容忍），可按页面严格度单独调整
"""
import pytest

LOGIN_URL = "http://127.0.0.1:8090/"


@pytest.mark.ui
def test_login_page_visual(web_driver, visual_check):
    """登录页视觉回归：打开登录页，截图对比基线。"""
    web_driver.goto(LOGIN_URL)
    web_driver.wait_for_load_state("networkidle")
    visual_check("login_page", threshold=0.02)


@pytest.mark.ui
def test_login_page_strict_visual(web_driver, visual_check):
    """登录页视觉回归（严格阈值 1%）：同一页面二次确认。"""
    web_driver.goto(LOGIN_URL)
    web_driver.wait_for_load_state("networkidle")
    visual_check("login_page_strict", threshold=0.01)
