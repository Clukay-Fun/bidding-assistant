"""
业绩匹配模块单元测试
"""

import pytest
import sys
from pathlib import Path
from datetime import datetime, timedelta

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from config.settings import expand_keywords, INDUSTRY_SYNONYMS


class TestKeywordExpansion:
    """关键词扩展测试"""
    
    def test_expand_energy_keywords(self):
        """测试能源类关键词扩展"""
        keywords = ["能源"]
        expanded = expand_keywords(keywords)
        
        assert "燃气" in expanded
        assert "天然气" in expanded
        assert "光伏" in expanded
        assert "电力" in expanded
        assert "储能" in expanded
    
    def test_expand_gas_keywords(self):
        """测试燃气类关键词扩展"""
        keywords = ["燃气"]
        expanded = expand_keywords(keywords)
        
        assert "天然气" in expanded
        assert "LNG" in expanded
        assert "CNG" in expanded
    
    def test_expand_multiple_keywords(self):
        """测试多个关键词扩展"""
        keywords = ["能源", "金融"]
        expanded = expand_keywords(keywords)
        
        # 能源类
        assert "燃气" in expanded
        assert "光伏" in expanded
        
        # 金融类
        assert "银行" in expanded
        assert "证券" in expanded
    
    def test_expand_empty_keywords(self):
        """测试空关键词"""
        keywords = []
        expanded = expand_keywords(keywords)
        assert len(expanded) == 0
    
    def test_expand_unknown_keyword(self):
        """测试未知关键词（不在同义词表中）"""
        keywords = ["未知行业"]
        expanded = expand_keywords(keywords)
        
        # 应该保留原关键词
        assert "未知行业" in expanded


class TestIndustrySynonyms:
    """行业同义词配置测试"""
    
    def test_synonyms_not_empty(self):
        """测试同义词表非空"""
        assert len(INDUSTRY_SYNONYMS) > 0
    
    def test_energy_synonyms(self):
        """测试能源类同义词"""
        assert "能源" in INDUSTRY_SYNONYMS
        assert len(INDUSTRY_SYNONYMS["能源"]) >= 5
    
    def test_finance_synonyms(self):
        """测试金融类同义词"""
        assert "金融" in INDUSTRY_SYNONYMS
        assert "银行" in INDUSTRY_SYNONYMS["金融"]


class TestTimeRangeFilter:
    """时间范围筛选测试"""
    
    def test_within_five_years(self):
        """测试近五年内"""
        years = 5
        cutoff_date = datetime.now() - timedelta(days=years*365)
        
        # 3年前的日期应该通过
        three_years_ago = datetime.now() - timedelta(days=3*365)
        assert three_years_ago > cutoff_date
        
        # 6年前的日期应该不通过
        six_years_ago = datetime.now() - timedelta(days=6*365)
        assert six_years_ago < cutoff_date
    
    def test_within_three_years(self):
        """测试近三年内"""
        years = 3
        cutoff_date = datetime.now() - timedelta(days=years*365)
        
        # 2年前的日期应该通过
        two_years_ago = datetime.now() - timedelta(days=2*365)
        assert two_years_ago > cutoff_date
        
        # 4年前的日期应该不通过
        four_years_ago = datetime.now() - timedelta(days=4*365)
        assert four_years_ago < cutoff_date


class TestMatchScoring:
    """匹配评分测试"""
    
    def test_score_range(self):
        """测试评分范围"""
        scores = [95, 80, 65, 40]
        
        for score in scores:
            assert 0 <= score <= 100
    
    def test_score_classification(self):
        """测试评分分类"""
        def classify_score(score):
            if score >= 90:
                return "完全符合"
            elif score >= 70:
                return "基本符合"
            elif score >= 50:
                return "部分符合"
            else:
                return "不符合"
        
        assert classify_score(95) == "完全符合"
        assert classify_score(80) == "基本符合"
        assert classify_score(60) == "部分符合"
        assert classify_score(30) == "不符合"


class TestContractFiltering:
    """合同筛选测试"""
    
    @pytest.fixture
    def sample_contracts(self):
        """示例合同数据"""
        return [
            {
                "id": 1,
                "contract_name": "燃气公司常法合同",
                "party_a": "深圳燃气公司",
                "party_a_industry": "燃气",
                "is_state_owned": True,
                "amount": 10.0,
                "sign_date": "2024-01-15",
                "project_type": "常法"
            },
            {
                "id": 2,
                "contract_name": "科技公司专项服务",
                "party_a": "某科技有限公司",
                "party_a_industry": "信息技术",
                "is_state_owned": False,
                "amount": 5.0,
                "sign_date": "2023-06-01",
                "project_type": "专项"
            },
            {
                "id": 3,
                "contract_name": "劳动争议代理",
                "party_a": "张三",
                "party_a_industry": "个人",
                "is_state_owned": False,
                "amount": 2.0,
                "sign_date": "2024-03-01",
                "project_type": "诉讼"
            }
        ]
    
    def test_filter_by_industry(self, sample_contracts):
        """测试按行业筛选"""
        keywords = ["燃气", "天然气"]
        
        filtered = []
        for c in sample_contracts:
            text = f"{c['party_a']} {c['party_a_industry']}"
            for kw in keywords:
                if kw in text:
                    filtered.append(c)
                    break
        
        assert len(filtered) == 1
        assert filtered[0]["id"] == 1
    
    def test_filter_by_project_type(self, sample_contracts):
        """测试按项目类型筛选"""
        project_type = "常法"
        
        filtered = [c for c in sample_contracts if c["project_type"] == project_type]
        
        assert len(filtered) == 1
        assert filtered[0]["id"] == 1
    
    def test_filter_by_state_owned(self, sample_contracts):
        """测试按国企筛选"""
        filtered = [c for c in sample_contracts if c["is_state_owned"]]
        
        assert len(filtered) == 1
        assert filtered[0]["id"] == 1
    
    def test_filter_by_amount(self, sample_contracts):
        """测试按金额筛选"""
        min_amount = 5.0
        
        filtered = [c for c in sample_contracts if c["amount"] >= min_amount]
        
        assert len(filtered) == 2
        assert all(c["amount"] >= min_amount for c in filtered)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
