from page_objects.web.base_page import BasePage

class ProductsPage(BasePage):
    """商品列表页面对象"""
    # 搜索框
    SEARCH_INPUT = "input[placeholder*='']"  # 使用通配符匹配
    SEARCH_BUTTON = "button[type='submit']"

    # 商品分类
    CATEGORY_ELECTRONICS = "text='电子数码'"
    CATEGORY_BOOKS = "text='图书'"
    CATEGORY_CLOTHING = "text='服装'"
    CATEGORY_HOME_KITCHEN = "text='家居厨房'"

    # 价格筛选
    PRICE_MIN_INPUT = "input[placeholder='最低']"
    PRICE_MAX_INPUT = "input[placeholder='最高']"
    PRICE_APPLY_BUTTON = "button:has-text('应用')"

    # 商品卡片
    PRODUCT_CARD = ".product-card"
    PRODUCT_TITLE = "h3"
    PRODUCT_PRICE = ".price"
    ADD_TO_CART_BUTTON = "button:has-text('加入购物车')"
    OUT_OF_STOCK_BUTTON = "button:has-text('缺货')"

    # 分页
    NEXT_PAGE_BUTTON = "button:has-text('下一页')"
    PREV_PAGE_BUTTON = "button:has-text('上一页')"

    def __init__(self, page):
        super().__init__(page)

    def open_products_page(self):
        from utils.tools.config_reader import ConfigReader
        env = ConfigReader.get_env_config()
        self.goto_url(f"{env['base_ui_url']}/products", "商品列表页")

    def search_product(self, keyword):
        self.page.fill(self.SEARCH_INPUT, keyword)
        self.page.click(self.SEARCH_BUTTON)
        self.page.wait_for_load_state("networkidle")

    def select_category(self, category_name):
        self.page.click(f"text='{category_name}'")
        self.page.wait_for_load_state("networkidle")

    def filter_by_price(self, min_price, max_price):
        self.page.fill(self.PRICE_MIN_INPUT, str(min_price))
        self.page.fill(self.PRICE_MAX_INPUT, str(max_price))
        self.page.click(self.PRICE_APPLY_BUTTON)
        self.page.wait_for_load_state("networkidle")

    def get_product_count(self):
        return len(self.page.query_selector_all(self.PRODUCT_CARD))

    def get_product_titles(self):
        cards = self.page.query_selector_all(self.PRODUCT_CARD)
        return [card.query_selector(self.PRODUCT_TITLE).inner_text() for card in cards if card.query_selector(self.PRODUCT_TITLE)]

    def add_to_cart(self, index=0):
        buttons = self.page.query_selector_all(self.ADD_TO_CART_BUTTON)
        if index < len(buttons):
            buttons[index].click()
            self.page.wait_for_timeout(2000)
            return True
        return False

    def is_product_out_of_stock(self, index=0):
        cards = self.page.query_selector_all(self.PRODUCT_CARD)
        if index < len(cards):
            return cards[index].query_selector(self.OUT_OF_STOCK_BUTTON) is not None
        return False

    def go_to_next_page(self):
        self.page.click(self.NEXT_PAGE_BUTTON)
        self.page.wait_for_load_state("networkidle")

    def go_to_prev_page(self):
        self.page.click(self.PREV_PAGE_BUTTON)
        self.page.wait_for_load_state("networkidle")

    def click_product(self, index=0):
        cards = self.page.query_selector_all(self.PRODUCT_CARD)
        if index < len(cards):
            cards[index].click()
            self.page.wait_for_load_state("networkidle")
            return True
        return False
