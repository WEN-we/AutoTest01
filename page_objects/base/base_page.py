"""
通用页面对象（PO）基类

大厂分层规范（PO 模式核心约束）：
- PO 层只封装「页面元素定位 + 页面操作」，【不写断言】；
- 断言统一放在用例层（tests/）；
- 业务流组合放在服务层（service_objects/）。

本基类提供跨平台通用的能力：
- driver/page 统一持有（兼容 Selenium WebDriver 与 Playwright Page）
- 统一日志（loguru）
- 失败证据：页面截图
- URL 校验辅助

升级记录（2026-08-22）：由 3 行空壳升级为完整通用基类。
"""
import os
from datetime import datetime

from utils.tools.logger import log


class BasePage:
    """通用页面对象基类（所有平台 PO 的抽象基类）"""

    def __init__(self, driver, logger=None):
        self.driver = driver
        # 兼容 Playwright 风格的 page 属性命名
        self.page = driver
        self.logger = logger or log

    # ---------- 失败证据 ----------
    def take_screenshot(self, filepath: str = None) -> str:
        """保存当前页面截图（兼容 Selenium/Playwright），返回保存路径；失败返回空串。"""
        if filepath is None:
            filepath = os.path.join(
                "reports", "screenshots",
                f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{self.__class__.__name__}.png",
            )
        os.makedirs(os.path.dirname(filepath), exist_ok=True)

        if hasattr(self.driver, "get_screenshot_as_png"):
            with open(filepath, "wb") as f:
                f.write(self.driver.get_screenshot_as_png())
        elif hasattr(self.driver, "screenshot"):
            self.driver.screenshot(path=filepath)
        else:
            self.logger.warning(f"当前 driver 不支持截图：{type(self.driver)}")
            return ""
        self.logger.info(f"截图已保存：{filepath}")
        return filepath

    # ---------- 校验辅助 ----------
    def get_current_url(self) -> str:
        """获取当前页面 URL（Selenium: current_url；Playwright: url）"""
        if hasattr(self.driver, "current_url"):
            return self.driver.current_url
        if hasattr(self.driver, "url"):
            return self.driver.url
        return ""

    def get_page_title(self) -> str:
        """获取页面标题（Selenium: title；Playwright: title()）"""
        try:
            if hasattr(self.driver, "title"):
                value = self.driver.title
                return value() if callable(value) else str(value)
        except Exception:
            pass
        return ""

    def verify_url_contains(self, keyword: str) -> bool:
        """URL 是否包含关键字（用于页面跳转校验，供用例层断言调用）"""
        return keyword in self.get_current_url()

    def log_action(self, message: str):
        """记录 PO 操作日志（统一格式）"""
        self.logger.info(f"[PO::{self.__class__.__name__}] {message}")
