import sqlite3
import os

def extract_vix_data(source_db_path, target_db_path):
    """
    Extracts india_vix table from master DB to a production slim DB.
    Also initializes the trades table for S1.
    """
    print(f"Connecting to master DB: {source_db_path}")
    if not os.path.exists(source_db_path):
        print(f"Error: Source DB not found at {source_db_path}")
        return

    # Connect to both databases
    source_conn = sqlite3.connect(source_db_path)
    target_conn = sqlite3.connect(target_db_path)
    
    source_cursor = source_conn.cursor()
    target_cursor = target_conn.cursor()

    # 1. Create india_vix in target
    print("Extracting india_vix table...")
    target_cursor.execute("DROP TABLE IF EXISTS india_vix")
    target_cursor.execute("""
        CREATE TABLE india_vix (
            date TEXT PRIMARY KEY,
            open REAL,
            high REAL,
            low REAL,
            close REAL
        )
    """)

    # Copy data
    source_cursor.execute("SELECT date, open, high, low, close FROM india_vix")
    rows = source_cursor.fetchall()
    target_cursor.executemany("INSERT INTO india_vix VALUES (?, ?, ?, ?, ?)", rows)
    
    # 2. Create trades_s1 in target
    print("Initializing trades_s1 table...")
    target_cursor.execute("DROP TABLE IF EXISTS trades_s1")
    target_cursor.execute("""
        CREATE TABLE trades_s1 (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT,
            vix_at_entry REAL,
            regime_label TEXT,
            ce_symbol TEXT,
            pe_symbol TEXT,
            ce_entry REAL,
            pe_entry REAL,
            combined_entry REAL,
            ce_exit REAL,
            pe_exit REAL,
            combined_exit REAL,
            pnl REAL,
            exit_reason TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    target_conn.commit()
    source_conn.close()
    target_conn.close()
    
    size_mb = os.path.getsize(target_db_path) / (1024 * 1024)
    print(f"Success! Slim production DB created at: {target_db_path} ({size_mb:.2f} MB)")

if __name__ == "__main__":
    SOURCE = r"D:\Dev\option-historical_data\data\NIFTY_1MIN_OPTIONS_BACKTEST.db"
    TARGET = r"D:\Dev\Codex\ThetaEdge\S1_straddle\data\thetaedge_prod.db"
    
    os.makedirs(os.path.dirname(TARGET), exist_ok=True)
    extract_vix_data(SOURCE, TARGET)
