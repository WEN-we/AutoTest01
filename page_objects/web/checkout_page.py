from page_objects.web.base_page import BasePage

class CheckoutPage(BasePage):
    """结算页面对象"""
    ADDRESS_INPUT = "textarea[placeholder*='地址']"
    RECIPIENT_INPUT = "input[placeholder*='收货人']"
    PHONE_INPUT = "input[placeholder*='手机']"
    PAYMENT_METHOD_ALIPAY = "text='支付宝'"
    PAYMENT_METHOD_WECHAT = "text='微信支付'"
    PAYMENT_METHOD_CARD = "text='信用卡'"
    PAYMENT_METHOD_DEBIT = "text='借记卡'"
    ORDER_TOTAL = ".order-total"
    SUBMIT_ORDER_BUTTON = "button:has-text('提交订单')"
    ORDER_SUCCESS_TEXT = "text='下单成功'"

    def __init__(self, page):
        super().__init__(page)

    def fill_shipping_info(self, recipient, phone, address):
        self.page.fill(self.RECIPIENT_INPUT, recipient)
        self.page.fill(self.PHONE_INPUT, phone)
        self.page.fill(self.ADDRESS_INPUT, address)

    def select_payment_method(self, method="alipay"):
        method_map = {
            "alipay": self.PAYMENT_METHOD_ALIPAY,
            "wechat": self.PAYMENT_METHOD_WECHAT,
            "card": self.PAYMENT_METHOD_CARD,
            "debit": self.PAYMENT_METHOD_DEBIT
        }
        selector = method_map.get(method, self.PAYMENT_METHOD_ALIPAY)
        self.page.click(selector)

    def get_order_total(self):
        element = self.page.query_selector(self.ORDER_TOTAL)
        return element.inner_text() if element else "0"

    def submit_order(self):
        self.page.click(self.SUBMIT_ORDER_BUTTON)
        self.page.wait_for_load_state("networkidle")
        self.page.wait_for_timeout(3000)

    def is_order_successful(self):
        return self.page.query_selector(self.ORDER_SUCCESS_TEXT) is not None
