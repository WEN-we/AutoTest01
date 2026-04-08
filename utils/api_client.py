import requests
from utils.config_reader import ConfigReader
from utils.logger import log


class APIClient:
    """接口请求封装类（通用，无需修改）"""

    def __init__(self, base_url: str | None = None):
        """
        base_url:
          - None: 使用 env_config.yaml 中当前环境的 base_api_url
          - 指定值: 用于多端（Android/iOS/鸿蒙/Windows 等）按端覆写
        """
        # 获取当前环境的API基础地址
        self.base_url = base_url or ConfigReader.get_env_config()["base_api_url"]
        # 【修改：学之思管理端必须的请求头】
        self.headers = {
            "Content-Type": "application/json;charset=UTF-8",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Referer": "https://www.mindskip.net:7003/",
            "Origin": "https://www.mindskip.net:7003"
        }
        # 新增 session 保持登录状态
        self.session = requests.Session()
        self.session.headers.update(self.headers)

    def get(self, url, params=None, headers=None, timeout=10):
        """封装GET请求"""
        full_url = self.base_url + url
        final_headers = {**self.headers, **(headers or {})}
        try:
            log.info(f"发送GET请求：{full_url}，参数：{params}")
            response = self.session.get(
                full_url, params=params, headers=final_headers, timeout=timeout
            )
            response.raise_for_status()
            log.info(f"GET响应：{response.status_code}，数据：{response.json()}")
            return response
        except requests.exceptions.RequestException as e:
            log.error(f"GET请求失败：{e}")
            raise

    def post(self, url, json=None, data=None, headers=None, timeout=10):
        """封装POST请求"""
        full_url = self.base_url + url
        final_headers = {**self.headers, **(headers or {})}
        try:
            log.info(f"发送POST请求：{full_url}，数据：{json or data}")
            # 使用 session 发送
            response = self.session.post(
                full_url, json=json, data=data, headers=final_headers, timeout=timeout
            )
            log.info(f"POST响应：{response.status_code}，数据：{response.json()}")
            return response
        except requests.exceptions.RequestException as e:
            log.error(f"POST请求失败：{e}")
            raise


# 测试代码（可删除）
if __name__ == "__main__":
    client = APIClient()