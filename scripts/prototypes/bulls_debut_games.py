"""Build the top fifteen first games as a Bull since 1983-84, ranked by Game Score.

The top-game-performances prototype owns NBA.com collection, Hollinger Game
Score, reconciliation and the settled table renderer. This prototype adds the
debut rule: a player's earliest logged Bulls regular-season game must be his
first Bulls game ever. Only a player's first logged Bulls game is considered, so returns
(Jordan 1994-95, Pippen 2003-04) never count, and players who entered the NBA
before 1983-84 (the first season with a Bulls team game log and complete box
scores) are checked for an earlier Bulls stint against career team history.
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd
from nba_api.stats.endpoints import commonallplayers, playercareerstats

_REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO))

from bulls.config import BULLS_TEAM_ID
from bulls.data.fetch import _NBA_HEADERS
from bulls.graphics.house import cut_out_flat_background
from scripts.prototypes import top_game_performances as base
from scripts.prototypes.season_opener_performances import TABLE_LAYOUT


PROJECT = "bulls-debut-games"
FIRST_END_YEAR = 1984
TOP_N = 15
DATA_DIR = _REPO / "docs" / "visuals" / "2026-09-25-bulls-debut-games" / "data"
CAREER_PATH = DATA_DIR / "career_team_seasons.csv"
FIRST_SEASONS_PATH = DATA_DIR / "nba_common_all_players.csv"
# The NBA CDN serves a silhouette for these four. The user supplied cropped portraits
# (2026-09-25) on flat white; data/portraits_source keeps them unchanged.
PORTRAIT_SOURCES = {
    78523: "Mitchell Wiggins.png",
    966: "Jerome Williams.png",
    2648: "Ronald Dupree.png",
    1594: "Rick Brunson.png",
}
GAME_SCORE_INPUTS = ["minutes", "points", "fgm", "fga", "ftm", "fta", "oreb", "dreb",
                     "ast", "stl", "blk", "tov", "pf"]


def season_end_year(season_id: str) -> int:
    """Map NBA.com's '2001-02' season id to its ending year."""
    return int(str(season_id)[:4]) + 1


def fetch_first_seasons(refresh: bool = False) -> pd.DataFrame:
    """NBA.com's all-time player list with each player's first season (FROM_YEAR = start year)."""
    if FIRST_SEASONS_PATH.exists() and not refresh:
        return pd.read_csv(FIRST_SEASONS_PATH)
    frame = base._request_frame(
        lambda: commonallplayers.CommonAllPlayers(
            is_only_current_season=0, headers=_NBA_HEADERS, timeout=60
        ),
        "CommonAllPlayers",
    )[["PERSON_ID", "DISPLAY_FIRST_LAST", "FROM_YEAR", "TO_YEAR"]]
    frame["captured_at"] = datetime.now(base.SNAPSHOT_TZ).isoformat(timespec="seconds")
    FIRST_SEASONS_PATH.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(FIRST_SEASONS_PATH, index=False)
    return frame


def _career_request(player_id: int):
    """One career request; NBA.com's occasional error body surfaces as a retryable ValueError."""
    try:
        return playercareerstats.PlayerCareerStats(
            player_id=player_id, per_mode36="Totals", headers=_NBA_HEADERS, timeout=60
        )
    except KeyError as exc:
        raise ValueError(f"NBA.com returned an error body ({exc}).") from exc


def fetch_career_seasons(player_ids: list[int], refresh: bool = False) -> pd.DataFrame:
    """Load each player's regular-season team history, fetching only missing players."""
    cached = pd.read_csv(CAREER_PATH) if CAREER_PATH.exists() and not refresh else pd.DataFrame()
    wanted = set(int(p) for p in player_ids)
    if len(cached):
        cached = cached[cached["PLAYER_ID"].astype(int).isin(wanted)]
    have = set(cached["PLAYER_ID"].astype(int)) if len(cached) else set()
    frames = [cached] if len(cached) else []
    missing = sorted(wanted - have)
    for index, player_id in enumerate(missing, 1):
        print(f"Career history {index}/{len(missing)}: {player_id}")
        frame = base._request_frame(
            lambda: _career_request(player_id),
            f"PlayerCareerStats {player_id}",
        )
        if frame.empty:
            raise ValueError(f"NBA.com returned no career rows for player {player_id}.")
        frame["captured_at"] = datetime.now(base.SNAPSHOT_TZ).isoformat(timespec="seconds")
        frames.append(frame)
        # Save as we go so an interrupted run resumes instead of refetching.
        CAREER_PATH.parent.mkdir(parents=True, exist_ok=True)
        pd.concat(frames, ignore_index=True).to_csv(CAREER_PATH, index=False)
    result = pd.concat(frames, ignore_index=True)
    result.to_csv(CAREER_PATH, index=False)
    return result


def first_bulls_games(working: pd.DataFrame) -> pd.DataFrame:
    """Each player's earliest logged Bulls regular-season game with minutes played."""
    played = working[working["minutes"] > 0].copy()
    played["game_date_parsed"] = pd.to_datetime(played["game_date"], errors="raise")
    first = played.sort_values(["game_date_parsed", "game_id"], kind="stable")
    first = first.groupby("player_id", sort=False).head(1)
    return first.drop(columns="game_date_parsed").reset_index(drop=True)


def attach_first_nba_season(first: pd.DataFrame, first_seasons: pd.DataFrame) -> pd.DataFrame:
    """Add each player's first NBA season (ending year) from CommonAllPlayers."""
    seasons = first_seasons[["PERSON_ID", "FROM_YEAR"]].rename(columns={"PERSON_ID": "player_id"})
    audit = first.merge(seasons, on="player_id", how="left", validate="one_to_one")
    if audit["FROM_YEAR"].isna().any():
        names = audit.loc[audit["FROM_YEAR"].isna(), "player"].tolist()
        raise ValueError(f"CommonAllPlayers has no first season for {names}.")
    audit["first_nba_season_end"] = audit.pop("FROM_YEAR").astype(int) + 1
    return audit


def needs_career_check(audit: pd.DataFrame) -> pd.Series:
    """Only players who entered the NBA before the game logs begin could have an unlogged Bulls stint."""
    return audit["first_nba_season_end"] < FIRST_END_YEAR


def classify_debuts(audit: pd.DataFrame, career: pd.DataFrame) -> pd.DataFrame:
    """Mark each first logged Bulls game as a true Bulls debut or a pre-window stint.

    The Bulls game logs are complete from 1983-84, so for anyone whose NBA career began
    then or later the first logged Bulls game is the first Bulls game. Earlier entrants
    are checked against NBA.com's career team history.
    """
    audit = audit.copy()
    seasons = career[["PLAYER_ID", "SEASON_ID", "TEAM_ID"]].copy()
    seasons["end_year"] = seasons["SEASON_ID"].map(season_end_year)
    chicago = seasons[seasons["TEAM_ID"].eq(BULLS_TEAM_ID)]
    first_chi = chicago.groupby("PLAYER_ID")["end_year"].min()
    checked = needs_career_check(audit)
    audit["first_bulls_season_end"] = audit["season_end_year"].where(
        ~checked, audit["player_id"].map(first_chi)
    )
    if audit.loc[checked, "first_bulls_season_end"].isna().any():
        names = audit.loc[checked & audit["first_bulls_season_end"].isna(), "player"].tolist()
        raise ValueError(f"Career history has no Chicago season for {names}.")
    if (audit["first_bulls_season_end"] > audit["season_end_year"]).any():
        raise ValueError("A logged Bulls game precedes the player's first career Chicago season.")
    audit["first_bulls_season_end"] = audit["first_bulls_season_end"].astype(int)
    audit["debut_rule"] = checked.map({True: "career team history", False: "entered NBA 1983-84 or later"})
    audit["is_debut"] = audit["first_bulls_season_end"].eq(audit["season_end_year"])
    audit["rookie_season"] = audit["first_nba_season_end"].eq(audit["season_end_year"])
    audit["status"] = [
        "debut" if debut else f"earlier Bulls stint (first Bulls season ended {year})"
        for debut, year in zip(audit["is_debut"], audit["first_bulls_season_end"])
    ]
    return audit


def game_score_upper_bound(row: pd.Series) -> float:
    """Best possible Game Score for a box score with blanks; missing is never read as zero.

    Blank rebound splits take the total as offensive (worth more), blank turnovers and fouls
    take zero. Any other blank makes the game unboundable.
    """
    filled = row.copy()
    if pd.isna(filled["oreb"]) or pd.isna(filled["dreb"]):
        known = filled["dreb"] if pd.notna(filled["dreb"]) else 0
        filled["oreb"] = filled["reb"] - known
        filled["dreb"] = known
    for field in ("tov", "pf"):
        if pd.isna(filled[field]):
            filled[field] = 0
    if filled[GAME_SCORE_INPUTS].isna().any():
        return float("inf")
    return base.game_score(filled)


def post_portraits() -> dict[int, Path]:
    """Cut the supplied portraits out of their white surround, framed like NBA headshots."""
    portraits = {}
    for player_id, name in PORTRAIT_SOURCES.items():
        portraits[player_id] = cut_out_flat_background(
            DATA_DIR / "portraits_source" / name, DATA_DIR / "portraits" / f"{player_id}.png"
        )
    return portraits


def rank_debuts(debuts: pd.DataFrame, top_n: int = TOP_N) -> pd.DataFrame:
    """Rank by displayed (one-decimal) Game Score, then points, then TS%.

    Ranking on the printed value keeps a visible tie ordered by the visible tiebreak.
    """
    keyed = debuts.assign(display_game_score=debuts["game_score"].round(1))
    ranked = keyed.sort_values(
        ["display_game_score", "points", "ts_pct", "game_date", "player", "player_id"],
        ascending=[False, False, False, True, True, True],
        kind="stable",
    ).head(top_n).drop(columns="display_game_score").copy()
    if len(ranked) != top_n:
        raise ValueError(f"Expected {top_n} ranked debuts; got {len(ranked)}.")
    ranked["rank"] = range(1, len(ranked) + 1)
    return ranked.reset_index(drop=True)


def validate(audit: pd.DataFrame, debuts: pd.DataFrame, ranked: pd.DataFrame,
             working: pd.DataFrame) -> dict[str, object]:
    """Check coverage and keep the numbers the Notion record and caption cite."""
    if audit["player_id"].duplicated().any():
        raise ValueError("A player has more than one first Bulls game.")
    incomplete = debuts[debuts[GAME_SCORE_INPUTS].isna().any(axis=1)]
    complete = debuts.drop(incomplete.index)
    games = working[working["game_id"].isin(ranked["game_id"])]
    per_game = games.groupby("game_id").agg(player_points=("points", "sum"),
                                            team_points=("team_points", "first"))
    if not per_game["player_points"].eq(per_game["team_points"]).all():
        raise ValueError("Ranked debut games do not reconcile to the Bulls team score.")
    cutoff = float(ranked.iloc[-1]["game_score"])
    bounds = incomplete.apply(game_score_upper_bound, axis=1)
    if (bounds >= cutoff).any():
        raise ValueError(f"An incomplete debut could reach the top fifteen: {incomplete['player'].tolist()}.")
    first_out = complete.sort_values("game_score", ascending=False).iloc[TOP_N]
    if round(float(first_out["game_score"]), 1) == round(cutoff, 1):
        raise ValueError("A displayed Game Score tie crosses the top-fifteen cutoff.")
    return {
        "players_logged": len(audit),
        "debut_count": len(debuts),
        "incomplete_debuts": [
            f"{row.player} {row.game_date} (best case {bound:.1f})"
            for row, bound in zip(incomplete.itertuples(), bounds)
        ],
        "earlier_stint_count": int((~audit["is_debut"]).sum()),
        "career_checked_count": int(audit["debut_rule"].eq("career team history").sum()),
        "rookie_debut_count": int(debuts["rookie_season"].sum()),
        "top_score": round(float(ranked.iloc[0]["game_score"]), 1),
        "cutoff_score": round(cutoff, 1),
        "first_out": f"{first_out['player']} {first_out['game_score']:.1f}",
    }


def canva_copy(report: dict[str, object]) -> str:
    return "\n".join([
        "CANVA COPY",
        "TITLE: BEST FIRST GAMES AS A BULL",
        "SUBTITLE: Top 15 Bulls debuts since 1983-84, ranked by Game Score",
        "FOOTER: Data via nba.com | 1983-84 to 2025-26 regular seasons | "
        "Each player's first regular-season game with the Bulls",
        "NOTE: Game Score measures box-score productivity. Only a player's first Bulls game counts; "
        "later returns do not. "
        "FG and 3PT show makes–attempts; TOV is turnovers.",
        f"AUDIT: {report['debut_count']} Bulls debuts; {report['earlier_stint_count']} players with a "
        f"pre-1983-84 Bulls stint excluded; cutoff {report['cutoff_score']:.1f}; "
        f"first out {report['first_out']}; incomplete box scores {report['incomplete_debuts']}.",
    ])


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the Bulls debut-game table.")
    parser.add_argument("--refresh", action="store_true", help="Refetch career histories.")
    parser.add_argument("--final", action="store_true", help="Render at final resolution.")
    args = parser.parse_args()

    snapshot = datetime.now(base.SNAPSHOT_TZ)
    players, teams = base.fetch_bulls_history(season_type="Regular Season",
                                              first_end_year=FIRST_END_YEAR)
    working = base.build_working_table(players, teams)
    first = attach_first_nba_season(first_bulls_games(working), fetch_first_seasons(args.refresh))
    early = first.loc[needs_career_check(first), "player_id"].tolist()
    audit = classify_debuts(first, fetch_career_seasons(early, refresh=args.refresh))
    debuts = audit[audit["is_debut"]].copy()
    # Box scores with blanks can't be scored; validate() proves none could reach the list.
    ranked = rank_debuts(debuts.dropna(subset=GAME_SCORE_INPUTS))
    report = validate(audit, debuts, ranked, working)

    audit.to_csv(DATA_DIR / "first_bulls_games_audit.csv", index=False)
    ranked.to_csv(DATA_DIR / "top_15_bulls_debuts.csv", index=False)

    base.ensure_headshots(ranked["player_id"].tolist())
    base.ensure_historical_headshot_fallbacks(ranked["player_id"].tolist())
    chart = base.render_chart(
        ranked, snapshot.date().isoformat(), decade="bulls-debuts",
        season_type="Regular Season", show_free_throws=False, show_turnovers=True,
        top_n=TOP_N, layout=TABLE_LAYOUT, final=args.final, emphasize_points=True,
        shooting_after_assists=True,
        # NBA.com has no plus/minus before 1996-97 (Earl Cureton's 1986 debut).
        show_plus_minus=False,
        portraits=post_portraits(),
    )
    print(f"Chart: {chart}")
    print(canva_copy(report))
    print(ranked[["rank", "player", "season", "game_date", "matchup", "result", "points",
                  "game_score", "rookie_season"]].to_string(index=False))


if __name__ == "__main__":
    main()
