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
    logger.info("=== 进入喂食机专家节点 ===")
    
    query = state["query"]
    expert_advice = state.get("expert_advice")
    
    # 动态获取设备列表（每次请求时刷新）
    devices_info = None
    try:
        from services.feeder_service import get_feeder_service
        feeder_service = get_feeder_service()
        devices = feeder_service.get_devices()
        
        if devices:
            device_lines = [f"- 设备名称: {dev.get('devName', '未知')}, 设备ID: {dev.get('devID', '未知')}"
                          for dev in devices]
            devices_info = "## 可用设备列表\n\n" + "\n".join(device_lines)
            logger.info(f"✅ 已获取 {len(devices)} 个设备信息")
        else:
            logger.warning("⚠️ 未能获取设备列表")
    except Exception as e:
        logger.error(f"❌ 获取设备列表失败: {e}")
    
    try:
        # 使用预创建的 Agent 执行任务
        from graph.agent_manager import agent_manager
        
        logger.info(f"ReAct Agent 开始执行: {query[:50]}...")
        
        result = await agent_manager.invoke_feeder_agent(
            query=query,
            devices_info=devices_info,
            expert_advice=expert_advice
        )
        
        logger.info(f"ReAct Agent 执行完成")
        
        return Command(
            update={
                "result": result,
                "current_node": "feeder_agent_node",
                "messages": result.get("all_messages", [])
            },
            goto="__end__"
        )
        
    except Exception as e:
        logger.error(f"喂食机节点失败: {e}", exc_info=True)
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
    logger.info("=== 进入摄像头专家节点 ===")
    
    query = state["query"]
    
    try:
        # 使用预创建的 Agent 执行任务
        from graph.agent_manager import agent_manager
        
        logger.info(f"ReAct Agent 开始执行: {query[:50]}...")
        
        result = await agent_manager.invoke_camera_agent(query=query)
        
        logger.info(f"ReAct Agent 执行完成")
        
        return Command(
            update={
                "result": result,
                "current_node": "camera_agent_node",
                "messages": result.get("all_messages", [])
            },
            goto="__end__"
        )
        
    except Exception as e:
        logger.error(f"摄像头节点失败: {e}", exc_info=True)
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
    logger.info("=== 进入传感器专家节点 ===")
    
    query = state["query"]
    
    try:
        # 使用预创建的 Agent 执行任务
        from graph.agent_manager import agent_manager
        
        logger.info(f"ReAct Agent 开始执行: {query[:50]}...")
        
        result = await agent_manager.invoke_sensor_agent(query=query)
        
        logger.info(f"ReAct Agent 执行完成")
        
        return Command(
            update={
                "result": result,
                "current_node": "sensor_agent_node",
                "messages": result.get("all_messages", [])
            },
            goto="__end__"
        )
        
    except Exception as e:
        logger.error(f"传感器节点失败: {e}", exc_info=True)
        return Command(
            update={
                "error": str(e),
                "result": {"success": False, "error": str(e)},
                "current_node": "sensor_agent_node"
            },
            goto="__end__"
        )
