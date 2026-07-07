"""简历与岗位匹配评分路由"""

import hashlib
import logging

from fastapi import APIRouter, HTTPException

from app.models.schemas import MatchRequest, MatchResponse, ErrorResponse, ResumeInfo, BasicInfo
import app.services.cache as cache_mod
from app.services.matcher import match_resume_with_job
from app.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/resume", tags=["匹配评分"])


@router.post(
    "/{resume_id}/match",
    response_model=MatchResponse,
    responses={404: {"model": ErrorResponse}, 400: {"model": ErrorResponse}},
    summary="简历与岗位匹配评分",
    description="提交岗位需求描述，对已解析的简历进行匹配度评分。",
)
async def match_resume(resume_id: str, body: MatchRequest):
    # 1. 从缓存获取简历
    svc = cache_mod.cache_service
    if not svc or not svc.available:
        raise HTTPException(
            status_code=404,
            detail="缓存服务未启用，请先上传简历。",
        )

    cached = await svc.get_resume(resume_id)
    if not cached:
        raise HTTPException(
            status_code=404,
            detail="未找到该简历，可能已过期。请重新上传。",
        )

    # 2. 重建 ResumeInfo
    basic = cached.get("basic_info", {})
    resume_info = ResumeInfo(
        basic_info=BasicInfo(**basic) if basic else BasicInfo(),
        job_intent=cached.get("job_intent", ""),
        expected_salary=cached.get("expected_salary", ""),
        work_years=cached.get("work_years", ""),
        education=cached.get("education", ""),
        projects=cached.get("projects", []),
        skills=cached.get("skills", []),
        raw_text="",  # 缓存中不存原始文本
    )

    # 3. 检查匹配缓存
    jd_hash = hashlib.md5(body.job_description.encode()).hexdigest()

    if svc.available:
        cached_match = await svc.get_match(resume_id, jd_hash)
        if cached_match:
            logger.info(f"命中匹配缓存: {resume_id}:{jd_hash}")
            return cached_match

    # 4. 执行匹配评分
    try:
        result = match_resume_with_job(
            resume=resume_info,
            job_description=body.job_description,
            api_key=settings.dashscope_api_key,
        )
    except Exception as e:
        logger.error(f"匹配评分异常: {e}")
        raise HTTPException(status_code=500, detail=f"匹配评分失败: {str(e)}")

    # 5. 写入匹配缓存
    if svc.available:
        await svc.set_match(resume_id, jd_hash, result.model_dump())

    return result
