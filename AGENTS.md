# Working Guide

The compact entrypoint for agents working in this repository. `CLAUDE.md` imports this file, so
keep shared instructions here and put detailed guidance in its named owner document.

## Scope

Bulls analysis and lightweight social-graphics generation for `@chicagobullsdata`. Everything runs
as scripts: prototypes for one-off mocks, promoted CLIs only for repeat formats. The notebook
workflow is retired.

## Read the Right Document

| When working on… | Read… |
| --- | --- |
| Account purpose, audience, metrics, or priorities | `STRATEGY.md` |
| A visual, mock, or post iteration | `DESIGN.md`, then `POSTING_WORKFLOW.md` |
| Editorial direction, idea lanes, or fairness guardrails | `bulls-content-playbook.html` |
| The current shelf of post ideas | `idea-catalog.html` |
| Fetchers, analysis, graphics code, scripts, or tests | `DEVELOPMENT.md` |
| Setup and a high-level orientation | `README.md` |

## Defaults

1. Keep solutions simple and avoid speculative architecture.
2. Favor analysis quality over presentation polish.
3. Avoid scheduled automation, heavy export pipelines, and heavy framework additions unless asked.
4. Keep thresholds, coverage windows, and sources visible on graphics.
5. Work one post idea at a time.
6. Work directly on the local `main` branch. Do not create branches or Git worktrees by default.
   After completing and verifying requested changes, commit and push directly to `main`. Use a
   separate branch only when the user explicitly requests it or agrees that unusually risky work
   should be isolated.

## Instagram Access

- The user is logged into `@chicagobullsdata` in Chrome. Inspect the live account or saved
  references only when the task depends on current state; treat that state as best-effort and
  session-specific.
- Use the runtime's Chrome or browser capability when available. Helpful reference surfaces include
  the grid, the saved `Basketball` collection, and accounts such as Basketball University, Kirk
  Goldsberry, WNBA Viz Wiz, and datakabas.
- Read-only by default: never post, comment, like, follow, or change settings without explicit,
  per-action approval.

## Documentation Ownership

- Update the document that owns a changed decision: strategy in `STRATEGY.md`, visual-system
  decisions in `DESIGN.md`, post-production behavior in `POSTING_WORKFLOW.md`, and technical
  conventions in `DEVELOPMENT.md`.
- Keep `AGENTS.md` as a short map plus durable defaults; do not duplicate detailed procedures here.
- Update `README.md` when the repository layout, setup, or entrypoint map changes.
