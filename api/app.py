"""
FastAPI应用主文件
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.device_api import router as device_router
from config.settings import settings
from utils.logger import logger
from services import feeder_service, camera_service, sensor_service

@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动
    logger.info(f"🚀 {settings.APP_NAME} v{settings.APP_VERSION} 启动")
    logger.info(f"环境: {'开发' if settings.DEBUG else '生产'}")
    
    # 1. 预初始化所有设备 Agent（最耗时，但只执行一次）
    from graph.agent_manager import agent_manager
    agent_manager.initialize()
    logger.info("✅ 设备 Agent 已预创建完成")
    
    # 2. 预构建工作流（启动时只构建一次）
    from graph.builder import build_device_workflow
    app.state.workflow = build_device_workflow()
    logger.info("✅ 工作流已预构建完成")
    
    yield
    
    # 关闭
    logger.info("关闭服务连接...")
    feeder_service.close()  # 同步方法
    await camera_service.close()
    await sensor_service.close()
    logger.info("👋 服务已关闭")


# 创建FastAPI应用
app = FastAPI(
    title=settings.APP_NAME,
    description="设备管理Agent服务 - 基于LangGraph的多设备控制系统",
    version=settings.APP_VERSION,
    lifespan=lifespan
)

# CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(device_router, prefix="/api/v1", tags=["设备管理"])


@app.get("/")
async def root():
    """根路径"""
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "running",
        "description": "设备管理Agent服务"
    }


@app.get("/health")
async def health_check():
    """健康检查"""
    return {
        "status": "healthy",
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION
    }

