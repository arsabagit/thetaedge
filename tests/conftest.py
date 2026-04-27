"""
Shared fixtures and mocks for ThetaEdge test suite.

Module-level setup (outside any fixture) runs at pytest collection time:
  - Adds project root to sys.path so all shared.* imports resolve.
  - Pre-imports shared.auth and injects a MagicMock api if login failed,
    preventing sys.exit(1) when algo_strike_straddle_s1.py is imported.
"""
import sys
import os
import pytest
from unittest.mock import MagicMock

# ─── Project root on sys.path ────────────────────────────────────────────────
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

# ─── Pre-patch shared.auth ───────────────────────────────────────────────────
# auth.py calls login() at module import time. If the broker API is unreachable
# (test env, no network, expired TOTP), login() returns None and the strategy
# module calls sys.exit(1) at module level. We prevent this by injecting a
# MagicMock api before any test module that imports the strategy is collected.
import shared.auth as _auth_module  # noqa: E402 — must follow sys.path setup

if _auth_module.api is None:
    _auth_module.api = MagicMock(name="mock_shoonya_api")


# ─── 41 required trade_context keys (matches trades_S1 DB schema) ────────────
REQUIRED_TRADE_CONTEXT_KEYS = [
    "trade_date", "strategy", "vix_at_entry", "regime_label",
    "config_sl_pct", "config_pt_pct", "config_otm",
    "nifty_spot", "atm_strike",
    "ce_strike", "ce_entry_price", "ce_entry_time", "ce_exit_price", "ce_exit_time",
    "ce_sl_level", "ce_pt_level", "ce_pnl_pts", "ce_exit_reason",
    "pe_strike", "pe_entry_price", "pe_entry_time", "pe_exit_price", "pe_exit_time",
    "pe_sl_level", "pe_pt_level", "pe_pnl_pts", "pe_exit_reason",
    "total_premium", "total_pnl_pts", "total_pnl_rs",
    "lot_size", "qty", "gross_pnl_rs", "tax_charges_rs", "net_pnl_rs",
    "capital_before", "capital_after", "lots_traded",
    "trade_result", "exit_type", "paper_trading",
]


# ─── Fixtures ────────────────────────────────────────────────────────────────

@pytest.fixture
def mock_getLTP(monkeypatch):
    """Always returns 100.0 — prevents real API calls in tests."""
    from shared import order_manager
    monkeypatch.setattr(order_manager, "getLTP", lambda exchange, symbol: 100.0)
    return 100.0


@pytest.fixture
def mock_placeOrder(monkeypatch):
    """Always returns 0 (paper trade success) — prevents real orders."""
    from shared import order_manager
    monkeypatch.setattr(order_manager, "placeOrder", lambda *args, **kwargs: 0)
    return 0


@pytest.fixture
def mock_send_telegram(monkeypatch):
    """Swallows all Telegram alerts — prevents real messages during tests."""
    from shared import notifier
    mock = MagicMock()
    monkeypatch.setattr(notifier, "send_telegram_alert", mock)
    return mock


@pytest.fixture
def paper_trading_env(monkeypatch):
    """Ensures PAPER_TRADING=1 is in os.environ for the test scope."""
    monkeypatch.setenv("PAPER_TRADING", "1")
    return "1"


@pytest.fixture
def sample_trade_context():
    """
    Returns a complete valid trade_context dict with all 41 required keys.
    Values are representative of a paper-traded LOW_VIX_MODE S1 straddle.
    """
    return {
        "trade_date":      "2026-05-07",
        "strategy":        "S1",
        "vix_at_entry":    15.0,
        "regime_label":    "LOW_VIX_MODE",
        "config_sl_pct":   25,
        "config_pt_pct":   30,
        "config_otm":      150,
        "nifty_spot":      24500.0,
        "atm_strike":      24500,
        "ce_strike":       24650,
        "ce_entry_price":  100.0,
        "ce_entry_time":   "09:20:05",
        "ce_exit_price":   60.0,
        "ce_exit_time":    "11:30:00",
        "ce_sl_level":     125.0,
        "ce_pt_level":     70.0,
        "ce_pnl_pts":      40.0,
        "ce_exit_reason":  "PT_HIT",
        "pe_strike":       24350,
        "pe_entry_price":  80.0,
        "pe_entry_time":   "09:20:05",
        "pe_exit_price":   56.0,
        "pe_exit_time":    "11:30:00",
        "pe_sl_level":     100.0,
        "pe_pt_level":     56.0,
        "pe_pnl_pts":      24.0,
        "pe_exit_reason":  "PT_HIT",
        "total_premium":   180.0,
        "total_pnl_pts":   64.0,
        "total_pnl_rs":    4800.0,
        "lot_size":        75,
        "qty":             75,
        "gross_pnl_rs":    4800.0,
        "tax_charges_rs":  150.0,
        "net_pnl_rs":      4650.0,
        "capital_before":  120000.0,
        "capital_after":   124650.0,
        "lots_traded":     1,
        "trade_result":    "WIN",
        "exit_type":       "PT_EXIT",
        "paper_trading":   1,
    }
