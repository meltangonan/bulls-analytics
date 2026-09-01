"""Build the Bulls' season three-point-percentage leader since 2010-11 for Canva.

Each season's most accurate qualifying Bulls three-point shooter is plotted as
his own portrait on a vertical timeline, against the accuracy a shooter needed
that season to sit in the top tenth of qualified NBA three-point shooters.

That benchmark is the point of the post. Comparing a team's *best* shooter to
the league *average* is a comparison whose answer is fixed before any data is
collected -- the maximum of a group beats its mean essentially always, and the
Bulls leader duly cleared the league average in all sixteen seasons. The top-10%
line is a bar the Bulls leader genuinely fails to clear in six of them, so the
crossings carry information rather than restating arithmetic.

Qualification is a flat minimum of 150 regular-season three-point attempts,
applied identically to the Bulls leader and to the league distribution behind
the benchmark. The bar matters more than it looks: at 50 attempts the 2001-02
"leader" shot 26-for-58, and at 200 the most recent season flips from Ayo
Dosunmu (45.1% on 193 attempts) to Nikola Vucevic (37.6%). 150 keeps at least
four qualifiers in every Bulls season while excluding sub-two-attempt-per-game
sample noise.

Three caveats belong in the caption rather than on the chart. A flat attempts
bar is harder in the shortened 2011-12 (66 games), 2019-20 and 2020-21 seasons;
it is harder in 2010-11 (four qualifying Bulls) than 2024-25 (eleven), because
league three-point volume roughly doubled across the window; and the Bulls
figure covers a player's Chicago-only stint while the league distribution behind
the percentile uses full-season lines, because NBA.com only splits a traded
player by stint when the request is scoped to one team.

NBA.com supplies every season from one endpoint pair, and each season's Bulls
player totals are reconciled against the Bulls' own team totals so a silently
mis-scoped response fails here rather than on the chart.

The renderer produces a transparent chart asset; Canva owns the title, subtitle,
source line, and page framing.
"""

from __future__ import annotations

import argparse
import math
import re
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

_REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO))

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import pandas as pd
import requests
from matplotlib.patches import FancyBboxPatch
from nba_api.stats.endpoints import leaguedashplayerstats, leaguedashteamstats

from bulls.config import API_DELAY, BULLS_TEAM_ID
from bulls.data.fetch import _NBA_HEADERS
from bulls.graphics import house
from bulls.graphics.house import (
    DRAFT_DPI,
    HEADSHOT_CACHE,
    ensure_headshots,
    export_dpi,
    helvetica,
    rendered_width,
)
from bulls.visuals import visual_dir

FIRST_SEASON_END_YEAR = 2011
LAST_SEASON_END_YEAR = 2026
MIN_THREE_POINT_ATTEMPTS = 150
BENCHMARK_PERCENTILE = 90  # "top 10% of qualified NBA three-point shooters"
RETRY_ATTEMPTS = 4
RETRY_BACKOFF = 4  # Each retry waits proportionally longer than API_DELAY.
SNAPSHOT_TZ = ZoneInfo("America/Chicago")
PROJECT = "three-point-leaders"

OUT = _REPO / "output" / "feed"
# Single-consumer data lives with its post from the first run, not in the ignored
# cache -- see AGENTS.md and tests/test_data_locations.py.
POST_DATA = visual_dir(_REPO / "docs" / "visuals", PROJECT) / "data"
RAW = POST_DATA / "raw"
# NBA's CDN serves no portrait for Nate Robinson, only the grey silhouette. This
# copy was hand-sourced for the 2026-08-20 height ladder; portraits here win over
# the shared cache so the post carries the image it actually renders.
PORTRAITS = POST_DATA / "portraits"

NBA_PLAYER_URL = (
    "https://www.nba.com/stats/players/traditional"
    "?PerMode=Totals&Season={season}&SeasonType=Regular%20Season"
    f"&TeamID={BULLS_TEAM_ID}"
)
NBA_TEAM_URL = (
    "https://www.nba.com/stats/teams/traditional"
    "?PerMode=Totals&Season={season}&SeasonType=Regular%20Season"
)
NBA_LEAGUE_PLAYER_URL = (
    "https://www.nba.com/stats/players/traditional"
    "?PerMode=Totals&Season={season}&SeasonType=Regular%20Season"
)

# The timeline runs down the page: seasons are rows, accuracy is the x axis.
# Sixteen surnames cannot be made legible on a horizontal time axis at the width
# a 1080 px page gives them, and a vertical layout has a whole row for each.
CHART_WIDTH = 1800
CHART_HEIGHT = 2200

SEASON_LABEL_X = 185
# The plot is deliberately wide relative to the canvas: a two-percentage-point
# gridline gap is 11% of the chart width, up from 7.7%. Like the portrait size,
# only the ratio survives Canva scaling the asset onto the page -- widening the
# plot in pixels alone would change nothing a reader ever sees.
PLOT_LEFT = 250
PLOT_RIGHT = 1438
# The axis is fitted to the series actually drawn, snapped out to even
# percentages. A fixed 34% floor spent a fifth of the width on a band no Bulls
# leader ever entered; adding the league-average line widens it on demand.
AXIS_PAD = 0.6
AXIS_STEP = 2.0

FIRST_ROW_Y = 2070
ROW_HEIGHT = 128
AXIS_LABEL_Y = 2170
GRID_TOP = 2145
GRID_BOTTOM = 120

# The portraits are the series -- no line connects them -- so they are sized as a
# share of the chart width rather than in pixels. A chart drawn wider and a
# portrait drawn bigger cancel out once Canva scales the asset onto the page;
# only the ratio survives. With sixteen rows the asset is taller than a 4:5 page,
# so it lands height-constrained and the ratio that matters is portrait to chart
# *height*, not width -- which is why the rows are packed to a 4 px gap.
HEADSHOT_HALF = 62
HEADSHOT_CROP_FRACTION = 0.68
# NBA portraits are not framed identically. Mike Dunleavy sits low enough in his
# that hair-to-chin is fractionally taller than the standard window: shifting the
# window down only trades a cut chin for cut hair, so he needs a slightly taller
# one. The drawn size grows with it, which keeps his head the same size as every
# other face -- a wider crop at a fixed drawn size would shrink him instead.
CROP_FRACTIONS = {2399: 0.74}  # Mike Dunleavy
LABEL_GAP = 18          # portrait edge to the name
VALUE_GAP = 11          # name to the percentage

# Both series labels hang the same distance below the last row so they read as a
# pair rather than a stack. The drop is derived from the portrait rather than
# fixed: either label can land at nearly the same x as the last portrait, and
# with the newest season on top the bottom row is 2010-11, whose leader sits
# within 0.2 points of the benchmark. A literal value here collided the moment
# the row order flipped.
SERIES_LABEL_DROP = HEADSHOT_HALF + 28
NAME_RISE = 18          # name and percentage sit above the row centre
LINE_DROP = 24          # the made-attempted line sits below it

# Every vertical rule is a light grey: the gridlines quietest, the two reference
# series a step darker so they still read as data. Grey is the right register for
# all three -- they are scaffolding, not the subject (DESIGN.md §2).
# This chart takes no theme. The page canvas changes from post to post, the asset
# is always transparent, and the only meaningful colours are Bulls red and the
# house near-black -- so the palette is stated here rather than resolved through
# a canvas-dependent theme (DESIGN.md §2).
#
# #242424 is the account's black: nothing in a graphic is pure or near-pure black.
INK = "#242424"
SUPPORT_GREY = "#5F5B57"   # the made-attempted line, subordinate to the name
# Chart greys must read on the page canvas, which Canva owns and which varies:
# #FAF8F5 through at least #E9E5E1. A gridline tuned to the lightest canvas is
# invisible on the darker one -- #E6E2DB vanished on #E9E5E1, a 5-value
# difference. These are chosen to hold across that whole range.
GRIDLINE = "#D8D2CA"
# Labels all read at one weight -- season, accuracy axis, and both series names.
# The rules they annotate stay grey; the words naming them do not, so the reader
# can find the axis without the axis competing with the portraits.
BENCHMARK_GREY = "#A8A199"
LEAGUE_GREY = "#BEB7AD"
# Hierarchy comes from weight and dash length as much as tone: the benchmark is
# heavier with long dashes, the league average lighter with short ones, so the
# league line reads without competing.
BENCHMARK_WIDTH = 2.0
LEAGUE_WIDTH = 1.5


@dataclass(frozen=True)
class ChartType:
    """Type sizing for the leader timeline at 1400 x 1520."""

    value: float = 15.5
    season: float = 14.0
    name: float = 15.5
    line: float = 12.5
    axis: float = 14.0
    series: float = 13.0


CHART_TYPE = ChartType()

SEASON_COLUMNS = [
    "season",
    "season_end_year",
    "player_id",
    "player_name",
    "games_played",
    "team_games",
    "three_pm",
    "three_pa",
    "three_pct",
    "qualified",
]
LEAGUE_COLUMNS = [
    "season",
    "season_end_year",
    "team_games",
    "league_three_pm",
    "league_three_pa",
    "league_three_pct",
    "league_three_pa_per_team_game",
    "benchmark_three_pct",
    "qualified_shooters",
    "bulls_three_pct",
    "bulls_three_pa_per_game",
    "bulls_attempt_rank",
]

NAME_SUFFIXES = {"jr.", "jr", "sr.", "sr", "ii", "iii", "iv", "v"}


def season_label(end_year: int) -> str:
    """Return an NBA end year as an NBA.com season string."""
    return f"{end_year - 1}-{str(end_year)[-2:]}"


def display_season(end_year: int) -> str:
    """Return the row label for one season. A row has width for the full form."""
    return season_label(end_year)


def last_name(full_name: str) -> str:
    """Return the surname a Bulls fan would recognise on a crowded axis.

    Generational suffixes are dropped and internal capitals are preserved, so
    "Zach LaVine" stays LaVine rather than becoming LAVINE or Lavine.
    """
    parts = [p for p in re.split(r"\s+", full_name.strip()) if p]
    while len(parts) > 1 and parts[-1].lower().strip(".") in NAME_SUFFIXES:
        parts.pop()
    return parts[-1] if parts else full_name


def _fetch_frame(endpoint, **kwargs) -> pd.DataFrame:
    """Call one NBA.com endpoint, retrying the timeouts it hands out freely."""
    last_error: Exception | None = None
    for attempt in range(RETRY_ATTEMPTS):
        time.sleep(API_DELAY * (1 + attempt * RETRY_BACKOFF))
        try:
            return endpoint(timeout=60, headers=_NBA_HEADERS, **kwargs).get_data_frames()[0]
        except (requests.Timeout, requests.ConnectionError) as error:
            last_error = error
            print(f"  NBA.com timed out; retry {attempt + 1} of {RETRY_ATTEMPTS - 1}")
    raise RuntimeError(f"NBA.com did not respond after {RETRY_ATTEMPTS} attempts.") from last_error


def _cached_frame(path: Path, fetch) -> pd.DataFrame:
    if path.exists():
        return pd.read_csv(path)
    frame = fetch()
    RAW.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, index=False)
    return frame


def fetch_season(
    end_year: int, *, refresh: bool = False
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Return one season's Chicago-only player totals, all 30 team totals, and
    every player in the league.

    The Chicago call is scoped to the team, which is the only way NBA.com splits
    a traded player into stints. The league-wide call cannot be split that way --
    it returns one row per player, tagged with the last team he appeared for --
    so it is used only for the accuracy distribution, never for team attribution.
    """
    season = season_label(end_year)
    player_path = RAW / f"chi-players-{end_year}.csv"
    team_path = RAW / f"league-teams-{end_year}.csv"
    league_player_path = RAW / f"league-players-{end_year}.csv"
    if refresh:
        player_path.unlink(missing_ok=True)
        team_path.unlink(missing_ok=True)
        league_player_path.unlink(missing_ok=True)

    players = _cached_frame(
        player_path,
        lambda: _fetch_frame(
            leaguedashplayerstats.LeagueDashPlayerStats,
            season=season,
            season_type_all_star="Regular Season",
            per_mode_detailed="Totals",
            team_id_nullable=BULLS_TEAM_ID,
        ),
    )
    teams = _cached_frame(
        team_path,
        lambda: _fetch_frame(
            leaguedashteamstats.LeagueDashTeamStats,
            season=season,
            season_type_all_star="Regular Season",
            per_mode_detailed="Totals",
        ),
    )
    league_players = _cached_frame(
        league_player_path,
        lambda: _fetch_frame(
            leaguedashplayerstats.LeagueDashPlayerStats,
            season=season,
            season_type_all_star="Regular Season",
            per_mode_detailed="Totals",
        ),
    )
    return players, teams, league_players


def _require(frame: pd.DataFrame, columns: set[str], label: str) -> None:
    missing = columns - set(frame.columns)
    if missing:
        raise ValueError(f"NBA.com {label} is missing {sorted(missing)}.")


def build_tables(refresh: bool = False) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Return every Bulls player-season and one league row per season.

    The reconciliation here is the load-bearing check: Chicago-only player
    three-point totals must sum exactly to the Bulls' team totals, which catches
    a response scoped to the wrong team or truncated mid-roster.
    """
    season_rows: list[dict] = []
    league_rows: list[dict] = []

    for end_year in range(FIRST_SEASON_END_YEAR, LAST_SEASON_END_YEAR + 1):
        season = season_label(end_year)
        players, teams, league_players = fetch_season(end_year, refresh=refresh)
        _require(players, {"PLAYER_ID", "PLAYER_NAME", "GP", "FG3M", "FG3A"}, f"{season} players")
        _require(teams, {"TEAM_ID", "GP", "FG3M", "FG3A"}, f"{season} teams")
        _require(league_players, {"PLAYER_ID", "FG3M", "FG3A"}, f"{season} league players")

        if league_players["PLAYER_ID"].duplicated().any():
            raise ValueError(f"{season}: NBA.com returned duplicate league players.")
        shooters = league_players[league_players["FG3A"] >= MIN_THREE_POINT_ATTEMPTS]
        if len(shooters) < 50:
            raise ValueError(
                f"{season}: only {len(shooters)} qualified league shooters -- too few "
                "for a stable percentile."
            )
        benchmark = float(
            (shooters["FG3M"] / shooters["FG3A"] * 100).quantile(BENCHMARK_PERCENTILE / 100)
        )

        if len(teams) < 29:
            raise ValueError(f"{season}: NBA.com returned only {len(teams)} team rows.")
        if players["PLAYER_ID"].duplicated().any():
            raise ValueError(f"{season}: NBA.com returned duplicate Bulls players.")

        bulls = teams.loc[teams["TEAM_ID"] == BULLS_TEAM_ID]
        if len(bulls) != 1:
            raise ValueError(f"{season}: {len(bulls)} Bulls team rows, expected exactly one.")
        bulls = bulls.iloc[0]
        team_games = int(bulls["GP"])
        team_3pm, team_3pa = int(bulls["FG3M"]), int(bulls["FG3A"])

        player_3pm = int(pd.to_numeric(players["FG3M"], errors="raise").sum())
        player_3pa = int(pd.to_numeric(players["FG3A"], errors="raise").sum())
        if (player_3pm, player_3pa) != (team_3pm, team_3pa):
            raise ValueError(
                f"{season}: Bulls player threes ({player_3pm}-{player_3pa}) do not reconcile "
                f"to the team total ({team_3pm}-{team_3pa})."
            )

        attempts_per_game = teams["FG3A"] / teams["GP"]
        rank = int(attempts_per_game.rank(ascending=False, method="min")[teams["TEAM_ID"] == BULLS_TEAM_ID].iloc[0])
        league_3pm = int(teams["FG3M"].sum())
        league_3pa = int(teams["FG3A"].sum())
        league_rows.append(
            {
                "season": season,
                "season_end_year": end_year,
                "team_games": team_games,
                "league_three_pm": league_3pm,
                "league_three_pa": league_3pa,
                "league_three_pct": league_3pm / league_3pa * 100,
                "league_three_pa_per_team_game": league_3pa / int(teams["GP"].sum()),
                "benchmark_three_pct": benchmark,
                "qualified_shooters": int(len(shooters)),
                "bulls_three_pct": team_3pm / team_3pa * 100,
                "bulls_three_pa_per_game": team_3pa / team_games,
                "bulls_attempt_rank": rank,
            }
        )

        for _, player in players.iterrows():
            attempts = int(player["FG3A"])
            season_rows.append(
                {
                    "season": season,
                    "season_end_year": end_year,
                    "player_id": int(player["PLAYER_ID"]),
                    "player_name": str(player["PLAYER_NAME"]),
                    "games_played": int(player["GP"]),
                    "team_games": team_games,
                    "three_pm": int(player["FG3M"]),
                    "three_pa": attempts,
                    "three_pct": (int(player["FG3M"]) / attempts * 100) if attempts else float("nan"),
                    "qualified": attempts >= MIN_THREE_POINT_ATTEMPTS,
                }
            )

    return (
        pd.DataFrame(season_rows, columns=SEASON_COLUMNS),
        pd.DataFrame(league_rows, columns=LEAGUE_COLUMNS),
    )


def build_leaders(season_table: pd.DataFrame, league_table: pd.DataFrame) -> pd.DataFrame:
    """Return one qualifying accuracy leader per season, with league context."""
    leaders: list[dict] = []
    for end_year, group in season_table.groupby("season_end_year", sort=True):
        qualified = group[group["qualified"]].sort_values(
            ["three_pct", "three_pa"], ascending=[False, False]
        )
        if qualified.empty:
            raise ValueError(
                f"{season_label(end_year)}: no Bull reached "
                f"{MIN_THREE_POINT_ATTEMPTS} three-point attempts."
            )
        top = qualified.iloc[0]
        # A genuine tie would make "the leader" a coin flip; say so rather than
        # letting sort order pick silently.
        ties = qualified[qualified["three_pct"].round(4) == round(float(top["three_pct"]), 4)]
        if len(ties) > 1:
            raise ValueError(
                f"{season_label(end_year)}: {len(ties)} players tie at "
                f"{top['three_pct']:.4f}% -- the leader needs a stated tiebreak."
            )
        league = league_table.loc[league_table["season_end_year"] == end_year].iloc[0]
        leaders.append(
            {
                "season": top["season"],
                "season_end_year": int(end_year),
                "player_id": int(top["player_id"]),
                "player_name": top["player_name"],
                "last_name": last_name(top["player_name"]),
                "three_pm": int(top["three_pm"]),
                "three_pa": int(top["three_pa"]),
                "three_pct": float(top["three_pct"]),
                "league_three_pct": float(league["league_three_pct"]),
                "benchmark_three_pct": float(league["benchmark_three_pct"]),
                "qualified_shooters": int(league["qualified_shooters"]),
                "beat_benchmark": float(top["three_pct"]) > float(league["benchmark_three_pct"]),
                "edge": float(top["three_pct"]) - float(league["benchmark_three_pct"]),
                "qualifiers": int(len(qualified)),
                "runner_up": qualified.iloc[1]["player_name"] if len(qualified) > 1 else "",
                "runner_up_pct": float(qualified.iloc[1]["three_pct"]) if len(qualified) > 1 else float("nan"),
            }
        )
    return pd.DataFrame(leaders)


def validate(leaders: pd.DataFrame) -> dict[str, object]:
    """Fail on anything that would render off the chart, and report the headline."""
    expected = LAST_SEASON_END_YEAR - FIRST_SEASON_END_YEAR + 1
    if len(leaders) != expected:
        raise ValueError(f"Expected {expected} seasons, built {len(leaders)}.")
    series = [leaders["three_pct"], leaders["league_three_pct"], leaders["benchmark_three_pct"]]
    lows = pd.concat(series).min()
    highs = pd.concat(series).max()
    # The axis is fitted to the data, so the guard is on plausibility instead:
    # a leader outside this band means the qualification rule broke, not that the
    # chart needs rescaling.
    if lows < 30.0 or highs > 55.0:
        raise ValueError(f"Values span {lows:.1f}%-{highs:.1f}%, which is not a plausible 3P%.")
    best = leaders.loc[leaders["three_pct"].idxmax()]
    return {
        "first_season": leaders["season"].iloc[0],
        "last_season": leaders["season"].iloc[-1],
        "distinct_players": int(leaders["player_name"].nunique()),
        "seasons": int(len(leaders)),
        "best_name": best["player_name"],
        "best_season": best["season"],
        "best_pct": float(best["three_pct"]),
        "best_line": f"{int(best['three_pm'])}-of-{int(best['three_pa'])}",
        "league_low": float(leaders["league_three_pct"].min()),
        "league_high": float(leaders["league_three_pct"].max()),
        "leader_low": float(leaders["three_pct"].min()),
        "leader_high": float(leaders["three_pct"].max()),
        "min_qualifiers": int(leaders["qualifiers"].min()),
        "max_qualifiers": int(leaders["qualifiers"].max()),
        "beat_count": int(leaders["beat_benchmark"].sum()),
        "missed_count": int((~leaders["beat_benchmark"]).sum()),
        "benchmark_low": float(leaders["benchmark_three_pct"].min()),
        "benchmark_high": float(leaders["benchmark_three_pct"].max()),
        "shooters_low": int(leaders["qualified_shooters"].min()),
        "shooters_high": int(leaders["qualified_shooters"].max()),
        "missed_seasons": ", ".join(leaders.loc[~leaders["beat_benchmark"], "season"]),
    }


def axis_bounds(values: list[float]) -> tuple[float, float, list[float]]:
    """Return the axis floor, ceiling and gridline ticks fitted to the data."""
    low = math.floor((min(values) - AXIS_PAD) / AXIS_STEP) * AXIS_STEP
    high = math.ceil((max(values) + AXIS_PAD) / AXIS_STEP) * AXIS_STEP
    ticks = []
    tick = low
    while tick <= high + 1e-9:
        ticks.append(round(tick, 1))
        tick += AXIS_STEP
    return low, high, ticks


def _x(percent: float, low: float, high: float) -> float:
    """Map a three-point percentage onto the horizontal accuracy axis."""
    return PLOT_LEFT + (percent - low) / (high - low) * (PLOT_RIGHT - PLOT_LEFT)


def _row_y(index: int) -> float:
    """Map a season's position onto its row. The timeline runs down the page."""
    return FIRST_ROW_Y - index * ROW_HEIGHT


def portrait_path(player_id: int) -> Path:
    """Return the portrait to draw, preferring this post's own hand-sourced copy."""
    local = PORTRAITS / f"{player_id}.png"
    return local if local.is_file() else HEADSHOT_CACHE / f"{player_id}.png"


def top_anchored_headshot(ax, image_path, x, y, half_size, *, crop=HEADSHOT_CROP_FRACTION, zorder=5):
    """Place a full-colour, top-anchored square crop of one player's portrait.

    The NBA CDN serves a player's *current* portrait, so a chart spanning 2010 to
    2026 arrives with several leaders in the uniform of a team they joined years
    later. Anchoring the crop to the top of the frame shows more face and less
    jersey, which keeps those off-brand colours from becoming blocks (DESIGN.md
    §5). A missing file becomes a neutral placeholder rather than a crash.
    """
    try:
        image = plt.imread(image_path)
    except (FileNotFoundError, OSError, ValueError):
        return ax.add_patch(
            FancyBboxPatch(
                (x - half_size, y - half_size),
                2 * half_size,
                2 * half_size,
                boxstyle="square,pad=0",
                facecolor="#DDD8D1",
                edgecolor="none",
                zorder=zorder,
            )
        )
    height, width = image.shape[:2]
    side = max(1, round(min(height, width) * crop))
    left = max(0, (width - side) // 2)
    square = image[:side, left:left + side]
    # Source pixels per drawn pixel is held constant, so a portrait cropped wider
    # is drawn correspondingly bigger and every head lands at the same scale.
    drawn = half_size * crop / HEADSHOT_CROP_FRACTION
    return ax.imshow(
        square,
        extent=[x - drawn, x + drawn, y - drawn, y + drawn],
        interpolation="bilinear",
        zorder=zorder,
    )


def render_chart(
    leaders: pd.DataFrame, date: str, *, final: bool = False, show_league: bool = True
) -> Path:
    """Render the transparent vertical leader timeline for Canva."""
    # Newest season on top. The tables stay chronological -- only the drawing
    # order flips -- so the reader meets the current roster first and reads back
    # into history rather than scrolling through a decade to reach today.
    leaders = leaders.iloc[::-1].reset_index(drop=True)
    count = len(leaders)
    fig = plt.figure(
        figsize=(CHART_WIDTH / DRAFT_DPI, CHART_HEIGHT / DRAFT_DPI), facecolor="none"
    )
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, CHART_WIDTH)
    ax.set_ylim(0, CHART_HEIGHT)
    ax.axis("off")

    drawn = list(leaders["three_pct"]) + list(leaders["benchmark_three_pct"])
    if show_league:
        drawn += list(leaders["league_three_pct"])
    low, high, ticks = axis_bounds([float(v) for v in drawn])

    for tick in ticks:
        x = _x(tick, low, high)
        ax.plot([x, x], [GRID_BOTTOM, GRID_TOP], color=GRIDLINE, linewidth=1.2, zorder=0)
        ax.text(
            x,
            AXIS_LABEL_Y,
            f"{tick:.0f}%",
            ha="center",
            va="center",
            fontsize=CHART_TYPE.axis,
            color=INK,
            fontproperties=helvetica(),
            zorder=1,
        )

    ys = [_row_y(i) for i in range(count)]
    leader_x = [_x(float(v), low, high) for v in leaders["three_pct"]]
    benchmark_x = [_x(float(v), low, high) for v in leaders["benchmark_three_pct"]]

    # The benchmark is context, so it takes the muted dashed reference grammar
    # from DESIGN.md §4 rather than a second bright colour.
    ax.plot(
        benchmark_x, ys, color=BENCHMARK_GREY, linewidth=BENCHMARK_WIDTH,
        linestyle=(0, (5, 3)), zorder=2,
    )
    if show_league:
        league_x = [_x(float(v), low, high) for v in leaders["league_three_pct"]]
        ax.plot(
            league_x, ys, color=LEAGUE_GREY, linewidth=LEAGUE_WIDTH,
            linestyle=(0, (2, 3)), zorder=2,
        )
        ax.text(
            league_x[-1], ys[-1] - SERIES_LABEL_DROP, "NBA AVERAGE",
            ha="center", va="center",
            fontsize=CHART_TYPE.series, color=INK,
            fontproperties=helvetica("bold"), zorder=4,
        )

    for index, (_, row) in enumerate(leaders.iterrows()):
        y = ys[index]
        ax.text(
            SEASON_LABEL_X,
            y,
            display_season(int(row["season_end_year"])),
            ha="right",
            va="center",
            fontsize=CHART_TYPE.season,
            color=INK,
            fontproperties=helvetica(),
            zorder=4,
        )
        top_anchored_headshot(
            ax, portrait_path(int(row["player_id"])), leader_x[index], y,
            HEADSHOT_HALF,
            crop=CROP_FRACTIONS.get(int(row["player_id"]), HEADSHOT_CROP_FRACTION),
            zorder=5,
        )
        # The label sits on the side of the portrait away from the benchmark, so
        # the dashed line never runs behind a surname. Every percentage is red:
        # whether a season cleared the benchmark is carried by which side of the
        # line the portrait sits on, so colour would be a second encoding of one
        # fact rather than a second fact.
        flip = benchmark_x[index] > leader_x[index]
        edge = leader_x[index] + (-1 if flip else 1) * (HEADSHOT_HALF + LABEL_GAP)
        align = "right" if flip else "left"
        made = f"{int(row['three_pm'])}-{int(row['three_pa'])}"

        if flip:
            value = ax.text(
                edge, y + NAME_RISE, f"{row['three_pct']:.1f}%", ha=align, va="center",
                fontsize=CHART_TYPE.value, color=house.RED,
                fontproperties=helvetica("bold"), zorder=6,
            )
            name = ax.text(
                edge - rendered_width(ax, value) - VALUE_GAP, y + NAME_RISE,
                row["last_name"], ha=align, va="center", fontsize=CHART_TYPE.name,
                color=INK, fontproperties=helvetica("bold"), zorder=6,
            )
            outer = name.get_position()[0] - rendered_width(ax, name)
            if outer < SEASON_LABEL_X + 24:
                raise ValueError(f"The label for {row['player_name']} runs into the season column.")
        else:
            name = ax.text(
                edge, y + NAME_RISE, row["last_name"], ha=align, va="center",
                fontsize=CHART_TYPE.name, color=INK,
                fontproperties=helvetica("bold"), zorder=6,
            )
            value = ax.text(
                edge + rendered_width(ax, name) + VALUE_GAP, y + NAME_RISE,
                f"{row['three_pct']:.1f}%", ha=align, va="center",
                fontsize=CHART_TYPE.value, color=house.RED,
                fontproperties=helvetica("bold"), zorder=6,
            )
            outer = value.get_position()[0] + rendered_width(ax, value)
            if outer > CHART_WIDTH - 20:
                raise ValueError(f"The label for {row['player_name']} runs off the chart.")

        # Made-attempted, quieter and italic: it qualifies the percentage above it
        # rather than competing with it, and it is what stops 45.1% being read
        # without knowing it rests on 193 attempts.
        ax.text(
            edge, y - LINE_DROP, made, ha=align, va="center",
            fontsize=CHART_TYPE.line, color=SUPPORT_GREY,
            fontproperties=helvetica("oblique"), zorder=6,
        )

    ax.text(
        benchmark_x[-1],
        ys[-1] - SERIES_LABEL_DROP,
        f"TOP {100 - BENCHMARK_PERCENTILE}% OF NBA SHOOTERS",
        ha="center",
        va="center",
        fontsize=CHART_TYPE.series,
        color=INK,
        fontproperties=helvetica("bold"),
        zorder=4,
    )

    OUT.mkdir(parents=True, exist_ok=True)
    suffix = "final" if final else "draft"
    variant = "" if show_league else "-no-league"
    path = OUT / f"{date}-bulls-three-point-leaders{variant}-{suffix}.png"
    fig.savefig(path, dpi=export_dpi(final), transparent=True, pad_inches=0)
    plt.close(fig)
    return path


def write_working_tables(
    season_table: pd.DataFrame, league_table: pd.DataFrame, leaders: pd.DataFrame
) -> tuple[Path, Path, Path]:
    """Write every player-season, every league season, and the ranked leaders."""
    POST_DATA.mkdir(parents=True, exist_ok=True)
    seasons_path = POST_DATA / "bulls-player-seasons.csv"
    league_path = POST_DATA / "league-seasons.csv"
    leaders_path = POST_DATA / "season-leaders.csv"
    season_table.to_csv(seasons_path, index=False)
    league_table.to_csv(league_path, index=False)
    leaders.to_csv(leaders_path, index=False)
    return seasons_path, league_path, leaders_path


def canva_copy_block(report: dict[str, object], leaders: pd.DataFrame) -> str:
    """Return the exact data-bound framing to paste around the chart asset."""
    return "\n".join(
        [
            "CANVA COPY",
            "TITLE: THE BULLS' BEST SHOOTER",
            "SUBTITLE: The most accurate Bull from three, every season since "
            f"{report['first_season']} — against the NBA's top tenth",
            "FOOTER: Data via nba.com | "
            f"{report['first_season']} to {report['last_season']} regular seasons | "
            f"Min. {MIN_THREE_POINT_ATTEMPTS} 3PA, Chicago-only stints | "
            f"Benchmark: {BENCHMARK_PERCENTILE}th percentile of qualified NBA shooters",
            f"NOTE: {report['distinct_players']} different players in "
            f"{report['seasons']} seasons. The Bulls' best shooter missed the NBA's "
            f"top tenth in {report['missed_count']} of them ({report['missed_seasons']}).",
            f"AUDIT: {report['best_name']} {report['best_season']} is the high mark at "
            f"{report['best_pct']:.1f}% ({report['best_line']}); leaders span "
            f"{report['leader_low']:.1f}–{report['leader_high']:.1f}%; "
            f"{report['min_qualifiers']}–{report['max_qualifiers']} qualifiers per season.",
        ]
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build the Bulls season three-point-percentage leader chart asset."
    )
    parser.add_argument(
        "--refresh", action="store_true", help="Refetch every cached NBA.com season response."
    )
    parser.add_argument(
        "--final", action="store_true", help="Export at final resolution after the draft is approved."
    )
    parser.add_argument(
        "--no-league",
        action="store_true",
        help="Drop the league-average line and fit the axis to the benchmark alone.",
    )
    args = parser.parse_args()

    snapshot = datetime.now(SNAPSHOT_TZ)
    season_table, league_table = build_tables(refresh=args.refresh)
    leaders = build_leaders(season_table, league_table)
    report = validate(leaders)
    seasons_path, league_path, leaders_path = write_working_tables(
        season_table, league_table, leaders
    )
    ensure_headshots(leaders["player_id"].tolist())
    chart_path = render_chart(
        leaders, snapshot.date().isoformat(), final=args.final, show_league=not args.no_league
    )

    print(f"Player seasons: {seasons_path}")
    print(f"League seasons: {league_path}")
    print(f"Leaders:        {leaders_path}")
    print(f"Chart:          {chart_path}")
    print()
    print(f"{'SEASON':8} {'LEADER':20} {'LINE':>10} {'3P%':>7} {'TOP10%':>7} {'EDGE':>6}  ")
    for _, row in leaders.iterrows():
        mark = "" if row["beat_benchmark"] else "  <- below"
        print(
            f"{row['season']:8} {row['player_name'][:20]:20} "
            f"{row['three_pm']:3d}-{row['three_pa']:<6d} {row['three_pct']:6.1f}% "
            f"{row['benchmark_three_pct']:6.1f}% {row['edge']:+5.1f}{mark}"
        )
    print()
    print(canva_copy_block(report, leaders))


if __name__ == "__main__":
    main()
