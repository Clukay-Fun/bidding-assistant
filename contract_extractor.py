"""
合同信息提取模块
功能：
1. PDF → 图片（保存为BLOB）
2. OCR识别文本（初步）
3. GLM-4.1V视觉校验 + 结构化提取（精准）
4. 存入数据库
"""

from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI
from pdf2image import convert_from_path
from PIL import Image
import json
import os
import io
import base64
import time

from database import get_session, add_contract, Contract
from text_cleaner import filter_watermarks

# 加载环境变量
load_dotenv()

# ============================================
# region 配置区域
# ============================================

# Poppler路径
POPPLER_PATH = r"D:\.Software\poppler\Library\bin"

# 硅基流动API配置
SILICONFLOW_API_KEY = os.getenv("SILICONFLOW_API_KEY")
SILICONFLOW_BASE_URL = "https://api.siliconflow.cn/v1"

# 模型配置
VISION_MODEL = "THUDM/GLM-4.1V-9B-Thinking"  # 视觉模型（校验+提取）
EXTRACT_MODEL = "Qwen/Qwen3-8B"  # 备用文本模型

# 输出目录
OUTPUT_DIR = Path("./output")
OUTPUT_DIR.mkdir(exist_ok=True)

# endregion
# ============================================

# ============================================
# region 数据清洗
# ============================================

def clean_float(value):
    """清洗浮点数字段"""
    if value is None or value == "" or value == "null":
        return None
    try:
        return float(value)
    except (ValueError, TypeError):
        return None


def clean_bool(value):
    """清洗布尔字段"""
    if value is None:
        return False
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.lower() in ['true', 'yes', '是', '1']
    return bool(value)


def clean_string(value):
    """清洗字符串字段"""
    if value is None or value == "null":
        return None
    return str(value).strip() if value else None

# endregion
# ============================================

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


def blob_to_images(blob_data: bytes) -> list:
    """从BLOB解压图片"""
    import zipfile
    
    images = []
    buffer = io.BytesIO(blob_data)
    
    with zipfile.ZipFile(buffer, 'r') as zf:
        for name in sorted(zf.namelist()):
            img_data = zf.read(name)
            img = Image.open(io.BytesIO(img_data))
            images.append(img)
    
    return images


def image_to_base64(image: Image.Image, max_size: int = 1024) -> str:
    """将图片转换为base64（压缩以节省token）"""
    # 调整大小
    if max(image.size) > max_size:
        ratio = max_size / max(image.size)
        new_size = (int(image.size[0] * ratio), int(image.size[1] * ratio))
        image = image.resize(new_size, Image.Resampling.LANCZOS)
    
    # 转换为base64
    buffer = io.BytesIO()
    image.save(buffer, format='JPEG', quality=85)
    return base64.b64encode(buffer.getvalue()).decode('utf-8')

# endregion
# ============================================


# ============================================
# region OCR识别（初步）
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
# region GLM-4.1V 视觉提取
# ============================================

VISION_EXTRACT_PROMPT = """你是一个专业的法律合同信息提取专家。我会给你合同的扫描图片，请仔细查看图片内容，提取关键信息。

## 重要提示
- 请直接从图片中识别文字，不要依赖OCR参考文本中的错误
- 人名、公司名要完整准确，不要漏字
- 仔细辨认每一个汉字

## 提取字段

1. **contract_name**: 合同名称/标题
2. **party_a**: 甲方名称（委托方）- 请完整准确识别
3. **party_a_id**: 甲方身份证号或统一社会信用代码
4. **party_a_industry**: 甲方所在行业（如：燃气、银行、医疗、个人等）
5. **is_state_owned**: 是否是国企（true/false）
6. **is_individual**: 是否是个人（true/false）
7. **amount**: 合同金额（数字，单位：万元）
8. **fee_method**: 收费方式
9. **sign_date**: 签订日期（格式：YYYY-MM-DD）
10. **project_type**: 项目类型（只能填：常法/诉讼/专项）
11. **project_detail**: 项目详情/服务内容/案件名称
12. **subject_amount**: 标的额（诉讼项目，单位：万元）
13. **opponent**: 对方当事人（诉讼项目）
14. **team_member**: 团队成员/承办律师 - 请完整准确识别每个人的姓名
15. **summary**: 一句话概括合同核心内容（50字以内）

## OCR参考文本（可能有错误，仅供参考）

{ocr_text}

## 输出格式

请直接输出JSON，不要包含```json```标记：
{{
  "contract_name": "...",
  "party_a": "...",
  "party_a_id": "...",
  "party_a_industry": "...",
  "is_state_owned": false,
  "is_individual": false,
  "amount": 0,
  "fee_method": "...",
  "sign_date": "YYYY-MM-DD",
  "project_type": "常法/诉讼/专项",
  "project_detail": "...",
  "subject_amount": null,
  "opponent": null,
  "team_member": "...",
  "summary": "..."
}}
"""


def extract_with_vision(images: list, ocr_text: str, max_pages: int = 5) -> dict:
    """
    使用GLM-4.1V视觉模型提取合同信息
    
    参数:
        images: 图片列表
        ocr_text: OCR识别的参考文本
        max_pages: 最多发送几页图片（控制API消耗）
    """
    print("🤖 GLM-4.1V 视觉提取中...")
    
    client = OpenAI(
        api_key=SILICONFLOW_API_KEY,
        base_url=SILICONFLOW_BASE_URL
    )
    
    # 准备图片（取前几页，通常合同关键信息在前面）
    selected_images = images[:max_pages]
    
    # 构建消息内容
    content = []
    
    # 添加图片
    for i, img in enumerate(selected_images):
        img_base64 = image_to_base64(img)
        content.append({
            "type": "image_url",
            "image_url": {
                "url": f"data:image/jpeg;base64,{img_base64}"
            }
        })
    
    # 添加文本提示
    prompt = VISION_EXTRACT_PROMPT.format(ocr_text=ocr_text[:3000])  # 限制OCR文本长度
    content.append({
        "type": "text",
        "text": prompt
    })
    
    try:
        response = client.chat.completions.create(
            model=VISION_MODEL,
            messages=[
                {
                    "role": "user",
                    "content": content
                }
            ],
            temperature=0.1,
            max_tokens=2000
        )
        
        result_text = response.choices[0].message.content.strip()
        
        # 清理可能的markdown标记和思考过程
        if "```json" in result_text:
            result_text = result_text.split("```json")[1].split("```")[0]
        elif "```" in result_text:
            result_text = result_text.split("```")[1].split("```")[0]
        
        # 尝试找到JSON部分
        if "{" in result_text:
            start = result_text.find("{")
            end = result_text.rfind("}") + 1
            result_text = result_text[start:end]
        
        info = json.loads(result_text.strip())
        print("   ✅ 视觉提取完成")
        return info
        
    except json.JSONDecodeError as e:
        print(f"   ⚠️ JSON解析失败: {e}")
        print(f"   原始输出: {result_text[:500]}...")
        return {}
    except Exception as e:
        print(f"   ❌ 视觉提取失败: {e}")
        return {}

# endregion
# ============================================

# ============================================
# region 缓存功能
# ============================================

import hashlib

CACHE_DIR = Path("./cache")
CACHE_DIR.mkdir(exist_ok=True)


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


def load_cache(file_path: str, cache_type: str):
    """加载缓存"""
    cache_path = get_cache_path(file_path, cache_type)
    if cache_path.exists():
        with open(cache_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return None


def save_cache(file_path: str, cache_type: str, data):
    """保存缓存"""
    cache_path = get_cache_path(file_path, cache_type)
    with open(cache_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# endregion
# ============================================

# ============================================
# region 备用：纯文本提取
# ============================================

EXTRACT_PROMPT = """你是一个专业的法律合同信息提取专家。请从以下合同文本中提取关键信息。

## 提取字段

1. **contract_name**: 合同名称
2. **party_a**: 甲方名称
3. **party_a_id**: 甲方身份证/统一社会信用代码
4. **party_a_industry**: 甲方所在行业
5. **is_state_owned**: 是否国企（true/false）
6. **is_individual**: 是否个人（true/false）
7. **amount**: 合同金额（万元）
8. **fee_method**: 收费方式
9. **sign_date**: 签订日期（YYYY-MM-DD）
10. **project_type**: 项目类型（常法/诉讼/专项）
11. **project_detail**: 项目详情
12. **subject_amount**: 标的额（诉讼项目，万元）
13. **opponent**: 对方当事人（诉讼项目）
14. **team_member**: 团队成员
15. **summary**: 一句话概括（50字内）

## 输出JSON格式（不要```标记）

## 合同文本

"""


def extract_with_text(text: str) -> dict:
    """备用：使用纯文本模型提取（不消耗视觉API）"""
    print("🤖 文本模型提取中（备用）...")
    
    client = OpenAI(
        api_key=SILICONFLOW_API_KEY,
        base_url=SILICONFLOW_BASE_URL
    )
    
    try:
        response = client.chat.completions.create(
            model=EXTRACT_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": "你是专业的法律合同信息提取专家。请严格按JSON格式输出。"
                },
                {
                    "role": "user",
                    "content": EXTRACT_PROMPT + text[:8000]
                }
            ],
            temperature=0.1,
            max_tokens=2000
        )
        
        result_text = response.choices[0].message.content.strip()
        
        if result_text.startswith("```"):
            result_text = result_text.split("```")[1]
            if result_text.startswith("json"):
                result_text = result_text[4:]
        if result_text.endswith("```"):
            result_text = result_text[:-3]
        
        return json.loads(result_text.strip())
        
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
    
    参数:
        pdf_path: PDF文件路径
        save_to_db: 是否保存到数据库
        use_vision: 是否使用视觉模型
        use_cache: 是否使用缓存
    """
    start_time = time.time()
    
    print("\n" + "="*50)
    print(f"📄 处理合同: {pdf_path}")
    print("="*50)
    
    file_name = Path(pdf_path).name
    
    
    # 检查是否有完整缓存
    if use_cache:
        cached_result = load_cache(pdf_path, "result")
        if cached_result:
            print("   📦 使用缓存结果")
            return cached_result
    
    # 1. PDF转图片（检查缓存）
    images = None
    image_blob = None
    
    if use_cache:
        cached_images = load_cache(pdf_path, "images_meta")
        if cached_images:
            print("   📦 使用缓存图片信息")
            # 重新转换图片（因为图片对象不能缓存）
            images = pdf_to_images(pdf_path)
            image_blob = images_to_blob(images)
        
    if images is None:
        images = pdf_to_images(pdf_path)
        print("💾 压缩图片为BLOB...")
        image_blob = images_to_blob(images)
        print(f"   ✅ BLOB大小: {len(image_blob) / 1024 / 1024:.2f} MB")
        
        if use_cache:
            save_cache(pdf_path, "images_meta", {"page_count": len(images)})
    
    # 2. OCR识别（检查缓存）
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
    
    # 3. AI提取信息
    if use_vision:
        info = extract_with_vision(images, raw_text)
    else:
        info = extract_with_text(raw_text)
    
    # 如果视觉提取失败，回退到文本提取
    if not info and use_vision:
        print("   ⚠️ 视觉提取失败，尝试文本提取...")
        info = extract_with_text(raw_text)
    
    # 4. 保存到数据库
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
    
    # 5. 缓存完整结果
    if use_cache and info:
        save_cache(pdf_path, "result", info)
    
    elapsed = time.time() - start_time
    print(f"\n⏱️ 总耗时: {elapsed:.2f} 秒")
    
    return info
# endregion
# ============================================

# ============================================
# region 批量处理
# ============================================

def batch_process_contracts(
    folder_path: str,
    use_vision: bool = True,
    use_cache: bool = True
) -> list:
    """
    批量处理文件夹中的所有合同PDF
    
    参数:
        folder_path: 文件夹路径
        use_vision: 是否使用视觉模型
        use_cache: 是否使用缓存
    
    返回:
        处理结果列表
    """
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
    
    return results

# endregion
# ============================================

# ============================================
# region 测试入口
# ============================================

if __name__ == "__main__":
    import sys
    
    # 默认路径
    default_folder = "./documents/业绩"
    
    # 支持命令行参数
    if len(sys.argv) > 1:
        path = sys.argv[1]
    else:
        path = default_folder
    
    from pathlib import Path
    
    if Path(path).is_file():
        # 单个文件
        info = process_contract_pdf(path, use_vision=True)
        
        print("\n" + "="*50)
        print("📋 提取结果预览")
        print("="*50)
        for key, value in info.items():
            if key != "db_id":
                print(f"   {key}: {value}")
    
    elif Path(path).is_dir():
        # 批量处理文件夹
        results = batch_process_contracts(path, use_vision=False)
        
        # 保存处理报告
        import json
        report_path = Path("./output/batch_report.json")
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        print(f"\n📄 处理报告已保存: {report_path}")
    
    else:
        print(f"❌ 路径不存在: {path}")

# endregion
# ============================================