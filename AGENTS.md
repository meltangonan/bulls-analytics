# AGENTS.md

Guidance for Codex and other coding agents working in this repo.

## Project Intent
- Bulls analytics workspace for notebook-driven exploration.
- Primary output is analysis in Jupyter notebooks, not productionized artifacts.

## Non-Goals (Unless User Asks)
- No scheduled automation workflows.
- No PNG/export pipelines.
- No heavy framework additions.

## Engineering Rules
1. Keep it simple; avoid over-engineering.
2. Prioritize reusable analysis helpers over presentation helpers.
3. Keep notebooks concise: headings + one-liner context.
4. Extract helper functions only when notebook logic repeats 2-3 times.
5. Prefer small, test-backed changes.

## Repo Conventions
- `bulls/data`: NBA API fetch helpers
- `bulls/analysis`: stat and shot-quality logic
- `bulls/viz`: matplotlib notebook chart helpers
- `notebooks`: exploration and visual analysis
- `tests`: fast unit tests with mocks

## Validation
Run before finishing:

```bash
./run_tests.sh
```

## Documentation Sync
If behavior changes, update:
- `README.md`
- `CLAUDE.md`
- `AGENTS.md`
