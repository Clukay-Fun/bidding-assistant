"""
向量语义搜索服务
功能：使用 pgvector 实现语义相似度搜索
"""

from typing import List, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import text
import httpx

from app.config import (
    SILICONFLOW_API_KEY,
    SILICONFLOW_BASE_URL,
    EMBEDDING_MODEL,
    EMBEDDING_DIM,
)
from app.db.models import Performance, Lawyer


# ============================================
# region 配置常量
# ============================================

# 向量搜索 Top-K
VECTOR_TOP_K = 10

# 相似度阈值（余弦距离，越小越相似，0~2 范围）
# 注意：余弦距离 = 1 - 余弦相似度，所以 0.3 表示相似度约 0.7
VECTOR_DISTANCE_THRESHOLD = 0.8

# endregion
# ============================================


# ============================================
# region 生成向量嵌入
# ============================================

def get_embedding(text: str) -> Optional[List[float]]:
    """
    调用硅基流动 API 生成文本向量
    
    参数:
        text: 待向量化的文本
    
    返回:
        1024 维的向量列表，失败返回 None
    
    原理:
        BGE-M3 模型将文本映射到 1024 维空间，
        语义相近的文本在向量空间中距离更近
    """
    if not text or not text.strip():
        return None
    
    try:
        response = httpx.post(
            f"{SILICONFLOW_BASE_URL}/embeddings",
            headers={
                "Authorization": f"Bearer {SILICONFLOW_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": EMBEDDING_MODEL,
                "input": text,
                "encoding_format": "float"
            },
            timeout=30.0
        )
        
        if response.status_code == 200:
            result = response.json()
            embedding = result["data"][0]["embedding"]
            return embedding
        else:
            print(f"❌ Embedding API 错误: {response.status_code}")
            return None
            
    except Exception as e:
        print(f"❌ 获取向量失败: {e}")
        return None


def get_embeddings_batch(texts: List[str]) -> List[Optional[List[float]]]:
    """
    批量获取向量嵌入（提高效率）
    
    参数:
        texts: 文本列表
    
    返回:
        对应的向量列表
    """
    if not texts:
        return []
    
    try:
        response = httpx.post(
            f"{SILICONFLOW_BASE_URL}/embeddings",
            headers={
                "Authorization": f"Bearer {SILICONFLOW_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": EMBEDDING_MODEL,
                "input": texts,
                "encoding_format": "float"
            },
            timeout=60.0
        )
        
        if response.status_code == 200:
            result = response.json()
            # 按 index 排序确保顺序正确
            data = sorted(result["data"], key=lambda x: x["index"])
            return [item["embedding"] for item in data]
        else:
            print(f"❌ Batch Embedding 错误: {response.status_code}")
            return [None] * len(texts)
            
    except Exception as e:
        print(f"❌ 批量获取向量失败: {e}")
        return [None] * len(texts)

# endregion
# ============================================


# ============================================
# region 业绩向量搜索
# ============================================

def search_performances_by_vector(
    db: Session,
    query: str,
    top_k: int = VECTOR_TOP_K,
    distance_threshold: float = VECTOR_DISTANCE_THRESHOLD,
) -> List[Tuple[Performance, float]]:
    """
    使用向量相似度搜索业绩
    
    参数:
        db: 数据库会话
        query: 查询文本（如 "能源行业法律服务"）
        top_k: 返回最相似的 K 条结果
        distance_threshold: 距离阈值，超过此值的结果会被过滤
    
    返回:
        (Performance, distance) 元组列表，按距离升序排列
    
    原理:
        1. 将查询文本转为向量
        2. 使用 pgvector 的 <-> 运算符计算余弦距离
        3. 距离越小，语义越相似
    """
    # 1. 获取查询向量
    query_embedding = get_embedding(query)
    if not query_embedding:
        print("❌ 无法生成查询向量")
        return []
    
    # 2. 构建 SQL 查询
    # 注意：<-> 是余弦距离运算符，需要 pgvector 扩展
    sql = text("""
        SELECT 
            id,
            embedding <-> :query_vec AS distance
        FROM performances
        WHERE embedding IS NOT NULL
          AND embedding <-> :query_vec < :threshold
        ORDER BY distance
        LIMIT :top_k
    """)
    
    # 3. 执行查询
    # 注意：pgvector 需要向量格式为 '[0.1, 0.2, ...]'
    vector_str = "[" + ",".join(map(str, query_embedding)) + "]"
    
    result = db.execute(
        sql,
        {
            "query_vec": vector_str,
            "threshold": distance_threshold,
            "top_k": top_k
        }
    )
    
    print(f"🔍 向量搜索: 查询向量维度={len(query_embedding)}, 阈值={distance_threshold}")
    
    # 4. 获取完整的 Performance 对象
    rows = result.fetchall()
    performances_with_distance = []
    
    for row in rows:
        performance = db.query(Performance).filter(
            Performance.id == row.id
        ).first()
        if performance:
            performances_with_distance.append((performance, row.distance))
    
    return performances_with_distance


def hybrid_search_performances(
    db: Session,
    query: str,
    top_k: int = VECTOR_TOP_K,
    keyword_weight: float = 0.3,
    vector_weight: float = 0.7,
) -> List[Tuple[Performance, float]]:
    """
    混合搜索：向量相似度 + 关键词匹配
    
    参数:
        db: 数据库会话
        query: 查询文本
        top_k: 返回结果数量
        keyword_weight: 关键词匹配权重
        vector_weight: 向量相似度权重
    
    返回:
        (Performance, score) 元组列表，按综合得分降序排列
    
    原理:
        混合搜索结合两种方法的优点：
        - 向量搜索：理解语义，"法律服务" ≈ "法务咨询"
        - 关键词搜索：精确匹配，确保关键词命中
    """
    # 1. 向量搜索
    vector_results = search_performances_by_vector(
        db, query, top_k=top_k * 2  # 取更多用于融合
    )
    
    # 2. 关键词搜索（从 crud.py 复用逻辑）
    from app.db.crud import search_performances
    keyword_results = search_performances(db, keyword=query)
    
    # 3. 融合评分
    scores = {}
    
    # 向量搜索得分（距离转相似度：1 - distance/2）
    for perf, distance in vector_results:
        similarity = 1 - distance / 2  # 归一化到 0~1
        scores[perf.id] = scores.get(perf.id, 0) + similarity * vector_weight
    
    # 关键词匹配得分（命中即给分）
    for perf in keyword_results:
        scores[perf.id] = scores.get(perf.id, 0) + 1.0 * keyword_weight
    
    # 4. 排序并获取 top_k
    sorted_ids = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:top_k]
    
    # 5. 查询完整对象
    results = []
    for perf_id, score in sorted_ids:
        perf = db.query(Performance).filter(Performance.id == perf_id).first()
        if perf:
            results.append((perf, score))
    
    return results

# endregion
# ============================================


# ============================================
# region 律师向量搜索
# ============================================

def search_lawyers_by_resume(
    db: Session,
    query: str,
    top_k: int = 5,
) -> List[Tuple[Lawyer, float]]:
    """
    根据需求搜索匹配的律师（基于简历向量）
    
    参数:
        db: 数据库会话
        query: 需求描述（如 "有能源行业经验的律师"）
        top_k: 返回结果数量
    
    返回:
        (Lawyer, distance) 元组列表
    """
    query_embedding = get_embedding(query)
    if not query_embedding:
        return []
    
    sql = text("""
        SELECT 
            id,
            resume_embedding <-> :query_vec AS distance
        FROM lawyers
        WHERE resume_embedding IS NOT NULL
        ORDER BY distance
        LIMIT :top_k
    """)
    
    # pgvector 需要向量格式为 '[0.1, 0.2, ...]'
    vector_str = "[" + ",".join(map(str, query_embedding)) + "]"
    
    result = db.execute(
        sql,
        {
            "query_vec": vector_str,
            "top_k": top_k
        }
    )
    
    rows = result.fetchall()
    lawyers_with_distance = []
    
    for row in rows:
        lawyer = db.query(Lawyer).filter(Lawyer.id == row.id).first()
        if lawyer:
            lawyers_with_distance.append((lawyer, row.distance))
    
    return lawyers_with_distance

# endregion
# ============================================


# ============================================
# region 向量更新工具
# ============================================

def update_performance_embedding(db: Session, performance_id: int) -> bool:
    """
    为单条业绩生成/更新向量
    
    原理:
        将业绩的关键信息拼接成文本，生成向量存入数据库
    """
    perf = db.query(Performance).filter(Performance.id == performance_id).first()
    if not perf:
        return False
    
    # 拼接用于向量化的文本
    text_parts = [
        perf.party_a or "",
        perf.contract_type or "",
        perf.project_detail or "",
        perf.summary or "",
    ]
    text_to_embed = " ".join(filter(None, text_parts))
    
    if not text_to_embed.strip():
        return False
    
    embedding = get_embedding(text_to_embed)
    if embedding:
        perf.embedding = embedding
        db.commit()
        return True
    
    return False


def batch_update_embeddings(db: Session, batch_size: int = 10) -> int:
    """
    批量更新所有缺失向量的业绩
    
    返回:
        成功更新的数量
    """
    # 查找没有向量的业绩
    performances = db.query(Performance).filter(
        Performance.embedding.is_(None)
    ).limit(batch_size).all()
    
    if not performances:
        print("✅ 所有业绩都已有向量")
        return 0
    
    # 准备文本
    texts = []
    for perf in performances:
        text_parts = [
            perf.party_a or "",
            perf.contract_type or "",
            perf.project_detail or "",
            perf.summary or "",
        ]
        texts.append(" ".join(filter(None, text_parts)))
    
    # 批量获取向量
    embeddings = get_embeddings_batch(texts)
    
    # 更新数据库
    count = 0
    for perf, embedding in zip(performances, embeddings):
        if embedding:
            perf.embedding = embedding
            count += 1
    
    db.commit()
    print(f"✅ 成功更新 {count}/{len(performances)} 条向量")
    
    return count

# endregion
# ============================================