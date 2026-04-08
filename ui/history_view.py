from datetime import date

import customtkinter as ctk
import matplotlib
import matplotlib.ticker as mticker
matplotlib.use("TkAgg")
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

import database

MONTH_ABBREVS = [
    "", "jan", "fev", "mar", "abr", "mai", "jun",
    "jul", "ago", "set", "out", "nov", "dez",
]
MONTH_FULL = [
    "", "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
    "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro",
]


def _fmt(v: float) -> str:
    return f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


class HistoryView(ctk.CTkFrame):
    def __init__(self, parent):
        super().__init__(parent, fg_color="transparent")

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        self.current_year = date.today().year

        self._build_nav()
        self._build_kpi_row()
        self._build_content()

    # ── Nav ──────────────────────────────────────────────────────────────────

    def _build_nav(self):
        nav = ctk.CTkFrame(self, fg_color="transparent")
        nav.grid(row=0, column=0, sticky="ew", padx=24, pady=(20, 12))
        nav.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            nav, text="Histórico Anual",
            font=ctk.CTkFont(size=20, weight="bold"),
        ).grid(row=0, column=0, sticky="w")

        year_nav = ctk.CTkFrame(nav, fg_color="transparent")
        year_nav.grid(row=0, column=1)

        ctk.CTkButton(year_nav, text="◀", width=36, command=self._prev_year).pack(side="left")
        self.year_label = ctk.CTkLabel(
            year_nav, text=str(self.current_year),
            font=ctk.CTkFont(size=18, weight="bold"), width=70,
        )
        self.year_label.pack(side="left", padx=6)
        ctk.CTkButton(year_nav, text="▶", width=36, command=self._next_year).pack(side="left")

    # ── KPI cards ─────────────────────────────────────────────────────────────

    def _build_kpi_row(self):
        self.kpi_row = ctk.CTkFrame(self, fg_color="transparent")
        self.kpi_row.grid(row=1, column=0, sticky="ew", padx=24, pady=(0, 12))
        self.kpi_row.grid_columnconfigure((0, 1, 2), weight=1)

        self.kpi_total   = self._make_kpi_card(self.kpi_row, "Total do Ano",    0)
        self.kpi_avg     = self._make_kpi_card(self.kpi_row, "Média / mês",     1)
        self.kpi_best    = self._make_kpi_card(self.kpi_row, "Melhor Mês",      2)

    def _make_kpi_card(self, parent, title: str, col: int):
        card = ctk.CTkFrame(parent)
        card.grid(row=0, column=col, sticky="ew",
                  padx=(0, 12) if col < 2 else 0, pady=0)
        card.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(card, text=title,
                     font=ctk.CTkFont(size=11),
                     text_color=("gray40", "gray60")).grid(
            row=0, column=0, padx=16, pady=(14, 2), sticky="w",
        )
        val_lbl = ctk.CTkLabel(card, text="—",
                               font=ctk.CTkFont(size=18, weight="bold"))
        val_lbl.grid(row=1, column=0, padx=16, pady=(0, 14), sticky="w")
        return val_lbl

    # ── Table + Chart ─────────────────────────────────────────────────────────

    def _build_content(self):
        content = ctk.CTkFrame(self, fg_color="transparent")
        content.grid(row=2, column=0, sticky="nsew", padx=24, pady=(0, 16))
        content.grid_columnconfigure(1, weight=1)
        content.grid_rowconfigure(0, weight=1)

        # Table
        self.table_frame = ctk.CTkFrame(content, width=240)
        self.table_frame.grid(row=0, column=0, sticky="ns", padx=(0, 16))
        self.table_frame.grid_propagate(False)

        # Chart
        chart_card = ctk.CTkFrame(content)
        chart_card.grid(row=0, column=1, sticky="nsew")
        chart_card.grid_columnconfigure(0, weight=1)
        chart_card.grid_rowconfigure(0, weight=1)

        self.fig = Figure(dpi=100)
        self.fig.patch.set_facecolor("#2b2b2b")
        self.ax = self.fig.add_subplot(111)
        self.canvas = FigureCanvasTkAgg(self.fig, master=chart_card)
        self.canvas.get_tk_widget().grid(row=0, column=0, sticky="nsew",
                                         padx=4, pady=4)

    # ── Theme ─────────────────────────────────────────────────────────────────

    def _chart_theme(self) -> dict:
        if ctk.get_appearance_mode().lower() == "light":
            return {
                "figure_bg": "#f4f6f8", "axes_bg": "#ffffff",
                "text": "#1f2937",      "spine": "#cbd5e1",
                "line": "#2563eb",      "fill": "#93c5fd",
                "grid": "#e2e8f0",      "today": "#dc2626",
            }
        return {
            "figure_bg": "#2b2b2b",    "axes_bg": "#2b2b2b",
            "text": "#f3f4f6",         "spine": "#4b5563",
            "line": "#4fc3f7",         "fill": "#4fc3f7",
            "grid": "#374151",         "today": "#f87171",
        }

    def refresh_theme(self):
        self._load()

    # ── Navigation ────────────────────────────────────────────────────────────

    def _prev_year(self):
        self.current_year -= 1
        self._load()

    def _next_year(self):
        self.current_year += 1
        self._load()

    # ── Load ──────────────────────────────────────────────────────────────────

    def _load(self):
        self.year_label.configure(text=str(self.current_year))
        totals = database.get_yearly_totals(self.current_year)

        non_zero   = [(m, v) for m, v in totals if v > 0]
        total_year = sum(v for _, v in totals)
        avg        = sum(v for _, v in non_zero) / len(non_zero) if non_zero else 0
        best_month, best_val = max(non_zero, key=lambda x: x[1]) if non_zero else (0, 0)
        max_val    = best_val or 1

        # KPI cards
        self.kpi_total.configure(text=_fmt(total_year))
        self.kpi_avg.configure(text=_fmt(avg))
        best_label = (
            f"{MONTH_FULL[best_month]} · {_fmt(best_val)}" if best_month else "—"
        )
        self.kpi_best.configure(text=best_label,
                                font=ctk.CTkFont(size=14, weight="bold"))

        today = date.today()
        current_month = today.month if today.year == self.current_year else None

        # ── Table ──
        for w in self.table_frame.winfo_children():
            w.destroy()

        # Header
        header = ctk.CTkFrame(self.table_frame, fg_color="transparent")
        header.pack(fill="x", padx=8, pady=(10, 4))
        ctk.CTkLabel(header, text="Período", width=80,
                     font=ctk.CTkFont(weight="bold"), anchor="w").pack(side="left")
        ctk.CTkLabel(header, text="Total", width=110,
                     font=ctk.CTkFont(weight="bold"), anchor="e").pack(side="right")

        ctk.CTkFrame(self.table_frame, height=1,
                     fg_color=("gray80", "gray35")).pack(fill="x", padx=8, pady=(0, 4))

        for month, total in totals:
            period = f"{MONTH_ABBREVS[month]}/{str(self.current_year)[2:]}"
            is_current = month == current_month
            is_zero = total == 0

            row_fg = ("#3B8ED0", "#2F6EA7") if is_current else "transparent"
            text_color = "white" if is_current else (
                ("gray55", "gray50") if is_zero else ("gray10", "gray90")
            )

            row = ctk.CTkFrame(self.table_frame, fg_color=row_fg, corner_radius=6)
            row.pack(fill="x", padx=8, pady=1)

            ctk.CTkLabel(row, text=period, width=80, anchor="w",
                         text_color=text_color).pack(side="left", padx=(8, 0), pady=5)

            # proportional bar
            if total > 0 and not is_current:
                bar_w = max(3, int(60 * total / max_val))
                ctk.CTkFrame(row, width=bar_w, height=6,
                             fg_color=("#93c5fd", "#4fc3f7"),
                             corner_radius=3).pack(side="left", padx=4)

            ctk.CTkLabel(row, text=_fmt(total), width=100, anchor="e",
                         text_color=text_color).pack(side="right", padx=(0, 8), pady=5)

        # ── Chart ──
        theme = self._chart_theme()
        self.ax.clear()
        self.fig.patch.set_facecolor(theme["figure_bg"])
        self.ax.set_facecolor(theme["axes_bg"])

        labels = [MONTH_ABBREVS[m] + f"/{str(self.current_year)[2:]}" for m, _ in totals]
        values = [v for _, v in totals]
        xs     = list(range(len(labels)))

        self.ax.plot(xs, values, marker="o", linewidth=2,
                     color=theme["line"], markersize=5, zorder=3)
        self.ax.fill_between(xs, values, alpha=0.12,
                             color=theme["fill"], zorder=2)

        # Highlight current month
        if current_month is not None:
            ci = current_month - 1
            self.ax.plot(ci, values[ci], marker="o", markersize=9,
                         color=theme["today"], zorder=4)

        # Annotate peak
        if non_zero:
            peak_i = best_month - 1
            peak_v = values[peak_i]
            self.ax.annotate(
                _fmt(peak_v),
                xy=(peak_i, peak_v),
                xytext=(0, 10), textcoords="offset points",
                ha="center", fontsize=8, color=theme["text"],
            )

        self.ax.set_xticks(xs)
        self.ax.set_xticklabels(labels, rotation=45, ha="right")
        self.ax.yaxis.set_major_formatter(
            mticker.FuncFormatter(lambda v, _: f"R$ {v:,.0f}".replace(",", "."))
        )
        self.ax.tick_params(colors=theme["text"], labelsize=8)
        self.ax.grid(True, alpha=0.15, linestyle="--", color=theme["grid"])

        for spine in ("top", "right"):
            self.ax.spines[spine].set_visible(False)
        for spine in ("bottom", "left"):
            self.ax.spines[spine].set_color(theme["spine"])

        self.fig.tight_layout(pad=1.5)
        self.canvas.draw()

    def on_show(self):
        self._load()
