# Summer League Report Handoff

## RESUME HERE (2026-07-11 morning)

The Memphis game is played and final: **Grizzlies 97, Bulls 96** (game ID `1522600012`,
2026-07-10). The clarification gate is DONE — the user locked **four featured players: Caleb
Wilson, Jaylin Sellers, Noa Essengue, Dailyn Swain** (the script's feature cap was raised from
three to four for this). Caleb Wilson's pro debut is the headline: 35 points, 12-21 FG, 7-11 3PT,
30% of Bulls FGA, −11 in the one-point loss. His 2-6 FT line is correct under the one-FT rule
(each make was worth two points).

Rendering was blocked overnight only because NBA.com's derived feeds lagged the box score: the
shot chart returned zero rows and the advanced box (NETRTG/USG%/TS%) returned all-zero placeholder
rows hours after the final. A guard now detects the all-zero advanced frame and degrades to "—"
instead of printing fake zeros. Both feeds should be populated by morning.

Morning command (then the normal refinement gate, then `--final` after approval):

```bash
venv/bin/python scripts/prototypes/summer_league_report.py --game-id 1522600012 --carousel \
  --player "Caleb Wilson" --player "Jaylin Sellers" \
  --player "Noa Essengue" --player "Dailyn Swain"
```

`--date` defaults to the game's own date, so the post still reads JUL 10, 2026. The 2026 game
triggers the automatic TS% footnote. Watch for the rookie-headshot silhouette warning on Wilson.
The feature-cap raise and the advanced-box zero-guard are **uncommitted** on local `main` —
present them with the rendered post and get commit approval together.

## Next-session goal

After the Bulls' Summer League game, create a player-led Instagram post through the normal
clarification and draft-refinement workflow.

## The game

- **Bulls vs. Memphis Grizzlies, Friday July 10, 2026, 8:00 PM ET / 7:00 PM CT**, Las Vegas.
- Confirmed against two independent sources (ESPN Summer League hub, Bulls roster announcement
  coverage). Later Bulls games: **July 14 vs. Washington**, **July 16 vs. LA Lakers**. Reporting
  differs on whether a July 13 vs. Utah game exists — re-verify before relying on it.
- Headline angle: **Caleb Wilson** (No. 4 pick, likely pro debut) against **Cameron Boozer**
  (No. 3 pick). Top-five picks often play only one or two Summer League games, so this may be the
  only Wilson game we get.

## Rules context — verified

Summer League 2026 is running the experimental **one-free-throw rule**: outside the last two minutes
of regulation and all of overtime, a player shoots a single free throw worth the number of points he
was awarded. A shooting foul on a three becomes one attempt worth three.

The math consequence: TS% is `PTS / (2 × (FGA + 0.44 × FTA))`, and the `0.44` coefficient assumes
most trips to the line are two-shot trips. Under the one-FT rule `FTA` roughly halves while points
stay the same, so TS% inflates (a 71 TS% performance under normal rules reads ~82 under the
experiment).

**User decision (2026-07-10, evening), superseding the earlier eFG%-only rule:** the report prints
NBA.com's **TS%** anyway — the user chose it with full knowledge of the inflation, as an informed
override. The disclosure is automated: `one_ft_rule_applies(game_id)` gates a footnote ("TS% reads
high under the one-free-throw rule") that prints on every slide of a 2026 Summer League game and
stays off for normal-rules games like the 2025 rehearsal. Do not quote a 2026 SL TS% in captions
without the same qualifier.

## Working format

- Keep the general title `SUMMER LEAGUE REPORT`.
- **Slide 1 (approved direction after anatomy study, 2026-07-10):** Bulls-only front page — no opponent
  comparison ("that's the point of this page"). Bold subtitle: Bulls score red, opponent
  black, date gray; no kicker by default (`--kicker` adds an approved editorial line).
  Snapshot band holds four white stat cards (REB, AST, STL, TO) plus the team shot map
  with FG / 3PT / FT make-attempt lines and percentages. Replace the bordered featured-player
  card stack below it with the compact Great Tables-style player comparison proven in
  `scripts/prototypes/summer_league_great_tables_spike.py`. Keep the Bulls visual system rather
  than copying the reference: white, Bulls red/black, Archivo, restrained rules/striping, and one
  meaningful emphasis. Columns follow the F5 Great Tables tutorial (final user decisions,
  2026-07-11): headshot, PLAYER, MIN, PTS, REB, AST, TOV, STL, BLK, FGM/A, 3PM/A, FTM/A, USG%,
  TS%, NETRTG last. Rows sort by PTS so the headline scorer tops the table, and **no column is
  color-highlighted** (an earlier NETRTG color block was tried and removed). NETRTG/USG%/TS%
  come from `BoxScoreAdvancedV3` (merged in `fetch_game_data`; degrades to "—" with a warning if
  the endpoint lags). The +/- column was dropped as redundant with NETRTG. The player-slide payoff
  card is TRUE SHOOTING. Do not repeat a title/subtitle inside the embedded table.
- **Player slides (approved C2 direction):** date-only subtitle, no kicker. Use the C2 mockup's
  structure: a large exact-location FGA chart on the left and a compact supporting metric rail on
  the right. Remove the `PRIMARY TAKEAWAY` label and takeaway headline entirely; do not manufacture
  an editorial thesis. Retain the original box line (PTS, MIN, FG, 3PT, REB, AST), FGA share, TS%
  (the red payoff card; see the rules-context section for the footnote it requires on 2026 games),
  plus/minus, and HOW HE SCORED splits for RIM/PAINT, MID-RANGE, THREES, and FREE THROWS, but give
  them hierarchy instead of equal-weight cards. Plot all FGA with the same circular shape: solid
  for makes and hollow for misses. Do not distinguish 2PA from 3PA by marker.
- **APPROVED (2026-07-10, pre-game).** Both slides are built, refined, and user-approved on the
  rehearsal game: slide 1 with the embedded Great Tables comparison (sorted by PTS, PTS is the
  magnitude-colored column), and the C2 player slide (identity chips, exact-FGA court left,
  shot-profile cards right with a solid-red eFG% payoff card; card text centered after a spacing
  fix). Slide 1 is post-ready on its own; the user may post slide 1 alone tonight if the player
  slide needs more polish on real data. `great-tables>=0.22` is now in `requirements.txt`
  (`gt_extras` stays environment-only; spike script only). Approved mocks:
  `docs/mocks/2025-07-14-summer-league-report-s1.png` and `-s2.png`; catalog card added (Mocked).
- Feature one to three Bulls player cards, only when the game provides a real story.
- Every card keeps the basic box score and adds one selected lens:
  - `shot_diet` — how the player scored, grouped as rim/paint, mid-range, and threes.
  - `role` — the player's share of Bulls field-goal attempts.
  - `impact` — the Bulls' plus/minus in the player's minutes.
- Do not force three cards or a different lens for each player when the game does not support it.
- `shot_diet` needs volume to say anything. Below roughly eight field-goal attempts, prefer `role`
  or `impact`.

## Prepared tool

`scripts/prototypes/summer_league_report.py`. **`--game-id` is now optional** — with no arguments it
resolves the most recent completed Bulls Summer League game itself.

1. Run the review pass. It prints the game it resolved, then the story table:

```bash
venv/bin/python scripts/prototypes/summer_league_report.py
```

2. Run the clarification gate before choosing players, lenses, title/subtitle copy, and fan-voice
   level.
3. Render the draft. **The chosen format for tonight (user decision, 2026-07-10) is the carousel**:
   a team front-page slide (score + team snapshot + featured list + swipe cue) plus one full slide
   per player showing the box line, all three lenses, and a large shot map:

```bash
venv/bin/python scripts/prototypes/summer_league_report.py --carousel \
  --player "Caleb Wilson" \
  --player "Dailyn Swain"
```

Slides save as `<game-date>-summer-league-report-s1.png`, `-s2.png`, … in `output/feed/`. Use
`--final` for the 300-DPI export only after the draft is approved. The original single-image mode
still works (one to three `--player`/`--lens` pairs; lenses `shot_diet`, `role`, `impact`) — in
carousel mode `--lens` is ignored because every player slide shows all three. Pass `--kicker` for
the approved editorial line. `--date` defaults to the game's own date, so a post rendered after
midnight still dates itself correctly.

**Format decision (user, 2026-07-10).** After talking through alternatives, the user chose the
carousel and kept the existing `SUMMER LEAGUE REPORT` identity. One carousel post per game: a team
front-page slide (slide 1) followed by one full slide per featured player. A reframe that treated the
post as a permanent "debut card" was considered and rejected — the user prefers the original report
framing. The single-image mode remains available as a fallback but the carousel is the intended
game-night format.

**Type player names from the review-pass table, not from press articles.** The script matches
NBA.com box-score spellings; outlets disagree (one spells the returning forward "Noe Essengue",
NBA.com prints "Noa Essengue"). A wrong name raises an error that lists the valid ones.

### Safety rails now in place

- **Refuses to render a game in progress.** Checks `gameStatus == 3` (Final) via `BoxScoreSummaryV3`
  before fetching anything. Running the script at halftime prints a clear message instead of a
  beautiful, wrong graphic.
- **Auto-resolves the game ID** via `LeagueGameFinder(league_id_nullable="15")`. Summer League game
  IDs encode league 15. Before the game is final this exits with a plain message; if NBA.com lags,
  fall back to `--game-id <id>` taken from the NBA.com game URL.

## Data notes

- The NBA game-specific box-score feed works for Summer League once the game ID is known. The repo's
  season game lookup is regular-season-scoped — do not use it here.
- Shots come from the promoted **`bulls.data.get_game_shots(game_id)`** fetcher, which derives
  `league_id` from the game-ID prefix (`15` = Summer League) — `ShotChartDetail` otherwise defaults
  to the regular NBA and silently returns zero rows. `shot_diet` reads its `shot_zone` column (the
  NBA's own `SHOT_ZONE_BASIC` label): `Restricted Area` + `In The Paint (Non-RA)` → RIM/PAINT,
  `Mid-Range` → MID, and the corner/above-the-break/backcourt zones → 3PT.
- If the shot chart lags the box score right after the buzzer, the script warns and continues; only
  a `shot_diet` lens is blocked (with a clear message). `role` and `impact` never need shots.
- `shot_diet` cards now embed a **mini half-court shot map** (makes solid red, misses hollow),
  inspired by a saved reference post. Draft-stage; not yet through the refinement gate.
- Do **not** re-derive zones from coordinates or `shotDistance`. The NBA already publishes the
  answer, and hand-rolled thresholds are how the old bug happened. Verified on the rehearsal game:
  shot-chart attempts reconcile exactly with box-score FGA for all eight Bulls who played.
- `playbyplayv3` is no longer used. Its `area` / `areaDetail` fields come back null for Summer
  League, so it can only give raw distance and coordinates.

## Fixed since the last session

- `shot_diet` used a hand-rolled `<= 14 ft` distance proxy for "RIM/PAINT". The paint is only 16 ft
  wide, so step-backs, baseline fadeaways, and short-corner floaters were counted as rim pressure —
  and the error only ever ran in the flattering direction. It disagreed with the NBA's own zones on
  5 of the Bulls' 74 attempts in the rehearsal game. Buzelis's card read `9 RIM/PAINT · 1 MID`; the
  NBA says `7 RIM/PAINT · 3 MID`. Essengue's card claimed **0 mid-range attempts** when the NBA
  records one. Now sourced from `SHOT_ZONE_BASIC` instead of a threshold we maintain.
- The subtitle stripped only the strings `"Atlanta "` and `"Chicago "` from the opponent name, so
  every other opponent rendered as a full name beside the Bulls' nickname. Tonight it would have
  read "Bulls 98 · Memphis Grizzlies 91". Now uses a proper nickname helper.
- This document previously said `--player "Daylon Swain"`. He is **Dailyn Swain**. That command
  raised a `ValueError`.

## Open questions

- **One-card whitespace (single-image mode only).** The single-image layout was designed around
  three cards; one card leaves a large empty band at the bottom. This is now moot for the primary
  path — the carousel gives each player a full slide — but if anyone falls back to single-image mode
  for a one-player night, the band is still there. Centring was tried and rejected (it strands the
  `PLAYER STORIES` header). Left as a `DESIGN.md` decision only if single-image mode is ever revived.
- ~~Player-slide kicker repeats.~~ Superseded 2026-07-10: kickers were removed from all slides
  (slide 1 accepts an optional `--kicker`; player slides have none and show a date-only subtitle).
- ~~Long names on player slides.~~ Resolved 2026-07-10: names auto-shrink via `_fitted_text`, and
  hyphens render as spaces in the display face (Academic M54 has no hyphen glyph — data lookups
  still use the exact NBA.com spelling).
- **Footnote disclosure.** The footnote still reads `Summer League game · Data via NBA.com/Stats`.
  It does not disclose the shot-diet thresholds, which `AGENTS.md` asks for, nor the one-free-throw
  rule. The user chose to leave this for now. FT volume will look low under the one-FT rule; if it
  reads jarring on the real game, a one-line footnote is the fix.
- ~~No `idea-catalog.html` card exists.~~ Resolved 2026-07-10: card added (Mocked), mocks in
  `docs/mocks/`.
- **Rookie headshots.** CDN photos for 2026 rookies (Caleb Wilson especially) may still be gray
  silhouettes. The script warns when a cached file is under ~20 KB; fall back to a Bulls team-CDN
  crop per `DESIGN.md` §8 if the warning fires. Both the slide-1 table and the player slide show
  headshots.

## Current evidence

- Rehearsal game: Bulls 114, Pacers 105, July 14, 2025; NBA game ID `1522500033`.
- The approved four-slide carousel renders clean against the rehearsal game; approved mocks are
  committed at `docs/mocks/2025-07-14-summer-league-report-s1.png` and `-s2.png`. The legacy
  single-image mode still renders.
- Full suite passes (132 tests). Output PNGs under `output/feed/` stay untracked; the pre-redesign
  renders are preserved there as `*-baseline.png`.
- Design-study artifacts: `docs/ideation/summer-league-anatomy-study.html`, wireframes and spikes in
  `scripts/prototypes/` (see its README).

## Game-night runbook (tonight: Bulls vs. Grizzlies, 7:00 PM CT)

1. Wait for the final buzzer (~9:00–9:30 PM CT). The script refuses in-progress games.
2. Review pass — auto-resolves the game and prints the story table:

   ```bash
   venv/bin/python scripts/prototypes/summer_league_report.py
   ```

   If NBA.com lags on auto-resolve, pass `--game-id` from the NBA.com game URL.
3. Clarification gate with the user: choose 1–3 featured players from the printed table (type names
   exactly as the table spells them) and confirm any `--kicker` line. Watch for the headshot
   silhouette warning on rookies.
4. Draft render at 150 DPI:

   ```bash
   venv/bin/python scripts/prototypes/summer_league_report.py --carousel \
     --player "<Name>" [--player "<Name>" ...]
   ```

5. Refine with the user. Slide 1 alone is an approved fallback post if the player slides need work.
6. After approval: re-run with `--final` (300 DPI), copy finals to `docs/mocks/`, save the caption
   on the catalog card (or note the user is writing it), and use `promote-bulls-post` for posting
   copy. The user posts manually; update the card to `Posted` only after they confirm it is live.

## Roster reference (verify spellings against the review pass)

Caleb Wilson, Dailyn Swain, Noa Essengue, Boo Buie, Kennedy Chandler, Antonio Reeves, Jaylin
Sellers, Tobe Awaka, Charles Bediako, Donovan Atwell, Keyshawn Bryant, Houston Mallette, Grant
Newell, Jalen Washington, Malik Williams.

Boo Buie is Northwestern's all-time leading scorer — a local angle if the game gives him one. Noa
Essengue also played the 2025 Summer League, so a year-over-year comparison is available.

## Relevant references

- `POSTING_WORKFLOW.md` — mandatory clarification and draft-refinement gates.
- `DESIGN.md` — active Bulls visual system.
- `scripts/prototypes/README.md` — concise command reference.
- `scripts/prototypes/summer_league_recap_mock.py` — earlier static rough mock; use the data-driven
  report script for the live post.

## Suggested next-session skills

- Use the project's normal visual-post workflow from `POSTING_WORKFLOW.md`.
- Use `browser:control-chrome` only if checking the current NBA.com game page or the logged-in
  Instagram account is necessary.
- Do not post or modify Instagram without explicit per-action approval.
