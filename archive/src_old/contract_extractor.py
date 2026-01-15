"""
合同信息提取模块
功能：
1. PDF → 图片（保存为BLOB）
2. OCR识别文本（初步）
3. GLM-4.1V视觉校验 + 结构化提取（精准）
4. 存入数据库
"""

from pathlib import Path
from openai import OpenAI
from pdf2image import convert_from_path
from PIL import Image
import json
import io
import base64
import time
import sys

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from config.settings import (
    POPPLER_PATH,
    SILICONFLOW_API_KEY,
    SILICONFLOW_BASE_URL,
    EXTRACT_MODEL,
    VISION_MODEL,
    OUTPUT_DIR,
    CACHE_DIR
)
from src.database import get_session, add_contract
from src.text_cleaner import filter_watermarks
from src.utils import (
    load_prompt, 
    clean_json_response, 
    clean_float, 
    clean_bool, 
    clean_string,
    load_cache,
    save_cache,
    get_file_hash
)


# ============================================
# region PDF处理
# ============================================

def pdf_to_images(pdf_path: str, dpi: int = 200) -> list:
    """将PDF转换为图片列表"""
    print(f"📄 正在将PDF转为图片: {pdf_path}")
    
    images = convert_from_path(
        pdf_path,
        poppler_path=POPPLER_PATH,
        dpi=dpi
    )
    
    print(f"   ✅ 共转换 {len(images)} 页")
    return images


def images_to_blob(images: list) -> bytes:
    """将多张图片合并为单个BLOB（ZIP格式）"""
    import zipfile
    
    buffer = io.BytesIO()
    
    with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
        for i, img in enumerate(images):
            img_buffer = io.BytesIO()
            img.save(img_buffer, format='PNG')
            zf.writestr(f"page_{i+1}.png", img_buffer.getvalue())
    
    return buffer.getvalue()


def image_to_base64(image: Image.Image, max_size: int = 1024) -> str:
    """将图片转换为base64（压缩以节省token）"""
    if max(image.size) > max_size:
        ratio = max_size / max(image.size)
        new_size = (int(image.size[0] * ratio), int(image.size[1] * ratio))
        image = image.resize(new_size, Image.Resampling.LANCZOS)
    
    buffer = io.BytesIO()
    image.save(buffer, format='JPEG', quality=85)
    return base64.b64encode(buffer.getvalue()).decode('utf-8')

# endregion
# ============================================


# ============================================
# region OCR识别
# ============================================

def ocr_images(images: list) -> str:
    """对图片进行OCR识别，返回合并的文本"""
    from paddleocr import PaddleOCR
    
    print("🔧 正在进行OCR识别（初步）...")
    
    ocr = PaddleOCR(
        lang='ch',
        use_doc_orientation_classify=False,
        use_doc_unwarping=False,
        use_textline_orientation=False,
    )
    
    all_results = []
    
    for i, image in enumerate(images):
        print(f"   🔍 识别第 {i+1}/{len(images)} 页...")
        
        temp_path = OUTPUT_DIR / f"temp_page_{i+1}.png"
        image.save(temp_path)
        
        result = ocr.predict(str(temp_path))
        
        page_text = []
        if result:
            for item in result:
                if isinstance(item, dict):
                    rec_texts = item.get('rec_texts', [])
                    for text in rec_texts:
                        page_text.append(text)
        
        all_results.append({
            "page": i + 1,
            "content": [{"text": t, "confidence": 0.9} for t in page_text]
        })
        
        temp_path.unlink(missing_ok=True)
    
    # 过滤水印
    print("   🔍 过滤水印...")
    filtered_results = filter_watermarks(all_results)
    
    # 合并文本
    full_text = ""
    for page in filtered_results:
        full_text += f"\n--- 第{page['page']}页 ---\n"
        for item in page['content']:
            full_text += item['text'] + "\n"
    
    print(f"   ✅ OCR完成，共提取 {len(full_text)} 字符")
    return full_text

# endregion
# ============================================


# ============================================
# region AI提取
# ============================================

def extract_with_vision(images: list, ocr_text: str, max_pages: int = 5) -> dict:
    """使用GLM-4.1V视觉模型提取合同信息"""
    print("🤖 GLM-4.1V 视觉提取中...")
    
    client = OpenAI(
        api_key=SILICONFLOW_API_KEY,
        base_url=SILICONFLOW_BASE_URL
    )
    
    selected_images = images[:max_pages]
    
    content = []
    
    for i, img in enumerate(selected_images):
        img_base64 = image_to_base64(img)
        content.append({
            "type": "image_url",
            "image_url": {
                "url": f"data:image/jpeg;base64,{img_base64}"
            }
        })
    
    # 加载提示词
    prompt_template = load_prompt("contract_extract_vision")
    prompt = prompt_template.replace("{ocr_text}", ocr_text[:3000])
    
    content.append({
        "type": "text",
        "text": prompt
    })
    
    try:
        response = client.chat.completions.create(
            model=VISION_MODEL,
            messages=[{"role": "user", "content": content}],
            temperature=0.1,
            max_tokens=2000
        )
        
        result_text = response.choices[0].message.content.strip()
        result_text = clean_json_response(result_text)
        
        info = json.loads(result_text)
        print("   ✅ 视觉提取完成")
        return info
        
    except json.JSONDecodeError as e:
        print(f"   ⚠️ JSON解析失败: {e}")
        return {}
    except Exception as e:
        print(f"   ❌ 视觉提取失败: {e}")
        return {}


def extract_with_text(text: str) -> dict:
    """备用：使用纯文本模型提取"""
    print("🤖 文本模型提取中（备用）...")
    
    client = OpenAI(
        api_key=SILICONFLOW_API_KEY,
        base_url=SILICONFLOW_BASE_URL
    )
    
    try:
        prompt_template = load_prompt("contract_extract")
        prompt = prompt_template.replace("{contract_text}", text[:8000])
        
        response = client.chat.completions.create(
            model=EXTRACT_MODEL,
            messages=[
                {"role": "system", "content": "你是专业的法律合同信息提取专家。请严格按JSON格式输出。"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,
            max_tokens=2000
        )
        
        result_text = response.choices[0].message.content.strip()
        result_text = clean_json_response(result_text)
        
        return json.loads(result_text)
        
    except Exception as e:
        print(f"   ❌ 文本提取失败: {e}")
        return {}

# endregion
# ============================================


# ============================================
# region 主处理流程
# ============================================

def process_contract_pdf(
    pdf_path: str, 
    save_to_db: bool = True,
    use_vision: bool = True,
    use_cache: bool = True
) -> dict:
    """
    处理单个合同PDF
    """
    start_time = time.time()
    
    print("\n" + "="*50)
    print(f"📄 处理合同: {pdf_path}")
    print("="*50)
    
    file_name = Path(pdf_path).name
    
    # 检查缓存
    if use_cache:
        cached_result = load_cache(pdf_path, "result")
        if cached_result:
            print("   📦 使用缓存结果")
            return cached_result
    
    # 1. PDF转图片
    images = pdf_to_images(pdf_path)
    
    # 2. 图片转BLOB
    print("💾 压缩图片为BLOB...")
    image_blob = images_to_blob(images)
    print(f"   ✅ BLOB大小: {len(image_blob) / 1024 / 1024:.2f} MB")
    
    # 3. OCR识别（检查缓存）
    raw_text = None
    if use_cache:
        cached_ocr = load_cache(pdf_path, "ocr")
        if cached_ocr:
            print("   📦 使用缓存OCR结果")
            raw_text = cached_ocr.get("text", "")
    
    if raw_text is None:
        raw_text = ocr_images(images)
        if use_cache:
            save_cache(pdf_path, "ocr", {"text": raw_text})
    
    # 4. AI提取信息
    if use_vision:
        info = extract_with_vision(images, raw_text)
    else:
        info = extract_with_text(raw_text)
    
    if not info and use_vision:
        print("   ⚠️ 视觉提取失败，尝试文本提取...")
        info = extract_with_text(raw_text)
    
    # 5. 保存到数据库
    if save_to_db and info:
        print("💾 保存到数据库...")
        
        session = get_session()
        try:
            contract = add_contract(
                session,
                file_name=file_name,
                contract_name=clean_string(info.get("contract_name")),
                party_a=clean_string(info.get("party_a")),
                party_a_id=clean_string(info.get("party_a_id")),
                party_a_industry=clean_string(info.get("party_a_industry")),
                is_state_owned=clean_bool(info.get("is_state_owned")),
                is_individual=clean_bool(info.get("is_individual")),
                amount=clean_float(info.get("amount")),
                fee_method=clean_string(info.get("fee_method")),
                sign_date=clean_string(info.get("sign_date")),
                project_type=clean_string(info.get("project_type")),
                project_detail=clean_string(info.get("project_detail")),
                subject_amount=clean_float(info.get("subject_amount")),
                opponent=clean_string(info.get("opponent")),
                team_member=clean_string(info.get("team_member")),
                summary=clean_string(info.get("summary")),
                image_data=image_blob,
                image_count=len(images),
                raw_text=raw_text
            )
            print(f"   ✅ 已保存，ID: {contract.id}")
            info["db_id"] = contract.id
        except Exception as e:
            print(f"   ❌ 保存失败: {e}")
        finally:
            session.close()
    
    # 6. 缓存结果
    if use_cache and info:
        save_cache(pdf_path, "result", info)
    
    elapsed = time.time() - start_time
    print(f"\n⏱️ 总耗时: {elapsed:.2f} 秒")
    
    return info


def batch_process_contracts(
    folder_path: str,
    use_vision: bool = True,
    use_cache: bool = True
) -> list:
    """批量处理文件夹中的所有合同PDF"""
    folder = Path(folder_path)
    pdf_files = list(folder.glob("*.pdf"))
    
    print("\n" + "="*50)
    print(f"📂 批量处理合同")
    print("="*50)
    print(f"📁 文件夹: {folder_path}")
    print(f"📄 发现 {len(pdf_files)} 个PDF文件")
    print(f"🤖 使用视觉模型: {'是' if use_vision else '否'}")
    print(f"📦 使用缓存: {'是' if use_cache else '否'}")
    
    results = []
    
    for i, pdf_file in enumerate(pdf_files, 1):
        print(f"\n{'='*50}")
        print(f"[{i}/{len(pdf_files)}] {pdf_file.name}")
        print("="*50)
        
        try:
            info = process_contract_pdf(
                str(pdf_file), 
                save_to_db=True,
                use_vision=use_vision,
                use_cache=use_cache
            )
            results.append({
                "file": str(pdf_file),
                "status": "success",
                "info": info
            })
        except Exception as e:
            print(f"❌ 处理失败: {e}")
            results.append({
                "file": str(pdf_file),
                "status": "failed",
                "error": str(e)
            })
    
    # 统计结果
    success = len([r for r in results if r["status"] == "success"])
    failed = len([r for r in results if r["status"] == "failed"])
    
    print("\n" + "="*50)
    print(f"📊 批量处理完成")
    print("="*50)
    print(f"   ✅ 成功: {success}")
    print(f"   ❌ 失败: {failed}")
    print(f"   📁 总计: {len(pdf_files)}")
    
    # 保存报告
    report_path = OUTPUT_DIR / "batch_report.json"
    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"📄 处理报告已保存: {report_path}")
    
    return results

# endregion
# ============================================


if __name__ == "__main__":
    if len(sys.argv) > 1:
        path = sys.argv[1]
        use_vision = "--no-vision" not in sys.argv
        
        if Path(path).is_file():
            info = process_contract_pdf(path, use_vision=use_vision)
            print("\n📋 提取结果:")
            for k, v in info.items():
                if k != "db_id":
                    print(f"   {k}: {v}")
        elif Path(path).is_dir():
            batch_process_contracts(path, use_vision=use_vision)
    else:
        print("用法:")
        print("  python -m src.contract_extractor <PDF文件路径>")
        print("  python -m src.contract_extractor <文件夹路径>")
        print("  python -m src.contract_extractor <路径> --no-vision")
