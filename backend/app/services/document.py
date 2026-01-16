"""
文档解析服务
使用 markitdown 将 PDF/Word 转换为 Markdown
"""

import io
from typing import Optional
from markitdown import MarkItDown

# ============================================
# region 配置
# ============================================

_markitdown_instance = None

def get_markitdown() -> MarkItDown:
    """获取 MarkItDown 实例（单例）"""
    global _markitdown_instance
    
    if _markitdown_instance is None:
        _markitdown_instance = MarkItDown()
    
    return _markitdown_instance

# endregion
# ============================================


# ============================================
# region PDF 转 Markdown
# ============================================

def pdf_to_markdown(pdf_path: Optional[str] = None, pdf_bytes: Optional[bytes] = None) -> str:
    """
    将 PDF 转换为 Markdown
    
    参数:
        pdf_path: PDF 文件路径（二选一）
        pdf_bytes: PDF 字节流（二选一）
    返回:
        Markdown 文本
    """
    md = get_markitdown()
    
    if pdf_path:
        result = md.convert(pdf_path)
        return result.text_content
    elif pdf_bytes:
        # markitdown 支持 file-like object
        result = md.convert_stream(io.BytesIO(pdf_bytes), file_extension=".pdf")
        return result.text_content
    else:
        raise ValueError("必须提供 pdf_path 或 pdf_bytes")

# endregion
# ============================================


# ============================================
# region Word 转 Markdown
# ============================================

def word_to_markdown(word_path: Optional[str] = None, word_bytes: Optional[bytes] = None) -> str:
    """
    将 Word 文档转换为 Markdown
    
    参数:
        word_path: Word 文件路径（二选一）
        word_bytes: Word 字节流（二选一）
    返回:
        Markdown 文本
    """
    md = get_markitdown()
    
    if word_path:
        result = md.convert(word_path)
        return result.text_content
    elif word_bytes:
        result = md.convert_stream(io.BytesIO(word_bytes), file_extension=".docx")
        return result.text_content
    else:
        raise ValueError("必须提供 word_path 或 word_bytes")

# endregion
# ============================================


# ============================================
# region 通用文档转换
# ============================================

def document_to_markdown(
    file_path: Optional[str] = None,
    file_bytes: Optional[bytes] = None,
    file_extension: Optional[str] = None,
) -> str:
    """
    通用文档转 Markdown
    
    参数:
        file_path: 文件路径
        file_bytes: 文件字节流
        file_extension: 文件扩展名（如 .pdf, .docx）
    返回:
        Markdown 文本
    """
    md = get_markitdown()
    
    if file_path:
        result = md.convert(file_path)
        return result.text_content
    elif file_bytes and file_extension:
        result = md.convert_stream(io.BytesIO(file_bytes), file_extension=file_extension)
        return result.text_content
    else:
        raise ValueError("必须提供 file_path，或者 file_bytes + file_extension")

# endregion
# ============================================
