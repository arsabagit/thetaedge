import pandas as pd
import sqlite3
import os
import re
from datetime import datetime

# Paths
DB_PATH = r"d:\Dev\option-historical_data\data\NIFTY_1MIN_OPTIONS_BACKTEST.db"
NEW_DATA_DIR = r"d:\Dev\option-historical_data\new"

def parse_option_symbol(symbol):
    """
    Parses NIFTY symbols like NIFTY21APR26C24500
    Returns (expiry_dt, strike_pr, option_typ)
    """
    if not symbol or "NIFTY" not in symbol:
        return None, None, None
    
    # Extract parts using regex
    # Format: NIFTY DDMMMYY [C/P] Strike
    match = re.search(r"NIFTY(\d{2}[A-Z]{3}\d{2})([CP])(\d+)", symbol)
    if match:
        expiry_str = match.group(1) # e.g. 21APR26
        opt_char = match.group(2)   # e.g. C
        strike = float(match.group(3))
        
        try:
            # Normalize expiry to YYYY-MM-DD
            expiry_dt = datetime.strptime(expiry_str, "%d%b%y").strftime("%Y-%m-%d")
        except:
            expiry_dt = None
            
        opt_typ = "CE" if opt_char == "C" else "PE"
        return expiry_dt, strike, opt_typ
    return None, None, None

def ingest_dataframe_to_table(df, table_name, conn, unique_cols):
    """Safely ingests a dataframe using a temporary table and INSERT OR IGNORE."""
    temp_table = f"temp_{table_name}"
    df.to_sql(temp_table, conn, if_exists='replace', index=False)
    
    col_str = ", ".join(df.columns)
    
    query = f"""
    INSERT OR IGNORE INTO {table_name} ({col_str})
    SELECT {col_str} FROM {temp_table}
    """
    conn.execute(query)
    conn.execute(f"DROP TABLE {temp_table}")
    print(f"   Processed {len(df)} records into {table_name}.")

def ingest_index_data(conn):
    print("RUNNING Ingesting Index Data...")
    idx_path = os.path.join(NEW_DATA_DIR, "index_data.csv")
    if not os.path.exists(idx_path):
        print("Index data CSV not found.")
        return

    df = pd.read_csv(idx_path)
    df = df[df['symbol'] == 'NIFTY']
    df = df[['time', 'into', 'inth', 'intl', 'intc']]
    df.columns = ['timestamp', 'open', 'high', 'low', 'close']
    df['timestamp'] = pd.to_datetime(df['timestamp']).dt.strftime('%Y-%m-%d %H:%M:%S')
    
    ingest_dataframe_to_table(df, 'nifty_spot_1min', conn, ['timestamp'])

def ingest_options_data(conn):
    print("Ingesting Options Data (options_data.csv)...")
    opt_path = os.path.join(NEW_DATA_DIR, "options_data.csv")
    if not os.path.exists(opt_path):
        print("Options data CSV not found.")
        return

    df = pd.read_csv(opt_path)
    df_clean = df[['time', 'into', 'inth', 'intl', 'intc', 'v', 'oi', 'symbol']].copy()
    df_clean.columns = ['timestamp', 'open', 'high', 'low', 'close', 'volume', 'open_int', 'symbol']
    df_clean['timestamp'] = pd.to_datetime(df_clean['timestamp'], format='mixed').dt.strftime('%Y-%m-%d %H:%M:%S')
    
    print("   Parsing symbols...")
    parsed = df_clean['symbol'].apply(parse_option_symbol)
    df_clean['expiry_dt'] = [p[0] for p in parsed]
    df_clean['strike_pr'] = [p[1] for p in parsed]
    df_clean['option_typ'] = [p[2] for p in parsed]
    df_clean['source'] = 'CSV_IMPORT'
    
    final_cols = ['timestamp', 'expiry_dt', 'strike_pr', 'option_typ', 'open', 'high', 'low', 'close', 'volume', 'open_int', 'symbol', 'source']
    df_clean = df_clean[final_cols]
    df_2026 = df_clean[df_clean['timestamp'].str.startswith('2026')].copy()
    
    ingest_dataframe_to_table(df_2026, 'options_2026', conn, ['timestamp', 'symbol'])

def ingest_ohlc_data(conn):
    print("Ingesting Master OHLC Data (ohlc_data.csv)...")
    ohlc_path = os.path.join(NEW_DATA_DIR, "ohlc_data.csv")
    if not os.path.exists(ohlc_path):
        print("OHLC data CSV not found.")
        return

    df = pd.read_csv(ohlc_path)
    df['timestamp'] = pd.to_datetime(df['time'], format='mixed').dt.strftime('%Y-%m-%d %H:%M:%S')
    
    # 1. Spot
    spot_df = df[df['symbol'] == 'NIFTY'][['timestamp', 'open', 'high', 'low', 'close']].copy()
    if not spot_df.empty:
        ingest_dataframe_to_table(spot_df, 'nifty_spot_1min', conn, ['timestamp'])
        
    # 2. Options
    opt_df = df[df['symbol'] != 'NIFTY'].copy()
    if not opt_df.empty:
        opt_df = opt_df[['timestamp', 'open', 'high', 'low', 'close', 'volume', 'oi', 'symbol']]
        opt_df.columns = ['timestamp', 'open', 'high', 'low', 'close', 'volume', 'open_int', 'symbol']
        
        parsed = opt_df['symbol'].apply(parse_option_symbol)
        opt_df['expiry_dt'] = [p[0] for p in parsed]
        opt_df['strike_pr'] = [p[1] for p in parsed]
        opt_df['option_typ'] = [p[2] for p in parsed]
        opt_df['source'] = 'CSV_IMPORT_OHLC'
        
        final_cols = ['timestamp', 'expiry_dt', 'strike_pr', 'option_typ', 'open', 'high', 'low', 'close', 'volume', 'open_int', 'symbol', 'source']
        opt_df = opt_df[final_cols]
        opt_df_2026 = opt_df[opt_df['timestamp'].str.startswith('2026')].copy()
        
        ingest_dataframe_to_table(opt_df_2026, 'options_2026', conn, ['timestamp', 'symbol'])

def run_ingestion():
    if not os.path.exists(DB_PATH):
        print(f"ERROR: Database not found: {DB_PATH}")
        return

    conn = sqlite3.connect(DB_PATH)
    
    try:
        ingest_index_data(conn)
        ingest_options_data(conn)
        ingest_ohlc_data(conn)
        
        print("Cleaning up duplicates (secondary check)...")
        cursor = conn.cursor()
        cursor.execute("DELETE FROM nifty_spot_1min WHERE rowid NOT IN (SELECT MIN(rowid) FROM nifty_spot_1min GROUP BY timestamp)")
        cursor.execute("DELETE FROM options_2026 WHERE rowid NOT IN (SELECT MIN(rowid) FROM options_2026 GROUP BY timestamp, symbol)")
        conn.commit()
    except Exception as e:
        conn.rollback()
        print(f"INGESTION FAILED: {e}")
    finally:
        conn.close()
    
    print("\nINGESTION PROCESS COMPLETE.")

if __name__ == "__main__":
    run_ingestion()
