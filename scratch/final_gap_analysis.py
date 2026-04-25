import sqlite3
import pandas as pd

DB_PATH = r"d:\Dev\option-historical_data\data\NIFTY_1MIN_OPTIONS_BACKTEST.db"

def run_gap_analysis():
    conn = sqlite3.connect(DB_PATH)
    
    print("--- 2024-2026 DATA GAP ANALYSIS ---")
    
    # 1. Spot Analysis
    print("\n[SPOT INDEX COVERAGE]")
    df_spot = pd.read_sql_query("""
        SELECT 
            strftime('%Y', timestamp) as year, 
            MIN(timestamp) as start_date, 
            MAX(timestamp) as end_date, 
            COUNT(DISTINCT date(timestamp)) as trading_days
        FROM nifty_spot_1min 
        WHERE timestamp >= '2024-01-01'
        GROUP BY year
    """, conn)
    print(df_spot.to_string(index=False))
    
    # 2. Options Analysis
    print("\n[OPTIONS COVERAGE (2025-2026)]")
    # For options, we have separate tables so we combine them for analysis
    query_opt = """
    SELECT '2024' as year, MIN(timestamp) as start_date, MAX(timestamp) as end_date, COUNT(DISTINCT date(timestamp)) as trading_days FROM options_2024
    UNION ALL
    SELECT '2025' as year, MIN(timestamp) as start_date, MAX(timestamp) as end_date, COUNT(DISTINCT date(timestamp)) as trading_days FROM options_2025
    UNION ALL
    SELECT '2026' as year, MIN(timestamp) as start_date, MAX(timestamp) as end_date, COUNT(DISTINCT date(timestamp)) as trading_days FROM options_2026
    """
    df_opt = pd.read_sql_query(query_opt, conn)
    print(df_opt.to_string(index=False))
    
    # 3. India VIX Analysis
    print("\n[INDIA VIX COVERAGE]")
    df_vix = pd.read_sql_query("""
        SELECT 
            strftime('%Y', date) as year, 
            MIN(date) as start_date, 
            MAX(date) as end_date, 
            COUNT(date) as total_days
        FROM india_vix
        WHERE date >= '2024-01-01'
        GROUP BY year
    """, conn)
    print(df_vix.to_string(index=False))
    
    conn.close()

if __name__ == "__main__":
    run_gap_analysis()
