# Summer League Sticky-Stats Post Handoff

**Status: ACTIVE — Canva-assembly pilot; repo retained for analytics and chart exports**

## Objective

Build one standalone @chicagobullsdata post that profiles the 2026 Bulls Summer League players by
**3PT Attempt Rate** and **Rim Rate**. Published research found both shot-diet traits carried
strongly from a player's first Summer League to his rookie season, so the scatter supplies a more
durable player-style read than shooting percentages or plus-minus.

The broader six-stat carousel is no longer the active deliverable. The user may split the other
sticky metrics into separate posts later; do not build those until this single-post direction is
decided.

This is a **separate post** from the SL-wrap post
(`docs/handoffs/2026-07-18-sl-wrap-brainstorm.md`, still ACTIVE). Sequencing between the two is
undecided; work one post at a time.

## Finalized Scope Decisions (user-confirmed)

1. **One two-axis player profile:** x = 3PT Attempt Rate (3PA / FGA; Phillips R² 0.70) and
   y = Rim Rate (rim FGA / FGA; Lee R² 0.65). Both axes use rates so the chart describes shot
   selection rather than playing-time opportunity.

2. **Cite, don't rebuild.** Present the R² values as the sources' findings with attribution on
   the graphic. Do not recompute historical SL-to-rookie correlations. (A self-computed rebuild
   was discussed and shelved as a possible offseason follow-up.)

3. **Comp-based outlook is shelved.** Nearest-neighbor rookie comps ("past rookies with Wilson's
   SL profile and the range of their rookie seasons") was explored in depth and deliberately cut:
   it requires a historical multi-year SL play-by-play/shot-location pool (hundreds of API calls,
   thinning coverage before ~2017). Keep out of scope unless the user re-opens it.

4. **Context device: this year's SL class.** Plot all 2026 Summer League players with 50+ minutes;
   the pool is descriptive current-season context, while the R² findings remain attributed to
   their historical rookie-only research samples.

5. **Five Bulls get headshots:** Caleb Wilson, Dailyn Swain, Noa Essengue, Jaylin Sellers, and
   Donovan Atwell. Caleb retains the red payoff ring, but the post is a five-player shot-profile
   comparison rather than a Caleb-only projection.

6. **Three-slide 1080×1350 carousel on the default jersey theme, tipoffball-style structure**
   (user-directed 2026-07-20; supersedes both the single-image scope and the same-day dense
   explainer draft). The user reviewed @tipoffball's "The Most Impactful NBA Players in 2010"
   post (instagram.com/p/Da8V1e_jcQH) and asked for its cover → definitions → chart flow:
   - **Slide 1 — cover:** centered masthead, the five Bulls headshots in a staggered cluster
     (Wilson larger with the red ring), one big Academic M54 hook title "WHAT STICKS FROM SUMMER
     LEAGUE" plus a one-line lowercase subtitle. No stats or thresholds. Note: Academic M54 has
     no "?" glyph, so hook titles must work as statements.
   - **Slide 2 — definitions:** bold hook line ("Most Summer League stats are noise."), a short
     narrative homage naming Phillips/The F5 (25 stats, 485 rookies, 2008–24) and Lee/The
     Hardwood Collective (shot-location extension, 2017–25), a "Definitions" chip, and three
     term-chip entries (3PT Attempt Rate, Rim Rate, R²) each with a one-sentence plain-English
     definition and its R²/source tag, closing with the shot-profile-not-player-grade line.
     Explicitly cut per user: "Bulls SL Class"/"2026"/"Research Explainer" subtitle, the
     what-doesn't-stick row, the STICKY ≠ GOOD band, and the five-Bulls minutes row.
   - **Slide 3 — the scatter** (unchanged from the draft-2 cleanup): muted pool dots, median
     crosshair, quadrant labels, R² cards with author attribution, and the axis-definition pair.

## Verified Source Details (read directly from the articles this session)

### Phillips (The F5) — primary citation for box-score stats

- Owen Phillips, "Summer League Stats You Can Trust," *The F5*, Jul 18, 2025.
  https://thef5.substack.com/p/summer-league-stats-you-can-trust — **paywalled**; the user is a
  logged-in subscriber in Chrome. All needed values are captured below.
- Method: 25 stats, 485 rookies, SL 2008–2024 (no 2020-21 season — no SL that year), per-36 and
  rate stats, **min 50 SL minutes & 250 rookie-season minutes**. "Summer League" includes Vegas,
  California Classic, and Salt Lake City. Chart title: "Summer League Stats vs. Rookie Season
  Stats."
- Full R² ladder (read off the chart, verified by zoom): 3PT Attempt Rate 0.70 · 3PA/36 0.68 ·
  AST/36 0.58 · BLK/36 0.56 · TRB/36 0.55 · ORB/36 0.51 · DRB/36 0.37 · PF/36 0.36 ·
  FGA/36 0.35 · Fantasy Pts/36 0.28 · TOV/36 0.26 · FT Attempt Rate 0.25 · AST/TO 0.24 ·
  FTA/36 0.24 · PTS/36 0.23 · STL/36 0.19 · FT% 0.14 · Game Score/36 0.13 · DRE/36 0.12 ·
  eFG% 0.12 · 2P% 0.10 · TS% 0.09 · MPG 0.03 · 3P% 0.03 · +/- per 36 0.02.
- Useful caption fodder: the icky-stat story (3P%, TS%, plus-minus ≈ noise) is the hook that
  makes the sticky six meaningful.
- Phillips also has a paid 2021 code tutorial (RealGM scrape + per-36 + lm in R) at
  https://thef5.substack.com/p/how-to-summer-league — only relevant if a rebuild is ever done.

### Lee (The Hardwood Collective) — primary citation for rim/dunk rate

- David Lee, Summer League article, *The Hardwood Collective*,
  https://thehardwoodcollective.com/articles/summer-league (published ~Jul 9, 2026; announced via
  https://x.com/dlee4three/status/2075285660752306507 — the X post and article are the same work,
  an explicit expansion of Phillips' study).
- Method: SL play-by-play, **SL 2017–2025 (no 2020), min 50 SL minutes & 250 rookie minutes**
  (mirrors Phillips' thresholds). Chart title: "Summer League Advanced Stats vs. Rookie Season."
- R² values (read off the chart, verified by zoom): Dunk Rate 0.74 · Rim Rate 0.65 ·
  AST/USG 0.51 · OREB Pts Added/100 0.50 · Unassisted 2P Creation% 0.47 · Unassisted% 0.44 ·
  Moreyball% 0.40 · Offensive Load 0.38 · Rim AST/100 0.34 · Non-Rim:Rim Rate 0.33 ·
  STOP% 0.30 · Box Creation 0.29 · STOP% (est) 0.26 · FT Pts Added/100 0.20 ·
  TOV Pts Added/100 0.14 · Rim Pts Added/100 0.12.
- **Metric-definition note for possible later posts:** Rim Rate is rim FGA / total FGA; the live
  Fifth Factor tracker defines Dunk Rate as dunk FGA / total FGA. Another Lee glossary uses “Dunk
  Rate” for dunks / rim FGA, so any later dunk graphic must print the denominator rather than rely
  on the label alone.

## Requirements

### Analytical

- 2026 Bulls SL facts: team went 1-4 across 5 games (Jul 10 @MEM through Jul 17 @CLE; details in
  the SL-wrap handoff). **Caleb Wilson played 4 of 5 games** — recompute his stats from NBA.com
  data, not the fan-circulated line.
- Compute 3PT Attempt Rate from finalized NBA.com box-score 3PA/FGA and Rim Rate from reconciled
  NBA.com Restricted Area attempts / finalized FGA.
- Percentile pool: all 2026 SL players with at least 50 minutes. This mirrors both studies' Summer
  League qualification threshold while keeping the current-season comparison intuitive.

### Functional (graphic/post)

- One scatter with all five Bulls labeled by both rates; keep the 50-minute floor, coverage window,
  sources, and reconciled-player count visible on the graphic.
- Both citations on the graphic: "R²: Phillips, The F5 (2008–24 rookies)" and "Lee, The Hardwood
  Collective (2017–25)," or equivalent compact form.
- Fairness guardrail (bulls-content-playbook): sticky stats describe *what kind of player*, not
  *how good* — Phillips' own closing point. Keep the caption on that side of the line,
  especially with grade-discourse swirling (see SL-wrap handoff).
- Follow `POSTING_WORKFLOW.md` (incl. hashtag block rule) and `DESIGN.md`.

### Technical

- Reuse `bulls/data/fetch.py`: `get_box_score`, `get_player_shots`, `get_league_shots`,
  `league_for_game` are SL-aware. `scripts/prototypes/summer_league_report.py` has the SL
  fetch/prep patterns from the four posted reports (per-game; this post needs cross-game
  aggregation).
- **Coverage recon passed 2026-07-20:** the pool covers all three circuits used by the historical
  research: 12 California Classic games (NBA league ID 13), 6 Salt Lake City games (ID 16), and
  76 Las Vegas games (ID 15), Jul 3–19. The aggregate contains 2,749 player-games, 13,625 box-score
  FGA, and 13,619 shot-detail FGA. The six-shot gap is isolated to California game `1322600006`:
  Trevor Keels is missing five shot-detail attempts and Tre White one, so both are excluded from
  shot-derived distributions rather than assigned biased rates. There are 321 players at 50+
  minutes and 319 whose shot-detail FGA reconcile to their finalized box-score FGA. Game-level CSVs are
  cached under ignored `cache/sl_sticky_stats_2026/` so later slides do not repeat roughly 190 API
  calls. One NBA.com minute-format error in that same California box (`129:53` for 29:53, etc.) is
  normalized only when a single-game minute value is impossibly above 100.
- Rim-zone definition should stay consistent with the repo's existing shot-zone handling (see
  the shot-zone data fix that shipped with the Cavs report, commit range through `a74ecf9`).
- New analysis belongs in a prototype script per `DEVELOPMENT.md`; no promoted CLI unless the
  format repeats.

## Refined Three-Slide Draft for Review (2026-07-20)

- Prototype: `scripts/prototypes/summer_league_sticky_stats.py` (renders all three slides)
- Slide 1 (cover): `output/feed/2026-07-20-sl-shot-profile-s1-cover.png`
- Slide 2 (research): `output/feed/2026-07-20-sl-shot-profile-s2-research.png`
- Slide 3 (Bulls scatter): `output/feed/2026-07-20-sl-shot-profile-s3-bulls.png`
- Narrative progression is now explicit: slide 1 promises the answer, slide 2 explains the
  first-Summer-League-to-rookie comparison and the two signals, and slide 3 applies them to the five
  Bulls. Repeated research language was removed from slide 3 so the player profiles are the payoff.
- Visual refinement: the cover has one watermark and a swipe cue; the research slide replaces the
  paragraph-heavy definitions page with a process diagram, two hero R² cards, and one compact R²
  explanation; the scatter has lighter pool dots, fewer ticks, neutral quadrant labels, shorter axis
  labels, and a Bulls-specific title/kicker. The threshold, reconciliation count, and source stack remain.
- **Official Bulls shot-profile values:** Wilson 45.59% 3PT / 23.53% rim; Swain 22.58% / 41.94%;
  Essengue 37.50% / 43.75%; Sellers 62.30% / 34.43%; Atwell 91.67% / 2.78%. The 319-player
  medians are 42.86% 3PT and 27.27% rim.
- **Chart read:** upper-left is rim-heavy; lower-right is three-heavy; upper-right is high in both
  and therefore lighter on other twos. These axes are mechanically related parts of one shot diet,
  so do not present their current-pool relationship as a separate predictive finding.
- Pure calculation coverage: `tests/test_summer_league_sticky_stats.py`.

## Canva Template Experiment (2026-07-21)

At the user's request, the three-slide structure was laid out as a Canva template via the Canva
connector: design `DAHQCKjwtPI`, "SL Sticky Stats — What Sticks From Summer League (template)"
(open it from the account's Canva designs; the edit link is deliberately omitted because this
repository is public). Built by generating each slide as a separate
AI design, merging them into one 3-page 1080×1350 design, then correcting all copy to this
handoff's approved wording (R² values, Phillips/Lee attribution, thresholds, fairness closing
line). Structure and copy only — it is not an approved post surface and does not replace the
repo's Python analysis and chart exports. Pages 1–3 are the first generic-editorial draft, kept as reference;
**pages 4–6 are the design-system-converged variant** (user-requested 2026-07-21): jersey-trim
stripe at the top of each page, exact token colors (#FAF8F5/#141414/#5F5B57/#A19B92/#CE1141),
empty red-ring circular placeholder cluster on the cover, and slide 3 rebuilt to the
title → tick-subtitle → red italic kicker → chart frame → faint bottom-left source grammar.
Canva approximates the fonts (no Academic M54/Archivo; family not settable via connector) and
the subtitle separators are printed "·" glyphs rather than drawn ticks. Remaining manual Canva
steps: drag the saved ESPN headshots
(`assets/img/*-headshot.png`; no Essengue headshot saved yet) into the page-1 cluster, drop a
rendered scatter PNG into the page-3 placeholder frame, and optionally unify title fonts across
pages (Canva lacks Academic M54; connector cannot change font family). Intermediate generated
designs (`DAHQCMg8I2o`, `DAHQCCqMnd4`, `DAHQCJ8IbTw`, `DAHQCM-eyUc`) and the user's original blank
design are leftover and can be deleted in Canva.

## Canva-Assembly Pilot (2026-07-21, user-confirmed direction)

The user intends to transition post assembly to Canva: the repo stays the analytics and chart
generator; charts are pasted into the Canva template, downloaded, and posted manually. Confirmed
division of labor: Canva owns framing (title/subtitle/kicker/footer/watermark); **stat-derived
fine print stays rendered on the chart image** (threshold, reconciliation count, axes-not-a-
regression note) so template text cannot drift from the data.

- `scripts/prototypes/summer_league_sticky_stats.py` gained `render_chart_only()` and a
  `--chart-only` flag: frameless slide-3 scatter, transparent background, 1080×1000 logical
  (2160×2000 px with `--final`), exported to
  `output/feed/2026-07-20-sl-shot-profile-s3-chart-only.png`. Existing slide renders untouched.
- Pilot remaining (manual, in Canva): paste the chart PNG onto page 6 of `DAHQCKjwtPI`, drag the
  four saved ESPN headshots into the page-4 circles (Essengue headshot still missing), unify
  title fonts, download, compare against the Matplotlib original before committing to the system.
- Canva Brand Kit is to be a **mirror** of DESIGN.md §2 tokens (jersey palette + Archivo; Academic
  M54 upload subject to its non-commercial license) — the repo remains the editor of record; no
  test can see Canva drift.
- Do not rewrite `POSTING_WORKFLOW.md`/`DEVELOPMENT.md` for this until the pilot is judged
  successful and the carousel narrative itself is settled.
## Next Action

Continue the manual Canva-assembly pilot: paste the chart-only PNG onto page 6 of `DAHQCKjwtPI`,
place the four saved ESPN headshots on page 4, source the missing Essengue image, unify the Canva title
fonts, and compare the downloaded carousel against the Matplotlib original. Keep the repository focused
on verified analysis and chart generation; the HTML renderer experiment was rejected and removed. The
carousel narrative still needs user approval before final export, catalog promotion, or posting work.
