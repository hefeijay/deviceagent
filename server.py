#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
设备管理Agent服务启动入口
"""
import uvicorn
from config.settings import settings
from utils.logger import logger

if __name__ == "__main__":
    logger.info("=" * 60)
    logger.info(f"启动 {settings.APP_NAME} v{settings.APP_VERSION}")
    logger.info("=" * 60)
    
    uvicorn.run(
        "api.app:app",
        host="0.0.0.0",
        port=5004,
        reload=settings.DEBUG,
        log_level="info"
    )

