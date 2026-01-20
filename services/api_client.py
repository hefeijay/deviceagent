#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
API客户端模块
负责上传喂食记录等数据到后端服务器
"""

import time
from typing import Dict, Any, Optional
from functools import wraps

import requests

from config.settings import settings
from utils.logger import logger


def retry_on_failure(max_attempts: int = 3, delay: float = 2.0):
    """重试装饰器"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < max_attempts - 1:
                        logger.warning(f"第{attempt + 1}次尝试失败: {e}, {delay}秒后重试...")
                        time.sleep(delay)
                    else:
                        logger.error(f"所有重试均失败，最终错误: {e}")
            raise last_exception
        return wrapper
    return decorator


class APIClient:
    """后端API客户端类"""
    
    def __init__(self):
        self.base_url = settings.BACKEND_API_BASE_URL
        self.timeout = settings.BACKEND_API_TIMEOUT
        self.session = requests.Session()
        
        logger.info(f"APIClient 初始化: base_url={self.base_url}")
    
    def _post_json(self, endpoint: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        发送POST JSON请求
        
        Args:
            endpoint: 端点路径（如 '/api/data/feeders'）
            data: 请求数据
            
        Returns:
            响应数据字典
        """
        url = f"{self.base_url.rstrip('/')}/{endpoint.lstrip('/')}"
        
        try:
            response = self.session.post(
                url,
                json=data,
                timeout=self.timeout
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"API请求失败: {url} - {e}")
            raise
    
    @retry_on_failure(max_attempts=3, delay=2.0)
    def send_feeder_data(
        self,
        feeder_id: str,
        feed_amount_g: Optional[float] = None,
        run_time_s: Optional[int] = None,
        status: str = "ok",
        notes: Optional[str] = None,
        timestamp: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        发送喂食机数据
        
        Args:
            feeder_id: 喂食机ID（使用设备名如 "AI"）
            feed_amount_g: 投喂量（克）
            run_time_s: 运行时长（秒）
            status: 状态（ok/warning/error）
            notes: 备注
            timestamp: Unix时间戳（毫秒），可选
            
        Returns:
            响应数据
        """
        endpoint = "/api/data/feeders"
        
        payload = {
            "feeder_id": feeder_id,
            "batch_id": settings.BATCH_ID,
            "pool_id": settings.POOL_ID,
            "status": status,
        }
        
        if feed_amount_g is not None:
            payload["feed_amount_g"] = feed_amount_g
        if run_time_s is not None:
            payload["run_time_s"] = run_time_s
        if notes:
            payload["notes"] = notes
        if timestamp:
            payload["timestamp"] = timestamp
        
        logger.info(f"上传喂食记录: {payload}")
        return self._post_json(endpoint, payload)
    
    def close(self):
        """关闭连接"""
        if self.session:
            self.session.close()
            logger.info("APIClient HTTP会话已关闭")


# 全局API客户端实例
_api_client: Optional[APIClient] = None


def get_api_client() -> APIClient:
    """获取API客户端单例"""
    global _api_client
    if _api_client is None:
        _api_client = APIClient()
    return _api_client


# 兼容简写
api_client = get_api_client()

