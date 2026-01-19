"""
全局配置模块
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# 加载 .env 文件
load_dotenv()

# ============================================
# region 项目路径
# ============================================
BASE_DIR = Path(__file__).resolve().parent.parent
BACKEND_DIR = Path(__file__).parent.parent
PROMPTS_DIR = BASE_DIR / "prompts"
# endregion
# ============================================


# ============================================
# region 硅基流动 API 配置
# ============================================
SILICONFLOW_API_KEY = os.getenv("SILICONFLOW_API_KEY", "")
SILICONFLOW_BASE_URL = os.getenv("SILICONFLOW_BASE_URL", "https://api.siliconflow.cn/v1")
# endregion
# ============================================

# ============================================
# region 模型配置
# ============================================
# 核心推理：用于 Agent 的规划和复杂条款判定
REASONING_MODEL = os.getenv("REASONING_MODEL", "deepseek-ai/DeepSeek-R1-Distill-Qwen-7B")

# 任务执行：用于具体的 JSON 提取和标书解析
EXTRACT_MODEL = os.getenv("EXTRACT_MODEL", "Qwen/Qwen3-8B")

# 对话输出：用于最终的交互式回复
CHAT_MODEL = os.getenv("CHAT_MODEL", "internlm/internlm2_5-7b-chat")

# 嵌入模型
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "BAAI/bge-m3")
EMBEDDING_DIM = 1024

# 重排序模型
RERANK_MODEL = os.getenv("RERANK_MODEL", "BAAI/bge-reranker-v2-m3")

# 视觉识别模型
VISION_MODEL = os.getenv("VISION_MODEL", "THUDM/GLM-4.1V-9B-Thinking")
# endregion
# ============================================

# ============================================
# region 数据库配置
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
# endregion
# ============================================

# ============================================
# region OCR 配置
# ============================================
OCR_LANG = os.getenv("OCR_LANG", "ch")
# endregion
# ============================================