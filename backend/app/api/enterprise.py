"""
企业管理 API 路由
提供企业的增删改查接口
"""

from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db import crud
from app.schemas import (
    EnterpriseCreate,
    EnterpriseUpdate,
    EnterpriseResponse,
)


# ============================================
# region 路由定义
# ============================================

router = APIRouter(prefix="/enterprises", tags=["企业管理"])

# endregion
# ============================================


# ============================================
# region 查询接口
# ============================================

@router.get("/", response_model=List[EnterpriseResponse])
async def list_enterprises(
    skip: int = Query(0, ge=0, description="跳过记录数"),
    limit: int = Query(20, ge=1, le=100, description="返回记录数"),
    db: Session = Depends(get_db),
):
    """
    获取企业列表（分页）
    """
    from app.db.models import Enterprise
    
    enterprises = db.query(Enterprise).offset(skip).limit(limit).all()
    return enterprises


@router.get("/search", response_model=List[EnterpriseResponse])
async def search_enterprises(
    name_keyword: Optional[str] = Query(None, description="企业名称关键词"),
    industry: Optional[str] = Query(None, description="行业"),
    is_state_owned: Optional[bool] = Query(None, description="是否国企"),
    db: Session = Depends(get_db),
):
    """
    搜索企业（多条件）
    """
    enterprises = crud.search_enterprises(
        db=db,
        name_keyword=name_keyword,
        industry=industry,
        is_state_owned=is_state_owned,
    )
    return enterprises


@router.get("/by-code/{credit_code}", response_model=EnterpriseResponse)
async def get_enterprise_by_code(
    credit_code: str,
    db: Session = Depends(get_db),
):
    """
    根据统一社会信用代码获取企业
    """
    enterprise = crud.get_enterprise_by_credit_code(db, credit_code)
    if not enterprise:
        raise HTTPException(status_code=404, detail="企业不存在")
    return enterprise


@router.get("/by-name/{company_name}", response_model=EnterpriseResponse)
async def get_enterprise_by_name(
    company_name: str,
    db: Session = Depends(get_db),
):
    """
    根据企业名称获取企业（精确匹配）
    """
    enterprise = crud.get_enterprise_by_name(db, company_name)
    if not enterprise:
        raise HTTPException(status_code=404, detail="企业不存在")
    return enterprise

# endregion
# ============================================


# ============================================
# region 创建接口
# ============================================

@router.post("/", response_model=EnterpriseResponse, status_code=201)
async def create_enterprise(
    data: EnterpriseCreate,
    db: Session = Depends(get_db),
):
    """
    创建企业记录
    """
    # 检查信用代码是否已存在
    existing = crud.get_enterprise_by_credit_code(db, data.credit_code)
    if existing:
        raise HTTPException(status_code=400, detail="该信用代码已存在")
    
    enterprise = crud.create_enterprise(db, data)
    return enterprise

# endregion
# ============================================


# ============================================
# region 更新接口
# ============================================

@router.put("/{credit_code}", response_model=EnterpriseResponse)
async def update_enterprise(
    credit_code: str,
    data: EnterpriseUpdate,
    db: Session = Depends(get_db),
):
    """
    更新企业记录
    """
    enterprise = crud.update_enterprise(db, credit_code, data)
    if not enterprise:
        raise HTTPException(status_code=404, detail="企业不存在")
    return enterprise

# endregion
# ============================================


# ============================================
# region 删除接口
# ============================================

@router.delete("/{credit_code}")
async def delete_enterprise(
    credit_code: str,
    db: Session = Depends(get_db),
):
    """
    删除企业记录
    """
    success = crud.delete_enterprise(db, credit_code)
    if not success:
        raise HTTPException(status_code=404, detail="企业不存在")
    return {"message": "删除成功", "credit_code": credit_code}

# endregion
# ============================================


# ============================================
# region 统计接口
# ============================================

@router.get("/stats/summary")
async def get_enterprise_stats(db: Session = Depends(get_db)):
    """
    获取企业统计信息
    """
    from sqlalchemy import func
    from app.db.models import Enterprise
    
    # 总数
    total_count = db.query(func.count(Enterprise.credit_code)).scalar()
    
    # 国企数量
    state_owned_count = db.query(func.count(Enterprise.credit_code)).filter(
        Enterprise.is_state_owned == True
    ).scalar()
    
    # 按行业统计
    industry_stats = db.query(
        Enterprise.industry,
        func.count(Enterprise.credit_code).label("count"),
    ).group_by(Enterprise.industry).all()
    
    # 自动填充数量
    auto_filled_count = db.query(func.count(Enterprise.credit_code)).filter(
        Enterprise.auto_filled == True
    ).scalar()
    
    return {
        "total_count": total_count,
        "state_owned_count": state_owned_count,
        "auto_filled_count": auto_filled_count,
        "by_industry": [
            {
                "industry": item[0] or "未分类",
                "count": item[1],
            }
            for item in industry_stats
        ],
    }

# endregion
# ============================================