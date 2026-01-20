"""
核心节点实现
"""
import json
import re
from typing import Literal
from langchain_core.messages import HumanMessage, AIMessage
from langgraph.types import Command
from graph.schemas import DeviceState
from llms.llm_manager import llm_manager
from tools.tool_provider import tool_registry, DeviceToolFunction
from enums.device_node import DeviceNode
from enums.device_type import DeviceType
from utils.logger import logger


async def expert_gate_node(state: DeviceState) -> Command[Literal["device_router_node"]]:
    """
    专家判断节点
    判断是否需要咨询外部专家，并实时转发专家的流式输出
    """
    session_id = state["session_id"]
    logger.info(f"=== 进入专家判断节点 === [Session: {session_id}]")
    
    query = state["query"]
    messages = state.get("messages", [])
    event_queue = state.get("event_queue")  # ← 获取事件队列
    
    # 推送节点进入事件
    if event_queue:
        try:
            event_queue.put_nowait({
                "type": "node",
                "node": "expert_gate_node",
                "message": "📋 进入专家判断节点"
            })
        except Exception as e:
            logger.error(f"推送node事件失败: {e}")
    
    # 加载提示词
    system_prompt = llm_manager.load_prompt(DeviceNode.EXPERT_GATE.get_prompt())
    
    # 准备工具
    tools = [DeviceToolFunction.CONSULT_EXPERT.get_func()]
    
    # 构建消息
    if not messages:
        messages = [HumanMessage(content=query)]
    
    try:
        # 推送LLM判断事件
        if event_queue:
            event_queue.put_nowait({
                "type": "status",
                "message": "🤔 判断是否需要咨询专家..."
            })
        
        # 调用LLM判断
        response = await llm_manager.invoke_with_tools(
            messages=messages,
            tools=tools,
            system_prompt=system_prompt
        )
        
        # 检查是否调用了专家工具
        expert_advice = None
        if hasattr(response, 'tool_calls') and response.tool_calls:
            for tool_call in response.tool_calls:
                if tool_call['name'] == 'consult_expert':
                    # 直接使用 expert_service 的流式方法（支持事件队列）
                    from services.expert_service import expert_service
                    
                    # 提取参数
                    expert_query = tool_call['args'].get('query', query)
                    
                    # 使用流式咨询方法
                    result = await expert_service.consult_stream(
                        query=expert_query,
                        session_id=session_id,
                        event_queue=event_queue  # ← 传递事件队列
                    )
                    
                    if result.get("success"):
                        expert_advice = f"🧑‍🏫 专家建议:\n{result.get('answer', '')}"
                        logger.info(f"[Session: {session_id}] 专家建议: {expert_advice[:100]}...")
                    else:
                        error = result.get("error", "未知错误")
                        expert_advice = f"❌ 专家咨询失败: {error}"
                        logger.error(f"[Session: {session_id}] 专家咨询失败: {error}")
                    
                    break
        else:
            # 不需要咨询专家
            if event_queue:
                event_queue.put_nowait({
                    "type": "status",
                    "message": "ℹ️ 无需咨询专家，直接处理"
                })
        
        # 更新状态
        return Command(
            update={
                "expert_advice": expert_advice,
                "current_node": "expert_gate_node",
                "messages": messages + [response]
            },
            goto="device_router_node"
        )
        
    except Exception as e:
        logger.error(f"专家判断节点失败: {e}", exc_info=True)
        
        # 推送错误事件
        if event_queue:
            event_queue.put_nowait({
                "type": "error",
                "error": str(e),
                "message": f"❌ 专家判断节点失败: {str(e)}"
            })
        
        return Command(
            update={
                "error": str(e),
                "current_node": "expert_gate_node"
            },
            goto="device_router_node"
        )


async def device_router_node(state: DeviceState) -> Command[
    Literal["feeder_agent_node", "camera_agent_node", "sensor_agent_node", "__end__"]
]:
    """
    设备路由节点
    根据请求识别设备类型并路由
    """
    session_id = state["session_id"]
    logger.info(f"=== 进入设备路由节点 === [Session: {session_id}]")
    
    query = state["query"]
    expert_advice = state.get("expert_advice")
    event_queue = state.get("event_queue")  # ← 获取事件队列
    
    # 推送节点进入事件
    if event_queue:
        try:
            event_queue.put_nowait({
                "type": "node",
                "node": "device_router_node",
                "message": "📋 进入设备路由节点"
            })
        except Exception as e:
            logger.error(f"推送node事件失败: {e}")
    
    try:
        # 加载提示词
        system_prompt = llm_manager.load_prompt(DeviceNode.DEVICE_ROUTER.get_prompt())
        
        # 构建用户提示
        user_prompt = f"用户请求: {query}\n\n请根据用户请求识别设备类型并返回JSON格式的路由决策。"
        
        # 推送LLM判断事件
        if event_queue:
            try:
                event_queue.put_nowait({
                    "type": "status",
                    "message": "🤔 正在识别设备类型..."
                })
            except Exception as e:
                logger.error(f"推送status事件失败: {e}")
        
        # 调用LLM进行路由决策
        response_text = await llm_manager.invoke_simple(
            prompt=user_prompt,
            system_prompt=system_prompt
        )
        
        logger.info(f"[Session: {session_id}] LLM路由响应: {response_text[:200]}...")
        
        # 解析JSON响应
        device_type = DeviceType.FEEDER  # 默认值
        target_node = "feeder_agent_node"  # 默认值
        
        # 尝试从响应中提取JSON（支持嵌套JSON）
        json_start = response_text.find('{')
        json_end = response_text.rfind('}')
        
        if json_start != -1 and json_end != -1 and json_end > json_start:
            try:
                json_str = response_text[json_start:json_end + 1]
                routing_data = json.loads(json_str)
                
                target_node = routing_data.get("target_node", "feeder_agent_node")
                device_type_str = routing_data.get("device_type", "feeder")
                device_type = DeviceType.from_str(device_type_str)
                
                # 验证节点名称的有效性
                valid_nodes = ["feeder_agent_node", "camera_agent_node", "sensor_agent_node"]
                if target_node not in valid_nodes:
                    logger.warning(f"[Session: {session_id}] 无效的节点名称: {target_node}，使用默认路由")
                    target_node = "feeder_agent_node"
                    device_type = DeviceType.FEEDER
                
            except json.JSONDecodeError as e:
                logger.error(f"[Session: {session_id}] JSON解析失败: {e}，尝试从文本中提取")
                # JSON解析失败，继续尝试文本提取
                json_start = -1
        
        # 如果没有找到或解析JSON失败，尝试从文本中提取设备类型关键词
        if json_start == -1:
            logger.warning(f"[Session: {session_id}] 未找到有效的JSON格式响应，尝试从文本中提取设备类型")
            response_lower = response_text.lower()
            
            if "feeder" in response_lower or "喂食" in response_lower:
                device_type = DeviceType.FEEDER
                target_node = "feeder_agent_node"
            elif "camera" in response_lower or "拍照" in response_lower or "摄像" in response_lower:
                device_type = DeviceType.CAMERA
                target_node = "camera_agent_node"
            elif "sensor" in response_lower or "传感器" in response_lower or "水质" in response_lower:
                device_type = DeviceType.SENSOR
                target_node = "sensor_agent_node"
        
        logger.info(f"[Session: {session_id}] 识别设备类型: {device_type.value}, 路由到: {target_node}")
        
        # 推送路由决策事件
        if event_queue:
            try:
                event_queue.put_nowait({
                    "type": "routing",
                    "device_type": device_type.value,
                    "target_node": target_node,
                    "message": f"🔀 路由到: {device_type.value}"
                })
            except Exception as e:
                logger.error(f"推送routing事件失败: {e}")
        
        return Command(
            update={
                "device_type": device_type.value,
                "current_node": "device_router_node"
            },
            goto=target_node
        )
        
    except Exception as e:
        logger.error(f"[Session: {session_id}] 设备路由节点失败: {e}", exc_info=True)
        
        # 推送错误事件
        if event_queue:
            try:
                event_queue.put_nowait({
                    "type": "error",
                    "error": str(e),
                    "message": f"❌ 设备路由失败: {str(e)}"
                })
            except Exception as e2:
                logger.error(f"推送error事件失败: {e2}")
        
        # 错误时使用默认路由
        device_type = DeviceType.FEEDER
        target_node = "feeder_agent_node"
        
        logger.warning(f"[Session: {session_id}] 使用默认路由: {device_type.value} -> {target_node}")
        
        return Command(
            update={
                "device_type": device_type.value,
                "current_node": "device_router_node",
                "error": str(e)
            },
            goto=target_node
        )

