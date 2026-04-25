# ThetaEdge — NIFTY Options Algo Trading System

> **Status:** Paper Trading 🟡 | Live Trading 🔴 (not yet enabled)
> **Deployment:** Hetzner VPS | Broker: Shoonya (Finvasia) | Instrument: NIFTY 50 Weekly Options

---

## Strategies

| ID | Name | Type | VIX Mode | Status |
|----|------|------|----------|--------|
| S1 | Regime-Adaptive NIFTY Strangle | Short OTM Strangle | Dual-regime | 🟡 Paper Trading |

### S1 — Parameter Reference

| Regime | Condition | Entry | OTM Offset | Stop-Loss | Profit Target | Margin/Lot |
|--------|-----------|-------|-----------|-----------|---------------|------------|
| HIGH_VIX_MODE | VIX ≥ 16.5 | 09:25 IST | 100 pts | 40% of premium | 70% combined decay | ₹1,10,000 |
| LOW_VIX_MODE  | VIX < 16.5 | 09:20 IST | 150 pts | 25% of premium | 30% combined decay | ₹97,500   |

> ⚠️ All parameters are locked in `shared/regime_config.py`. Do NOT hardcode these values in strategy files.

---

## Project Structure

```
ThetaEdge/
├── .github/
│   └── copilot-instructions.md     ← Copilot rules and locked design decisions
├── .thetaedge/
│   ├── ARCHITECTURE.md             ← Full system design and execution flow
│   ├── PARAMETERS.md               ← All locked parameters with rationale
│   ├── KNOWN_BUGS.md               ← Active bug tracker
│   ├── prompts/                    ← Reusable Copilot prompt templates
│   └── skills/
│       └── trading_conventions.md  ← Trading domain knowledge for Copilot
├── shared/                         ← Shared modules used by ALL strategies
│   ├── regime_config.py            ← ⭐ Single source of truth for all parameters
│   ├── capital_manager.py          ← Lot sizing, expiry, tax charges
│   ├── scheduler.py                ← Daily cron orchestrator
│   ├── auth.py                     ← Shoonya API authentication
│   ├── order_manager.py            ← placeOrder(), getLTP()
│   ├── notifier.py                 ← Telegram alerts
│   ├── trade_logger.py             ← SQLite DB writer
│   ├── market_data_fetcher.py      ← VIX fetch, OHLC data
│   └── holiday_calendar.py         ← NSE trading day checker
├── S1_straddle/                    ← Strategy S1 module
│   ├── algo_strike_straddle_s1.py  ← Core execution engine
│   ├── config.py                   ← S1 runtime config (reads from .env)
│   ├── run_s1.py                   ← Production entry point
│   ├── capital_state.json          ← Live capital tracker
│   ├── logs/                       ← Daily execution logs
│   └── data/
│       ├── thetaedge_prod.db       ← Live trade records (SQLite)
│       └── thetaedge_historical.db ← Historical reference data
├── deploy/                         ← Hetzner deployment scripts
├── .env                            ← Secrets — NEVER commit this file
├── .env.example                    ← Template for .env setup
├── requirements.txt
└── README.md                       ← This file
```

---

## Setup

### 1. Clone and install dependencies
```bash
git clone https://github.com/YOUR_USERNAME/ThetaEdge.git
cd ThetaEdge
pip install -r requirements.txt
```

### 2. Configure environment
```bash
cp .env.example .env
# Edit .env with your credentials
```

Required `.env` values:
```
PAPER_TRADING=1
STARTING_CAPITAL=120000
MAX_LOTS_OVERRIDE=1
TELEGRAM_BOT_TOKEN=your_token
TELEGRAM_CHAT_ID=your_chat_id
SHOONYA_USER_ID=your_user_id
SHOONYA_API_KEY=your_api_key
SHOONYA_ACCESS_TOKEN=your_token
```

### 3. Run in paper trading mode
```bash
# Always confirm PAPER_TRADING=1 in .env before running
python S1_straddle/run_s1.py
```

> ⚠️ `run_s1.py` starts the scheduler. The strategy auto-launches at 09:00 IST on trading days.
> Do NOT run `algo_strike_straddle_s1.py` directly in production — always use `run_s1.py`.

---

## Daily Execution Flow

```
08:45 IST  Hetzner cron starts run_s1.py
09:00 IST  Scheduler fetches VIX, checks holiday, sends Telegram morning alert
           → Launches algo_strike_straddle_s1.py as subprocess
09:15 IST  Strategy locks VIX regime (HIGH or LOW)
09:20/25   Strike selection, order placement
09:20–15:30 Position monitoring loop (PT / SL / Recovery)
15:30 IST  Force exit all open legs
           → PnL calculated, DB logged, Telegram summary sent
```

---

## Maintenance

| Task | Command / Location |
|------|--------------------|
| View daily logs | `S1_straddle/logs/s1_cron.log` |
| Check trade DB | `sqlite3 S1_straddle/data/thetaedge_prod.db "SELECT * FROM trades_S1 ORDER BY trade_date DESC LIMIT 5;"` |
| Manual capital update | Edit `S1_straddle/capital_state.json` |
| Check open bugs | `.thetaedge/KNOWN_BUGS.md` |
| Review architecture | `.thetaedge/ARCHITECTURE.md` |

---

## Known Open Issues

> See `.thetaedge/KNOWN_BUGS.md` for full details.

| ID | Severity | File | Issue |
|----|----------|------|-------|
| BUG-001 | 🔴 Critical | `shared/scheduler.py` | Strategy not launched from scheduler |
| BUG-002 | 🔴 Critical | `S1_straddle/algo_strike_straddle_s1.py` | Wrong expiry date in option symbol |
| BUG-003 | 🟠 High | `S1_straddle/algo_strike_straddle_s1.py` | Time exit fires at 15:15 instead of 15:30 |
| WARN-001 | 🟡 Medium | `shared/capital_manager.py` | Capital buffer not applied in lot sizing |

---

## Backtested Performance Reference (S1 — 2017 to 2024)

| Year | Net PnL | Net ROI | Trades |
|------|---------|---------|--------|
| 2017 | ₹18,459 | 9.23% | 245 |
| 2018 | ₹30,943 | 15.47% | 220 |
| 2019 | ₹28,549 | 14.27% | 218 |
| 2020 | ₹85,782 | 42.89% | 249 |
| 2021 | ₹82,668 | 41.33% | 246 |
| 2022 | ₹27,553 | 13.78% | 247 |
| 2023 | ₹11,786 | 5.89% | 245 |
| 2024 | ₹23,524 | 11.76% | 173 |

- **Initial Capital:** ₹2,00,000 | **Sharpe Ratio:** 1.44 | **Max Drawdown:** 7.57%
- Backtesting project is maintained separately — do not merge backtest code into this repo.

---

## Before Going Live

- [ ] All 3 open critical bugs resolved
- [ ] Smoke test passes on paper trading for minimum 10 consecutive trading days
- [ ] Telegram alerts verified on mobile
- [ ] DB records verified via SQLite query
- [ ] `.env` reviewed: `PAPER_TRADING=1` confirmed
- [ ] Hetzner cron verified: `crontab -l` shows correct 08:45 entry
- [ ] Change `PAPER_TRADING=0` only after all above are checked

---

## Contributing / Modifying

> Before making any code change, read `.github/copilot-instructions.md` and `.thetaedge/ARCHITECTURE.md`.

- All strategy parameters must remain in `shared/regime_config.py`
- Do not change VIX threshold (16.5) without re-running full backtests
- Do not change PT logic from portfolio-level to leg-level
- Do not hardcode expiry dates — always use `get_expiry_string()`
- Document any parameter changes in `.thetaedge/PARAMETERS.md`
