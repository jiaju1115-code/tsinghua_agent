from __future__ import annotations

from pathlib import Path
from typing import Any

from .common import dedupe_path, ensure_output_path
from .models import FilePlan, SectionSpec


def _register_font() -> str:
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont

    candidates = [
        Path("C:/Windows/Fonts/msyh.ttc"),
        Path("C:/Windows/Fonts/simhei.ttf"),
        Path("C:/Windows/Fonts/simsun.ttc"),
    ]
    for path in candidates:
        if path.is_file():
            try:
                pdfmetrics.registerFont(TTFont("CampusCJK", str(path)))
                return "CampusCJK"
            except Exception:
                continue
    return "Helvetica"


def create_pdf(plan: FilePlan, output_path: str | Path | None = None) -> Path:
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import mm
    from reportlab.platypus import ListFlowable, ListItem, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    path = dedupe_path(ensure_output_path(plan.title, "pdf", output_path))
    font = _register_font()
    styles = getSampleStyleSheet()
    title = ParagraphStyle("CampusTitle", parent=styles["Title"], fontName=font, fontSize=24, leading=31, textColor=colors.HexColor("#532A6E"), alignment=TA_CENTER, spaceAfter=10)
    subtitle = ParagraphStyle("CampusSubtitle", parent=styles["Normal"], fontName=font, fontSize=10.5, leading=15, textColor=colors.HexColor("#596273"), alignment=TA_CENTER, spaceAfter=20)
    heading = ParagraphStyle("CampusHeading", parent=styles["Heading1"], fontName=font, fontSize=15, leading=20, textColor=colors.HexColor("#532A6E"), spaceBefore=12, spaceAfter=7)
    body = ParagraphStyle("CampusBody", parent=styles["BodyText"], fontName=font, fontSize=10.5, leading=17, textColor=colors.HexColor("#24324A"), spaceAfter=7)
    source_style = ParagraphStyle("CampusSource", parent=body, fontSize=8.5, leading=13, textColor=colors.HexColor("#596273"))
    document = SimpleDocTemplate(str(path), pagesize=A4, rightMargin=22 * mm, leftMargin=22 * mm, topMargin=20 * mm, bottomMargin=20 * mm, title=plan.title, author=plan.author or "清问·TsingAsk V2")
    story: list[Any] = [Paragraph(plan.title, title)]
    if plan.subtitle:
        story.append(Paragraph(plan.subtitle, subtitle))
    for section in plan.sections:
        story.append(Paragraph(section.heading, heading))
        story.extend(Paragraph(text.replace("\n", "<br/>"), body) for text in section.paragraphs)
        if section.bullets:
            story.append(ListFlowable([ListItem(Paragraph(text, body)) for text in section.bullets], bulletType="bullet", leftIndent=18))
        if section.table:
            data = [[Paragraph(str(value), body) for value in row] for row in section.table]
            table = Table(data, repeatRows=1, hAlign="LEFT")
            table.setStyle(TableStyle([
                ("FONTNAME", (0, 0), (-1, -1), font),
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#EEE8F2")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#532A6E")),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#D9DEE7")),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]))
            story.extend([table, Spacer(1, 6)])
    if plan.sources:
        story.append(Paragraph("资料来源", heading))
        for source in plan.sources:
            story.append(Paragraph(f"{source.get('title', '来源')}：{source.get('url', '')}", source_style))

    def footer(canvas: Any, doc: Any) -> None:
        canvas.saveState()
        canvas.setFont(font, 8)
        canvas.setFillColor(colors.HexColor("#7A8190"))
        canvas.drawRightString(A4[0] - 22 * mm, 11 * mm, f"第 {doc.page} 页")
        canvas.restoreState()

    document.build(story, onFirstPage=footer, onLaterPages=footer)
    return path


def read_pdf(path: str | Path) -> dict[str, Any]:
    import pdfplumber

    pages = []
    with pdfplumber.open(path) as pdf:
        for number, page in enumerate(pdf.pages, 1):
            pages.append({"page_number": number, "text": page.extract_text() or "", "width": page.width, "height": page.height})
    return {"format": "pdf", "pages": pages, "page_count": len(pages)}


def modify_pdf(
    input_path: str | Path,
    *,
    replacements: dict[str, str] | None = None,
    output_path: str | Path | None = None,
) -> tuple[Path, int, tuple[str, ...]]:
    from pypdf import PdfReader, PdfWriter

    source = Path(input_path).resolve()
    reader = PdfReader(source)
    fields = reader.get_fields() or {}
    field_updates = {key: value for key, value in (replacements or {}).items() if key in fields}
    if field_updates:
        path = dedupe_path(ensure_output_path(f"{source.stem}_filled", "pdf", output_path))
        writer = PdfWriter()
        writer.clone_document_from_reader(reader)
        writer.update_page_form_field_values(None, field_updates, auto_regenerate=False)
        with path.open("wb") as handle:
            writer.write(handle)
        verified = PdfReader(path).get_fields() or {}
        changed = sum(str(verified.get(key, {}).get("/V", "")) == str(value) for key, value in field_updates.items())
        if changed != len(field_updates):
            raise RuntimeError("PDF form verification failed after writing")
        return path, changed, ("已原位填写可交互 PDF 表单字段；未扁平化，原版式保持不变。",)
    extracted = read_pdf(input_path)
    changed = 0
    sections = []
    for page in extracted["pages"]:
        text = page["text"]
        updated = text
        for old, new in (replacements or {}).items():
            updated = updated.replace(old, new)
        changed += int(updated != text)
        sections.append(SectionSpec(heading=f"原文件第 {page['page_number']} 页", paragraphs=[updated or "[此页未提取到文本]"]))
    plan = FilePlan(
        title=f"{Path(input_path).stem}（修改版）",
        output_format="pdf",
        template_key="course_report",
        subtitle="基于原 PDF 文本重排导出",
        sections=sections,
    )
    path = create_pdf(plan, output_path)
    warning = ("PDF 修改采用文本提取后重新排版；复杂原版式、批注、表单或扫描图像不能保证保留。",)
    return path, changed, warning
