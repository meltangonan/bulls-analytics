#!/usr/bin/env python3
"""Build Zach LaVine's Bulls season zone charts, tenure chart, and cover.

    venv/bin/python scripts/prototypes/lavine_bulls_zone_charts.py --final

The fifth in the tenure family, after Rose, DeRozan, Butler and Hinrich, and
deliberately identical to Hinrich in method and page set: one slide per charted
season, a pooled tenure slide, a bare tenure cover, and the small-multiples grid
of every charted season. Same twelve zones, reconciliation, grey floor rule and
audit files, so the five can sit side by side.

**His last season is split by a trade.** He was dealt to Sacramento on
2025-02-03, so 2024-25 holds only his Chicago games. Every pull here is scoped
to ``team_id=BULLS_TEAM_ID``, and because a wrongly-scoped shot pull returns an
empty frame rather than an error, the reconciliation against his official
Chicago totals is what makes the narrow pull trustworthy rather than merely
narrow.
"""
from __future__ import annotations

import argparse
from datetime import date
from pathlib import Path
import sys

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from bulls.analysis import shot_maps as sm
from bulls.config import BULLS_TEAM_ID
from bulls.data import fetch
from bulls.data import shots as shot_data
from scripts import make_shot_chart as shot_chart


PLAYER_ID = 203897
PLAYER_NAME = "Zach LaVine"
SEASONS = (
    "2017-18", "2018-19", "2019-20", "2020-21", "2021-22", "2022-23",
    "2023-24", "2024-25",
)
# Same line as Hinrich: a season earns its own shot chart at 300 Chicago
# attempts. Every season still feeds the pooled tenure chart and every audit
# file; the floor decides which seasons are DRAWN, not which are counted.
CHART_MIN_SEASON_FGA = 300
GRID_ROW_PLAN = (3, 3, 2)
SEASON_MIN_ZONE_FGA = sm.MIN_ZONE12_FGA_PLAYER
# Twenty attempts per pooled season, so the tenure grey means what a season
# grey means.
TENURE_MIN_ZONE_FGA = SEASON_MIN_ZONE_FGA * len(SEASONS)
PROJECT = "lavine-bulls-zone-charts"
START_DATE = "2026-09-22"
SLUG = f"{START_DATE}-{PROJECT}"
TENURE_LABEL = "Bulls tenure"
TOTAL_COLUMNS = (
    "PLAYER_ID", "PLAYER_NAME", "TEAM_ABBREVIATION", "GP", "MIN",
    "PTS", "FGM", "FGA", "FG_PCT",
)
LOCATION_COLUMNS = ["loc_x", "loc_y", "shot_distance", "shot_zone",
                    "shot_zone_area"]


def fetch_bulls_totals(season: str) -> pd.Series:
    """Fetch the independent Chicago totals used to reconcile this post's shots."""
    return fetch.get_player_season_totals(
        PLAYER_ID, season, team_id=BULLS_TEAM_ID,
        columns=TOTAL_COLUMNS, player_name=PLAYER_NAME,
    )


def load_bulls_totals(season: str, data_dir: Path,
                      refresh: bool = False) -> pd.Series:
    path = data_dir / f"{season}-zach-lavine-bulls-totals.csv"
    if path.exists() and not refresh:
        row = pd.read_csv(path).iloc[0]
        if set(TOTAL_COLUMNS).issubset(row.index):
            if int(row.PLAYER_ID) != PLAYER_ID:
                raise ValueError(f"{season}: saved totals are not {PLAYER_NAME}")
            return row
    row = fetch_bulls_totals(season)
    out = row.to_frame().T
    out.insert(0, "season", season)
    out.to_csv(path, index=False)
    row = out.iloc[0]
    if int(row.PLAYER_ID) != PLAYER_ID:
        raise ValueError(f"{season}: saved totals are not {PLAYER_NAME}")
    return row


def reconcile_shots(season: str, totals: pd.Series,
                    shots: pd.DataFrame) -> None:
    """The raw pull must equal the official Chicago line, before any filtering.

    Checked on the raw frame on purpose. Reconciling after dropping unlocated
    rows would compare a number to itself and pass for a pull scoped to the
    wrong team, which is the one mistake this whole post is exposed to.
    """
    if len(shots) != int(totals.FGA):
        raise ValueError(
            f"{season}: shot rows {len(shots)} != Bulls FGA {int(totals.FGA)}"
        )
    makes = int(shots.shot_made.sum())
    if makes != int(totals.FGM):
        raise ValueError(
            f"{season}: shot makes {makes} != Bulls FGM {int(totals.FGM)}"
        )


def located_shots(label: str, shots: pd.DataFrame) -> tuple[pd.DataFrame, int]:
    """Drop only attempts with no location fields at all, and count them.

    Historical ShotChartDetail occasionally returns a valid make/miss and shot
    value with no x/y, distance, or NBA zone. Such a row belongs in scoring
    totals but cannot honestly contribute to a location chart. A row missing
    only SOME of those fields is a different thing -- a shape change in the feed
    rather than a known gap -- so it raises rather than being quietly dropped.

    LaVine has none: every one of his Chicago attempts carries a location.
    """
    unlocated = shots[LOCATION_COLUMNS].isna().all(axis=1)
    partial = shots[LOCATION_COLUMNS].isna().any(axis=1) & ~unlocated
    if partial.any():
        raise ValueError(
            f"{label}: {int(partial.sum())} rows have partially missing "
            "location data"
        )
    return shots.loc[~unlocated].copy(), int(unlocated.sum())


def load_bulls_shots(season: str, totals: pd.Series, data_dir: Path,
                     refresh: bool = False) -> pd.DataFrame:
    path = data_dir / f"{season}-zach-lavine-bulls-shots.csv"
    if path.exists() and not refresh:
        shots = pd.read_csv(path)
    else:
        shots = fetch.get_player_shots(
            PLAYER_ID, team_id=BULLS_TEAM_ID, season=season
        )
        if shots.empty:
            raise ValueError(
                f"NBA.com returned no {PLAYER_NAME} shots for {season}")
        shots.to_csv(path, index=False)
    reconcile_shots(season, totals, shots)
    return shots


def load_league_shots(season: str, refresh: bool = False) -> pd.DataFrame:
    """The season's league baseline, read from the shared cache and left there.

    Rose, DeRozan and Butler each copied every season's ~10 MB league pull into
    their own ``data/`` folder; Hinrich stopped, and so does this post. Over
    eight seasons that would be ~85 MB, and it duplicates the single dataset the repo
    names as shared: ``tests/test_data_locations.py`` justifies ``cache/shot_charts``
    as "league shot baseline behind the whole shot-chart family", and AGENTS.md
    lists it among the things that stay in the ignored cache precisely because no
    one post owns it.

    What must ship with the post is what the post alone can produce -- his shots,
    his totals, and the zone splits the slides print. Those are all written to
    ``data/``. The league baseline is refetchable by any of the family's scripts
    and belongs to none of them.
    """
    league = shot_data.league_shots(season, refresh)
    if league.empty:
        raise ValueError(f"NBA.com returned no league shots for {season}")
    return league


def collapse_to_source_family(zones: pd.Series) -> pd.Series:
    return zones.replace({
        "Left Baseline": "Mid-Range",
        "Left Mid-Range": "Mid-Range",
        "Center Mid-Range": "Mid-Range",
        "Right Mid-Range": "Mid-Range",
        "Right Baseline": "Mid-Range",
        "Left Wing 3": "Above the Break 3",
        "Top of Key 3": "Above the Break 3",
        "Right Wing 3": "Above the Break 3",
    })


def assert_source_family_reconciliation(season: str,
                                        shots: pd.DataFrame) -> None:
    custom = pd.Series(sm.zone12_of_shots(shots), index=shots.index)
    actual = collapse_to_source_family(custom).value_counts().sort_index()
    expected = shots.shot_zone.value_counts().sort_index()
    if actual.to_dict() != expected.to_dict():
        raise ValueError(
            f"{season}: custom zones crossed an NBA broad-zone family")


def summary_row(label: str, totals: pd.Series, shots: pd.DataFrame,
                zones: pd.DataFrame, min_zone_fga: int,
                unlocated_fga: int, league_unlocated_fga: int,
                charted: bool = True) -> dict[str, object]:
    overall = shot_chart._zone12_overall_metrics(shots)
    rated = zones[zones.rated]
    return {
        "window": label,
        "games": int(totals.GP),
        "minutes": round(float(totals.MIN), 1),
        "points": int(totals.PTS),
        "ppg": round(float(totals.PTS) / int(totals.GP), 1),
        "bulls_fga": int(totals.FGA),
        "shot_rows": len(shots),
        "fgm": int(shots.shot_made.sum()),
        "efg_pct": round(overall["efg_pct"], 1),
        "three_pct": round(overall["three_pct"], 1),
        "zones_rated": len(rated),
        "zones_grey": len(zones) - len(rated),
        "rated_fga_share_pct": round(rated.fga.sum() / len(shots) * 100, 1),
        "mapped_zone_fga": int(zones.fga.sum()),
        "excluded_backcourt_fga": int(zones.subject_excluded_fga.iloc[0]),
        "unlocated_fga": unlocated_fga,
        "source_zone_value_conflicts": int(
            zones.subject_source_conflict_fga.iloc[0]
        ),
        "league_zone_value_conflicts": int(
            zones.league_source_conflict_fga.iloc[0]
        ),
        "league_unlocated_fga": league_unlocated_fga,
        "min_zone_fga": min_zone_fga,
        "charted": charted,
        "scope": "Chicago attempts only",
    }


def pooled_totals(rows: list[pd.Series]) -> pd.Series:
    return pd.Series({
        "GP": sum(int(row.GP) for row in rows),
        "MIN": sum(float(row.MIN) for row in rows),
        "PTS": sum(int(row.PTS) for row in rows),
        "FGA": sum(int(row.FGA) for row in rows),
        "FGM": sum(int(row.FGM) for row in rows),
    })


def render(label: str, shots: pd.DataFrame, league: pd.DataFrame,
           min_zone_fga: int, output_dir: Path, final: bool,
           ppg: float, gp: int) -> Path:
    suffix = label.lower().replace("–", "-").replace(" ", "-")
    out = output_dir / f"{date.today().isoformat()}-zone-zach-lavine-{suffix}.png"
    shot_chart.render_zones(
        {
            "player": shots,
            "league": league,
            "name": PLAYER_NAME,
            "season": label,
            "min_fga": min_zone_fga,
            "pill": "large",
            "summary_metrics": True,
            "summary_ppg": ppg,
            # GP leads the summary so the injury-shortened seasons (24 games in
            # 2017-18, 25 in 2023-24) read as short at a glance.
            "summary_gp": gp,
        },
        out,
        final,
    )
    return out


def render_tenure_cover(shots: pd.DataFrame, league: pd.DataFrame,
                        min_zone_fga: int, output_dir: Path,
                        final: bool) -> Path:
    """The pooled tenure chart with every overlay suppressed -- the cover.

    A data-colour cover in DESIGN.md's sense: the fills are still an analytical
    claim, so it uses the same window, baseline, palette and floor as the tenure
    slide it opens for. A cover built to a looser floor would show a different
    chart from the one carrying the numbers several slides later, which is the
    kind of contradiction nobody catches until it is printed.

    Only the tenure chart gets one. Bare twins of each season were built for
    Hinrich and dropped: the season slides exist to carry their numbers, and a pill-free
    copy of each is a second set of assets with no page to live on.
    """
    label = TENURE_LABEL
    suffix = label.lower().replace("\u2013", "-").replace(" ", "-")
    out = output_dir / f"{date.today().isoformat()}-zone-zach-lavine-{suffix}-cover.png"
    shot_chart.render_zones(
        {
            "player": shots,
            "league": league,
            "name": PLAYER_NAME,
            "season": label,
            "min_fga": min_zone_fga,
            "show_details": False,
            "summary_metrics": False,
            "court_ink": shot_chart.ZONE12_COURT_INK,
        },
        out,
        final,
    )
    return out


def render_cover(by_season: dict[str, dict[str, pd.DataFrame]],
                 output_dir: Path, final: bool) -> Path:
    out = output_dir / f"{date.today().isoformat()}-zonegrid-zach-lavine-tenure.png"
    shot_chart.render_zonegrid(
        {
            "by_season": by_season,
            "min_fga": SEASON_MIN_ZONE_FGA,
            # Three to a row, with the tenth hanging left under the stack. Three
            # wide is what buys the size: the courts come out 335 px against the
            # 248 a four-wide row allows, because four of them squeeze the page
            # width while three leave room to grow into. The odd court is left
            # aligned rather than centred so the columns stay true and it reads
            # as the next season in sequence.
            "row_plan": GRID_ROW_PLAN,
            "align": "left",
        },
        out,
        final,
    )
    return out


def build(args: argparse.Namespace) -> list[Path]:
    args.output_dir.mkdir(parents=True, exist_ok=True)
    args.data_dir.mkdir(parents=True, exist_ok=True)
    outputs, summaries, splits = [], [], []
    all_shots, all_league, all_totals = [], [], []
    by_season: dict[str, dict[str, pd.DataFrame]] = {}

    for season in SEASONS:
        print(f"\n{'=' * 72}\n{season}")
        totals = load_bulls_totals(season, args.data_dir, args.refresh)
        raw_shots = load_bulls_shots(season, totals, args.data_dir, args.refresh)
        shots, unlocated = located_shots(season, raw_shots)
        raw_league = load_league_shots(season, args.refresh_league)
        league, league_unlocated = located_shots(f"{season} league", raw_league)
        assert_source_family_reconciliation(season, shots)
        zones = sm.zone12_split(shots, league, min_fga=SEASON_MIN_ZONE_FGA)
        audit = zones.copy()
        audit.insert(0, "window", season)
        splits.append(audit)
        charted = int(totals.FGA) >= CHART_MIN_SEASON_FGA
        summaries.append(summary_row(
            season, totals, shots, zones, SEASON_MIN_ZONE_FGA,
            unlocated, league_unlocated, charted,
        ))
        if charted:
            outputs.append(render(
                season, shots, league, SEASON_MIN_ZONE_FGA,
                args.output_dir, args.final,
                float(totals.PTS) / int(totals.GP), int(totals.GP),
            ))
            by_season[season] = {"subject": shots, "league": league}
        else:
            print(f"{season}: {int(totals.FGA)} Chicago FGA, under "
                  f"{CHART_MIN_SEASON_FGA} -- no chart, pooled into the tenure")
        all_shots.append(shots.assign(source_season=season))
        all_league.append(league.assign(source_season=season))
        all_totals.append(totals)

    tenure_shots = pd.concat(all_shots, ignore_index=True)
    # The pooled league is the same eight seasons stacked, so the tenure chart
    # compares him with the era he actually played in rather than with a single
    # borrowed year. Weighting each season's league contribution by HIS attempts
    # that season was tested as the more careful alternative and moved no zone's
    # league FG% by more than 0.21 points for Hinrich -- well inside the chart's
    # +/-2.5 band. Plain pooling is kept because it is the version a reader can
    # reproduce from the saved files.
    tenure_league = pd.concat(all_league, ignore_index=True)
    tenure_zones = sm.zone12_split(
        tenure_shots, tenure_league, min_fga=TENURE_MIN_ZONE_FGA
    )
    audit = tenure_zones.copy()
    audit.insert(0, "window", TENURE_LABEL)
    splits.append(audit)
    totals = pooled_totals(all_totals)
    summaries.append(summary_row(
        TENURE_LABEL, totals, tenure_shots, tenure_zones, TENURE_MIN_ZONE_FGA,
        sum(int(row["unlocated_fga"]) for row in summaries),
        sum(int(row["league_unlocated_fga"]) for row in summaries),
    ))
    outputs.append(render(
        TENURE_LABEL, tenure_shots, tenure_league, TENURE_MIN_ZONE_FGA,
        args.output_dir, args.final,
        float(totals.PTS) / int(totals.GP), int(totals.GP),
    ))
    outputs.append(render_tenure_cover(tenure_shots, tenure_league,
                                       TENURE_MIN_ZONE_FGA, args.output_dir,
                                       args.final))
    outputs.append(render_cover(by_season, args.output_dir, args.final))

    summary = pd.DataFrame(summaries)
    summary.to_csv(args.data_dir / "zone-chart-summary.csv", index=False)
    pd.concat(splits, ignore_index=True).to_csv(
        args.data_dir / "zone-splits.csv", index=False, float_format="%.4f"
    )
    print("\nZACH LAVINE BULLS ZONE SUMMARY")
    print(summary.to_string(index=False))
    print("\nCANVA COPY")
    charted = [row["window"] for row in summaries[:-1] if row["charted"]]
    print("Title: Zach LaVine as a Bull, season by season")
    print(f"Coverage: {len(SEASONS)} Chicago regular seasons, "
          f"{SEASONS[0]} to {SEASONS[-1]}")
    print(f"Charted seasons: {len(charted)} of {len(SEASONS)} · "
          f"{CHART_MIN_SEASON_FGA}+ Chicago FGA")
    print("Season qualifier: Grey zones are under 20 FGA")
    print(f"Tenure qualifier: Grey zones are under {TENURE_MIN_ZONE_FGA} FGA "
          f"(20 × {len(SEASONS)} seasons)")
    print("2024-25 note: Chicago games only (traded to Sacramento 2025-02-03)")
    print("Source: NBA.com/stats · Chicago attempts only")
    return outputs


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--refresh", action="store_true")
    parser.add_argument("--refresh-league", action="store_true")
    parser.add_argument("--final", action="store_true")
    parser.add_argument(
        "--output-dir", type=Path, default=ROOT / "output" / PROJECT
    )
    parser.add_argument(
        "--data-dir", type=Path,
        default=ROOT / "docs" / "visuals" / SLUG / "data",
    )
    return parser.parse_args()


if __name__ == "__main__":
    build(parse_args())
