import time
import datetime
import uuid
import logging
from config import settings
from src.utils.date_utils import get_next_thursday, format_date_for_symbol
from src.database.db_manager import DBManager

from src.utils.notifier import send_telegram_alert, alert_entry, alert_exit, alert_eod_status, get_pnl_summary
from src.strategy.iron_condor.wing_calculator import compute_hedge_strike
from src.strategy.iron_condor.risk_manager import (
    initial_sl as ic_initial_sl,
    compute_tsl as ic_compute_tsl,
    is_sl_hit as ic_is_sl_hit,
    cross_to_cost_sl,
    is_max_loss_breached,
)
from src.strategy.short_strangle_sidewinder.risk_manager import (
    initial_sl as ss_initial_sl,
    compute_tsl as ss_compute_tsl,
    is_sl_hit as ss_is_sl_hit,
)

logger = logging.getLogger("StrategyEngine")

class StrategyEngine:
    def __init__(self, api, mode=1, strategy="ShortStrangle"):
        self.api = api
        self.db = DBManager(strategy_type=strategy)
        self.mode = mode # 0: Live, 1: Paper, 2: Backtest
        self.strategy_type = strategy # "ShortStrangle" or "IronCondor"
        
        # Legs: CE_SELL, PE_SELL, CE_BUY, PE_BUY
        self.legs = {
            "CE_SELL": self._init_leg_state("CE_SELL"),
            "PE_SELL": self._init_leg_state("PE_SELL"),
            "CE_BUY": self._init_leg_state("CE_BUY"),
            "PE_BUY": self._init_leg_state("PE_BUY")
        }
        self.last_filter_alert = 0 # Throttle for VIX/Gap alerts
        self.final_abort_sent = False # Final 11:01 alert flag
        
        from offline_downloader import OfflineDownloader
        from src.utils.date_utils import format_date_for_symbol
        downloader = OfflineDownloader()
        
        # Load master and find exact active expiry
        master_df = downloader.load_nfo_master()
        target_index = settings.TARGET_INDEX
        self.expiry_str = format_date_for_symbol(downloader.get_actual_expiry(target_index, datetime.datetime.now()))
        self.target_index = target_index
        
        # Expert Audit Hardening: Recovery Process
        # Check if there are "OPEN" trades in the DB that we should manage
        open_trades = self.db.get_recent_open_trades(self.strategy_type)
        if open_trades:
            logger.info(f"Recovery Mode: Found {len(open_trades)} orphaned trades in DB. Re-adopting...")
            for t in open_trades:
                leg_key = t["type"] # e.g. "CE_SELL"
                if leg_key in self.legs:
                    self.legs[leg_key].update({
                        "id": t["id"],
                        "symbol": t["symbol"],
                        "token": t.get("token"), 
                        "entry_price": t["entry_price"],
                        "qty": t["quantity"],
                        "sl": ic_initial_sl(t["entry_price"]) if "SELL" in leg_key else 0,
                        "last_trail_ref": t["entry_price"],
                        "active": True
                    })
                    # Re-resolve Token if missing in DB
                    if not self.legs[leg_key].get("token"):
                        # This avoids a crash if token wasn't stored in old DB schema
                        # StrategyEngine logic is already in scope, no import needed.
                        pass

        logger.info(f"Strategy Engine Initialized. Mode: {self.mode}, Strategy: {self.strategy_type}, Expiry: {self.expiry_str}")

    def _init_leg_state(self, leg_type):
        return {
            "id": str(uuid.uuid4())[:8],
            "type": leg_type,
            "symbol": None,
            "entry_price": 0,
            "sl": 0,
            "qty": 0,
            "active": False,
            "last_trail_ref": 0,
            "ttp_active": False,
            "ttp_high": 0
        }

    def get_ltp(self, exchange, token, expected_symbol=None, entry_price=None):
        try:
            ret = self.api.get_quotes(exchange=exchange, token=str(token))
            if ret and 'lp' in ret:
                quote_symbol = str(ret.get("tsym", "")).strip().upper()
                expected = str(expected_symbol or "").strip().upper()

                # Defensive guard: if token resolves to a different symbol,
                # retry a few times because Shoonya occasionally returns
                # transient wrong snapshots.
                if expected and quote_symbol and quote_symbol != expected:
                    matched = False
                    ltp = -1.0
                    for _ in range(3):
                        time.sleep(0.05)
                        retry = self.api.get_quotes(exchange=exchange, token=str(token))
                        if not retry or 'lp' not in retry:
                            continue
                        retry_symbol = str(retry.get("tsym", "")).strip().upper()
                        if retry_symbol == expected:
                            ltp = float(str(retry['lp']).replace(",", ""))
                            matched = True
                            break

                    if not matched:
                        logger.warning(
                            "Quote symbol mismatch for token %s: expected %s, got %s",
                            token,
                            expected,
                            quote_symbol,
                        )
                        return -1.0
                else:
                    ltp = float(str(ret['lp']).replace(",", ""))

                # Defensive guard: re-confirm extreme spikes before using them.
                if entry_price and entry_price > 0 and ltp > 0:
                    spike_mult = getattr(settings, "QUOTE_SPIKE_MULTIPLIER", 8.0)
                    if ltp >= (entry_price * spike_mult):
                        confirm = self.api.get_quotes(exchange=exchange, token=str(token))
                        if not confirm or 'lp' not in confirm:
                            logger.warning(
                                "Spike check failed for %s (token %s): no confirm quote",
                                expected or token,
                                token,
                            )
                            return -1.0

                        confirm_symbol = str(confirm.get("tsym", "")).strip().upper()
                        if expected and confirm_symbol and confirm_symbol != expected:
                            logger.warning(
                                "Spike confirm mismatch for token %s: expected %s, got %s",
                                token,
                                expected,
                                confirm_symbol,
                            )
                            return -1.0

                        confirm_ltp = float(str(confirm['lp']).replace(",", ""))
                        if confirm_ltp >= (entry_price * spike_mult):
                            logger.warning(
                                "Ignoring anomalous LTP for %s: %.2f / %.2f (entry %.2f, x%.1f)",
                                expected or token,
                                ltp,
                                confirm_ltp,
                                entry_price,
                                spike_mult,
                            )
                            return -1.0
                        ltp = confirm_ltp

                return ltp
            return -1.0
        except:
            return -1.0

    def find_strikes(self):
        """Elite token discovery searching for target premiums."""
        import pandas as pd
        import os
        master_path = "data/historical/NFO_symbols.csv"
        if not os.path.exists(master_path):
            logger.error("NFO_symbols.csv missing. Run offline_downloader.py first.")
            return None
        
        master_df = pd.read_csv(master_path, low_memory=False)
        idx = self.target_index
        idx_token = settings.NIFTY_TOKEN if idx == "NIFTY" else settings.BANKNIFTY_TOKEN
        
        spot = self.get_ltp("NSE", idx_token)
        if spot == -1: return None
        
        round_base = 50 if idx == "NIFTY" else 100
        atm_strike = int(round(spot / round_base) * round_base)
        
        # Search range: ATM +/- 15 strikes
        strikes_to_scan = [atm_strike + (i * round_base) for i in range(-15, 16)]
        
        all_tokens = []
        token_to_sym = {}
        for s in strikes_to_scan:
            for opt in ['C', 'P']:
                sym = f"{idx}{self.expiry_str}{opt}{s}"
                match = master_df[master_df['TradingSymbol'] == sym]
                if not match.empty:
                    tok = str(match.iloc[0]['Token'])
                    all_tokens.append(tok)
                    token_to_sym[tok] = {"sym": sym, "strike": s, "type": 'CE' if opt == 'C' else 'PE'}

        if not all_tokens: return None

        # Fetch all premiums sequentially (Bulk get_quotes buggy on some server environments)
        prices = {}
        for tok in all_tokens:
            try:
                res = self.api.get_quotes(exchange="NFO", token=tok)
                if res and 'lp' in res:
                    prices[tok] = float(res['lp'])
                time.sleep(0.05) # Small throttle to avoid API rate limits
            except:
                continue

        if not prices: return None

        # Find Best Matches
        def find_best(opt_type, target):
            best_tok = None
            min_diff = 9999
            for tok, p in prices.items():
                if token_to_sym[tok]['type'] == opt_type:
                    diff = abs(p - target)
                    if diff < min_diff:
                        min_diff = diff
                        best_tok = tok
            return best_tok

        def lookup_token(symbol):
            match = master_df[master_df['TradingSymbol'] == symbol]
            if not match.empty:
                return str(match.iloc[0]['Token'])
            return None

        results = {"atm_strike": atm_strike, "spot": spot}
        matches = [
            ("CE_SELL", settings.TARGET_PREMIUM, "CE"),
            ("PE_SELL", settings.TARGET_PREMIUM, "PE"),
        ]

        for key, target, opt_type in matches:
            tok = find_best(opt_type, target)
            if tok:
                results[f"{key}_TOK"] = tok
                sym = token_to_sym[tok]['sym']
                results[f"{key}_SYM"] = sym
                sold_strike = token_to_sym[tok]['strike']
                
                # Expert Audit: WING_DISTANCE logic for Iron Condor hedges
                if self.strategy_type == "IronCondor":
                    buy_key = key.replace("SELL", "BUY")
                    hedge_strike = compute_hedge_strike(sold_strike, opt_type)
                    
                    hedge_opt = "C" if opt_type == "CE" else "P"
                    hedge_sym = f"{idx}{self.expiry_str}{hedge_opt}{hedge_strike}"
                    hedge_tok = lookup_token(hedge_sym)
                    if hedge_tok:
                        results[f"{buy_key}_TOK"] = hedge_tok
                        results[f"{buy_key}_SYM"] = hedge_sym
                    else:
                        logger.warning(f"Could not find hedge token for {hedge_sym}")
        
        return results

    def entry_protocol(self):
        strikes = self.find_strikes()
        if not strikes or "CE_SELL_TOK" not in strikes: return
        
        spot = strikes.get('spot', 0)
        vix = self.get_ltp("NSE", settings.VIX_TOKEN)
        
        # Expert Audit: VIX Filter (CONSERVATIVE: Assume unsafe if fetch fails)
        if vix == -1.0:
            # API failure: Assume worst-case (high volatility)
            logger.warning("VIX fetch failed — assuming unsafe market, skipping entry")
            if time.time() - self.last_filter_alert > 1800:
                send_telegram_alert(
                    "⚠️ <b>ENTRY SKIPPED — VIX Unavailable</b>\n\n"
                    "🌡️ India VIX fetch failed\n"
                    "🛡️ Assuming unsafe market conditions\n"
                    "⏭️ Skipping entry for safety"
                )
                self.last_filter_alert = time.time()
            return
        
        max_vix_allowed = getattr(settings, "MAX_VIX_TO_TRADE", 24.0)
        if vix > max_vix_allowed:
            logger.warning(f"VIX {vix:.2f} exceeds limit {max_vix_allowed:.2f} — skipping entry")
            # Throttle alerts to once every 30 mins
            if time.time() - self.last_filter_alert > 1800:
                send_telegram_alert(
                    f"⚠️ <b>ENTRY SKIPPED — VIX Too High</b>\n\n"
                    f"🌡️ India VIX: {vix:.2f}\n"
                    f"🚫 Limit: {max_vix_allowed:.2f}\n"
                    f"⏭️ Entry aborted for safety"
                )
                self.last_filter_alert = time.time()
            return
        
        logger.info(f"✅ VIX CHECK PASSED: India VIX = {vix:.2f} (limit: {max_vix_allowed:.2f})")

        # Expert Audit: Gap Protection
        idx_token = settings.NIFTY_TOKEN if self.target_index == "NIFTY" else settings.BANKNIFTY_TOKEN
        quote = self.api.get_quotes(exchange="NSE", token=idx_token)
        gap_pts = 0
        if quote and 'pc' in quote:
            prev_close = float(quote['pc'])
            gap_pts = abs(spot - prev_close)
            if gap_pts > getattr(settings, "GAP_PROTECTION_POINTS", 150):
                logger.warning(f"Market gap {gap_pts:.2f} pts exceeds limit {settings.GAP_PROTECTION_POINTS}")
                # Throttle alerts to once every 30 mins
                if time.time() - self.last_filter_alert > 1800:
                    send_telegram_alert(
                        f"⚠️ <b>ENTRY SKIPPED — Market Gap</b>\n\n"
                        f"📉 Gap: {gap_pts:.2f} pts from prev close\n"
                        f"🚫 Limit: {settings.GAP_PROTECTION_POINTS} pts\n"
                        f"⏭️ Entry aborted for safety"
                    )
                    self.last_filter_alert = time.time()
                return

        qty = settings.INDEX_LOT_SIZES.get(self.target_index, 25)
        
        # Order Execution Priority: BUY first for margin efficiency
        leg_priorities = []
        if self.strategy_type == "IronCondor":
            leg_priorities.append([("CE_BUY", "CE_BUY_TOK", "CE_BUY_SYM"), ("PE_BUY", "PE_BUY_TOK", "PE_BUY_SYM")])
        
        leg_priorities.append([("CE_SELL", "CE_SELL_TOK", "CE_SELL_SYM"), ("PE_SELL", "PE_SELL_TOK", "PE_SELL_SYM")])

        for priority_group in leg_priorities:
            for leg_key, tok_key, sym_key in priority_group:
                if tok_key not in strikes: continue
                
                sym = strikes[sym_key]
                tok = strikes[tok_key]
                leg = self.legs[leg_key]
                
                price = self.get_ltp("NFO", tok)
                if price <= 0: price = 1.0 # Fallback for paper trades
                
                sl_val = 0
                if "SELL" in leg_key:
                    sl_val = ss_initial_sl(price) if self.strategy_type == "ShortStrangle" else ic_initial_sl(price)
                
                leg.update({
                    "symbol": sym, "token": tok, "entry_price": price,
                    "qty": qty, "sl": sl_val, "last_trail_ref": price,
                    "entry_time": datetime.datetime.now(), "active": True
                })
                
                self.db.log_trade({
                    "id": leg["id"], "symbol": sym, "type": leg["type"],
                    "entry_price": price, "quantity": qty, 
                    "entry_time": datetime.datetime.now().isoformat(),
                    "status": "OPEN", "mode": "LIVE" if self.mode == 0 else "PAPER",
                    "strategy": self.strategy_type,
                    "vix": vix, "gap_pts": gap_pts, "atm_strike": strikes.get('atm_strike'),
                    "target_premium": settings.TARGET_PREMIUM if "SELL" in leg_key else getattr(settings, "HEDGE_PREMIUM", 2.0),
                    "token": tok
                })
                
                if settings.PAPER_TRADING == 0 and self.mode == 0:
                    side = 'S' if "SELL" in leg_key else 'B'
                    logger.info(f"PLACING LIVE ORDER: {side} {sym} @ {price}")
                    alert_entry(self.strategy_type, leg_key, sym, qty, price, mode="LIVE", sl=sl_val or None)
                    
                    res = self.api.place_order(
                        buy_or_sell=side, product_type='M', exchange='NFO', 
                        symbol=sym, quantity=qty, price_type='LMT', price=price
                    )
                    if res and res.get('stat') == 'Ok':
                        ord_id = res['norenordno']
                        # Expert Audit: Margin/Rejection Check
                        time.sleep(0.5) 
                        history = self.api.single_order_history(ord_id)
                        if history and any(h.get('status') == 'Rejected' for h in history):
                            reason = history[0].get('rejreason', 'Unknown rejection')
                            self.db.add_log("ERROR", "Execution", f"Rejection for {sym}: {reason}")
                            if "SELL" in leg_key: # Only critical for sells
                                self.exit_all("MARGIN REJECTED")
                                return
                else:
                    logger.info(f"PAPER TRADE ENTRY: {sym} @ {price}")
                    alert_entry(self.strategy_type, leg_key, sym, qty, price, mode="PAPER", sl=sl_val or None)
            
            # Small delay between Buy and Sell groups for margin system to sync
            if len(leg_priorities) > 1: time.sleep(1)

    def risk_sentry(self, leg_key):
        leg = self.legs[leg_key]
        if not leg["active"]: return

        ltp = self.get_ltp(
            "NFO",
            leg["token"],
            expected_symbol=leg.get("symbol"),
            entry_price=leg.get("entry_price"),
        )
        if ltp == -1: return

        # Only Sellers have risk sentry for now
        if "SELL" in leg_key:
            # 1. Stop Loss (Fixed point logic)
            if ic_is_sl_hit(ltp, leg["sl"]) if self.strategy_type != "ShortStrangle" else ss_is_sl_hit(ltp, leg["sl"]):
                logger.info(f"[SL HIT] {leg_key}: LTP {ltp:.2f} >= SL {leg['sl']:.2f}")
                self.exit_leg(leg_key, ltp, "SL HIT")
                
                # Cross-to-Cost (CTC) logic for the other leg
                other_sell = "PE_SELL" if leg_key == "CE_SELL" else "CE_SELL"
                if self.legs[other_sell]["active"]:
                    self.legs[other_sell]["sl"] = cross_to_cost_sl(self.legs[other_sell])
                    logger.info(f"[CTC] Moving {other_sell} SL to cost ({self.legs[other_sell]['sl']:.2f})")
                return

            # 2. Trail-to-Cost (TTP) / TSL logic using points
            profit_pts = leg["entry_price"] - ltp
            if profit_pts >= settings.TTP_ACTIVATION and not leg["ttp_active"]:
                leg["ttp_active"] = True
                leg["sl"] = leg["entry_price"] # Move to cost
                logger.info(f"[TTP] {leg_key} profit {profit_pts:.2f} >= {settings.TTP_ACTIVATION}. SL at cost.")
            
            # Trailing Stop-Loss Ratchet (Points based)
            if self.strategy_type == "ShortStrangle":
                new_sl = ss_compute_tsl(leg["entry_price"], ltp, leg["sl"])
            else:
                new_sl = ic_compute_tsl(leg["entry_price"], ltp, leg["sl"])
            if new_sl < leg["sl"]:
                leg["sl"] = new_sl
                leg["last_trail_ref"] = ltp
                logger.info(f"[TSL] {leg_key} new SL: {new_sl:.2f}")

    def exit_leg(self, leg_key, price, reason):
        leg = self.legs[leg_key]
        if not leg["active"]: return
        
        # Limit price buffer for buying back
        exit_limit = round((price * (1 + settings.BUFFER_PERCENTAGE)) * 20) / 20
        
        leg["active"] = False
        side_mult = 1 if "SELL" in leg_key else -1
        pnl = (leg["entry_price"] - price) * leg["qty"] * side_mult
        
        self.db.log_trade({
            "id": leg["id"], "exit_price": price,
            "exit_time": datetime.datetime.now().isoformat(),
            "pnl": pnl, "status": "CLOSED"
        })
        
        logger.info(f"EXIT {leg_key} ({reason}): {leg['symbol']} @ {price:.2f} | PnL: {pnl:.2f}")

        if settings.PAPER_TRADING == 0 and self.mode == 0:
            side = 'B' if "SELL" in leg_key else 'S'
            self.api.place_order(
                buy_or_sell=side, product_type='M', 
                exchange='NFO', symbol=leg["symbol"], 
                quantity=leg["qty"], price_type='LMT', price=exit_limit
            )
        else:
            logger.info(f"PAPER TRADE EXIT: {leg['symbol']} @ {exit_limit}")
            
        # Enhanced Telegram Alert with daily/overall PnL
        duration_str = ""
        if leg.get("entry_time"):
            dur = datetime.datetime.now() - leg["entry_time"]
            hours, remainder = divmod(dur.seconds, 3600)
            minutes, _ = divmod(remainder, 60)
            duration_str = f"{hours}h {minutes}m"

        side_mult = 1 if "SELL" in leg_key else -1
        pnl_pts = (leg["entry_price"] - price) * side_mult
        daily_pnl, overall_pnl = get_pnl_summary(self.db.db_path)

        alert_exit(
            self.strategy_type, leg_key, leg["symbol"], leg["qty"],
            leg["entry_price"], price, pnl_pts, pnl, reason,
            duration_str=duration_str, daily_pnl=daily_pnl, overall_pnl=overall_pnl,
        )

    def exit_all(self, reason):
        for k in self.legs:
            if self.legs[k]["active"]:
                current_ltp = self.get_ltp(
                    "NFO",
                    self.legs[k]["token"],
                    expected_symbol=self.legs[k].get("symbol"),
                    entry_price=self.legs[k].get("entry_price"),
                )
                if current_ltp == -1: current_ltp = self.legs[k]["entry_price"]
                self.exit_leg(k, current_ltp, reason)

    def check_portfolio_max_loss(self):
        """
        CRITICAL RISK MANAGEMENT: Exit all positions if portfolio M2M breaches MAX_LOSS_PER_DAY.
        Called every cycle when any leg is active.
        """
        total_pnl_m2m = 0.0
        for leg_key, leg in self.legs.items():
            if not leg.get("active"):
                continue
            ltp = self.get_ltp(
                "NFO",
                leg["token"],
                expected_symbol=leg.get("symbol"),
                entry_price=leg.get("entry_price"),
            )
            if ltp == -1:
                logger.warning(
                    "Could not fetch validated LTP for %s (token %s)",
                    leg_key,
                    leg.get("token"),
                )
                continue
            side_mult = 1 if "SELL" in leg_key else -1
            total_pnl_m2m += (leg["entry_price"] - ltp) * leg["qty"] * side_mult
        active_legs = [k for k, v in self.legs.items() if v.get("active")]
        
        # Check breach
        if is_max_loss_breached(total_pnl_m2m):
            logger.critical(f"PORTFOLIO MAX LOSS: M2M ₹{total_pnl_m2m:.2f} < limit ₹{settings.MAX_LOSS_PER_DAY:.2f}")
            send_telegram_alert(
                f"🔥 <b>PORTFOLIO MAX LOSS BREACHED</b>\n\n"
                f"💸 Current M2M: ₹{total_pnl_m2m:,.2f}\n"
                f"🚫 Limit: ₹{settings.MAX_LOSS_PER_DAY:,.2f}\n"
                f"📊 Active legs: {', '.join(active_legs)}\n"
                f"⚠️ Closing all positions immediately"
            )
            self.exit_all("PORTFOLIO_MAX_LOSS_BREACH")
            return False
        
        return True

    def run_cycle(self):
        now = datetime.datetime.now()
        now_str = now.strftime("%H:%M")
        
        # Logic: Enter if time is >= Start and <= Window End
        # We stop searching for entries after 11:00 AM to avoid decaying premiums
        ENTRY_WINDOW_END = "11:00"
        is_trade_window = now_str >= settings.TRADE_START_TIME and now_str < ENTRY_WINDOW_END
        
        if is_trade_window and not any(l["active"] for l in self.legs.values()):
            if not self.db.has_traded_today(self.strategy_type):
                logger.info(f"Initiating Entry Protocol (Time: {now_str})")
                self.entry_protocol()
        
        # Expert Audit: Final Abort Alert at 11:01
        if now_str >= "11:01" and now_str < settings.UNIVERSAL_EXIT_TIME:
            if not self.final_abort_sent and not any(l["active"] for l in self.legs.values()):
                if not self.db.has_traded_today(self.strategy_type):
                    logger.info("No entry found by 11:00 AM. Aborting session.")
                    send_telegram_alert(
                        "🛑 <b>SESSION ABORTED</b>\n\n"
                        "⏰ No suitable entry found by 11:00 AM\n"
                        "📋 Giving up for today"
                    )
                    self.final_abort_sent = True
            
        # Portfolio-level max-loss check (uses validated quotes with anomaly guard).
        if any(l["active"] for l in self.legs.values()):
            if not self.check_portfolio_max_loss():
                return False

        if now_str >= settings.UNIVERSAL_EXIT_TIME:
            if any(l["active"] for l in self.legs.values()):
                send_telegram_alert(
                    "⏰ <b>UNIVERSAL EXIT — 15:15</b>\n\n"
                    "🔔 Market closing window reached\n"
                    "📤 Closing all remaining positions"
                )
                self.exit_all("TIME EXIT")
            alert_eod_status(self.strategy_type, self.db.db_path)
            return False

        # Expert Audit: Green Lock (14:00 PM Logic)
        if now_str >= settings.PROFIT_LOCK_TIME:
            active_legs = [l for l in self.legs.values() if l["active"]]
            if active_legs:
                # Check if ALL active legs are profitable
                all_green = True
                for k, leg in self.legs.items():
                    if leg["active"]:
                        curr_ltp = self.get_ltp("NFO", leg["token"])
                        if curr_ltp != -1:
                            side_mult = 1 if "SELL" in k else -1
                            leg_pnl = (leg["entry_price"] - curr_ltp) * side_mult
                            if leg_pnl <= 0:
                                all_green = False
                                break
                
                if all_green:
                    send_telegram_alert(
                        f"🟢 <b>GREEN LOCK ACTIVATED — {settings.PROFIT_LOCK_TIME}</b>\n\n"
                        f"✅ All legs profitable\n"
                        f"🔒 Locking in gains"
                    )
                    self.exit_all("GREEN LOCK (14:00)")
                    return False

        for k in self.legs:
            if self.legs[k]["active"]: self.risk_sentry(k)
        
        return True
