"""Tests for bulls.graphics module."""

from __future__ import annotations

import matplotlib.pyplot as plt
import pandas as pd

from bulls.graphics import build_zone_pps_post, save_feed_post


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


class TestSaveFeedPost:
    """Tests for save_feed_post."""

    def test_writes_png_file(self, tmp_path):
        fig = build_zone_pps_post(_sample_team_shots())
        output_path = tmp_path / "feed-post.png"
        saved = save_feed_post(fig, str(output_path))
        plt.close(fig)

        assert saved.exists()
        assert saved.suffix == ".png"
