"""Build the current Bulls roster DARKO landscape chart for Canva.

This is a post-specific, roster-sized workflow. NBA.com supplies membership,
DARKO supplies full-precision ODPM/DDPM values, and the saved working table is
the analytical input to the chart. It does not use DARKO's team field as a
roster filter or its rounded Download CSV.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

_REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO))

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import pandas as pd
import requests
from matplotlib.font_manager import FontProperties
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

from bulls.data import get_player_headshot
from bulls.graphics.house import (
    DEFAULT_THEME,
    DRAFT_DPI,
    body_font,
    export_dpi,
    rendered_width,
)


NBA_ROSTER_URL = "https://www.nba.com/team/1610612741/roster"
DARKO_URL = "https://www.darko.app/"
SNAPSHOT_TZ = ZoneInfo("America/Chicago")
OUT = _REPO / "output" / "feed"
HEADSHOTS = _REPO / "cache" / "headshots"

CHART_WIDTH = 1080
CHART_HEIGHT = 1030
PANEL = (188, 178, 1015, 956)  # x0, y0, x1, y1
ODPM_LIMITS = (-2.6, 1.7)
DDPM_LIMITS = (-1.5, 1.5)

REFERENCE_ROSTER = {
    "Tobe Awaka",
    "Jaylin Sellers",
    "Josh Giddey",
    "Dailyn Swain",
    "Rob Dillingham",
    "Caleb Wilson",
    "Nic Claxton",
    "Leonard Miller",
    "Zach Collins",
    "Matas Buzelis",
    "Norman Powell",
    "Noa Essengue",
    "Jalen Smith",
    "Tre Jones",
    "Isaac Okoro",
    "Patrick Williams",
}
REFERENCE_MISSING = {
    "Tobe Awaka",
    "Jaylin Sellers",
    "Dailyn Swain",
    "Caleb Wilson",
}
REFERENCE_DISPLAY_VALUES = {
    "Jalen Smith": (0.4, 0.7, 1.2),
    "Norman Powell": (1.4, -0.9, 0.5),
    "Josh Giddey": (0.7, -0.5, 0.2),
    "Zach Collins": (-1.2, 1.2, 0.0),
    "Tre Jones": (0.6, -0.9, -0.3),
    "Matas Buzelis": (-0.2, -0.7, -0.8),
    "Leonard Miller": (-0.1, -0.8, -0.9),
    "Isaac Okoro": (-0.6, -0.6, -1.2),
    "Nic Claxton": (-1.6, -0.1, -1.7),
    "Noa Essengue": (-1.4, -0.3, -1.7),
    "Patrick Williams": (-2.2, -0.5, -2.7),
    "Rob Dillingham": (-2.1, -0.7, -2.8),
}

SHORT_NAMES = {
    "Josh Giddey": "GIDDEY",
    "Rob Dillingham": "DILLINGHAM",
    "Nic Claxton": "CLAXTON",
    "Leonard Miller": "L. MILLER",
    "Zach Collins": "COLLINS",
    "Matas Buzelis": "BUZELIS",
    "Norman Powell": "POWELL",
    "Noa Essengue": "ESSENGUE",
    "Jalen Smith": "J. SMITH",
    "Tre Jones": "T. JONES",
    "Isaac Okoro": "OKORO",
    "Patrick Williams": "P. WILLIAMS",
}

# When two exact-coordinate portraits overlap vertically, the lower player is
# painted last (on top). Put the upper player's name above their portrait so
# that the lower portrait does not have to cover the label or face.
NAME_ABOVE = {"Nic Claxton", "Matas Buzelis", "Patrick Williams"}

HELVETICA_TTC = Path("/System/Library/Fonts/Helvetica.ttc")
HELVETICA_FACES = {"regular": 0, "bold": 1}
FONT_CACHE_DIR = _REPO / "cache" / "fonts"

_DARKO_NUMBER = r"[+\-\d.eE]+"
_DARKO_RECORD = re.compile(
    r'\{nba_id:(?P<nba_id>\d+),'
    r'player_name:"(?P<player_name>[^"]+)",'
    r'team_name:"(?P<team_name>[^"]+)",'
    r'tm_id:(?P<tm_id>\d+),'
    r'position:"(?P<position>[^"]+)",'
    r'season:(?P<season>\d+),'
    r'career_game_num:(?P<career_game_num>\d+),'
    rf'dpm:(?P<dpm>{_DARKO_NUMBER}),'
    rf'o_dpm:(?P<o_dpm>{_DARKO_NUMBER}),'
    rf'd_dpm:(?P<d_dpm>{_DARKO_NUMBER}),'
    r"box_dpm:"
)


def helvetica(weight: str = "regular") -> FontProperties:
    """Match the approved Sticky Stats chart typography."""
    fallback = "bold" if weight == "bold" else "medium"
    if not HELVETICA_TTC.exists():
        return body_font(fallback)
    extracted = FONT_CACHE_DIR / f"Helvetica-{weight}.ttf"
    if not extracted.exists():
        try:
            from fontTools.ttLib import TTCollection

            collection = TTCollection(str(HELVETICA_TTC))
            FONT_CACHE_DIR.mkdir(parents=True, exist_ok=True)
            collection.fonts[HELVETICA_FACES.get(weight, 0)].save(str(extracted))
        except Exception:
            return body_font(fallback)
    return FontProperties(fname=str(extracted))


def _fetch_html(url: str) -> str:
    response = requests.get(
        url,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml",
        },
        timeout=30,
    )
    response.raise_for_status()
    return response.text


def parse_nba_roster(html: str) -> pd.DataFrame:
    """Read the official roster array embedded in NBA.com's roster page."""
    marker = '"roster":'
    marker_index = html.find(marker)
    if marker_index < 0:
        raise ValueError("NBA.com roster payload was not found.")

    payload, _ = json.JSONDecoder().raw_decode(html[marker_index + len(marker):])
    rows = [
        {
            "nba_id": int(player["PLAYER_ID"]),
            "official_roster_name": str(player["PLAYER"]),
        }
        for player in payload
    ]
    roster = pd.DataFrame(rows)
    if roster.empty:
        raise ValueError("NBA.com roster payload was empty.")
    return roster


def _parse_darko_number(value: str) -> float:
    if value.startswith("-."):
        value = "-0" + value[1:]
    elif value.startswith("."):
        value = "0" + value
    return float(value)


def parse_darko_roster(html: str, roster_ids: set[int]) -> pd.DataFrame:
    """Extract full-precision DARKO records for the roster IDs only."""
    rows = []
    for match in _DARKO_RECORD.finditer(html):
        nba_id = int(match.group("nba_id"))
        if nba_id not in roster_ids:
            continue
        rows.append(
            {
                "nba_id": nba_id,
                "darko_name": match.group("player_name"),
                "darko_team_field": match.group("team_name"),
                "darko_team_id": int(match.group("tm_id")),
                "darko_position": match.group("position"),
                "darko_season": int(match.group("season")),
                "darko_career_game_num": int(match.group("career_game_num")),
                "dpm": _parse_darko_number(match.group("dpm")),
                "o_dpm": _parse_darko_number(match.group("o_dpm")),
                "d_dpm": _parse_darko_number(match.group("d_dpm")),
            }
        )
    return pd.DataFrame(rows)


def build_working_table(
    roster: pd.DataFrame,
    darko: pd.DataFrame,
    snapshot_time: datetime,
) -> pd.DataFrame:
    """Join official roster membership to DARKO without inventing missing values."""
    table = roster.merge(darko, on="nba_id", how="left", validate="one_to_one")
    for column in ["darko_team_id", "darko_season", "darko_career_game_num"]:
        table[column] = table[column].astype("Int64")
    table["data_available"] = table["dpm"].notna()
    table["roster_source"] = NBA_ROSTER_URL
    table["darko_source"] = DARKO_URL
    table["snapshot_date"] = snapshot_time.date().isoformat()
    table["snapshot_timestamp_ct"] = snapshot_time.isoformat(timespec="seconds")
    return table[
        [
            "nba_id",
            "official_roster_name",
            "darko_name",
            "darko_team_field",
            "darko_team_id",
            "darko_position",
            "darko_season",
            "darko_career_game_num",
            "o_dpm",
            "d_dpm",
            "dpm",
            "data_available",
            "roster_source",
            "darko_source",
            "snapshot_date",
            "snapshot_timestamp_ct",
        ]
    ]


def validate_working_table(table: pd.DataFrame) -> dict:
    """Validate coverage, identity, missingness, and component arithmetic."""
    if table["nba_id"].duplicated().any():
        raise ValueError("Working table contains duplicate NBA player IDs.")
    if table["official_roster_name"].duplicated().any():
        raise ValueError("Working table contains duplicate official roster names.")

    available = order_available_for_portrait_layers(table)
    missing = table.loc[~table["data_available"]].copy()
    if available.empty:
        raise ValueError("No official-roster players matched DARKO.")
    if available[["o_dpm", "d_dpm", "dpm"]].isna().any().any():
        raise ValueError("Available DARKO rows contain missing impact values.")
    if missing[["o_dpm", "d_dpm", "dpm"]].notna().any().any():
        raise ValueError("Unavailable DARKO rows contain invented impact values.")

    aliases = available.loc[
        available["official_roster_name"] != available["darko_name"],
        ["official_roster_name", "darko_name"],
    ]
    unexpected_aliases = {
        tuple(row)
        for row in aliases.itertuples(index=False, name=None)
        if tuple(row) != ("Nic Claxton", "Nicolas Claxton")
    }
    if unexpected_aliases:
        raise ValueError(f"Unexpected NBA/DARKO name aliases: {unexpected_aliases}")

    available["component_residual"] = (
        available["dpm"] - available["o_dpm"] - available["d_dpm"]
    ).abs()
    max_residual = float(available["component_residual"].max())
    if max_residual > 0.00002:
        raise ValueError(
            f"DPM component residual exceeded tolerance: {max_residual:.8f}"
        )

    roster_names = set(table["official_roster_name"])
    missing_names = set(missing["official_roster_name"])
    reference_changes = []
    for name, expected in REFERENCE_DISPLAY_VALUES.items():
        row = available.loc[available["official_roster_name"] == name]
        if row.empty:
            reference_changes.append(f"{name}: DARKO row became unavailable")
            continue
        current = (
            round(float(row.iloc[0]["o_dpm"]), 1),
            round(float(row.iloc[0]["d_dpm"]), 1),
            round(float(row.iloc[0]["dpm"]), 1),
        )
        if current != expected:
            reference_changes.append(
                f"{name}: ODPM/DDPM/DPM {expected} -> {current}"
            )

    return {
        "roster_count": len(table),
        "available_count": len(available),
        "missing_count": len(missing),
        "missing_names": sorted(missing_names),
        "roster_added": sorted(roster_names - REFERENCE_ROSTER),
        "roster_removed": sorted(REFERENCE_ROSTER - roster_names),
        "availability_added": sorted(REFERENCE_MISSING - missing_names),
        "availability_removed": sorted(missing_names - REFERENCE_MISSING),
        "display_value_changes": reference_changes,
        "max_component_residual": max_residual,
    }


def order_available_for_portrait_layers(table: pd.DataFrame) -> pd.DataFrame:
    """Draw lower-DDPM portraits last so lower faces remain fully visible."""
    return (
        table.loc[table["data_available"]]
        .copy()
        .sort_values(
            ["d_dpm", "official_roster_name"],
            ascending=[False, True],
        )
    )


def write_table(table: pd.DataFrame, snapshot_date: str) -> Path:
    path = OUT / f"{snapshot_date}-current-bulls-darko-landscape-working.csv"
    path.parent.mkdir(parents=True, exist_ok=True)
    table.to_csv(path, index=False)
    return path


def chart_x(value: float) -> float:
    x0, _, x1, _ = PANEL
    return x0 + (value - ODPM_LIMITS[0]) / (
        ODPM_LIMITS[1] - ODPM_LIMITS[0]
    ) * (x1 - x0)


def chart_y(value: float) -> float:
    _, y0, _, y1 = PANEL
    return y0 + (value - DDPM_LIMITS[0]) / (
        DDPM_LIMITS[1] - DDPM_LIMITS[0]
    ) * (y1 - y0)


def square_headshot_label(
    ax,
    image_path: Path,
    x: float,
    y: float,
    half_size: float,
):
    """Place a square center crop without adding a ranking-coded border."""
    try:
        image = plt.imread(image_path)
    except (FileNotFoundError, OSError, ValueError):
        return ax.add_patch(
            FancyBboxPatch(
                (x - half_size, y - half_size),
                2 * half_size,
                2 * half_size,
                boxstyle="square,pad=0",
                facecolor="#DDD8D1",
                edgecolor="none",
                zorder=8,
            )
        )

    height, width = image.shape[:2]
    side = min(height, width)
    left = max(0, (width - side) // 2)
    top = max(0, (height - side) // 2)
    square = image[top:top + side, left:left + side]
    return ax.imshow(
        square,
        extent=[x - half_size, x + half_size, y - half_size, y + half_size],
        interpolation="bilinear",
        zorder=8,
    )


def ensure_headshots(available: pd.DataFrame) -> None:
    """Populate the existing NBA CDN cache for every plotted player."""
    for nba_id in available["nba_id"].astype(int):
        path = HEADSHOTS / f"{nba_id}.png"
        if not path.exists():
            get_player_headshot(nba_id)


def render_chart_only(
    table: pd.DataFrame,
    snapshot_date: str,
    final: bool,
) -> Path:
    """Render the flat chart-only asset for external Canva framing."""
    theme = DEFAULT_THEME
    panel_fill = "#F5F1EC"
    available = order_available_for_portrait_layers(table)

    fig = plt.figure(figsize=(CHART_WIDTH / DRAFT_DPI, CHART_HEIGHT / DRAFT_DPI))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, CHART_WIDTH)
    ax.set_ylim(0, CHART_HEIGHT)
    ax.set_aspect("equal")
    ax.set_xticks([])
    ax.set_yticks([])
    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.patch.set_alpha(0)

    x0, y0, x1, y1 = PANEL
    ax.add_patch(
        FancyBboxPatch(
            (x0 - 16, y0 - 14),
            x1 - x0 + 30,
            y1 - y0 + 26,
            boxstyle="round,pad=0,rounding_size=12",
            facecolor=panel_fill,
            edgecolor="none",
            zorder=0,
        )
    )

    for value in [-2.0, -1.0, 0.0, 1.0]:
        x = chart_x(value)
        is_zero = value == 0.0
        ax.plot(
            [x, x],
            [y0, y1],
            color=theme.muted if is_zero else theme.grid,
            lw=1.25 if is_zero else 1.0,
            linestyle=(0, (4, 4)) if is_zero else "solid",
            alpha=0.72 if is_zero else 1.0,
            zorder=2,
        )
        ax.plot([x, x], [y0, y0 - 9], color=theme.ink, lw=1.5, zorder=5)
        ax.text(
            x,
            y0 - 20,
            f"{value:g}",
            ha="center",
            va="top",
            fontsize=12.5,
            color=theme.ink,
            fontproperties=helvetica(),
        )

    for value in [-1.0, 0.0, 1.0]:
        y = chart_y(value)
        is_zero = value == 0.0
        ax.plot(
            [x0, x1],
            [y, y],
            color=theme.muted if is_zero else theme.grid,
            lw=1.25 if is_zero else 1.0,
            linestyle=(0, (4, 4)) if is_zero else "solid",
            alpha=0.72 if is_zero else 1.0,
            zorder=2,
        )
        ax.plot([x0, x0 - 9], [y, y], color=theme.ink, lw=1.5, zorder=5)
        ax.text(
            x0 - 18,
            y,
            f"{value:g}",
            ha="right",
            va="center",
            fontsize=12.5,
            color=theme.ink,
            fontproperties=helvetica(),
        )

    ax.plot([x0, x1], [y0, y0], color=theme.ink, lw=2.1, zorder=5)
    ax.plot([x0, x0], [y0, y1], color=theme.ink, lw=2.1, zorder=5)

    def quadrant_pill(
        anchor_x: float,
        anchor_y: float,
        horizontal: str,
        vertical: str,
        title: str,
        detail: str,
    ) -> None:
        """Draw one descriptive sign-based quadrant key."""
        detail_font = body_font("regular")
        title_probe = ax.text(
            0,
            0,
            title,
            fontsize=9.3,
            fontproperties=helvetica("bold"),
            alpha=0,
        )
        title_width = rendered_width(ax, title_probe)
        title_probe.remove()
        detail_probe = ax.text(
            0,
            0,
            detail,
            fontsize=8.2,
            fontproperties=detail_font,
            alpha=0,
        )
        detail_width = rendered_width(ax, detail_probe)
        detail_probe.remove()

        box_width = max(title_width, detail_width) + 24
        box_height = 50
        left = anchor_x if horizontal == "left" else anchor_x - box_width
        bottom = anchor_y if vertical == "bottom" else anchor_y - box_height
        ax.add_patch(
            FancyBboxPatch(
                (left, bottom),
                box_width,
                box_height,
                boxstyle="round,pad=0,rounding_size=9",
                facecolor=theme.canvas,
                edgecolor=theme.rule,
                linewidth=1.0,
                alpha=0.94,
                zorder=10,
            )
        )
        ax.text(
            left + 12,
            bottom + box_height - 16,
            title,
            ha="left",
            va="center",
            fontsize=9.3,
            color=theme.ink,
            fontproperties=helvetica("bold"),
            zorder=11,
        )
        ax.text(
            left + 12,
            bottom + 15,
            detail,
            ha="left",
            va="center",
            fontsize=8.2,
            color=theme.muted,
            fontproperties=detail_font,
            zorder=11,
        )

    quadrant_pill(
        x0 + 14,
        y1 - 14,
        "left",
        "top",
        "DEFENSE-POSITIVE",
        "↓ ODPM  ↑ DDPM",
    )
    quadrant_pill(
        x1 - 14,
        y1 - 14,
        "right",
        "top",
        "POSITIVE ON BOTH",
        "↑ ODPM  ↑ DDPM",
    )
    quadrant_pill(
        x0 + 14,
        y0 + 14,
        "left",
        "bottom",
        "NEGATIVE ON BOTH",
        "↓ ODPM  ↓ DDPM",
    )
    quadrant_pill(
        x1 - 14,
        y0 + 14,
        "right",
        "bottom",
        "OFFENSE-POSITIVE",
        "↑ ODPM  ↓ DDPM",
    )

    half_size = 36
    for layer_index, row in enumerate(available.itertuples(index=False)):
        point_x = chart_x(float(row.o_dpm))
        point_y = chart_y(float(row.d_dpm))
        image_zorder = 6.0 + layer_index * 0.2
        label_zorder = image_zorder + 0.1

        image = square_headshot_label(
            ax,
            HEADSHOTS / f"{int(row.nba_id)}.png",
            point_x,
            point_y,
            half_size=half_size,
        )
        image.set_zorder(image_zorder)

        name_above = row.official_roster_name in NAME_ABOVE
        name_y = point_y + half_size + 7 if name_above else point_y - half_size - 7
        ax.text(
            point_x,
            name_y,
            SHORT_NAMES[row.official_roster_name],
            ha="center",
            va="bottom" if name_above else "top",
            fontsize=8.4,
            color=theme.ink,
            fontproperties=helvetica("bold"),
            zorder=label_zorder,
        )

    ax.text(
        (x0 + x1) / 2,
        105,
        "ODPM",
        ha="center",
        va="center",
        fontsize=17,
        color=theme.ink,
        fontproperties=helvetica("bold"),
    )
    direction_fontsize = 9.7
    offense_direction = "BETTER OFFENSIVE IMPACT"
    offense_probe = ax.text(
        0,
        0,
        offense_direction,
        fontsize=direction_fontsize,
        fontproperties=helvetica("bold"),
        alpha=0,
    )
    offense_width = rendered_width(ax, offense_probe)
    offense_probe.remove()
    offense_x = x0 + 8
    ax.text(
        offense_x,
        105,
        offense_direction,
        ha="left",
        va="center",
        fontsize=direction_fontsize,
        color=theme.ink,
        fontproperties=helvetica("bold"),
    )
    offense_arrow_y = 108
    ax.add_patch(
        FancyArrowPatch(
            (offense_x + offense_width + 7, offense_arrow_y),
            (offense_x + offense_width + 43, offense_arrow_y),
            arrowstyle="-|>",
            mutation_scale=11,
            linewidth=1.35,
            color=theme.accent,
            zorder=8,
        )
    )
    ax.text(
        90,
        (y0 + y1) / 2,
        "DDPM",
        ha="center",
        va="center",
        rotation=90,
        fontsize=17,
        color=theme.ink,
        fontproperties=helvetica("bold"),
    )
    defense_direction = "BETTER DEFENSIVE IMPACT"
    defense_probe = ax.text(
        0,
        0,
        defense_direction,
        fontsize=direction_fontsize,
        fontproperties=helvetica("bold"),
        alpha=0,
    )
    defense_height = rendered_width(ax, defense_probe)
    defense_probe.remove()
    defense_bottom = y0 + 22
    defense_x = x0 - 49
    ax.text(
        defense_x,
        defense_bottom + defense_height / 2,
        defense_direction,
        ha="center",
        va="center",
        rotation=90,
        fontsize=direction_fontsize,
        color=theme.ink,
        fontproperties=helvetica("bold"),
    )
    defense_arrow_x = defense_x - 3
    ax.add_patch(
        FancyArrowPatch(
            (defense_arrow_x, defense_bottom + defense_height + 7),
            (defense_arrow_x, defense_bottom + defense_height + 43),
            arrowstyle="-|>",
            mutation_scale=11,
            linewidth=1.35,
            color=theme.accent,
            zorder=8,
        )
    )
    output = OUT / f"{snapshot_date}-current-bulls-darko-landscape-chart.png"
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output, dpi=export_dpi(final), transparent=True)
    plt.close(fig)
    return output


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--final",
        action="store_true",
        help="Export at 300 DPI; first-review drafts should omit this.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    snapshot_time = datetime.now(SNAPSHOT_TZ)
    roster_html = _fetch_html(NBA_ROSTER_URL)
    darko_html = _fetch_html(DARKO_URL)

    roster = parse_nba_roster(roster_html)
    darko = parse_darko_roster(darko_html, set(roster["nba_id"].astype(int)))
    table = build_working_table(roster, darko, snapshot_time)
    report = validate_working_table(table)

    snapshot_date = snapshot_time.date().isoformat()
    table_path = write_table(table, snapshot_date)
    ensure_headshots(table.loc[table["data_available"]])
    chart_path = render_chart_only(table, snapshot_date, args.final)

    print(json.dumps(report, indent=2))
    print(f"Wrote {table_path}")
    print(f"Wrote {chart_path}")


if __name__ == "__main__":
    main()
