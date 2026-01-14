"""
API 路由模块
"""

from app.api.health import router as health_router

__all__ = [
    "health_router",
]