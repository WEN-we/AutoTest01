"""
应用级常量定义
"""

# 文件上传限制
MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB

# 分页默认值
DEFAULT_PAGE = 1
DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100

# 测试执行超时（秒）
DEFAULT_TEST_TIMEOUT = 3600

# JWT配置默认值
DEFAULT_JWT_EXPIRATION_HOURS = 24
DEFAULT_BCRYPT_ROUNDS = 12
DEFAULT_MAX_LOGIN_ATTEMPTS = 5
DEFAULT_LOCKOUT_MINUTES = 30

# Allure报告配置
ALLURE_RESULTS_DIR = 'reports/allure-results'
ALLURE_REPORT_DIR = 'reports/allure-report'

# 上传目录
UPLOAD_FOLDER = 'uploads/avatars'

# CORS配置
CORS_ORIGINS = '*'
CORS_RESOURCES = r'/api/*'

# 日志级别映射
LOG_LEVEL_MAP = {
    'DEBUG': 10,
    'INFO': 20,
    'WARNING': 30,
    'ERROR': 40,
    'CRITICAL': 50
}
