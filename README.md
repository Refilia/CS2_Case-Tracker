# CS2 Case Tracker

A desktop application to track your CS2 case inventory on the Steam Market. Monitor current prices, record purchases and sales, and view price history charts — all with Steam fees automatically accounted for.

---

## Features

- **Portfolio tracking** — add cases in batches with quantity, buy price, and date
- **Live Steam prices** — fetches the current lowest/median market price for each case
- **Steam fee aware** — all P/L figures are shown after the 15% Steam Market fee (10% CS2 + 5% Steam)
- **Price history chart** — click any case row to see a price chart over time with your buy price marked
- **Sales tracking** — record sales and view your realised profit/loss history
- **Persistent data** — everything is saved locally in JSON files and survives restarts
- **Searchable dropdowns** — type to filter the case list when adding batches or recording sales

---

## Installation

### Option A — Run the .exe (Windows, no Python required)

1. Go to the [Releases](../../releases) page and download `CS2 Case Tracker.exe`
2. Place the `.exe` and the `CS2_tracker.ico` file in the same folder
3. Double-click `CS2 Case Tracker.exe` to launch

> **Note:** On first launch the app takes 10–15 seconds to start while it unpacks itself. Subsequent launches are faster.  
> A `data\` folder will be created automatically next to the exe — this is where your portfolio is stored. Keep it alongside the exe.

---

### Option B — Run from source (Windows / Mac / Linux)

#### Requirements

- Python 3.11 or newer
- pip

#### Steps

1. **Clone the repository**
   ```bash
   git clone https://github.com/Refilia/CS2_Case-Tracker.git
   cd CS2_Case-Tracker
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Run the app**
   ```bash
   python main.py
   ```

---

### Option C — Build the .exe yourself

1. Complete Option B steps first
2. Install PyInstaller:
   ```bash
   pip install pyinstaller
   ```
3. Build:
   ```bash
   pyinstaller --onefile --windowed --name "CS2 Case Tracker" --icon "CS2_tracker.ico" --collect-data customtkinter --collect-data matplotlib --collect-data PIL main.py
   ```
4. The exe will be at `dist\CS2 Case Tracker.exe`
5. Copy your `CS2_tracker.ico` into the `dist\` folder alongside the exe

---

## Usage

| Action | How |
|---|---|
| Add cases | Click **+ Add Batch** — select case, enter quantity, buy price per case, and date |
| Multiple batches | Add the same case multiple times with different prices/dates |
| Refresh prices | Click **↻ Refresh Prices** — fetches live Steam Market prices (allow ~1.5 s per case) |
| View chart | Click any row in the table to see the price history chart below |
| Manage / remove batches | Click the **Manage** button on any row |
| Record a sale | Click **Record Sale** — quantity is automatically deducted from your portfolio (FIFO) |
| View sales history | Click **Sales History** |

---

## Data storage

All data is saved in a `data\` folder next to the exe (or next to `main.py` when running from source):

| File | Contents |
|---|---|
| `portfolio.json` | Your case batches (quantity, buy price, date) |
| `portfolio.backup.json` | Automatic backup of the previous portfolio state |
| `price_history.json` | Timestamped price snapshots for each case |
| `sales.json` | Recorded sales history |

---

## Tech stack

- [customtkinter](https://github.com/TomSchimansky/CustomTkinter) — modern dark-themed UI
- [matplotlib](https://matplotlib.org/) — embedded price history charts
- [requests](https://docs.python-requests.org/) — Steam Market API calls
- [PyInstaller](https://pyinstaller.org/) — packaging into a standalone exe
