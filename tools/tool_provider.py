"""工具注册和管理"""
from enum import Enum
from dataclasses import dataclass
from typing import Callable, Any, List, Optional
from utils.logger import logger

# 导入所有工具
from tools.feeder_tools import (
    feed_device, 
    get_device_info,
    create_schedule_task,
    update_schedule_task,
    delete_schedule_task,
    list_schedule_tasks
)
from tools.expert_tools import consult_expert
from tools.camera_tools import capture_image, start_streaming, stop_streaming
from tools.sensor_tools import read_sensor_data, read_all_sensors


@dataclass
class ToolInfo:
    """工具信息"""
    name: str
    func: Callable[..., Any]
    category: str  # feeder, camera, sensor, expert


class DeviceToolFunction(Enum):
    """设备工具枚举"""
    
    # 专家咨询工具
    CONSULT_EXPERT = ToolInfo("consult_expert", consult_expert, "expert")
    
    # 喂食机工具 - 即时喂食
    FEED_DEVICE = ToolInfo("feed_device", feed_device, "feeder")
    # GET_DEVICE_STATUS = ToolInfo("get_device_status", get_device_status, "feeder")  # 暂时禁用：API响应问题
    GET_DEVICE_INFO = ToolInfo("get_device_info", get_device_info, "feeder")
    
    # 喂食机工具 - 定时任务
    CREATE_SCHEDULE_TASK = ToolInfo("create_schedule_task", create_schedule_task, "feeder")
    UPDATE_SCHEDULE_TASK = ToolInfo("update_schedule_task", update_schedule_task, "feeder")
    DELETE_SCHEDULE_TASK = ToolInfo("delete_schedule_task", delete_schedule_task, "feeder")
    LIST_SCHEDULE_TASKS = ToolInfo("list_schedule_tasks", list_schedule_tasks, "feeder")
    
    # # 摄像头工具
    # CAPTURE_IMAGE = ToolInfo("capture_image", capture_image, "camera")
    # START_STREAMING = ToolInfo("start_streaming", start_streaming, "camera")
    # STOP_STREAMING = ToolInfo("stop_streaming", stop_streaming, "camera")
    
    # # 传感器工具
    # READ_SENSOR_DATA = ToolInfo("read_sensor_data", read_sensor_data, "sensor")
    # READ_ALL_SENSORS = ToolInfo("read_all_sensors", read_all_sensors, "sensor")
    
    def get_name(self) -> str:
        """获取工具名称"""
        return self.value.name
    
    def get_func(self) -> Callable:
        """获取工具函数"""
        return self.value.func
    
    def get_category(self) -> str:
        """获取工具类别"""
        return self.value.category


class ToolRegistry:
    """工具注册表"""
    
    def __init__(self):
        self._tools = {}
        self._register_default_tools()
    
    def _register_default_tools(self):
        """注册所有默认工具"""
        for tool_enum in DeviceToolFunction:
            self._tools[tool_enum.get_name()] = tool_enum.get_func()
            logger.info(f"注册工具: {tool_enum.get_name()} ({tool_enum.get_category()})")
    
    def get_tool(self, name: str):
        """获取单个工具"""
        return self._tools.get(name)
    
    def get_tools_by_category(self, category: str) -> List[Any]:
        """按类别获取工具"""
        return [
            tool.get_func() 
            for tool in DeviceToolFunction 
            if tool.get_category() == category
        ]
    
    def get_tools_by_names(self, names: List[str]) -> List[Any]:
        """按名称列表获取工具"""
        tools = []
        for name in names:
            tool = self._tools.get(name)
            if tool:
                tools.append(tool)
            else:
                logger.warning(f"工具未找到: {name}")
        return tools
    
    def list_tools(self) -> List[str]:
        """列出所有工具名称"""
        return list(self._tools.keys())
    
    def list_categories(self) -> List[str]:
        """列出所有工具类别"""
        categories = set()
        for tool in DeviceToolFunction:
            categories.add(tool.get_category())
        return list(categories)


# 全局工具注册表实例
tool_registry = ToolRegistry()

