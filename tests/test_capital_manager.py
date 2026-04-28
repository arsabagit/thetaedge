"""
test_capital_manager.py — Tests for shared/capital_manager.py.

Covers lot sizing (dynamic pivot 2024-11-20), expiry calculation (nearest
Thursday with holiday fallback to Wednesday), and tax charge calculation.

NOTE ON DATES:
  April 28, 2026 (Monday): next Thursday is May 1 which is a NSE Holiday
  (Maharashtra Day). The expiry correctly moves to Wednesday April 30, 2026.
  Tests use May 4-14 2026 to avoid this holiday ambiguity.
"""
import datetime
import pytest
from shared.capital_manager import (
    get_lot_size,
    calculateLots,
    get_current_expiry,
    get_expiry_string,
    calculate_tax_charges,
    calculate_total_charges,
)


# ─── get_lot_size tests ───────────────────────────────────────────────────────

def test_lot_size_before_pivot():
    """Dates before 2024-11-20 must return lot size 50."""
    assert get_lot_size(datetime.date(2024, 11, 19)) == 50


def test_lot_size_on_pivot():
    """The pivot date 2024-11-20 itself must return lot size 75."""
    assert get_lot_size(datetime.date(2024, 11, 20)) == 75


def test_lot_size_after_pivot():
    """Current trading dates (2026+) must return lot size 75."""
    assert get_lot_size(datetime.date(2026, 4, 28)) == 75


# ─── calculateLots tests ─────────────────────────────────────────────────────

def test_calculate_lots_basic():
    """Capital == margin → exactly 1 lot."""
    lots, qty = calculateLots(current_capital=110000, margin_per_lot=110000)
    assert lots == 1
    assert qty == 75


def test_calculate_lots_minimum_one():
    """Capital < margin → floor would give 0, but minimum is enforced at 1."""
    lots, qty = calculateLots(current_capital=50000, margin_per_lot=110000)
    assert lots == 1
    assert qty == 75


def test_calculate_lots_max_override():
    """max_lots_override caps lots even when capital allows more."""
    lots, qty = calculateLots(
        current_capital=500000, margin_per_lot=110000, max_lots_override=2
    )
    assert lots == 2
    assert qty == 150


# ─── get_current_expiry tests ─────────────────────────────────────────────────

def test_get_expiry_monday():
    """Monday 2026-05-04 → nearest Thursday is 2026-05-07 (not a holiday)."""
    result = get_current_expiry(datetime.date(2026, 5, 4))
    assert result == datetime.date(2026, 5, 7)


def test_get_expiry_thursday():
    """Thursday 2026-05-07 (not a holiday) → same-day expiry."""
    result = get_current_expiry(datetime.date(2026, 5, 7))
    assert result == datetime.date(2026, 5, 7)


def test_get_expiry_friday():
    """Friday 2026-05-08 → next Thursday is 2026-05-14 (not a holiday)."""
    result = get_current_expiry(datetime.date(2026, 5, 8))
    assert result == datetime.date(2026, 5, 14)


def test_get_expiry_holiday_thursday():
    """
    When nearest Thursday IS a holiday, expiry moves back one day to Wednesday.
    2026-04-28 (Monday) → nearest Thursday is 2026-05-01 (Maharashtra Day holiday)
    → expiry must be 2026-04-30 (Wednesday).
    """
    result = get_current_expiry(datetime.date(2026, 4, 28))
    assert result == datetime.date(2026, 4, 30)


# ─── get_expiry_string tests ─────────────────────────────────────────────────

def test_expiry_string_format():
    """Expiry string must be DDMMMYY uppercase (2-digit year), e.g. '07MAY26' — Shoonya format."""
    result = get_expiry_string(datetime.date(2026, 5, 4))
    assert result == "07MAY26"
    assert result == result.upper(), "Expiry string must be uppercase"
    assert len(result) == 7, "Format must be DDMMMYY (7 chars), not DDMMMYYYY"


def test_expiry_string_monday():
    """Monday 2026-05-04 → expiry string '07MAY26' (2-digit year, not today's date)."""
    result = get_expiry_string(datetime.date(2026, 5, 4))
    assert result == "07MAY26"


# ─── calculate_tax_charges tests ─────────────────────────────────────────────

def test_tax_charges_keys():
    """calculate_tax_charges must return all required charge components."""
    result = calculate_tax_charges(qty=75, entry_price=100.0, exit_price=60.0)
    required_keys = {"stt", "exchange_charges", "sebi_charges", "gst", "stamp_duty", "total_charges"}
    assert required_keys.issubset(result.keys())


def test_tax_charges_zero_brokerage():
    """Shoonya is zero brokerage — brokerage must always be 0.0."""
    result = calculate_tax_charges(qty=75, entry_price=100.0, exit_price=60.0)
    assert result["brokerage"] == 0.0


def test_total_charges_both_legs():
    """calculate_total_charges must return a dict with 'tax_charges_rs' key."""
    result = calculate_total_charges(
        qty=75,
        ce_entry=100.0, ce_exit=60.0,
        pe_entry=80.0,  pe_exit=56.0,
    )
    assert "tax_charges_rs" in result
    assert result["tax_charges_rs"] > 0
