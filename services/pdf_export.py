import calendar
from collections import defaultdict

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
from reportlab.graphics.shapes import Drawing, Rect, String, Group
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, KeepTogether,
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

from models import Config, DayEntry, DayFlags, EventType
from services.calculator import calc_monthly_summary

WEEKDAY_NAMES = ["seg", "ter", "qua", "qui", "sex", "sáb", "dom"]
MONTH_NAMES = [
    "", "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
    "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro",
]

# Theme colors
HEADER_BG = colors.HexColor("#2b2b2b")
WEEKEND_BG = colors.HexColor("#f0f0f0")
BORDER_COLOR = colors.HexColor("#cccccc")
SUMMARY_HEADER_BG = colors.HexColor("#37474f")

# Consistent font
FONT = "Helvetica"
FONT_BOLD = "Helvetica-Bold"


def _hex_to_color(hex_str: str) -> colors.Color:
    hex_str = hex_str.lstrip("#")
    r, g, b = int(hex_str[0:2], 16), int(hex_str[2:4], 16), int(hex_str[4:6], 16)
    return colors.Color(r / 255, g / 255, b / 255)


def _fmt_brl(value: float) -> str:
    return f"R$ {value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _fmt_hours(value: float) -> str:
    if value == 0:
        return "-"
    return f"{value:g}".replace(".", ",")


def _build_event_badges(
    day_entries: list[DayEntry],
    et_map: dict[int, EventType],
    max_width: float,
) -> Drawing | None:
    """Build a Drawing with rounded-rect badges for each event."""
    badge_height = 11
    badge_radius = 3
    badge_pad_x = 3
    badge_gap = 3
    font_size = 6
    row_height = badge_height + 1

    # Build badge specs: (text, color)
    badges = []
    for entry in day_entries:
        if not entry.event_type_id and entry.hours == 0:
            continue
        et = et_map.get(entry.event_type_id)
        hours_str = f"{entry.hours:g}".replace(".", ",")
        if et:
            text = f"{et.name} ({hours_str}h)"
            badges.append((text, et.color))
        else:
            badges.append((f"{hours_str}h", "#607D8B"))

    if not badges:
        return None

    # Calculate badge widths
    badge_specs = []
    for text, color in badges:
        text_w = stringWidth(text, FONT, font_size)
        w = text_w + badge_pad_x * 2
        badge_specs.append((text, color, w))

    d = Drawing(max_width, row_height)

    x = 0
    for text, color, w in badge_specs:
        if x + w > max_width and x > 0:
            break
        r = Rect(x, 1, w, badge_height, rx=badge_radius, ry=badge_radius)
        r.fillColor = _hex_to_color(color)
        r.strokeColor = _hex_to_color(color)
        d.add(r)

        s = String(x + badge_pad_x, 4, text,
                   fontSize=font_size, fillColor=colors.white, fontName=FONT)
        d.add(s)

        x += w + badge_gap

    return d


def _build_pie_chart(
    entries: list[DayEntry],
    et_map: dict[int, EventType],
    event_types: list[EventType],
    width: float,
) -> Drawing:
    """Build a pie chart showing hours distribution by event type."""
    from reportlab.graphics.charts.piecharts import Pie

    # Aggregate hours by event type
    hours_by_type: dict[int, float] = {}
    for e in entries:
        if e.event_type_id and e.hours > 0:
            hours_by_type[e.event_type_id] = hours_by_type.get(e.event_type_id, 0) + e.hours

    # Filter to types with hours, keep order from event_types
    chart_data = []
    for et in event_types:
        h = hours_by_type.get(et.id, 0)
        if h > 0:
            chart_data.append((et, h))

    height = 115
    d = Drawing(width, height)

    if not chart_data:
        s = String(width / 2, height / 2, "Sem dados", fontSize=9,
                   fillColor=colors.HexColor("#999999"), textAnchor="middle",
                   fontName=FONT)
        d.add(s)
        return d

    total_hours = sum(h for _, h in chart_data)

    pie_size = 85
    pie = Pie()
    pie.x = 5
    pie.y = (height - pie_size) / 2
    pie.width = pie_size
    pie.height = pie_size
    pie.data = [h for _, h in chart_data]
    pie.labels = None
    pie.slices.strokeWidth = 0.5
    pie.slices.strokeColor = colors.white

    for i, (et, _) in enumerate(chart_data):
        pie.slices[i].fillColor = _hex_to_color(et.color)

    d.add(pie)

    # Legend to the right of pie: [color] Name XX% (XXh)
    legend_x = pie.x + pie_size + 10
    legend_y = pie.y + pie_size - 6
    line_height = 14

    for i, (et, h) in enumerate(chart_data):
        pct = (h / total_hours) * 100
        hours_str = f"{h:g}".replace(".", ",")
        y_pos = legend_y - i * line_height

        # Color square
        dot = Rect(legend_x, y_pos - 1, 10, 10, rx=2, ry=2)
        dot.fillColor = _hex_to_color(et.color)
        dot.strokeColor = _hex_to_color(et.color)
        d.add(dot)

        # Label: "Normal 92%" in dark + "(23h)" in muted
        main_text = f"{et.name} {pct:.0f}%"
        label = String(legend_x + 14, y_pos,
                       main_text,
                       fontSize=7, fillColor=colors.HexColor("#333333"),
                       fontName=FONT)
        # Measure main text width to position the hours part
        from reportlab.pdfbase.pdfmetrics import stringWidth
        main_w = stringWidth(main_text, FONT, 7)
        hours_label = String(legend_x + 14 + main_w + 2, y_pos,
                             f"({hours_str}h)",
                             fontSize=5, fillColor=colors.HexColor("#999999"),
                             fontName=FONT)
        d.add(hours_label)
        d.add(label)

    return d


def _build_legend_drawing(event_types: list[EventType], total_width: float) -> Drawing:
    """Build a Drawing with rounded-rect colored chips for the legend."""
    height = 16
    d = Drawing(total_width, height)

    n = len(event_types)
    gap = 3
    chip_width = (total_width - gap * (n - 1)) / n
    chip_height = 14
    y = 1

    for i, et in enumerate(event_types):
        x = i * (chip_width + gap)
        color = _hex_to_color(et.color)
        r = Rect(x, y, chip_width, chip_height, rx=4, ry=4)
        r.fillColor = color
        r.strokeColor = color
        d.add(r)

        s = String(
            x + chip_width / 2, y + 5,
            et.name,
            fontSize=7,
            fillColor=colors.white,
            textAnchor="middle",
            fontName=FONT_BOLD,
        )
        d.add(s)

    return d


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

    # Group entries by day
    entries_by_day: dict[int, list[DayEntry]] = defaultdict(list)
    for e in entries:
        entries_by_day[e.day].append(e)

    num_days = calendar.monthrange(year, month)[1]
    month_name = MONTH_NAMES[month]

    doc = SimpleDocTemplate(
        filepath,
        pagesize=A4,
        leftMargin=12 * mm,
        rightMargin=12 * mm,
        topMargin=10 * mm,
        bottomMargin=10 * mm,
    )

    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "ReportTitle", parent=styles["Title"],
        fontSize=16, spaceAfter=0,
        textColor=colors.HexColor("#212121"),
        fontName=FONT_BOLD,
    )
    subtitle_style = ParagraphStyle(
        "ReportSubtitle", parent=styles["Normal"],
        fontSize=9, alignment=TA_CENTER,
        textColor=colors.HexColor("#757575"),
        spaceAfter=2 * mm,
        fontName=FONT,
    )
    cell_style = ParagraphStyle(
        "Cell", parent=styles["Normal"],
        fontSize=7, leading=9,
        fontName=FONT,
    )
    cell_center = ParagraphStyle(
        "CellCenter", parent=cell_style,
        alignment=TA_CENTER,
    )
    chip_style = ParagraphStyle(
        "Chip", parent=cell_style,
        fontSize=7, leading=9,
    )
    right_aligned = ParagraphStyle(
        "RightAligned", parent=cell_style,
        alignment=TA_RIGHT,
    )

    elements = []

    # --- Header ---
    elements.append(Paragraph("Relatório Mensal", title_style))
    subtitle_parts = [f"{month_name} / {year}"]
    if config.nome:
        subtitle_parts.append(f"— {config.nome}")
    elements.append(Paragraph(" ".join(subtitle_parts), subtitle_style))

    # --- Main Table ---
    # Columns: Dia | Sem | Eventos | Horas | VT | VR
    col_widths = [12 * mm, 12 * mm, 110 * mm, 16 * mm, 12 * mm, 12 * mm]
    total_width = sum(col_widths)

    # Legend as first row
    legend_drawing = _build_legend_drawing(event_types, total_width)
    legend_row = [legend_drawing, "", "", "", "", ""]

    header_row = [
        Paragraph('<font color="white"><b>Dia</b></font>', cell_center),
        Paragraph('<font color="white"><b>Sem</b></font>', cell_center),
        Paragraph('<font color="white"><b>Eventos</b></font>', cell_center),
        Paragraph('<font color="white"><b>Horas</b></font>', cell_center),
        Paragraph('<font color="white"><b>VT</b></font>', cell_center),
        Paragraph('<font color="white"><b>VR</b></font>', cell_center),
    ]
    data = [legend_row, header_row]

    for day in range(1, num_days + 1):
        weekday = calendar.weekday(year, month, day)
        day_entries = entries_by_day.get(day, [])

        day_hours = sum(
            e.hours for e in day_entries
            if e.event_type_id or e.hours > 0
        )

        events_cell = _build_event_badges(day_entries, et_map, col_widths[2] - 6)
        if events_cell is None:
            events_cell = ""

        f = flags_map.get(day)
        vt_text = "✓" if f and f.vt else ""
        vr_text = "✓" if f and f.vr else ""

        row = [
            Paragraph(f"<b>{day}</b>", cell_center),
            Paragraph(WEEKDAY_NAMES[weekday], cell_center),
            events_cell,
            Paragraph(f"<b>{_fmt_hours(day_hours)}</b>", cell_center),
            Paragraph(vt_text, cell_center),
            Paragraph(vr_text, cell_center),
        ]
        data.append(row)

    table = Table(data, colWidths=col_widths, repeatRows=2)

    style_cmds = [
        # Legend row (row 0)
        ("SPAN", (0, 0), (-1, 0)),
        ("BACKGROUND", (0, 0), (-1, 0), colors.white),
        ("TOPPADDING", (0, 0), (-1, 0), 0),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 1),
        ("LEFTPADDING", (0, 0), (-1, 0), 0),
        ("RIGHTPADDING", (0, 0), (-1, 0), 0),
        # Header row (row 1)
        ("BACKGROUND", (0, 1), (-1, 1), HEADER_BG),
        ("TEXTCOLOR", (0, 1), (-1, 1), colors.white),
        # General
        ("FONTSIZE", (0, 0), (-1, -1), 7),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("GRID", (0, 1), (-1, -1), 0.4, BORDER_COLOR),
        ("TOPPADDING", (0, 1), (-1, -1), 1),
        ("BOTTOMPADDING", (0, 1), (-1, -1), 1),
        ("LEFTPADDING", (0, 1), (-1, -1), 3),
        ("RIGHTPADDING", (0, 1), (-1, -1), 3),
        # Eventos column left-aligned
        ("ALIGN", (2, 2), (2, -1), "LEFT"),
    ]

    for day in range(1, num_days + 1):
        row_idx = day + 1
        weekday = calendar.weekday(year, month, day)
        if weekday >= 5:
            style_cmds.append(
                ("BACKGROUND", (0, row_idx), (-1, row_idx), WEEKEND_BG)
            )
        elif day % 2 == 0:
            style_cmds.append(
                ("BACKGROUND", (0, row_idx), (-1, row_idx), colors.HexColor("#fafafa"))
            )

    table.setStyle(TableStyle(style_cmds))
    elements.append(table)

    elements.append(Spacer(1, 6 * mm))

    # --- Summary section: pie chart | resumo | financeiro ---
    # All widths must sum to total_width for alignment
    summary = calc_monthly_summary(year, month, entries, flags, config, ae_fechadas)

    pie_col_w = 58 * mm
    pie_gap_w = 8 * mm
    table_gap_w = 4 * mm
    remaining = total_width - pie_col_w - pie_gap_w - table_gap_w
    resumo_col_w = remaining * 0.38
    fin_col_w = remaining * 0.62

    # Pie chart
    pie_drawing = _build_pie_chart(entries, et_map, event_types, pie_col_w)

    # Resumo table
    resumo_label_w = resumo_col_w * 0.62
    resumo_val_w = resumo_col_w * 0.38
    resumo_data = [
        [Paragraph('<font color="white"><b>Resumo</b></font>', cell_center), ""],
        ["Horas Totais", Paragraph(f"<b>{_fmt_hours(summary.total_hours)}</b>", right_aligned)],
        ["AE Fechadas", Paragraph(f"<b>{summary.ae_fechadas}</b>", right_aligned)],
        ["Transportes", Paragraph(f"<b>{summary.transport_days}</b>", right_aligned)],
        ["Alimentação", Paragraph(f"<b>{summary.meal_days}</b>", right_aligned)],
        ["", ""],
    ]
    row_h = 17
    header_h = 19
    row_heights = [header_h] + [row_h] * 5
    resumo_table = Table(resumo_data, colWidths=[resumo_label_w, resumo_val_w], rowHeights=row_heights)
    resumo_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), SUMMARY_HEADER_BG),
        ("SPAN", (0, 0), (-1, 0)),
        ("FONTSIZE", (0, 0), (-1, -1), 7),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("BOX", (0, 0), (-1, -1), 0.5, BORDER_COLOR),
        ("LINEBELOW", (0, 0), (-1, 0), 0.5, BORDER_COLOR),
    ]))

    # Financeiro table — show config values in muted parentheses
    muted = '<font color="#999999" size="5">'
    fin_label_w = fin_col_w * 0.50
    fin_val_w = fin_col_w * 0.50
    fin_data = [
        [Paragraph('<font color="white"><b>Financeiro</b></font>', cell_center), ""],
        [Paragraph(f'Salário {muted}({_fmt_brl(config.valor_hora)}/h)</font>', cell_style),
         Paragraph(f"{_fmt_brl(summary.salary)}", right_aligned)],
        [Paragraph(f'Bonus AE {muted}({_fmt_brl(config.valor_ae)}/ae)</font>', cell_style),
         Paragraph(f"{_fmt_brl(summary.bonus_ae)}", right_aligned)],
        [Paragraph(f'VT {muted}({_fmt_brl(config.vt_dia)}/dia)</font>', cell_style),
         Paragraph(f"{_fmt_brl(summary.vt_total)}", right_aligned)],
        [Paragraph(f'VR {muted}({_fmt_brl(config.vr_dia)}/dia)</font>', cell_style),
         Paragraph(f"{_fmt_brl(summary.vr_total)}", right_aligned)],
        [Paragraph("<b>TOTAL</b>", cell_style),
         Paragraph(f"<b>{_fmt_brl(summary.total)}</b>",
                    ParagraphStyle("rb", parent=cell_style, alignment=TA_RIGHT, fontSize=8))],
    ]
    fin_table = Table(fin_data, colWidths=[fin_label_w, fin_val_w], rowHeights=row_heights)
    fin_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), SUMMARY_HEADER_BG),
        ("SPAN", (0, 0), (-1, 0)),
        ("FONTSIZE", (0, 0), (-1, -1), 7),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("BOX", (0, 0), (-1, -1), 0.5, BORDER_COLOR),
        ("LINEBELOW", (0, 0), (-1, 0), 0.5, BORDER_COLOR),
        ("LINEABOVE", (0, -1), (-1, -1), 1, colors.HexColor("#333333")),
        ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#e8f5e9")),
    ]))

    # Wrapper: pie | pie_gap | resumo | table_gap | financeiro = total_width
    wrapper_data = [[pie_drawing, "", resumo_table, "", fin_table]]
    wrapper = Table(
        wrapper_data,
        colWidths=[pie_col_w, pie_gap_w, resumo_col_w, table_gap_w, fin_col_w],
    )
    wrapper.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
    ]))

    elements.append(KeepTogether([wrapper]))

    # --- Footer ---
    elements.append(Spacer(1, 3 * mm))
    footer_style = ParagraphStyle(
        "Footer", parent=styles["Normal"],
        fontSize=7, textColor=colors.HexColor("#9e9e9e"),
        alignment=TA_CENTER,
        fontName=FONT,
    )
    elements.append(Paragraph(
        f"Gerado por Controle de Horas • {month_name} {year}",
        footer_style,
    ))

    doc.build(elements)
