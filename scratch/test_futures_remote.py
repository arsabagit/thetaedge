import datetime
import sys
# Add project root and shared dir to sys.path
sys.path.append("/home/algo/ThetaEdge")
sys.path.append("/home/algo/ThetaEdge/shared")
from shared.auth import ShoonyaAuth

def test_futures():
    auth = ShoonyaAuth()
    api = auth.login()
    if not api:
        print("Login failed")
        return

    ts = int(datetime.datetime(2024, 11, 1, 9, 15).timestamp())
    
    # Test NIFTY Nov 2024 Future on NFO
    # Trying to search for the token first
    try:
        res_search = api.searchscrip(exchange='NFO', searchtext='NIFTY24NOV24')
        if res_search and 'values' in res_search:
            token = res_search['values'][0]['token']
            tsym = res_search['values'][0]['tsym']
            print(f"Found Future: {tsym} (Token: {token})")
            
            res_data = api.get_time_price_series(exchange='NFO', token=token, starttime=ts, endtime=ts+3600, interval='1')
            print(f"Future Data Result: {len(res_data) if res_data else 0}")
        else:
            print("No Future token found for NIFTY24NOV24")
    except Exception as e:
        print(f"Search failed: {e}")

if __name__ == "__main__":
    test_futures()
