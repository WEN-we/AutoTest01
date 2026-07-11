# 快速测试 Locust 连接
# 注意：此文件为 locust 性能测试脚本，不应被 pytest 收集
# 文件名以 test_ 开头会被 pytest 自动收集，但顶层 requests 调用会导致阻塞
# 因此将顶层请求移入 main 块中，仅 locust 直接运行时执行

import requests
from locust import HttpUser, task, between


def quick_test_connection():
    """快速测试连接性，仅在直接运行时执行"""
    try:
        response = requests.post(
            "http://localhost:8090/api/login",
            json={"username": "admin", "password": ""},
            timeout=5
        )
        print(f"直接请求状态码: {response.status_code}")
        print(f"响应: {response.text[:200]}")
    except requests.exceptions.RequestException as e:
        print(f"连接失败: {e}")


class TestUser(HttpUser):
    host = "http://localhost:8090"
    wait_time = between(0, 0)

    @task
    def test_login(self):
        response = self.client.post(
            "/api/login",
            json={"username": "admin", "password": ""}
        )
        print(f"Locust 请求状态码: {response.status_code}")
        print(f"响应: {response.text[:200]}")


if __name__ == "__main__":
    quick_test_connection()
    print("运行此测试: locust -f test_quick.py --headless -u 1 -r 1 --run-time 1s --host http://localhost:8090")
