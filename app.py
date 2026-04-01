import customtkinter as ctk

import database
from ui.monthly_view import MonthlyView
from ui.history_view import HistoryView
from ui.config_view import ConfigView


class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Controle de Horas")
        self.geometry("1200x750")
        self.minsize(1000, 600)

        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        database.init_db()

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
            self.sidebar, text="Lançamentos",
            command=lambda: self.show_frame("lancamentos"),
        )
        self.btn_lancamentos.grid(row=1, column=0, padx=20, pady=5)

        self.btn_historico = ctk.CTkButton(
            self.sidebar, text="Histórico",
            command=lambda: self.show_frame("historico"),
        )
        self.btn_historico.grid(row=2, column=0, padx=20, pady=5)

        self.btn_config = ctk.CTkButton(
            self.sidebar, text="Configuração",
            command=lambda: self.show_frame("config"),
        )
        self.btn_config.grid(row=3, column=0, padx=20, pady=5)

        self.nav_buttons = {
            "lancamentos": self.btn_lancamentos,
            "historico": self.btn_historico,
            "config": self.btn_config,
        }

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

        self.show_frame("lancamentos")

    def show_frame(self, name: str) -> None:
        for key, btn in self.nav_buttons.items():
            if key == name:
                btn.configure(fg_color=("gray75", "gray25"))
            else:
                btn.configure(fg_color=("gray70", "gray30") if False else ctk.ThemeManager.theme["CTkButton"]["fg_color"])

        frame = self.frames[name]
        frame.tkraise()

        if hasattr(frame, "on_show"):
            frame.on_show()

    def _on_config_saved(self) -> None:
        lancamentos = self.frames["lancamentos"]
        if hasattr(lancamentos, "refresh_summary"):
            lancamentos.refresh_summary()


if __name__ == "__main__":
    app = App()
    app.mainloop()
