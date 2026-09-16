"""Prepare Bulls player-season drive leaderboards from NBA tracking.

The three selections answer distinct questions: total drive volume, points scored
from drives, and assists created from drives. Raw league-player and team responses
are retained because NBA's server-side historical team filter is not stable.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
from nba_api.stats.endpoints import leaguedashptstats

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from bulls.data.fetch import _NBA_HEADERS

DATA = ROOT / "docs/visuals/2026-09-15-drive-leaders/data"
BULLS = 1610612741
SEASONS = [f"{year}-{str(year + 1)[-2:]}" for year in range(2013, 2026)]
COUNT_COLUMNS = [
    "DRIVES", "DRIVE_FGM", "DRIVE_FGA", "DRIVE_FTM", "DRIVE_FTA",
    "DRIVE_PTS", "DRIVE_PASSES", "DRIVE_AST", "DRIVE_TOV", "DRIVE_PF",
]


def fetch(kind: str, season: str, refresh: bool = False) -> pd.DataFrame:
    path = DATA / "raw" / f"{kind}_{season}.json"
    if refresh or not path.exists():
        params = dict(
            season=season,
            season_type_all_star="Regular Season",
            player_or_team="Player" if kind == "players" else "Team",
            pt_measure_type="Drives",
            per_mode_simple="Totals",
        )
        response = leaguedashptstats.LeagueDashPtStats(
            **params, headers=_NBA_HEADERS, timeout=60
        )
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({
            "endpoint": "LeagueDashPtStats",
            "parameters": params,
            "retrieved_at": datetime.now(timezone.utc).isoformat(),
            "response": response.get_dict(),
        }, ensure_ascii=False))
        time.sleep(.5)
    payload = json.loads(path.read_text())
    result = payload["response"]["resultSets"][0]
    frame = pd.DataFrame(result["rowSet"], columns=result["headers"])
    if frame.empty:
        raise ValueError(f"Missing {kind} tracking data for {season}")
    return frame


def validate_rows(frame: pd.DataFrame) -> pd.DataFrame:
    required = ["PLAYER_ID", "PLAYER_NAME", "TEAM_ID", "GP", *COUNT_COLUMNS]
    missing = [column for column in required if column not in frame]
    if missing:
        raise ValueError(f"Missing drive columns: {', '.join(missing)}")
    if frame[required].isna().any().any():
        raise ValueError("Selected tracking rows contain missing values")
    out = frame.copy()
    # NBA does not expose drive 3PM. Keep the arithmetic difference as an audit
    # only: historical rows can even be negative, so it is not a valid 3PM field.
    out["DRIVE_POINTS_RESIDUAL"] = (
        out.DRIVE_PTS - 2 * out.DRIVE_FGM - out.DRIVE_FTM
    )
    return out


def prepare_season(players: pd.DataFrame, teams: pd.DataFrame, season: str) -> tuple[pd.DataFrame, dict]:
    # The league-wide response carries the displayed team identity. Historical
    # TeamID-filtered requests have returned internally mixed seasons/stints.
    bulls = players.loc[players.TEAM_ID == BULLS].copy()
    if bulls.empty or bulls.PLAYER_ID.duplicated().any():
        raise ValueError(f"Invalid Chicago player rows for {season}")
    bulls = validate_rows(bulls)
    team = teams.loc[teams.TEAM_ID == BULLS]
    if len(team) != 1:
        raise ValueError(f"Missing Chicago team row for {season}")
    team = team.iloc[0]
    bulls["season"] = season
    bulls["player_id"] = bulls.PLAYER_ID.astype(int)
    bulls["player_name"] = bulls.PLAYER_NAME.replace({"Jimmy Butler III": "Jimmy Butler"})
    bulls["gp"] = bulls.GP.astype(int)
    bulls["drives"] = bulls.DRIVES.astype(int)
    bulls["drives_per_game"] = bulls.drives / bulls.gp
    bulls["drive_fgm"] = bulls.DRIVE_FGM.astype(int)
    bulls["drive_fga"] = bulls.DRIVE_FGA.astype(int)
    bulls["drive_fg_pct"] = 100 * bulls.DRIVE_FG_PCT
    bulls["drive_shot_pct"] = 100 * bulls.drive_fga / bulls.drives
    bulls["drive_ftm"] = bulls.DRIVE_FTM.astype(int)
    bulls["drive_fta"] = bulls.DRIVE_FTA.astype(int)
    bulls["drive_pts"] = bulls.DRIVE_PTS.astype(int)
    bulls["drive_points_residual"] = bulls.DRIVE_POINTS_RESIDUAL.astype(int)
    bulls["drive_passes"] = bulls.DRIVE_PASSES.astype(int)
    bulls["drive_pass_pct"] = 100 * bulls.DRIVE_PASSES_PCT
    bulls["drive_ast"] = bulls.DRIVE_AST.astype(int)
    bulls["drive_ast_pct"] = 100 * bulls.DRIVE_AST_PCT
    bulls["drive_ast_per_drive"] = bulls.drive_ast / bulls.drives
    bulls["drive_pf"] = bulls.DRIVE_PF.astype(int)
    bulls["drive_pf_pct"] = 100 * bulls.DRIVE_PF_PCT
    columns = [
        "season", "player_id", "player_name", "gp", "drives", "drives_per_game",
        "drive_fgm", "drive_fga", "drive_fg_pct", "drive_shot_pct", "drive_ftm", "drive_fta",
        "drive_points_residual", "drive_pts", "drive_passes", "drive_pass_pct",
        "drive_ast", "drive_ast_pct", "drive_ast_per_drive", "drive_pf",
        "drive_pf_pct",
    ]
    audit = {"season": season, "player_rows": len(bulls)}
    for column in COUNT_COLUMNS:
        audit[f"player_minus_team_{column.lower()}"] = int(bulls[column].sum() - team[column])
    audit["drive_points_residual"] = int(bulls.DRIVE_POINTS_RESIDUAL.sum())
    audit["negative_player_residuals"] = int((bulls.DRIVE_POINTS_RESIDUAL < 0).sum())
    return bulls[columns], audit


def ranked(frame: pd.DataFrame, metric: str) -> pd.DataFrame:
    out = frame.sort_values(
        [metric, "drives", "season", "player_id"],
        ascending=[False, False, True, True], kind="stable",
    ).head(15).copy()
    out.insert(0, "rank", range(1, len(out) + 1))
    return out


def main(refresh: bool = False) -> None:
    DATA.mkdir(parents=True, exist_ok=True)
    frames, audits = [], []
    for season in SEASONS:
        frame, audit = prepare_season(
            fetch("players", season, refresh), fetch("teams", season, refresh), season
        )
        frames.append(frame)
        audits.append(audit)
        print(f"{season}: {len(frame)} Chicago rows; team differences retained", flush=True)
    all_rows = pd.concat(frames, ignore_index=True)
    outputs = {
        "all_player_seasons": all_rows,
        "top15_drives": ranked(all_rows, "drives"),
        "top15_drive_points": ranked(all_rows, "drive_pts"),
        "top15_drive_assists": ranked(all_rows, "drive_ast"),
        "season_audit": pd.DataFrame(audits),
    }
    for name, frame in outputs.items():
        frame.to_csv(DATA / f"{name}.csv", index=False)
    copy = {
        "title": "Bulls driving leaders",
        "scope": "2013–14 to 2025–26 regular season · Chicago games only",
        "source": "Source: NBA.com · Second Spectrum player tracking",
        "handle": "@chicagobullsdata",
        "slides": [
            {"title": "Most drives", "subtitle": "Top 15 Bulls seasons by total drives; shot and pass rates show how drives ended"},
            {"title": "Most points from drives", "subtitle": "Top 15 Bulls seasons by drive points"},
            {"title": "Most assists from drives", "subtitle": "Top 15 Bulls seasons by drive assists; AST% is the percentage of drives that produced an assist"},
        ],
        "definition": "A drive attacks the basket off the dribble in half-court offense.",
        "points_note": "Drive points are NBA's reported points scored on drives. They do not consistently reconcile to 2×FGM + FTM, and drive 3PM is unavailable.",
        "coverage_note": "NBA notes that player tracking is not available for every game.",
    }
    (DATA / "canva_copy.json").write_text(json.dumps(copy, indent=2, ensure_ascii=False))
    (DATA / "source.json").write_text(json.dumps({
        "endpoint": "LeagueDashPtStats",
        "measure": "Drives",
        "player_source": "league-wide player response filtered to TEAM_ID 1610612741",
        "season_type": "Regular Season",
        "seasons": SEASONS,
        "retrieved_at": datetime.now(timezone.utc).isoformat(),
        "row_grain": "one player-team-season aggregate",
        "limitations": [
            "No event rows, coordinates, drive direction, or shot linkage.",
            "Drive 3PM is unavailable; DRIVE_PTS is retained as reported because historical component arithmetic does not always reconcile.",
            "Tracking may be unavailable for some games.",
            "Player sums can differ from team totals, especially around team stints; differences are retained in season_audit.csv.",
        ],
    }, indent=2))
    print_columns = {
        "top15_drives": "drives",
        "top15_drive_points": "drive_pts",
        "top15_drive_assists": "drive_ast",
    }
    for name, metric in print_columns.items():
        print(f"\n{name}\n", outputs[name][
            ["rank", "player_name", "season", metric]
        ].to_string(index=False))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--refresh", action="store_true")
    main(parser.parse_args().refresh)
