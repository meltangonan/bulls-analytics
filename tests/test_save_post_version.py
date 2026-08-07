"""Tests for the post-image versioning helper.

The behaviour worth pinning is the numbering: versions are the record of how a
post was made, so they must never renumber or collide when a post is rebuilt.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location(
    "save_post_version", ROOT / "scripts" / "save_post_version.py")
svp = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(svp)


@pytest.fixture
def posts(tmp_path, monkeypatch):
    monkeypatch.setattr(svp, "POSTS", tmp_path / "docs" / "posts")
    return tmp_path / "docs" / "posts"


def _png(tmp_path, name):
    path = tmp_path / name
    path.write_bytes(b"\x89PNG\r\n\x1a\n fake")
    return path


def test_first_save_is_v01_and_carries_the_date(posts, tmp_path):
    saved = svp.save("shot-value-ladder", [_png(tmp_path, "ladder-pps.png")],
                     when="2026-08-07")
    assert saved[0].name == "2026-08-07-v01-ladder-pps.png"
    assert saved[0].parent.name == "shot-value-ladder"


def test_version_increments_and_never_renumbers_history(posts, tmp_path):
    src = _png(tmp_path, "ladder-pps.png")
    for expected in ("v01", "v02", "v03"):
        saved = svp.save("shot-value-ladder", [src], when="2026-08-07")
        assert expected in saved[0].name
    # A later day continues the sequence rather than restarting it.
    saved = svp.save("shot-value-ladder", [src], when="2026-09-01")
    assert saved[0].name == "2026-09-01-v04-ladder-pps.png"


def test_every_file_in_one_save_shares_a_version(posts, tmp_path):
    """A version is a set of images shown together, not one image."""
    files = [_png(tmp_path, f"chart-{i}.png") for i in range(3)]
    saved = svp.save("shot-value-ladder", files, when="2026-08-07")
    assert {s.name.split("-v")[1][:2] for s in saved} == {"01"}


def test_version_is_zero_padded_so_ten_sorts_after_nine(posts, tmp_path):
    src = _png(tmp_path, "chart.png")
    for _ in range(10):
        svp.save("p", [src], when="2026-08-07")
    names = sorted(p.name for p in (posts / "p").glob("*.png"))
    assert names[-1].startswith("2026-08-07-v10")


def test_an_already_dated_render_is_not_double_stamped(posts, tmp_path):
    """The chart CLIs date their own output; saving must not stack stamps."""
    src = _png(tmp_path, "2026-08-07-ladder-pps-league.png")
    saved = svp.save("shot-value-ladder", [src], when="2026-08-07")
    assert saved[0].name == "2026-08-07-v01-ladder-pps-league.png"


def test_resaving_a_previously_saved_file_does_not_stack_versions(posts, tmp_path):
    src = _png(tmp_path, "2026-08-07-v03-ladder-pps-league.png")
    saved = svp.save("shot-value-ladder", [src], when="2026-08-08")
    assert saved[0].name == "2026-08-08-v01-ladder-pps-league.png"


def test_missing_file_fails_loudly_rather_than_saving_nothing(posts, tmp_path):
    with pytest.raises(SystemExit):
        svp.save("shot-value-ladder", [tmp_path / "absent.png"])


def test_slug_is_normalised(posts, tmp_path):
    saved = svp.save("Shot Value Ladder!", [_png(tmp_path, "c.png")],
                     when="2026-08-07")
    assert saved[0].parent.name == "shot-value-ladder"


def test_empty_slug_is_rejected(posts, tmp_path):
    with pytest.raises(SystemExit):
        svp.save("---", [_png(tmp_path, "c.png")])


# --- render target shape ---------------------------------------------------
def test_render_and_archive_use_the_same_folder_shape():
    """``output/feed/<slug>/`` mirrors ``docs/posts/<slug>/``.

    Two differently-shaped homes for the same images read as the convention not
    being followed, which is exactly how it was first reported.
    """
    import argparse
    import importlib.util as _ilu

    spec = _ilu.spec_from_file_location("msc", ROOT / "scripts" / "make_shot_chart.py")
    msc = _ilu.module_from_spec(spec)
    spec.loader.exec_module(msc)

    args = argparse.Namespace(chart="ladder", metric="pps", focus="",
                              band=2.0, post="Shot Value Ladder")
    path = msc._output_path(args, "bulls")
    assert path.parent.name == "shot-value-ladder"
    assert path.parent.parent.name == "feed"

    args.post = ""
    flat = msc._output_path(args, "bulls")
    assert flat.parent.name == "feed"
