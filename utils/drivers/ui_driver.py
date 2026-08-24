from playwright.sync_api import sync_playwright
from utils.tools.config_reader import ConfigReader
from utils.tools.logger import log
import os


class UIDriver:
    """UI驱动封装类（Playwright）"""

    def __init__(self):
        self.ui_config = ConfigReader.get_ui_config()
        self.browser = None
        self.context = None
        self.page = None

    def _headless(self) -> bool:
        """无头模式判定：环境变量 HEADLESS 优先（CI 标准），未设置时读 yaml。"""
        env = os.getenv("HEADLESS")
        if env is not None:
            return env.strip().lower() in ("1", "true", "yes", "on")
        return bool(self.ui_config.get("headless", False))

    def start_driver(self):
        """启动浏览器"""
        playwright = sync_playwright().start()
        # 启动浏览器
        self.browser = getattr(playwright, self.ui_config["browser"]).launch(
            headless=self._headless(),
            args=[f"--window-size={self.ui_config['window_size']}"],
        )
        # 创建上下文
        self.context = self.browser.new_context(
            viewport={"width": 1920, "height": 1080}
        )
        self.page = self.context.new_page()
        # 设置超时
        self.page.set_default_timeout(self.ui_config["timeout"] * 1000)
        log.info(
            f"浏览器启动成功：{self.ui_config['browser']}，无头模式：{self.ui_config['headless']}"
        )
        return self.page

    def quit_driver(self):
        """关闭浏览器"""
        if self.browser:
            self.browser.close()
            log.info("浏览器已关闭")


# 测试代码（可删除）
if __name__ == "__main__":
    driver = UIDriver()
    page = driver.start_driver()
    page.goto(driver.ui_config["login_url"])
    driver.quit_driver()
