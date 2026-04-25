# Prompt: Pre-deploy review

Review this code change for production safety.

Check specifically:

- parameter source of truth
- expiry generation
- PT logic type
- SL logic correctness
- 15:30 exit enforcement
- scheduler launch path
- logging completeness
- paper trading safety
- import stability
- no accidental refactor of stable modules

Give output in this format:

1. Safe
2. Risky
3. Broken
   List exact reasons and exact lines/functions affected.
