import sys
import os
from datetime import date

# Ensure project root is in path
BASE_DIR = r"d:\Dev\Codex\ThetaEdge"
sys.path.insert(0, BASE_DIR)

from shared.capital_manager import get_expiry_string

test_dates = [
    date(2024, 4, 18),   # Thursday → same day expiry
    date(2024, 4, 15),   # Monday   → expiry that Thursday 18th
    date(2024, 4, 19),   # Friday   → expiry next Thursday 25th
    date(2024, 4, 18),   # Thursday -> same day expiry
    date(2024, 4, 15),   # Monday   -> expiry that Thursday 18th
    date(2024, 4, 19),   # Friday   -> expiry next Thursday 25th
    date(2026, 4, 22),   # Wednesday -> expiry Thursday 23rd
    date(2026, 4, 23),   # Thursday  -> same day expiry 23rd
]

print("--- TESTING EXPIRY CALCULATIONS ---")
for d in test_dates:
    print(f"{d} ({d.strftime('%A')}) -> expiry: {get_expiry_string(d)}")
