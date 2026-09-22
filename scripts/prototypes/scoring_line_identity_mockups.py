#!/usr/bin/env python3
"""Render the qualified current Bulls roster as individual scoring-line assets.

Each chart uses the player's complete 2025-26 regular season across all teams.
The comparison population is the current 2026-27 Bulls roster members who
appeared in at least 20 games during 2025-26.
"""

from __future__ import annotations

import importlib.util
from datetime import date
from pathlib import Path

import pandas as pd
from PIL import Image, ImageDraw, ImageFont

from bulls.graphics import house


ROOT = Path(__file__).resolve().parents[2]
SCORING_SCRIPT = ROOT / "scripts/prototypes/bulls_scoring_lines.py"
SPEC = importlib.util.spec_from_file_location("bulls_scoring_lines", SCORING_SCRIPT)
SCORING = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(SCORING)

OUTPUT_DIR = ROOT / "output/scoring_line_identity_mockups"
DATA_DIR = ROOT / "docs/visuals/2026-09-20-current-roster-scoring-lines/data"
HEADSHOTS = ROOT / "cache/headshots"

MIN_GAMES = 20
FINAL_DPI = 300
FINAL_WIDTH = 1500
FINAL_HEIGHT = 1200

# The explicit order is also the Canva page order: descending 2025-26 PPG,
# split evenly after the fifth player. No chart receives hero treatment.
PLAYERS = {
    "Norman Powell": 1626181,
    "Josh Giddey": 1630581,
    "Matas Buzelis": 1641824,
    "Tre Jones": 1630200,
    "Nic Claxton": 1629651,
    "Jalen Smith": 1630188,
    "Isaac Okoro": 1630171,
    "Leonard Miller": 1631159,
    "Patrick Williams": 1630172,
    "Rob Dillingham": 1642265,
}


def _slug(name: str) -> str:
    return name.lower().replace(" ", "-")


def _font(size: int, *, weight: str = "bold") -> ImageFont.FreeTypeFont:
    font_path = house.helvetica(weight).get_file()
    if not font_path:
        raise RuntimeError(f"Helvetica {weight} did not resolve to a font file")
    return ImageFont.truetype(font_path, size=size)


def _team_season_label(teams: str) -> str:
    """Put Chicago first when a current Bull played for multiple teams."""
    abbreviations = str(teams).split("/")
    if "CHI" in abbreviations:
        abbreviations = ["CHI", *[team for team in abbreviations if team != "CHI"]]
    return f"{'/'.join(abbreviations)}, 2025-26"


def _games_played_label(games_played: int) -> str:
    return f"{int(games_played)} GP"


def _square_portrait(path: Path, *, size: int = 300) -> Image.Image:
    portrait = Image.open(path).convert("RGBA")
    # Zoom modestly into the NBA CDN cutout: preserve a square face/shoulders
    # crop while leaving only a small jersey cue at the bottom.
    crop_size = int(min(portrait.size) * 0.82)
    left = (portrait.width - crop_size) // 2
    portrait = portrait.crop((left, 0, left + crop_size, crop_size))
    return portrait.resize((size, size), Image.Resampling.LANCZOS)


def _compose(
    base_path: Path,
    player_name: str,
    player_id: int,
    team_season: str,
    games_played: int,
    output_path: Path,
    *,
    dpi: int = FINAL_DPI,
) -> None:
    """Place a square portrait in reserved space above every chart line."""
    base = Image.open(base_path).convert("RGBA")
    canvas = Image.new("RGBA", base.size, (255, 255, 255, 0))
    canvas.alpha_composite(base, (0, 0))
    portrait = _square_portrait(HEADSHOTS / f"{player_id}.png")
    portrait_x = 62
    portrait_y = 70
    canvas.alpha_composite(portrait, (portrait_x, portrait_y))

    draw = ImageDraw.Draw(canvas)
    name_x = 390
    name_y = 88
    draw.text(
        (name_x, name_y),
        player_name,
        fill=house.BLACK,
        font=_font(78),
    )
    draw.text(
        (name_x, 182),
        team_season,
        fill=house.BLACK,
        font=_font(48, weight="regular"),
    )
    draw.text(
        (name_x, 242),
        _games_played_label(games_played),
        fill=house.BLACK,
        font=_font(48, weight="regular"),
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(output_path, dpi=(dpi, dpi))


def _current_roster_data() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Load the saved all-team player seasons and apply the 20-game floor."""
    games = pd.read_csv(DATA_DIR / "player_game_points.csv", parse_dates=["game_date"])
    audit = pd.read_csv(DATA_DIR / "roster_scoring_audit.csv")
    audit["qualifies"] = audit["games_played"].fillna(0).ge(MIN_GAMES)
    qualified_ids = set(audit.loc[audit["qualifies"], "player_id"])
    return games[games["player_id"].isin(qualified_ids)].copy(), audit


def main() -> None:
    house.ensure_headshots(PLAYERS.values())
    games, audit = _current_roster_data()
    selected = audit.loc[audit["qualifies"], "player_name"].tolist()
    if set(selected) != set(PLAYERS):
        raise RuntimeError(
            "Saved current-roster data does not match the expected qualified set: "
            f"expected {sorted(PLAYERS)}, found {sorted(selected)}"
        )
    selection = audit[audit["player_name"].isin(PLAYERS)].copy()
    order = {name: index for index, name in enumerate(PLAYERS, start=1)}
    selection["render_order"] = selection["player_name"].map(order)
    selection["slide"] = selection["render_order"].map(lambda value: 1 if value <= 5 else 2)
    selection["minimum_games"] = MIN_GAMES
    selection["player_season_scope"] = "complete 2025-26 regular season across all teams"
    selection["trend_method"] = "trailing 10-game average; shown after 5 games"
    selection["asset_width_px"] = FINAL_WIDTH
    selection["asset_height_px"] = FINAL_HEIGHT
    selection["canva_placement_px"] = "500x400"
    selection["canva_layout"] = "2-2-1; x=25/555/290; y=170/585/1000"
    selection["current_roster_season"] = "2026-27"
    selection["selection_generated_on"] = date.today().isoformat()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    selection.sort_values("render_order").to_csv(
        OUTPUT_DIR / "current_roster_scoring_selection.csv", index=False
    )
    for player_name, player_id in PLAYERS.items():
        player_row = audit.loc[audit["player_name"] == player_name].iloc[0]
        base = OUTPUT_DIR / f"{_slug(player_name)}-base.png"
        SCORING.render_player(
            games,
            audit,
            player_name,
            base,
            y_max=60,
            visible_y_max=50,
            pixel_width=FINAL_WIDTH,
            pixel_height=FINAL_HEIGHT,
        )
        output = OUTPUT_DIR / f"{_slug(player_name)}-scoring-line.png"
        _compose(
            base,
            player_name,
            player_id,
            _team_season_label(player_row["teams"]),
            player_row["games_played"],
            output,
        )
        print(f"Saved {output}")


if __name__ == "__main__":
    main()
