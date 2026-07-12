# 用户模块压测任务文件
# 此文件定义了用户相关的压测任务，包括登录、获取用户信息和用户列表

import sys
import os
import yaml
import random
from locust import TaskSet, task

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.tools.logger import log as logger
from utils.tools.path_manager import get_config_path

# 从配置文件获取测试用户名列表
perf_data_path = get_config_path('perf_config.yaml')
logger.info(f"加载配置文件: {perf_data_path}")

with open(perf_data_path, 'r', encoding='utf-8') as f:
    perf_data = yaml.safe_load(f)

# 生成随机用户数据用于性能测试
# 用户名/密码必须与 CI 工作流（post-release-validation.yml）中插入数据库的凭据完全匹配
# CI 环境（PERF_CI=1）使用 100 个用户，本地使用 1000 个
perf_user_count = 100 if os.getenv('PERF_CI', '0') == '1' else 1000
perf_users = []
for i in range(1, perf_user_count + 1):
    perf_users.append({
        'username': f'perf_test_{i:04d}',
        'password': 'Test@1234'
    })

logger.info(f"生成 {len(perf_users)} 个测试用户用于性能测试")

# 调试：显示前5个测试用户
if perf_users:
    logger.info(f"前5个测试用户:")
    for i, u in enumerate(perf_users[:5]):
        logger.info(f"  {i+1}. username={u['username']}, password={u['password']}")

# 输出配置信息
login_endpoint = perf_data['api_params']['user']['login']['endpoint']
logger.info(f"登录接口配置: {login_endpoint}")

class UserTasks(TaskSet):
    """用户模块压测任务"""

    user_index = 0

    def on_start(self):
        """每个用户开始时执行的操作"""
        self.login()

    @task(3)
    def login(self):
        """登录任务"""
        user = perf_users[self.__class__.user_index]
        self.__class__.user_index = (self.__class__.user_index + 1) % len(perf_users)

        payload = {
            "username": user['username'],
            "password": user['password'],
            "test_mode": True
        }
        logger.info(f"用户 {user['username']} 开始登录，密码: {user['password']}")

        max_retries = 3
        retry_delay = 1

        for attempt in range(max_retries):
            try:
                response = self.client.post(
                    login_endpoint,
                    json=payload,
                    timeout=10
                )
                logger.info(f"响应状态码: {response.status_code}, 响应内容: {response.text[:200] if response.text else '无'}")

                if response.status_code == 200:
                    logger.info(f"用户 {user['username']} 登录成功")
                    return
                elif response.status_code == 0:
                    logger.warning(f"用户 {user['username']} 登录失败，状态码: 0，第 {attempt + 1}/{max_retries} 次尝试")
                    if attempt < max_retries - 1:
                        import time
                        time.sleep(retry_delay * (attempt + 1))
                else:
                    logger.error(f"用户 {user['username']} 登录失败，状态码: {response.status_code}")
                    return
            except Exception as e:
                logger.warning(f"用户 {user['username']} 登录异常: {str(e)}，第 {attempt + 1}/{max_retries} 次尝试")
                if attempt < max_retries - 1:
                    import time
                    time.sleep(retry_delay * (attempt + 1))

        logger.error(f"用户 {user['username']} 登录失败，已重试 {max_retries} 次")

    # @task(2)
    # def get_user_info(self):
    #     """获取用户信息任务"""
    #     logger.info("开始获取用户信息")
    #     # 本地服务可能没有用户信息接口，这里仅作为示例
    #     response = self.client.get(
    #         perf_data['api_params']['user']['user_info']['endpoint']
    #     )
    #     if response.status_code == 200:
    #         logger.info("获取用户信息成功")
    #     else:
    #         logger.error(f"获取用户信息失败，状态码: {response.status_code}")
    #
    # @task(1)
    # def get_user_list(self):
    #     """获取用户列表任务"""
    #     logger.info("开始获取用户列表")
    #     # 本地服务可能没有用户列表接口，这里仅作为示例
    #     params = {
    #         "page": perf_data['api_params']['user']['user_list']['page'],
    #         "page_size": perf_data['api_params']['user']['user_list']['page_size']
    #     }
    #     response = self.client.get(
    #         perf_data['api_params']['user']['user_list']['endpoint'],
    #         params=params
    #     )
    #     if response.status_code == 200:
    #         logger.info("获取用户列表成功")
    #     else:
    #         logger.error(f"获取用户列表失败，状态码: {response.status_code}")
