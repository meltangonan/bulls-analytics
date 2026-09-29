import pandas as pd
import pytest

from scripts.prototypes.bulls_rookie_debuts import (
    apply_bbr_fills,
    classify,
    competition_ranks,
    needs_career_check,
    rank_debuts,
)

CAREER_COLUMNS = ["PLAYER_ID", "SEASON_ID", "TEAM_ID"]
NO_CAREER = pd.DataFrame(columns=CAREER_COLUMNS)


def audit_row(player_id, player, season_end_year, first_nba_season_end, draft_year, points=10):
    return {"player_id": player_id, "player": player, "season_end_year": season_end_year,
            "first_nba_season_end": first_nba_season_end, "draft_year": draft_year, "points": points}


def test_classify_counts_every_first_nba_game_with_chicago_and_drops_aba_veterans():
    audit = pd.DataFrame([
        audit_row(1, "Drafted rookie", 1985, 1985, 1984),
        audit_row(2, "Undrafted rookie", 2004, 2004, None),
        audit_row(3, "1976 draftee", 1977, 1977, 1976),
        audit_row(4, "ABA veteran", 1977, 1977, 1971),
        audit_row(5, "Undrafted ABA veteran", 1977, 1977, None),
        audit_row(6, "Veteran arrival", 1995, 1987, 1986),
    ])
    result = classify(audit, NO_CAREER).set_index("player")
    assert result["eligible"].to_dict() == {
        "Drafted rookie": True, "Undrafted rookie": True, "1976 draftee": True,
        "ABA veteran": False, "Undrafted ABA veteran": False, "Veteran arrival": False,
    }


def test_classify_trusts_career_history_over_a_draft_year_first_season():
    # Listed from his draft year, but his only NBA seasons were with Chicago.
    audit = pd.DataFrame([audit_row(2450, "Stash", 2006, 2003, 2002)])
    career = pd.DataFrame([{"PLAYER_ID": 2450, "SEASON_ID": "2005-06", "TEAM_ID": 1610612741}])
    assert classify(audit, NO_CAREER)["eligible"].tolist() == [False]
    assert classify(audit, career)["eligible"].tolist() == [True]


def test_career_check_covers_only_listed_veterans_at_or_above_the_cutoff():
    audit = classify(pd.DataFrame([
        audit_row(1, "High-scoring veteran", 2002, 1995, 1994, points=36),
        audit_row(2, "Low-scoring veteran", 2002, 1995, 1994, points=4),
        audit_row(3, "Rookie", 2002, 2002, 2001, points=30),
    ]), NO_CAREER)
    assert audit.loc[needs_career_check(audit, 16), "player"].tolist() == ["High-scoring veteran"]


def test_competition_ranks_label_ties():
    assert competition_ranks(pd.Series([26, 17, 17, 16, 14, 14])) == ["1", "T2", "T2", "4", "T5", "T5"]


def test_rank_debuts_keeps_everyone_tied_with_the_last_place_in_date_order():
    rows = pd.DataFrame({
        "player_id": range(5), "points": [20, 15, 14, 14, 9],
        "game_date": ["2000-01-01", "2001-01-01", "2010-01-01", "1999-01-01", "2002-01-01"],
    })
    ranked = rank_debuts(rows, top_n=3)
    assert ranked["player_id"].tolist() == [0, 1, 3, 2]
    assert ranked["rank"].tolist() == [1, 2, 3, 3]
    assert ranked["rank_label"].tolist() == ["1", "2", "T3", "T3"]


def test_bbr_fills_only_fill_blank_cells():
    ranked = pd.DataFrame([{"player_id": 1, "game_date": "1982-10-29", "stl": float("nan"), "tov": 2.0}])
    fills = pd.DataFrame([{"player_id": 1, "player": "X", "game_date": "1982-10-29", "stat": "stl", "value": 1}])
    assert apply_bbr_fills(ranked, fills)["stl"].tolist() == [1]
    with pytest.raises(ValueError, match="not blank"):
        apply_bbr_fills(ranked, fills.assign(stat="tov"))
