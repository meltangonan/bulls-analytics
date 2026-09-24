"""Audit Bulls player-season field-goal leaders in two-foot distance bands."""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from bulls.graphics.court import HALFCOURT_Y


ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "docs/visuals/2026-09-23-distance-band-fgm/data"
RAW = DATA / "shotchartdetail"
SEASONS = [f"{year}-{(year + 1) % 100:02d}" for year in range(1997, 2026)]
TEAM_ID = 1610612741
REQUIRED = {
    "GAME_ID", "GAME_EVENT_ID", "PLAYER_ID", "PLAYER_NAME", "TEAM_ID",
    "SHOT_TYPE", "SHOT_DISTANCE", "SHOT_MADE_FLAG", "LOC_X", "LOC_Y",
}


def load_shots() -> pd.DataFrame:
    frames = []
    for season in SEASONS:
        path = RAW / f"{season}.csv.gz"
        shots = pd.read_csv(path)
        missing = REQUIRED - set(shots.columns)
        if missing:
            raise ValueError(f"{season}: missing columns {sorted(missing)}")
        if not shots.TEAM_ID.eq(TEAM_ID).all():
            raise ValueError(f"{season}: non-Bulls shots found")
        if not shots.SHOT_MADE_FLAG.isin([0, 1]).all():
            raise ValueError(f"{season}: invalid make flags")
        shots["season"] = season
        frames.append(shots)
    return pd.concat(frames, ignore_index=True)


def reconcile(shots: pd.DataFrame) -> pd.DataFrame:
    official = pd.read_csv(DATA / "official-team-totals.csv")
    observed = shots.assign(
        is_three=shots.SHOT_TYPE.eq("3PT Field Goal"),
    ).groupby("season", as_index=False).agg(
        FGA=("SHOT_MADE_FLAG", "size"),
        FGM=("SHOT_MADE_FLAG", "sum"),
        FG3A=("is_three", "sum"),
    )
    threes = shots[shots.SHOT_TYPE.eq("3PT Field Goal")].groupby("season")[
        "SHOT_MADE_FLAG"
    ].sum().rename("FG3M")
    observed = observed.join(threes, on="season")
    comparison = observed.merge(official, on="season", suffixes=("_shots", "_official"))
    if len(comparison) != len(SEASONS):
        raise ValueError("official comparison is missing a season")
    for stat in ("FGA", "FGM", "FG3A", "FG3M"):
        if not comparison[f"{stat}_shots"].eq(comparison[f"{stat}_official"]).all():
            bad = comparison.loc[
                comparison[f"{stat}_shots"].ne(comparison[f"{stat}_official"]), "season"
            ].tolist()
            raise ValueError(f"{stat} differs from official totals: {bad}")
    return comparison


def build_table(shots: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    invalid_location = shots.SHOT_DISTANCE.isna() | shots.LOC_X.isna() | shots.LOC_Y.isna()
    if not shots.loc[~invalid_location, "SHOT_DISTANCE"].ge(0).all():
        raise ValueError("negative shot distance")
    excluded = shots.assign(
        missing_location=invalid_location,
        missing_location_made=invalid_location & shots.SHOT_MADE_FLAG.eq(1),
        beyond_30=shots.SHOT_DISTANCE.ge(30),
        beyond_30_made=shots.SHOT_DISTANCE.ge(30) & shots.SHOT_MADE_FLAG.eq(1),
    ).groupby("season", as_index=False).agg(
        missing_location=("missing_location", "sum"),
        missing_location_made=("missing_location_made", "sum"),
        beyond_30=("beyond_30", "sum"),
        beyond_30_made=("beyond_30_made", "sum"),
    )
    valid = shots.loc[~invalid_location & shots.SHOT_DISTANCE.lt(30)].copy()
    valid["band_start_ft"] = valid.SHOT_DISTANCE.astype(int).floordiv(2).mul(2)
    valid["is_three"] = valid.SHOT_TYPE.eq("3PT Field Goal")
    valid["three_made"] = valid.is_three & valid.SHOT_MADE_FLAG.eq(1)
    grouped = valid.groupby(
        ["band_start_ft", "PLAYER_ID", "PLAYER_NAME", "season"], as_index=False
    ).agg(
        FGA=("SHOT_MADE_FLAG", "size"),
        FGM=("SHOT_MADE_FLAG", "sum"),
        three_made=("three_made", "sum"),
    )
    grouped["two_made"] = grouped.FGM - grouped.three_made
    grouped["points_from_field_goals"] = 2 * grouped.two_made + 3 * grouped.three_made
    grouped["PPS"] = grouped.points_from_field_goals / grouped.FGA
    grouped["band"] = grouped.band_start_ft.astype(str) + "–" + (
        grouped.band_start_ft + 2
    ).astype(str) + " ft"
    grouped = grouped.sort_values(
        ["band_start_ft", "FGM", "FGA", "PLAYER_NAME", "season"],
        ascending=[True, False, True, True, True],
    )
    max_makes = grouped.groupby("band_start_ft").FGM.transform("max")
    tied_leaders = grouped.loc[grouped.FGM.eq(max_makes)].copy()
    leaders = (tied_leaders.sort_values(
        ["band_start_ft", "PPS", "FGA", "PLAYER_ID", "season"],
        ascending=[True, False, True, True, True],
    ).drop_duplicates("band_start_ft").copy())
    if set(leaders.band_start_ft) != set(range(0, 30, 2)) or len(leaders) != 15:
        raise ValueError("a distance band has no leader")
    return grouped, leaders, tied_leaders, excluded


def build_30_plus(shots: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Keep the unbounded group separate from the two-foot court bands."""
    valid = shots.loc[
        shots.SHOT_DISTANCE.ge(30) & shots.LOC_X.notna() & shots.LOC_Y.notna()
    ].copy()
    valid["three_made"] = (
        valid.SHOT_TYPE.eq("3PT Field Goal") & valid.SHOT_MADE_FLAG.eq(1)
    )
    grouped = valid.groupby(
        ["PLAYER_ID", "PLAYER_NAME", "season"], as_index=False
    ).agg(
        FGA=("SHOT_MADE_FLAG", "size"),
        FGM=("SHOT_MADE_FLAG", "sum"),
        three_made=("three_made", "sum"),
    )
    grouped["two_made"] = grouped.FGM - grouped.three_made
    grouped["points_from_field_goals"] = 2 * grouped.two_made + 3 * grouped.three_made
    grouped["PPS"] = grouped.points_from_field_goals / grouped.FGA
    grouped["band"] = "30+ ft"
    grouped = grouped.sort_values(
        ["FGM", "FGA", "PLAYER_NAME", "season"],
        ascending=[False, True, True, True],
    )
    leaders = grouped.loc[grouped.FGM.eq(grouped.FGM.max())].copy()
    return grouped, leaders


def build_30_to_halfcourt(shots: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """30+ ft radially, stopped at the straight midcourt line."""
    located = shots.loc[
        shots.SHOT_DISTANCE.ge(30) & shots.LOC_X.notna() & shots.LOC_Y.notna()
    ].copy()
    if located.LOC_X.abs().gt(250).any():
        raise ValueError("30+ ft shot outside the 50-foot court width")
    located["inside_halfcourt"] = located.LOC_Y.lt(HALFCOURT_Y)
    audit = located.assign(
        inside_made=located.inside_halfcourt & located.SHOT_MADE_FLAG.eq(1),
        beyond_made=~located.inside_halfcourt & located.SHOT_MADE_FLAG.eq(1),
    ).groupby("season", as_index=False).agg(
        all_30_plus_fga=("SHOT_MADE_FLAG", "size"),
        all_30_plus_fgm=("SHOT_MADE_FLAG", "sum"),
        inside_halfcourt_fga=("inside_halfcourt", "sum"),
        inside_halfcourt_fgm=("inside_made", "sum"),
        beyond_halfcourt_fgm=("beyond_made", "sum"),
    )
    audit["beyond_halfcourt_fga"] = (
        audit.all_30_plus_fga - audit.inside_halfcourt_fga
    )
    player_seasons, tied = build_30_plus(located.loc[located.inside_halfcourt])
    player_seasons["band"] = "30 ft–half court"
    winner = (tied.sort_values(
        ["PPS", "FGA", "PLAYER_ID", "season"],
        ascending=[False, True, True, True],
    ).head(1).copy())
    winner["band"] = "30 ft–half court"
    return player_seasons, winner, audit


def main() -> None:
    shots = load_shots()
    reconciliation = reconcile(shots)
    player_seasons, leaders, tied_leaders, excluded = build_table(shots)
    long_player_seasons, long_leaders = build_30_plus(shots)
    halfcourt_player_seasons, halfcourt_leader, halfcourt_audit = build_30_to_halfcourt(shots)
    DATA.mkdir(parents=True, exist_ok=True)
    reconciliation.to_csv(DATA / "source-reconciliation.csv", index=False)
    excluded.to_csv(DATA / "location-exclusions.csv", index=False)
    player_seasons.to_csv(DATA / "all-player-seasons.csv", index=False)
    leaders.to_csv(DATA / "distance-band-leaders.csv", index=False)
    tied_leaders.to_csv(DATA / "distance-band-fgm-ties.csv", index=False)
    long_player_seasons.to_csv(DATA / "30-plus-player-seasons.csv", index=False)
    long_leaders.to_csv(DATA / "30-plus-leaders.csv", index=False)
    halfcourt_player_seasons.to_csv(DATA / "30-to-halfcourt-player-seasons.csv", index=False)
    halfcourt_leader.to_csv(DATA / "30-to-halfcourt-leader.csv", index=False)
    halfcourt_audit.to_csv(DATA / "30-to-halfcourt-audit.csv", index=False)
    carousel = pd.concat([leaders, halfcourt_leader], ignore_index=True)
    carousel[["band", "PLAYER_NAME", "season", "FGM", "FGA", "PPS"]].to_csv(
        DATA / "carousel-values.csv", index=False
    )
    print(leaders[[
        "band", "PLAYER_NAME", "season", "FGM", "FGA", "PPS", "two_made", "three_made"
    ]].to_string(index=False, formatters={"PPS": "{:.3f}".format}))
    print("\n30+ feet:")
    print(long_leaders[["PLAYER_NAME", "season", "FGM", "FGA", "PPS"]].to_string(
        index=False, formatters={"PPS": "{:.3f}".format}
    ))
    print("\n30 ft to half court:")
    print(halfcourt_leader[["PLAYER_NAME", "season", "FGM", "FGA", "PPS"]].to_string(
        index=False, formatters={"PPS": "{:.3f}".format}
    ))


if __name__ == "__main__":
    main()
