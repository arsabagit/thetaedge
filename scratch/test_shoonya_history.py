import os
import sys
import datetime
from shared.auth import ShoonyaAuth

def test_availability():
    try:
        auth = ShoonyaAuth()
        api = auth.login()
        if not api:
            print("API LOGIN FAILED")
            return
        
        # Test Start of Gap: Nov 1, 2024
        start_ts = datetime.datetime(2024, 11, 1, 9, 15).timestamp()
        end_ts = datetime.datetime(2024, 11, 1, 15, 30).timestamp()
        
        res = api.get_time_price_series(exchange='NSE', token='26000', start_time=start_ts, end_time=end_ts)
        
        if res:
            print(f"SUCCESS: Found {len(res)} records for 2024-11-01.")
            print(f"Sample: {res[0]}")
        else:
            print("FAILURE: No data returned for 2024-11-01.")
            
    except Exception as e:
        print(f"ERROR: {e}")

if __name__ == "__main__":
    test_availability()
