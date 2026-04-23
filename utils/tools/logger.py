from loguru import logger
import os
from pathlib import Path

# 日志目录（自动创建）
LOG_DIR = Path(__file__).parent.parent / "logs"
LOG_DIR.mkdir(exist_ok=True)

# 配置日志（企业级格式）
logger.add(
    LOG_DIR / "auto_test_{time:YYYY-MM-DD}.log",  # 按日期分文件
    rotation="00:00",  # 每天0点新建日志文件
    retention="7 days",  # 保留7天日志
    encoding="utf-8",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {module}:{line} | {message}",
    level="INFO"
)

# 对外暴露logger对象，其他模块直接导入使用
log = logger

# 测试代码（可删除）
if __name__ == "__main__":
    log.info("自动化测试开始")
    log.error("测试失败：登录接口返回500")