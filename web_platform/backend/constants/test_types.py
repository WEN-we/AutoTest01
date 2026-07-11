"""
测试类型常量定义
"""

# 测试类型到目录的映射
TEST_TYPE_MAPPING = {
    'api': 'test_api',
    'ui': 'test_ui',
    'smoke': 'test_smoke',
    'android': 'test_android',
    'ios': 'test_ios',
    'harmony': 'test_harmony',
    'windows': 'test_windows',
    'linux': 'test_linux',
    'service': 'test_service',
    'performance': 'test_performance',
    'ai': 'test_ai',
    'whitebox': 'test_whitebox'
}

# 测试类型到显示名称的映射
TEST_TYPE_DISPLAY_NAMES = {
    'api': '接口测试',
    'ui': 'Web UI测试',
    'smoke': '冒烟测试',
    'android': 'Android测试',
    'ios': 'iOS测试',
    'harmony': '鸿蒙测试',
    'windows': 'Windows测试',
    'linux': 'Linux测试',
    'service': '服务端测试',
    'performance': '性能测试',
    'ai': 'AI测试',
    'whitebox': '白盒测试'
}

# 测试场景类型
TEST_SCENES = {
    'login': '登录场景',
    'order': '订单场景',
    'payment': '支付场景',
    'search': '搜索场景',
    'other': '其他场景'
}

# pytest状态映射
PYTEST_STATUS_MAP = {
    'PASSED': 'passed',
    'FAILED': 'failed',
    'SKIPPED': 'skipped',
    'ERROR': 'error'
}

# 执行状态
EXECUTION_STATUS = {
    'PENDING': 'pending',
    'RUNNING': 'running',
    'SUCCESS': 'success',
    'FAILED': 'failed',
    'STOPPED': 'stopped'
}

# 任务状态
TASK_STATUS = {
    'IDLE': 'idle',
    'RUNNING': 'running',
    'SUCCESS': 'success',
    'FAILED': 'failed',
    'STOPPED': 'stopped'
}
