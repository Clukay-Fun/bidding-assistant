"""
文件上传 API 路由
提供合同 PDF 上传和解析功能
"""

import io
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends, BackgroundTasks
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from app.db.database import get_db
from app.db import crud
from app.schemas import PerformanceCreate, PerformanceResponse
from app.services import (
    pdf_bytes_to_images,
    ocr_images,
    filter_watermarks,
    extract_contract_info,
    images_to_blob,
)


# ============================================
# region 路由定义
# ============================================

router = APIRouter(prefix="/upload", tags=["文件上传"])

# endregion
# ============================================


# ============================================
# region 响应模型
# ============================================

class OCRResult(BaseModel):
    """OCR 识别结果"""
    page_count: int = Field(..., description="总页数")
    full_text: str = Field(..., description="完整文本")


class ExtractResult(BaseModel):
    """合同提取结果"""
    contract_name: Optional[str] = None
    party_a: Optional[str] = None
    party_a_credit_code: Optional[str] = None
    contract_type: Optional[str] = None
    amount: Optional[float] = None
    sign_date: Optional[str] = None
    project_detail: Optional[str] = None
    subject_amount: Optional[float] = None
    opponent: Optional[str] = None
    team_member: Optional[str] = None
    summary: Optional[str] = None
    is_state_owned: bool = False


class UploadResponse(BaseModel):
    """上传响应"""
    success: bool = Field(..., description="是否成功")
    message: str = Field(..., description="提示信息")
    file_name: str = Field(..., description="文件名")
    page_count: int = Field(0, description="PDF 页数")
    ocr_text_length: int = Field(0, description="OCR 文本长度")
    extracted_info: Optional[ExtractResult] = Field(None, description="提取的合同信息")
    performance_id: Optional[int] = Field(None, description="保存后的业绩 ID")

# endregion
# ============================================


# ============================================
# region OCR 接口
# ============================================

@router.post("/ocr", response_model=OCRResult)
async def upload_and_ocr(
    file: UploadFile = File(..., description="PDF 文件"),
    filter_watermark: bool = Form(True, description="是否过滤水印"),
):
    """
    上传 PDF 并进行 OCR 识别（仅识别，不提取信息）
    """
    # 验证文件类型
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="只支持 PDF 文件")
    
    try:
        # 读取文件内容
        pdf_bytes = await file.read()
        
        # 转换为图片
        images = pdf_bytes_to_images(pdf_bytes)
        
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
        
        return OCRResult(
            page_count=len(images),
            full_text=full_text.strip(),
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"OCR 处理失败: {str(e)}")

# endregion
# ============================================


# ============================================
# region 合同解析接口
# ============================================

@router.post("/contract", response_model=UploadResponse)
async def upload_and_extract_contract(
    file: UploadFile = File(..., description="合同 PDF 文件"),
    use_vision: bool = Form(False, description="是否使用视觉模型（默认关闭，使用纯文本提取更快）"),
    save_to_db: bool = Form(True, description="是否保存到数据库"),
    db: Session = Depends(get_db),
):
    """
    上传合同 PDF，进行 OCR 识别并提取关键信息
    """
    print(f"[上传] 开始处理文件: {file.filename}")
    
    # 验证文件类型
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="只支持 PDF 文件")
    
    file_name = file.filename
    
    # 检查文件是否已存在
    existing = crud.get_performance_by_filename(db, file_name)
    if existing:
        # 删除旧记录，允许重新上传
        db.delete(existing)
        db.commit()
        print(f"[上传] 已删除旧记录: {file_name}, ID: {existing.id}")
    
    try:
        # 读取文件内容
        print("[上传] 读取文件内容...")
        pdf_bytes = await file.read()
        print(f"[上传] 文件大小: {len(pdf_bytes)} 字节")
        
        # 1. PDF 转图片
        print("[上传] PDF 转图片...")
        images = pdf_bytes_to_images(pdf_bytes)
        page_count = len(images)
        print(f"[上传] 转换完成，共 {page_count} 页")
        
        # 2. OCR 识别
        print("[上传] OCR 识别中...")
        ocr_results = ocr_images(images)
        ocr_results = filter_watermarks(ocr_results)
        print(f"[上传] OCR 完成，共 {len(ocr_results)} 页结果")
        
        # 合并全文
        full_text = ""
        for page in ocr_results:
            full_text += f"\n--- 第{page['page']}页 ---\n"
            for item in page["content"]:
                full_text += item["text"] + "\n"
        print(f"[上传] OCR 文本长度: {len(full_text)} 字符")
        
        # 3. 提取合同信息
        print(f"[上传] AI 提取信息中... (use_vision={use_vision})")
        extracted_info = extract_contract_info(
            images=images,
            ocr_text=full_text,
            use_vision=use_vision,
        )
        print(f"[上传] 提取结果: {extracted_info}")
        
        # 4. 保存到数据库
        performance_id = None
        if save_to_db:
            print("[上传] 保存到数据库...")
            
            # 转换日期格式
            sign_date = None
            if extracted_info.get("sign_date"):
                try:
                    sign_date = datetime.strptime(extracted_info["sign_date"], "%Y-%m-%d").date()
                except ValueError:
                    pass
            
            # 金额（AI 已按万元提取，直接使用）
            amount = extracted_info.get("amount")
            subject_amount = extracted_info.get("subject_amount")
            
            # 创建业绩记录
            performance_data = PerformanceCreate(
                file_name=file_name,
                party_a=extracted_info.get("party_a"),
                party_a_credit_code=extracted_info.get("party_a_credit_code"),
                contract_type=extracted_info.get("contract_type"),
                amount=amount,
                sign_date=sign_date,
                project_detail=extracted_info.get("project_detail"),
                subject_amount=subject_amount,
                opponent=extracted_info.get("opponent"),
                team_member=extracted_info.get("team_member"),
                summary=extracted_info.get("summary"),
                raw_text=full_text,
            )
            
            performance = crud.create_performance(db, performance_data)
            performance_id = performance.id
            print(f"[上传] 保存成功，ID: {performance_id}")
        
        return UploadResponse(
            success=True,
            message="合同解析成功" + ("，已保存到数据库" if save_to_db else ""),
            file_name=file_name,
            page_count=page_count,
            ocr_text_length=len(full_text),
            extracted_info=ExtractResult(**extracted_info),
            performance_id=performance_id,
        )
        
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"合同解析失败: {str(e)}")

# endregion
# ============================================


# ============================================
# region 批量上传接口
# ============================================

@router.post("/contracts/batch")
async def batch_upload_contracts(
    files: list[UploadFile] = File(..., description="多个合同 PDF 文件"),
    use_vision: bool = Form(False, description="是否使用视觉模型"),
    db: Session = Depends(get_db),
):
    """
    批量上传合同 PDF
    """
    results = []
    
    for file in files:
        if not file.filename.lower().endswith(".pdf"):
            results.append({
                "file_name": file.filename,
                "success": False,
                "message": "不是 PDF 文件",
            })
            continue
        
        # 检查是否已存在
        existing = crud.get_performance_by_filename(db, file.filename)
        if existing:
            results.append({
                "file_name": file.filename,
                "success": False,
                "message": f"文件已存在，ID: {existing.id}",
            })
            continue
        
        try:
            # 读取文件
            pdf_bytes = await file.read()
            
            # 转图片
            images = pdf_bytes_to_images(pdf_bytes)
            
            # OCR
            ocr_results = ocr_images(images)
            ocr_results = filter_watermarks(ocr_results)
            
            full_text = ""
            for page in ocr_results:
                full_text += f"\n--- 第{page['page']}页 ---\n"
                for item in page["content"]:
                    full_text += item["text"] + "\n"
            
            # 提取信息
            extracted_info = extract_contract_info(
                images=images,
                ocr_text=full_text,
                use_vision=use_vision,
            )
            
            # 保存
            sign_date = None
            if extracted_info.get("sign_date"):
                try:
                    sign_date = datetime.strptime(extracted_info["sign_date"], "%Y-%m-%d").date()
                except ValueError:
                    pass
            '''
            amount = extracted_info.get("amount")
            if amount:
                amount = amount / 10000
            '''
            amount = extracted_info.get("amount")
            
            performance_data = PerformanceCreate(
                file_name=file.filename,
                party_a=extracted_info.get("party_a"),
                party_a_credit_code=extracted_info.get("party_a_credit_code"),
                contract_type=extracted_info.get("contract_type"),
                amount=amount,
                sign_date=sign_date,
                project_detail=extracted_info.get("project_detail"),
                summary=extracted_info.get("summary"),
                raw_text=full_text,
            )
            
            performance = crud.create_performance(db, performance_data)
            
            results.append({
                "file_name": file.filename,
                "success": True,
                "message": "解析成功",
                "performance_id": performance.id,
            })
            
        except Exception as e:
            results.append({
                "file_name": file.filename,
                "success": False,
                "message": str(e),
            })
    
    # 统计
    success_count = sum(1 for r in results if r["success"])
    fail_count = len(results) - success_count
    
    return {
        "total": len(results),
        "success_count": success_count,
        "fail_count": fail_count,
        "results": results,
    }

# endregion
# ============================================