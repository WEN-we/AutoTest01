# Locust性能测试主入口文件
# 此文件定义了压测用户类和用户行为

import sys
import os
# 添加项目根目录到Python路径，确保能正确导入模块
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from locust import HttpUser, TaskSet, between
from tests.test_performance.tasks.user_tasks import UserTasks
from tests.test_performance.config import BASE_URL, MIN_THINK_TIME, MAX_THINK_TIME


class UserBehavior(TaskSet):
    """用户行为集合"""
    tasks = {
        UserTasks: 3,  # 用户模块任务权重，数字越大执行频率越高
        # OrderTasks: 2   # 订单模块任务权重（暂时注释，因为本地页面只有登录页面）
    }

class PerformanceUser(HttpUser):
    """压测用户类"""
    host = BASE_URL  # 被测系统的基础URL
    tasks = [UserBehavior]  # 用户行为集合
    wait_time = between(MIN_THINK_TIME, MAX_THINK_TIME)  # 思考时间范围

if __name__ == "__main__":
    import os
    import sys
    # 运行Locust
    os.system(f"locust -f {__file__}")