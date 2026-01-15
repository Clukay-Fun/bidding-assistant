"""
语义搜索 API 路由
功能：暴露向量搜索服务为 REST API
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from app.db.database import get_db
from app.services.vector_search import (
    search_performances_by_vector,
    hybrid_search_performances,
    search_lawyers_by_resume,
)


# ============================================
# region 路由实例
# ============================================

router = APIRouter(prefix="/search", tags=["语义搜索"])

# endregion
# ============================================


# ============================================
# region 请求/响应模型
# ============================================

class SemanticSearchRequest(BaseModel):
    """语义搜索请求体"""
    query: str = Field(..., min_length=1, max_length=500, description="搜索查询文本")
    top_k: int = Field(10, ge=1, le=50, description="返回结果数量")
    mode: str = Field("hybrid", description="搜索模式: vector/keyword/hybrid")


class PerformanceSearchResult(BaseModel):
    """业绩搜索结果"""
    id: int
    file_name: str
    party_a: Optional[str] = None
    contract_type: Optional[str] = None
    amount: Optional[float] = None
    sign_date: Optional[str] = None
    project_detail: Optional[str] = None
    summary: Optional[str] = None
    score: float = Field(..., description="相似度得分（越高越相似）")

    class Config:
        from_attributes = True


class LawyerSearchResult(BaseModel):
    """律师搜索结果"""
    id: int
    name: str
    license_no: Optional[str] = None
    resume: Optional[str] = None
    score: float = Field(..., description="相似度得分")

    class Config:
        from_attributes = True


class SearchResponse(BaseModel):
    """搜索响应"""
    success: bool = True
    query: str
    mode: str
    total: int
    results: List[PerformanceSearchResult]


class LawyerSearchResponse(BaseModel):
    """律师搜索响应"""
    success: bool = True
    query: str
    total: int
    results: List[LawyerSearchResult]

# endregion
# ============================================


# ============================================
# region 业绩语义搜索
# ============================================

@router.post("/semantic/performances", response_model=SearchResponse)
async def search_performances_semantic(
    request: SemanticSearchRequest,
    db: Session = Depends(get_db),
):
    """
    业绩语义搜索
    
    - **query**: 搜索文本，如 "能源行业法律服务业绩"
    - **top_k**: 返回结果数量，默认 10
    - **mode**: 搜索模式
        - [vector](cci:1://file:///e:/.Program/Python/bidding-assistant/backend/app/services/vector_search.py:132:0-195:37): 纯向量搜索（理解语义）
        - [keyword](cci:1://file:///e:/.Program/Python/bidding-assistant/config/settings.py:135:0-152:25): 纯关键词搜索（精确匹配）
        - [hybrid](cci:1://file:///e:/.Program/Python/bidding-assistant/backend/app/services/vector_search.py:198:0-254:18): 混合搜索（推荐，兼顾语义和精确）
    """
    try:
        if request.mode == "vector":
            # 纯向量搜索
            results = search_performances_by_vector(
                db=db,
                query=request.query,
                top_k=request.top_k,
            )
            # 距离转相似度得分
            search_results = [
                PerformanceSearchResult(
                    id=perf.id,
                    file_name=perf.file_name,
                    party_a=perf.party_a,
                    contract_type=perf.contract_type,
                    amount=float(perf.amount) if perf.amount else None,
                    sign_date=str(perf.sign_date) if perf.sign_date else None,
                    project_detail=perf.project_detail[:200] if perf.project_detail else None,
                    summary=perf.summary[:200] if perf.summary else None,
                    score=round(1 - distance / 2, 4),  # 距离转相似度
                )
                for perf, distance in results
            ]
        
        elif request.mode == "keyword":
            # 纯关键词搜索
            from app.db.crud import search_performances
            results = search_performances(db=db, keyword=request.query)
            search_results = [
                PerformanceSearchResult(
                    id=perf.id,
                    file_name=perf.file_name,
                    party_a=perf.party_a,
                    contract_type=perf.contract_type,
                    amount=float(perf.amount) if perf.amount else None,
                    sign_date=str(perf.sign_date) if perf.sign_date else None,
                    project_detail=perf.project_detail[:200] if perf.project_detail else None,
                    summary=perf.summary[:200] if perf.summary else None,
                    score=1.0,  # 关键词命中给满分
                )
                for perf in results[:request.top_k]
            ]
        
        else:  # hybrid
            # 混合搜索
            results = hybrid_search_performances(
                db=db,
                query=request.query,
                top_k=request.top_k,
            )
            search_results = [
                PerformanceSearchResult(
                    id=perf.id,
                    file_name=perf.file_name,
                    party_a=perf.party_a,
                    contract_type=perf.contract_type,
                    amount=float(perf.amount) if perf.amount else None,
                    sign_date=str(perf.sign_date) if perf.sign_date else None,
                    project_detail=perf.project_detail[:200] if perf.project_detail else None,
                    summary=perf.summary[:200] if perf.summary else None,
                    score=round(score, 4),
                )
                for perf, score in results
            ]
        
        return SearchResponse(
            query=request.query,
            mode=request.mode,
            total=len(search_results),
            results=search_results,
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"搜索失败: {str(e)}")


@router.get("/semantic/performances")
async def search_performances_get(
    q: str = Query(..., min_length=1, description="搜索关键词"),
    top_k: int = Query(10, ge=1, le=50, description="返回数量"),
    mode: str = Query("hybrid", description="搜索模式"),
    db: Session = Depends(get_db),
):
    """
    业绩语义搜索（GET 方法，便于浏览器测试）
    """
    request = SemanticSearchRequest(query=q, top_k=top_k, mode=mode)
    return await search_performances_semantic(request, db)

# endregion
# ============================================


# ============================================
# region 律师语义搜索
# ============================================

@router.post("/semantic/lawyers", response_model=LawyerSearchResponse)
async def search_lawyers_semantic(
    request: SemanticSearchRequest,
    db: Session = Depends(get_db),
):
    """
    律师语义搜索（基于简历）
    
    - **query**: 需求描述，如 "有能源行业诉讼经验"
    - **top_k**: 返回结果数量
    """
    try:
        results = search_lawyers_by_resume(
            db=db,
            query=request.query,
            top_k=request.top_k,
        )
        
        search_results = [
            LawyerSearchResult(
                id=lawyer.id,
                name=lawyer.name,
                license_no=lawyer.license_no,
                resume=lawyer.resume[:300] if lawyer.resume else None,
                score=round(1 - distance / 2, 4),
            )
            for lawyer, distance in results
        ]
        
        return LawyerSearchResponse(
            query=request.query,
            total=len(search_results),
            results=search_results,
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"搜索失败: {str(e)}")

# endregion
# ============================================

# ============================================
# region 向量管理（开发/管理用）
# ============================================

@router.post("/admin/update-embeddings")
async def update_embeddings(
    batch_size: int = Query(10, ge=1, le=100, description="批量大小"),
    db: Session = Depends(get_db),
):
    """
    批量更新缺失向量的业绩（管理接口）
    
    用于首次导入数据后生成向量嵌入
    """
    from app.services.vector_search import batch_update_embeddings
    
    try:
        count = batch_update_embeddings(db, batch_size=batch_size)
        return {
            "success": True,
            "message": f"成功更新 {count} 条向量",
            "updated_count": count,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"更新失败: {str(e)}")


@router.get("/admin/stats")
async def get_search_stats(db: Session = Depends(get_db)):
    """
    获取搜索相关统计信息
    """
    from app.db.models import Performance, Lawyer
    from sqlalchemy import func
    
    # 统计业绩数据
    total_performances = db.query(func.count(Performance.id)).scalar()
    performances_with_embedding = db.query(func.count(Performance.id)).filter(
        Performance.embedding.isnot(None)
    ).scalar()
    
    # 统计律师数据
    total_lawyers = db.query(func.count(Lawyer.id)).scalar()
    lawyers_with_embedding = db.query(func.count(Lawyer.id)).filter(
        Lawyer.resume_embedding.isnot(None)
    ).scalar()
    
    return {
        "performances": {
            "total": total_performances,
            "with_embedding": performances_with_embedding,
            "without_embedding": total_performances - performances_with_embedding,
        },
        "lawyers": {
            "total": total_lawyers,
            "with_embedding": lawyers_with_embedding,
            "without_embedding": total_lawyers - lawyers_with_embedding,
        },
    }

# endregion
# ============================================