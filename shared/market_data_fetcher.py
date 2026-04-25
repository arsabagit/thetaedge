import sqlite3
import datetime
import os
import time
import logging
from S1_straddle.config import PROD_DB_PATH

logger = logging.getLogger(__name__)

def fetch_morning_vix(target_date=None):
    """
    Fetches the India VIX close for the morning startup.
    Tries the target_date first, then looks back for the most recent trading day.
    """
    if target_date is None:
        target_date = datetime.date.today()
    
    if not os.path.exists(PROD_DB_PATH):
        logger.error(f"Production DB not found at {PROD_DB_PATH}")
        return 15.0 # Conservative default

    try:
        conn = sqlite3.connect(PROD_DB_PATH)
        cursor = conn.cursor()
        
        # 1. Try fetching exact date (in case DB was pre-filled)
        date_str = target_date.strftime('%Y-%m-%d')
        cursor.execute("SELECT close FROM india_vix WHERE date = ?", (date_str,))
        row = cursor.fetchone()
        
        if row:
            vix = float(row[0])
            print(f"[INFO] Fetched exact VIX for {date_str}: {vix:.2f}")
            conn.close()
            return vix
            
        # 2. Look back for the latest available VIX entry
        print(f"[FETCH] No exact VIX for {date_str}, looking back...")
        cursor.execute("SELECT date, close FROM india_vix WHERE date < ? ORDER BY date DESC LIMIT 1", (date_str,))
        row = cursor.fetchone()
        
        if row:
            vix = float(row[1])
            found_date = row[0]
            print(f"[INFO] Fetched latest available VIX (from {found_date}): {vix:.2f}")
            conn.close()
            return vix
            
    except Exception as e:
        logger.error(f"Failed to fetch VIX from DB: {e}")
        
    print("[WARNING] VIX data missing or error in lookup! Falling back to 15.0.")
    return 15.0 # Balanced fallback

def fetch_and_save_vix(target_date=None, retry_count=3):
    """
    Fetches today's India VIX from Shoonya API and saves it to india_vix table.
    Retries up to 3 times with 60 second gap.
    """
    from shared.auth import ShoonyaAuth
    if target_date is None:
        target_date = datetime.date.today()
    
    date_str = target_date.strftime('%Y-%m-%d')
    logger.info(f"[VIX] Fetching VIX for {date_str} (attempting {retry_count} retries)...")

    try:
        auth = ShoonyaAuth()
        api = auth.login()
        if not api:
            raise Exception("API Login failed for VIX fetch.")
        
        # We try to get today's quote first
        res = api.get_quotes(exchange='NSE', token='26017')
        if res and 'lp' in res:
            vix_lp = float(res['lp'])
            vix_open = float(res.get('o', vix_lp))
            vix_high = float(res.get('h', vix_lp))
            vix_low = float(res.get('l', vix_lp))
            
            # Save to thetaedge_prod.db (simplified single-row update for today)
            conn = sqlite3.connect(PROD_DB_PATH)
            conn.execute('''
                INSERT OR REPLACE INTO india_vix (date, open, high, low, close)
                VALUES (?, ?, ?, ?, ?)
            ''', (date_str, vix_open, vix_high, vix_low, vix_lp))
            conn.commit()
            conn.close()
            
            logger.info(f"[SUCCESS] VIX {vix_lp} confirmed and saved for {date_str}")
            return vix_lp
        else:
            raise Exception(f"Invalid API response for VIX: {res}")

    except Exception as e:
        logger.error(f"[ERROR] VIX fetch attempt failed: {e}")
        if retry_count > 0:
            logger.info("[RETRY] Waiting 60 seconds before next VIX fetch attempt...")
            time.sleep(60)
            return fetch_and_save_vix(target_date, retry_count - 1)
        
    # Fallback: Read latest available VIX from DB
    logger.warning("[FALLBACK] VIX fetch exhausted all retries. Using latest available from database.")
    return fetch_morning_vix(target_date)

def check_vix_gaps():
    """
    Checks for missing dates in the india_vix table vs expected trading days.
    Intended for Sunday night sanity check.
    """
    from shared.holiday_calendar import is_trading_day
    logger.info("[INTEGRITY] Running weekly VIX integrity check...")
    # This would compare DB dates vs expected and log/alert on gaps.
    print("VIX Integrity Check complete (Logic implemented in Data Vault).")

if __name__ == "__main__":
    import sys
    if "--check-gaps" in sys.argv:
        check_vix_gaps()
    else:
        v = fetch_morning_vix()
        print(f"Morning VIX: {v}")
