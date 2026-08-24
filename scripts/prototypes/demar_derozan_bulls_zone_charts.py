#!/usr/bin/env python3
"""Build DeMar DeRozan's three Bulls season zone charts and tenure total.

Every player row is a regular-season field-goal attempt taken for Chicago.
Season pages use that season's NBA attempts as the comparison. The tenure page
pools the same three NBA seasons, so both player and baseline are attempt-
weighted across the identical window.

Usage:
    ../bulls-analytics/venv/bin/python \
        scripts/prototypes/demar_derozan_bulls_zone_charts.py --refresh --final
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


PLAYER_ID = 201942
PLAYER_NAME = "DeMar DeRozan"
SEASONS = ("2021-22", "2022-23", "2023-24")
SEASON_MIN_ZONE_FGA = sm.MIN_ZONE12_FGA_PLAYER
TENURE_MIN_ZONE_FGA = SEASON_MIN_ZONE_FGA * len(SEASONS)
PROJECT = "demar-derozan-bulls-zone-charts"
START_DATE = "2026-08-24"
SLUG = f"{START_DATE}-{PROJECT}"
LEADERBOARD_COLUMNS = (
    "PLAYER_ID", "PLAYER_NAME", "TEAM_ABBREVIATION", "GP", "MIN",
    "FGM", "FGA", "FG_PCT",
)


def fetch_bulls_totals(season: str) -> pd.Series:
    """Return DeRozan's official Chicago regular-season totals."""
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
        raise ValueError(f"{season} totals missing: " + ", ".join(sorted(missing)))
    player = table[table.PLAYER_ID.astype(int).eq(PLAYER_ID)]
    if len(player) != 1:
        raise ValueError(f"expected one {PLAYER_NAME} row for {season}, found {len(player)}")
    return player.loc[:, LEADERBOARD_COLUMNS].iloc[0]


def load_bulls_totals(season: str, data_dir: Path,
                      refresh: bool = False) -> pd.Series:
    path = data_dir / f"{season}-demar-derozan-bulls-totals.csv"
    if path.exists() and not refresh:
        return pd.read_csv(path).iloc[0]
    player = fetch_bulls_totals(season)
    out = player.to_frame().T
    out.insert(0, "season", season)
    out.to_csv(path, index=False)
    return out.iloc[0]


def load_bulls_shots(season: str, totals: pd.Series, data_dir: Path,
                     refresh: bool = False) -> pd.DataFrame:
    path = data_dir / f"{season}-demar-derozan-bulls-shots.csv"
    if path.exists() and not refresh:
        shots = pd.read_csv(path)
    else:
        shots = fetch.get_player_shots(
            PLAYER_ID, team_id=BULLS_TEAM_ID, season=season
        )
        if shots.empty:
            raise ValueError(f"NBA.com returned no {PLAYER_NAME} shots for {season}")
        shots.to_csv(path, index=False)
    reconcile_shot_count(season, totals, shots)
    return shots


def reconcile_shot_count(season: str, totals: pd.Series,
                         shots: pd.DataFrame) -> None:
    expected, actual = int(totals.FGA), len(shots)
    if actual != expected:
        raise ValueError(f"{season}: shot rows {actual} != Bulls FGA {expected}")


def league_zone_baseline(label: str, league: pd.DataFrame) -> pd.DataFrame:
    working = league.copy()
    working["zone"] = sm.zone_of(working.loc_x, working.loc_y)
    grouped = working.groupby("zone", as_index=False)["shot_made"].agg(
        fga="size", fgm="sum"
    )
    grouped.insert(0, "window", label)
    grouped["fg_pct"] = grouped.fgm / grouped.fga * 100
    grouped["fga_share_pct"] = grouped.fga / len(working) * 100
    return grouped


def summary_row(label: str, totals: pd.Series, shots: pd.DataFrame,
                zones: pd.DataFrame, min_zone_fga: int,
                included_seasons: str) -> dict[str, object]:
    overall = shot_chart._zone12_overall_metrics(shots)
    rated = zones[zones.rated]
    return {
        "window": label,
        "player_id": PLAYER_ID,
        "player": PLAYER_NAME,
        "included_seasons": included_seasons,
        "games": int(totals.GP),
        "minutes": round(float(totals.MIN), 1),
        "bulls_fga": int(totals.FGA),
        "shot_rows": len(shots),
        "fgm": int(shots.shot_made.sum()),
        "fg_pct": round(shots.shot_made.mean() * 100, 1),
        "efg_pct": round(overall["efg_pct"], 1),
        "three_pct": round(overall["three_pct"], 1),
        "zones_rated": len(rated),
        "zones_grey": len(zones) - len(rated),
        "rated_fga_share_pct": round(rated.fga.sum() / len(shots) * 100, 1),
        "min_zone_fga": min_zone_fga,
        "scope": "Chicago attempts only",
    }


def tenure_totals(season_totals: list[pd.Series]) -> pd.Series:
    """Add counting fields; each game belongs to exactly one Bulls season."""
    return pd.Series({
        "GP": sum(int(row.GP) for row in season_totals),
        "MIN": sum(float(row.MIN) for row in season_totals),
        "FGA": sum(int(row.FGA) for row in season_totals),
    })


def render(label: str, shots: pd.DataFrame, league: pd.DataFrame,
           min_zone_fga: int, output_dir: Path, final: bool) -> Path:
    suffix = label.lower().replace("–", "-").replace(" ", "-")
    out = output_dir / f"{date.today().isoformat()}-zone-demar-derozan-{suffix}.png"
    shot_chart.render_zones(
        {
            "player": shots,
            "league": league,
            "name": PLAYER_NAME,
            "season": label,
            "min_fga": min_zone_fga,
            "pill": "large",
            "summary_metrics": True,
        },
        out,
        final,
    )
    return out


def print_canva_copy(summary: pd.DataFrame) -> None:
    print("\nCANVA COPY — 5-SLIDE CAROUSEL")
    print("PAGE 1 — COVER")
    print("Title: DeMar DeRozan as a Bull, season by season")
    print("Subtitle: How his shot profile changed across three Chicago seasons")
    for page, row in enumerate(summary.itertuples(index=False), start=2):
        tenure = row.window == "Bulls tenure"
        print(f"\nPAGE {page} — {row.window}")
        print(f"Title: {'Three-year Bulls tenure' if tenure else row.window}")
        print(f"Subtitle: {row.bulls_fga:,} Bulls FGA · {row.games} games")
        print("Key: Colour = FG% vs the NBA in that zone")
        print("Reading it: vs LA = percentage-point gap to the matching league baseline")
        print(
            "Qualifier: Chicago attempts only · Grey zones are under "
            f"{row.min_zone_fga} FGA"
        )
        print("Source: NBA.com/stats")


def build(args: argparse.Namespace) -> list[Path]:
    args.output_dir.mkdir(parents=True, exist_ok=True)
    args.data_dir.mkdir(parents=True, exist_ok=True)
    outputs: list[Path] = []
    summaries: list[dict[str, object]] = []
    zone_tables: list[pd.DataFrame] = []
    baseline_tables: list[pd.DataFrame] = []
    all_shots: list[pd.DataFrame] = []
    all_league: list[pd.DataFrame] = []
    all_totals: list[pd.Series] = []

    for season in SEASONS:
        print(f"\n{'=' * 72}\n{season}")
        totals = load_bulls_totals(season, args.data_dir, args.refresh)
        shots = load_bulls_shots(season, totals, args.data_dir, args.refresh)
        league = shot_data.league_shots(season, args.refresh_league)
        if league.empty:
            raise ValueError(f"NBA.com returned no league shots for {season}")
        zones = sm.zone12_split(shots, league, min_fga=SEASON_MIN_ZONE_FGA)
        audit = zones.copy()
        audit.insert(0, "window", season)
        zone_tables.append(audit)
        baseline_tables.append(league_zone_baseline(season, league))
        summaries.append(summary_row(
            season, totals, shots, zones, SEASON_MIN_ZONE_FGA, season
        ))
        outputs.append(render(
            season, shots, league, SEASON_MIN_ZONE_FGA, args.output_dir, args.final
        ))
        all_shots.append(shots.assign(source_season=season))
        all_league.append(league.assign(source_season=season))
        all_totals.append(totals)

    pooled_shots = pd.concat(all_shots, ignore_index=True)
    pooled_league = pd.concat(all_league, ignore_index=True)
    pooled_zones = sm.zone12_split(
        pooled_shots, pooled_league, min_fga=TENURE_MIN_ZONE_FGA
    )
    pooled_audit = pooled_zones.copy()
    pooled_audit.insert(0, "window", "Bulls tenure")
    zone_tables.append(pooled_audit)
    baseline_tables.append(league_zone_baseline("Bulls tenure", pooled_league))
    totals = tenure_totals(all_totals)
    summaries.append(summary_row(
        "Bulls tenure", totals, pooled_shots, pooled_zones,
        TENURE_MIN_ZONE_FGA, ", ".join(SEASONS)
    ))
    outputs.append(render(
        "Bulls tenure", pooled_shots, pooled_league, TENURE_MIN_ZONE_FGA,
        args.output_dir, args.final
    ))

    summary = pd.DataFrame(summaries)
    summary.to_csv(args.data_dir / "zone-chart-summary.csv", index=False)
    pd.concat(zone_tables, ignore_index=True).to_csv(
        args.data_dir / "zone-splits.csv", index=False, float_format="%.4f"
    )
    pd.concat(baseline_tables, ignore_index=True).to_csv(
        args.data_dir / "league-zone-baselines.csv", index=False,
        float_format="%.4f"
    )
    print("\nDEROZAN BULLS ZONE SUMMARY")
    print(summary.to_string(index=False))
    print_canva_copy(summary)
    print(f"\nData: {args.data_dir}")
    return outputs


def build_cover(args: argparse.Namespace) -> Path:
    """Build the selected data-free zone treatment for the cover page."""
    args.output_dir.mkdir(parents=True, exist_ok=True)
    treatment = "preview" if args.cover_preview_only else "blank"
    out = args.output_dir / (
        f"{date.today().isoformat()}-zone-demar-derozan-cover-{treatment}.png"
    )
    renderer = (shot_chart.render_preview_zones if args.cover_preview_only
                else shot_chart.render_blank_zones)
    renderer(out, args.final)
    return out


def build_red_cover_variants(args: argparse.Namespace) -> list[Path]:
    """Build reusable Bulls-red cover courts without player-specific names."""
    args.output_dir.mkdir(parents=True, exist_ok=True)
    variants = (
        ("bulls-red", shot_chart.ZONE12_BULLS_RED),
        ("bulls-red-light", shot_chart.ZONE12_BULLS_RED_LIGHT),
    )
    outputs = []
    for name, fill in variants:
        out = args.output_dir / f"{date.today().isoformat()}-zone-cover-{name}.png"
        shot_chart.render_solid_cover_zones(out, args.final, fill)
        outputs.append(out)
    return outputs


def build_tenure_data_cover(args: argparse.Namespace) -> Path:
    """Build DeRozan's real pooled-tenure colors without detail overlays."""
    args.output_dir.mkdir(parents=True, exist_ok=True)
    player = pd.concat([
        pd.read_csv(args.data_dir / f"{season}-demar-derozan-bulls-shots.csv")
        for season in SEASONS
    ], ignore_index=True)
    league = pd.concat([
        shot_data.league_shots(season, args.refresh_league)
        for season in SEASONS
    ], ignore_index=True)
    out = args.output_dir / (
        f"{date.today().isoformat()}-zone-demar-derozan-bulls-tenure-cover.png"
    )
    shot_chart.render_zones(
        {
            "player": player,
            "league": league,
            "name": PLAYER_NAME,
            "season": "Bulls tenure",
            "min_fga": TENURE_MIN_ZONE_FGA,
            "show_details": False,
            "summary_metrics": False,
            "court_ink": "#242424",
        },
        out,
        args.final,
    )
    return out


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build DeMar DeRozan Bulls-tenure twelve-zone charts"
    )
    parser.add_argument("--refresh", action="store_true")
    parser.add_argument("--refresh-league", action="store_true")
    parser.add_argument("--final", action="store_true")
    parser.add_argument("--cover-only", action="store_true",
                        help="render only the data-free gray cover silhouette")
    parser.add_argument("--cover-preview-only", action="store_true",
                        help="render only the data-free solid-color cover teaser")
    parser.add_argument("--cover-red-variants-only", action="store_true",
                        help="render reusable solid Bulls-red cover variants")
    parser.add_argument("--tenure-data-cover-only", action="store_true",
                        help="render pooled tenure colors without data overlays")
    parser.add_argument("--output-dir", type=Path,
                        default=ROOT / "output" / PROJECT)
    parser.add_argument("--data-dir", type=Path,
                        default=ROOT / "docs" / "visuals" / SLUG / "data")
    return parser.parse_args()


if __name__ == "__main__":
    cli_args = parse_args()
    if cli_args.tenure_data_cover_only:
        build_tenure_data_cover(cli_args)
    elif cli_args.cover_red_variants_only:
        build_red_cover_variants(cli_args)
    elif cli_args.cover_only or cli_args.cover_preview_only:
        build_cover(cli_args)
    else:
        build(cli_args)
