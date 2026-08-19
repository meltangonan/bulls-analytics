"""Tests for the fan-facing Bulls rookie composite table."""

from __future__ import annotations

import pandas as pd
import pytest

from scripts.prototypes.bulls_rookie_composite_table import (
    _context,
    _format_rank,
    validate_ranking,
)


def test_format_rank_preserves_average_rank_ties():
    assert _format_rank(3.0) == "#3"
    assert _format_rank(3.5) == "#3.5"


def test_context_uses_raw_wins_only_for_equal_length_seasons():
    normal = pd.Series(
        {"season_label": "2008-09", "team_record": "41-41", "team_win_change": 8,
         "team_win_pct_change": 8 / 82}
    )
    shortened = pd.Series(
        {"season_label": "2020-21", "team_record": "31-41", "team_win_change": float("nan"),
         "team_win_pct_change": 0.092094}
    )
    assert _context(normal) == "2008–09  ·  41–41  ·  +8 wins"
    assert _context(shortened) == "2020–21  ·  31–41  ·  +9.2 win% pts"


def test_validation_rejects_a_composite_that_does_not_reconcile():
    columns = {
        "composite_rank": [1] * 23,
        "average_category_rank": [1] * 23,
        "player_id": list(range(23)),
        "player_name": [f"Player {i}" for i in range(23)],
        "season_label": ["2000-01"] * 23,
        "team_record": ["41-41"] * 23,
        "team_win_change": [0] * 23,
        "team_win_pct_change": [0.0] * 23,
        "ppg": [1.0] * 23,
        "rpg": [1.0] * 23,
        "apg": [1.0] * 23,
        "stocks_per_game": [1.0] * 23,
        "ts_pct": [0.5] * 23,
        "ws": [1.0] * 23,
        "rank_ppg": [2.0] * 23,
        "rank_rpg": [2.0] * 23,
        "rank_apg": [2.0] * 23,
        "rank_stocks_per_game": [2.0] * 23,
        "rank_ts_pct": [2.0] * 23,
        "rank_ws": [2.0] * 23,
    }
    with pytest.raises(ValueError, match="do not reconcile"):
        validate_ranking(pd.DataFrame(columns))
