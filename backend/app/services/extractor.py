"""
合同信息提取服务
整合自 src/contract_extractor.py，使用视觉模型提取合同关键信息
"""

import json
import base64
import io
from typing import List, Optional
from PIL import Image
from openai import OpenAI

from app.config import (
    SILICONFLOW_API_KEY,
    SILICONFLOW_BASE_URL,
    EXTRACT_MODEL,
)


# ============================================
# region 配置
# ============================================

# 视觉模型（用于图片识别）
VISION_MODEL = "THUDM/GLM-4.1V-9B-Thinking"

# 提取提示词
EXTRACT_PROMPT = """
请从以下合同图片和OCR文本中提取关键信息，以JSON格式输出。

OCR识别文本（供参考）：
{ocr_text}

请提取以下字段（如果无法识别则填null）：
```json
{
    "contract_name": "合同名称",
    "party_a": "甲方名称",
    "party_a_credit_code": "甲方统一社会信用代码（18位）",
    "party_a_industry": "甲方所属行业",
    "is_state_owned": true或false（甲方是否为国企）,
    "contract_type": "合同类型（委托代理合同/常年法律顾问合同/专项法律服务/其他）",
    "amount": 合同金额（数字，单位：万元，请转换为万元后填写），
    "sign_date": "签订日期（YYYY-MM-DD格式）",
    "project_detail": "项目详情/服务内容摘要",
    "subject_amount": 标的额（诉讼案件，数字，单位：万元），
    "opponent": "对方当事人（诉讼案件）",
    "team_member": "团队成员/承办律师",
    "summary": "合同摘要（一句话描述）"
}
```

注意：
1. 金额统一转换为【万元】单位（例如：60000元 = 6万元，填写6）
2. 日期请转换为 YYYY-MM-DD 格式
3. 只输出JSON，不要其他内容
"""

# 纯文本提取提示词
TEXT_EXTRACT_PROMPT = """
请从以下合同文本中提取关键信息，以JSON格式输出。

合同文本：
{contract_text}

请提取以下字段（如果无法识别则填null）：
```json
{
    "contract_name": "合同名称",
    "party_a": "甲方名称",
    "party_a_credit_code": "甲方统一社会信用代码（18位）",
    "party_a_industry": "甲方所属行业",
    "is_state_owned": true或false（甲方是否为国企）,
    "contract_type": "合同类型（委托代理合同/常年法律顾问合同/专项法律服务/其他）",
    "amount": 合同金额（数字，单位：万元，请转换为万元后填写）,
    "sign_date": "签订日期（YYYY-MM-DD格式）",
    "project_detail": "项目详情/服务内容摘要",
    "subject_amount": 标的额（诉讼案件，数字，单位：万元）,
    "opponent": "对方当事人（诉讼案件）",
    "team_member": "团队成员/承办律师",
    "summary": "合同摘要（一句话描述）"
}
```

注意：
1. 金额统一转换为【万元】单位（例如：60000元 = 6万元，填写6）
2. 日期请转换为 YYYY-MM-DD 格式
3. 只输出JSON，不要其他内容
"""

# endregion
# ============================================


# ============================================
# region LLM 客户端
# ============================================

def get_client() -> OpenAI:
    """获取 LLM 客户端"""
    return OpenAI(
        api_key=SILICONFLOW_API_KEY,
        base_url=SILICONFLOW_BASE_URL,
    )

# endregion
# ============================================


# ============================================
# region 图片处理
# ============================================

def image_to_base64(image: Image.Image, max_size: int = 1024) -> str:
    """
    将图片转换为 base64（压缩以节省 token）
    
    参数:
        image: PIL Image
        max_size: 最大尺寸
    返回:
        base64 字符串
    """
    # 缩放图片
    if max(image.size) > max_size:
        ratio = max_size / max(image.size)
        new_size = (int(image.size[0] * ratio), int(image.size[1] * ratio))
        image = image.resize(new_size, Image.Resampling.LANCZOS)
    
    # 转换为 JPEG base64
    buffer = io.BytesIO()
    image.save(buffer, format="JPEG", quality=85)
    return base64.b64encode(buffer.getvalue()).decode("utf-8")


def images_to_blob(images: List[Image.Image]) -> bytes:
    """
    将多张图片打包为 ZIP BLOB
    
    参数:
        images: PIL Image 列表
    返回:
        ZIP 字节流
    """
    import zipfile
    
    buffer = io.BytesIO()
    
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for i, img in enumerate(images):
            img_buffer = io.BytesIO()
            img.save(img_buffer, format="PNG")
            zf.writestr(f"page_{i+1}.png", img_buffer.getvalue())
    
    return buffer.getvalue()

# endregion
# ============================================


# ============================================
# region JSON 解析
# ============================================

def clean_json_response(text: str) -> str:
    """清理 AI 返回的 JSON 文本"""
    import re
    
    # 移除 markdown 代码块标记
    if "```json" in text:
        text = text.split("```json")[1].split("```")[0]
    elif "```" in text:
        parts = text.split("```")
        if len(parts) >= 2:
            text = parts[1]
    
    # 提取 JSON 部分
    if "{" in text:
        start = text.find("{")
        end = text.rfind("}") + 1
        text = text[start:end]
    
    return text.strip()


def parse_extracted_info(text: str) -> dict:
    """解析提取的信息"""
    try:
        clean_text = clean_json_response(text)
        return json.loads(clean_text)
    except json.JSONDecodeError:
        return {}

# endregion
# ============================================


# ============================================
# region 视觉模型提取
# ============================================

def extract_with_vision(
    images: List[Image.Image],
    ocr_text: str,
    max_pages: int = 5,
) -> dict:
    """
    使用视觉模型提取合同信息
    
    参数:
        images: PDF 页面图片列表
        ocr_text: OCR 识别的文本（辅助）
        max_pages: 最多处理的页数
    返回:
        提取的合同信息字典
    """
    client = get_client()
    
    # 只取前几页
    selected_images = images[:max_pages]
    
    # 构建多模态内容
    content = []
    
    for img in selected_images:
        img_base64 = image_to_base64(img)
        content.append({
            "type": "image_url",
            "image_url": {
                "url": f"data:image/jpeg;base64,{img_base64}"
            }
        })
    
    # 添加提示词
    prompt = EXTRACT_PROMPT.replace("{ocr_text}", ocr_text[:3000])
    content.append({
        "type": "text",
        "text": prompt,
    })
    
    try:
        response = client.chat.completions.create(
            model=VISION_MODEL,
            messages=[{"role": "user", "content": content}],
            temperature=0.1,
            max_tokens=2000,
        )
        
        result_text = response.choices[0].message.content.strip()
        return parse_extracted_info(result_text)
        
    except Exception as e:
        print(f"视觉模型提取失败: {e}")
        return {}

# endregion
# ============================================


# ============================================
# region 文本模型提取
# ============================================

def extract_with_text(text: str) -> dict:
    """
    使用纯文本模型提取合同信息（备用方案）
    
    参数:
        text: 合同文本
    返回:
        提取的合同信息字典
    """
    client = get_client()
    
    prompt = TEXT_EXTRACT_PROMPT.replace("{contract_text}", text[:8000])
    
    try:
        response = client.chat.completions.create(
            model=EXTRACT_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": "你是专业的法律合同信息提取专家。请严格按JSON格式输出。"
                },
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,
            max_tokens=2000,
        )
        
        result_text = response.choices[0].message.content.strip()
        return parse_extracted_info(result_text)
        
    except Exception as e:
        print(f"文本模型提取失败: {e}")
        return {}

# endregion
# ============================================


# ============================================
# region 数据清洗
# ============================================

def clean_float(value) -> Optional[float]:
    """清洗浮点数"""
    if value is None or value == "" or value == "null":
        return None
    try:
        return float(value)
    except (ValueError, TypeError):
        return None


def clean_bool(value) -> bool:
    """清洗布尔值"""
    if value is None:
        return False
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.lower() in ["true", "yes", "是", "1"]
    return bool(value)


def clean_string(value) -> Optional[str]:
    """清洗字符串"""
    if value is None or value == "null":
        return None
    return str(value).strip() if value else None


def clean_extracted_info(info: dict) -> dict:
    """清洗提取的信息"""
    return {
        "contract_name": clean_string(info.get("contract_name")),
        "party_a": clean_string(info.get("party_a")),
        "party_a_credit_code": clean_string(info.get("party_a_credit_code")),
        "contract_type": clean_string(info.get("contract_type")),
        "amount": clean_float(info.get("amount")),
        "sign_date": clean_string(info.get("sign_date")),
        "project_detail": clean_string(info.get("project_detail")),
        "subject_amount": clean_float(info.get("subject_amount")),
        "opponent": clean_string(info.get("opponent")),
        "team_member": clean_string(info.get("team_member")),
        "summary": clean_string(info.get("summary")),
        "is_state_owned": clean_bool(info.get("is_state_owned")),
    }

# endregion
# ============================================


# ============================================
# region 主函数
# ============================================

def extract_contract_info(
    images: List[Image.Image],
    ocr_text: str,
    use_vision: bool = True,
) -> dict:
    """
    提取合同信息
    
    参数:
        images: PDF 页面图片列表
        ocr_text: OCR 识别的文本
        use_vision: 是否使用视觉模型
    返回:
        清洗后的合同信息字典
    """
    info = {}
    
    # 优先使用视觉模型
    if use_vision and images:
        info = extract_with_vision(images, ocr_text)
    
    # 如果视觉模型失败，使用文本模型
    if not info and ocr_text:
        info = extract_with_text(ocr_text)
    
    # 清洗数据
    return clean_extracted_info(info)

# endregion
# ============================================