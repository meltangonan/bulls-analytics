"""Tests for bulls.graphics module."""

from __future__ import annotations

import matplotlib.pyplot as plt
import pandas as pd

from bulls.graphics import (
    build_zone_pps_post,
    build_zone_team_stats_post,
    build_zone_volume_leaders_post,
    save_feed_post,
)


def _sample_team_shots() -> pd.DataFrame:
    rows = []

    # Restricted Area: strong zone
    for i in range(24):
        rows.append(
            {
                "shot_zone": "Restricted Area",
                "shot_type": "2PT",
                "shot_made": i < 15,
            }
        )

    # Above the Break 3: average zone
    for i in range(22):
        rows.append(
            {
                "shot_zone": "Above the Break 3",
                "shot_type": "3PT",
                "shot_made": i < 8,
            }
        )

    # Mid-Range: lower-value zone
    for i in range(20):
        rows.append(
            {
                "shot_zone": "Mid-Range",
                "shot_type": "2PT",
                "shot_made": i < 6,
            }
        )

    return pd.DataFrame(rows)


class TestBuildZonePpsPost:
    """Tests for build_zone_pps_post."""

    def test_returns_figure(self):
        shots = _sample_team_shots()
        fig = build_zone_pps_post(shots)
        assert isinstance(fig, plt.Figure)
        plt.close(fig)

    def test_handles_empty_dataframe(self):
        fig = build_zone_pps_post(pd.DataFrame())
        assert isinstance(fig, plt.Figure)
        plt.close(fig)

    def test_handles_no_zones_meeting_min_shots(self):
        shots = _sample_team_shots()
        fig = build_zone_pps_post(shots, min_shots=1000)
        assert isinstance(fig, plt.Figure)
        plt.close(fig)


def _sample_detailed_shots() -> pd.DataFrame:
    """Sample shots with player info and zone area for detailed zone mapping."""
    rows = []
    # Player A: 10 shots in Restricted Area
    for i in range(10):
        rows.append({
            "player_id": 1, "player_name": "Player A",
            "shot_zone": "Restricted Area", "shot_zone_area": "Center(C)",
            "shot_type": "2PT", "shot_made": i < 6,
            "game_id": f"00{i % 3}",
        })
    # Player B: 8 shots in Mid-Range (Left Side Center)
    for i in range(8):
        rows.append({
            "player_id": 2, "player_name": "Player B",
            "shot_zone": "Mid-Range", "shot_zone_area": "Left Side Center(LC)",
            "shot_type": "2PT", "shot_made": i < 4,
            "game_id": f"00{i % 3}",
        })
    # Player A: 6 shots Above the Break 3 (Center)
    for i in range(6):
        rows.append({
            "player_id": 1, "player_name": "Player A",
            "shot_zone": "Above the Break 3", "shot_zone_area": "Center(C)",
            "shot_type": "3PT", "shot_made": i < 2,
            "game_id": f"00{i % 3}",
        })
    return pd.DataFrame(rows)


class TestBuildZoneTeamStatsPost:
    """Tests for build_zone_team_stats_post."""

    def test_returns_figure(self):
        shots = _sample_detailed_shots()
        fig = build_zone_team_stats_post(shots)
        assert isinstance(fig, plt.Figure)
        plt.close(fig)

    def test_handles_empty_dataframe(self):
        fig = build_zone_team_stats_post(pd.DataFrame())
        assert isinstance(fig, plt.Figure)
        plt.close(fig)


class TestBuildZoneVolumeLeadersPost:
    """Tests for build_zone_volume_leaders_post."""

    def test_returns_figure(self):
        shots = _sample_detailed_shots()
        fig = build_zone_volume_leaders_post(shots, min_shots=3)
        assert isinstance(fig, plt.Figure)
        plt.close(fig)

    def test_handles_empty_dataframe(self):
        fig = build_zone_volume_leaders_post(pd.DataFrame())
        assert isinstance(fig, plt.Figure)
        plt.close(fig)


class TestSaveFeedPost:
    """Tests for save_feed_post."""

    def test_writes_png_file(self, tmp_path):
        fig = build_zone_pps_post(_sample_team_shots())
        output_path = tmp_path / "feed-post.png"
        saved = save_feed_post(fig, str(output_path))
        plt.close(fig)

        assert saved.exists()
        assert saved.suffix == ".png"
