from dataclasses import dataclass


@dataclass
class EventType:
    id: int
    name: str
    color: str


@dataclass
class DayEntry:
    year: int
    month: int
    day: int
    slot: int
    event_type_id: int | None
    hours: float


@dataclass
class DayFlags:
    year: int
    month: int
    day: int
    vt: bool
    vr: bool


@dataclass
class Config:
    nome: str
    valor_hora: float
    valor_ae: float
    vt_dia: float
    vr_dia: float


@dataclass
class MonthlySummary:
    year: int
    month: int
    total_hours: float
    ae_fechadas: int
    adjustments_total: float
    transport_days: int
    meal_days: int
    salary: float
    bonus_ae: float
    vt_total: float
    vr_total: float
    total: float


@dataclass
class MonthAdjustment:
    description: str
    value: float
