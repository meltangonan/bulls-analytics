# Summer League Report Handoff

**Status: CLOSED — first live post shipped 2026-07-11**

## Outcome

The first live Summer League Report covered the July 10 Bulls–Grizzlies game and shipped as a
five-slide carousel featuring Caleb Wilson, Jaylin Sellers, Noa Essengue, and Dailyn Swain. The
approved finals live at `docs/mocks/2026-07-10-summer-league-report-s*.png`; the catalog card records
the final caption, design decisions, and pre-Insights review. The implementation and post-cycle
review are on `main` through commit `f0314a0`.

## Durable Pointers

- `idea-catalog.html` — post-specific outcome, caption, and review evidence.
- `scripts/prototypes/README.md` — current command sequence and game-night operating notes.
- `scripts/prototypes/summer_league_report.py` — executable behavior and CLI help.
- `DEVELOPMENT.md` — Summer League feed, league-ID, and data-quality guardrails.
- `DESIGN.md` — confirmed visual rules from the shipped carousel.
- `POSTING_WORKFLOW.md` — approval, caption ownership, release, and review behavior.

Reusable decisions and run instructions were moved to those owners. Superseded pre-game commands,
earlier table variants, resolved questions, and the dated “tonight” runbook were removed from this
handoff so they cannot compete with the current sources of truth.

## Remaining Follow-up

An Instagram Insights review is still useful when the data is available. Treat that as a new
`review-bulls-post` task; it does not reopen this completed creation handoff.
