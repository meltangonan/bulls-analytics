# Summer League Report Handoff

**Status: ACTIVE — awaiting the final Bulls–Jazz game and NBA.com feeds on 2026-07-13**

## Current Objective

Replace the Bulls–Grizzlies rehearsal data with the completed Bulls–Jazz Summer League game,
choose the player stories supported by the final box score, and finish the approved carousel for
manual Instagram posting. The user approved the revised format on 2026-07-13; do not reopen the
layout unless the Jazz data exposes a real fit or legibility problem.

## Approved Format

- Slide 1 uses the jersey off-white canvas, matchup logos/title, score/date subtitle, a roughly
  35/65 team-comparison-to-shot-diet panel, the FG/3PT/FT shooting lines, and the player table.
- Player slides use the player as the outlined title, six identity chips, a pale-red evidence
  panel, exact shot locations, off-white supporting cards, and one solid-red true-shooting card.
- Every slide keeps `Data via nba.com` bottom-left and `@chicagobullsdata` bottom-right.
- This is the approved Summer League recap format. Regular-season analytical experiments belong
  in a separate prototype and should not block tonight's post.

Implementation: `scripts/prototypes/summer_league_report.py`.

## Clearest Next Action

After the game is final, use the `create-bulls-post` skill and run:

```bash
venv/bin/python scripts/prototypes/summer_league_report.py --season 2026
```

The review pass auto-resolves the latest completed Bulls Summer League game and prints the player
table. If the Jazz game is still in progress, or the NBA.com shot/advanced feeds have not populated,
the script should refuse to render rather than print false zeros. Once the feeds are ready:

1. Show the review table to the user and recommend one to four player stories; do not automatically
   repeat the four Grizzlies-game players.
2. Render the 150-DPI carousel with the selected `--player` values plus `--carousel` and visually
   inspect every slide, including rookie headshots and long player names.
3. Preserve the Summer League true-shooting caveat in the analytical review: the 2026
   one-free-throw rule can make TS% read unusually high.
4. After the user approves the Jazz-data draft, render with `--final`, copy the approved 300-DPI
   slides to `docs/mocks/`, update the matching catalog card, run the full tests and
   `git diff --check`, then stop for explicit commit/push approval.
5. Mark this handoff `CLOSED` and compact it again after the Jazz post is finalized.

## Durable Pointers

- `scripts/prototypes/README.md` — game-night command sequence and operating notes.
- `DEVELOPMENT.md` — Summer League league-ID and feed-readiness guardrails.
- `DESIGN.md` — visual-system rules and jersey-theme decision.
- `POSTING_WORKFLOW.md` — draft/final approval and release behavior.
- `idea-catalog.html` — post-specific status, caption, and review evidence.

The July 10 Bulls–Grizzlies carousel remains the first shipped example at
`docs/mocks/2026-07-10-summer-league-report-s*.png`.
