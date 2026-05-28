import json
import sys
import uuid
from datetime import datetime
from pathlib import Path


def _app_dir() -> Path:
    # When frozen by PyInstaller sys.executable is the .exe itself
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).parent.parent


_DATA_DIR = _app_dir() / "data"
_PORTFOLIO_FILE = _DATA_DIR / "portfolio.json"
_PORTFOLIO_BACKUP = _DATA_DIR / "portfolio.backup.json"
_HISTORY_FILE = _DATA_DIR / "price_history.json"
_SALES_FILE = _DATA_DIR / "sales.json"


def _ensure_data_dir():
    _DATA_DIR.mkdir(exist_ok=True)


def load_portfolio() -> dict:
    _ensure_data_dir()
    if not _PORTFOLIO_FILE.exists():
        return {"batches": []}
    with open(_PORTFOLIO_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_portfolio(data: dict):
    _ensure_data_dir()
    # Keep one backup of the previous state before every write
    if _PORTFOLIO_FILE.exists():
        import shutil
        shutil.copy2(_PORTFOLIO_FILE, _PORTFOLIO_BACKUP)
    with open(_PORTFOLIO_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def add_batch(case_name: str, quantity: int, purchase_price: float, purchase_date: str) -> dict:
    data = load_portfolio()
    batch = {
        "id": str(uuid.uuid4()),
        "case_name": case_name,
        "quantity": quantity,
        "purchase_price_eur": purchase_price,
        "purchase_date": purchase_date,
    }
    data["batches"].append(batch)
    save_portfolio(data)
    return batch


def remove_batch(batch_id: str):
    data = load_portfolio()
    data["batches"] = [b for b in data["batches"] if b["id"] != batch_id]
    save_portfolio(data)


def get_cases() -> list:
    data = load_portfolio()
    seen: list = []
    for b in data["batches"]:
        if b["case_name"] not in seen:
            seen.append(b["case_name"])
    return seen


def get_batches_for_case(case_name: str) -> list:
    data = load_portfolio()
    return [b for b in data["batches"] if b["case_name"] == case_name]


def load_price_history() -> dict:
    _ensure_data_dir()
    if not _HISTORY_FILE.exists():
        return {}
    with open(_HISTORY_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def deduct_from_portfolio(case_name: str, quantity: int):
    """Remove `quantity` units from the portfolio using FIFO (oldest purchase date first)."""
    data = load_portfolio()
    case_batches = sorted(
        [b for b in data["batches"] if b["case_name"] == case_name],
        key=lambda b: b["purchase_date"],
    )
    other_batches = [b for b in data["batches"] if b["case_name"] != case_name]

    remaining = quantity
    kept = []
    for b in case_batches:
        if remaining <= 0:
            kept.append(b)
        elif b["quantity"] <= remaining:
            remaining -= b["quantity"]
            # batch fully consumed — drop it
        else:
            updated = dict(b)
            updated["quantity"] -= remaining
            remaining = 0
            kept.append(updated)

    data["batches"] = other_batches + kept
    save_portfolio(data)


def avg_buy_price(case_name: str) -> float | None:
    """Weighted average purchase price across all batches for a case, or None if not in portfolio."""
    batches = get_batches_for_case(case_name)
    if not batches:
        return None
    total_qty = sum(b["quantity"] for b in batches)
    total_cost = sum(b["quantity"] * b["purchase_price_eur"] for b in batches)
    return total_cost / total_qty if total_qty else None


def load_sales() -> dict:
    _ensure_data_dir()
    if not _SALES_FILE.exists():
        return {"sales": []}
    with open(_SALES_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_sales(data: dict):
    _ensure_data_dir()
    with open(_SALES_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def add_sale(case_name: str, quantity: int, sell_price: float, buy_price_snapshot: float, sell_date: str) -> dict:
    """Record a completed sale.  buy_price_snapshot is the avg buy price at time of sale."""
    data = load_sales()
    sale = {
        "id": str(uuid.uuid4()),
        "case_name": case_name,
        "quantity": quantity,
        "sell_price_eur": sell_price,
        "buy_price_eur": buy_price_snapshot,
        "sell_date": sell_date,
    }
    data["sales"].append(sale)
    save_sales(data)
    return sale


def remove_sale(sale_id: str):
    data = load_sales()
    data["sales"] = [s for s in data["sales"] if s["id"] != sale_id]
    save_sales(data)


def get_all_sales() -> list:
    return load_sales()["sales"]


def append_price(case_name: str, price: float):
    _ensure_data_dir()
    history = load_price_history()
    if case_name not in history:
        history[case_name] = []
    history[case_name].append({
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "price": round(price, 4),
    })
    with open(_HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, indent=2, ensure_ascii=False)
