"""
ThetaEdge — Holiday Calendar Sanity Check
Runs weekly (Sunday) to validate the holiday calendar for the upcoming week.
"""
import sys
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

import datetime
from shared.holiday_calendar import is_trading_day
from shared.notifier import send_telegram_alert

def run_sanity_check():
    today = datetime.date.today()
    upcoming = []
    for i in range(1, 6):
        day = today + datetime.timedelta(days=i)
        status = "TRADING" if is_trading_day(day) else "HOLIDAY"
        upcoming.append(f"  {day.strftime('%a %d %b')}: {status}")

    msg = (
        f"📅 <b>ThetaEdge — Weekly Calendar Check</b>\n"
        f"━━━━━━━━━━━━━━━━\n"
        f"Upcoming 5 days:\n"
        + "\n".join(upcoming)
    )
    print(msg)
    send_telegram_alert(msg)

if __name__ == "__main__":
    run_sanity_check()
