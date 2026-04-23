import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 订单模块压测任务文件
# 此文件定义了订单相关的压测任务，包括创建订单、获取订单列表和订单详情
# 注意：当前本地服务可能未实现订单相关接口，仅供将来扩展使用

import sys
import os
import yaml
from locust import TaskSet, task

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.tools.logger import log as logger

# 加载压测数据
CURRENT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
perf_data_path = os.path.join(CURRENT_DIR, 'perf_config.yaml')
with open(perf_data_path, 'r', encoding='utf-8') as f:
    perf_data = yaml.safe_load(f)

class OrderTasks(TaskSet):
    """订单模块压测任务"""
    
    @task(2)
    def create_order(self):
        """创建订单任务"""
        logger.info("开始创建订单")
        # 本地服务可能没有订单接口，这里仅作为示例
        payload = {
            "product_id": perf_data['api_params']['order']['create']['product_id'],
            "quantity": perf_data['api_params']['order']['create']['quantity']
        }
        response = self.client.post(
            perf_data['api_params']['order']['create']['endpoint'],
            json=payload,
            headers={"Content-Type": "application/json"}
        )
        if response.status_code == 200:
            # 保存订单ID
            self.order_id = response.json().get('order_id', '')
            logger.info("创建订单成功")
        else:
            logger.error(f"创建订单失败，状态码: {response.status_code}")
    
    @task(3)
    def get_order_list(self):
        """获取订单列表任务"""
        logger.info("开始获取订单列表")
        # 本地服务可能没有订单列表接口，这里仅作为示例
        params = {
            "page": perf_data['api_params']['order']['list']['page'],
            "page_size": perf_data['api_params']['order']['list']['page_size']
        }
        response = self.client.get(
            perf_data['api_params']['order']['list']['endpoint'],
            params=params
        )
        if response.status_code == 200:
            logger.info("获取订单列表成功")
        else:
            logger.error(f"获取订单列表失败，状态码: {response.status_code}")
    
    @task(1)
    def get_order_detail(self):
        """获取订单详情任务"""
        logger.info("开始获取订单详情")
        # 本地服务可能没有订单详情接口，这里仅作为示例
        if hasattr(self, 'order_id'):
            # 替换endpoint中的order_id占位符
            endpoint = perf_data['api_params']['order']['detail']['endpoint'].format(
                order_id=self.order_id
            )
            response = self.client.get(
                endpoint
            )
            if response.status_code == 200:
                logger.info("获取订单详情成功")
            else:
                logger.error(f"获取订单详情失败，状态码: {response.status_code}")
        else:
            logger.warning("无订单ID，无法获取订单详情")