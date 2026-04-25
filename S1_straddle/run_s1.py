import sys
import os

# Set working directory to project root for clean imports
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from shared.scheduler import run_scheduler

def print_banner():
    print("=" * 60)
    print("      ThetaEdge S1 — Production Runner Entry")
    print("      Target: NIFTY Regime-Adaptive Straddle")
    print("      Timezone: Asia/Kolkata (IST)")
    print("=" * 60)
    print(f"Project Root: {BASE_DIR}")
    print(f"Log Output: S1_straddle/logs/s1_cron.log")
    print("-" * 60)

if __name__ == "__main__":
    try:
        print_banner()
        # Start the perpetual scheduler loop
        run_scheduler()
    except Exception as e:
        print(f"[FATAL] Production runner crashed: {e}")
        sys.exit(1)
