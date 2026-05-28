import time
import requests

_MARKET_URL = (
    "https://steamcommunity.com/market/priceoverview/"
    "?appid=730&currency=3&market_hash_name={name}"
)

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}

# Steam Market fees for CS2: 5% Steam fee + 10% CS2 publisher fee = 15% total
STEAM_FEE = 0.15
NET_MULTIPLIER = 1 - STEAM_FEE

CS2_CASES = sorted([
    "Gallery Case",
    "Kilowatt Case",
    "Revolution Case",
    "Recoil Case",
    "Dreams & Nightmares Case",
    "Operation Riptide Case",
    "Snakebite Case",
    "Fracture Case",
    "Operation Broken Fang Case",
    "Prisma 2 Case",
    "CS20 Case",
    "Shattered Web Case",
    "Danger Zone Case",
    "Prisma Case",
    "Horizon Case",
    "Clutch Case",
    "Spectrum 2 Case",
    "Operation Hydra Case",
    "Spectrum Case",
    "Glove Case",
    "Gamma 2 Case",
    "Gamma Case",
    "Chroma 3 Case",
    "Operation Wildfire Case",
    "Revolver Case",
    "Shadow Case",
    "Falchion Case",
    "Chroma 2 Case",
    "Chroma Case",
    "Operation Vanguard Weapon Case",
    "Huntsman Weapon Case",
    "Operation Breakout Weapon Case",
    "Operation Phoenix Weapon Case",
    "Winter Offensive Weapon Case",
    "CS:GO Weapon Case 3",
    "CS:GO Weapon Case 2",
    "CS:GO Weapon Case",
    "eSports 2014 Summer Case",
    "eSports 2013 Winter Case",
    "eSports 2013 Case",
    "Nightmare Case",
])


def _parse_eur(raw: str) -> float:
    """Parse Steam's EUR price string to float.

    Steam sometimes returns a garbled currency symbol (e.g. � instead of €),
    so we strip everything that isn't a digit, comma, or period first.
    """
    import re
    s = re.sub(r"[^\d,.]", "", raw).strip()
    if not s:
        raise ValueError(f"unparseable price: {raw!r}")
    if "." in s and "," in s:
        if s.rindex(".") < s.rindex(","):
            # European thousands: 1.234,56
            s = s.replace(".", "").replace(",", ".")
        else:
            # English thousands: 1,234.56
            s = s.replace(",", "")
    elif "," in s:
        s = s.replace(",", ".")
    return float(s)


def fetch_price(case_name: str) -> float | None:
    """Return the current Steam Market price in EUR, or None on failure.

    Prefers lowest_price; falls back to median_price if lowest_price is absent
    (Steam omits lowest_price for some items when no buy-now listings exist).
    """
    try:
        url = _MARKET_URL.format(name=requests.utils.quote(case_name))
        resp = requests.get(url, headers=_HEADERS, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        if not data.get("success"):
            return None
        raw = data.get("lowest_price") or data.get("median_price", "")
        if not raw:
            return None
        return _parse_eur(raw)
    except Exception:
        return None


def fetch_all_prices(case_names: list, progress_callback=None) -> dict:
    """Fetch prices for all case_names with a delay to respect Steam rate limits."""
    results: dict = {}
    for i, name in enumerate(case_names):
        if progress_callback:
            progress_callback(i + 1, len(case_names), name)
        price = fetch_price(name)
        if price is not None:
            results[name] = price
        if i < len(case_names) - 1:
            time.sleep(1.5)
    return results
