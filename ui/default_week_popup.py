import customtkinter as ctk

import database
from models import DefaultWeekEntry

WEEKDAY_NAMES_FULL = ["Segunda", "Terça", "Quarta", "Quinta", "Sexta", "Sábado", "Domingo"]


class DefaultWeekDayPopup(ctk.CTkToplevel):
    def __init__(self, parent, weekday: int, event_types, on_close):
        super().__init__(parent)

        self.weekday = weekday
        self.event_types = event_types
        self.event_names = [et.name for et in event_types]
        self.event_name_to_id = {et.name: et.id for et in event_types}
        self.event_name_to_color = {et.name: et.color for et in event_types}
        self.on_close_cb = on_close
        self.row_frames: list[ctk.CTkFrame] = []

        day_name = WEEKDAY_NAMES_FULL[weekday]
        self.title(f"Semana Padrão — {day_name}")
        self.geometry("420x360")
        self.resizable(False, True)
        self.transient(parent)
        self.wait_visibility()
        self.grab_set()

        self.update_idletasks()
        px = parent.winfo_rootx() + parent.winfo_width() // 2 - 210
        py = parent.winfo_rooty() + parent.winfo_height() // 2 - 180
        self.geometry(f"+{px}+{py}")

        ctk.CTkLabel(
            self, text=day_name,
            font=ctk.CTkFont(size=14, weight="bold"),
        ).pack(pady=(12, 6), padx=16, anchor="w")

        self.entries_frame = ctk.CTkScrollableFrame(self, fg_color="transparent", height=200)
        self.entries_frame.pack(fill="both", expand=True, padx=10, pady=(0, 6))

        ctk.CTkButton(
            self, text="+ Adicionar Evento",
            command=self._add_empty_row,
            fg_color=("gray75", "gray25"), text_color=("black", "white"),
            hover_color=("gray65", "gray35"),
        ).pack(fill="x", padx=10, pady=(0, 4))

        ctk.CTkButton(self, text="Fechar", command=self._close).pack(
            fill="x", padx=10, pady=(0, 12),
        )

        self.protocol("WM_DELETE_WINDOW", self._close)
        self._load_entries()

    def _load_entries(self):
        for w in self.entries_frame.winfo_children():
            w.destroy()
        self.row_frames.clear()
        for entry in database.get_default_week_entries_for_weekday(self.weekday):
            event_name = next(
                (et.name for et in self.event_types if et.id == entry.event_type_id), ""
            )
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

        entry = ctk.CTkEntry(row, width=65, height=30, placeholder_text="Horas")
        entry.pack(side="left", padx=(0, 4))
        if hours_str:
            entry.insert(0, hours_str)

        initial_color = self.event_name_to_color.get(event_name, ("gray60", "gray40"))
        color_lbl = ctk.CTkLabel(
            row, text="", width=14, height=24,
            fg_color=initial_color, corner_radius=4,
        )
        color_lbl.pack(side="left", padx=(0, 4))

        combo = ctk.CTkComboBox(row, values=self.event_names, width=140, height=30)
        combo.set(event_name)
        combo.pack(side="left", padx=(0, 4))

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
            children[3].configure(state="disabled" if idx == 0 else "normal")
            children[4].configure(state="disabled" if idx == last else "normal")

    def _save_all(self):
        entries: list[DefaultWeekEntry] = []
        slot = 0
        for row_frame in self.row_frames:
            children = row_frame.winfo_children()
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
            if event_type_id and hours > 0:
                entries.append(DefaultWeekEntry(
                    id=0, weekday=self.weekday, slot=slot,
                    event_type_id=event_type_id, hours=hours,
                ))
                slot += 1
        database.save_default_week_entries_for_weekday(self.weekday, entries)

    def _close(self):
        self._save_all()
        self.on_close_cb()
        self.destroy()
