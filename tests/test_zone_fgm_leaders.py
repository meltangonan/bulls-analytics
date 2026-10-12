"""Ranking rules, zone guards, and saved-value checks for the zone FGM leaders post.

The saved-data tests pin the published numbers to their source trail: every
displayed leader must be the top of its zone in the full ranking table, every
league season must reconcile with official totals, and the worked example on
the Notion page must reproduce from the saved split.
"""
from pathlib import Path

import pandas as pd
import pytest

from bulls.analysis import shot_maps as sm
from scripts.prototypes import zone_fgm_leaders as leaders


DATA = Path(__file__).resolve().parents[1] / "docs" / "visuals" / leaders.SLUG / "data"


def shots(rows):
    """Zoned shot rows: (zone, player_id, name, season, made)."""
    return pd.DataFrame(rows, columns=[
        "zone", "player_id", "player_name", "season", "shot_made"])


def all_zones_once():
    """One make per zone by a filler player, so every zone has a leader."""
    return [(zone, 99, "Filler", "1997-98", True) for zone in sm.ZONE12_ORDER]


def test_most_makes_wins_and_a_tie_goes_to_fewer_attempts():
    rows = all_zones_once() + [
        ("Top of Key 3", 1, "Volume", "2001-02", made) for made in (1, 1, 0, 0)
    ] + [
        ("Top of Key 3", 2, "Efficient", "2002-03", made) for made in (1, 1, 0)
    ]
    table, top, ties = leaders.rank(shots(rows))
    zone = top.set_index("zone").loc["Top of Key 3"]
    # Both made two; the higher FG% (two of three) takes the tie.
    assert zone.player_name == "Efficient"
    assert set(ties.loc[ties.zone.eq("Top of Key 3"), "player_name"]) == {
        "Volume", "Efficient"}
    assert int(zone.FGM) == 2 and int(zone.FGA) == 3


def test_season_scope_keeps_player_seasons_apart():
    rows = all_zones_once() + [
        ("Restricted Area", 1, "Deng", season, True)
        for season in ("2005-06", "2005-06", "2006-07", "2006-07")
    ] + [("Restricted Area", 2, "Rose", "2010-11", True)] * 3
    _, top, _ = leaders.rank(shots(rows))
    assert top.set_index("zone").loc["Restricted Area"].player_name == "Rose"


def test_tenure_scope_pools_a_players_seasons():
    rows = all_zones_once() + [
        ("Restricted Area", 1, "Deng", season, True)
        for season in ("2005-06", "2005-06", "2006-07", "2006-07")
    ] + [("Restricted Area", 2, "Rose", "2010-11", True)] * 3
    _, top, _ = leaders.rank(shots(rows), tenure=True)
    rim = top.set_index("zone").loc["Restricted Area"]
    assert rim.player_name == "Deng"
    assert int(rim.FGM) == 4 and int(rim.seasons) == 2
    assert rim.season == "2005-06 to 2006-07"


def test_a_zone_without_any_make_or_attempt_fails_loudly():
    rows = [(zone, 99, "Filler", "1997-98", True) for zone in sm.ZONE12_ORDER[:-1]]
    with pytest.raises(ValueError, match="a zone has no leader"):
        leaders.rank(shots(rows))


def test_custom_zone_must_agree_with_nba_side_label():
    """A baseline shot labelled by NBA as the other side means a mirrored axis."""
    zoned = pd.DataFrame({
        "zone": ["Left Baseline"], "shot_zone": ["Mid-Range"],
        "shot_zone_area": ["Right Side(R)"],
    })
    with pytest.raises(ValueError, match="side label"):
        leaders.assert_family_and_side(zoned)


def test_custom_zone_must_stay_inside_nba_family():
    zoned = pd.DataFrame({
        "zone": ["Top of Key 3"], "shot_zone": ["Mid-Range"],
        "shot_zone_area": ["Center(C)"],
    })
    with pytest.raises(ValueError, match="broad-zone family"):
        leaders.assert_family_and_side(zoned)


@pytest.mark.parametrize("prefix, table", [
    ("", "all-player-seasons.csv"),
    ("tenure-", "tenure-all-player-tenures.csv"),
])
def test_saved_leaders_top_their_zone_in_the_full_table(prefix, table):
    values = pd.read_csv(DATA / f"{prefix}carousel-values.csv")
    full = pd.read_csv(DATA / table)
    assert list(values.zone) == list(sm.ZONE12_ORDER)
    best = full.groupby("zone").FGM.max()
    for row in values.itertuples():
        assert row.FGM == best[row.zone]
        # No zone has a tie for first in either scope; a tie would need its
        # tiebreak stated on the page.
        assert (full.loc[full.zone.eq(row.zone), "FGM"] == row.FGM).sum() == 1


def test_saved_single_season_leaders_match_the_published_page():
    values = pd.read_csv(DATA / "carousel-values.csv").set_index("zone")
    expected = {
        "Restricted Area": ("Derrick Rose", "2010-11", 315, 542),
        "In The Paint (Non-RA)": ("Elton Brand", "1999-00", 211, 460),
        "Left Baseline": ("Elton Brand", "2000-01", 82, 211),
        "Left Mid-Range": ("Michael Jordan", "1997-98", 104, 244),
        "Center Mid-Range": ("DeMar DeRozan", "2021-22", 141, 278),
        "Right Mid-Range": ("Michael Jordan", "1997-98", 135, 301),
        "Right Baseline": ("Michael Jordan", "1997-98", 106, 241),
        "Left Corner 3": ("Matas Buzelis", "2024-25", 35, 81),
        "Left Wing 3": ("Coby White", "2024-25", 81, 210),
        "Top of Key 3": ("Nikola Vučević", "2024-25", 78, 187),
        "Right Wing 3": ("Ben Gordon", "2005-06", 58, 118),
        "Right Corner 3": ("Ayo Dosunmu", "2023-24", 37, 95),
    }
    for zone, (name, season, fgm, fga) in expected.items():
        row = values.loc[zone]
        assert (row.player_name, row.season, row.FGM, row.FGA) == (name, season, fgm, fga)


def test_worked_example_reproduces_from_saved_split():
    """DeRozan 2021-22 center mid-range, as printed in the Notion provenance."""
    splits = pd.read_csv(DATA / "leader-zone-splits.csv")
    row = splits.loc[splits.leader_zone.eq("Center Mid-Range")
                     & splits.zone.eq("Center Mid-Range")].iloc[0]
    assert (row.fgm, row.fga) == (141, 278)
    assert round(row.fg * 100, 1) == 50.7
    assert round(row.fg_rel, 1) == 8.3
    assert round(row.fga_share_pct, 1) == 18.1
    assert round(row.fga_share_pct - row.lg_fga_share_pct, 1) == 14.8
    # The share denominator is every Chicago attempt that season, backcourt included.
    values = pd.read_csv(DATA / "carousel-values.csv").set_index("zone")
    assert values.loc["Center Mid-Range", "player_window_FGA"] == 1535
    assert round(141 / 1535 * 100, 1) == 9.2  # makes share, a different number
    assert round(278 / 1535 * 100, 1) == round(row.fga_share_pct, 1)


def test_every_saved_league_season_reconciles_with_official_totals():
    check = pd.read_csv(DATA / "league-source-reconciliation.csv")
    manifest = pd.read_csv(DATA / "league-source-manifest.csv")
    assert set(check.season) == set(manifest.season)
    assert check.shot_rows.eq(check.FGA).all()
    assert check.shot_makes.eq(check.FGM).all()


def test_tenure_league_baseline_covers_every_leader_season():
    """A pooled comparison needs the league from each season the player is pooled over."""
    values = pd.read_csv(DATA / "tenure-carousel-values.csv")
    full = pd.read_csv(DATA / "tenure-all-player-tenures.csv")
    saved = set(pd.read_csv(DATA / "league-source-manifest.csv").season)
    seasons = pd.read_csv(DATA / "all-player-seasons.csv")
    for row in values.itertuples():
        played = set(seasons.loc[seasons.player_id.eq(row.player_id), "season"])
        assert played <= saved
        assert row.seasons == len(played)
    assert len(full) > len(values)
