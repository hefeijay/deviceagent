#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
喂食机工具函数
将喂食机服务包装成可供大模型调用的工具函数
包含：即时喂食、定时喂食任务管理（创建/修改/删除/查询）
"""
import logging
from datetime import datetime
from typing import Dict, Any, Optional

import pytz
from pydantic import BaseModel, Field
from langchain_core.tools import tool

from config.settings import settings

logger = logging.getLogger(__name__)

# 日本时区
JAPAN_TZ = pytz.timezone(settings.TIMEZONE)


# ==================== Pydantic Schemas ====================

class FeedDeviceInput(BaseModel):
    """喂食设备的输入参数"""
    device_id: str = Field(..., description="设备ID，必须指定，通过list_devices工具获取")
    feed_count: int = Field(default=1, description="喂食份数，每份约17g，范围1-10份")


class CreateScheduleTaskInput(BaseModel):
    """创建定时喂食任务的输入参数"""
    device_id: str = Field(..., description="设备ID")
    feed_count: int = Field(default=1, description="喂食份数，范围1-10")
    scheduled_time: str = Field(..., description="计划执行时间，如'2024-01-15T20:20:00'")
    mode: str = Field(default="once", description="once(一次性)或daily(每天循环)")


class UpdateScheduleTaskInput(BaseModel):
    """更新定时喂食任务的输入参数"""
    task_id: str = Field(..., description="任务ID")
    device_id: Optional[str] = Field(None, description="新的设备ID")
    feed_count: Optional[int] = Field(None, description="新的喂食份数")
    scheduled_time: Optional[str] = Field(None, description="新的执行时间")
    mode: Optional[str] = Field(None, description="新的任务模式")


class DeleteScheduleTaskInput(BaseModel):
    """删除定时喂食任务的输入参数"""
    task_id: str = Field(..., description="要删除的任务ID")


class ListScheduleTasksInput(BaseModel):
    """查询定时喂食任务列表的输入参数"""
    status: Optional[str] = Field(None, description="按状态筛选：pending/completed/failed/cancelled")
    device_id: Optional[str] = Field(None, description="按设备ID筛选")


class DeviceStatusInput(BaseModel):
    """查询设备状态的输入参数"""
    device_id: str = Field(..., description="设备ID，必须指定，通过list_devices工具获取")


class DeviceInfoInput(BaseModel):
    """查询设备信息的输入参数"""
    device_id: str = Field(..., description="设备ID，必须指定，通过list_devices工具获取")


@tool(args_schema=FeedDeviceInput)
def feed_device(**kwargs) -> Dict[str, Any]:
    """
    立即执行喂食操作（即时喂食）。
    注意：如果用户说"在某时某分"、"明天"、"每天"等包含时间的请求，应使用create_schedule_task创建定时任务，而不是此工具。
    此工具仅用于"现在喂"、"喂一下"等立即执行的请求。
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


# ==================== 定时喂食任务工具 ====================

@tool(args_schema=CreateScheduleTaskInput)
def create_schedule_task(**kwargs) -> Dict[str, Any]:
    """
    创建定时喂食任务。当用户说"在几点"、"下午三点"、"明天"、"每天"等包含时间的喂食请求时使用此工具。
    mode="once"为一次性定时任务，mode="daily"为每天循环任务。
    """
    try:
        device_id = kwargs.get('device_id')
        feed_count = kwargs.get('feed_count', 1)
        scheduled_time_str = kwargs.get('scheduled_time')
        mode = kwargs.get('mode', 'once')
        
        if not device_id:
            return {
                "success": False,
                "message": "❌ 缺少必需参数 device_id"
            }
        
        if not scheduled_time_str:
            return {
                "success": False,
                "message": "❌ 缺少必需参数 scheduled_time"
            }
        
        # 验证feed_count
        if feed_count <= 0 or feed_count > 10:
            return {
                "success": False,
                "message": f"❌ 喂食份数必须在1-10之间，当前: {feed_count}"
            }
        
        # 验证mode
        if mode not in ['once', 'daily']:
            return {
                "success": False,
                "message": f"❌ 任务模式必须是 'once' 或 'daily'，当前: {mode}"
            }
        
        # 解析时间
        try:
            scheduled_time = datetime.fromisoformat(scheduled_time_str)
            if scheduled_time.tzinfo is None:
                # 如果没有时区，假设是日本时间
                scheduled_time = JAPAN_TZ.localize(scheduled_time)
            else:
                # 转换为日本时区
                scheduled_time = scheduled_time.astimezone(JAPAN_TZ)
        except ValueError as e:
            return {
                "success": False,
                "message": f"❌ 时间格式错误: {scheduled_time_str}，请使用格式如 '2024-01-15T20:20:00'"
            }
        
        # 调用服务创建任务
        from services.schedule_service import get_schedule_service
        service = get_schedule_service()
        
        result = service.create_task(
            device_id=device_id,
            feed_count=feed_count,
            scheduled_time=scheduled_time,
            mode=mode
        )
        
        return result
        
    except Exception as e:
        logger.error(f"创建定时任务失败: {e}", exc_info=True)
        return {
            "success": False,
            "message": f"❌ 创建定时任务失败: {str(e)}"
        }


@tool(args_schema=UpdateScheduleTaskInput)
def update_schedule_task(**kwargs) -> Dict[str, Any]:
    """
    更新定时喂食任务。只能修改待执行状态的任务。
    """
    try:
        task_id = kwargs.get('task_id')
        
        if not task_id:
            return {
                "success": False,
                "message": "❌ 缺少必需参数 task_id"
            }
        
        # 构建更新参数
        update_params = {}
        
        if kwargs.get('device_id'):
            update_params['device_id'] = kwargs['device_id']
        
        if kwargs.get('feed_count') is not None:
            feed_count = kwargs['feed_count']
            if feed_count <= 0 or feed_count > 10:
                return {
                    "success": False,
                    "message": f"❌ 喂食份数必须在1-10之间，当前: {feed_count}"
                }
            update_params['feed_count'] = feed_count
        
        if kwargs.get('scheduled_time'):
            try:
                scheduled_time = datetime.fromisoformat(kwargs['scheduled_time'])
                if scheduled_time.tzinfo is None:
                    scheduled_time = JAPAN_TZ.localize(scheduled_time)
                else:
                    scheduled_time = scheduled_time.astimezone(JAPAN_TZ)
                update_params['scheduled_time'] = scheduled_time
            except ValueError as e:
                return {
                    "success": False,
                    "message": f"❌ 时间格式错误: {kwargs['scheduled_time']}"
                }
        
        if kwargs.get('mode'):
            if kwargs['mode'] not in ['once', 'daily']:
                return {
                    "success": False,
                    "message": f"❌ 任务模式必须是 'once' 或 'daily'"
                }
            update_params['mode'] = kwargs['mode']
        
        if not update_params:
            return {
                "success": False,
                "message": "❌ 没有提供要更新的参数"
            }
        
        # 调用服务更新任务
        from services.schedule_service import get_schedule_service
        service = get_schedule_service()
        
        result = service.update_task(task_id=task_id, **update_params)
        
        return result
        
    except Exception as e:
        logger.error(f"更新定时任务失败: {e}", exc_info=True)
        return {
            "success": False,
            "message": f"❌ 更新定时任务失败: {str(e)}"
        }


@tool(args_schema=DeleteScheduleTaskInput)
def delete_schedule_task(**kwargs) -> Dict[str, Any]:
    """
    删除定时喂食任务。删除后任务状态变为已取消。
    """
    try:
        task_id = kwargs.get('task_id')
        
        if not task_id:
            return {
                "success": False,
                "message": "❌ 缺少必需参数 task_id"
            }
        
        # 调用服务删除任务
        from services.schedule_service import get_schedule_service
        service = get_schedule_service()
        
        result = service.delete_task(task_id=task_id)
        
        return result
        
    except Exception as e:
        logger.error(f"删除定时任务失败: {e}", exc_info=True)
        return {
            "success": False,
            "message": f"❌ 删除定时任务失败: {str(e)}"
        }


@tool(args_schema=ListScheduleTasksInput)
def list_schedule_tasks(**kwargs) -> Dict[str, Any]:
    """
    查询定时喂食任务列表。可按状态或设备ID筛选。
    """
    try:
        status = kwargs.get('status')
        device_id = kwargs.get('device_id')
        
        # 调用服务查询任务
        from services.schedule_service import get_schedule_service
        service = get_schedule_service()
        
        result = service.list_tasks(status=status, device_id=device_id)
        
        return result
        
    except Exception as e:
        logger.error(f"查询定时任务列表失败: {e}", exc_info=True)
        return {
            "success": False,
            "tasks": [],
            "message": f"❌ 查询定时任务列表失败: {str(e)}"
        }


# 工具列表，用于绑定到 LLM
FEEDER_TOOLS = [
    feed_device,
    # get_device_status,  # 暂时禁用：API响应问题
    get_device_info,
    # 定时任务工具
    create_schedule_task,
    update_schedule_task,
    delete_schedule_task,
    list_schedule_tasks
]

