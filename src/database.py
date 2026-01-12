"""
数据库模块
功能：PostgreSQL数据库连接和表定义
"""

from sqlalchemy import create_engine, Column, Integer, String, Text, Boolean, DateTime, Float, LargeBinary
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
from pathlib import Path
import sys

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from config.settings import DATABASE_URL


# ============================================
# region 数据库引擎
# ============================================

engine = create_engine(DATABASE_URL, echo=False)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_session():
    """获取数据库会话"""
    return SessionLocal()

# endregion
# ============================================


# ============================================
# region 表定义
# ============================================

class Contract(Base):
    """合同表"""
    __tablename__ = "contracts"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    file_name = Column(String(255), comment="原始文件名")
    contract_name = Column(String(500), comment="合同名称")
    
    # 甲方信息
    party_a = Column(String(255), comment="甲方名称")
    party_a_id = Column(String(50), comment="甲方身份证/统一社会信用代码")
    party_a_industry = Column(String(100), comment="甲方所在行业")
    is_state_owned = Column(Boolean, default=False, comment="是否是国企")
    is_individual = Column(Boolean, default=False, comment="是否是个人")
    
    # 合同信息
    amount = Column(Float, comment="合同金额（万元）")
    fee_method = Column(String(100), comment="收费方式")
    sign_date = Column(String(20), comment="签订日期")
    
    # 项目信息
    project_type = Column(String(50), comment="项目类型（常法/诉讼/专项）")
    project_detail = Column(Text, comment="项目详情/服务内容")
    subject_amount = Column(Float, comment="标的额（诉讼项目）")
    opponent = Column(String(255), comment="对方当事人（诉讼项目）")
    
    # 团队和摘要
    team_member = Column(String(500), comment="团队成员")
    summary = Column(Text, comment="AI生成的摘要")
    
    # 文件存储
    image_data = Column(LargeBinary, comment="图片数据（BLOB）")
    image_count = Column(Integer, default=0, comment="图片页数")
    raw_text = Column(Text, comment="OCR原文")
    
    # 时间戳
    created_at = Column(DateTime, default=datetime.now, comment="创建时间")
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment="更新时间")
    
    def __repr__(self):
        return f"<Contract(id={self.id}, name='{self.contract_name}', party_a='{self.party_a}')>"
    
    def to_dict(self):
        """转换为字典（不包含BLOB）"""
        return {
            "id": self.id,
            "file_name": self.file_name,
            "contract_name": self.contract_name,
            "party_a": self.party_a,
            "party_a_id": self.party_a_id,
            "party_a_industry": self.party_a_industry,
            "is_state_owned": self.is_state_owned,
            "is_individual": self.is_individual,
            "amount": self.amount,
            "fee_method": self.fee_method,
            "sign_date": self.sign_date,
            "project_type": self.project_type,
            "project_detail": self.project_detail,
            "subject_amount": self.subject_amount,
            "opponent": self.opponent,
            "team_member": self.team_member,
            "summary": self.summary,
            "image_count": self.image_count,
            "created_at": str(self.created_at) if self.created_at else None,
            "updated_at": str(self.updated_at) if self.updated_at else None,
        }

# endregion
# ============================================


# ============================================
# region 数据库初始化
# ============================================

def init_db():
    """初始化数据库（创建表）"""
    print("🔧 初始化数据库...")
    Base.metadata.create_all(bind=engine)
    print("✅ 数据库表创建完成")


def drop_db():
    """删除所有表（谨慎使用）"""
    print("⚠️ 删除所有表...")
    Base.metadata.drop_all(bind=engine)
    print("✅ 表已删除")

# endregion
# ============================================


# ============================================
# region CRUD操作
# ============================================

def add_contract(session, **kwargs) -> Contract:
    """添加合同"""
    contract = Contract(**kwargs)
    session.add(contract)
    session.commit()
    session.refresh(contract)
    return contract


def get_contract_by_id(session, contract_id: int) -> Contract:
    """根据ID获取合同"""
    return session.query(Contract).filter(Contract.id == contract_id).first()


def get_all_contracts(session) -> list:
    """获取所有合同"""
    return session.query(Contract).all()


def search_contracts(session, **filters) -> list:
    """
    搜索合同
    
    示例:
        search_contracts(session, project_type="常法", is_state_owned=True)
    """
    query = session.query(Contract)
    
    for key, value in filters.items():
        if hasattr(Contract, key) and value is not None:
            query = query.filter(getattr(Contract, key) == value)
    
    return query.all()


def delete_contract(session, contract_id: int) -> bool:
    """删除合同"""
    contract = get_contract_by_id(session, contract_id)
    if contract:
        session.delete(contract)
        session.commit()
        return True
    return False

# endregion
# ============================================


if __name__ == "__main__":
    # 测试数据库连接和表创建
    print("\n" + "="*50)
    print("🚀 数据库初始化测试")
    print("="*50 + "\n")
    
    try:
        init_db()
        
        # 测试连接
        session = get_session()
        print("✅ 数据库连接成功")
        
        # 统计现有数据
        count = session.query(Contract).count()
        print(f"📊 当前合同数量: {count}")
        
        session.close()
        print("\n✅ 数据库测试完成！")
        
    except Exception as e:
        print(f"❌ 数据库错误: {e}")
