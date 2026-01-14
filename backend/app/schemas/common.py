"""
通用 Pydantic 模型
用于 API 请求/响应的数据验证
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Optional, List
from pydantic import BaseModel, Field


# ============================================
# region 业绩 Schema
# ============================================

class PerformanceCreate(BaseModel):
    """创建业绩的输入模型"""
    file_name: str = Field(..., max_length=255, description="文件名")
    party_a: Optional[str] = Field(None, max_length=255, description="甲方名称")
    party_a_credit_code: Optional[str] = Field(None, max_length=18, description="甲方信用代码")
    contract_type: Optional[str] = Field(None, max_length=50, description="合同类型")
    amount: Optional[Decimal] = Field(None, ge=0, description="合同金额（万元）")
    sign_date: Optional[date] = Field(None, description="签订日期")
    project_detail: Optional[str] = Field(None, description="项目详情")
    subject_amount: Optional[Decimal] = Field(None, ge=0, description="标的额")
    opponent: Optional[str] = Field(None, max_length=255, description="对方当事人")
    team_member: Optional[str] = Field(None, max_length=500, description="团队成员")
    summary: Optional[str] = Field(None, description="AI摘要")
    raw_text: Optional[str] = Field(None, description="OCR原文")


class PerformanceUpdate(BaseModel):
    """更新业绩的输入模型（所有字段可选）"""
    party_a: Optional[str] = Field(None, max_length=255)
    party_a_credit_code: Optional[str] = Field(None, max_length=18)
    contract_type: Optional[str] = Field(None, max_length=50)
    amount: Optional[Decimal] = Field(None, ge=0)
    sign_date: Optional[date] = None
    project_detail: Optional[str] = None
    subject_amount: Optional[Decimal] = Field(None, ge=0)
    opponent: Optional[str] = Field(None, max_length=255)
    team_member: Optional[str] = Field(None, max_length=500)
    summary: Optional[str] = None


class PerformanceResponse(BaseModel):
    """业绩响应模型"""
    id: int
    file_name: str
    party_a: Optional[str] = None
    party_a_credit_code: Optional[str] = None
    contract_type: Optional[str] = None
    amount: Optional[float] = None
    sign_date: Optional[date] = None
    project_detail: Optional[str] = None
    subject_amount: Optional[float] = None
    opponent: Optional[str] = None
    team_member: Optional[str] = None
    summary: Optional[str] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True  # 支持从 ORM 模型转换

# endregion
# ============================================


# ============================================
# region 企业 Schema
# ============================================

class EnterpriseCreate(BaseModel):
    """创建企业的输入模型"""
    credit_code: str = Field(..., max_length=18, description="统一社会信用代码")
    company_name: str = Field(..., max_length=255, description="企业名称")
    business_scope: Optional[str] = Field(None, description="经营范围")
    is_state_owned: bool = Field(False, description="是否国企")
    industry: Optional[str] = Field(None, max_length=100, description="行业")
    enterprise_type: Optional[str] = Field(None, max_length=50, description="企业类型")
    auto_filled: bool = Field(False, description="是否自动填充")
    data_source: Optional[str] = Field(None, max_length=50, description="数据来源")


class EnterpriseUpdate(BaseModel):
    """更新企业的输入模型"""
    company_name: Optional[str] = Field(None, max_length=255)
    business_scope: Optional[str] = None
    is_state_owned: Optional[bool] = None
    industry: Optional[str] = Field(None, max_length=100)
    enterprise_type: Optional[str] = Field(None, max_length=50)
    auto_filled: Optional[bool] = None
    data_source: Optional[str] = Field(None, max_length=50)


class EnterpriseResponse(BaseModel):
    """企业响应模型"""
    credit_code: str
    company_name: str
    business_scope: Optional[str] = None
    is_state_owned: bool
    industry: Optional[str] = None
    enterprise_type: Optional[str] = None
    auto_filled: bool
    data_source: Optional[str] = None

    class Config:
        from_attributes = True

# endregion
# ============================================


# ============================================
# region 律师 Schema
# ============================================

class LawyerCreate(BaseModel):
    """创建律师的输入模型"""
    name: str = Field(..., max_length=50, description="姓名")
    id_card: Optional[str] = Field(None, max_length=18, description="身份证号")
    license_no: Optional[str] = Field(None, max_length=50, description="执业证号")
    resume: Optional[str] = Field(None, description="简历")
    id_card_image: Optional[str] = Field(None, max_length=255)
    degree_image: Optional[str] = Field(None, max_length=255)
    diploma_image: Optional[str] = Field(None, max_length=255)
    license_image: Optional[str] = Field(None, max_length=255)


class LawyerUpdate(BaseModel):
    """更新律师的输入模型"""
    name: Optional[str] = Field(None, max_length=50)
    id_card: Optional[str] = Field(None, max_length=18)
    license_no: Optional[str] = Field(None, max_length=50)
    resume: Optional[str] = None
    id_card_image: Optional[str] = Field(None, max_length=255)
    degree_image: Optional[str] = Field(None, max_length=255)
    diploma_image: Optional[str] = Field(None, max_length=255)
    license_image: Optional[str] = Field(None, max_length=255)


class LawyerResponse(BaseModel):
    """律师响应模型"""
    id: int
    name: str
    id_card: Optional[str] = None
    license_no: Optional[str] = None
    resume: Optional[str] = None
    id_card_image: Optional[str] = None
    degree_image: Optional[str] = None
    diploma_image: Optional[str] = None
    license_image: Optional[str] = None

    class Config:
        from_attributes = True

# endregion
# ============================================


# ============================================
# region 搜索条件 Schema
# ============================================

class PerformanceSearchParams(BaseModel):
    """业绩搜索参数"""
    party_a: Optional[str] = Field(None, description="甲方名称（模糊）")
    contract_type: Optional[str] = Field(None, description="合同类型")
    min_amount: Optional[float] = Field(None, ge=0, description="最小金额")
    max_amount: Optional[float] = Field(None, ge=0, description="最大金额")
    years: Optional[int] = Field(None, ge=1, le=10, description="近N年")
    keyword: Optional[str] = Field(None, description="关键词")

# endregion
# ============================================