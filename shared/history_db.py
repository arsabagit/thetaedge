import sqlite3
import os
import logging
import pandas as pd

logger = logging.getLogger(__name__)

class HistoryDB:
    def __init__(self, db_path):
        self.db_path = db_path
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self.init_db()

    def get_connection(self):
        return sqlite3.connect(self.db_path)

    def init_db(self):
        with self.get_connection() as conn:
            # Table 1: Index OHLC (Matches master nifty_spot_1min)
            conn.execute('''
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
            conn.execute('''
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
            
            # Indices for range queries
            conn.execute('CREATE INDEX IF NOT EXISTS idx_index_time ON nifty_index_1min (timestamp)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_options_time ON nifty_options_1min (timestamp)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_options_symbol ON nifty_options_1min (symbol)')
            conn.commit()
    
    def save_index(self, df):
        """
        Saves index OHLC data. 
        Expects Shoonya df with: time, into, inth, intl, intc, intv
        """
        if df.empty: return
        
        # Map to Master Schema
        mapping = {
            'time': 'timestamp', 
            'into': 'open', 'inth': 'high', 'intl': 'low', 
            'intc': 'close', 'intv': 'volume'
        }
        data = df[list(mapping.keys())].rename(columns=mapping)
        
        # Ensure timestamp is string for ISO storage
        if not pd.api.types.is_string_dtype(data['timestamp']):
            data['timestamp'] = data['timestamp'].dt.strftime('%Y-%m-%d %H:%M:%S')

        with self.get_connection() as conn:
            placeholders = ', '.join(['?'] * len(data.columns))
            sql = f"INSERT OR IGNORE INTO nifty_index_1min ({', '.join(data.columns)}) VALUES ({placeholders})"
            conn.executemany(sql, data.values.tolist())
            conn.commit()

    def save_options(self, df, expiry_dt):
        """
        Saves options OHLC data.
        Expects Shoonya df with: time, into, inth, intl, intc, intv, intoi, symbol
        """
        if df.empty: return
        
        # Map to Master Schema
        mapping = {
            'time': 'timestamp',
            'into': 'open', 'inth': 'high', 'intl': 'low', 
            'intc': 'close', 'intv': 'volume', 'intoi': 'open_int',
            'symbol': 'symbol'
        }
        data = df[list(mapping.keys())].rename(columns=mapping)
        
        # Extract metadata from standard tsym (e.g. NIFTY17APR24C22500)
        # However, for 100% accuracy, we pass strike/type if known or parse from symbol
        def parse_symbol(row):
            sym = row['symbol']
            # Simple heuristic for NIFTY. In production we pass these explicitly for backfill.
            # Here we assume symbols are from downloader as NIFTYDDMMMYY[C/P]STRIKE
            import re
            m = re.search(r'([CP])(\d+)$', sym)
            if m:
                return float(m.group(2)), 'CE' if m.group(1) == 'C' else 'PE'
            return 0.0, 'XX'

        # We prefer passing these in from data_vault.py to be safe.
        # But if they aren't there, we'll try to parse.
        if 'strike_pr' not in data.columns:
            data['strike_pr'], data['option_typ'] = zip(*data.apply(parse_symbol, axis=1))

        data['expiry_dt'] = expiry_dt.strftime('%Y-%m-%d')
        data['source'] = 'Shoonya'
        
        # Ensure timestamp is string
        if not pd.api.types.is_string_dtype(data['timestamp']):
            data['timestamp'] = data['timestamp'].dt.strftime('%Y-%m-%d %H:%M:%S')

        cols = ['timestamp', 'expiry_dt', 'strike_pr', 'option_typ', 'open', 'high', 'low', 'close', 'volume', 'open_int', 'symbol', 'source']
        data = data[cols]

        with self.get_connection() as conn:
            placeholders = ', '.join(['?'] * len(cols))
            sql = f"INSERT OR IGNORE INTO nifty_options_1min ({', '.join(cols)}) VALUES ({placeholders})"
            conn.executemany(sql, data.values.tolist())
            conn.commit()
