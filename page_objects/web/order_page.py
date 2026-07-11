from page_objects.web.base_page import BasePage

class OrderPage(BasePage):
    """订单管理页面对象"""
    ORDER_ITEM = ".order-item"
    ORDER_NUMBER = ".order-number"
    ORDER_STATUS = ".order-status"
    ORDER_TOTAL = ".order-total"
    ORDER_DATE = ".order-date"
    VIEW_DETAIL_BUTTON = "button:has-text('查看详情')"
    CANCEL_ORDER_BUTTON = "button:has-text('取消订单')"
    PAY_NOW_BUTTON = "button:has-text('立即支付')"
    CONFIRM_RECEIPT_BUTTON = "button:has-text('确认收货')"

    # 订单状态
    STATUS_PENDING_PAYMENT = "待付款"
    STATUS_PENDING_SHIPMENT = "待发货"
    STATUS_PENDING_DELIVERY = "待收货"
    STATUS_COMPLETED = "已完成"
    STATUS_CANCELLED = "已取消"

    def __init__(self, page):
        super().__init__(page)

    def open_orders_page(self):
        from utils.tools.config_reader import ConfigReader
        env = ConfigReader.get_env_config()
        self.goto_url(f"{env['base_ui_url']}/orders", "订单管理页")

    def get_order_count(self):
        return len(self.page.query_selector_all(self.ORDER_ITEM))

    def get_order_statuses(self):
        items = self.page.query_selector_all(self.ORDER_ITEM)
        return [item.query_selector(self.ORDER_STATUS).inner_text() for item in items if item.query_selector(self.ORDER_STATUS)]

    def view_order_detail(self, index=0):
        buttons = self.page.query_selector_all(self.VIEW_DETAIL_BUTTON)
        if index < len(buttons):
            buttons[index].click()
            self.page.wait_for_load_state("networkidle")

    def cancel_order(self, index=0):
        buttons = self.page.query_selector_all(self.CANCEL_ORDER_BUTTON)
        if index < len(buttons):
            buttons[index].click()
            self.page.wait_for_timeout(2000)

    def pay_order(self, index=0):
        buttons = self.page.query_selector_all(self.PAY_NOW_BUTTON)
        if index < len(buttons):
            buttons[index].click()
            self.page.wait_for_load_state("networkidle")

    def confirm_receipt(self, index=0):
        buttons = self.page.query_selector_all(self.CONFIRM_RECEIPT_BUTTON)
        if index < len(buttons):
            buttons[index].click()
            self.page.wait_for_timeout(2000)
