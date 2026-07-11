import os
import requests
from utils.tools.config_reader import ConfigReader
from utils.tools.logger import log


class APIClient:
    """通用接口请求封装类

    默认从 env_config.yaml 读取 base_url。
    支持通过环境变量覆盖默认 headers（如特定业务需要自定义 Origin/Referer）。
    """

    def __init__(self, base_url: str | None = None):
        # 读取配置文件接口地址
        self.base_url = base_url or ConfigReader.get_env_config()["base_api_url"]

        # 通用请求头（可通过环境变量 ECOMMERCE_ORIGIN / ECOMMERCE_REFERER 覆盖）
        origin = os.getenv("ECOMMERCE_ORIGIN", "")
        referer = os.getenv("ECOMMERCE_REFERER", "")
        self.headers = {
            "Accept": "application/json, text/plain, */*",
            "Accept-Encoding": "gzip, deflate, br, zstd",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Content-Type": "application/json;charset=UTF-8",
        }
        if origin:
            self.headers["Origin"] = origin
        if referer:
            self.headers["Referer"] = referer

        # 初始化 session
        self.session = requests.Session()
        self.session.headers.update(self.headers)
        self.session.trust_env = False  # 关闭代理

    def get(self, url, params=None, headers=None, timeout=10):
        # 自动处理斜杠
        full_url = self.base_url.rstrip('/') + '/' + url.lstrip('/')
        final_headers = {**self.headers, **(headers or {})}
        try:
            log.info(f"发送GET请求：{full_url}，参数：{params}")
            response = self.session.get(
                full_url, params=params, headers=final_headers, timeout=timeout
            )
            try:
                res_data = response.json()
            except:
                res_data = response.text[:200]
            log.info(f"GET响应：{response.status_code}，数据：{res_data}")
            return response
        except requests.exceptions.RequestException as e:
            log.error(f"GET请求失败：{e}")
            raise

    def post(self, url, json=None, data=None, headers=None, timeout=10):
        # 修复斜杠拼接
        full_url = self.base_url.rstrip('/') + '/' + url.lstrip('/')
        final_headers = {**self.headers, **(headers or {})}
        try:
            log.info(f"发送POST请求：{full_url}，数据：{json}")
            response = self.session.post(
                full_url, json=json, data=data, headers=final_headers, timeout=timeout
            )
            try:
                res_data = response.json()
            except:
                res_data = response.text[:200]
            log.info(f"POST响应：{response.status_code}，数据：{res_data}")
            return response
        except requests.exceptions.RequestException as e:
            log.error(f"POST请求失败：{e}")
            raise


# 测试代码（可删除）
if __name__ == "__main__":
    client = APIClient()