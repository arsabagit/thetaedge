"""
test_regime_config.py — Tests for RegimeConfig (shared/regime_config.py).

RegimeConfig is the SINGLE SOURCE OF TRUTH for all strategy parameters.
Every parameter value is tested here so deviations are caught immediately.
"""
import pytest
from shared.regime_config import RegimeConfig


# ─── VIX Threshold boundary tests ────────────────────────────────────────────

def test_high_vix_mode():
    """VIX=17.0 (above threshold) must return CONFIG_A (HIGH_VIX_MODE)."""
    config = RegimeConfig.get_config(17.0)
    assert config["label"] == "HIGH_VIX_MODE"


def test_low_vix_mode():
    """VIX=15.0 (below threshold) must return CONFIG_B (LOW_VIX_MODE)."""
    config = RegimeConfig.get_config(15.0)
    assert config["label"] == "LOW_VIX_MODE"


def test_exact_threshold():
    """VIX=16.5 (exactly at threshold) must return CONFIG_A — >= means HIGH."""
    config = RegimeConfig.get_config(16.5)
    assert config["label"] == "HIGH_VIX_MODE"


def test_just_below_threshold():
    """VIX=16.49 (just below threshold) must return CONFIG_B (LOW_VIX_MODE)."""
    config = RegimeConfig.get_config(16.49)
    assert config["label"] == "LOW_VIX_MODE"


# ─── Entry time tests ─────────────────────────────────────────────────────────

def test_high_vix_entry_time():
    """HIGH_VIX_MODE entry time must be 09:25."""
    assert RegimeConfig.CONFIG_A["entry_time"] == "09:25"


def test_low_vix_entry_time():
    """LOW_VIX_MODE entry time must be 09:20."""
    assert RegimeConfig.CONFIG_B["entry_time"] == "09:20"


# ─── Stop-loss tests ──────────────────────────────────────────────────────────

def test_high_vix_sl():
    """HIGH_VIX_MODE stop-loss must be 40%."""
    assert RegimeConfig.CONFIG_A["sl_pct"] == 40


def test_low_vix_sl():
    """LOW_VIX_MODE stop-loss must be 25%."""
    assert RegimeConfig.CONFIG_B["sl_pct"] == 25


# ─── Profit target tests ──────────────────────────────────────────────────────

def test_high_vix_pt():
    """HIGH_VIX_MODE profit target must be 70%."""
    assert RegimeConfig.CONFIG_A["profit_target_pct"] == 70


def test_low_vix_pt():
    """LOW_VIX_MODE profit target must be 30%."""
    assert RegimeConfig.CONFIG_B["profit_target_pct"] == 30


# ─── OTM offset tests ─────────────────────────────────────────────────────────

def test_high_vix_otm():
    """HIGH_VIX_MODE OTM offset must be 100 points."""
    assert RegimeConfig.CONFIG_A["otm"] == 100


def test_low_vix_otm():
    """LOW_VIX_MODE OTM offset must be 150 points."""
    assert RegimeConfig.CONFIG_B["otm"] == 150


# ─── Threshold constant test ──────────────────────────────────────────────────

def test_vix_threshold_value():
    """VIX_THRESHOLD must be exactly 16.5 — locked design decision."""
    assert RegimeConfig.VIX_THRESHOLD == 16.5
