"""Build the Bulls' top ten single-game performances by decade.

NBA.com's PlayerGameLogs endpoint supplies the historical Chicago player-game
box scores. This prototype caches one player-game response and one Bulls team
game response per season, calculates Hollinger Game Score and single-game TS%,
and renders three transparent table assets for Canva. By default the source is
the regular season; ``--playoffs`` switches the same analysis to playoff games.
"""

from __future__ import annotations

import argparse
import hashlib
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
from matplotlib.colors import to_rgb
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
    heat_text_color,
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
    2430: "https://a.espncdn.com/i/headshots/nba/players/full/1703.png",  # Carlos Boozer
    2768: "https://a.espncdn.com/i/headshots/nba/players/full/2377.png",  # Chris Duhon
}
CDN_SILHOUETTE_MD5 = "e7f284977a49"

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

# Alternate shooting-context layout used when FT replaces TS%. These positions
# match the settled playoff-performance table exactly.
FT_TABLE_PTS_LEFT, FT_TABLE_PTS_RIGHT = 696, 766
FT_TABLE_FG_LEFT, FT_TABLE_FG_RIGHT = 766, 871
FT_TABLE_THREE_PT_LEFT, FT_TABLE_THREE_PT_RIGHT = 871, 976
FT_TABLE_FT_LEFT, FT_TABLE_FT_RIGHT = 976, 1081
FT_TABLE_REB_LEFT, FT_TABLE_REB_RIGHT = 1081, 1157
FT_TABLE_AST_LEFT, FT_TABLE_AST_RIGHT = 1157, 1233
FT_TABLE_STL_LEFT, FT_TABLE_STL_RIGHT = 1233, 1309
FT_TABLE_BLK_LEFT, FT_TABLE_BLK_RIGHT = 1309, 1385
FT_TABLE_PLUS_MINUS_LEFT, FT_TABLE_PLUS_MINUS_RIGHT = 1385, 1461

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
    name_rise: float = 12
    context_drop: float = 17


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


def _read_cached_games(path: Path) -> pd.DataFrame:
    """Read a cached season with NBA.com's 10-character game IDs intact.

    Live responses carry zero-padded ID strings; letting pandas parse the cache
    as integers drops the zeros, so a cached side never joins a live one.
    """
    frame = pd.read_csv(path, dtype={"game_id": str})
    frame["game_id"] = frame["game_id"].str.zfill(10)
    return frame


def fetch_bulls_team_games(
    end_year: int,
    *,
    season_type: str = "Regular Season",
    refresh: bool = False,
) -> pd.DataFrame:
    """Load Bulls game scores used to reconcile player totals per game."""
    cache_path = RAW_CACHE / f"CHI-team-{season_type_slug(season_type)}-{end_year}.csv"
    if cache_path.exists() and not refresh:
        return _read_cached_games(cache_path)

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
    result["team_points"] = pd.to_numeric(result["team_points"], errors="raise").astype(int)
    # NBA.com leaves plus/minus blank before 1996-97; keep the blank rather than inventing zero.
    result["team_plus_minus"] = pd.to_numeric(result["team_plus_minus"], errors="raise").astype("Int64")
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
        cached = _read_cached_games(cache_path)
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
    first_end_year: int = FIRST_SEASON_END_YEAR,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Load every Bulls season of the requested type since 2000–01 (or ``first_end_year``)."""
    player_frames: list[pd.DataFrame] = []
    team_frames: list[pd.DataFrame] = []
    for end_year in range(first_end_year, LAST_SEASON_END_YEAR + 1):
        print(f"Loading {display_season_label(end_year)}")
        player_frames.append(fetch_bulls_season(end_year, season_type=season_type, refresh=refresh))
        team_frames.append(fetch_bulls_team_games(end_year, season_type=season_type, refresh=refresh))
    return (
        pd.concat(player_frames, ignore_index=True),
        pd.concat(team_frames, ignore_index=True),
    )


def decade_for_end_year(end_year: int) -> str:
    """Map an NBA ending year to the decade label used by the carousel."""
    if 1981 <= end_year <= 1990:
        return "1980s"
    if 1991 <= end_year <= 2000:
        return "1990s"
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


REGULATION_TEAM_MINUTES = 240.0
OVERTIME_TEAM_MINUTES = 25.0
# Overtime steps sit 25 minutes apart, so snapping is unambiguous well before
# half a step. The worst observed source drift is ~3 minutes, so 6 absorbs
# rounding with headroom while still rejecting a total that sits between steps.
MINUTES_TOLERANCE = 6.0
# Deviation past this is still assigned a period count but is reported, so a
# reader can see which games NBA.com under-reported.
MINUTES_REPORT_THRESHOLD = 1.0


def minute_reconciliation(table: pd.DataFrame) -> pd.DataFrame:
    """Compare each game's logged team minutes against its period budget.

    NBA.com's player game log carries no period count, but every box score
    distributes a fixed team minute budget: 240 in regulation and 25 more per
    overtime. Snapping to the nearest step recovers the period count; the
    residual exposes games whose minutes do not add up.
    """
    totals = table.groupby("game_id")["minutes"].sum().rename("team_minutes")
    periods = ((totals - REGULATION_TEAM_MINUTES) / OVERTIME_TEAM_MINUTES).round()
    expected = REGULATION_TEAM_MINUTES + periods * OVERTIME_TEAM_MINUTES
    frame = pd.concat([totals, periods.rename("overtime_periods").astype(int)], axis=1)
    frame["expected_minutes"] = expected
    frame["minutes_deviation"] = totals - expected
    if (frame["overtime_periods"] < 0).any():
        raise ValueError("A game logged fewer minutes than regulation allows.")
    off = frame[frame["minutes_deviation"].abs() > MINUTES_TOLERANCE]
    if not off.empty:
        raise ValueError(
            "Team minutes do not match a regulation/overtime budget: "
            f"{off['team_minutes'].to_dict()}"
        )
    return frame


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


def top_games_by_decade(table: pd.DataFrame, *, top_n: int = TOP_N) -> pd.DataFrame:
    """Return the requested top player-games in each decade with deterministic ties."""
    ranked = (
        table.sort_values(
            ["decade", "game_score", "points", "ts_pct", "game_date", "player", "player_id"],
            ascending=[True, False, False, False, True, True, True],
            kind="stable",
        )
        .groupby("decade", sort=False, group_keys=False)
        .head(top_n)
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
                    is_silhouette = hashlib.md5(cache_path.read_bytes()).hexdigest().startswith(
                        CDN_SILHOUETTE_MD5
                    )
                    usable_cache = image.format == "PNG" and not is_silhouette
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
    if pd.isna(value):
        return ""
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


# PTS, REB, AST lead, then the made-attempted shooting cells: the counting-stat reading order.
SHOOTING_AFTER_ASSISTS = (0, 3, 4, 1, 2, 5, 6, 7, 8)


def _shooting_order(cells: tuple, shooting_after_assists: bool) -> tuple:
    """Reorder the nine no-FT turnover cells when shooting follows assists."""
    return tuple(cells[i] for i in SHOOTING_AFTER_ASSISTS) if shooting_after_assists else cells


def _turnover_values(
    row: pd.Series, show_free_throws: bool, shooting_after_assists: bool = False
) -> tuple[str, ...]:
    """Return one row's cells for the turnover table, optionally including FT."""
    cells = (
        (
            str(int(row["points"])),
            f"{int(row['fgm'])}–{int(row['fga'])}",
            f"{int(row['fg3m'])}–{int(row['fg3a'])}",
        )
        + ((f"{int(row['ftm'])}–{int(row['fta'])}",) if show_free_throws else ())
        + (
            str(int(row["reb"])),
            str(int(row["ast"])),
            str(int(row["stl"])),
            str(int(row["blk"])),
            str(int(row["tov"])),
            _signed_box_score_value(row["plus_minus"]),
        )
    )
    return _shooting_order(cells, shooting_after_assists)


def identity_width(ax, rows: pd.DataFrame, layout: TableLayout) -> float:
    """Measure the widest player name or game-context line, as the row loop draws them."""
    def measure(text, size, weight=None):
        artist = ax.text(0, 0, text, fontsize=size,
                         fontproperties=helvetica(weight) if weight else helvetica())
        width = rendered_width(ax, artist)
        artist.remove()
        return width

    widest = 0.0
    for _, row in rows.iterrows():
        widest = max(widest, measure(_display_name(str(row["player"])), layout.name_font_size, "bold"))
        date, matchup, result = _game_context_parts(row)
        note = str(row.get("context_note", "") or "")
        parts = [(date, None), (matchup, None)] + ([(note, None)] if note and note != "nan" else [])
        context = sum(measure(text, layout.context_font_size, weight) + 9 for text, weight in parts)
        widest = max(widest, context + measure(result, layout.context_font_size, "bold"))
    return widest


def equal_gap_bounds(ax, cells, *, left, right, header_size, value_size):
    """Split [left, right] into columns as wide as their widest cell plus one shared gap.

    ``cells[0]`` is the header row (bold); the rest are value rows. Each column gets half a
    gap on both sides, so neighbouring columns always show the same white space.
    """
    widths = []
    for column in zip(*cells):
        column_widths = []
        for index, text in enumerate(column):
            artist = ax.text(0, 0, text, fontsize=header_size if index == 0 else value_size,
                             fontproperties=helvetica("bold"))
            column_widths.append(rendered_width(ax, artist))
            artist.remove()
        widths.append(max(column_widths))
    gap = (right - left - sum(widths)) / len(widths)
    if gap <= 0:
        raise ValueError("Table columns do not fit in the available width.")
    bounds, cursor = [], left
    for width in widths:
        bounds.append((cursor, cursor + width + gap))
        cursor += width + gap
    return tuple(bounds)


def render_chart(
    rows: pd.DataFrame,
    date: str,
    *,
    decade: str,
    season_type: str = "Regular Season",
    show_free_throws: bool = False,
    show_turnovers: bool = False,
    top_n: int = TOP_N,
    layout: TableLayout = DECADE_LAYOUT,
    final: bool = False,
    emphasize_points: bool = False,
    shooting_after_assists: bool = False,
    score_fill: Callable[[float], str] | None = None,
    show_plus_minus: bool = True,
    portraits: dict[int, Path] | None = None,
) -> Path:
    """Render one transparent decade table in the settled ladder grammar.

    ``score_fill`` swaps the continuous red card for per-row Game Score cells
    coloured by that function (for example ``house.game_score_fill``).
    ``portraits`` maps a player id to a post-local portrait that replaces the
    shared NBA CDN headshot (for players the CDN serves a silhouette for).
    """
    if shooting_after_assists and (not show_turnovers or show_free_throws):
        raise ValueError("Shooting after assists needs the turnover layout without FT.")
    if not show_plus_minus and (not show_turnovers or show_free_throws):
        raise ValueError("Dropping +/- needs the turnover layout without FT.")
    # +/- is the last cell in every turnover ordering.
    trim = (lambda cells: cells) if show_plus_minus else (lambda cells: cells[:-1])
    if len(rows) != top_n:
        raise ValueError(f"Expected {top_n} rows for {decade}; got {len(rows)}.")
    rows = rows.sort_values("rank", kind="stable").reset_index(drop=True)
    chart_height = slide_height(len(rows), layout)
    header_y = chart_height - layout.header_from_top
    header_rule_y = chart_height - layout.header_rule_from_top
    first_row_y = chart_height - layout.first_row_from_top
    dpi = export_dpi(final)
    fig = plt.figure(figsize=(CHART_WIDTH / export_dpi(False), chart_height / export_dpi(False)), facecolor="none")
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, CHART_WIDTH)
    ax.set_ylim(0, chart_height)
    ax.axis("off")
    theme = DEFAULT_THEME

    # The 15-row season table uses the full width more efficiently: portraits
    # reach the left edge, Game Score moves toward the identity block, the
    # three shooting columns share one width, and TOV fits beside BLK.
    if show_turnovers:
        gmsc_left, gmsc_right = 510, 618
        stat_bounds = (
            (636, 696),   # PTS
            (696, 790),   # FG
            (790, 884),   # 3PT
            (884, 978),   # FT
            (978, 1059),  # REB
            (1059, 1140), # AST
            (1140, 1221), # STL
            (1221, 1302), # BLK
            (1302, 1383), # TOV
            (1383, 1465), # +/-
        )
        if not show_free_throws:
            # Without FT, Game Score sits a fixed gap after the widest name or game line, and
            # each stat column takes its widest header or value plus one shared visible gap,
            # so neither long identities nor wide made-attempted cells crowd a neighbour.
            gmsc_left = round(layout.name_x + identity_width(ax, rows, layout) + 22)
            gmsc_right = gmsc_left + 108
            stat_bounds = equal_gap_bounds(
                ax,
                [trim(_shooting_order(("PTS", "FG", "3PT", "REB", "AST", "STL", "BLK", "TOV", "+/-"),
                                      shooting_after_assists))]
                + [trim(_turnover_values(row, False, shooting_after_assists))
                   for _, row in rows.iterrows()],
                left=gmsc_right + 18,
                right=1465,
                header_size=layout.header_font_size,
                value_size=layout.value_font_size,
            )
    else:
        gmsc_left, gmsc_right = GMSC_LEFT, GMSC_RIGHT
        stat_bounds = ()

    if show_turnovers:
        stat_labels = ("PTS", "FG", "3PT", "FT", "REB", "AST", "STL", "BLK", "TOV", "+/-")
        if not show_free_throws:
            stat_labels = trim(_shooting_order(
                tuple(label for label in stat_labels if label != "FT"), shooting_after_assists))
        headers = (
            (layout.name_x, "PLAYER", "left", theme.ink),
            ((gmsc_left + gmsc_right) / 2, "GMSC", "center",
             theme.ink if score_fill else theme.accent),
        ) + tuple(
            ((left + right) / 2, label, "center", theme.ink)
            for (left, right), label in zip(stat_bounds, stat_labels)
        )
    elif show_free_throws:
        headers = (
            (layout.name_x, "PLAYER", "left", theme.ink),
            ((GMSC_LEFT + GMSC_RIGHT) / 2, "GMSC", "center", theme.accent),
            ((FT_TABLE_PTS_LEFT + FT_TABLE_PTS_RIGHT) / 2, "PTS", "center", theme.ink),
            ((FT_TABLE_FG_LEFT + FT_TABLE_FG_RIGHT) / 2, "FG", "center", theme.ink),
            ((FT_TABLE_THREE_PT_LEFT + FT_TABLE_THREE_PT_RIGHT) / 2, "3PT", "center", theme.ink),
            ((FT_TABLE_FT_LEFT + FT_TABLE_FT_RIGHT) / 2, "FT", "center", theme.ink),
            ((FT_TABLE_REB_LEFT + FT_TABLE_REB_RIGHT) / 2, "REB", "center", theme.ink),
            ((FT_TABLE_AST_LEFT + FT_TABLE_AST_RIGHT) / 2, "AST", "center", theme.ink),
            ((FT_TABLE_STL_LEFT + FT_TABLE_STL_RIGHT) / 2, "STL", "center", theme.ink),
            ((FT_TABLE_BLK_LEFT + FT_TABLE_BLK_RIGHT) / 2, "BLK", "center", theme.ink),
            (
                (FT_TABLE_PLUS_MINUS_LEFT + FT_TABLE_PLUS_MINUS_RIGHT) / 2,
                "+/-",
                "center",
                theme.ink,
            ),
        )
    else:
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

    table_right = stat_bounds[-1][1] if show_turnovers else PLUS_MINUS_RIGHT
    separator_color = "#B8B0A8" if show_turnovers else theme.rule
    ax.plot(
        [0 if show_turnovers else ROW_RULE_LEFT, table_right],
        [header_rule_y, header_rule_y],
        color=theme.ink,
        linewidth=2.0,
        zorder=3,
    )

    if score_fill is None:
        draw_accent_card(
            ax, gmsc_left, gmsc_right, first_row_y, len(rows), layout.row_height
        )

    for index, row in rows.iterrows():
        y = first_row_y - index * layout.row_height
        if score_fill is not None:
            ax.add_patch(
                Rectangle(
                    (gmsc_left, y - layout.row_height / 2),
                    gmsc_right - gmsc_left,
                    layout.row_height,
                    facecolor=score_fill(float(row["game_score"])),
                    edgecolor="none",
                    zorder=2,
                )
            )
        if index:
            divider_y = y + layout.row_height / 2
            rule_segments = (
                ((0, table_right),)
                if score_fill is not None
                else ((0, gmsc_left), (gmsc_right, table_right))
                if show_turnovers
                else row_rule_segments()
            )
            for rule_left, rule_right in rule_segments:
                ax.plot(
                    [rule_left, rule_right],
                    [divider_y, divider_y],
                    color=separator_color,
                    linewidth=1.0,
                    zorder=3,
                )

        ax.text(
            (gmsc_left + gmsc_right) / 2,
            y,
            f"{float(row['game_score']):.1f}",
            ha="center",
            va="center",
            fontsize=layout.gmsc_font_size,
            color=(
                heat_text_color(to_rgb(score_fill(float(row["game_score"]))))
                if score_fill is not None
                else "#FFFFFF"
            ),
            fontproperties=helvetica("bold"),
            zorder=6,
        )
        face_headshot_label(
            ax,
            (portraits or {}).get(
                int(row["player_id"]), HEADSHOT_CACHE / f"{int(row['player_id'])}.png"
            ),
            layout.headshot_x,
            y + layout.headshot_rise,
            layout.headshot_half_size,
            zorder=4,
        )
        name = ax.text(
            layout.name_x,
            y + layout.name_rise,
            _display_name(str(row["player"])),
            ha="left",
            va="center",
            fontsize=layout.name_font_size,
            color=theme.ink,
            fontproperties=helvetica("bold"),
            zorder=4,
        )
        name_budget = gmsc_left - layout.name_x - 16
        width = rendered_width(ax, name)
        if width > name_budget:
            name.set_fontsize(layout.name_font_size * name_budget / width)
        context_date, context_matchup, context_result = _game_context_parts(row)
        context_font = helvetica()
        context_y = y - layout.context_drop
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
        result_x = matchup_x + rendered_width(ax, matchup_artist) + 9
        # Mixed regular-season/playoff tables mark playoff rows, e.g. "(RD 1 GM1)".
        context_note = str(row.get("context_note", "") or "")
        if context_note and context_note != "nan":
            note_artist = ax.text(
                result_x,
                context_y,
                context_note,
                ha="left",
                va="center",
                fontsize=layout.context_font_size,
                color=theme.muted,
                fontproperties=context_font,
                zorder=5,
            )
            result_x += rendered_width(ax, note_artist) + 9
        result_color = "#3FAE63" if context_result == "W" else "#D64545"
        ax.text(
            result_x,
            context_y,
            context_result,
            ha="left",
            va="center",
            fontsize=layout.context_font_size,
            color=result_color,
            fontproperties=helvetica("bold"),
            zorder=5,
        )
        if show_turnovers:
            values = tuple(
                (left, right, value)
                for (left, right), value in zip(
                    stat_bounds,
                    trim(_turnover_values(row, show_free_throws, shooting_after_assists)),
                )
            )
        elif show_free_throws:
            values = (
                (FT_TABLE_PTS_LEFT, FT_TABLE_PTS_RIGHT, str(int(row["points"]))),
                (FT_TABLE_FG_LEFT, FT_TABLE_FG_RIGHT, f"{int(row['fgm'])}–{int(row['fga'])}"),
                (
                    FT_TABLE_THREE_PT_LEFT,
                    FT_TABLE_THREE_PT_RIGHT,
                    f"{int(row['fg3m'])}–{int(row['fg3a'])}",
                ),
                (FT_TABLE_FT_LEFT, FT_TABLE_FT_RIGHT, f"{int(row['ftm'])}–{int(row['fta'])}"),
                (FT_TABLE_REB_LEFT, FT_TABLE_REB_RIGHT, str(int(row["reb"]))),
                (FT_TABLE_AST_LEFT, FT_TABLE_AST_RIGHT, str(int(row["ast"]))),
                (FT_TABLE_STL_LEFT, FT_TABLE_STL_RIGHT, str(int(row["stl"]))),
                (FT_TABLE_BLK_LEFT, FT_TABLE_BLK_RIGHT, str(int(row["blk"]))),
                (
                    FT_TABLE_PLUS_MINUS_LEFT,
                    FT_TABLE_PLUS_MINUS_RIGHT,
                    _signed_box_score_value(row["plus_minus"]),
                ),
            )
        else:
            values = (
                (TS_LEFT, TS_RIGHT, f"{float(row['ts_pct']):.1f}%"),
                (PTS_LEFT, PTS_RIGHT, str(int(row["points"]))),
                (FG_LEFT, FG_RIGHT, f"{int(row['fgm'])}–{int(row['fga'])}"),
                (THREE_PT_LEFT, THREE_PT_RIGHT, f"{int(row['fg3m'])}–{int(row['fg3a'])}"),
                (REB_LEFT, REB_RIGHT, str(int(row["reb"]))),
                (AST_LEFT, AST_RIGHT, str(int(row["ast"]))),
                (STL_LEFT, STL_RIGHT, str(int(row["stl"]))),
                (BLK_LEFT, BLK_RIGHT, str(int(row["blk"]))),
                (PLUS_MINUS_LEFT, PLUS_MINUS_RIGHT, _signed_box_score_value(row["plus_minus"])),
            )
        for column, (left, right, value) in enumerate(values):
            ax.text(
                (left + right) / 2,
                y,
                value,
                ha="center",
                va="center",
                fontsize=layout.value_font_size,
                color=theme.ink,
                fontproperties=helvetica("bold") if emphasize_points and column == 0 else helvetica(),
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
