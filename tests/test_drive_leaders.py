import json
from datetime import datetime, timezone

import pandas as pd
import pytest

from scripts.prototypes import drive_leaders_data as data
from scripts.prototypes import drive_leaders_table as table


def sample() -> pd.DataFrame:
    return pd.DataFrame({
        "PLAYER_ID": [1], "PLAYER_NAME": ["Player One"], "TEAM_ID": [data.BULLS],
        "GP": [10], "DRIVES": [100], "DRIVE_FGM": [20], "DRIVE_FGA": [40],
        "DRIVE_FG_PCT": [.5], "DRIVE_FTM": [8], "DRIVE_FTA": [10],
        "DRIVE_PTS": [50], "DRIVE_PTS_PCT": [.5], "DRIVE_PASSES": [45],
        "DRIVE_PASSES_PCT": [.45], "DRIVE_AST": [12], "DRIVE_AST_PCT": [.12],
        "DRIVE_TOV": [5], "DRIVE_TOV_PCT": [.05], "DRIVE_PF": [9],
        "DRIVE_PF_PCT": [.09],
    })


def test_drive_point_residual_is_preserved_without_calling_it_threes():
    got = data.validate_rows(sample())
    assert got.DRIVE_POINTS_RESIDUAL.iloc[0] == 2


def test_negative_drive_point_residual_is_retained_for_audit():
    frame = sample(); frame.loc[0, "DRIVE_PTS"] = 45
    got = data.validate_rows(frame)
    assert got.DRIVE_POINTS_RESIDUAL.iloc[0] == -3


def test_ranked_uses_metric_then_drive_volume():
    frame = pd.DataFrame({"drive_pts": [10, 10, 8], "drives": [50, 60, 90],
                          "season": ["2020-21"]*3, "player_id": [1, 2, 3]})
    got = data.ranked(frame, "drive_pts")
    assert got.player_id.tolist() == [2, 1, 3]
    assert got["rank"].tolist() == [1, 2, 3]


def test_display_formats_each_table_unit():
    row = pd.Series({"drive_fgm": 20, "drive_fga": 40, "drive_fg_pct": 50.04,
                     "drive_shot_pct": 40.04, "drives_per_game": 10.04,
                     "drive_ast_pct": 16.66,
                     "drive_pts": 50})
    assert table.display(row, "fg") == "20–40"
    assert table.display(row, "drive_fg_pct") == "50.0%"
    assert table.display(row, "drive_shot_pct") == "40.0%"
    assert table.display(row, "drives_per_game") == "10.0"
    assert table.display(row, "drive_ast_pct") == "16.7%"
    assert table.display(row, "drive_pts") == "50"


@pytest.mark.parametrize("team_retrieved_at", ["2026-09-15T13:00:00+00:00", None])
def test_cached_rebuild_preserves_source_dates(tmp_path, monkeypatch, team_retrieved_at):
    monkeypatch.setattr(data, "DATA", tmp_path)
    monkeypatch.setattr(data, "SEASONS", ["2025-26"])

    def unexpected_fetch(*args, **kwargs):
        pytest.fail("A cached rebuild must not fetch data")

    monkeypatch.setattr(data.leaguedashptstats, "LeagueDashPtStats", unexpected_fetch)
    raw = tmp_path / "raw"
    raw.mkdir()
    frame = sample()
    dates = {"players": "2026-09-15T12:00:00+00:00", "teams": team_retrieved_at}
    originals = {}
    for kind, retrieved_at in dates.items():
        payload = {"response": {"resultSets": [{
            "headers": frame.columns.tolist(), "rowSet": frame.values.tolist(),
        }]}}
        if retrieved_at is not None:
            payload["retrieved_at"] = retrieved_at
        path = raw / f"{kind}_2025-26.json"
        path.write_text(json.dumps(payload))
        originals[path] = path.read_bytes()

    before = datetime.now(timezone.utc)
    data.main()
    source = json.loads((tmp_path / "source.json").read_text())
    assert before <= datetime.fromisoformat(source["generated_at"]) <= datetime.now(timezone.utc)
    assert "retrieved_at" not in source
    assert source["source_snapshots"] == [
        {"path": f"raw/{kind}_2025-26.json", "retrieved_at": retrieved_at}
        for kind, retrieved_at in dates.items()
    ]
    assert all(path.read_bytes() == content for path, content in originals.items())
    published = pd.read_csv(tmp_path / "top15_drive_points.csv")
    assert published.drive_pts.tolist() == [50]
