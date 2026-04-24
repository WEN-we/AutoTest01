"""
AI 增强页面对基类
继承项目原有 BasePage，添加 AI 相关方法
"""
from page_objects.base.base_page import BasePage  # 正确的导入路径
from utils.tools.logger import log as logger


class AIBasePage(BasePage):
    """AI 增强页面对基类"""

    def __init__(self, driver):
        """
        初始化页面对象

        Args:
            driver: WebDriver实例
        """
        super().__init__(driver)
        logger.info("初始化AI增强页面对象")
    
    def open(self, url):
        """
        打开指定URL

        Args:
            url: 要打开的URL
        """
        logger.info(f"打开URL: {url}")
        self.driver.goto(url)
    
    def get_title(self):
        """
        获取页面标题

        Returns:
            str: 页面标题
        """
        return self.driver.title()
    
    def get_url(self):
        """
        获取当前页面URL

        Returns:
            str: 当前页面URL
        """
        return self.driver.url
    
    def get_page_source(self):
        """
        获取页面源代码

        Returns:
            str: 页面源代码
        """
        return self.driver.content()
    
    def click(self, element_identifier):
        """
        点击元素

        Args:
            element_identifier: 元素标识符
        """
        # 清理元素标识符，移除可能的括号
        clean_identifier = element_identifier.strip().rstrip('()')
        
        # 打印页面信息，用于调试
        logger.info(f"尝试点击元素: {element_identifier}")
        logger.info(f"清理后的标识符: {clean_identifier}")
        logger.info(f"当前页面URL: {self.get_url()}")
        logger.info(f"当前页面标题: {self.get_title()}")
        
        # 优先尝试JavaScript点击，提高可靠性
        try:
            logger.info("优先尝试使用JavaScript点击按钮")
            if clean_identifier == "登录":
                # 专门处理登录按钮
                self.driver.evaluate("document.querySelector('button').click()")
            else:
                # 尝试通过ID或name定位
                js_code = f"""
                var element = document.getElementById('{clean_identifier}') || 
                             document.getElementsByName('{clean_identifier}')[0] || 
                             document.querySelector('button');
                if (element) element.click();
                """
                self.driver.evaluate(js_code)
            logger.info("成功使用JavaScript点击元素")
            return
        except Exception as e:
            logger.warning(f"JavaScript点击失败: {e}")
        
        # JavaScript点击失败，尝试Playwright定位
        # 尝试多种定位方式
        locators = [
            f"text={clean_identifier}",  # 文本定位（优先）
            f"button:has-text('{clean_identifier}')",  # 按钮文本定位（优先）
            f"#{clean_identifier}",  # ID定位
            f"[name='{clean_identifier}']",  # name定位
            f"button",  # 所有按钮
            f"//button",  # XPath所有按钮
            f"//button[contains(text(), '{clean_identifier}')]",  # XPath文本包含定位
        ]
        
        for locator in locators:
            try:
                logger.info(f"尝试定位: {locator}")
                element = self.driver.locator(locator)
                # 等待元素可见
                element.wait_for(state="visible", timeout=5000)
                # 等待元素可点击
                element.wait_for(state="enabled", timeout=5000)
                # 点击元素
                element.click(timeout=5000)
                logger.info(f"成功点击元素: {locator}")
                return
            except Exception as e:
                logger.warning(f"定位方式 {locator} 失败: {e}")
                continue
        
        # 所有定位方式都失败，尝试获取页面内容进行分析
        try:
            page_content = self.get_page_source()
            logger.info(f"页面内容（前500字符）: {page_content[:500]}")
        except Exception as e:
            logger.error(f"获取页面内容失败: {e}")
        
        # 所有定位方式都失败
        logger.error(f"所有定位方式都失败，无法点击元素: {element_identifier}")
        raise Exception(f"无法点击元素: {element_identifier}")
    
    def input(self, element_identifier, value):
        """
        输入值

        Args:
            element_identifier: 元素标识符
            value: 要输入的值
        """
        # 这里简化处理，实际应根据元素标识符类型进行不同的定位
        try:
            # 尝试通过ID定位
            element = self.driver.locator(f"#{element_identifier}")
            element.fill(value, timeout=5000)  # 设置超时时间
        except Exception:
            try:
                # 尝试通过name定位
                element = self.driver.locator(f"[name='{element_identifier}']")
                element.fill(value, timeout=5000)  # 设置超时时间
            except Exception as e:
                logger.error(f"输入元素 {element_identifier} 失败: {e}")
                raise

    def get_page_info(self):
        """
        获取页面信息，用于AI分析

        Returns:
            dict: 页面信息
        """
        logger.info("获取页面信息")

        try:
            page_info = {
                "title": self.get_title(),
                "url": self.get_url(),
                "source": self.get_page_source()
            }
            logger.info(f"获取页面信息成功: {page_info['title']}")
            return page_info
        except Exception as e:
            logger.error(f"获取页面信息失败: {e}")
            return {}

    def ai_click(self, element_identifier):
        """
        AI辅助点击

        Args:
            element_identifier: 元素标识符

        Returns:
            bool: 操作是否成功
        """
        logger.info(f"AI辅助点击元素: {element_identifier}")

        try:
            self.click(element_identifier)
            logger.info(f"点击元素 {element_identifier} 成功")
            return True
        except Exception as e:
            logger.error(f"点击元素 {element_identifier} 失败: {e}")
            return False

    def ai_input(self, element_identifier, value):
        """
        AI辅助输入

        Args:
            element_identifier: 元素标识符
            value: 输入值

        Returns:
            bool: 操作是否成功
        """
        logger.info(f"AI辅助输入元素: {element_identifier}, 值: {value}")

        try:
            self.input(element_identifier, value)
            logger.info(f"输入元素 {element_identifier} 成功")
            return True
        except Exception as e:
            logger.error(f"输入元素 {element_identifier} 失败: {e}")
            return False