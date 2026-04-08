import customtkinter as ctk

import database
from models import Config
from ui.default_week_popup import DefaultWeekDayPopup

# Display order starts on Sunday; maps display_idx → Python weekday (Mon=0…Sun=6)
WEEKDAY_DISPLAY  = ["Dom", "Seg", "Ter", "Qua", "Qui", "Sex", "Sáb"]
DISPLAY_TO_PY    = [6, 0, 1, 2, 3, 4, 5]


class ConfigView(ctk.CTkFrame):
    def __init__(self, parent, on_save_callback=None):
        super().__init__(parent, fg_color="transparent")
        self.on_save_callback = on_save_callback
        self._active_popup: DefaultWeekDayPopup | None = None

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(
            self, text="Configuração",
            font=ctk.CTkFont(size=20, weight="bold"),
        ).grid(row=0, column=0, pady=(20, 16))

        scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        scroll.grid(row=1, column=0, sticky="nsew")
        scroll.grid_columnconfigure(0, weight=1)

        main = ctk.CTkFrame(scroll, fg_color="transparent")
        main.grid(row=0, column=0, sticky="ew", padx=60, pady=(0, 30))
        main.grid_columnconfigure(0, weight=1)

        self._build_top_card(main)
        self._build_week_card(main)
        self._build_summary_card(main)

        self._load()
        self._load_week()

    # ── Top card ─────────────────────────────────────────────────────────────

    def _build_top_card(self, parent):
        card = ctk.CTkFrame(parent)
        card.grid(row=0, column=0, sticky="ew")
        card.grid_columnconfigure(1, weight=1)
        card.grid_columnconfigure(3, weight=1)

        PAD_X = 28
        PAD_Y = 10

        # Nome — full width spanning all columns
        ctk.CTkLabel(card, text="Nome", anchor="w", width=110).grid(
            row=0, column=0, padx=(PAD_X, 8), pady=(24, PAD_Y), sticky="w",
        )
        self.nome_entry = ctk.CTkEntry(card)
        self.nome_entry.grid(
            row=0, column=1, columnspan=3, padx=(0, PAD_X),
            pady=(24, PAD_Y), sticky="ew",
        )

        # Separator
        ctk.CTkFrame(card, height=1, fg_color=("gray80", "gray30")).grid(
            row=1, column=0, columnspan=4, sticky="ew", padx=PAD_X, pady=(4, 12),
        )

        # Financial fields: 2 per row, label + entry side by side
        fields = [
            ("Valor/Hora (R$)", "valor_hora"),
            ("Valor/AE (R$)",   "valor_ae"),
            ("VT/Dia (R$)",     "vt_dia"),
            ("VR/Dia (R$)",     "vr_dia"),
        ]
        self.entries: dict[str, ctk.CTkEntry] = {}
        for i, (label_text, key) in enumerate(fields):
            grid_row = i // 2 + 2
            is_right = i % 2 == 1
            col_lbl  = 2 if is_right else 0
            col_ent  = 3 if is_right else 1
            lpad = (20, 8) if is_right else (PAD_X, 8)
            rpad = (0, PAD_X) if is_right else (0, 12)

            ctk.CTkLabel(card, text=label_text, anchor="w", width=110).grid(
                row=grid_row, column=col_lbl, padx=lpad, pady=PAD_Y, sticky="w",
            )
            entry = ctk.CTkEntry(card, width=120)
            entry.grid(row=grid_row, column=col_ent, padx=rpad, pady=PAD_Y, sticky="ew")
            self.entries[key] = entry

        # Save row
        save_row = ctk.CTkFrame(card, fg_color="transparent")
        save_row.grid(row=4, column=0, columnspan=4, pady=(12, 20), padx=PAD_X, sticky="ew")
        save_row.grid_columnconfigure(0, weight=1)
        self.status_label = ctk.CTkLabel(save_row, text="", anchor="e")
        self.status_label.grid(row=0, column=0, sticky="e", padx=(0, 12))
        ctk.CTkButton(save_row, text="Salvar", width=130, command=self._save).grid(
            row=0, column=1, sticky="e",
        )

    # ── Week card ─────────────────────────────────────────────────────────────

    def _build_week_card(self, parent):
        card = ctk.CTkFrame(parent)
        card.grid(row=1, column=0, sticky="ew", pady=(20, 0))
        card.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(card, text="Semana Padrão",
                     font=ctk.CTkFont(size=14, weight="bold")).grid(
            row=0, column=0, sticky="w", padx=24, pady=(16, 8),
        )

        self.event_types = database.get_event_types()
        self.event_type_map = {et.id: et for et in self.event_types}

        gf = ctk.CTkFrame(card, fg_color="transparent")
        gf.grid(row=1, column=0, sticky="ew", padx=16, pady=(0, 16))
        gf.grid_columnconfigure(1, weight=1)

        for col, text in enumerate(["Dia", "Eventos", "Horas", "VT", "VR"]):
            ctk.CTkLabel(gf, text=text, font=ctk.CTkFont(weight="bold"),
                         anchor="w" if col == 1 else "center").grid(
                row=0, column=col, padx=4, pady=(0, 4), sticky="ew",
            )

        self.week_chips_frames: list[ctk.CTkFrame] = []
        self.week_hours_labels: list[ctk.CTkLabel] = []
        self.week_vt_vars: list[ctk.IntVar] = []
        self.week_vr_vars: list[ctk.IntVar] = []

        for disp_idx, name in enumerate(WEEKDAY_DISPLAY):
            r = disp_idx + 1
            py_wday = DISPLAY_TO_PY[disp_idx]

            ctk.CTkLabel(gf, text=name, width=50, anchor="center").grid(
                row=r, column=0, padx=4, pady=3,
            )

            chips_frame = ctk.CTkFrame(gf, fg_color="transparent", height=32)
            chips_frame.grid(row=r, column=1, padx=4, pady=3, sticky="ew")
            chips_frame.grid_propagate(False)
            ctk.CTkButton(
                chips_frame, text="+", width=28, height=24,
                fg_color=("gray70", "gray30"), hover_color=("gray60", "gray40"),
                text_color=("black", "white"),
                command=lambda w=py_wday: self._open_weekday_popup(w),
            ).pack(side="left", padx=(0, 4))
            self.week_chips_frames.append(chips_frame)

            hours_lbl = ctk.CTkLabel(gf, text="0", width=52, anchor="center")
            hours_lbl.grid(row=r, column=2, padx=4, pady=3)
            self.week_hours_labels.append(hours_lbl)

            vt_var = ctk.IntVar(value=0)
            ctk.CTkCheckBox(gf, text="", variable=vt_var, width=30,
                            command=lambda w=py_wday: self._on_flag_change(w)).grid(
                row=r, column=3, padx=4, pady=3,
            )
            self.week_vt_vars.append(vt_var)

            vr_var = ctk.IntVar(value=0)
            ctk.CTkCheckBox(gf, text="", variable=vr_var, width=30,
                            command=lambda w=py_wday: self._on_flag_change(w)).grid(
                row=r, column=4, padx=4, pady=3,
            )
            self.week_vr_vars.append(vr_var)

    # ── Summary card ─────────────────────────────────────────────────────────

    def _build_summary_card(self, parent):
        card = ctk.CTkFrame(parent)
        card.grid(row=2, column=0, sticky="ew", pady=(20, 0))
        card.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(card, text="Estimativa de Ganhos",
                     font=ctk.CTkFont(size=14, weight="bold")).grid(
            row=0, column=0, sticky="w", padx=24, pady=(16, 10),
        )

        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.grid(row=1, column=0, sticky="ew", padx=24, pady=(0, 20))
        inner.grid_columnconfigure(1, weight=1)

        for col, text in enumerate(["Semana", "Mês (×4)"]):
            ctk.CTkLabel(inner, text=text, font=ctk.CTkFont(weight="bold"),
                         anchor="e").grid(row=0, column=col + 2, padx=(0, 4 if col == 0 else 0),
                                          pady=(0, 6), sticky="e")

        self._summary_labels: dict[str, tuple] = {}
        for r, (key, title) in enumerate([
            ("horas_row", "Horas"),
            ("vt_row",    "VT"),
            ("vr_row",    "VR"),
        ]):
            row = r + 1
            ctk.CTkLabel(inner, text=title, anchor="w", width=60).grid(
                row=row, column=0, padx=(0, 8), pady=2, sticky="w",
            )
            detail = ctk.CTkLabel(inner, text="", anchor="w",
                                  text_color=("gray50", "gray60"))
            detail.grid(row=row, column=1, padx=(0, 24), pady=2, sticky="w")

            wlbl = ctk.CTkLabel(inner, text="R$ 0,00", anchor="e", width=100)
            wlbl.grid(row=row, column=2, padx=(0, 16), pady=2, sticky="e")

            mlbl = ctk.CTkLabel(inner, text="R$ 0,00", anchor="e", width=110)
            mlbl.grid(row=row, column=3, pady=2, sticky="e")

            self._summary_labels[key] = (detail, wlbl, mlbl)

        ctk.CTkFrame(inner, height=1, fg_color=("gray80", "gray30")).grid(
            row=4, column=0, columnspan=4, sticky="ew", pady=(6, 6),
        )
        ctk.CTkLabel(inner, text="Total", anchor="w",
                     font=ctk.CTkFont(weight="bold")).grid(
            row=5, column=0, columnspan=2, pady=2, sticky="w",
        )
        self._total_week_lbl = ctk.CTkLabel(
            inner, text="R$ 0,00", anchor="e",
            font=ctk.CTkFont(weight="bold"), width=100,
        )
        self._total_week_lbl.grid(row=5, column=2, padx=(0, 16), pady=2, sticky="e")
        self._total_month_lbl = ctk.CTkLabel(
            inner, text="R$ 0,00", anchor="e",
            font=ctk.CTkFont(size=15, weight="bold"), width=110,
        )
        self._total_month_lbl.grid(row=5, column=3, pady=2, sticky="e")

    # ── Config ───────────────────────────────────────────────────────────────

    def _load(self):
        config = database.get_config()
        self.nome_entry.delete(0, "end")
        self.nome_entry.insert(0, config.nome)
        for key, entry in self.entries.items():
            entry.delete(0, "end")
            val = getattr(config, key)
            entry.insert(0, f"{val:.2f}".replace(".", ","))

    def _save(self):
        try:
            nome = self.nome_entry.get().strip()
            values = {}
            for key, entry in self.entries.items():
                text = entry.get().strip().replace(",", ".")
                values[key] = float(text)
            database.update_config(Config(nome=nome, **values))
            self.status_label.configure(text="Salvo!", text_color="green")
            self.after(2000, lambda: self.status_label.configure(text=""))
            self._update_summary()
            if self.on_save_callback:
                self.on_save_callback()
        except ValueError:
            self.status_label.configure(text="Valor inválido!", text_color="red")

    # ── Default week ─────────────────────────────────────────────────────────

    def _load_week(self):
        flags = database.get_default_week_flags()
        for disp_idx in range(7):
            py_wday = DISPLAY_TO_PY[disp_idx]
            self._refresh_weekday_chips(disp_idx, py_wday)
            vt, vr = flags.get(py_wday, (False, False))
            self.week_vt_vars[disp_idx].set(int(vt))
            self.week_vr_vars[disp_idx].set(int(vr))
        self._update_summary()

    def _refresh_weekday_chips(self, disp_idx: int, py_wday: int):
        frame = self.week_chips_frames[disp_idx]
        for widget in frame.winfo_children():
            if widget.cget("text") != "+":
                widget.destroy()

        entries = database.get_default_week_entries_for_weekday(py_wday)
        total_hours = 0.0
        for entry in entries:
            et = self.event_type_map.get(entry.event_type_id)
            if not et:
                continue
            total_hours += entry.hours
            hours_str = str(entry.hours).replace(".", ",").rstrip("0").rstrip(",")
            label = f"{et.name[:4]}. {hours_str}h" if len(et.name) > 5 else f"{et.name} {hours_str}h"
            ctk.CTkButton(
                frame, text=label, width=80, height=24,
                fg_color=et.color, hover_color=et.color,
                text_color="white", font=ctk.CTkFont(size=11),
                command=lambda w=py_wday, d=disp_idx: self._open_weekday_popup(w, d),
            ).pack(side="left", padx=(0, 3))

        self.week_hours_labels[disp_idx].configure(
            text=str(total_hours).rstrip("0").rstrip(".") or "0",
        )
        self._update_summary()

    def _open_weekday_popup(self, py_wday: int, disp_idx: int | None = None):
        if disp_idx is None:
            disp_idx = DISPLAY_TO_PY.index(py_wday)
        if self._active_popup and self._active_popup.winfo_exists():
            self._active_popup.focus()
            return
        self._active_popup = DefaultWeekDayPopup(
            parent=self.winfo_toplevel(),
            weekday=py_wday,
            event_types=self.event_types,
            on_close=lambda d=disp_idx, w=py_wday: self._refresh_weekday_chips(d, w),
        )

    def _on_flag_change(self, py_wday: int):
        disp_idx = DISPLAY_TO_PY.index(py_wday)
        database.save_default_week_flag(
            py_wday,
            vt=bool(self.week_vt_vars[disp_idx].get()),
            vr=bool(self.week_vr_vars[disp_idx].get()),
        )
        self._update_summary()

    # ── Summary ──────────────────────────────────────────────────────────────

    def _update_summary(self):
        config  = database.get_config()
        entries = database.get_default_week()
        flags   = database.get_default_week_flags()

        total_hours = sum(e.hours for e in entries)
        vt_days = sum(1 for w in range(7) if flags.get(w, (False, False))[0])
        vr_days = sum(1 for w in range(7) if flags.get(w, (False, False))[1])

        w_horas = total_hours * config.valor_hora
        w_vt    = vt_days    * config.vt_dia
        w_vr    = vr_days    * config.vr_dia
        w_total = w_horas + w_vt + w_vr

        def fmt(v: float) -> str:
            return f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

        hours_str = str(total_hours).rstrip("0").rstrip(".") or "0"
        d, wl, ml = self._summary_labels["horas_row"]
        d.configure(text=f"{hours_str}h  ×  R$ {config.valor_hora:.2f}/h".replace(".", ","))
        wl.configure(text=fmt(w_horas))
        ml.configure(text=fmt(w_horas * 4))

        d, wl, ml = self._summary_labels["vt_row"]
        d.configure(text=f"{vt_days} dia(s)  ×  R$ {config.vt_dia:.2f}".replace(".", ","))
        wl.configure(text=fmt(w_vt))
        ml.configure(text=fmt(w_vt * 4))

        d, wl, ml = self._summary_labels["vr_row"]
        d.configure(text=f"{vr_days} dia(s)  ×  R$ {config.vr_dia:.2f}".replace(".", ","))
        wl.configure(text=fmt(w_vr))
        ml.configure(text=fmt(w_vr * 4))

        self._total_week_lbl.configure(text=fmt(w_total))
        self._total_month_lbl.configure(text=fmt(w_total * 4))

    def on_show(self):
        self._load()
        self._update_summary()
