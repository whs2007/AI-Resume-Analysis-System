"""PDF 简历解析服务"""

import hashlib
from pathlib import Path

import fitz  # PyMuPDF

from app.utils.text_cleaner import clean_resume_text


# 允许的文件类型
ALLOWED_CONTENT_TYPES = {"application/pdf"}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB


class PDFParseError(Exception):
    """PDF 解析异常"""
    pass


def validate_pdf(file_content: bytes, filename: str) -> None:
    """
    验证上传文件是否为合法 PDF。

    Args:
        file_content: 文件二进制内容
        filename: 原始文件名

    Raises:
        PDFParseError: 文件不合法时抛出
    """
    if not filename.lower().endswith('.pdf'):
        raise PDFParseError("仅支持 PDF 格式的文件")

    if len(file_content) == 0:
        raise PDFParseError("上传的文件为空")

    if len(file_content) > MAX_FILE_SIZE:
        raise PDFParseError(f"文件大小超过限制（最大 {MAX_FILE_SIZE // (1024*1024)}MB）")

    # 检查 PDF 文件头魔数
    if not file_content.startswith(b'%PDF'):
        raise PDFParseError("文件格式无效：不是合法的 PDF 文件")


def parse_pdf(file_content: bytes) -> str:
    """
    解析 PDF 文件，提取文本内容。

    支持多页简历，逐页提取后合并。

    Args:
        file_content: PDF 文件的二进制内容

    Returns:
        清洗后的完整文本

    Raises:
        PDFParseError: 解析失败时抛出
    """
    try:
        doc = fitz.open(stream=file_content, filetype="pdf")
    except Exception as e:
        raise PDFParseError(f"无法打开 PDF 文件：{str(e)}")

    if doc.page_count == 0:
        doc.close()
        raise PDFParseError("PDF 文件没有页面内容")

    texts: list[str] = []
    for page_num in range(doc.page_count):
        try:
            page = doc[page_num]
            page_text = page.get_text("text")
            if page_text.strip():
                texts.append(page_text.strip())
        except Exception as e:
            # 单页失败不中断，继续提取其他页
            texts.append(f"[第 {page_num + 1} 页解析异常: {e}]")

    doc.close()

    if not texts:
        raise PDFParseError("未能从 PDF 中提取到任何文本内容")

    raw_text = "\n".join(texts)
    cleaned = clean_resume_text(raw_text)

    if not cleaned:
        raise PDFParseError("PDF 文本清洗后为空，可能是扫描版 PDF 或图片简历")

    return cleaned


def compute_file_hash(file_content: bytes) -> str:
    """计算文件 MD5 哈希，作为缓存 key"""
    return hashlib.md5(file_content).hexdigest()
