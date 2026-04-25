import sys
from unittest.mock import MagicMock

# 1. MOCK HEAVY DEPENDENCIES BEFORE IMPORTS
mock_noren = MagicMock()
sys.modules["NorenApi"] = mock_noren
sys.modules["pyotp"] = MagicMock()

import os
import datetime
import sqlite3
import pandas as pd
from unittest.mock import patch

# Store real date for instantiation
real_date = datetime.date

# Ensure project root is in path
BASE_DIR = r"d:\Dev\Codex\ThetaEdge"
sys.path.insert(0, BASE_DIR)

# CONFIG FOR SMOKE TEST
TEST_DATE = real_date(2024, 4, 18)  # Thursday
BACKTEST_DB = r"D:\Dev\option-historical_data\data\NIFTY_1MIN_OPTIONS_BACKTEST.db"
VIX_VALUE = 12.62

# 2. Setup Mock for LTP
def get_mock_ltp(exchange, symbol_or_token):
    conn = sqlite3.connect(BACKTEST_DB)
    if "Nifty" in str(symbol_or_token) or str(symbol_or_token).isdigit():
        if exchange == "NSE":
            cursor = conn.cursor()
            cursor.execute("SELECT close FROM nifty_spot_1min WHERE timestamp >= '2024-04-18 09:20:00' LIMIT 1")
            row = cursor.fetchone()
            conn.close()
            return row[0] if row else 22251.15
    
    import re
    match = re.search(r"([CP])(\d+)$", str(symbol_or_token))
    if match:
        opt_type = "CE" if match.group(1) == "C" else "PE"
        strike = float(match.group(2))
        
        cursor = conn.cursor()
        cursor.execute("""
            SELECT close FROM options_2024 
            WHERE date(timestamp) = '2024-04-18' 
            AND strike_pr = ? AND option_typ = ? 
            AND timestamp >= '2024-04-18 09:20:00' 
            LIMIT 1
        """, (strike, opt_type))
        row = cursor.fetchone()
        conn.close()
        return row[0] if row else 100.0 # fallback
        
    return 10.0

# 3. Inject mock api
mock_api = MagicMock()
mock_api.get_quotes.side_effect = lambda exchange, token: {"lp": str(get_mock_ltp(exchange, token)), "stat": "Ok"}

import shared.auth
shared.auth.api = mock_api

import shared.order_manager
import shared.market_data_fetcher
import shared.notifier

# 4. Setup the harness
@patch('shared.auth.ShoonyaAuth')
@patch('shared.order_manager.getLTP', side_effect=get_mock_ltp)
@patch('shared.order_manager.placeOrder')
@patch('shared.market_data_fetcher.fetch_morning_vix', return_value=VIX_VALUE)
@patch('shared.notifier.send_telegram_alert')
@patch('time.sleep', return_value=None)
def run_smoke_test(mock_sleep, mock_tg, mock_vix, mock_place, mock_ltp, mock_auth):
    print(f"STARTING RETROACTIVE SMOKE TEST for {TEST_DATE}")
    
    import S1_straddle.algo_strike_straddle_s1 as s1
    
    # 5. MOCK exitPosition to avoid infinite loop
    # We want it to call finalize_trade directly
    def mock_exit_pos(atmCE, atmPE, qty):
        print("\n--- Phase 3: PnL & DB Verification ---")
        ce_entry = s1.trade_context["ce_entry_price"]
        pe_entry = s1.trade_context["pe_entry_price"]
        
        # Simulate a WIN exit (30% decay)
        s1.finalize_trade(
            ce_exit=round(ce_entry * 0.7, 2), 
            pe_exit=round(pe_entry * 0.7, 2),
            ce_reason="SMOKE_PT",
            pe_reason="SMOKE_PT"
        )
    
    s1.exitPosition = mock_exit_pos
    
    # Carefully mock 'today' for the strategy
    class NewDate(real_date):
        @classmethod
        def today(cls):
            return TEST_DATE
    s1.datetime.date = NewDate
    
    # Inject our mock api into the strategy too
    s1.api = mock_api
    s1.PAPER_TRADING = 1 
    s1.trade_context["trade_date"] = TEST_DATE.strftime("%Y-%m-%d")

    print("\n--- Phase 1: Regime Lock ---")
    s1.fetch_vix_and_lock_regime()
    print(f"DONE: VIX: {s1.vix_at_entry} | Regime: {s1.regime_label}")
    
    print("\n--- Phase 2: Strike Selection ---")
    s1.findStrikePriceATM()
    
    # Verify DB write
    conn = sqlite3.connect(r"D:\Dev\Codex\ThetaEdge\S1_straddle\data\thetaedge_prod.db")
    cursor = conn.cursor()
    cursor.execute("SELECT trade_date, regime_label, ce_strike, pe_strike, net_pnl_rs, tax_charges_rs FROM trades_S1")
    row = cursor.fetchone()
    conn.close()
    
    if row:
        print("\n✅ DB VERIFICATION SUCCESSFUL")
        print(f"   Date: {row[0]} | Regime: {row[1]}")
        print(f"   CE: {row[2]} | PE: {row[3]}")
        print(f"   Net PnL: {row[4]} | Taxes: {row[5]}")
    else:
        print("\n❌ DB VERIFICATION FAILED - No record found!")
    
    print("\nDONE: SMOKE TEST HARNESS COMPLETED SUCCESSFULY")

if __name__ == "__main__":
    run_smoke_test()
