import sqlite3
import os

DB_PATH = r"d:\Dev\option-historical_data\data\NIFTY_1MIN_OPTIONS_BACKTEST.db"
LOCAL_DB_PATH = r"D:\Dev\Codex\ThetaEdge\S1_straddle\data\thetaedge_historical.db"

def check_db(path, name):
    print(f"--- Checking {name} ---")
    if not os.path.exists(path):
        print(f"File not found: {path}")
        return

    try:
        conn = sqlite3.connect(path)
        c = conn.cursor()
        
        # Check index/spot table
        # Try different table names if needed
        tables = ["nifty_spot_1min", "nifty_index_1min"]
        spot_found = False
        for t in tables:
            try:
                c.execute(f"SELECT MAX(timestamp) FROM {t} WHERE timestamp LIKE '2026%'")
                print(f"{t} Max 2026: {c.fetchone()[0]}")
                spot_found = True
                break
            except:
                continue
        
        if not spot_found:
             print("No spot table found with 2026 data.")

        # Check options table
        opt_tables = ["options_2026", "nifty_options_1min"]
        opt_found = False
        for t in opt_tables:
            try:
                c.execute(f"SELECT MAX(timestamp) FROM {t}")
                print(f"{t} Overall Max: {c.fetchone()[0]}")
                opt_found = True
                break
            except:
                continue
        
        if not opt_found:
            print("No options table found.")
            
        conn.close()
    except Exception as e:
        print(f"Error checking {name}: {e}")

check_db(DB_PATH, "MAIN BACKTEST DB")
check_db(LOCAL_DB_PATH, "LOCAL THETAEDGE DB")
