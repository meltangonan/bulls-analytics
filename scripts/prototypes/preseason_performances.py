"""Build the Bulls' top fifteen preseason performances since 2005-06.

The established top-game-performances prototype owns Hollinger Game Score,
reconciliation, and the settled table renderer. This prototype differs only in
its source: preseason rows come from NBA.com's LeagueGameLog, the feed behind
nba.com/stats/players/boxscores.

PlayerGameLogs, which the regular-season posts use, drops three Bulls preseason
games in 2005-06 and 2006-07 that LeagueGameLog keeps. Before 2005-06 the
preseason feed is not usable: 2003-04 and 2004-05 hold only 15 and 48 games
league-wide (a full preseason is about 110) and every row records exactly five
minutes, a placeholder. Earlier seasons return nothing.
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd
from nba_api.stats.endpoints import leaguegamelog

_REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO))

from bulls.data.fetch import _NBA_HEADERS
from scripts.prototypes import top_game_performances as base


PROJECT = "preseason-performances"
SEASON_TYPE = "Pre Season"
FIRST_END_YEAR = 2006
TOP_N = 15
TABLE_LAYOUT = base.FIFTEEN_ROW_LAYOUT
DATA_DIR = base._REPO / "docs" / "visuals" / "2026-10-03-preseason-performances" / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
# NBA.com serves a silhouette for Nate Robinson; this cut-out is copied from the 2026-09-16
# most-points-in-a-half post (the 2026-08-20 height ladder holds the original source).
PORTRAITS = {101126: DATA_DIR / "portraits" / "101126.png"}
SOURCE_URL = (
    "https://www.nba.com/stats/players/boxscores"
    "?Season={season}&SeasonType=Pre%20Season&TeamID=1610612741"
)


def _fetch_league_log(end_year: int, kind: str, refresh: bool) -> pd.DataFrame:
    """Load the Bulls rows of one season's preseason LeagueGameLog (kind P or T)."""
    path = RAW_DATA_DIR / f"CHI-{'players' if kind == 'P' else 'team'}-preseason-{end_year}.csv"
    if path.exists() and not refresh:
        return pd.read_csv(path, dtype={"GAME_ID": str})
    season = base.season_label(end_year)
    frame = base._request_frame(
        lambda: leaguegamelog.LeagueGameLog(
            season=season,
            season_type_all_star=SEASON_TYPE,
            player_or_team_abbreviation=kind,
            headers=_NBA_HEADERS,
            timeout=60,
        ),
        f"preseason {kind} log for {season}",
    )
    # The response is league-wide; keep the Bulls rows, in NBA.com's own columns.
    frame = frame[frame["TEAM_ABBREVIATION"].eq("CHI")].copy()
    if frame.empty:
        raise ValueError(f"NBA.com returned no Bulls preseason games for {season}.")
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, index=False)
    return frame


def player_games(raw: pd.DataFrame, end_year: int) -> pd.DataFrame:
    """Shape LeagueGameLog player rows into the shared player-game schema."""
    base._require_columns(raw, set(base.PLAYER_COLUMNS), "preseason player games")
    result = raw[list(base.PLAYER_COLUMNS)].rename(columns=base.PLAYER_COLUMNS).copy()
    result["game_id"] = result["game_id"].astype(str).str.zfill(10)
    result["game_date"] = result["game_date"].astype(str).str.slice(0, 10)
    numeric = [column for column in base.PLAYER_COLUMNS.values()
               if column not in {"player", "game_id", "game_date", "matchup", "result"}]
    for column in numeric:
        result[column] = pd.to_numeric(result[column], errors="raise")
    result["player_id"] = result["player_id"].astype(int)
    result["season_end_year"] = end_year
    result["season"] = base.display_season_label(end_year)
    result["opponent"] = result["matchup"].map(base._opponent)
    result["game_score"] = result.apply(base.game_score, axis=1)
    result["ts_pct"] = result.apply(base.true_shooting_pct, axis=1)
    result["player_source_url"] = SOURCE_URL.format(season=base.season_label(end_year))
    return result


def team_games(raw: pd.DataFrame, end_year: int) -> pd.DataFrame:
    """Shape LeagueGameLog team rows into the shared team-game schema."""
    base._require_columns(raw, {"GAME_ID", "GAME_DATE", "MATCHUP", "WL", "PTS", "PLUS_MINUS"},
                          "preseason team games")
    result = raw[["GAME_ID", "GAME_DATE", "MATCHUP", "WL", "PTS", "PLUS_MINUS"]].rename(
        columns={"GAME_ID": "game_id", "GAME_DATE": "game_date", "MATCHUP": "matchup",
                 "WL": "result", "PTS": "team_points", "PLUS_MINUS": "team_plus_minus"}
    ).copy()
    result["game_id"] = result["game_id"].astype(str).str.zfill(10)
    result["game_date"] = result["game_date"].astype(str).str.slice(0, 10)
    result["team_points"] = pd.to_numeric(result["team_points"], errors="raise").astype(int)
    result["team_plus_minus"] = pd.to_numeric(result["team_plus_minus"], errors="raise").astype("Int64")
    result["season_end_year"] = end_year
    result["team_source_url"] = SOURCE_URL.format(season=base.season_label(end_year))
    return result


def _fetch_unnamed_players(end_year: int, refresh: bool) -> pd.DataFrame:
    """Load Bulls preseason rows that NBA.com logs without a player name.

    LeagueGameLog drops them; PlayerGameLogs keeps them. In 2007-08 one such row (player ID
    201243, 5 points in 4 minutes at home to Dallas) is needed for the Bulls' 100 to reconcile.
    """
    path = RAW_DATA_DIR / f"CHI-unnamed-players-preseason-{end_year}.csv"
    if path.exists() and not refresh:
        return pd.read_csv(path, dtype={"GAME_ID": str})
    frame = base._request_frame(
        lambda: base.playergamelogs.PlayerGameLogs(
            season_nullable=base.season_label(end_year),
            season_type_nullable=SEASON_TYPE,
            team_id_nullable=str(base.BULLS_TEAM_ID),
            headers=_NBA_HEADERS,
            timeout=60,
        ),
        f"preseason player game logs for {base.season_label(end_year)}",
    )
    frame = frame[frame["PLAYER_NAME"].isna()].copy()
    frame["PLAYER_NAME"] = "Unnamed in NBA.com (ID " + frame["PLAYER_ID"].astype(str) + ")"
    frame.to_csv(path, index=False)
    return frame


UNNAMED_PLAYER_SEASONS = (2008,)
# 2005-10-17 vs MIN went four quarters (line score 12-21-30-26) but NBA.com logs 220 Bulls and
# 235 Wolves minutes. Points reconcile, so only the minute-budget check skips it.
SHORT_MINUTE_GAMES = {"0010500044"}


def fetch_preseasons(refresh: bool) -> tuple[pd.DataFrame, pd.DataFrame]:
    players, teams = [], []
    for end_year in range(FIRST_END_YEAR, base.LAST_SEASON_END_YEAR + 1):
        print(f"Loading {base.display_season_label(end_year)} preseason")
        raw = _fetch_league_log(end_year, "P", refresh)
        if end_year in UNNAMED_PLAYER_SEASONS:
            raw = pd.concat([raw, _fetch_unnamed_players(end_year, refresh)], ignore_index=True)
        players.append(player_games(raw, end_year))
        teams.append(team_games(_fetch_league_log(end_year, "T", refresh), end_year))
    players = pd.concat(players, ignore_index=True)
    teams = pd.concat(teams, ignore_index=True)
    # NBA.com leaves W/L blank on the player rows of one game (2017-10-03 at NOP, a 113-109
    # Bulls win). Fill only blanks from the team record; a conflicting value still fails.
    blank = players["result"].isna()
    players.loc[blank, "result"] = players.loc[blank, "game_id"].map(
        teams.set_index("game_id")["result"]
    )
    print(f"Filled blank W/L from the team record for games: {sorted(players.loc[blank, 'game_id'].unique())}")
    return players, teams


def rank_preseason(rows: pd.DataFrame, top_n: int = TOP_N) -> pd.DataFrame:
    """Rank preseason player-games using the settled deterministic tie-breaks."""
    # Game Score inputs are whole stats times one-decimal weights, so rounding to 0.1 is exact and
    # stops float noise (23.800000000000004 vs 23.8) from overriding the points tiebreak.
    ranked = rows.assign(score_key=rows["game_score"].round(1)).sort_values(
        ["score_key", "points", "ts_pct", "game_date", "player", "player_id"],
        ascending=[False, False, False, True, True, True],
        kind="stable",
    ).head(top_n).drop(columns="score_key").copy()
    if len(ranked) != top_n:
        raise ValueError(f"Expected {top_n} ranked preseason performances; got {len(ranked)}.")
    ranked["rank"] = range(1, len(ranked) + 1)
    return ranked.reset_index(drop=True)


def validate_preseason(
    teams: pd.DataFrame,
    played: pd.DataFrame,
    ranked: pd.DataFrame,
) -> dict[str, object]:
    """Check coverage and preserve the factual claims used in the mock."""
    expected_years = set(range(FIRST_END_YEAR, base.LAST_SEASON_END_YEAR + 1))
    if set(teams["season_end_year"].astype(int)) != expected_years:
        raise ValueError("Preseason source does not cover every season since 2005-06.")
    if set(played["game_id"]) != set(teams["game_id"]):
        raise ValueError("Every Bulls preseason game must have player box-score rows.")
    box_fields = ["minutes", "points", "fgm", "fga", "ftm", "fta", "oreb", "dreb", "ast",
                  "stl", "blk", "tov", "pf"]
    if played[box_fields].isna().any().any():
        raise ValueError("A preseason player-game is missing a Game Score input.")
    if played["minutes"].eq(5).all():
        raise ValueError("Minutes look like NBA.com's five-minute placeholder.")
    per_game = played.groupby("game_id").agg(player_points=("points", "sum"),
                                             team_points=("team_points", "first"))
    if not per_game["player_points"].eq(per_game["team_points"]).all():
        raise ValueError("Preseason player points do not reconcile to the Bulls team score.")
    minutes = base.minute_reconciliation(played[~played["game_id"].isin(SHORT_MINUTE_GAMES)])
    if len(ranked) != TOP_N or ranked.duplicated(["game_id", "player_id"]).any():
        raise ValueError("The ranking must hold fifteen distinct player-games.")
    return {
        "season_count": len(expected_years),
        "team_game_count": teams["game_id"].nunique(),
        "player_game_count": len(played),
        "overtime_games": int((minutes["overtime_periods"] > 0).sum()),
        "games_per_season": teams.groupby("season_end_year")["game_id"].nunique().to_dict(),
        "top_score": round(float(ranked.iloc[0]["game_score"]), 1),
        "cutoff_score": round(float(ranked.iloc[-1]["game_score"]), 1),
        "next_score": round(float(played.sort_values("game_score", ascending=False)
                                  .iloc[TOP_N]["game_score"]), 1),
        "player_count": ranked["player"].nunique(),
    }


def write_data(teams: pd.DataFrame, played: pd.DataFrame, ranked: pd.DataFrame) -> None:
    """Ship the selection and display tables beside the raw NBA.com rows."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    teams.to_csv(DATA_DIR / "preseason_team_games.csv", index=False)
    played.to_csv(DATA_DIR / "preseason_player_games.csv", index=False)
    ranked.to_csv(DATA_DIR / "top_15_preseason_performances.csv", index=False)


def canva_copy(report: dict[str, object]) -> str:
    """Print the exact framing tied to this analysis run."""
    return "\n".join(
        [
            "CANVA COPY",
            "TITLE: THE BULLS' BEST PRESEASON GAMES",
            "SUBTITLE: Top 15 individual performances since 2005-06, ranked by Game Score",
            "FOOTER: Data via nba.com | 2005-06 to 2025-26 preseasons",
            (
                "NOTE: Game Score measures box-score productivity. "
                "FG and 3PT show makes-attempts; TOV is turnovers."
            ),
            (
                f"AUDIT: {report['player_game_count']} player-games across "
                f"{report['team_game_count']} preseason games; top-fifteen cutoff "
                f"{report['cutoff_score']:.1f}, next {report['next_score']:.1f}."
            ),
        ]
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the Bulls preseason performance table.")
    parser.add_argument("--refresh", action="store_true", help="Refetch NBA.com season responses.")
    parser.add_argument("--final", action="store_true", help="Render the chart at final resolution.")
    args = parser.parse_args()

    snapshot = datetime.now(base.SNAPSHOT_TZ)
    players, teams = fetch_preseasons(args.refresh)
    working = base.build_working_table(players, teams)
    played = working[working["minutes"] > 0].reset_index(drop=True)
    ranked = rank_preseason(played)
    report = validate_preseason(teams, played, ranked)
    write_data(teams, played, ranked)

    base.ensure_headshots(ranked["player_id"].tolist())
    base.ensure_historical_headshot_fallbacks(ranked["player_id"].tolist())
    chart = base.render_chart(
        ranked,
        snapshot.date().isoformat(),
        decade="preseason",
        season_type=SEASON_TYPE,
        show_free_throws=False,
        show_turnovers=True,
        top_n=TOP_N,
        layout=TABLE_LAYOUT,
        final=args.final,
        emphasize_points=True,
        shooting_after_assists=True,
        # Every row sits in the 20+ band, so the default red card replaces the band colors.
        # Matches the season-opener table this post pairs with.
        show_plus_minus=False,
        portraits=PORTRAITS,
        made_attempted_dash="-",
        true_shooting=True,
        # Preseason playing time varies widely, so minutes give each line its context.
        show_minutes=True,
    )
    print(f"Chart: {chart}")
    print(f"Data: {DATA_DIR}")
    print(canva_copy(report))
    print(f"Games per season: {report['games_per_season']}")
    print()
    print(
        ranked[
            ["rank", "player", "season", "game_date", "matchup", "result", "minutes",
             "points", "game_score", "ts_pct"]
        ].to_string(index=False)
    )


if __name__ == "__main__":
    main()
