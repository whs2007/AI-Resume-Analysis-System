"""简历与岗位需求匹配评分服务"""

import json
import logging
import re
from typing import Optional

from dashscope import Generation
from dashscope.api_entities.dashscope_response import GenerationResponse

from app.models.schemas import MatchDetail, MatchResponse, ResumeInfo

logger = logging.getLogger(__name__)

# 匹配评分 Prompt
MATCHING_SYSTEM_PROMPT = """你是一位专业的招聘专家。你需要根据候选人简历和岗位需求描述，评估匹配度。

请严格按照以下 JSON 格式返回结果，不要添加任何其他内容：

{
  "skill_match": 85.0,
  "experience_relevance": 70.0,
  "education_match": 80.0,
  "keywords": ["Python", "FastAPI", "MySQL"],
  "analysis": "候选人技能与岗位需求较为匹配。Python 开发经验丰富，但缺少云端部署经验。建议进一步面试考察。"
}

评分说明：
- skill_match (0-100): 技能匹配率，候选人的技术栈与岗位要求技能的匹配程度
- experience_relevance (0-100): 工作经验相关性，工作年限和项目经历与岗位需求的相关程度
- education_match (0-100): 学历匹配度，学历背景与岗位要求的匹配程度
- keywords: 从岗位描述中提取的核心关键词（5-10个）
- analysis: 50-150字的匹配分析，包括优势、不足和建议

评分要客观公正，不要过于宽松也不要过于苛刻。
"""


def _extract_keywords_from_jd(job_description: str) -> list[str]:
    """
    从岗位描述中提取关键词（基于常见技术词汇匹配）。
    作为 AI 不可用时的降级方案。
    """
    tech_keywords = {
        'Python', 'Java', 'JavaScript', 'TypeScript', 'Go', 'Rust', 'C++', 'C#', 'PHP',
        'React', 'Vue', 'Angular', 'Node.js', 'Django', 'Flask', 'FastAPI', 'Spring', 'Spring Boot',
        'MySQL', 'PostgreSQL', 'MongoDB', 'Redis', 'Elasticsearch', 'Oracle', 'SQLite',
        'Docker', 'Kubernetes', 'AWS', 'Azure', '阿里云', 'GCP', 'Linux',
        'Git', 'CI/CD', 'Jenkins', 'RESTful', 'GraphQL', 'gRPC', 'WebSocket',
        'TensorFlow', 'PyTorch', 'Scikit-learn', 'Pandas', 'NumPy', '机器学习', '深度学习',
        'NLP', '计算机视觉', '数据分析', '大数据', 'Spark', 'Hadoop', 'Flink',
        'HTML', 'CSS', 'SASS', 'Webpack', 'Vite', 'Nginx', 'Tomcat',
        '微服务', '分布式', '高并发', '系统设计', '项目管理', '敏捷开发',
        '本科', '硕士', '博士', '计算机', '软件工程', '人工智能', '数学',
    }

    jd_lower = job_description.lower()
    found = []
    for kw in tech_keywords:
        if kw.lower() in jd_lower:
            found.append(kw)

    return found[:10]


def _compute_base_score(resume: ResumeInfo, keywords: list[str]) -> MatchDetail:
    """
    基础评分算法：基于关键词匹配率计算分数。
    作为 AI 不可用时的降级方案。
    """
    if not keywords:
        return MatchDetail(skill_match=0.0, experience_relevance=0.0, education_match=0.0)

    resume_skills_lower = [s.lower() for s in resume.skills]

    # 技能匹配率
    skill_matched = sum(1 for kw in keywords if any(kw.lower() in s for s in resume_skills_lower))
    # 同时检查简历文本中是否包含关键词
    text_lower = resume.raw_text.lower()
    text_matched = sum(1 for kw in keywords if kw.lower() in text_lower)
    total_matched = max(skill_matched, text_matched)
    skill_match = min(100, (total_matched / len(keywords)) * 100)

    # 工作经验相关性
    work_years_lower = resume.work_years.lower()
    if any(w in work_years_lower for w in ['应届', '实习', '无']):
        experience_score = 30
    elif any(w in work_years_lower for w in ['1年', '2年', '1-2']):
        experience_score = 50
    elif any(w in work_years_lower for w in ['3年', '4年', '3-5']):
        experience_score = 75
    elif any(w in work_years_lower for w in ['5年', '6年', '7年', '8年', '9年', '10年', '多年']):
        experience_score = 90
    else:
        experience_score = 40  # 未知时保守估计

    # 学历匹配度
    edu_lower = resume.education.lower()
    if any(deg in edu_lower for deg in ['博士', 'phd']):
        education_score = 95
    elif any(deg in edu_lower for deg in ['硕士', 'master']):
        education_score = 85
    elif any(deg in edu_lower for deg in ['本科', 'bachelor', '学士']):
        education_score = 75
    elif any(deg in edu_lower for deg in ['大专', '专科']):
        education_score = 50
    else:
        education_score = 40

    return MatchDetail(
        skill_match=round(skill_match, 1),
        experience_relevance=round(experience_score, 1),
        education_match=round(education_score, 1),
    )


def _rule_based_match(resume: ResumeInfo, job_description: str) -> MatchResponse:
    """规则降级匹配（AI 不可用时）"""
    keywords = _extract_keywords_from_jd(job_description)
    details = _compute_base_score(resume, keywords)

    # 综合评分 = 技能(50%) + 经验(30%) + 学历(20%)
    score = (
        details.skill_match * 0.5
        + details.experience_relevance * 0.3
        + details.education_match * 0.2
    )

    return MatchResponse(
        match_score=round(score, 1),
        details=details,
        keywords=keywords,
        analysis="（规则匹配模式）匹配度基于关键词和简历信息计算，配置 AI 可获得更精准的分析。",
    )


def match_resume_with_job(
    resume: ResumeInfo,
    job_description: str,
    api_key: str,
    model: str = "qwen-turbo",
) -> MatchResponse:
    """
    将简历与岗位需求进行匹配评分。

    Args:
        resume: 已解析的简历信息
        job_description: 岗位需求描述
        api_key: DashScope API Key
        model: 模型名称

    Returns:
        匹配结果
    """
    if not api_key:
        logger.warning("未配置 DASHSCOPE_API_KEY，使用规则降级匹配")
        return _rule_based_match(resume, job_description)

    # 构建简历摘要
    resume_summary = f"""候选人信息：
- 求职意向：{resume.job_intent or '未知'}
- 工作年限：{resume.work_years or '未知'}
- 学历背景：{resume.education or '未知'}
- 技能：{', '.join(resume.skills) if resume.skills else '未提取到'}
- 项目经历：{'; '.join(resume.projects[:3]) if resume.projects else '未提取到'}"""

    user_prompt = f"{resume_summary}\n\n岗位需求描述：\n{job_description}\n\n请评估匹配度。"

    try:
        response: GenerationResponse = Generation.call(
            api_key=api_key,
            model=model,
            messages=[
                {"role": "system", "content": MATCHING_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.1,
            result_format="message",
        )

        if response.status_code != 200:
            raise Exception(f"API 错误: {response.status_code} {response.message}")

        ai_text = response.output.choices[0].message.content

        # 解析 JSON
        text = ai_text.strip()
        code_match = re.search(r'```(?:json)?\s*\n?(.*?)\n?```', text, re.DOTALL)
        if code_match:
            text = code_match.group(1).strip()
        start = text.find('{')
        end = text.rfind('}')
        if start != -1 and end != -1:
            text = text[start:end + 1]

        result = json.loads(text)

        details = MatchDetail(
            skill_match=float(result.get("skill_match", 0)),
            experience_relevance=float(result.get("experience_relevance", 0)),
            education_match=float(result.get("education_match", 0)),
        )

        # 综合评分
        score = (
            details.skill_match * 0.5
            + details.experience_relevance * 0.3
            + details.education_match * 0.2
        )

        return MatchResponse(
            match_score=round(score, 1),
            details=details,
            keywords=result.get("keywords", []),
            analysis=result.get("analysis", ""),
        )

    except Exception as e:
        logger.error(f"AI 匹配评分失败: {e}，降级为规则匹配")
        return _rule_based_match(resume, job_description)
