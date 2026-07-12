# 性能压测配置文件
# 此文件用于配置性能测试的各项参数

# 基本配置
BASE_URL = "http://localhost:8090"  # 被测系统域名（本地登录服务）

# 压测参数
USER_COUNT = 100  # 并发用户数（峰值并发）
SPAWN_RATE = 10  # 每秒启动的用户数
RUN_TIME = "10m"  # 压测运行时间（格式：数字+单位，如10s、5m、1h）

# 思考时间（秒）
# 思考时间是指用户执行完一个任务后，等待一段时间再执行下一个任务
# 用于模拟真实用户的操作间隔
# CI 环境通过 PERF_CI=1 自动缩短思考时间
MIN_THINK_TIME = 0.0 if os.getenv('PERF_CI', '0') == '1' else 1  # 最小思考时间
MAX_THINK_TIME = 0.5 if os.getenv('PERF_CI', '0') == '1' else 3  # 最大思考时间

# 报告配置
import os
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
REPORT_DIR = os.path.join(CURRENT_DIR, "reports")  # 报告存放目录
if not os.path.exists(REPORT_DIR):
    os.makedirs(REPORT_DIR)  # 如果目录不存在则创建

# 日志配置
# 使用项目全局的日志配置
LOG_LEVEL = "INFO"  # 日志级别（DEBUG、INFO、WARNING、ERROR、CRITICAL）