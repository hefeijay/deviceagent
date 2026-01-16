#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
喂食机工具函数
将喂食机服务包装成可供大模型调用的工具函数
"""
import logging
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field
from langchain_core.tools import tool

logger = logging.getLogger(__name__)


# 定义工具参数的 Pydantic schemas

class FeedDeviceInput(BaseModel):
    """喂食设备的输入参数"""
    device_id: str = Field(..., description="设备ID，必须指定，通过list_devices工具获取")
    feed_count: int = Field(default=1, description="喂食份数，每份约17g，范围1-10份")


class DeviceStatusInput(BaseModel):
    """查询设备状态的输入参数"""
    device_id: str = Field(..., description="设备ID，必须指定，通过list_devices工具获取")


class DeviceInfoInput(BaseModel):
    """查询设备信息的输入参数"""
    device_id: str = Field(..., description="设备ID，必须指定，通过list_devices工具获取")


@tool(args_schema=FeedDeviceInput)
def feed_device(**kwargs) -> Dict[str, Any]:
    """
    执行喂食操作。向设备发送喂食指令，每份约17g饲料。
    当用户要求喂食、投喂、给鱼喂食时使用此工具。
    必须提供device_id参数，请先使用list_devices工具获取设备ID。
    """
    try:
        # 从 kwargs 提取参数
        device_id = kwargs.get('device_id')
        feed_count = kwargs.get('feed_count', 1)
        
        if not device_id:
            return {
                "success": False,
                "message": "❌ 缺少必需参数 device_id，请先调用 list_devices 获取设备ID"
            }
        
        from services.feeder_service import get_feeder_service
        service = get_feeder_service()
        
        logger.info(f"执行喂食: device_id={device_id}, feed_count={feed_count}")
        
        # 验证feed_count
        if feed_count <= 0 or feed_count > 10:
            return {
                "success": False,
                "feed_count": feed_count,
                "device_id": device_id,
                "message": f"❌ 喂食份数必须在1-10之间，当前: {feed_count}"
            }
        
        # 执行喂食
        result = service.feed(device_id, feed_count)
        
        if result:
            feed_amount_g = feed_count * 17.0
            return {
                "success": True,
                "feed_count": feed_count,
                "device_id": device_id,
                "feed_amount_g": feed_amount_g,
                "message": f"✅ 成功喂食 {feed_count} 份（约 {feed_amount_g:.1f}g）"
            }
        else:
            return {
                "success": False,
                "feed_count": feed_count,
                "device_id": device_id,
                "message": f"❌ 喂食操作失败"
            }
            
    except Exception as e:
        logger.error(f"喂食工具执行失败: {e}", exc_info=True)
        return {
            "success": False,
            "message": f"❌ 喂食失败: {str(e)}"
        }


# @tool(args_schema=DeviceStatusInput)
# def get_device_status(**kwargs) -> Dict[str, Any]:
#     """
#     查询设备的实时状态信息，包括在线状态、电池电量、剩余饲料量、上次喂食份数等。
#     当用户询问设备状态、是否在线、电池电量、剩余饲料等情况时使用此工具。
#     必须提供device_id参数，请先使用list_devices工具获取设备ID。
#     
#     暂时禁用：云端 API msgType 1402 响应问题，导致请求卡住
#     """
#     try:
#         # 从 kwargs 提取参数
#         device_id = kwargs.get('device_id')
#         
#         if not device_id:
#             return {
#                 "success": False,
#                 "message": "❌ 缺少必需参数 device_id，请先调用 list_devices 获取设备ID"
#             }
#         
#         from services.feeder_service import get_feeder_service
#         service = get_feeder_service()
#         
#         status = service.get_device_status(device_id)
#         
#         if status:
#             # 格式化状态信息
#             status_info = []
#             if 'online' in status:
#                 status_info.append(f"在线状态: {'🟢 在线' if status['online'] else '🔴 离线'}")
#             if 'feedAmount' in status:
#                 status_info.append(f"上次喂食量: {status['feedAmount']}份")
#             if 'leftover' in status:
#                 status_info.append(f"剩余饲料: {status['leftover']}g")
#             if 'battery' in status:
#                 status_info.append(f"电池电量: {status['battery']}%")
#             
#             return {
#                 "success": True,
#                 "device_id": device_id,
#                 "status": status,
#                 "message": f"📊 设备状态:\n" + "\n".join(status_info)
#             }
#         else:
#             return {
#                 "success": False,
#                 "device_id": device_id,
#                 "status": {},
#                 "message": f"❌ 无法查询设备状态"
#             }
#     except Exception as e:
#         logger.error(f"查询设备状态失败: {e}", exc_info=True)
#         return {
#             "success": False,
#             "status": {},
#             "message": f"❌ 查询设备状态失败: {str(e)}"
#         }

@tool(args_schema=DeviceInfoInput)
def get_device_info(**kwargs) -> Dict[str, Any]:
    """
    获取设备的详细配置信息，包括设备名称、ID、固件版本、时区、网络类型等。
    当用户询问设备配置、固件版本、详细信息时使用此工具。
    必须提供device_id参数，请先使用list_devices工具获取设备ID。
    """
    try:
        # 从 kwargs 提取参数
        device_id = kwargs.get('device_id')
        
        if not device_id:
            return {
                "success": False,
                "message": "❌ 缺少必需参数 device_id，请先调用 list_devices 获取设备ID"
            }
        
        from services.feeder_service import get_feeder_service
        service = get_feeder_service()
        
        # 通过ID查找设备
        devices = service.get_devices()
        device = None
        if devices:
            for dev in devices:
                if dev.get('devID') == device_id:
                    device = dev
                    break
        
        if device:
            info_lines = []
            info_lines.append(f"设备名称: {device.get('devName', '未知')}")
            info_lines.append(f"设备ID: {device.get('devID', '未知')}")
            info_lines.append(f"设备类型: {device.get('devType', '未知')}")
            info_lines.append(f"固件版本: {device.get('devVersion', '未知')}")
            info_lines.append(f"时区: UTC+{device.get('devTimeZone', 0)}")
            info_lines.append(f"网络类型: {device.get('netType', '未知')}")
            
            return {
                "success": True,
                "device": device,
                "message": "📱 设备信息:\n" + "\n".join(info_lines)
            }
        else:
            return {
                "success": False,
                "device": None,
                "message": f"❌ 无法找到设备"
            }
    except Exception as e:
        logger.error(f"查询设备信息失败: {e}", exc_info=True)
        return {
            "success": False,
            "device": None,
            "message": f"❌ 查询设备信息失败: {str(e)}"
        }


# 工具列表，用于绑定到 LLM
FEEDER_TOOLS = [
    feed_device,
    # get_device_status,  # 暂时禁用：API响应问题
    get_device_info
]

