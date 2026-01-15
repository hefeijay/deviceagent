"""操作状态枚举"""
from enum import Enum


class OperationStatus(Enum):
    """操作状态"""
    
    SUCCESS = "success"              # 成功
    FAILED = "failed"                # 失败
    PENDING = "pending"              # 待处理
    TIMEOUT = "timeout"              # 超时
    DEVICE_OFFLINE = "device_offline"  # 设备离线
    INVALID_PARAMS = "invalid_params"  # 参数错误
    
    def get_status(self) -> str:
        """获取状态字符串"""
        return self.value

