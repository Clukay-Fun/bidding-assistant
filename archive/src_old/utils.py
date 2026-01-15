"""
工具函数模块
"""

import hashlib
import json
from pathlib import Path
from typing import Any, Optional

# 导入配置
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from config.settings import CACHE_DIR, PROMPTS_DIR


# ============================================
# region 缓存功能
# ============================================

def get_file_hash(file_path: str) -> str:
    """计算文件的MD5哈希"""
    hasher = hashlib.md5()
    with open(file_path, 'rb') as f:
        for chunk in iter(lambda: f.read(8192), b''):
            hasher.update(chunk)
    return hasher.hexdigest()


def get_cache_path(file_path: str, cache_type: str) -> Path:
    """获取缓存文件路径"""
    file_hash = get_file_hash(file_path)
    return CACHE_DIR / f"{file_hash}_{cache_type}.json"


def load_cache(file_path: str, cache_type: str) -> Optional[Any]:
    """加载缓存"""
    cache_path = get_cache_path(file_path, cache_type)
    if cache_path.exists():
        with open(cache_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return None


def save_cache(file_path: str, cache_type: str, data: Any) -> None:
    """保存缓存"""
    cache_path = get_cache_path(file_path, cache_type)
    with open(cache_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def clear_cache(file_path: str = None) -> int:
    """
    清除缓存
    
    参数:
        file_path: 指定文件路径，为None则清除所有缓存
    
    返回:
        清除的文件数量
    """
    count = 0
    
    if file_path:
        file_hash = get_file_hash(file_path)
        for cache_file in CACHE_DIR.glob(f"{file_hash}_*.json"):
            cache_file.unlink()
            count += 1
    else:
        for cache_file in CACHE_DIR.glob("*.json"):
            cache_file.unlink()
            count += 1
    
    return count

# endregion
# ============================================


# ============================================
# region 提示词加载
# ============================================

def load_prompt(prompt_name: str, **kwargs) -> str:
    """
    加载并格式化提示词模板
    
    参数:
        prompt_name: 提示词文件名（不含扩展名）
        **kwargs: 格式化参数
    
    返回:
        格式化后的提示词
    """
    prompt_path = PROMPTS_DIR / f"{prompt_name}.md"
    
    if not prompt_path.exists():
        raise FileNotFoundError(f"提示词文件不存在: {prompt_path}")
    
    with open(prompt_path, 'r', encoding='utf-8') as f:
        template = f.read()
    
    # 如果有参数，进行格式化
    if kwargs:
        # 处理JSON中的大括号（避免与format冲突）
        # 先替换示例中的大括号
        template = template.replace('```\n{', '```\n{{')
        template = template.replace('}\n```', '}}\n```')
        
        try:
            template = template.format(**kwargs)
        except KeyError:
            # 如果格式化失败，返回原模板
            pass
    
    return template

# endregion
# ============================================


# ============================================
# region 数据清洗
# ============================================

def clean_float(value: Any) -> Optional[float]:
    """清洗浮点数字段"""
    if value is None or value == "" or value == "null":
        return None
    try:
        return float(value)
    except (ValueError, TypeError):
        return None


def clean_bool(value: Any) -> bool:
    """清洗布尔字段"""
    if value is None:
        return False
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.lower() in ['true', 'yes', '是', '1']
    return bool(value)


def clean_string(value: Any) -> Optional[str]:
    """清洗字符串字段"""
    if value is None or value == "null":
        return None
    return str(value).strip() if value else None


def clean_json_response(text: str) -> str:
    """清理AI返回的JSON文本"""
    # 移除markdown代码块标记
    if "```json" in text:
        text = text.split("```json")[1].split("```")[0]
    elif "```" in text:
        parts = text.split("```")
        if len(parts) >= 2:
            text = parts[1]
    
    # 提取JSON部分
    if "{" in text:
        start = text.find("{")
        end = text.rfind("}") + 1
        text = text[start:end]
    
    return text.strip()

# endregion
# ============================================


# ============================================
# region 文件处理
# ============================================

def get_file_type(file_path: str) -> str:
    """获取文件类型"""
    suffix = Path(file_path).suffix.lower()
    
    type_map = {
        '.pdf': 'pdf',
        '.docx': 'docx',
        '.doc': 'doc',
        '.md': 'markdown',
        '.txt': 'text',
    }
    
    return type_map.get(suffix, 'unknown')


def ensure_dir(dir_path: str) -> Path:
    """确保目录存在"""
    path = Path(dir_path)
    path.mkdir(parents=True, exist_ok=True)
    return path

# endregion
# ============================================


# ============================================
# region 格式化输出
# ============================================

def print_header(title: str, char: str = "=", width: int = 50) -> None:
    """打印标题"""
    print(f"\n{char * width}")
    print(f"  {title}")
    print(f"{char * width}")


def print_result(label: str, value: Any, indent: int = 0) -> None:
    """打印结果"""
    prefix = "  " * indent
    print(f"{prefix}{label}: {value}")


def format_amount(amount: Optional[float]) -> str:
    """格式化金额"""
    if amount is None:
        return "未知"
    if amount >= 10000:
        return f"{amount/10000:.2f}亿元"
    elif amount >= 1:
        return f"{amount:.2f}万元"
    else:
        return f"{amount*10000:.0f}元"

# endregion
# ============================================
