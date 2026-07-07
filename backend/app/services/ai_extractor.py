"""通义千问 AI 关键信息提取服务"""

import json
import logging
import re
from typing import Optional

from dashscope import Generation
from dashscope.api_entities.dashscope_response import GenerationResponse

from app.models.schemas import BasicInfo, ResumeInfo
from app.utils.text_cleaner import extract_email, extract_phone

logger = logging.getLogger(__name__)

# 信息提取 Prompt
EXTRACTION_SYSTEM_PROMPT = """你是一位专业的简历解析专家。你的任务是从简历文本中提取结构化的关键信息。

请严格按照以下 JSON 格式返回结果，不要添加任何其他内容：

{
  "name": "姓名",
  "phone": "电话号码",
  "email": "邮箱地址",
  "address": "所在城市/地区",
  "job_intent": "求职意向/期望职位",
  "expected_salary": "期望薪资（如 15K-20K 或 面议）",
  "work_years": "工作年限（如 3年 或 应届生）",
  "education": "最高学历及专业（如 本科-计算机科学）",
  "projects": ["项目名称: 项目简述", "..."],
  "skills": ["技能1", "技能2", "..."]
}

规则：
1. 如果某个字段无法从简历中提取，填写空字符串 "" 或空数组 []
2. 项目经历只提取最重要的 3-5 个，用简洁的一句话概括每个项目
3. 技能提取技术相关的关键词（编程语言、框架、工具等），最多 15 个
4. 工作年限如果是应届生或实习，填写"应届生"
5. 学历需要包含学位+专业，如"硕士-人工智能"、"本科-软件工程"
"""


def _parse_ai_response(text: str) -> dict:
    """
    解析 AI 返回的文本，提取 JSON。

    兼容以下情况：
    - 纯 JSON
    - Markdown 代码块包裹的 JSON
    - 文本中嵌入的 JSON 片段
    """
    text = text.strip()

    # 尝试提取 Markdown 代码块中的 JSON
    code_match = re.search(r'```(?:json)?\s*\n?(.*?)\n?```', text, re.DOTALL)
    if code_match:
        text = code_match.group(1).strip()

    # 尝试找到第一个 { 和最后一个 } 之间的内容
    start = text.find('{')
    end = text.rfind('}')
    if start != -1 and end != -1 and end > start:
        text = text[start:end + 1]

    return json.loads(text)


def _rule_based_fallback(cleaned_text: str) -> ResumeInfo:
    """
    规则降级提取：当 AI 调用失败时，使用正则表达式提取基本信息。
    """
    info = ResumeInfo()

    # 正则提取邮箱和电话
    info.basic_info.email = extract_email(cleaned_text)
    info.basic_info.phone = extract_phone(cleaned_text)

    # 尝试从文本前几行提取姓名（通常简历开头是姓名）
    lines = cleaned_text.strip().split('\n')
    first_lines = [l.strip() for l in lines[:5] if l.strip() and len(l.strip()) < 20]
    if first_lines:
        # 过滤掉明显不是姓名的行
        for line in first_lines:
            # 纯中文，2-4个汉字，不包含标点
            if re.match(r'^[一-鿿]{2,4}$', line):
                info.basic_info.name = line
                break

    # 技能关键词搜索
    tech_keywords = [
        'Python', 'Java', 'JavaScript', 'TypeScript', 'Go', 'Rust', 'C++', 'C#',
        'React', 'Vue', 'Angular', 'Node.js', 'Django', 'Flask', 'FastAPI', 'Spring',
        'MySQL', 'PostgreSQL', 'MongoDB', 'Redis', 'Elasticsearch',
        'Docker', 'Kubernetes', 'AWS', 'Azure', 'Linux',
        'Git', 'CI/CD', 'RESTful', 'GraphQL', 'gRPC',
        '机器学习', '深度学习', 'NLP', '计算机视觉', '数据分析',
        'TensorFlow', 'PyTorch', 'Scikit-learn', 'Pandas', 'NumPy',
    ]
    info.skills = [kw for kw in tech_keywords if kw.lower() in cleaned_text.lower()]

    info.raw_text = cleaned_text
    return info


def extract_resume_info(
    cleaned_text: str,
    api_key: str,
    model: str = "qwen-turbo",
    max_retries: int = 2,
) -> ResumeInfo:
    """
    使用通义千问从简历文本中提取结构化信息。

    Args:
        cleaned_text: 清洗后的简历文本
        api_key: DashScope API Key
        model: 模型名称，默认 qwen-turbo（性价比高）
        max_retries: AI 调用最大重试次数

    Returns:
        结构化的简历信息
    """
    if not api_key:
        logger.warning("未配置 DASHSCOPE_API_KEY，使用规则降级提取")
        return _rule_based_fallback(cleaned_text)

    # 截断过长文本（qwen-turbo 上下文 8K，留足余量）
    max_text_len = 6000
    if len(cleaned_text) > max_text_len:
        truncated = cleaned_text[:max_text_len]
        logger.info(f"简历文本过长({len(cleaned_text)}字符)，已截断至{max_text_len}字符")
    else:
        truncated = cleaned_text

    user_prompt = f"请解析以下简历文本，提取关键信息：\n\n{truncated}"

    last_error = None
    for attempt in range(max_retries + 1):
        try:
            response: GenerationResponse = Generation.call(
                api_key=api_key,
                model=model,
                messages=[
                    {"role": "system", "content": EXTRACTION_SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.1,  # 低温度保证输出稳定
                result_format="message",
            )

            if response.status_code != 200:
                raise Exception(f"API 返回错误状态码 {response.status_code}: {response.message}")

            ai_text = response.output.choices[0].message.content
            extracted = _parse_ai_response(ai_text)

            # 构建 ResumeInfo
            info = ResumeInfo(
                basic_info=BasicInfo(
                    name=extracted.get("name", ""),
                    phone=extracted.get("phone", ""),
                    email=extracted.get("email", ""),
                    address=extracted.get("address", ""),
                ),
                job_intent=extracted.get("job_intent", ""),
                expected_salary=extracted.get("expected_salary", ""),
                work_years=extracted.get("work_years", ""),
                education=extracted.get("education", ""),
                projects=extracted.get("projects", []),
                skills=extracted.get("skills", []),
                raw_text=cleaned_text,
            )

            # 正则补充：AI 漏掉的邮箱/电话用正则补齐
            if not info.basic_info.email:
                info.basic_info.email = extract_email(cleaned_text)
            if not info.basic_info.phone:
                info.basic_info.phone = extract_phone(cleaned_text)

            return info

        except json.JSONDecodeError as e:
            last_error = f"AI 返回格式解析失败: {e}"
            logger.warning(f"第 {attempt + 1} 次提取失败: {last_error}")
            if attempt < max_retries:
                continue

        except Exception as e:
            last_error = str(e)
            logger.error(f"第 {attempt + 1} 次 AI 调用失败: {last_error}")
            if attempt < max_retries:
                continue

    # 所有重试都失败，降级为规则提取
    logger.warning(f"AI 提取全部失败 ({last_error})，降级为规则提取")
    return _rule_based_fallback(cleaned_text)
