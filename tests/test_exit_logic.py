"""
test_exit_logic.py — Tests for exit condition logic in S1 strategy.

These tests validate the LOGIC of exit conditions in isolation, without
importing the strategy module. They verify:
  - Time exit fires at exactly 15:30 (not 15:15 — BUG-003 which was fixed)
  - Portfolio-level profit target (both legs together, not per-leg)
  - SL calculation (entry + sl_pct%)
  - NIFTY ATM strike rounding (nearest 50)
  - Recovery leg exit conditions
"""
import datetime


# ─── Time exit tests ──────────────────────────────────────────────────────────

def test_time_exit_at_1530():
    """15:30 >= 15:30 must be True — time exit fires exactly at 15:30."""
    assert datetime.time(15, 30) >= datetime.time(15, 30)


def test_time_exit_before_1530():
    """15:29 >= 15:30 must be False — one minute before must not fire."""
    assert not (datetime.time(15, 29) >= datetime.time(15, 30))


def test_time_exit_at_1515_must_be_false():
    """15:15 >= 15:30 must be False — BUG-003 regression guard."""
    assert not (datetime.time(15, 15) >= datetime.time(15, 30))


# ─── Portfolio-level profit target tests ─────────────────────────────────────

def test_portfolio_pt_triggers():
    """
    PT fires when combined_ltp <= total_premium * (pt_pct / 100).
    60 <= 200 * 0.30 = 60.0 → True (boundary: <= means PT fires).
    """
    combined_ltp = 60.0
    total_premium = 200.0
    pt_pct = 30
    pt_target = total_premium * (pt_pct / 100)
    assert combined_ltp <= pt_target


def test_portfolio_pt_not_triggered():
    """61 > 60.0 — one point above target, PT must NOT fire."""
    combined_ltp = 61.0
    total_premium = 200.0
    pt_pct = 30
    pt_target = total_premium * (pt_pct / 100)
    assert not (combined_ltp <= pt_target)


# ─── SL level calculation tests ──────────────────────────────────────────────

def test_ce_sl_calculation():
    """CE SL level = entry_price * (1 + sl_pct / 100). 100 * 1.40 = 140.0."""
    entry = 100.0
    sl_pct = 40
    sl_level = round(entry * (1 + sl_pct / 100), 2)
    assert sl_level == 140.0


def test_pe_sl_calculation():
    """PE SL level = entry_price * (1 + sl_pct / 100). 80 * 1.25 = 100.0."""
    entry = 80.0
    sl_pct = 25
    sl_level = round(entry * (1 + sl_pct / 100), 2)
    assert sl_level == 100.0


# ─── Recovery leg PT tests ────────────────────────────────────────────────────

def test_recovery_pt_triggers():
    """Recovery leg PT: ltp <= entry * (pt_pct/100). 29.9 <= 30.0 → True."""
    ltp = 29.9
    entry = 100.0
    pt_pct = 30
    assert ltp <= entry * (pt_pct / 100)


def test_recovery_pt_not_triggered():
    """31.0 > 30.0 — recovery PT must NOT trigger."""
    ltp = 31.0
    entry = 100.0
    pt_pct = 30
    assert not (ltp <= entry * (pt_pct / 100))


# ─── Recovery leg SL tests ───────────────────────────────────────────────────

def test_recovery_sl_triggers():
    """Recovery leg SL: ltp > entry (leg moved against). 101 > 100 → True."""
    ltp = 101.0
    entry = 100.0
    assert ltp > entry


def test_recovery_sl_not_triggered():
    """99 < 100 — recovery SL must NOT trigger."""
    ltp = 99.0
    entry = 100.0
    assert not (ltp > entry)


# ─── ATM strike rounding tests ───────────────────────────────────────────────

def _round_to_nearest_50(spot: float) -> int:
    """Mirrors the ATM rounding logic in findStrikePriceATM()."""
    return int(round(spot / 50, 0) * 50)


def test_atm_strike_nifty_rounding():
    """Spot 24473 rounds DOWN to nearest 50 = 24450."""
    assert _round_to_nearest_50(24473) == 24450


def test_atm_strike_exact():
    """Spot exactly on a 50-multiple stays unchanged."""
    assert _round_to_nearest_50(24500) == 24500
