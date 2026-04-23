import requests
from utils.tools.config_reader import ConfigReader
from utils.tools.logger import log


class APIClient:
    """接口请求封装类（云班课专用，不自动登录）"""

    def __init__(self, base_url: str | None = None):
        # 读取配置文件接口地址
        self.base_url = base_url or ConfigReader.get_env_config()["base_api_url"]

        # 你抓包的完整请求头（原样保留）
        self.headers = {
            "Accept": "application/json, text/plain, */*",
            "Accept-Encoding": "gzip, deflate, br, zstd",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6",
            "Content-Type": "application/json;charset=UTF-8",
            "Origin": "https://www.mosoteach.cn",
            "Referer": "https://www.mosoteach.cn/",
            "Sec-Ch-Ua": '"Chromium";v="146", "Not.A.Brand";v="24", "Microsoft Edge";v="146"',
            "Sec-Ch-Ua-Mobile": "?0",
            "Sec-Ch-Ua-Platform": '"Windows"',
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-site",
            "User-Agent": "Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36 Edg/108.0.0.0",
            "X-Client-App-Id": "MTWEB",
            "X-Client-Version": "6.0.0",
            "X-Security-Type": "SECURITY_TYPE_TOKEN"
        }

        # 初始化 session
        self.session = requests.Session()
        self.session.headers.update(self.headers)
        self.session.trust_env = False  # 关闭代理，必加

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