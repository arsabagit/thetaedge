# ThetaEdge — Add New Strategy Prompt
# Paste this when adding S2, S3 or any new strategy module

You are adding a new strategy to ThetaEdge.

## Non-negotiable rules
1. Do NOT touch any S1 files — S1 must remain unchanged.
2. Do NOT change `shared/regime_config.py` unless adding a new config class (not modifying CONFIG_A or CONFIG_B).
3. Do NOT change `shared/capital_manager.py` logic.
4. Do NOT change `shared/scheduler.py` S1 launch path.
5. New strategy must live in its own folder: `S{N}_strategyname/`
6. New strategy must have its own: `config.py`, `run_s{N}.py`, `algo_*.py`, `capital_state.json`, `logs/`, `data/`
7. Reuse shared modules: `order_manager`, `notifier`, `trade_logger`, `auth`, `holiday_calendar`
8. New parameters must go in a new `Config class` in `shared/regime_config.py` — NOT inside the strategy folder.
9. New DB table must not conflict with `trades_S1`.

## Required output before writing any code
1. Proposed folder structure
2. New config class design
3. Execution flow (timestamped like ARCHITECTURE.md)
4. What shared modules it uses vs what it adds
5. DB table name and key columns
6. Impact on scheduler (if any)

Only write code after the above plan is confirmed.

## Strategy to add:
[DESCRIBE YOUR NEW STRATEGY HERE]
