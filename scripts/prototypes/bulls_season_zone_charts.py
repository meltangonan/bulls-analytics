#!/usr/bin/env python3
"""Build a 10-slide 2021-22 Bulls season zone-shot-chart carousel.

The carousel answers a single-team question: how did Chicago's nine highest-
volume regular-season shooters divide the court? Selection and chart data use
the same Chicago stint, so attempts for another team never enter the page.

Usage:
    venv/bin/python scripts/prototypes/bulls_season_zone_charts.py
    venv/bin/python scripts/prototypes/bulls_season_zone_charts.py --refresh --final
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
from bulls.data import fetch
from bulls.data import shots as shot_data
from scripts import make_shot_chart as shot_chart


SEASON = "2021-22"
MIN_PLAYER_FGA = 250
MAX_PLAYER_PAGES = 9
PROJECT = "2021-22-bulls-season-zone-charts"
START_DATE = "2026-08-24"
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


def fetch_leaderboard(season: str = SEASON) -> pd.DataFrame:
    """Fetch the official Bulls player-total table for one regular season."""
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
    out = table.loc[:, LEADERBOARD_COLUMNS].copy()
    out.insert(0, "season", season)
    return out


def load_leaderboard(season: str, data_dir: Path,
                     refresh: bool = False) -> pd.DataFrame:
    """Load the post-owned table, fetching it only when needed."""
    path = data_dir / f"bulls-season-fga-leaderboard-{season}.csv"
    if path.exists() and not refresh:
        return pd.read_csv(path)
    table = fetch_leaderboard(season)
    data_dir.mkdir(parents=True, exist_ok=True)
    table.to_csv(path, index=False)
    return table


def qualify_player(fga: int, minimum: int = MIN_PLAYER_FGA) -> bool:
    """Return whether a player's season sample clears the visible qualifier."""
    return int(fga) >= minimum


def select_players(table: pd.DataFrame, minimum: int = MIN_PLAYER_FGA,
                   limit: int = MAX_PLAYER_PAGES) -> pd.DataFrame:
    """Return the highest-volume qualified Bulls players in stable order."""
    required = {"PLAYER_ID", "PLAYER_NAME", "FGA", "MIN"}
    missing = required - set(table.columns)
    if missing:
        raise ValueError("leaderboard missing: " + ", ".join(sorted(missing)))
    ranked = table[table.FGA.apply(qualify_player, minimum=minimum)].sort_values(
        ["FGA", "MIN", "PLAYER_ID"],
        ascending=[False, False, True],
        kind="stable",
    )
    if len(ranked) < limit:
        raise ValueError(
            f"only {len(ranked)} players clear the {minimum}+ FGA qualifier; "
            f"need {limit} for the carousel"
        )
    return ranked.head(limit).reset_index(drop=True)


def load_player_shots(season: str, player: pd.Series, data_dir: Path,
                      refresh: bool = False) -> pd.DataFrame:
    """Load every regular-season attempt the player took for Chicago."""
    slug = player_slug(str(player.PLAYER_NAME))
    path = data_dir / f"{season}-{slug}-bulls-shots.csv"
    if path.exists() and not refresh:
        shots = pd.read_csv(path)
    else:
        shots = fetch.get_player_shots(
            int(player.PLAYER_ID),
            team_id=BULLS_TEAM_ID,
            season=season,
        )
        if shots.empty:
            raise ValueError(f"NBA.com returned no shots for {player.PLAYER_NAME}")
        data_dir.mkdir(parents=True, exist_ok=True)
        shots.to_csv(path, index=False)
    reconcile_shot_count(season, player, shots)
    return shots


def reconcile_shot_count(season: str, player: pd.Series,
                         shots: pd.DataFrame) -> None:
    """Prove that raw shot rows reconstruct the selecting Bulls FGA total."""
    expected = int(player.FGA)
    actual = len(shots)
    if actual != expected:
        raise ValueError(
            f"{season} {player.PLAYER_NAME}: shot rows {actual} != Bulls FGA {expected}"
        )


def league_zone_baseline(season: str, league: pd.DataFrame) -> pd.DataFrame:
    """Derive the twelve same-season NBA reference values used for colour."""
    working = league.copy()
    working["zone"] = sm.zone12_of_shots(working)
    grouped = (
        working.groupby("zone", as_index=False)["shot_made"]
        .agg(fga="size", fgm="sum")
    )
    grouped.insert(0, "season", season)
    grouped["fg_pct"] = grouped.fgm / grouped.fga * 100
    grouped["fga_share_pct"] = grouped.fga / len(working) * 100
    return grouped


def summary_row(rank: int, player: pd.Series, shots: pd.DataFrame,
                zones: pd.DataFrame, season: str = SEASON,
                minimum: int = MIN_PLAYER_FGA) -> dict[str, object]:
    """Return display-ready audit values for one chart page."""
    fga = len(shots)
    made = int(shots.shot_made.sum())
    threes = shots.shot_type.eq("3PT")
    three_made = int(shots.loc[threes, "shot_made"].sum())
    rated = zones[zones.rated]
    return {
        "season": season,
        "rank": rank,
        "player_id": int(player.PLAYER_ID),
        "player": str(player.PLAYER_NAME),
        "games": int(player.GP),
        "minutes": round(float(player.MIN), 1),
        "bulls_fga": int(player.FGA),
        "shot_rows": fga,
        "fgm": made,
        "fg_pct": round(made / fga * 100, 1),
        "efg_pct": round((made + 0.5 * three_made) / fga * 100, 1),
        "three_fga": int(threes.sum()),
        "three_fgm": three_made,
        "three_pct": round(three_made / int(threes.sum()) * 100, 1)
        if threes.any() else float("nan"),
        "zones_rated": int(len(rated)),
        "zones_grey": int(len(zones) - len(rated)),
        "rated_fga_share_pct": round(rated.fga.sum() / fga * 100, 1),
        "min_zone_fga": sm.MIN_ZONE12_FGA_PLAYER,
        "qualifier": f"{minimum}+ Bulls FGA",
        "scope": "Chicago attempts only",
    }


def print_canva_copy(summary: pd.DataFrame) -> None:
    print("\nCANVA COPY — 10-SLIDE CAROUSEL")
    print("PAGE 1 — COVER")
    print("Title: The 2021-22 Bulls through zone shot charts")
    print("Subtitle: Where Chicago's nine highest-volume shooters took their shots")
    print("Coverage: 2021-22 regular season · Chicago attempts only")
    for page, row in enumerate(summary.itertuples(index=False), start=2):
        print(f"\nPAGE {page} — {row.player}")
        print(f"Title: {row.player}")
        print(
            f"Subtitle: 2021-22 regular season · {row.bulls_fga:,} Bulls FGA · "
            f"{row.games} games"
        )
        print("Key: Colour = FG% vs the NBA in that zone")
        print("Reading it: vs LA = percentage-point gap to that season's league average")
        print("Qualifier: 250+ Bulls FGA · Grey zones are under 20 FGA")
        print("Source: NBA.com/stats")


def build(args: argparse.Namespace) -> list[Path]:
    args.output_dir.mkdir(parents=True, exist_ok=True)
    args.data_dir.mkdir(parents=True, exist_ok=True)

    leaderboard = load_leaderboard(args.season, args.data_dir, args.refresh)
    selected = select_players(leaderboard, args.min_fga, args.limit)
    league = shot_data.league_shots(args.season, args.refresh_league)
    if league.empty:
        raise ValueError(f"NBA.com returned no league shots for {args.season}")
    league_zone_baseline(args.season, league).to_csv(
        args.data_dir / f"league-zone-baseline-{args.season}.csv",
        index=False,
        float_format="%.4f",
    )

    stamp = date.today().isoformat()
    outputs: list[Path] = []
    summaries: list[dict[str, object]] = []
    zone_tables: list[pd.DataFrame] = []

    for rank, player in enumerate(selected.itertuples(index=False), start=1):
        player_series = pd.Series(player._asdict())
        shots = load_player_shots(args.season, player_series, args.data_dir, args.refresh)
        zones = sm.zone12_split(
            shots, league, min_fga=sm.MIN_ZONE12_FGA_PLAYER
        )
        zone_table = zones.copy()
        zone_table.insert(0, "season", args.season)
        zone_table.insert(1, "rank", rank)
        zone_table.insert(2, "player_id", int(player.PLAYER_ID))
        zone_table.insert(3, "player", str(player.PLAYER_NAME))
        zone_tables.append(zone_table)
        summaries.append(summary_row(
            rank, player_series, shots, zones, args.season, args.min_fga
        ))

        name = str(player.PLAYER_NAME)
        out = args.output_dir / (
            f"{stamp}-zone-season-{args.season}-{rank:02d}-{player_slug(name)}.png"
        )
        print(f"\n{rank}. {name}: {len(shots):,} Bulls FGA")
        shot_chart.render_zones(
            {
                "player": shots,
                "league": league,
                "name": name,
                "season": args.season,
                "min_fga": sm.MIN_ZONE12_FGA_PLAYER,
                "pill": "large",
                "summary_metrics": True,
            },
            out,
            args.final,
        )
        outputs.append(out)

    summary = pd.DataFrame(summaries)
    summary.to_csv(
        args.data_dir / f"zone-chart-summary-{args.season}.csv",
        index=False,
        float_format="%.1f",
    )
    pd.concat(zone_tables, ignore_index=True).to_csv(
        args.data_dir / f"zone-splits-{args.season}.csv",
        index=False,
        float_format="%.4f",
    )

    print("\nQUALIFIED BULLS")
    print(f"Qualifier: {args.min_fga}+ Bulls FGA in the {args.season} regular season")
    print(summary.to_string(index=False))
    print_canva_copy(summary)
    print(f"\nData: {args.data_dir}")
    return outputs


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build a Bulls single-season twelve-zone carousel"
    )
    parser.add_argument("--season", default=SEASON)
    parser.add_argument("--min-fga", type=int, default=MIN_PLAYER_FGA)
    parser.add_argument("--limit", type=int, default=MAX_PLAYER_PAGES)
    parser.add_argument("--refresh", action="store_true",
                        help="refetch the leaderboard and player shot logs")
    parser.add_argument("--refresh-league", action="store_true",
                        help="refetch the shared NBA league baseline")
    parser.add_argument("--final", action="store_true",
                        help="render at publish DPI")
    parser.add_argument("--output-dir", type=Path,
                        default=ROOT / "output" / PROJECT)
    parser.add_argument("--data-dir", type=Path,
                        default=ROOT / "docs" / "visuals" / SLUG / "data")
    return parser.parse_args()


if __name__ == "__main__":
    build(parse_args())
