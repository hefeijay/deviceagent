"""
定时任务调度器
参考: ai_japan/src/scheduler/task_scheduler.py
支持一次性任务和每天循环任务，使用系统配置时区
"""
import json
import time
import logging
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable
from concurrent.futures import ThreadPoolExecutor, Future

import pytz

from config.settings import settings

logger = logging.getLogger(__name__)


class ScheduledTask:
    """调度任务封装类"""
    
    def __init__(
        self,
        task_id: str,
        device_id: str,
        feed_count: int,
        scheduled_time: datetime,
        mode: str,
        execute_func: Callable,
        db_id: Optional[int] = None
    ):
        """
        初始化调度任务
        
        Args:
            task_id: 任务唯一标识
            device_id: 设备ID
            feed_count: 喂食份数
            scheduled_time: 计划执行时间（带时区）
            mode: 任务模式（once/daily）
            execute_func: 执行函数
            db_id: 数据库记录ID
        """
        self.task_id = task_id
        self.device_id = device_id
        self.feed_count = feed_count
        
        # 确保 scheduled_time 使用系统配置的时区
        tz = pytz.timezone(settings.TIMEZONE)
        if scheduled_time.tzinfo is None:
            self.scheduled_time = tz.localize(scheduled_time)
        else:
            self.scheduled_time = scheduled_time.astimezone(tz)
        
        self.mode = mode
        self.execute_func = execute_func
        self.db_id = db_id
        
        self.last_run: Optional[datetime] = None
        self.run_count = 0
        self.success_count = 0
        self.failure_count = 0
        self.last_error: Optional[str] = None
        self.is_running = False
        
        # 计算初始的 next_run（对于 daily 任务，如果今天时间已过则设为明天）
        self.next_run = self._calculate_initial_next_run(self.scheduled_time)
    
    def _calculate_initial_next_run(self, scheduled_time: datetime) -> Optional[datetime]:
        """计算初始的下次执行时间"""
        tz = pytz.timezone(settings.TIMEZONE)
        now = datetime.now(tz)
        
        # 确保 scheduled_time 的时区与系统时区一致
        if scheduled_time.tzinfo is None:
            scheduled_time = tz.localize(scheduled_time)
        else:
            scheduled_time = scheduled_time.astimezone(tz)
        
        if self.mode == "daily":
            # daily任务：如果今天时间已过，设为明天
            next_time = scheduled_time.replace(
                year=now.year,
                month=now.month,
                day=now.day
            )
            # 确保 next_time 也有正确的时区
            if next_time.tzinfo is None:
                next_time = tz.localize(next_time)
            else:
                next_time = next_time.astimezone(tz)
            
            if next_time <= now:
                next_time += timedelta(days=1)
            return next_time
        else:
            # once任务：直接使用设定的时间（已确保时区一致）
            return scheduled_time
    
    def calculate_next_run(self, tz) -> Optional[datetime]:
        """计算下次执行时间"""
        if self.mode == "once":
            # 一次性任务执行后不再执行
            return None
        elif self.mode == "daily":
            # 每天同一时间执行
            now = datetime.now(tz)
            
            # 确保 scheduled_time 的时区与系统时区一致
            scheduled_time = self.scheduled_time
            if scheduled_time.tzinfo is None:
                scheduled_time = tz.localize(scheduled_time)
            else:
                scheduled_time = scheduled_time.astimezone(tz)
            
            next_time = scheduled_time.replace(
                year=now.year,
                month=now.month,
                day=now.day
            )
            # 确保 next_time 也有正确的时区
            if next_time.tzinfo is None:
                next_time = tz.localize(next_time)
            else:
                next_time = next_time.astimezone(tz)
            
            # 如果今天的时间已过，则安排到明天
            if next_time <= now:
                next_time += timedelta(days=1)
            return next_time
        return None
    
    def get_info(self) -> Dict[str, Any]:
        """获取任务信息"""
        return {
            "task_id": self.task_id,
            "device_id": self.device_id,
            "feed_count": self.feed_count,
            "scheduled_time": self.scheduled_time.isoformat() if self.scheduled_time else None,
            "mode": self.mode,
            "next_run": self.next_run.isoformat() if self.next_run else None,
            "last_run": self.last_run.isoformat() if self.last_run else None,
            "run_count": self.run_count,
            "success_count": self.success_count,
            "failure_count": self.failure_count,
            "last_error": self.last_error,
            "is_running": self.is_running
        }


class TaskScheduler:
    """定时任务调度器"""
    
    _instance: Optional["TaskScheduler"] = None
    
    def __init__(self):
        """初始化调度器"""
        self.tasks: Dict[str, ScheduledTask] = {}
        self.running = False
        self.executor: Optional[ThreadPoolExecutor] = None
        self.scheduler_thread: Optional[threading.Thread] = None
        self.futures: Dict[str, Future] = {}
        self.stop_event = threading.Event()
        self.lock = threading.Lock()
        
        # 时区配置
        self.tz = pytz.timezone(settings.TIMEZONE)
        
        # 调度配置
        self.check_interval = settings.SCHEDULER_CHECK_INTERVAL
        self.max_workers = settings.SCHEDULER_MAX_WORKERS
        
        logger.info(f"定时任务调度器初始化完成，时区: {settings.TIMEZONE}")
    
    @classmethod
    def get_instance(cls) -> "TaskScheduler":
        """获取单例实例"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    def add_task(self, task: ScheduledTask) -> bool:
        """
        添加任务到调度器
        
        Args:
            task: 调度任务实例
            
        Returns:
            是否添加成功
        """
        with self.lock:
            if task.task_id in self.tasks:
                logger.warning(f"任务已存在: {task.task_id}")
                return False
            
            self.tasks[task.task_id] = task
            logger.info(f"✅ 任务添加成功: {task.task_id}, 计划执行时间: {task.next_run}")
            return True
    
    def remove_task(self, task_id: str) -> bool:
        """
        移除任务
        
        Args:
            task_id: 任务ID
            
        Returns:
            是否移除成功
        """
        with self.lock:
            if task_id not in self.tasks:
                logger.warning(f"任务不存在: {task_id}")
                return False
            
            # 如果任务正在执行，先取消
            if task_id in self.futures:
                future = self.futures[task_id]
                if not future.done():
                    future.cancel()
                del self.futures[task_id]
            
            del self.tasks[task_id]
            logger.info(f"✅ 任务移除成功: {task_id}")
            return True
    
    def update_task(self, task_id: str, **kwargs) -> bool:
        """
        更新任务
        
        Args:
            task_id: 任务ID
            **kwargs: 要更新的字段
            
        Returns:
            是否更新成功
        """
        with self.lock:
            if task_id not in self.tasks:
                logger.warning(f"任务不存在: {task_id}")
                return False
            
            task = self.tasks[task_id]
            
            if 'device_id' in kwargs:
                task.device_id = kwargs['device_id']
            if 'feed_count' in kwargs:
                task.feed_count = kwargs['feed_count']
            if 'scheduled_time' in kwargs:
                # 确保新的 scheduled_time 使用系统配置的时区
                new_scheduled_time = kwargs['scheduled_time']
                if new_scheduled_time.tzinfo is None:
                    task.scheduled_time = self.tz.localize(new_scheduled_time)
                else:
                    task.scheduled_time = new_scheduled_time.astimezone(self.tz)
                # 重新计算 next_run
                task.next_run = task._calculate_initial_next_run(task.scheduled_time)
            if 'mode' in kwargs:
                task.mode = kwargs['mode']
                # 如果模式改变，重新计算 next_run
                task.next_run = task._calculate_initial_next_run(task.scheduled_time)
            
            logger.info(f"✅ 任务更新成功: {task_id}")
            return True
    
    def get_task(self, task_id: str) -> Optional[ScheduledTask]:
        """获取任务"""
        return self.tasks.get(task_id)
    
    def get_all_tasks(self) -> List[Dict[str, Any]]:
        """获取所有任务信息"""
        with self.lock:
            return [task.get_info() for task in self.tasks.values()]
    
    def start(self):
        """启动调度器"""
        if self.running:
            logger.warning("调度器已在运行中")
            return
        
        self.running = True
        self.stop_event.clear()
        self.executor = ThreadPoolExecutor(max_workers=self.max_workers)
        
        # 启动调度线程
        self.scheduler_thread = threading.Thread(target=self._scheduler_loop, daemon=True)
        self.scheduler_thread.start()
        
        logger.info(f"🚀 定时任务调度器启动成功，检查间隔: {self.check_interval}秒")
    
    def stop(self):
        """停止调度器"""
        if not self.running:
            return
        
        logger.info("正在停止定时任务调度器...")
        self.running = False
        self.stop_event.set()
        
        # 等待调度线程结束
        if self.scheduler_thread and self.scheduler_thread.is_alive():
            self.scheduler_thread.join(timeout=5)
        
        # 关闭线程池
        if self.executor:
            self.executor.shutdown(wait=True)
        
        logger.info("✅ 定时任务调度器已停止")
    
    def _scheduler_loop(self):
        """调度器主循环"""
        logger.info("调度器主循环开始运行")
        
        while self.running:
            try:
                now = datetime.now(self.tz)
                
                # 检查需要执行的任务
                with self.lock:
                    for task_id, task in list(self.tasks.items()):
                        if (task.next_run and 
                            task.next_run <= now and 
                            not task.is_running):
                            
                            self._execute_task(task)
                
                # 清理已完成的Future
                self._cleanup_futures()
                
                # 等待检查间隔
                self.stop_event.wait(self.check_interval)
                
            except Exception as e:
                logger.error(f"调度器循环异常: {e}", exc_info=True)
                self.stop_event.wait(self.check_interval)
    
    def _execute_task(self, task: ScheduledTask):
        """执行任务"""
        task.is_running = True
        task.last_run = datetime.now(self.tz)
        task.run_count += 1
        
        logger.info(f"🔄 开始执行任务: {task.task_id}, 设备: {task.device_id}, 份数: {task.feed_count}")
        
        # 提交任务到线程池
        future = self.executor.submit(self._run_task, task)
        self.futures[task.task_id] = future
    
    def _run_task(self, task: ScheduledTask):
        """运行任务（在线程池中执行）"""
        try:
            # 执行喂食操作（传递mode参数）
            success = task.execute_func(task.device_id, task.feed_count, task.task_id, task.mode)
            
            if success:
                task.success_count += 1
                task.last_error = None
                logger.info(f"✅ 任务执行成功: {task.task_id}")
            else:
                task.failure_count += 1
                task.last_error = "执行返回失败"
                logger.error(f"❌ 任务执行失败: {task.task_id}")
            
        except Exception as e:
            task.failure_count += 1
            task.last_error = str(e)
            logger.error(f"❌ 任务执行异常: {task.task_id}, 错误: {e}", exc_info=True)
        
        finally:
            task.is_running = False
            
            # 计算下次执行时间
            task.next_run = task.calculate_next_run(self.tz)
            
            if task.next_run:
                logger.info(f"📅 任务 {task.task_id} 下次执行时间: {task.next_run}")
            else:
                # 一次性任务执行完毕，从调度器移除（但不从数据库删除）
                logger.info(f"📋 一次性任务 {task.task_id} 执行完毕")
                with self.lock:
                    if task.task_id in self.tasks:
                        del self.tasks[task.task_id]
    
    def _cleanup_futures(self):
        """清理已完成的Future对象"""
        completed_tasks = []
        for task_id, future in self.futures.items():
            if future.done():
                completed_tasks.append(task_id)
        
        for task_id in completed_tasks:
            del self.futures[task_id]


# 全局单例
_task_scheduler: Optional[TaskScheduler] = None


def get_task_scheduler() -> TaskScheduler:
    """获取任务调度器单例"""
    global _task_scheduler
    if _task_scheduler is None:
        _task_scheduler = TaskScheduler.get_instance()
    return _task_scheduler

