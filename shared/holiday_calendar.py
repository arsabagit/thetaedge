import datetime
from datetime import date, timedelta
import logging
import sys
import argparse

try:
    from jugaad_data.holidays import holidays
    JUGAAD_AVAILABLE = True
except ImportError:
    JUGAAD_AVAILABLE = False

logger = logging.getLogger(__name__)

# NSE 2026 Trading Holidays (Verified from circular NSE/CMTR/71775)
NSE_HOLIDAYS_2026 = [
    '2026-01-26', # Republic Day
    '2026-02-26', # Mahashivratri
    '2026-03-25', # Holi
    '2026-04-02', # Ram Navami
    '2026-04-14', # Dr. Ambedkar Jayanti
    '2026-05-01', # Maharashtra Day
    '2026-08-15', # Independence Day
    '2026-08-27', # Ganesh Chaturthi
    '2026-10-02', # Gandhi Jayanti
    '2026-10-20', # Diwali Laxmi Pujan (Tentative)
    '2026-10-21', # Diwali Balipratipada (Tentative)
    '2026-11-04', # Gurunanak Jayanti
    '2026-12-25', # Christmas
]

def get_nse_holidays_dynamic(year):
    """Fetches NSE holidays dynamically using jugaad-data."""
    if not JUGAAD_AVAILABLE:
        return []
        
    try:
        h_data = holidays(year)
        dynamic_list = []
        for h in h_data:
            if 'tradingDate' in h:
                try:
                    dt = datetime.datetime.strptime(h['tradingDate'], '%d-%b-%Y').strftime('%Y-%m-%d')
                    dynamic_list.append(dt)
                except ValueError:
                    pass
        return dynamic_list
    except Exception as e:
        logger.error(f"Failed to fetch dynamic holidays: {e}")
        return []

def is_trading_day(target_date=None):
    """Checks if a given date is a trading day (not weekend, not holiday)."""
    if target_date is None:
        target_date = date.today()
    
    if isinstance(target_date, datetime.datetime):
        target_date = target_date.date()
        
    # 1. Weekend Check
    if target_date.weekday() >= 5: # 5=Sat, 6=Sun
        return False
    
    # 2. Hardcoded Holiday Check
    date_str = target_date.strftime('%Y-%m-%d')
    if date_str in NSE_HOLIDAYS_2026:
        return False
        
    return True

def get_next_trading_day(start_date=None):
    """Returns the next valid trading day from the given date."""
    if start_date is None:
        start_date = date.today()
        
    current = start_date + timedelta(days=1)
    while not is_trading_day(current):
        current += timedelta(days=1)
    return current

def run_sanity_check():
    """Compares hardcoded list with jugaad-data dynamic fetcher."""
    print("--- ThetaEdge Holiday Sanity Check ---")
    today = date.today()
    year = today.year
    
    dynamic = get_nse_holidays_dynamic(year)
    if not dynamic:
        print("[WARNING] Could not fetch dynamic holidays. Sanity check skipped.")
        return

    hardcoded = NSE_HOLIDAYS_2026
    
    mismatches = []
    # Check if any dynamic holidays are missing from hardcoded
    for d_date in dynamic:
        if d_date.startswith(str(year)) and d_date not in hardcoded:
            mismatches.append(f"MISSING in Hardcoded: {d_date}")
            
    # Check if any hardcoded holidays are missing from dynamic
    for h_date in hardcoded:
        if h_date.startswith(str(year)) and h_date not in dynamic:
            mismatches.append(f"MISSING in Dynamic: {h_date}")

    if mismatches:
        print("[CRITICAL] Holiday Mismatches Found!")
        for m in mismatches:
            print(f"  - {m}")
        # In a real scenario, this would trigger a Telegram alert
        from shared.notifier import send_telegram_alert
        send_telegram_alert(f"⚠️ Holiday Mismatch Detected!\nYear: {year}\n" + "\n".join(mismatches))
    else:
        print("[SUCCESS] Holiday lists are in sync.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--sanity-check", action="store_true")
    args = parser.parse_args()
    
    if args.sanity_check:
        run_sanity_check()
    else:
        print(f"Today ({date.today()}) is trading day: {is_trading_day()}")
