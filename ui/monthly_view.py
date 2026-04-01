import calendar
from datetime import date

import customtkinter as ctk

import database
from models import DayEntry, DayFlags
from services.calculator import calc_monthly_summary

WEEKDAY_NAMES = ["seg", "ter", "qua", "qui", "sex", "sáb", "dom"]
MONTH_NAMES = [
    "", "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
    "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro",
]
NUM_SLOTS = 8


class MonthlyView(ctk.CTkFrame):
    def __init__(self, parent):
        super().__init__(parent, fg_color="transparent")

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        today = date.today()
        self.current_year = today.year
        self.current_month = today.month

        self.event_types = database.get_event_types()
        self.event_type_map = {et.id: et for et in self.event_types}
        self.event_name_to_id = {et.name: et.id for et in self.event_types}
        self.event_names = [""] + [et.name for et in self.event_types]

        # Row widget references for auto-save
        self.slot_combos: list[list[ctk.CTkComboBox]] = []
        self.slot_entries: list[list[ctk.CTkEntry]] = []
        self.vt_vars: list[ctk.IntVar] = []
        self.vr_vars: list[ctk.IntVar] = []
        self.hours_labels: list[ctk.CTkLabel] = []

        self._build_nav_bar()
        self._build_grid_area()
        self._build_legend()
        self._build_summary()
        self._load_month()

    # --- Navigation Bar ---

    def _build_nav_bar(self):
        nav = ctk.CTkFrame(self, fg_color="transparent")
        nav.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 5))
        nav.grid_columnconfigure(1, weight=1)

        btn_prev = ctk.CTkButton(nav, text="◀", width=40, command=self._prev_month)
        btn_prev.grid(row=0, column=0, padx=(0, 10))

        self.month_label = ctk.CTkLabel(
            nav, text="", font=ctk.CTkFont(size=18, weight="bold"),
        )
        self.month_label.grid(row=0, column=1)

        btn_next = ctk.CTkButton(nav, text="▶", width=40, command=self._next_month)
        btn_next.grid(row=0, column=2, padx=(10, 10))

        btn_pdf = ctk.CTkButton(
            nav, text="Exportar PDF", width=120,
            command=self._export_pdf,
        )
        btn_pdf.grid(row=0, column=3)

    def _prev_month(self):
        if self.current_month == 1:
            self.current_month = 12
            self.current_year -= 1
        else:
            self.current_month -= 1
        self._load_month()

    def _next_month(self):
        if self.current_month == 12:
            self.current_month = 1
            self.current_year += 1
        else:
            self.current_month += 1
        self._load_month()

    # --- Grid ---

    def _build_grid_area(self):
        self.grid_frame = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.grid_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=5)

    def _build_grid(self, num_days: int):
        for widget in self.grid_frame.winfo_children():
            widget.destroy()

        self.slot_combos = []
        self.slot_entries = []
        self.vt_vars = []
        self.vr_vars = []
        self.hours_labels = []

        # Header
        headers = ["Dia", "Sem"]
        for i in range(1, NUM_SLOTS + 1):
            headers.append(f"Evt{i}")
        headers += ["Horas", "VT", "VR"]

        col = 0
        for h in headers:
            if h.startswith("Evt"):
                # Event columns span 2 grid columns (combo + entry)
                lbl = ctk.CTkLabel(
                    self.grid_frame, text=h,
                    font=ctk.CTkFont(weight="bold"), width=100,
                )
                lbl.grid(row=0, column=col, columnspan=2, padx=1, pady=2)
                col += 2
            else:
                w = 50 if h in ("Dia", "Sem", "VT", "VR", "Horas") else 60
                lbl = ctk.CTkLabel(
                    self.grid_frame, text=h,
                    font=ctk.CTkFont(weight="bold"), width=w,
                )
                lbl.grid(row=0, column=col, padx=1, pady=2)
                col += 1

        # Rows
        for day_idx in range(num_days):
            day_num = day_idx + 1
            row = day_idx + 1
            weekday = calendar.weekday(self.current_year, self.current_month, day_num)
            is_weekend = weekday >= 5

            row_bg = ("gray20" if is_weekend else "transparent")

            col = 0

            # Day number
            ctk.CTkLabel(
                self.grid_frame, text=str(day_num), width=50,
                fg_color=row_bg if is_weekend else "transparent",
            ).grid(row=row, column=col, padx=1, pady=1)
            col += 1

            # Weekday
            ctk.CTkLabel(
                self.grid_frame, text=WEEKDAY_NAMES[weekday], width=50,
                fg_color=row_bg if is_weekend else "transparent",
            ).grid(row=row, column=col, padx=1, pady=1)
            col += 1

            # Event slots
            day_combos = []
            day_entries = []
            for slot in range(NUM_SLOTS):
                combo = ctk.CTkComboBox(
                    self.grid_frame, values=self.event_names,
                    width=70, height=28,
                    command=lambda val, d=day_idx: self._on_slot_change(d),
                )
                combo.set("")
                combo.grid(row=row, column=col, padx=0, pady=1)
                day_combos.append(combo)
                col += 1

                entry = ctk.CTkEntry(self.grid_frame, width=35, height=28)
                entry.grid(row=row, column=col, padx=(0, 2), pady=1)
                entry.bind("<FocusOut>", lambda e, d=day_idx: self._on_slot_change(d))
                entry.bind("<Return>", lambda e, d=day_idx: self._on_slot_change(d))
                day_entries.append(entry)
                col += 1

            self.slot_combos.append(day_combos)
            self.slot_entries.append(day_entries)

            # Hours/day label
            hours_lbl = ctk.CTkLabel(self.grid_frame, text="0", width=50)
            hours_lbl.grid(row=row, column=col, padx=1, pady=1)
            self.hours_labels.append(hours_lbl)
            col += 1

            # VT checkbox
            vt_var = ctk.IntVar(value=0)
            vt_cb = ctk.CTkCheckBox(
                self.grid_frame, text="", variable=vt_var, width=30,
                command=lambda d=day_idx: self._on_flag_change(d),
            )
            vt_cb.grid(row=row, column=col, padx=1, pady=1)
            self.vt_vars.append(vt_var)
            col += 1

            # VR checkbox
            vr_var = ctk.IntVar(value=0)
            vr_cb = ctk.CTkCheckBox(
                self.grid_frame, text="", variable=vr_var, width=30,
                command=lambda d=day_idx: self._on_flag_change(d),
            )
            vr_cb.grid(row=row, column=col, padx=1, pady=1)
            self.vr_vars.append(vr_var)

    # --- Legend ---

    def _build_legend(self):
        legend = ctk.CTkFrame(self, fg_color="transparent")
        legend.grid(row=2, column=0, sticky="ew", padx=10, pady=5)

        ctk.CTkLabel(legend, text="Legenda:", font=ctk.CTkFont(weight="bold")).pack(
            side="left", padx=(0, 10),
        )
        for et in self.event_types:
            ctk.CTkLabel(
                legend, text=f"  {et.name}  ",
                fg_color=et.color, corner_radius=4,
                text_color="white",
            ).pack(side="left", padx=3)

    # --- Summary ---

    def _build_summary(self):
        self.summary_frame = ctk.CTkFrame(self)
        self.summary_frame.grid(row=3, column=0, sticky="ew", padx=10, pady=(5, 10))

        # Left side
        left = ctk.CTkFrame(self.summary_frame, fg_color="transparent")
        left.pack(side="left", padx=20, pady=10)

        self.lbl_horas_totais = ctk.CTkLabel(left, text="Horas Totais: 0")
        self.lbl_horas_totais.pack(anchor="w")

        ae_frame = ctk.CTkFrame(left, fg_color="transparent")
        ae_frame.pack(anchor="w")
        ctk.CTkLabel(ae_frame, text="AE Fechadas:").pack(side="left")
        self.ae_entry = ctk.CTkEntry(ae_frame, width=50, height=28)
        self.ae_entry.pack(side="left", padx=5)
        self.ae_entry.insert(0, "0")
        self.ae_entry.bind("<FocusOut>", lambda e: self._on_ae_change())
        self.ae_entry.bind("<Return>", lambda e: self._on_ae_change())

        self.lbl_transportes = ctk.CTkLabel(left, text="Transportes: 0")
        self.lbl_transportes.pack(anchor="w")

        self.lbl_alimentacao = ctk.CTkLabel(left, text="Alimentação: 0")
        self.lbl_alimentacao.pack(anchor="w")

        # Right side
        right = ctk.CTkFrame(self.summary_frame, fg_color="transparent")
        right.pack(side="right", padx=20, pady=10)

        self.lbl_salario = ctk.CTkLabel(right, text="Salário: R$ 0,00")
        self.lbl_salario.pack(anchor="e")

        self.lbl_bonus_ae = ctk.CTkLabel(right, text="Bonus AE: R$ 0,00")
        self.lbl_bonus_ae.pack(anchor="e")

        self.lbl_vt = ctk.CTkLabel(right, text="VT: R$ 0,00")
        self.lbl_vt.pack(anchor="e")

        self.lbl_vr = ctk.CTkLabel(right, text="VR: R$ 0,00")
        self.lbl_vr.pack(anchor="e")

        self.lbl_total = ctk.CTkLabel(
            right, text="TOTAL: R$ 0,00",
            font=ctk.CTkFont(size=16, weight="bold"),
        )
        self.lbl_total.pack(anchor="e", pady=(5, 0))

    # --- Data Loading ---

    def _load_month(self):
        self.month_label.configure(
            text=f"{MONTH_NAMES[self.current_month]} / {self.current_year}"
        )

        num_days = calendar.monthrange(self.current_year, self.current_month)[1]
        self._build_grid(num_days)

        entries = database.get_month_entries(self.current_year, self.current_month)
        flags = database.get_month_flags(self.current_year, self.current_month)
        ae = database.get_ae_fechadas(self.current_year, self.current_month)

        # Populate entries
        for entry in entries:
            day_idx = entry.day - 1
            slot_idx = entry.slot - 1
            if 0 <= day_idx < num_days and 0 <= slot_idx < NUM_SLOTS:
                if entry.event_type_id and entry.event_type_id in self.event_type_map:
                    et = self.event_type_map[entry.event_type_id]
                    self.slot_combos[day_idx][slot_idx].set(et.name)
                if entry.hours:
                    self.slot_entries[day_idx][slot_idx].delete(0, "end")
                    self.slot_entries[day_idx][slot_idx].insert(0, str(entry.hours))

        # Populate flags
        flags_map = {f.day: f for f in flags}
        for day_idx in range(num_days):
            day_num = day_idx + 1
            if day_num in flags_map:
                f = flags_map[day_num]
                self.vt_vars[day_idx].set(1 if f.vt else 0)
                self.vr_vars[day_idx].set(1 if f.vr else 0)

        # AE Fechadas
        self.ae_entry.delete(0, "end")
        self.ae_entry.insert(0, str(ae))

        self._update_all_hours()
        self.refresh_summary()

    def on_show(self):
        self.event_types = database.get_event_types()
        self.event_type_map = {et.id: et for et in self.event_types}
        self.event_name_to_id = {et.name: et.id for et in self.event_types}

    # --- Auto-save ---

    def _on_slot_change(self, day_idx: int):
        day_num = day_idx + 1
        for slot_idx in range(NUM_SLOTS):
            combo_val = self.slot_combos[day_idx][slot_idx].get()
            entry_val = self.slot_entries[day_idx][slot_idx].get().strip()

            event_type_id = self.event_name_to_id.get(combo_val)
            try:
                hours = float(entry_val.replace(",", ".")) if entry_val else 0.0
            except ValueError:
                hours = 0.0

            if event_type_id or hours > 0:
                entry = DayEntry(
                    year=self.current_year,
                    month=self.current_month,
                    day=day_num,
                    slot=slot_idx + 1,
                    event_type_id=event_type_id,
                    hours=hours,
                )
                database.upsert_day_entry(entry)
            else:
                database.delete_day_entry(
                    self.current_year, self.current_month, day_num, slot_idx + 1,
                )

        self._update_day_hours(day_idx)
        self.refresh_summary()

    def _on_flag_change(self, day_idx: int):
        day_num = day_idx + 1
        flags = DayFlags(
            year=self.current_year,
            month=self.current_month,
            day=day_num,
            vt=bool(self.vt_vars[day_idx].get()),
            vr=bool(self.vr_vars[day_idx].get()),
        )
        database.upsert_day_flags(flags)
        self.refresh_summary()

    def _on_ae_change(self):
        try:
            val = int(self.ae_entry.get().strip())
        except ValueError:
            val = 0
        database.set_ae_fechadas(self.current_year, self.current_month, val)
        self.refresh_summary()

    # --- Calculations ---

    def _get_day_hours(self, day_idx: int) -> float:
        total = 0.0
        for slot_idx in range(NUM_SLOTS):
            entry_val = self.slot_entries[day_idx][slot_idx].get().strip()
            try:
                total += float(entry_val.replace(",", ".")) if entry_val else 0.0
            except ValueError:
                pass
        return total

    def _update_day_hours(self, day_idx: int):
        hours = self._get_day_hours(day_idx)
        self.hours_labels[day_idx].configure(
            text=str(hours).replace(".", ",") if hours else "0"
        )

    def _update_all_hours(self):
        for i in range(len(self.hours_labels)):
            self._update_day_hours(i)

    def refresh_summary(self):
        entries = database.get_month_entries(self.current_year, self.current_month)
        flags = database.get_month_flags(self.current_year, self.current_month)
        config = database.get_config()
        try:
            ae = int(self.ae_entry.get().strip())
        except ValueError:
            ae = 0

        summary = calc_monthly_summary(
            self.current_year, self.current_month,
            entries, flags, config, ae,
        )

        fmt = lambda v: f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

        self.lbl_horas_totais.configure(
            text=f"Horas Totais: {summary.total_hours}".replace(".", ",")
        )
        self.lbl_transportes.configure(text=f"Transportes: {summary.transport_days}")
        self.lbl_alimentacao.configure(text=f"Alimentação: {summary.meal_days}")
        self.lbl_salario.configure(text=f"Salário: {fmt(summary.salary)}")
        self.lbl_bonus_ae.configure(text=f"Bonus AE: {fmt(summary.bonus_ae)}")
        self.lbl_vt.configure(text=f"VT: {fmt(summary.vt_total)}")
        self.lbl_vr.configure(text=f"VR: {fmt(summary.vr_total)}")
        self.lbl_total.configure(text=f"TOTAL: {fmt(summary.total)}")

    # --- PDF Export ---

    def _export_pdf(self):
        from tkinter import filedialog
        from services.pdf_export import export_month_pdf

        filepath = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            filetypes=[("PDF", "*.pdf")],
            initialfile=f"relatorio_{self.current_year}_{self.current_month:02d}.pdf",
        )
        if not filepath:
            return

        entries = database.get_month_entries(self.current_year, self.current_month)
        flags = database.get_month_flags(self.current_year, self.current_month)
        config = database.get_config()
        ae = database.get_ae_fechadas(self.current_year, self.current_month)

        export_month_pdf(
            year=self.current_year,
            month=self.current_month,
            entries=entries,
            flags=flags,
            event_types=self.event_types,
            config=config,
            ae_fechadas=ae,
            filepath=filepath,
        )
