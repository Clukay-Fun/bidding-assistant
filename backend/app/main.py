"""
FastAPI 应用主入口
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import BACKEND_DIR
from app.db.database import engine, Base


# ============================================
# region 生命周期管理
# ============================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    应用生命周期管理
    - 启动时：初始化数据库表
    - 关闭时：清理资源
    """
    # 启动时执行
    print("🚀 正在启动应用...")

    # 启用 pgvector 扩展（必须在创建表之前）
    from app.db.database import init_pgvector
    init_pgvector()
    
    # 创建数据库表（如果不存在）
    # 注意：生产环境建议使用 Alembic 迁移
    Base.metadata.create_all(bind=engine)
    print("✅ 数据库表已就绪")
    
    yield  # 应用运行中
    
    # 关闭时执行
    print("👋 应用正在关闭...")

# endregion
# ============================================


# ============================================
# region 创建应用实例
# ============================================

app = FastAPI(
    title="招投标助手 API",
    description="智能招投标助手系统后端服务",
    version="0.1.0",
    lifespan=lifespan,
)

# endregion
# ============================================


# ============================================
# region 中间件配置
# ============================================

# CORS 跨域配置（允许前端访问）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境应限制具体域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# endregion
# ============================================


# ============================================
# region 注册路由
# ============================================

# 健康检查路由
from app.api.health import router as health_router
app.include_router(health_router, tags=["健康检查"])

# 对话路由
from app.api.chat import router as chat_router
app.include_router(chat_router, prefix="/api/v1", tags=["对话"])

# 业绩管理路由
from app.api.performance import router as performance_router
app.include_router(performance_router, prefix="/api/v1", tags=["业绩管理"])

# 企业管理路由
from app.api.enterprise import router as enterprise_router
app.include_router(enterprise_router, prefix="/api/v1", tags=["企业管理"])

# 律师管理路由
from app.api.lawyer import router as lawyer_router
app.include_router(lawyer_router, prefix="/api/v1", tags=["律师管理"])

# 文件上传路由
from app.api.upload import router as upload_router
app.include_router(upload_router, prefix="/api/v1", tags=["文件上传"])

# 语义搜索路由
from app.api.search import router as search_router
app.include_router(search_router, prefix="/api/v1", tags=["语义搜索"])

# endregion
# ============================================


# ============================================
# region 根路由
# ============================================

@app.get("/")
async def root():
    """根路由 - API 欢迎信息"""
    return {
        "message": "欢迎使用招投标助手 API",
        "version": "0.1.0",
        "docs": "/docs",
    }

# endregion
# ============================================