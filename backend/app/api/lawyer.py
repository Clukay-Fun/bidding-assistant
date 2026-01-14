"""
律师管理 API 路由
提供律师的增删改查接口
"""

from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db import crud
from app.schemas import (
    LawyerCreate,
    LawyerUpdate,
    LawyerResponse,
)


# ============================================
# region 路由定义
# ============================================

router = APIRouter(prefix="/lawyers", tags=["律师管理"])

# endregion
# ============================================


# ============================================
# region 查询接口
# ============================================

@router.get("/", response_model=List[LawyerResponse])
async def list_lawyers(
    db: Session = Depends(get_db),
):
    """
    获取所有律师列表
    """
    lawyers = crud.get_all_lawyers(db)
    return lawyers


@router.get("/search", response_model=List[LawyerResponse])
async def search_lawyers(
    name: Optional[str] = Query(None, description="姓名（模糊匹配）"),
    license_no: Optional[str] = Query(None, description="执业证号"),
    db: Session = Depends(get_db),
):
    """
    搜索律师
    """
    lawyers = crud.search_lawyers(
        db=db,
        name=name,
        license_no=license_no,
    )
    return lawyers


@router.get("/{lawyer_id}", response_model=LawyerResponse)
async def get_lawyer(
    lawyer_id: int,
    db: Session = Depends(get_db),
):
    """
    获取单个律师详情
    """
    lawyer = crud.get_lawyer_by_id(db, lawyer_id)
    if not lawyer:
        raise HTTPException(status_code=404, detail="律师不存在")
    return lawyer


@router.get("/by-name/{name}", response_model=LawyerResponse)
async def get_lawyer_by_name(
    name: str,
    db: Session = Depends(get_db),
):
    """
    根据姓名获取律师（精确匹配）
    """
    lawyer = crud.get_lawyer_by_name(db, name)
    if not lawyer:
        raise HTTPException(status_code=404, detail="律师不存在")
    return lawyer

# endregion
# ============================================


# ============================================
# region 创建接口
# ============================================

@router.post("/", response_model=LawyerResponse, status_code=201)
async def create_lawyer(
    data: LawyerCreate,
    db: Session = Depends(get_db),
):
    """
    创建律师记录
    """
    # 检查姓名是否已存在（可选：允许同名）
    existing = crud.get_lawyer_by_name(db, data.name)
    if existing:
        raise HTTPException(status_code=400, detail="该律师已存在")
    
    lawyer = crud.create_lawyer(db, data)
    return lawyer

# endregion
# ============================================


# ============================================
# region 更新接口
# ============================================

@router.put("/{lawyer_id}", response_model=LawyerResponse)
async def update_lawyer(
    lawyer_id: int,
    data: LawyerUpdate,
    db: Session = Depends(get_db),
):
    """
    更新律师记录
    """
    lawyer = crud.update_lawyer(db, lawyer_id, data)
    if not lawyer:
        raise HTTPException(status_code=404, detail="律师不存在")
    return lawyer

# endregion
# ============================================


# ============================================
# region 删除接口
# ============================================

@router.delete("/{lawyer_id}")
async def delete_lawyer(
    lawyer_id: int,
    db: Session = Depends(get_db),
):
    """
    删除律师记录
    """
    success = crud.delete_lawyer(db, lawyer_id)
    if not success:
        raise HTTPException(status_code=404, detail="律师不存在")
    return {"message": "删除成功", "id": lawyer_id}

# endregion
# ============================================


# ============================================
# region 统计接口
# ============================================

@router.get("/stats/summary")
async def get_lawyer_stats(db: Session = Depends(get_db)):
    """
    获取律师统计信息
    """
    from sqlalchemy import func
    from app.db.models import Lawyer
    
    # 总数
    total_count = db.query(func.count(Lawyer.id)).scalar()
    
    # 有执业证号的数量
    with_license_count = db.query(func.count(Lawyer.id)).filter(
        Lawyer.license_no.isnot(None),
        Lawyer.license_no != "",
    ).scalar()
    
    # 有简历的数量
    with_resume_count = db.query(func.count(Lawyer.id)).filter(
        Lawyer.resume.isnot(None),
        Lawyer.resume != "",
    ).scalar()
    
    return {
        "total_count": total_count,
        "with_license_count": with_license_count,
        "with_resume_count": with_resume_count,
    }

# endregion
# ============================================