# Summer League Sticky-Stats Post Handoff

**Status: ACTIVE — approved Canva carousel preserved; pending promotion and publication**

## Current Deliverable

A three-slide 1080×1350 carousel about the two Summer League shot-profile stats that published
research found relatively sticky into a player's rookie season:

- **3PT Attempt Rate:** 3PA / finalized box-score FGA; published R² 0.70.
- **Rim Rate:** NBA.com Restricted Area attempts / finalized box-score FGA; published R² 0.65.

This is separate from `docs/handoffs/2026-07-18-sl-wrap-brainstorm.md`, which remains ACTIVE.

## Final Carousel

Canva design: `DAHQCKjwtPI` (design ID only; never store the private edit URL).

The approved downloads are preserved at:

- `docs/mocks/2026-07-21-sl-sticky-stats-s1.png`
- `docs/mocks/2026-07-21-sl-sticky-stats-s2.png`
- `docs/mocks/2026-07-21-sl-sticky-stats-s3.png`

The matching `idea-catalog.html` card is `Mocked` until the user confirms the post is live.

1. **Cover:** “What can we take from the Bulls' time at summer league?” with Caleb Wilson,
   Dailyn Swain, Jaylin Sellers, and Donovan Atwell.
2. **Research:** the Phillips/Lee sticky-stat explanation, both R² values, methods, citations, and
   the CTA to see where the Bulls rookies land.
3. **Payoff:** the current-player-pool scatter and the closing statement that these are shot
   tendencies we can probably expect, not exact rookie-season values or player grades.

## Analytical Record

The Python analysis covers the 2026 California Classic, Salt Lake City, and Las Vegas circuits.
Game-level files remain in ignored `cache/sl_sticky_stats_2026/` so the roughly 190 NBA.com calls do
not need to be repeated.

- Qualification: minimum 50 Summer League minutes.
- Qualified pool: 321 players.
- Rankable pool: 319 players whose shot-detail FGA reconcile to finalized box-score FGA.
- The six-attempt gap is isolated to California game `1322600006`: Trevor Keels is missing five
  shot-detail attempts and Tre White one; both are excluded from shot-derived distributions.
- Current-pool medians: 42.86% 3PT Attempt Rate and 27.27% Rim Rate.

Featured Bulls values:

| Player | 3PT Attempt Rate | Rim Rate |
| --- | ---: | ---: |
| Caleb Wilson | 45.59% | 23.53% |
| Dailyn Swain | 22.58% | 41.94% |
| Jaylin Sellers | 62.30% | 34.43% |
| Donovan Atwell | 91.67% | 2.78% |

Noa Essengue remains an unlabeled pool point. The chart describes shot selection, not quality or
playing-time opportunity. The visible down-right relationship between the axes is arithmetic
because both are shares of FGA; do not present it as another predictive finding.

## Source Record

- Owen Phillips, “Summer League Stats You Can Trust,” *The F5*, Jul 18, 2025:
  2008–24 Summer Leagues, 485 rookies, minimum 50 SL and 250 rookie minutes; 3PT Attempt Rate
  R² 0.70.
- David Lee, “Summer League,” *The Hardwood Collective*, 2026:
  2017–25 Summer Leagues, minimum 50 SL and 250 rookie minutes; Rim Rate R² 0.65.

The post cites these published findings rather than recomputing historical SL-to-rookie
correlations. A self-computed rebuild and nearest-neighbor rookie comps were deliberately shelved
because they require a large, thinning historical shot-location dataset.

## Production Record

- Analysis and chart asset: `scripts/prototypes/summer_league_sticky_stats.py`
- Analysis, Canva-copy, and chart-export tests: `tests/test_summer_league_sticky_stats.py`
- Saved headshots: `assets/img/*-headshot.png`
- Live chart-only export: `output/feed/2026-07-21-sl-sticky-stats-chart.png`

The Canva pilot established the supported division of labor now recorded in `DESIGN.md`,
`POSTING_WORKFLOW.md`, and `DEVELOPMENT.md`: Python owns verified analysis and chart/data assets;
Canva may own framing and editorial copy; downloaded final pages return to `docs/mocks/`.

The chart-only export deliberately uses Helvetica to match the Canva composition. The helper splits
Regular/Bold faces from the local macOS Helvetica collection into ignored `cache/fonts/` and falls
back to Archivo off macOS. This is post-scoped and does not replace the house Academic M54 + Archivo
system.

## Open Items Before Publishing

1. **Verify the David Lee X handle.** Slide 2 currently shows `@dlee4threenba`; the sourced post is
   at `x.com/dlee4three`.
2. Exhibit 1 reproduces a chart from Phillips' paywalled Substack. It is credited; the user accepted
   the judgment call, but it remains worth remembering before publication.
3. Accepted Canva deviations: slide 3 uses spaced `|` subtitle separators, and the
   axes-are-not-a-regression note is omitted from the graphic. Do not turn the dot-cloud slope into
   a caption finding.
4. Capitalization of “summer league” differs between slides 1 and 2.

Next action: run `promote-bulls-post`, complete the final downloaded-page and handle checks, prepare
the hashtag block, and publish only with explicit user approval. Mark the catalog card `Posted` only
after the user confirms the live post.

## Git Forensics (2026-07-22)

- The rejected full-slide HTML/SVG renderer and its tests were removed before a normal commit; they
  never appeared on GitHub. Three leftover bytecode files were deleted during repository cleanup.
- Local commit `e1f9087` contained a Canva edit link and was amended to `3d60054` before push.
  GitHub contains `3d60054` and not `e1f9087`.
- Final Canva-ready chart work was committed and pushed as `283da56`.
- Batch 1 preserved the approved Canva downloads and catalog card in local commit `0d0cd6a`; that
  commit was not yet pushed when this handoff was compacted.
