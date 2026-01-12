"""
RAG问答系统
功能：检索相关文档 + LLM生成答案（带引用）
"""

from pathlib import Path
from openai import OpenAI as OpenAIClient
import httpx
import time
import sys

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from llama_index.core import Settings, VectorStoreIndex
from llama_index.vector_stores.qdrant import QdrantVectorStore
from llama_index.embeddings.openai import OpenAIEmbedding
from qdrant_client import QdrantClient

from config.settings import (
    SILICONFLOW_API_KEY,
    SILICONFLOW_BASE_URL,
    EMBEDDING_MODEL,
    EMBEDDING_BATCH_SIZE,
    REASONING_MODEL,
    RERANK_MODEL,
    QDRANT_PATH,
    QDRANT_COLLECTION_NAME
)
from src.utils import load_prompt


# ============================================
# region 初始化
# ============================================

def get_llm_client() -> OpenAIClient:
    """获取LLM客户端"""
    return OpenAIClient(
        api_key=SILICONFLOW_API_KEY,
        base_url=SILICONFLOW_BASE_URL
    )


def init_embedding():
    """初始化Embedding模型"""
    embed_model = OpenAIEmbedding(
        api_key=SILICONFLOW_API_KEY,
        api_base=SILICONFLOW_BASE_URL,
        model_name=EMBEDDING_MODEL,
        embed_batch_size=EMBEDDING_BATCH_SIZE,
    )
    Settings.embed_model = embed_model
    print(f"✅ Embedding: {EMBEDDING_MODEL}")


def load_index() -> VectorStoreIndex:
    """加载已有的向量索引"""
    print(f"📂 加载索引: {QDRANT_COLLECTION_NAME}")
    
    client = QdrantClient(path=QDRANT_PATH)
    vector_store = QdrantVectorStore(
        client=client,
        collection_name=QDRANT_COLLECTION_NAME,
    )
    
    index = VectorStoreIndex.from_vector_store(vector_store)
    print(f"✅ 索引加载完成")
    return index

# endregion
# ============================================


# ============================================
# region Rerank重排序
# ============================================

def rerank_nodes(query: str, nodes: list, top_n: int = 3) -> list:
    """
    使用硅基流动的Rerank API对结果重排序
    """
    if not nodes:
        return nodes
    
    try:
        documents = [node.text for node in nodes]
        
        response = httpx.post(
            f"{SILICONFLOW_BASE_URL}/rerank",
            headers={
                "Authorization": f"Bearer {SILICONFLOW_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": RERANK_MODEL,
                "query": query,
                "documents": documents,
                "top_n": top_n
            },
            timeout=30.0
        )
        
        if response.status_code == 200:
            result = response.json()
            
            reranked_nodes = []
            for item in result.get("results", []):
                idx = item["index"]
                if idx < len(nodes):
                    nodes[idx].score = item["relevance_score"]
                    reranked_nodes.append(nodes[idx])
            
            print(f"   🔄 Rerank完成，保留 {len(reranked_nodes)} 个结果")
            return reranked_nodes
        else:
            print(f"   ⚠️ Rerank API返回错误: {response.status_code}")
            return nodes[:top_n]
            
    except Exception as e:
        print(f"   ⚠️ Rerank失败: {e}")
        return nodes[:top_n]

# endregion
# ============================================


# ============================================
# region LLM调用
# ============================================

def call_llm(prompt: str) -> str:
    """调用LLM生成回答"""
    client = get_llm_client()
    
    response = client.chat.completions.create(
        model=REASONING_MODEL,
        messages=[
            {"role": "system", "content": "你是一个专业的招投标文档分析助手。"},
            {"role": "user", "content": prompt}
        ],
        temperature=0.1,
        max_tokens=2000
    )
    
    return response.choices[0].message.content

# endregion
# ============================================


# ============================================
# region RAG问答
# ============================================

def query_with_sources(
    index: VectorStoreIndex,
    question: str,
    top_k: int = 5,
    use_rerank: bool = True,
    rerank_top_n: int = 3
) -> dict:
    """
    带引用来源的RAG问答
    """
    start_time = time.time()
    
    # 1. 检索相关文档
    retriever = index.as_retriever(similarity_top_k=top_k)
    nodes = retriever.retrieve(question)
    print(f"   📄 检索到 {len(nodes)} 个相关文档")
    
    # 2. 重排序
    if use_rerank and len(nodes) > 0:
        nodes = rerank_nodes(question, nodes, top_n=rerank_top_n)
    
    # 3. 构建上下文
    context_parts = []
    sources = []
    
    for i, node in enumerate(nodes, 1):
        title = node.metadata.get("title", "未知")
        path = node.metadata.get("path", "未知")
        content = node.text
        
        context_parts.append(f"【文档{i}】\n标题: {title}\n路径: {path}\n内容: {content}\n")
        sources.append({
            "title": title,
            "path": path,
            "content": content[:200] + "..." if len(content) > 200 else content,
            "score": node.score
        })
    
    context = "\n".join(context_parts)
    
    # 4. 加载提示词并调用LLM
    prompt_template = load_prompt("rag_qa")
    prompt = prompt_template.replace("{context}", context).replace("{question}", question)
    answer = call_llm(prompt)
    
    elapsed = time.time() - start_time
    
    return {
        "answer": answer,
        "sources": sources,
        "time": elapsed
    }

# endregion
# ============================================


# ============================================
# region 交互式问答
# ============================================

def interactive_qa(index: VectorStoreIndex):
    """交互式问答"""
    print("\n" + "="*50)
    print("💬 招投标文档问答系统")
    print("="*50)
    print("输入问题进行查询，输入 'quit' 或 'q' 退出\n")
    
    while True:
        question = input("🙋 你的问题: ").strip()
        
        if question.lower() in ['quit', 'q', '退出']:
            print("👋 再见！")
            break
        
        if not question:
            continue
        
        print(f"\n🔍 正在查询...")
        
        try:
            result = query_with_sources(index, question)
            
            print(f"\n{'='*50}")
            print(f"📝 回答：")
            print(f"{'='*50}")
            print(result["answer"])
            
            print(f"\n{'='*50}")
            print(f"📚 引用来源（共{len(result['sources'])}条）：")
            print(f"{'='*50}")
            for i, source in enumerate(result["sources"], 1):
                print(f"\n[{i}] {source['title']}")
                print(f"    路径: {source['path']}")
                print(f"    相似度: {source['score']:.4f}")
            
            print(f"\n⏱️ 耗时: {result['time']:.2f} 秒\n")
            
        except Exception as e:
            print(f"❌ 查询出错: {e}\n")

# endregion
# ============================================


# ============================================
# region 主函数
# ============================================

def main():
    print("\n" + "="*50)
    print("🚀 RAG问答系统启动")
    print("="*50 + "\n")
    
    # 初始化
    init_embedding()
    print(f"✅ LLM: {REASONING_MODEL}")
    print(f"✅ Rerank: {RERANK_MODEL}")
    
    # 加载索引
    index = load_index()
    
    # 启动交互式问答
    interactive_qa(index)


if __name__ == "__main__":
    main()
