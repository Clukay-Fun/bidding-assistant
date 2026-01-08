"""
PDF扫描件解析模块
功能：PDF → 图片 → PaddleOCR识别 → Markdown输出
"""

from pathlib import Path
from pdf2image import convert_from_path
from paddleocr import PaddleOCR
import time

# ============================================
# region 配置区域
# ============================================

POPPLER_PATH = r"D:\.Software\poppler\Library\bin"
OUTPUT_DIR = Path("./output")
OUTPUT_DIR.mkdir(exist_ok=True)

# endregion
# ============================================


# ============================================
# region PDF转图片
# ============================================

def pdf_to_images(pdf_path: str) -> list:
    """将PDF每一页转为图片"""
    print(f"📄 正在将PDF转为图片...")
    images = convert_from_path(
        pdf_path,
        poppler_path=POPPLER_PATH,
        dpi=200
    )
    print(f"✅ 共转换 {len(images)} 页")
    return images

# endregion
# ============================================


# ============================================
# region OCR识别
# ============================================

def ocr_images(images: list) -> list:
    """对每张图片进行OCR识别，返回结构化结果"""
    start_time = time.time()
    
    print("🔧 正在初始化PaddleOCR...")
    ocr = PaddleOCR(
        lang='ch',
        use_doc_orientation_classify=False,
        use_doc_unwarping=False,
        use_textline_orientation=False,
    )
    print("✅ PaddleOCR初始化完成")
    
    all_results = []
    
    for i, image in enumerate(images):
        print(f"🔍 正在识别第 {i+1}/{len(images)} 页...")
        
        try:
            temp_path = OUTPUT_DIR / f"page_{i+1}.png"
            image.save(temp_path)
            
            result = ocr.predict(str(temp_path))
            
            page_text = []
            if result:
                for item in result:
                    if isinstance(item, dict):
                        rec_texts = item.get('rec_texts', [])
                        rec_scores = item.get('rec_scores', [])
                        
                        for j, text in enumerate(rec_texts):
                            page_text.append({
                                "text": text,
                                "confidence": round(rec_scores[j], 3) if j < len(rec_scores) else 0,
                            })
            
            print(f"   ✅ 本页提取 {len(page_text)} 条文本")
            all_results.append({
                "page": i + 1,
                "content": page_text
            })
            
        except Exception as e:
            print(f"   ❌ 第 {i+1} 页识别出错: {str(e)}")
            all_results.append({
                "page": i + 1,
                "content": [],
                "error": str(e)
            })
    
    elapsed = time.time() - start_time
    print(f"\n⏱️ OCR总耗时: {elapsed:.2f} 秒，平均每页: {elapsed/len(images):.2f} 秒")
    return all_results

# endregion
# ============================================


# ============================================
# region 结果转Markdown
# ============================================

def results_to_markdown(results: list, source_name: str) -> str:
    """将OCR结果转换为Markdown格式"""
    md_lines = []
    
    # 文档标题
    md_lines.append(f"# {source_name}\n")
    
    for page in results:
        page_num = page["page"]
        content = page["content"]
        
        # 页码标记
        md_lines.append(f"\n## 第 {page_num} 页\n")
        
        if page.get("error"):
            md_lines.append(f"*[识别出错: {page['error']}]*\n")
        elif content:
            for item in content:
                md_lines.append(item["text"])
        else:
            md_lines.append("*[本页无内容]*\n")
        
        md_lines.append("")  # 空行分隔
    
    return "\n".join(md_lines)

# endregion
# ============================================


# ============================================
# region 主函数
# ============================================

def pdf_to_markdown(pdf_path: str, output_path: str = None, filter_watermark: bool = True) -> str:
    """
    PDF扫描件转Markdown
    
    参数:
        pdf_path: PDF文件路径
        output_path: 输出路径（可选）
        filter_watermark: 是否过滤水印
    
    返回:
        Markdown文件路径
    """
    start_time = time.time()
    print(f"\n📄 正在处理PDF: {pdf_path}")
    
    # 1. PDF转图片
    images = pdf_to_images(pdf_path)
    
    # 2. OCR识别
    results = ocr_images(images)
    
    # 3. 过滤水印（可选）
    if filter_watermark:
        from text_cleaner import filter_watermarks
        print("\n🔍 开始过滤水印")
        results = filter_watermarks(results)
    
    # 4. 转换为Markdown
    source_name = Path(pdf_path).stem
    markdown_content = results_to_markdown(results, source_name)
    
    # 5. 保存文件
    if output_path is None:
        output_path = OUTPUT_DIR / f"{source_name}.md"
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(markdown_content)
    
    elapsed = time.time() - start_time
    print(f"\n✅ Markdown已保存: {output_path}")
    print(f"⏱️ 总耗时: {elapsed:.2f} 秒")
    
    return str(output_path)

# endregion
# ============================================


if __name__ == "__main__":
    test_file = "街道服务业绩20260106.pdf"
    pdf_to_markdown(test_file)