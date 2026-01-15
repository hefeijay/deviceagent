"""
工作流构建器
"""
from langgraph.graph import StateGraph, START, END
from graph.schemas import DeviceState
from graph.nodes import expert_gate_node, device_router_node
from graph.device_nodes import feeder_agent_node, camera_agent_node, sensor_agent_node
from utils.logger import logger


def build_device_workflow():
    """
    构建设备管理工作流
    
    流程:
    START -> expert_gate_node -> device_router_node -> [设备节点] -> END
    """
    logger.info("构建设备管理工作流")
    
    # 创建状态图
    builder = StateGraph(DeviceState)
    
    # 添加节点
    builder.add_node("expert_gate_node", expert_gate_node)
    builder.add_node("device_router_node", device_router_node)
    builder.add_node("feeder_agent_node", feeder_agent_node)
    builder.add_node("camera_agent_node", camera_agent_node)
    builder.add_node("sensor_agent_node", sensor_agent_node)
    
    # 添加边
    # START -> 专家判断
    builder.add_edge(START, "expert_gate_node")
    
    # 设备节点 -> END
    builder.add_edge("feeder_agent_node", END)
    builder.add_edge("camera_agent_node", END)
    builder.add_edge("sensor_agent_node", END)
    
    # 编译工作流
    workflow = builder.compile()
    
    logger.info("设备管理工作流构建完成")
    
    return workflow

