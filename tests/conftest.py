import pytest
from utils.ui_driver import UIDriver
from utils.api_client import APIClient
from utils.logger import log

# 接口客户端夹具（所有接口用例复用）
@pytest.fixture(scope="session")
def api_client():
    """创建接口客户端"""
    log.info("初始化接口客户端")
    client = APIClient()
    yield client
    log.info("接口客户端销毁")

# UI驱动夹具（所有UI用例复用）
# 🔥 重点：scope 改成 "session"，只启动一次浏览器
@pytest.fixture(scope="session", autouse=True)
def ui_driver():
    """UI自动化 fixture（彻底解决异步冲突）"""
    log.info("初始化UI驱动")
    driver = UIDriver()
    page = driver.start_driver()
    yield page
    log.info("关闭UI驱动")
    driver.quit_driver()