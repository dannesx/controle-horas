import calendar

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

from models import Config, DayEntry, DayFlags, EventType
from services.calculator import calc_monthly_summary

WEEKDAY_NAMES = ["seg", "ter", "qua", "qui", "sex", "sáb", "dom"]
MONTH_NAMES = [
    "", "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
    "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro",
]


def _hex_to_color(hex_str: str) -> colors.Color:
    hex_str = hex_str.lstrip("#")
    r, g, b = int(hex_str[0:2], 16), int(hex_str[2:4], 16), int(hex_str[4:6], 16)
    return colors.Color(r / 255, g / 255, b / 255)


def _fmt_brl(value: float) -> str:
    return f"R$ {value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def export_month_pdf(
    year: int,
    month: int,
    entries: list[DayEntry],
    flags: list[DayFlags],
    event_types: list[EventType],
    config: Config,
    ae_fechadas: int,
    filepath: str,
) -> None:
    et_map = {et.id: et for et in event_types}
    flags_map = {f.day: f for f in flags}

    # Group entries by (day, slot)
    entries_map: dict[tuple[int, int], DayEntry] = {}
    for e in entries:
        entries_map[(e.day, e.slot)] = e

    num_days = calendar.monthrange(year, month)[1]

    doc = SimpleDocTemplate(
        filepath,
        pagesize=landscape(A4),
        leftMargin=10 * mm,
        rightMargin=10 * mm,
        topMargin=15 * mm,
        bottomMargin=15 * mm,
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "Title2", parent=styles["Title"],
        fontSize=16, spaceAfter=10,
    )
    elements = []

    # Title
    elements.append(
        Paragraph(f"Relatório Mensal - {MONTH_NAMES[month]} / {year}", title_style)
    )
    elements.append(Spacer(1, 5 * mm))

    # Table header
    header = ["Dia", "Sem"]
    for i in range(1, 9):
        header.append(f"Evt{i}")
    header += ["Horas", "VT", "VR"]

    data = [header]

    # Table rows
    for day in range(1, num_days + 1):
        weekday = calendar.weekday(year, month, day)
        row = [str(day), WEEKDAY_NAMES[weekday]]

        day_hours = 0.0
        for slot in range(1, 9):
            entry = entries_map.get((day, slot))
            if entry and (entry.event_type_id or entry.hours):
                et_name = et_map[entry.event_type_id].name if entry.event_type_id else ""
                cell = f"{et_name} {entry.hours}" if et_name else str(entry.hours)
                row.append(cell.strip())
                day_hours += entry.hours
            else:
                row.append("")

        row.append(str(day_hours) if day_hours else "0")

        f = flags_map.get(day)
        row.append("X" if f and f.vt else "")
        row.append("X" if f and f.vr else "")

        data.append(row)

    col_widths = [25, 25] + [60] * 8 + [35, 20, 20]

    table = Table(data, colWidths=[w * mm / 2.5 for w in col_widths])

    style_cmds = [
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#333333")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTSIZE", (0, 0), (-1, -1), 7),
        ("FONTSIZE", (0, 0), (-1, 0), 8),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
    ]

    # Color weekend rows
    for day in range(1, num_days + 1):
        weekday = calendar.weekday(year, month, day)
        if weekday >= 5:
            style_cmds.append(
                ("BACKGROUND", (0, day), (-1, day), colors.HexColor("#e0e0e0"))
            )

    # Color event cells
    for day in range(1, num_days + 1):
        for slot in range(1, 9):
            entry = entries_map.get((day, slot))
            if entry and entry.event_type_id and entry.event_type_id in et_map:
                et = et_map[entry.event_type_id]
                col_idx = slot + 1  # +1 for Dia, +1 for Sem, but slot is 1-based
                style_cmds.append(
                    ("BACKGROUND", (col_idx, day), (col_idx, day),
                     _hex_to_color(et.color))
                )
                style_cmds.append(
                    ("TEXTCOLOR", (col_idx, day), (col_idx, day), colors.white)
                )

    table.setStyle(TableStyle(style_cmds))
    elements.append(table)

    # Summary
    elements.append(Spacer(1, 8 * mm))

    summary = calc_monthly_summary(year, month, entries, flags, config, ae_fechadas)

    summary_data = [
        ["Horas Totais", str(summary.total_hours).replace(".", ","),
         "Salário", _fmt_brl(summary.salary)],
        ["AE Fechadas", str(summary.ae_fechadas),
         "Bonus AE", _fmt_brl(summary.bonus_ae)],
        ["Transportes", str(summary.transport_days),
         "VT", _fmt_brl(summary.vt_total)],
        ["Alimentação", str(summary.meal_days),
         "VR", _fmt_brl(summary.vr_total)],
        ["", "", "TOTAL", _fmt_brl(summary.total)],
    ]

    summary_table = Table(summary_data, colWidths=[80, 60, 60, 80])
    summary_table.setStyle(TableStyle([
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("ALIGN", (1, 0), (1, -1), "RIGHT"),
        ("ALIGN", (3, 0), (3, -1), "RIGHT"),
        ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
        ("LINEABOVE", (2, -1), (3, -1), 1, colors.black),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    elements.append(summary_table)

    doc.build(elements)
