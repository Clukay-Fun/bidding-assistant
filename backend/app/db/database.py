"""
数据库连接管理
"""

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from app.config import DATABASE_URL


# ============================================
# region 数据库引擎
# ============================================

engine = create_engine(
    DATABASE_URL,
    echo=False,  # 生产环境设为 False，调试时可设为 True 查看 SQL
    pool_pre_ping=True,  # 连接前检测是否有效
)

# endregion
# ============================================


# ============================================
# region 会话工厂
# ============================================

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

# endregion
# ============================================


# ============================================
# region 模型基类
# ============================================

Base = declarative_base()

# endregion
# ============================================


# ============================================
# region 依赖注入
# ============================================

def get_db():
    """
    FastAPI 依赖注入函数
    
    用法：
        @app.get("/items")
        def read_items(db: Session = Depends(get_db)):
            ...
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# endregion
# ============================================