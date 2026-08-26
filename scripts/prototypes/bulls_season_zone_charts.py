#!/usr/bin/env python3
"""Build a Bulls single-season zone-shot-chart carousel.

The carousel answers a single-team question: how did Chicago's qualified
regular-season shooters divide the court? Selection and chart data use the
same Chicago stint, so attempts for another team never enter the page.

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
from nba_api.stats.endpoints import leaguedashplayerstats, leaguedashteamstats

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
# Post-specific team treatment: every 2010-11 Bulls zone has at least 188 FGA.
# Colour all observed team zones against the same-season NBA instead of carrying
# the 400-attempt current-season floor backward into a lower-volume era.
TEAM_ZONE_MIN_FGA = 1
COVER_COLOR_SEED = 201011
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


def fetch_team_totals(season: str = SEASON) -> pd.DataFrame:
    """Fetch Chicago's official regular-season FGM and FGA reconciliation row."""
    table = leaguedashteamstats.LeagueDashTeamStats(
        season=season,
        season_type_all_star="Regular Season",
        team_id_nullable=BULLS_TEAM_ID,
        per_mode_detailed="Totals",
        timeout=60,
        headers=fetch._NBA_HEADERS,
    ).get_data_frames()[0]
    row = table.loc[table.TEAM_ID == BULLS_TEAM_ID, [
        "TEAM_ID", "TEAM_NAME", "GP", "FGM", "FGA", "FG_PCT"
    ]].copy()
    if len(row) != 1:
        raise ValueError(f"expected one {season} Bulls team row, found {len(row)}")
    row.insert(0, "season", season)
    return row


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
    if limit <= 0:
        return ranked.reset_index(drop=True)
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


def separate_unclassifiable_league_shots(
    league: pd.DataFrame, maximum_share: float = 0.001
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Separate source rows that have no coordinates or basic NBA zone.

    A tiny number of historical NBA attempts have a made/missed result but no
    location. They belong in league totals, but cannot honestly be assigned to
    one of twelve court zones. Preserve them as an audit rather than guessing.
    """
    required = ["loc_x", "loc_y", "shot_zone"]
    missing_columns = set(required) - set(league.columns)
    if missing_columns:
        raise ValueError(
            "league shots missing: " + ", ".join(sorted(missing_columns))
        )
    incomplete = league[required].isna().any(axis=1)
    excluded = league.loc[incomplete].copy()
    if len(excluded) / len(league) > maximum_share:
        raise ValueError(
            f"{len(excluded):,} of {len(league):,} league shots lack a zone "
            "or coordinates; refusing to build a partial baseline"
        )
    return league.loc[~incomplete].copy(), excluded


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


def print_canva_copy(summary: pd.DataFrame, season: str = SEASON,
                     minimum: int = MIN_PLAYER_FGA) -> None:
    print(f"\nCANVA COPY — {len(summary) + 1}-SLIDE CAROUSEL")
    print("PAGE 1 — COVER")
    print(f"Title: The {season} Bulls through zone shot charts")
    print("Subtitle: Where Chicago's qualified shooters took their shots")
    print(f"Coverage: {season} regular season · Chicago attempts only")
    for page, row in enumerate(summary.itertuples(index=False), start=2):
        print(f"\nPAGE {page} — {row.player}")
        print(f"Title: {row.player}")
        print(
            f"Subtitle: {season} regular season · {row.bulls_fga:,} Bulls FGA · "
            f"{row.games} games"
        )
        print("Key: Colour = FG% vs the NBA in that zone")
        print("Reading it: vs LA = percentage-point gap to that season's league average")
        print(
            f"Qualifier: {minimum}+ Bulls FGA · Grey zones are under 20 FGA"
        )
        print("Source: NBA.com/stats")


def build(args: argparse.Namespace) -> list[Path]:
    args.output_dir.mkdir(parents=True, exist_ok=True)
    args.data_dir.mkdir(parents=True, exist_ok=True)

    leaderboard = load_leaderboard(args.season, args.data_dir, args.refresh)
    selected = select_players(leaderboard, args.min_fga, args.limit)
    league_raw = shot_data.league_shots(args.season, args.refresh_league)
    if league_raw.empty:
        raise ValueError(f"NBA.com returned no league shots for {args.season}")
    league, unclassifiable = separate_unclassifiable_league_shots(league_raw)
    unclassifiable.to_csv(
        args.data_dir / f"league-unclassifiable-shots-{args.season}.csv",
        index=False,
    )
    if not unclassifiable.empty:
        print(
            f"League location coverage: {len(league):,}/{len(league_raw):,} "
            f"shots ({len(unclassifiable):,} source rows preserved but excluded)"
        )
    league_zone_baseline(args.season, league).to_csv(
        args.data_dir / f"league-zone-baseline-{args.season}.csv",
        index=False,
        float_format="%.4f",
    )

    stamp = date.today().isoformat()
    outputs: list[Path] = []
    summaries: list[dict[str, object]] = []
    zone_tables: list[pd.DataFrame] = []

    if args.include_cover:
        cover_out = args.output_dir / (
            f"{date.today().isoformat()}-zone-season-{args.season}-cover-decorative.png"
        )
        shot_chart.render_randomized_cover_zones(
            cover_out, args.final, COVER_COLOR_SEED
        )
        outputs.append(cover_out)

    if args.include_team:
        team = shot_data.team_shots(BULLS_TEAM_ID, args.season, args.refresh)
        totals = fetch_team_totals(args.season)
        expected_fga = int(totals.iloc[0].FGA)
        expected_fgm = int(totals.iloc[0].FGM)
        if len(team) != expected_fga:
            raise ValueError(
                f"{args.season} Bulls: shot rows {len(team)} != team FGA "
                f"{expected_fga}"
            )
        if int(team.shot_made.sum()) != expected_fgm:
            raise ValueError(
                f"{args.season} Bulls: shot makes {int(team.shot_made.sum())} "
                f"!= team FGM {expected_fgm}"
            )
        totals.to_csv(
            args.data_dir / f"bulls-team-totals-{args.season}.csv", index=False
        )
        team.to_csv(
            args.data_dir / f"bulls-team-shots-{args.season}.csv", index=False
        )
        team_zones = sm.zone12_split(
            team, league, min_fga=TEAM_ZONE_MIN_FGA
        )
        team_zones.to_csv(
            args.data_dir / f"bulls-team-zone-splits-{args.season}.csv",
            index=False,
            float_format="%.4f",
        )
        team_out = args.output_dir / (
            f"{date.today().isoformat()}-zone-season-{args.season}-00-chicago-bulls.png"
        )
        shot_chart.render_zones(
            {
                "player": team,
                "league": league,
                "name": "Chicago Bulls",
                "season": args.season,
                "min_fga": TEAM_ZONE_MIN_FGA,
                "pill": "large",
                "summary_metrics": True,
                "show_thin_legend": False,
            },
            team_out,
            args.final,
        )
        outputs.append(team_out)
        print(
            f"\nChicago Bulls team chart: {len(team):,} FGA · "
            f"{int(team.shot_made.sum()):,} FGM · "
            f"{int(team_zones.rated.sum())}/12 rated zones"
        )

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
    print_canva_copy(summary, args.season, args.min_fga)
    print(f"\nData: {args.data_dir}")
    return outputs


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build a Bulls single-season twelve-zone carousel"
    )
    parser.add_argument("--season", default=SEASON)
    parser.add_argument("--min-fga", type=int, default=MIN_PLAYER_FGA)
    parser.add_argument("--limit", type=int, default=MAX_PLAYER_PAGES)
    parser.add_argument("--include-team", action="store_true",
                        help="also render all Bulls attempts as one team chart")
    parser.add_argument("--include-cover", action="store_true",
                        help="also render the data-free decorative cover court")
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
