"""
AI驱动的文档结构解析器
功能：使用大模型将Markdown文档解析为层级Node结构
"""

from pathlib import Path
from openai import OpenAI
import json
import time
import sys

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from config.settings import (
    SILICONFLOW_API_KEY, 
    SILICONFLOW_BASE_URL, 
    EXTRACT_MODEL,
    OUTPUT_DIR
)
from src.utils import load_prompt, clean_json_response


# ============================================
# region API客户端
# ============================================

def get_client() -> OpenAI:
    """获取API客户端"""
    return OpenAI(
        api_key=SILICONFLOW_API_KEY,
        base_url=SILICONFLOW_BASE_URL
    )

# endregion
# ============================================


# ============================================
# region 结构化解析
# ============================================

def parse_document_structure(markdown_content: str, chunk_size: int = 15000) -> dict:
    """
    使用AI解析文档结构
    
    参数:
        markdown_content: Markdown文档内容
        chunk_size: 分块大小（避免超出token限制）
    
    返回:
        层级结构字典
    """
    client = get_client()
    
    # 如果文档较短，直接解析
    if len(markdown_content) <= chunk_size:
        return _parse_chunk(client, markdown_content)
    
    # 文档较长，分块解析后合并
    print(f"📄 文档较长（{len(markdown_content)}字符），分块处理...")
    chunks = _split_by_chapters(markdown_content)
    
    all_children = []
    root_content = ""
    
    for i, chunk in enumerate(chunks):
        print(f"   🔍 解析第 {i+1}/{len(chunks)} 块...")
        result = _parse_chunk(client, chunk)
        
        if result:
            # 收集根节点内容
            if result.get("content"):
                root_content += result["content"] + "\n"
            
            # 收集子节点
            if result.get("children"):
                all_children.extend(result["children"])
    
    return {
        "title": "招标文件",
        "level": 0,
        "content": root_content.strip(),
        "children": all_children
    }


def _parse_chunk(client: OpenAI, content: str) -> dict:
    """解析单个文档块"""
    try:
        # 加载提示词
        prompt_template = load_prompt("structure_parse")
        prompt = prompt_template.replace("{document_content}", content)
        
        response = client.chat.completions.create(
            model=EXTRACT_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": "你是一个专业的文档结构分析专家。请严格按照JSON格式输出，不要包含任何其他内容。"
                },
                {
                    "role": "user", 
                    "content": prompt
                }
            ],
            temperature=0.1,
            max_tokens=16000
        )
        
        result_text = response.choices[0].message.content.strip()
        result_text = clean_json_response(result_text)
        
        return json.loads(result_text)
        
    except json.JSONDecodeError as e:
        print(f"   ⚠️ JSON解析失败: {e}")
        return None
    except Exception as e:
        print(f"   ❌ API调用失败: {e}")
        return None


def _split_by_chapters(content: str) -> list:
    """按章节分割文档"""
    import re
    
    # 按"第X章"分割
    pattern = r'(?=^#*\s*第[一二三四五六七八九十百]+章)'
    chunks = re.split(pattern, content, flags=re.MULTILINE)
    
    # 过滤空块
    chunks = [c.strip() for c in chunks if c.strip()]
    
    # 如果没有章节标记，按固定长度分割
    if len(chunks) <= 1:
        chunk_size = 12000
        chunks = [content[i:i+chunk_size] for i in range(0, len(content), chunk_size)]
    
    return chunks

# endregion
# ============================================


# ============================================
# region 转换为Node列表
# ============================================

def structure_to_nodes(structure: dict, parent_id: str = None) -> list:
    """
    将层级结构转换为扁平的Node列表
    
    每个Node包含:
        - id: 唯一标识
        - text: 内容文本
        - metadata: 元数据（标题、层级、父节点等）
    """
    nodes = []
    
    def _traverse(node: dict, parent_id: str = None, path: list = []):
        # 生成节点ID
        node_id = f"node_{len(nodes)}"
        
        # 构建当前路径
        current_path = path + [node.get("title", "")]
        
        # 创建Node
        node_data = {
            "id": node_id,
            "text": node.get("content", ""),
            "metadata": {
                "title": node.get("title", ""),
                "level": node.get("level", 0),
                "parent_id": parent_id,
                "path": " > ".join(current_path),
                "has_children": len(node.get("children", [])) > 0
            }
        }
        
        nodes.append(node_data)
        
        # 递归处理子节点
        for child in node.get("children", []):
            _traverse(child, node_id, current_path)
    
    _traverse(structure)
    return nodes

# endregion
# ============================================


# ============================================
# region 主函数
# ============================================

def parse_markdown_to_nodes(markdown_path: str) -> list:
    """
    解析Markdown文件为Node列表
    
    参数:
        markdown_path: Markdown文件路径
    
    返回:
        Node列表
    """
    start_time = time.time()
    print(f"\n{'='*50}")
    print(f"🚀 开始解析文档结构")
    print(f"{'='*50}")
    print(f"📄 文件: {markdown_path}")
    
    # 读取文件
    with open(markdown_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    print(f"📏 文档长度: {len(content)} 字符")
    
    # AI解析结构
    print(f"\n🤖 调用AI解析文档结构...")
    structure = parse_document_structure(content)
    
    if not structure:
        print("❌ 文档结构解析失败")
        return []
    
    # 保存结构（调试用）
    structure_path = OUTPUT_DIR / f"{Path(markdown_path).stem}_structure.json"
    with open(structure_path, 'w', encoding='utf-8') as f:
        json.dump(structure, f, ensure_ascii=False, indent=2)
    print(f"💾 结构已保存: {structure_path}")
    
    # 转换为Node列表
    nodes = structure_to_nodes(structure)
    
    # 保存Node列表
    nodes_path = OUTPUT_DIR / f"{Path(markdown_path).stem}_nodes.json"
    with open(nodes_path, 'w', encoding='utf-8') as f:
        json.dump(nodes, f, ensure_ascii=False, indent=2)
    print(f"💾 Nodes已保存: {nodes_path}")
    
    elapsed = time.time() - start_time
    print(f"\n{'='*50}")
    print(f"✅ 解析完成!")
    print(f"📊 共生成 {len(nodes)} 个Node")
    print(f"⏱️ 耗时: {elapsed:.2f} 秒")
    print(f"{'='*50}")
    
    return nodes

# endregion
# ============================================


if __name__ == "__main__":
    if len(sys.argv) > 1:
        parse_markdown_to_nodes(sys.argv[1])
    else:
        # 默认测试
        test_file = OUTPUT_DIR / "采购文件.md"
        if test_file.exists():
            parse_markdown_to_nodes(str(test_file))
        else:
            print("用法: python -m src.node_parser <Markdown文件路径>")
