"""Reconciliation guards for the national-TV schedule-release snapshot."""

import csv
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts" / "prototypes"))

from bulls_national_tv_history import (  # noqa: E402
    CURRENT_BAR_GRADIENT,
    CURRENT_GAMES,
    HISTORICAL_BAR_GRADIENT,
    NETWORK_FIELDS,
    SNAPSHOT,
    load_current_comparison,
    load_seasons,
    order_seasons,
)

SEASONS = load_seasons()
PROJECT_DATA = SNAPSHOT.parent

EXPECTED_TOTALS = {
    "2010-11": 18,
    "2011-12": 22,
    "2012-13": 19,
    "2013-14": 24,
    "2014-15": 25,
    "2015-16": 23,
    "2016-17": 25,
    "2017-18": 1,
    "2018-19": 2,
    "2019-20": 1,
    "2020-21": 3,
    "2021-22": 5,
    "2022-23": 10,
    "2023-24": 4,
    "2024-25": 2,
    "2025-26": 3,
    "2026-27": 3,
}

BULLS_RELEASE_PRIMARY_SEASONS = {
    "2010-11",
    "2011-12",
    "2012-13",
    "2013-14",
    "2014-15",
    "2015-16",
    "2016-17",
    "2017-18",
    "2018-19",
    "2019-20",
    "2020-21",
    "2022-23",
    "2023-24",
    "2024-25",
    "2025-26",
    "2026-27",
}


def test_covers_every_season_from_2010_11_through_2026_27():
    assert [season.season for season in SEASONS] == list(EXPECTED_TOTALS)


def test_descending_chart_order_puts_the_current_season_first():
    ordered = order_seasons(SEASONS, descending=True)
    assert ordered[0].season == "2026-27"
    assert ordered[-1].season == "2010-11"
    assert {season.season for season in ordered} == set(EXPECTED_TOTALS)


def test_current_season_red_gradient_is_distinct_from_black_history():
    assert CURRENT_BAR_GRADIENT != HISTORICAL_BAR_GRADIENT
    for gradient in (CURRENT_BAR_GRADIENT, HISTORICAL_BAR_GRADIENT):
        assert all(color.startswith("#") and len(color) == 7 for color in gradient)


@pytest.mark.parametrize("season", SEASONS, ids=lambda season: season.season)
def test_total_matches_audited_release_count(season):
    assert season.total == EXPECTED_TOTALS[season.season]


@pytest.mark.parametrize("season", SEASONS, ids=lambda season: season.season)
def test_network_components_sum_to_total(season):
    assert season.network_sum == season.total


def test_old_and_new_media_eras_do_not_mix_network_definitions():
    old_fields = ("nbc", "nbcsn", "peacock", "prime_video")
    new_obsolete_field = "tnt"
    for season in SEASONS:
        if season.season <= "2024-25":
            assert all(getattr(season, field) == 0 for field in old_fields)
        else:
            assert getattr(season, new_obsolete_field) == 0


def test_pandemic_season_is_the_only_split_release():
    split = [season.season for season in SEASONS if season.release_type == "split"]
    assert split == ["2020-21"]


def test_current_game_rows_reconcile_to_current_total_and_networks():
    with CURRENT_GAMES.open(encoding="utf-8") as handle:
        rows = list(csv.DictReader(line for line in handle if not line.startswith("#")))
    assert len(rows) == EXPECTED_TOTALS["2026-27"]
    assert {row["primary_network"] for row in rows} == {"NBC", "Peacock", "ESPN"}
    assert {row["simulcast"] for row in rows} == {
        "Peacock",
        "NBCSN",
        "ESPN streaming app",
    }
    assert len({row["matchup"] for row in rows}) == len(rows)


def test_2025_26_rows_reconcile_to_dated_official_pdf():
    path = PROJECT_DATA / "bulls-2025-26-national-games.csv"
    with path.open(encoding="utf-8") as handle:
        rows = list(csv.DictReader(line for line in handle if not line.startswith("#")))
    assert len(rows) == EXPECTED_TOTALS["2025-26"]
    assert {row["network"] for row in rows} == {"ESPN", "Peacock", "Prime Video"}
    assert [row["pdf_page"] for row in rows] == ["1", "2", "3"]


def test_2024_25_rows_reconcile_to_original_release_pdf():
    path = PROJECT_DATA / "bulls-2024-25-national-games.csv"
    with path.open(encoding="utf-8") as handle:
        rows = list(csv.DictReader(line for line in handle if not line.startswith("#")))
    assert len(rows) == EXPECTED_TOTALS["2024-25"]
    assert {row["network"] for row in rows} == {"ESPN"}
    assert {row["date"] for row in rows} == {"2024-11-20", "2025-01-17"}


def test_current_comparison_matches_release_day_counts():
    assert load_current_comparison() == {"Chicago Bulls": 3, "New York Knicks": 34}


def test_snapshot_documents_definition_capture_date_and_sources():
    text = SNAPSHOT.read_text(encoding="utf-8")
    header = "\n".join(line for line in text.splitlines() if line.startswith("#"))
    assert "Captured 2026-08-13" in header
    assert "NBA TV" in header
    assert "later flex" in header
    assert "2020-21" in header
    assert "sportsmediawatch.com" not in text.lower()
    for season in SEASONS:
        assert season.source_url.startswith("https://")
        assert season.source_note
        assert all(getattr(season, field) >= 0 for field in NETWORK_FIELDS)


def test_bulls_release_is_primary_whenever_one_was_found():
    for season in SEASONS:
        if season.season in BULLS_RELEASE_PRIMARY_SEASONS:
            assert "nba.com/bulls/" in season.source_url


def test_2021_22_uses_first_party_fallback_not_a_media_report():
    season = next(season for season in SEASONS if season.season == "2021-22")
    assert season.source_url.startswith("https://www.nba.com/")
    assert "Bulls media-guide" in season.source_note
