#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
喂食机服务 - 封装IoT API调用
"""
import logging
import requests
from typing import Dict, Any, Optional, List
from config.settings import settings

logger = logging.getLogger(__name__)


class FeederService:
    """喂食机云端API封装"""
    
    def __init__(self):
        """初始化喂食机服务"""
        self.user_id = settings.AIJ_FEEDER_USER
        self.password = settings.AIJ_FEEDER_PASS
        self.base_url = settings.AIJ_FEEDER_BASE_URL
        self.timeout = settings.AIJ_FEEDER_TIMEOUT
        self.authkey: Optional[str] = None
        self._session = requests.Session()
        
        if not self.user_id or not self.password:
            logger.warning("未配置喂食机凭证（AIJ_FEEDER_USER/AIJ_FEEDER_PASS）")
        else:
            logger.info(f"喂食机服务初始化: user={self.user_id}, url={self.base_url}")
    
    def _post(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """发送POST请求"""
        try:
            resp = self._session.post(
                self.base_url, 
                json=payload, 
                verify=True, 
                timeout=self.timeout
            )
            return {
                "success": True, 
                "status_code": resp.status_code, 
                "data": resp.json()
            }
        except Exception as e:
            logger.error(f"API请求失败: {e}")
            return {"success": False, "error": str(e)}
    
    def login(self) -> bool:
        """登录获取authkey"""
        if not self.user_id or not self.password:
            logger.error("❌ 登录失败: 缺少用户名或密码配置（AIJ_FEEDER_USER/AIJ_FEEDER_PASS）")
            return False
            
        payload = {
            "msgType": 1000,
            "userID": self.user_id,
            "password": self.password,
        }
        logger.info(f"尝试登录喂食机: userID={self.user_id}")
        result = self._post(payload)
        
        if result.get("success"):
            data = result.get("data", {})
            status = data.get("status")
            logger.info(f"登录 API 响应: status={status}")
            
            if status == 1:
                self.authkey = data["data"][0]["authkey"]
                logger.info(f"✅ 喂食机登录成功: authkey={self.authkey[:10]}...")
                return True
            else:
                error_msg = data.get("msg") or data.get("message") or "未知错误"
                logger.error(f"❌ 登录失败: status={status}, 原因: {error_msg}")
                return False
        else:
            error = result.get("error", "未知错误")
            logger.error(f"❌ 登录请求失败: {error}")
            return False
    
    def feed(self, dev_id: str, count: int = 1) -> bool:
        """
        执行喂食操作
        
        Args:
            dev_id: 设备ID
            count: 喂食份数
        
        Returns:
            bool: 喂食是否成功
        """
        if not self.authkey:
            logger.info("未登录，尝试登录...")
            if not self.login():
                logger.error("登录失败，无法执行喂食操作")
                return False
        
        payload = {
            "msgType": 2001,
            "authkey": self.authkey,
            "userID": self.user_id,
            "devID": dev_id,
            "feedCount": count,
        }
        logger.info(f"发送喂食请求: devID={dev_id}, count={count}")
        result = self._post(payload)
        
        if result.get("success"):
            data = result.get("data", {})
            status = data.get("status")
            logger.info(f"API 响应: status={status}, data={data}")
            
            if status == 1:
                logger.info(f"✅ 喂食成功: {count}份 -> 设备 {dev_id}")
                return True
            else:
                error_msg = data.get("msg") or data.get("message") or "未知错误"
                logger.error(f"❌ 喂食失败: status={status}, 原因: {error_msg}, 完整响应: {data}")
                return False
        else:
            error = result.get("error", "未知错误")
            logger.error(f"❌ 喂食请求失败: {error}")
            return False
    
    def get_devices(self, page_index: int = 0, page_size: int = 50) -> List[Dict[str, Any]]:
        """获取设备列表"""
        if not self.authkey:
            logger.info("未登录，尝试登录...")
            if not self.login():
                logger.error("登录失败，无法获取设备列表")
                return []
        
        payload = {
            "msgType": 1401,
            "authkey": self.authkey,
            "userID": self.user_id,
            "pageIndex": page_index,
            "pageSize": page_size,
        }
        logger.info(f"请求获取设备列表: userID={self.user_id}, page={page_index}, size={page_size}")
        result = self._post(payload)
        
        if result.get("success"):
            data = result.get("data", {})
            status = data.get("status")
            
            if status == 1:
                devices = data.get("data", [])
                if isinstance(devices, list):
                    logger.info(f"✅ 获取设备列表成功: 共 {len(devices)} 个设备")
                    return devices
                else:
                    logger.warning("设备列表格式不正确")
                    return []
            else:
                error_msg = data.get("msg") or data.get("message") or "未知错误"
                logger.error(f"❌ 获取设备列表失败: status={status}, 原因: {error_msg}")
                return []
        else:
            error = result.get("error", "未知错误")
            logger.error(f"❌ 获取设备列表请求失败: {error}")
            return []
    
    def get_device_status(self, dev_id: str) -> Optional[Dict[str, Any]]:
        """
        获取设备状态
        
        Args:
            dev_id: 设备ID
        
        Returns:
            dict: 设备状态信息，包含 online, battery, leftover, feedAmount 等
        """
        if not self.authkey:
            logger.info("未登录，尝试登录...")
            if not self.login():
                logger.error("登录失败，无法获取设备状态")
                return None
        
        payload = {
            "msgType": 1402,  # 获取设备状态的消息类型
            "authkey": self.authkey,
            "userID": self.user_id,
            "devID": dev_id,
            "groupID": "",  # 必需参数，空字符串表示查询所有分组
            "pageIndex": 0,  # 分页参数
            "pageSize": 50,  # 分页大小
        }
        logger.info(f"请求获取设备状态: devID={dev_id}")
        result = self._post(payload)
        
        if result.get("success"):
            data = result.get("data", {})
            status = data.get("status")
            
            if status == 1:
                device_data = data.get("data", [])
                if device_data and isinstance(device_data, list) and len(device_data) > 0:
                    status_info = device_data[0]
                    logger.info(f"✅ 获取设备状态成功: {status_info}")
                    return status_info
                else:
                    logger.warning("设备状态数据为空")
                    return None
            else:
                error_msg = data.get("msg") or data.get("message") or "未知错误"
                logger.error(f"❌ 获取设备状态失败: status={status}, 原因: {error_msg}")
                return None
        else:
            error = result.get("error", "未知错误")
            logger.error(f"❌ 获取设备状态请求失败: {error}")
            return None
    
    def find_device_by_name(self, device_name: str) -> Optional[Dict[str, Any]]:
        """
        根据设备名称查找设备
        
        Args:
            device_name: 设备名称
        
        Returns:
            匹配的设备信息，如果找不到返回 None
        """
        devices = self.get_devices()
        if not devices:
            logger.warning("设备列表为空")
            return None
        
        device_name_lower = device_name.lower().strip()
        for device in devices:
            if device.get('devName', '').lower() == device_name_lower:
                logger.info(f"✅ 找到设备: {device}")
                return device
        
        logger.warning(f"⚠️ 未找到设备: {device_name}")
        return None
    
    def find_device(self, query: str) -> Dict[str, Any]:
        """
        根据用户输入查找设备
        
        Args:
            query: 用户输入的设备名称或ID
        
        Returns:
            匹配的设备信息，包含 devID 和 devName（找不到时返回默认设备）
        """
        devices = self.get_devices()
        if not devices:
            logger.warning("设备列表为空，使用默认设备")
            return {
                'devID': self.default_device_id,
                'devName': self.default_device_name
            }
        
        query_lower = query.lower().strip()
        
        # 精确匹配设备ID
        for device in devices:
            if device.get('devID') == query:
                logger.info(f"✅ 精确匹配设备ID: {device}")
                return device
        
        # 精确匹配设备名称
        for device in devices:
            if device.get('devName', '').lower() == query_lower:
                logger.info(f"✅ 精确匹配设备名称: {device}")
                return device
        
        # 模糊匹配设备名称
        for device in devices:
            if query_lower in device.get('devName', '').lower():
                logger.info(f"✅ 模糊匹配设备名称: {device}")
                return device
        
        logger.warning(f"⚠️ 未找到匹配的设备: {query}，使用默认设备")
        return {
            'devID': self.default_device_id,
            'devName': self.default_device_name
        }
    
    def get_default_device_id(self) -> str:
        """获取默认设备ID"""
        return self.default_device_id
    
    def get_default_device_name(self) -> str:
        """获取默认设备名称"""
        return self.default_device_name
    
    def close(self):
        """关闭连接"""
        if self._session:
            self._session.close()
            logger.info("喂食机HTTP会话已关闭")


# 全局单例
_feeder_service: Optional[FeederService] = None

def get_feeder_service() -> FeederService:
    """获取喂食机服务单例"""
    global _feeder_service
    if _feeder_service is None:
        _feeder_service = FeederService()
    return _feeder_service

# 兼容旧代码
feeder_service = get_feeder_service()

