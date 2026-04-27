"""
test_auth.py — Tests for shared/auth.py.

Verifies the module-level api export and initialize_api() function that were
added to fix the ImportError crash on 2026-04-27.
"""
import os
import pytest
from unittest.mock import patch, MagicMock


def test_api_object_exists():
    """shared.auth must export a module-level 'api' object that is not None."""
    import shared.auth as auth
    assert hasattr(auth, "api"), "shared.auth must have a module-level 'api'"
    assert auth.api is not None, (
        "shared.auth.api is None — login failed. "
        "Check .env credentials or network connectivity."
    )


def test_api_has_correct_type():
    """
    The api object must have the Shoonya trading methods expected by
    order_manager.py (duck-type check — works for both real and mock api).
    """
    import shared.auth as auth
    assert hasattr(auth.api, "get_quotes"), "api must have get_quotes method"
    assert hasattr(auth.api, "place_order"), "api must have place_order method"


def test_initialize_api_callable():
    """initialize_api must exist in shared.auth and be callable."""
    import shared.auth as auth
    assert hasattr(auth, "initialize_api"), (
        "shared.auth must export initialize_api() function"
    )
    assert callable(auth.initialize_api)


def test_initialize_api_returns_api():
    """initialize_api() must return the same api object (session already live)."""
    import shared.auth as auth
    result = auth.initialize_api()
    assert result is not None
    assert result is auth.api


def test_paper_trading_skips_real_login():
    """
    With PAPER_TRADING=1, placeOrder() must return 0 (simulated success)
    without ever calling the broker API.
    """
    os.environ["PAPER_TRADING"] = "1"
    from shared.order_manager import placeOrder
    result = placeOrder("NIFTY07MAY2026C24650", "SELL", 75, "MARKET", 0)
    assert result == 0, (
        f"PAPER_TRADING=1 must return 0 (simulated order), got {result}"
    )
