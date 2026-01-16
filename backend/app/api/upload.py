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
from fastapi.responses import StreamingResponse
from app.services import pdf_to_markdown
import asyncio


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
    use_vision: bool = Form(True, description="是否使用视觉模型"),
    save_to_db: bool = Form(True, description="是否保存到数据库"),
    db: Session = Depends(get_db),
):
    """
    上传合同 PDF，进行 OCR 识别并提取关键信息
    """
    # 验证文件类型
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="只支持 PDF 文件")
    
    file_name = file.filename
    
    # 检查文件是否已存在
    existing = crud.get_performance_by_filename(db, file_name)
    if existing:
        raise HTTPException(status_code=400, detail=f"文件 '{file_name}' 已存在，ID: {existing.id}")
    
    try:
        # 读取文件内容
        pdf_bytes = await file.read()
        
        # 1. PDF 转图片
        images = pdf_bytes_to_images(pdf_bytes)
        page_count = len(images)
        
        # 2. OCR 识别
        ocr_results = ocr_images(images)
        ocr_results = filter_watermarks(ocr_results)
        
        # 合并全文
        full_text = ""
        for page in ocr_results:
            full_text += f"\n--- 第{page['page']}页 ---\n"
            for item in page["content"]:
                full_text += item["text"] + "\n"
        
        # 3. 提取合同信息
        extracted_info = extract_contract_info(
            images=images,
            ocr_text=full_text,
            use_vision=use_vision,
        )
        
        # 4. 保存到数据库
        performance_id = None
        if save_to_db:
            # 转换日期格式
            sign_date = None
            if extracted_info.get("sign_date"):
                try:
                    sign_date = datetime.strptime(extracted_info["sign_date"], "%Y-%m-%d").date()
                except ValueError:
                    pass
            
            # 金额转换（元 -> 万元）
            amount = extracted_info.get("amount")
            if amount:
                amount = amount / 10000  # 转为万元
            
            subject_amount = extracted_info.get("subject_amount")
            if subject_amount:
                subject_amount = subject_amount / 10000
            
            # 图片打包为 BLOB
            image_blob = images_to_blob(images)
            
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
        raise HTTPException(status_code=500, detail=f"合同解析失败: {str(e)}")

# endregion
# ============================================

# ============================================
# region 上传合同流
# ============================================

@router.post("/contract/stream")
async def upload_contract_stream(
    file: UploadFile = File(..., description="合同 PDF 文件"),
    use_vision: bool = Form(False, description="是否使用视觉模型"),
    use_markitdown: bool = Form(True, description="是否用 markitdown"),
    save_to_db: bool = Form(True, description="是否保存到数据库"),
    db: Session = Depends(get_db),
):
    """
    流式上传合同 PDF（SSE），实时返回处理进度
    """
    import time
    
    # 验证文件类型
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="只支持 PDF 文件")
    
    file_name = file.filename
    
    # 检查文件是否已存在
    existing = crud.get_performance_by_filename(db, file_name)
    if existing:
        raise HTTPException(status_code=400, detail=f"文件 '{file_name}' 已存在，ID: {existing.id}")
    
    # 预读取文件
    pdf_bytes = await file.read()
    
    async def progress_generator():
        """生成进度事件流"""
        total_start = time.time()
        images = []
        page_count = 0
        
        try:
            if use_markitdown:
                # ========== 方案 1：markitdown 快速解析 ==========
                yield _sse_event("progress", {
                    "step": 1,
                    "total_steps": 4,
                    "message": "正在解析 PDF 为 Markdown...",
                    "progress": 10
                })
                step_start = time.time()
                
                full_text = pdf_to_markdown(pdf_bytes=pdf_bytes)
                page_count = full_text.count("\n---") + 1  # 估算页数
                
                yield _sse_event("progress", {
                    "step": 1,
                    "message": f"解析完成，约 {page_count} 页，{len(full_text)} 字符",
                    "progress": 40,
                    "elapsed": f"{time.time() - step_start:.1f}s"
                })
                
                # Step 2: LLM 提取信息（纯文本模式）
                yield _sse_event("progress", {
                    "step": 2,
                    "total_steps": 4,
                    "message": "正在用 AI 提取合同信息...",
                    "progress": 50
                })
                step_start = time.time()
                extracted_info = extract_contract_info(
                    images=[],
                    ocr_text=full_text,
                    use_vision=False,  # markitdown 模式不用视觉
                )
                yield _sse_event("progress", {
                    "step": 2,
                    "message": "AI 提取完成",
                    "progress": 80,
                    "elapsed": f"{time.time() - step_start:.1f}s"
                })
                
            else:
                # ========== 方案 2：传统 OCR 流程 ==========
                # Step 1: PDF 转图片
                yield _sse_event("progress", {
                    "step": 1,
                    "total_steps": 4,
                    "message": "正在转换 PDF 为图片...",
                    "progress": 10
                })
                step_start = time.time()
                images = pdf_bytes_to_images(pdf_bytes)
                page_count = len(images)
                yield _sse_event("progress", {
                    "step": 1,
                    "message": f"PDF 转换完成，共 {page_count} 页",
                    "progress": 20,
                    "elapsed": f"{time.time() - step_start:.1f}s"
                })
                
                # Step 2: OCR 识别
                yield _sse_event("progress", {
                    "step": 2,
                    "total_steps": 4,
                    "message": f"正在 OCR 识别 {page_count} 页...",
                    "progress": 25
                })
                step_start = time.time()
                ocr_results = ocr_images(images)
                ocr_results = filter_watermarks(ocr_results)
                
                # 合并全文
                full_text = ""
                for page in ocr_results:
                    full_text += f"\n--- 第{page['page']}页 ---\n"
                    for item in page["content"]:
                        full_text += item["text"] + "\n"
                
                yield _sse_event("progress", {
                    "step": 2,
                    "message": f"OCR 完成，识别 {len(full_text)} 字符",
                    "progress": 50,
                    "elapsed": f"{time.time() - step_start:.1f}s"
                })
                
                # Step 3: LLM 提取信息
                yield _sse_event("progress", {
                    "step": 3,
                    "total_steps": 4,
                    "message": "正在用 AI 提取合同信息...",
                    "progress": 55
                })
                step_start = time.time()
                extracted_info = extract_contract_info(
                    images=images,
                    ocr_text=full_text,
                    use_vision=use_vision,
                )
                yield _sse_event("progress", {
                    "step": 3,
                    "message": "AI 提取完成",
                    "progress": 80,
                    "elapsed": f"{time.time() - step_start:.1f}s"
                })
            
            # ========== 公共步骤：保存数据库 ==========
            performance_id = None
            if save_to_db:
                step_num = 3 if use_markitdown else 4
                yield _sse_event("progress", {
                    "step": step_num,
                    "total_steps": 4,
                    "message": "正在保存到数据库...",
                    "progress": 85
                })
                step_start = time.time()
                
                # 转换日期格式
                sign_date = None
                if extracted_info.get("sign_date"):
                    try:
                        sign_date = datetime.strptime(extracted_info["sign_date"], "%Y-%m-%d").date()
                    except ValueError:
                        pass
                
                # 金额转换
                amount = extracted_info.get("amount")
                if amount:
                    amount = amount / 10000
                
                subject_amount = extracted_info.get("subject_amount")
                if subject_amount:
                    subject_amount = subject_amount / 10000
                
                # 图片打包（仅 OCR 模式有图片）
                image_blob = images_to_blob(images) if images else None
                
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
                
                yield _sse_event("progress", {
                    "step": step_num,
                    "message": f"保存成功，ID: {performance_id}",
                    "progress": 95,
                    "elapsed": f"{time.time() - step_start:.1f}s"
                })
            
            # ========== 完成 ==========
            total_elapsed = time.time() - total_start
            yield _sse_event("complete", {
                "success": True,
                "message": "合同解析完成",
                "file_name": file_name,
                "page_count": page_count,
                "ocr_text_length": len(full_text),
                "extracted_info": extracted_info,
                "performance_id": performance_id,
                "total_elapsed": f"{total_elapsed:.1f}s",
                "mode": "markitdown" if use_markitdown else "ocr"
            })
            
        except Exception as e:
            yield _sse_event("error", {
                "success": False,
                "message": f"处理失败: {str(e)}"
            })

    
    return StreamingResponse(
        progress_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


def _sse_event(event_type: str, data: dict) -> str:
    """格式化 SSE 事件"""
    import json
    return f"event: {event_type}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"
# endregion
# ============================================

# ============================================
# region 批量上传接口
# ============================================

@router.post("/contracts/batch")
async def batch_upload_contracts(
    files: list[UploadFile] = File(..., description="多个合同 PDF 文件"),
    use_vision: bool = Form(True, description="是否使用视觉模型"),
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
            
            amount = extracted_info.get("amount")
            if amount:
                amount = amount / 10000
            
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