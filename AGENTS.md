# Working Guide

The compact entrypoint for agents working in this repository. `CLAUDE.md` imports this file, so
keep shared instructions here and put detailed guidance in its named owner document.

## Scope

Bulls analysis and lightweight social-graphics production for `@chicagobullsdata`. Python scripts
produce either complete posts or verified chart/data assets for Canva assembly: prototypes for
one-off mocks, promoted CLIs only for repeat formats. The notebook workflow is retired.

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
4. Support two production paths: Python may render the complete post or supply verified chart/data
   assets for Canva assembly. Canva is not an analytical source.
5. Keep applicable qualification thresholds, coverage windows, and sources visible on graphics.
   Preserve approved Canva downloads in `docs/mocks/` before treating ignored output as disposable.
6. Work one post idea at a time.
7. Work directly on the local `main` branch. Do not create branches or Git worktrees by default.
   After completing and verifying requested changes, show the user the result and wait for explicit
   approval before committing or pushing to `main`. Treat commit and push approval as applying only
   to the completed work currently under review. Use a separate branch only when the user explicitly
   requests it or agrees that unusually risky work should be isolated.

## Instagram and X Access

- The user is logged into `@chicagobullsdata` in the runtimes in-app browser or Chrome. Inspect the live account or saved
  references only when the task depends on current state; treat that state as best-effort and
  session-specific.
- The user is also logged into X as `@bullsdata` (display name "Mel", created July 2026), usually in
  an in-app browser tab. It follows a curated set of basketball data/analytics accounts; use its
  timeline and X search as a reference surface for narratives, beat-reporter news (e.g. K.C.
  Johnson), and the official `@chicagobulls` account.
- Use the runtime's in-app browser capability when available, fallback to Chrome. Helpful reference surfaces include
  the grid, the saved `Basketball` collection, and accounts such as Basketball University, Kirk
  Goldsberry, WNBA Viz Wiz, and datakabas.
- Read-only by default on both platforms: never post, comment, like, follow, or change settings
  without explicit, per-action approval.

## Documentation Ownership

- Update the document that owns a changed decision: strategy in `STRATEGY.md`, visual-system
  decisions in `DESIGN.md`, post-production behavior in `POSTING_WORKFLOW.md`, and technical
  conventions in `DEVELOPMENT.md`.
- A visual-system decision has three synchronized repository surfaces: the executable layer
  (`bulls/graphics/house.py` / `craft.py`), the canonical record (`DESIGN.md`), and the rendered
  companion (`design-system.html`). Change all three together; `tests/test_design_tokens.py`
  enforces this for color tokens only, so fonts, components, and layout values rely on this rule.
  Canva's Brand Kit is a manually reviewed downstream mirror, not another canonical owner.
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
