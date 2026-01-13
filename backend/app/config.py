"""
全局配置管理
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# 加载 .env 文件
load_dotenv()

# ============================================
# region 路径配置
# ============================================
# backend 目录
BACKEND_DIR = Path(__file__).parent.parent
# 项目根目录
ROOT_DIR = BACKEND_DIR.parent
# endregion
# ============================================

# ============================================
# region 数据库配置
# ============================================
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "bidding_assistant")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")

DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
# endregion
# ============================================

# ============================================
# region API配置（硅基流动）
# ============================================
SILICONFLOW_API_KEY = os.getenv("SILICONFLOW_API_KEY", "")
SILICONFLOW_BASE_URL = "https://api.siliconflow.cn/v1"
# endregion
# ============================================

# ============================================
# region 模型配置
# ============================================
# 主控Agent（决策/规划）
REASONING_MODEL = "deepseek-ai/DeepSeek-R1-0528-Qwen3-8B"
# endregion
# ============================================

# 子任务执行（提取/打杂）
EXTRACT_MODEL = "Qwen/Qwen3-8B"

# Embedding模型
EMBEDDING_MODEL = "BAAI/bge-m3"
EMBEDDING_DIM = 1024  # BGE-M3 是 1024 维

# ============================================
# region Agent配置
# ============================================
AGENT_MAX_STEPS = 10  # 最大执行步数，防止死循环
AGENT_TIMEOUT = 60    # 单步超时时间（秒）
# endregion
# ============================================