"""Prepare Bulls leaderboards for most points in a half and in a quarter.

NBA.com's PlayerGameLogs endpoint accepts ``GameSegment`` (First Half, Second
Half, Overtime) and ``Period`` (1-4) filters. One Bulls-filtered response per
season, season type and split is cached under the post's ``data/raw``.

Split coverage starts in 1996-97, which is where this post starts. For 1995-96 and earlier the endpoint silently
ignores the split filter and returns full-game rows, so every season must pass
``reconcile``: quarters sum to halves, halves plus overtime sum to the full
game, and no split row equals the full game unless the player scored nothing
elsewhere. A player absent from a split response logged no minutes in it and
is counted as zero only after that reconciliation holds.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
from nba_api.stats.endpoints import playergamelogs

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from bulls.data.fetch import _NBA_HEADERS

DATA = ROOT / "docs/visuals/2026-09-16-most-points-in-a-half/data"
BULLS = 1610612741
TOP_N = 10
MAX_ROWS = 15  # a tie that would push a slide past this stops the slide above the tie
# Split filters work from 1996-97, the first season with period-level data.
SEASONS = [f"{year}-{str(year + 1)[-2:]}" for year in range(1996, 2026)]
SEASON_TYPES = {"Regular Season": "rs", "Playoffs": "po", "PlayIn": "pi"}
SPLITS = {
    "full": {},
    "h1": {"game_segment_nullable": "First Half"},
    "h2": {"game_segment_nullable": "Second Half"},
    "ot": {"game_segment_nullable": "Overtime"},
    "q1": {"period_nullable": 1},
    "q2": {"period_nullable": 2},
    "q3": {"period_nullable": 3},
    "q4": {"period_nullable": 4},
}
STATS = ["PTS", "FGM", "FGA", "FG3M", "FG3A", "FTM", "FTA", "MIN"]
# One single-slide post each: any regulation quarter, any half. Each board names the
# season types it ranks; the quarter post was published without play-in (none qualified).
BOARDS = {
    "quarter": (["q1", "q2", "q3", "q4"], ["Regular Season", "Playoffs"]),
    "half": (["h1", "h2"], ["Regular Season", "Playoffs", "PlayIn"]),
}
DISPLAY_NAME_FIXES = {"Jimmy Butler III": "Jimmy Butler"}


def fetch(season: str, season_type: str, split: str, refresh: bool = False) -> pd.DataFrame:
    path = DATA / "raw" / f"{SEASON_TYPES[season_type]}_{season}_{split}.json"
    if refresh or not path.exists():
        params = dict(season_nullable=season, season_type_nullable=season_type,
                      team_id_nullable=BULLS, **SPLITS[split])
        for attempt in range(3):
            try:
                response = playergamelogs.PlayerGameLogs(
                    **params, headers=_NBA_HEADERS, timeout=60)
                break
            except Exception:
                if attempt == 2:
                    raise
                time.sleep(5 * (attempt + 1))
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({
            "endpoint": "PlayerGameLogs",
            "parameters": params,
            "retrieved_at": datetime.now(timezone.utc).isoformat(),
            "response": response.get_dict(),
        }, ensure_ascii=False))
        time.sleep(.6)
    result = json.loads(path.read_text())["response"]["resultSets"][0]
    return pd.DataFrame(result["rowSet"], columns=result["headers"])


def player_games(season: str, season_type: str) -> pd.DataFrame:
    """One row per Bulls player-game with full, half, overtime and quarter stats."""
    full = fetch(season, season_type, "full")
    if full.empty:
        return full
    keys = ["GAME_ID", "PLAYER_ID"]
    wide = full[keys + ["PLAYER_NAME", "GAME_DATE", "MATCHUP", "WL"] + STATS].copy()
    for split in SPLITS:
        if split == "full":
            continue
        part = fetch(season, season_type, split)
        if not part.empty and not part.set_index(keys).index.isin(wide.set_index(keys).index).all():
            raise ValueError(f"{season} {season_type} {split}: rows missing from full game logs")
        part = part[keys + STATS].rename(columns={c: f"{split}_{c}" for c in STATS}) if not part.empty \
            else pd.DataFrame(columns=keys + [f"{split}_{c}" for c in STATS])
        wide = wide.merge(part, on=keys, how="left")
        wide[f"{split}_played"] = wide[f"{split}_PTS"].notna()
        wide[[f"{split}_{c}" for c in STATS]] = wide[[f"{split}_{c}" for c in STATS]].fillna(0)
    wide.insert(0, "season_type", season_type)
    wide.insert(0, "season", season)
    return wide


def reconcile(wide: pd.DataFrame) -> pd.DataFrame:
    """Raise on any counting-stat mismatch; return a per-season audit."""
    for stat in ["PTS", "FGM", "FGA", "FG3M", "FG3A", "FTM", "FTA"]:
        checks = {
            "q1+q2=h1": wide[f"q1_{stat}"] + wide[f"q2_{stat}"] - wide[f"h1_{stat}"],
            "q3+q4=h2": wide[f"q3_{stat}"] + wide[f"q4_{stat}"] - wide[f"h2_{stat}"],
            "h1+h2+ot=full": wide[f"h1_{stat}"] + wide[f"h2_{stat}"] + wide[f"ot_{stat}"] - wide[stat],
        }
        for name, diff in checks.items():
            bad = wide[diff != 0]
            if len(bad):
                sample = bad[["season", "season_type", "PLAYER_NAME", "GAME_DATE"]].head(3).to_dict("records")
                raise ValueError(f"{stat} {name} fails on {len(bad)} rows, e.g. {sample}")
    return (wide.groupby(["season", "season_type"])
            .agg(games=("GAME_ID", "nunique"), player_games=("PLAYER_ID", "size"),
                 pts=("PTS", "sum"), h1_pts=("h1_PTS", "sum"), h2_pts=("h2_PTS", "sum"),
                 ot_pts=("ot_PTS", "sum"))
            .reset_index())


def leaderboard(wide: pd.DataFrame, splits: list[str], label: dict[str, str]) -> pd.DataFrame:
    """Top TOP_N by points plus every row tied with TOP_N-th place, unless that tie
    would exceed MAX_ROWS; then the board stops above the tied group (fewer than TOP_N rows).

    Tied rows share a rank (shown as T-n). Within a tie, rows are ordered by fewer
    field-goal attempts, then the earlier game; that order is display only.
    """
    frames = []
    for split in splits:
        part = wide[wide[f"{split}_played"]].copy()
        part["split"] = split
        part["split_label"] = label[split]
        for stat in STATS:
            part[stat.lower()] = part[f"{split}_{stat}"]
        part["game_pts"] = part["PTS"]
        frames.append(part)
    rows = pd.concat(frames, ignore_index=True)
    rows = rows.sort_values(["pts", "fga", "GAME_DATE"], ascending=[False, True, True], kind="stable")
    cutoff = rows["pts"].iloc[TOP_N - 1]
    top = rows[rows["pts"] >= cutoff].copy()
    if len(top) > MAX_ROWS:
        top = rows[rows["pts"] > cutoff].copy()
    top["rank"] = top["pts"].rank(method="min", ascending=False).astype(int)
    top["tied"] = top["pts"].duplicated(keep=False)
    top["player_name"] = top.PLAYER_NAME.replace(DISPLAY_NAME_FIXES)
    top["game_date"] = pd.to_datetime(top.GAME_DATE).dt.date.astype(str)
    top["opponent"] = top.MATCHUP.str.split(" ").str[-1]
    top["home"] = top.MATCHUP.str.contains("vs.")
    return top[["rank", "tied", "PLAYER_ID", "player_name", "season", "season_type", "game_date",
                "MATCHUP", "opponent", "home", "WL", "split", "split_label", "pts", "fgm",
                "fga", "fg3m", "fg3a", "ftm", "fta", "min", "game_pts", "GAME_ID"]] \
        .rename(columns={"PLAYER_ID": "player_id", "MATCHUP": "matchup", "WL": "result",
                         "GAME_ID": "game_id"})


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--refresh", action="store_true")
    args = parser.parse_args()
    frames = []
    for season_type in SEASON_TYPES:
        for season in SEASONS:
            if args.refresh:
                for split in SPLITS:
                    fetch(season, season_type, split, refresh=True)
            frames.append(player_games(season, season_type))
            print(season_type, season, flush=True)
    wide = pd.concat([f for f in frames if not f.empty], ignore_index=True)
    audit = reconcile(wide)
    audit.to_csv(DATA / "season_audit.csv", index=False)
    wide.to_csv(DATA / "player_games.csv", index=False)
    labels = {"h1": "1H", "h2": "2H", "q1": "1Q", "q2": "2Q", "q3": "3Q", "q4": "4Q"}
    # Season types are ranked together; the renderer marks non-regular-season rows.
    for board, (splits, season_types) in BOARDS.items():
        pool = wide[wide.season_type.isin(season_types)]
        leaderboard(pool, splits, labels).to_csv(DATA / f"top_{board}.csv", index=False)
    print(f"{len(wide):,} player-games reconciled across {audit.games.sum():,} team games")


if __name__ == "__main__":
    main()
