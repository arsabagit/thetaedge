# Prompt: Safe bug fix mode

You are working on ThetaEdge production code.

Follow these rules strictly:

1. Do not redesign strategy logic.
2. Do not touch locked parameters unless explicitly instructed.
3. Do not convert portfolio PT to leg-level PT.
4. Do not hardcode expiry.
5. Do not change DB schema unless asked.
6. Prefer smallest safe diff.
7. Explain bug, root cause, exact fix, and side effects before editing.

When editing:

- keep `RegimeConfig` as source of truth
- preserve `trade_context`
- preserve paper trading safety
- preserve 15:30 exit rule
- preserve date-aware lot size logic

Output format:

1. Bug identified
2. Root cause
3. Minimal code change
4. Risk check
5. Updated code block
