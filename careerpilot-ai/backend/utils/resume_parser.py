"""
Utility for extracting raw text from uploaded resume files (PDF/text).
"""
from pypdf import PdfReader
import io


def extract_text_from_pdf(file_bytes: bytes) -> str:
    reader = PdfReader(io.BytesIO(file_bytes))
    text_parts = []
    for page in reader.pages:
        text_parts.append(page.extract_text() or "")
    return "\n".join(text_parts)


def extract_text(filename: str, file_bytes: bytes) -> str:
    if filename.lower().endswith(".pdf"):
        return extract_text_from_pdf(file_bytes)
    # assume plain text
    return file_bytes.decode("utf-8", errors="ignore")
