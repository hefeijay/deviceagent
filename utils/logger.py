"""
日志配置
"""
import logging
import sys
from pathlib import Path
from logging.handlers import RotatingFileHandler
from config.settings import settings

# 创建日志目录
log_dir = Path(settings.LOG_PATH)
log_dir.mkdir(parents=True, exist_ok=True)

# 创建logger
logger = logging.getLogger("deviceagent")
logger.setLevel(getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO))

# 清除已有的handler
logger.handlers.clear()

# 日志格式
formatter = logging.Formatter(
    "%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

# 控制台handler
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.DEBUG)
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

# 文件handler
file_handler = RotatingFileHandler(
    log_dir / "deviceagent.log",
    maxBytes=10 * 1024 * 1024,  # 10MB
    backupCount=5,
    encoding="utf-8"
)
file_handler.setLevel(logging.INFO)
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

# 错误日志文件handler
error_handler = RotatingFileHandler(
    log_dir / "error.log",
    maxBytes=10 * 1024 * 1024,
    backupCount=5,
    encoding="utf-8"
)
error_handler.setLevel(logging.ERROR)
error_handler.setFormatter(formatter)
logger.addHandler(error_handler)

logger.info("日志系统初始化完成")

