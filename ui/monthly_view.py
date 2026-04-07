import calendar
from datetime import date, timedelta

import customtkinter as ctk

import database
from models import DayEntry, DayFlags, MonthAdjustment
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
        self.wait_visibility()
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


class WeekCopyPopup(ctk.CTkToplevel):
    ACCENT_COLOR = "#3B8ED0"

    def __init__(
        self,
        parent,
        source_labels: list[str],
        target_labels: list[str],
        event_types,
        default_source: str,
        default_target: str,
        on_confirm,
    ):
        super().__init__(parent)

        self.on_confirm = on_confirm
        self.event_type_vars: dict[int, ctk.IntVar] = {}

        self.title("Copiar Semana")
        self.geometry("760x460")
        self.resizable(False, False)
        self.transient(parent)
        self.wait_visibility()
        self.grab_set()

        self.update_idletasks()
        px = parent.winfo_rootx() + parent.winfo_width() // 2 - 380
        py = parent.winfo_rooty() + parent.winfo_height() // 2 - 250
        self.geometry(f"+{px}+{py}")
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        ctk.CTkLabel(
            self,
            text="Selecione a semana de origem e a semana de destino",
            font=ctk.CTkFont(size=15, weight="bold"),
        ).grid(row=0, column=0, padx=20, pady=(18, 14), sticky="w")

        selector_frame = ctk.CTkFrame(self, fg_color="transparent")
        selector_frame.grid(row=1, column=0, padx=20, pady=(0, 12), sticky="ew")
        selector_frame.grid_columnconfigure(0, weight=1)
        selector_frame.grid_columnconfigure(1, weight=1)

        self._build_week_selector(
            selector_frame,
            column=0,
            title="Semana de origem",
            labels=source_labels,
            selected_value=default_source,
        )
        self._build_week_selector(
            selector_frame,
            column=1,
            title="Semana de destino",
            labels=target_labels,
            selected_value=default_target,
        )

        events_frame = ctk.CTkFrame(self, fg_color="transparent")
        events_frame.grid(row=2, column=0, padx=20, pady=(0, 10), sticky="nsew")
        ctk.CTkLabel(
            events_frame,
            text="Tipos de evento para copiar",
            font=ctk.CTkFont(weight="bold"),
        ).pack(anchor="w")

        toggle_frame = ctk.CTkFrame(events_frame, fg_color="transparent")
        toggle_frame.pack(fill="x", pady=(6, 6))
        ctk.CTkButton(
            toggle_frame, text="Marcar todos", width=110,
            command=self._select_all_event_types,
        ).pack(side="left", padx=(0, 6))
        ctk.CTkButton(
            toggle_frame, text="Limpar", width=90,
            command=self._clear_all_event_types,
        ).pack(side="left")

        self.events_list = ctk.CTkFrame(events_frame)
        self.events_list.pack(fill="x")
        self.events_list.grid_columnconfigure(0, weight=1)
        self.events_list.grid_columnconfigure(1, weight=1)
        for idx, event_type in enumerate(event_types):
            var = ctk.IntVar(value=1)
            self.event_type_vars[event_type.id] = var
            row = ctk.CTkFrame(self.events_list, fg_color="transparent")
            row.grid(
                row=idx // 2,
                column=idx % 2,
                padx=6,
                pady=4,
                sticky="w",
            )
            ctk.CTkLabel(
                row, text="", width=14, height=24,
                fg_color=event_type.color, corner_radius=4,
            ).pack(side="left", padx=(0, 8))
            ctk.CTkCheckBox(
                row,
                text=event_type.name,
                variable=var,
                onvalue=1,
                offvalue=0,
            ).pack(side="left", anchor="w")

        self.status_label = ctk.CTkLabel(self, text="")
        self.status_label.grid(row=3, column=0, padx=20, pady=(0, 10), sticky="ew")

        actions = ctk.CTkFrame(self, fg_color="transparent")
        actions.grid(row=4, column=0, padx=20, pady=(0, 18), sticky="ew")
        actions.grid_columnconfigure((0, 1), weight=1)

        ctk.CTkButton(
            actions,
            text="Cancelar",
            command=self._close,
            fg_color="transparent",
            hover_color=self.ACCENT_COLOR,
            border_width=1,
            border_color=self.ACCENT_COLOR,
            text_color=self.ACCENT_COLOR,
        ).grid(row=0, column=0, padx=(0, 6), sticky="ew")

        ctk.CTkButton(
            actions, text="Confirmar copia", command=self._submit,
        ).grid(row=0, column=1, padx=(6, 0), sticky="ew")

        self.protocol("WM_DELETE_WINDOW", self._close)

    def _submit(self):
        source_label = self.source_select.get()
        target_label = self.target_select.get()
        if source_label == target_label:
            self.status_label.configure(
                text="Selecione semanas diferentes.", text_color="red",
            )
            return

        selected_event_type_ids = [
            event_type_id
            for event_type_id, var in self.event_type_vars.items()
            if var.get()
        ]
        if not selected_event_type_ids:
            self.status_label.configure(
                text="Selecione ao menos um tipo de evento.", text_color="red",
            )
            return

        self.on_confirm(source_label, target_label, selected_event_type_ids)
        self.destroy()

    def _close(self):
        self.destroy()

    def _select_all_event_types(self):
        for var in self.event_type_vars.values():
            var.set(1)

    def _clear_all_event_types(self):
        for var in self.event_type_vars.values():
            var.set(0)

    def _build_week_selector(self, parent, column: int, title: str, labels: list[str], selected_value: str):
        container = ctk.CTkFrame(parent)
        container.grid(row=0, column=column, padx=(0, 8) if column == 0 else (8, 0), sticky="nsew")

        ctk.CTkLabel(
            container, text=title, font=ctk.CTkFont(weight="bold"),
        ).pack(anchor="w", padx=14, pady=(12, 6))

        hint = "Escolha uma semana visivel para copiar." if column == 0 else "Escolha em qual semana os dados serao colados."
        ctk.CTkLabel(
            container, text=hint, text_color=("gray40", "gray65"),
        ).pack(anchor="w", padx=14, pady=(0, 8))

        select = ctk.CTkComboBox(
            container,
            values=labels,
            state="readonly",
            width=320,
        )
        select.pack(fill="x", padx=14, pady=(0, 14))
        select.set(selected_value)

        if column == 0:
            self.source_select = select
        else:
            self.target_select = select


class MonthExtrasPopup(ctk.CTkToplevel):
    def __init__(self, parent, current_ae: int, current_adjustments: list[MonthAdjustment], on_save):
        super().__init__(parent)

        self.on_save = on_save
        self.row_frames: list[ctk.CTkFrame] = []

        self.title("Extras do Mês")
        self.geometry("520x420")
        self.resizable(False, False)
        self.transient(parent)
        self.wait_visibility()
        self.grab_set()

        self.update_idletasks()
        px = parent.winfo_rootx() + parent.winfo_width() // 2 - 260
        py = parent.winfo_rooty() + parent.winfo_height() // 2 - 210
        self.geometry(f"+{px}+{py}")

        ctk.CTkLabel(
            self, text="Extras do mês",
            font=ctk.CTkFont(size=16, weight="bold"),
        ).pack(padx=16, pady=(16, 10), anchor="w")

        ae_frame = ctk.CTkFrame(self, fg_color="transparent")
        ae_frame.pack(fill="x", padx=16, pady=(0, 10))
        ctk.CTkLabel(ae_frame, text="AE Fechadas").pack(side="left")
        self.ae_entry = ctk.CTkEntry(ae_frame, width=80)
        self.ae_entry.pack(side="left", padx=(8, 0))
        self.ae_entry.insert(0, str(current_ae))

        ctk.CTkLabel(
            self, text="Observações e valores",
            font=ctk.CTkFont(weight="bold"),
        ).pack(padx=16, pady=(0, 6), anchor="w")

        self.rows_container = ctk.CTkScrollableFrame(self, height=220)
        self.rows_container.pack(fill="both", expand=True, padx=16, pady=(0, 8))

        for adjustment in current_adjustments:
            self._add_row(adjustment.description, adjustment.value)
        if not current_adjustments:
            self._add_row("", None)

        ctk.CTkButton(
            self, text="+ Adicionar observação",
            command=lambda: self._add_row("", None),
        ).pack(fill="x", padx=16, pady=(0, 8))

        self.status_label = ctk.CTkLabel(self, text="")
        self.status_label.pack(fill="x", padx=16, pady=(0, 8))

        actions = ctk.CTkFrame(self, fg_color="transparent")
        actions.pack(fill="x", padx=16, pady=(0, 16))
        actions.grid_columnconfigure((0, 1), weight=1)

        ctk.CTkButton(actions, text="Cancelar", command=self._close).grid(
            row=0, column=0, padx=(0, 6), sticky="ew"
        )
        ctk.CTkButton(actions, text="Salvar", command=self._submit).grid(
            row=0, column=1, padx=(6, 0), sticky="ew"
        )

        self.protocol("WM_DELETE_WINDOW", self._close)

    def _add_row(self, description: str, value: float | None):
        row = ctk.CTkFrame(self.rows_container, fg_color="transparent")
        row.pack(fill="x", pady=4)
        self.row_frames.append(row)

        desc_entry = ctk.CTkEntry(row, width=290, placeholder_text="Observação")
        desc_entry.pack(side="left", padx=(0, 6))
        if description:
            desc_entry.insert(0, description)

        value_entry = ctk.CTkEntry(row, width=100, placeholder_text="Valor")
        value_entry.pack(side="left", padx=(0, 6))
        if value is not None:
            value_entry.insert(0, f"{value:.2f}".replace(".", ","))

        ctk.CTkButton(
            row, text="✕", width=30,
            command=lambda r=row: self._remove_row(r),
        ).pack(side="left")

    def _remove_row(self, row_frame: ctk.CTkFrame):
        if row_frame in self.row_frames:
            self.row_frames.remove(row_frame)
        row_frame.destroy()
        if not self.row_frames:
            self._add_row("", None)

    def _submit(self):
        try:
            ae_text = self.ae_entry.get().strip()
            ae_fechadas = int(ae_text) if ae_text else 0
            adjustments: list[MonthAdjustment] = []
            for row_frame in self.row_frames:
                desc_entry, value_entry, _ = row_frame.winfo_children()
                description = desc_entry.get().strip()
                value_text = value_entry.get().strip().replace(",", ".")

                if not description and not value_text:
                    continue
                if not description or not value_text:
                    raise ValueError

                adjustments.append(MonthAdjustment(
                    description=description,
                    value=float(value_text),
                ))

            self.on_save(ae_fechadas, adjustments)
            self.destroy()
        except ValueError:
            self.status_label.configure(
                text="Preencha AE com inteiro e cada extra com descrição e valor válidos.",
                text_color="red",
            )

    def _close(self):
        self.destroy()


class MonthlyView(ctk.CTkFrame):
    WEEK_NUMBER_COL_WIDTH = 34
    FLAG_ACCENT_COLOR = "#3B8ED0"
    FLAG_HOVER_COLOR = "#2F6EA7"
    FLAG_BG_LIGHT = "#EBEBEB"
    FLAG_BG_DARK = "#2B2B2B"

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
        self.week_number_labels: list[ctk.CTkLabel] = []
        self.day_labels: list[ctk.CTkLabel] = []
        self.week_labels: list[ctk.CTkLabel] = []
        self.vt_vars: list[ctk.IntVar] = []
        self.vr_vars: list[ctk.IntVar] = []
        self.vt_checkboxes: list[ctk.CTkCheckBox] = []
        self.vr_checkboxes: list[ctk.CTkCheckBox] = []
        self.row_widgets: list[list] = []
        self.week_group_start_by_day: dict[int, int] = {}

        self._active_popup: DayEditPopup | None = None
        self._week_copy_popup: WeekCopyPopup | None = None
        self._month_extras_popup: MonthExtrasPopup | None = None

        self._build_nav_bar()
        self._build_grid_area()
        self._build_legend()
        self._build_summary()

        # Toast overlay (uses place() to float without affecting layout)
        self.toast_label = ctk.CTkLabel(
            self, text="", fg_color="#2d7d46", text_color="white",
            corner_radius=8, height=32, font=ctk.CTkFont(size=12),
        )

        self._load_month()

    def _weekend_row_color(self):
        return ("gray86", "gray20")

    def _subtle_text_color(self):
        return ("gray35", "gray65")

    def _divider_color(self):
        return ("gray75", "gray35")

    def _today_row_color(self):
        return ("#3B8ED0", "#2F6EA7")

    def _default_row_text_color(self):
        return ("gray15", "gray90")

    def _get_week_start(self, current_date: date) -> date:
        return current_date - timedelta(days=(current_date.weekday() + 1) % 7)

    def _get_week_number(self, current_date: date) -> int:
        return int(self._get_week_start(current_date).strftime("%U"))

    def _blend_color(self, fg_hex: str, bg_hex: str, alpha: float) -> str:
        fg_hex = fg_hex.lstrip("#")
        bg_hex = bg_hex.lstrip("#")
        fg_rgb = tuple(int(fg_hex[i:i + 2], 16) for i in (0, 2, 4))
        bg_rgb = tuple(int(bg_hex[i:i + 2], 16) for i in (0, 2, 4))
        blended = tuple(
            round((alpha * fg) + ((1 - alpha) * bg))
            for fg, bg in zip(fg_rgb, bg_rgb)
        )
        return "#{:02X}{:02X}{:02X}".format(*blended)

    def _checkbox_enabled_colors(self) -> dict[str, tuple[str, str] | str]:
        return {
            "fg_color": (self.FLAG_ACCENT_COLOR, self.FLAG_ACCENT_COLOR),
            "hover_color": (self.FLAG_HOVER_COLOR, self.FLAG_HOVER_COLOR),
            "border_color": (self.FLAG_ACCENT_COLOR, self.FLAG_ACCENT_COLOR),
            "checkmark_color": "white",
        }

    def _checkbox_disabled_colors(self) -> dict[str, tuple[str, str] | str]:
        disabled_fill = (
            self._blend_color(self.FLAG_ACCENT_COLOR, self.FLAG_BG_LIGHT, 0.12),
            self._blend_color(self.FLAG_ACCENT_COLOR, self.FLAG_BG_DARK, 0.12),
        )
        disabled_border = (
            self._blend_color(self.FLAG_ACCENT_COLOR, self.FLAG_BG_LIGHT, 0.35),
            self._blend_color(self.FLAG_ACCENT_COLOR, self.FLAG_BG_DARK, 0.35),
        )
        disabled_hover = (
            self._blend_color(self.FLAG_HOVER_COLOR, self.FLAG_BG_LIGHT, 0.2),
            self._blend_color(self.FLAG_HOVER_COLOR, self.FLAG_BG_DARK, 0.2),
        )
        return {
            "fg_color": disabled_fill,
            "hover_color": disabled_hover,
            "border_color": disabled_border,
            "checkmark_color": disabled_border,
        }

    def _apply_flag_checkbox_style(self, checkbox: ctk.CTkCheckBox, disabled: bool):
        colors = self._checkbox_disabled_colors() if disabled else self._checkbox_enabled_colors()
        checkbox.configure(**colors)

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

        self.copy_menu = ctk.CTkOptionMenu(
            nav, values=["Copiar Mês Anterior", "Copiar Semana"],
            command=self._on_copy, width=180,
            fg_color=("gray75", "gray25"),
            button_color=("gray65", "gray35"),
            button_hover_color=("gray55", "gray45"),
            text_color=("black", "white"),
        )
        self.copy_menu.set("Copiar...")
        self.copy_menu.grid(row=0, column=3, padx=(0, 10))

        ctk.CTkButton(nav, text="Exportar PDF", width=120, command=self._export_pdf).grid(
            row=0, column=4
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
            ("", 0, 1), ("Dia", 1, 1), ("Sem", 2, 1), ("Eventos", 3, 1),
            ("Horas", 4, 1), ("VT", 5, 1), ("VR", 6, 1),
        ]:
            ctk.CTkLabel(
                self.grid_frame, text=text,
                font=ctk.CTkFont(weight="bold"),
                width=self.WEEK_NUMBER_COL_WIDTH if col == 0 else 50 if text in ("Dia", "Sem", "Horas", "VT", "VR") else 380,
            ).grid(row=0, column=col, columnspan=colspan, padx=2, pady=2)

        for day_idx in range(MAX_DAYS):
            row = day_idx + 1
            row_widget_list = []

            week_number_lbl = ctk.CTkLabel(self.grid_frame, text="", width=self.WEEK_NUMBER_COL_WIDTH)
            week_number_lbl.grid(row=row, column=0, padx=2, pady=1)
            self.week_number_labels.append(week_number_lbl)
            row_widget_list.append(week_number_lbl)

            day_lbl = ctk.CTkLabel(self.grid_frame, text=str(day_idx + 1), width=50)
            day_lbl.grid(row=row, column=1, padx=2, pady=1)
            self.day_labels.append(day_lbl)
            row_widget_list.append(day_lbl)

            week_lbl = ctk.CTkLabel(self.grid_frame, text="", width=50)
            week_lbl.grid(row=row, column=2, padx=2, pady=1)
            self.week_labels.append(week_lbl)
            row_widget_list.append(week_lbl)

            chips_frame = ctk.CTkFrame(self.grid_frame, fg_color="transparent", width=380, height=32)
            chips_frame.grid(row=row, column=3, padx=4, pady=1, sticky="w")
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
            hours_lbl.grid(row=row, column=4, padx=2, pady=1)
            self.hours_labels.append(hours_lbl)
            row_widget_list.append(hours_lbl)

            vt_var = ctk.IntVar(value=0)
            vt_cb = ctk.CTkCheckBox(
                self.grid_frame, text="", variable=vt_var, width=30,
                command=lambda d=day_idx: self._on_flag_change(d),
            )
            vt_cb.grid(row=row, column=5, padx=2, pady=1)
            self.vt_vars.append(vt_var)
            self.vt_checkboxes.append(vt_cb)
            row_widget_list.append(vt_cb)

            vr_var = ctk.IntVar(value=0)
            vr_cb = ctk.CTkCheckBox(
                self.grid_frame, text="", variable=vr_var, width=30,
                command=lambda d=day_idx: self._on_flag_change(d),
            )
            vr_cb.grid(row=row, column=6, padx=2, pady=1)
            self.vr_vars.append(vr_var)
            self.vr_checkboxes.append(vr_cb)
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
        self.week_group_start_by_day = {}
        today = date.today()
        for day_idx in range(num_days):
            current_date = date(self.current_year, self.current_month, day_idx + 1)
            weekday = current_date.weekday()
            is_weekend = weekday >= 5
            is_today = current_date == today
            row_bg = self._today_row_color() if is_today else self._weekend_row_color() if is_weekend else "transparent"
            row_text_color = "white" if is_today else self._default_row_text_color()

            week_number = self._get_week_number(current_date)
            self.week_number_labels[day_idx].configure(text=str(week_number), fg_color=row_bg, text_color=row_text_color)
            self.day_labels[day_idx].configure(text=str(day_idx + 1), fg_color=row_bg, text_color=row_text_color)
            self.week_labels[day_idx].configure(text=WEEKDAY_NAMES[weekday], fg_color=row_bg, text_color=row_text_color)
            self.vt_vars[day_idx].set(0)
            self.vr_vars[day_idx].set(0)
            self.hours_labels[day_idx].configure(text="0")
            self._clear_chips(day_idx)

        self._layout_week_number_labels(num_days)

    def _layout_week_number_labels(self, num_days: int):
        for day_idx, label in enumerate(self.week_number_labels):
            if day_idx >= num_days:
                label.grid_remove()
                continue

            current_date = date(self.current_year, self.current_month, day_idx + 1)
            week_key = self._get_week_start(current_date)
            if day_idx > 0:
                previous_date = date(self.current_year, self.current_month, day_idx)
                previous_week_key = self._get_week_start(previous_date)
                if week_key == previous_week_key:
                    label.grid_remove()
                    continue

            span = 1
            next_idx = day_idx + 1
            while next_idx < num_days:
                next_date = date(self.current_year, self.current_month, next_idx + 1)
                if self._get_week_start(next_date) != week_key:
                    break
                span += 1
                next_idx += 1

            for offset in range(span):
                self.week_group_start_by_day[day_idx + offset] = day_idx

            label.grid(
                row=day_idx + 1,
                column=0,
                rowspan=span,
                padx=2,
                pady=1,
                sticky="ns",
            )

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

    def _update_day_flag_state(self, day_idx: int, total_hours: float, persist: bool = False):
        has_hours = total_hours > 0
        state = "normal" if has_hours else "disabled"
        self._apply_flag_checkbox_style(self.vt_checkboxes[day_idx], disabled=not has_hours)
        self._apply_flag_checkbox_style(self.vr_checkboxes[day_idx], disabled=not has_hours)
        self.vt_checkboxes[day_idx].configure(state=state)
        self.vr_checkboxes[day_idx].configure(state=state)

        if has_hours:
            return

        self.vt_vars[day_idx].set(0)
        self.vr_vars[day_idx].set(0)
        if persist:
            database.upsert_day_flags(DayFlags(
                year=self.current_year,
                month=self.current_month,
                day=day_idx + 1,
                vt=False,
                vr=False,
            ))

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

        self.lbl_ae_fechadas = ctk.CTkLabel(left, text="AE Fechadas: 0")
        self.lbl_ae_fechadas.pack(anchor="w")

        self.lbl_ajustes = ctk.CTkLabel(left, text="Ajustes: R$ 0,00")
        self.lbl_ajustes.pack(anchor="w")

        self.lbl_transportes = ctk.CTkLabel(left, text="Transportes: 0")
        self.lbl_transportes.pack(anchor="w")

        self.lbl_alimentacao = ctk.CTkLabel(left, text="Alimentação: 0")
        self.lbl_alimentacao.pack(anchor="w")

        ctk.CTkButton(
            left, text="Extras do mês", command=self._open_month_extras_popup,
        ).pack(anchor="w", pady=(8, 0))

        right = ctk.CTkFrame(self.summary_frame, fg_color="transparent")
        right.pack(side="right", padx=20, pady=10)

        self.lbl_salario = ctk.CTkLabel(right, text="Salário: R$ 0,00")
        self.lbl_salario.pack(anchor="e")

        self.lbl_bonus_ae = ctk.CTkLabel(right, text="Bonus AE: R$ 0,00")
        self.lbl_bonus_ae.pack(anchor="e")

        self.lbl_valor_ajustes = ctk.CTkLabel(right, text="Ajustes: R$ 0,00")
        self.lbl_valor_ajustes.pack(anchor="e")

        self.lbl_vt = ctk.CTkLabel(right, text="VT: R$ 0,00")
        self.lbl_vt.pack(anchor="e")

        self.lbl_vr = ctk.CTkLabel(right, text="VR: R$ 0,00")
        self.lbl_vr.pack(anchor="e")

        self.summary_divider = ctk.CTkFrame(right, height=1, fg_color=self._divider_color())
        self.summary_divider.pack(fill="x", pady=6)

        self.lbl_media = ctk.CTkLabel(
            right, text="Média/dia: 0h",
            text_color=self._subtle_text_color(),
        )
        self.lbl_media.pack(anchor="e")

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

        # Group entries by day and render chips
        from collections import defaultdict
        entries_by_day: dict[int, list[DayEntry]] = defaultdict(list)
        totals_by_day: dict[int, float] = {}
        for entry in entries:
            entries_by_day[entry.day].append(entry)

        for day_idx in range(num_days):
            day_num = day_idx + 1
            day_entries = entries_by_day.get(day_num, [])
            self._render_day_chips(day_idx, day_entries)
            total = sum(e.hours for e in day_entries)
            totals_by_day[day_num] = total
            self.hours_labels[day_idx].configure(
                text=str(total).replace(".", ",") if total else "0"
            )
            self._update_day_flag_state(day_idx, total)

        # Populate flags
        flags_map = {f.day: f for f in flags}
        for day_idx in range(num_days):
            day_num = day_idx + 1
            total = totals_by_day.get(day_num, 0.0)
            if total <= 0:
                if day_num in flags_map and (flags_map[day_num].vt or flags_map[day_num].vr):
                    self._update_day_flag_state(day_idx, total, persist=True)
                continue
            if day_num in flags_map:
                f = flags_map[day_num]
                self.vt_vars[day_idx].set(1 if f.vt else 0)
                self.vr_vars[day_idx].set(1 if f.vr else 0)

        self.refresh_summary()

    def on_show(self):
        self.event_types = database.get_event_types()
        self.event_type_map = {et.id: et for et in self.event_types}
        self.refresh_theme()

    def refresh_theme(self):
        self.summary_divider.configure(fg_color=self._divider_color())
        self.lbl_media.configure(text_color=self._subtle_text_color())
        self._load_month()

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
        self._flash_row(day_idx)
        day_entries = database.get_day_entries(self.current_year, self.current_month, day_idx + 1)
        self._render_day_chips(day_idx, day_entries)
        total = sum(e.hours for e in day_entries)
        self.hours_labels[day_idx].configure(
            text=str(total).replace(".", ",") if total else "0"
        )
        self._update_day_flag_state(day_idx, total, persist=True)
        self.refresh_summary()

    # --- Flags ---

    def _on_flag_change(self, day_idx: int):
        self._flash_row(day_idx)
        flags = DayFlags(
            year=self.current_year,
            month=self.current_month,
            day=day_idx + 1,
            vt=bool(self.vt_vars[day_idx].get()),
            vr=bool(self.vr_vars[day_idx].get()),
        )
        database.upsert_day_flags(flags)
        self.refresh_summary()

    def _open_month_extras_popup(self):
        if self._month_extras_popup and self._month_extras_popup.winfo_exists():
            self._month_extras_popup.focus()
            return

        self._month_extras_popup = MonthExtrasPopup(
            parent=self.winfo_toplevel(),
            current_ae=database.get_ae_fechadas(self.current_year, self.current_month),
            current_adjustments=database.get_month_adjustments(self.current_year, self.current_month),
            on_save=self._save_month_extras,
        )

    def _save_month_extras(self, ae_fechadas: int, adjustments: list[MonthAdjustment]):
        database.set_ae_fechadas(self.current_year, self.current_month, ae_fechadas)
        database.replace_month_adjustments(self.current_year, self.current_month, adjustments)
        self.refresh_summary()

    # --- Summary ---

    def refresh_summary(self):
        entries = database.get_month_entries(self.current_year, self.current_month)
        flags = database.get_month_flags(self.current_year, self.current_month)
        config = database.get_config()
        ae = database.get_ae_fechadas(self.current_year, self.current_month)
        adjustments = database.get_month_adjustments(self.current_year, self.current_month)
        adjustments_total = sum(adjustment.value for adjustment in adjustments)

        summary = calc_monthly_summary(
            self.current_year, self.current_month,
            entries, flags, config, ae, adjustments_total,
        )

        fmt = lambda v: f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

        self.lbl_horas_totais.configure(
            text=f"Horas Totais: {summary.total_hours}".replace(".", ",")
        )
        self.lbl_ae_fechadas.configure(text=f"AE Fechadas: {summary.ae_fechadas}")
        self.lbl_ajustes.configure(text=f"Ajustes: {fmt(summary.adjustments_total)}")
        self.lbl_transportes.configure(text=f"Transportes: {summary.transport_days}")
        self.lbl_alimentacao.configure(text=f"Alimentação: {summary.meal_days}")
        self.lbl_salario.configure(text=f"Salário: {fmt(summary.salary)}")
        self.lbl_bonus_ae.configure(text=f"Bonus AE: {fmt(summary.bonus_ae)}")
        self.lbl_valor_ajustes.configure(text=f"Ajustes: {fmt(summary.adjustments_total)}")
        self.lbl_vt.configure(text=f"VT: {fmt(summary.vt_total)}")
        self.lbl_vr.configure(text=f"VR: {fmt(summary.vr_total)}")

        days_with_entries = len(set(e.day for e in entries if e.hours > 0))

        if days_with_entries > 0:
            media_diaria = summary.total_hours / days_with_entries
        else:
            media_diaria = 0.0

        self.lbl_media.configure(
            text=f"Média/dia: {media_diaria:.1f}h".replace(".", ",")
        )

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
        adjustments = database.get_month_adjustments(self.current_year, self.current_month)

        export_month_pdf(
            year=self.current_year,
            month=self.current_month,
            entries=entries,
            flags=flags,
            event_types=self.event_types,
            config=config,
            ae_fechadas=ae,
            adjustments=adjustments,
            filepath=filepath,
        )
        self._show_toast("PDF exportado!")

    # --- Visual Feedback ---

    def _flash_row(self, day_idx: int):
        highlight = "#2d5a1e"
        week_label_idx = self.week_group_start_by_day.get(day_idx, day_idx)
        self.week_number_labels[week_label_idx].configure(fg_color=highlight)
        self.day_labels[day_idx].configure(fg_color=highlight)
        self.week_labels[day_idx].configure(fg_color=highlight)

        current_date = date(self.current_year, self.current_month, day_idx + 1)
        weekday = current_date.weekday()
        original = (
            self._today_row_color()
            if current_date == date.today()
            else self._weekend_row_color() if weekday >= 5 else "transparent"
        )

        def restore():
            try:
                self.week_number_labels[week_label_idx].configure(fg_color=original)
                self.day_labels[day_idx].configure(fg_color=original)
                self.week_labels[day_idx].configure(fg_color=original)
            except Exception:
                pass

        self.after(800, restore)

    def _show_toast(self, msg: str):
        self.toast_label.configure(text=f"  {msg}  ")
        self.toast_label.place(relx=0.5, y=50, anchor="center")
        self.after(1800, self.toast_label.place_forget)

    # --- Copy Patterns ---

    def _on_copy(self, choice: str):
        self.copy_menu.set("Copiar...")
        if choice == "Copiar Mês Anterior":
            self._copy_previous_month()
        elif choice == "Copiar Semana":
            self._open_copy_week_popup()

    def _copy_previous_month(self):
        if self.current_month == 1:
            prev_year, prev_month = self.current_year - 1, 12
        else:
            prev_year, prev_month = self.current_year, self.current_month - 1

        prev_entries = database.get_month_entries(prev_year, prev_month)
        prev_flags = database.get_month_flags(prev_year, prev_month)

        if not prev_entries and not prev_flags:
            self._show_toast("Mês anterior sem dados")
            return

        curr_entries = database.get_month_entries(self.current_year, self.current_month)
        curr_days_with_data = set(e.day for e in curr_entries)

        num_days = calendar.monthrange(self.current_year, self.current_month)[1]
        copied = 0

        for entry in prev_entries:
            if entry.day > num_days or entry.day in curr_days_with_data:
                continue
            database.upsert_day_entry(DayEntry(
                year=self.current_year, month=self.current_month,
                day=entry.day, slot=entry.slot,
                event_type_id=entry.event_type_id, hours=entry.hours,
            ))
            copied += 1

        prev_flags_map = {f.day: f for f in prev_flags}
        for day, flag in prev_flags_map.items():
            if day > num_days or day in curr_days_with_data:
                continue
            database.upsert_day_flags(DayFlags(
                year=self.current_year, month=self.current_month,
                day=day, vt=flag.vt, vr=flag.vr,
            ))

        self._load_month()
        if copied > 0:
            self._show_toast("Mês anterior copiado!")
        else:
            self._show_toast("Dias já preenchidos")

    def _open_copy_week_popup(self):
        if self._week_copy_popup and self._week_copy_popup.winfo_exists():
            self._week_copy_popup.focus()
            return

        source_weeks = self._get_source_week_starts()
        target_weeks = self._get_target_week_starts()
        if not source_weeks or not target_weeks:
            self._show_toast("Nenhuma semana disponível")
            return

        source_map = {self._format_week_label(week): week for week in source_weeks}
        target_map = {self._format_week_label(week): week for week in target_weeks}
        self._source_week_map = source_map
        self._target_week_map = target_map

        default_target = self._infer_default_target_week()
        default_source = default_target - timedelta(days=7)

        default_target_label = self._closest_week_label(default_target, list(target_map.keys()), target_map)
        default_source_label = self._closest_week_label(default_source, list(source_map.keys()), source_map)

        self._week_copy_popup = WeekCopyPopup(
            parent=self.winfo_toplevel(),
            source_labels=list(source_map.keys()),
            target_labels=list(target_map.keys()),
            event_types=self.event_types,
            default_source=default_source_label,
            default_target=default_target_label,
            on_confirm=self._copy_selected_week,
        )

    def _infer_default_target_week(self) -> date:
        today = date.today()
        if (self.current_year, self.current_month) == (today.year, today.month):
            ref = today
        else:
            last_day = calendar.monthrange(self.current_year, self.current_month)[1]
            ref = date(self.current_year, self.current_month, last_day)
        return self._get_week_start(ref)

    def _get_source_week_starts(self) -> list[date]:
        prev_year, prev_month = self._shift_month(self.current_year, self.current_month, -1)
        next_year, next_month = self._shift_month(self.current_year, self.current_month, 1)

        weeks = (
            self._get_month_week_starts(prev_year, prev_month)
            + self._get_month_week_starts(self.current_year, self.current_month)
            + self._get_month_week_starts(next_year, next_month)
        )
        seen = set()
        unique_weeks = []
        for week in weeks:
            if week not in seen:
                seen.add(week)
                unique_weeks.append(week)
        return unique_weeks

    def _get_target_week_starts(self) -> list[date]:
        return self._get_month_week_starts(self.current_year, self.current_month)

    def _get_month_week_starts(self, year: int, month: int) -> list[date]:
        first_day = date(year, month, 1)
        last_day = date(year, month, calendar.monthrange(year, month)[1])
        week_start = self._get_week_start(first_day)
        week_starts = []
        while week_start <= last_day:
            week_starts.append(week_start)
            week_start += timedelta(days=7)
        return week_starts

    def _shift_month(self, year: int, month: int, delta: int) -> tuple[int, int]:
        shifted = month + delta
        while shifted < 1:
            shifted += 12
            year -= 1
        while shifted > 12:
            shifted -= 12
            year += 1
        return year, shifted

    def _format_week_label(self, week_start: date) -> str:
        week_number = self._get_week_number(week_start)
        week_end = week_start + timedelta(days=6)
        if week_start.year == week_end.year:
            return (
                f"Semana {week_number}: de {week_start.strftime('%d/%m')} "
                f"a {week_end.strftime('%d/%m')} de {week_end.year}"
            )
        return (
            f"Semana {week_number}: de {week_start.strftime('%d/%m/%Y')} "
            f"a {week_end.strftime('%d/%m/%Y')}"
        )

    def _closest_week_label(
        self,
        target_week: date,
        labels: list[str],
        week_map: dict[str, date],
    ) -> str:
        return min(labels, key=lambda label: abs((week_map[label] - target_week).days))

    def _copy_selected_week(
        self,
        source_label: str,
        target_label: str,
        selected_event_type_ids: list[int],
    ):
        source_start = self._source_week_map[source_label]
        target_start = self._target_week_map[target_label]
        selected_event_type_ids_set = set(selected_event_type_ids)

        copied_days = 0
        skipped_days = 0
        source_days_without_data = 0

        for offset in range(7):
            source = source_start + timedelta(days=offset)
            target = target_start + timedelta(days=offset)

            if target.year != self.current_year or target.month != self.current_month:
                continue

            source_entries = [
                entry
                for entry in database.get_day_entries(source.year, source.month, source.day)
                if entry.event_type_id in selected_event_type_ids_set
            ]
            source_flag = database.get_day_flags(source.year, source.month, source.day)
            if not source_entries:
                source_days_without_data += 1
                continue

            target_entries = database.get_day_entries(target.year, target.month, target.day)
            target_flag = database.get_day_flags(target.year, target.month, target.day)
            has_target_flag = bool(target_flag and (target_flag.vt or target_flag.vr))
            if target_entries or has_target_flag:
                skipped_days += 1
                continue

            for entry in source_entries:
                database.upsert_day_entry(DayEntry(
                    year=target.year, month=target.month,
                    day=target.day, slot=entry.slot,
                    event_type_id=entry.event_type_id, hours=entry.hours,
                ))

            if source_flag and (source_flag.vt or source_flag.vr):
                database.upsert_day_flags(DayFlags(
                    year=target.year, month=target.month,
                    day=target.day, vt=source_flag.vt, vr=source_flag.vr,
                ))

            copied_days += 1

        self._load_month()
        if copied_days > 0 and skipped_days == 0:
            self._show_toast("Semana copiada!")
        elif copied_days > 0:
            self._show_toast(f"Semana copiada ({skipped_days} dia(s) ignorado(s))")
        elif skipped_days > 0:
            self._show_toast("Destino já possui dados")
        elif source_days_without_data > 0:
            self._show_toast("Semana de origem sem dados")
        else:
            self._show_toast("Nada para copiar")
