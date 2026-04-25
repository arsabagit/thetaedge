import os
import sys
import time
import sqlite3
import datetime
import pandas as pd
# Add project root and shared dir to sys.path
sys.path.append("/home/algo/ThetaEdge")
sys.path.append("/home/algo/ThetaEdge/shared")
from shared.auth import ShoonyaAuth

# Config
DB_NAME = "spot_gap_recovery.db"
GAP_START = datetime.datetime(2026, 4, 1)
GAP_END = datetime.datetime(2026, 4, 5)
CHUNK_DAYS = 10
NIFTY_TOKEN = "26000"

def setup_db():
    conn = sqlite3.connect(DB_NAME)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS nifty_spot_1min (
            timestamp DATETIME PRIMARY KEY,
            open REAL,
            high REAL,
            low REAL,
            close REAL
        )
    """)
    conn.commit()
    return conn

def backfill():
    auth = ShoonyaAuth()
    api = auth.login()
    if not api:
        print("Login failed")
        return

    conn = setup_db()
    current_start = GAP_START

    while current_start < GAP_END:
        current_end = current_start + datetime.timedelta(days=CHUNK_DAYS)
        if current_end > GAP_END:
            current_end = GAP_END

        print(f"Fetching {current_start.strftime('%Y-%m-%d')} to {current_end.strftime('%Y-%m-%d')}...")
        
        try:
            res = api.get_time_price_series(
                exchange='NSE', 
                token=NIFTY_TOKEN, 
                starttime=int(current_start.timestamp()), 
                endtime=int(current_end.timestamp()),
                interval="1"
            )
            
            if res and isinstance(res, list):
                data = []
                for entry in res:
                    # Shoonya returns time as '22-04-2026 15:29:00'
                    # Or '2024-11-01 09:15:00' depending on version/token.
                    # We normalize to YYYY-MM-DD HH:MM:SS
                    ts_raw = entry['time']
                    try:
                        ts = datetime.datetime.strptime(ts_raw, "%d-%m-%Y %H:%M:%S").strftime("%Y-%m-%d %H:%M:%S")
                    except:
                        ts = datetime.datetime.strptime(ts_raw, "%Y-%m-%d %H:%M:%S").strftime("%Y-%m-%d %H:%M:%S")
                    
                    data.append((ts, float(entry['into']), float(entry['inth']), float(entry['intl']), float(entry['intc'])))
                
                conn.executemany("INSERT OR IGNORE INTO nifty_spot_1min VALUES (?, ?, ?, ?, ?)", data)
                conn.commit()
                print(f"   Saved {len(data)} records.")
            else:
                print(f"   No data found for this chunk.")
            
            # Rate limiting
            time.sleep(1)
            
        except Exception as e:
            print(f"   Error: {e}")
            time.sleep(5)
            
        current_start = current_end

    conn.close()
    print("BACKFILL COMPLETE.")

if __name__ == "__main__":
    backfill()
