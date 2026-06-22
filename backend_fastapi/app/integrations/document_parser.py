from io import BytesIO
from pathlib import Path

from docx import Document as DocxDocument
from pypdf import PdfReader


SUPPORTED_PARSE_EXTENSIONS = {".txt", ".md", ".markdown", ".pdf", ".docx"}


def parse_document_content(content: bytes, file_name: str) -> str:
    suffix = Path(file_name).suffix.lower()
    if suffix in {".txt", ".md", ".markdown"}:
        return content.decode("utf-8", errors="ignore")
    if suffix == ".pdf":
        return _parse_pdf(content)
    if suffix == ".docx":
        return _parse_docx(content)
    # 未识别类型退回文本解析，避免阻断历史文件或前端自定义扩展名。
    return content.decode("utf-8", errors="ignore")


def _parse_pdf(content: bytes) -> str:
    reader = PdfReader(BytesIO(content))
    pages = []
    for index, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""
        if text:
            pages.append(f"[page:{index}]\n{text}")
    return "\n\n".join(pages)


def _parse_docx(content: bytes) -> str:
    doc = DocxDocument(BytesIO(content))
    return "\n".join(paragraph.text for paragraph in doc.paragraphs if paragraph.text)
