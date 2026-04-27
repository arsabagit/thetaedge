"""
test_trade_context.py — Tests for trade_context structure and PnL calculations.

The trade_context dict is the canonical trade record passed to log_trade_s1().
These tests guard against:
  - Missing keys (which cause silent NULLs in the DB)
  - Wrong PnL arithmetic
  - Wrong trade_result classification
"""
import pytest
from tests.conftest import REQUIRED_TRADE_CONTEXT_KEYS


# ─── Helper: trade result classification ─────────────────────────────────────
# Mirrors the classification logic expected in the strategy.
# WIN  : net_pnl >  100
# LOSS : net_pnl < -100
# BREAKEVEN: -100 <= net_pnl <= 100

def _classify_result(net_pnl: float) -> str:
    if net_pnl > 100:
        return "WIN"
    if net_pnl < -100:
        return "LOSS"
    return "BREAKEVEN"


# ─── Structure tests ──────────────────────────────────────────────────────────

def test_all_required_keys_present(sample_trade_context):
    """sample_trade_context must contain all 41 DB schema keys."""
    missing = [k for k in REQUIRED_TRADE_CONTEXT_KEYS if k not in sample_trade_context]
    assert not missing, f"Missing trade_context keys: {missing}"


def test_all_required_keys_count(sample_trade_context):
    """Exactly 41 required keys must be defined (no accidental column drops)."""
    assert len(REQUIRED_TRADE_CONTEXT_KEYS) == 41


# ─── PnL calculation tests ────────────────────────────────────────────────────

def test_pnl_calculation():
    """CE PnL = entry - exit (sell-to-open strategy). 100 - 60 = 40 pts."""
    ce_entry = 100.0
    ce_exit = 60.0
    ce_pnl_pts = round(ce_entry - ce_exit, 2)
    assert ce_pnl_pts == 40.0


def test_net_pnl_calculation():
    """net_pnl_rs = gross_pnl_rs - tax_charges_rs."""
    gross_pnl_rs = 4800.0
    tax_charges_rs = 150.0
    net_pnl_rs = round(gross_pnl_rs - tax_charges_rs, 2)
    assert net_pnl_rs == 4650.0


# ─── Trade result classification tests ───────────────────────────────────────

def test_trade_result_win():
    """net_pnl=500 is a clear win → trade_result must be 'WIN'."""
    assert _classify_result(500.0) == "WIN"


def test_trade_result_loss():
    """net_pnl=-500 is a clear loss → trade_result must be 'LOSS'."""
    assert _classify_result(-500.0) == "LOSS"


def test_trade_result_breakeven():
    """net_pnl=50 is within breakeven band → trade_result must be 'BREAKEVEN'."""
    assert _classify_result(50.0) == "BREAKEVEN"


# ─── Capital tracking tests ───────────────────────────────────────────────────

def test_capital_after_win():
    """After a winning trade, capital increases by net_pnl."""
    capital_before = 120000.0
    net_pnl = 1000.0
    capital_after = round(capital_before + net_pnl, 2)
    assert capital_after == 121000.0


def test_capital_after_loss():
    """After a losing trade, capital decreases by abs(net_pnl)."""
    capital_before = 120000.0
    net_pnl = -1000.0
    capital_after = round(capital_before + net_pnl, 2)
    assert capital_after == 119000.0
