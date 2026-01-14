"""
OCR 识别服务
整合自 src/ocr_parser.py，提供 PDF 转文本功能
"""

import io
from pathlib import Path
from typing import List, Optional
from PIL import Image

from app.config import BACKEND_DIR


# ============================================
# region 配置
# ============================================

# Poppler 路径（从环境变量或默认路径）
import os
POPPLER_PATH = os.getenv("POPPLER_PATH", r"D:\.Software\poppler\Library\bin")

# OCR 配置
OCR_DPI = 200
OCR_LANG = "ch"

# 临时文件目录
TEMP_DIR = BACKEND_DIR / "temp"
TEMP_DIR.mkdir(exist_ok=True)

# endregion
# ============================================


# ============================================
# region PDF 转图片
# ============================================

def pdf_to_images(pdf_path: str, dpi: int = OCR_DPI) -> List[Image.Image]:
    """
    将 PDF 转换为图片列表
    
    参数:
        pdf_path: PDF 文件路径
        dpi: 分辨率
    返回:
        PIL Image 列表
    """
    from pdf2image import convert_from_path
    
    images = convert_from_path(
        pdf_path,
        poppler_path=POPPLER_PATH,
        dpi=dpi,
    )
    
    return images


def pdf_bytes_to_images(pdf_bytes: bytes, dpi: int = OCR_DPI) -> List[Image.Image]:
    """
    将 PDF 字节流转换为图片列表
    
    参数:
        pdf_bytes: PDF 文件字节
        dpi: 分辨率
    返回:
        PIL Image 列表
    """
    from pdf2image import convert_from_bytes
    
    images = convert_from_bytes(
        pdf_bytes,
        poppler_path=POPPLER_PATH,
        dpi=dpi,
    )
    
    return images

# endregion
# ============================================


# ============================================
# region OCR 识别
# ============================================

_ocr_instance = None

def get_ocr_instance():
    """获取 PaddleOCR 实例（单例）"""
    global _ocr_instance
    
    if _ocr_instance is None:
        from paddleocr import PaddleOCR
        _ocr_instance = PaddleOCR(
            lang=OCR_LANG,
            use_doc_orientation_classify=False,
            use_doc_unwarping=False,
            use_textline_orientation=False,
        )
    
    return _ocr_instance


def ocr_image(image: Image.Image) -> List[dict]:
    """
    对单张图片进行 OCR 识别
    
    参数:
        image: PIL Image
    返回:
        识别结果列表 [{"text": "...", "confidence": 0.9}, ...]
    """
    import tempfile
    
    ocr = get_ocr_instance()
    
    # 保存为临时文件
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
        temp_path = f.name
        image.save(temp_path)
    
    try:
        result = ocr.predict(temp_path)
        
        texts = []
        if result:
            for item in result:
                if isinstance(item, dict):
                    rec_texts = item.get("rec_texts", [])
                    rec_scores = item.get("rec_scores", [])
                    
                    for i, text in enumerate(rec_texts):
                        confidence = rec_scores[i] if i < len(rec_scores) else 0.0
                        texts.append({
                            "text": text,
                            "confidence": round(confidence, 3),
                        })
        
        return texts
    finally:
        # 清理临时文件
        Path(temp_path).unlink(missing_ok=True)


def ocr_images(images: List[Image.Image]) -> List[dict]:
    """
    对多张图片进行 OCR 识别
    
    参数:
        images: PIL Image 列表
    返回:
        按页组织的结果 [{"page": 1, "content": [...]}, ...]
    """
    results = []
    
    for i, image in enumerate(images, 1):
        page_texts = ocr_image(image)
        results.append({
            "page": i,
            "content": page_texts,
        })
    
    return results

# endregion
# ============================================


# ============================================
# region 水印过滤
# ============================================

def filter_watermarks(
    ocr_results: List[dict],
    freq_threshold_ratio: float = 0.5,
    min_threshold: int = 3,
    similarity_threshold: float = 70.0,
    max_watermark_len: int = 12,
) -> List[dict]:
    """
    过滤 OCR 结果中的水印文本
    
    参数:
        ocr_results: OCR 结果
        freq_threshold_ratio: 频率阈值比例
        min_threshold: 最小频率阈值
        similarity_threshold: 模糊匹配相似度阈值
        max_watermark_len: 水印最大长度
    返回:
        过滤后的结果
    """
    from collections import Counter
    from rapidfuzz import fuzz
    
    # 统计文本频率
    text_counter = Counter()
    total_pages = len(ocr_results)
    
    for page in ocr_results:
        for item in page.get("content", []):
            text = item.get("text", "").strip()
            if text and len(text) <= max_watermark_len:
                text_counter[text] += 1
    
    # 计算频率阈值
    freq_threshold = max(total_pages * freq_threshold_ratio, min_threshold)
    
    # 筛选候选水印
    candidate_watermarks = {
        text for text, count in text_counter.items()
        if count >= freq_threshold
    }
    
    # 水印判断函数
    def is_watermark(text: str) -> bool:
        if not text or len(text) > max_watermark_len:
            return False
        if text in candidate_watermarks:
            return True
        for wm in candidate_watermarks:
            if fuzz.ratio(text, wm) >= similarity_threshold:
                return True
        return False
    
    # 过滤水印
    filtered_results = []
    
    for page in ocr_results:
        filtered_content = []
        
        for item in page.get("content", []):
            text = item.get("text", "").strip()
            if not is_watermark(text):
                filtered_content.append({
                    "text": text.replace("|", "｜"),
                    "confidence": item.get("confidence", 0),
                })
        
        filtered_results.append({
            "page": page["page"],
            "content": filtered_content,
        })
    
    return filtered_results

# endregion
# ============================================


# ============================================
# region 主函数
# ============================================

def extract_text_from_pdf(
    pdf_path: Optional[str] = None,
    pdf_bytes: Optional[bytes] = None,
    filter_watermark: bool = True,
) -> dict:
    """
    从 PDF 提取文本
    
    参数:
        pdf_path: PDF 文件路径（二选一）
        pdf_bytes: PDF 字节流（二选一）
        filter_watermark: 是否过滤水印
    返回:
        {
            "pages": [...],
            "full_text": "...",
            "page_count": 10,
        }
    """
    # 转换为图片
    if pdf_path:
        images = pdf_to_images(pdf_path)
    elif pdf_bytes:
        images = pdf_bytes_to_images(pdf_bytes)
    else:
        raise ValueError("必须提供 pdf_path 或 pdf_bytes")
    
    # OCR 识别
    ocr_results = ocr_images(images)
    
    # 过滤水印
    if filter_watermark:
        ocr_results = filter_watermarks(ocr_results)
    
    # 合并全文
    full_text = ""
    for page in ocr_results:
        full_text += f"\n--- 第{page['page']}页 ---\n"
        for item in page["content"]:
            full_text += item["text"] + "\n"
    
    return {
        "pages": ocr_results,
        "full_text": full_text.strip(),
        "page_count": len(images),
    }

# endregion
# ============================================