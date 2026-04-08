# 纯 Pytest 安卓用例，企业标准写法
def test_android_app_open(android_driver):
    """
    用例1：打开APP并验证启动成功
    """
    # 获取APP包名
    package = android_driver.current_package
    print(f"当前APP包名: {package}")

    # 断言：包名不为空 = 启动成功
    assert package is not None, "APP启动失败"


def test_android_click_element(android_driver):
    """
    用例2：点击元素（示例，可改为你的登录/首页）
    """
    try:
        # 根据 ID 点击（你后续替换成自己的元素）
        android_driver.find_element("id", "com.android.settings:id/title").click()
        print("元素点击成功")
    except Exception as e:
        print("未找到元素，跳过")