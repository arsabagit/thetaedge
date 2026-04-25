import json
import os
import math
import datetime

def load_capital(filepath="S1_straddle/capital_state.json"):
    """Loads capital state from a JSON file."""
    if not os.path.exists(filepath):
        # Default fallback
        return {
            "starting_capital": 120000,
            "current_capital": 120000,
            "paper_trading_mode": True,
            "max_lots_override": 1
        }
    with open(filepath, 'r') as f:
        return json.load(f)

def save_capital(data, filepath="S1_straddle/capital_state.json"):
    """Saves capital state to a JSON file."""
    data["last_updated"] = datetime.date.today().strftime("%Y-%m-%d")
    with open(filepath, 'w') as f:
        json.dump(data, f, indent=2)

def get_lot_size(trade_date):
    """
    Returns NSE Nifty lot size standard:
    - 50 for dates before 2024-11-20
    - 75 for dates from 2024-11-20 onwards
    """
    pivot_date = datetime.date(2024, 11, 20)
    if isinstance(trade_date, str):
        trade_date = datetime.datetime.strptime(trade_date, "%Y-%m-%d").date()
    
    if trade_date < pivot_date:
        return 50
    return 75

def calculateLots(current_capital, margin_per_lot, buffer_pct=30, max_lots_override=None):
    """
    Calculates quantity based on available capital and margin requirements.
    buffer_pct: Percentage of capital to keep as a buffer (not used for calculation currently)
    """
    # Simple compounding logic: floor(capital / margin_per_lot)
    lots = math.floor(current_capital / margin_per_lot)
    lots = max(1, lots) # Minimum 1 lot
    
    if max_lots_override is not None:
        lots = min(lots, max_lots_override)
        
    lot_size = get_lot_size(datetime.date.today())
    return lots, lots * lot_size

def calculate_tax_charges(qty: int, entry_price: float, 
                           exit_price: float) -> dict:
    """
    Calculate all taxes and charges for ONE options leg (CE or PE).
    Shoonya = Zero brokerage broker.
    Based on NSE standard rates for Index Options (NIFTY).
    
    Args:
        qty: number of units (lot_size × number_of_lots), e.g. 75
        entry_price: premium at which option was SOLD (open)
        exit_price:  premium at which option was BOUGHT back (close)
    
    Returns:
        dict with individual charge components + total
    """
    
    # Turnover = total value of both sides of trade
    turnover = (entry_price + exit_price) * qty
    
    # Brokerage: Shoonya = ₹0 for options
    brokerage = 0.0
    
    # STT: 0.1% on SELL premium only (we SELL to open)
    stt = round(entry_price * qty * 0.001, 2)
    
    # NSE Exchange Transaction Charges: 0.053% of turnover
    exchange_charges = round(turnover * 0.00053, 2)
    
    # SEBI Turnover Charges: ₹10 per crore = 0.0001% of turnover
    sebi_charges = round(turnover * 0.000001, 2)
    
    # GST: 18% on (brokerage + exchange + sebi)
    gst = round((brokerage + exchange_charges + sebi_charges) * 0.18, 2)
    
    # Stamp Duty: 0.003% on BUY side only (we BUY to close)
    stamp_duty = round(exit_price * qty * 0.00003, 2)
    
    total = round(
        brokerage + stt + exchange_charges + 
        sebi_charges + gst + stamp_duty, 2
    )
    
    return {
        "brokerage":        brokerage,
        "stt":              stt,
        "exchange_charges": exchange_charges,
        "sebi_charges":     sebi_charges,
        "gst":              gst,
        "stamp_duty":       stamp_duty,
        "total_charges":    total
    }


def calculate_total_charges(qty: int,
                             ce_entry: float, ce_exit: float,
                             pe_entry: float, pe_exit: float) -> dict:
    """
    Calculate combined charges for BOTH legs of the strangle.
    Call this once per trade to get tax_charges_rs for DB.
    
    Args:
        qty:      units per leg (lot_size × lots), e.g. 75
        ce_entry: CE sell price
        ce_exit:  CE buy-back price
        pe_entry: PE sell price  
        pe_exit:  PE buy-back price
    
    Returns:
        dict with per-leg breakdown + combined total
    """
    ce_charges = calculate_tax_charges(qty, ce_entry, ce_exit)
    pe_charges = calculate_tax_charges(qty, pe_entry, pe_exit)
    
    combined_total = round(
        ce_charges["total_charges"] + pe_charges["total_charges"], 2
    )
    
    return {
        "ce_charges":        ce_charges,          # full breakdown
        "pe_charges":        pe_charges,           # full breakdown
        "tax_charges_rs":    combined_total,       # → goes into DB column
        "ce_total":          ce_charges["total_charges"],
        "pe_total":          pe_charges["total_charges"]
    }


from datetime import date, timedelta

def get_current_expiry(trade_date: date = None) -> date:
    """
    Returns the nearest upcoming NIFTY weekly expiry (Thursday).
    If today IS Thursday, returns today (same-day expiry).
    If Thursday has passed this week, returns next Thursday.
    
    NIFTY weekly expiry = every Thursday.
    If Thursday is a market holiday, expiry moves to Wednesday.
    
    Args:
        trade_date: date to calculate from. Defaults to today.
    
    Returns:
        date object of the nearest expiry
    """
    if trade_date is None:
        trade_date = date.today()
    
    # Thursday = weekday 3
    days_until_thursday = (3 - trade_date.weekday()) % 7
    nearest_thursday = trade_date + timedelta(days=days_until_thursday)
    
    # If that Thursday is a holiday, move to Wednesday
    from shared.holiday_calendar import is_trading_day
    if not is_trading_day(nearest_thursday):
        nearest_thursday = nearest_thursday - timedelta(days=1)
    
    return nearest_thursday


def get_expiry_string(trade_date: date = None) -> str:
    """
    Returns expiry as formatted string for Shoonya API symbol.
    Format: DDMMMYYYY uppercase e.g. "24APR2026"
    
    Args:
        trade_date: date to calculate from. Defaults to today.
    
    Returns:
        string like "24APR2026"
    """
    expiry_date = get_current_expiry(trade_date)
    return expiry_date.strftime("%d%b%Y").upper()


def get_monthly_expiry(trade_date: date = None) -> date:
    """
    Returns the last Thursday of the current month (monthly expiry).
    Used for data vault collection of monthly contracts.
    
    Args:
        trade_date: date to calculate from. Defaults to today.
    
    Returns:
        date object of monthly expiry
    """
    if trade_date is None:
        trade_date = date.today()
    
    # Find last day of month
    if trade_date.month == 12:
        last_day = date(trade_date.year + 1, 1, 1) - timedelta(days=1)
    else:
        last_day = date(trade_date.year, trade_date.month + 1, 1) - timedelta(days=1)
    
    # Find last Thursday
    days_back = (last_day.weekday() - 3) % 7
    last_thursday = last_day - timedelta(days=days_back)
    
    return last_thursday
