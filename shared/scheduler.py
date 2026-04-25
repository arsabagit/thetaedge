import schedule
import time
import subprocess
import os
import sys
from datetime import datetime, time as dtime
from shared.holiday_calendar import is_trading_day
from shared.market_data_fetcher import fetch_morning_vix
from shared.notifier import send_telegram_alert
from shared.regime_config import RegimeConfig

# Ensure project root is in path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def morning_startup():
    today = datetime.now().date()
    print(f"\n[STARTUP] Activity Triggered: {datetime.now()}")
    
    if not is_trading_day(today):
        print(f"[HOLIDAY] {today} - No trading. Clean exit.")
        send_telegram_alert(f"⚪ <b>ThetaEdge S1</b>\n━━━━━━━━━━━━━━━━\n📅 Date: {today}\n💤 Reason: NSE Trading Holiday / Weekend\n🏁 No trading today.")
        return False
    
    # NEW: Fetch and Save VIX at 09:00 IST
    from shared.market_data_fetcher import fetch_and_save_vix
    vix = fetch_and_save_vix(today)
    
    # Lock regime with confirmed VIX
    config = RegimeConfig.get_config(vix)
    
    # Log regime (locks the specific parameters for the day)
    # The S1 strategy script also re-fetches this, but this is the authoritative morning alert.
    msg = (
        f"🟢 <b>ThetaEdge S1 Starting</b>\n"
        f"━━━━━━━━━━━━━━━━\n"
        f"📅 Date: {today}\n"
        f"📊 VIX: {vix:.2f}\n"
        f"⚙️ Regime: <b>{config['label']}</b>\n"
        f"⏰ Entry Window: {config['entry_time']}\n"
        f"🎯 OTM Offset: {config['otm']} pts\n"
        f"🛡️ SL: {config['sl_pct']}% | PT: {config['profit_target_pct']}%"
    )
    print(f"[SUCCESS] Regime Selected: {config['label']} (VIX: {vix})")
    send_telegram_alert(msg)
    # --- FIX: Actually launch the strategy process ---
    import subprocess, sys, os
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    LOG_FILE = os.path.join(BASE_DIR, "S1_straddle", "logs", "s1_cron.log")
    strategy_script = os.path.join(BASE_DIR, "S1_straddle", "algo_strike_straddle_s1.py")
    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
    with open(LOG_FILE, "a") as log:
        subprocess.Popen(
            [sys.executable, strategy_script],
            stdout=log,
            stderr=log
        )
    print(f"[LAUNCHED] Strategy process started: {strategy_script}")
    return True

def market_close_check():
    now = datetime.now()
    print(f"[CLOSE] Market close check at {now}")
    send_telegram_alert(
        f"🔴 <b>ThetaEdge S1 Session Ended</b>\n"
        f"━━━━━━━━━━━━━━━━\n"
        f"⏰ Time: 15:30 IST\n"
        f"📝 Check logs for final CSV output"
    )

def run_scheduler():
    # Production schedule in IST
    schedule.every().day.at("09:00").do(morning_startup)
    schedule.every().day.at("15:30").do(market_close_check)
    
    today_status = "TRADING" if is_trading_day(datetime.now().date()) else "HOLIDAY"
    print(f"[{datetime.now()}] ThetaEdge Scheduler initialized. Mode: {today_status}")
    print("Waiting for timed triggers...")
    
    while True:
        try:
            schedule.run_pending()
            time.sleep(30)
        except KeyboardInterrupt:
            print("\n[STOP] Scheduler stopped by user.")
            break
        except Exception as e:
            print(f"[ERROR] Scheduler exception: {e}")
            time.sleep(60)

if __name__ == "__main__":
    # Test morning startup manually if needed
    if len(sys.argv) > 1 and sys.argv[1] == "--test-startup":
        morning_startup()
    else:
        run_scheduler()
