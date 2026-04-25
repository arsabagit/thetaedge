# ThetaEdge — System Architecture

## Overview

ThetaEdge is a modular, regime-adaptive NIFTY options trading system. It sells OTM straddles daily, adjusting strike distances, stop-losses, and profit targets based on the prevailing India VIX regime detected each morning.

---

## Execution Flow (Daily)

```
08:45 IST  ─── Hetzner cron triggers run_s1.py
               │
               └─► shared/scheduler.py::run_scheduler()
                          │
09:00 IST          ├─► morning_startup()
                   │      ├─ is_trading_day() check → holiday? exit cleanly
                   │      ├─ fetch_and_save_vix() → get today's India VIX
                   │      ├─ RegimeConfig.get_config(vix) → lock regime
                   │      ├─ send_telegram_alert() → morning briefing
                   │      └─► subprocess.Popen(algo_strike_straddle_s1.py)
                   │                │
                   │       09:15    ├─ fetch_vix_and_lock_regime()
                   │                │    ├─ Re-fetch VIX (authoritative lock)
                   │                │    ├─ Set: otm, SL_pct, PT_pct, entry_time
                   │                │    └─ update_strategy_qty() → calculateLots()
                   │                │
                   │       09:20/25 ├─ findStrikePriceATM()
                   │                │    ├─ getLTP("NSE", "Nifty 50") → spot price
                   │                │    ├─ Round to nearest 50 → ATM strike
                   │                │    ├─ CE = ATM + otm, PE = ATM - otm
                   │                │    ├─ get_expiry_string() → symbol expiry
                   │                │    └─► takeEntry(atmCE, atmPE)
                   │                │
                   │                ├─ takeEntry()
                   │                │    ├─ getLTP for CE and PE premiums
                   │                │    ├─ Calculate dynamic SL levels
                   │                │    │    CE_SL = ce_entry × (1 + SL_pct/100)
                   │                │    │    PE_SL = pe_entry × (1 + SL_pct/100)
                   │                │    ├─ Calculate combined PT level
                   │                │    │    PT_value = (ce+pe) × PT_pct/100
                   │                │    ├─ placeOrder(CE, SELL, qty, MARKET)
                   │                │    ├─ placeOrder(PE, SELL, qty, MARKET)
                   │                │    └─► exitPosition()
                   │                │
                   │                └─ exitPosition() ── MONITORING LOOP ──
                   │                     ├─ Every 1 second: getLTP(CE), getLTP(PE)
                   │                     ├─ CHECK 1: Portfolio PT
                   │                     │    if (ce+pe) <= PT_value → exit both
                   │                     ├─ CHECK 2: CE SL
                   │                     │    if ce_ltp > CE_SL → exit CE
                   │                     │    → enter CE-leg-lost recovery loop
                   │                     ├─ CHECK 3: PE SL
                   │                     │    if pe_ltp > PE_SL → exit PE
                   │                     │    → enter PE-leg-lost recovery loop
                   │                     ├─ CHECK 4: Time exit
                   │                     │    if time >= 15:30 → exit remaining
                   │                     └─► finalize_trade()
                   │                              ├─ Calculate PnL points + Rs
                   │                              ├─ calculate_total_charges()
                   │                              ├─ save_capital() → JSON
                   │                              ├─ log_trade_s1() → SQLite
                   │                              └─ send_telegram_alert() → summary
                   │
15:30 IST          └─► market_close_check() → evening Telegram alert
```

---

## Regime Logic

VIX is fetched from NSE/Shoonya at 09:00 and 09:15 IST. The 09:15 fetch is authoritative.

```
VIX < 16.5  →  LOW_VIX_MODE  (Config B)
VIX >= 16.5 →  HIGH_VIX_MODE (Config A)
```

**Why 16.5?** Backtested on 2017–2024 data (2,183 trades). Threshold of 16.5 maximises the Sharpe Ratio of the split strategy vs any other threshold from 13–22. Validated in `vix_threshold_results.csv`.

---

## Profit Target Design

**Portfolio-level PT** — the single most important design decision.

```python
profit_target_value = total_premium * (profit_target_pct / 100)
# Exit when combined LTP decays to this level
if (ltp_ce + ltp_pe) <= profit_target_value:
    # Exit both legs simultaneously
```

**Why portfolio-level?** Leg-level PT is gameable by IV crush on one side while the other expands. Portfolio-level PT captures the true combined theta decay regardless of directional movement in individual legs.

---

## Leg Recovery Logic (One SL Hit)

When ONE leg hits its SL, the surviving leg is monitored with two exit conditions:
1. **Recovery PT:** `ltp <= entry_price × 0.30` (30% of entry = deep theta decay)
2. **Breakeven SL:** `ltp > entry_price` (moved back above entry = stop the bleeding)
3. **Time exit:** `time >= 15:30`

This avoids the classic mistake of riding a winning leg into a reversal after the hedge is gone.

---

## Capital Management

- **Starting Capital:** ₹1,20,000 (configurable via `.env`)
- **Margin per lot:** ₹1,10,000 (HIGH VIX) / ₹97,500 (LOW VIX)
- **Max lots override:** 1 (configurable via `.env`) — prevents runaway scaling
- **Lot sizing formula:** `floor(capital / margin_per_lot)`, minimum 1 lot
- **Compounding:** Disabled by default. Each trade uses fixed lot count.

---

## Tax & Charges Model (Shoonya — Zero Brokerage)

Per leg per trade:
| Charge | Rate | Applied On |
|--------|------|-----------|
| Brokerage | ₹0 | — |
| STT | 0.1% | Sell premium only |
| Exchange (NSE) | 0.053% | Total turnover |
| SEBI | 0.0001% | Total turnover |
| GST | 18% | Exchange + SEBI charges |
| Stamp Duty | 0.003% | Buy premium only |

---

## Database Schema (trades_S1 table)

41 columns per trade record. Key columns:

| Column | Type | Source |
|--------|------|--------|
| `trade_date` | TEXT | System date |
| `vix_at_entry` | REAL | `fetch_morning_vix()` |
| `regime_label` | TEXT | `RegimeConfig.get_config()` |
| `config_sl_pct` | REAL | `RegimeConfig` |
| `config_pt_pct` | REAL | `RegimeConfig` |
| `config_otm` | INT | `RegimeConfig` |
| `nifty_spot` | REAL | `getLTP("NSE", "Nifty 50")` |
| `atm_strike` | INT | Rounded to nearest 50 |
| `ce_strike` / `pe_strike` | INT | ATM ± otm |
| `ce_entry_price` / `pe_entry_price` | REAL | `getLTP("NFO", symbol)` |
| `ce_sl_level` / `pe_sl_level` | REAL | entry × (1 + SL_pct/100) |
| `total_premium` | REAL | ce_entry + pe_entry |
| `ce_exit_price` / `pe_exit_price` | REAL | Exit LTP |
| `ce_exit_reason` / `pe_exit_reason` | TEXT | SL_HIT/PROFIT_TARGET/TIME_EXIT |
| `exit_type` | TEXT | BOTH_PT/BOTH_SL/ONE_SL_ONE_PT |
| `gross_pnl_rs` | REAL | PnL points × qty |
| `tax_charges_rs` | REAL | `calculate_total_charges()` |
| `net_pnl_rs` | REAL | gross − charges |
| `capital_before` / `capital_after` | REAL | `capital_state.json` |
| `trade_result` | TEXT | WIN/LOSS/BREAKEVEN |
| `paper_trading` | INT | 1=paper, 0=live |
