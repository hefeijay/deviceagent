"""
State Schema定义
"""
from typing import TypedDict, Optional, List, Dict, Any
from langchain_core.messages import BaseMessage


class DeviceState(TypedDict):
    """设备管理系统的State"""
    
    # 消息历史
    messages: List[BaseMessage]
    
    # 用户原始请求
    query: str
    
    # 会话ID
    session_id: str
    
    # 专家建议（如果有）
    expert_advice: Optional[str]
    
    # 设备类型
    device_type: Optional[str]
    
    # 当前节点
    current_node: Optional[str]
    
    # 执行结果
    result: Optional[Dict[str, Any]]
    
    # 错误信息
    error: Optional[str]

