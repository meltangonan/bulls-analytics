"""Rank Bulls regular-season win percentage against every current opponent.

The ranked field is deliberately split into two equal-width column-chart assets
for a carousel.  Both assets use the same 25–65% vertical scale, and form one
continuous master image.  Minnesota begins the second slide, giving ranks 1–14
and ranks 15–29 a clean, intentional swipe transition.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO))

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.image import imread
from matplotlib.offsetbox import AnnotationBbox, OffsetImage
from PIL import Image

from bulls.graphics.house import DEFAULT_THEME, export_dpi, helvetica
from scripts.prototypes.top_game_performances import (
    FIRST_SEASON_END_YEAR,
    LAST_SEASON_END_YEAR,
    fetch_bulls_team_games,
    season_label,
    team_source_url,
)


SLUG = "best-bulls-winpct-by-opponent"
PROJECT = _REPO / "docs" / "visuals" / f"2026-08-31-{SLUG}"
DATA_DIR = PROJECT / "data"
LOGO_DIR = PROJECT / "assets" / "logos"
OUT = _REPO / "output" / SLUG

MIN_MEETINGS = 40
SLIDES = ((1, 14), (15, 29))
SCALE_MIN = 25
SCALE_MAX = 65
CHART_WIDTH = 1800
CHART_HEIGHT = 1600
DRAFT_DPI = 150
LOGO_ZOOM = 0.115  # approximately the visual width of a 0.70-unit bar

# These are franchise-continuity mappings: they preserve the original source
# rows while grouping an old NBA.com abbreviation with its current franchise.
HISTORICAL_TO_CURRENT = {
    "NJN": "BKN",
    "NOH": "NOP",
    "NOK": "NOP",
    "SEA": "OKC",
    "VAN": "MEM",
    "CHH": "CHA",
}

FRANCHISE_NAMES = {
    "ATL": "Hawks", "BOS": "Celtics", "BKN": "Nets", "CHA": "Hornets",
    "CLE": "Cavaliers", "DAL": "Mavericks", "DEN": "Nuggets", "DET": "Pistons",
    "GSW": "Warriors", "HOU": "Rockets", "IND": "Pacers", "LAC": "Clippers",
    "LAL": "Lakers", "MEM": "Grizzlies", "MIA": "Heat", "MIL": "Bucks",
    "MIN": "Timberwolves", "NOP": "Pelicans", "NYK": "Knicks", "OKC": "Thunder",
    "ORL": "Magic", "PHI": "76ers", "PHX": "Suns", "POR": "Trail Blazers",
    "SAC": "Kings", "SAS": "Spurs", "TOR": "Raptors", "UTA": "Jazz", "WAS": "Wizards",
}

# Reuse the conference colors settled for the 30+ points-vs-opponent chart.
# They distinguish opponents without changing what the height encodes.
WEST_FILL = "#FF003E"
EAST_FILL = "#2A54C0"
FRANCHISE_CONFERENCES = {
    "ATL": "East", "BOS": "East", "BKN": "East", "CHA": "East", "CLE": "East",
    "DAL": "West", "DEN": "West", "DET": "East", "GSW": "West", "HOU": "West",
    "IND": "East", "LAC": "West", "LAL": "West", "MEM": "West", "MIA": "East",
    "MIL": "East", "MIN": "West", "NOP": "West", "NYK": "East", "OKC": "West",
    "ORL": "East", "PHI": "East", "PHX": "West", "POR": "West", "SAC": "West",
    "SAS": "West", "TOR": "East", "UTA": "West", "WAS": "East",
}


def current_opponent(code: str) -> str:
    """Return the current franchise code for one NBA.com opponent abbreviation."""
    return HISTORICAL_TO_CURRENT.get(str(code), str(code))


def opponent_from_matchup(matchup: str) -> str:
    """Extract the opponent abbreviation from a Bulls home or road matchup."""
    text = str(matchup)
    if "vs." in text:
        return text.split("vs.", 1)[1].strip()
    if "@" in text:
        return text.split("@", 1)[1].strip()
    raise ValueError(f"Cannot read an opponent from matchup {matchup!r}.")


def fetch_team_history(*, refresh: bool = False) -> pd.DataFrame:
    """Load one regular-season Bulls team-game row for every season since 2000."""
    frames = [
        fetch_bulls_team_games(end_year, refresh=refresh)
        for end_year in range(FIRST_SEASON_END_YEAR, LAST_SEASON_END_YEAR + 1)
    ]
    return pd.concat(frames, ignore_index=True)


def build_summary(games: pd.DataFrame, *, min_meetings: int = MIN_MEETINGS) -> pd.DataFrame:
    """Calculate one current-franchise row per opponent from distinct Bulls games."""
    required = {"game_id", "matchup", "result", "season_end_year"}
    missing = required - set(games.columns)
    if missing:
        raise ValueError(f"Team-game data is missing {sorted(missing)}.")
    if games.duplicated("game_id").any():
        raise ValueError("Team-game data contains duplicate Bulls game IDs.")

    rows = games[["game_id", "matchup", "result"]].copy()
    rows["source_opponent"] = rows["matchup"].map(opponent_from_matchup)
    rows["franchise"] = rows["source_opponent"].map(current_opponent)
    rows["win"] = rows["result"].eq("W")
    if not rows["result"].isin(["W", "L"]).all():
        raise ValueError("Regular-season results must be W or L.")

    summary = rows.groupby("franchise", as_index=False).agg(
        wins=("win", "sum"), meetings=("game_id", "nunique")
    )
    missing_franchises = set(FRANCHISE_NAMES) - set(summary["franchise"])
    unexpected_franchises = set(summary["franchise"]) - set(FRANCHISE_NAMES)
    if missing_franchises or unexpected_franchises:
        raise ValueError(
            f"Current franchise field mismatch; missing={sorted(missing_franchises)}, "
            f"unexpected={sorted(unexpected_franchises)}."
        )
    summary["wins"] = summary["wins"].astype(int)
    summary["meetings"] = summary["meetings"].astype(int)
    summary["losses"] = summary["meetings"] - summary["wins"]
    summary["win_pct"] = summary["wins"] / summary["meetings"] * 100
    summary["team"] = summary["franchise"].map(FRANCHISE_NAMES)
    summary["conference"] = summary["franchise"].map(FRANCHISE_CONFERENCES)
    if summary["conference"].isna().any():
        raise ValueError("Every current opponent must have a conference color.")
    summary["eligible"] = summary["meetings"] >= min_meetings
    if not summary["eligible"].all():
        thin = summary.loc[~summary["eligible"], "franchise"].tolist()
        raise ValueError(f"Opponent sample is below {min_meetings} meetings: {thin}")
    summary = summary.sort_values(
        ["win_pct", "wins", "meetings", "team"], ascending=[False, False, False, True], kind="stable"
    ).reset_index(drop=True)
    summary["rank"] = summary.index + 1
    summary["minimum_meetings"] = min_meetings
    summary["coverage_start"] = season_label(FIRST_SEASON_END_YEAR)
    summary["coverage_end"] = season_label(LAST_SEASON_END_YEAR)
    return summary[
        ["rank", "franchise", "team", "conference", "wins", "losses", "meetings", "win_pct", "minimum_meetings",
         "coverage_start", "coverage_end"]
    ]


def validate_summary(summary: pd.DataFrame, games: pd.DataFrame) -> dict[str, int | float]:
    """Fail loudly if the ranked output no longer reconstructs the source games."""
    if len(summary) != 29 or summary["franchise"].duplicated().any():
        raise ValueError("The ranking must contain each of the 29 current opponent franchises once.")
    if summary["meetings"].min() < MIN_MEETINGS:
        raise ValueError("A displayed opponent falls below the meeting threshold.")
    if int(summary["meetings"].sum()) != games["game_id"].nunique():
        raise ValueError("Opponent meetings do not reconcile to Bulls team games.")
    expected_wins = int(games["result"].eq("W").sum())
    if int(summary["wins"].sum()) != expected_wins:
        raise ValueError("Opponent wins do not reconcile to Bulls wins.")
    if not summary["win_pct"].is_monotonic_decreasing:
        raise ValueError("Opponent ranking must descend by win percentage.")
    return {
        "opponent_count": len(summary),
        "meeting_count": int(summary["meetings"].sum()),
        "win_count": expected_wins,
        "min_meetings": int(summary["meetings"].min()),
    }


def render_continuous_chart(summary: pd.DataFrame, *, final: bool = False) -> Path:
    """Render all 29 ranks on one canvas that can be cut into seamless tiles."""
    if len(summary) != 29:
        raise ValueError("The continuous chart requires all 29 ranked opponents.")
    theme = DEFAULT_THEME
    full_width = CHART_WIDTH * 2
    fig, ax = plt.subplots(figsize=(full_width / DRAFT_DPI, CHART_HEIGHT / DRAFT_DPI))
    fig.patch.set_alpha(0)
    ax.set_facecolor("none")
    # The left crop carries 14 ranks and the right carries 15.  Giving each
    # half its own equal-width plotting area keeps MIN wholly on slide two
    # while retaining the exact central crop and the shared vertical frame.
    ax.remove()
    axes = [
        fig.add_axes((0.0225, 0.08, 0.4775, 0.83)),
        fig.add_axes((0.5, 0.08, 0.4775, 0.83)),
    ]

    for ax, (first_rank, last_rank) in zip(axes, SLIDES, strict=True):
        rows = summary.iloc[first_rank - 1:last_rank]
        x = np.arange(1, len(rows) + 1)
        colors = [WEST_FILL if conference == "West" else EAST_FILL for conference in rows["conference"]]
        # A deliberately zoomed, labeled baseline makes the small differences
        # in this compact ranking legible. Bars still expose their exact value.
        ax.bar(
            x, rows["win_pct"] - SCALE_MIN, bottom=SCALE_MIN,
            width=0.70, color=colors, zorder=3,
        )
        ax.axhline(50, color=theme.muted, linewidth=1.2, linestyle=(0, (3, 3)), zorder=1)

        for slot, row in enumerate(rows.itertuples(index=False), start=1):
            value_y = float(row.win_pct)
            # Keep both data labels inside the fill. The compact type treatment
            # prevents a five-character percentage from reaching past a narrow bar.
            ax.text(slot, value_y - 0.78, f"{value_y:.1f}%",
                    ha="center", va="top", color="white",
                    fontsize=11.5, fontproperties=helvetica("bold"), zorder=4)
            ax.text(slot, value_y - 1.84, f"{row.wins}–{row.losses}",
                    ha="center", va="top", color="white",
                    fontsize=8.1, fontproperties=helvetica("oblique"), zorder=4)
            # The reference's diamond-and-stem annotation becomes an NBA logo,
            # team label, and record. It leaves the baseline unburdened.
            label_y = min(SCALE_MAX + 1.5, value_y + 6.0)
            ax.plot([slot, slot], [value_y + 0.35, label_y - 0.85], color=theme.ink,
                    linewidth=1.35, zorder=2)
            logo_path = LOGO_DIR / f"{row.franchise}.png"
            if not logo_path.exists():
                raise ValueError(f"Missing opponent logo: {logo_path}")
            logo = OffsetImage(imread(logo_path), zoom=LOGO_ZOOM)
            ax.add_artist(AnnotationBbox(
                logo, (slot, label_y), frameon=False, pad=0, annotation_clip=False, zorder=5
            ))
            # The first label on the right crop begins at the literal swipe
            # edge. Anchor it inward so a long name (Timberwolves) cannot be
            # cut by the crop while its logo remains centered on the bar.
            label_x = 0.70 if first_rank > 1 and slot == 1 else slot
            label_ha = "left" if first_rank > 1 and slot == 1 else "center"
            ax.text(label_x, label_y + 1.35, row.team, ha=label_ha, va="bottom", color=theme.ink,
                    fontsize=9.6 if len(row.team) < 12 else 8.5, fontproperties=helvetica("bold"), zorder=6)

        ax.set_xlim(0.5, len(rows) + 0.5)
        # The unlabelled headroom is only for logo callouts, never for a value.
        ax.set_ylim(SCALE_MIN, SCALE_MAX + 5)
        ax.set_xticks([])
        y_ticks = np.arange(SCALE_MIN, SCALE_MAX + 0.1, 2.5)
        ax.set_yticks(y_ticks)
        ax.set_yticklabels(
            [f"{tick:.0f}%" if tick % 5 == 0 and first_rank == 1 else "" for tick in y_ticks],
            color=theme.muted, fontsize=10, fontproperties=helvetica(),
        )
        ax.tick_params(axis="y", length=0, pad=8)
        ax.grid(False)
        for spine in ax.spines.values():
            spine.set_visible(False)

    OUT.mkdir(parents=True, exist_ok=True)
    resolution = "final" if final else "draft"
    output = OUT / f"2026-08-31-bulls-opponent-win-pct-continuous-{resolution}.png"
    fig.savefig(output, dpi=export_dpi(final), transparent=True)
    plt.close(fig)
    return output


def crop_continuous_chart(source: Path, *, final: bool = False) -> tuple[Path, Path]:
    """Cut a continuous chart exactly in half for a swipe-through carousel."""
    with Image.open(source) as image:
        if image.width != CHART_WIDTH * 2 or image.height != CHART_HEIGHT:
            raise ValueError(f"Unexpected continuous-chart size {image.size}.")
        seam = image.width // 2
        resolution = "final" if final else "draft"
        left = OUT / f"2026-08-31-bulls-opponent-win-pct-ranks-01-14-{resolution}.png"
        right = OUT / f"2026-08-31-bulls-opponent-win-pct-ranks-15-29-{resolution}.png"
        image.crop((0, 0, seam, image.height)).save(left)
        image.crop((seam, 0, image.width, image.height)).save(right)
    return left, right


def write_data(games: pd.DataFrame, summary: pd.DataFrame) -> None:
    """Store this post's own source rows and calculated ranking for audit."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    saved = games.copy()
    saved["source_opponent"] = saved["matchup"].map(opponent_from_matchup)
    saved["franchise"] = saved["source_opponent"].map(current_opponent)
    saved.to_csv(DATA_DIR / "bulls-regular-season-team-games-2000-01-to-2025-26.csv", index=False)
    summary.to_csv(DATA_DIR / "bulls-win-percentage-by-opponent-summary.csv", index=False)


def copy_block(summary: pd.DataFrame, audit: dict[str, int | float]) -> str:
    """Return exact title, subtitle, and footnote strings for the Canva page."""
    first, last = summary.iloc[0], summary.iloc[-1]
    return "\n".join([
        "CANVA COPY",
        "Title: WHO HAVE THE BULLS DONE BEST AGAINST SINCE 2000?",
        "Subtitle: Chicago regular-season win percentage vs. every current NBA opponent",
        "Chart key: Blue = Eastern Conference opponent • red = Western Conference opponent • opponent logo • team • Bulls record",
        "Footnote: 2000–01 through 2025–26 regular seasons. Each bar is Bulls wins divided by Bulls games against that opponent. Historical team abbreviations are grouped with current franchises.",
        "Source: NBA.com LeagueGameFinder, Chicago Bulls team game logs; calculated locally",
        f"Check: {first.team} leads at {first.win_pct:.1f}% ({first.wins}-{first.losses}); {last.team} is last at {last.win_pct:.1f}% ({last.wins}-{last.losses}). {audit['meeting_count']} Bulls games total; every opponent has at least {audit['min_meetings']} meetings.",
    ])


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--refresh", action="store_true", help="Refetch cached NBA.com team-game rows.")
    parser.add_argument("--final", action="store_true", help="Render publish-resolution chart assets.")
    args = parser.parse_args()
    games = fetch_team_history(refresh=args.refresh)
    summary = build_summary(games)
    audit = validate_summary(summary, games)
    write_data(games, summary)
    continuous = render_continuous_chart(summary, final=args.final)
    left, right = crop_continuous_chart(continuous, final=args.final)
    print(f"Saved {continuous.relative_to(_REPO)}")
    print(f"Saved {left.relative_to(_REPO)}")
    print(f"Saved {right.relative_to(_REPO)}")
    print(f"Audit: {audit}")
    print(copy_block(summary, audit))


if __name__ == "__main__":
    main()
