# ACTIVE — 2025–26 Bulls assist-duos post

## Objective

Create a separate `@chicagobullsdata` post showing which Bulls pairs produced the most assisted
baskets for one another during the 2025–26 regular season.

This is a companion to the most-used two-player lineup table, not an extra metric for that table.
Do not combine shared-minutes ratings and player-to-player assists in one graphic.

## Settled direction

- Population: all players who logged a 2025–26 regular-season Bulls stint, including players later
  traded away. This is a completed-season Chicago recap, not a current-roster view.
- Rank the top five unordered pairs by **combined assists between the two players**:
  `A assists B + B assists A`.
- Preserve the directional split in the graphic. A combined total without the two directions hides
  whether the relationship was balanced or primarily creator-to-finisher.
- Treat this as a volume post: "most productive assist connections," not "best chemistry" or
  "most efficient duo." Minutes, role, and ballhandling responsibility drive totals.
- Start with one ranked board or table row per pair. The likely row anatomy is two player names or
  headshots, the two directional counts, and one prominent combined total.
- Keep the first version simple. Do not begin with per-100 shared-possession rates, an assist
  network, or play-by-play reconstruction.
- Build one transparent Python chart asset for Canva assembly. Canva owns the title, subtitle,
  coverage/source line, and handle.

## Confirmed NBA.com data path

The installed `nba_api` package exposes:

```python
from nba_api.stats.endpoints import playerdashptpass
```

`PlayerDashPtPass` takes `team_id`, `player_id`, `season`, and
`season_type_all_star`. Its `PassesMade` dataset includes:

- `PLAYER_ID` and `PLAYER_NAME_LAST_FIRST`
- `PASS_TO`
- `PASS_TEAMMATE_PLAYER_ID`
- `PASS`
- `AST`
- made/attempted field-goal columns from those passes

Use the existing Bulls ID and NBA request headers from `bulls.data.fetch`. A live 2025–26 check
returned:

- Josh Giddey → Matas Buzelis: **84 assists**
- Matas Buzelis → Josh Giddey: **13 assists**
- Proposed combined duo total: **97**

That check establishes feasibility; it is not a complete leaderboard.

## Aggregation guardrail

Fetch **`PassesMade` only** for every Bulls player. Do not append `PassesReceived`, because it is the
same relationship viewed from the recipient and would double-count the events.

For each directional row:

1. Keep the passer ID, recipient ID, passer name, recipient name, and `AST`.
2. Create a canonical unordered pair key by sorting the two player IDs.
3. Retain the original passer/recipient orientation for the directional display.
4. Sum both orientations to produce the pair's combined total.
5. Rank the unordered pairs by that combined total and select the top five.

Build the season's Bulls player-ID list from a Chicago-filtered team/player endpoint, not from the
current roster. `bulls.data.get_team_player_advanced_stats(season="2025-26")` is one existing source
of team-stint player IDs.

## Required validation

- Confirm the selected player list represents Bulls stints rather than the July 2026 roster.
- Confirm every `(passer_id, recipient_id)` directional key is unique before aggregation.
- For representative high-volume passers, compare the sum of `PassesMade.AST` with their
  Chicago-stint assist total and explain any NBA tracking discrepancy rather than silently forcing
  equality.
- Confirm the two directions sum exactly to every displayed combined total.
- Inspect names for traded players and do not infer stint scope from a returned current/later team
  abbreviation.
- Save a date-stamped analytical CSV containing both directional rows and the combined totals before
  rendering.
- Keep coverage and source language explicit: `2025–26 regular season` and `NBA.com/Stats`.

Use play-by-play only as a fallback or cross-check if the passing endpoint proves incomplete. A
full play-by-play pipeline would add substantially more collection and identity-matching work
without improving the first version's basketball question.

## Working copy direction

- Working title: **THE BULLS’ TOP ASSIST CONNECTIONS**
- Working subtitle: **The five pairs that created the most baskets for one another**
- Qualification: **2025–26 regular season · Combined assists in both directions**
- Method note: **Totals reflect made baskets officially credited with an assist; volume is affected
  by minutes and offensive role.**
- Source: **Data via NBA.com/Stats**

Treat these as starting words, not approved final copy.

## Work completed

- Confirmed that NBA.com's player-to-player passing endpoint is available in the project venv.
- Inspected the endpoint's expected `PassesMade` and `PassesReceived` columns.
- Successfully fetched the Giddey directional rows quoted above.
- Chose a combined-total ranking with the two directions preserved.
- Confirmed this should remain a separate post from the two-player on-court ratings table.

No assist-duos fetcher, analysis function, chart code, tests, catalog card, or final graphic has been
created yet.

## Clearest next action

Use the `create-bulls-post` skill. Read `AGENTS.md`, `DESIGN.md`, `POSTING_WORKFLOW.md`, and
`DEVELOPMENT.md`, then fetch the full Bulls player-to-player passing table and show the validated top
five pairs before making the graphic. Preserve the decisions above and keep the implementation
post-specific until a second use proves that a reusable fetcher or chart builder is needed.
