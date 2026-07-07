"""简历文本清洗工具"""

import re


def clean_resume_text(raw_text: str) -> str:
    """
    清洗 PDF 提取的原始文本：
    - 去除多余空白（保留段落间一个空行）
    - 统一中文标点
    - 修复断行（中文行间不应有换行）
    - 去除控制字符

    Args:
        raw_text: PDF 提取的原始文本

    Returns:
        清洗后的干净文本
    """
    if not raw_text or not raw_text.strip():
        return ""

    # 1. 去除控制字符（保留换行和制表符）
    text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]', '', raw_text)

    # 2. 统一换行为 \n
    text = text.replace('\r\n', '\n').replace('\r', '\n')

    # 3. 中文行间换行合并（中文字符后的换行符视为同一段落内的软换行）
    # 匹配：中文字符/中文标点 后紧跟换行，然后是中文/英文/数字
    text = re.sub(r'(?<=[一-鿿　-〿＀-￯])\n(?=[一-鿿\w\d])', '', text)

    # 4. 去除行首行尾多余空白
    lines = text.split('\n')
    cleaned_lines = [line.strip() for line in lines]

    # 5. 合并连续空行为单个空行
    result_lines = []
    prev_empty = False
    for line in cleaned_lines:
        if not line:
            if not prev_empty:
                result_lines.append('')
                prev_empty = True
        else:
            result_lines.append(line)
            prev_empty = False

    text = '\n'.join(result_lines)

    # 6. 压缩多余空格（英文单词间保留一个空格）
    text = re.sub(r' {2,}', ' ', text)

    # 7. 去除首尾空白
    text = text.strip()

    return text


def extract_email(text: str) -> str:
    """基于正则提取邮箱"""
    match = re.search(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', text)
    return match.group(0) if match else ""


def extract_phone(text: str) -> str:
    """基于正则提取中国大陆手机号"""
    match = re.search(r'1[3-9]\d{9}', text)
    return match.group(0) if match else ""
