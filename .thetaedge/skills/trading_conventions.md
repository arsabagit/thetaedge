# ThetaEdge — Trading Domain Knowledge for Copilot

This file teaches Copilot the trading-specific conventions used in this codebase.

---

## NIFTY Options Basics

- **NIFTY** = NSE Nifty 50 Index. Current value ~24,000–25,000 points (April 2026)
- **Strike interval:** 50 points (e.g., 24450, 24500, 24550)
- **ATM strike:** Nearest 50-point multiple to current spot price
- **CE (Call):** Right to BUY. We SELL CE → profit if market stays flat or falls
- **PE (Put):** Right to SELL. We SELL PE → profit if market stays flat or rises
- **Straddle:** SELL ATM CE + SELL ATM PE at same strike
- **Strangle:** SELL OTM CE + SELL OTM PE at different strikes (our strategy)
- **Premium:** The price of an option contract (in points). We SELL to collect premium.
- **Weekly expiry:** Every Thursday. Last trading day of that week's contracts.

---

## Strategy S1 in Plain English

Each trading day:
1. Check India VIX at 09:15
2. If VIX >= 16.5 → sell CE at ATM+100, sell PE at ATM-100 at 09:25
3. If VIX < 16.5 → sell CE at ATM+150, sell PE at ATM-150 at 09:20
4. Monitor combined premium (CE_ltp + PE_ltp)
5. Exit if combined premium decays to target (we keep the difference as profit)
6. Exit individual leg if it exceeds its SL level
7. Force exit all at 15:30

**We make money when:** Market stays in a range and options decay (theta).
**We lose money when:** Market makes a big move in either direction.

---

## Shoonya API Conventions

### Symbol Format
```
NIFTY{DDMMMYYYY}{C/P}{STRIKE}
Examples:
  NIFTY01MAY2026C24500   ← NIFTY Call, expiry 01 May 2026, strike 24500
  NIFTY01MAY2026P24100   ← NIFTY Put,  expiry 01 May 2026, strike 24100
```

### getLTP(exchange, symbol) returns
- For NSE spot: `getLTP("NSE", "Nifty 50")` → float (current NIFTY level)
- For NFO options: `getLTP("NFO", "NIFTY01MAY2026C24500")` → float (option premium)
- Returns `-1.0` on failure → always check before using

### placeOrder(symbol, action, qty, order_type, price, product)
```python
placeOrder("NIFTY01MAY2026C24500", "SELL", 75, "MARKET", 0, "regular")
placeOrder("NIFTY01MAY2026C24500", "BUY",  75, "MARKET", 0, "regular")
```
- `PAPER_TRADING=1` → logs the order but does NOT send to exchange

---

## PnL Calculation

```python
# Per leg (points)
ce_pnl_pts = ce_entry_price - ce_exit_price   # Positive = profit (we sold high, bought low)
pe_pnl_pts = pe_entry_price - pe_exit_price

# Total in Rupees
total_pnl_rs = (ce_pnl_pts + pe_pnl_pts) * qty
# e.g., (15.0 + 10.0) pts × 75 qty = ₹1,875

# After charges
net_pnl_rs = total_pnl_rs - tax_charges_rs
```

---

## India VIX Conventions

- **India VIX** = NSE Volatility Index. Measures expected 30-day volatility of NIFTY.
- Normal range: 10–20. Crisis range: 20–50+.
- VIX < 13 → very low premium, thin edge
- VIX 13–16.5 → LOW_VIX_MODE
- VIX 16.5–25 → HIGH_VIX_MODE (best for this strategy)
- VIX > 25 → extreme risk, consider not trading
- Fetched via `fetch_morning_vix()` from Shoonya/NSE data feed

---

## Trade Result Classification

```python
if net_pnl_rs > 0:     trade_result = "WIN"
elif net_pnl_rs < -100: trade_result = "LOSS"      # -100 threshold for breakeven zone
else:                   trade_result = "BREAKEVEN"
```

---

## Exit Type Classification

| exit_type | Meaning |
|-----------|---------|
| `BOTH_PT` | Both legs exited at portfolio profit target |
| `BOTH_SL` | Both legs hit their stop-losses |
| `ONE_SL_ONE_PT` | One leg hit SL, surviving leg hit recovery profit |
| `TIME_EXIT` | Forced exit at 15:30 |
| `MIXED` | Combination of time and SL/PT exits |

---

## Lot Size History (NSE Official Changes)

| Effective Date | NIFTY Lot Size |
|----------------|---------------|
| Before 2024-11-20 | 50 units |
| 2024-11-20 onwards | 75 units |

This affects all historical backtesting. Always use `get_lot_size(trade_date)`.
