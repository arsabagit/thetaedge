import sqlite3
import datetime
import logging
from S1_straddle.config import PROD_DB_PATH

logger = logging.getLogger(__name__)

def log_trade_s1(trade_data: dict):
    """
    Logs a complete S1 trade record to the thetaedge_prod.db.
    Expects a dictionary with 35+ keys matching the trades_S1 schema.
    """
    try:
        conn = sqlite3.connect(PROD_DB_PATH)
        cursor = conn.cursor()
        
        columns = [
            "trade_date", "strategy", "vix_at_entry", "regime_label",
            "config_sl_pct", "config_pt_pct", "config_otm",
            "nifty_spot", "atm_strike",
            "ce_strike", "ce_entry_price", "ce_entry_time", "ce_exit_price", "ce_exit_time", "ce_sl_level", "ce_pt_level", "ce_pnl_pts", "ce_exit_reason",
            "pe_strike", "pe_entry_price", "pe_entry_time", "pe_exit_price", "pe_exit_time", "pe_sl_level", "pe_pt_level", "pe_pnl_pts", "pe_exit_reason",
            "total_premium", "total_pnl_pts", "total_pnl_rs", "lot_size", "qty", "gross_pnl_rs", "tax_charges_rs", "net_pnl_rs",
            "capital_before", "capital_after", "lots_traded",
            "trade_result", "exit_type", "paper_trading"
        ]
        
        placeholders = ", ".join(["?"] * len(columns))
        sql = f"INSERT INTO trades_S1 ({', '.join(columns)}) VALUES ({placeholders})"
        
        values = [trade_data.get(col) for col in columns]
        
        cursor.execute(sql, values)
        conn.commit()
        conn.close()
        logger.info(f"[SUCCESS] Trade logged to SQLite: {trade_data['trade_date']} | Net PnL: {trade_data['net_pnl_rs']}")
        return True
    except Exception as e:
        logger.error(f"[ERROR] Failed to log trade to SQLite: {e}")
        return False
