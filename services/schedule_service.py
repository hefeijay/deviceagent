"""
定时任务管理服务
负责任务的CRUD操作、数据库持久化、与调度器交互
"""
import json
import uuid
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional

import pytz

from config.settings import settings
from database.db_session import db_session_factory
from models.task import Task, TaskTopic, TaskStatus, TaskMode
from scheduler.task_scheduler import get_task_scheduler, ScheduledTask

logger = logging.getLogger(__name__)


class ScheduleService:
    """定时任务管理服务"""
    
    def __init__(self):
        """初始化服务"""
        self.japan_tz = pytz.timezone(settings.TIMEZONE)
        logger.info("定时任务管理服务初始化完成")
    
    def _generate_task_id(self) -> str:
        """生成任务唯一ID"""
        return str(uuid.uuid4())
    
    def _execute_feed_task(self, device_id: str, feed_count: int, task_id: str, mode: str = TaskMode.ONCE) -> bool:
        """
        执行喂食任务
        
        Args:
            device_id: 设备ID
            feed_count: 喂食份数
            task_id: 任务ID
            mode: 任务模式（once/daily）
            
        Returns:
            是否执行成功
        """
        try:
            from services.feeder_service import get_feeder_service
            feeder_service = get_feeder_service()
            
            logger.info(f"🍽️ 执行定时喂食: task_id={task_id}, device_id={device_id}, feed_count={feed_count}, mode={mode}")
            
            # 执行喂食（会自动上传记录）
            result = feeder_service.feed(device_id, feed_count)
            
            # 根据模式决定状态更新
            if mode == TaskMode.DAILY:
                # daily任务：执行后保持pending状态，只记录执行结果
                self._update_task_execution_record(
                    task_id=task_id,
                    success=result,
                    device_id=device_id,
                    feed_count=feed_count
                )
            else:
                # once任务：执行后更新为completed或failed
                self._update_task_status(
                    task_id=task_id,
                    status=TaskStatus.COMPLETED if result else TaskStatus.FAILED,
                    response=json.dumps({
                        "success": result,
                        "device_id": device_id,
                        "feed_count": feed_count,
                        "executed_at": datetime.now(self.japan_tz).isoformat()
                    })
                )
            
            return result
            
        except Exception as e:
            logger.error(f"执行喂食任务失败: {e}", exc_info=True)
            
            # 更新数据库任务状态为失败（once任务才标记failed，daily任务只记录错误）
            if mode == TaskMode.DAILY:
                self._update_task_execution_record(
                    task_id=task_id,
                    success=False,
                    device_id=device_id,
                    feed_count=feed_count,
                    error=str(e)
                )
            else:
                self._update_task_status(
                    task_id=task_id,
                    status=TaskStatus.FAILED,
                    response=json.dumps({
                        "success": False,
                        "error": str(e),
                        "executed_at": datetime.now(self.japan_tz).isoformat()
                    })
                )
            
            return False
    
    def _update_task_execution_record(self, task_id: str, success: bool, device_id: str, feed_count: int, error: str = None):
        """更新daily任务的执行记录（不改变状态）"""
        try:
            with db_session_factory() as session:
                task = session.query(Task).filter(Task.task_id == task_id).first()
                if task:
                    # 读取现有的response，追加新的执行记录
                    existing_response = json.loads(task.response) if task.response else {"executions": []}
                    if "executions" not in existing_response:
                        existing_response = {"executions": []}
                    
                    # 添加本次执行记录
                    execution_record = {
                        "success": success,
                        "device_id": device_id,
                        "feed_count": feed_count,
                        "executed_at": datetime.now(self.japan_tz).isoformat()
                    }
                    if error:
                        execution_record["error"] = error
                    
                    existing_response["executions"].append(execution_record)
                    
                    # 只保留最近10次执行记录
                    if len(existing_response["executions"]) > 10:
                        existing_response["executions"] = existing_response["executions"][-10:]
                    
                    task.response = json.dumps(existing_response, ensure_ascii=False)
                    # 状态保持pending，不更新completed_at
                    session.commit()
                    logger.info(f"✅ daily任务执行记录已更新: {task_id}, success={success}")
        except Exception as e:
            logger.error(f"更新daily任务执行记录失败: {e}", exc_info=True)
    
    def _update_task_status(self, task_id: str, status: str, response: Optional[str] = None):
        """更新数据库中的任务状态"""
        try:
            with db_session_factory() as session:
                task = session.query(Task).filter(Task.task_id == task_id).first()
                if task:
                    task.status = status
                    if response:
                        task.response = response
                    if status == TaskStatus.COMPLETED:
                        task.completed_at = datetime.now(self.japan_tz)
                    session.commit()
                    logger.info(f"✅ 任务状态已更新: {task_id} -> {status}")
        except Exception as e:
            logger.error(f"更新任务状态失败: {e}", exc_info=True)
    
    def create_task(
        self,
        device_id: str,
        feed_count: int,
        scheduled_time: datetime,
        mode: str = TaskMode.ONCE
    ) -> Dict[str, Any]:
        """
        创建定时喂食任务
        
        Args:
            device_id: 设备ID
            feed_count: 喂食份数
            scheduled_time: 计划执行时间（带时区的datetime对象）
            mode: 任务模式（once/daily）
            
        Returns:
            创建结果
        """
        try:
            task_id = self._generate_task_id()
            
            # 确保时间带有日本时区
            if scheduled_time.tzinfo is None:
                scheduled_time = self.japan_tz.localize(scheduled_time)
            else:
                scheduled_time = scheduled_time.astimezone(self.japan_tz)
            
            # 检查时间是否在未来（一次性任务）
            now = datetime.now(self.japan_tz)
            if mode == TaskMode.ONCE and scheduled_time <= now:
                return {
                    "success": False,
                    "message": f"❌ 定时时间必须在未来，当前日本时间: {now.strftime('%Y-%m-%d %H:%M:%S')}"
                }
            
            # 构建请求参数
            request_data = {
                "device_id": device_id,
                "feed_count": feed_count,
                "scheduled_time": scheduled_time.isoformat()
            }
            
            # 保存到数据库
            with db_session_factory() as session:
                task = Task(
                    task_id=task_id,
                    topic=TaskTopic.SCHEDULE_FEED,
                    tool_name="feed_device",
                    mode=mode,
                    request=json.dumps(request_data, ensure_ascii=False),
                    status=TaskStatus.PENDING
                )
                session.add(task)
                session.commit()
                db_id = task.id
                logger.info(f"✅ 任务已保存到数据库: task_id={task_id}, db_id={db_id}")
            
            # 添加到调度器
            scheduler = get_task_scheduler()
            scheduled_task = ScheduledTask(
                task_id=task_id,
                device_id=device_id,
                feed_count=feed_count,
                scheduled_time=scheduled_time,
                mode=mode,
                execute_func=self._execute_feed_task,
                db_id=db_id
            )
            scheduler.add_task(scheduled_task)
            
            return {
                "success": True,
                "task_id": task_id,
                "device_id": device_id,
                "feed_count": feed_count,
                "scheduled_time": scheduled_time.strftime("%Y-%m-%d %H:%M:%S %Z"),
                "mode": mode,
                "message": f"✅ 定时喂食任务创建成功！\n📅 计划执行时间: {scheduled_time.strftime('%Y-%m-%d %H:%M')} (日本时间)\n🐟 设备: {device_id}\n🍽️ 喂食份数: {feed_count}份"
            }
            
        except Exception as e:
            logger.error(f"创建定时任务失败: {e}", exc_info=True)
            return {
                "success": False,
                "message": f"❌ 创建定时任务失败: {str(e)}"
            }
    
    def update_task(
        self,
        task_id: str,
        device_id: Optional[str] = None,
        feed_count: Optional[int] = None,
        scheduled_time: Optional[datetime] = None,
        mode: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        更新定时任务
        
        Args:
            task_id: 任务ID
            device_id: 新的设备ID（可选）
            feed_count: 新的喂食份数（可选）
            scheduled_time: 新的计划执行时间（可选）
            mode: 新的任务模式（可选）
            
        Returns:
            更新结果
        """
        try:
            with db_session_factory() as session:
                task = session.query(Task).filter(Task.task_id == task_id).first()
                
                if not task:
                    return {
                        "success": False,
                        "message": f"❌ 任务不存在: {task_id}"
                    }
                
                if task.status != TaskStatus.PENDING:
                    return {
                        "success": False,
                        "message": f"❌ 只能修改待执行的任务，当前状态: {task.status}"
                    }
                
                # 解析当前请求参数
                request_data = json.loads(task.request)
                
                # 更新参数
                if device_id is not None:
                    request_data["device_id"] = device_id
                if feed_count is not None:
                    request_data["feed_count"] = feed_count
                if scheduled_time is not None:
                    if scheduled_time.tzinfo is None:
                        scheduled_time = self.japan_tz.localize(scheduled_time)
                    else:
                        scheduled_time = scheduled_time.astimezone(self.japan_tz)
                    request_data["scheduled_time"] = scheduled_time.isoformat()
                if mode is not None:
                    task.mode = mode
                
                task.request = json.dumps(request_data, ensure_ascii=False)
                session.commit()
                
                # 更新调度器中的任务
                scheduler = get_task_scheduler()
                update_kwargs = {}
                if device_id is not None:
                    update_kwargs["device_id"] = device_id
                if feed_count is not None:
                    update_kwargs["feed_count"] = feed_count
                if scheduled_time is not None:
                    update_kwargs["scheduled_time"] = scheduled_time
                if mode is not None:
                    update_kwargs["mode"] = mode
                
                scheduler.update_task(task_id, **update_kwargs)
                
                logger.info(f"✅ 任务已更新: {task_id}")
                
                return {
                    "success": True,
                    "task_id": task_id,
                    "message": f"✅ 定时任务更新成功！\n任务ID: {task_id}"
                }
                
        except Exception as e:
            logger.error(f"更新定时任务失败: {e}", exc_info=True)
            return {
                "success": False,
                "message": f"❌ 更新定时任务失败: {str(e)}"
            }
    
    def delete_task(self, task_id: str) -> Dict[str, Any]:
        """
        删除定时任务
        
        Args:
            task_id: 任务ID
            
        Returns:
            删除结果
        """
        try:
            with db_session_factory() as session:
                task = session.query(Task).filter(Task.task_id == task_id).first()
                
                if not task:
                    return {
                        "success": False,
                        "message": f"❌ 任务不存在: {task_id}"
                    }
                
                # 更新状态为已取消
                task.status = TaskStatus.CANCELLED
                session.commit()
                
                # 从调度器移除
                scheduler = get_task_scheduler()
                scheduler.remove_task(task_id)
                
                logger.info(f"✅ 任务已删除: {task_id}")
                
                return {
                    "success": True,
                    "task_id": task_id,
                    "message": f"✅ 定时任务已删除\n任务ID: {task_id}"
                }
                
        except Exception as e:
            logger.error(f"删除定时任务失败: {e}", exc_info=True)
            return {
                "success": False,
                "message": f"❌ 删除定时任务失败: {str(e)}"
            }
    
    def get_task(self, task_id: str) -> Dict[str, Any]:
        """
        获取任务详情
        
        Args:
            task_id: 任务ID
            
        Returns:
            任务详情
        """
        try:
            with db_session_factory() as session:
                task = session.query(Task).filter(Task.task_id == task_id).first()
                
                if not task:
                    return {
                        "success": False,
                        "message": f"❌ 任务不存在: {task_id}"
                    }
                
                request_data = json.loads(task.request)
                
                return {
                    "success": True,
                    "task": {
                        "task_id": task.task_id,
                        "topic": task.topic,
                        "device_id": request_data.get("device_id"),
                        "feed_count": request_data.get("feed_count"),
                        "scheduled_time": request_data.get("scheduled_time"),
                        "mode": task.mode,
                        "status": task.status,
                        "created_at": task.created_at.isoformat() if task.created_at else None,
                        "completed_at": task.completed_at.isoformat() if task.completed_at else None
                    }
                }
                
        except Exception as e:
            logger.error(f"获取任务详情失败: {e}", exc_info=True)
            return {
                "success": False,
                "message": f"❌ 获取任务详情失败: {str(e)}"
            }
    
    def list_tasks(
        self,
        status: Optional[str] = None,
        device_id: Optional[str] = None,
        limit: int = 50
    ) -> Dict[str, Any]:
        """
        获取定时任务列表
        
        Args:
            status: 按状态筛选（可选）
            device_id: 按设备ID筛选（可选）
            limit: 返回数量限制
            
        Returns:
            任务列表
        """
        try:
            with db_session_factory() as session:
                query = session.query(Task).filter(
                    Task.topic == TaskTopic.SCHEDULE_FEED
                )
                
                if status:
                    query = query.filter(Task.status == status)
                
                tasks = query.order_by(Task.created_at.desc()).limit(limit).all()
                
                task_list = []
                for task in tasks:
                    request_data = json.loads(task.request)
                    
                    # 如果指定了device_id筛选
                    if device_id and request_data.get("device_id") != device_id:
                        continue
                    
                    task_list.append({
                        "task_id": task.task_id,
                        "device_id": request_data.get("device_id"),
                        "feed_count": request_data.get("feed_count"),
                        "scheduled_time": request_data.get("scheduled_time"),
                        "mode": task.mode,
                        "status": task.status,
                        "created_at": task.created_at.isoformat() if task.created_at else None
                    })
                
                # 构建消息
                if task_list:
                    msg_lines = [f"📋 定时喂食任务列表（共{len(task_list)}个）:\n"]
                    for i, t in enumerate(task_list, 1):
                        status_emoji = {
                            "pending": "⏳",
                            "running": "🔄",
                            "completed": "✅",
                            "failed": "❌",
                            "cancelled": "🚫"
                        }.get(t["status"], "❓")
                        
                        # 解析时间
                        try:
                            dt = datetime.fromisoformat(t["scheduled_time"])
                            time_str = dt.strftime("%Y-%m-%d %H:%M")
                        except:
                            time_str = t["scheduled_time"]
                        
                        msg_lines.append(
                            f"{i}. {status_emoji} 设备: {t['device_id']}, "
                            f"份数: {t['feed_count']}, "
                            f"时间: {time_str}, "
                            f"模式: {t['mode']}"
                        )
                        msg_lines.append(f"   ID: {t['task_id'][:8]}...")
                    message = "\n".join(msg_lines)
                else:
                    message = "📋 暂无定时喂食任务"
                
                return {
                    "success": True,
                    "count": len(task_list),
                    "tasks": task_list,
                    "message": message
                }
                
        except Exception as e:
            logger.error(f"获取任务列表失败: {e}", exc_info=True)
            return {
                "success": False,
                "tasks": [],
                "message": f"❌ 获取任务列表失败: {str(e)}"
            }
    
    def load_pending_tasks(self) -> int:
        """
        从数据库加载所有待执行的定时投喂任务到调度器
        
        Returns:
            加载的任务数量
        """
        try:
            with db_session_factory() as session:
                tasks = session.query(Task).filter(
                    Task.status == TaskStatus.PENDING,
                    Task.topic == TaskTopic.SCHEDULE_FEED
                ).all()
                
                scheduler = get_task_scheduler()
                loaded_count = 0
                
                for task in tasks:
                    try:
                        request_data = json.loads(task.request)
                        
                        # 解析计划执行时间
                        scheduled_time = datetime.fromisoformat(request_data["scheduled_time"])
                        if scheduled_time.tzinfo is None:
                            scheduled_time = self.japan_tz.localize(scheduled_time)
                        
                        now = datetime.now(self.japan_tz)
                        
                        # once任务时间已过，标记为失败
                        if task.mode == TaskMode.ONCE and scheduled_time <= now:
                            task.status = TaskStatus.FAILED
                            task.response = json.dumps({
                                "error": "任务时间已过",
                                "scheduled_time": scheduled_time.isoformat(),
                                "checked_at": now.isoformat()
                            })
                            session.commit()
                            logger.warning(f"⏰ 一次性任务时间已过，标记为失败: {task.task_id}")
                            continue
                        
                        # 创建调度任务（ScheduledTask会自动计算正确的next_run）
                        # daily任务如果今天时间已过会自动设为明天
                        scheduled_task = ScheduledTask(
                            task_id=task.task_id,
                            device_id=request_data["device_id"],
                            feed_count=request_data["feed_count"],
                            scheduled_time=scheduled_time,
                            mode=task.mode,
                            execute_func=self._execute_feed_task,
                            db_id=task.id
                        )
                        
                        scheduler.add_task(scheduled_task)
                        loaded_count += 1
                        logger.info(f"📅 任务已加载: {task.task_id}, next_run={scheduled_task.next_run}")
                        
                    except Exception as e:
                        logger.error(f"加载任务失败: {task.task_id}, 错误: {e}")
                
                logger.info(f"📋 从数据库加载了 {loaded_count} 个待执行的定时投喂任务")
                return loaded_count
                
        except Exception as e:
            logger.error(f"加载待执行任务失败: {e}", exc_info=True)
            return 0


# 全局单例
_schedule_service: Optional[ScheduleService] = None


def get_schedule_service() -> ScheduleService:
    """获取定时任务管理服务单例"""
    global _schedule_service
    if _schedule_service is None:
        _schedule_service = ScheduleService()
    return _schedule_service

