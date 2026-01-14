"""
数据库 CRUD 操作
提供业绩、企业、律师的增删改查功能
使用 Pydantic Schema 进行输入验证，确保安全
"""

from datetime import datetime, timedelta
from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.db.models import Performance, Enterprise, Lawyer
from app.schemas.common import (
    PerformanceCreate, PerformanceUpdate,
    EnterpriseCreate, EnterpriseUpdate,
    LawyerCreate, LawyerUpdate,
)


# ============================================
# region 业绩表 CRUD
# ============================================

def create_performance(db: Session, data: PerformanceCreate) -> Performance:
    """
    创建业绩记录
    
    参数:
        db: 数据库会话
        data: 经过 Pydantic 验证的输入数据
    """
    performance = Performance(**data.model_dump(exclude_none=True))
    db.add(performance)
    db.commit()
    db.refresh(performance)
    return performance


def get_performance_by_id(db: Session, performance_id: int) -> Optional[Performance]:
    """根据ID获取业绩"""
    return db.query(Performance).filter(Performance.id == performance_id).first()


def get_performance_by_filename(db: Session, file_name: str) -> Optional[Performance]:
    """根据文件名获取业绩"""
    return db.query(Performance).filter(Performance.file_name == file_name).first()


def get_all_performances(db: Session, skip: int = 0, limit: int = 100) -> List[Performance]:
    """获取所有业绩（分页）"""
    return db.query(Performance).offset(skip).limit(limit).all()


def search_performances(
    db: Session,
    party_a: Optional[str] = None,
    contract_type: Optional[str] = None,
    min_amount: Optional[float] = None,
    max_amount: Optional[float] = None,
    years: Optional[int] = None,
    keyword: Optional[str] = None,
) -> List[Performance]:
    """
    多条件搜索业绩
    
    参数:
        party_a: 甲方名称（模糊匹配）
        contract_type: 合同类型
        min_amount: 最小金额
        max_amount: 最大金额
        years: 近N年
        keyword: 关键词（搜索项目详情和摘要）
    """
    query = db.query(Performance)
    
    # 甲方名称模糊匹配
    if party_a:
        query = query.filter(Performance.party_a.ilike(f"%{party_a}%"))
    
    # 合同类型
    if contract_type:
        query = query.filter(Performance.contract_type == contract_type)
    
    # 金额范围
    if min_amount is not None:
        query = query.filter(Performance.amount >= min_amount)
    if max_amount is not None:
        query = query.filter(Performance.amount <= max_amount)
    
    # 时间范围（近N年）
    if years:
        cutoff_date = datetime.now() - timedelta(days=years * 365)
        query = query.filter(Performance.sign_date >= cutoff_date.date())
    
    # 关键词搜索
    if keyword:
        query = query.filter(
            or_(
                Performance.project_detail.ilike(f"%{keyword}%"),
                Performance.summary.ilike(f"%{keyword}%"),
                Performance.party_a.ilike(f"%{keyword}%"),
            )
        )
    
    return query.all()


def update_performance(
    db: Session, 
    performance_id: int, 
    data: PerformanceUpdate
) -> Optional[Performance]:
    """
    更新业绩记录
    
    参数:
        db: 数据库会话
        performance_id: 业绩ID
        data: 经过 Pydantic 验证的更新数据
    """
    performance = get_performance_by_id(db, performance_id)
    if not performance:
        return None
    
    # 只更新非 None 的字段
    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(performance, key, value)
    
    performance.updated_at = datetime.now()
    db.commit()
    db.refresh(performance)
    return performance


def delete_performance(db: Session, performance_id: int) -> bool:
    """删除业绩记录"""
    performance = get_performance_by_id(db, performance_id)
    if performance:
        db.delete(performance)
        db.commit()
        return True
    return False

# endregion
# ============================================


# ============================================
# region 企业表 CRUD
# ============================================

def create_enterprise(db: Session, data: EnterpriseCreate) -> Enterprise:
    """
    创建企业记录
    
    参数:
        db: 数据库会话
        data: 经过 Pydantic 验证的输入数据
    """
    enterprise = Enterprise(**data.model_dump(exclude_none=True))
    db.add(enterprise)
    db.commit()
    db.refresh(enterprise)
    return enterprise


def get_enterprise_by_credit_code(db: Session, credit_code: str) -> Optional[Enterprise]:
    """根据统一社会信用代码获取企业"""
    return db.query(Enterprise).filter(Enterprise.credit_code == credit_code).first()


def get_enterprise_by_name(db: Session, company_name: str) -> Optional[Enterprise]:
    """根据企业名称获取企业（精确匹配）"""
    return db.query(Enterprise).filter(Enterprise.company_name == company_name).first()


def search_enterprises(
    db: Session,
    name_keyword: Optional[str] = None,
    industry: Optional[str] = None,
    is_state_owned: Optional[bool] = None,
) -> List[Enterprise]:
    """
    搜索企业
    
    参数:
        name_keyword: 企业名称关键词
        industry: 行业
        is_state_owned: 是否国企
    """
    query = db.query(Enterprise)
    
    if name_keyword:
        query = query.filter(Enterprise.company_name.ilike(f"%{name_keyword}%"))
    
    if industry:
        query = query.filter(Enterprise.industry == industry)
    
    if is_state_owned is not None:
        query = query.filter(Enterprise.is_state_owned == is_state_owned)
    
    return query.all()


def update_enterprise(
    db: Session, 
    credit_code: str, 
    data: EnterpriseUpdate
) -> Optional[Enterprise]:
    """
    更新企业记录
    
    参数:
        db: 数据库会话
        credit_code: 企业信用代码
        data: 经过 Pydantic 验证的更新数据
    """
    enterprise = get_enterprise_by_credit_code(db, credit_code)
    if not enterprise:
        return None
    
    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(enterprise, key, value)
    
    enterprise.updated_at = datetime.now()
    db.commit()
    db.refresh(enterprise)
    return enterprise


def delete_enterprise(db: Session, credit_code: str) -> bool:
    """删除企业记录"""
    enterprise = get_enterprise_by_credit_code(db, credit_code)
    if enterprise:
        db.delete(enterprise)
        db.commit()
        return True
    return False

# endregion
# ============================================


# ============================================
# region 律师表 CRUD
# ============================================

def create_lawyer(db: Session, data: LawyerCreate) -> Lawyer:
    """
    创建律师记录
    
    参数:
        db: 数据库会话
        data: 经过 Pydantic 验证的输入数据
    """
    lawyer = Lawyer(**data.model_dump(exclude_none=True))
    db.add(lawyer)
    db.commit()
    db.refresh(lawyer)
    return lawyer


def get_lawyer_by_id(db: Session, lawyer_id: int) -> Optional[Lawyer]:
    """根据ID获取律师"""
    return db.query(Lawyer).filter(Lawyer.id == lawyer_id).first()


def get_lawyer_by_name(db: Session, name: str) -> Optional[Lawyer]:
    """根据姓名获取律师（精确匹配）"""
    return db.query(Lawyer).filter(Lawyer.name == name).first()


def get_all_lawyers(db: Session) -> List[Lawyer]:
    """获取所有律师"""
    return db.query(Lawyer).all()


def search_lawyers(
    db: Session,
    name: Optional[str] = None,
    license_no: Optional[str] = None,
) -> List[Lawyer]:
    """
    搜索律师
    
    参数:
        name: 姓名（模糊匹配）
        license_no: 执业证号
    """
    query = db.query(Lawyer)
    
    if name:
        query = query.filter(Lawyer.name.ilike(f"%{name}%"))
    
    if license_no:
        query = query.filter(Lawyer.license_no == license_no)
    
    return query.all()


def update_lawyer(
    db: Session, 
    lawyer_id: int, 
    data: LawyerUpdate
) -> Optional[Lawyer]:
    """
    更新律师记录
    
    参数:
        db: 数据库会话
        lawyer_id: 律师ID
        data: 经过 Pydantic 验证的更新数据
    """
    lawyer = get_lawyer_by_id(db, lawyer_id)
    if not lawyer:
        return None
    
    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(lawyer, key, value)
    
    lawyer.updated_at = datetime.now()
    db.commit()
    db.refresh(lawyer)
    return lawyer


def delete_lawyer(db: Session, lawyer_id: int) -> bool:
    """删除律师记录"""
    lawyer = get_lawyer_by_id(db, lawyer_id)
    if lawyer:
        db.delete(lawyer)
        db.commit()
        return True
    return False

# endregion
# ============================================