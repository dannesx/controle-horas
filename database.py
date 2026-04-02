import sqlite3
from pathlib import Path

from models import Config, DayEntry, DayFlags, EventType, MonthlySummary

DB_PATH = Path(__file__).parent / "data" / "controle_horas.db"

DEFAULT_EVENT_TYPES = [
    ("Normal", "#8ac926"),
    ("Reposição", "#fe994a"),
    ("Reunião", "#FDD835"),
    ("Experimental", "#1982c4"),
    ("Coordenação", "#6a4c93"),
    ("Outros", "#ff595e"),
]


def get_connection() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db() -> None:
    conn = get_connection()
    try:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS config (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                nome       TEXT NOT NULL DEFAULT '',
                valor_hora REAL NOT NULL DEFAULT 0,
                valor_ae   REAL NOT NULL DEFAULT 0,
                vt_dia     REAL NOT NULL DEFAULT 0,
                vr_dia     REAL NOT NULL DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS event_types (
                id    INTEGER PRIMARY KEY AUTOINCREMENT,
                name  TEXT NOT NULL UNIQUE,
                color TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS day_entries (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                year          INTEGER NOT NULL,
                month         INTEGER NOT NULL,
                day           INTEGER NOT NULL,
                slot          INTEGER NOT NULL,
                event_type_id INTEGER REFERENCES event_types(id),
                hours         REAL NOT NULL DEFAULT 0.0,
                UNIQUE(year, month, day, slot)
            );

            CREATE TABLE IF NOT EXISTS day_flags (
                year  INTEGER NOT NULL,
                month INTEGER NOT NULL,
                day   INTEGER NOT NULL,
                vt    INTEGER NOT NULL DEFAULT 0,
                vr    INTEGER NOT NULL DEFAULT 0,
                PRIMARY KEY (year, month, day)
            );

            CREATE TABLE IF NOT EXISTS month_extras (
                year        INTEGER NOT NULL,
                month       INTEGER NOT NULL,
                ae_fechadas INTEGER NOT NULL DEFAULT 0,
                PRIMARY KEY (year, month)
            );
        """)

        # Seed config if empty
        row = conn.execute("SELECT COUNT(*) FROM config").fetchone()
        if row[0] == 0:
            conn.execute("INSERT INTO config (id) VALUES (1)")

        # Migrate: add nome column if missing
        cols = [r[1] for r in conn.execute("PRAGMA table_info(config)").fetchall()]
        if "nome" not in cols:
            conn.execute("ALTER TABLE config ADD COLUMN nome TEXT NOT NULL DEFAULT ''")
        if "tema" not in cols:
            conn.execute("ALTER TABLE config ADD COLUMN tema TEXT NOT NULL DEFAULT 'dark'")

        # Seed event types if empty
        row = conn.execute("SELECT COUNT(*) FROM event_types").fetchone()
        if row[0] == 0:
            conn.executemany(
                "INSERT INTO event_types (name, color) VALUES (?, ?)",
                DEFAULT_EVENT_TYPES,
            )

        conn.commit()
    finally:
        conn.close()


# --- Config ---

def get_config() -> Config:
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT nome, valor_hora, valor_ae, vt_dia, vr_dia FROM config WHERE id = 1"
        ).fetchone()
        return Config(*row)
    finally:
        conn.close()


def update_config(config: Config) -> None:
    conn = get_connection()
    try:
        conn.execute(
            "UPDATE config SET nome=?, valor_hora=?, valor_ae=?, vt_dia=?, vr_dia=? WHERE id=1",
            (config.nome, config.valor_hora, config.valor_ae, config.vt_dia, config.vr_dia),
        )
        conn.commit()
    finally:
        conn.close()


def get_tema() -> str:
    conn = get_connection()
    try:
        row = conn.execute("SELECT tema FROM config WHERE id = 1").fetchone()
        return row[0] if row else "dark"
    finally:
        conn.close()


def set_tema(tema: str) -> None:
    conn = get_connection()
    try:
        conn.execute("UPDATE config SET tema=? WHERE id=1", (tema,))
        conn.commit()
    finally:
        conn.close()


# --- Event Types ---

def get_event_types() -> list[EventType]:
    conn = get_connection()
    try:
        rows = conn.execute("SELECT id, name, color FROM event_types ORDER BY id").fetchall()
        return [EventType(*r) for r in rows]
    finally:
        conn.close()


def update_event_type_color(event_id: int, color: str) -> None:
    conn = get_connection()
    try:
        conn.execute(
            "UPDATE event_types SET color=? WHERE id=?",
            (color, event_id),
        )
        conn.commit()
    finally:
        conn.close()


# --- Day Entries ---

def get_month_entries(year: int, month: int) -> list[DayEntry]:
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT year, month, day, slot, event_type_id, hours "
            "FROM day_entries WHERE year=? AND month=? ORDER BY day, slot",
            (year, month),
        ).fetchall()
        return [DayEntry(*r) for r in rows]
    finally:
        conn.close()


def upsert_day_entry(entry: DayEntry) -> None:
    conn = get_connection()
    try:
        conn.execute(
            "INSERT INTO day_entries (year, month, day, slot, event_type_id, hours) "
            "VALUES (?, ?, ?, ?, ?, ?) "
            "ON CONFLICT(year, month, day, slot) DO UPDATE SET "
            "event_type_id=excluded.event_type_id, hours=excluded.hours",
            (entry.year, entry.month, entry.day, entry.slot,
             entry.event_type_id, entry.hours),
        )
        conn.commit()
    finally:
        conn.close()


def get_day_entries(year: int, month: int, day: int) -> list[DayEntry]:
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT year, month, day, slot, event_type_id, hours "
            "FROM day_entries WHERE year=? AND month=? AND day=? ORDER BY slot",
            (year, month, day),
        ).fetchall()
        return [DayEntry(*r) for r in rows]
    finally:
        conn.close()


def delete_day_entry(year: int, month: int, day: int, slot: int) -> None:
    conn = get_connection()
    try:
        conn.execute(
            "DELETE FROM day_entries WHERE year=? AND month=? AND day=? AND slot=?",
            (year, month, day, slot),
        )
        conn.commit()
    finally:
        conn.close()


def delete_day_entries_for_day(year: int, month: int, day: int) -> None:
    conn = get_connection()
    try:
        conn.execute(
            "DELETE FROM day_entries WHERE year=? AND month=? AND day=?",
            (year, month, day),
        )
        conn.commit()
    finally:
        conn.close()


# --- Day Flags ---

def get_month_flags(year: int, month: int) -> list[DayFlags]:
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT year, month, day, vt, vr FROM day_flags "
            "WHERE year=? AND month=? ORDER BY day",
            (year, month),
        ).fetchall()
        return [DayFlags(r[0], r[1], r[2], bool(r[3]), bool(r[4])) for r in rows]
    finally:
        conn.close()


def upsert_day_flags(flags: DayFlags) -> None:
    conn = get_connection()
    try:
        conn.execute(
            "INSERT INTO day_flags (year, month, day, vt, vr) "
            "VALUES (?, ?, ?, ?, ?) "
            "ON CONFLICT(year, month, day) DO UPDATE SET "
            "vt=excluded.vt, vr=excluded.vr",
            (flags.year, flags.month, flags.day, int(flags.vt), int(flags.vr)),
        )
        conn.commit()
    finally:
        conn.close()


def get_day_flags(year: int, month: int, day: int) -> DayFlags | None:
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT year, month, day, vt, vr FROM day_flags "
            "WHERE year=? AND month=? AND day=?",
            (year, month, day),
        ).fetchone()
        if row:
            return DayFlags(row[0], row[1], row[2], bool(row[3]), bool(row[4]))
        return None
    finally:
        conn.close()


# --- Month Extras ---

def get_ae_fechadas(year: int, month: int) -> int:
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT ae_fechadas FROM month_extras WHERE year=? AND month=?",
            (year, month),
        ).fetchone()
        return row[0] if row else 0
    finally:
        conn.close()


def set_ae_fechadas(year: int, month: int, value: int) -> None:
    conn = get_connection()
    try:
        conn.execute(
            "INSERT INTO month_extras (year, month, ae_fechadas) "
            "VALUES (?, ?, ?) "
            "ON CONFLICT(year, month) DO UPDATE SET ae_fechadas=excluded.ae_fechadas",
            (year, month, value),
        )
        conn.commit()
    finally:
        conn.close()


# --- Yearly Summary ---

def get_yearly_totals(year: int) -> list[tuple[int, float]]:
    """Returns list of (month, total_salary) for the given year."""
    conn = get_connection()
    try:
        config = get_config()
        results = []
        for month in range(1, 13):
            entries = get_month_entries(year, month)
            flags = get_month_flags(year, month)
            ae = get_ae_fechadas(year, month)

            total_hours = sum(e.hours for e in entries)
            transport_days = sum(1 for f in flags if f.vt)
            meal_days = sum(1 for f in flags if f.vr)

            salary = total_hours * config.valor_hora
            bonus_ae = ae * config.valor_ae
            vt_total = transport_days * config.vt_dia
            vr_total = meal_days * config.vr_dia
            total = salary + bonus_ae + vt_total + vr_total

            results.append((month, total))
        return results
    finally:
        conn.close()
