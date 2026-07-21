# Summer League Sticky-Stats Post Handoff

**Status: ACTIVE — carousel assembled and approved in Canva; pending publish + promotion**

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

5. **Four Bulls get headshots** (revised 2026-07-21; was five): Caleb Wilson, Dailyn Swain,
   Jaylin Sellers, and Donovan Atwell. Noa Essengue was dropped from the featured set and remains
   an unlabeled dot in the plotted pool. **No player-specific emphasis:** Wilson's larger portrait,
   red ring, and red value text were removed — every featured Bull now renders at the same portrait
   size with a neutral ring, a red dot, and a red connector line, so the graphic compares shot
   diets rather than ranking players. Portraits use the user-saved ESPN headshots in
   `assets/img/*-headshot.png` (see `ESPN_HEADSHOTS` in the prototype); no ESPN file for Essengue.

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
the subtitle separators are printed glyphs rather than drawn ticks.

**Superseded:** the user has since rewritten every slide by hand and deleted the draft pages —
see "Final Carousel" below for the shipped state. The generated pages served only as scaffolding.
Intermediate generated designs (`DAHQCMg8I2o`, `DAHQCCqMnd4`, `DAHQCJ8IbTw`, `DAHQCM-eyUc`) and
the original blank design are leftover and can be deleted in Canva.

## Canva-Assembly Pilot (2026-07-21, user-confirmed direction)

The user intends to transition post assembly to Canva: the repo stays the analytics and chart
generator; charts are pasted into the Canva template, downloaded, and posted manually. Confirmed
division of labor: Canva owns framing (title/subtitle/kicker/footer/watermark); **stat-derived
fine print stays rendered on the chart image** (threshold, reconciliation count, axes-not-a-
regression note) so template text cannot drift from the data.

- `scripts/prototypes/summer_league_sticky_stats.py` gained `render_chart_only()` and a
  `--chart-only` flag: frameless slide-3 scatter, transparent background, 1080×1000 logical
  (2160×2000 px with `--final`), exported to
  `output/feed/2026-07-20-sl-shot-profile-s3-chart-only.png`.
- Chart-only revisions (2026-07-21 user edits): panel outline removed (fill retained — the Canva
  page supplies framing), the "FEWER OTHER 2S" sub-label removed, Essengue dropped, uniform
  red dot/red connector markers for all four Bulls per scope decision 5, and **headshot rings
  removed entirely** (portraits sit directly on the panel).
- Second pass: canvas is now 1080×1080 logical (2160×2160 at `--final`) with wider margins so a
  Canva frame that crops slightly cannot clip the axis titles or fine print; axes are drawn in
  ink at lw 2.2 with outward tick marks and larger tick labels; player value pairs use a spaced
  "×" separator instead of "·"; and each player's label block is placed on the far side of the
  portrait from its dot so the red connector never crosses text.
- Third pass — @bballuniversity-style rebuild (user-supplied reference: their "Leaders in Paint
  Non-RA FGA" post). Connector lines and marker dots are gone; **each portrait is itself the data
  point**, centered on the player's exact coordinates at radius 46 and drawn above the pool dots.
  The plotted range runs -6→106% (x) and -14→104% (y) so a portrait on an extreme value (Atwell,
  2.8% rim) is not clipped by the axis. Four rounded corner keys name each quadrant
  (PAINT-FIRST / RIM + THREES / MID-RANGE LEAN / PERIMETER-FIRST). Each key's second line is a
  **parallel restatement of both axes** in the reference's idiom — "higher rim, lower 3PT" /
  "higher rim, higher 3PT" / "lower rim, lower 3PT" / "lower rim, higher 3PT" — rather than the
  interpretive phrasing first drafted; the user found the restatement easier to decode. Keep them
  short: the bottom-right key runs into Atwell's portrait if the line grows much wider.
- **Quadrant wash tried and rejected (2026-07-21):** a soft four-corner gradient was built and
  then removed at the user's call — it made the pool dots and portraits harder to read. The panel
  is a single flat `#F5F1EC`. If any quadrant tinting is revisited, it must not use a
  green-good / red-bad ramp: the reference chart can, because its axes measure efficiency, but
  ours measure style, and a good-to-bad ramp would contradict scope decision 5 and the playbook's
  shot-profile-not-player-grade guardrail.
- Fifth pass (user edits): the two fine-print lines were **removed from the chart image** — the
  user types them into Canva instead — and each player's rate pair is now Bulls red bold 9 pt so
  the payoff numbers separate from the gray pool. Canvas trimmed to 1080×1030 logical
  (2160×2060 at `--final`) now that the caption band is empty. `--chart-only` prints the exact
  fine-print strings to stdout for copying into the template.
- ⚠️ **Drift risk introduced deliberately:** the qualification threshold, reconciliation count,
  and source credits are no longer baked into the image, but `AGENTS.md` default 4 and the
  playbook still require them on the published graphic. They are now a manual sync point — after
  any refetch, re-copy the printed values into Canva before posting.
- Fourth pass (user edits): flat panel restored, the tinted marker dots dropped from the quadrant
  keys, the canvas-colored halo removed from the player name/stat labels, and those labels
  reduced to 9.5 pt name / 8.5 pt values. The halo remains on the two MEDIAN labels only, where
  it keeps them readable over the dashed crosshair and pool dots; on the flat panel it is the
  same color as the background and therefore invisible.
- Label placement is now geometric rather than hand-tuned: labels sit under each portrait and
  flip above only when there is no room beneath, and the bottom two quadrant keys tuck just under
  the 0% line to stay clear of Wilson's stat label. Re-check these if the featured set changes.
- **Typography deviation (post-scoped, deliberate):** the chart-only export is set entirely in
  **Helvetica**, not the house Archivo, to match Canva-side type. `helvetica()` in the prototype
  splits the Regular/Bold faces out of `/System/Library/Fonts/Helvetica.ttc` into ignored
  `cache/fonts/` — matplotlib registers only the Regular face of that collection, so asking for
  bold by family name silently renders regular. The licensed system font is never copied into the
  repo, and the helper falls back to Archivo off macOS. Helvetica has no U+2192 glyph, so the
  fine print spells out "Summer League-to-rookie" instead of using an arrow. **This is not a
  DESIGN.md change** — the house system still specifies Academic M54 + Archivo; revisit only if
  Helvetica is adopted across posts.
- `render_shot_profile()` (the legacy full-poster slide 3) deliberately still carries the old
  five-player, Caleb-emphasized treatment and a bordered panel. It is retained as the prior
  reference render; only the chart-only export is the live deliverable. Reconcile or retire it
  when the Canva pilot is judged.
- Pilot remaining (manual, in Canva): paste the chart PNG onto page 6 of `DAHQCKjwtPI`, drag the
  four saved ESPN headshots into the page-4 circles (Essengue headshot still missing), unify
  title fonts, download, compare against the Matplotlib original before committing to the system.
- Canva Brand Kit is to be a **mirror** of DESIGN.md §2 tokens (jersey palette + Archivo; Academic
  M54 upload subject to its non-commercial license) — the repo remains the editor of record; no
  test can see Canva drift.
- Do not rewrite `POSTING_WORKFLOW.md`/`DEVELOPMENT.md` for this until the pilot is judged
  successful and the carousel narrative itself is settled.
## Final Carousel (2026-07-21, user-approved)

The Canva-assembly pilot succeeded and is now the working method: the repo produces verified
numbers and the chart-only PNG; Canva owns all framing and copy. Design `DAHQCKjwtPI` is down to
the three final pages (the earlier reference drafts were deleted).

- **Slide 1 — cover:** "What can we take from the Bulls' time at summer league?" over the four
  ESPN headshots, the summer-league-is-mostly-noise setup, and a swipe cue.
- **Slide 2 — research:** "STICKY STATS", the Phillips/Lee explainer with both R² values, method
  footnotes (2008–24 and 2017–25, min 50 SL / 250 rookie minutes), two exhibit charts, and the
  "SEE WHERE THE BULLS' ROOKIES LAND" CTA. Footers carry full citations with dates.
- **Slide 3 — payoff:** "BULLS SHOT PROFILES" over the chart-only export, closing on "These are
  the shot tendencies we can probably expect in their rookie seasons."
- Title was deliberately kept functional (names what the chart shows) rather than narrative; the
  closing line says *tendencies*, not exact values, because R² 0.70/0.65 leaves ~55% of the
  spread unexplained and extremes regress toward the middle.

## Open Items Before Publishing

1. **Verify the David Lee handle.** Slide 2 tags `@dlee4threenba`; the sourced post is at
   `x.com/dlee4three`. Flagged repeatedly and still unresolved — confirm before posting, since the
   post reproduces his chart and tags him.
2. **Exhibit 1 is a chart image from Phillips' paywalled Substack.** Credited, but republishing a
   subscriber-only graphic publicly is a judgment call the user has accepted.
3. **Accepted deviations:** slide 3's subtitle uses `|` glyphs where `DESIGN.md` specifies drawn
   tick marks (Canva cannot draw them), and the axes-are-not-a-regression note was dropped from
   the graphic — the down-right slope of the dot cloud is arithmetic, not a finding, so keep that
   out of the caption.
4. Capitalization of "summer league" differs between slide 1 (lowercase) and slide 2 (title case).

## Next Action

Run `promote-bulls-post` for the caption and hashtag block, resolve the handle check above, then
publish. Afterward, move the reusable Canva-assembly method out of this handoff into
`POSTING_WORKFLOW.md` and add the post to `idea-catalog.html`.
