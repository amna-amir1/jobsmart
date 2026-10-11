"""
pdf_utils.py

Plain/markdown-jaisa text le kar ek achi dikhne wali, downloadable PDF banati hai.
"""

from fpdf import FPDF
from fpdf.enums import XPos, YPos


class StyledPDF(FPDF):
    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(150, 150, 150)
        self.cell(0, 10, f"Page {self.page_no()}", align="C")


ACCENT_COLOR = (30, 64, 175)
TEXT_COLOR = (30, 30, 30)
MUTED_COLOR = (90, 90, 90)


def _clean_text(text: str) -> str:
    replacements = {
        "\u2018": "'", "\u2019": "'",
        "\u201c": '"', "\u201d": '"',
        "\u2013": "-", "\u2014": "-",
        "\u2022": "-", "\u2026": "...",
    }
    for bad, good in replacements.items():
        text = text.replace(bad, good)

    # Defensive: agar AI ne phir bhi markdown bold/italic symbols bhej diye
    # hon, unhe hata do — plain, clean ATS-friendly text chahiye.
    text = text.replace("**", "").replace("__", "")

    return text.encode("latin-1", "ignore").decode("latin-1")


def _break_long_tokens(text: str, max_len: int = 45) -> str:
    words = text.split(" ")
    fixed_words = []
    for word in words:
        if len(word) > max_len:
            chunks = [word[i:i + max_len] for i in range(0, len(word), max_len)]
            fixed_words.append(" ".join(chunks))
        else:
            fixed_words.append(word)
    return " ".join(fixed_words)


def text_to_pdf(content: str, output_path: str, doc_title: str = "") -> str:
    content = _clean_text(content)

    pdf = StyledPDF(format="A4")
    pdf.set_auto_page_break(auto=True, margin=20)
    pdf.set_margins(18, 18, 18)
    pdf.add_page()

    if doc_title:
        pdf.set_font("Helvetica", "B", 16)
        pdf.set_text_color(*ACCENT_COLOR)
        pdf.multi_cell(0, 9, _break_long_tokens(_clean_text(doc_title)),
                        new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.ln(3)

    for raw_line in content.split("\n"):
        line = raw_line.rstrip()
        line = _break_long_tokens(line)

        if not line.strip():
            pdf.ln(3)
            continue

        if line.startswith("# "):
            pdf.set_font("Helvetica", "B", 18)
            pdf.set_text_color(*ACCENT_COLOR)
            pdf.multi_cell(0, 9, line[2:].strip(), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            pdf.ln(2)

        elif line.startswith("## "):
            pdf.ln(2)
            pdf.set_font("Helvetica", "B", 13)
            pdf.set_text_color(*ACCENT_COLOR)
            pdf.multi_cell(0, 8, line[3:].strip(), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            pdf.set_draw_color(*ACCENT_COLOR)
            pdf.line(pdf.l_margin, pdf.get_y(), pdf.w - pdf.r_margin, pdf.get_y())
            pdf.ln(3)

        elif line.startswith("- ") or line.startswith("* "):
            pdf.set_font("Helvetica", "", 11)
            pdf.set_text_color(*TEXT_COLOR)
            pdf.set_x(pdf.l_margin + 4)
            pdf.multi_cell(0, 6.5, f"-  {line[2:].strip()}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)

        else:
            pdf.set_font("Helvetica", "", 11)
            pdf.set_text_color(*TEXT_COLOR)
            pdf.multi_cell(0, 6.5, line.strip(), new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    pdf.output(output_path)
    return output_path