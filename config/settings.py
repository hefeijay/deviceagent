"""
配置管理
使用pydantic-settings管理环境变量
"""
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """应用配置"""
    
    # ========== 应用基础配置 ==========
    APP_NAME: str = "DeviceAgent"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    
    # ========== LLM配置 ==========
    LLM_BASE_URL: str
    LLM_API_KEY: str
    LLM_MODEL: str = "gpt-4"
    LLM_TEMPERATURE: float = 0.7
    
    # ========== 外部专家服务配置 ==========
    EXPERT_API_BASE_URL: str = "http://localhost:5003"
    EXPERT_API_KEY: Optional[str] = None
    EXPERT_API_TIMEOUT: int = 60
    
    # ========== 喂食机IoT API配置 ==========
    AIJ_FEEDER_USER: str = ""
    AIJ_FEEDER_PASS: str = ""
    AIJ_FEEDER_BASE_URL: str = "https://ffish.huaeran.cn:8081/commonRequest"
    AIJ_FEEDER_TIMEOUT: int = 15
    
    # ========== 摄像头硬件API配置 ==========
    CAMERA_API_URL: str = ""
    CAMERA_API_KEY: Optional[str] = None
    CAMERA_TIMEOUT: int = 30
    
    # ========== 传感器硬件API配置 ==========
    SENSOR_API_URL: str = ""
    SENSOR_API_KEY: Optional[str] = None
    SENSOR_TIMEOUT: int = 30
    
    # ========== 后端数据上传API配置 ==========
    BACKEND_API_BASE_URL: str = "http://8.216.33.92:5002"
    BACKEND_API_TIMEOUT: int = 30
    BATCH_ID: int = 2
    POOL_ID: str = "4"
    
    # ========== 日志配置 ==========
    LOG_LEVEL: str = "INFO"
    LOG_PATH: str = "./logs"
    
    # ========== MySQL数据库配置 ==========
    MYSQL_HOST: str = "rm-0iwx9y9q368yc877wbo.mysql.japan.rds.aliyuncs.com"
    MYSQL_PORT: int = 3306
    MYSQL_USER: str = "root"
    MYSQL_PASSWORD: str = "Root155017"
    MYSQL_DATABASE: str = "cognitive"
    
    # ========== 定时任务调度器配置 ==========
    SCHEDULER_CHECK_INTERVAL: int = 60  # 检查间隔（秒）
    SCHEDULER_MAX_WORKERS: int = 10     # 最大工作线程数
    
    # ========== 时区配置 ==========
    # TIMEZONE: str = "Asia/Tokyo"  # 日本时区
    TIMEZONE: str = "Asia/Shanghai"  # 中国时区
    
    @property
    def SQLALCHEMY_DATABASE_URI(self) -> str:
        """构建数据库连接URI"""
        return f"mysql+pymysql://{self.MYSQL_USER}:{self.MYSQL_PASSWORD}@{self.MYSQL_HOST}:{self.MYSQL_PORT}/{self.MYSQL_DATABASE}?charset=utf8mb4"
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


# 全局配置实例
settings = Settings()

