"""
文本清洗模块
功能：过滤水印、清理OCR结果
"""

from collections import Counter
from rapidfuzz import fuzz


# ============================================
# region 水印过滤
# ============================================

def filter_watermarks(
    ocr_results: list,
    freq_threshold_ratio: float = 0.5,
    min_threshold: int = 3,
    similarity_threshold: float = 70.0,
    max_watermark_len: int = 12
) -> list:
    """
    过滤OCR结果中的水印文本
    
    参数:
        ocr_results: OCR结果列表，格式为 [{"page": 1, "content": [{"text": "..."}]}]
        freq_threshold_ratio: 频率阈值比例（相对于总页数）
        min_threshold: 最小频率阈值
        similarity_threshold: 模糊匹配相似度阈值
        max_watermark_len: 水印最大长度
    
    返回:
        过滤后的OCR结果
    """
    # 统计所有文本的出现频率
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
    
    print(f"📊 总页数: {total_pages}, 频率阈值: {freq_threshold}")
    print(f"📋 发现 {len(candidate_watermarks)} 个候选水印:")
    for wm in candidate_watermarks:
        print(f"   - \"{wm}\" (出现 {text_counter[wm]} 次)")
    
    # 定义水印判断函数
    def is_watermark(text: str) -> bool:
        if not text or len(text) > max_watermark_len:
            return False
        
        # 精确匹配
        if text in candidate_watermarks:
            return True
        
        # 模糊匹配
        for wm in candidate_watermarks:
            if fuzz.ratio(text, wm) >= similarity_threshold:
                return True
        
        return False
    
    # 过滤水印
    filtered_results = []
    watermark_count = 0
    
    for page in ocr_results:
        filtered_content = []
        
        for item in page.get("content", []):
            text = item.get("text", "").strip()
            
            if is_watermark(text):
                watermark_count += 1
            else:
                # 替换可能破坏Markdown的字符
                cleaned_text = text.replace("|", "｜")
                filtered_content.append({
                    "text": cleaned_text,
                    "confidence": item.get("confidence", 0)
                })
        
        filtered_results.append({
            "page": page["page"],
            "content": filtered_content
        })
    
    print(f"🗑️ 共过滤 {watermark_count} 条水印文本")
    
    return filtered_results

# endregion
# ============================================


if __name__ == "__main__":
    # 测试
    test_data = [
        {"page": 1, "content": [{"text": "正文内容"}, {"text": "仅限于投标使用"}]},
        {"page": 2, "content": [{"text": "更多内容"}, {"text": "仅限于投标使用"}]},
    ]
    
    result = filter_watermarks(test_data)
    print("\n过滤后结果:")
    for page in result:
        print(f"第{page['page']}页: {[item['text'] for item in page['content']]}")
