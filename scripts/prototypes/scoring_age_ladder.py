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
MIN_USABLE_HEADSHOT_BYTES = 50_000
FACE_CROP_HEIGHT_FRACTION = 0.72

# The current NBA CDN returns a generic silhouette for these retired players.
# ESPN retains actual studio portraits at its stable player-image endpoint.
HISTORICAL_HEADSHOT_URLS = {
    2430: "https://a.espncdn.com/i/headshots/nba/players/full/1703.png",  # Carlos Boozer
    703: "https://a.espncdn.com/i/headshots/nba/players/full/846.png",  # Kurt Thomas
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
) -> tuple[float, float, float]:
    """Map PPG to either the clutch red scale or a comparison heat scale."""
    span = maximum - minimum
    fraction = 1.0 if span <= 0 else (float(points_per_game) - minimum) / span
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
) -> None:
    """Draw a gapless conditional-format column with optional outer rounding."""
    if fill_style not in {METRIC_FILL_ROUNDED_BAND, METRIC_FILL_SQUARE_CELLS}:
        raise ValueError(f"Unknown metric fill style: {fill_style}")

    clip_path = None
    if fill_style == METRIC_FILL_ROUNDED_BAND:
        top = layout.first_row_y + layout.row_height / 2
        bottom = (
            layout.first_row_y
            - (len(players) - 1) * layout.row_height
            - layout.row_height / 2
        )
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
        ax.add_patch(clip_path)

    # A small overlap prevents raster resampling from exposing hairline gaps
    # between adjacent fills. The shared clip only rounds the full band's
    # outside corners; every internal color transition stays square.
    overlap = 0.75 if fill_style == METRIC_FILL_ROUNDED_BAND else 0.0
    for index, value in enumerate(players["points_per_game"]):
        y = layout.first_row_y - index * layout.row_height
        cell = Rectangle(
            (metric_left, y - layout.row_height / 2 - overlap),
            metric_right - metric_left,
            layout.row_height + 2 * overlap,
            facecolor=ppg_fill(
                float(value), minimum_ppg, maximum_ppg, color_scale
            ),
            edgecolor="none",
            linewidth=0,
            antialiased=False,
            zorder=2,
        )
        if clip_path is not None:
            cell.set_clip_path(clip_path)
        ax.add_patch(cell)


def header_rule_segments() -> tuple[tuple[float, float], ...]:
    """Draw the full-width ruler directly beneath the column headers."""
    return ((ROW_RULE_LEFT, GP_RIGHT),)


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


def face_headshot_label(ax, image_path, x, y, half_size, *, zorder=4):
    """Place the face-focused crop used by the account's recent tables."""
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
    side = min(int(height * FACE_CROP_HEIGHT_FRACTION), width)
    left = max(0, (width - side) // 2)
    square = image[:side, left:left + side]
    return ax.imshow(
        square,
        extent=[x - half_size, x + half_size, y - half_size, y + half_size],
        interpolation="bilinear",
        zorder=zorder,
    )


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
    metric_header: str = "PPG",
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
    final: bool = False,
) -> Path:
    """Render one transparent player-metric table for Canva."""
    if winners.empty:
        raise ValueError("Cannot render an empty age ladder.")
    if metric_column not in winners.columns:
        raise ValueError(f"Age ladder rows are missing metric column {metric_column!r}.")
    sort_columns = ["age"] if sort_by is None else sort_by
    players = winners.sort_values(
        sort_columns,
        ascending=sort_ascending,
        kind="stable",
    ).reset_index(drop=True)
    if layout.first_row_y - (len(players) - 1) * layout.row_height - layout.row_height / 2 < 0:
        raise ValueError("Age ladder table does not fit the chart asset height.")
    dpi = export_dpi(final)
    fig = plt.figure(
        figsize=(CHART_WIDTH / dpi, CHART_HEIGHT / dpi),
        facecolor="none",
    )
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, CHART_WIDTH)
    ax.set_ylim(0, CHART_HEIGHT)
    ax.axis("off")

    theme = DEFAULT_THEME
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
    ax.text(
        (games_left + games_right) / 2,
        layout.header_y,
        "GP",
        ha="center",
        va="center",
        fontsize=layout.header_font_size,
        color=theme.ink,
        fontproperties=helvetica("bold"),
    )
    for rule_left, rule_right in header_rule_segments():
        ax.plot(
            [rule_left, rule_right],
            [layout.header_rule_y, layout.header_rule_y],
            color=theme.ink,
            linewidth=2.0,
        )

    metric_players = players.rename(columns={metric_column: "points_per_game"})
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
            y + layout.headshot_rise,
            layout.headshot_half_size,
            zorder=4,
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
            metric_value,
            minimum_ppg,
            maximum_ppg,
            color_scale,
        )
        ax.text(
            (metric_left + metric_right) / 2,
            y,
            f"{metric_value:.1f}",
            ha="center",
            va="center",
            fontsize=layout.ppg_font_size,
            color=ppg_text_color(fill),
            fontproperties=helvetica("bold"),
            zorder=4,
        )
        ax.text(
            (games_left + games_right) / 2,
            y,
            str(int(player["games"])),
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
    fig.savefig(path, dpi=dpi, transparent=True, pad_inches=0)
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
