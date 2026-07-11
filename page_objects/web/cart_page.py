from page_objects.web.base_page import BasePage

class CartPage(BasePage):
    """购物车页面对象"""
    CART_ITEM = ".cart-item"
    CART_ITEM_TITLE = ".cart-item-title"
    CART_ITEM_PRICE = ".cart-item-price"
    CART_ITEM_QTY = "input[placeholder*='数量']"
    QTY_INCREASE_BUTTON = "button:has-text('+')"
    QTY_DECREASE_BUTTON = "button:has-text('-')"
    REMOVE_BUTTON = "button:has-text('删除')"
    SELECT_ITEM_CHECKBOX = "input[type='checkbox']"
    TOTAL_PRICE = ".total-price"
    CHECKOUT_BUTTON = "button:has-text('去结算')"
    SELECT_ALL_CHECKBOX = "input[type='checkbox']:first"
    EMPTY_CART_TEXT = "text='购物车是空的'"

    def __init__(self, page):
        super().__init__(page)

    def open_cart_page(self):
        from utils.tools.config_reader import ConfigReader
        env = ConfigReader.get_env_config()
        self.goto_url(f"{env['base_ui_url']}/cart", "购物车页")

    def get_cart_item_count(self):
        return len(self.page.query_selector_all(self.CART_ITEM))

    def get_cart_item_titles(self):
        items = self.page.query_selector_all(self.CART_ITEM)
        return [item.query_selector(self.CART_ITEM_TITLE).inner_text() for item in items if item.query_selector(self.CART_ITEM_TITLE)]

    def increase_quantity(self, index=0):
        buttons = self.page.query_selector_all(self.QTY_INCREASE_BUTTON)
        if index < len(buttons):
            buttons[index].click()
            self.page.wait_for_timeout(1000)

    def decrease_quantity(self, index=0):
        buttons = self.page.query_selector_all(self.QTY_DECREASE_BUTTON)
        if index < len(buttons):
            buttons[index].click()
            self.page.wait_for_timeout(1000)

    def remove_item(self, index=0):
        buttons = self.page.query_selector_all(self.REMOVE_BUTTON)
        if index < len(buttons):
            buttons[index].click()
            self.page.wait_for_timeout(2000)

    def select_item(self, index=0):
        checkboxes = self.page.query_selector_all(self.SELECT_ITEM_CHECKBOX)
        if index < len(checkboxes):
            if not checkboxes[index].is_checked():
                checkboxes[index].click()

    def select_all_items(self):
        checkbox = self.page.query_selector(self.SELECT_ALL_CHECKBOX)
        if checkbox and not checkbox.is_checked():
            checkbox.click()

    def get_total_price(self):
        element = self.page.query_selector(self.TOTAL_PRICE)
        return element.inner_text() if element else "0"

    def is_cart_empty(self):
        return self.page.query_selector(self.EMPTY_CART_TEXT) is not None

    def go_to_checkout(self):
        self.page.click(self.CHECKOUT_BUTTON)
        self.page.wait_for_load_state("networkidle")
