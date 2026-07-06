"""Tests for bulls.graphics module."""

from __future__ import annotations

import matplotlib.pyplot as plt
import pandas as pd

from bulls.graphics import (
    build_zone_pps_post,
    build_zone_team_stats_post,
    build_zone_volume_leaders_post,
    gradient_bar,
    headshot_label,
    save_feed_post,
    stacked_label,
    threshold_footer,
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


class TestGradientBar:
    """Tests for gradient_bar."""

    def test_min_maps_light_and_max_maps_dark(self):
        fig, ax = plt.subplots()
        low = gradient_bar(ax, y=1.0, value=0.0, vmin=0.0, vmax=10.0, length=100)
        high = gradient_bar(ax, y=2.0, value=10.0, vmin=0.0, vmax=10.0, length=100)

        low_intensity = sum(low.get_facecolor()[:3])
        high_intensity = sum(high.get_facecolor()[:3])
        assert low_intensity > high_intensity
        plt.close(fig)


class TestStackedLabel:
    """Tests for stacked_label."""

    def test_renders_primary_above_secondary(self):
        fig, ax = plt.subplots()
        primary, secondary = stacked_label(ax, 0.5, 0.5, "Coby White", "22.4 PPG")

        assert primary.get_text() == "Coby White"
        assert secondary.get_text() == "22.4 PPG"
        assert primary.get_position()[1] > secondary.get_position()[1]
        plt.close(fig)

    def test_truncates_long_name(self):
        fig, ax = plt.subplots()
        primary, _ = stacked_label(ax, 0.5, 0.5, "Giannis Antetokounmpo", "30.1 PPG")

        assert primary.get_text() == "G. Antetokounmpo"
        plt.close(fig)


class TestThresholdFooter:
    """Tests for threshold_footer."""

    def test_contains_threshold_and_coverage_window(self):
        fig, ax = plt.subplots()
        threshold_footer(fig, "Min. 20 games", "2025-26 season through Jul 4")

        footer = " ".join(t.get_text() for t in fig.texts)
        assert "20" in footer
        assert "2025-26 season through Jul 4" in footer
        plt.close(fig)


class TestHeadshotLabel:
    """Tests for headshot_label."""

    def test_none_path_draws_placeholder(self):
        fig, ax = plt.subplots()
        artist = headshot_label(ax, None, 0.5, 0.5, radius=0.1)

        assert artist in ax.images
        plt.close(fig)

    def test_missing_path_draws_placeholder(self, tmp_path):
        fig, ax = plt.subplots()
        artist = headshot_label(ax, tmp_path / "missing.png", 0.5, 0.5, radius=0.1)

        assert artist in ax.images
        plt.close(fig)

    def test_radius_sets_extent(self):
        fig, ax = plt.subplots()
        artist = headshot_label(ax, None, 10.0, 20.0, radius=5.0)

        assert tuple(artist.get_extent()) == (5.0, 15.0, 15.0, 25.0)
        plt.close(fig)

    def test_real_image_renders_instead_of_placeholder(self, tmp_path):
        import numpy as np

        img_path = tmp_path / "headshot.png"
        plt.imsave(img_path, np.zeros((20, 20, 3)))

        fig, ax = plt.subplots()
        artist = headshot_label(ax, img_path, 0.5, 0.5, radius=0.1)

        # Placeholder discs are 190px square; the real-image branch keeps
        # the source image's dimensions through the circular crop.
        assert artist.get_array().shape[0] == 20
        plt.close(fig)
