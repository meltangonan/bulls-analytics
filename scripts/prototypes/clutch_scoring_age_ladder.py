"""Build the Bulls' clutch scoring leader at every NBA-listed age since 2000.

Clutch means the final five minutes of the fourth quarter or overtime with the
score within five points.  The primary number is total clutch points: unlike a
rate leaderboard, it rewards both scoring and repeatedly earning close-game
minutes.  Actual clutch minutes and points per five clutch minutes remain
visible so the opportunity and scoring rate behind the total are not hidden.
"""

from __future__ import annotations

import argparse
import shutil
import sys
import time
from datetime import datetime
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO))

import pandas as pd
from nba_api.stats.endpoints import leaguedashplayerclutch

from bulls.config import BULLS_TEAM_ID
from bulls.data.fetch import _NBA_HEADERS
from bulls.graphics.house import HEADSHOT_CACHE, ensure_headshots
from scripts.prototypes.assist_age_ladder import ensure_blank_headshot
from scripts.prototypes.assist_duos import display_name
from scripts.prototypes.scoring_age_ladder import (
    PPG_SCALE_RED_YELLOW_GREEN,
    SNAPSHOT_TZ,
    TrailingColumn,
    ensure_historical_headshot_fallbacks,
    render_chart,
)
from scripts.prototypes.stocks_age_ladder import (
    STOCKS_CHART_HEIGHT,
    STOCKS_CHART_WIDTH,
    STOCKS_FACE_CROP_FRACTION,
    STOCKS_LAYOUT,
    STOCKS_METRIC_WIDTH,
    STOCKS_NAME_COLUMN_GAP,
)

PROJECT = "clutch-scoring-age-ladder"
PROJECT_DATE = "2026-09-13"
FIRST_SEASON = 2000
LAST_SEASON = 2025
MIN_CLUTCH_GAMES = 10
CLUTCH_TIME = "Last 5 Minutes"
POINT_DIFF = "5"
AHEAD_BEHIND = "Ahead or Behind"

DATA_DIR = _REPO / "docs" / "visuals" / f"{PROJECT_DATE}-{PROJECT}" / "data"
ANTONIO_DAVIS_PORTRAIT = DATA_DIR / "portraits" / "213-user-provided-cutout.png"
OUT = _REPO / "output" / PROJECT
SOURCE_URL = (
    "https://www.nba.com/stats/players/clutch-traditional"
    "?PerMode=Totals&Season={season}&SeasonType=Regular%20Season"
    "&ClutchTime=Last%205%20Minutes&PointDiff=5"
    f"&TeamID={BULLS_TEAM_ID}"
)
KEEP = [
    "season", "player_id", "player", "age", "clutch_games", "clutch_minutes",
    "clutch_points", "clutch_fgm", "clutch_fga", "clutch_ftm", "clutch_fta",
    "wins", "losses", "source_url",
]
LEAGUE_AVERAGE_RATIO_FLOOR = 0.0
LEAGUE_AVERAGE_RATIO_MIDPOINT = 1.0
# The full qualified NBA population's 95th percentile is about 2.9x its
# season average.  Four times average leaves headroom above that mark while
# still reserving full green for truly exceptional seasons.
LEAGUE_AVERAGE_RATIO_CEILING = 4.0
TRAILING_COLUMNS = (
    TrailingColumn("MIN", "clutch_minutes"),
    TrailingColumn("PTS/5MIN", "clutch_points_per_5_minutes", decimals=1),
)
# The longer rate label needs more air than the stock ladder's compact GP/STL
# headers. Equal slots keep MIN and PTS/5MIN visually balanced.
CLUTCH_TRAILING_SLOT_WIDTH = 160
# DESIGN.md's structural separator gray stays visible on Canva's warm canvas;
# the inherited jersey-theme rule is too pale and reads as white after export.
CLUTCH_ROW_RULE_COLOR = "#B8B0A8"


def season_labels() -> list[str]:
    return [f"{year}-{str(year + 1)[-2:]}" for year in range(FIRST_SEASON, LAST_SEASON + 1)]


def fetch_season(season: str) -> pd.DataFrame:
    """Fetch one team-filtered clutch season and retain claim-bearing fields."""
    frame = leaguedashplayerclutch.LeagueDashPlayerClutch(
        season=season,
        season_type_all_star="Regular Season",
        per_mode_detailed="Totals",
        clutch_time=CLUTCH_TIME,
        point_diff=POINT_DIFF,
        ahead_behind=AHEAD_BEHIND,
        team_id_nullable=BULLS_TEAM_ID,
        timeout=60,
        headers=_NBA_HEADERS,
    ).get_data_frames()[0]
    required = {"PLAYER_ID", "PLAYER_NAME", "AGE", "GP", "W", "L", "MIN", "PTS", "FGM", "FGA", "FTM", "FTA"}
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"NBA.com clutch response changed, missing {sorted(missing)}")
    if frame.empty:
        raise ValueError(f"NBA.com returned no Bulls clutch rows for {season}.")
    if frame["PLAYER_ID"].duplicated().any():
        raise ValueError(f"NBA.com returned duplicate Bulls players for {season}.")
    out = frame[list(required)].rename(columns={
        "PLAYER_ID": "player_id", "PLAYER_NAME": "player", "AGE": "age",
        "GP": "clutch_games", "W": "wins", "L": "losses", "MIN": "clutch_minutes",
        "PTS": "clutch_points", "FGM": "clutch_fgm", "FGA": "clutch_fga",
        "FTM": "clutch_ftm", "FTA": "clutch_fta",
    })
    out.insert(0, "season", season)
    out["source_url"] = SOURCE_URL.format(season=season)
    return out[KEEP]


def fetch_league_season(season: str) -> pd.DataFrame:
    """Fetch the league population used to grade that season's Bulls rows."""
    frame = leaguedashplayerclutch.LeagueDashPlayerClutch(
        season=season,
        season_type_all_star="Regular Season",
        per_mode_detailed="Totals",
        clutch_time=CLUTCH_TIME,
        point_diff=POINT_DIFF,
        ahead_behind=AHEAD_BEHIND,
        timeout=60,
        headers=_NBA_HEADERS,
    ).get_data_frames()[0]
    required = {"PLAYER_ID", "PLAYER_NAME", "GP", "PTS"}
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"NBA.com league clutch response changed, missing {sorted(missing)}")
    if frame.empty:
        raise ValueError(f"NBA.com returned no league clutch rows for {season}.")
    out = frame[["PLAYER_ID", "PLAYER_NAME", "GP", "PTS"]].rename(columns={
        "PLAYER_ID": "player_id", "PLAYER_NAME": "player",
        "GP": "clutch_games", "PTS": "clutch_points",
    })
    out.insert(0, "season", season)
    return out


def load_or_fetch_season(season: str, *, refresh: bool = False) -> pd.DataFrame:
    path = DATA_DIR / f"CHI-{season}.csv"
    if path.exists() and not refresh:
        return pd.read_csv(path)
    for attempt in range(1, 4):
        try:
            frame = fetch_season(season)
            path.parent.mkdir(parents=True, exist_ok=True)
            frame.to_csv(path, index=False)
            time.sleep(0.8)
            return frame
        except Exception:  # noqa: BLE001 - transient NBA endpoint errors are retried
            if attempt == 3:
                raise
            time.sleep(2**attempt)
    raise AssertionError("retry loop ended unexpectedly")


def load_or_fetch_league_season(season: str, *, refresh: bool = False) -> pd.DataFrame:
    path = DATA_DIR / f"league-{season}.csv"
    if path.exists() and not refresh:
        return pd.read_csv(path)
    for attempt in range(1, 4):
        try:
            frame = fetch_league_season(season)
            path.parent.mkdir(parents=True, exist_ok=True)
            frame.to_csv(path, index=False)
            time.sleep(0.8)
            return frame
        except Exception:  # noqa: BLE001 - transient NBA endpoint errors are retried
            if attempt == 3:
                raise
            time.sleep(2**attempt)
    raise AssertionError("retry loop ended unexpectedly")


def fetch_history(*, refresh: bool = False) -> pd.DataFrame:
    frames = []
    for season in season_labels():
        print(f"Loading {season}")
        frames.append(load_or_fetch_season(season, refresh=refresh))
    return pd.concat(frames, ignore_index=True)


def fetch_league_history(*, refresh: bool = False) -> pd.DataFrame:
    frames = []
    for season in season_labels():
        print(f"Loading league {season}")
        frames.append(load_or_fetch_league_season(season, refresh=refresh))
    return pd.concat(frames, ignore_index=True)


def league_averages(league: pd.DataFrame) -> pd.DataFrame:
    """Arithmetic mean clutch points among players meeting the post's floor."""
    qualified = league.loc[league["clutch_games"] >= MIN_CLUTCH_GAMES].copy()
    if set(qualified["season"]) != set(season_labels()):
        raise ValueError("League clutch baseline does not cover every season since 2000.")
    baseline = qualified.groupby("season", as_index=False).agg(
        league_average_clutch_points=("clutch_points", "mean"),
        league_qualified_players=("player_id", "size"),
    )
    if not baseline["league_average_clutch_points"].between(20, 60).all():
        raise ValueError("A league clutch-points average is outside the expected range.")
    if not baseline["league_qualified_players"].ge(50).all():
        raise ValueError("A league clutch baseline has too few qualified players.")
    return baseline


def attach_league_average(table: pd.DataFrame, league: pd.DataFrame) -> pd.DataFrame:
    out = table.merge(league_averages(league), on="season", how="left", validate="many_to_one")
    if out["league_average_clutch_points"].isna().any():
        raise ValueError("A Bulls row is missing its season's league clutch average.")
    out["league_average_ratio"] = (
        out["clutch_points"] / out["league_average_clutch_points"]
    )
    return out


def build_working_table(rows: pd.DataFrame) -> pd.DataFrame:
    missing = set(KEEP) - set(rows.columns)
    if missing:
        raise ValueError(f"Historical clutch rows are missing {sorted(missing)}")
    table = rows.copy()
    numeric = ["player_id", "age", "clutch_games", "wins", "losses", "clutch_points"]
    for column in numeric:
        table[column] = pd.to_numeric(table[column], errors="raise").astype(int)
    table["season_end_year"] = table["season"].str[:4].astype(int) + 1
    table["games"] = table["clutch_games"]
    table["clutch_points_per_game"] = table["clutch_points"] / table["clutch_games"]
    positive_minutes = table["clutch_minutes"] > 0
    table["clutch_points_per_minute"] = (
        table["clutch_points"] / table["clutch_minutes"]
    ).where(positive_minutes)
    table["clutch_points_per_5_minutes"] = table["clutch_points_per_minute"] * 5
    table["qualified"] = table["clutch_games"] >= MIN_CLUTCH_GAMES
    winners = (
        table.loc[table["qualified"]]
        .sort_values(
            ["age", "clutch_points", "clutch_points_per_game", "clutch_games", "player"],
            ascending=[True, False, False, False, True], kind="stable",
        )
        .drop_duplicates("age", keep="first")
    )
    keys = pd.MultiIndex.from_frame(winners[["season", "player_id"]])
    table["selected"] = pd.MultiIndex.from_frame(table[["season", "player_id"]]).isin(keys)
    return table.sort_values(["age", "season", "player_id"], kind="stable").reset_index(drop=True)


def age_winners(table: pd.DataFrame) -> pd.DataFrame:
    return table.loc[table["selected"]].sort_values("age", kind="stable").reset_index(drop=True)


def validate(table: pd.DataFrame) -> dict[str, object]:
    if set(table["season"]) != set(season_labels()):
        raise ValueError("Historical clutch source does not cover every season since 2000.")
    if table.duplicated(["season", "player_id"]).any():
        raise ValueError("A Bulls player appears more than once in a season.")
    if not (table["wins"] + table["losses"]).eq(table["clutch_games"]).all():
        raise ValueError("Clutch wins and losses do not reconcile to appearances.")
    if not table["qualified"].eq(table["clutch_games"] >= MIN_CLUTCH_GAMES).all():
        raise ValueError("Minimum clutch-games qualification is inconsistent.")
    positive_minutes = table["clutch_minutes"] > 0
    expected_per_five = (
        table.loc[positive_minutes, "clutch_points"]
        / table.loc[positive_minutes, "clutch_minutes"]
        * 5
    )
    if not table.loc[positive_minutes, "clutch_points_per_5_minutes"].sub(expected_per_five).abs().lt(1e-10).all():
        raise ValueError("Points per five clutch minutes do not reconcile to points and minutes.")
    if "league_average_ratio" in table:
        if not table["league_average_ratio"].ge(0).all():
            raise ValueError("A league-average clutch-points ratio is negative.")
        if not table["league_qualified_players"].ge(50).all():
            raise ValueError("A league clutch baseline has too few qualified players.")
    winners = age_winners(table)
    if winners["clutch_points_per_5_minutes"].isna().any():
        raise ValueError("A displayed winner has no positive clutch-minute denominator.")
    expected = (
        table.loc[table["qualified"]]
        .sort_values(["age", "clutch_points", "clutch_points_per_game", "clutch_games", "player"],
                     ascending=[True, False, False, False, True], kind="stable")
        .drop_duplicates("age", keep="first")
    )
    if set(zip(winners.season, winners.player_id)) != set(zip(expected.season, expected.player_id)):
        raise ValueError("Selected clutch ladder does not use the correct winners.")
    return {
        "season_count": table["season"].nunique(), "qualified_count": int(table["qualified"].sum()),
        "age_count": len(winners), "youngest_age": int(winners.age.min()),
        "oldest_age": int(winners.age.max()), "highest_points": int(winners.clutch_points.max()),
        "lowest_points": int(winners.clutch_points.min()),
        "lowest_ratio": float(winners.league_average_ratio.min()),
        "highest_ratio": float(winners.league_average_ratio.max()),
    }


def apply_display_names(winners: pd.DataFrame) -> pd.DataFrame:
    out = winners.copy()
    out["player"] = [display_name(str(r.player), int(r.player_id), int(r.season_end_year)) for r in out.itertuples()]
    return out


def install_post_portrait_fallbacks() -> None:
    """Install approved, post-local portraits after the shared CDN fallback."""
    if not ANTONIO_DAVIS_PORTRAIT.exists():
        raise FileNotFoundError(f"Missing Antonio Davis portrait: {ANTONIO_DAVIS_PORTRAIT}")
    HEADSHOT_CACHE.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(ANTONIO_DAVIS_PORTRAIT, HEADSHOT_CACHE / "213.png")


def render(winners: pd.DataFrame, date: str, *, final: bool = False) -> Path:
    # The printed total stays familiar; its fill grades the season against the
    # average NBA player who met the same 10-clutch-game qualification.
    return render_chart(
        apply_display_names(winners), date, slug="one-slide", layout=STOCKS_LAYOUT,
        scale_min=LEAGUE_AVERAGE_RATIO_FLOOR,
        scale_max=LEAGUE_AVERAGE_RATIO_CEILING,
        fill_midpoint=LEAGUE_AVERAGE_RATIO_MIDPOINT,
        color_scale=PPG_SCALE_RED_YELLOW_GREEN,
        metric_column="clutch_points", fill_column="league_average_ratio",
        metric_header="PTS", metric_decimals=0,
        output_stem="bulls-clutch-scoring-age-ladder", trailing_columns=TRAILING_COLUMNS,
        chart_width=STOCKS_CHART_WIDTH, chart_height=STOCKS_CHART_HEIGHT,
        auto_name_column=True, name_column_gap=STOCKS_NAME_COLUMN_GAP,
        metric_width=STOCKS_METRIC_WIDTH,
        trailing_slot_width=CLUTCH_TRAILING_SLOT_WIDTH,
        row_rule_color=CLUTCH_ROW_RULE_COLOR,
        face_crop_fraction=STOCKS_FACE_CROP_FRACTION,
        portrait_crop_overrides={213: 0.68},
        clip_portraits_to_row=True,
        final=final,
    )


def canva_copy(report: dict[str, object]) -> str:
    return "\n".join([
        "TITLE: THE BULLS' CLUTCH SCORING AGE LADDER",
        "SUBTITLE: Most clutch points by a Bull at every age since 2000",
        "FOOTER: Data via nba.com | 2000–01 to 2025–26 regular seasons | Min. 10 clutch games | NBA-listed age",
        "NOTE: Clutch = final 5:00 with the score within 5 points. Chicago-only player stints.",
        "NOTE: MIN is total clutch minutes. PTS/5MIN is points per five clutch minutes, "
        "calculated from all actual clutch minutes, including shorter appearances and overtime.",
        "NOTE: One qualifying player-season per age.",
        "NOTE: PTS shading compares each player to that season's NBA average among players with 10+ clutch games. "
        "Yellow is average; green is 4x average.",
        f"AUDIT: {report['age_count']} ages ({report['youngest_age']}–{report['oldest_age']}); "
        f"{report['qualified_count']} qualifying player-seasons across {report['season_count']} seasons; "
        f"displayed totals {report['lowest_points']}–{report['highest_points']}; "
        f"{report['lowest_ratio']:.2f}x–{report['highest_ratio']:.2f}x league average.",
    ])


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the Bulls clutch-scoring age ladder.")
    parser.add_argument("--refresh", action="store_true")
    parser.add_argument("--final", action="store_true")
    args = parser.parse_args()
    table = attach_league_average(
        build_working_table(fetch_history(refresh=args.refresh)),
        fetch_league_history(refresh=args.refresh),
    )
    report = validate(table)
    OUT.mkdir(parents=True, exist_ok=True)
    working = OUT / f"{PROJECT_DATE}-bulls-clutch-scoring-age-ladder-working.csv"
    table.to_csv(working, index=False)
    winners = age_winners(table)
    ids = sorted(set(winners.player_id))
    ensure_headshots(ids)
    ensure_historical_headshot_fallbacks(ids)
    install_post_portrait_fallbacks()
    ensure_blank_headshot()
    chart = render(winners, datetime.now(SNAPSHOT_TZ).date().isoformat(), final=args.final)
    print(f"Audit: {working}\nChart: {chart}\n{canva_copy(report)}")


if __name__ == "__main__":
    main()
