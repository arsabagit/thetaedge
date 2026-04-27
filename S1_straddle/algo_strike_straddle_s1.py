import shared.auth as auth
from shared.capital_manager import (
    calculateLots, load_capital, save_capital, get_lot_size, 
    calculate_total_charges, get_expiry_string
)
from shared.order_manager import placeOrder, getLTP
from shared.notifier import send_telegram_alert
from shared.trade_logger import log_trade_s1
from S1_straddle.config import *
import time
import datetime
import pandas as pd
import sys
import os
import sqlite3

# ─── Auth Startup Validation ────────────────────────────────────────────────
# initialize_api() validates (or retries) the session established at import time.
# Exits immediately if auth failed — prevents silent order failures downstream.
_api = auth.initialize_api()
if _api is None:
    print("[CRITICAL] Shoonya authentication failed at startup — exiting")
    sys.exit(1)
print("[INFO] Shoonya API authenticated successfully")
# ────────────────────────────────────────────────────────────────────────────

# ==========================================
# Strategy S1: Global Trade State
# ==========================================
trade_context = {
    "trade_date": datetime.date.today().strftime("%Y-%m-%d"),
    "strategy": "S1",
    "paper_trading": PAPER_TRADING,
    "exit_type": "PENDING"
}

# Regime Parameters (Dynamically set at 09:15 AM)
entryHour = 9
entryMinute = 20
entrySecond = 0
startTime = datetime.time(entryHour, entryMinute, entrySecond)

stock = "NIFTY"
otm = 0          
SL_percentage = 50
profit_target_pct = 50
regime_label = "PENDING"
vix_at_entry = 0.0
margin_per_lot = 110000 

ce_entry_price = 0.0
pe_entry_price = 0.0
ceSL = 0.0
peSL = 0.0
atm_strike = 0
nifty_spot = 0.0

clients = [
    {
        "broker": "shoonya",
        "userID": "",
        "apiKey": "",
        "accessToken": "",
        "qty": 75  
    }
]

def update_strategy_qty():
    """Wrapper for centralized calculateLots"""
    global clients, margin_per_lot
    capital_data = load_capital(CAPITAL_FILE)
    trade_context["capital_before"] = capital_data.get("current_capital", STARTING_CAPITAL)
    
    lots, final_qty = calculateLots(
        current_capital=trade_context["capital_before"],
        margin_per_lot=margin_per_lot,
        max_lots_override=MAX_LOTS_OVERRIDE
    )
    
    clients[0]['qty'] = final_qty
    trade_context["lots_traded"] = lots
    trade_context["qty"] = final_qty
    trade_context["lot_size"] = get_lot_size(datetime.date.today())
    print(f"[SUCCESS] Position Sizes Calculated: {lots} lots | Qty: {final_qty}")

def findStrikePriceATM():
    print(" Placing Orders ")
    name = "Nifty 50" if stock == "NIFTY" else "Nifty Bank"
    
    trade_date_obj = datetime.datetime.strptime(trade_context["trade_date"], "%Y-%m-%d").date()
    from shared.capital_manager import get_expiry_string
    expiry_str = get_expiry_string(trade_date_obj)

    ltp = float(getLTP("NSE",name))
    if ltp == -1.0:
        print("[CRITICAL] Could not fetch Spot LTP. Entry aborted.")
        return

    trade_context["nifty_spot"] = ltp
    if stock == "BANKNIFTY":
        closest_Strike = int(round((ltp / 100),0) * 100)
    else:
        closest_Strike = int(round((ltp / 50),0) * 50)

    trade_context["atm_strike"] = closest_Strike
    print("closest strike:", closest_Strike)
    
    closest_Strike_CE = closest_Strike + otm
    closest_Strike_PE = closest_Strike - otm
    trade_context["ce_strike"] = closest_Strike_CE
    trade_context["pe_strike"] = closest_Strike_PE

    atmCE = f"{STOCK}{expiry_str}C{closest_Strike_CE}"
    atmPE = f"{STOCK}{expiry_str}P{closest_Strike_PE}"

    takeEntry(atmCE, atmPE)

def takeEntry(atmCE, atmPE):
    global ce_entry_price, pe_entry_price, ceSL, peSL
    ce_entry_price = float(getLTP("NFO",atmCE))
    pe_entry_price = float(getLTP("NFO",atmPE))
    
    if ce_entry_price <= 0 or pe_entry_price <= 0:
        print(f"[ERROR] Invalid option prices. Aborting.")
        return

    trade_context["ce_entry_price"] = ce_entry_price
    trade_context["pe_entry_price"] = pe_entry_price
    trade_context["ce_entry_time"] = datetime.datetime.now().strftime("%H:%M:%S")
    trade_context["pe_entry_time"] = datetime.datetime.now().strftime("%H:%M:%S")
    trade_context["total_premium"] = round(ce_entry_price + pe_entry_price, 2)

    # Dynamic SL
    ceSL = round(ce_entry_price + (ce_entry_price * SL_percentage / 100), 2)
    peSL = round(pe_entry_price + (pe_entry_price * SL_percentage / 100), 2)
    trade_context["ce_sl_level"] = ceSL
    trade_context["pe_sl_level"] = peSL
    
    # Profit Target Level (Combined)
    trade_context["ce_pt_level"] = round(ce_entry_price * (profit_target_pct / 100), 2)
    trade_context["pe_pt_level"] = round(pe_entry_price * (profit_target_pct / 100), 2)

    qty = clients[0]['qty']
    print("\n============_Placing_Trades_=====================")
    placeOrder(atmCE, "SELL", qty, "MARKET", 0, "regular")
    placeOrder(atmPE, "SELL", qty, "MARKET", 0, "regular")
    print(f"Entry Executed | CE: {atmCE}@{ce_entry_price} (SL {ceSL}) | PE: {atmPE}@{pe_entry_price} (SL {peSL}) | Qty: {qty}")

    exitPosition(atmCE, atmPE, qty)

def exitPosition(atmCE, atmPE, qty):
    global ce_entry_price, pe_entry_price, ceSL, peSL
    
    profit_target_value = trade_context["total_premium"] * (profit_target_pct / 100)
    print(f"Profit Target: Exit when combined < {profit_target_value:.2f}")
    
    ce_exit_price, pe_exit_price = 0.0, 0.0
    ce_exit_reason, pe_exit_reason = "PENDING", "PENDING"
    
    traded = "No"
    while traded == "No":
        dt = datetime.datetime.now()
        try:
            ltp_ce = float(getLTP("NFO", atmCE))
            ltp_pe = float(getLTP("NFO", atmPE))

            # Combined Profit Target check
            if (ltp_ce + ltp_pe) <= profit_target_value:
                print(f"PROFIT TARGET REACHED: {ltp_ce+ltp_pe:.2f}")
                placeOrder(atmCE, "BUY", qty, "MARKET", 0, "regular")
                placeOrder(atmPE, "BUY", qty, "MARKET", 0, "regular")
                ce_exit_price, pe_exit_price = ltp_ce, ltp_pe
                ce_exit_reason, pe_exit_reason = "PROFIT_TARGET", "PROFIT_TARGET"
                trade_context["exit_type"] = "BOTH_PT"
                traded = "Close"
                continue

            # Individual SL / Time checks
            if (ltp_ce > ceSL or dt.time() >= datetime.time(15, 30)):
                placeOrder(atmCE, "BUY", qty, "MARKET", 0, "regular")
                ce_exit_price = ltp_ce
                ce_exit_reason = "TIME_EXIT" if dt.time() >= datetime.time(15, 30) else "SL_HIT"
                traded = "CE"
            elif (ltp_pe > peSL or dt.time() >= datetime.time(15, 30)):
                placeOrder(atmPE, "BUY", qty, "MARKET", 0, "regular")
                pe_exit_price = ltp_pe
                pe_exit_reason = "TIME_EXIT" if dt.time() >= datetime.time(15, 30) else "SL_HIT"
                traded = "PE"
            else:
                time.sleep(1)
        except: time.sleep(1)

    # Leg Recovery / Trailing Logic
    if traded == "CE":
        while traded == "CE":
            dt = datetime.datetime.now()
            ltp_pe = float(getLTP("NFO", atmPE))
            if ltp_pe <= (pe_entry_price * 0.30) or dt.time() >= datetime.time(15, 30) or ltp_pe > pe_entry_price:
                placeOrder(atmPE, "BUY", qty, "MARKET", 0, "regular")
                pe_exit_price = ltp_pe
                pe_exit_reason = "TRAILING_EXIT" if ltp_pe <= (pe_entry_price * 0.3) else ("TIME_EXIT" if dt.time() >= datetime.time(15, 30) else "SL_HIT")
                traded = "Close"
                trade_context["exit_type"] = "ONE_SL_ONE_PT" if "PROFIT" in pe_exit_reason else "BOTH_SL"
            time.sleep(1)
    elif traded == "PE":
        while traded == "PE":
            dt = datetime.datetime.now()
            ltp_ce = float(getLTP("NFO", atmCE))
            if ltp_ce <= (ce_entry_price * 0.30) or dt.time() >= datetime.time(15, 30) or ltp_ce > ce_entry_price:
                placeOrder(atmCE, "BUY", qty, "MARKET", 0, "regular")
                ce_exit_price = ltp_ce
                ce_exit_reason = "TRAILING_EXIT" if ltp_ce <= (ce_entry_price * 0.3) else ("TIME_EXIT" if dt.time() >= datetime.time(15, 30) else "SL_HIT")
                traded = "Close"
                trade_context["exit_type"] = "ONE_SL_ONE_PT" if "PROFIT" in ce_exit_reason else "BOTH_SL"
            time.sleep(1)

    finalize_trade(ce_exit_price, pe_exit_price, ce_exit_reason, pe_exit_reason)

def finalize_trade(ce_exit, pe_exit, ce_reason, pe_reason):
    trade_context["ce_exit_price"] = ce_exit
    trade_context["pe_exit_price"] = pe_exit
    trade_context["ce_exit_time"] = datetime.datetime.now().strftime("%H:%M:%S")
    trade_context["pe_exit_time"] = datetime.datetime.now().strftime("%H:%M:%S")
    trade_context["ce_exit_reason"] = ce_reason
    trade_context["pe_exit_reason"] = pe_reason
    
    trade_context["ce_pnl_pts"] = round(ce_entry_price - ce_exit, 2)
    trade_context["pe_pnl_pts"] = round(pe_entry_price - pe_exit, 2)
    trade_context["total_pnl_pts"] = round(trade_context["ce_pnl_pts"] + trade_context["pe_pnl_pts"], 2)
    trade_context["total_pnl_rs"] = round(trade_context["total_pnl_pts"] * trade_context["qty"], 2)
    trade_context["gross_pnl_rs"] = trade_context["total_pnl_rs"]
    
    # Calculate Tax Charges
    charges = calculate_total_charges(
        qty=trade_context["qty"],
        ce_entry=ce_entry_price, ce_exit=ce_exit,
        pe_entry=pe_entry_price, pe_exit=pe_exit
    )
    trade_context["tax_charges_rs"] = charges["tax_charges_rs"]
    trade_context["net_pnl_rs"] = round(trade_context["gross_pnl_rs"] - trade_context["tax_charges_rs"], 2)
    
    # Update Capital
    trade_context["capital_after"] = trade_context["capital_before"] + trade_context["net_pnl_rs"]
    save_capital({"current_capital": trade_context["capital_after"], "starting_capital": STARTING_CAPITAL}, CAPITAL_FILE)
    
    # Result Classification
    trade_context["trade_result"] = "WIN" if trade_context["net_pnl_rs"] > 0 else ("LOSS" if trade_context["net_pnl_rs"] < -100 else "BREAKEVEN")
    
    # FINAL PRODUCTION LOGGING
    log_trade_s1(trade_context)
    
    print(f"\n[DONE] Strategy 1 finished. Net PnL: Rs.{trade_context['net_pnl_rs']}")
    send_telegram_alert(f"🏁 <b>S1 {regime_label} Finished</b>\nNet PnL: Rs. {trade_context['net_pnl_rs']}\nResult: {trade_context['trade_result']}")

def fetch_vix_and_lock_regime():
    global entryHour, entryMinute, otm, SL_percentage, profit_target_pct, regime_label, vix_at_entry, margin_per_lot, startTime
    from shared.market_data_fetcher import fetch_morning_vix
    
    vix_at_entry = fetch_morning_vix()
    trade_context["vix_at_entry"] = vix_at_entry
    
    config = RegimeConfig.get_config(vix_at_entry)
    regime_label = config["label"]
    trade_context["regime_label"] = regime_label
    
    otm = config["otm"]
    SL_percentage = config["sl_pct"]
    profit_target_pct = config["profit_target_pct"]
    margin_per_lot = config["margin_per_lot"]
    
    trade_context["config_sl_pct"] = SL_percentage
    trade_context["config_pt_pct"] = profit_target_pct
    trade_context["config_otm"] = otm
    
    entryHour, entryMinute = map(int, config["entry_time"].split(':'))
    startTime = datetime.time(entryHour, entryMinute, 0)
    update_strategy_qty()

def checkTime_tofindStrike():
    print(f"[MONITOR] S1 Monitoring Started. Time: {datetime.datetime.now()}")
    vix_fetched = False
    while True:
        dt = datetime.datetime.now()
        if dt.hour == 9 and dt.minute == 15 and not vix_fetched:
            fetch_vix_and_lock_regime()
            vix_fetched = True
            
        if vix_fetched and dt.time() >= startTime:
            findStrikePriceATM()
            break
        time.sleep(1)

if __name__ == "__main__":
    checkTime_tofindStrike()
