"""简历上传与查询路由"""

import hashlib
import json
import logging
import uuid
from typing import Optional

from fastapi import APIRouter, File, HTTPException, UploadFile

from app.models.schemas import ResumeUploadResponse, ErrorResponse
from app.services.ai_extractor import extract_resume_info
from app.services.cache import cache_service
from app.services.pdf_parser import parse_pdf, validate_pdf, compute_file_hash
from app.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/resume", tags=["简历管理"])


@router.post(
    "/upload",
    response_model=ResumeUploadResponse,
    responses={400: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
    summary="上传并解析简历 PDF",
    description="上传一份 PDF 格式的简历文件，系统将自动解析文本、提取关键信息并返回结构化数据。",
)
async def upload_resume(file: UploadFile = File(..., description="PDF 简历文件")):
    # 1. 读取文件内容
    try:
        file_content = await file.read()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"文件读取失败: {str(e)}")

    # 2. 验证文件
    try:
        validate_pdf(file_content, file.filename or "unknown.pdf")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    # 3. 计算文件哈希
    file_hash = compute_file_hash(file_content)

    # 4. 检查缓存
    if cache_service and cache_service.available:
        cached = await cache_service.get_resume(file_hash)
        if cached:
            logger.info(f"命中缓存: {file_hash}")
            return cached

    # 5. 解析 PDF
    try:
        cleaned_text = parse_pdf(file_content)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    # 6. AI 提取关键信息
    resume_info = extract_resume_info(
        cleaned_text=cleaned_text,
        api_key=settings.dashscope_api_key,
    )

    # 7. 构建响应
    response = ResumeUploadResponse(
        id=file_hash,
        basic_info=resume_info.basic_info,
        job_intent=resume_info.job_intent,
        expected_salary=resume_info.expected_salary,
        work_years=resume_info.work_years,
        education=resume_info.education,
        projects=resume_info.projects,
        skills=resume_info.skills,
    )

    # 8. 写入缓存
    if cache_service and cache_service.available:
        await cache_service.set_resume(file_hash, response.model_dump())

    return response


@router.get(
    "/{resume_id}",
    response_model=ResumeUploadResponse,
    responses={404: {"model": ErrorResponse}},
    summary="查询已解析的简历",
    description="通过简历 ID 查询之前已解析的简历信息（从缓存中获取）。",
)
async def get_resume(resume_id: str):
    if not cache_service or not cache_service.available:
        raise HTTPException(
            status_code=404,
            detail="缓存服务未启用，无法查询历史简历。请重新上传。",
        )

    cached = await cache_service.get_resume(resume_id)
    if not cached:
        raise HTTPException(status_code=404, detail="未找到该简历，可能已过期。请重新上传。")

    return cached
