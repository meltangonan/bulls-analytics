# Development Reference

Read before changing fetchers, analysis, graphics builders, scripts, or tests. `DESIGN.md` owns
visual decisions; `POSTING_WORKFLOW.md` owns post production.

Code lives in `bulls/data` (NBA API wrappers), `bulls/analysis` (stat functions), and
`bulls/graphics` (`house.py` tokens/themes/fonts, `craft.py` shared helpers, and `court.py` standard
court geometry). Read the modules for signatures — this file covers only what the code can't tell you.

## Post Worktrees

Any post task that changes repo files starts in its own linked worktree; the user does not need to
request isolation. The primary checkout stays on `main` and is the integration copy — never switch
it to a post branch. Use the visible sibling directory
`../bulls-analytics-worktrees/<post-slug>` with the branch `post/<post-slug>`. The directory names
the post, never the agent or the model: which tool is driving can change mid-build, and often does.
Worktrees created under the older `<agent>-<slug>` naming keep their names until their post lands —
renaming a live worktree costs more than the inconsistency.

Before editing, fetch and fast-forward a clean primary `main`, run `scripts/check_worktrees.sh`, and
stop rather than switching, cleaning, or discarding unexpected work. Create the post worktree from
that current `main`. Copy the primary checkout's ignored `cache/` in when present: the small
snapshot avoids duplicate NBA requests while keeping concurrent writes isolated. Do not copy
`venv/`; run scripts with the primary checkout's `venv/bin/python`. `./run_tests.sh` finds that
shared interpreter automatically while forcing imports to resolve from the current worktree.

⚠️ **The primary checkout owns the cache.** A cache built inside a worktree must be copied back
before that worktree is removed, or it goes with the directory. Prefer running long fetches from the
primary checkout, which writes only to ignored `cache/` and touches no tracked file.

Keep post-specific implementation, tests, outputs, and any required shared code or owner-doc changes
in the worktree. Defer the shared `scripts/prototypes/README.md` index until integration. After the
user approves committing or pushing:

1. Make **one commit** in the post worktree holding the whole reviewed post — implementation,
   tests, saved versions, final pages, and data. A post is one unit of work however many iterations
   it took. Then update the primary `main` and rebase the post branch onto it, resolving real
   shared-code conflicts there.
2. Add the deferred index updates in the rebased worktree, validate, and amend them into the same
   reviewed post commit when practical.
3. Inspect the staged/final diff and commit file list; never use `git add -A` or `git commit -am`.
4. Fast-forward the primary `main` to the post branch, push only with explicit approval, and prove
   local/remote SHA parity.
5. Remove the worktree and delete its branch only once `scripts/check_worktrees.sh` reports nothing
   unsaved there. Preserve and report anything dirty, unmerged, or unclear.

**Ask what is unsaved, not what is merged.** A merged branch means the *code* landed. It says
nothing about renders sitting in ignored `output/` or a `cache/` that took an hour to fetch, and
both have been destroyed by cleanups that asked only the first question: a day of approved renders
from a worktree whose branch had already landed, and 2,132 rate-limited play-by-play requests behind
an already-published post. `scripts/check_worktrees.sh` asks the second question, and the filing
rules remove the exposure — single-owner data is written to the post's tracked `data/` from the
start, and tracked files make a worktree dirty, which is already protected (`bulls/visuals.py`).

**Abandoned posts leave a reason, not files.** When an idea is dropped mid-build, the valuable part
is why: "the cohort fell below the minutes threshold once I applied it" is what stops the same dead
end being reopened in three months. Write that on the Notion page and set its status back. Then
delete the branch and remove the worktree — nothing lands in `docs/visuals/`. A dropped post that
leaves a stale worktree and no written reason has cost you twice.

Run `scripts/check_worktrees.sh` at task start. It reports what is actually unsaved in each
worktree — modified tracked files, renders sitting in ignored `output/`, and cache size — rather
than whether a branch is merged. Those are different questions, and answering the wrong one is how
a day of approved renders was deleted from a worktree whose branch had already landed.

## Conventions

- Keep reusable fetching and analysis in `bulls/data` and `bulls/analysis`; reusable builders in
  `bulls/graphics`; entry points in `scripts/`.
- Start new formats as one script per idea batch in `scripts/prototypes/`. Promote to a reusable
  module and CLI only after the format repeats. Extract a helper only after the same logic appears
  in 2–3 prototypes.
- **For a format that fetches substantial raw data, prepare display-ready content before drawing.**
  Calculations, editorial selections, labels, images, and shot marks belong in a preparation step;
  the renderer receives that prepared object instead of understanding NBA API columns. This keeps
  analytical truth and visual composition independently testable. Keep the prepared shape
  format-specific — don't invent a universal post schema, and let simple one-off prototypes stay
  direct.
- Never rebuild analytical logic in Canva, and never recompute a number that the chart already
  proved. Canva is layout only.
- **Data that can't be fetched is still that post's data: it lives in the post's tracked
  `docs/visuals/<slug>/data/` as a dated snapshot CSV, never as a literal in a script, and never
  behind a scraper.** Salary and contract data is the standing case: it isn't an
  NBA.com statistic, and the sites that compile it (Basketball Reference, Spotrac) prohibit
  automated access in their terms and return 403 to scripted requests. So the snapshot is captured
  by hand, committed, and carries `#` comment lines naming each source URL, the capture date, the
  exact call parameters, and every exclusion or correction. **Give each snapshot reconciliations the
  tests can assert** — a total the source itself publishes, a structural invariant like roster size
  or games per season — so a transcription slip or a bad source row fails a test instead of
  shipping. `payroll_vs_wins.py` is the worked example: its guards caught Spotrac publishing a
  2015-16 Bulls payroll inflated by three players who joined the team the following offseason.
- Keep the matching Notion page current as the idea, status, and post log.
- **`docs/visuals/YYYY-MM-DD-<slug>/` is the tracked home for visual work**, whether it becomes a
  post or stays a reviewed chart. `assets/` holds our renders including the publish-DPI export;
  `data/` holds the numbers behind them. `bulls/visuals.py` explains why the two are kept
  differently; `scripts/save_visual_version.py` carries the promotion test and performs the save.
  Saving is continuous; committing is not. Promoted files accumulate uncommitted in the
  worktree and land as one commit when the post is finished — see Post Worktrees.
  - **Promote decisions, not renders.** A render earns a version when it carries a different metric,
    cohort, threshold, chart type, sort or claim, or when the user approves it. Adjustments — moved,
    resized, recoloured, re-cropped — are overwritten in `output/`. When the two tests disagree,
    promote: over-promoting costs 300 KB, under-promoting loses the only copy.
  - Versions are stamped `YYYY-MM-DD-vNN-<name>.png`, zero-padded so v10 sorts after v9, numbered
    one past the highest present so a rebuild never renumbers history.
  - **Save the approved version at the resolution that goes into Canva.** Draft renders are often
    half-size previews; the export you actually upload is the file worth keeping, and it used to be
    left in scratch where it died with the worktree. Expect the approved draft and its full-size
    export as two adjacent near-identical versions. That is the point, not duplication.
  - `--final` now means one thing only: on a prototype it renders at 300 DPI. The clashing
    `save_visual_version.py --final` flag was removed with the `final/` folder on 2026-08-22.
    Save chart renders with `--project <slug>` alone, whatever DPI they are.
  - The folder's date is fixed when the post starts and never moves; a later save finds the folder
    by slug whatever date it carries, so a post spanning three days stays in one place.
- `output/` is gitignored scratch. Render there freely; promote what carries a decision.
- Name renders `YYYY-MM-DD-{chart}-{mode}-{scope}.png` and pass `--project <slug>` so they land in
  `output/YYYY-MM-DD-<slug>/`, mirroring `docs/visuals/YYYY-MM-DD-<slug>/`. Omit `--project` only for
  disposable one-off exploration, which lands directly in `output/`.
- Prefer small, test-backed changes. No automation, export pipelines, or heavy frameworks unless
  requested.

## Data Provenance

Every data-bearing post gets a provenance section on its Notion page, written as the work lands
rather than on request (`AGENTS.md` owns that rule; this section defines the content). A finding is
reproducible only if the trail to it is written down, and the trail is the first thing forgotten.

Six questions, and a section that cannot answer all six is incomplete:

1. **Source and exact call.** Which endpoint, through which wrapper, with the real parameters pasted
   in — not paraphrased. Parameter names here are frequently misleading: `season_type_all_star` is
   the ordinary season-type filter (the suffix marks which *value list* it accepts, one that includes
   `All Star`), and `context_measure_simple="FGA"` is what returns every attempt rather than makes
   only. A reader who cannot see the literal call cannot tell what was scoped in or out.
2. **The grain.** What one raw row represents, with a real sample. "One row per field-goal attempt"
   is the fact everything else rests on.
3. **Units and coordinate systems.** NBA shot coordinates are tenths of a foot with the hoop at the
   origin and the baseline at `loc_y = -47.5`; every court constant in the code derives from that.
4. **Derived versus measured fields.** State which columns the provider computed, and verify the
   relationship rather than assuming it. `shot_distance` is exactly `floor(hypot(loc_x, loc_y)/10)`,
   confirmed at 100% across 219,160 rows — which is what made "did they bin differently?" answerable.
5. **What the source structurally cannot contain.** The most valuable line in the section and the
   easiest to skip. `ShotChartDetail` is a field-goal log with no concept of a free throw, so any
   points-per-shot figure built on it understates the rim, where shooting fouls concentrate. That is
   a property of the dataset, not a setting — no parameter would add them.
6. **One worked example.** A single real row traced from raw fields to its contribution to the
   published number. This is the step that catches errors: a plausible-sounding claim about your own
   pipeline survives a summary and dies against a trace.

Record where the data itself lives, not only how it was obtained. A provenance section that names an
endpoint but points at a folder that no longer exists answers nothing — see the tracked
`docs/visuals/<slug>/data/` rule above.

Also record what was cached and trimmed, since a cache written under an older column set is a
silent-wrong-answer trap (see the guardrails below).

## Data Guardrails

These are the traps that produce silently wrong numbers rather than errors.

- **⚠️ NBA.com's clutch split stops at 1996-97, and asking for anything earlier returns an EMPTY
  frame rather than an error.** The split is derived from play-by-play, and the play-by-play archive
  starts in 1996-97 — the same floor as shot-location data. Verified 2026-08-21 against
  `LeagueDashPlayerClutch`: 1995-96 and 1990-91 each returned 0 rows with nothing raised, while
  1996-97 returned 13. Nothing in the response says the window was empty because the era is
  unavailable, so an unchecked "since 1976" or "full Jordan era" table would ship a 1996-onward
  leaderboard under a headline claiming decades it does not contain. Assert the row count per season
  rather than trusting the call to fail. The same trap should be assumed for any other endpoint
  derived from play-by-play.
- **⚠️ A team-filtered `LeagueDash*` row is the right stint stamped with the wrong team.**
  `team_id_nullable` correctly returns only what the player did for that team, but
  `TEAM_ABBREVIATION` in the response names his *last* team of the season. Ron Mercer's 2001-02
  Bulls stint comes back stamped `IND`, because Chicago traded him in February. Filtering the
  response down to `CHI` therefore looks like an obvious safety check and silently deletes 45 real
  Bulls clutch stints from 2000-01 onward, every one belonging to a traded player. Verified
  2026-08-21: Mercer's 19 Bulls clutch games plus 4 Indiana clutch games equal the 23 in his
  unfiltered row, and Brad Miller's 23 plus 10 equal 33 the same way. The reconciliation, not the
  abbreviation, is the check worth writing — a stint must be a subset of the player's unfiltered
  season. A stint can legitimately equal the whole season when the player recorded no clutch
  minutes after the trade, so "strictly smaller" is too strong a rule; Coby White, Kirk Hinrich and
  Cameron Payne each appear absent from their new team's clutch response.
  `scripts/prototypes/clutch_seasons_table.py` owns the worked version.
- **⚠️ NBA.com does not publish where a foul happened, and no parameter adds it.** Verified
  2026-08-07 against a full Bulls game: all 36 `PlayByPlayV3` foul rows return `xLegacy=0,
  yLegacy=0`, while 180 of 181 shot rows in the same response carry real coordinates.
  `ShotChartDetail` rejects `ContextMeasure=PFD` and `FTA` with HTTP 400 and 500s on `PF`; the
  `cdn.nba.com` live feed answers 403 outside a browser session. **The tempting workaround is wrong
  and looks right**: borrowing coordinates from the shot event beside each foul only reaches
  and-ones, because NBA scoring charges no field-goal attempt when a player is fouled on a miss.
  That covered 8 of 36 fouls in the test game, and the survivors are rim finishes by construction —
  so the resulting "where they get fouled" map shows the sampling method, not the team. Use drive
  tracking when the question is foul-drawing, and say the chart counts the situation rather than
  locating it.
- **`LeagueDashPtStats` drive fields cross-check each other, so use that.** `DRIVE_FTA` and
  `DRIVE_PF_PCT` are published independently, and free throws per foul drawn must land just under
  2.0, because a drive foul is nearly always a two-shot foul — measured at 1.971 (range 1.78–2.03)
  across 125 qualified 2025-26 players. Assert the 1.5–2.5 band on every run; drift there means the
  two fields stopped describing the same events and the rate axis is no longer trustworthy.

- **`ShotChartDetail` filters by `league_id` server-side and defaults to the regular NBA**, so it
  returns zero rows for Summer League games without complaining. Use `get_game_shots`, which derives
  the league from the game-ID prefix (`00` NBA, `15` Summer League). Prefer the NBA's own `shot_zone`
  labels over re-deriving zones from distance or coordinates.
- **The 12 detailed zones need `shot_zone_area`, and a fetcher that drops it fails silently** —
  `detailed_zones` returns the six basic zones unchanged rather than raising. All three shot
  fetchers now pass the column through when the API supplies it, but a cache written before that
  will quietly collapse to six zones. Refetch rather than reuse.
- **NBA's `SHOT_ZONE_AREA` sectors are angular from the hoop, but the number of sectors depends on
  distance**: one inside 8 ft (all `Center(C)`), three from 8–16 ft (cuts at 60°/120°), five beyond
  16 ft (cuts at 36°/72°/108°/144°). Pool the bands and the angle ranges overlap and look
  self-contradictory. Consequences: `Left/Right Side Center` never appears inside 16 ft, so "Left
  Mid-Range" is always a long two; `Left/Right Side` inside 16 ft covers a 60° wedge rather than only
  the baseline its name suggests; above-the-break threes use just three sectors because the corners
  take the outer two. Verified against 7,463 labelled 2025-26 shots — a classifier built to this
  spec reproduces NBA's own labels on 99.8%, the rest being boundary rounding in NBA's integer
  coordinates.
- **The baseline/mid-range divider runs from the hoop through the corner break**, the point where
  the arc meets the straight corner line, rather than at NBA's 36°. `shot_maps.CORNER_BREAK_DEG`
  derives it (22.13°) instead of hard-coding it. Three lines then meet at one point — corner line,
  arc, divider — so the boundary continues a mark already painted on the floor instead of sitting at
  an angle nobody can name. It moves **44 of 7,417 Bulls shots (0.59%)** out of the baseline zones
  into the mid-range ones, and changed **none** of `scoring_by_location.py`'s twelve zone leaders,
  which was checked before the change landed.
- **The two central mid-range cuts split what the baseline cuts leave into even thirds**
  (`shot_maps.MID_SECTOR_CUTS`), not NBA's 72°/108°. Measured, not assumed: NBA's own angles gave the
  centre sector 17.5% of the mid-range's area against 27.9% for each wing, because the paint pushes
  the centre sector's inner edge out to the free-throw line — a ray is a poor proxy for area there.
  Even thirds flattened both the area split (12.4% spread against 14.5%) and, more sharply, the split
  of league three-point volume above the arc (31/33/36% against NBA's 35/26/39%). Rays through the
  paint's own top corners were tried first and rejected — geometrically the more "principled" choice,
  they overshoot badly and hand the centre 46.9% of above-the-break threes. The change moved 224 Bulls
  shots (3.0%) and two of `scoring_by_location.py`'s zone leaders (Right Mid-Range, Top of Key 3);
  both were checked and accepted as the archived post shipped under the old cuts, and a re-run under
  the new ones would name different players there.
  `shot_maps.ATB_CUTS` is `MID_SECTOR_CUTS[1:3]`, not a separate pair of numbers — the above-the-break
  dividers are literally the same two rays continued past the arc, so they cannot drift apart from the
  mid-range cuts they extend.
- **A zone chart that draws NBA's real sector geometry looks broken, so the twelve-zone family
  deliberately does not.** The change in sector count at 16 ft makes each baseline/mid-range divider
  a stepped "tent" rather than a straight ray, and it reads as a rendering fault (flagged three times
  in review). `shot_maps.zone_of` uses five sectors at *every* distance and classifies from `loc_x`/
  `loc_y`, so the drawn regions and the grouped numbers are the same object
  and the chart cannot draw one set of regions while counting another. It lives in `shot_maps`
  rather than in a prototype because two posts now draw these regions — `scoring_by_location.py`
  and `--chart zones` — and a second copy of a classifier is the same failure one level up: two
  charts counting different regions while both claim to show NBA's zones. `scoring_by_location.py`
  re-exports it under its original name. The divergence is measured,
  not assumed: 34 of 5,855 roster shots move (0.6%), almost all long twos near the 16 ft line, and
  one of twelve zone leaders changes. The script prints the live agreement rate against NBA's labels
  on every run — if that figure drifts, the geometry drifted. **This is a deliberate exception to
  preferring NBA's labels, and it is only safe because the divergence is measured and reported.**
  Any other post should still group by NBA's own `shot_zone`.
- **`shot_maps.polar_cells()` is the second deliberate exception, and it solves the 16 ft step
  differently.** Rather than flattening the sector count, it keeps NBA's angular cuts — three
  sectors inside, five outside — and moves the change from 16 ft to the three-point line, where the
  floor already has a painted line for the step to sit on. Classification comes from `loc_x`/`loc_y`
  and `shot_type`, so the drawn regions and the counted regions are the same object; a
  `tile the court without overlap` test asserts every shot lands in exactly one cell. The 2PT/3PT
  split follows `shot_type` rather than radius so the corner pocket stays with the threes.
- **To qualify a per-bucket leader, gate on a *share* of the bucket, not a rank or a flat floor.**
  When bucket volume varies wildly this is the difference between a defensible claim and a fluke.
  In `scoring_by_location.py` the roster took 2,226 shots at the rim and 29 from right mid-range, so
  "top 3 by attempts" meant 324 shots in one zone and 8 in another, while a flat 10-attempt floor
  handed the rim to a 28-attempt reserve over the man who took 351 — it drops the volume requirement
  entirely. A 15% share scales itself (334 at the rim, 9 on the right baseline) and cut the
  low-sample zones from three to one. Bayesian shrinkage was also tried and was worse: with the
  bucket mean as the prior, any small-sample overperformer still floats to the top.
- **`detailed_zones` reclassifies `Above the Break 3` + `Back Court(BC)` as `Backcourt`.** A
  half-court heave arrives labelled an above-the-break three, so a zone analysis that filters on the
  raw `shot_zone` alone scores a 60-footer against Top of Key.
- **Summer League's traditional box score can finalize hours before its shot-chart and advanced-box
  feeds.** `summer_league_report.py` treats empty or all-zero derived feeds as unavailable rather
  than printing false values. Expect a morning-after render when NBA.com lags.
- **Shot-chart data includes everyone who took a Bulls shot that season, including traded players.**
  Filter to a roster and show both views when the comparison needs to be fair.
- **⚠️ Two roster sources, and they disagree. Use `get_current_roster()` for any "current roster"
  post.** It reads the roster array embedded in NBA.com's public team page and reflects trades,
  signings, and draft picks immediately. `get_roster()` wraps `commonteamroster`, which is
  *season*-scoped and lags badly: checked 2026-07-25 it still returned Sexton, Simons, Yabusele,
  and Richards while missing Claxton, Powell, and every 2026 rookie — 8 wrong out of 18. Never
  infer current membership from a season stats endpoint's team field either; that answers "who
  played here last season," which is a different question.
- **NBA.com's team-filtered player endpoints can attach a traded player's *later* team abbreviation**
  even while games, minutes, and ratings remain scoped to the team you requested. Treat the request's
  `team_id_nullable` filter as the stint scope; never infer scope from the returned abbreviation.
- **Play-by-play names the assister only inside the event description, with no player id.**
  `PlayByPlayV3` is the sole source of player-to-player assist detail before 2013-14 and the only
  source at any date carrying `shotValue`, but resolving `"(Butler 3 AST)"` to a person is a
  minefield, and every failure is silent. Use `assist_duos_fetch.surname_key` / `_name_variants`
  rather than re-deriving: fold diacritics (descriptions are ASCII `Vucevic`, the name column is
  `Vučević`); strip generational suffixes (the column says `Butler III`, the description says
  `Butler` — **417 of Jimmy Butler's 2016-17 assists vanished** on this alone); and generate
  first-name prefixes of one, two, and three letters, because a shared surname is disambiguated by
  whatever prefix is unique (`J. Sampson`, and `Ty.`/`Ti. Thomas` for Tyrus and Tim). Resolve within
  the game first, then the season, and run resolution *after* the whole season is collected — a
  player whose only appearance in a game is the assist itself produces no event row of his own.
- **Reconcile extracted play-by-play against the official box score before reading any leaderboard.**
  Summing `AST` over a season's team game log costs one request and turns every bug above from
  something you must notice into a number that is not zero. All 26 Bulls seasons now sit at
  48,316/48,316. Report a gap, never force it away.
- **Use pbpstats as a secondary parser and analysis surface, not an independent provider.** It
  derives its results from NBA feeds, so it is most valuable for checking our event attribution and
  for questions where its added structure saves substantial work: passer-to-scorer assist networks,
  players on court, possession boundaries, corrected event order, and shot-zone breakdowns. Keep
  NBA.com's structured endpoint as the production source when it answers the question. The public
  pbpstats API is best-effort—it returned intermittent 500/503 errors and timeouts during the
  assist-duos audit—so cache any result a post depends on in that post's tracked `data/` folder.
  API reference: `https://api.pbpstats.com/docs`; parser: `https://github.com/dblackrun/pbpstats`.
- **Two-man lineup minutes (`leaguedashlineups`) return zero rows before 2007-08.** Shared minutes
  are the better denominator than shared games, but they do not exist for the early 2000s, so a
  since-2000 post must use games played together. Choose a metric against the oldest season on the
  graphic, not the newest.
- **The NBA CDN answers an unknown player with a grey silhouette, not a 404**, and it is 12,430
  bytes — above any "file too small" threshold. Detect it by hashing (`assist_duos.is_silhouette`);
  a size check silently passes it through and the chart renders a grey blob that reads as a design
  choice. This also defeats `ensure_historical_headshot_fallbacks`, which treats any file over its
  size floor as a usable cache and so skips the replacement it was written to fetch.
- **The Advanced endpoint reports minutes per game even when `PerMode=Totals`.** For total player
  minutes paired with advanced ratings, use `get_team_player_advanced_stats()`, which joins
  Traditional totals to the Advanced ratings.
- **DataBallR's percentiles are position-adjusted; ours are league-wide.** Don't treat a mismatch as
  a bug. Tre Jones reads 67th percentile in assists there and 89th here off the same rate. Claxton is
  the tell: DataBallR has him 95th in assists and 23rd in rebounds, which is only possible ranked
  against other centers. Pick the population that fits the post — league-wide preserves positional
  archetypes, position-adjusted normalizes them away — and say which one on the graphic.
- **`LeagueDashPlayerShotLocations` (`distance_range="By Zone"`) returns per-player zone splits for
  the whole league in one request** — far cheaper than re-deriving zones from `get_league_shots()`,
  and its FGM/FGA reconcile exactly to each player's box score. Its columns arrive as a two-level
  index that needs flattening. Note zone points exclude free throws, which have no location.
- `get_league_shots()` hits all 30 teams — about 30 API calls, slow.
- Set `min_shots` by timeframe: roughly 30 for a season, 10 for a recent-games view.
- Treat NBA response caches, reconciled analysis caches, and extracted font caches as expensive
  reusable inputs, not cleanup targets. Headshots cache in `cache/headshots/`.

## Graphics Notes

- **New work builds chart assets, not full pages.** Export transparent at a size comfortably larger
  than the placed size; the Canva page supplies the `#FAF8F5` background and all typography. The
  full-layout helpers in `house.py` (`draw_header`, `draw_jersey_stripe`, `draw_footer`, `save_post`)
  are legacy — see `DESIGN.md`.
- Chart text uses `house.helvetica()` / `house.helvetica("bold")`, which extracts the real Bold face
  from the macOS system `Helvetica.ttc` into `cache/fonts/` — matplotlib silently renders regular if
  you ask for bold by family name. The extraction stays in `cache/` so the licensed system font is
  never committed; it falls back to an installed sans-serif off macOS.
- Pull chart colors from the `Theme` tokens (`theme.ink`, `theme.accent`, `theme.grid`, …) rather
  than the white-canvas module constants.
- Prototypes should print a Canva copy block of the exact strings to paste, so the page's numbers and
  the chart's numbers come from the same run.
- Building from an F5 or similar tutorial: reproduce its styling and structure closely, swapping in
  our palette and Helvetica (`DESIGN.md` §6).
- `summer_league_report.py` calls `GT.as_raw_html()`, uses Helvetica in the browser, and renders through
  `nokap.from_html`, and composites the cropped PNG into the Matplotlib canvas. **This browser-backed
  step is part of the live report path**, not the rejected full-slide HTML renderer (`DESIGN.md`,
  Settled). `gt_extras` stays limited to the separate Great Tables spike.
- Court graphics use `analysis.detailed_zones()`.
- `bulls/graphics/court.py` owns the shot-chart dimensions and continuous restricted-area D path.
  Conventional charts call `draw_half_court()`; rings, cells, and ladders keep their specialized
  renderers for clipping and contrast but import the same constants and geometry primitive. A new
  shot-chart renderer may change court color, opacity, clipping, and line weight—not landmark
  positions or shapes.

## CLIs

```bash
venv/bin/python scripts/make_shot_chart.py --player "NAME" --chart hotspot|hex|rings|cells|zones|ladder [--final]
venv/bin/python scripts/make_shot_chart.py --team --chart zones [--project <slug>]
venv/bin/python scripts/make_shot_chart.py --team|--league --chart ladder --metric pps|fg-rel|pps-rel [--project <slug>]
venv/bin/python scripts/make_shot_chart.py --team --chart ladder --blank [--project <slug>]
venv/bin/python scripts/prototypes/current_roster_zone_charts.py    # the team plus every qualified player
venv/bin/python scripts/save_visual_version.py --project <slug> <files...>   # preserve a reviewed version
```

## Chart Family Notes

Why these charts are shaped the way they are. `DESIGN.md` owns how a chart looks; this covers the
analytical choices behind the shot-chart family, which are easy to undo by accident.

`rings`, `zones`, and `cells` answer the same question — how well he shoots by area, against the
league — at four regions, twelve, and 18. Choose by sample. `rings` keeps every band large enough
to carry volume as well as efficiency; `cells` locates a strength or a hole precisely but greys out
what it cannot stand behind. On a ~950-attempt season about half the `cells` grid greys, which is
informative when a player genuinely has no mid-range game and misleading when he simply missed time
— read the printed per-cell table before publishing either.

`zones` sits between them and is the only one of the three that fills the whole court, which is what
makes it the colourful sibling of the hex chart rather than another sparse map. It uses NBA's twelve
named regions via `shot_maps.zone_of`, colours each by FG% against the league across five bands, and
prints the zone's share of all subject FGA under the shooting figure, followed by its signed gap to
the NBA share in the same `vs LA` grammar. The two are meant to be read together because a player can
be excellent in a zone he rarely visits. Shooting is the top line because the fill is shooting; the
colour and the first figure have to be the same thing. The scale runs red → yellow → green by default
(`--palette hex` for the blue scale the hex carousel used); `DESIGN.md` owns why.

**Points per shot is deliberately not on it.** Inside one zone the point value is a constant, so PPS
is FG% times that constant and "his PPS vs the league's" ranks identically to "his FG% vs the
league's". PPS earned its place on the scoring-by-location post because that chart compared *across*
zones, where a 35% three really does beat a 52% long two. Here it would be a third figure repeating
the first. `tests/test_zone_charts.py` pins the identity so nobody re-adds it.

`zones` accepts `--team` because shot share has one denominator at either scope: attempts in the zone
divided by all attempts by that team or player. The NBA reference repeats the same calculation over
all league attempts, so the team opener and player slides are directly comparable and the chart no
longer needs possession endpoints. The raw attempt count in the shooting line preserves absolute
volume. `--league` is still rejected: the league cannot be its own efficiency baseline.

The optional carousel summary below a zone chart reports total FGA, eFG%, and 3PT%. eFG% is
`(FGM + 0.5 × 3PM) / FGA`; 3PT% is `3PM / 3PA`. The summary cards are descriptive and carry no
league comparison; the zone figures remain the chart's comparison layer. Mid-range share remains in
the zone pills and editorial interpretation rather than becoming a fourth headline card.

**Every zone's pill prints makes over attempts** — `11/32 FG (34.4%)` — which changed what the
colour floor has to protect. Early drafts hid the sample behind the floor entirely: a thin zone was
greyed and only its attempt *rate* survived, because the reader had no way to judge the percentage
for themselves. Once the raw count is on the page, the floor's only job is protecting the **colour**
— a reader who can see "0 / 1" still learns what happened without the chart assigning that result
an efficiency band. That is what let the floor come down from an evidence-grade bar to a
display-grade one.

**Both floors are solved, not chosen**, by asking a precision question at a strength each subject's
sample can support.

| Subject | Rule | Function | n | Why that rule |
| --- | --- | --- | --- | --- |
| Team chart | one standard error can't move it a band | `colour_floor(2.5)` | 400 | ~7,400 team shots can afford the strict reading |
| Player chart | one **shot** can't move it farther than the full neutral span | `single_shot_floor(5.0)` | 20 | a rotation player's ~500 shots across twelve zones cannot reach a standard-error bar anywhere but the rim |

`single_shot_floor` is `⌈100 / band_width⌉`: one make out of *n* moves a percentage by `100/n`
points, and the neutral band spans 5 points from −2.5 to +2.5, so 20 caps one shot's movement at
that full span. The ±5 outer cuts make each light band 2.5 points wide, so one shot can still cross
one of those narrower bands at the floor. That is accepted because the count is printed inline and
20 is explicitly a display-grade bar rather than an evidence-grade confidence threshold.
`tests/test_zone_charts.py` pins the arithmetic so the number stays checkable rather than becoming
folklore.

**This floor was 45 for several rounds** — solved the same way as the team's, `colour_floor(7.5)` —
before the counts-in-the-pill change made it clearly too strict: at 45, 71% of the carousel printed
grey, including every mid-range zone for every player, on a chart meant to be colourful and legible
at a glance rather than to carry an evidence-grade claim on its own. Three fixes were costed and
rejected before landing on the single-shot rule:

| Idea | Why it fails |
| --- | --- |
| Flat floor of 25 | Margin of error ±19.6 points, far wider than the ±5 outer cut — the scale would be finer than its own noise |
| Floor as a **share of the league's** volume in that zone | Anchored at the rim it gives the baseline zones a floor of 2 attempts (±65 points); anchored the other way the rim floor becomes 904. Precision depends on the raw count, not on how rare the zone is |
| Floor as a **share of the player's own** attempts | Backwards: it sets the *loosest* bar for the player the chart knows *least* about (Miller's 5% floor is 13 shots; Buzelis's is 48), and it makes green mean a different margin of error on every slide in the carousel |
| Floor solved per zone from the league's own FG% there | Correct, and worthless — the spread across all twelve zones is 4.7 attempts, because binomial variance is nearly flat over the 35–67% range basketball occupies |

Merging the five mid-range zones into one band, and colouring the fill by volume instead of FG%,
were also mocked and rejected on editorial grounds rather than statistical ones — twelve named zones
and an efficiency-coded fill are the post. **Do not re-open any of these without new evidence; the
arithmetic is above.**

**A zone gets one of three treatments**, by attempt count:

| Attempts | Treatment | Pill |
| --- | --- | --- |
| ≥ floor | solid band colour | full four-line pill |
| 1 to floor−1 | grey | full four-line pill, muted |
| 0 | grey | `0 FGA` only |

Grey means the zone has not earned an efficiency colour. A nonzero zone keeps the full descriptive
pill, while a zero-attempt zone says `0 FGA`; the labels distinguish those two states without asking
texture to carry the caveat. `zone-chart-summary-<season>.csv` reports the rated share per subject so
a thin chart (Claxton: 92% of attempts on 2 of 12 rated zones, because he takes 92% of his shots at
the rim) can be checked before publishing rather than discovered after.

`ladder` is the distance-only form, concentric distance bands and no angle at all. It gets its
fullest read from team-scale volume, but it can also show a player's shot-value profile:
`--team` pulls every Bulls shot (traded players included — this is the team's offence, not a
roster), `--league` charts all 30 teams. `--metric pps` is the "Midrange Is Dead" chart and the one
that carries an argument, because points per shot is the only scale on which a two and a three
compare; `fg-rel` and `pps-rel` measure each ring against the league at the same distance and answer
"did they shoot it well" versus "did the shot pay". `--league` rejects the `-rel` metrics, which
would be all zeros. The colour scale is **clamped, not fitted** — the rim ring is a large enough
outlier to squash every other ring into one shade if it sets the range.

The default rating floor is 40 attempts for a team or league ladder and 15 for a player ladder.
Fifteen matches the fine shot-cell chart's floor: it reveals player midrange bands without assigning
meaning to a result built from only a few makes or misses. Pass `--min-fga` only when the post has an
explicitly justified alternative; the graphic prints the actual floor in its grey-band key.

`--blank` produces the same 2-foot ladder and court geometry entirely in neutral grey, with no
values, scale, or methodology copy. It is a data-free cover asset for a carousel whose later slides
reveal the colored analytical charts; it should not be presented as a player's result.

**The split at 24 ft is the method, not a detail.** Inside it a ring counts two-point attempts only;
outside it, threes only. Binning purely by distance makes the 22-24 ft rings ~95% corner threes, so
they read ~1.15 PPS, the curve rises smoothly into the arc, and the cliff the chart exists to show
vanishes.

**The corner pocket is carved out, and this is a deliberate divergence from the reference card.**
A corner three sits ~22 ft from the hoop — inside the radius where the ladder counts twos — so a
purely radial chart has to drop it. The card does exactly that: it loses 22% of all league threes
and then paints the corner strip with the *above-the-break* value from 24-25 ft. That is backwards.
Corner threes are the second most efficient shot in basketball, **1.15 PPS against 1.05 above the
break**, so the card shows a great area as a merely good one. `shot_maps.corner_mask()` takes the
region beyond the corner line and inside the split radius, `corner_split()` gives it its own value,
and the two-point rings clip to the corner line so the two tile exactly. The carve-out is free of
ambiguity: across 219,160 league attempts **zero** two-pointers fall beyond the corner line inside
24 ft, because beyond that line a two does not exist. Coverage goes from 90.4% to **99.5%**; what
remains excluded is heaves past 31 ft and ~190 above-the-break threes that register just under 24 ft.

Ring values verified against a published league "Midrange Is Dead" card for 2025-26: of
its 31 printed values, 15 reproduce exactly and 15 land within 0.01, with only the outermost 30-31 ft
ring (smallest sample) off by 0.03. Pure-distance binning matches 16/31 but produces 0.70 / 1.10 /
1.17 where the card prints 0.70 / 0.74 / 0.62 — that trio is the diagnostic if the method drifts.

**Bands are 2 ft wide (`--band` overrides).** Two independent arguments landed on the same number.
Statistically, 1 ft oversamples: across the league's own ladder **21 of 29 neighbouring 1 ft bands are
statistically indistinguishable**, so most of that resolution renders noise as detail — pooling pairs
turns the league mid-range from a jittery walk into a clean monotonic decline (0.91 → 0.87 → 0.84 →
0.80 → 0.75 → 0.70, then the jump to 1.09 over the arc). Physically, a shooter and his defender
occupy about two feet of floor, so a 14 ft and a 15 ft attempt are the same basketball situation
measured twice; bands should be no finer than the resolution at which the phenomenon varies. It also
takes a single team season from 12 grey bands to 2. 2 ft divides both `LADDER_MAX_FT` (30) and
`LADDER_TWO_MAX_FT` (24), which it must — otherwise a band straddles the 2PT/3PT split.

**The outer band has a hard edge at 30 ft; attempts past it are excluded and reported.** The
reference card instead makes its outermost band a `30+` catch-all with no upper bound, which is why
its top value reads 0.87 against our 0.90: it absorbs 962 heaves out to half court. A band with no
outer edge is not a distance band, so we cap and disclose (0.4% of league attempts) rather than
absorb. `ladder_edges()` snaps the last edge down so a wider band can never readmit them.

**Colour scales are fixed, round and symmetric — never fitted.** Two separate requirements: a
*clamped* range, so the rim's 1.51 cannot squash every other ring into one shade; and a *meaningful
midpoint*, so the colour turn sits on a number a reader can name. For PPS that is 1.00 — a shot worth
exactly one point — running 0.80 to 1.20 in steps of 0.05, which is what the reference does. Centring
on the league mean (1.09) instead was a real bug: it pushed the turn up so 1.00 rendered orange and
nothing went green until ~1.15, quietly flattering every ring between. Label placement is likewise
measured, not eyeballed: glyph-ink centres are compared against band centres and the residual held at
0 px (`LABEL_NUDGE_PX`).

## Tests

```bash
./run_tests.sh
```

All NBA API calls are mocked. `test_design_tokens.py` is the token drift alarm: it fails when hex
values in `DESIGN.md` or `bulls/config.py` stop matching
`bulls/graphics/house.py`. It parses the §2 table rows by token name, so keep that table's format
intact when editing `DESIGN.md`.
