# ThetaEdge — GitHub Copilot Instructions

## Project Identity
- **Name:** ThetaEdge
- **Purpose:** Automated NIFTY options trading bot — paper trading first, live trading later
- **Broker:** Shoonya (Finvasia) — Zero brokerage
- **Instrument:** NIFTY 50 Index Options (Weekly Expiry, every Thursday)
- **Deployment:** Hetzner Linux VPS, cron-triggered at 08:45 IST on weekdays
- **Language:** Python 3.10+
- **Database:** SQLite (`thetaedge_prod.db`, `thetaedge_historical.db`)

---

## CRITICAL: What Copilot Must NEVER Change

The following are locked design decisions. Do NOT alter these under any circumstance unless the user explicitly says "override architecture decision":

1. **`RegimeConfig` is the single source of truth** for all strategy parameters.
   - ALL VIX thresholds, SL%, PT%, OTM offsets, entry times, and margin values live ONLY in `shared/regime_config.py`
   - No strategy file, config file, or scheduler should hardcode these values
   - Access via `RegimeConfig.get_config(vix)` only

2. **Portfolio-level Profit Target** — NEVER revert to leg-level PT.
   - PT fires when `(ltp_ce + ltp_pe) <= total_premium * (profit_target_pct / 100)`
   - Both legs exit simultaneously at PT

3. **Dynamic Expiry via `get_expiry_string()`** — NEVER use today's date as expiry.
   - Always call `get_expiry_string(trade_date)` from `shared/capital_manager.py`
   - Returns nearest Thursday (or Wednesday if Thursday is holiday)
   - Format: `DDMMMYY` uppercase **2-digit year** e.g. `01MAY26` — Shoonya NFO symbol format
   - **NEVER use 4-digit year** (`01MAY2026`) — Shoonya returns `None` / `-1.0` LTP for that symbol

4. **`trade_context` dict** is the canonical trade record passed to `log_trade_s1()`.
   - Do not add new DB columns without updating BOTH `trade_logger.py` schema AND `trade_context`
   - All 41 columns must be populated before `log_trade_s1()` is called

5. **Time exit is 15:30 IST** — not 15:15, not 15:00.
   - Always use `dt.time() >= datetime.time(15, 30)` for time-based exit condition
   - NEVER use `dt.minute >= 15` or `dt.minute >= 30` as standalone conditions

6. **VIX is fetched ONCE at 09:00 IST** via scheduler and ONCE at 09:15 IST inside strategy.
   - The scheduler fetch is for the morning Telegram alert
   - The strategy fetch at 09:15 is the authoritative lock for that day's regime
   - Do NOT add additional VIX fetches mid-day

7. **`PAPER_TRADING = 1` is the default** — never change this to 0 without explicit user instruction.

8. **Lot size is dynamic** — NEVER hardcode 75 anywhere except as a default fallback.
   - Always call `get_lot_size(trade_date)` from `shared/capital_manager.py`
   - Returns 50 for dates before 2024-11-20, returns 75 from 2024-11-20 onwards

---

## Folder Structure

```
ThetaEdge/                          ← Project root (open this in VS Code)
├── .github/
│   └── copilot-instructions.md     ← THIS FILE — Copilot reads this automatically
├── .thetaedge/
│   ├── ARCHITECTURE.md             ← Full system design
│   ├── PARAMETERS.md               ← All locked parameters with rationale
│   ├── KNOWN_BUGS.md               ← Active bug tracker
│   ├── prompts/
│   │   ├── fix_bugs.md             ← Prompt for bug fixes
│   │   └── add_strategy.md        ← Prompt for adding new strategies
│   └── skills/
│       └── trading_conventions.md  ← Domain knowledge for Copilot
├── shared/                         ← Shared modules (used by ALL strategies)
│   ├── regime_config.py            ← ⭐ SINGLE SOURCE OF TRUTH for parameters
│   ├── capital_manager.py          ← Lot sizing, expiry calculation, tax charges
│   ├── scheduler.py                ← Daily cron orchestrator
│   ├── auth.py                     ← Shoonya API authentication
│   ├── order_manager.py            ← placeOrder(), getLTP()
│   ├── notifier.py                 ← Telegram alerts
│   ├── trade_logger.py             ← SQLite DB writer
│   ├── market_data_fetcher.py      ← VIX fetch, OHLC data
│   └── holiday_calendar.py         ← NSE trading day checker
├── S1_straddle/                    ← Strategy S1 module
│   ├── algo_strike_straddle_s1.py  ← Core strategy execution engine
│   ├── config.py                   ← S1-specific constants (imports from shared)
│   ├── run_s1.py                   ← Production entry point
│   ├── capital_state.json          ← Live capital tracker
│   ├── logs/                       ← Daily execution logs
│   └── data/
│       ├── thetaedge_prod.db       ← Live paper trade records
│       └── thetaedge_historical.db ← Historical reference data
├── .env                            ← Secrets (never commit)
├── requirements.txt
└── README.md
```

---

## Module Responsibilities (Do Not Cross Boundaries)

| Module | Owns | Does NOT own |
|--------|------|--------------|
| `regime_config.py` | All strategy parameters | Order placement, DB writes |
| `capital_manager.py` | Lot calc, expiry, tax charges | Strategy logic, orders |
| `scheduler.py` | Daily orchestration, holiday check | Strategy parameters |
| `algo_strike_straddle_s1.py` | Trade execution loop | Parameter values (reads from RegimeConfig) |
| `trade_logger.py` | DB schema and writes | PnL calculation |
| `order_manager.py` | API order calls | Strategy decisions |

---

## Coding Standards

- All times in **IST (Asia/Kolkata)**. No UTC conversion needed — VPS is set to IST.
- All monetary values in **Indian Rupees (₹)**. No currency conversion.
- All option premiums in **points** (1 point = ₹1 × lot_size for PnL).
- Use `round(x, 2)` for all monetary and premium calculations.
- `trade_context` keys use `snake_case` strings — never change existing key names.
- Log format: `[LEVEL] Message` e.g. `[SUCCESS]`, `[ERROR]`, `[CRITICAL]`, `[MONITOR]`.
- Exceptions: always catch with `except Exception as e:` and `print(f"[ERROR] {e}")`. Never bare `except:`.

---

## Environment Variables (.env)

```
PAPER_TRADING=1
STARTING_CAPITAL=120000
MAX_LOTS_OVERRIDE=1
TELEGRAM_BOT_TOKEN=<token>
TELEGRAM_CHAT_ID=<chat_id>
SHOONYA_USER_ID=<id>
SHOONYA_API_KEY=<key>
SHOONYA_ACCESS_TOKEN=<token>
```

---

## Before Every Deploy — Run Tests First

```bash
pytest tests/ -v
```

- All 68 tests must pass before any code reaches Hetzner.
- If a fix causes any test to fail, the fix is not complete.
- **Never delete or weaken existing tests to make a fix pass — fix the code instead.**
- `test_time_exit_at_1515_must_be_false` is a permanent regression guard — do not touch it.

Current test count: **68** | Added: 2026-04-27

---

## When Copilot Suggests a Change — Checklist

Before accepting any Copilot suggestion that touches strategy logic, verify:
- [ ] Does it read parameters from `RegimeConfig`? (not hardcoded)
- [ ] Does it use `get_expiry_string()` for the option symbol? (not today's date)
- [ ] Does it use `datetime.time(15, 30)` for time exit? (not 15:15)
- [ ] Is the PT check portfolio-level? (`ltp_ce + ltp_pe <= target`, not per-leg)
- [ ] Does it call `get_lot_size(trade_date)` for quantity? (not hardcoded 75)
- [ ] Is `PAPER_TRADING` still 1?
- [ ] Does `pytest tests/ -v` still pass with 0 failures?
