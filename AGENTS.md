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
| Design register, brand personality, or design principles (feeds the Impeccable skill) | `PRODUCT.md` |
| A visual, mock, or post iteration | `DESIGN.md`, then `POSTING_WORKFLOW.md` |
| Editorial direction, idea lanes, or fairness guardrails | `bulls-content-playbook.html` |
| The current shelf of post ideas | `idea-catalog.html` |
| Creating, promoting, or reviewing a specific post | Matching skill in `.agents/skills/`, then its routed owner documents |
| Fetchers, analysis, graphics code, scripts, or tests | `DEVELOPMENT.md` |
| Setup and a high-level orientation | `README.md` |

## Defaults

1. Keep solutions simple and avoid speculative architecture.
2. Favor analysis quality over presentation polish.
3. Avoid scheduled automation, heavy export pipelines, and heavy framework additions unless asked.
4. Keep applicable qualification thresholds, coverage windows, and sources visible on graphics.
5. Work one post idea at a time.
6. Work directly on the local `main` branch. Do not create branches or Git worktrees by default.
   After completing and verifying requested changes, show the user the result and wait for explicit
   approval before committing or pushing to `main`. Treat commit and push approval as applying only
   to the completed work currently under review. Use a separate branch only when the user explicitly
   requests it or agrees that unusually risky work should be isolated.

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
- Treat documentation maintenance as part of completing the work; the user should not need to ask
  separately. Update only the affected owner documents and revise or replace stale guidance instead
  of duplicating it or appending unnecessary history.
- Treat temporal language such as "current," "today," wake conditions, and manually maintained
  freshness labels as a maintenance obligation: update it with the related artifact or remove it
  when Git history and item-level dates are the more reliable record.
- Surface evidence-based hypotheses and unresolved patterns to the user for confirmation. Record an
  explicitly stated user preference as a durable rule; keep conclusions inferred from results as
  hypotheses until the user confirms them or repeated evidence supports them.
- Treat `docs/handoffs/` as temporary transfer notes, not owner documents. Mark each handoff
  `ACTIVE` or `CLOSED`; when work closes, move reusable knowledge to the relevant owner document,
  catalog card, or format README, then compact the handoff to its outcome, remaining follow-up, and
  durable pointers. Remove superseded operational instructions.
- Keep owner documents current-state-first. Retain decision history only when it prevents a settled
  question from being re-litigated; compact or archive it when it starts obscuring the active rules.
- Keep `AGENTS.md` as a short map plus durable defaults; do not duplicate detailed procedures here.
- Update `README.md` when the repository layout, setup, or entrypoint map changes.

## Cross-Tool Skills

- Keep the canonical copy of each Bulls-authored repo skill in `.agents/skills/<skill-name>/`.
- For Claude Code discovery, create `.claude/skills/<skill-name>/` with a relative `SKILL.md`
  symlink to the canonical `.agents/skills/<skill-name>/SKILL.md`. Link any supporting resources
  the same way when they exist. Never maintain copied skill files in both locations.
- When adding, renaming, or removing a repo skill, update both discovery paths and verify that each
  resolves to the same `SKILL.md`.
- Exception: third-party skills that ship provider-specific builds (currently Impeccable) keep their
  installer-managed copies in both `.agents/skills/` and `.claude/skills/`; do not replace them with
  symlinks.
