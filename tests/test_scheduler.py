"""
test_scheduler.py — Tests for shared/scheduler.py.

Tests the holiday check logic and the morning_startup() function.
All external calls (Telegram, subprocess, VIX fetch) are mocked.
"""
import datetime
import pytest
from unittest.mock import patch, MagicMock, call
from shared.holiday_calendar import is_trading_day


# ─── is_trading_day tests ─────────────────────────────────────────────────────

def test_trading_day_monday():
    """Monday 2026-05-04 is not a holiday → must return True."""
    assert is_trading_day(datetime.date(2026, 5, 4)) is True


def test_trading_day_saturday():
    """Saturday is always a non-trading day → must return False."""
    assert is_trading_day(datetime.date(2026, 5, 2)) is False


def test_trading_day_sunday():
    """Sunday is always a non-trading day → must return False."""
    assert is_trading_day(datetime.date(2026, 5, 3)) is False


def test_holiday_check():
    """2026-05-01 (Maharashtra Day) is in NSE_HOLIDAYS_2026 → must return False."""
    assert is_trading_day(datetime.date(2026, 5, 1)) is False


# ─── morning_startup() tests ─────────────────────────────────────────────────

@patch("shared.scheduler.send_telegram_alert")
@patch("shared.scheduler.is_trading_day", return_value=False)
@patch("subprocess.Popen")
def test_morning_startup_no_trade_on_holiday(mock_popen, mock_trading_day, mock_tg):
    """
    On a holiday, morning_startup() must:
      - Send a holiday Telegram alert
      - NOT launch subprocess.Popen
      - Return False
    """
    from shared.scheduler import morning_startup

    result = morning_startup()

    assert result is False
    mock_tg.assert_called_once()
    mock_popen.assert_not_called()


@patch("shared.scheduler.send_telegram_alert")
@patch("shared.scheduler.is_trading_day", return_value=True)
@patch("shared.market_data_fetcher.fetch_and_save_vix", return_value=15.0)
@patch("subprocess.Popen")
@patch("builtins.open", MagicMock())          # prevent log file creation
@patch("os.makedirs", MagicMock())            # prevent log dir creation
def test_morning_startup_launches_strategy(
    mock_popen, mock_vix, mock_trading_day, mock_tg
):
    """
    On a trading day, morning_startup() must:
      - Call fetch_and_save_vix to get VIX
      - Send a Telegram regime alert
      - Launch the strategy via subprocess.Popen
      - Return True
    """
    from shared.scheduler import morning_startup

    result = morning_startup()

    assert result is True
    mock_tg.assert_called_once()

    # Popen must have been called with the strategy script path
    assert mock_popen.called
    popen_args = mock_popen.call_args[0][0]   # first positional arg = cmd list
    assert any("algo_strike_straddle_s1" in arg for arg in popen_args), (
        f"Expected strategy script in Popen args, got: {popen_args}"
    )
