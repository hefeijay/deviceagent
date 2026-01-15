"""
核心节点实现
"""
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
    
    # 简单的关键词匹配路由
    query_lower = query.lower()
    
    # 识别设备类型
    if any(keyword in query_lower for keyword in ['喂食', '投喂', '饲料', 'feed']):
        device_type = DeviceType.FEEDER
        target_node = "feeder_agent_node"
    elif any(keyword in query_lower for keyword in ['拍照', '照片', '视频', '监控', 'camera', 'photo']):
        device_type = DeviceType.CAMERA
        target_node = "camera_agent_node"
    elif any(keyword in query_lower for keyword in ['温度', 'ph', '溶氧', '盐度', '水质', 'sensor']):
        device_type = DeviceType.SENSOR
        target_node = "sensor_agent_node"
    else:
        # 默认路由到喂食机
        device_type = DeviceType.FEEDER
        target_node = "feeder_agent_node"
    
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

