# CLAUDE.md

Minimal guidance for AI edits in this repository.

## Scope
This project is notebook-first Bulls analysis.

## Priorities
1. Keep solutions simple.
2. Favor analysis quality over presentation polish.
3. Avoid adding automation/pipelines unless explicitly requested.

## Working Style
- Keep reusable code in `bulls/data`, `bulls/analysis`, and `bulls/viz`.
- Keep notebooks concise (short markdown, more code/plots).
- Do not add PNG/export workflows by default.

## Tests
- Run tests with the project venv:
  - `./run_tests.sh`
  - or `venv/bin/python -m pytest tests/ -v`

## Docs
Update `README.md`, `CLAUDE.md`, and `AGENTS.md` when behavior or workflow changes.
