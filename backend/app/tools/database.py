"""
数据库工具
提供业绩、企业、律师的查询功能
"""

from typing import Optional, List
from sqlalchemy.orm import Session

from app.tools.decorators import tool
from app.db.database import SessionLocal
from app.db import crud


# ============================================
# region 辅助函数
# ============================================

def get_db_session() -> Session:
    """获取数据库会话（工具内部使用）"""
    return SessionLocal()

# endregion
# ============================================


# ============================================
# region 业绩查询工具
# ============================================

@tool(
    name="search_performances",
    description="搜索业绩合同，可按甲方、金额、年限、关键词等条件筛选",
    category="database"
)
def search_performances(
    party_a: Optional[str] = None,
    contract_type: Optional[str] = None,
    min_amount: Optional[float] = None,
    max_amount: Optional[float] = None,
    years: Optional[int] = None,
    keyword: Optional[str] = None,
) -> dict:
    """
    搜索业绩合同
    
    party_a: 甲方名称（模糊匹配）
    contract_type: 合同类型（委托代理合同/常年法律顾问合同/其他）
    min_amount: 最小合同金额（万元）
    max_amount: 最大合同金额（万元）
    years: 近N年的业绩
    keyword: 关键词搜索（匹配项目详情、摘要、甲方）
    """
    db = get_db_session()
    try:
        results = crud.search_performances(
            db=db,
            party_a=party_a,
            contract_type=contract_type,
            min_amount=min_amount,
            max_amount=max_amount,
            years=years,
            keyword=keyword,
        )
        
        return {
            "count": len(results),
            "performances": [p.to_dict() for p in results]
        }
    finally:
        db.close()


@tool(
    name="get_performance_detail",
    description="获取指定业绩的详细信息",
    category="database"
)
def get_performance_detail(performance_id: int) -> dict:
    """
    获取业绩详情
    
    performance_id: 业绩ID
    """
    db = get_db_session()
    try:
        result = crud.get_performance_by_id(db, performance_id)
        if result:
            return {"found": True, "performance": result.to_dict()}
        else:
            return {"found": False, "message": f"未找到ID为 {performance_id} 的业绩"}
    finally:
        db.close()

# endregion
# ============================================


# ============================================
# region 企业查询工具
# ============================================

@tool(
    name="search_enterprises",
    description="搜索企业信息，可按名称、行业、是否国企筛选",
    category="database"
)
def search_enterprises(
    name_keyword: Optional[str] = None,
    industry: Optional[str] = None,
    is_state_owned: Optional[bool] = None,
) -> dict:
    """
    搜索企业
    
    name_keyword: 企业名称关键词
    industry: 行业分类
    is_state_owned: 是否国企
    """
    db = get_db_session()
    try:
        results = crud.search_enterprises(
            db=db,
            name_keyword=name_keyword,
            industry=industry,
            is_state_owned=is_state_owned,
        )
        
        return {
            "count": len(results),
            "enterprises": [e.to_dict() for e in results]
        }
    finally:
        db.close()


@tool(
    name="get_enterprise_by_name",
    description="根据企业名称获取企业信息",
    category="database"
)
def get_enterprise_by_name(company_name: str) -> dict:
    """
    获取企业信息
    
    company_name: 企业名称（精确匹配）
    """
    db = get_db_session()
    try:
        result = crud.get_enterprise_by_name(db, company_name)
        if result:
            return {"found": True, "enterprise": result.to_dict()}
        else:
            return {"found": False, "message": f"未找到企业: {company_name}"}
    finally:
        db.close()

# endregion
# ============================================


# ============================================
# region 律师查询工具
# ============================================

@tool(
    name="search_lawyers",
    description="搜索律师信息",
    category="database"
)
def search_lawyers(
    name: Optional[str] = None,
    license_no: Optional[str] = None,
) -> dict:
    """
    搜索律师
    
    name: 律师姓名（模糊匹配）
    license_no: 执业证号
    """
    db = get_db_session()
    try:
        results = crud.search_lawyers(
            db=db,
            name=name,
            license_no=license_no,
        )
        
        return {
            "count": len(results),
            "lawyers": [l.to_dict() for l in results]
        }
    finally:
        db.close()


@tool(
    name="get_all_lawyers",
    description="获取所有律师列表",
    category="database"
)
def get_all_lawyers() -> dict:
    """获取所有律师"""
    db = get_db_session()
    try:
        results = crud.get_all_lawyers(db)
        return {
            "count": len(results),
            "lawyers": [l.to_dict() for l in results]
        }
    finally:
        db.close()

# endregion
# ============================================