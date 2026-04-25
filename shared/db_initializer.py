import sqlite3
import os
import sys

# Add parent directory to path to import config
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from S1_straddle.config import PROD_DB_PATH, HISTORICAL_DB_PATH, DATA_DIR

def init_prod_db():
    """Initializes the production database with trades and versioning tables."""
    print(f"Initializing Production DB at: {PROD_DB_PATH}")
    os.makedirs(os.path.dirname(PROD_DB_PATH), exist_ok=True)
    
    conn = sqlite3.connect(PROD_DB_PATH)
    cursor = conn.cursor()
    
    # 1. trades_S1 table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS trades_S1 (
        -- Identity
        id                INTEGER PRIMARY KEY AUTOINCREMENT,
        trade_date        TEXT NOT NULL,          -- "2026-04-28"
        strategy          TEXT DEFAULT 'S1',      -- future-proof for S2, S3

        -- Regime & Config
        vix_at_entry      REAL,                   -- 17.53
        regime_label      TEXT,                   -- "HIGH_VIX_MODE" / "LOW_VIX_MODE"
        config_sl_pct     REAL,                   -- 40.0 or 25.0
        config_pt_pct     REAL,                   -- 70.0 or 30.0
        config_otm        INTEGER,                -- 100 or 150

        -- Market Context
        nifty_spot        REAL,                   -- 22251.15
        atm_strike        INTEGER,                -- 22250

        -- CE Leg
        ce_strike         INTEGER,                -- 22350
        ce_entry_price    REAL,                   -- 85.50
        ce_entry_time     TEXT,                   -- "09:25:12"
        ce_exit_price     REAL,                   -- 42.75
        ce_exit_time      TEXT,                   -- "13:45:00"
        ce_sl_level       REAL,                   -- 119.70
        ce_pt_level       REAL,                   -- 25.65
        ce_pnl_pts        REAL,                   -- 42.75
        ce_exit_reason    TEXT,                   -- "PT_HIT" / "SL_HIT" / "TIME_EXIT"

        -- PE Leg
        pe_strike         INTEGER,                -- 22150
        pe_entry_price    REAL,                   -- 92.30
        pe_entry_time     TEXT,                   -- "09:25:12"
        pe_exit_price     REAL,                   -- 46.15
        pe_exit_time      TEXT,                   -- "13:45:00"
        pe_sl_level       REAL,                   -- 129.22
        pe_pt_level       REAL,                   -- 27.69
        pe_pnl_pts        REAL,                   -- 46.15
        pe_exit_reason    TEXT,                   -- "PT_HIT" / "SL_HIT" / "TIME_EXIT"

        -- Combined Result
        total_premium     REAL,                   -- 177.80 (ce + pe entry)
        total_pnl_pts     REAL,                   -- 88.90 (combined)
        total_pnl_rs      REAL,                   -- PnL in rupees (pts × lot_size)
        lot_size          INTEGER,                -- 75
        qty               INTEGER,                -- 75 (1 lot)
        gross_pnl_rs      REAL,                   -- before tax/charges
        tax_charges_rs    REAL,                   -- brokerage + STT + GST
        net_pnl_rs        REAL,                   -- after all charges

        -- Capital State
        capital_before    REAL,                   -- 120000.00
        capital_after     REAL,                   -- 126690.00
        lots_traded       INTEGER,                -- 1

        -- Trade Classification
        trade_result      TEXT,                   -- "WIN" / "LOSS" / "BREAKEVEN"
        exit_type         TEXT,                   -- "BOTH_PT" / "BOTH_SL" / 
                                                  -- "ONE_SL_ONE_PT" / "TIME_EXIT"
                                                  -- "HOLIDAY_SKIP" / "NO_TRADE"

        -- Paper vs Live
        paper_trading     INTEGER DEFAULT 1,      -- 1=paper, 0=live

        -- Timestamps
        created_at        TEXT DEFAULT (datetime('now','localtime'))
    )''')
    
    # Indices
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_trade_date ON trades_S1(trade_date)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_regime ON trades_S1(regime_label)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_result ON trades_S1(trade_result)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_paper ON trades_S1(paper_trading)")
    
    # 2. db_version table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS db_version (
        version     INTEGER PRIMARY KEY,
        applied_at  TEXT DEFAULT (datetime('now','localtime')),
        notes       TEXT
    )''')
    
    cursor.execute("INSERT OR IGNORE INTO db_version (version, notes) VALUES (1, 'Initial schema - ThetaEdge S1')")

    # 3. india_vix (Required for market_data_fetcher)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS india_vix (
        date TEXT PRIMARY KEY,
        open REAL,
        high REAL,
        low REAL,
        close REAL
    )''')
    
    conn.commit()
    conn.close()
    print("Production DB initialization complete.")

def init_historical_db():
    """Initializes the Data Vault (historical) database."""
    print(f"Initializing Historical DB at: {HISTORICAL_DB_PATH}")
    os.makedirs(os.path.dirname(HISTORICAL_DB_PATH), exist_ok=True)
    
    conn = sqlite3.connect(HISTORICAL_DB_PATH)
    cursor = conn.cursor()
    
    # Table 1: Index OHLC (Matches master nifty_spot_1min)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS nifty_index_1min (
            timestamp DATETIME,
            open REAL,
            high REAL,
            low REAL,
            close REAL,
            volume INTEGER,
            PRIMARY KEY (timestamp)
        )
    ''')
    
    # Table 2: Options OHLC (Matches master options_YYYY)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS nifty_options_1min (
            timestamp DATETIME,
            expiry_dt DATE,
            strike_pr REAL,
            option_typ TEXT,
            open REAL,
            high REAL,
            low REAL,
            close REAL,
            volume INTEGER,
            open_int INTEGER,
            symbol TEXT,
            source TEXT,
            PRIMARY KEY (timestamp, symbol)
        )
    ''')
    
    # Indices
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_index_time ON nifty_index_1min (timestamp)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_options_time ON nifty_options_1min (timestamp)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_options_symbol ON nifty_options_1min (symbol)')
    
    conn.commit()
    conn.close()
    print("Historical DB initialization complete.")

if __name__ == "__main__":
    init_prod_db()
    init_historical_db()
