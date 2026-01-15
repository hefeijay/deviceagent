"""设备类型枚举"""
from enum import Enum


class DeviceType(Enum):
    """设备类型"""
    
    FEEDER = "feeder"        # 喂食机
    CAMERA = "camera"        # 摄像头
    SENSOR = "sensor"        # 传感器
    UNKNOWN = "unknown"      # 未知设备
    
    @classmethod
    def from_str(cls, device_type: str) -> "DeviceType":
        """从字符串获取设备类型"""
        for dt in cls:
            if dt.value == device_type.lower():
                return dt
        return cls.UNKNOWN
    
    def get_type(self) -> str:
        """获取设备类型字符串"""
        return self.value

