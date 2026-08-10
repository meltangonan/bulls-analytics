#!/usr/bin/env python3
"""Build relative-FG% hex charts for qualified current Bulls players.

Roster membership is live and current. Shot data is each player's complete
2025-26 NBA regular season across all teams, which keeps traded players' full
season intact rather than mistaking a Bulls stint for the requested population.
"""
from __future__ import annotations

import argparse
from datetime import date
from pathlib import Path
import sys

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from bulls.config import CURRENT_SEASON
from bulls.data import shots as shot_data
from bulls.data.fetch import get_current_roster
from scripts import make_shot_chart as shot_chart


MIN_PLAYER_FGA = 250
PROJECT = "bulls-player-hex"


def player_slug(name: str) -> str:
    return name.lower().replace(" ", "-").replace(".", "")


def qualifies_player(fga: int, minimum: int = MIN_PLAYER_FGA) -> bool:
    """A player needs enough season volume for the spatial map to be readable."""
    return fga >= minimum


def canva_stats_row(subject: str, scope: str, shots: pd.DataFrame) -> dict[str, object]:
    """The four fields the user will recreate manually in Canva."""
    fga = len(shots)
    made = int(shots.shot_made.sum())
    threes = shots.shot_type.eq("3PT")
    three_made = int(shots.loc[threes, "shot_made"].sum())
    three_attempted = int(threes.sum())
    return {
        "subject": subject,
        "scope": scope,
        "fga": fga,
        "efg_pct": round((made + 0.5 * three_made) / fga * 100, 1),
        "three_pt_pct": round(three_made / three_attempted * 100, 1),
    }


def player_summary(name: str, nba_id: int, shots: pd.DataFrame,
                   mapped: pd.DataFrame, cells: pd.DataFrame,
                   minimum: int) -> dict[str, object]:
    fga = len(shots)
    displayed = cells.displayed
    displayed_fga = int(cells.loc[displayed, "exact_fga"].sum())
    made = int(shots.shot_made.sum()) if fga else 0
    threes = shots.shot_type.eq("3PT") if fga else pd.Series(dtype=bool)
    made_threes = int(shots.loc[threes, "shot_made"].sum()) if fga else 0
    attempted_threes = int(threes.sum()) if fga else 0
    return {
        "nba_id": nba_id,
        "official_roster_name": name,
        "season_fga": fga,
        "season_fgm": made,
        "season_fg_pct": made / fga * 100 if fga else float("nan"),
        "season_efg_pct": ((made + 0.5 * made_threes) / fga * 100
                           if fga else float("nan")),
        "season_3pm": made_threes,
        "season_3pa": attempted_threes,
        "season_3pt_pct": (made_threes / attempted_threes * 100
                           if attempted_threes else float("nan")),
        "mapped_fga": len(mapped),
        "displayed_fga": displayed_fga,
        "displayed_fga_pct": displayed_fga / fga * 100 if fga else 0.0,
        "displayed_cells": int(displayed.sum()),
        "rated_cells": int(cells.color_rated.sum()),
        "gray_cells": int((displayed & ~cells.color_rated).sum()),
        "minimum_fga": minimum,
        "qualified": qualifies_player(fga, minimum),
    }


def build(args: argparse.Namespace) -> list[Path]:
    roster = get_current_roster()
    league = shot_data.league_shots(args.season, args.refresh)
    team_shots = shot_data.team_shots(season=args.season, refresh=args.refresh)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    args.data_dir.mkdir(parents=True, exist_ok=True)

    prepared: list[tuple[object, pd.DataFrame, pd.DataFrame, pd.DataFrame]] = []
    audit_rows: list[dict[str, object]] = []
    for player in roster.itertuples(index=False):
        shots = shot_data.player_shots(int(player.nba_id), args.season, args.refresh)
        if shots.empty:
            mapped = shots.copy()
            cells = pd.DataFrame({
                "displayed": pd.Series(dtype=bool),
                "exact_fga": pd.Series(dtype=int),
                "color_rated": pd.Series(dtype=bool),
            })
        else:
            ctx = {"player": shots, "league": league, "show_thin_gray": False}
            mapped, cells = shot_chart.prepare_hex_table(ctx)
        audit_rows.append(player_summary(
            str(player.official_roster_name), int(player.nba_id), shots,
            mapped, cells, args.min_fga))
        if qualifies_player(len(shots), args.min_fga):
            prepared.append((player, shots, mapped, cells))

    qualifying_cell_fga = np.concatenate([
        cells.loc[cells.displayed, "exact_fga"].to_numpy(float)
        for _, shots, _, cells in prepared if qualifies_player(len(shots), args.min_fga)
    ])
    shared_size_cap = float(np.percentile(
        qualifying_cell_fga, shot_chart.HEX_SIZE_CAP_PERCENTILE))

    audit = pd.DataFrame(audit_rows).sort_values(
        ["qualified", "season_fga", "official_roster_name"],
        ascending=[False, False, True])
    audit["shared_player_size_cap_fga"] = shared_size_cap
    audit_path = args.data_dir / f"current-roster-hex-audit-{args.season}.csv"
    audit.to_csv(audit_path, index=False, float_format="%.4f")
    stats_path = args.data_dir / f"bulls-team-and-current-roster-hex-stats-{args.season}.csv"
    stats_rows = [canva_stats_row("Chicago Bulls", "Chicago attempts", team_shots)]
    for row in audit.loc[audit.qualified].itertuples(index=False):
        stats_rows.append({
            "subject": row.official_roster_name,
            "scope": "Full season, all teams",
            "fga": int(row.season_fga),
            "efg_pct": round(float(row.season_efg_pct), 1),
            "three_pt_pct": round(float(row.season_3pt_pct), 1),
        })
    stats = pd.DataFrame(stats_rows)
    stats.to_csv(stats_path, index=False, float_format="%.1f")

    outputs: list[Path] = []
    for player, shots, _, cells in sorted(
            prepared, key=lambda item: (-len(item[1]), item[0].official_roster_name)):
        name = str(player.official_roster_name)
        nba_id = int(player.nba_id)
        slug = player_slug(name)
        ctx = {
            "player": shots,
            "league": league,
            "name": name,
            "season": args.season,
            "show_thin_gray": False,
            "hex_size_cap": shared_size_cap,
        }
        _, cells = shot_chart.prepare_hex_table(ctx)
        output = args.output_dir / f"{date.today().isoformat()}-hex-{slug}-fg-rel.png"
        shot_chart.render_hex(ctx, output, False)
        outputs.append(output)

        shots.to_csv(args.data_dir / f"{slug}-shots-{args.season}.csv", index=False)
        exported = cells.copy()
        exported.insert(0, "nba_id", nba_id)
        exported.insert(1, "official_roster_name", name)
        exported.to_csv(
            args.data_dir / f"{slug}-hex-cells-{args.season}.csv",
            index=False, float_format="%.4f")

    qualifiers = audit[audit.qualified]
    excluded = audit[~audit.qualified]
    print("\nROSTER HEX SUMMARY")
    print(f"Roster as of: {date.today().isoformat()}")
    print(f"Qualifier: {args.min_fga}+ FGA in the {args.season} NBA regular season")
    print(f"Shared player size cap: {shared_size_cap:.2f} FGA per exact cell")
    print("Full-season totals across all teams")
    print(f"Qualified ({len(qualifiers)}): " + ", ".join(qualifiers.official_roster_name))
    print("Excluded: " + ", ".join(
        f"{row.official_roster_name} ({row.season_fga} FGA)"
        for row in excluded.itertuples(index=False)))
    print(f"Audit: {audit_path}")
    print(f"Canva stats (team + players): {stats_path}")
    return outputs


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build qualified current-Bulls relative-FG% hex charts")
    parser.add_argument("--season", default=CURRENT_SEASON)
    parser.add_argument("--min-fga", type=int, default=MIN_PLAYER_FGA)
    parser.add_argument("--refresh", action="store_true")
    parser.add_argument(
        "--output-dir", type=Path,
        default=ROOT / "output" / PROJECT)
    parser.add_argument(
        "--data-dir", type=Path,
        default=ROOT / "docs" / "visuals" / "2026-08-09-bulls-player-hex" / "data")
    return parser.parse_args()


if __name__ == "__main__":
    build(parse_args())
