# Prompt: Add new strategy safely

You are adding a new strategy to ThetaEdge.

Rules:

1. Do not disturb S1 architecture.
2. Reuse shared modules where possible.
3. New strategy parameters must live in a dedicated shared config structure.
4. New strategy must not break scheduler, DB logging, or S1 paths.
5. Keep new code modular and isolated.

Before writing code, provide:

- folder structure
- config ownership
- execution flow
- DB/logging impact
- deployment impact

Then implement with minimal coupling.
