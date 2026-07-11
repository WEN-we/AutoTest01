import pytest
import allure
from time import sleep
from page_objects.web.products_page import ProductsPage
from utils.tools.config_reader import ConfigReader
from utils.tools.logger import log

search_data = ConfigReader.read_yaml("test_data/ui/ecommerce_test_data.yaml")["ec_product_search"]
category_data = ConfigReader.read_yaml("test_data/ui/ecommerce_test_data.yaml")["ec_product_category"]
price_data = ConfigReader.read_yaml("test_data/ui/ecommerce_test_data.yaml")["ec_price_filter"]


@allure.feature("商品搜索")
@pytest.mark.ecommerce
class TestEcProductSearch:
    """商品搜索UI测试"""

    @pytest.mark.parametrize("case", search_data)
    def test_search_product(self, ui_driver, case):
        log.info(f"执行用例：{case['case_name']}")
        products_page = ProductsPage(ui_driver)
        products_page.open_products_page()
        sleep(2)

        products_page.search_product(case["keyword"])
        sleep(2)

        count = products_page.get_product_count()
        assert count >= case["expected_min_count"], (
            f"搜索结果数量断言失败：预期>={case['expected_min_count']}，实际[{count}]"
        )

        # 有结果时校验标题包含关键词
        if count > 0:
            titles = products_page.get_product_titles()
            keyword = case["keyword"]
            try:
                matched = any(keyword in title for title in titles)
                assert matched, f"搜索结果标题未包含关键词[{keyword}]，实际标题：{titles}"
                log.info(f"✅ 搜索关键词[{keyword}]匹配成功，共{count}条结果")
            except AssertionError:
                raise
            except Exception as e:
                log.warning(f"标题匹配校验异常：{e}")
        else:
            log.info(f"✅ 搜索[{case['keyword']}]无结果，符合预期")


@allure.feature("商品分类筛选")
@pytest.mark.ecommerce
class TestEcProductCategory:
    """商品分类筛选UI测试"""

    @pytest.mark.parametrize("case", category_data)
    def test_select_category(self, ui_driver, case):
        log.info(f"执行用例：{case['case_name']}")
        products_page = ProductsPage(ui_driver)
        products_page.open_products_page()
        sleep(2)

        # 记录筛选前商品数量
        count_before = products_page.get_product_count()

        products_page.select_category(case["category"])
        sleep(2)

        count = products_page.get_product_count()
        assert count >= case["expected_min_count"], (
            f"分类筛选结果数量断言失败：分类[{case['category']}]，"
            f"预期>={case['expected_min_count']}，实际[{count}]"
        )
        log.info(
            f"✅ 分类[{case['category']}]筛选成功，筛选前[{count_before}]条，筛选后[{count}]条"
        )


@allure.feature("商品价格筛选")
@pytest.mark.ecommerce
class TestEcPriceFilter:
    """商品价格筛选UI测试"""

    @pytest.mark.parametrize("case", price_data)
    def test_filter_by_price(self, ui_driver, case):
        log.info(f"执行用例：{case['case_name']}")
        products_page = ProductsPage(ui_driver)
        products_page.open_products_page()
        sleep(2)

        products_page.filter_by_price(case["min_price"], case["max_price"])
        sleep(2)

        count = products_page.get_product_count()
        assert count >= case["expected_min_count"], (
            f"价格筛选结果数量断言失败：区间[{case['min_price']}-{case['max_price']}]，"
            f"预期>={case['expected_min_count']}，实际[{count}]"
        )

        # 有结果时校验价格在区间内
        if count > 0:
            min_price = case["min_price"]
            max_price = case["max_price"]
            try:
                price_elements = products_page.page.query_selector_all(
                    products_page.PRODUCT_PRICE
                )
                for el in price_elements:
                    if el:
                        price_text = el.inner_text()
                        price_value = float(
                            price_text.replace("¥", "").replace(",", "").strip()
                        )
                        assert min_price <= price_value <= max_price, (
                            f"商品价格[{price_value}]不在区间[{min_price}-{max_price}]内"
                        )
                log.info(
                    f"✅ 价格区间[{min_price}-{max_price}]筛选成功，共{count}条结果"
                )
            except AssertionError:
                raise
            except Exception as e:
                log.warning(f"价格区间校验异常：{e}")
        else:
            log.info(
                f"✅ 价格区间[{case['min_price']}-{case['max_price']}]无结果，符合预期"
            )
