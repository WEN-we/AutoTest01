from utils.tools.logger import log


class BasePage:
    """基础页面类（通用操作）"""

    def __init__(self, page):
        self.page = page

    def click(self, locator, description=""):
        """点击元素"""
        log.info(f"点击元素：{description}，定位符：{locator}")
        self.page.click(locator)

    def input_text(self, locator, text, description=""):
        """输入文本"""
        log.info(f"输入文本：{description}，定位符：{locator}，内容：{text}")
        self.page.fill(locator, text)

    def get_text(self, locator, description=""):
        """获取元素文本"""
        text = self.page.text_content(locator)
        log.info(f"获取元素文本：{description}，定位符：{locator}，内容：{text}")
        return text

    def wait_for_element(self, locator, timeout=None):
        """等待元素可见"""
        log.info(f"等待元素可见：{locator}")
        self.page.wait_for_selector(locator, state="visible", timeout=timeout)

    def goto_url(self, url, description=""):
        """访问URL"""
        log.info(f"访问URL：{description}，地址：{url}")
        self.page.goto(url)
