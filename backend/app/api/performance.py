"""
业绩管理 API 路由
提供业绩的增删改查接口
"""

from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db import crud
from app.schemas import (
    PerformanceCreate,
    PerformanceUpdate,
    PerformanceResponse,
)


# ============================================
# region 路由定义
# ============================================

router = APIRouter(prefix="/performances", tags=["业绩管理"])

# endregion
# ============================================

# ============================================
# region 统计接口
# ============================================

@router.get("/stats/summary")
async def get_performance_stats(db: Session = Depends(get_db)):
    """
    获取业绩统计信息
    """
    from sqlalchemy import func
    from app.db.models import Performance
    
    # 总数
    total_count = db.query(func.count(Performance.id)).scalar()
    
    # 总金额
    total_amount = db.query(func.sum(Performance.amount)).scalar() or 0
    
    # 按合同类型统计
    type_stats = db.query(
        Performance.contract_type,
        func.count(Performance.id).label("count"),
        func.sum(Performance.amount).label("amount"),
    ).group_by(Performance.contract_type).all()
    
    return {
        "total_count": total_count,
        "total_amount": float(total_amount),
        "by_type": [
            {
                "type": item[0] or "未分类",
                "count": item[1],
                "amount": float(item[2] or 0),
            }
            for item in type_stats
        ],
    }

# endregion
# ============================================

# ============================================
# region 查询接口
# ============================================

@router.get("/", response_model=List[PerformanceResponse])
async def list_performances(
    skip: int = Query(0, ge=0, description="跳过记录数"),
    limit: int = Query(20, ge=1, le=100, description="返回记录数"),
    db: Session = Depends(get_db),
):
    """
    获取业绩列表（分页）
    """
    performances = crud.get_all_performances(db, skip=skip, limit=limit)
    return performances


@router.get("/search", response_model=List[PerformanceResponse])
async def search_performances(
    party_a: Optional[str] = Query(None, description="甲方名称（模糊匹配）"),
    contract_type: Optional[str] = Query(None, description="合同类型"),
    min_amount: Optional[float] = Query(None, ge=0, description="最小金额"),
    max_amount: Optional[float] = Query(None, ge=0, description="最大金额"),
    years: Optional[int] = Query(None, ge=1, le=10, description="近N年"),
    keyword: Optional[str] = Query(None, description="关键词"),
    db: Session = Depends(get_db),
):
    """
    搜索业绩（多条件）
    """
    performances = crud.search_performances(
        db=db,
        party_a=party_a,
        contract_type=contract_type,
        min_amount=min_amount,
        max_amount=max_amount,
        years=years,
        keyword=keyword,
    )
    return performances


@router.get("/{performance_id}", response_model=PerformanceResponse)
async def get_performance(
    performance_id: int,
    db: Session = Depends(get_db),
):
    """
    获取单个业绩详情
    """
    performance = crud.get_performance_by_id(db, performance_id)
    if not performance:
        raise HTTPException(status_code=404, detail="业绩不存在")
    return performance

# endregion
# ============================================


# ============================================
# region 创建接口
# ============================================

@router.post("/", response_model=PerformanceResponse, status_code=201)
async def create_performance(
    data: PerformanceCreate,
    db: Session = Depends(get_db),
):
    """
    创建业绩记录
    """
    # 检查文件名是否已存在
    existing = crud.get_performance_by_filename(db, data.file_name)
    if existing:
        raise HTTPException(status_code=400, detail="该文件名已存在")
    
    performance = crud.create_performance(db, data)
    return performance

# endregion
# ============================================


# ============================================
# region 更新接口
# ============================================

@router.put("/{performance_id}", response_model=PerformanceResponse)
async def update_performance(
    performance_id: int,
    data: PerformanceUpdate,
    db: Session = Depends(get_db),
):
    """
    更新业绩记录
    """
    performance = crud.update_performance(db, performance_id, data)
    if not performance:
        raise HTTPException(status_code=404, detail="业绩不存在")
    return performance

# endregion
# ============================================


# ============================================
# region 删除接口
# ============================================

@router.delete("/{performance_id}")
async def delete_performance(
    performance_id: int,
    db: Session = Depends(get_db),
):
    """
    删除业绩记录
    """
    success = crud.delete_performance(db, performance_id)
    if not success:
        raise HTTPException(status_code=404, detail="业绩不存在")
    return {"message": "删除成功", "id": performance_id}

# endregion
# ============================================