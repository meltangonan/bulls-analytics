# AGENTS.md

Guidance for Codex and other coding agents working in this repo.

## Project Intent
- Bulls analytics workspace for notebook-driven exploration.
- Primary output is analysis in Jupyter notebooks, not productionized artifacts.

## Non-Goals (Unless User Asks)
- No scheduled automation workflows.
- No heavy PNG/export pipelines.
- No heavy framework additions.

## Engineering Rules
1. Keep it simple; avoid over-engineering.
2. Prioritize reusable analysis helpers over presentation helpers.
3. Keep notebooks concise: headings + one-liner context.
4. Extract helper functions only when notebook logic repeats 2-3 times.
5. Prefer small, test-backed changes.
6. Use one notebook per idea with consistent section structure.
7. Before building any visual/graphic, run the Clarification Gate below.

## Repo Conventions
- `bulls/data`: NBA API fetch helpers
- `bulls/analysis`: stat and shot-quality logic
- `bulls/viz`: matplotlib notebook chart helpers
- `bulls/graphics`: single-image social graphics builders
- `scripts`: CLI entrypoints for generating images/posts
- `notebooks/active`: current idea notebooks (`YYYY-MM-DD-topic-slug.ipynb`)
- `notebooks/archive`: frozen/older notebooks
- `notebooks/templates`: starter notebooks
- `notebooks/INDEX.md`: notebook catalog + workflow rules
- `tests`: fast unit tests with mocks

## Clarification Gate (Required for Visual Requests)
- Ask focused clarification questions before implementation.
- Ask one question at a time when possible.
- Do not generate final visuals until all required fields below are clear.
- If the runtime supports AskUserTool, use it; otherwise ask directly in chat.

Required fields:
- `insight_goal`: What the visual should prove.
- `scope`: Team/player and season vs last N games.
- `visual_type`: Chart/card type.
- `style_direction`: Visual direction (clean, bold, editorial, etc.).
- `output_text`: Exact title/subtitle/footnote copy.

Defaults (if user says "pick for me"):
- `size`: 1080x1350 (Instagram feed portrait)
- `format`: PNG

After clarifying:
- Re-state the agreed brief in 3-6 bullet points.
- Then implement data/analysis changes, add tests, and generate the image.

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
