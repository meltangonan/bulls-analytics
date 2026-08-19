"""Build the Bulls' top ten single-game performances by decade.

NBA.com's PlayerGameLogs endpoint supplies the historical Chicago player-game
box scores. This prototype caches one player-game response and one Bulls team
game response per season, calculates Hollinger Game Score and single-game TS%,
and renders three transparent table assets for Canva. By default the source is
the regular season; ``--playoffs`` switches the same analysis to playoff games.
"""

from __future__ import annotations

import argparse
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from io import BytesIO
from pathlib import Path
from typing import Callable
from zoneinfo import ZoneInfo

_REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO))

import matplotlib
import matplotlib.patheffects as PathEffects

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import requests
from PIL import Image
from matplotlib.patches import FancyBboxPatch, Rectangle
from nba_api.stats.endpoints import leaguegamefinder, playergamelogs

from bulls.config import BULLS_TEAM_ID
from bulls.data.fetch import _NBA_HEADERS
from bulls.graphics.house import (
    DEFAULT_THEME,
    accent_card_bounds,
    draw_accent_card,
    HEADSHOT_CACHE,
    ensure_headshots,
    export_dpi,
    helvetica,
    rendered_width,
)


FIRST_SEASON_END_YEAR = 2001
LAST_SEASON_END_YEAR = 2026
TOP_N = 10
NBA_REQUEST_ATTEMPTS = 3
LIVE_REQUEST_DELAY_SECONDS = 0.8
SNAPSHOT_TZ = ZoneInfo("America/Chicago")
SEASON_TYPE_SLUGS = {"Regular Season": "regular-season", "Playoffs": "playoffs"}
MIN_USABLE_HEADSHOT_BYTES = 5_000
HISTORICAL_HEADSHOT_URLS = {
    1500: "https://basket-retro.com/wp-content/uploads/2016/05/ron.jpg",  # Ron Mercer
    2768: "https://a.espncdn.com/i/headshots/nba/players/full/2377.png",  # Chris Duhon
}

CHART_WIDTH = 1500
ROW_RULE_LEFT = 24
GMSC_LEFT, GMSC_RIGHT = 566, 674
TS_LEFT, TS_RIGHT = 696, 796
PTS_LEFT, PTS_RIGHT = 796, 866
FG_LEFT, FG_RIGHT = 866, 971
THREE_PT_LEFT, THREE_PT_RIGHT = 971, 1076
REB_LEFT, REB_RIGHT = 1076, 1153
AST_LEFT, AST_RIGHT = 1153, 1230
STL_LEFT, STL_RIGHT = 1230, 1307
BLK_LEFT, BLK_RIGHT = 1307, 1384
PLUS_MINUS_LEFT, PLUS_MINUS_RIGHT = 1384, 1461

GAME_SCORE_CARD_OUTSET_X = 8
GAME_SCORE_CARD_OUTSET_Y = 9
GAME_SCORE_CARD_OVERLAP_Y = 7
GAME_SCORE_FILL = DEFAULT_THEME.accent


@dataclass(frozen=True)
class TableLayout:
    """Row and type sizing shared with the BPM/scoring ladder table family."""

    header_from_top: float
    header_rule_from_top: float
    first_row_from_top: float
    bottom_pad: float
    row_height: float
    headshot_x: float
    name_x: float
    headshot_half_size: float
    headshot_rise: float
    header_font_size: float
    name_font_size: float
    context_font_size: float
    value_font_size: float
    gmsc_font_size: float


DECADE_LAYOUT = TableLayout(
    header_from_top=59,
    header_rule_from_top=88,
    first_row_from_top=150,
    bottom_pad=56,
    row_height=112,
    headshot_x=112,
    name_x=176,
    headshot_half_size=58,
    headshot_rise=7,
    header_font_size=15,
    name_font_size=20,
    context_font_size=11.5,
    value_font_size=16,
    gmsc_font_size=16,
)

RAW_CACHE = _REPO / "cache" / "nba.com" / "top-game-performances"
OUT = _REPO / "output"

PLAYER_SOURCE_URL = (
    "https://www.nba.com/stats/players/boxscores-traditional"
    "?Season={season}&SeasonType={season_type}&TeamID={team_id}"
)
TEAM_SOURCE_URL = (
    "https://www.nba.com/stats/teams/boxscores"
    "?Season={season}&SeasonType={season_type}&TeamID={team_id}"
)

PLAYER_COLUMNS = {
    "PLAYER_ID": "player_id",
    "PLAYER_NAME": "player",
    "GAME_ID": "game_id",
    "GAME_DATE": "game_date",
    "MATCHUP": "matchup",
    "WL": "result",
    "MIN": "minutes",
    "PTS": "points",
    "FGM": "fgm",
    "FGA": "fga",
    "FG3M": "fg3m",
    "FG3A": "fg3a",
    "FTM": "ftm",
    "FTA": "fta",
    "OREB": "oreb",
    "DREB": "dreb",
    "REB": "reb",
    "AST": "ast",
    "STL": "stl",
    "BLK": "blk",
    "TOV": "tov",
    "PF": "pf",
    "PLUS_MINUS": "plus_minus",
}


def season_label(end_year: int) -> str:
    """Return an NBA end-year as an NBA season string."""
    return f"{end_year - 1}-{str(end_year)[-2:]}"


def display_season_label(end_year: int) -> str:
    """Return a season with an en dash for display."""
    return season_label(end_year).replace("-", "–", 1)


def season_type_slug(season_type: str) -> str:
    """Return the stable filename slug for an NBA.com season type."""
    try:
        return SEASON_TYPE_SLUGS[season_type]
    except KeyError as exc:
        raise ValueError(f"Unsupported NBA season type: {season_type!r}.") from exc


def _source_season_type(season_type: str) -> str:
    """Encode the season type in the query string used by nba.com/stats."""
    season_type_slug(season_type)
    return season_type.replace(" ", "%20")


def player_source_url(end_year: int, season_type: str = "Regular Season") -> str:
    return PLAYER_SOURCE_URL.format(
        season=season_label(end_year),
        season_type=_source_season_type(season_type),
        team_id=BULLS_TEAM_ID,
    )


def team_source_url(end_year: int, season_type: str = "Regular Season") -> str:
    return TEAM_SOURCE_URL.format(
        season=season_label(end_year),
        season_type=_source_season_type(season_type),
        team_id=BULLS_TEAM_ID,
    )


def game_score(row: pd.Series) -> float:
    """Calculate Hollinger Game Score from one traditional box score."""
    return float(
        row["points"]
        + 0.4 * row["fgm"]
        - 0.7 * row["fga"]
        - 0.4 * (row["fta"] - row["ftm"])
        + 0.7 * row["oreb"]
        + 0.3 * row["dreb"]
        + row["stl"]
        + 0.7 * row["ast"]
        + 0.7 * row["blk"]
        - 0.4 * row["pf"]
        - row["tov"]
    )


def true_shooting_pct(row: pd.Series) -> float:
    """Calculate estimated true shooting percentage for one game."""
    attempts = row["fga"] + 0.44 * row["fta"]
    if attempts <= 0:
        return 0.0
    return float(row["points"] / (2 * attempts) * 100)


def _request_frame(factory: Callable[[], object], source: str) -> pd.DataFrame:
    """Make a paced NBA.com request with small transient-failure retries."""
    for attempt in range(1, NBA_REQUEST_ATTEMPTS + 1):
        try:
            frame = factory().get_data_frames()[0]
            if not isinstance(frame, pd.DataFrame):
                raise ValueError(f"NBA.com {source} response was not a table.")
            time.sleep(LIVE_REQUEST_DELAY_SECONDS)
            return frame
        except (requests.RequestException, ValueError) as exc:
            if attempt == NBA_REQUEST_ATTEMPTS:
                raise
            wait_seconds = 2**attempt
            print(f"NBA.com {source} request failed ({exc}); retrying in {wait_seconds}s")
            time.sleep(wait_seconds)
    raise AssertionError("NBA.com retry loop ended unexpectedly.")


def _require_columns(frame: pd.DataFrame, required: set[str], source: str) -> None:
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"NBA.com {source} response is missing {sorted(missing)}.")


def _opponent(matchup: str) -> str:
    text = str(matchup)
    if "vs." in text:
        return text.split("vs.", 1)[1].strip()
    if "@" in text:
        return text.split("@", 1)[1].strip()
    return text


def fetch_bulls_team_games(
    end_year: int,
    *,
    season_type: str = "Regular Season",
    refresh: bool = False,
) -> pd.DataFrame:
    """Load Bulls game scores used to reconcile player totals per game."""
    cache_path = RAW_CACHE / f"CHI-team-{season_type_slug(season_type)}-{end_year}.csv"
    if cache_path.exists() and not refresh:
        return pd.read_csv(cache_path)

    season = season_label(end_year)
    frame = _request_frame(
        lambda: leaguegamefinder.LeagueGameFinder(
            team_id_nullable=BULLS_TEAM_ID,
            season_nullable=season,
            season_type_nullable=season_type,
            headers=_NBA_HEADERS,
            timeout=60,
        ),
        f"team games for {season}",
    )
    _require_columns(frame, {"GAME_ID", "GAME_DATE", "MATCHUP", "WL", "PTS", "PLUS_MINUS"}, "team games")
    result = frame[["GAME_ID", "GAME_DATE", "MATCHUP", "WL", "PTS", "PLUS_MINUS"]].copy()
    result = result.rename(
        columns={
            "GAME_ID": "game_id",
            "GAME_DATE": "game_date",
            "MATCHUP": "matchup",
            "WL": "result",
            "PTS": "team_points",
            "PLUS_MINUS": "team_plus_minus",
        }
    )
    for column in ("team_points", "team_plus_minus"):
        result[column] = pd.to_numeric(result[column], errors="raise").astype(int)
    result["game_id"] = result["game_id"].astype(str)
    result["season_end_year"] = end_year
    result["team_source_url"] = team_source_url(end_year, season_type)
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(cache_path, index=False)
    return result


def fetch_bulls_season(
    end_year: int,
    *,
    season_type: str = "Regular Season",
    refresh: bool = False,
) -> pd.DataFrame:
    """Load and calculate one Chicago player-game table for a season type."""
    cache_path = RAW_CACHE / f"CHI-players-{season_type_slug(season_type)}-{end_year}.csv"
    if cache_path.exists() and not refresh:
        cached = pd.read_csv(cache_path)
        if {"fg3m", "fg3a"}.issubset(cached.columns):
            return cached

    season = season_label(end_year)
    frame = _request_frame(
        lambda: playergamelogs.PlayerGameLogs(
            season_nullable=season,
            season_type_nullable=season_type,
            team_id_nullable=str(BULLS_TEAM_ID),
            timeout=60,
            headers=_NBA_HEADERS,
        ),
        f"player games for {season}",
    )
    _require_columns(frame, set(PLAYER_COLUMNS), "player games")
    result = frame[list(PLAYER_COLUMNS)].rename(columns=PLAYER_COLUMNS).copy()
    result["game_id"] = result["game_id"].astype(str)
    result["game_date"] = result["game_date"].astype(str).str.slice(0, 10)
    numeric_columns = [
        "player_id",
        "minutes",
        "points",
        "fgm",
        "fga",
        "fg3m",
        "fg3a",
        "ftm",
        "fta",
        "oreb",
        "dreb",
        "reb",
        "ast",
        "stl",
        "blk",
        "tov",
        "pf",
        "plus_minus",
    ]
    for column in numeric_columns:
        result[column] = pd.to_numeric(result[column], errors="raise")
    result["player_id"] = result["player_id"].astype(int)
    result["season_end_year"] = end_year
    result["season"] = display_season_label(end_year)
    result["opponent"] = result["matchup"].map(_opponent)
    result["game_score"] = result.apply(game_score, axis=1)
    result["ts_pct"] = result.apply(true_shooting_pct, axis=1)
    result["player_source_url"] = player_source_url(end_year, season_type)
    result = result[
        [
            "season_end_year",
            "season",
            "player_id",
            "player",
            "game_id",
            "game_date",
            "matchup",
            "opponent",
            "result",
            "minutes",
            "points",
            "fgm",
            "fga",
            "fg3m",
            "fg3a",
            "ftm",
            "fta",
            "oreb",
            "dreb",
            "reb",
            "ast",
            "stl",
            "blk",
            "tov",
            "pf",
            "plus_minus",
            "game_score",
            "ts_pct",
            "player_source_url",
        ]
    ]
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(cache_path, index=False)
    return result


def fetch_bulls_history(
    *,
    season_type: str = "Regular Season",
    refresh: bool = False,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Load every Bulls season of the requested type since 2000–01."""
    player_frames: list[pd.DataFrame] = []
    team_frames: list[pd.DataFrame] = []
    for end_year in range(FIRST_SEASON_END_YEAR, LAST_SEASON_END_YEAR + 1):
        print(f"Loading {display_season_label(end_year)}")
        player_frames.append(fetch_bulls_season(end_year, season_type=season_type, refresh=refresh))
        team_frames.append(fetch_bulls_team_games(end_year, season_type=season_type, refresh=refresh))
    return (
        pd.concat(player_frames, ignore_index=True),
        pd.concat(team_frames, ignore_index=True),
    )


def decade_for_end_year(end_year: int) -> str:
    """Map an NBA ending year to the decade label used by the carousel."""
    if 2001 <= end_year <= 2010:
        return "2000s"
    if 2011 <= end_year <= 2020:
        return "2010s"
    if 2021 <= end_year <= 2026:
        return "2020s"
    raise ValueError(f"Season ending {end_year} is outside the post timeframe.")


def build_working_table(players: pd.DataFrame, teams: pd.DataFrame) -> pd.DataFrame:
    """Validate raw rows and attach team-score reconciliation fields."""
    required_players = {
        "season_end_year",
        "season",
        "player_id",
        "player",
        "game_id",
        "game_date",
        "matchup",
        "opponent",
        "result",
        "minutes",
        "points",
        "fgm",
        "fga",
        "fg3m",
        "fg3a",
        "ftm",
        "fta",
        "oreb",
        "dreb",
        "reb",
        "ast",
        "stl",
        "blk",
        "tov",
        "pf",
        "plus_minus",
        "game_score",
        "ts_pct",
        "player_source_url",
    }
    required_teams = {
        "season_end_year",
        "game_id",
        "game_date",
        "matchup",
        "result",
        "team_points",
        "team_plus_minus",
        "team_source_url",
    }
    missing_players = required_players - set(players.columns)
    missing_teams = required_teams - set(teams.columns)
    if missing_players:
        raise ValueError(f"Player-game rows are missing {sorted(missing_players)}.")
    if missing_teams:
        raise ValueError(f"Team-game rows are missing {sorted(missing_teams)}.")

    table = players.copy()
    team = teams.copy()
    table["season_end_year"] = pd.to_numeric(table["season_end_year"], errors="raise").astype(int)
    team["season_end_year"] = pd.to_numeric(team["season_end_year"], errors="raise").astype(int)
    table["game_id"] = table["game_id"].astype(str)
    team["game_id"] = team["game_id"].astype(str)
    if table.duplicated(["game_id", "player_id"]).any():
        raise ValueError("NBA.com returned duplicate player-game rows.")
    if team.duplicated(["game_id"]).any():
        raise ValueError("NBA.com returned duplicate Bulls team-game rows.")

    joined = table.merge(
        team[
            [
                "season_end_year",
                "game_id",
                "game_date",
                "matchup",
                "result",
                "team_points",
                "team_plus_minus",
            ]
        ].rename(
            columns={
                "game_date": "team_game_date",
                "matchup": "team_matchup",
                "result": "team_result",
            }
        ),
        on=["season_end_year", "game_id"],
        how="left",
        validate="many_to_one",
    )
    if joined["team_points"].isna().any():
        raise ValueError("Every player-game row must match a Bulls team-game row.")
    for player_column, team_column in (
        ("game_date", "team_game_date"),
        ("matchup", "team_matchup"),
        ("result", "team_result"),
    ):
        if not joined[player_column].astype(str).eq(joined[team_column].astype(str)).all():
            raise ValueError(f"Player-game {player_column} does not match the Bulls team-game record.")
    joined["decade"] = joined["season_end_year"].map(decade_for_end_year)
    joined["game_score"] = joined.apply(game_score, axis=1)
    joined["ts_pct"] = joined.apply(true_shooting_pct, axis=1)
    return joined


def validate_working_table(
    table: pd.DataFrame,
    *,
    require_all_seasons: bool = True,
) -> dict[str, object]:
    """Validate coverage, score reconciliation, and exactly ten rows per decade."""
    expected_years = set(range(FIRST_SEASON_END_YEAR, LAST_SEASON_END_YEAR + 1))
    present_years = set(table["season_end_year"].astype(int))
    if require_all_seasons and present_years != expected_years:
        raise ValueError("Historical source coverage does not include every season since 2000–01.")
    if not present_years.issubset(expected_years):
        raise ValueError("Historical source coverage includes a season outside the post timeframe.")
    if table.duplicated(["game_id", "player_id"]).any():
        raise ValueError("The working table contains duplicate player-game rows.")
    if table["minutes"].isna().any():
        raise ValueError("Player-game minutes contain missing values.")
    if (table["minutes"] <= 0).any():
        raise ValueError("The working table contains non-playing player-game rows.")
    if not np.isfinite(table["game_score"]).all() or not np.isfinite(table["ts_pct"]).all():
        raise ValueError("Game Score and TS% must be finite for every row.")

    per_game = table.groupby(["season_end_year", "game_id"], as_index=False).agg(
        player_points=("points", "sum"),
        team_points=("team_points", "first"),
    )
    if not per_game["player_points"].eq(per_game["team_points"]).all():
        bad = per_game.loc[~per_game["player_points"].eq(per_game["team_points"])].head(1)
        raise ValueError(f"Player scoring does not reconcile to a Bulls team score: {bad.to_dict('records')}.")

    ranked = top_games_by_decade(table)
    counts = ranked.groupby("decade").size().to_dict()
    if counts != {"2000s": TOP_N, "2010s": TOP_N, "2020s": TOP_N}:
        raise ValueError(f"Each decade must produce exactly ten rows; got {counts}.")
    return {
        "season_count": len(present_years),
        "player_game_count": len(table),
        "game_count": table["game_id"].nunique(),
        "decade_counts": counts,
        "top_scores": {
            decade: ranked.loc[ranked["decade"].eq(decade), "game_score"].round(1).tolist()
            for decade in ("2000s", "2010s", "2020s")
        },
    }


def top_games_by_decade(table: pd.DataFrame) -> pd.DataFrame:
    """Return the top ten player-games in each decade with deterministic ties."""
    ranked = (
        table.sort_values(
            ["decade", "game_score", "points", "ts_pct", "game_date", "player", "player_id"],
            ascending=[True, False, False, False, True, True, True],
            kind="stable",
        )
        .groupby("decade", sort=False, group_keys=False)
        .head(TOP_N)
        .copy()
    )
    ranked["rank"] = ranked.groupby("decade", sort=False).cumcount() + 1
    return ranked.sort_values(["decade", "rank"], kind="stable").reset_index(drop=True)


def write_working_table(
    table: pd.DataFrame,
    date: str,
    *,
    season_type: str = "Regular Season",
) -> Path:
    path = OUT / f"{date}-bulls-top-game-performances-{season_type_slug(season_type)}-working.csv"
    path.parent.mkdir(parents=True, exist_ok=True)
    table.to_csv(path, index=False)
    return path


def ensure_historical_headshot_fallbacks(player_ids: list[int]) -> None:
    """Replace known NBA CDN silhouettes with usable historical portraits."""
    for player_id in {int(value) for value in player_ids}:
        url = HISTORICAL_HEADSHOT_URLS.get(player_id)
        cache_path = HEADSHOT_CACHE / f"{player_id}.png"
        usable_cache = False
        if cache_path.exists() and cache_path.stat().st_size >= MIN_USABLE_HEADSHOT_BYTES:
            try:
                with Image.open(cache_path) as image:
                    usable_cache = image.format == "PNG"
                    if player_id == 1500:
                        usable_cache = usable_cache and image.size == (188, 188)
            except (OSError, SyntaxError):
                usable_cache = False
        if url is None or usable_cache:
            continue
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        if len(response.content) < MIN_USABLE_HEADSHOT_BYTES:
            raise ValueError(f"Historical headshot fallback for NBA player {player_id} is unexpectedly small.")
        image = Image.open(BytesIO(response.content)).convert("RGBA")
        if player_id == 1500:
            # The source is a wide Kentucky portrait collage. Keep the clean
            # left portrait and leave the shared renderer to apply its normal
            # upper-face crop.
            image = image.crop((40, 0, 228, 188))
            pixels = np.array(image)
            pixels[(pixels[:, :, :3] >= 245).all(axis=2), 3] = 0
            image = Image.fromarray(pixels)
        image.save(cache_path, format="PNG")


def _display_name(name: str) -> str:
    """Use the natural display name while preserving NBA.com's source data."""
    return {"Jimmy Butler III": "Jimmy Butler"}.get(str(name), str(name))


def _signed_box_score_value(value: float | int) -> str:
    """Show positive plus/minus values with an explicit leading plus sign."""
    integer = int(value)
    return f"{integer:+d}" if integer > 0 else str(integer)


def _display_date(value: str) -> str:
    """Format an ISO source date compactly for the table context line."""
    return pd.Timestamp(value).strftime("%b %d, %Y").replace(" 0", " ")


def _game_context(row: pd.Series) -> str:
    date_label, matchup_label, result = _game_context_parts(row)
    return f"{date_label}  {matchup_label}  {result}"


def _game_context_parts(row: pd.Series) -> tuple[str, str, str]:
    result = str(row["result"]) if str(row["result"]) in {"W", "L"} else "–"
    matchup = str(row["matchup"])
    venue = "vs " if "vs." in matchup else "@"
    return _display_date(str(row["game_date"])), f"{venue}{_opponent(matchup)}", result


def face_headshot_label(ax, image_path, x, y, half_size, *, zorder=4):
    """Crop the upper portrait so current-team uniforms do not become the mark."""
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
    side = min(int(height * 0.74), width)
    left = max(0, (width - side) // 2)
    square = image[:side, left:left + side]
    return ax.imshow(
        square,
        extent=[x - half_size, x + half_size, y - half_size, y + half_size],
        interpolation="bilinear",
        zorder=zorder,
    )


def slide_height(row_count: int, layout: TableLayout = DECADE_LAYOUT) -> float:
    """Fit exactly the header and requested rows without transparent dead space."""
    return (
        layout.first_row_from_top
        + (row_count - 1) * layout.row_height
        + layout.row_height / 2
        + layout.bottom_pad
    )


def row_rule_segments() -> tuple[tuple[float, float], ...]:
    """Leave the Game Score cell edge-to-edge, as in the BPM table."""
    return ((ROW_RULE_LEFT, GMSC_LEFT), (GMSC_RIGHT, PLUS_MINUS_RIGHT))


def game_score_card_bounds(
    row_count: int,
    first_row_y: float,
    layout: TableLayout = DECADE_LAYOUT,
) -> tuple[float, float, float, float]:
    """Return the rounded card footprint behind the Game Score values."""
    return accent_card_bounds(
        GMSC_LEFT, GMSC_RIGHT, first_row_y, row_count, layout.row_height
    )


def game_score_card(
    ax,
    row_count: int,
    first_row_y: float,
    layout: TableLayout = DECADE_LAYOUT,
) -> None:
    """Draw one continuous, solid Bulls-red Game Score card.

    The shape now lives in `bulls.graphics.house` so the rookie leaderboard
    draws the identical card behind its own ranking column (DESIGN.md).
    """
    draw_accent_card(
        ax, GMSC_LEFT, GMSC_RIGHT, first_row_y, row_count, layout.row_height
    )


def render_chart(
    rows: pd.DataFrame,
    date: str,
    *,
    decade: str,
    season_type: str = "Regular Season",
    final: bool = False,
) -> Path:
    """Render one transparent decade table in the settled ladder grammar."""
    if len(rows) != TOP_N:
        raise ValueError(f"Expected ten rows for {decade}; got {len(rows)}.")
    rows = rows.sort_values("rank", kind="stable").reset_index(drop=True)
    layout = DECADE_LAYOUT
    chart_height = slide_height(len(rows), layout)
    header_y = chart_height - layout.header_from_top
    header_rule_y = chart_height - layout.header_rule_from_top
    first_row_y = chart_height - layout.first_row_from_top
    dpi = export_dpi(final)
    fig = plt.figure(figsize=(CHART_WIDTH / dpi, chart_height / dpi), facecolor="none")
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, CHART_WIDTH)
    ax.set_ylim(0, chart_height)
    ax.axis("off")
    theme = DEFAULT_THEME

    headers = (
        (layout.name_x, "PLAYER", "left", theme.ink),
        ((GMSC_LEFT + GMSC_RIGHT) / 2, "GMSC", "center", theme.accent),
        ((TS_LEFT + TS_RIGHT) / 2, "TS%", "center", theme.ink),
        ((PTS_LEFT + PTS_RIGHT) / 2, "PTS", "center", theme.ink),
        ((FG_LEFT + FG_RIGHT) / 2, "FG", "center", theme.ink),
        ((THREE_PT_LEFT + THREE_PT_RIGHT) / 2, "3PT", "center", theme.ink),
        ((REB_LEFT + REB_RIGHT) / 2, "REB", "center", theme.ink),
        ((AST_LEFT + AST_RIGHT) / 2, "AST", "center", theme.ink),
        ((STL_LEFT + STL_RIGHT) / 2, "STL", "center", theme.ink),
        ((BLK_LEFT + BLK_RIGHT) / 2, "BLK", "center", theme.ink),
        ((PLUS_MINUS_LEFT + PLUS_MINUS_RIGHT) / 2, "+/-", "center", theme.ink),
    )
    for x, label, alignment, color in headers:
        ax.text(
            x,
            header_y,
            label,
            ha=alignment,
            va="center",
            fontsize=layout.header_font_size,
            color=color,
            fontproperties=helvetica("bold"),
        )

    ax.plot(
        [ROW_RULE_LEFT, PLUS_MINUS_RIGHT],
        [header_rule_y, header_rule_y],
        color=theme.ink,
        linewidth=2.0,
        zorder=3,
    )

    game_score_card(ax, len(rows), first_row_y, layout)

    for index, row in rows.iterrows():
        y = first_row_y - index * layout.row_height
        if index:
            divider_y = y + layout.row_height / 2
            for rule_left, rule_right in row_rule_segments():
                ax.plot(
                    [rule_left, rule_right],
                    [divider_y, divider_y],
                    color=theme.rule,
                    linewidth=1.0,
                    zorder=3,
                )

        ax.text(
            (GMSC_LEFT + GMSC_RIGHT) / 2,
            y,
            f"{float(row['game_score']):.1f}",
            ha="center",
            va="center",
            fontsize=layout.gmsc_font_size,
            color="#FFFFFF",
            fontproperties=helvetica("bold"),
            zorder=6,
        )
        face_headshot_label(
            ax,
            HEADSHOT_CACHE / f"{int(row['player_id'])}.png",
            layout.headshot_x,
            y + layout.headshot_rise,
            layout.headshot_half_size,
            zorder=4,
        )
        name = ax.text(
            layout.name_x,
            y + 12,
            _display_name(str(row["player"])),
            ha="left",
            va="center",
            fontsize=layout.name_font_size,
            color=theme.ink,
            fontproperties=helvetica("bold"),
            zorder=4,
        )
        name_budget = GMSC_LEFT - layout.name_x - 16
        width = rendered_width(ax, name)
        if width > name_budget:
            name.set_fontsize(layout.name_font_size * name_budget / width)
        context_date, context_matchup, context_result = _game_context_parts(row)
        context_font = helvetica()
        context_y = y - 17
        date_artist = ax.text(
            layout.name_x,
            context_y,
            context_date,
            ha="left",
            va="center",
            fontsize=layout.context_font_size,
            color=theme.muted,
            fontproperties=context_font,
            zorder=5,
        )
        date_width = rendered_width(ax, date_artist)
        matchup_x = layout.name_x + date_width + 9
        matchup_artist = ax.text(
            matchup_x,
            context_y,
            context_matchup,
            ha="left",
            va="center",
            fontsize=layout.context_font_size,
            color=theme.muted,
            fontproperties=context_font,
            zorder=5,
        )
        matchup_width = rendered_width(ax, matchup_artist)
        result_color = "#3FAE63" if context_result == "W" else "#D64545"
        ax.text(
            matchup_x + matchup_width + 9,
            context_y,
            context_result,
            ha="left",
            va="center",
            fontsize=layout.context_font_size,
            color=result_color,
            fontproperties=helvetica("bold"),
            zorder=5,
        )
        for left, right, value in (
            (TS_LEFT, TS_RIGHT, f"{float(row['ts_pct']):.1f}%"),
            (PTS_LEFT, PTS_RIGHT, str(int(row["points"]))),
            (FG_LEFT, FG_RIGHT, f"{int(row['fgm'])}–{int(row['fga'])}"),
            (THREE_PT_LEFT, THREE_PT_RIGHT, f"{int(row['fg3m'])}–{int(row['fg3a'])}"),
            (REB_LEFT, REB_RIGHT, str(int(row["reb"]))),
            (AST_LEFT, AST_RIGHT, str(int(row["ast"]))),
            (STL_LEFT, STL_RIGHT, str(int(row["stl"]))),
            (BLK_LEFT, BLK_RIGHT, str(int(row["blk"]))),
            (PLUS_MINUS_LEFT, PLUS_MINUS_RIGHT, _signed_box_score_value(row["plus_minus"])),
        ):
            ax.text(
                (left + right) / 2,
                y,
                value,
                ha="center",
                va="center",
                fontsize=layout.value_font_size,
                color=theme.ink,
                fontproperties=helvetica(),
                zorder=4,
            )

    OUT.mkdir(parents=True, exist_ok=True)
    suffix = "final" if final else "draft"
    path = OUT / (
        f"{date}-bulls-top-game-performances-{season_type_slug(season_type)}-"
        f"{decade}-{suffix}.png"
    )
    fig.savefig(path, dpi=dpi, transparent=True, bbox_inches=None, pad_inches=0)
    plt.close(fig)
    return path


def canva_copy_block(report: dict[str, object], season_type: str = "Regular Season") -> str:
    """Return the exact data-bound framing for Canva."""
    playoff = season_type == "Playoffs"
    period = "playoff" if playoff else "regular-season"
    title = "THE BULLS' BEST PLAYOFF GAMES BY DECADE" if playoff else "THE BULLS' BEST GAMES BY DECADE"
    subtitle = f"Top 10 {period} box-score performances ranked by Game Score"
    footer = (
        f"Data via nba.com | 2000–01 to 2025–26 {period} games | "
        "Game Score calculated from NBA.com box scores"
    )
    audit_suffix = "seasons with a playoff game" if playoff else "seasons"
    return "\n".join(
        [
            "CANVA COPY",
            f"TITLE: {title}",
            f"SUBTITLE: {subtitle}",
            "SLIDES: 2000s | 2010s | 2020s",
            f"FOOTER: {footer}",
            "NOTE: Game Score measures box-score productivity; TS% is supporting context. Overtime games are included and not adjusted.",
            f"AUDIT: {report['player_game_count']} player-games across {report['game_count']} Bulls {period} games and {report['season_count']} {audit_suffix}.",
        ]
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the Bulls top-game performances carousel assets.")
    parser.add_argument("--refresh", action="store_true", help="Refetch all cached NBA.com season responses.")
    parser.add_argument("--playoffs", action="store_true", help="Use playoff games instead of regular-season games.")
    parser.add_argument("--final", action="store_true", help="Export at final resolution after approval.")
    args = parser.parse_args()

    snapshot = datetime.now(SNAPSHOT_TZ)
    season_type = "Playoffs" if args.playoffs else "Regular Season"
    players, teams = fetch_bulls_history(season_type=season_type, refresh=args.refresh)
    table = build_working_table(players, teams)
    report = validate_working_table(table, require_all_seasons=season_type == "Regular Season")
    date = snapshot.date().isoformat()
    audit_path = write_working_table(table, date, season_type=season_type)
    ranked = top_games_by_decade(table)
    ensure_headshots(ranked["player_id"].tolist())
    ensure_historical_headshot_fallbacks(ranked["player_id"].tolist())
    chart_paths = []
    for decade in ("2000s", "2010s", "2020s"):
        chart_paths.append(
            render_chart(
                ranked.loc[ranked["decade"].eq(decade)],
                date,
                decade=decade,
                season_type=season_type,
                final=args.final,
            )
        )
    print(f"Audit: {audit_path}")
    for chart_path in chart_paths:
        print(f"Chart: {chart_path}")
    print(canva_copy_block(report, season_type))
    for decade in ("2000s", "2010s", "2020s"):
        print(f"\n{decade}")
        print(
            ranked.loc[ranked["decade"].eq(decade), ["rank", "player", "game_date", "opponent", "game_score", "ts_pct"]]
            .to_string(index=False)
        )


if __name__ == "__main__":
    main()
