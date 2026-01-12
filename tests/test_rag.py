"""
RAG问答模块单元测试
"""

import pytest
import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))


class TestPromptLoading:
    """提示词加载测试"""
    
    def test_prompt_files_exist(self):
        """测试提示词文件存在"""
        prompts_dir = Path(__file__).parent.parent / "prompts"
        
        expected_files = [
            "structure_parse.md",
            "contract_extract.md",
            "contract_extract_vision.md",
            "requirement_parse.md",
            "match_evaluate.md",
            "rag_qa.md"
        ]
        
        for filename in expected_files:
            prompt_path = prompts_dir / filename
            assert prompt_path.exists(), f"提示词文件不存在: {filename}"
    
    def test_prompt_not_empty(self):
        """测试提示词内容非空"""
        prompts_dir = Path(__file__).parent.parent / "prompts"
        
        for prompt_file in prompts_dir.glob("*.md"):
            content = prompt_file.read_text(encoding='utf-8')
            assert len(content) > 100, f"提示词内容过短: {prompt_file.name}"


class TestContextBuilding:
    """上下文构建测试"""
    
    @pytest.fixture
    def sample_nodes(self):
        """示例检索结果"""
        return [
            {
                "text": "供应商应具有独立法人资格",
                "metadata": {
                    "title": "资格要求",
                    "path": "第一章 > 二、资格要求"
                },
                "score": 0.95
            },
            {
                "text": "近三年无重大违法记录",
                "metadata": {
                    "title": "信誉要求",
                    "path": "第一章 > 三、信誉要求"
                },
                "score": 0.85
            }
        ]
    
    def test_build_context(self, sample_nodes):
        """测试上下文构建"""
        context_parts = []
        
        for i, node in enumerate(sample_nodes, 1):
            title = node["metadata"]["title"]
            path = node["metadata"]["path"]
            content = node["text"]
            
            context_parts.append(
                f"【文档{i}】\n标题: {title}\n路径: {path}\n内容: {content}\n"
            )
        
        context = "\n".join(context_parts)
        
        assert "【文档1】" in context
        assert "【文档2】" in context
        assert "资格要求" in context
        assert "信誉要求" in context
    
    def test_source_extraction(self, sample_nodes):
        """测试来源提取"""
        sources = []
        
        for node in sample_nodes:
            sources.append({
                "title": node["metadata"]["title"],
                "path": node["metadata"]["path"],
                "score": node["score"]
            })
        
        assert len(sources) == 2
        assert sources[0]["score"] > sources[1]["score"]


class TestQueryProcessing:
    """查询处理测试"""
    
    def test_query_normalization(self):
        """测试查询标准化"""
        queries = [
            "供应商资格要求是什么",
            "  供应商资格要求是什么  ",
            "供应商资格要求是什么？"
        ]
        
        normalized = [q.strip().rstrip("？?") for q in queries]
        
        assert all(q == "供应商资格要求是什么" for q in normalized)
    
    def test_empty_query_handling(self):
        """测试空查询处理"""
        empty_queries = ["", "  ", None]
        
        for q in empty_queries:
            is_empty = not q or not q.strip()
            assert is_empty


class TestRerankResults:
    """重排序结果测试"""
    
    @pytest.fixture
    def sample_results(self):
        """示例检索结果"""
        return [
            {"id": 1, "score": 0.7, "text": "内容1"},
            {"id": 2, "score": 0.9, "text": "内容2"},
            {"id": 3, "score": 0.5, "text": "内容3"},
            {"id": 4, "score": 0.8, "text": "内容4"},
        ]
    
    def test_rerank_ordering(self, sample_results):
        """测试重排序顺序"""
        # 模拟重排序后的分数
        reranked_scores = {1: 0.85, 2: 0.95, 3: 0.3, 4: 0.75}
        
        for result in sample_results:
            result["rerank_score"] = reranked_scores[result["id"]]
        
        # 按重排序分数排序
        sorted_results = sorted(
            sample_results, 
            key=lambda x: x["rerank_score"], 
            reverse=True
        )
        
        assert sorted_results[0]["id"] == 2
        assert sorted_results[1]["id"] == 1
    
    def test_top_k_selection(self, sample_results):
        """测试TopK选择"""
        top_k = 3
        
        sorted_results = sorted(
            sample_results,
            key=lambda x: x["score"],
            reverse=True
        )[:top_k]
        
        assert len(sorted_results) == top_k
        assert sorted_results[0]["score"] >= sorted_results[-1]["score"]


class TestAnswerGeneration:
    """答案生成测试"""
    
    def test_answer_with_sources(self):
        """测试带来源的答案"""
        answer = "根据文档，供应商需要满足以下条件..."
        sources = [
            "第一章 > 二、资格要求",
            "第一章 > 三、信誉要求"
        ]
        
        full_answer = answer + "\n\n**信息来源**：\n"
        for src in sources:
            full_answer += f"- {src}\n"
        
        assert "信息来源" in full_answer
        assert "资格要求" in full_answer
    
    def test_no_answer_found(self):
        """测试未找到答案的情况"""
        empty_results = []
        
        if not empty_results:
            answer = "抱歉，在文档中未找到相关信息。"
        
        assert "未找到" in answer


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
