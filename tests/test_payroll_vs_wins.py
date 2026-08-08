"""Reconciliation guards for the hand-captured payroll snapshot.

The snapshot in ``data/`` is transcribed by hand from two sites that block
scripted access, so nothing downstream can re-derive it. These tests stand in
for that missing fetch: each one restates a fact the sources publish
independently, so a transcription slip -- or a repeat of the source error found
on 2026-08-08 -- fails the suite instead of shipping a wrong bar.
"""

import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts" / "prototypes"))

from payroll_vs_wins import load_seasons  # noqa: E402

SEASONS = load_seasons()

# Basketball Reference's NBA Salary Cap History page, transcribed independently
# of the payroll figures. Spotrac's own implied cap (Total Cap Allocations +
# Cap Space) matched every one of these exactly on capture day; that agreement
# between two unrelated sources is the strongest check in the dataset.
CAP_HISTORY = {
    "2011-12": 58_044_000,
    "2012-13": 58_044_000,
    "2013-14": 58_679_000,
    "2014-15": 63_065_000,
    "2015-16": 70_000_000,
    "2016-17": 94_143_000,
    "2017-18": 99_093_000,
    "2018-19": 101_869_000,
    "2019-20": 109_140_000,
    "2020-21": 109_140_000,
    "2021-22": 112_414_000,
    "2022-23": 123_655_000,
    "2023-24": 136_021_000,
    "2024-25": 140_588_000,
    "2025-26": 154_647_000,
}

# Scheduled games per season. The three short years are the 2011-12 lockout,
# the 2019-20 COVID stoppage, and the 2020-21 compressed season.
SCHEDULED_GAMES = {"2011-12": 66, "2019-20": 65, "2020-21": 72}


def test_covers_fifteen_consecutive_seasons():
    """Spotrac's cap tracker starts at 2011-12; a gap would mean a dropped row."""
    seasons = [s.season for s in SEASONS]
    assert seasons == list(CAP_HISTORY)


@pytest.mark.parametrize("season", SEASONS, ids=lambda s: s.season)
def test_salary_cap_matches_published_history(season):
    assert season.salary_cap == CAP_HISTORY[season.season]


@pytest.mark.parametrize("season", SEASONS, ids=lambda s: s.season)
def test_games_played_matches_the_schedule(season):
    """Catches a record transcribed from the wrong season.

    Spotrac's own Record column is the previous season's on archived pages, so
    this is the specific mistake most likely to recur.
    """
    assert season.games == SCHEDULED_GAMES.get(season.season, 82)


@pytest.mark.parametrize("season", SEASONS, ids=lambda s: s.season)
def test_dead_cap_is_a_component_of_payroll(season):
    assert 0 <= season.dead_cap <= season.payroll


@pytest.mark.parametrize("season", SEASONS, ids=lambda s: s.season)
def test_cap_share_stays_in_a_believable_band(season):
    """A team cannot spend far outside this range and remain a going concern.

    The 2015-16 source error produced 146%, well past the top of the band; a
    structural bound like this is what catches a wrong financial figure, because
    the figure itself looks plausible in isolation.
    """
    assert 0.80 <= season.cap_share <= 1.35


def test_2015_16_uses_the_corrected_payroll():
    """Regression guard for the source error found on 2026-08-08.

    Spotrac publishes $102,184,130 for this season from an 18-player table in a
    15-man roster. Robin Lopez, Jerian Grant, and Spencer Dinwiddie all joined
    Chicago in the *following* offseason and are absent from Basketball
    Reference's 2015-16 roster. Removing them yields $86,783,378, matching the
    Patricia Bender salary archive to the dollar; the figure below adds the
    $333,333 of dead money Spotrac reports separately.
    """
    season = next(s for s in SEASONS if s.season == "2015-16")
    spotrac_published = 102_184_130
    bender_archive = 86_783_378

    assert season.payroll != spotrac_published
    assert season.payroll == bender_archive + season.dead_cap
    assert season.dead_cap == 333_333


def test_2015_16_sits_just_over_the_luxury_tax_line():
    """Independent sanity check on the correction.

    The Bulls are reported to have paid a modest luxury tax in 2015-16. The
    corrected payroll clears the $84.74M tax line by a little; Spotrac's
    inflated figure would have cleared it by $17M and implied a tax bill larger
    than the franchise has paid in its history.
    """
    season = next(s for s in SEASONS if s.season == "2015-16")
    tax_line = 84_740_000
    assert tax_line < season.payroll < tax_line + 5_000_000


def test_snapshot_documents_its_sources():
    """The provenance header is the only record of how these numbers were made."""
    header = [
        line
        for line in (
            REPO
            / "docs"
            / "visuals"
            / "2026-08-08-payroll-vs-wins"
            / "data"
            / "2026-08-08-bulls-payroll-vs-wins.csv"
        )
        .read_text()
        .splitlines()
        if line.startswith("#")
    ]
    text = "\n".join(header)
    assert "spotrac.com/nba/cap" in text
    assert "basketball-reference.com" in text
    assert "DO NOT USE SPOTRAC'S \"RECORD\" COLUMN" in text
    assert "CORRECTION" in text
