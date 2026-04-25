# ThetaEdge — Known Bugs & Fix Tracker

> Last Updated: 2026-04-25
> Status: 3 bugs identified in code audit. Not yet fixed.

---

## 🔴 BUG-001 — Scheduler Does Not Launch Strategy [CRITICAL]

| Field              | Detail                          |
| ------------------ | ------------------------------- |
| **File**     | `shared/scheduler.py`         |
| **Function** | `morning_startup()`           |
| **Severity** | CRITICAL — strategy never runs |
| **Status**   | OPEN                            |

**Problem:** `morning_startup()` fetches VIX, sends Telegram alert, then returns `True` — but never starts `algo_strike_straddle_s1.py`. The strategy process is never spawned.

**Fix:** After `send_telegram_alert(msg)` in `morning_startup()`, add:

```python
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOG_FILE = os.path.join(BASE_DIR, "S1_straddle", "logs", "s1_cron.log")
strategy_script = os.path.join(BASE_DIR, "S1_straddle", "algo_strike_straddle_s1.py")
os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
with open(LOG_FILE, "a") as log:
    subprocess.Popen([sys.executable, strategy_script], stdout=log, stderr=log)
print(f"[LAUNCHED] Strategy process started: {strategy_script}")
```

---

## 🔴 BUG-002 — Wrong Expiry Date in Option Symbol [CRITICAL]

| Field              | Detail                                     |
| ------------------ | ------------------------------------------ |
| **File**     | `S1_straddle/algo_strike_straddle_s1.py` |
| **Function** | `findStrikePriceATM()`                   |
| **Severity** | CRITICAL — builds invalid option symbols  |
| **Status**   | OPEN                                       |

**Problem:** Uses today's date as expiry:

```python
expiry_str_2d = trade_date_obj.strftime("%d%b%y").upper()  # e.g. "28APR26"
atmCE = f"{STOCK}{expiry_str_2d}C{closest_Strike_CE}"       # WRONG symbol
```

On Monday April 28, this builds `NIFTY28APR26C24000` which does not exist. Correct expiry is `01MAY2026`.

**Fix:** Replace with:

```python
from shared.capital_manager import get_expiry_string
expiry_str = get_expiry_string(trade_date_obj)   # Returns "01MAY2026"
atmCE = f"{STOCK}{expiry_str}C{closest_Strike_CE}"
atmPE = f"{STOCK}{expiry_str}P{closest_Strike_PE}"
```

---

## 🔴 BUG-003 — Time Exit Fires at 15:15 Instead of 15:30

| Field              | Detail                                            |
| ------------------ | ------------------------------------------------- |
| **File**     | `S1_straddle/algo_strike_straddle_s1.py`        |
| **Function** | `exitPosition()` (4 locations)                  |
| **Severity** | HIGH — exits 15 minutes early, loses theta decay |
| **Status**   | OPEN                                              |

**Problem:** `dt.minute >= 15` is True at 15:15, 15:20, 15:25, AND 15:30:

```python
if (ltp_ce > ceSL or (dt.hour >= 15 and dt.minute >= 15)):  # Fires at 15:15!
```

**Fix:** Replace ALL 4 occurrences in `exitPosition()` with:

```python
if (ltp_ce > ceSL or dt.time() >= datetime.time(15, 30)):
```

Occurrences:

1. CE SL check in main monitoring loop
2. PE SL check in main monitoring loop
3. Time check in CE recovery loop
4. Time check in PE recovery loop

---

## ⚠️ WARNING-001 — Capital Buffer Not Applied

| Field              | Detail                                            |
| ------------------ | ------------------------------------------------- |
| **File**     | `shared/capital_manager.py`                     |
| **Function** | `calculateLots()`                               |
| **Severity** | WARNING — safe for paper trading, risky pre-live |
| **Status**   | MONITOR                                           |

**Problem:** `buffer_pct=30` parameter is defined but commented as "not used currently". With ₹1,20,000 capital and ₹1,10,000 margin, only ₹10,000 buffer remains.

**Pre-live fix:** Apply buffer before going live:

```python
usable_capital = current_capital * (1 - buffer_pct / 100)  # Keep 30% as buffer
lots = math.floor(usable_capital / margin_per_lot)
```

---

## ✅ RESOLVED BUGS (History)

| Bug ID  | Description                                              | Resolved   |
| ------- | -------------------------------------------------------- | ---------- |
| BUG-000 | `NameError: expiry not defined` in symbol construction | 2026-04-22 |
| BUG-001 | Scheduler not launching strateg                          | 2026-04-25 |
| BUG-002 | Wrong expiry date in option symbol                       | 2026-04-25 |
| BUG-003 | Time exit firing at 15:15 instead of 15:30               | 2026-04-25 |
