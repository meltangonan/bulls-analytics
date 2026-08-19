"""Reconcile the hand-captured databallr on/off snapshot against our own fetch.

On/off is the one column that does not come from NBA.com: the league's endpoint
serves nothing before 2007-08, so the numbers were read off databallr's public
On-Off view and stored as a snapshot. Hand-captured data earns its place only if
it reconciles, so this asserts the overlap we can check — games and minutes —
against the NBA.com rows the rest of the table is built from.
"""

from __future__ import annotations

import pandas as pd
import pytest

from scripts.prototypes.bulls_rookie_chronological_table import (
    MIN_IMPACT_MINUTES,
    MIN_MINUTES,
    ON_OFF_CSV,
)
from scripts.prototypes.bulls_rookie_metric_analysis import NBA_RAW_CSV, normalize_name


@pytest.fixture(scope="module")
def joined() -> pd.DataFrame:
    snapshot = pd.read_csv(ON_OFF_CSV)
    ours = pd.read_csv(NBA_RAW_CSV)
    ours = ours[ours["minutes"].ge(MIN_MINUTES)].copy()
    snapshot["key"] = snapshot["player_name"].map(normalize_name)
    ours["key"] = ours["player_name"].map(normalize_name)
    return ours.merge(
        snapshot[["season", "key", "games", "minutes", "net_on", "net_on_off"]],
        on=["season", "key"],
        how="left",
        suffixes=("", "_databallr"),
        validate="one_to_one",
    )


def test_every_qualified_rookie_was_captured(joined):
    missing = joined.loc[joined["net_on_off"].isna(), "player_name"]
    assert not len(missing), f"no captured on/off row for {sorted(missing)}"


def test_games_played_agree_exactly(joined):
    """Both sides read NBA.com's box score, so games must match to the row."""
    assert (joined["games"] == joined["games_databallr"]).all()


def test_minutes_agree_to_rounding(joined):
    """databallr prints whole minutes; ours carry NBA.com's decimals."""
    assert (joined["minutes"] - joined["minutes_databallr"]).abs().max() < 1.0


def test_on_court_net_rating_tracks_our_own_fetch(joined):
    """Different lineup derivations, so allow a gap, but not a different stat."""
    assert joined["net_rating"].corr(joined["net_on"]) > 0.9


def test_the_blanking_floor_still_leaves_most_of_the_table_populated(joined):
    shown = joined["minutes"].ge(MIN_IMPACT_MINUTES).sum()
    assert shown == 32
    assert len(joined) - shown == 14
