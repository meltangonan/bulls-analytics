"""The shared box-total fetch must preserve a traded player's requested stint."""
from types import SimpleNamespace

import pandas as pd
import pytest

from bulls.config import BULLS_TEAM_ID
from bulls.data import fetch
from scripts.prototypes import derrick_rose_bulls_zone_charts as rose
from scripts.prototypes import hinrich_bulls_zone_charts as hinrich
from scripts.prototypes import jimmy_butler_bulls_zone_charts as butler


@pytest.mark.parametrize("post", [rose, hinrich, butler])
def test_post_requests_chicago_totals_and_keeps_final_team_display_label(post, monkeypatch):
    requested = {}
    row = dict.fromkeys(post.TOTAL_COLUMNS, 0)
    row.update(PLAYER_ID=post.PLAYER_ID, PLAYER_NAME=post.PLAYER_NAME,
               TEAM_ABBREVIATION="ATL", GP=35, FGA=118, FGM=47, PTS=123)

    def endpoint(**kwargs):
        requested.update(kwargs)
        return SimpleNamespace(get_data_frames=lambda: [pd.DataFrame([row])])

    monkeypatch.setattr(fetch.leaguedashplayerstats, "LeagueDashPlayerStats", endpoint)
    result = post.fetch_bulls_totals("2015-16")
    assert requested["team_id_nullable"] == BULLS_TEAM_ID
    assert requested["season"] == "2015-16"
    assert requested["per_mode_detailed"] == "Totals"
    assert requested["season_type_all_star"] == "Regular Season"
    assert result.FGA == 118
    assert result.TEAM_ABBREVIATION == "ATL"


@pytest.mark.parametrize("failure", ["missing field", "absent player", "duplicate player"])
def test_unusable_source_cannot_pass_as_one_reconciliable_total(failure, monkeypatch):
    frame = pd.DataFrame([{"PLAYER_ID": 2550, "FGA": 118}])
    if failure == "missing field":
        frame = frame.drop(columns="FGA")
    elif failure == "absent player":
        frame["PLAYER_ID"] = 1
    else:
        frame = pd.concat([frame, frame], ignore_index=True)
    monkeypatch.setattr(
        fetch.leaguedashplayerstats, "LeagueDashPlayerStats",
        lambda **kwargs: SimpleNamespace(get_data_frames=lambda: [frame]),
    )
    with pytest.raises(ValueError, match="totals missing|expected one"):
        fetch.get_player_season_totals(
            2550, "2015-16", team_id=BULLS_TEAM_ID,
            columns=("PLAYER_ID", "FGA"), player_name="Kirk Hinrich",
        )
