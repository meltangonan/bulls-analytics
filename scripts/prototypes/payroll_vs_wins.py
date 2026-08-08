"""Build the Bulls payroll-share vs win-percentage chart asset for Canva.

Two panels sharing one season axis, 2011-12 through 2025-26:

* top -- columns of payroll as a share of that season's salary cap, with the
  dead-money portion drawn as a darker foot on each column;
* bottom -- a line of regular-season win percentage.

Read it by looking straight down a season. A single combo chart was rejected:
both measures are percentages, so one axis would be honest, but they occupy
different bands and a shared axis implies the two numbers are comparable in
magnitude. They are percentages of unrelated things.

Salary is not an NBA.com statistic, and the sites that compile it prohibit
automated access, so this reads a committed hand-captured snapshot from
this post's own tracked ``docs/visuals/`` data folder rather than fetching. The header
carry the sources, the year-convention trap, and the 2015-16 correction;
``tests/test_payroll_vs_wins.py`` asserts the reconciliations that caught it.

Title, subtitle, source line, and watermark belong on the Canva page (DESIGN.md
section 3).
"""

from __future__ import annotations

import argparse
import csv
import sys
from dataclasses import dataclass
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO))

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import to_rgb
from matplotlib.patches import Rectangle

from bulls.graphics.house import DEFAULT_THEME, export_dpi, helvetica

# One slug names both the post's tracked folder and its scratch folder, so the two
# mirror each other and a render never has to be hunted for (DEVELOPMENT.md).
SLUG = "2026-08-08-payroll-vs-wins"
PROJECT = _REPO / "docs" / "visuals" / SLUG
SNAPSHOT = PROJECT / "data" / "2026-08-08-bulls-payroll-vs-wins.csv"
OUT = _REPO / "output" / SLUG

CHART_WIDTH = 1080
CHART_HEIGHT = 1120
DRAFT_DPI = 150

# Seasons the league did not play in full. Win percentage already handles this;
# the note exists so the Canva page can say so rather than inviting the question.
SHORT_SEASONS = {"2011-12": 66, "2019-20": 65, "2020-21": 72}

# Win-percentage points worth a number on the chart, and which side of the line
# the label clears. Peaks take the label above, troughs below.
CALLOUTS = {
    "2011-12": "above",
    "2018-19": "below",
    "2021-22": "above",
    "2025-26": "below",
}

# Top-to-bottom colour ramps, matching the assist-duos board so the two posts read
# as the same hand. Lighter at the top, deeper at the base. No drop shadow here:
# these columns sit on a gridline rather than floating on a card.
BAR_WIDTH = 0.68
RED_BAR_GRADIENT = ("#E12C52", "#A80E35")
DARK_BAR_GRADIENT = ("#333333", "#0C0C0C")


@dataclass(frozen=True)
class Season:
    season: str
    payroll: int
    dead_cap: int
    salary_cap: int
    wins: int
    losses: int

    @property
    def cap_share(self) -> float:
        return self.payroll / self.salary_cap

    @property
    def dead_share(self) -> float:
        """Dead money as a share of the cap -- the darker foot of the column."""
        return self.dead_cap / self.salary_cap

    @property
    def win_pct(self) -> float:
        return self.wins / (self.wins + self.losses)

    @property
    def games(self) -> int:
        return self.wins + self.losses


def load_seasons(path: Path = SNAPSHOT) -> list[Season]:
    """Read the snapshot, skipping its ``#`` provenance header."""
    with path.open() as handle:
        rows = csv.DictReader(line for line in handle if not line.startswith("#"))
        seasons = [
            Season(
                season=row["season"],
                payroll=int(row["payroll"]),
                dead_cap=int(row["dead_cap"]),
                salary_cap=int(row["salary_cap"]),
                wins=int(row["wins"]),
                losses=int(row["losses"]),
            )
            for row in rows
        ]
    if not seasons:
        raise ValueError(f"No data rows in {path}")
    return seasons


def _gradient_column(ax, x: float, low: float, high: float, colors, zorder: int) -> None:
    """Fill one span of a column with a top-to-bottom colour ramp.

    matplotlib bars take a flat facecolor, so the ramp is drawn as an image and
    clipped to an invisible rectangle the size of the span. Same technique the
    assist-duos board uses for its split bars.
    """
    if high <= low:
        return
    top, bottom = (np.array(to_rgb(c)) for c in colors)
    ramp = np.linspace(bottom, top, 256).reshape(256, 1, 3)
    left = x - BAR_WIDTH / 2
    clip = Rectangle(
        (left, low), BAR_WIDTH, high - low, facecolor="none", edgecolor="none"
    )
    ax.add_patch(clip)
    image = ax.imshow(
        ramp,
        extent=(left, left + BAR_WIDTH, low, high),
        origin="lower",
        aspect="auto",
        interpolation="bicubic",
        zorder=zorder,
    )
    image.set_clip_path(clip)


def render_chart(seasons: list[Season], *, final: bool = False) -> Path:
    """Render the transparent two-panel asset for Canva."""
    theme = DEFAULT_THEME
    label_font = helvetica()
    bold_font = helvetica("bold")

    fig = plt.figure(figsize=(CHART_WIDTH / DRAFT_DPI, CHART_HEIGHT / DRAFT_DPI))
    # Top panel taller: the columns carry the argument, the line supplies the verdict.
    top, bottom = fig.subplots(
        2, 1, sharex=True, gridspec_kw={"height_ratios": [1.45, 1], "hspace": 0.045}
    )

    positions = range(len(seasons))
    labels = [s.season for s in seasons]

    # --- top panel: payroll as a share of the cap ---------------------------
    for x, season in zip(positions, seasons):
        # Red from the dead-money line up to full payroll, dark below it. Drawing
        # the foot second means the split stays a hard edge inside one column.
        _gradient_column(
            top, x, season.dead_share * 100, season.cap_share * 100, RED_BAR_GRADIENT, 3
        )
        _gradient_column(
            top, x, 0, season.dead_share * 100, DARK_BAR_GRADIENT, 4
        )

    # The cap itself is the reference the columns are measured against. The line
    # stops at the last column so its label can sit in the right margin; nearly
    # every column clears 100%, so there is no gap over the data to label into.
    top.plot(
        [-0.7, len(seasons) - 0.4],
        [100, 100],
        color=theme.muted,
        linestyle=(0, (4, 3)),
        linewidth=1.2,
        zorder=5,
    )
    top.text(
        len(seasons) - 0.2,
        100,
        "SALARY CAP",
        fontproperties=bold_font,
        fontsize=9,
        color=theme.muted,
        ha="left",
        va="center",
    )

    for x, season in zip(positions, seasons):
        top.text(
            x,
            season.cap_share * 100 + 2.5,
            f"{season.cap_share * 100:.0f}%",
            fontproperties=bold_font,
            fontsize=9,
            color=theme.ink,
            ha="center",
            va="bottom",
            zorder=6,
        )

    top.set_ylim(0, max(s.cap_share for s in seasons) * 100 + 12)
    top.set_ylabel(
        "PAYROLL AS SHARE OF CAP", fontproperties=bold_font, fontsize=10, color=theme.muted
    )
    top.yaxis.set_major_formatter(lambda value, _: f"{value:.0f}%")

    # --- bottom panel: win percentage ---------------------------------------
    bottom.plot(
        positions,
        [s.win_pct for s in seasons],
        color=theme.ink,
        linewidth=2.4,
        marker="o",
        markersize=7,
        markerfacecolor=theme.accent,
        markeredgecolor=theme.accent,
        zorder=3,
    )
    bottom.plot(
        [-0.7, len(seasons) - 0.4],
        [0.5, 0.5],
        color=theme.muted,
        linestyle=(0, (4, 3)),
        linewidth=1.2,
        zorder=2,
    )
    bottom.text(
        len(seasons) - 0.2,
        0.5,
        ".500",
        fontproperties=bold_font,
        fontsize=9,
        color=theme.muted,
        ha="left",
        va="center",
    )

    # Label the bends only. A value on every point is trivia and collides with
    # the line through the steep stretches (DESIGN.md section 4).
    for season_name, placement in CALLOUTS.items():
        index = next(i for i, s in enumerate(seasons) if s.season == season_name)
        season = seasons[index]
        offset = 0.035 if placement == "above" else -0.035
        bottom.text(
            index,
            season.win_pct + offset,
            f"{season.win_pct:.3f}".lstrip("0"),
            fontproperties=bold_font,
            fontsize=10,
            color=theme.ink,
            ha="center",
            va="bottom" if placement == "above" else "top",
            zorder=5,
        )

    bottom.set_ylim(0.13, 0.87)
    bottom.set_ylabel("WIN PCT", fontproperties=bold_font, fontsize=10, color=theme.muted)

    # --- shared season axis --------------------------------------------------
    bottom.set_xticks(list(positions))
    bottom.set_xticklabels(labels, rotation=45, ha="right")
    for tick in bottom.get_xticklabels():
        tick.set_fontproperties(label_font)
        tick.set_fontsize(9)
        tick.set_color(theme.ink)

    for panel in (top, bottom):
        # Right margin exists so the reference-line labels never sit on the data.
        panel.set_xlim(-0.7, len(seasons) + 1.9)
        panel.grid(axis="y", color=theme.grid, linewidth=1.0, zorder=0)
        panel.set_axisbelow(True)
        for spine in panel.spines.values():
            spine.set_visible(False)
        panel.tick_params(axis="both", length=0, colors=theme.muted)
        for tick in panel.get_yticklabels():
            tick.set_fontproperties(label_font)
            tick.set_fontsize(9)

    fig.subplots_adjust(left=0.11, right=0.98, top=0.98, bottom=0.11)

    OUT.mkdir(parents=True, exist_ok=True)
    output = OUT / "2026-08-08-payroll-vs-wins.png"
    fig.savefig(output, dpi=export_dpi(final), transparent=True)
    plt.close(fig)
    return output


def canva_copy_block(seasons: list[Season]) -> str:
    """Exact strings for the Canva page, from the same run as the chart.

    Never retype a number from the chart by eye (DESIGN.md section 3).
    """
    recent = [s for s in seasons if s.season >= "2020-21"]
    share_lo = min(s.cap_share for s in recent) * 100
    share_hi = max(s.cap_share for s in recent) * 100
    wins_lo = min(s.wins for s in recent)
    wins_hi = max(s.wins for s in recent)
    dearest = max(seasons, key=lambda s: s.cap_share)
    deadest = max(seasons, key=lambda s: s.dead_share)
    short = ", ".join(f"{name} ({games} games)" for name, games in SHORT_SEASONS.items())

    return "\n".join(
        [
            "--- CANVA COPY ---",
            "",
            f"Across the last {len(recent)} seasons the Bulls spent between",
            f"{share_lo:.0f}% and {share_hi:.0f}% of the salary cap every year",
            f"and won between {wins_lo} and {wins_hi} games.",
            "",
            f"MOST EXPENSIVE: {dearest.season} at {dearest.cap_share * 100:.0f}% of cap "
            f"({dearest.wins}-{dearest.losses}).",
            f"MOST DEAD MONEY: {deadest.season}, ${deadest.dead_cap:,} "
            f"({deadest.dead_share * 100:.0f}% of that season's cap) paid to players "
            "no longer on the roster.",
            "",
            "The NBA salary cap is soft. Teams exceed it legally using Bird rights",
            "and exceptions, which is why most columns clear 100%.",
            "",
            "Payroll is cap charge including dead money. Black foot on each column",
            "is the dead-money share.",
            f"Shortened seasons: {short}. Win pct accounts for this.",
            "",
            "SOURCE: Payroll and dead cap via Spotrac · Salary cap and records via "
            "Basketball Reference · Captured 2026-08-08",
            "",
            "--- END ---",
        ]
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--final",
        action="store_true",
        help="Export at final DPI; first-review drafts should omit this.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    seasons = load_seasons()
    chart_path = render_chart(seasons, final=args.final)

    print(f"{'SEASON':<9} {'CAP SHARE':>10} {'DEAD':>8} {'RECORD':>8} {'WIN PCT':>8}")
    for season in seasons:
        print(
            f"{season.season:<9} {season.cap_share * 100:>9.1f}% "
            f"{season.dead_share * 100:>7.1f}% "
            f"{f'{season.wins}-{season.losses}':>8} {season.win_pct:>8.3f}"
        )

    print(f"\nWrote {chart_path}\n")
    print(canva_copy_block(seasons))


if __name__ == "__main__":
    main()
