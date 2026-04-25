import requests
import logging
import sqlite3
from datetime import datetime, date
import shared.settings as settings

logger = logging.getLogger("Notifier")

# ── Strategy maps ───────────────────────────────────────────────────────────
_STRAT_ICON = {
    "IronCondor": "🦅",
    "ShortStrangle": "🐍",
}

_STRAT_NAME = {
    "IronCondor": "Iron Condor",
    "ShortStrangle": "Short Strangle",
}


def _mode_str():
    """Return human-readable trading mode."""
    return "Paper Trade" if settings.PAPER_TRADING else "LIVE ⚠️"


def _timestamp():
    """Return formatted IST timestamp."""
    return datetime.now().strftime("%d %b %Y %H:%M IST")


def _html_escape(text):
    """Escape HTML special characters in dynamic text."""
    return str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def send_telegram_alert(message, parse_mode="HTML"):
    """Send a Telegram alert. Message is sent as-is — caller formats."""
    token = settings.TELEGRAM_BOT_TOKEN
    chat_id = settings.TELEGRAM_CHAT_ID

    if not token or not chat_id:
        logger.warning(f"Telegram NOT configured. Alert logged instead:\n{message}")
        return False

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": parse_mode,
    }

    try:
        response = requests.post(url, json=payload, timeout=10)
        if response.status_code == 200:
            logger.debug("Telegram alert sent successfully.")
            return True
        else:
            logger.error(f"Telegram API Error: {response.status_code} - {response.text}")
            return False
    except requests.exceptions.Timeout:
        logger.error("Telegram request timed out (10s)")
        return False
    except Exception as e:
        logger.error(f"Failed to send Telegram alert: {e}")
        return False


# ── Rich alert helpers ──────────────────────────────────────────────────────

def alert_entry(strategy_type, leg_key, symbol, qty, price, mode="PAPER", sl=None):
    """Structured trade entry alert — bold header, emoji per line."""
    icon = _STRAT_ICON.get(strategy_type, "📊")
    name = _STRAT_NAME.get(strategy_type, strategy_type)
    leg_name = leg_key.replace("_", " ")
    mode_label = "Paper Trade" if mode == "PAPER" else "LIVE ⚠️"

    lines = [
        f"✅ <b>TRADE OPENED — {_html_escape(name)}</b>",
        "",
        f"{icon} Strategy: {_html_escape(name)}",
        f"📊 Leg: {_html_escape(leg_name)}",
        f"📈 Symbol: {_html_escape(symbol)}",
        f"💰 Entry: ₹{price:,.2f}",
        f"📦 Qty: {qty}",
    ]
    if sl is not None and sl > 0:
        sl_pts = sl - price
        lines.append(f"🛑 SL: ₹{sl:,.2f} (+{sl_pts:.0f} pts)")
    lines.extend([
        "",
        f"📋 Mode: {mode_label}",
        f"🕐 {_timestamp()}",
    ])
    send_telegram_alert("\n".join(lines))


def alert_exit(strategy_type, leg_key, symbol, qty, entry_price, exit_price,
               pnl_pts, pnl_rs, reason, duration_str="", daily_pnl=None, overall_pnl=None):
    """Structured trade exit alert — bold header with reason, emoji per line."""
    icon = _STRAT_ICON.get(strategy_type, "📊")
    name = _STRAT_NAME.get(strategy_type, strategy_type)
    leg_name = leg_key.replace("_", " ")
    pnl_pct = (pnl_rs / (entry_price * qty) * 100) if entry_price * qty else 0
    pnl_icon = "🟢" if pnl_rs >= 0 else "🔴"
    header_icon = "✅" if pnl_rs >= 0 else "🔴"

    lines = [
        f"{header_icon} <b>TRADE CLOSED — {_html_escape(reason)}</b>",
        "",
        f"{icon} Strategy: {_html_escape(name)}",
        f"📊 Leg: {_html_escape(leg_name)}",
        f"📈 Symbol: {_html_escape(symbol)}",
        f"💰 Entry: ₹{entry_price:,.2f} → Exit: ₹{exit_price:,.2f}",
        f"{pnl_icon} PnL: {pnl_pts:+.2f} pts | ₹{pnl_rs:+,.2f} ({pnl_pct:+.1f}%)",
    ]
    if duration_str:
        lines.append(f"⏱️ Duration: {duration_str}")
    if daily_pnl is not None:
        d_icon = "🟢" if daily_pnl >= 0 else "🔴"
        lines.append(f"💵 Daily PnL: {d_icon} ₹{daily_pnl:+,.2f}")
    if overall_pnl is not None:
        o_icon = "🟢" if overall_pnl >= 0 else "🔴"
        lines.append(f"💼 Overall PnL: {o_icon} ₹{overall_pnl:+,.2f}")
    lines.extend([
        "",
        f"📋 Mode: {_mode_str()}",
        f"🕐 {_timestamp()}",
    ])
    send_telegram_alert("\n".join(lines))


def alert_eod_status(strategy_type, db_path):
    """End-of-day summary — bold header, emoji per line."""
    icon = _STRAT_ICON.get(strategy_type, "📊")
    name = _STRAT_NAME.get(strategy_type, strategy_type)
    today_str = date.today().isoformat()
    try:
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()

        cur.execute(
            "SELECT COUNT(*), COALESCE(SUM(pnl),0) FROM trades "
            "WHERE status='CLOSED' AND date(exit_time)=?", (today_str,)
        )
        day_count, day_pnl = cur.fetchone()

        cur.execute("SELECT COUNT(*), COALESCE(SUM(pnl),0) FROM trades WHERE status='CLOSED'")
        total_count, total_pnl = cur.fetchone()

        conn.close()
    except Exception as e:
        logger.error(f"EOD status query failed: {e}")
        send_telegram_alert(
            f"📊 <b>END OF DAY — {_html_escape(name)}</b>\n\n"
            f"❌ Failed to read DB: {_html_escape(str(e))}"
        )
        return

    day_icon = "🟢" if day_pnl >= 0 else "🔴"
    total_icon = "🟢" if total_pnl >= 0 else "🔴"
    lines = [
        f"📊 <b>END OF DAY — {_html_escape(name)}</b>",
        "",
        f"{icon} Strategy: {_html_escape(name)}",
        f"📅 Date: {today_str}",
        f"📈 Today: {day_count} trades | {day_icon} ₹{day_pnl:+,.2f}",
        f"💼 Overall: {total_count} trades | {total_icon} ₹{total_pnl:+,.2f}",
        "",
        f"📋 Mode: {_mode_str()}",
        f"🕐 {_timestamp()}",
    ]
    send_telegram_alert("\n".join(lines))


def get_pnl_summary(db_path):
    """Return (daily_pnl, overall_pnl) for embedding in trade alerts."""
    today_str = date.today().isoformat()
    try:
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        cur.execute(
            "SELECT COALESCE(SUM(pnl),0) FROM trades "
            "WHERE status='CLOSED' AND date(exit_time)=?", (today_str,)
        )
        daily = cur.fetchone()[0]
        cur.execute("SELECT COALESCE(SUM(pnl),0) FROM trades WHERE status='CLOSED'")
        overall = cur.fetchone()[0]
        conn.close()
        return daily, overall
    except Exception:
        return None, None

