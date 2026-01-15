"""
传感器服务 - 连接管理器
职责：管理HTTP客户端、提供配置信息
"""
import httpx
import logging
from typing import Optional
from config.settings import settings

logger = logging.getLogger(__name__)


class SensorService:
    """传感器服务 - 连接管理器"""
    
    def __init__(self):
        """初始化配置"""
        self.base_url = settings.SENSOR_API_URL
        self.api_key = settings.SENSOR_API_KEY
        self.timeout = settings.SENSOR_TIMEOUT
        self._client: Optional[httpx.AsyncClient] = None
        logger.info(f"传感器服务初始化: {self.base_url}")
    
    async def get_client(self) -> httpx.AsyncClient:
        """
        获取HTTP客户端（单例、懒加载）
        供Tool层使用
        """
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=self.timeout,
                headers={
                    "Authorization": f"Bearer {self.api_key}" if self.api_key else "",
                    "Content-Type": "application/json"
                }
            )
            logger.debug("创建新的传感器HTTP客户端")
        return self._client
    
    async def close(self):
        """关闭连接"""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            logger.info("传感器HTTP客户端已关闭")


# 全局单例
sensor_service = SensorService()

