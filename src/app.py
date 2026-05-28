import sys
import threading
from datetime import date, datetime
from pathlib import Path
from tkinter import messagebox

import customtkinter as ctk

from src import portfolio, steam_api
from src.chart import PriceChart

ctk.set_appearance_mode("light")
ctk.set_default_color_theme("blue")

# ── Pastel pink palette ────────────────────────────────────────────────────
_COL_WIDTHS  = [220, 105, 90, 105, 115, 105, 85]
_COL_HEADERS = ["Case Name", "Batches", "Total Qty", "Avg Buy", "Market Price", "Net Sell", "P/L"]

_BG          = "#FFF8FA"   # main window background
_CARD_BG     = "#FCE4EC"   # summary card / header strip
_ROW_EVEN    = "#FFFFFF"
_ROW_ODD     = "#FFF0F5"   # lavender blush
_ROW_SEL     = "#FFD6E7"   # selected row
_HDR_BG      = "#F8BBD0"   # column header bar
_PINK        = "#F06292"   # primary accent (buttons, highlights)
_PINK_HOVER  = "#EC407A"   # button hover
_GREEN       = "#388E3C"   # profit
_RED         = "#D32F2F"   # loss
_BLUE        = "#E91E63"   # market price (deep pink)
_NET_GREEN   = "#43A047"   # net sell
_DIM         = "#AAAAAA"   # secondary text
_TEXT        = "#2D2D2D"   # primary text

# Resolve icon path once — next to the exe when frozen, project root otherwise
_ICO = (Path(sys.executable).parent if getattr(sys, "frozen", False)
        else Path(__file__).parent.parent) / "CS2_tracker.ico"


def _apply_icon(window):
    """Set the CS2 tracker icon on any Tk/CTk window.

    CTkToplevel resets the icon via wm_iconbitmap('') at ~200 ms.
    We fire twice (350 ms and 600 ms) to survive any late resets.
    """
    if _ICO.exists():
        ico = str(_ICO)
        window.after(350, lambda: window.iconbitmap(ico))
        window.after(600, lambda: window.iconbitmap(ico))


class _AutocompleteCombo(ctk.CTkFrame):
    """Entry field that shows a filtered dropdown popup as the user types."""

    def __init__(self, master, values: list, width: int = 360, on_select=None, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self._all = list(values)
        self._on_select = on_select
        self._popup = None
        self._close_job = None

        self._var = ctk.StringVar()
        self._entry = ctk.CTkEntry(self, width=width, textvariable=self._var,
                                   placeholder_text="Type to search…")
        self._entry.pack()

        self._entry.bind("<KeyRelease>", self._on_key)
        self._entry.bind("<FocusOut>",   self._schedule_close)
        self._entry.bind("<Escape>",     lambda e: self._close())
        self._entry.bind("<Return>",     lambda e: self._close())

    # ── public interface ────────────────────────────────────────────────────
    def get(self) -> str:
        return self._var.get().strip()

    def set(self, value: str):
        self._var.set(value)

    def focus_set(self):
        self._entry.focus_set()

    # ── internal ────────────────────────────────────────────────────────────
    def _matches(self) -> list:
        typed = self._var.get().strip().lower()
        if not typed:
            return self._all
        return [v for v in self._all if typed in v.lower()]

    def _on_key(self, event):
        if event.keysym in ("Return", "Escape", "Tab"):
            return
        matches = self._matches()
        if matches:
            self._show_popup(matches)
        else:
            self._close()

    def _show_popup(self, matches: list):
        self.update_idletasks()
        x = self._entry.winfo_rootx()
        y = self._entry.winfo_rooty() + self._entry.winfo_height() + 2
        w = self._entry.winfo_width()
        row_h = 30
        h = min(len(matches) * row_h + 6, 220)

        if self._popup and self._popup.winfo_exists():
            # Reuse existing popup — just refresh its contents
            self._popup.geometry(f"{w}x{h}+{x}+{y}")
            for child in self._list_frame.winfo_children():
                child.destroy()
        else:
            import tkinter as tk
            self._popup = tk.Toplevel(self)
            self._popup.overrideredirect(True)
            self._popup.attributes("-topmost", True)
            self._popup.configure(bg="#1c1c2e")
            self._popup.geometry(f"{w}x{h}+{x}+{y}")

            outer = ctk.CTkScrollableFrame(self._popup, fg_color="#1c1c2e",
                                           scrollbar_button_color="#333355")
            outer.pack(fill="both", expand=True)
            self._list_frame = outer

        for m in matches:
            btn = ctk.CTkButton(
                self._list_frame, text=m, anchor="w", height=28,
                fg_color="transparent", hover_color="#2a2a4e",
                text_color="#dddddd", font=("Ink Free", 13, "bold"),
                command=lambda v=m: self._pick(v),
            )
            btn.pack(fill="x", padx=2, pady=1)

    def _pick(self, value: str):
        if self._close_job:
            self._entry.after_cancel(self._close_job)
            self._close_job = None
        self._var.set(value)
        self._close()
        self._entry.focus_set()
        if self._on_select:
            self._on_select(value)

    def _schedule_close(self, event=None):
        self._close_job = self._entry.after(200, self._close)

    def _close(self):
        if self._popup and self._popup.winfo_exists():
            self._popup.destroy()
        self._popup = None
        self._close_job = None


class _AddBatchDialog(ctk.CTkToplevel):
    def __init__(self, master, on_add):
        super().__init__(master)
        _apply_icon(self)
        self.title("Add Batch")
        self.geometry("420x330")
        self.resizable(False, False)
        self._on_add = on_add
        self._build()
        self.after(150, self._activate)

    def _activate(self):
        self.lift()
        self.focus_force()
        self.grab_set()

    def _build(self):
        ctk.CTkLabel(self, text="Add a new batch of cases", font=("Ink Free", 17, "bold")).pack(pady=(18, 14))

        ctk.CTkLabel(self, text="Case Name", anchor="w").pack(fill="x", padx=28)
        self.case_combo = _AutocompleteCombo(self, values=steam_api.CS2_CASES, width=360)
        self.case_combo.pack(padx=28, pady=(2, 10))

        row1 = ctk.CTkFrame(self, fg_color="transparent")
        row1.pack(fill="x", padx=28, pady=(0, 10))
        row1.columnconfigure(0, weight=1)
        row1.columnconfigure(1, weight=1)

        ctk.CTkLabel(row1, text="Quantity", anchor="w").grid(row=0, column=0, sticky="w")
        ctk.CTkLabel(row1, text="Price per case (€)", anchor="w").grid(row=0, column=1, sticky="w", padx=(12, 0))
        self.qty_entry = ctk.CTkEntry(row1, placeholder_text="e.g. 500", width=160)
        self.qty_entry.grid(row=1, column=0, sticky="ew")
        self.price_entry = ctk.CTkEntry(row1, placeholder_text="e.g. 0.19", width=160)
        self.price_entry.grid(row=1, column=1, sticky="ew", padx=(12, 0))

        ctk.CTkLabel(self, text="Purchase Date (YYYY-MM-DD)", anchor="w").pack(fill="x", padx=28)
        self.date_entry = ctk.CTkEntry(self, width=360)
        self.date_entry.insert(0, str(date.today()))
        self.date_entry.pack(padx=28, pady=(2, 0))

        ctk.CTkButton(self, text="Add Batch", command=self._submit, width=200).pack(pady=20)

    def _submit(self):
        case_name = self.case_combo.get()
        qty_raw = self.qty_entry.get().strip()
        price_raw = self.price_entry.get().strip().replace(",", ".")
        date_raw = self.date_entry.get().strip()

        if case_name not in steam_api.CS2_CASES:
            messagebox.showerror("Validation", "Please select a valid case name from the list.", parent=self)
            return
        try:
            qty = int(qty_raw)
            assert qty > 0
        except (ValueError, AssertionError):
            messagebox.showerror("Validation", "Quantity must be a positive integer.", parent=self)
            return
        try:
            price = float(price_raw)
            assert price > 0
        except (ValueError, AssertionError):
            messagebox.showerror("Validation", "Price must be a positive number (e.g. 0.19).", parent=self)
            return
        try:
            date.fromisoformat(date_raw)
        except ValueError:
            messagebox.showerror("Validation", "Date must be in YYYY-MM-DD format.", parent=self)
            return

        portfolio.add_batch(case_name, qty, price, date_raw)
        self._on_add()
        self.destroy()


class _SellDialog(ctk.CTkToplevel):
    def __init__(self, master, on_sold):
        super().__init__(master)
        _apply_icon(self)
        self.title("Record Sale")
        self.geometry("420x340")
        self.resizable(False, False)
        self._on_sold = on_sold
        self._build()
        self.after(150, self._activate)

    def _activate(self):
        self.lift()
        self.focus_force()
        self.grab_set()

    def _owned_qty(self, case_name: str) -> int:
        return sum(b["quantity"] for b in portfolio.get_batches_for_case(case_name))

    def _on_case_changed(self, value):
        qty = self._owned_qty(value)
        self._avail_lbl.configure(text=f"Available in portfolio: {qty}")

    def _build(self):
        owned = portfolio.get_cases()
        if not owned:
            ctk.CTkLabel(
                self, text="No cases in portfolio to sell.",
                text_color=_DIM, font=("Ink Free", 15, "bold"),
            ).pack(pady=60)
            return

        ctk.CTkLabel(self, text="Record a sale (price = after Steam fees)", font=("Ink Free", 17, "bold")).pack(pady=(18, 14))

        ctk.CTkLabel(self, text="Case Name", anchor="w").pack(fill="x", padx=28)
        self._avail_lbl = ctk.CTkLabel(
            self, text=f"Available in portfolio: {self._owned_qty(owned[0])}",
            font=("Ink Free", 13, "bold"), text_color=_DIM, anchor="w",
        )
        self.case_combo = _AutocompleteCombo(
            self, values=owned, width=360,
            on_select=self._on_case_changed,
        )
        self.case_combo.set(owned[0])
        self.case_combo.pack(padx=28, pady=(2, 4))
        self._avail_lbl.pack(fill="x", padx=28, pady=(0, 8))

        row1 = ctk.CTkFrame(self, fg_color="transparent")
        row1.pack(fill="x", padx=28, pady=(0, 10))
        row1.columnconfigure(0, weight=1)
        row1.columnconfigure(1, weight=1)

        ctk.CTkLabel(row1, text="Quantity sold", anchor="w").grid(row=0, column=0, sticky="w")
        ctk.CTkLabel(row1, text="Price received per case (€)", anchor="w").grid(row=0, column=1, sticky="w", padx=(12, 0))
        self.qty_entry = ctk.CTkEntry(row1, placeholder_text="e.g. 100", width=160)
        self.qty_entry.grid(row=1, column=0, sticky="ew")
        self.price_entry = ctk.CTkEntry(row1, placeholder_text="e.g. 0.27", width=160)
        self.price_entry.grid(row=1, column=1, sticky="ew", padx=(12, 0))

        ctk.CTkLabel(self, text="Sale Date (YYYY-MM-DD)", anchor="w").pack(fill="x", padx=28)
        self.date_entry = ctk.CTkEntry(self, width=360)
        self.date_entry.insert(0, str(date.today()))
        self.date_entry.pack(padx=28, pady=(2, 0))

        ctk.CTkButton(self, text="Record Sale", command=self._submit, width=200).pack(pady=18)

    def _submit(self):
        case_name = self.case_combo.get()
        qty_raw = self.qty_entry.get().strip()
        price_raw = self.price_entry.get().strip().replace(",", ".")
        date_raw = self.date_entry.get().strip()

        if case_name not in portfolio.get_cases():
            messagebox.showerror("Validation", "Please select a case from your portfolio.", parent=self)
            return
        try:
            qty = int(qty_raw)
            assert qty > 0
        except (ValueError, AssertionError):
            messagebox.showerror("Validation", "Quantity must be a positive integer.", parent=self)
            return

        available = self._owned_qty(case_name)
        if qty > available:
            messagebox.showerror(
                "Validation",
                f"You only have {available} × {case_name} in your portfolio.",
                parent=self,
            )
            return

        try:
            sell_price = float(price_raw)
            assert sell_price > 0
        except (ValueError, AssertionError):
            messagebox.showerror("Validation", "Price must be a positive number.", parent=self)
            return
        try:
            date.fromisoformat(date_raw)
        except ValueError:
            messagebox.showerror("Validation", "Date must be in YYYY-MM-DD format.", parent=self)
            return

        buy_snap = portfolio.avg_buy_price(case_name) or 0.0
        portfolio.add_sale(case_name, qty, sell_price, buy_snap, date_raw)
        portfolio.deduct_from_portfolio(case_name, qty)
        self._on_sold()
        self.destroy()


class _SalesHistoryWindow(ctk.CTkToplevel):
    _WIDTHS = [105, 195, 75, 110, 110, 110, 100, 110]
    _HEADERS = ["Date", "Case Name", "Qty", "Sell/case", "Total recv.", "Avg buy", "P/L/case", "Total P/L"]

    def __init__(self, master):
        super().__init__(master)
        _apply_icon(self)
        self.title("Sales History")
        self.geometry("1000x520")
        self.minsize(800, 380)
        self._build()
        self.after(150, self._activate)

    def _activate(self):
        self.lift()
        self.focus_force()

    def _build(self):
        self.configure(fg_color=_BG)

        # Header bar
        hdr = ctk.CTkFrame(self, fg_color="transparent")
        hdr.pack(fill="x", padx=18, pady=(14, 0))
        ctk.CTkLabel(hdr, text="Sales History", font=("Ink Free", 24, "bold"), text_color=_PINK).pack(side="left")

        # Summary bar
        summary_frame = ctk.CTkFrame(self, fg_color=_CARD_BG, corner_radius=8)
        summary_frame.pack(fill="x", padx=18, pady=(8, 0))
        self._summary_lbl = ctk.CTkLabel(
            summary_frame, text="", font=("Ink Free", 14, "bold"), text_color=_DIM,
        )
        self._summary_lbl.pack(padx=16, pady=10)

        # Column header
        col_hdr = ctk.CTkFrame(self, fg_color=_HDR_BG, corner_radius=0, height=34)
        col_hdr.pack(fill="x", padx=18, pady=(8, 0))
        col_hdr.pack_propagate(False)
        for i, (h, cw) in enumerate(zip(self._HEADERS, self._WIDTHS)):
            ctk.CTkLabel(
                col_hdr, text=h, width=cw,
                font=("Ink Free", 13, "bold"),
                text_color=_TEXT, anchor="w",
            ).pack(side="left", padx=(10 if i == 0 else 0, 0))

        # Scrollable table
        self._table = ctk.CTkScrollableFrame(self, fg_color=_ROW_EVEN, corner_radius=0)
        self._table.pack(fill="both", expand=True, padx=18, pady=(0, 14))

        self._render()

    def _render(self):
        for w in self._table.winfo_children():
            w.destroy()

        sales = portfolio.get_all_sales()
        # Sort newest first
        sales = sorted(sales, key=lambda s: s["sell_date"], reverse=True)

        if not sales:
            ctk.CTkLabel(
                self._table,
                text="No sales recorded yet. Use 'Record Sale' in the main window.",
                text_color=_DIM, font=("Ink Free", 14, "bold"),
            ).pack(pady=30)
            self._summary_lbl.configure(text="No sales yet.")
            return

        total_received = 0.0
        total_pl = 0.0

        for i, s in enumerate(sales):
            bg = _ROW_EVEN if i % 2 == 0 else _ROW_ODD
            row = ctk.CTkFrame(self._table, fg_color=bg, corner_radius=0)
            row.pack(fill="x")

            sell = s["sell_price_eur"]
            buy = s["buy_price_eur"]
            qty = s["quantity"]
            pl_case = sell - buy
            pl_total = pl_case * qty
            recv_total = sell * qty
            total_received += recv_total
            total_pl += pl_total

            sign = "+" if pl_case >= 0 else ""
            pl_color = _GREEN if pl_case >= 0 else _RED

            values = [
                s["sell_date"],
                s["case_name"],
                str(qty),
                f"{sell:.2f} €",
                f"{recv_total:.2f} €",
                f"{buy:.2f} €",
                f"{sign}{pl_case:.2f} €",
                f"{sign}{pl_total:.2f} €",
            ]
            colors = [_DIM, _TEXT, _DIM, _NET_GREEN, _NET_GREEN, _DIM, pl_color, pl_color]
            fonts = [("Ink Free", 13, "bold")] * 8

            for j, (val, col, font, cw) in enumerate(zip(values, colors, fonts, self._WIDTHS)):
                ctk.CTkLabel(
                    row, text=val, width=cw, font=font, text_color=col, anchor="w",
                ).pack(side="left", padx=(10 if j == 0 else 0, 0), pady=8)

            ctk.CTkButton(
                row, text="✕", width=32, height=26,
                fg_color=_PINK, hover_color=_PINK_HOVER, text_color="#ffffff",
                command=lambda sid=s["id"]: self._remove(sid),
            ).pack(side="right", padx=8, pady=5)

        sign = "+" if total_pl >= 0 else ""
        color = _GREEN if total_pl >= 0 else _RED
        self._summary_lbl.configure(
            text=(
                f"Total received: {total_received:.2f} €   │   "
                f"Total realised P/L: {sign}{total_pl:.2f} €"
            ),
            text_color=color,
        )

    def _remove(self, sale_id: str):
        if messagebox.askyesno("Confirm", "Remove this sale record?", parent=self):
            portfolio.remove_sale(sale_id)
            self._render()


class _BatchListDialog(ctk.CTkToplevel):
    """Shows all batches for one case and lets the user delete them."""

    def __init__(self, master, case_name: str, on_change):
        super().__init__(master)
        _apply_icon(self)
        self.title(f"Batches — {case_name}")
        self.geometry("480x360")
        self.resizable(False, True)
        self._case_name = case_name
        self._on_change = on_change
        self._build()
        self.after(150, self._activate)

    def _activate(self):
        self.lift()
        self.focus_force()
        self.grab_set()

    def _build(self):
        self.configure(fg_color=_BG)
        ctk.CTkLabel(
            self, text=self._case_name,
            font=("Ink Free", 16, "bold"), text_color=_PINK,
        ).pack(pady=(16, 6))

        self._scroll = ctk.CTkScrollableFrame(self, fg_color=_ROW_ODD)
        self._scroll.pack(fill="both", expand=True, padx=16, pady=(0, 12))
        self._render()

    def _render(self):
        for w in self._scroll.winfo_children():
            w.destroy()

        batches = portfolio.get_batches_for_case(self._case_name)
        if not batches:
            ctk.CTkLabel(self._scroll, text="No batches.", text_color=_DIM).pack(pady=20)
            return

        for b in batches:
            row = ctk.CTkFrame(self._scroll, fg_color=_CARD_BG, corner_radius=6)
            row.pack(fill="x", pady=3)

            info = (
                f"{b['quantity']}×  |  bought: {b['purchase_price_eur']:.2f} €  |  {b['purchase_date']}"
            )
            ctk.CTkLabel(row, text=info, font=("Ink Free", 13, "bold"), anchor="w", text_color=_TEXT).pack(
                side="left", padx=12, pady=8
            )
            ctk.CTkButton(
                row, text="Remove", width=72, height=28,
                fg_color=_PINK, hover_color=_PINK_HOVER, text_color="#ffffff",
                command=lambda bid=b["id"]: self._remove(bid),
            ).pack(side="right", padx=8, pady=6)

    def _remove(self, batch_id: str):
        if messagebox.askyesno("Confirm", "Remove this batch?", parent=self):
            portfolio.remove_batch(batch_id)
            self._on_change()
            self._render()


class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("CS2 Case Tracker")
        self.geometry("960x720")
        self.minsize(750, 560)

        _apply_icon(self)

        self._current_prices: dict = {}
        self._selected_case: str | None = None
        self._row_widgets: dict = {}  # case_name -> row frame

        self._build_ui()
        self._load_cached_prices()

    # ------------------------------------------------------------------ build

    def _build_ui(self):
        self.configure(fg_color=_BG)

        # ── Header ──────────────────────────────────────────────────────────
        hdr = ctk.CTkFrame(self, fg_color="transparent")
        hdr.pack(fill="x", padx=18, pady=(14, 0))

        ctk.CTkLabel(
            hdr, text="CS2 Case Tracker",
            font=("Ink Free", 26, "bold"),
            text_color=_PINK,
        ).pack(side="left")

        _btn = dict(fg_color=_PINK, hover_color=_PINK_HOVER, text_color="#ffffff")

        self._refresh_btn = ctk.CTkButton(
            hdr, text="↻  Refresh Prices", width=148,
            command=self._start_refresh, **_btn,
        )
        self._refresh_btn.pack(side="right")

        ctk.CTkButton(
            hdr, text="+ Add Batch", width=120,
            command=self._open_add_dialog, **_btn,
        ).pack(side="right", padx=(0, 8))

        ctk.CTkButton(
            hdr, text="Record Sale", width=120,
            command=self._open_sell_dialog, **_btn,
        ).pack(side="right", padx=(0, 8))

        ctk.CTkButton(
            hdr, text="Sales History", width=120,
            command=self._open_sales_history, **_btn,
        ).pack(side="right", padx=(0, 8))

        self._status_lbl = ctk.CTkLabel(
            hdr, text="", font=("Ink Free", 13, "bold"), text_color=_DIM,
        )
        self._status_lbl.pack(side="right", padx=(0, 14))

        # ── Summary bar ─────────────────────────────────────────────────────
        self._summary_frame = ctk.CTkFrame(self, fg_color=_CARD_BG, corner_radius=8)
        self._summary_frame.pack(fill="x", padx=18, pady=(10, 0))

        self._summary_lbl = ctk.CTkLabel(
            self._summary_frame,
            text="Add batches and refresh prices to see your portfolio summary.",
            font=("Ink Free", 14, "bold"), text_color=_DIM,
        )
        self._summary_lbl.pack(padx=16, pady=10)

        # ── Table header ────────────────────────────────────────────────────
        col_hdr = ctk.CTkFrame(self, fg_color=_HDR_BG, corner_radius=0, height=34)
        col_hdr.pack(fill="x", padx=18, pady=(8, 0))
        col_hdr.pack_propagate(False)

        ctk.CTkLabel(
            col_hdr, text="Actions", width=80,
            font=("Ink Free", 13, "bold"),
            text_color=_TEXT, anchor="w",
        ).pack(side="right", padx=(0, 10))

        for i, (h, cw) in enumerate(zip(_COL_HEADERS, _COL_WIDTHS)):
            ctk.CTkLabel(
                col_hdr, text=h, width=cw,
                font=("Ink Free", 13, "bold"),
                text_color=_TEXT, anchor="w",
            ).pack(side="left", padx=(10 if i == 0 else 0, 0))

        # ── Scrollable table ────────────────────────────────────────────────
        self._table = ctk.CTkScrollableFrame(
            self, fg_color=_ROW_EVEN, corner_radius=0, height=210,
        )
        self._table.pack(fill="x", padx=18)

        # ── Divider ─────────────────────────────────────────────────────────
        ctk.CTkFrame(self, height=2, fg_color=_HDR_BG, corner_radius=0).pack(
            fill="x", padx=18, pady=(6, 0)
        )

        # ── Chart section ───────────────────────────────────────────────────
        chart_hdr = ctk.CTkFrame(self, fg_color="transparent")
        chart_hdr.pack(fill="x", padx=18, pady=(8, 0))
        ctk.CTkLabel(
            chart_hdr, text="Price History",
            font=("Ink Free", 15, "bold"),
            text_color=_TEXT,
        ).pack(side="left")

        self._chart = PriceChart(self, corner_radius=8)
        self._chart.pack(fill="both", expand=True, padx=18, pady=(4, 14))

    # --------------------------------------------------------------- data

    def _load_cached_prices(self):
        history = portfolio.load_price_history()
        for case_name, snapshots in history.items():
            if snapshots:
                self._current_prices[case_name] = snapshots[-1]["price"]
        self._refresh_table()

    # --------------------------------------------------------------- table

    def _refresh_table(self):
        for w in self._table.winfo_children():
            w.destroy()
        self._row_widgets.clear()

        cases = portfolio.get_cases()
        if not cases:
            ctk.CTkLabel(
                self._table,
                text="No cases yet — click '+ Add Batch' to start tracking.",
                text_color=_DIM, font=("Ink Free", 14, "bold"),
            ).pack(pady=24)
            self._update_summary([])
            return

        for i, case_name in enumerate(cases):
            bg = _ROW_EVEN if i % 2 == 0 else _ROW_ODD
            row = ctk.CTkFrame(self._table, fg_color=bg, corner_radius=0, cursor="hand2")
            row.pack(fill="x")
            self._row_widgets[case_name] = row

            batches = portfolio.get_batches_for_case(case_name)
            total_qty = sum(b["quantity"] for b in batches)
            total_cost = sum(b["quantity"] * b["purchase_price_eur"] for b in batches)
            avg_buy = total_cost / total_qty if total_qty else 0

            current = self._current_prices.get(case_name)
            if current is not None:
                net = current * 0.85
                pl_pct = (net - avg_buy) / avg_buy * 100 if avg_buy else 0
                sign = "+" if pl_pct >= 0 else ""
                pl_color = _GREEN if pl_pct >= 0 else _RED
                cur_text = f"{current:.2f} €"
                net_text = f"{net:.2f} €"
                pl_text = f"{sign}{pl_pct:.1f}%"
            else:
                pl_color = _DIM
                cur_text = net_text = pl_text = "—"

            batch_label = f"{len(batches)} batch{'es' if len(batches) != 1 else ''}"
            values = [
                case_name, batch_label, str(total_qty),
                f"{avg_buy:.2f} €", cur_text, net_text, pl_text,
            ]
            colors = [_TEXT, _DIM, _DIM, _DIM, _BLUE, _NET_GREEN, pl_color]
            fonts = [("Ink Free", 13, "bold")] + [("Ink Free", 13, "bold")] * 6

            # Pack manage button first so it anchors to the far right
            ctk.CTkButton(
                row, text="Manage", width=72, height=26,
                fg_color=_PINK, hover_color=_PINK_HOVER,
                text_color="#ffffff", font=("Ink Free", 13, "bold"),
                command=lambda cn=case_name: self._open_batch_list(cn),
            ).pack(side="right", padx=(0, 10))

            for j, (val, col, font, cw) in enumerate(zip(values, colors, fonts, _COL_WIDTHS)):
                lbl = ctk.CTkLabel(
                    row, text=val, width=cw, font=font, text_color=col, anchor="w",
                )
                lbl.pack(side="left", padx=(10 if j == 0 else 0, 0), pady=9)
                lbl.bind("<Button-1>", lambda e, cn=case_name: self._on_row_click(cn))

            row.bind("<Button-1>", lambda e, cn=case_name: self._on_row_click(cn))

        self._update_summary(cases)
        if self._selected_case and self._selected_case in self._row_widgets:
            self._highlight_row(self._selected_case)

    def _highlight_row(self, case_name: str):
        for cn, row in self._row_widgets.items():
            row.configure(fg_color=_ROW_SEL if cn == case_name else (
                _ROW_EVEN if list(self._row_widgets).index(cn) % 2 == 0 else _ROW_ODD
            ))

    def _update_summary(self, cases: list):
        if not cases:
            self._summary_lbl.configure(
                text="Add batches and click '↻ Refresh Prices' to see your portfolio summary.",
                text_color=_DIM,
            )
            return

        total_invested = 0.0
        total_net = 0.0
        has_prices = False

        for cn in cases:
            for b in portfolio.get_batches_for_case(cn):
                total_invested += b["quantity"] * b["purchase_price_eur"]
                cur = self._current_prices.get(cn)
                if cur is not None:
                    total_net += b["quantity"] * cur * 0.85
                    has_prices = True

        if has_prices and total_invested:
            pl = total_net - total_invested
            pl_pct = pl / total_invested * 100
            sign = "+" if pl >= 0 else ""
            color = _GREEN if pl >= 0 else _RED
            text = (
                f"Invested: {total_invested:.2f} €   │   "
                f"Net value (after Steam fees): {total_net:.2f} €   │   "
                f"Total P/L: {sign}{pl:.2f} € ({sign}{pl_pct:.1f}%)"
            )
            self._summary_lbl.configure(text=text, text_color=color)
        else:
            self._summary_lbl.configure(
                text=f"Invested: {total_invested:.2f} €   │   Refresh prices to see current value.",
                text_color="#aaaaaa",
            )

    # --------------------------------------------------------------- events

    def _on_row_click(self, case_name: str):
        self._selected_case = case_name
        self._highlight_row(case_name)
        history = portfolio.load_price_history()
        batches = portfolio.get_batches_for_case(case_name)
        self._chart.update_chart(case_name, history.get(case_name, []), batches)

    def _open_add_dialog(self):
        dlg = _AddBatchDialog(self, on_add=self._refresh_table)
        dlg.focus()

    def _open_batch_list(self, case_name: str):
        def on_change():
            self._refresh_table()
        dlg = _BatchListDialog(self, case_name, on_change=on_change)
        dlg.focus()

    def _open_sell_dialog(self):
        dlg = _SellDialog(self, on_sold=self._refresh_table)
        dlg.focus()

    def _open_sales_history(self):
        win = _SalesHistoryWindow(self)
        win.focus()

    # --------------------------------------------------------------- refresh

    def _start_refresh(self):
        cases = portfolio.get_cases()
        if not cases:
            self._status_lbl.configure(text="No cases to refresh.")
            return
        self._refresh_btn.configure(state="disabled", text="Fetching…")
        self._status_lbl.configure(text="")
        t = threading.Thread(target=self._fetch_thread, args=(cases,), daemon=True)
        t.start()

    def _fetch_thread(self, cases: list):
        def progress(i: int, total: int, name: str):
            self.after(0, lambda: self._status_lbl.configure(
                text=f"Fetching {i}/{total}: {name}…"
            ))

        prices = steam_api.fetch_all_prices(cases, progress_callback=progress)

        for name, price in prices.items():
            portfolio.append_price(name, price)

        self._current_prices.update(prices)
        now = datetime.now().strftime("%H:%M:%S")

        def done():
            self._refresh_btn.configure(state="normal", text="↻  Refresh Prices")
            self._status_lbl.configure(text=f"Updated {now}")
            self._refresh_table()
            if self._selected_case:
                self._on_row_click(self._selected_case)

        self.after(0, done)
