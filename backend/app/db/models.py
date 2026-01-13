"""
数据库模型定义
对应三张核心表：业绩库、企业库、律师库
"""

from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Text, Boolean, 
    DateTime, Float, LargeBinary, Date, DECIMAL
)
from pgvector.sqlalchemy import Vector

from app.db.database import Base
from app.config import EMBEDDING_DIM


# ============================================
# region 业绩库 (performances)
# ============================================

class Performance(Base):
    """业绩合同表"""
    __tablename__ = "performances"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    file_name = Column(String(255), unique=True, nullable=False, comment="文件名（唯一标识）")
    
    # 甲方信息
    party_a = Column(String(255), comment="甲方名称")
    party_a_credit_code = Column(String(18), comment="甲方统一社会信用代码")
    
    # 合同信息
    contract_type = Column(String(50), comment="合同类型")
    amount = Column(DECIMAL(12, 2), comment="合同金额（万元）")
    sign_date = Column(Date, comment="签订日期")
    
    # 项目信息
    project_detail = Column(Text, comment="项目详情/服务内容")
    subject_amount = Column(DECIMAL(12, 2), comment="标的额（诉讼项目）")
    opponent = Column(String(255), comment="对方当事人（诉讼项目）")
    
    # 团队
    team_member = Column(String(500), comment="团队成员")
    
    # AI摘要
    summary = Column(Text, comment="AI生成的摘要")
    
    # 向量嵌入
    embedding = Column(Vector(EMBEDDING_DIM), comment="文档向量")
    
    # 原始数据
    raw_text = Column(Text, comment="OCR原文")
    image_data = Column(LargeBinary, comment="图片数据")
    
    # 时间戳
    created_at = Column(DateTime, default=datetime.now, comment="创建时间")
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment="更新时间")
    
    def __repr__(self):
        return f"<Performance(id={self.id}, file_name='{self.file_name}')>"
    
    def to_dict(self):
        """转为字典（不含 BLOB 和向量）"""
        return {
            "id": self.id,
            "file_name": self.file_name,
            "party_a": self.party_a,
            "party_a_credit_code": self.party_a_credit_code,
            "contract_type": self.contract_type,
            "amount": float(self.amount) if self.amount else None,
            "sign_date": str(self.sign_date) if self.sign_date else None,
            "project_detail": self.project_detail,
            "subject_amount": float(self.subject_amount) if self.subject_amount else None,
            "opponent": self.opponent,
            "team_member": self.team_member,
            "summary": self.summary,
            "created_at": str(self.created_at) if self.created_at else None,
        }

# endregion
# ============================================


# ============================================
# region 企业库 (enterprises)
# ============================================

class Enterprise(Base):
    """企业信息表"""
    __tablename__ = "enterprises"
    
    credit_code = Column(String(18), primary_key=True, comment="统一社会信用代码")
    company_name = Column(String(255), nullable=False, comment="企业名称")
    business_scope = Column(Text, comment="经营范围")
    is_state_owned = Column(Boolean, default=False, comment="是否国企")
    industry = Column(String(100), comment="行业分类")
    enterprise_type = Column(String(50), comment="企业类型")
    
    # 数据来源标记
    auto_filled = Column(Boolean, default=False, comment="是否自动填充")
    data_source = Column(String(50), comment="数据来源")
    
    # 时间戳
    created_at = Column(DateTime, default=datetime.now, comment="创建时间")
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment="更新时间")
    
    def __repr__(self):
        return f"<Enterprise(credit_code='{self.credit_code}', name='{self.company_name}')>"
    
    def to_dict(self):
        return {
            "credit_code": self.credit_code,
            "company_name": self.company_name,
            "business_scope": self.business_scope,
            "is_state_owned": self.is_state_owned,
            "industry": self.industry,
            "enterprise_type": self.enterprise_type,
            "auto_filled": self.auto_filled,
            "data_source": self.data_source,
        }

# endregion
# ============================================


# ============================================
# region 律师库 (lawyers)
# ============================================

class Lawyer(Base):
    """律师信息表"""
    __tablename__ = "lawyers"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(50), nullable=False, comment="姓名")
    id_card = Column(String(18), comment="身份证号")
    license_no = Column(String(50), comment="执业证号")
    
    # 简历
    resume = Column(Text, comment="简历内容")
    resume_embedding = Column(Vector(EMBEDDING_DIM), comment="简历向量")
    
    # 证件图片路径
    id_card_image = Column(String(255), comment="身份证图片路径")
    degree_image = Column(String(255), comment="学位证图片路径")
    diploma_image = Column(String(255), comment="毕业证图片路径")
    license_image = Column(String(255), comment="执业证图片路径")
    
    # 时间戳
    created_at = Column(DateTime, default=datetime.now, comment="创建时间")
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment="更新时间")
    
    def __repr__(self):
        return f"<Lawyer(id={self.id}, name='{self.name}')>"
    
    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "id_card": self.id_card,
            "license_no": self.license_no,
            "resume": self.resume,
            "id_card_image": self.id_card_image,
            "degree_image": self.degree_image,
            "diploma_image": self.diploma_image,
            "license_image": self.license_image,
        }

# endregion
# ============================================