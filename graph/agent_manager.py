"""
Agent 管理器 - 预创建和缓存所有设备 Agent
"""
from typing import Optional, Dict, Any
import asyncio
import json
from langchain.agents import create_agent
from langchain.agents.middleware import ToolCallLimitMiddleware
from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.messages import AIMessage

from llms.llm_manager import llm_manager
from tools.tool_provider import tool_registry
from enums.device_node import DeviceNode
from utils.logger import logger


class ToolLoggingCallback(BaseCallbackHandler):
    """自定义回调处理器，记录工具调用和返回结果，并支持流式推送"""
    
    def __init__(self, event_queue: Optional[asyncio.Queue] = None):
        """初始化回调处理器
        
        Args:
            event_queue: 可选的事件队列，用于流式推送
        """
        super().__init__()
        self.event_queue = event_queue
    
    def on_tool_start(self, serialized: dict, input_str: str, **kwargs) -> None:
        """工具开始执行时记录"""
        tool_name = serialized.get("name", "unknown")
        logger.info(f"🔧 开始调用工具: {tool_name}")
        logger.info(f"📥 工具输入: {input_str}")
        
        # 推送事件到队列
        if self.event_queue:
            try:
                # 解析输入参数
                try:
                    args = json.loads(input_str) if input_str else {}
                except:
                    args = {"raw": input_str}
                
                event = {
                    "type": "tool_call",
                    "tool": tool_name,
                    "args": args,
                    "message": f"🔧 调用工具: {tool_name}"
                }
                self.event_queue.put_nowait(event)
            except Exception as e:
                logger.error(f"推送tool_call事件失败: {e}")
    
    def on_tool_end(self, output, **kwargs) -> None:
        """工具执行完成时记录"""
        output_str = str(output.content) if hasattr(output, "content") else str(output)
        logger.info(f"📤 工具返回: {output_str[:200]}...")
        
        # 推送事件到队列
        if self.event_queue:
            try:
                # 尝试解析为JSON
                try:
                    result_data = json.loads(output_str)
                except:
                    result_data = {"raw": output_str[:500]}
                
                event = {
                    "type": "tool_result",
                    "result": result_data,
                    "message": f"📤 工具返回: {output_str[:100]}..."
                }
                self.event_queue.put_nowait(event)
            except Exception as e:
                logger.error(f"推送tool_result事件失败: {e}")


class DeviceAgentManager:
    """设备 Agent 管理器 - 单例模式"""
    
    _instance: Optional["DeviceAgentManager"] = None
    
    def __init__(self):
        """初始化所有设备 Agent"""
        self.feeder_agent = None
        self.camera_agent = None
        self.sensor_agent = None
        self._initialized = False
        
        logger.info("🤖 初始化设备 Agent 管理器...")
    
    @classmethod
    def get_instance(cls) -> "DeviceAgentManager":
        """获取单例实例"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    def initialize(self):
        """初始化所有 Agent（在应用启动时调用）"""
        if self._initialized:
            logger.warning("Agent 管理器已初始化，跳过")
            return
        
        logger.info("开始预创建所有设备 Agent...")
        
        # 创建 LLM（复用）
        llm = llm_manager.get_llm()
        
        # 配置工具调用限制中间件
        tool_limiter = ToolCallLimitMiddleware(
            thread_limit=20,
            run_limit=10,
            exit_behavior="continue"
        )
        
        # 1. 创建喂食机 Agent
        try:
            feeder_prompt = llm_manager.load_prompt(DeviceNode.FEEDER_AGENT.get_prompt())
            feeder_tools = [t for t in tool_registry.get_tools_by_category("feeder") 
                           if t.name != 'list_devices']
            
            self.feeder_agent = create_agent(
                model=llm,
                tools=feeder_tools,
                system_prompt=feeder_prompt,
                middleware=[tool_limiter]
            )
            logger.info(f"✅ 喂食机 Agent 创建完成（{len(feeder_tools)} 个工具）")
        except Exception as e:
            logger.error(f"❌ 创建喂食机 Agent 失败: {e}")
        
        # # 2. 创建摄像头 Agent
        # try:
        #     camera_prompt = llm_manager.load_prompt(DeviceNode.CAMERA_AGENT.get_prompt())
        #     camera_tools = tool_registry.get_tools_by_category("camera")
            
        #     self.camera_agent = create_agent(
        #         model=llm,
        #         tools=camera_tools,
        #         system_prompt=camera_prompt,
        #         middleware=[tool_limiter]
        #     )
        #     logger.info(f"✅ 摄像头 Agent 创建完成（{len(camera_tools)} 个工具）")
        # except Exception as e:
        #     logger.error(f"❌ 创建摄像头 Agent 失败: {e}")
        
        # # 3. 创建传感器 Agent
        # try:
        #     sensor_prompt = llm_manager.load_prompt(DeviceNode.SENSOR_AGENT.get_prompt())
        #     sensor_tools = tool_registry.get_tools_by_category("sensor")
            
        #     self.sensor_agent = create_agent(
        #         model=llm,
        #         tools=sensor_tools,
        #         system_prompt=sensor_prompt,
        #         middleware=[tool_limiter]
        #     )
        #     logger.info(f"✅ 传感器 Agent 创建完成（{len(sensor_tools)} 个工具）")
        # except Exception as e:
        #     logger.error(f"❌ 创建传感器 Agent 失败: {e}")
        
        # self._initialized = True
        # logger.info("🎉 所有设备 Agent 预创建完成！")
    
    async def invoke_feeder_agent(
        self,
        query: str,
        devices_info: Optional[str] = None,
        expert_advice: Optional[str] = None,
        event_queue: Optional[asyncio.Queue] = None
    ) -> Dict[str, Any]:
        """
        执行喂食机 Agent
        
        Args:
            query: 用户查询
            devices_info: 设备列表信息（动态注入）
            expert_advice: 专家建议（可选）
            event_queue: 事件队列（用于流式推送）
        
        Returns:
            执行结果
        """
        if not self.feeder_agent:
            raise RuntimeError("喂食机 Agent 未初始化")
        
        # 构建完整的用户消息（包含设备列表和专家建议）
        full_message = query
        
        if devices_info:
            full_message = f"{devices_info}\n\n用户请求：{query}"
        
        if expert_advice:
            full_message += f"\n\n专家建议：{expert_advice}"
        
        # 执行 Agent（传递事件队列）
        result = await self.feeder_agent.ainvoke(
            {"messages": [("user", full_message)]},
            config={"callbacks": [ToolLoggingCallback(event_queue)]}
        )
        
        # 提取最终回答
        messages = result.get("messages", [])
        final_response = None
        
        for msg in reversed(messages):
            if isinstance(msg, AIMessage) and msg.content:
                final_response = msg
                break
        
        if not final_response:
            logger.warning("⚠️ 没有找到有效的 AIMessage")
            final_response = AIMessage(content="操作已完成")
        
        return {
            "success": True,
            "messages": [final_response],
            "all_messages": messages
        }
    
    async def invoke_camera_agent(
        self,
        query: str,
        event_queue: Optional[asyncio.Queue] = None
    ) -> Dict[str, Any]:
        """执行摄像头 Agent"""
        if not self.camera_agent:
            raise RuntimeError("摄像头 Agent 未初始化")
        
        result = await self.camera_agent.ainvoke(
            {"messages": [("user", query)]},
            config={"callbacks": [ToolLoggingCallback(event_queue)]}
        )
        
        messages = result.get("messages", [])
        final_response = None
        
        for msg in reversed(messages):
            if isinstance(msg, AIMessage) and msg.content:
                final_response = msg
                break
        
        if not final_response:
            final_response = AIMessage(content="操作已完成")
        
        return {
            "success": True,
            "messages": [final_response],
            "all_messages": messages
        }
    
    async def invoke_sensor_agent(
        self,
        query: str,
        event_queue: Optional[asyncio.Queue] = None
    ) -> Dict[str, Any]:
        """执行传感器 Agent"""
        if not self.sensor_agent:
            raise RuntimeError("传感器 Agent 未初始化")
        
        result = await self.sensor_agent.ainvoke(
            {"messages": [("user", query)]},
            config={"callbacks": [ToolLoggingCallback(event_queue)]}
        )
        
        messages = result.get("messages", [])
        final_response = None
        
        for msg in reversed(messages):
            if isinstance(msg, AIMessage) and msg.content:
                final_response = msg
                break
        
        if not final_response:
            final_response = AIMessage(content="操作已完成")
        
        return {
            "success": True,
            "messages": [final_response],
            "all_messages": messages
        }


# 全局单例
agent_manager = DeviceAgentManager.get_instance()

