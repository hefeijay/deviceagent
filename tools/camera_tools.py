"""摄像头工具"""
from langchain_core.tools import tool
from services.camera_service import camera_service
from utils.logger import logger
import httpx


@tool
async def capture_image(camera_id: str = "default") -> str:
    """
    拍照
    
    Args:
        camera_id: 摄像头ID，默认default
        
    Returns:
        str: 拍照结果（图片URL）
    """
    logger.info(f"工具调用: capture_image, camera_id={camera_id}")
    
    try:
        client = await camera_service.get_client()
        
        # 发送拍照请求
        response = await client.post(
            "/api/v1/capture",
            json={"camera_id": camera_id}
        )
        response.raise_for_status()
        
        data = response.json()
        image_url = data.get('image_url')
        
        return (
            f"📷 拍照成功！\n"
            f"- 摄像头: {camera_id}\n"
            f"- 图片链接: {image_url}"
        )
        
    except httpx.TimeoutException:
        logger.error(f"拍照超时: camera_id={camera_id}")
        return f"❌ 拍照失败: 设备响应超时"
        
    except Exception as e:
        logger.error(f"拍照失败: {e}")
        return f"❌ 拍照失败: {str(e)}"


@tool
async def start_streaming(camera_id: str = "default") -> str:
    """
    开启视频流
    
    Args:
        camera_id: 摄像头ID，默认default
        
    Returns:
        str: 视频流地址
    """
    logger.info(f"工具调用: start_streaming, camera_id={camera_id}")
    
    try:
        client = await camera_service.get_client()
        
        response = await client.post(
            "/api/v1/stream/start",
            json={"camera_id": camera_id}
        )
        response.raise_for_status()
        
        data = response.json()
        stream_url = data.get('stream_url')
        
        return (
            f"🎥 视频流已开启！\n"
            f"- 摄像头: {camera_id}\n"
            f"- 流地址: {stream_url}"
        )
        
    except Exception as e:
        logger.error(f"开启视频流失败: {e}")
        return f"❌ 开启视频流失败: {str(e)}"


@tool
async def stop_streaming(camera_id: str = "default") -> str:
    """
    关闭视频流
    
    Args:
        camera_id: 摄像头ID，默认default
        
    Returns:
        str: 操作结果
    """
    logger.info(f"工具调用: stop_streaming, camera_id={camera_id}")
    
    try:
        client = await camera_service.get_client()
        
        response = await client.post(
            "/api/v1/stream/stop",
            json={"camera_id": camera_id}
        )
        response.raise_for_status()
        
        return f"✅ 视频流已关闭 ({camera_id})"
        
    except Exception as e:
        logger.error(f"关闭视频流失败: {e}")
        return f"❌ 关闭视频流失败: {str(e)}"

