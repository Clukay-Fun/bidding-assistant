"""
全局配置模块
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# 加载 .env 文件
load_dotenv()

# ============================================
# 项目路径
# ============================================
BASE_DIR = Path(__file__).resolve().parent.parent
BACKEND_DIR = Path(__file__).parent.parent
PROMPTS_DIR = BASE_DIR / "prompts"

# ============================================
# 硅基流动 API 配置
# ============================================
SILICONFLOW_API_KEY = os.getenv("SILICONFLOW_API_KEY", "")
SILICONFLOW_BASE_URL = os.getenv("SILICONFLOW_BASE_URL", "https://api.siliconflow.cn/v1")

# ============================================
# 模型配置
# ============================================
# 对话模型
CHAT_MODEL = os.getenv("CHAT_MODEL", "Qwen/Qwen2.5-72B-Instruct")

# 提取模型（用于合同信息提取）
EXTRACT_MODEL = os.getenv("EXTRACT_MODEL", "Qwen/Qwen2.5-72B-Instruct")

# 嵌入模型
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "BAAI/bge-m3")
EMBEDDING_DIM = 1024

# 重排序模型
RERANK_MODEL = os.getenv("RERANK_MODEL", "BAAI/bge-reranker-v2-m3")

# 视觉识别模型
VISION_MODEL = os.getenv("VISION_MODEL", "Pro/Qwen2.5-VL-7B-Instruct")

# ============================================
# 数据库配置
# ============================================
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "bidding_assistant")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "postgres")

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
)

# ============================================
# OCR 配置
# ============================================
OCR_LANG = os.getenv("OCR_LANG", "ch")