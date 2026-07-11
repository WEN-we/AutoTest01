import os
import sys
import shutil
import subprocess
from pathlib import Path
from datetime import datetime

if sys.platform == 'win32':
    os.system('chcp 65001 >nul 2>&1')
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

import pytest

from utils.tools.logger import logger


def _truthy_env(name: str) -> bool:
    return os.getenv(name, "").strip().lower() in {"1", "true", "yes", "y", "on"}


def _enabled(target: str) -> bool:
    """
    ENABLE_<TARGET>=1 时启用对应端的测试收集/执行。
    例如：ENABLE_ANDROID=1、ENABLE_WINDOWS=1
    """
    return _truthy_env(f"ENABLE_{target.upper()}")


def _path_has(parts: tuple[str, ...], path: Path) -> bool:
    p = str(path).replace("\\", "/")
    return any(f"/{part}/" in f"/{p}/" for part in parts)


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--run-all",
        action="store_true",
        default=False,
        help="收集并尝试运行所有端用例（可能需要额外环境/驱动）",
    )


def pytest_ignore_collect(collection_path: Path, config: pytest.Config) -> bool:
    # 让跨平台/重依赖用例默认不阻塞“基础可跑集”(API/UI)
    if config.getoption("--run-all"):
        return False

    p = collection_path

    # Android/iOS：默认不开启（需要 Appium/设备/环境）
    if _path_has(("tests/test_android",), p) and not _enabled("android"):
        return True
    if _path_has(("tests/test_ios",), p) and not _enabled("ios"):
        return True

    # Windows：只在 Windows 下默认收集；其他平台需显式 ENABLE_WINDOWS=1
    if _path_has(("tests/test_windows",), p):
        return sys.platform != "win32" and not _enabled("windows")

    # Linux GUI：只在 Linux 下默认收集；其他平台需显式 ENABLE_LINUX=1
    if _path_has(("tests/test_linux",), p):
        return sys.platform != "linux" and not _enabled("linux")

    # Service：通常需要 SSH/服务端环境，默认不开启
    if _path_has(("tests/test_service",), p) and not _enabled("service"):
        return True

    # Harmony：默认不开启（通常需要对应环境/服务端）
    if _path_has(("tests/test_harmony",), p) and not _enabled("harmony"):
        return True

    return False


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    """
    自动按目录给用例打 marker，避免逐个文件手工加 @pytest.mark.xxx。
    """
    for item in items:
        path = Path(str(item.fspath)).as_posix()
        if "/tests/test_api/" in path:
            item.add_marker(pytest.mark.api)
        elif "/tests/test_ui/" in path:
            item.add_marker(pytest.mark.ui)
        elif "/tests/test_smoke/" in path:
            item.add_marker(pytest.mark.smoke)
        elif "/tests/test_android/" in path:
            item.add_marker(pytest.mark.android)
        elif "/tests/test_ios/" in path:
            item.add_marker(pytest.mark.ios)
        elif "/tests/test_windows/" in path:
            item.add_marker(pytest.mark.windows)
        elif "/tests/test_linux/" in path:
            item.add_marker(pytest.mark.linux)
        elif "/tests/test_service/" in path:
            item.add_marker(pytest.mark.service)
        elif "/tests/test_harmony/" in path:
            item.add_marker(pytest.mark.harmony)
        elif "/tests/test_ecommerce/" in path:
            item.add_marker(pytest.mark.ecommerce)
        elif "/tests/test_ai/" in path:
            item.add_marker(pytest.mark.ai)
        elif "/tests/test_performance/" in path:
            item.add_marker(pytest.mark.performance)
        elif "/tests/test_selenium/" in path:
            item.add_marker(pytest.mark.selenium)
        elif "/tests/test_whitebox/" in path:
            item.add_marker(pytest.mark.whitebox)

# ==============================
# 1. Web 自动化驱动
# ==============================
@pytest.fixture(scope="session", name="web_driver")
def fixture_web_driver():
    logger.info("===== Web 驱动初始化 =====")
    from utils.drivers.ui_driver import UIDriver

    web = UIDriver()
    driver = web.start_driver()
    yield driver
    web.quit_driver()
    logger.info("===== Web 驱动关闭 =====")


@pytest.fixture(scope="session", name="ui_driver")
def fixture_ui_driver(web_driver):
    """
    兼容用例中使用的 ui_driver 命名（实际复用 web_driver）。
    """
    yield web_driver


@pytest.fixture(scope="session", name="selenium_driver")
def fixture_selenium_driver():
    """
    Selenium Web驱动（Chrome/Firefox/Edge）
    """
    logger.info("===== Selenium 驱动初始化 =====")
    from utils.drivers.selenium_driver import SeleniumDriver

    selenium = SeleniumDriver()
    driver = selenium.start_driver()
    yield driver
    selenium.quit_driver()
    logger.info("===== Selenium 驱动关闭 =====")


@pytest.fixture(scope="session", name="api_client")
def fixture_api_client():
    from utils.tools.api_client import APIClient

    logger.info("===== API Client 初始化 =====")
    client = APIClient()
    yield client


@pytest.fixture(scope="session", name="harmony_api_client")
def fixture_harmony_api_client(request: pytest.FixtureRequest):
    if not _enabled("harmony") and not request.config.getoption("--run-all"):
        pytest.skip("未启用 Harmony 端：请设置 ENABLE_HARMONY=1 或使用 --run-all")

    from utils.tools.api_client import APIClient
    from utils.tools.config_reader import ConfigReader

    base_url = ConfigReader.get_harmony_config()["base_api_url"]
    logger.info(f"===== Harmony API Client 初始化: {base_url} =====")
    client = APIClient(base_url=base_url)
    yield client

# ==============================
# 2. 安卓新机型驱动（Appium）
# ==============================
@pytest.fixture(scope="session", name="android_driver")
def fixture_android_driver(request: pytest.FixtureRequest):
    if not _enabled("android") and not request.config.getoption("--run-all"):
        pytest.skip("未启用 Android 端：请设置 ENABLE_ANDROID=1 或使用 --run-all")
    logger.info("===== 安卓新机型驱动初始化 =====")
    from utils.drivers.android_driver import AndroidDriver

    ad = AndroidDriver()
    driver = ad.start_driver()
    yield driver
    ad.quit_driver()
    logger.info("===== 安卓新机型驱动关闭 =====")

# ==============================
# 3. iOS 驱动
# ==============================
@pytest.fixture(scope="session", name="ios_driver")
def fixture_ios_driver(request: pytest.FixtureRequest):
    if not _enabled("ios") and not request.config.getoption("--run-all"):
        pytest.skip("未启用 iOS 端：请设置 ENABLE_IOS=1 或使用 --run-all")
    logger.info("===== iOS 驱动初始化 =====")
    from utils.drivers.ios_driver import IosDriver

    ios = IosDriver()
    driver = ios.start_driver()
    yield driver
    ios.quit_driver()
    logger.info("===== iOS 驱动关闭 =====")

# ==============================
# 4. 安卓旧机型驱动（Airtest · 红米4专用）
# ==============================
@pytest.fixture(scope="session", name="air_driver")
def fixture_air_driver(request: pytest.FixtureRequest):
    if not _enabled("android") and not request.config.getoption("--run-all"):
        pytest.skip("未启用 Android(Airtest) 端：请设置 ENABLE_ANDROID=1 或使用 --run-all")
    logger.info("===== 安卓旧机型驱动（Airtest）初始化 =====")
    from utils.drivers.airtest_driver import AirtestDriver

    air = AirtestDriver()
    yield air
    air.quit()
    logger.info("===== 安卓旧机型驱动（Airtest）关闭 =====")

# ==============================
# 5. Windows GUI 驱动
# ==============================
@pytest.fixture(scope="session", name="windows_driver")
def fixture_windows_driver(request: pytest.FixtureRequest):
    if (
        not _enabled("windows")
        and not request.config.getoption("--run-all")
        and sys.platform != "win32"
    ):
        pytest.skip("非 Windows 平台且未启用 Windows 端：请设置 ENABLE_WINDOWS=1 或使用 --run-all")
    logger.info("===== Windows 驱动初始化 =====")
    from utils.drivers.windows_driver import WindowsDriver

    win = WindowsDriver()
    yield win
    logger.info("===== Windows 驱动关闭 =====")

# ==============================
# 6. Linux GUI 驱动
# ==============================
@pytest.fixture(scope="session", name="linux_driver")
def fixture_linux_driver(request: pytest.FixtureRequest):
    if (
        not _enabled("linux")
        and not request.config.getoption("--run-all")
        and sys.platform != "linux"
    ):
        pytest.skip("非 Linux 平台且未启用 Linux 端：请设置 ENABLE_LINUX=1 或使用 --run-all")
    logger.info("===== Linux GUI 驱动初始化 =====")
    from utils.drivers.linux_driver import LinuxDriver

    linux_gui = LinuxDriver()
    yield linux_gui
    logger.info("===== Linux GUI 驱动关闭 =====")


@pytest.fixture(scope="session", name="linux_gui")
def fixture_linux_gui(linux_driver):
    """
    兼容用例中使用的 linux_gui 命名（实际复用 linux_driver）。
    """
    yield linux_driver

# ==============================
# 7. Linux SSH 客户端
# ==============================
@pytest.fixture(scope="session", name="linux_client")
def fixture_linux_client(request: pytest.FixtureRequest):
    if not _enabled("service") and not request.config.getoption("--run-all"):
        pytest.skip("未启用 service 端：请设置 ENABLE_SERVICE=1 或使用 --run-all")
    logger.info("===== Linux SSH 连接 =====")
    from utils.tools.linux_client import LinuxClient

    client = LinuxClient()
    client.connect()
    yield client
    client.close()
    logger.info("===== Linux SSH 关闭 =====")


# ==============================
# 8. 本地执行自动生成Allure HTML报告
# ==============================
def _get_allure_path() -> str:
    """获取allure可执行文件路径"""
    allure_exe = shutil.which('allure')
    if allure_exe:
        return allure_exe
    venv_allure = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.venv', 'Scripts', 'allure.exe')
    if os.path.exists(venv_allure):
        return venv_allure
    return None


def _detect_test_type_from_items(items) -> str:
    """从测试用例路径检测测试类型"""
    if not items:
        return 'unknown'
    # 取第一个用例的路径来判断测试类型
    first_path = str(items[0].fspath).replace('\\', '/')
    type_map = {
        'test_api': 'api',
        'test_ui': 'ui',
        'test_smoke': 'smoke',
        'test_android': 'android',
        'test_ios': 'ios',
        'test_windows': 'windows',
        'test_linux': 'linux',
        'test_harmony': 'harmony',
        'test_service': 'service',
        'test_performance': 'performance',
        'test_ai': 'ai',
        'test_whitebox': 'whitebox',
    }
    for key, test_type in type_map.items():
        if f'/tests/{key}/' in first_path or f'\\tests\\{key}\\' in first_path:
            return test_type
    return 'unknown'


def pytest_sessionfinish(session, exitstatus):
    """测试会话结束时自动生成Allure HTML报告

    本地手动执行pytest时：
    1. 从 allure-results 生成 HTML 报告
    2. 报告目录命名为：reports/allure-report/YYYYMMDD_HHMMSS_测试类型/
    3. 保留历史报告，不覆盖旧的
    """
    # 只在本地手动执行时生成（通过检测是否在测试平台执行）
    if os.getenv('TEST_PLATFORM_EXECUTION', '').strip().lower() in ('1', 'true', 'yes'):
        return

    allure_path = _get_allure_path()
    if not allure_path:
        logger.warning("未找到allure命令，跳过生成HTML报告")
        return

    project_root = os.path.dirname(os.path.dirname(__file__))
    allure_results_dir = os.path.join(project_root, 'reports', 'allure-results')

    # 检查是否有allure结果文件
    if not os.path.exists(allure_results_dir) or not os.listdir(allure_results_dir):
        logger.info("没有allure结果文件，跳过生成报告")
        return

    # 检测测试类型
    test_type = _detect_test_type_from_items(session.items)

    # 生成报告名称：时间戳_测试类型
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    report_name = f"{timestamp}_{test_type}"
    report_output_dir = os.path.join(project_root, 'reports', 'allure-report', report_name)

    try:
        os.makedirs(report_output_dir, exist_ok=True)
        cmd = f'"{allure_path}" generate "{allure_results_dir}" -o "{report_output_dir}" --clean'
        logger.info(f"正在生成Allure HTML报告: {report_name}")
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=120
        )

        if result.returncode == 0:
            logger.info(f"✅ Allure报告生成成功: {report_output_dir}")
            # 生成完成后清空 allure-results，避免下次执行时混入旧数据
            for f in os.listdir(allure_results_dir):
                fpath = os.path.join(allure_results_dir, f)
                if os.path.isfile(fpath):
                    os.remove(fpath)
                elif os.path.isdir(fpath):
                    shutil.rmtree(fpath)
            logger.info("已清理 allure-results 临时文件")
        else:
            logger.error(f"Allure报告生成失败: {result.stderr}")
    except Exception as e:
        logger.error(f"生成Allure报告异常: {e}")