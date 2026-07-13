# Bulls–Jazz Summer League Report Handoff

**Status: ACTIVE — awaiting the final game and NBA.com feeds on 2026-07-13**

## Current Objective

Create a new Summer League Report for the July 13 Bulls–Jazz game using the approved carousel
format. Replace the Bulls–Grizzlies rehearsal data with the completed Jazz-game data, recommend
the player stories supported by that box score, and finish the post for manual Instagram posting.

This is a new post. The closed Grizzlies report remains documented separately in
`docs/handoffs/2026-07-09-summer-league-report.md`.

## Approved Format

- Slide 1 uses the jersey off-white canvas, matchup logos/title, score/date subtitle, a roughly
  35/65 team-comparison-to-shot-diet panel, the FG/3PT/FT shooting lines, and the player table.
- Player slides use the player as the outlined title, six identity chips, a pale-red evidence
  panel, exact shot locations, off-white supporting cards, and one solid-red true-shooting card.
- Every slide keeps `Data via nba.com` bottom-left and `@chicagobullsdata` bottom-right.
- Regular-season Gamebook experiments live in a separate prototype and should not block this post.

Implementation: `scripts/prototypes/summer_league_report.py`.

## Clearest Next Action

After the game is final, use the `create-bulls-post` skill and run:

```bash
venv/bin/python scripts/prototypes/summer_league_report.py --season 2026
```

The review pass auto-resolves the latest completed Bulls Summer League game and prints the player
table. If the Jazz game is still in progress, or the NBA.com shot/advanced feeds have not populated,
the script should refuse to render rather than print false zeros. Once the feeds are ready:

1. Show the review table to the user and recommend one to four player stories based on this game;
   do not automatically repeat the Grizzlies-game selections.
2. Render the 150-DPI carousel with the selected `--player` values plus `--carousel`, then visually
   inspect every slide, including rookie headshots and long player names.
3. Preserve the analytical caveat that the 2026 Summer League one-free-throw rule can make TS%
   read unusually high.
4. After the user approves the Jazz-data draft, render with `--final`, copy the approved 300-DPI
   slides to `docs/mocks/`, create or update the Jazz post's catalog card, run the full tests and
   `git diff --check`, then stop for explicit commit/push approval.
5. Mark this handoff `CLOSED` and compact it after the Jazz post is finalized.

## Durable Pointers

- `scripts/prototypes/README.md` — game-night command sequence and operating notes.
- `DEVELOPMENT.md` — Summer League league-ID and feed-readiness guardrails.
- `DESIGN.md` — visual-system rules and jersey-theme decision.
- `POSTING_WORKFLOW.md` — draft/final approval and release behavior.
- `idea-catalog.html` — post-specific status, caption, and review evidence.
