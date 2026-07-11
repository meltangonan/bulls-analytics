"""Design-study wireframes for the Summer League report.

These are intentionally grayscale and use the already-settled Jul 14 sample data.
They test information structure, not final visual styling:

1. Repeated-row board (one scan pattern, one emphasized metric)
2. Player-as-columns comparison table (data reshaped before styling)
3. Editorial player story (one takeaway owns the slide)

The active ``summer_league_report.py`` prototype is not imported or modified so the
user's uncommitted carousel work remains an untouched baseline.
"""

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

import matplotlib

matplotlib.use("Agg")
import matplotlib.font_manager as fm
import matplotlib.pyplot as plt
from matplotlib.patches import Arc, Circle, Rectangle

from bulls.data.fetch import get_game_shots
from bulls.graphics.craft import headshot_label
from bulls.graphics.feed import DEFAULT_DPI, save_feed_post


OUT = REPO / "output" / "feed"
W, H = 1080, 1350
GAME_ID = "1522500033"

INK = "#202020"
MID = "#707070"
FAINT = "#A5A5A5"
RULE = "#D8D8D8"
LIGHT = "#F3F3F3"
LIGHTER = "#F8F8F8"
COURT = "#CEC9C1"
PANEL = "#FAF8F4"
BODY = {
    "regular": REPO / "assets" / "fonts" / "Archivo-400.ttf",
    "medium": REPO / "assets" / "fonts" / "Archivo-500.ttf",
    "bold": REPO / "assets" / "fonts" / "Archivo-600.ttf",
}

PLAYERS = [
    {
        "name": "Matas Buzelis",
        "id": 1641824,
        "pts": 28,
        "min": 31,
        "fg": "8-14",
        "three": "2-4",
        "reb": 5,
        "ast": 1,
        "efg": "64.3%",
        "pm": "+1",
        "takeaway": "6-7 at the rim/paint",
    },
    {
        "name": "Noa Essengue",
        "id": 1642855,
        "pts": 21,
        "min": 31,
        "fg": "7-14",
        "three": "3-8",
        "reb": 3,
        "ast": 1,
        "efg": "60.7%",
        "pm": "+3",
        "takeaway": "Three levels in the shot diet",
    },
    {
        "name": "Javon Freeman-Liberty",
        "id": 1631241,
        "pts": 18,
        "min": 28,
        "fg": "6-14",
        "three": "2-4",
        "reb": 8,
        "ast": 5,
        "efg": "50.0%",
        "pm": "+10",
        "takeaway": "8 rebounds and 5 assists",
    },
]


def fp(weight="regular"):
    return fm.FontProperties(fname=str(BODY[weight]))


def canvas(label: str, title: str, subtitle: str):
    fig = plt.figure(figsize=(W / DEFAULT_DPI, H / DEFAULT_DPI), facecolor="white")
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, W)
    ax.set_ylim(0, H)
    ax.axis("off")

    ax.text(60, H - 42, label.upper(), ha="left", va="top", fontsize=9, color=FAINT,
            fontproperties=fp("bold"))
    ax.text(60, H - 80, title, ha="left", va="top", fontsize=30, color=INK,
            fontproperties=fp("bold"))
    ax.text(60, H - 140, subtitle, ha="left", va="top", fontsize=14, color=MID,
            fontproperties=fp("medium"))
    ax.plot([60, 1020], [H - 178, H - 178], color=INK, lw=1.2)

    ax.text(60, 38, "WIREFRAME · STRUCTURE ONLY · JUL 14 SAMPLE DATA", ha="left", va="bottom",
            fontsize=8, color=FAINT, fontproperties=fp())
    ax.text(1020, 38, "@chicagobullsdata", ha="right", va="bottom", fontsize=9,
            color=MID, fontproperties=fp("medium"))
    return fig, ax


def headshot(player):
    return REPO / "cache" / "headshots" / f"{player['id']}.png"


def draw_row_board():
    fig, ax = canvas(
        "Direction A · repeated-row board",
        "Summer League Report",
        "Bulls 114 · Pacers 105 · Jul 14, 2025",
    )

    ax.text(60, 1134, "THREE PLAYER LINES FROM THE WIN", ha="left", va="top", fontsize=11,
            color=MID, fontproperties=fp("bold"))
    ax.text(1020, 1134, "PTS", ha="right", va="top", fontsize=11, color=MID,
            fontproperties=fp("bold"))

    y_tops = [1085, 800, 515]
    for player, top in zip(PLAYERS, y_tops):
        bottom = top - 245
        ax.plot([60, 1020], [bottom, bottom], color=RULE, lw=1)
        headshot_label(ax, headshot(player), 145, top - 118, radius=76)

        ax.text(255, top - 60, player["name"], ha="left", va="top", fontsize=26, color=INK,
                fontproperties=fp("bold"))
        ax.text(255, top - 105, player["takeaway"], ha="left", va="top", fontsize=14,
                color=MID, fontproperties=fp("medium"))
        detail = f"{player['min']} MIN   ·   {player['fg']} FG   ·   {player['three']} 3PT   ·   {player['reb']} REB   ·   {player['ast']} AST"
        ax.text(255, top - 153, detail, ha="left", va="top", fontsize=12.5, color=MID,
                fontproperties=fp("medium"))

        ax.add_patch(Rectangle((870, bottom + 1), 150, 244, facecolor=LIGHT, edgecolor="none"))
        ax.text(945, top - 96, str(player["pts"]), ha="center", va="center", fontsize=43,
                color=INK, fontproperties=fp("bold"))
        ax.text(945, top - 145, "POINTS", ha="center", va="center", fontsize=9.5,
                color=MID, fontproperties=fp("bold"))

    ax.text(60, 220, "WHY THIS STRUCTURE", ha="left", va="top", fontsize=10, color=MID,
            fontproperties=fp("bold"))
    ax.text(60, 187, "One repeated unit. Images identify. One metric gets the visual endpoint.",
            ha="left", va="top", fontsize=13, color=INK, fontproperties=fp("medium"))
    ax.text(60, 154, "Best when the post's job is fast scanning, not full game explanation.",
            ha="left", va="top", fontsize=13, color=MID, fontproperties=fp())
    return fig


def draw_comparison_table():
    fig, ax = canvas(
        "Direction B · players-as-columns",
        "Summer League Report",
        "A direct comparison of the three featured Bulls",
    )

    left, right = 60, 1020
    stub_w = 245
    col_w = (right - left - stub_w) / 3
    top = 1128
    header_h = 180

    ax.plot([left, right], [top - header_h, top - header_h], color=INK, lw=1.1)
    for i, player in enumerate(PLAYERS):
        cx = left + stub_w + col_w * (i + 0.5)
        headshot_label(ax, headshot(player), cx, top - 58, radius=48)
        ax.text(cx, top - 116, player["name"].replace("Javon ", "J. "), ha="center", va="top",
                fontsize=12.5, color=INK, fontproperties=fp("bold"))
        ax.text(cx, top - 145, player["takeaway"], ha="center", va="top", fontsize=8.5,
                color=MID, fontproperties=fp("medium"))

    rows = [
        ("Points", [p["pts"] for p in PLAYERS]),
        ("Minutes", [p["min"] for p in PLAYERS]),
        ("Field goals", [p["fg"] for p in PLAYERS]),
        ("Three-pointers", [p["three"] for p in PLAYERS]),
        ("Rebounds", [p["reb"] for p in PLAYERS]),
        ("Assists", [p["ast"] for p in PLAYERS]),
        ("Effective FG%", [p["efg"] for p in PLAYERS]),
        ("Plus/minus", [p["pm"] for p in PLAYERS]),
    ]
    row_h = 92
    for idx, (label, values) in enumerate(rows):
        y_top = top - header_h - idx * row_h
        if idx % 2:
            ax.add_patch(Rectangle((left, y_top - row_h), right - left, row_h,
                                   facecolor=LIGHTER, edgecolor="none"))
        if label == "Effective FG%":
            ax.add_patch(Rectangle((left, y_top - row_h), right - left, row_h,
                                   facecolor="#E7E7E7", edgecolor="none"))
        ax.text(left + 8, y_top - row_h / 2, label, ha="left", va="center", fontsize=14,
                color=INK, fontproperties=fp("bold" if label == "Effective FG%" else "medium"))
        for i, value in enumerate(values):
            cx = left + stub_w + col_w * (i + 0.5)
            ax.text(cx, y_top - row_h / 2, str(value), ha="center", va="center", fontsize=16,
                    color=INK, fontproperties=fp("bold" if label == "Effective FG%" else "medium"))

    ax.text(60, 170, "WHY THIS STRUCTURE", ha="left", va="top", fontsize=10, color=MID,
            fontproperties=fp("bold"))
    ax.text(60, 137, "The data shape does the design work: players become columns because",
            ha="left", va="top", fontsize=12.5, color=INK, fontproperties=fp("medium"))
    ax.text(60, 108, "direct comparison is the job of this slide.", ha="left", va="top",
            fontsize=12.5, color=MID, fontproperties=fp())
    return fig


def draw_half_court(ax, left, bottom, width, height):
    ax.add_patch(Rectangle((left, bottom), width, height, fill=False, edgecolor=RULE, lw=1.4))
    hoop_x = left + width / 2
    hoop_y = bottom + 60
    ax.add_patch(Circle((hoop_x, hoop_y), 10, fill=False, edgecolor=MID, lw=1.5))
    ax.add_patch(Rectangle((hoop_x - 86, bottom), 172, 210, fill=False, edgecolor=RULE, lw=1.4))
    ax.add_patch(Arc((hoop_x, hoop_y), width * 0.82, width * 0.82,
                     theta1=22, theta2=158, edgecolor=RULE, lw=1.4))
    ax.text(hoop_x, bottom + height / 2, "EXACT SHOT MAP\nFROM EXISTING DATA", ha="center",
            va="center", fontsize=11, color=FAINT, fontproperties=fp("bold"))


def draw_real_shot_chart(
    ax, shots, player_id, left, bottom, width, label_size=9, draw_legend=True
):
    """Draw real NBA locations with one FGA marker and fill=make/miss.

    NBA coordinates are tenths of a foot with the hoop at (0, 0). We keep that
    coordinate system and scale the court paths into the requested wireframe box.
    Every FGA is a circle. Solid markers are makes; hollow markers are misses.
    """
    player_shots = shots[shots["player_id"] == player_id]
    scale = width / 500
    top_y = 300

    def t(cx, cy):
        return left + (cx + 250) * scale, bottom + (cy + 47.5) * scale

    court = dict(color=COURT, lw=1.15)
    ax.plot([t(-250, -47.5)[0], t(250, -47.5)[0]], [bottom, bottom], **court)
    for side in (-250, 250):
        ax.plot([t(side, -47.5)[0]] * 2, [bottom, t(side, top_y)[1]], **court)
    ax.add_patch(Rectangle(t(-80, -47.5), 160 * scale, 190 * scale,
                           fill=False, edgecolor=COURT, lw=1.15))
    hoop_x, hoop_y = t(0, 0)
    ax.add_patch(Circle((hoop_x, hoop_y), 7.5 * scale * 2,
                        fill=False, edgecolor=MID, lw=1.2))
    ax.plot([t(-30, -7.5)[0], t(30, -7.5)[0]], [t(0, -7.5)[1]] * 2,
            color=COURT, lw=1.15)
    corner_top = (237.5**2 - 220**2) ** 0.5
    for side in (-220, 220):
        ax.plot([t(side, -47.5)[0]] * 2,
                [t(side, -47.5)[1], t(side, corner_top)[1]], **court)
    ax.add_patch(Arc((hoop_x, hoop_y), 475 * scale, 475 * scale,
                     theta1=22.1, theta2=157.9, edgecolor=COURT, lw=1.15))

    marker_size = max(6.5, 7.2 * scale)
    for _, shot in player_shots.iterrows():
        x, y = t(float(shot["loc_x"]), min(float(shot["loc_y"]), top_y))
        ax.plot(
            x,
            y,
            marker="o",
            ms=marker_size,
            mfc=INK if bool(shot["shot_made"]) else "white",
            mec=INK,
            mew=1.1,
            linestyle="none",
            zorder=5,
        )

    if draw_legend:
        legend_y = bottom - 28
        ax.plot(left, legend_y, marker="o", ms=7, mfc=INK, mec=INK,
                linestyle="none")
        ax.text(left + 14, legend_y, "MAKE", ha="left", va="center", fontsize=label_size,
                color=MID, fontproperties=fp("bold"))
        ax.plot(left + 92, legend_y, marker="o", ms=7, mfc="white", mec=INK,
                mew=1.2, linestyle="none")
        ax.text(left + 106, legend_y, "MISS", ha="left", va="center", fontsize=label_size,
                color=MID, fontproperties=fp("bold"))


def draw_player_story_with_shots(shots):
    """Direction C2: the editorial slide with exact shot locations."""
    player = PLAYERS[0]
    fig, ax = canvas(
        "Direction C2 · editorial story + real FGA",
        "Matas Buzelis · 28 Points",
        "Jul 14, 2025 · Bulls 114, Pacers 105",
    )
    headshot_label(ax, headshot(player), 132, 1060, radius=64)
    ax.text(225, 1100, "PRIMARY TAKEAWAY", ha="left", va="top", fontsize=10,
            color=MID, fontproperties=fp("bold"))
    ax.text(225, 1062, "6–7 AT THE RIM / PAINT", ha="left", va="top", fontsize=30,
            color=INK, fontproperties=fp("bold"))
    ax.text(225, 970, "The court is the evidence layer; the stat line stays supporting.",
            ha="left", va="top", fontsize=12, color=FAINT, fontproperties=fp("medium"))

    ax.add_patch(Rectangle((60, 322), 650, 615, facecolor=PANEL,
                           edgecolor=RULE, lw=1))
    ax.text(86, 905, "ALL 14 FIELD-GOAL ATTEMPTS", ha="left", va="top", fontsize=10,
            color=MID, fontproperties=fp("bold"))
    draw_real_shot_chart(ax, shots, player["id"], 86, 430, 598)

    ax.text(760, 910, "SHOT PROFILE", ha="left", va="top", fontsize=10, color=MID,
            fontproperties=fp("bold"))
    support = [
        ("8–14", "FIELD GOALS"),
        ("6–7", "RIM / PAINT"),
        ("64.3%", "EFFECTIVE FG"),
        ("10–13", "FREE THROWS"),
    ]
    for index, (value, label) in enumerate(support):
        y = 845 - index * 122
        ax.text(760, y, value, ha="left", va="top", fontsize=31, color=INK,
                fontproperties=fp("bold"))
        ax.text(760, y - 58, label, ha="left", va="top", fontsize=9.5, color=MID,
                fontproperties=fp("bold"))
        ax.plot([760, 1020], [y - 84, y - 84], color=RULE, lw=1)

    ax.text(60, 236, "WHY THIS STRUCTURE", ha="left", va="top", fontsize=10,
            color=MID, fontproperties=fp("bold"))
    ax.text(60, 202, "The shot chart answers where. The side rail answers how much.",
            ha="left", va="top", fontsize=13, color=INK, fontproperties=fp("medium"))
    ax.text(60, 168, "Every mark is an FGA. Solid is make; hollow is miss.",
            ha="left", va="top", fontsize=13, color=MID, fontproperties=fp())
    return fig


def draw_shot_profile_small_multiples(shots):
    """Direction D: one shared court grammar repeated for three players."""
    fig, ax = canvas(
        "Direction D · shot-profile small multiples",
        "Three Bulls · Three Shot Profiles",
        "Bulls 114 · Pacers 105 · Jul 14, 2025",
    )
    ax.text(60, 1132, "Every court uses the same scale and encoding.", ha="left", va="top",
            fontsize=12, color=MID, fontproperties=fp("medium"))
    ax.plot(842, 1128, marker="o", ms=7, mfc=INK, mec=INK, linestyle="none")
    ax.text(857, 1128, "MAKE", ha="left", va="center", fontsize=8.5, color=MID,
            fontproperties=fp("bold"))
    ax.plot(930, 1128, marker="o", ms=7, mfc="white", mec=INK, mew=1.2,
            linestyle="none")
    ax.text(945, 1128, "MISS", ha="left", va="center", fontsize=8.5, color=MID,
            fontproperties=fp("bold"))

    row_tops = [1080, 785, 490]
    for player, top in zip(PLAYERS, row_tops):
        headshot_label(ax, headshot(player), 118, top - 78, radius=50)
        ax.text(190, top - 36, player["name"], ha="left", va="top", fontsize=20,
                color=INK, fontproperties=fp("bold"))
        player_shots = shots[shots["player_id"] == player["id"]]
        makes = int(player_shots["shot_made"].sum())
        ax.text(190, top - 76, f"{makes}-{len(player_shots)} FG · {player['efg']} eFG",
                ha="left", va="top", fontsize=12, color=MID, fontproperties=fp("bold"))
        ax.text(190, top - 112, player["takeaway"], ha="left", va="top", fontsize=11.5,
                color=FAINT, fontproperties=fp("medium"))
        draw_real_shot_chart(
            ax, shots, player["id"], 560, top - 220, 420, label_size=8, draw_legend=False
        )
        ax.plot([60, 1020], [top - 260, top - 260], color=RULE, lw=1)

    ax.text(60, 174, "WHY THIS STRUCTURE", ha="left", va="top", fontsize=10,
            color=MID, fontproperties=fp("bold"))
    ax.text(60, 140, "Shared scales make location patterns comparable without turning the",
            ha="left", va="top", fontsize=12.5, color=INK, fontproperties=fp("medium"))
    ax.text(60, 110, "cover into a dashboard.", ha="left", va="top", fontsize=12.5,
            color=MID, fontproperties=fp())
    return fig


def draw_player_story():
    player = PLAYERS[0]
    fig, ax = canvas(
        "Direction C · one editorial player story",
        "Matas Owned the Paint",
        "Jul 14, 2025 · Bulls 114, Pacers 105",
    )

    headshot_label(ax, headshot(player), 145, 1055, radius=78)
    ax.text(255, 1110, "MATAS BUZELIS", ha="left", va="top", fontsize=24, color=INK,
            fontproperties=fp("bold"))
    ax.text(255, 1065, "28 POINTS", ha="left", va="top", fontsize=15, color=MID,
            fontproperties=fp("bold"))
    ax.text(255, 1010, "6–7", ha="left", va="top", fontsize=60, color=INK,
            fontproperties=fp("bold"))
    ax.text(415, 986, "AT THE RIM / PAINT", ha="left", va="top", fontsize=15, color=MID,
            fontproperties=fp("bold"))
    ax.text(255, 918, "This is the slide's thesis—not another equal-weight stat card.", ha="left",
            va="top", fontsize=11, color=FAINT, fontproperties=fp("medium"))

    draw_half_court(ax, 60, 310, 610, 550)

    ax.text(730, 850, "SUPPORTING EVIDENCE", ha="left", va="top", fontsize=9.5, color=MID,
            fontproperties=fp("bold"))
    evidence = [
        ("10–13", "FREE THROWS"),
        ("2–4", "THREES"),
        ("64.3%", "EFFECTIVE FG"),
    ]
    for i, (value, label) in enumerate(evidence):
        y = 790 - i * 145
        ax.text(730, y, value, ha="left", va="top", fontsize=34, color=INK,
                fontproperties=fp("bold"))
        ax.text(730, y - 48, label, ha="left", va="top", fontsize=10, color=MID,
                fontproperties=fp("bold"))
        ax.plot([730, 1020], [y - 80, y - 80], color=RULE, lw=1)

    ax.text(60, 228, "WHY THIS STRUCTURE", ha="left", va="top", fontsize=10, color=MID,
            fontproperties=fp("bold"))
    ax.text(60, 195, "One claim owns the page. The court proves it; three numbers support it.",
            ha="left", va="top", fontsize=13, color=INK, fontproperties=fp("medium"))
    ax.text(60, 160, "Best when the carousel should feel like analysis rather than a game dashboard.",
            ha="left", va="top", fontsize=13, color=MID, fontproperties=fp())
    return fig


def main():
    shots = get_game_shots(GAME_ID)
    if len(shots) != 74 or int(shots["shot_made"].sum()) != 37:
        raise RuntimeError(
            f"Expected rehearsal-game reconciliation of 37 makes on 74 FGA; "
            f"received {int(shots['shot_made'].sum())} on {len(shots)}."
        )
    outputs = [
        ("2025-07-14-summer-league-wireframe-a-row-board.png", draw_row_board),
        ("2025-07-14-summer-league-wireframe-b-comparison.png", draw_comparison_table),
        ("2025-07-14-summer-league-wireframe-c-player-story.png", draw_player_story),
    ]
    for name, builder in outputs:
        fig = builder()
        save_feed_post(fig, OUT / name, dpi=DEFAULT_DPI)
        plt.close(fig)
        print(f"Saved {OUT / name}")
    shot_outputs = [
        ("2025-07-14-summer-league-wireframe-c2-real-shot-chart.png", draw_player_story_with_shots),
        ("2025-07-14-summer-league-wireframe-d-shot-small-multiples.png", draw_shot_profile_small_multiples),
    ]
    for name, builder in shot_outputs:
        fig = builder(shots)
        save_feed_post(fig, OUT / name, dpi=DEFAULT_DPI)
        plt.close(fig)
        print(f"Saved {OUT / name}")


if __name__ == "__main__":
    main()
