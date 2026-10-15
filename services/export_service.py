"""Экспорт табличных отчётов в Excel (.xlsx) и PDF."""

import os

from openpyxl import Workbook
from openpyxl.styles import Font

FONT_CANDIDATES = (
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/TTF/DejaVuSans.ttf",
    "/usr/share/fonts/dejavu/DejaVuSans.ttf",
)


def export_excel(path: str, title: str, headers: tuple, rows) -> None:
    """Сохраняет отчёт в файл Excel.

    Args:
        path: путь к файлу .xlsx.
        title: название листа.
        headers: заголовки колонок.
        rows: строки данных.
    """
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = title[:31]
    sheet.append(list(headers))
    for cell in sheet[1]:
        cell.font = Font(bold=True)
    for row in rows:
        sheet.append(list(row))
    for column_cells in sheet.columns:
        length = max(len(str(cell.value or "")) for cell in column_cells)
        sheet.column_dimensions[column_cells[0].column_letter].width = min(
            max(length + 2, 8), 40
        )
    workbook.save(path)


def _cyrillic_font():
    """Подбирает шрифт с кириллицей для PDF.

    Returns:
        Имя шрифта для reportlab.
    """
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    for path in FONT_CANDIDATES:
        if os.path.exists(path):
            pdfmetrics.registerFont(TTFont("DejaVu", path))
            return "DejaVu"
    raise RuntimeError(
        "Не найден шрифт DejaVuSans (пакет fonts-dejavu-core) — PDF с "
        "кириллицей без него не собрать. Установите: "
        "sudo apt install fonts-dejavu-core"
    )


def export_pdf(path: str, title: str, headers: tuple, rows) -> None:
    """Сохраняет отчёт в файл PDF (альбомная ориентация A4).

    Args:
        path: путь к файлу .pdf.
        title: заголовок отчёта.
        headers: заголовки колонок.
        rows: строки данных.
    """
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.platypus import (Paragraph, SimpleDocTemplate, Table,
                                    TableStyle)

    font = _cyrillic_font()
    heading_style = ParagraphStyle("h", fontName=font, fontSize=14, leading=18)
    cell_style = ParagraphStyle("c", fontName=font, fontSize=8, leading=10)

    document = SimpleDocTemplate(path, pagesize=landscape(A4),
                                 topMargin=28, bottomMargin=28)
    story = [Paragraph(title, heading_style), Paragraph(" ", cell_style)]

    def fmt(value):
        return str(value if value is not None else "")

    data = [[Paragraph(f"<b>{fmt(h)}</b>", cell_style) for h in headers]]
    for row in rows:
        data.append([Paragraph(fmt(cell), cell_style) for cell in row])
    table = Table(data, repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1a1f33")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#c9cdd6")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1),
         [colors.white, colors.HexColor("#f5f6fa")]),
    ]))
    story.append(table)
    document.build(story)
