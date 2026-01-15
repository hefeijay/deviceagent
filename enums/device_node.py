"""设备节点枚举"""
from enum import Enum
from dataclasses import dataclass
from typing import Optional


@dataclass
class NodeConfig:
    """节点配置"""
    node: str                      # 节点名称
    prompt: Optional[str] = None   # 提示词文件名
    model: Optional[str] = None    # 使用的模型


class DeviceNode(Enum):
    """设备节点枚举"""
    
    # 核心节点
    EXPERT_GATE = NodeConfig(
        node="expert_gate_node",
        prompt="expert_gate_prompt"
    )
    
    DEVICE_ROUTER = NodeConfig(
        node="device_router_node",
        prompt="device_router_prompt"
    )
    
    # 设备专家节点
    FEEDER_AGENT = NodeConfig(
        node="feeder_agent_node",
        prompt="feeder_agent_prompt"
    )
    
    CAMERA_AGENT = NodeConfig(
        node="camera_agent_node",
        prompt="camera_agent_prompt"
    )
    
    SENSOR_AGENT = NodeConfig(
        node="sensor_agent_node",
        prompt="sensor_agent_prompt"
    )
    
    def get_node(self) -> str:
        """获取节点名称"""
        return self.value.node
    
    def get_prompt(self) -> str:
        """获取提示词文件名"""
        if self.value.prompt:
            return self.value.prompt
        return self.value.node.replace("_node", "_prompt")
    
    def get_model(self) -> str:
        """获取模型名称"""
        from config.settings import settings
        if self.value.model:
            return self.value.model
        return settings.LLM_MODEL

