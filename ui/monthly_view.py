import calendar
from datetime import date

import customtkinter as ctk

import database
from models import DayEntry, DayFlags
from services.calculator import calc_monthly_summary

WEEKDAY_NAMES = ["seg", "ter", "qua", "qui", "sex", "sáb", "dom"]
WEEKDAY_NAMES_FULL = ["Segunda", "Terça", "Quarta", "Quinta", "Sexta", "Sábado", "Domingo"]
MONTH_NAMES = [
    "", "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
    "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro",
]
NUM_SLOTS = 8
MAX_DAYS = 31


class DayEditPopup(ctk.CTkToplevel):
    def __init__(self, parent, day_num, year, month, weekday, event_types, on_close):
        super().__init__(parent)

        self.day_num = day_num
        self.year = year
        self.month = month
        self.event_types = event_types
        self.event_names = [et.name for et in event_types]
        self.event_name_to_id = {et.name: et.id for et in event_types}
        self.event_name_to_color = {et.name: et.color for et in event_types}
        self.on_close_cb = on_close
        self.row_frames: list[ctk.CTkFrame] = []

        day_name = WEEKDAY_NAMES_FULL[weekday]
        month_name = MONTH_NAMES[month]
        self.title(f"{day_num} de {month_name} - {day_name}")
        self.geometry("420x360")
        self.resizable(False, True)
        self.transient(parent)
        self.grab_set()

        # Center on parent
        self.update_idletasks()
        px = parent.winfo_rootx() + parent.winfo_width() // 2 - 210
        py = parent.winfo_rooty() + parent.winfo_height() // 2 - 180
        self.geometry(f"+{px}+{py}")

        # Header
        ctk.CTkLabel(
            self, text=f"{day_num} de {month_name} ({day_name})",
            font=ctk.CTkFont(size=14, weight="bold"),
        ).pack(pady=(12, 6), padx=16, anchor="w")

        # Scrollable list of event rows
        self.entries_frame = ctk.CTkScrollableFrame(self, fg_color="transparent", height=200)
        self.entries_frame.pack(fill="both", expand=True, padx=10, pady=(0, 6))

        ctk.CTkButton(
            self, text="+ Adicionar Evento",
            command=self._add_empty_row,
            fg_color=("gray75", "gray25"), text_color=("black", "white"),
            hover_color=("gray65", "gray35"),
        ).pack(fill="x", padx=10, pady=(0, 4))

        ctk.CTkButton(self, text="Fechar", command=self._close).pack(
            fill="x", padx=10, pady=(0, 12)
        )

        self.protocol("WM_DELETE_WINDOW", self._close)
        self._load_entries()

    def _load_entries(self):
        for w in self.entries_frame.winfo_children():
            w.destroy()
        self.row_frames.clear()
        entries = database.get_day_entries(self.year, self.month, self.day_num)
        for entry in entries:
            event_name = ""
            for et in self.event_types:
                if et.id == entry.event_type_id:
                    event_name = et.name
                    break
            hours_str = str(entry.hours).replace(".", ",") if entry.hours else ""
            self._add_row(event_name, hours_str)
        self._update_button_states()

    def _add_empty_row(self):
        self._add_row("", "")
        self._update_button_states()

    def _add_row(self, event_name: str, hours_str: str):
        row = ctk.CTkFrame(self.entries_frame, fg_color="transparent")
        row.pack(fill="x", pady=3)
        self.row_frames.append(row)

        # Hours entry first
        entry = ctk.CTkEntry(row, width=65, height=30, placeholder_text="Horas")
        entry.pack(side="left", padx=(0, 4))
        if hours_str:
            entry.insert(0, hours_str)

        # Color indicator (updates on combo change)
        initial_color = self.event_name_to_color.get(event_name, ("gray60", "gray40"))
        color_lbl = ctk.CTkLabel(
            row, text="", width=14, height=24,
            fg_color=initial_color, corner_radius=4,
        )
        color_lbl.pack(side="left", padx=(0, 4))

        # Type combo
        combo = ctk.CTkComboBox(row, values=self.event_names, width=140, height=30)
        combo.set(event_name)
        combo.pack(side="left", padx=(0, 4))

        # Reorder buttons
        ctk.CTkButton(
            row, text="▲", width=26, height=30,
            fg_color="transparent", border_width=1,
            hover_color=("gray70", "gray30"),
            command=lambda r=row: self._move_row(r, -1),
        ).pack(side="left", padx=(0, 2))

        ctk.CTkButton(
            row, text="▼", width=26, height=30,
            fg_color="transparent", border_width=1,
            hover_color=("gray70", "gray30"),
            command=lambda r=row: self._move_row(r, +1),
        ).pack(side="left", padx=(0, 4))

        # Delete button
        ctk.CTkButton(
            row, text="✕", width=26, height=30,
            fg_color="transparent", border_width=1,
            hover_color=("gray70", "gray30"),
            command=lambda r=row: self._remove_row(r),
        ).pack(side="left")

        def on_combo_change(val, lbl=color_lbl):
            lbl.configure(fg_color=self.event_name_to_color.get(val, ("gray60", "gray40")))
            self._save_all()

        combo.configure(command=on_combo_change)
        entry.bind("<FocusOut>", lambda e: self._save_all())
        entry.bind("<Return>", lambda e: self._save_all())

    def _remove_row(self, row_frame: ctk.CTkFrame):
        if row_frame in self.row_frames:
            self.row_frames.remove(row_frame)
        row_frame.destroy()
        self._update_button_states()
        self._save_all()

    def _move_row(self, row_frame: ctk.CTkFrame, direction: int):
        if row_frame not in self.row_frames:
            return
        idx = self.row_frames.index(row_frame)
        new_idx = idx + direction
        if new_idx < 0 or new_idx >= len(self.row_frames):
            return
        self.row_frames[idx], self.row_frames[new_idx] = self.row_frames[new_idx], self.row_frames[idx]
        for frame in self.row_frames:
            frame.pack_forget()
        for frame in self.row_frames:
            frame.pack(fill="x", pady=3)
        self._update_button_states()
        self._save_all()

    def _update_button_states(self):
        last = len(self.row_frames) - 1
        for idx, row_frame in enumerate(self.row_frames):
            children = row_frame.winfo_children()
            if len(children) < 5:
                continue
            # layout: [entry, color_lbl, combo, btn_up, btn_down, btn_del]
            children[3].configure(state="disabled" if idx == 0 else "normal")
            children[4].configure(state="disabled" if idx == last else "normal")

    def _save_all(self):
        database.delete_day_entries_for_day(self.year, self.month, self.day_num)
        slot = 1
        for row_frame in self.row_frames:
            children = row_frame.winfo_children()
            # layout: [entry, color_lbl, combo, btn_up, btn_down, btn_del]
            if len(children) < 3:
                continue
            entry_w, _, combo = children[0], children[1], children[2]
            event_name = combo.get()
            event_type_id = self.event_name_to_id.get(event_name)
            raw = entry_w.get().strip().replace(",", ".")
            try:
                hours = float(raw) if raw else 0.0
            except ValueError:
                hours = 0.0

            if event_type_id or hours > 0:
                database.upsert_day_entry(DayEntry(
                    year=self.year, month=self.month, day=self.day_num,
                    slot=slot, event_type_id=event_type_id, hours=hours,
                ))
                slot += 1

    def _close(self):
        self._save_all()
        self.on_close_cb()
        self.destroy()


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

        # Row widget references
        self.chips_frames: list[ctk.CTkFrame] = []
        self.hours_labels: list[ctk.CTkLabel] = []
        self.day_labels: list[ctk.CTkLabel] = []
        self.week_labels: list[ctk.CTkLabel] = []
        self.vt_vars: list[ctk.IntVar] = []
        self.vr_vars: list[ctk.IntVar] = []
        self.row_widgets: list[list] = []

        self._active_popup: DayEditPopup | None = None

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

        ctk.CTkButton(nav, text="◀", width=40, command=self._prev_month).grid(
            row=0, column=0, padx=(0, 10)
        )

        self.month_label = ctk.CTkLabel(
            nav, text="", font=ctk.CTkFont(size=18, weight="bold"),
        )
        self.month_label.grid(row=0, column=1)

        ctk.CTkButton(nav, text="▶", width=40, command=self._next_month).grid(
            row=0, column=2, padx=(10, 10)
        )

        ctk.CTkButton(nav, text="Exportar PDF", width=120, command=self._export_pdf).grid(
            row=0, column=3
        )

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
        self._build_grid_once()

    def _build_grid_once(self):
        """Build MAX_DAYS rows once at startup — reused across all month changes."""
        for text, col, colspan in [
            ("Dia", 0, 1), ("Sem", 1, 1), ("Eventos", 2, 1),
            ("Horas", 3, 1), ("VT", 4, 1), ("VR", 5, 1),
        ]:
            ctk.CTkLabel(
                self.grid_frame, text=text,
                font=ctk.CTkFont(weight="bold"),
                width=50 if text in ("Dia", "Sem", "Horas", "VT", "VR") else 380,
            ).grid(row=0, column=col, columnspan=colspan, padx=2, pady=2)

        for day_idx in range(MAX_DAYS):
            row = day_idx + 1
            row_widget_list = []

            day_lbl = ctk.CTkLabel(self.grid_frame, text=str(day_idx + 1), width=50)
            day_lbl.grid(row=row, column=0, padx=2, pady=1)
            self.day_labels.append(day_lbl)
            row_widget_list.append(day_lbl)

            week_lbl = ctk.CTkLabel(self.grid_frame, text="", width=50)
            week_lbl.grid(row=row, column=1, padx=2, pady=1)
            self.week_labels.append(week_lbl)
            row_widget_list.append(week_lbl)

            chips_frame = ctk.CTkFrame(self.grid_frame, fg_color="transparent", width=380, height=32)
            chips_frame.grid(row=row, column=2, padx=4, pady=1, sticky="w")
            chips_frame.grid_propagate(False)

            add_btn = ctk.CTkButton(
                chips_frame, text="+", width=28, height=24,
                fg_color=("gray70", "gray30"), hover_color=("gray60", "gray40"),
                text_color=("black", "white"),
                command=lambda d=day_idx: self._open_day_popup(d),
            )
            add_btn.pack(side="left", padx=(0, 4))

            self.chips_frames.append(chips_frame)
            row_widget_list.append(chips_frame)

            hours_lbl = ctk.CTkLabel(self.grid_frame, text="0", width=50)
            hours_lbl.grid(row=row, column=3, padx=2, pady=1)
            self.hours_labels.append(hours_lbl)
            row_widget_list.append(hours_lbl)

            vt_var = ctk.IntVar(value=0)
            vt_cb = ctk.CTkCheckBox(
                self.grid_frame, text="", variable=vt_var, width=30,
                command=lambda d=day_idx: self._on_flag_change(d),
            )
            vt_cb.grid(row=row, column=4, padx=2, pady=1)
            self.vt_vars.append(vt_var)
            row_widget_list.append(vt_cb)

            vr_var = ctk.IntVar(value=0)
            vr_cb = ctk.CTkCheckBox(
                self.grid_frame, text="", variable=vr_var, width=30,
                command=lambda d=day_idx: self._on_flag_change(d),
            )
            vr_cb.grid(row=row, column=5, padx=2, pady=1)
            self.vr_vars.append(vr_var)
            row_widget_list.append(vr_cb)

            self.row_widgets.append(row_widget_list)

    def _show_rows(self, num_days: int):
        for day_idx in range(MAX_DAYS):
            for widget in self.row_widgets[day_idx]:
                if day_idx < num_days:
                    widget.grid()
                else:
                    widget.grid_remove()

    def _reset_rows(self, num_days: int):
        for day_idx in range(num_days):
            weekday = calendar.weekday(self.current_year, self.current_month, day_idx + 1)
            is_weekend = weekday >= 5
            row_bg = "gray20" if is_weekend else "transparent"

            self.day_labels[day_idx].configure(text=str(day_idx + 1), fg_color=row_bg)
            self.week_labels[day_idx].configure(text=WEEKDAY_NAMES[weekday], fg_color=row_bg)
            self.vt_vars[day_idx].set(0)
            self.vr_vars[day_idx].set(0)
            self.hours_labels[day_idx].configure(text="0")
            self._clear_chips(day_idx)

    def _clear_chips(self, day_idx: int):
        frame = self.chips_frames[day_idx]
        for widget in frame.winfo_children():
            # Keep the "+" button (first child), destroy chips
            if widget.cget("text") != "+":
                widget.destroy()

    def _render_day_chips(self, day_idx: int, day_entries: list[DayEntry]):
        self._clear_chips(day_idx)
        frame = self.chips_frames[day_idx]
        for entry in day_entries:
            if not entry.event_type_id:
                continue
            et = self.event_type_map.get(entry.event_type_id)
            if not et:
                continue
            hours_str = str(entry.hours).replace(".", ",").rstrip("0").rstrip(",")
            label = f"{et.name[:4]}. {hours_str}h" if len(et.name) > 5 else f"{et.name} {hours_str}h"
            chip = ctk.CTkButton(
                frame, text=label, width=80, height=24,
                fg_color=et.color, hover_color=et.color,
                text_color="white", font=ctk.CTkFont(size=11),
                command=lambda d=day_idx: self._open_day_popup(d),
            )
            chip.pack(side="left", padx=(0, 3))

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
        self._show_rows(num_days)
        self._reset_rows(num_days)

        entries = database.get_month_entries(self.current_year, self.current_month)
        flags = database.get_month_flags(self.current_year, self.current_month)
        ae = database.get_ae_fechadas(self.current_year, self.current_month)

        # Group entries by day and render chips
        from collections import defaultdict
        entries_by_day: dict[int, list[DayEntry]] = defaultdict(list)
        for entry in entries:
            entries_by_day[entry.day].append(entry)

        for day_idx in range(num_days):
            day_num = day_idx + 1
            day_entries = entries_by_day.get(day_num, [])
            self._render_day_chips(day_idx, day_entries)
            total = sum(e.hours for e in day_entries)
            self.hours_labels[day_idx].configure(
                text=str(total).replace(".", ",") if total else "0"
            )

        # Populate flags
        flags_map = {f.day: f for f in flags}
        for day_idx in range(num_days):
            day_num = day_idx + 1
            if day_num in flags_map:
                f = flags_map[day_num]
                self.vt_vars[day_idx].set(1 if f.vt else 0)
                self.vr_vars[day_idx].set(1 if f.vr else 0)

        self.ae_entry.delete(0, "end")
        self.ae_entry.insert(0, str(ae))

        self.refresh_summary()

    def on_show(self):
        self.event_types = database.get_event_types()
        self.event_type_map = {et.id: et for et in self.event_types}

    # --- Popup ---

    def _open_day_popup(self, day_idx: int):
        if self._active_popup and self._active_popup.winfo_exists():
            self._active_popup.focus()
            return

        weekday = calendar.weekday(self.current_year, self.current_month, day_idx + 1)
        popup = DayEditPopup(
            parent=self.winfo_toplevel(),
            day_num=day_idx + 1,
            year=self.current_year,
            month=self.current_month,
            weekday=weekday,
            event_types=self.event_types,
            on_close=lambda: self._on_day_popup_close(day_idx),
        )
        self._active_popup = popup

    def _on_day_popup_close(self, day_idx: int):
        self._active_popup = None
        day_entries = database.get_day_entries(self.current_year, self.current_month, day_idx + 1)
        self._render_day_chips(day_idx, day_entries)
        total = sum(e.hours for e in day_entries)
        self.hours_labels[day_idx].configure(
            text=str(total).replace(".", ",") if total else "0"
        )
        self.refresh_summary()

    # --- Flags ---

    def _on_flag_change(self, day_idx: int):
        flags = DayFlags(
            year=self.current_year,
            month=self.current_month,
            day=day_idx + 1,
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

    # --- Summary ---

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
