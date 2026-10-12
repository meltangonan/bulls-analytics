import importlib.util
import io
from pathlib import Path

import pytest
from PIL import Image

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "strip_image_metadata.py"
SPEC = importlib.util.spec_from_file_location("strip_image_metadata", SCRIPT)
strip = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(strip)


def png(width, height):
    out = io.BytesIO()
    Image.new("RGB", (width, height), "#E9E5E1").save(out, "PNG")
    return out.getvalue()


def test_a_2x_page_is_halved_to_feed_size():
    data = strip.feed_size(png(2160, 2880), "page.png")
    assert Image.open(io.BytesIO(data)).size == (1080, 1440)
    strip.clean_png(data, "page.png")


def test_a_1x_page_passes_through_with_a_warning(capsys):
    data = png(1080, 1350)
    assert strip.feed_size(data, "page.png") == data
    assert "export at 2x" in capsys.readouterr().out


def test_an_unexpected_width_is_refused():
    with pytest.raises(AssertionError, match="expected a 2x page"):
        strip.feed_size(png(1500, 2000), "page.png")
