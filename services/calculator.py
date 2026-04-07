from models import Config, DayEntry, DayFlags, MonthlySummary


def calc_monthly_summary(
    year: int,
    month: int,
    entries: list[DayEntry],
    flags: list[DayFlags],
    config: Config,
    ae_fechadas: int = 0,
    adjustments_total: float = 0.0,
) -> MonthlySummary:
    total_hours = sum(e.hours for e in entries)
    transport_days = sum(1 for f in flags if f.vt)
    meal_days = sum(1 for f in flags if f.vr)

    salary = total_hours * config.valor_hora
    bonus_ae = ae_fechadas * config.valor_ae
    vt_total = transport_days * config.vt_dia
    vr_total = meal_days * config.vr_dia
    total = salary + bonus_ae + vt_total + vr_total + adjustments_total

    return MonthlySummary(
        year=year,
        month=month,
        total_hours=total_hours,
        ae_fechadas=ae_fechadas,
        adjustments_total=adjustments_total,
        transport_days=transport_days,
        meal_days=meal_days,
        salary=salary,
        bonus_ae=bonus_ae,
        vt_total=vt_total,
        vr_total=vr_total,
        total=total,
    )
