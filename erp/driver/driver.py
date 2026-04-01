import time

from playwright.sync_api import sync_playwright

class GetDriver:
        with sync_playwright() as p:
                browser=p.chromium.launch(headless=False)
                page=browser.new_page()
                page.goto('http://www.baidu.com')
                time.sleep(5)
                #page.fill('.chat-input-tool','张雪峰')
                #page.locator('.chat-input-tool').fill('张雪峰')
                page.click('.chat-input-tool')
                # 最强输入法：无视元素类型，直接输入！
                page.keyboard.type('张雪峰')
                page.click('#chat-submit-button')
                #page.locator('')
                page.click('.chat-input-container')
                # 2. 等待下拉框加载（必加，避免元素没出来就点击）
                page.wait_for_selector("text=张雪峰曾称最希望死法是猝死")
                time.sleep(5)
                # 3. 点击目标下拉项（文本定位，直接命中）
                page.click("text=张雪峰曾称最希望死法是猝死")

                # 验证：页面跳转到搜索结果页
                assert page.url.startswith("https://www.baidu.com/s?ie=utf-8&f=3&rsv_bp=1&rsv_idx=1&tn=baidu&wd=")
                print("点击下拉项成功！")

                time.sleep(15)
if __name__=='__main__':
    GetDriver()
