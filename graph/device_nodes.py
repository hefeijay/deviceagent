#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
设备专家节点实现 - 使用预创建的 Agent（性能优化）
"""
from typing import Literal
from langgraph.types import Command
from graph.schemas import DeviceState
from utils.logger import logger


async def feeder_agent_node(state: DeviceState) -> Command[Literal["__end__"]]:
    """喂食机专家节点 - 使用预创建的 Agent"""
    session_id = state["session_id"]
    logger.info(f"=== 进入喂食机专家节点 === [Session: {session_id}]")
    
    query = state["query"]
    expert_advice = state.get("expert_advice")
    event_queue = state.get("event_queue")  # ← 获取事件队列
    
    # 推送节点进入事件
    if event_queue:
        try:
            event_queue.put_nowait({
                "type": "node",
                "node": "feeder_agent_node",
                "message": "📋 进入喂食机专家节点"
            })
        except Exception as e:
            logger.error(f"推送node事件失败: {e}")
    
    # 动态获取设备列表（每次请求时刷新）
    devices_info = None
    try:
        from services.feeder_service import get_feeder_service
        feeder_service = get_feeder_service()
        
        # 推送设备查询事件
        if event_queue:
            event_queue.put_nowait({
                "type": "status",
                "message": "🔍 正在获取设备列表..."
            })
        
        devices = feeder_service.get_devices()
        
        if devices:
            device_lines = [f"- 设备名称: {dev.get('devName', '未知')}, 设备ID: {dev.get('devID', '未知')}"
                          for dev in devices]
            devices_info = "## 可用设备列表\n\n" + "\n".join(device_lines)
            logger.info(f"[Session: {session_id}] ✅ 已获取 {len(devices)} 个设备信息")
            
            # 推送设备发现事件
            if event_queue:
                event_queue.put_nowait({
                    "type": "devices_found",
                    "count": len(devices),
                    "message": f"✅ 找到 {len(devices)} 个设备"
                })
        else:
            logger.warning(f"[Session: {session_id}] ⚠️ 未能获取设备列表")
    except Exception as e:
        logger.error(f"[Session: {session_id}] ❌ 获取设备列表失败: {e}")
    
    try:
        # 使用预创建的 Agent 执行任务
        from graph.agent_manager import agent_manager
        
        logger.info(f"[Session: {session_id}] ReAct Agent 开始执行: {query[:50]}...")
        
        # 推送Agent开始事件
        if event_queue:
            event_queue.put_nowait({
                "type": "agent_start",
                "agent": "feeder_agent",
                "message": "🤖 喂食机Agent开始处理..."
            })
        
        result = await agent_manager.invoke_feeder_agent(
            query=query,
            devices_info=devices_info,
            expert_advice=expert_advice,
            event_queue=event_queue  # ← 传递事件队列
        )
        
        logger.info(f"[Session: {session_id}] ReAct Agent 执行完成")
        
        # 推送最终消息
        if event_queue and result.get("messages"):
            final_msg = result["messages"][0]
            if hasattr(final_msg, "content"):
                event_queue.put_nowait({
                    "type": "message",
                    "content": final_msg.content,
                    "source": "feeder_agent"
                })
        
        return Command(
            update={
                "result": result,
                "current_node": "feeder_agent_node",
                "messages": result.get("all_messages", [])
            },
            goto="__end__"
        )
        
    except Exception as e:
        logger.error(f"[Session: {session_id}] 喂食机节点失败: {e}", exc_info=True)
        
        # 推送错误事件
        if event_queue:
            event_queue.put_nowait({
                "type": "error",
                "error": str(e),
                "message": f"❌ 喂食机节点失败: {str(e)}"
            })
        
        return Command(
            update={
                "error": str(e),
                "result": {"success": False, "error": str(e)},
                "current_node": "feeder_agent_node"
            },
            goto="__end__"
        )


async def camera_agent_node(state: DeviceState) -> Command[Literal["__end__"]]:
    """摄像头专家节点 - 使用预创建的 Agent"""
    session_id = state["session_id"]
    logger.info(f"=== 进入摄像头专家节点 === [Session: {session_id}]")
    
    query = state["query"]
    
    try:
        # 使用预创建的 Agent 执行任务
        from graph.agent_manager import agent_manager
        
        logger.info(f"[Session: {session_id}] ReAct Agent 开始执行: {query[:50]}...")
        
        result = await agent_manager.invoke_camera_agent(query=query)
        
        logger.info(f"[Session: {session_id}] ReAct Agent 执行完成")
        
        return Command(
            update={
                "result": result,
                "current_node": "camera_agent_node",
                "messages": result.get("all_messages", [])
            },
            goto="__end__"
        )
        
    except Exception as e:
        logger.error(f"[Session: {session_id}] 摄像头节点失败: {e}", exc_info=True)
        return Command(
            update={
                "error": str(e),
                "result": {"success": False, "error": str(e)},
                "current_node": "camera_agent_node"
            },
            goto="__end__"
        )


async def sensor_agent_node(state: DeviceState) -> Command[Literal["__end__"]]:
    """传感器专家节点 - 使用预创建的 Agent"""
    session_id = state["session_id"]
    logger.info(f"=== 进入传感器专家节点 === [Session: {session_id}]")
    
    query = state["query"]
    
    try:
        # 使用预创建的 Agent 执行任务
        from graph.agent_manager import agent_manager
        
        logger.info(f"[Session: {session_id}] ReAct Agent 开始执行: {query[:50]}...")
        
        result = await agent_manager.invoke_sensor_agent(query=query)
        
        logger.info(f"[Session: {session_id}] ReAct Agent 执行完成")
        
        return Command(
            update={
                "result": result,
                "current_node": "sensor_agent_node",
                "messages": result.get("all_messages", [])
            },
            goto="__end__"
        )
        
    except Exception as e:
        logger.error(f"[Session: {session_id}] 传感器节点失败: {e}", exc_info=True)
        return Command(
            update={
                "error": str(e),
                "result": {"success": False, "error": str(e)},
                "current_node": "sensor_agent_node"
            },
            goto="__end__"
        )
