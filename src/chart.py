from datetime import datetime

import customtkinter as ctk
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
import matplotlib.dates as mdates

_BG = "#1a1a1a"
_AX_BG = "#141414"
_GRID_COLOR = "#2a2a2a"
_TICK_COLOR = "#888888"
_SPINE_COLOR = "#333333"
_PRICE_LINE = "#4fc3f7"
_NET_LINE = "#81c784"
_BATCH_COLORS = ["#ff8a65", "#ce93d8", "#fff176", "#80cbc4", "#ef9a9a", "#ffcc02"]


class PriceChart(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self.configure(fg_color=_BG)

        self.fig = Figure(figsize=(1, 1), dpi=100, facecolor=_BG)
        self.fig.subplots_adjust(left=0.07, right=0.97, top=0.88, bottom=0.18)
        self.ax = self.fig.add_subplot(111)
        self._style_ax()

        self.canvas = FigureCanvasTkAgg(self.fig, master=self)
        self.canvas.get_tk_widget().pack(fill="both", expand=True, padx=0, pady=0)
        self.clear_chart()

    def _style_ax(self):
        ax = self.ax
        ax.set_facecolor(_AX_BG)
        ax.tick_params(colors=_TICK_COLOR, labelsize=8)
        ax.grid(True, color=_GRID_COLOR, linewidth=0.5, linestyle="--")
        for spine in ax.spines.values():
            spine.set_edgecolor(_SPINE_COLOR)
        ax.title.set_color("#dddddd")
        ax.xaxis.label.set_color(_TICK_COLOR)
        ax.yaxis.label.set_color(_TICK_COLOR)

    def clear_chart(self):
        self.ax.clear()
        self._style_ax()
        self.ax.set_title("Select a case row to view its price history", color="#555555", fontsize=10)
        self.canvas.draw()

    def update_chart(self, case_name: str, price_history: list, batches: list):
        self.ax.clear()
        self._style_ax()

        if not price_history:
            self.ax.set_title(
                f"{case_name}  —  no price history yet, click ↻ Refresh",
                color="#888888", fontsize=10,
            )
            self.canvas.draw()
            return

        timestamps = [datetime.fromisoformat(p["timestamp"]) for p in price_history]
        prices = [p["price"] for p in price_history]
        net_prices = [p * 0.85 for p in prices]

        marker = "o" if len(prices) == 1 else None
        ms = 6 if len(prices) == 1 else 3

        self.ax.plot(
            timestamps, prices,
            color=_PRICE_LINE, linewidth=2,
            label="Market price", marker=marker or "o", markersize=ms,
        )
        self.ax.plot(
            timestamps, net_prices,
            color=_NET_LINE, linewidth=1.5, linestyle="--",
            label="Net after Steam fees (15%)", marker=marker, markersize=ms,
        )

        for i, batch in enumerate(batches):
            color = _BATCH_COLORS[i % len(_BATCH_COLORS)]
            buy = batch["purchase_price_eur"]
            label = f"Buy {batch['quantity']}× @ {buy:.3f} € ({batch['purchase_date']})"
            self.ax.axhline(y=buy, color=color, linestyle=":", linewidth=1.5, label=label, alpha=0.85)

        self.ax.set_title(case_name, color="#dddddd", fontsize=11, pad=6)
        self.ax.set_ylabel("Price (€)", color=_TICK_COLOR, fontsize=9)

        if len(timestamps) > 1:
            date_range = (timestamps[-1] - timestamps[0]).days
            if date_range <= 2:
                self.ax.xaxis.set_major_formatter(mdates.DateFormatter("%d.%m %H:%M"))
            elif date_range <= 60:
                self.ax.xaxis.set_major_formatter(mdates.DateFormatter("%d.%m"))
            else:
                self.ax.xaxis.set_major_formatter(mdates.DateFormatter("%m/%Y"))

        self.ax.tick_params(axis="x", rotation=25, labelsize=7)
        self.ax.tick_params(axis="y", labelsize=8)

        legend = self.ax.legend(
            fontsize=7.5, facecolor="#1e1e1e", edgecolor="#333333",
            labelcolor="#cccccc", loc="upper left",
        )

        self.canvas.draw()
