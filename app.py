import customtkinter as ctk
from datetime import date
from tkinter import messagebox

import database
from ui.monthly_view import MonthlyView
from ui.history_view import HistoryView
from ui.config_view import ConfigView


class App(ctk.CTk):
    ACCENT_COLOR = "#3B8ED0"
    ACCENT_HOVER_COLOR = "#2F6EA7"
    ACCENT_TEXT_COLOR = "#3B8ED0"

    def __init__(self):
        super().__init__()
        self._first_run_without_db = not database.DB_PATH.exists()
        self._current_frame_name = "lancamentos"

        self.title("Controle de Horas")
        self.geometry("1200x750")
        self.minsize(1000, 600)

        ctk.set_default_color_theme("blue")
        database.init_db()

        self.tema_atual = database.get_tema()
        ctk.set_appearance_mode(self.tema_atual)

        # Layout
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Sidebar
        self.sidebar = ctk.CTkFrame(self, width=200, corner_radius=0)
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_rowconfigure(5, weight=1)

        title_label = ctk.CTkLabel(
            self.sidebar, text="Controle\nde Horas",
            font=ctk.CTkFont(size=20, weight="bold"),
        )
        title_label.grid(row=0, column=0, padx=20, pady=(20, 30))

        self.btn_lancamentos = ctk.CTkButton(
            self.sidebar, text="Lançamentos", width=160, border_width=1,
            command=lambda: self.show_frame("lancamentos"),
        )
        self.btn_lancamentos.grid(row=1, column=0, padx=20, pady=5)

        self.btn_historico = ctk.CTkButton(
            self.sidebar, text="Histórico", width=160, border_width=1,
            command=lambda: self.show_frame("historico"),
        )
        self.btn_historico.grid(row=2, column=0, padx=20, pady=5)

        self.btn_config = ctk.CTkButton(
            self.sidebar, text="Configuração", width=160, border_width=1,
            command=lambda: self.show_frame("config"),
        )
        self.btn_config.grid(row=3, column=0, padx=20, pady=5)

        self.nav_buttons = {
            "lancamentos": self.btn_lancamentos,
            "historico": self.btn_historico,
            "config": self.btn_config,
        }

        # Theme toggle (pushed to bottom by row 5 spacer)
        self.btn_tema = ctk.CTkButton(
            self.sidebar,
            text="Tema: Claro" if self.tema_atual == "dark" else "Tema: Escuro",
            command=self._toggle_tema,
            width=160,
            border_width=1,
        )
        self.btn_tema.grid(row=6, column=0, padx=20, pady=(0, 20))

        for key, btn in self.nav_buttons.items():
            self._bind_secondary_hover(btn, lambda _, button=btn, button_key=key: self._on_nav_button_enter(button_key, button))
            self._bind_secondary_leave(btn, lambda _, button=btn, button_key=key: self._on_nav_button_leave(button_key, button))

        self._bind_secondary_hover(self.btn_tema, lambda _, button=self.btn_tema: self._apply_primary_button_style(button))
        self._bind_secondary_leave(self.btn_tema, lambda _, button=self.btn_tema: self._apply_secondary_button_style(button))
        self._apply_secondary_button_style(self.btn_tema)

        # Content area
        self.content = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        self.content.grid(row=0, column=1, sticky="nsew")
        self.content.grid_columnconfigure(0, weight=1)
        self.content.grid_rowconfigure(0, weight=1)

        # Frames
        self.frames: dict[str, ctk.CTkFrame] = {}
        self.frames["lancamentos"] = MonthlyView(self.content)
        self.frames["historico"] = HistoryView(self.content)
        self.frames["config"] = ConfigView(self.content, on_save_callback=self._on_config_saved)

        for frame in self.frames.values():
            frame.grid(row=0, column=0, sticky="nsew")

        self.show_frame("config" if self._first_run_without_db else "lancamentos")

        # Keyboard shortcuts
        self.bind_all("<Control-Key-1>", lambda e: self.show_frame("lancamentos"))
        self.bind_all("<Control-Key-2>", lambda e: self.show_frame("historico"))
        self.bind_all("<Control-Key-3>", lambda e: self.show_frame("config"))
        self.bind_all("<Control-Left>", self._on_nav_left)
        self.bind_all("<Control-Right>", self._on_nav_right)

        if self._first_run_without_db:
            self.after(150, self._show_first_run_notice)
        else:
            self.after(300, self._check_apply_default_week)

        self.after(100, self._setup_holidays)

        self.bind_all("<Button-4>", self._on_mousewheel)
        self.bind_all("<Button-5>", self._on_mousewheel)
        self.bind_all("<MouseWheel>", self._on_mousewheel)

    def show_frame(self, name: str) -> None:
        self._current_frame_name = name
        for key, btn in self.nav_buttons.items():
            if key == name:
                self._apply_primary_button_style(btn)
            else:
                self._apply_secondary_button_style(btn)

        frame = self.frames[name]
        frame.tkraise()

        if hasattr(frame, "on_show"):
            frame.on_show()

    def _on_config_saved(self) -> None:
        lancamentos = self.frames["lancamentos"]
        if hasattr(lancamentos, "refresh_summary"):
            lancamentos.refresh_summary()

    def _setup_holidays(self) -> None:
        today = date.today()
        if database.has_holidays_for_year(today.year):
            return

        self._holiday_banner = ctk.CTkLabel(
            self,
            text="  Preparando feriados...  ",
            fg_color=("#3B8ED0", "#1a4a7a"),
            text_color="white",
            corner_radius=6,
            height=28,
            font=ctk.CTkFont(size=12),
        )
        self._holiday_banner.place(relx=0.5, rely=1.0, anchor="s", y=-12)

        database.ensure_holidays_for_year(today.year, on_complete=self._on_holidays_ready)

    def _on_holidays_ready(self) -> None:
        try:
            self.after(0, self._finish_holidays_setup)
        except Exception:
            pass

    def _finish_holidays_setup(self) -> None:
        if hasattr(self, "_holiday_banner"):
            self._holiday_banner.place_forget()
        lancamentos = self.frames.get("lancamentos")
        if lancamentos and hasattr(lancamentos, "_load_month"):
            lancamentos._load_month()

    def _check_apply_default_week(self) -> None:
        today = date.today()
        if not database.get_default_week():
            return
        if not database.is_month_empty(today.year, today.month):
            return

        month_name = [
            "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
            "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro",
        ][today.month - 1]

        answer = messagebox.askyesno(
            "Aplicar semana padrão",
            f"O mês de {month_name} está vazio.\n\n"
            f"Deseja aplicar a semana padrão para {month_name} de {today.year}?",
            parent=self,
        )
        if answer:
            database.apply_default_week_to_month(today.year, today.month)
            lancamentos = self.frames.get("lancamentos")
            if lancamentos and hasattr(lancamentos, "on_show"):
                lancamentos.on_show()

    def _show_first_run_notice(self) -> None:
        messagebox.showinfo(
            "Configuração inicial",
            "Nenhum banco de dados foi encontrado.\n\n"
            "Configure seus dados em Configuração para começar a usar o sistema.",
            parent=self,
        )
        self.show_frame("config")

    def _toggle_tema(self):
        self.tema_atual = "light" if self.tema_atual == "dark" else "dark"
        ctk.set_appearance_mode(self.tema_atual)
        database.set_tema(self.tema_atual)
        self.btn_tema.configure(
            text="Tema: Claro" if self.tema_atual == "dark" else "Tema: Escuro"
        )
        self._apply_secondary_button_style(self.btn_tema)
        for key, btn in self.nav_buttons.items():
            if key == self._current_frame_name:
                self._apply_primary_button_style(btn)
            else:
                self._apply_secondary_button_style(btn)
        for frame in self.frames.values():
            if hasattr(frame, "refresh_theme"):
                frame.refresh_theme()

    def _apply_primary_button_style(self, button: ctk.CTkButton) -> None:
        button.configure(
            fg_color=self.ACCENT_COLOR,
            hover_color=self.ACCENT_HOVER_COLOR,
            border_color=self.ACCENT_COLOR,
            text_color="white",
        )

    def _apply_secondary_button_style(self, button: ctk.CTkButton) -> None:
        button.configure(
            fg_color="transparent",
            hover_color=self.ACCENT_COLOR,
            border_color=self.ACCENT_COLOR,
            text_color=self.ACCENT_TEXT_COLOR,
        )

    def _on_nav_button_enter(self, key: str, button: ctk.CTkButton) -> None:
        if key != self._current_frame_name:
            self._apply_primary_button_style(button)

    def _on_nav_button_leave(self, key: str, button: ctk.CTkButton) -> None:
        if key != self._current_frame_name:
            self._apply_secondary_button_style(button)

    def _bind_secondary_hover(self, button: ctk.CTkButton, callback) -> None:
        button.bind("<Enter>", callback)

    def _bind_secondary_leave(self, button: ctk.CTkButton, callback) -> None:
        button.bind("<Leave>", callback)

    def _on_mousewheel(self, event):
        widget = event.widget
        while widget:
            if isinstance(widget, ctk.CTkScrollableFrame):
                canvas = widget._parent_canvas
                if event.num == 4 or event.delta > 0:
                    canvas.yview_scroll(-1, "units")
                elif event.num == 5 or event.delta < 0:
                    canvas.yview_scroll(1, "units")
                return
            try:
                widget = widget.master
            except Exception:
                break

    def _on_nav_left(self, event):
        focused = self.focus_get()
        if focused and focused.winfo_class() in ("Entry", "Text", "TCombobox"):
            return
        lancamentos = self.frames.get("lancamentos")
        if lancamentos:
            lancamentos._prev_month()

    def _on_nav_right(self, event):
        focused = self.focus_get()
        if focused and focused.winfo_class() in ("Entry", "Text", "TCombobox"):
            return
        lancamentos = self.frames.get("lancamentos")
        if lancamentos:
            lancamentos._next_month()


if __name__ == "__main__":
    app = App()
    app.mainloop()
