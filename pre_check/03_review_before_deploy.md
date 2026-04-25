# ThetaEdge — Pre-Deploy Safety Review
# Paste this before switching PAPER_TRADING=0 or deploying to Hetzner

You are doing a pre-deployment safety review of ThetaEdge.

## Review checklist — go through every item

### Architecture integrity
- [ ] `RegimeConfig` is the only source for VIX threshold, SL%, PT%, OTM, entry times, margin
- [ ] No strategy file hardcodes any of those values
- [ ] PT is still portfolio-level: `(ltp_ce + ltp_pe) <= combined_target`
- [ ] Time exit uses `datetime.time(15, 30)` — not minute comparison

### Expiry safety
- [ ] `findStrikePriceATM()` uses `get_expiry_string()` — NOT `strftime("%d%b%y")`
- [ ] Verify: on a Monday, expiry returns the coming Thursday, not today

### Scheduler launch
- [ ] `morning_startup()` ends with `subprocess.Popen(...)` launching the strategy script
- [ ] Log file path is correct: `S1_straddle/logs/s1_cron.log`
- [ ] Holiday check happens BEFORE the subprocess is launched

### Capital safety
- [ ] `PAPER_TRADING` env var confirmed — show current value
- [ ] `MAX_LOTS_OVERRIDE` confirmed — show current value
- [ ] `capital_state.json` exists and has correct starting capital

### Logging completeness
- [ ] All 41 `trade_context` keys are populated before `log_trade_s1()` is called
- [ ] `save_capital()` is called after every trade
- [ ] Telegram alert is sent at end of every trade

### Environment
- [ ] `.env` file has all required keys (list them)
- [ ] Shoonya credentials are valid and non-expired
- [ ] Hetzner cron is set to `08:45 IST` on weekdays (show `crontab -l` output)

## Output format
For each checklist item:
✅ PASS — [confirmation]
⚠️ WARNING — [issue, non-blocking]
❌ FAIL — [issue, must fix before deploying]

Only give DEPLOY READY confirmation when all items are ✅ or ⚠️ (no ❌).

## Files to review:
[PASTE FILE NAMES OR CODE SNIPPETS TO CHECK]
