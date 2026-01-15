"""
设备管理API路由
"""
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, AsyncGenerator
from langchain_core.messages import HumanMessage
from utils.logger import logger
import json
import asyncio

router = APIRouter()


class DeviceRequest(BaseModel):
    """设备操作请求"""
    query: str = Field(..., description="用户请求内容")
    session_id: str = Field(..., description="会话ID（由主Agent传递）")
    context: Optional[Dict[str, Any]] = Field(None, description="上下文信息")


class DeviceResponse(BaseModel):
    """设备操作响应"""
    success: bool = Field(..., description="是否成功")
    session_id: str = Field(..., description="会话ID")
    result: Optional[Dict[str, Any]] = Field(None, description="执行结果")
    error: Optional[str] = Field(None, description="错误信息")
    device_type: Optional[str] = Field(None, description="设备类型")


@router.post("/chat", response_model=DeviceResponse)
async def chat(device_request: DeviceRequest, request: Request):
    """
    设备控制对话接口
    
    主Agent调用此接口，传入设备相关的任务请求
    """
    try:
        # 使用主Agent传递的会话ID
        session_id = device_request.session_id
        
        logger.info(f"[Session: {session_id}] 收到设备任务请求: {device_request.query[:100]}...")
        
        # 使用预构建的工作流（从 app.state 获取）
        workflow = request.app.state.workflow
        
        # 准备初始状态
        initial_state = {
            "query": device_request.query,
            "session_id": session_id,
            "messages": [HumanMessage(content=device_request.query)],
            "expert_advice": None,
            "device_type": None,
            "current_node": None,
            "result": None,
            "error": None
        }
        
        # 执行工作流
        final_state = await workflow.ainvoke(initial_state)
        
        # 提取结果
        success = final_state.get("error") is None
        result = final_state.get("result")
        error = final_state.get("error")
        device_type = final_state.get("device_type")
        
        logger.info(f"[Session: {session_id}] 任务执行完成: success={success}, device_type={device_type}")
        
        return DeviceResponse(
            success=success,
            session_id=session_id,
            result=result,
            error=error,
            device_type=device_type
        )
        
    except Exception as e:
        logger.error(f"执行设备任务失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/chat/stream")
async def chat_stream(device_request: DeviceRequest, request: Request):
    """
    设备控制对话接口（流式版本）
    
    返回 SSE (Server-Sent Events) 格式的流式响应
    支持完整的中间过程输出，包括：
    - 节点切换
    - 工具调用和结果
    - 专家咨询的完整流程
    - AI思考过程
    """
    async def event_generator() -> AsyncGenerator[str, None]:
        """生成 SSE 事件流"""
        try:
            session_id = device_request.session_id
            
            logger.info(f"[Session: {session_id}] 收到流式设备任务请求: {device_request.query[:100]}...")
            
            # 创建事件队列
            event_queue = asyncio.Queue()
            
            # 发送开始事件
            yield f"data: {json.dumps({'type': 'start', 'session_id': session_id, 'query': device_request.query}, ensure_ascii=False)}\n\n"
            
            # 使用预构建的工作流
            workflow = request.app.state.workflow
            
            # 准备初始状态（包含事件队列）
            initial_state = {
                "query": device_request.query,
                "session_id": session_id,
                "messages": [HumanMessage(content=device_request.query)],
                "expert_advice": None,
                "device_type": None,
                "current_node": None,
                "result": None,
                "error": None,
                "stream_mode": True,
                "event_queue": event_queue  # ← 传递事件队列
            }
            
            # 创建工作流执行任务
            workflow_task = asyncio.create_task(workflow.ainvoke(initial_state))
            
            # 同时监听事件队列和工作流完成
            workflow_done = False
            
            while not workflow_done or not event_queue.empty():
                try:
                    # 等待事件或超时
                    event = await asyncio.wait_for(event_queue.get(), timeout=0.1)
                    
                    # 发送事件
                    yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
                    
                except asyncio.TimeoutError:
                    # 超时，检查工作流是否完成
                    if workflow_task.done():
                        workflow_done = True
                        
                        try:
                            final_state = await workflow_task
                            
                            # 发送完成事件
                            success = final_state.get("error") is None
                            result = final_state.get("result")
                            error = final_state.get("error")
                            device_type = final_state.get("device_type")
                            
                            final_event = {
                                "type": "done",
                                "success": success,
                                "session_id": session_id,
                                "result": _serialize_event(result),
                                "error": error,
                                "device_type": device_type
                            }
                            
                            yield f"data: {json.dumps(final_event, ensure_ascii=False)}\n\n"
                            
                            logger.info(f"[Session: {session_id}] 流式任务执行完成: success={success}, device_type={device_type}")
                            
                        except Exception as e:
                            logger.error(f"工作流执行失败: {e}", exc_info=True)
                            error_event = {
                                "type": "error",
                                "error": str(e)
                            }
                            yield f"data: {json.dumps(error_event, ensure_ascii=False)}\n\n"
            
        except Exception as e:
            logger.error(f"流式执行设备任务失败: {e}", exc_info=True)
            error_event = {
                "type": "error",
                "error": str(e)
            }
            yield f"data: {json.dumps(error_event, ensure_ascii=False)}\n\n"
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


def _serialize_event(obj: Any) -> Any:
    """序列化事件对象，处理 LangChain 消息类型"""
    if obj is None:
        return None
    
    if isinstance(obj, dict):
        result = {}
        for k, v in obj.items():
            if k == "messages" and isinstance(v, list):
                # 序列化消息列表
                result[k] = [_serialize_message(msg) for msg in v]
            elif k == "all_messages" and isinstance(v, list):
                # all_messages 太长，只返回数量
                result[k + "_count"] = len(v)
            else:
                result[k] = _serialize_event(v)
        return result
    
    if isinstance(obj, list):
        return [_serialize_event(item) for item in obj]
    
    if hasattr(obj, "dict"):
        return obj.dict()
    
    if hasattr(obj, "content"):
        return _serialize_message(obj)
    
    return obj


def _serialize_message(msg: Any) -> Dict[str, Any]:
    """序列化 LangChain 消息对象"""
    if hasattr(msg, "content"):
        return {
            "type": getattr(msg, "type", "unknown"),
            "content": msg.content,
        }
    return str(msg)


@router.get("/device/status")
async def get_device_status():
    """
    获取设备服务状态
    """
    from tools.tool_provider import tool_registry
    
    return {
        "status": "running",
        "available_tools": tool_registry.list_tools(),
        "tool_categories": tool_registry.list_categories()
    }


@router.get("/device/tools")
async def list_device_tools():
    """
    列出所有可用的设备工具
    """
    from tools.tool_provider import tool_registry, DeviceToolFunction
    
    tools_info = []
    for tool_enum in DeviceToolFunction:
        tools_info.append({
            "name": tool_enum.get_name(),
            "category": tool_enum.get_category(),
        })
    
    return {
        "total": len(tools_info),
        "tools": tools_info
    }

