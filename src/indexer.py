"""
LlamaIndex 索引构建器
功能：将解析后的Node转换为LlamaIndex格式，生成向量并存储
"""

from pathlib import Path
import json
import time
import uuid
import sys

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from llama_index.core import Settings, VectorStoreIndex, StorageContext
from llama_index.core.schema import TextNode
from llama_index.vector_stores.qdrant import QdrantVectorStore
from llama_index.embeddings.openai import OpenAIEmbedding
from qdrant_client import QdrantClient

from config.settings import (
    SILICONFLOW_API_KEY,
    SILICONFLOW_BASE_URL,
    EMBEDDING_MODEL,
    EMBEDDING_BATCH_SIZE,
    QDRANT_PATH,
    QDRANT_COLLECTION_NAME,
    OUTPUT_DIR
)


# ============================================
# region 初始化
# ============================================

def init_settings():
    """初始化LlamaIndex全局设置"""
    
    # 配置Embedding模型
    embed_model = OpenAIEmbedding(
        api_key=SILICONFLOW_API_KEY,
        api_base=SILICONFLOW_BASE_URL,
        model_name=EMBEDDING_MODEL,
        embed_batch_size=EMBEDDING_BATCH_SIZE,
    )
    
    Settings.embed_model = embed_model
    Settings.chunk_size = 1024
    Settings.chunk_overlap = 200
    
    print(f"✅ Embedding模型已配置: {EMBEDDING_MODEL}")


def get_qdrant_client() -> QdrantClient:
    """获取Qdrant客户端（本地持久化模式）"""
    Path(QDRANT_PATH).mkdir(exist_ok=True)
    return QdrantClient(path=QDRANT_PATH)

# endregion
# ============================================


# ============================================
# region Node转换
# ============================================

def load_nodes_from_json(json_path: str) -> list:
    """
    从JSON文件加载Node并转换为LlamaIndex TextNode
    
    参数:
        json_path: node_parser.py生成的nodes.json文件路径
    
    返回:
        TextNode列表
    """
    print(f"📄 加载Node文件: {json_path}")
    
    with open(json_path, 'r', encoding='utf-8') as f:
        nodes_data = json.load(f)
    
    text_nodes = []
    
    for node in nodes_data:
        # 跳过没有内容的节点
        if not node.get("text", "").strip():
            continue
        
        # 创建TextNode，使用UUID作为ID
        text_node = TextNode(
            text=node["text"],
            id_=str(uuid.uuid4()),
            metadata={
                "title": node["metadata"]["title"],
                "level": node["metadata"]["level"],
                "path": node["metadata"]["path"],
                "parent_id": node["metadata"]["parent_id"],
                "has_children": node["metadata"]["has_children"],
                "original_id": node["id"],
            }
        )
        
        text_nodes.append(text_node)
    
    print(f"✅ 加载了 {len(text_nodes)} 个有效Node")
    return text_nodes

# endregion
# ============================================


# ============================================
# region 索引构建
# ============================================

def build_index(nodes: list, collection_name: str = None) -> VectorStoreIndex:
    """
    构建向量索引
    
    参数:
        nodes: TextNode列表
        collection_name: Qdrant集合名称
    
    返回:
        VectorStoreIndex
    """
    if collection_name is None:
        collection_name = QDRANT_COLLECTION_NAME
    
    start_time = time.time()
    print(f"\n🔨 开始构建索引...")
    print(f"   集合名称: {collection_name}")
    print(f"   节点数量: {len(nodes)}")
    
    # 初始化Qdrant
    client = get_qdrant_client()
    
    # 创建向量存储
    vector_store = QdrantVectorStore(
        client=client,
        collection_name=collection_name,
    )
    
    # 创建存储上下文
    storage_context = StorageContext.from_defaults(vector_store=vector_store)
    
    # 构建索引
    print(f"   🔢 生成向量嵌入中...")
    index = VectorStoreIndex(
        nodes=nodes,
        storage_context=storage_context,
        show_progress=True
    )
    
    elapsed = time.time() - start_time
    print(f"✅ 索引构建完成，耗时: {elapsed:.2f} 秒")
    
    return index


def load_index(collection_name: str = None) -> VectorStoreIndex:
    """
    加载已存在的索引
    
    参数:
        collection_name: Qdrant集合名称
    
    返回:
        VectorStoreIndex
    """
    if collection_name is None:
        collection_name = QDRANT_COLLECTION_NAME
    
    print(f"📂 加载已有索引: {collection_name}")
    
    client = get_qdrant_client()
    
    vector_store = QdrantVectorStore(
        client=client,
        collection_name=collection_name,
    )
    
    index = VectorStoreIndex.from_vector_store(vector_store)
    
    print(f"✅ 索引加载完成")
    return index

# endregion
# ============================================


# ============================================
# region 简单查询测试
# ============================================

def test_query(index: VectorStoreIndex, query: str, top_k: int = 3):
    """
    测试查询
    """
    print(f"\n🔍 查询: {query}")
    print(f"{'='*50}")
    
    retriever = index.as_retriever(similarity_top_k=top_k)
    results = retriever.retrieve(query)
    
    for i, result in enumerate(results, 1):
        print(f"\n📄 结果 {i} (相似度: {result.score:.4f})")
        print(f"   标题: {result.metadata.get('title', 'N/A')}")
        print(f"   路径: {result.metadata.get('path', 'N/A')}")
        print(f"   内容: {result.text[:200]}...")

# endregion
# ============================================


# ============================================
# region 主函数
# ============================================

def main():
    """主流程"""
    print("\n" + "="*50)
    print("🚀 LlamaIndex 索引构建")
    print("="*50)
    
    # 1. 初始化设置
    init_settings()
    
    # 2. 加载Node
    nodes_file = OUTPUT_DIR / "采购文件_nodes.json"
    if not nodes_file.exists():
        print(f"❌ Node文件不存在: {nodes_file}")
        print("   请先运行 node_parser.py 生成Node文件")
        return
    
    nodes = load_nodes_from_json(str(nodes_file))
    
    if not nodes:
        print("❌ 没有有效的Node")
        return
    
    # 3. 构建索引
    index = build_index(nodes)
    
    # 4. 测试查询
    print("\n" + "="*50)
    print("🧪 测试查询")
    print("="*50)
    
    test_queries = [
        "供应商资格要求是什么",
        "业绩要求",
        "最高限价是多少",
    ]
    
    for query in test_queries:
        test_query(index, query)


if __name__ == "__main__":
    main()
