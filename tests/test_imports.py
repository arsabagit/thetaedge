"""
test_imports.py — Smoke tests: verify every production module imports cleanly.

If any test in this file fails, it means a module has a broken import chain
(e.g. the auth crash that caused no-trade on 2026-04-27).
Run this first before every deploy: pytest tests/test_imports.py -v
"""
import sys


def test_auth_imports_cleanly():
    """shared.auth must have a module-level 'api' object after import."""
    import shared.auth as auth
    assert hasattr(auth, "api"), "shared.auth must export 'api' at module level"
    assert auth.api is not None, (
        "shared.auth.api is None — login failed or module-level export is missing"
    )


def test_order_manager_imports():
    """shared.order_manager imports without error (depends on shared.auth.api)."""
    import shared.order_manager  # noqa: F401


def test_capital_manager_imports():
    """shared.capital_manager imports without error."""
    import shared.capital_manager  # noqa: F401


def test_regime_config_imports():
    """shared.regime_config imports without error."""
    import shared.regime_config  # noqa: F401


def test_scheduler_imports():
    """shared.scheduler imports without error."""
    import shared.scheduler  # noqa: F401


def test_strategy_imports():
    """
    S1_straddle.algo_strike_straddle_s1 imports without error or sys.exit.

    conftest.py ensures shared.auth.api is non-None before this test runs,
    so initialize_api() returns the mock instead of triggering sys.exit(1).
    """
    # Ensure we get a fresh import (in case a previous run cached a bad state)
    sys.modules.pop("S1_straddle.algo_strike_straddle_s1", None)
    import S1_straddle.algo_strike_straddle_s1  # noqa: F401


def test_config_imports():
    """S1_straddle.config imports without error."""
    import S1_straddle.config  # noqa: F401
