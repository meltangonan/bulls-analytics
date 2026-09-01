"""Build the Bulls' biggest year-over-year scoring leaps since 2000 for Canva.

NBA.com supplies every Chicago-only player-season from 1999-00 onward from one
source, so a leap is measured between two consecutive seasons a player spent
with the Bulls. The ranked metric is points per 36 minutes. Raw points per game
remains in the audit tables for metric QA but is not printed on the chart.

Points per 36 rather than points per game is the whole point of the post.  Across
the qualifying pairs, a per-game gain correlates +0.73 with the player's gain in
minutes per game while a per-36 gain correlates +0.26, so a per-game ranking
largely measures a role increase rather than an improvement.  The script prints
both correlations on every run -- if the per-36 figure drifts toward the per-game
one, the metric stopped doing its job.

The renderer produces a transparent chart asset; Canva owns the title and page
framing.
"""

from __future__ import annotations

import argparse
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
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch
from nba_api.stats.endpoints import leaguedashplayerstats, leaguedashteamstats

from bulls.config import API_DELAY, BULLS_TEAM_ID
from bulls.data.fetch import _NBA_HEADERS
from bulls.graphics.house import (
    DEFAULT_THEME,
    DRAFT_DPI,
    HEADSHOT_CACHE,
    ensure_headshots,
    export_dpi,
    helvetica,
    rendered_width,
)


# The first leap needs a prior season, so the fetch starts one season early.
FIRST_SEASON_END_YEAR = 2000
LAST_SEASON_END_YEAR = 2026
FIRST_LEAP_END_YEAR = FIRST_SEASON_END_YEAR + 1
MIN_TEAM_GAME_SHARE = 0.5
MIN_MINUTES_PER_GAME = 15.0
MIN_ENDING_POINTS_PER_36 = 10.0
TOP_N = 15
PAGE_SIZES = (15,)
RETRY_ATTEMPTS = 4
RETRY_BACKOFF = 4  # Each retry waits proportionally longer than API_DELAY.
SNAPSHOT_TZ = ZoneInfo("America/Chicago")

CHART_WIDTH = 1800
CHART_HEIGHT = 2220
ROW_DARK = "#242424"
VERTICAL_GUIDE = "#B8B3AC"

HEADSHOT_X = 80
HEADSHOT_HALF = 64
HEADSHOT_CROP_FRACTION = 0.68
LABEL_LEFT = 160
PLOT_LEFT = 690
PLOT_RIGHT = 1650
AXIS_MIN = 7.5
AXIS_MAX = 26.5
AXIS_TICKS = (10.0, 15.0, 20.0, 25.0)

HEADER_Y = 2202
HEADER_RULE_Y = 2178
FIRST_ROW_Y = 2105
ROW_HEIGHT = 136
NAME_RISE = 28
RATE_DROP = 6
MINUTES_DROP = 34
SEASON_GAP = 7
SEASON_RISE = 12
AXIS_Y = 122
AXIS_LABEL_Y = 90

ARROW_WIDTH = 3.4
TIP_LABEL_GAP = 13

# NBA.com's own name field, corrected only where it misreads on a graphic:
# the suffix Butler added after his Bulls years, and Nocioni's dropped accent.
DISPLAY_NAMES = {
    202710: "Jimmy Butler",
    2804: "Andrés Nocioni",
}

RAW_CACHE = _REPO / "cache" / "nba.com" / "scoring-leaps"
OUT = _REPO / "output" / "feed"
NBA_PLAYER_URL = (
    "https://www.nba.com/stats/players/traditional"
    "?PerMode=Totals&Season={season}&SeasonType=Regular%20Season"
    f"&TeamID={BULLS_TEAM_ID}"
)
NBA_TEAM_URL = (
    "https://www.nba.com/stats/teams/traditional"
    "?PerMode=Totals&Season={season}&SeasonType=Regular%20Season"
    f"&TeamID={BULLS_TEAM_ID}"
)

SEASON_COLUMNS = [
    "season_end_year",
    "season",
    "player_id",
    "player",
    "games",
    "minutes",
    "points",
    "team_games",
    "team_points",
    "player_source_url",
    "team_source_url",
]


@dataclass(frozen=True)
class ChartType:
    """Type sizing for the leap chart."""

    name: float = 20.0
    season: float = 11.0
    rate: float = 12.0
    minutes: float = 11.5
    gain: float = 17.0
    axis: float = 15.0


CHART_TYPE = ChartType()


def season_label(end_year: int) -> str:
    """Return an NBA end year as an NBA.com season string."""
    return f"{end_year - 1}-{str(end_year)[-2:]}"


def display_season_label(end_year: int) -> str:
    """Return the same season with an en dash for chart labels."""
    return season_label(end_year).replace("-", "–", 1)


def player_source_url(end_year: int) -> str:
    """Return the NBA.com player-totals source for one season."""
    return NBA_PLAYER_URL.format(season=season_label(end_year))


def team_source_url(end_year: int) -> str:
    """Return the NBA.com team-totals source for one season."""
    return NBA_TEAM_URL.format(season=season_label(end_year))


def _required_columns(frame: pd.DataFrame, columns: set[str], source: str) -> None:
    missing = columns - set(frame.columns)
    if missing:
        raise ValueError(f"NBA.com {source} response is missing {sorted(missing)}.")


def _fetch_frame(endpoint, **kwargs) -> pd.DataFrame:
    """Call one NBA.com endpoint, pacing requests and retrying a timeout.

    Fetching 27 seasons back to back reliably trips stats.nba.com's rate limit,
    which surfaces as a read timeout rather than an HTTP error.
    """
    last_error: Exception | None = None
    for attempt in range(RETRY_ATTEMPTS):
        time.sleep(API_DELAY * (1 + attempt * RETRY_BACKOFF))
        try:
            return endpoint(timeout=60, headers=_NBA_HEADERS, **kwargs).get_data_frames()[0]
        except (requests.Timeout, requests.ConnectionError) as error:
            last_error = error
            print(f"  NBA.com timed out; retry {attempt + 1} of {RETRY_ATTEMPTS - 1}")
    raise RuntimeError(f"NBA.com did not respond after {RETRY_ATTEMPTS} attempts.") from last_error


def fetch_bulls_season(end_year: int, *, refresh: bool = False) -> pd.DataFrame:
    """Load a Chicago-only NBA.com season from cache or the live endpoint.

    Player totals are reconciled against the team's own totals so a silently
    incomplete or mis-scoped response fails here rather than on the chart.
    """
    cache_path = RAW_CACHE / f"CHI-{end_year}.csv"
    if cache_path.exists() and not refresh:
        return pd.read_csv(cache_path)

    season = season_label(end_year)
    players = _fetch_frame(
        leaguedashplayerstats.LeagueDashPlayerStats,
        season=season,
        season_type_all_star="Regular Season",
        per_mode_detailed="Totals",
        team_id_nullable=BULLS_TEAM_ID,
    )
    teams = _fetch_frame(
        leaguedashteamstats.LeagueDashTeamStats,
        season=season,
        season_type_all_star="Regular Season",
        per_mode_detailed="Totals",
        team_id_nullable=BULLS_TEAM_ID,
    )
    _required_columns(
        players, {"PLAYER_ID", "PLAYER_NAME", "GP", "MIN", "PTS"}, "player totals"
    )
    _required_columns(teams, {"TEAM_ID", "GP", "PTS"}, "team totals")

    bulls = teams.loc[teams["TEAM_ID"] == BULLS_TEAM_ID]
    if len(bulls) != 1:
        raise ValueError(f"NBA.com did not return exactly one Bulls row for {season}.")
    if players["PLAYER_ID"].duplicated().any():
        raise ValueError(f"NBA.com returned duplicate Bulls players for {season}.")
    team = bulls.iloc[0]
    team_points = int(team["PTS"])
    player_points = int(pd.to_numeric(players["PTS"], errors="raise").sum())
    if player_points != team_points:
        raise ValueError(
            f"NBA.com Bulls player points ({player_points}) do not reconcile to "
            f"team points ({team_points}) for {season}."
        )

    frame = players[["PLAYER_ID", "PLAYER_NAME", "GP", "MIN", "PTS"]].rename(
        columns={
            "PLAYER_ID": "player_id",
            "PLAYER_NAME": "player",
            "GP": "games",
            "MIN": "minutes",
            "PTS": "points",
        }
    )
    frame["season_end_year"] = end_year
    frame["season"] = display_season_label(end_year)
    frame["team_games"] = int(team["GP"])
    frame["team_points"] = team_points
    frame["player_source_url"] = player_source_url(end_year)
    frame["team_source_url"] = team_source_url(end_year)
    frame = frame[SEASON_COLUMNS]
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(cache_path, index=False)
    return frame


def fetch_bulls_history(*, refresh: bool = False) -> pd.DataFrame:
    """Load every Bulls regular season from 1999-00 onward."""
    frames: list[pd.DataFrame] = []
    for end_year in range(FIRST_SEASON_END_YEAR, LAST_SEASON_END_YEAR + 1):
        print(f"Loading {display_season_label(end_year)}")
        frames.append(fetch_bulls_season(end_year, refresh=refresh))
    return pd.concat(frames, ignore_index=True)


def build_season_table(rows: pd.DataFrame) -> pd.DataFrame:
    """Add per-minute rates and the full-time-Bull qualification to each season."""
    missing = set(SEASON_COLUMNS) - set(rows.columns)
    if missing:
        raise ValueError(f"Bulls season rows are missing {sorted(missing)}.")

    table = rows.copy()
    for column in ("season_end_year", "player_id", "games", "points", "team_games", "team_points"):
        table[column] = pd.to_numeric(table[column], errors="raise").astype(int)
    table["minutes"] = pd.to_numeric(table["minutes"], errors="raise").astype(float)
    if (table["games"] <= 0).any():
        raise ValueError("A Bulls player-season reports no games played.")

    table["minutes_per_game"] = table["minutes"] / table["games"]
    table["points_per_game"] = table["points"] / table["games"]
    # A scoreless player with zero minutes would divide by zero; NBA.com has no
    # such row, but the guard keeps the rate honest rather than infinite.
    table["points_per_36"] = table["points"] / table["minutes"].where(table["minutes"] > 0) * 36
    table["qualified"] = (table["games"] >= table["team_games"] * MIN_TEAM_GAME_SHARE) & (
        table["minutes_per_game"] >= MIN_MINUTES_PER_GAME
    )
    return table.sort_values(
        ["season_end_year", "player_id"], kind="stable"
    ).reset_index(drop=True)


def build_leap_table(season_table: pd.DataFrame) -> pd.DataFrame:
    """Pair each qualifying season with the player's qualifying season before it."""
    qualified = season_table.loc[season_table["qualified"]].copy()
    previous = qualified.copy()
    previous["join_year"] = previous["season_end_year"] + 1

    pairs = previous.merge(
        qualified,
        left_on=["player_id", "join_year"],
        right_on=["player_id", "season_end_year"],
        suffixes=("_prev", "_cur"),
        validate="one_to_one",
    )
    if pairs.empty:
        raise ValueError("No consecutive qualifying Bulls seasons were found.")

    pairs["gain_per_36"] = pairs["points_per_36_cur"] - pairs["points_per_36_prev"]
    pairs["percentage_increase"] = (
        pairs["gain_per_36"] / pairs["points_per_36_prev"].where(
            pairs["points_per_36_prev"] > 0
        ) * 100
    )
    pairs["gain_per_game"] = pairs["points_per_game_cur"] - pairs["points_per_game_prev"]
    pairs["gain_minutes_per_game"] = (
        pairs["minutes_per_game_cur"] - pairs["minutes_per_game_prev"]
    )
    pairs = pairs.loc[
        pairs["points_per_36_cur"] >= MIN_ENDING_POINTS_PER_36
    ].copy()
    if pairs.empty:
        raise ValueError("No qualifying leap reaches the ending scoring floor.")

    # Deterministic order: the largest leap first, then the higher finishing
    # rate, then the season and name so a tie can never reshuffle between runs.
    ranked = pairs.sort_values(
        ["gain_per_36", "points_per_36_cur", "season_end_year_cur", "player_prev"],
        ascending=[False, False, True, True],
        kind="stable",
    ).reset_index(drop=True)
    ranked["rank"] = ranked.index + 1
    return ranked


def top_leaps(leap_table: pd.DataFrame, count: int = TOP_N) -> pd.DataFrame:
    """Return the highest-ranked leaps in display order."""
    if len(leap_table) < count:
        raise ValueError(
            f"Only {len(leap_table)} qualifying leaps exist; {count} were requested."
        )
    return leap_table.head(count).reset_index(drop=True)


def chart_pages(leaders: pd.DataFrame) -> list[pd.DataFrame]:
    """Split the top 15 into two readable chart pages of eight and seven rows."""
    if len(leaders) != sum(PAGE_SIZES):
        raise ValueError(
            f"The chart needs exactly {sum(PAGE_SIZES)} leaders; received {len(leaders)}."
        )
    pages: list[pd.DataFrame] = []
    start = 0
    for size in PAGE_SIZES:
        pages.append(leaders.iloc[start:start + size].reset_index(drop=True))
        start += size
    return pages


def minutes_correlations(leap_table: pd.DataFrame) -> dict[str, float]:
    """Return how strongly each metric's gain tracks the player's minutes gain."""
    return {
        "per_36": float(leap_table["gain_per_36"].corr(leap_table["gain_minutes_per_game"])),
        "per_game": float(
            leap_table["gain_per_game"].corr(leap_table["gain_minutes_per_game"])
        ),
    }


def validate_tables(season_table: pd.DataFrame, leap_table: pd.DataFrame) -> dict[str, object]:
    """Validate coverage, reconciliation, the gate, and the ranked pairs."""
    expected_years = set(range(FIRST_SEASON_END_YEAR, LAST_SEASON_END_YEAR + 1))
    present_years = set(season_table["season_end_year"].astype(int))
    if present_years != expected_years:
        raise ValueError("Season coverage does not include every Bulls season since 1999-00.")
    if season_table.duplicated(["season_end_year", "player_id"]).any():
        raise ValueError("A Bulls player appears more than once in a season.")
    if (season_table["games"] > season_table["team_games"]).any():
        raise ValueError("A player has more Bulls games than the team played.")

    season_points = season_table.groupby("season_end_year", sort=False)["points"].sum()
    team_points = season_table.groupby("season_end_year", sort=False)["team_points"].first()
    if not season_points.eq(team_points).all():
        raise ValueError("Player scoring does not reconcile to Bulls team scoring.")

    expected_gate = (
        season_table["games"] >= season_table["team_games"] * MIN_TEAM_GAME_SHARE
    ) & (
        season_table["minutes_per_game"] >= MIN_MINUTES_PER_GAME
    )
    if not season_table["qualified"].eq(expected_gate).all():
        raise ValueError("The full-time-Bull qualification is inconsistent.")

    if (leap_table["season_end_year_cur"] != leap_table["season_end_year_prev"] + 1).any():
        raise ValueError("A leap pairs two seasons that are not consecutive.")
    if (leap_table["season_end_year_cur"] < FIRST_LEAP_END_YEAR).any():
        raise ValueError("A leap starts before the first season the window can support.")
    if leap_table.duplicated(["player_id", "season_end_year_cur"]).any():
        raise ValueError("A player-season appears in more than one leap.")
    if not leap_table["gain_per_36"].is_monotonic_decreasing:
        raise ValueError("Leaps are not ordered by the ranked metric.")

    for side in ("prev", "cur"):
        if (
            leap_table[f"games_{side}"]
            < leap_table[f"team_games_{side}"] * MIN_TEAM_GAME_SHARE
        ).any():
            raise ValueError("A leap includes a season below the games threshold.")
        if (leap_table[f"minutes_per_game_{side}"] < MIN_MINUTES_PER_GAME).any():
            raise ValueError("A leap includes a season below the minutes threshold.")
    if (leap_table["points_per_36_cur"] < MIN_ENDING_POINTS_PER_36).any():
        raise ValueError("A leap ends below the scoring-rate threshold.")
    if leap_table["percentage_increase"].isna().any():
        raise ValueError("A leap has no defined percentage increase.")

    correlations = minutes_correlations(leap_table)
    if any(pd.isna(value) for value in correlations.values()):
        raise ValueError(
            "Minutes gains do not vary across the leaps, so the ranked metric's "
            "control for playing time cannot be checked."
        )
    if not correlations["per_36"] < correlations["per_game"]:
        raise ValueError(
            "Points per 36 no longer tracks minutes less closely than points per "
            "game; the ranked metric has stopped controlling for role."
        )

    leaders = top_leaps(leap_table)
    return {
        "season_count": len(present_years),
        "player_season_count": len(season_table),
        "qualified_season_count": int(season_table["qualified"].sum()),
        "leap_count": len(leap_table),
        "leap_player_count": int(leap_table["player_id"].nunique()),
        "first_leap_season": display_season_label(FIRST_LEAP_END_YEAR),
        "last_leap_season": display_season_label(LAST_SEASON_END_YEAR),
        "correlation_per_36": correlations["per_36"],
        "correlation_per_game": correlations["per_game"],
        # Display names, so the Canva page can never disagree with the chart.
        "leader": display_name(leaders.iloc[0]),
        "leader_season": leaders.iloc[0]["season_cur"],
        "leader_gain": float(leaders.iloc[0]["gain_per_36"]),
        "leader_names": [display_name(leap) for _, leap in leaders.iterrows()],
    }


def write_working_tables(
    season_table: pd.DataFrame, leap_table: pd.DataFrame, date: str
) -> tuple[Path, Path]:
    """Write every player-season and every ranked leap so exclusions stay auditable."""
    OUT.mkdir(parents=True, exist_ok=True)
    season_path = OUT / f"{date}-bulls-scoring-leaps-seasons.csv"
    leap_path = OUT / f"{date}-bulls-scoring-leaps-pairs.csv"
    season_table.to_csv(season_path, index=False)
    leap_table.to_csv(leap_path, index=False)
    return season_path, leap_path


def display_name(leap: pd.Series) -> str:
    """Return the player name as it should read on the graphic."""
    return DISPLAY_NAMES.get(int(leap["player_id"]), str(leap["player_cur"]))


def season_marker(previous: str, current: str) -> str:
    """Return the complete compact span: 2013–14 and 2014–15 becomes 13–14 to 14–15."""
    return f"{str(previous)[2:]} to {str(current)[2:]}"


def gain_label(leap: pd.Series) -> str:
    """Return the signed per-36 gain printed at the arrow tip."""
    return (
        f"+{leap['gain_per_36']:.1f} "
        f"(+{leap['percentage_increase']:.1f}%)"
    )


def rate_label(leap: pd.Series) -> str:
    """Return the exact per-36 transition printed under the player name."""
    return (
        f"{leap['points_per_36_prev']:.1f} to "
        f"{leap['points_per_36_cur']:.1f} PTS/36"
    )


def minutes_label(leap: pd.Series) -> str:
    """Return the exact minutes-per-game transition for the third text line."""
    return (
        f"{leap['minutes_per_game_prev']:.1f} to "
        f"{leap['minutes_per_game_cur']:.1f} MPG"
    )


def top_anchored_headshot_label(ax, image_path, x, y, half_size, *, zorder=5):
    """Place a full-color, top-anchored square crop of one player's portrait.

    Anchoring the crop to the top of the frame rather than its centre shows more
    face and less jersey, which matters here because the NBA CDN serves a
    player's *current* portrait: this chart spans 2004 to 2024, so several
    players arrive in the uniform of a team they joined years later.

    Portraits keep NBA's transparent background and are not placed on a tile, so
    they sit directly on the Canva page.

    A missing or unreadable file becomes a neutral placeholder square, so the
    builder never breaks on one absent portrait.
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
    side = max(1, round(min(height, width) * HEADSHOT_CROP_FRACTION))
    left = max(0, (width - side) // 2)
    square = image[:side, left:left + side]
    return ax.imshow(
        square,
        extent=[x - half_size, x + half_size, y - half_size, y + half_size],
        interpolation="bilinear",
        zorder=zorder,
    )


def _x_position(value: float) -> float:
    """Map a points-per-36 value onto the chart's plot area."""
    span = AXIS_MAX - AXIS_MIN
    return PLOT_LEFT + (float(value) - AXIS_MIN) / span * (PLOT_RIGHT - PLOT_LEFT)


def render_chart(
    leaders: pd.DataFrame, date: str, *, page_number: int = 1, final: bool = False
) -> Path:
    """Render the transparent top-15 scoring-leaps chart for Canva."""
    if leaders.empty:
        raise ValueError("Cannot render an empty leap chart.")
    if len(leaders) > max(PAGE_SIZES):
        raise ValueError("The scoring-leaps chart cannot exceed fifteen rows.")
    if page_number not in range(1, len(PAGE_SIZES) + 1):
        raise ValueError("The scoring-leaps chart has only one slide.")
    leaders = leaders.reset_index(drop=True)
    lowest_row_y = FIRST_ROW_Y - (len(leaders) - 1) * ROW_HEIGHT
    if lowest_row_y - ROW_HEIGHT / 2 < AXIS_Y:
        raise ValueError("The leap chart does not fit the chart asset height.")
    if float(leaders["points_per_36_prev"].min()) < AXIS_MIN:
        raise ValueError("A leap starts below the chart's axis minimum.")
    if float(leaders["points_per_36_cur"].max()) > AXIS_MAX:
        raise ValueError("A leap ends above the chart's axis maximum.")

    theme = DEFAULT_THEME
    dpi = export_dpi(final)
    # Keep the physical layout fixed at the draft scale. Raising save DPI then
    # doubles the output pixels without doubling type relative to the chart.
    fig = plt.figure(
        figsize=(CHART_WIDTH / DRAFT_DPI, CHART_HEIGHT / DRAFT_DPI),
        facecolor="none",
    )
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, CHART_WIDTH)
    ax.set_ylim(0, CHART_HEIGHT)
    ax.axis("off")

    for tick in AXIS_TICKS:
        x = _x_position(tick)
        ax.plot(
            [x, x],
            [AXIS_Y, FIRST_ROW_Y + ROW_HEIGHT / 2],
            color=VERTICAL_GUIDE,
            linewidth=1.2,
            zorder=1,
        )
        ax.text(
            x,
            AXIS_LABEL_Y,
            f"{tick:.0f}",
            ha="center",
            va="center",
            fontsize=CHART_TYPE.axis,
            color=theme.muted,
            fontproperties=helvetica(),
        )
    for index, leap in leaders.iterrows():
        y = FIRST_ROW_Y - index * ROW_HEIGHT
        start_x = _x_position(leap["points_per_36_prev"])
        end_x = _x_position(leap["points_per_36_cur"])

        # A bare square crop, not the red-ringed circle: every row on a ranked
        # list is the same kind of thing, so a ring would read as an emphasis
        # this layer does not intend (DESIGN.md §5).
        top_anchored_headshot_label(
            ax,
            HEADSHOT_CACHE / f"{int(leap['player_id'])}.png",
            HEADSHOT_X,
            y,
            HEADSHOT_HALF,
            zorder=5,
        )
        name_artist = ax.text(
            LABEL_LEFT,
            y + NAME_RISE,
            display_name(leap),
            ha="left",
            va="center",
            fontsize=CHART_TYPE.name,
            color=ROW_DARK,
            fontproperties=helvetica("bold"),
            zorder=4,
        )
        season_artist = ax.text(
            LABEL_LEFT + rendered_width(ax, name_artist) + SEASON_GAP,
            y + NAME_RISE + SEASON_RISE,
            season_marker(leap["season_prev"], leap["season_cur"]),
            ha="left",
            va="center",
            fontsize=CHART_TYPE.season,
            color=theme.muted,
            fontproperties=helvetica("oblique"),
            zorder=4,
        )
        # A longer label than today's field would push into the plot; fail
        # rather than draw text over the arrows.
        rate_artist = ax.text(
            LABEL_LEFT,
            y - RATE_DROP,
            rate_label(leap),
            ha="left",
            va="center",
            fontsize=CHART_TYPE.rate,
            color=theme.muted,
            fontproperties=helvetica("bold"),
            zorder=4,
        )
        minutes_artist = ax.text(
            LABEL_LEFT,
            y - MINUTES_DROP,
            minutes_label(leap),
            ha="left",
            va="center",
            fontsize=CHART_TYPE.minutes,
            color=theme.muted,
            fontproperties=helvetica(),
            zorder=4,
        )
        label_right = max(
            name_artist.get_position()[0] + rendered_width(ax, name_artist),
            season_artist.get_position()[0] + rendered_width(ax, season_artist),
            rate_artist.get_position()[0] + rendered_width(ax, rate_artist),
            minutes_artist.get_position()[0] + rendered_width(ax, minutes_artist),
        )
        if label_right > PLOT_LEFT:
            raise ValueError(
                f"The label for {display_name(leap)} runs into the plot area."
            )
        # A dotted guide carries the eye from the name to a short arrow, the
        # same job the reference chart's row guides do.
        ax.plot(
            [PLOT_LEFT, start_x],
            [y, y],
            color=ROW_DARK,
            linewidth=1.0,
            linestyle=(0, (1, 4)),
            zorder=2,
        )
        ax.add_patch(
            FancyArrowPatch(
                (start_x, y),
                (end_x, y),
                arrowstyle="-|>",
                mutation_scale=17,
                linewidth=ARROW_WIDTH,
                color=theme.accent,
                shrinkA=0,
                shrinkB=0,
                joinstyle="miter",
                zorder=3,
            )
        )
        ax.text(
            end_x + TIP_LABEL_GAP,
            y,
            gain_label(leap),
            ha="left",
            va="center",
            fontsize=CHART_TYPE.gain,
            color=theme.accent,
            fontproperties=helvetica("bold"),
            zorder=4,
        )

    OUT.mkdir(parents=True, exist_ok=True)
    suffix = "final" if final else "draft"
    path = OUT / f"{date}-bulls-scoring-leaps-slide{page_number}-{suffix}.png"
    fig.savefig(path, dpi=dpi, transparent=True, pad_inches=0)
    plt.close(fig)
    return path


def canva_copy_block(report: dict[str, object]) -> str:
    """Return the exact data-bound framing to paste around the chart asset."""
    return "\n".join(
        [
            "CANVA COPY",
            "TITLE: THE BIGGEST LEAPS",
            "SUBTITLE: Largest year-over-year scoring jumps by a Bull since 2000",
            "FOOTER: Data via nba.com | "
            f"{report['first_leap_season']} to {report['last_leap_season']} regular seasons | "
            f"Min. half of team games and {MIN_MINUTES_PER_GAME:.0f} min/game in both seasons | "
            f"Ending season: {MIN_ENDING_POINTS_PER_36:.0f}+ PTS/36",
            "NOTE: Chicago-only stints, consecutive seasons. Ranked by points per 36 "
            "minutes, which holds playing time equal.",
            f"AUDIT: {report['leap_count']} qualifying back-to-back seasons across "
            f"{report['leap_player_count']} players; "
            f"{report['leader']} {report['leader_season']} leads at "
            f"+{report['leader_gain']:.1f} per 36.",
        ]
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build the Bulls year-over-year scoring leaps chart asset."
    )
    parser.add_argument(
        "--refresh", action="store_true", help="Refetch every cached NBA.com season response."
    )
    parser.add_argument(
        "--final", action="store_true", help="Export at final resolution after the draft is approved."
    )
    args = parser.parse_args()

    snapshot = datetime.now(SNAPSHOT_TZ)
    season_table = build_season_table(fetch_bulls_history(refresh=args.refresh))
    leap_table = build_leap_table(season_table)
    report = validate_tables(season_table, leap_table)
    date = snapshot.date().isoformat()
    season_path, leap_path = write_working_tables(season_table, leap_table, date)
    leaders = top_leaps(leap_table)
    ensure_headshots(leaders["player_id"].tolist())
    pages = chart_pages(leaders)
    chart_paths = [
        render_chart(page, date, page_number=index, final=args.final)
        for index, page in enumerate(pages, start=1)
    ]

    print(f"Seasons audit: {season_path}")
    print(f"Leaps audit:   {leap_path}")
    for index, chart_path in enumerate(chart_paths, start=1):
        print(f"Chart {index}:       {chart_path}")
    print()
    print(
        f"Minutes confound - gain vs. minutes gained: "
        f"per 36 {report['correlation_per_36']:+.2f}, "
        f"per game {report['correlation_per_game']:+.2f}"
    )
    print()
    for _, leap in leaders.iterrows():
        print(
            f"{int(leap['rank']):2d}. {display_name(leap):20s} {leap['season_cur']}  "
            f"{leap['points_per_36_prev']:5.1f} -> {leap['points_per_36_cur']:5.1f} per 36 "
            f"({leap['gain_per_36']:+.1f})   {leap['points_per_game_prev']:4.1f} -> "
            f"{leap['points_per_game_cur']:4.1f} ppg"
        )
    print()
    print(canva_copy_block(report))


if __name__ == "__main__":
    main()
