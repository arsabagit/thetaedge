# ThetaEdge — Bug Fix Prompt
# Paste this when you want Copilot to fix one or more bugs from KNOWN_BUGS.md

You are fixing bugs in ThetaEdge production code.

## Rules — follow strictly
1. Fix ONLY what is listed in KNOWN_BUGS.md. Do not refactor anything else.
2. Do not redesign strategy logic even if you think it can be improved.
3. Do not change locked parameters (VIX threshold, SL%, PT%, OTM, entry times).
4. Do not change portfolio-level PT to leg-level PT.
5. Do not hardcode expiry — always use `get_expiry_string()`.
6. Do not rename keys in `trade_context` dict.
7. Do not alter DB schema unless the bug explicitly requires it.
8. Keep `PAPER_TRADING = 1` protected.
9. Prefer smallest possible diff — one function at a time.
10. Respect `datetime.time(15, 30)` for time exit — never `dt.minute >= 30` or `dt.minute >= 15`.

## Output format for each bug fix
For each bug, give this structure:

### BUG-XXX: [name]
**Root Cause:** (1 sentence)
**Files Changed:** list exact files and functions
**Risk of Change:** None / Low / Medium
**Code Change:**
```python
# BEFORE (exact current code)

# AFTER (minimal corrected code)
```
**Verification:** How to confirm the fix is working

---

## Bugs to fix now:
[PASTE BUG IDs HERE — e.g., "Fix BUG-001, BUG-002, BUG-003"]
