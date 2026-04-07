from datetime import date

import customtkinter as ctk
import matplotlib
matplotlib.use("TkAgg")
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

import database

MONTH_ABBREVS = [
    "", "jan", "fev", "mar", "abr", "mai", "jun",
    "jul", "ago", "set", "out", "nov", "dez",
]


class HistoryView(ctk.CTkFrame):
    def __init__(self, parent):
        super().__init__(parent, fg_color="transparent")

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        self.current_year = date.today().year

        # Title + year selector
        nav = ctk.CTkFrame(self, fg_color="transparent")
        nav.grid(row=0, column=0, sticky="ew", padx=20, pady=(20, 10))
        nav.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            nav, text="Histórico Anual",
            font=ctk.CTkFont(size=20, weight="bold"),
        ).grid(row=0, column=0, padx=(0, 20))

        btn_prev = ctk.CTkButton(nav, text="◀", width=40, command=self._prev_year)
        btn_prev.grid(row=0, column=1, sticky="e", padx=5)

        self.year_label = ctk.CTkLabel(
            nav, text=str(self.current_year),
            font=ctk.CTkFont(size=18, weight="bold"),
        )
        self.year_label.grid(row=0, column=2, padx=5)

        btn_next = ctk.CTkButton(nav, text="▶", width=40, command=self._next_year)
        btn_next.grid(row=0, column=3, padx=5)

        # Table + chart container
        content = ctk.CTkFrame(self, fg_color="transparent")
        content.grid(row=1, column=0, sticky="nsew", padx=20, pady=10)
        content.grid_columnconfigure(1, weight=1)
        content.grid_rowconfigure(0, weight=1)

        # Table
        self.table_frame = ctk.CTkFrame(content)
        self.table_frame.grid(row=0, column=0, sticky="ns", padx=(0, 20))

        # Chart
        self.chart_frame = ctk.CTkFrame(content, fg_color="transparent")
        self.chart_frame.grid(row=0, column=1, sticky="nsew")

        self.fig = Figure(figsize=(6, 4), dpi=100)
        self.fig.patch.set_facecolor("#2b2b2b")
        self.ax = self.fig.add_subplot(111)
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.chart_frame)
        self.canvas.get_tk_widget().pack(fill="both", expand=True)

        # Average label
        self.avg_label = ctk.CTkLabel(
            self, text="",
            font=ctk.CTkFont(size=14),
        )
        self.avg_label.grid(row=2, column=0, pady=10)

    def _chart_theme(self) -> dict[str, str]:
        if ctk.get_appearance_mode().lower() == "light":
            return {
                "figure_bg": "#f4f6f8",
                "axes_bg": "#ffffff",
                "text": "#1f2937",
                "spine": "#cbd5e1",
                "line": "#2563eb",
            }
        return {
            "figure_bg": "#2b2b2b",
            "axes_bg": "#2b2b2b",
            "text": "#f3f4f6",
            "spine": "#6b7280",
            "line": "#4fc3f7",
        }

    def refresh_theme(self):
        self._load()

    def _prev_year(self):
        self.current_year -= 1
        self._load()

    def _next_year(self):
        self.current_year += 1
        self._load()

    def _load(self):
        self.year_label.configure(text=str(self.current_year))

        totals = database.get_yearly_totals(self.current_year)

        # Rebuild table
        for widget in self.table_frame.winfo_children():
            widget.destroy()

        # Header
        ctk.CTkLabel(
            self.table_frame, text="Período",
            font=ctk.CTkFont(weight="bold"), width=100,
        ).grid(row=0, column=0, padx=10, pady=5)
        ctk.CTkLabel(
            self.table_frame, text="Total",
            font=ctk.CTkFont(weight="bold"), width=120,
        ).grid(row=0, column=1, padx=10, pady=5)

        fmt = lambda v: f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

        non_zero = []
        for i, (month, total) in enumerate(totals):
            period = f"{MONTH_ABBREVS[month]}/{str(self.current_year)[2:]}"
            ctk.CTkLabel(self.table_frame, text=period, width=100).grid(
                row=i + 1, column=0, padx=10, pady=2,
            )
            ctk.CTkLabel(self.table_frame, text=fmt(total), width=120).grid(
                row=i + 1, column=1, padx=10, pady=2,
            )
            if total > 0:
                non_zero.append(total)

        # Average
        avg = sum(non_zero) / len(non_zero) if non_zero else 0
        self.avg_label.configure(text=f"Média: {fmt(avg)}")

        # Chart
        self.ax.clear()
        months = [MONTH_ABBREVS[m] + f"/{str(self.current_year)[2:]}" for m, _ in totals]
        values = [t for _, t in totals]
        theme = self._chart_theme()

        self.fig.patch.set_facecolor(theme["figure_bg"])
        self.ax.plot(months, values, marker="o", linewidth=2, color=theme["line"])
        self.ax.set_title("Ganho x Período", color=theme["text"], fontsize=14)
        self.ax.set_facecolor(theme["axes_bg"])
        self.ax.tick_params(colors=theme["text"], labelsize=8, rotation=45)
        self.ax.yaxis.label.set_color(theme["text"])
        self.ax.spines["bottom"].set_color(theme["spine"])
        self.ax.spines["left"].set_color(theme["spine"])
        self.ax.spines["top"].set_visible(False)
        self.ax.spines["right"].set_visible(False)

        self.fig.tight_layout()
        self.canvas.draw()

    def on_show(self):
        self._load()
