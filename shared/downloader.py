import os
import time
import datetime
import pandas as pd
import logging
import requests
import zipfile
import io
from shared.auth import ShoonyaAuth

logger = logging.getLogger(__name__)

class DataDownloader:
    def __init__(self):
        self.auth = ShoonyaAuth()
        self.api = self.auth.login()
        if not self.api:
            raise Exception("Shoonya API Login failed.")
        
        self.cache_dir = "data/cache"
        os.makedirs(self.cache_dir, exist_ok=True)
        self.rate_limit_delay = 0.5 # Per user request
        self.master_df = self.load_nfo_master()

    def load_nfo_master(self):
        """Download and cache Shoonya NFO Master file for token discovery."""
        master_path = os.path.join(self.cache_dir, "NFO_symbols.csv")
        if os.path.exists(master_path):
            mtime = os.path.getmtime(master_path)
            if (time.time() - mtime) < (6 * 3600):
                return pd.read_csv(master_path)

        url = "https://api.shoonya.com/NFO_symbols.txt.zip"
        try:
            logger.info("Downloading NFO Master file...")
            r = requests.get(url)
            if r.status_code == 200:
                z = zipfile.ZipFile(io.BytesIO(r.content))
                with z.open(z.namelist()[0]) as f:
                    df = pd.read_csv(f)
                    df.to_csv(master_path, index=False)
                    return df
        except Exception as e:
            logger.error(f"Failed to load NFO master: {e}")
        return pd.DataFrame()

    def throttle(self):
        time.sleep(self.rate_limit_delay)

    def fetch_ohlc(self, exchange, token, start_dt, end_dt):
        """Fetch historical 1-minute OHLC data."""
        start_ts = int(start_dt.timestamp())
        end_ts = int(end_dt.timestamp())
        self.throttle()
        
        try:
            res = self.api.get_time_price_series(
                exchange=exchange, token=token, 
                starttime=start_ts, endtime=end_ts, interval="1"
            )
            if res and isinstance(res, list) and len(res) > 0:
                df = pd.DataFrame(res)
                # Shoonya returns data in descending order often, or random.
                # Standardizing to ascending time.
                df['time'] = pd.to_datetime(df['time'], format='%d-%m-%Y %H:%M:%S')
                return df.sort_values('time')
        except Exception as e:
            logger.error(f"Error fetching OHLC for {token}: {e}")
        return pd.DataFrame()

    def discover_token(self, tsym):
        """Find token for a given Trading Symbol."""
        if not self.master_df.empty:
            match = self.master_df[self.master_df['TradingSymbol'] == tsym]
            if not match.empty:
                return str(match.iloc[0]['Token'])
        
        try:
            res = self.api.searchscrip("NFO", tsym)
            if res and 'values' in res:
                for v in res['values']:
                    if v['tsym'] == tsym:
                        return v['token']
        except: pass
        return None

    def get_actual_expiry(self, index, date_dt):
        """Find the nearest expiry >= date_dt from master."""
        if self.master_df.empty:
            # Fallback
            days_ahead = (3 - date_dt.weekday() + 7) % 7 # Thursday
            return (date_dt + datetime.timedelta(days=days_ahead)).date()
            
        idx_df = self.master_df[self.master_df['Symbol'] == index]
        expiries = pd.to_datetime(idx_df['Expiry'], format='%d-%b-%Y')
        valid_expiries = expiries[expiries.dt.date >= date_dt.date()]
        if not valid_expiries.empty:
            return valid_expiries.min().date()
        return (date_dt + datetime.timedelta(days=7)).date()

    def generate_tsym(self, index, date_dt, strike, opt_type):
        expiry = self.get_actual_expiry(index, date_dt)
        expiry_str = expiry.strftime('%d%b%y').upper()
        return f"{index}{expiry_str}{'C' if opt_type == 'CE' else 'P'}{int(strike)}"
