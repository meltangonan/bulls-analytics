"""Tests for bulls.graphics module."""

from __future__ import annotations

import matplotlib.pyplot as plt
from PIL import Image

from bulls.graphics import (
    CANVAS_HEIGHT,
    CANVAS_WIDTH,
    body_font,
    display_font,
    draw_footer,
    draw_header,
    gradient_bar,
    headshot_label,
    new_canvas,
    save_post,
    stacked_label,
    threshold_footer,
)


class TestHouseGraphics:
    """Executable checks for the settled design-system frame."""

    def test_canvas_uses_feed_coordinates(self):
        fig, ax = new_canvas()

        assert tuple(ax.get_xlim()) == (0.0, float(CANVAS_WIDTH))
        assert tuple(ax.get_ylim()) == (0.0, float(CANVAS_HEIGHT))
        plt.close(fig)

    def test_house_fonts_use_helvetica_files(self):
        from bulls.graphics.house import _HELVETICA_TTC

        fonts = (
            display_font(),
            body_font("regular"),
            body_font("medium"),
            body_font("bold"),
        )
        if _HELVETICA_TTC.exists():
            for font in fonts:
                assert "Helvetica" in font.get_file()
            return
        # Documented non-macOS path: family fallback, no extracted Helvetica file.
        for font in fonts:
            families = font.get_family()
            assert any(name in families for name in ("Helvetica", "Arial", "DejaVu Sans"))

    def test_header_and_footer_include_required_house_elements(self):
        fig, ax = new_canvas()
        draw_header(
            ax,
            [("THE SHAPE OF THE ", "#1A1A1A"), ("SEASON", "#CE1141")],
            ["Chicago Bulls", "2025-26 Season"],
            kicker="Games above/below .500",
        )
        draw_footer(ax)

        text = " ".join(artist.get_text() for artist in ax.texts)
        assert "THE SHAPE OF THE" in text
        assert "Games above/below .500" in text
        assert "Data via nba.com" in text
        assert "@chicagobullsdata" in text
        plt.close(fig)

    def test_house_export_has_explicit_draft_and_final_dimensions(self, tmp_path):
        draft_fig, _ = new_canvas()
        final_fig, _ = new_canvas()
        draft_path = save_post(draft_fig, tmp_path / "draft.png")
        final_path = save_post(final_fig, tmp_path / "final.png", final=True)
        plt.close(draft_fig)
        plt.close(final_fig)

        with Image.open(draft_path) as image:
            assert image.size == (1080, 1350)
        with Image.open(final_path) as image:
            assert image.size == (2160, 2700)


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
