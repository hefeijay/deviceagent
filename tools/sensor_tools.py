"""传感器工具"""
from langchain_core.tools import tool
from services.sensor_service import sensor_service
from utils.logger import logger
import httpx


@tool
async def read_sensor_data(
    sensor_type: str,
    sensor_id: str = "default"
) -> str:
    """
    读取传感器数据
    
    Args:
        sensor_type: 传感器类型 (temperature/ph/oxygen/salinity)
        sensor_id: 传感器ID，默认default
        
    Returns:
        str: 传感器读数
    """
    logger.info(f"工具调用: read_sensor_data, type={sensor_type}, id={sensor_id}")
    
    valid_types = ['temperature', 'ph', 'oxygen', 'salinity']
    if sensor_type not in valid_types:
        return f"❌ 不支持的传感器类型: {sensor_type}，支持: {', '.join(valid_types)}"
    
    try:
        client = await sensor_service.get_client()
        
        response = await client.get(
            f"/api/v1/sensor/{sensor_type}/{sensor_id}"
        )
        response.raise_for_status()
        
        data = response.json()
        value = data.get('value')
        unit = data.get('unit')
        timestamp = data.get('timestamp')
        
        return (
            f"📊 传感器读数:\n"
            f"- 类型: {sensor_type}\n"
            f"- 数值: {value} {unit}\n"
            f"- 时间: {timestamp}"
        )
        
    except httpx.TimeoutException:
        logger.error(f"读取传感器超时: {sensor_type}/{sensor_id}")
        return f"❌ 读取传感器失败: 设备响应超时"
        
    except Exception as e:
        logger.error(f"读取传感器失败: {e}")
        return f"❌ 读取传感器失败: {str(e)}"


@tool
async def read_all_sensors(sensor_id: str = "default") -> str:
    """
    读取所有传感器数据
    
    Args:
        sensor_id: 传感器组ID，默认default
        
    Returns:
        str: 所有传感器读数
    """
    logger.info(f"工具调用: read_all_sensors, id={sensor_id}")
    
    try:
        client = await sensor_service.get_client()
        
        response = await client.get(f"/api/v1/sensor/all/{sensor_id}")
        response.raise_for_status()
        
        data = response.json()
        
        result = "📊 传感器综合读数:\n"
        for sensor_type, info in data.items():
            result += f"- {sensor_type}: {info.get('value')} {info.get('unit')}\n"
        
        return result
        
    except Exception as e:
        logger.error(f"读取所有传感器失败: {e}")
        return f"❌ 读取传感器失败: {str(e)}"

