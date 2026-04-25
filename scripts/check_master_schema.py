import sqlite3
import os

db_path = r'D:\Dev\option-historical_data\data\NIFTY_1MIN_OPTIONS_BACKTEST.db'
if not os.path.exists(db_path):
    print(f"Error: {db_path} not found")
    exit(1)

conn = sqlite3.connect(db_path)
c = conn.cursor()

print("--- TABLES ---")
c.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = [r[0] for r in c.fetchall()]
print(tables)

for table in tables:
    print(f"\n--- SCHEMA for {table} ---")
    c.execute(f"PRAGMA table_info({table})")
    cols = c.fetchall()
    for col in cols:
        print(f"  {col[1]} ({col[2]})")

conn.close()
