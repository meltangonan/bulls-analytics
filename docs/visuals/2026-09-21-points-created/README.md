# Bulls points created: top 15 since 1996-97

Selected first post: the top 15 Bulls regular-season player-seasons from 1996-97
through 2025-26, with repeat players allowed. **All 15 ranks are verified using
NBA-only statistical inputs.** The totals, rates and ranks are unchanged. Current
v07 uses the verified dataset and is pixel-identical to the reviewed v06 layout.
Earlier mixed-source exploratory tables remain saved as research history.

[Notion post](https://www.notion.so/3e2e1c13abe681059cdfd8bbca295c65): In progress.
[Canva design](https://www.canva.com/design/DAHV2VGcKSk/Ox26trwE_gnQL_QutD-smg/edit):
page 2 passed composed-page QA on September 21 using a downloaded 1080×1440 PNG.
All 15 rows and figures match the verified table; no clipping or overlap.
The taller chart has 25.34 px side margins and 45.81 px above the source footer.
Review export: `output/points-created/canva-qa-page2-full.png` (temporary, untracked).
The cover remains unfinished. Promotion draft is recorded in Notion, not approved
or published. Publication is not confirmed.

## Definition and displayed statistics

Points created means the player's own points plus the actual field-goal points
scored from his assists. The player's own free throws count; extra and-one free
throws for the assisted scorer do not. Free-throw assists, secondary assists and
potential assists are excluded. Chicago figures count only the Bulls stint.

| Displayed statistic | Source and calculation |
| --- | --- |
| Points scored | NBA season and player-game summaries supply official PTS. |
| Assist points | We identify each assisted made basket in NBA play-by-play and add its actual value: 2 or 3 points. This is our calculation from individual plays, not a downloaded season assist-points summary. |
| Total PTS created | We add points scored and assist points. |
| NBA rank | We calculate competition rank: 1 plus the number of NBA players with more total points created that season. All NBA inputs; ties share rank. Traded players count once using their combined NBA season. |
| % team points | Total created divided by all Chicago points that season, multiplied by 100. The denominator includes games the player missed. |
| Created per game | Total created divided by the player's Bulls games played. |
| MVP annotation | Basketball Reference's season MVP voting table supplies the finish and whether it was tied. Only players receiving votes receive an annotation. |

Team shares overlap across teammates: the same basket can count toward the scorer
and the passer. NBA rank is our calculated statistic, not an NBA-published points
created leaderboard. The 1996-97 starting point refers to this historical
play-by-play scope, not the beginning of modern player tracking.

Example: Rose 2010-11 scored 2,026 and assisted 460 twos and 163 threes:
2,026 + 460 × 2 + 163 × 3 = 3,435. Dividing by his 81 games gives 42.4 per game;
dividing by Chicago's 8,087 points gives 42.5%.

## NBA-only verification and reproducibility

The source decision for this post is **NBA data for all scoring statistics and
league comparisons; Basketball Reference only for MVP voting**. Historical
mixed-source audits remain below as superseded decision evidence.

The NBA endpoints are:

- `https://stats.nba.com/stats/leaguedashplayerstats`: official full-season player
  summaries, Base/Totals/Regular Season. League-wide rows include combined traded
  stints; Chicago-only rows support the original Bulls selection.
- `https://stats.nba.com/stats/playergamelogs`: official individual game summaries,
  Regular Season. These supply player identities, team membership, PTS, AST, GP
  coverage, FGM and FG3M for reconciliation.
- `https://stats.nba.com/stats/playbyplayv3`: individual game events, including the
  assisted scorer, assister named in the description, and basket value.

`scripts/prototypes/points_created_nba_parse.py` resolves assister names against
that game's same-team roster, including accents, suffixes and shared surnames.
The extracted player-game assist counts and made two/three-point basket counts
are checked against the official game summaries. If a team-game fails the
checks, its assist points are not treated as verified. Ordinal warnings in an
otherwise reconciled, uniquely attributed game remain visible in the audit.
Matching counts are a reconciliation check; they cannot independently prove every
individual event's attribution.

`scripts/prototypes/points_created_nba_ranks.py` verifies the ranks without
estimating unexamined assists. Each unexamined assist must produce either two or
three field-goal points, which gives every NBA player a minimum and maximum
possible total. The script inspects more games until each player's entire range
falls above a Bulls target or cannot exceed it. Only then is that target's rank
certified. This establishes the exact rank without claiming to have calculated an
exact assist-points total for every league player. Excluded team-games retain the
official box-score bounds, so failed reconciliation cannot artificially narrow
a player's range. Game-level limits also account for teammates' made twos and
threes: a player cannot assist more of either kind than his teammates made, and
cannot assist his own baskets. These are mathematical limits, not average values.

The script also checks game-summary season totals against official season totals,
verifies each displayed Bulls total from NBA scoring and reconciled assists, and
checks the Chicago team denominator. Requests run serially and successful replies
are cached for resumption.

The completed audit inspected 3,754 NBA game records across 12 seasons: 984 reused
Chicago games and 2,770 newly fetched games. All 7,302 opponent comparisons are
resolved. Twenty-nine opponent team-games failed attribution or shooting checks;
they remain bounded unknowns, and none leaves a rank uncertain. Every displayed
Bulls assist total fully reconciles. All seasons were replayed successfully from
saved inputs with network requests disabled. Eleven focused logic tests and 31
documentation checks passed.

Current NBA-only evidence is under `data/nba-league/`:

- Preserved NBA source summaries, compressed play-by-play responses and source
  manifests retain the input trail, including source hashes and capture metadata
  where available. Reused caches do not receive a fabricated retrieval date.
- `assisted-baskets-<season>.csv.gz` records extracted baskets and whether the
  team-game passed validation. `issues-<season>.json` retains discrepancies.
- `comparison-intervals-<season>.csv` records official scoring, verified assists
  and the remaining ranges. `rank-proof-<season>.csv` records every opponent's
  relation to each target.
- `verified-ranks-<season>.csv` is written when a season's selected ranks are
  certified. `verified-ranks.csv` consolidates all selected seasons only after
  their certificate files exist.

The canonical graphic input is `data/nba-top15.csv`, separate from the
superseded exploratory selection files. `data/top15.csv` is the renderer's joined
output with MVP records. All 15 certificates and the renderer input are current
and consistent; `verification-summary.json` records the completed proof hashes.

```bash
/Users/meltangonan/projects/bulls-analytics/venv/bin/python scripts/prototypes/points_created_nba_ranks.py
/Users/meltangonan/projects/bulls-analytics/venv/bin/python scripts/prototypes/points_created_table.py --final
```

## Graphic and MVP records

`scripts/prototypes/points_created_table.py` uses the established portrait bar-table
format. Black represents points scored; gray represents assist points; the red
card displays total PTS created. NBA ranks in the top 10 use conditional green
`#218347`. Names and season groups are vertically centered, seasons use ordinary
hyphens and bold italic type, and parenthesized MVP annotations are bold Bulls red.
There are no ordinal rank labels beside the player names.

Current v07 uses a 3500 × 4014 transparent draft and a 7000 × 8026 publish asset,
with 254-unit rows. Both exports are pixel-identical to v06. The actual reviewed
Canva placement is x=25.34/y=185.20, width 1029.32 and height 1180.58, ending at
y=1365.78 with 45.81 pixels above the source footer. The downloaded 1080×1440
composed table page passed QA. The initial v01 and final v07 assets are retained;
superseded cosmetic versions and scratch exports were preserved locally under
`output/points-created-closeout-2026-09-21/` in the primary checkout.

Code and data work is complete. The user will finish the cover and caption in
Canva and expects to publish later in the week; no scheduled or completed
publication is claimed.

Five selected seasons received MVP votes: Rose 2010-11 (MVP), Jordan 1996-97
(2nd), Jordan 1997-98 (MVP), Pippen 1996-97 (11th), and DeRozan 2021-22
(tied 10th). `data/mvp-voting.csv`, `data/mvp-voting-sources.json`, and
`data/raw/mvp-awards-<endyear>.html` preserve the positive and no-votes findings.
These are voting finishes, not first-place vote counts. Historical NBA CDN
portraits may show later jerseys.

## Superseded exploratory evidence

The original Bulls selection covered 543 player-seasons and reconciled 55,063
assists against official NBA season AST. `data/bulls-source-totals.csv` retains
that selection evidence. Earlier assist-basket snapshots came from the
assist-duos post for 2000-01 onward and cached NBA PBP for 1996-97 through 1999-00.
The original scoring/GP summaries came from the bench-points-season post.

An independent NBA-only selection audit is saved in `data/nba-selection-audit.csv`.
All 543 rows match official Chicago player coverage, GP, PTS and AST. Reaggregating
52,410 NBA assisted baskets reproduces assist points and created totals for 508
rows. The remaining 35 rows (1998-99 and 1999-00) cannot reach the 2,415-point
selection threshold even if every assist produced three points; their largest
possible total is Elton Brand's 2,092. The top 15's identities, totals and order match.

`data-preview.html` and `data/preview-*.csv` retain the earlier top-15 and decade
options. Decades use season starting years: 2000-01 through 2009-10, 2010-11
through 2019-20, and 2020-21 through 2025-26. Their mixed-source NBA ranks are
**superseded**, not the canonical figures for this post.

`bbr_check.py` previously combined NBA points scored with Basketball Reference's
summarized `astd_pts` field for league opponents. Twelve of the final 15 Bulls
assist-points values matched that provider; Basketball Reference was two points
higher for Jordan and Pippen in 1996-97 and Butler in 2016-17. Those discrepancies
motivated the NBA-only rebuild. Raw `data/raw/bbr-<endyear>-pbp.html` files and
comparison audits remain evidence of that rejected approach; they supply no
current scoring or rank inputs.

`compare.py` and the saved pbpstats responses were exploratory cross-checks only.
Some requests failed, and two responses stopped at 500 players, short of official
league coverage. Ten complete seasons supplied 13 matching ranks across the
broader exploratory selections; this was not complete verification of the final
15. These files are retained but are not current source inputs.

NBA tracking's `LeagueDashPtStats` Passing field `AST_PTS_CREATED` was also
rejected as interchangeable: Butler 2016-17 was 1,004 there versus 959 from
assisted field goals. The tracked field has a different scope from this post's
explicit field-goal definition.
