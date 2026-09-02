from pathlib import Path

import pandas as pd
import pytest
from matplotlib.textpath import TextPath
from PIL import Image

from tests.conftest import requires_helvetica
from scripts.prototypes import bulls_nba_2k27_rating_cards as cards_module
from scripts.prototypes.bulls_nba_2k27_rating_cards import (
    change_color,
    change_label,
    load_cards,
    rating_fill,
    render_player_bars,
    text_color_for_fill,
    validate_cards,
)


def test_snapshot_contains_the_full_2k27_bulls_roster_in_rating_order():
    cards = load_cards()

    assert len(cards) == 16
    assert cards["player_name"].tolist()[:6] == [
        "Norman Powell",
        "Josh Giddey",
        "Matas Buzelis",
        "Nicolas Claxton",
        "Tre Jones",
        "Caleb Wilson",
    ]
    assert cards["official_confirmed"].all()
    assert cards.set_index("player_name").loc["Josh Giddey", "playmaking"] == 87
    assert cards.set_index("player_name").loc["Matas Buzelis", "outside_scoring"] == 84
    assert cards.set_index("player_name").loc["Jalen Smith", "rebounding"] == 77


def test_calebs_detail_ratings_are_now_available_but_his_prior_rating_is_not():
    cards = load_cards().set_index("player_name")
    caleb = cards.loc["Caleb Wilson"]

    assert caleb["nba_2k27_ovr"] == 77
    assert bool(caleb["detailed_ratings_available"]) is True
    assert caleb["athleticism"] == 80
    assert caleb["defense"] == 73
    assert change_label(caleb) == "2K DEBUT"


def test_change_labels_and_colors_distinguish_gains_drops_flat_and_debuts():
    cards = load_cards().set_index("player_name")

    assert change_label(cards.loc["Norman Powell"]) == "0 VS 2K26"
    assert change_label(cards.loc["Josh Giddey"]) == "2 VS 2K26"
    assert change_label(cards.loc["Patrick Williams"]) == "1 VS 2K26"
    assert change_color(cards.loc["Josh Giddey"]) == "#1F8A4C"
    assert change_color(cards.loc["Patrick Williams"]) == "#A90F2A"
    assert change_color(cards.loc["Norman Powell"]) == cards_module.DEFAULT_THEME.muted
    assert change_color(cards.loc["Caleb Wilson"]) == cards_module.DEFAULT_THEME.muted


def test_validation_rejects_unconfirmed_or_miscalculated_rows():
    cards = load_cards()

    unconfirmed = cards.copy()
    unconfirmed.loc[0, "official_confirmed"] = False
    with pytest.raises(ValueError, match="only confirmed"):
        validate_cards(unconfirmed)

    wrong_change = cards.copy()
    wrong_change.loc[1, "ovr_change"] = 3
    with pytest.raises(ValueError, match="ovr_change"):
        validate_cards(wrong_change)


def test_rating_colors_run_from_red_through_yellow_to_green():
    assert rating_fill(52).startswith("#")
    assert rating_fill(70) == "#f2c14e"
    assert rating_fill(87) != rating_fill(52)

    low_red, low_green, _ = cards_module.to_rgb(rating_fill(52))
    high_red, high_green, _ = cards_module.to_rgb(rating_fill(87))
    assert low_red > low_green
    assert high_green > high_red
    assert text_color_for_fill(rating_fill(70)) == "#141414"


def test_bar_asset_uses_one_left_aligned_grid():
    assert cards_module.ASSET_MARGIN == 4
    assert cards_module.ASSET_WIDTH - 2 * cards_module.ASSET_MARGIN > 450


def test_render_exports_one_transparent_asset_per_player(tmp_path, monkeypatch):
    cards = load_cards().iloc[:2]
    monkeypatch.setattr(cards_module, "OUT_DIR", tmp_path / "output")
    outputs = render_player_bars(cards)

    assert [output.name for output in outputs] == [
        "2026-08-28-2k27-rating-bars-norman-powell.png",
        "2026-08-28-2k27-rating-bars-josh-giddey.png",
    ]
    with Image.open(outputs[0]) as image:
        assert image.size == (500, 200)
        assert image.mode == "RGBA"
        assert image.getpixel((0, 0))[3] == 0


def test_full_roster_renders_as_sixteen_player_assets(tmp_path, monkeypatch):
    cards = load_cards()
    monkeypatch.setattr(cards_module, "OUT_DIR", tmp_path / "output")
    outputs = render_player_bars(cards)

    assert len(outputs) == 16
    assert outputs[-1].name.endswith("jaylin-sellers.png")
    with Image.open(outputs[-1]) as image:
        assert image.size == (500, 200)


def test_rendered_bar_text_uses_only_helvetica_bold(tmp_path, monkeypatch):
    weights = []
    real_helvetica = cards_module.helvetica

    def recording_helvetica(weight="regular"):
        weights.append(weight)
        return real_helvetica(weight)

    monkeypatch.setattr(cards_module, "helvetica", recording_helvetica)
    monkeypatch.setattr(cards_module, "OUT_DIR", tmp_path / "output")
    render_player_bars(load_cards().iloc[:1])

    assert weights
    assert set(weights) == {"bold"}


@requires_helvetica
def test_category_label_gutter_clears_the_longest_label():
    label = TextPath(
        (0, 0),
        "REBOUNDING",
        size=6.3,
        prop=cards_module.helvetica("bold"),
    )
    width_px = label.get_extents().width * cards_module.DRAFT_DPI / 72.0

    assert width_px + 12 < cards_module.BAR_LABEL_W
