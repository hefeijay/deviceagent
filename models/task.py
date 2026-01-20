"""
定时任务模型
复用现有的 tasks 表结构
"""
from datetime import datetime
from typing import Optional
from sqlalchemy import String, TIMESTAMP, text, Text
from sqlalchemy.orm import Mapped, mapped_column
from models.base import Base


class Task(Base):
    """定时任务表模型"""
    
    __tablename__ = "tasks"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True, init=False)
    
    # 任务唯一标识（UUID）
    task_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    
    # 任务类型标识，如 "定时投喂"
    topic: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    
    # 工具名称，如 "feed_device"
    tool_name: Mapped[str] = mapped_column(String(255), nullable=False)
    
    # 任务模式：once（一次性）/ daily（每天循环）
    mode: Mapped[str] = mapped_column(String(64), nullable=False)
    
    # 请求参数（JSON字符串）
    # 包含 device_id, feed_count, scheduled_time 等
    request: Mapped[str] = mapped_column(Text, nullable=False)
    
    # 任务状态：pending / running / completed / failed / cancelled
    status: Mapped[str] = mapped_column(String(64), nullable=False)
    
    # 执行结果（JSON字符串，可选）
    response: Mapped[Optional[str]] = mapped_column(Text, nullable=True, default=None)
    
    # 创建时间（自动填充）
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP, server_default=text("CURRENT_TIMESTAMP"), nullable=False, init=False
    )
    
    # 更新时间（自动更新）
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP,
        server_default=text("CURRENT_TIMESTAMP"),
        onupdate=text("CURRENT_TIMESTAMP"),
        nullable=False,
        init=False,
    )
    
    # 完成时间（可选）
    completed_at: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP, nullable=True, default=None)


class TaskTopic:
    """任务类型常量"""
    SCHEDULE_FEED = "定时投喂"      # 定时喂食
    SCHEDULE_CAMERA = "定时拍照"    # 定时拍照（未来扩展）
    SCHEDULE_SENSOR = "定时采集"    # 定时数据采集（未来扩展）


class TaskStatus:
    """任务状态常量"""
    PENDING = "pending"       # 等待执行
    RUNNING = "running"       # 正在执行
    COMPLETED = "completed"   # 执行完成
    FAILED = "failed"         # 执行失败
    CANCELLED = "cancelled"   # 已取消


class TaskMode:
    """任务模式常量"""
    ONCE = "once"     # 一次性任务
    DAILY = "daily"   # 每天循环

