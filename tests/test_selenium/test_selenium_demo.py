"""
Selenium Web测试示例
演示Selenium基础页面类的使用
"""
import pytest
from page_objects.web.selenium_base_page import SeleniumBasePage


class TestSeleniumDemo:
    """Selenium Web测试示例类"""

    def test_selenium_search(self, selenium_driver):
        """测试Selenium搜索功能"""
        page = SeleniumBasePage(selenium_driver)
        
        page.goto_url("https://www.baidu.com", "百度首页")
        
        page.input_text(('id', 'kw'), 'selenium自动化测试', '搜索框')
        
        page.click(('id', 'su'), '搜索按钮')
        
        page.wait_for_visible(('css', '#content_left'), timeout=10)
        
        assert 'selenium' in page.get_current_url().lower() or 'selenium' in page.get_title().lower()

    def test_selenium_login_demo(self, selenium_driver):
        """测试登录示例（演示用）"""
        page = SeleniumBasePage(selenium_driver)
        
        page.goto_url("https://www.baidu.com", "百度首页")
        
        assert page.is_displayed(('id', 'kw'), timeout=5)
        
        page.input_text(('id', 'kw'), 'pytest')
        page.click(('id', 'su'))
        
        page.wait(2)
        
        assert 'pytest' in page.get_title().lower() or 'pytest' in page.get_current_url()


class TestSeleniumAdvanced:
    """Selenium高级操作测试示例"""

    def test_mouse_operations(self, selenium_driver):
        """测试鼠标操作"""
        page = SeleniumBasePage(selenium_driver)
        
        page.goto_url("https://www.baidu.com")
        page.input_text(('id', 'kw'), '鼠标操作测试')
        page.click(('id', 'su'))
        page.wait(2)

    def test_dropdown_select(self, selenium_driver):
        """测试下拉框选择（演示用）"""
        page = SeleniumBasePage(selenium_driver)
        page.goto_url("https://www.baidu.com")
        assert page.is_displayed(('id', 'kw'))

    def test_javascript_execute(self, selenium_driver):
        """测试JavaScript执行"""
        page = SeleniumBasePage(selenium_driver)
        
        page.goto_url("https://www.baidu.com")
        
        page.scroll_to_bottom()
        page.wait(1)
        
        page.scroll_to_top()
        page.wait(1)
        
        title = page.execute_script("return document.title;")
        assert title == page.get_title()
