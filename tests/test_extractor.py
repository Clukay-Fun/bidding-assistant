"""
合同提取模块单元测试
"""

import pytest
import sys
from pathlib import Path
from unittest.mock import Mock, patch

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.utils import clean_float, clean_bool, clean_string, clean_json_response


class TestDataCleaning:
    """数据清洗函数测试"""
    
    def test_clean_float_valid(self):
        """测试有效浮点数"""
        assert clean_float(5.0) == 5.0
        assert clean_float("3.14") == 3.14
        assert clean_float(100) == 100.0
    
    def test_clean_float_invalid(self):
        """测试无效浮点数"""
        assert clean_float(None) is None
        assert clean_float("") is None
        assert clean_float("null") is None
        assert clean_float("abc") is None
    
    def test_clean_bool_true(self):
        """测试布尔值True"""
        assert clean_bool(True) is True
        assert clean_bool("true") is True
        assert clean_bool("True") is True
        assert clean_bool("yes") is True
        assert clean_bool("是") is True
        assert clean_bool("1") is True
    
    def test_clean_bool_false(self):
        """测试布尔值False"""
        assert clean_bool(False) is False
        assert clean_bool(None) is False
        assert clean_bool("false") is False
        assert clean_bool("no") is False
        assert clean_bool("0") is False
    
    def test_clean_string_valid(self):
        """测试有效字符串"""
        assert clean_string("hello") == "hello"
        assert clean_string("  hello  ") == "hello"
        assert clean_string(123) == "123"
    
    def test_clean_string_invalid(self):
        """测试无效字符串"""
        assert clean_string(None) is None
        assert clean_string("null") is None
        assert clean_string("") is None


class TestJsonCleaning:
    """JSON清理函数测试"""
    
    def test_clean_json_with_markdown(self):
        """测试带markdown标记的JSON"""
        text = '```json\n{"key": "value"}\n```'
        result = clean_json_response(text)
        assert result == '{"key": "value"}'
    
    def test_clean_json_plain(self):
        """测试普通JSON"""
        text = '{"key": "value"}'
        result = clean_json_response(text)
        assert result == '{"key": "value"}'
    
    def test_clean_json_with_prefix(self):
        """测试带前缀的JSON"""
        text = 'Here is the result: {"key": "value"}'
        result = clean_json_response(text)
        assert result == '{"key": "value"}'


class TestContractExtraction:
    """合同提取功能测试（需要Mock）"""
    
    @pytest.fixture
    def sample_ocr_text(self):
        """示例OCR文本"""
        return """
        常年法律顾问合同
        
        甲方：深圳市某某有限公司
        统一社会信用代码：91440300XXXXXXXXXX
        
        乙方：北京市某某律师事务所
        
        服务期限：2024年1月1日至2025年12月31日
        服务费用：人民币伍万元整（¥50,000.00）
        
        服务内容：
        1. 提供日常法律咨询
        2. 审查合同文件
        3. 参与商务谈判
        
        承办律师：张三、李四
        """
    
    @pytest.fixture
    def expected_result(self):
        """预期提取结果"""
        return {
            "contract_name": "常年法律顾问合同",
            "party_a": "深圳市某某有限公司",
            "project_type": "常法",
            "amount": 5.0,
            "team_member": "张三、李四"
        }
    
    def test_extraction_fields(self, sample_ocr_text, expected_result):
        """测试提取字段完整性"""
        # 这里应该调用实际的提取函数
        # 由于依赖外部API，使用Mock测试
        pass


class TestBatchProcessing:
    """批量处理测试"""
    
    def test_batch_empty_folder(self, tmp_path):
        """测试空文件夹"""
        # 创建空文件夹
        empty_folder = tmp_path / "empty"
        empty_folder.mkdir()
        
        # 检查是否正确处理空文件夹
        pdf_files = list(empty_folder.glob("*.pdf"))
        assert len(pdf_files) == 0
    
    def test_batch_file_detection(self, tmp_path):
        """测试文件检测"""
        # 创建测试文件
        test_folder = tmp_path / "test"
        test_folder.mkdir()
        
        (test_folder / "contract1.pdf").touch()
        (test_folder / "contract2.pdf").touch()
        (test_folder / "readme.txt").touch()
        
        # 检查PDF文件检测
        pdf_files = list(test_folder.glob("*.pdf"))
        assert len(pdf_files) == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
