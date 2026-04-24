# 用户模块压测任务文件
# 此文件定义了用户相关的压测任务，包括登录、获取用户信息和用户列表

import sys
import os
import yaml
import pymysql
from locust import TaskSet, task

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.tools.logger import log as logger
from utils.tools.path_manager import get_config_path

# 从数据库获取用户数据
def get_users_from_db():
    """从数据库获取用户数据"""
    users = []
    try:
        db = pymysql.connect(
            host="localhost",
            user="root",
            password=os.getenv("MYSQL_ROOT_PASSWORD", ""),  # 改成你本地MySQL密码
            database="test_auto",
            charset="utf8mb4"
        )
        cursor = db.cursor(pymysql.cursors.DictCursor)
        cursor.execute("SELECT username, password FROM user")
        users = cursor.fetchall()
        cursor.close()
        db.close()
        logger.info(f"从数据库成功获取 {len(users)} 个用户数据")
    except Exception as e:
        logger.error(f"从数据库获取用户数据失败: {e}")
    return users

# 加载压测数据
# 使用路径管理工具获取配置文件路径
perf_data_path = get_config_path('perf_config.yaml')

# 优先从数据库获取用户数据
users_from_db = get_users_from_db()
if users_from_db:
    # 使用数据库中的用户数据
    perf_data = {'users': users_from_db}
    # 加载API参数配置
    with open(perf_data_path, 'r', encoding='utf-8') as f:
        yaml_data = yaml.safe_load(f)
        perf_data['api_params'] = yaml_data.get('api_params', {})
else:
    # 如果数据库获取失败，使用yaml中的默认数据
    logger.warning("从数据库获取用户数据失败，使用yaml中的默认数据")
    with open(perf_data_path, 'r', encoding='utf-8') as f:
        perf_data = yaml.safe_load(f)

class UserTasks(TaskSet):
    """用户模块压测任务"""
    
    # 类变量，用于跟踪账号索引
    user_index = 0
    
    def on_start(self):
        """每个用户开始时执行的操作"""
        self.login()  # 用户启动时自动执行登录
    
    @task(3)
    def login(self):
        """登录任务"""
        # 轮询使用不同的账号
        user = perf_data['users'][self.__class__.user_index]
        # 更新账号索引，确保下一个用户使用不同账号
        self.__class__.user_index = (self.__class__.user_index + 1) % len(perf_data['users'])
        
        payload = {
            "username": user['username'],
            "password": user['password']
        }
        logger.info(f"用户 {user['username']} 开始登录")
        # 发送登录请求
        response = self.client.post(
            perf_data['api_params']['user']['login']['endpoint'],
            json=payload,
            headers={"Content-Type": "application/json"}
        )
        if response.status_code == 200:
            # 本地登录接口返回code=200表示成功
            logger.info(f"用户 {user['username']} 登录成功")
        else:
            logger.error(f"用户 {user['username']} 登录失败，状态码: {response.status_code}")
    
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