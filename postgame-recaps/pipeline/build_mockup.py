"""Build the self-contained postgame recap mockup for one or more games.

    venv/bin/python postgame-recaps/pipeline/build_mockup.py 0022500248 [more ids]

For each game, reads output/postgame-recap/<id>/recap.json (recap_data.py) and zones.png
(zones_share.py), embeds them with the house-crop portraits from portraits/, and writes
output/postgame-recap/mockup.html with a switcher between the games. The page only draws.
"""
import base64
import io
import json
import sys
from pathlib import Path

from PIL import Image

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from paths import LOGOS, OUTPUT, PORTRAITS, REPO  # noqa: E402

BRAND = REPO / "assets" / "brand" / "chicagobullsdata-mark.svg"  # the account's mark, top right of each page


def portrait(path: Path) -> str:
    """House face crop (top 74% of height, centred square), as a transparent PNG data URI."""
    image = Image.open(path).convert("RGBA")
    width, height = image.size
    side = min(int(height * 0.74), width)
    left = max(0, (width - side) // 2)
    image = image.crop((left, 0, left + side, side)).resize((200, 200), Image.LANCZOS)
    buffer = io.BytesIO()
    image.save(buffer, "PNG", optimize=True)
    return "data:image/png;base64," + base64.b64encode(buffer.getvalue()).decode()


def png(path: Path) -> tuple[str, list[int]]:
    image = Image.open(path).convert("RGBA")
    image = image.crop(image.getbbox())
    buffer = io.BytesIO()
    image.save(buffer, "PNG", optimize=True)
    return "data:image/png;base64," + base64.b64encode(buffer.getvalue()).decode(), list(image.size)


def player_ids(game: dict) -> set[int]:
    ids = {row[0] for row in game["box"]["starters"] + game["box"]["bench"]}
    ids |= {award[1] for award in game["awards"]}
    for _, chi, opp in game["leaders"]:
        ids |= set(chi[2]) | set(opp[2])
    ids |= {row[0] for row in (game["season_leaders"] or {}).get("rows", [])}
    for _, _, rows in game["matchups"] or []:
        ids |= {row[5] for row in rows if row[5]}
    return ids


def main(game_ids: list[str]) -> None:
    games, zones, sizes, ids = [], {}, {}, set()
    for game_id in game_ids:
        game = json.loads((OUTPUT / game_id / "recap.json").read_text())
        games.append(game)
        zones[game_id], sizes[game_id] = png(OUTPUT / game_id / "zones.png")
        ids |= player_ids(game)
    heads = {}
    for pid in sorted(ids):
        path = PORTRAITS / f"{pid}.png"
        if path.exists():
            heads[pid] = portrait(path)
    logos = {}
    for game in games:
        for tri in (game["chi"]["tri"], game["opp"]["tri"]):  # the featured team is CHI except in dry runs
            path = LOGOS / f"{tri}.svg"
            if path.exists():
                logos[tri] = "data:image/svg+xml;base64," + base64.b64encode(path.read_bytes()).decode()
    brand = "data:image/svg+xml;base64," + base64.b64encode(BRAND.read_bytes()).decode()
    assets = {"games": games, "zones": zones, "zsize": sizes, "heads": heads, "logos": logos, "brand": brand}
    out = OUTPUT / "mockup.html"
    out.write_text((HERE / "recap_template.html").read_text().replace("__ASSETS__", json.dumps(assets, ensure_ascii=False)))
    print(f"wrote {out} ({out.stat().st_size // 1024} KB), {len(games)} games, {len(heads)} portraits")


if __name__ == "__main__":
    main(sys.argv[1:])
