# CLAUDE.md

Minimal guidance for AI edits in this repository.

## Scope
This project is Bulls analysis with notebook exploration plus lightweight social graphics generation.

## Priorities
1. Keep solutions simple.
2. Favor analysis quality over presentation polish.
3. Avoid adding automation/pipelines unless explicitly requested.

## Working Style
- Keep reusable code in `bulls/data`, `bulls/analysis`, and `bulls/viz`.
- Keep social image builders in `bulls/graphics` and CLI entrypoints in `scripts/`.
- Use one notebook per idea in `notebooks/active/` with file name format `YYYY-MM-DD-topic-slug.ipynb`.
- Start new work from `notebooks/templates/idea_template.ipynb`.
- Move completed notebooks to `notebooks/archive/` and keep `notebooks/INDEX.md` updated.
- Keep notebooks concise (short markdown, focused code/plots).
- Do not add large export pipelines by default; keep graphics generation script-based and simple.

## Clarification Gate (Visual Requests)
- Before creating a new visual, clarify request details first.
- Ask one focused question at a time.
- If AskUserTool is available in the runtime, use it; otherwise ask directly.
- Do not start implementation until these are clear:
  - insight goal
  - scope/timeframe (team/player, season or last N games)
  - visual type
  - style direction
  - output text (title/subtitle/footnote)
- If user wants defaults: 1080x1350 PNG.

## Tests
- Run tests with the project venv:
  - `./run_tests.sh`
  - or `venv/bin/python -m pytest tests/ -v`

## Docs
Update `README.md`, `CLAUDE.md`, and `AGENTS.md` when behavior or workflow changes.
