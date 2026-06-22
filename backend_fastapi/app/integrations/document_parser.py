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
            pages.append(f"[[page:{index};anchor:page-{index}]]\n{text.strip()}")
    return "\n\n".join(pages)


def _parse_docx(content: bytes) -> str:
    doc = DocxDocument(BytesIO(content))
    parts = []
    current_anchor = "document-start"
    for paragraph in doc.paragraphs:
        text = paragraph.text.strip()
        if not text:
            continue
        style_name = paragraph.style.name if paragraph.style else ""
        if style_name.startswith("Heading"):
            level = _heading_level(style_name)
            current_anchor = slugify_anchor(text)
            parts.append(f"[[page:1;anchor:{current_anchor};heading:{level}]]\n{text}")
        else:
            parts.append(f"[[page:1;anchor:{current_anchor}]]\n{text}")
    return "\n\n".join(parts)


def _heading_level(style_name: str) -> int:
    digits = "".join(char for char in style_name if char.isdigit())
    return int(digits or "1")


def slugify_anchor(text: str) -> str:
    cleaned = "".join(char.lower() if char.isalnum() else "-" for char in text)
    return "-".join(part for part in cleaned.split("-") if part)[:80] or "section"
