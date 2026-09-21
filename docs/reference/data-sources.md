# Data source decisions

Read the relevant heading when choosing or changing a fetch. These are observed endpoint contracts,
not guarantees that providers never change; reconcile fresh results before publishing.

## Choosing a source

Prefer NBA.com. When no dashboard publishes the stat, NBA.com play-by-play can often still answer
it: `and_one_leaders_data.py` counts and-1s from `PlayByPlayV3` because no endpoint reports them.
Costing that out beats assuming it is impractical; one Bulls season is 82 requests, and every
Chicago game since 1996-97 is about 2,400.

Use consistent NBA inputs for a post's statistical totals and league comparisons, even when
reconstructing them takes more effort. Do not mix another provider's derived totals into the
comparison merely to save fetching time. Basketball Reference remains suitable for MVP voting;
document other exceptions and their reason explicitly.

Reach for another provider when it carries something NBA.com does not (Basketball Reference for
BPM, hand-captured salary, pbpstats for parsed possessions), or for an audit. A provider's derived
column is a parse of NBA events, not an independent measurement, so two of them agreeing is weaker
evidence than it looks. Before publishing a number that rests on one, count a sample from the feed:
the and-1 columns disagree with the logs they come from, differently in different eras.

## Coverage and team scope

NBA clutch and starter/bench splits return empty frames before 1996-97 rather than reporting an
unsupported season. Check every season's coverage; never label that data full-franchise history.
`bench_points_leaders.py` reconciles bench + starter totals to unsplit totals and qualifies at 70%
bench appearances. `clutch_seasons_table.py` checks team-filtered stints against unfiltered seasons.

A team-filtered `LeagueDash*` row contains the requested stint but can carry the player's *last*
team abbreviation. Do not filter returned rows to `CHI` again. Ron Mercer's 2001-02 Bulls clutch
row is stamped `IND`; Hinrich's 2015-16 Bulls totals are stamped `ATL`. Verify requested-team totals
against independent totals. A stint may equal the full season if no relevant events followed a trade.

NBA.com has three season types: `Regular Season`, `Playoffs` and `PlayIn`. A "regular season and
playoffs" pool silently omits play-in games; fetch them or state the exclusion. Identify rookies with
the explicit Rookie filter (`player_experience_nullable="Rookie"`), not `CommonAllPlayers.FROM_YEAR`:
that field can be the draft year (Randy Holcomb: 2002, first game 2005-06) and counts 1976 ABA
merger veterans as first-year players (Artis Gilmore). Game Score needs complete box scores, which
NBA.com player logs have only from 1983-84; earlier games lack steals, blocks, turnovers or
offensive rebounds.

League-wide player totals can similarly be stamped with the last team; do not group them by team
to reconstruct team totals. `three_point_leaders.py` uses that pool for the league distribution only
and reconciles Chicago player 3PM/3PA to official team totals.

## Rosters and rates

Use `get_current_roster()` for current membership; `get_roster()` wraps a season roster and can lag
trades and draft picks. Team season statistics include departed players. Decide whether the post
compares a team's season or today's players; neither population substitutes for the other.

The Advanced endpoint reports minutes per game even with `PerMode=Totals`. Use
`get_team_player_advanced_stats()` to join Traditional total minutes to Advanced ratings.
DataBallR percentiles are position-adjusted, while our league-wide comparisons may not be. Name the
comparison population before interpreting a disagreement. The rookie table's hand-captured on/off
snapshot fills pre-2007-08 coverage unavailable from NBA.com and blanks values below 750 minutes.

## Efficient requests and unavailable fields

`LeagueDashPlayerShotLocations(distance_range="By Zone")` returns the league's player zone totals
in one request, with a two-level column index to flatten. Prefer it when the question needs totals,
not individual coordinates. `get_league_shots()` makes approximately 30 team requests; reuse it only
when shot-level data is needed. Zone points exclude free throws.

`get_game_shots()` derives league ID from the game prefix (`00` NBA, `15` Summer League).
A default regular-NBA `ShotChartDetail` request silently returns no Summer League rows. Summer
League's traditional box score can finalize before shot and advanced feeds; empty/all-zero derived
feeds remain unavailable. The older report uses FG%, whose denominator is unaffected by the 2026
one-free-throw rule; don't silently substitute TS% in that report.

NBA foul events do not provide usable foul-location coordinates. Borrowing the adjacent shot's
coordinates disproportionately captures and-ones and omits fouled misses (no FGA is charged), so
it cannot support a foul-location map. Use drive tracking for foul-drawing questions and name the
situation being counted. `LeagueDashPtStats` drive free throws and foul percentage can cross-check:
free throws per foul drawn was 1.971 in the audited 2025-26 sample; the 1.5–2.5 guard is a diagnostic
for field mismatch, not a reason to force a source value into that range.

## Manual and cached data

Salary data is not an NBA statistic. Use dated, sourced snapshots and permitted access rather than
building around blocked scrapers. `payroll_vs_wins.py` and its CSV header document the worked
reconciliation, including three wrong-team players in the source's 2015-16 payroll. Compare cap
share across years and distinguish rebuilding strategy from spending efficiency.

The NBA portrait CDN may return a grey silhouette with HTTP success and a nontrivial file size.
Use an actual silhouette/content check (see `assist_duos.is_silhouette`) and inspect replacements;
a minimum-byte check doesn't establish a usable headshot. Preserve per-post fallback portraits.

Keep successful source responses; record unavailable seasons and schema drift explicitly. The
source ownership and audit trail are defined in `docs/reference/provenance.md`.
