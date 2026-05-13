# 快速测试 Locust 连接
import requests

# 测试直接请求
response = requests.post(
    "http://localhost:8080/api/login",
    json={"username": "admin", "password": ""}
)
print(f"直接请求状态码: {response.status_code}")
print(f"响应: {response.text[:200]}")

# 测试 Locust 客户端
from locust import HttpUser, task, between

class TestUser(HttpUser):
    host = "http://localhost:8080"
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
    print("运行此测试: locust -f test_quick.py --headless -u 1 -r 1 --run-time 1s --host http://localhost:8080")
