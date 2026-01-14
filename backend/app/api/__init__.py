"""
API 路由模块
"""

from app.api.health import router as health_router
from app.api.chat import router as chat_router
from app.api.performance import router as performance_router
from app.api.enterprise import router as enterprise_router
from app.api.lawyer import router as lawyer_router

__all__ = [
    "health_router",
    "chat_router",
    "performance_router",
    "enterprise_router",
    "lawyer_router",
]