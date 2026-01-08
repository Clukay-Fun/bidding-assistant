from collections import Counter
from rapidfuzz import fuzz

# region filter_watermarks 通用水印过滤器
def filter_watermarks(
    results: list,
    freq_threshold_ratio: float = 0.5,
    max_watermark_len: int = 12,
    similarity_threshold: float = 70.0
) -> list:
    """
    通用水印过滤器
    
    参数:
        results: OCR识别结果列表
        freq_threshold_ratio: 频率阈值比例（出现次数 > 总页数 * 该比例 视为高频）
        max_watermark_len: 水印最大长度（超过此长度的文本不会被识别为水印）
        similarity_threshold: 相似度阈值（0-100，与候选水印相似度超过此值则过滤）
    
    返回:
        过滤水印后的结果列表
    """
    total_pages = len(results)
    freq_threshold = max(total_pages * freq_threshold_ratio, 3)  # 至少出现3次才算高频
    
    # 第一步：统计所有文本的出现频率
    text_counter = Counter()
    for page in results:
        for item in page["content"]:
            text_counter[item["text"]] += 1
    
    # 第二步：筛选候选水印（高频+短文本）
    print(f"📊 总页数: {total_pages}, 频率阈值: {freq_threshold}")
    candidate_watermarks = set()
    for text,count in text_counter.items():
        is_high_freq = count >= freq_threshold
        is_short = len(text) <= max_watermark_len
        
        if is_high_freq and is_short:
            candidate_watermarks.add(text)
    print(f"📋 发现 {len(candidate_watermarks)} 个候选水印:")
    for wm in candidate_watermarks:
        print(f"   - '{wm}' (出现 {text_counter[wm]} 次)")
    
    # 第三步：定义水印匹配函数
    def is_watermark(text:str)->bool:
        # 完全匹配
        if text in candidate_watermarks:
            return True
        
        # 模糊匹配：与任意候选水印相似度超过阈值
        for wm in candidate_watermarks:
            similarity = fuzz.ratio(text,wm)
            if similarity >= similarity_threshold:
                return True
        return False
    
    # 第四步：过滤水印
    filtered_results = []
    removed_count = 0
    
    for page in results:
        new_content = []
        for item in page["content"]:
            if is_watermark(item["text"]):
                removed_count += 1
            else:
                new_content.append(item)
        
        filtered_results.append({
            "page": page["page"],
            "content": new_content
        })
        
    print(f"🗑️ 共过滤 {removed_count} 条水印文本")
    return filtered_results
# endregion