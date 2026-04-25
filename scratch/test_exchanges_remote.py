import datetime
import sys
# Add project root and shared dir to sys.path
sys.path.append("/home/algo/ThetaEdge")
sys.path.append("/home/algo/ThetaEdge/shared")
from shared.auth import ShoonyaAuth

def test_exchanges():
    auth = ShoonyaAuth()
    api = auth.login()
    if not api:
        print("Login failed")
        return

    ts = int(datetime.datetime(2024, 11, 1, 9, 15).timestamp())
    
    # Test NSE:26000 (Already failed in main script, but retry for 1 candle)
    res_nse = api.get_time_price_series(exchange='NSE', token='26000', starttime=ts, endtime=ts+300, interval='1')
    print(f"NSE:26000 Result: {len(res_nse) if res_nse else 0}")
    
    # Test IDX:26000
    res_idx = api.get_time_price_series(exchange='IDX', token='26000', starttime=ts, endtime=ts+300, interval='1')
    print(f"IDX:26000 Result: {len(res_idx) if res_idx else 0}")

    # Test NSE:Nifty 50 (some old APIs allowed index name)
    try:
        res_name = api.get_time_price_series(exchange='NSE', token='Nifty 50', starttime=ts, endtime=ts+300, interval='1')
        print(f"NSE:Nifty 50 Result: {len(res_name) if res_name else 0}")
    except:
        print("NSE:Nifty 50 failed")

if __name__ == "__main__":
    test_exchanges()
