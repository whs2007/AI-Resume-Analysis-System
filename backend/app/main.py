"""AI 智能简历分析系统 - FastAPI 应用入口"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers import resume, match

# 日志配置
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

# 缓存服务实例（lifespan 中初始化）
cache_svc = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    global cache_svc

    # 启动时：初始化缓存连接
    from app.services.cache import CacheService
    cache_svc = CacheService(settings.redis_url)
    await cache_svc.connect()

    # 注入到 cache 模块供其他服务使用
    import app.services.cache as cache_mod
    cache_mod.cache_service = cache_svc

    logger.info("简历分析系统已启动")
    yield

    # 关闭时：断开缓存连接
    if cache_svc:
        await cache_svc.disconnect()
    logger.info("简历分析系统已关闭")


app = FastAPI(
    title="AI 智能简历分析系统",
    description="支持 PDF 简历解析、AI 关键信息提取、岗位匹配评分的 RESTful API",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS 配置（允许前端跨域调用）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(resume.router)
app.include_router(match.router)


@app.get("/api/v1/health", tags=["系统"])
async def health_check():
    """健康检查接口"""
    return {
        "status": "ok",
        "service": "AI 智能简历分析系统",
        "version": "1.0.0",
        "ai_enabled": bool(settings.dashscope_api_key),
        "cache_enabled": cache_svc.available if cache_svc else False,
    }


@app.get("/", tags=["系统"])
async def root():
    """根路径"""
    return {
        "message": "欢迎使用 AI 智能简历分析系统",
        "docs": "/docs",
        "health": "/api/v1/health",
    }
