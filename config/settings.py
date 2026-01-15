"""
全局配置文件
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# ============================================
# 路径配置
# ============================================

# 项目根目录
ROOT_DIR = Path(__file__).parent.parent

# 各目录路径
PROMPTS_DIR = ROOT_DIR / "prompts"
OUTPUT_DIR = ROOT_DIR / "output"
CACHE_DIR = ROOT_DIR / "cache"
DOCUMENTS_DIR = ROOT_DIR / "documents"
QDRANT_DIR = ROOT_DIR / "qdrant_data"

# 确保目录存在
for dir_path in [OUTPUT_DIR, CACHE_DIR, DOCUMENTS_DIR, QDRANT_DIR]:
    dir_path.mkdir(exist_ok=True)

# Poppler路径（Windows PDF转图片依赖）
POPPLER_PATH = os.getenv("POPPLER_PATH", r"D:\.Software\poppler\Library\bin")

# ============================================
# API配置
# ============================================

# 硅基流动
SILICONFLOW_API_KEY = os.getenv("SILICONFLOW_API_KEY", "")
SILICONFLOW_BASE_URL = "https://api.siliconflow.cn/v1"

# ============================================
# 模型配置
# ============================================

# 嵌入模型
EMBEDDING_MODEL = "BAAI/bge-m3"
EMBEDDING_BATCH_SIZE = 32

# 重排序模型
RERANK_MODEL = "BAAI/bge-reranker-v2-m3"

# 结构化提取模型
EXTRACT_MODEL = "Qwen/Qwen3-8B"

# 视觉识别模型
VISION_MODEL = "Pro/GLM-4.1V-Thinking"

# 推理模型
REASONING_MODEL = "deepseek-ai/DeepSeek-R1-0528-Qwen3-8B"

# ============================================
# 数据库配置
# ============================================

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "bidding_assistant")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")

DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# ============================================
# Qdrant配置
# ============================================

QDRANT_PATH = str(QDRANT_DIR)
QDRANT_COLLECTION_NAME = "bidding_docs"

# ============================================
# OCR配置
# ============================================

OCR_DPI = 200  # PDF转图片DPI
OCR_LANG = "ch"  # OCR语言

# ============================================
# 缓存配置
# ============================================

USE_CACHE = True  # 是否启用缓存

# ============================================
# 行业同义词（用于业绩匹配）
# ============================================

INDUSTRY_SYNONYMS = {
    "能源": ["能源", "燃气", "天然气", "光伏", "电力", "储能", "分布式能源", "新能源", "清洁能源", "石油", "煤炭", "风电", "水电", "核电", "LNG", "CNG"],
    "燃气": ["燃气", "天然气", "液化气", "煤气", "LNG", "CNG"],
    "光伏": ["光伏", "太阳能", "新能源", "光电"],
    "电力": ["电力", "供电", "发电", "输电", "配电", "电网"],
    "金融": ["金融", "银行", "证券", "保险", "基金", "投资", "信托", "资管"],
    "医疗": ["医疗", "医院", "医药", "卫生", "健康", "制药", "生物医药"],
    "房地产": ["房地产", "地产", "房产", "置业", "物业", "住宅", "商业地产"],
    "信息技术": ["信息技术", "IT", "软件", "互联网", "科技", "数据", "人工智能", "AI"],
    "建筑": ["建筑", "施工", "工程", "建设", "装修", "装饰"],
    "交通": ["交通", "运输", "物流", "航空", "铁路", "港口", "航运"],
    "教育": ["教育", "学校", "培训", "高校", "大学"],
    "政府": ["政府", "机关", "事业单位", "国资", "国有"],
}


# ============================================
# 工具函数
# ============================================

def load_prompt(prompt_name: str) -> str:
    """
    加载提示词模板
    
    参数:
        prompt_name: 提示词文件名（不含扩展名）
    
    返回:
        提示词内容
    """
    prompt_path = PROMPTS_DIR / f"{prompt_name}.md"
    
    if not prompt_path.exists():
        raise FileNotFoundError(f"提示词文件不存在: {prompt_path}")
    
    with open(prompt_path, 'r', encoding='utf-8') as f:
        return f.read()


def expand_keywords(keywords: list) -> list:
    """
    扩展关键词（添加同义词）
    
    参数:
        keywords: 原始关键词列表
    
    返回:
        扩展后的关键词列表
    """
    expanded = set(keywords) if keywords else set()
    
    for kw in keywords or []:
        for category, synonyms in INDUSTRY_SYNONYMS.items():
            if kw in synonyms or kw == category:
                expanded.update(synonyms)
    
    return list(expanded)

# ============================================
# region 向量配置 (pgvector)
# ============================================

# 向量维度（bge-m3 输出维度为 1024）
VECTOR_DIMENSION = 1024

# 相似度搜索 Top-K
VECTOR_TOP_K = 10

# 相似度阈值（余弦距离小于此值才返回）
VECTOR_SIMILARITY_THRESHOLD = 0.8

# endregion
# ============================================