"""
loaders.py

PDF files se text nikalne ke liye.
"""

from pypdf import PdfReader


def load_pdf(file_path: str) -> str:
    """Diye gaye PDF file se poora text nikal kar ek string mein deta hai."""
    reader = PdfReader(file_path)
    text_parts = []
    for page in reader.pages:
        text_parts.append(page.extract_text() or "")
    text = "\n".join(text_parts)
    return _normalize_text(text)


def _normalize_text(text: str) -> str:
    """
    Kuch PDFs (khaaskar Word/Google Docs se banae gaye) hyphenated words
    (jaise "hands-on") ko ek INVISIBLE "soft hyphen" character (U+00AD) ke
    saath save karte hain, jo normal hyphen "-" jaisa nahi dikhta. Isay
    real hyphen se replace kar dete hain taake "hands-on" "handson" na ban
    jaye jab yeh text AI ko jaye ya PDF mein wapis likha jaye.
    """
    text = text.replace("\u00ad", "-")
    return text