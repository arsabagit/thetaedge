import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# =============================================================================
# STRATEGY CONFIGURATION
# =============================================================================

# Portfolio / General
MAX_TRADES_PER_DAY = 1
PAPER_TRADING = int(os.environ.get("PAPER_TRADING", 1))  # 1 = Paper (simulation only), 0 = LIVE (CAUTION!)
STRATEGY_TYPE = os.environ.get("STRATEGY_TYPE", "IronCondor")

# Dynamic Lot Sizes per Index
INDEX_LOT_SIZES = {
    "NIFTY": 25,
    "BANKNIFTY": 15
}

# Telegram Alerts - Load from environment (SECURE)
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID', '')

# Validation on startup
if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
    import warnings
    warnings.warn("⚠️  Telegram credentials not configured. Alerts will be DISABLED. Set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID in .env")
    TELEGRAM_BOT_TOKEN = ''
    TELEGRAM_CHAT_ID = ''

# Timing  (Expert Audit: Entry at 10:15 lets initial volatility settle)
TRADE_START_TIME   = "10:15"  # was 09:20 — changed per expert audit
PROFIT_LOCK_TIME   = "14:00"  # Pre-close: lock profits if both legs are green
UNIVERSAL_EXIT_TIME = "15:15" # Hard exit — never hold past this time

# =============================================================================
# RISK MANAGEMENT — FIXED POINTS (used by live strangle.py)
# =============================================================================
# CRITICAL: SL_POINTS and TP_POINTS were MISSING, causing AttributeError crash.
# Added per expert audit Phase 1 fix.

# ─── Iron Condor optimized params (grid search 2026-04-15) ───
IC_SL_POINTS = 20          # Tighter SL: exit if option rises ₹20 above entry
IC_TP_POINTS = 60          # Take-Profit: exit if option falls ₹60 below entry
IC_TARGET_PREMIUM = 110    # Aim for ₹110 premium per sold leg
IC_TSL_TRIGGER_POINTS = 8  # Every 8 pts of profit decay ...
IC_TSL_MOVE_POINTS = 5     # ... lower the SL by 5 pts (locks in 63% of decay)

# ─── Short Strangle optimized params (grid search 2026-04-15) ───
SS_SL_POINTS = 25          # Tighter SL: exit if option rises ₹25 above entry
SS_TP_POINTS = 60          # Take-Profit: exit if option falls ₹60 below entry
SS_TARGET_PREMIUM = 110    # Aim for ₹110 premium per sold leg
SS_TSL_TRAIL_RATIO = 4     # Lazy trail: every 4 pts decay → 1 pt trail (25% lock-in)

# ─── Legacy aliases (used by backtester / optimizer when monkey-patching) ───
SL_POINTS = IC_SL_POINTS
TP_POINTS = IC_TP_POINTS

# Portfolio-level drawdown limit (both legs combined)
MAX_LOSS_PER_DAY  = -5000  # Exit ALL positions if total M2M falls below ₹-5000

# Individual leg protection (Expert Audit Gap 4)
LEG_MAX_LOSS_MULTIPLIER = 2.0  # Exit a SINGLE leg if it reaches 2x entry price

# Percentage-based trailing system (used by backtester and TSL logic)
SL_PERCENTAGE     = 0.10   # 10% multiplier: SL = entry * 1.10

# Trailing Stop-Loss Ratchet (Iron Condor uses per-strategy values above)
TSL_TRIGGER_POINTS = IC_TSL_TRIGGER_POINTS
TSL_MOVE_POINTS    = IC_TSL_MOVE_POINTS

# Trail-to-Cost Activation (Logic D: move SL to break-even once +20 pts profit)
TTP_ACTIVATION     = 20
TTP_BUFFER_PERCENT = 0.01

# =============================================================================
# MARKET FILTERS — EXPERT AUDIT PHASE 2 ADDITIONS
# =============================================================================

# India VIX Filter: Do NOT trade if market fear index is too high.
# High VIX means options look expensive to sell, but the market is about
# to move violently — the worst environment for a Short Strangle.
VIX_TOKEN         = "26017"   # NSE token for India VIX
MAX_VIX_TO_TRADE  = 24.0      # Skip entry if India VIX > 24.0 (Increased for Paper Testing)
GAP_PROTECTION_POINTS = 150   # Skip if market opens > 150 pts away from prev close

# =============================================================================
# INSTRUMENT SELECTION  (Change TARGET_INDEX to switch between NIFTY/BANKNIFTY)
# =============================================================================
TARGET_INDEX  = "NIFTY"        # Options: "NIFTY" | "BANKNIFTY"

# NSE Spot Price Tokens
NIFTY_TOKEN       = "26000"    # NSE token for Nifty 50 index
BANKNIFTY_TOKEN   = "26009"    # NSE token for Bank Nifty index

# ATM Strike Rounding Interval
# Nifty strikes move in ₹50 increments; BankNifty strikes move in ₹100 increments.
# This is used in find_strikes() and antigravity_fetcher.py to calculate ATM.
NIFTY_STRIKE_INTERVAL     = 50
BANKNIFTY_STRIKE_INTERVAL = 100

# =============================================================================
# EXECUTION
# =============================================================================
TARGET_PREMIUM      = 110     # Aim for ₹110 premium per leg (optimized from 100)
WING_DISTANCE       = 200     # Strike distance for protective wings (e.g., 200 pts)
BUFFER_PERCENTAGE   = 0.05    # 5% limit price buffer on all order placements
TRAIL_CHECK_INTERVAL = 1      # Monitor loop frequency in seconds

# Quote anomaly guard: ignore sudden absurd LTP spikes unless re-confirmed.
# Example prevented: ₹~100 premium legs suddenly reading ₹24,500 due bad tick.
QUOTE_SPIKE_MULTIPLIER = float(os.environ.get("QUOTE_SPIKE_MULTIPLIER", 8.0))

# =============================================================================
# SHORT STRANGLE SIDEWINDER PARAMETERS
# (from D:\Dev\Python\short_strangle — TSL uses ratio-based ratchet, NOT golden ratio)
# =============================================================================
LOT_SIZE           = 25       # Contracts per 1 NIFTY lot (update if SEBI changes)
BASE_LOTS          = int(os.environ.get("BASE_LOTS", 1))
PROFIT_PER_LOT_ADD = int(os.environ.get("PROFIT_PER_LOT_ADD", 8000))
TSL_TRAIL_RATIO    = SS_TSL_TRAIL_RATIO   # Lazy trail: ratio=4 → 25% lock-in (optimized from 2)
OPTION_CHAIN_COUNT = 20       # Strikes to fetch on each side of ATM
MONITOR_INTERVAL_SECS = 15    # How often the risk engine polls LTP

# =============================================================================
# DATABASE — Per-strategy DB files for clean separation
# =============================================================================
IC_DB_PATH = "data/ic_trades.db"
SS_DB_PATH = "data/ss_trades.db"
