import sys
import os
from pathlib import Path
from loguru import logger

from utils.tools.path_manager import get_log_path

LOG_DIR = Path(get_log_path())
LOG_DIR.mkdir(exist_ok=True)

logger.remove()

# 注意：不使用 enqueue=True（2026-08-22 修复）。
# loguru 的 enqueue 队列线程在 Windows 管道/重定向（CI、2>&1）环境下，
# 进程退出时会写入已关闭的 stderr 导致静默 exit 1（日志全丢）。
# loguru 本身线程安全，直接同步写入即可。
logger.add(
    sys.stderr,
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {module}:{line} | {message}",
    level="INFO"
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
