import datetime
import logging
import sys
import os
import pandas as pd
from shared.downloader import DataDownloader
from shared.history_db import HistoryDB
from shared.notifier import send_telegram_alert
from shared.market_data_fetcher import fetch_and_save_vix
from S1_straddle.config import HISTORICAL_DB_PATH

# Configure Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(levelname)s | %(message)s')
logger = logging.getLogger("DataVault")

class DataVault:
    def __init__(self):
        self.downloader = DataDownloader()
        self.db = HistoryDB(HISTORICAL_DB_PATH)
        self.strike_step = 50
        self.strike_spread = 20 # User requested ATM +/- 20

    def collect_day(self, target_date):
        """Fetches NIFTY index + ATM +/- 20 options for a specific date."""
        day_str = target_date.strftime("%Y-%m-%d")
        if target_date.weekday() >= 5:
            logger.info(f"[{day_str}] Skipping weekend.")
            return None

        logger.info(f"🚀 Starting Data Vault collection for {day_str}...")
        
        start_ts = target_date.replace(hour=9, minute=15, second=0, microsecond=0)
        end_ts = target_date.replace(hour=15, minute=30, second=0, microsecond=0)
        
        stats = {"index": 0, "options": 0, "failures": 0}

        try:
            # 1. Fetch NIFTY Index (Token 26000)
            df_index = self.downloader.fetch_ohlc("NSE", "26000", start_ts, end_ts)
            if not df_index.empty:
                self.db.save_index(df_index)
                stats["index"] = len(df_index)
                
                # Derive ATM from last 'close' (intc)
                spot = float(df_index.iloc[-1]['intc'])
                atm = int(round(spot / self.strike_step) * self.strike_step)
                strikes = [atm + (j * self.strike_step) for j in range(-self.strike_spread, self.strike_spread + 1)]
                
                logger.info(f"[{day_str}] Spot: {spot}, ATM: {atm}. Fetching {len(strikes)*2} option contracts...")
                
                expiry = self.downloader.get_actual_expiry("NIFTY", target_date)
                
                for strike in strikes:
                    for opt_type in ['CE', 'PE']:
                        tsym = self.downloader.generate_tsym("NIFTY", target_date, strike, opt_type)
                        token = self.downloader.discover_token(tsym)
                        if token:
                            df_opt = self.downloader.fetch_ohlc("NFO", token, start_ts, end_ts)
                            if not df_opt.empty:
                                # Ensure required metadata exists for schema mapping
                                df_opt['symbol'] = tsym
                                df_opt['strike_pr'] = float(strike)
                                df_opt['option_typ'] = opt_type
                                self.db.save_options(df_opt, expiry)
                                stats["options"] += len(df_opt)
                            else:
                                logger.warning(f"[{day_str}] Missing data for {tsym}")
                                stats["failures"] += 1
                        else:
                            logger.error(f"[{day_str}] Token not found for {tsym}")
                            stats["failures"] += 1
            else:
                logger.warning(f"[{day_str}] No NIFTY index data (Market holiday?).")
                return None

        except Exception as e:
            logger.error(f"[{day_str}] Collection crashed: {e}")
            stats["failures"] += 1

        return stats

    def run_backfill(self, days=5):
        """Initial deployment backfill."""
        today = datetime.datetime.now()
        processed_days = []
        total_stats = {"index": 0, "options": 0, "failures": 0}
        
        logger.info(f"📦 INITIAL BACKFILL: Processing last {days} trading days...")
        
        for i in range(1, days + 1):
            target = today - datetime.timedelta(days=i)
            res = self.collect_day(target)
            if res:
                processed_days.append(target.strftime("%Y-%m-%d"))
                for k in total_stats: total_stats[k] += res[k]
        
        msg = (
            f"📦 <b>ThetaEdge Backfill Complete</b>\n"
            f"━━━━━━━━━━━━━━━━\n"
            f"📅 Days: {len(processed_days)} | Strikes: ±20\n"
            f"📊 Index records: {total_stats['index']}\n"
            f"📊 Option records: {total_stats['options']}\n"
            f"⚠️ Failures: {total_stats['failures']} (see logs)"
        )
        send_telegram_alert(msg)
        return total_stats

    def run_daily(self):
        """Standard daily trigger logic."""
        today = datetime.datetime.now()
        
        logger.info(f"VIX Ingestion: Starting check for {today.date()}...")
        vix_val = fetch_and_save_vix(today.date())
        
        res = self.collect_day(today)
        
        if res:
            msg = (
                f"📊 <b>ThetaEdge Data Vault</b>\n"
                f"━━━━━━━━━━━━━━━━\n"
                f"📅 Date: {today.strftime('%Y-%m-%d')}\n"
                f"📈 VIX Collected: {vix_val:.2f}\n"
                f"📊 Index records: {res['index']}\n"
                f"📊 Option records: {res['options']}\n"
                f"🎯 Strikes collected: ATM ± 20\n"
                f"Status: {'✅ Complete' if res['failures'] == 0 else '⚠️ ' + str(res['failures']) + ' failures'}"
            )
            send_telegram_alert(msg)
        else:
            logger.info("Nothing to collect today (Weekend/Holiday).")

if __name__ == "__main__":
    vault = DataVault()
    if "--backfill" in sys.argv:
        vault.run_backfill(days=5)
    elif "--collect-today" in sys.argv:
        vault.run_daily()
    else:
        print("Usage: python shared/data_vault.py [--backfill | --collect-today]")
