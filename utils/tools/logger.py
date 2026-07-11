import sys
import os
from pathlib import Path
from loguru import logger

from utils.tools.path_manager import get_log_path

LOG_DIR = Path(get_log_path())
LOG_DIR.mkdir(exist_ok=True)

logger.remove()

logger.add(
    sys.stderr,
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {module}:{line} | {message}",
    level="INFO",
    enqueue=True
)

logger.add(
    LOG_DIR / "auto_test_{time:YYYY-MM-DD}.log",
    rotation="00:00",
    retention="7 days",
    encoding="utf-8",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {module}:{line} | {message}",
    level="INFO"
)

log = logger

if __name__ == "__main__":
    log.info("自动化测试开始")
    log.error("测试失败：登录接口返回500")
