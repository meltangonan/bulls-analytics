# Summer League Report Handoff

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

This is why the report shows **eFG%** and not true shooting. TS% is `PTS / (2 × (FGA + 0.44 × FTA))`,
and the `0.44` coefficient assumes most trips to the line are two-shot trips. Under the one-FT rule
`FTA` roughly halves while points stay the same, so TS% inflates and becomes meaningless. eFG% only
touches field goals, so it survives the rule change untouched. **Do not print or cite TS% from these
games.**

## Working format

- Keep the general title `SUMMER LEAGUE REPORT`.
- Start with a compact final-score and team-stat snapshot.
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
- **Player-slide kicker repeats.** Every carousel slide currently shows the same kicker line
  ("N Bulls stories from the game"). On player slides it could read "Player story · 2 of 4" instead.
  Cheap to add during the refinement gate once real data is in front of us; deferred.
- **Footnote disclosure.** The footnote still reads `Summer League game · Data via NBA.com/Stats`.
  It does not disclose the shot-diet thresholds, which `AGENTS.md` asks for, nor the one-free-throw
  rule. The user chose to leave this for now.
- No `idea-catalog.html` card exists for this format yet.

## Current evidence

- Rehearsal game: Bulls 114, Pacers 105, July 14, 2025; NBA game ID `1522500033`.
- Both formats render clean against the rehearsal game: the single image (three lenses — Buzelis
  `shot_diet`, Essengue `impact`, Freeman-Liberty `role`) and the four-slide carousel (team front
  page + three player slides).
- `venv/bin/python -m pytest tests/test_summer_league_report.py -v` passes (11 tests); full suite
  passes (129 tests).
- Output PNGs are generated under `output/feed/` and are intentionally untracked.

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
