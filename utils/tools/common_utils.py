import time
import hashlib
from utils.tools.logger import log


class CommonUtils:
    """通用工具类"""

    @staticmethod
    def get_current_time(format="%Y-%m-%d %H:%M:%S"):
        """获取当前时间"""
        return time.strftime(format, time.localtime())

    @staticmethod
    def md5_encrypt(text):
        """MD5加密"""
        md5 = hashlib.md5()
        md5.update(text.encode("utf-8"))
        return md5.hexdigest()

    @staticmethod
    def wait_for_seconds(seconds):
        """等待指定秒数"""
        log.info(f"等待{seconds}秒")
        time.sleep(seconds)


# 测试代码（可删除）
if __name__ == "__main__":
    print(CommonUtils.get_current_time())
    print(CommonUtils.md5_encrypt("123456"))
