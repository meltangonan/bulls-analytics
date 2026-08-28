"""Build the Bulls' highest-scoring season at every age since 2000 for Canva.

NBA.com provides every player-season from 2000-01 onward from one source.  The
post uses its season-age field exactly as listed, regular-season Chicago-only
stints, and a minimum of half the Bulls' games in that season.  The renderer
produces a transparent chart asset; Canva owns the title and page framing.
"""

from __future__ import annotations

import argparse
import io
import math
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

_REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO))

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import requests
from PIL import Image
from matplotlib.colors import to_rgb
from matplotlib.patches import FancyBboxPatch, Rectangle
from nba_api.stats.endpoints import leaguedashplayerstats, leaguedashteamstats

from bulls.config import BULLS_TEAM_ID
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


FIRST_SEASON_END_YEAR = 2001
LAST_SEASON_END_YEAR = 2026
MIN_TEAM_GAMES_SHARE = 0.50
CHART_WIDTH = 1080
CHART_HEIGHT = 1110
SNAPSHOT_TZ = ZoneInfo("America/Chicago")

ROW_RULE_LEFT = 100
AGE_X = 155
HEADSHOT_X = 245
NAME_X = 300
# Compact columns follow the Basketball University reference rather than
# stretching two short values across the full chart width.
PPG_LEFT = 690
PPG_RIGHT = 810
GP_LEFT = PPG_RIGHT
GP_RIGHT = 930
PPG_SCALE_RED = "red"
PPG_SCALE_RED_YELLOW_GREEN = "red-yellow-green"
METRIC_FILL_ROUNDED_BAND = "rounded-band"
METRIC_FILL_SQUARE_CELLS = "square-cells"
HEAT_RED = "#D64545"
HEAT_YELLOW = "#F2D46B"
HEAT_GREEN = "#3FAE63"
# The header ruler is drawn at 2pt; keeping the conditional fill this far
# below its centre stops the top cell bleeding into the black line.
HEADER_RULE_CLEARANCE = 3.0
MIN_USABLE_HEADSHOT_BYTES = 50_000
FACE_CROP_HEIGHT_FRACTION = 0.72

# The current NBA CDN returns a generic silhouette for these retired players.
# ESPN retains actual studio portraits at its stable player-image endpoint.
HISTORICAL_HEADSHOT_URLS = {
    2430: "https://a.espncdn.com/i/headshots/nba/players/full/1703.png",  # Carlos Boozer
    703: "https://a.espncdn.com/i/headshots/nba/players/full/846.png",  # Kurt Thomas
    200748: "https://a.espncdn.com/i/headshots/nba/players/full/3032.png",  # Tyrus Thomas
}


@dataclass(frozen=True)
class TableLayout:
    """Row and type sizing for one age-table page."""

    header_y: float
    header_rule_y: float
    first_row_y: float
    row_height: float
    headshot_half_size: float
    headshot_rise: float
    header_font_size: float
    name_font_size: float
    age_font_size: float
    ppg_font_size: float
    season_font_size: float
    season_rise: float


@dataclass(frozen=True)
class TrailingColumn:
    """One narrow numeric column to the right of the heat cell.

    The ladder family shows games played here by default.  A composite metric
    such as stocks replaces it with its own components, so a reader can see
    that a 2.4 came from steals rather than blocks (`POSTING_WORKFLOW.md`
    fairness guardrails: expose important metric components).
    """

    header: str
    column: str
    decimals: int = 0


GAMES_COLUMN = (TrailingColumn("GP", "games"),)


ONE_SLIDE_LAYOUT = TableLayout(
    header_y=1043,
    header_rule_y=1018,
    first_row_y=992.75,
    row_height=50.5,
    headshot_half_size=30,
    headshot_rise=4,
    header_font_size=15,
    name_font_size=17.5,
    age_font_size=16,
    ppg_font_size=17.5,
    season_font_size=9.5,
    season_rise=9,
)
TWO_SLIDE_LAYOUT = TableLayout(
    header_y=1043,
    header_rule_y=1018,
    first_row_y=970,
    row_height=96,
    headshot_half_size=54,
    headshot_rise=7,
    header_font_size=16.5,
    name_font_size=20,
    age_font_size=19,
    ppg_font_size=20,
    season_font_size=10.5,
    season_rise=11,
)

RAW_CACHE = _REPO / "cache" / "nba.com" / "scoring-age-ladder"
OUT = _REPO / "output" / "feed"
NBA_PLAYER_SCORING_URL = (
    "https://www.nba.com/stats/players/traditional"
    "?PerMode=Totals&Season={season}&SeasonType=Regular%20Season"
    f"&TeamID={BULLS_TEAM_ID}"
)
NBA_TEAM_SCORING_URL = (
    "https://www.nba.com/stats/teams/traditional"
    "?PerMode=Totals&Season={season}&SeasonType=Regular%20Season"
    f"&TeamID={BULLS_TEAM_ID}"
)


def season_label(end_year: int) -> str:
    """Return an NBA end year as an NBA.com season string."""
    return f"{end_year - 1}-{str(end_year)[-2:]}"


def display_season_label(end_year: int) -> str:
    """Return the same season with an en dash for chart labels."""
    return season_label(end_year).replace("-", "\u2013", 1)


def player_source_url(end_year: int) -> str:
    """Return the NBA.com player-totals source for one season."""
    return NBA_PLAYER_SCORING_URL.format(season=season_label(end_year))


def team_source_url(end_year: int) -> str:
    """Return the NBA.com team-totals source for one season."""
    return NBA_TEAM_SCORING_URL.format(season=season_label(end_year))


def _required_columns(frame: pd.DataFrame, columns: set[str], source: str) -> None:
    missing = columns - set(frame.columns)
    if missing:
        raise ValueError(f"NBA.com {source} response is missing {sorted(missing)}.")


def fetch_bulls_season(end_year: int, *, refresh: bool = False) -> pd.DataFrame:
    """Load a Chicago-only NBA.com season from cache or the live endpoint."""
    cache_path = RAW_CACHE / f"CHI-{end_year}.csv"
    if cache_path.exists() and not refresh:
        return pd.read_csv(cache_path)

    season = season_label(end_year)
    players = leaguedashplayerstats.LeagueDashPlayerStats(
        season=season,
        season_type_all_star="Regular Season",
        per_mode_detailed="Totals",
        team_id_nullable=BULLS_TEAM_ID,
        timeout=60,
        headers=_NBA_HEADERS,
    ).get_data_frames()[0]
    teams = leaguedashteamstats.LeagueDashTeamStats(
        season=season,
        season_type_all_star="Regular Season",
        per_mode_detailed="Totals",
        team_id_nullable=BULLS_TEAM_ID,
        timeout=60,
        headers=_NBA_HEADERS,
    ).get_data_frames()[0]
    _required_columns(players, {"PLAYER_ID", "PLAYER_NAME", "AGE", "GP", "PTS"}, "player totals")
    _required_columns(teams, {"TEAM_ID", "GP", "PTS"}, "team totals")

    bulls = teams.loc[teams["TEAM_ID"] == BULLS_TEAM_ID]
    if len(bulls) != 1:
        raise ValueError(f"NBA.com did not return exactly one Bulls row for {season}.")
    if players["PLAYER_ID"].duplicated().any():
        raise ValueError(f"NBA.com returned duplicate Bulls players for {season}.")
    team = bulls.iloc[0]
    team_games = int(team["GP"])
    team_points = int(team["PTS"])
    player_points = int(pd.to_numeric(players["PTS"], errors="raise").sum())
    if player_points != team_points:
        raise ValueError(
            f"NBA.com Bulls player points ({player_points}) do not reconcile to "
            f"team points ({team_points}) for {season}."
        )

    frame = players[["PLAYER_ID", "PLAYER_NAME", "AGE", "GP", "PTS"]].rename(
        columns={
            "PLAYER_ID": "player_id",
            "PLAYER_NAME": "player",
            "AGE": "age",
            "GP": "games",
            "PTS": "points",
        }
    )
    frame["season_end_year"] = end_year
    frame["season"] = display_season_label(end_year)
    frame["team_games"] = team_games
    frame["team_points"] = team_points
    frame["points_per_game"] = frame["points"] / frame["games"]
    frame["player_source_url"] = player_source_url(end_year)
    frame["team_source_url"] = team_source_url(end_year)
    frame = frame[
        [
            "season_end_year",
            "season",
            "player_id",
            "player",
            "age",
            "games",
            "points",
            "points_per_game",
            "team_games",
            "team_points",
            "player_source_url",
            "team_source_url",
        ]
    ]
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(cache_path, index=False)
    return frame


def fetch_bulls_history(*, refresh: bool = False) -> pd.DataFrame:
    """Load every Bulls regular season since 2000-01."""
    frames: list[pd.DataFrame] = []
    for end_year in range(FIRST_SEASON_END_YEAR, LAST_SEASON_END_YEAR + 1):
        print(f"Loading {display_season_label(end_year)}")
        frames.append(fetch_bulls_season(end_year, refresh=refresh))
    return pd.concat(frames, ignore_index=True)


def build_working_table(rows: pd.DataFrame) -> pd.DataFrame:
    """Apply the minimum-games rule and select one PPG winner at each age."""
    required = {
        "season_end_year",
        "season",
        "player_id",
        "player",
        "age",
        "games",
        "points",
        "points_per_game",
        "team_games",
        "team_points",
        "player_source_url",
        "team_source_url",
    }
    missing = required - set(rows.columns)
    if missing:
        raise ValueError(f"Historical scoring rows are missing {sorted(missing)}.")

    table = rows.copy()
    for column in ("season_end_year", "player_id", "age", "games", "points", "team_games", "team_points"):
        table[column] = pd.to_numeric(table[column], errors="raise").astype(int)
    table["points_per_game"] = pd.to_numeric(table["points_per_game"], errors="raise").astype(float)
    table["minimum_games"] = (
        table["team_games"] * MIN_TEAM_GAMES_SHARE
    ).apply(math.ceil).astype(int)
    table["qualified"] = table["games"] >= table["minimum_games"]
    table["selected"] = False

    winners = (
        table.loc[table["qualified"]]
        .sort_values(
            ["age", "points_per_game", "points", "games", "player"],
            ascending=[True, False, False, False, True],
            kind="stable",
        )
        .drop_duplicates("age", keep="first")
    )
    winner_keys = pd.MultiIndex.from_frame(winners[["season_end_year", "player_id"]])
    table_keys = pd.MultiIndex.from_frame(table[["season_end_year", "player_id"]])
    table["selected"] = table_keys.isin(winner_keys)
    return table.sort_values(
        ["age", "season_end_year", "player", "player_id"], kind="stable"
    ).reset_index(drop=True)


def age_winners(table: pd.DataFrame) -> pd.DataFrame:
    """Return the selected Bulls season in chronological age order."""
    return table.loc[table["selected"]].sort_values("age", kind="stable").reset_index(drop=True)


def split_carousel_pages(winners: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Split the age ladder into two consecutive carousel pages."""
    players = winners.sort_values("age", kind="stable").reset_index(drop=True)
    midpoint = math.ceil(len(players) / 2)
    return (
        players.iloc[:midpoint].reset_index(drop=True),
        players.iloc[midpoint:].reset_index(drop=True),
    )


def validate_working_table(table: pd.DataFrame) -> dict[str, object]:
    """Validate NBA.com coverage, team reconciliation, and each age winner."""
    expected_years = set(range(FIRST_SEASON_END_YEAR, LAST_SEASON_END_YEAR + 1))
    present_years = set(table["season_end_year"].astype(int))
    if present_years != expected_years:
        raise ValueError("Historical source coverage does not include every season since 2000.")
    if table.duplicated(["season_end_year", "player_id"]).any():
        raise ValueError("A Bulls player appears more than once in a season.")
    if (table["games"] > table["team_games"]).any():
        raise ValueError("A player has more Bulls games than the team played.")
    if not table["qualified"].eq(table["games"] >= table["minimum_games"]).all():
        raise ValueError("Minimum-games qualification is inconsistent.")

    season_points = table.groupby("season_end_year", sort=False)["points"].sum()
    team_points = table.groupby("season_end_year", sort=False)["team_points"].first()
    if not season_points.eq(team_points).all():
        raise ValueError("Player scoring does not reconcile to Bulls team scoring.")

    winners = age_winners(table)
    if winners.empty:
        raise ValueError("No Bulls player-seasons qualified for the age ladder.")
    if winners["age"].duplicated().any():
        raise ValueError("The age ladder has more than one winner for an age.")
    expected_winners = (
        table.loc[table["qualified"]]
        .sort_values(
            ["age", "points_per_game", "points", "games", "player"],
            ascending=[True, False, False, False, True],
            kind="stable",
        )
        .drop_duplicates("age", keep="first")
    )
    actual_keys = set(zip(winners["season_end_year"], winners["player_id"]))
    expected_keys = set(zip(expected_winners["season_end_year"], expected_winners["player_id"]))
    if actual_keys != expected_keys:
        raise ValueError("The selected age ladder does not use the correct winners.")
    return {
        "season_count": len(present_years),
        "player_season_count": len(table),
        "qualified_count": int(table["qualified"].sum()),
        "age_count": len(winners),
        "youngest_age": int(winners["age"].min()),
        "oldest_age": int(winners["age"].max()),
        "winner_names": winners["player"].tolist(),
    }


def write_working_table(table: pd.DataFrame, date: str) -> Path:
    """Write every Bulls player-season so exclusions and runners-up stay auditable."""
    path = OUT / f"{date}-bulls-scoring-age-ladder-working.csv"
    path.parent.mkdir(parents=True, exist_ok=True)
    table.to_csv(path, index=False)
    return path


def season_marker(season: str) -> str:
    """Return the compact unstarred season label displayed beside a name."""
    return season[2:]


def historical_headshot_url(player_id: int) -> str | None:
    """Return a known usable portrait when NBA's retired-player CDN has none."""
    return HISTORICAL_HEADSHOT_URLS.get(int(player_id))


def ensure_historical_headshot_fallbacks(player_ids: list[int]) -> None:
    """Replace only known NBA-CDN silhouette files with their real portraits."""
    for player_id in {int(player_id) for player_id in player_ids}:
        url = historical_headshot_url(player_id)
        cache_path = HEADSHOT_CACHE / f"{player_id}.png"
        if url is None or (cache_path.exists() and cache_path.stat().st_size >= MIN_USABLE_HEADSHOT_BYTES):
            continue
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        if len(response.content) < MIN_USABLE_HEADSHOT_BYTES:
            raise ValueError(f"Historical headshot fallback for NBA player {player_id} is unexpectedly small.")
        image = Image.open(io.BytesIO(response.content)).convert("RGBA")
        image.save(cache_path, format="PNG")


def _mix(base: str, target: str, strength: float) -> tuple[float, float, float]:
    """Blend two colors using the exact clutch-table calculation."""
    amount = min(max(float(strength), 0.0), 1.0)
    base_rgb = np.array(to_rgb(base))
    target_rgb = np.array(to_rgb(target))
    return tuple(base_rgb * (1 - amount) + target_rgb * amount)


def ppg_fill(
    points_per_game: float,
    minimum: float,
    maximum: float,
    color_scale: str = PPG_SCALE_RED_YELLOW_GREEN,
    midpoint: float | None = None,
) -> tuple[float, float, float]:
    """Map PPG to either the clutch red scale or a comparison heat scale.

    ``midpoint`` pins the scale's yellow to a stated value rather than to the
    halfway point between the extremes. That is what lets yellow mean "league
    average" instead of "middle of whatever happens to be on this chart", while
    the two halves still stretch across the full observed spread.
    """
    value = float(points_per_game)
    if midpoint is None:
        span = maximum - minimum
        fraction = 1.0 if span <= 0 else (value - minimum) / span
    else:
        if not minimum < midpoint < maximum:
            raise ValueError("Heat-scale midpoint must sit between minimum and maximum.")
        if value <= midpoint:
            fraction = 0.5 * (value - minimum) / (midpoint - minimum)
        else:
            fraction = 0.5 + 0.5 * (value - midpoint) / (maximum - midpoint)
    fraction = min(max(fraction, 0.0), 1.0)
    if color_scale == PPG_SCALE_RED_YELLOW_GREEN:
        if fraction <= 0.5:
            return _mix(HEAT_RED, HEAT_YELLOW, fraction * 2)
        return _mix(HEAT_YELLOW, HEAT_GREEN, (fraction - 0.5) * 2)
    if color_scale != PPG_SCALE_RED:
        raise ValueError(f"Unknown PPG color scale: {color_scale}")
    return _mix("#F6DCE3", DEFAULT_THEME.accent, 0.35 + 0.65 * fraction)


def ppg_text_color(fill: tuple[float, float, float]) -> str:
    """Use the clutch points column's exact black-or-white contrast rule."""
    red, green, blue = fill
    luminance = 0.2126 * red + 0.7152 * green + 0.0722 * blue
    return "#FFFFFF" if luminance < 0.47 else DEFAULT_THEME.ink


def _ppg_cells(
    ax,
    players: pd.DataFrame,
    layout: TableLayout,
    minimum_ppg: float,
    maximum_ppg: float,
    color_scale: str = PPG_SCALE_RED_YELLOW_GREEN,
    metric_left: float = PPG_LEFT,
    metric_right: float = PPG_RIGHT,
    fill_style: str = METRIC_FILL_SQUARE_CELLS,
    top_limit: float | None = None,
    midpoint: float | None = None,
) -> None:
    """Draw a gapless conditional-format column with optional outer rounding."""
    if fill_style not in {METRIC_FILL_ROUNDED_BAND, METRIC_FILL_SQUARE_CELLS}:
        raise ValueError(f"Unknown metric fill style: {fill_style}")

    top = layout.first_row_y + layout.row_height / 2
    bottom = (
        layout.first_row_y
        - (len(players) - 1) * layout.row_height
        - layout.row_height / 2
    )
    clip_path = None
    if fill_style == METRIC_FILL_ROUNDED_BAND:
        clip_path = FancyBboxPatch(
            (metric_left, bottom),
            metric_right - metric_left,
            top - bottom,
            boxstyle="round,pad=0,rounding_size=13",
            facecolor="none",
            edgecolor="none",
            linewidth=0,
            transform=ax.transData,
        )
    elif top_limit is not None:
        # Square outer corners, but still a clip: it lets every cell overlap its
        # neighbour — which is what closes the hairline seams between rows —
        # without the first cell growing up into the header rule.
        clip_path = Rectangle(
            (metric_left, bottom),
            metric_right - metric_left,
            min(top, top_limit) - bottom,
            facecolor="none",
            edgecolor="none",
            linewidth=0,
            transform=ax.transData,
        )
    if clip_path is not None:
        ax.add_patch(clip_path)

    # A small overlap prevents raster resampling from exposing hairline gaps
    # between adjacent fills. It needs the clip to bound the band's outside
    # edges, so the unclipped legacy path keeps its exact, abutting cells.
    overlap = 0.75 if clip_path is not None else 0.0
    for index, value in enumerate(players["points_per_game"]):
        y = layout.first_row_y - index * layout.row_height
        cell = Rectangle(
            (metric_left, y - layout.row_height / 2 - overlap),
            metric_right - metric_left,
            layout.row_height + 2 * overlap,
            facecolor=ppg_fill(
                float(value), minimum_ppg, maximum_ppg, color_scale, midpoint
            ),
            edgecolor="none",
            linewidth=0,
            antialiased=clip_path is not None,
            zorder=2,
        )
        if clip_path is not None:
            cell.set_clip_path(clip_path)
        ax.add_patch(cell)


def header_rule_segments(rule_right: float = GP_RIGHT) -> tuple[tuple[float, float], ...]:
    """Draw the full-width ruler directly beneath the column headers."""
    return ((ROW_RULE_LEFT, rule_right),)


def row_rule_segments(
    row_rule_left: float = ROW_RULE_LEFT,
    metric_left: float = PPG_LEFT,
    games_left: float = GP_LEFT,
    games_right: float = GP_RIGHT,
    headshot_x: float = HEADSHOT_X,
    headshot_half_size: float = ONE_SLIDE_LAYOUT.headshot_half_size,
) -> tuple[tuple[float, float], ...]:
    """Run the ruler behind portraits; leave only the heat column uninterrupted."""
    # Faces draw later at zorder 4, above this zorder-3 rule. Keeping the ruler
    # continuous matches the assist-duo and Game Score tables: the line remains
    # legible as a table separator while the portrait naturally interrupts it.
    return ((row_rule_left, metric_left), (games_left, games_right))


def face_headshot_label(
    ax,
    image_path,
    x,
    y,
    half_size,
    *,
    zorder=4,
    crop_fraction=FACE_CROP_HEIGHT_FRACTION,
    clip_bottom=None,
):
    """Place the face-focused crop used by the account's recent tables.

    ``crop_fraction`` is the share of the source portrait's height kept from the
    top.  Lower values cut shoulders and neck and leave more face, which is what
    a larger portrait needs to stay a portrait rather than a torso.
    ``clip_bottom`` trims the drawn image at a row separator so a bigger
    portrait cannot bleed into the row beneath it (the rookie-table treatment).
    """
    try:
        image = plt.imread(image_path)
    except (FileNotFoundError, OSError, ValueError):
        return ax.add_patch(
            Rectangle(
                (x - half_size, y - half_size),
                2 * half_size,
                2 * half_size,
                facecolor="#DDD8D1",
                edgecolor="none",
                zorder=zorder,
            )
        )

    height, width = image.shape[:2]
    side = min(int(height * crop_fraction), width)
    left = max(0, (width - side) // 2)
    square = image[:side, left:left + side]
    artist = ax.imshow(
        square,
        extent=[x - half_size, x + half_size, y - half_size, y + half_size],
        interpolation="bilinear",
        zorder=zorder,
    )
    if clip_bottom is not None:
        artist.set_clip_path(
            Rectangle(
                (x - half_size, clip_bottom),
                2 * half_size,
                (y + half_size) - clip_bottom,
                transform=ax.transData,
            )
        )
    return artist


def name_block_width(ax, players, layout) -> float:
    """Width of the widest name plus its season marker, measured not guessed.

    Hardcoded column positions are what let a long name such as "Wendell Carter
    Jr." run its season marker underneath the metric column.  Measuring the
    real pool and starting the numbers after it removes the collision by
    construction rather than by nudging a constant.
    """
    season_font = helvetica()
    season_font.set_style("italic")
    widest = 0.0
    for _, player in players.iterrows():
        name = ax.text(
            0, 0, str(player["player"]),
            fontsize=layout.name_font_size, fontproperties=helvetica("bold"), alpha=0,
        )
        season = ax.text(
            0, 0, season_marker(str(player["season"])),
            fontsize=layout.season_font_size, fontproperties=season_font, alpha=0,
        )
        widest = max(widest, rendered_width(ax, name) + 6 + rendered_width(ax, season))
        name.remove()
        season.remove()
    return widest


def render_chart(
    winners: pd.DataFrame,
    date: str,
    *,
    slug: str = "one-slide",
    layout: TableLayout = ONE_SLIDE_LAYOUT,
    scale_min: float | None = None,
    scale_max: float | None = None,
    color_scale: str = PPG_SCALE_RED_YELLOW_GREEN,
    metric_column: str = "points_per_game",
    fill_column: str | None = None,
    fill_midpoint: float | None = None,
    metric_header: str = "PPG",
    metric_decimals: int = 1,
    output_stem: str = "bulls-scoring-age-ladder",
    show_age: bool = True,
    headshot_x: float = HEADSHOT_X,
    name_x: float = NAME_X,
    metric_left: float = PPG_LEFT,
    metric_right: float = PPG_RIGHT,
    games_left: float = GP_LEFT,
    games_right: float = GP_RIGHT,
    row_rule_left: float = ROW_RULE_LEFT,
    sort_by: list[str] | None = None,
    sort_ascending: bool | list[bool] = True,
    metric_fill_style: str = METRIC_FILL_SQUARE_CELLS,
    blank_headshot_ids: set[int] | None = None,
    trailing_columns: tuple[TrailingColumn, ...] = GAMES_COLUMN,
    chart_width: float = CHART_WIDTH,
    chart_height: float = CHART_HEIGHT,
    auto_name_column: bool = False,
    name_column_gap: float = 0.0,
    metric_width: float = PPG_RIGHT - PPG_LEFT,
    trailing_slot_width: float = GP_RIGHT - GP_LEFT,
    face_crop_fraction: float = FACE_CROP_HEIGHT_FRACTION,
    portrait_crop_overrides: dict[int, float] | None = None,
    portrait_rise_overrides: dict[int, float] | None = None,
    clip_portraits_to_row: bool = False,
    final: bool = False,
) -> Path:
    """Render one transparent player-metric table for Canva."""
    if winners.empty:
        raise ValueError("Cannot render an empty age ladder.")
    if metric_column not in winners.columns:
        raise ValueError(f"Age ladder rows are missing metric column {metric_column!r}.")
    # The printed number and the colour behind it need not be the same quantity:
    # a raw rate reads plainly, while its standing against a league baseline is
    # what makes the colour mean anything.
    fill_source = metric_column if fill_column is None else fill_column
    if fill_source not in winners.columns:
        raise ValueError(f"Age ladder rows are missing fill column {fill_source!r}.")
    if not trailing_columns:
        raise ValueError("A ladder table needs at least one trailing column.")
    missing_trailing = [
        entry.column for entry in trailing_columns if entry.column not in winners.columns
    ]
    if missing_trailing:
        raise ValueError(f"Age ladder rows are missing trailing columns {missing_trailing}.")
    sort_columns = ["age"] if sort_by is None else sort_by
    players = winners.sort_values(
        sort_columns,
        ascending=sort_ascending,
        kind="stable",
    ).reset_index(drop=True)
    if layout.first_row_y - (len(players) - 1) * layout.row_height - layout.row_height / 2 < 0:
        raise ValueError("Age ladder table does not fit the chart asset height.")
    # Geometry is fixed at the draft scale and only the export resolution
    # changes, so --final is the same layout at twice the pixels. Sizing the
    # figure by the export DPI instead kept the image 1080px wide and doubled
    # every point-sized font, which is a different chart, not a sharper one.
    fig = plt.figure(
        figsize=(chart_width / DRAFT_DPI, chart_height / DRAFT_DPI),
        facecolor="none",
    )
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, chart_width)
    ax.set_ylim(0, chart_height)
    ax.axis("off")

    theme = DEFAULT_THEME
    if auto_name_column:
        metric_left = name_x + name_block_width(ax, players, layout) + name_column_gap
        metric_right = metric_left + metric_width
        games_left = metric_right
        games_right = games_left + trailing_slot_width * len(trailing_columns)
        if games_right > chart_width:
            raise ValueError(
                f"Measured table is {games_right:.0f}px wide and overflows the "
                f"{chart_width:.0f}px chart asset."
            )
    if show_age:
        ax.text(
            AGE_X,
            layout.header_y,
            "AGE",
            ha="center",
            va="center",
            fontsize=layout.header_font_size,
            color=theme.ink,
            fontproperties=helvetica("bold"),
        )
    ax.text(
        name_x,
        layout.header_y,
        "PLAYER",
        ha="left",
        va="center",
        fontsize=layout.header_font_size,
        color=theme.ink,
        fontproperties=helvetica("bold"),
    )
    ax.text(
        (metric_left + metric_right) / 2,
        layout.header_y,
        metric_header,
        ha="center",
        va="center",
        fontsize=layout.header_font_size,
        color=theme.accent,
        fontproperties=helvetica("bold"),
    )
    slot_width = (games_right - games_left) / len(trailing_columns)
    trailing_centres = [
        games_left + (position + 0.5) * slot_width
        for position in range(len(trailing_columns))
    ]
    for entry, centre in zip(trailing_columns, trailing_centres):
        ax.text(
            centre,
            layout.header_y,
            entry.header,
            ha="center",
            va="center",
            fontsize=layout.header_font_size,
            color=theme.ink,
            fontproperties=helvetica("bold"),
        )
    for rule_left, rule_right in header_rule_segments(games_right):
        ax.plot(
            [rule_left, rule_right],
            [layout.header_rule_y, layout.header_rule_y],
            color=theme.ink,
            linewidth=2.0,
        )

    metric_players = players.rename(columns={fill_source: "points_per_game"})
    minimum_ppg = float(metric_players["points_per_game"].min()) if scale_min is None else float(scale_min)
    maximum_ppg = float(metric_players["points_per_game"].max()) if scale_max is None else float(scale_max)
    _ppg_cells(
        ax,
        metric_players,
        layout,
        minimum_ppg,
        maximum_ppg,
        color_scale,
        metric_left,
        metric_right,
        metric_fill_style,
        top_limit=layout.header_rule_y - HEADER_RULE_CLEARANCE,
        midpoint=fill_midpoint,
    )

    season_font = helvetica()
    season_font.set_style("italic")

    for index, player in players.iterrows():
        y = layout.first_row_y - index * layout.row_height
        if index:
            divider_y = y + layout.row_height / 2
            for rule_left, rule_right in row_rule_segments(
                row_rule_left,
                metric_left,
                games_left,
                games_right,
                headshot_x,
                layout.headshot_half_size,
            ):
                ax.plot(
                    [rule_left, rule_right],
                    [divider_y, divider_y],
                    color=theme.rule,
                    linewidth=1.0,
                    # Matplotlib projects a solid line half a linewidth past each
                    # end by default, which painted a pale notch into the
                    # conditional fill's corners at every row boundary.
                    solid_capstyle="butt",
                    zorder=3,
                )

        player_id = int(player["player_id"])
        headshot_path = (
            HEADSHOT_CACHE / "blank-headshot.png"
            if blank_headshot_ids and player_id in blank_headshot_ids
            else HEADSHOT_CACHE / f"{player_id}.png"
        )
        face_headshot_label(
            ax,
            headshot_path,
            headshot_x,
            y + (portrait_rise_overrides or {}).get(player_id, layout.headshot_rise),
            layout.headshot_half_size,
            zorder=4,
            crop_fraction=(portrait_crop_overrides or {}).get(player_id, face_crop_fraction),
            clip_bottom=(y - layout.row_height / 2) if clip_portraits_to_row else None,
        )
        if show_age:
            ax.text(
                AGE_X,
                y,
                str(int(player["age"])),
                ha="center",
                va="center",
                fontsize=layout.age_font_size,
                color=theme.accent,
                fontproperties=helvetica("bold"),
            )
        name = str(player["player"])
        name_artist = ax.text(
            name_x,
            y,
            name,
            ha="left",
            va="center",
            fontsize=layout.name_font_size,
            color=theme.ink,
            fontproperties=helvetica("bold"),
            zorder=4,
        )
        name_width = rendered_width(ax, name_artist)
        ax.text(
            name_x + name_width + 6,
            y + layout.season_rise,
            season_marker(str(player["season"])),
            ha="left",
            va="center",
            fontsize=layout.season_font_size,
            color=theme.muted,
            fontproperties=season_font,
            zorder=4,
        )

        metric_value = float(player[metric_column])
        fill = ppg_fill(
            float(player[fill_source]),
            minimum_ppg,
            maximum_ppg,
            color_scale,
            fill_midpoint,
        )
        ax.text(
            (metric_left + metric_right) / 2,
            y,
            f"{metric_value:.{metric_decimals}f}",
            ha="center",
            va="center",
            fontsize=layout.ppg_font_size,
            color=ppg_text_color(fill),
            fontproperties=helvetica("bold"),
            zorder=4,
        )
        for entry, centre in zip(trailing_columns, trailing_centres):
            raw = float(player[entry.column])
            label = f"{raw:.{entry.decimals}f}" if entry.decimals else str(int(round(raw)))
            ax.text(
                centre,
                y,
                label,
                ha="center",
                va="center",
                fontsize=layout.ppg_font_size,
                color=theme.ink,
                fontproperties=helvetica(),
                zorder=4,
            )

    OUT.mkdir(parents=True, exist_ok=True)
    suffix = "final" if final else "draft"
    path = OUT / f"{date}-{output_stem}-{slug}-{suffix}.png"
    fig.savefig(path, dpi=export_dpi(final), transparent=True, pad_inches=0)
    plt.close(fig)
    return path


def canva_copy_block(report: dict[str, object]) -> str:
    """Return the exact data-bound framing to paste around the chart asset."""
    return "\n".join(
        [
            "CANVA COPY",
            "TITLE: THE BULLS' SCORING AGE LADDER",
            "SUBTITLE: Highest PPG by a Bull at every age since 2000",
            "FOOTER: Data via nba.com | 2000\u201301 to 2025\u201326 regular seasons | "
            "Min. 50% of team games | Age as listed by NBA.com",
            "NOTE: Chicago-only player stints. One qualifying player-season per age.",
            f"AUDIT: {report['age_count']} ages, {report['youngest_age']}\u2013{report['oldest_age']}; "
            f"{report['qualified_count']} qualifying player-seasons across {report['season_count']} Bulls seasons.",
        ]
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the Bulls scoring age ladder chart asset.")
    parser.add_argument("--refresh", action="store_true", help="Refetch every cached NBA.com season response.")
    parser.add_argument("--final", action="store_true", help="Export at final resolution after the draft is approved.")
    args = parser.parse_args()
    snapshot = datetime.now(SNAPSHOT_TZ)
    table = build_working_table(fetch_bulls_history(refresh=args.refresh))
    report = validate_working_table(table)
    date = snapshot.date().isoformat()
    audit_path = write_working_table(table, date)
    winners = age_winners(table)
    ensure_headshots(winners["player_id"].tolist())
    ensure_historical_headshot_fallbacks(winners["player_id"].tolist())
    scale_min = float(winners["points_per_game"].min())
    scale_max = float(winners["points_per_game"].max())
    chart_paths = [
        render_chart(
            winners,
            date,
            slug="one-slide",
            layout=ONE_SLIDE_LAYOUT,
            scale_min=scale_min,
            scale_max=scale_max,
            final=args.final,
        ),
    ]
    print(f"Audit: {audit_path}")
    for chart_path in chart_paths:
        print(f"Chart: {chart_path}")
    print(canva_copy_block(report))


if __name__ == "__main__":
    main()
