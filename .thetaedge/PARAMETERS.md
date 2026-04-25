# ThetaEdge — Locked Parameters & Rationale

> ⚠️ These parameters are LOCKED. They are derived from backtesting 2,183 trades
> across 2017–2024 on 1-minute NIFTY option data. Do not change without re-running
> full backtests and updating this document with new evidence.

---

## VIX Threshold

| Parameter | Value | Location |
|-----------|-------|----------|
| `VIX_THRESHOLD` | **16.5** | `shared/regime_config.py` |

**Rationale:** Tested every 0.5-step threshold from 13.0 to 22.0. VIX=16.5 produced the highest blended Sharpe Ratio (1.44) across all years. Below 16.0 → too many HIGH_VIX days in 2023 that hurt performance. Above 17.0 → misses the volatility premium window.

---

## Regime A — HIGH_VIX_MODE (VIX >= 16.5)

| Parameter | Value | Rationale |
|-----------|-------|-----------|
| Entry Time | **09:25 IST** | Extra 5 min for volatile open to settle |
| OTM Offset | **100 pts** | Closer strikes capture higher premium when IV is elevated |
| SL % | **40%** | Wider SL to survive IV spikes at open |
| Profit Target % | **70%** | Higher PT because premiums are large enough to justify |
| Margin/Lot | **₹1,10,000** | NSE margin requirement increases with IV |

**When active:** Budget weeks, RBI policy days, global risk-off events, VIX > 16.5

---

## Regime B — LOW_VIX_MODE (VIX < 16.5)

| Parameter | Value | Rationale |
|-----------|-------|-----------|
| Entry Time | **09:20 IST** | Market settles faster in low-vol environments |
| OTM Offset | **150 pts** | Farther strikes needed — premiums are thin, need safety margin |
| SL % | **25%** | Tight SL — premium is small, losses must be contained |
| Profit Target % | **30%** | Lower PT — thin premiums decay faster in % terms |
| Margin/Lot | **₹97,500** | Slightly lower margin in calm markets |

**When active:** Trending low-vol markets (2023-style), pre-election calm, VIX < 16.5

---

## Exit Time

| Parameter | Value | Rationale |
|-----------|-------|-----------|
| Time Exit | **15:30 IST** | Last 30 min has highest theta decay; holding until 15:30 captures it |

**Implementation:** `dt.time() >= datetime.time(15, 30)` — NOT `dt.minute >= 30`

---

## Lot Size Pivots

| Date Range | Lot Size | NSE Change Date |
|------------|----------|-----------------|
| Before 2024-11-20 | **50** | Original NIFTY lot size |
| From 2024-11-20 | **75** | NSE revised effective Nov 20, 2024 |

**Implementation:** `get_lot_size(trade_date)` in `shared/capital_manager.py`

---

## Expiry Symbol Format

| Exchange | Format | Example |
|----------|--------|---------|
| Shoonya NFO | `{STOCK}{DDMMMYYYY}{C/P}{STRIKE}` | `NIFTY01MAY2026C24500` |

**Implementation:** `get_expiry_string(trade_date)` returns `"01MAY2026"` (nearest Thursday)

---

## Recovery Profit Trigger (Surviving Leg)

| Parameter | Value | Rationale |
|-----------|-------|-----------|
| Recovery PT level | **30% of entry price** | If surviving leg decays to 30%, theta has done its job |
| Recovery SL level | **entry price (breakeven)** | If it moves above entry, cut the loss at zero |

---

## Capital Defaults

| Parameter | Default | Env Override |
|-----------|---------|-------------|
| Starting Capital | ₹1,20,000 | `STARTING_CAPITAL` |
| Max Lots | 1 | `MAX_LOTS_OVERRIDE` |
| Paper Trading | 1 (ON) | `PAPER_TRADING` |

---

## Backtested Performance Reference (Benchmark)

These are the ORIGINAL benchmark results from the initial strategy validation.
Any code change must be verified against these numbers.

| Year | Gross PnL | Net PnL | Trades | Net ROI |
|------|-----------|---------|--------|---------|
| 2017 | ₹26,370 | ₹18,459 | 245 | 9.23% |
| 2018 | ₹44,205 | ₹30,943 | 220 | 15.47% |
| 2019 | ₹40,785 | ₹28,549 | 218 | 14.27% |
| 2020 | ₹1,22,546 | ₹85,782 | 249 | 42.89% |
| 2021 | ₹1,18,097 | ₹82,668 | 246 | 41.33% |
| 2022 | ₹39,362 | ₹27,553 | 247 | 13.78% |
| 2023 | ₹16,837 | ₹11,786 | 245 | 5.89% |
| 2024 | ₹33,606 | ₹23,524 | 173 | 11.76% |

**Average Annual ROI (2017–2024):** ~19.3%
**Sharpe Ratio (VIX-adaptive version):** 1.44
**Max Drawdown:** 7.57%
