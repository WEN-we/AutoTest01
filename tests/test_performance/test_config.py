# 测试配置文件加载
import sys
import os

# 模拟用户任务文件的路径设置
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.tools.path_manager import get_config_path
import yaml

# 获取配置文件路径
perf_data_path = get_config_path('perf_config.yaml')
print(f"配置文件路径: {perf_data_path}")
print(f"文件是否存在: {os.path.exists(perf_data_path)}")

# 读取配置文件
with open(perf_data_path, 'r', encoding='utf-8') as f:
    yaml_data = yaml.safe_load(f)

print("\n配置文件内容:")
print(f"login endpoint: {yaml_data['api_params']['user']['login']['endpoint']}")

# 模拟实际的 perf_data 结构
perf_data = {'users': [{'username': 'admin', 'password': ''}]}
perf_data['api_params'] = yaml_data.get('api_params', {})

print(f"\n最终的 login endpoint: {perf_data['api_params']['user']['login']['endpoint']}")