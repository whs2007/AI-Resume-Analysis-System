"""Pydantic 数据模型定义"""

from pydantic import BaseModel, Field
from typing import Optional


class BasicInfo(BaseModel):
    """基本信息"""
    name: str = Field(default="", description="姓名")
    phone: str = Field(default="", description="电话号码")
    email: str = Field(default="", description="邮箱地址")
    address: str = Field(default="", description="地址/城市")


class ResumeInfo(BaseModel):
    """简历完整信息"""
    basic_info: BasicInfo = Field(default_factory=BasicInfo, description="基本信息")
    job_intent: str = Field(default="", description="求职意向")
    expected_salary: str = Field(default="", description="期望薪资")
    work_years: str = Field(default="", description="工作年限")
    education: str = Field(default="", description="学历背景")
    projects: list[str] = Field(default_factory=list, description="项目经历列表")
    skills: list[str] = Field(default_factory=list, description="技能标签")
    raw_text: str = Field(default="", description="原始清洗后文本")


class ResumeUploadResponse(BaseModel):
    """简历上传响应"""
    id: str = Field(..., description="简历唯一 ID")
    basic_info: BasicInfo = Field(default_factory=BasicInfo)
    job_intent: str = ""
    expected_salary: str = ""
    work_years: str = ""
    education: str = ""
    projects: list[str] = Field(default_factory=list)
    skills: list[str] = Field(default_factory=list)


class MatchRequest(BaseModel):
    """匹配请求"""
    job_description: str = Field(..., min_length=1, max_length=10000, description="岗位需求描述")


class MatchDetail(BaseModel):
    """匹配详情"""
    skill_match: float = Field(default=0.0, description="技能匹配率 (0-100)")
    experience_relevance: float = Field(default=0.0, description="工作经验相关性 (0-100)")
    education_match: float = Field(default=0.0, description="学历匹配度 (0-100)")


class MatchResponse(BaseModel):
    """匹配结果响应"""
    match_score: float = Field(..., description="综合匹配度评分 (0-100)")
    details: MatchDetail = Field(default_factory=MatchDetail)
    keywords: list[str] = Field(default_factory=list, description="提取的岗位关键词")
    analysis: str = Field(default="", description="AI 匹配分析")


class ErrorResponse(BaseModel):
    """错误响应"""
    detail: str = Field(..., description="错误详情")
