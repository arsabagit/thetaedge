import os
from dotenv import load_dotenv
import sys

# Add parent directory and shared to path for easy modular imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.regime_config import RegimeConfig

# Load environment variables
load_dotenv()

# ==========================================
# Strategy S1: Regime-Adaptive Straddle
# ==========================================

# Core Settings
PAPER_TRADING = int(os.getenv("PAPER_TRADING", 1))
STOCK = "NIFTY"
LOT_SIZE = 75  # Standard NSE Nifty Lot Size

# Capital Management
STARTING_CAPITAL = float(os.getenv("STARTING_CAPITAL", 120000))
MAX_LOTS_OVERRIDE = int(os.getenv("MAX_LOTS_OVERRIDE", 1))

# Notifications
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# Files and Logs
LOG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
CAPITAL_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "capital_state.json")
PROD_DB_PATH = os.path.join(DATA_DIR, "thetaedge_prod.db")
HISTORICAL_DB_PATH = os.path.join(DATA_DIR, "thetaedge_historical.db")

# Regime Parameters (inherited from shared logic)
VIX_THRESHOLD = RegimeConfig.VIX_THRESHOLD
CONFIG_HIGH_VIX = RegimeConfig.CONFIG_A
CONFIG_LOW_VIX = RegimeConfig.CONFIG_B
