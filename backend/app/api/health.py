"""
健康检查路由
用于监控服务状态和数据库连接
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.db.database import get_db


# ============================================
# region 路由定义
# ============================================

router = APIRouter()

# endregion
# ============================================


# ============================================
# region 健康检查接口
# ============================================

@router.get("/health")
async def health_check():
    """
    基础健康检查
    返回服务运行状态
    """
    return {
        "status": "healthy",
        "service": "bidding-assistant-api",
    }


@router.get("/health/db")
async def database_health_check(db: Session = Depends(get_db)):
    """
    数据库健康检查
    验证数据库连接是否正常
    """
    try:
        # 执行简单查询测试连接
        db.execute(text("SELECT 1"))
        
        # 检查 pgvector 扩展
        result = db.execute(text("SELECT extversion FROM pg_extension WHERE extname = 'vector'"))
        pgvector_version = result.scalar()
        
        return {
            "status": "healthy",
            "database": "connected",
            "pgvector_version": pgvector_version,
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "database": "disconnected",
            "error": str(e),
        }


@router.get("/health/tables")
async def tables_health_check(db: Session = Depends(get_db)):
    """
    数据库表检查
    返回各表的记录数
    """
    try:
        # 查询各表记录数
        performances_count = db.execute(
            text("SELECT COUNT(*) FROM performances")
        ).scalar()
        
        enterprises_count = db.execute(
            text("SELECT COUNT(*) FROM enterprises")
        ).scalar()
        
        lawyers_count = db.execute(
            text("SELECT COUNT(*) FROM lawyers")
        ).scalar()
        
        return {
            "status": "healthy",
            "tables": {
                "performances": performances_count,
                "enterprises": enterprises_count,
                "lawyers": lawyers_count,
            }
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
        }

# endregion
# ============================================