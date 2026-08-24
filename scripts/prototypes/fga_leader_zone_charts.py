#!/usr/bin/env python3
"""Build one twelve-zone chart for each Bulls season FGA leader since 2020-21.

The selection and the chart use the same stint: total regular-season field-goal
attempts for Chicago.  That is deliberately different from the current-roster
zone carousel, where a player's chart follows him across every team he played
for.  Each season is compared with that season's NBA shot profile so the colour
does not mistake league-wide change for player change.

Usage:
    ../bulls-analytics/venv/bin/python \
        scripts/prototypes/fga_leader_zone_charts.py
    ../bulls-analytics/venv/bin/python \
        scripts/prototypes/fga_leader_zone_charts.py --refresh --final
"""
from __future__ import annotations

import argparse
from datetime import date
from pathlib import Path
import sys

import pandas as pd
from nba_api.stats.endpoints import leaguedashplayerstats

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from bulls.analysis import shot_maps as sm
from bulls.config import BULLS_TEAM_ID
from bulls.data import shots as shot_data
from bulls.data import fetch
from scripts import make_shot_chart as shot_chart


SEASONS = (
    "2020-21",
    "2021-22",
    "2022-23",
    "2023-24",
    "2024-25",
    "2025-26",
)
BONUS_SEASONS = ("2022-23",)
BONUS_MIN_FGA = 1_300
BONUS_MAX_GAP = 99
PROJECT = "2020s-fga-leader-zones"
START_DATE = "2026-08-23"
SLUG = f"{START_DATE}-{PROJECT}"
LEADERBOARD_COLUMNS = (
    "PLAYER_ID",
    "PLAYER_NAME",
    "TEAM_ABBREVIATION",
    "GP",
    "MIN",
    "FGM",
    "FGA",
    "FG_PCT",
)


def player_slug(name: str) -> str:
    return name.lower().replace(" ", "-").replace(".", "")


def select_fga_leader(table: pd.DataFrame) -> pd.Series:
    """Return the Bulls stint with the most total FGA.

    Minutes and then player id make an exact FGA tie deterministic.  The team
    abbreviation is intentionally not filtered: NBA.com can stamp a correctly
    team-filtered stint with the player's later team after a trade.
    """
    required = {"PLAYER_ID", "PLAYER_NAME", "FGA", "MIN"}
    missing = required - set(table.columns)
    if missing:
        raise ValueError("leaderboard missing: " + ", ".join(sorted(missing)))
    if table.empty:
        raise ValueError("Bulls leaderboard is empty")
    ranked = table.sort_values(
        ["FGA", "MIN", "PLAYER_ID"],
        ascending=[False, False, True],
        kind="stable",
    )
    return ranked.iloc[0]


def select_bonus_runner_up(table: pd.DataFrame) -> tuple[pd.Series, pd.Series]:
    """Return the leader and runner-up when both clear the narrow exception.

    The exception is deliberately reproducible: both players must attempt at
    least 1,300 shots and finish fewer than 100 attempts apart.  It adds the
    unusually close 2022-23 DeRozan season without quietly expanding the post
    to every season's top two.
    """
    required = {"PLAYER_ID", "PLAYER_NAME", "FGA", "MIN"}
    missing = required - set(table.columns)
    if missing:
        raise ValueError("leaderboard missing: " + ", ".join(sorted(missing)))
    if len(table) < 2:
        raise ValueError("bonus selection requires at least two players")
    ranked = table.sort_values(
        ["FGA", "MIN", "PLAYER_ID"],
        ascending=[False, False, True],
        kind="stable",
    )
    leader, runner_up = ranked.iloc[0], ranked.iloc[1]
    gap = int(leader.FGA) - int(runner_up.FGA)
    if int(runner_up.FGA) < BONUS_MIN_FGA or gap > BONUS_MAX_GAP:
        raise ValueError(
            "no qualifying runner-up: both players need at least "
            f"{BONUS_MIN_FGA:,} FGA and a gap under 100"
        )
    return leader, runner_up


def fetch_leaderboard(season: str) -> pd.DataFrame:
    """Official Bulls player totals for one regular season."""
    table = leaguedashplayerstats.LeagueDashPlayerStats(
        season=season,
        season_type_all_star="Regular Season",
        team_id_nullable=BULLS_TEAM_ID,
        per_mode_detailed="Totals",
        timeout=60,
        headers=fetch._NBA_HEADERS,
    ).get_data_frames()[0]
    missing = set(LEADERBOARD_COLUMNS) - set(table.columns)
    if missing:
        raise ValueError(
            f"{season} leaderboard missing: " + ", ".join(sorted(missing))
        )
    return table.loc[:, LEADERBOARD_COLUMNS].copy()


def load_leaderboard(season: str, data_dir: Path,
                     refresh: bool = False) -> pd.DataFrame:
    """Read the post-owned audit table, fetching only when it is absent."""
    path = data_dir / f"bulls-fga-leaderboard-{season}.csv"
    if path.exists() and not refresh:
        return pd.read_csv(path)
    table = fetch_leaderboard(season)
    table.insert(0, "season", season)
    table.to_csv(path, index=False)
    return table


def load_leader_shots(season: str, leader: pd.Series, data_dir: Path,
                      refresh: bool = False) -> pd.DataFrame:
    """Every regular-season attempt the selected player took for Chicago."""
    slug = player_slug(str(leader.PLAYER_NAME))
    path = data_dir / f"{season}-{slug}-bulls-shots.csv"
    if path.exists() and not refresh:
        shots = pd.read_csv(path)
    else:
        shots = fetch.get_player_shots(
            int(leader.PLAYER_ID),
            team_id=BULLS_TEAM_ID,
            season=season,
        )
        if shots.empty:
            raise ValueError(f"NBA.com returned no shots for {leader.PLAYER_NAME}, {season}")
        shots.to_csv(path, index=False)
    reconcile_shot_count(season, leader, shots)
    return shots


def reconcile_shot_count(season: str, leader: pd.Series,
                         shots: pd.DataFrame) -> None:
    """Prove that the raw shot log reconstructs the selecting FGA total."""
    expected = int(leader.FGA)
    actual = len(shots)
    if actual != expected:
        raise ValueError(
            f"{season} {leader.PLAYER_NAME}: shot rows {actual} != box FGA {expected}"
        )


def league_zone_baseline(season: str, league: pd.DataFrame) -> pd.DataFrame:
    """The twelve same-season NBA reference values that drive the chart."""
    working = league.copy()
    working["zone"] = sm.zone_of(working.loc_x, working.loc_y)
    grouped = (
        working.groupby("zone", as_index=False)["shot_made"]
        .agg(fga="size", fgm="sum")
    )
    grouped.insert(0, "season", season)
    grouped["fg_pct"] = grouped.fgm / grouped.fga * 100
    grouped["fga_share_pct"] = grouped.fga / len(working) * 100
    return grouped


def chart_summary(season: str, leader: pd.Series, shots: pd.DataFrame,
                  league: pd.DataFrame, zones: pd.DataFrame) -> dict[str, object]:
    rated = zones[zones.rated]
    made = int(shots.shot_made.sum())
    subject_overall = shot_chart._zone12_overall_metrics(shots)
    league_overall = shot_chart._zone12_overall_metrics(league)
    return {
        "season": season,
        "player_id": int(leader.PLAYER_ID),
        "player": str(leader.PLAYER_NAME),
        "games": int(leader.GP),
        "minutes": round(float(leader.MIN), 1),
        "box_fga": int(leader.FGA),
        "shot_rows": len(shots),
        "fgm": made,
        "fg_pct": round(made / len(shots) * 100, 1),
        "efg_pct": round(subject_overall["efg_pct"], 1),
        "efg_vs_league": round(
            subject_overall["efg_pct"] - league_overall["efg_pct"], 1
        ),
        "three_pct": round(subject_overall["three_pct"], 1),
        "three_vs_league": round(
            subject_overall["three_pct"] - league_overall["three_pct"], 1
        ),
        "zones_rated": len(rated),
        "zones_grey": len(zones) - len(rated),
        "rated_fga_share_pct": round(rated.fga.sum() / len(shots) * 100, 1),
        "min_zone_fga": sm.MIN_ZONE12_FGA_PLAYER,
        "scope": "Chicago attempts only",
    }


def print_canva_copy(summary: pd.DataFrame) -> None:
    print("\nCANVA COPY — 7-SLIDE CAROUSEL")
    print("PAGE 1 — COVER")
    print("Title: Bulls FGA leaders since 2020-21")
    print("Subtitle: Where Chicago's highest-volume shooter took his shots, year by year")
    print("Coverage: 2020-21 through 2025-26 regular seasons")
    for page, row in enumerate(summary.itertuples(index=False), start=2):
        print(f"\nPAGE {page} — {row.season}")
        print(f"Title: {row.player}")
        print(f"Subtitle: {row.season} regular season · Bulls leader with {row.box_fga:,} FGA")
        print("Key: Colour = FG% vs the NBA in that zone")
        print("Reading it: vs LA = percentage-point gap to that season's league average")
        print("Qualifier: Chicago attempts only · Grey zones are under 20 FGA")
        print("Source: NBA.com/stats")


def build_bonus(args: argparse.Namespace) -> list[Path]:
    """Build only the tightly qualified runner-up exception chart."""
    args.output_dir.mkdir(parents=True, exist_ok=True)
    args.data_dir.mkdir(parents=True, exist_ok=True)
    stamp = date.today().isoformat()
    outputs: list[Path] = []
    summaries: list[dict[str, object]] = []
    zone_tables: list[pd.DataFrame] = []

    for season in BONUS_SEASONS:
        print(f"\n{'=' * 72}\n{season} BONUS RUNNER-UP")
        leaderboard = load_leaderboard(season, args.data_dir, args.refresh)
        leader, runner_up = select_bonus_runner_up(leaderboard)
        shots = load_leader_shots(
            season, runner_up, args.data_dir, args.refresh
        )
        league = shot_data.league_shots(season, args.refresh_league)
        if league.empty:
            raise ValueError(f"NBA.com returned no league shots for {season}")

        zones = sm.zone12_split(
            shots, league, min_fga=sm.MIN_ZONE12_FGA_PLAYER
        )
        zone_table = zones.copy()
        zone_table.insert(0, "season", season)
        zone_table.insert(1, "player_id", int(runner_up.PLAYER_ID))
        zone_table.insert(2, "player", str(runner_up.PLAYER_NAME))
        zone_tables.append(zone_table)

        summary = chart_summary(season, runner_up, shots, league, zones)
        summary.update({
            "rank": 2,
            "leader": str(leader.PLAYER_NAME),
            "leader_fga": int(leader.FGA),
            "fga_behind": int(leader.FGA) - int(runner_up.FGA),
            "qualifier": "Both top two had 1,300+ FGA and finished under 100 apart",
        })
        summaries.append(summary)

        name = str(runner_up.PLAYER_NAME)
        final_suffix = "-final" if args.final else ""
        out = args.output_dir / (
            f"{stamp}-zone-fga-runner-up-{season}-{player_slug(name)}"
            f"{final_suffix}.png"
        )
        print(
            f"{name}: {len(shots):,} Chicago FGA; "
            f"{summary['fga_behind']} behind {leader.PLAYER_NAME}"
        )
        shot_chart.render_zones(
            {
                "player": shots,
                "league": league,
                "name": name,
                "season": season,
                "min_fga": sm.MIN_ZONE12_FGA_PLAYER,
                "pill": "large",
                "summary_metrics": True,
            },
            out,
            args.final,
        )
        outputs.append(out)

    summary_table = pd.DataFrame(summaries)
    summary_table.to_csv(
        args.data_dir / "fga-bonus-zone-summary.csv", index=False
    )
    pd.concat(zone_tables, ignore_index=True).to_csv(
        args.data_dir / "fga-bonus-zone-splits.csv",
        index=False,
        float_format="%.4f",
    )
    print("\nBONUS CHART SUMMARY")
    print(summary_table.to_string(index=False))
    row = summary_table.iloc[0]
    print("\nCANVA COPY — BONUS PAGE")
    print("Eyebrow: 2022-23 RUNNER-UP")
    print(f"Title: {row.player}")
    print(
        f"Subtitle: {row.box_fga:,} FGA · {row.fga_behind} behind "
        f"{row.leader}"
    )
    print("Qualifier: Chicago attempts only · Grey zones are under 20 FGA")
    print("Source: NBA.com/stats")
    return outputs


def build(args: argparse.Namespace) -> list[Path]:
    args.output_dir.mkdir(parents=True, exist_ok=True)
    args.data_dir.mkdir(parents=True, exist_ok=True)
    stamp = date.today().isoformat()

    outputs: list[Path] = []
    summaries: list[dict[str, object]] = []
    zone_tables: list[pd.DataFrame] = []
    league_tables: list[pd.DataFrame] = []

    for season in args.seasons:
        print(f"\n{'=' * 72}\n{season}")
        leaderboard = load_leaderboard(season, args.data_dir, args.refresh)
        leader = select_fga_leader(leaderboard)
        shots = load_leader_shots(season, leader, args.data_dir, args.refresh)
        league = shot_data.league_shots(season, args.refresh_league)
        if league.empty:
            raise ValueError(f"NBA.com returned no league shots for {season}")

        zones = sm.zone12_split(
            shots, league, min_fga=sm.MIN_ZONE12_FGA_PLAYER
        )
        zone_table = zones.copy()
        zone_table.insert(0, "season", season)
        zone_table.insert(1, "player_id", int(leader.PLAYER_ID))
        zone_table.insert(2, "player", str(leader.PLAYER_NAME))
        zone_tables.append(zone_table)
        league_tables.append(league_zone_baseline(season, league))
        summaries.append(chart_summary(season, leader, shots, league, zones))

        name = str(leader.PLAYER_NAME)
        final_suffix = "-final" if args.final else ""
        out = args.output_dir / (
            f"{stamp}-zone-fga-leader-{season}-{player_slug(name)}"
            f"{final_suffix}.png"
        )
        print(f"{name}: {len(shots):,} Chicago FGA")
        shot_chart.render_zones(
            {
                "player": shots,
                "league": league,
                "name": name,
                "season": season,
                "min_fga": sm.MIN_ZONE12_FGA_PLAYER,
                "pill": "large",
                "summary_metrics": True,
            },
            out,
            args.final,
        )
        outputs.append(out)

    summary = pd.DataFrame(summaries)
    summary.to_csv(args.data_dir / "fga-leader-zone-summary.csv", index=False)
    pd.concat(zone_tables, ignore_index=True).to_csv(
        args.data_dir / "fga-leader-zone-splits.csv",
        index=False,
        float_format="%.4f",
    )
    pd.concat(league_tables, ignore_index=True).to_csv(
        args.data_dir / "league-zone-baselines.csv",
        index=False,
        float_format="%.4f",
    )

    print("\nFGA LEADER SUMMARY")
    print(summary.to_string(index=False))
    print_canva_copy(summary)
    print(f"\nData: {args.data_dir}")
    return outputs


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build Bulls season-FGA-leader twelve-zone charts"
    )
    parser.add_argument("--seasons", nargs="+", default=list(SEASONS))
    parser.add_argument("--refresh", action="store_true",
                        help="refetch leaderboards and Chicago player shots")
    parser.add_argument("--refresh-league", action="store_true",
                        help="refetch the shared 30-team league baselines")
    parser.add_argument("--final", action="store_true")
    parser.add_argument(
        "--extras-only",
        action="store_true",
        help="render only the narrowly qualified 2022-23 runner-up chart",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=ROOT / "output" / PROJECT,
    )
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=ROOT / "docs" / "visuals" / SLUG / "data",
    )
    return parser.parse_args()


if __name__ == "__main__":
    cli_args = parse_args()
    build_bonus(cli_args) if cli_args.extras_only else build(cli_args)
