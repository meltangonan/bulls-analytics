"""Isolated Great Tables feasibility spike for the Summer League report.

This deliberately uses the same semantic-table workflow as the three F5
tutorials: shape the data, hide implementation columns, format images and
numbers, emphasize one verdict column, then make small finishing adjustments.

The dependency is intentionally not added to requirements.txt yet. This spike
exists to decide whether the output earns a project-level dependency change.
"""

import base64
from pathlib import Path

import pandas as pd
from great_tables import GT, md
import gt_extras as gte


REPO = Path(__file__).resolve().parents[2]
OUT = REPO / "output" / "feed"
HEADSHOTS = REPO / "cache" / "headshots"


def build_table() -> GT:
    rows = pd.DataFrame(
        [
            {
                "headshot": "1641824.png",
                "player": "Matas Buzelis",
                "min": 31,
                "pts": 28,
                "fg": "8-14",
                "three": "2-4",
                "reb": 5,
                "ast": 1,
                "efg": 64.3,
                "plus_minus": 1,
            },
            {
                "headshot": "1642855.png",
                "player": "Noa Essengue",
                "min": 31,
                "pts": 21,
                "fg": "7-14",
                "three": "3-8",
                "reb": 3,
                "ast": 1,
                "efg": 60.7,
                "plus_minus": 3,
            },
            {
                "headshot": "1631241.png",
                "player": "Javon Freeman-Liberty",
                "min": 28,
                "pts": 18,
                "fg": "6-14",
                "three": "2-4",
                "reb": 8,
                "ast": 5,
                "efg": 50.0,
                "plus_minus": 10,
            },
        ]
    )
    return (
        GT(rows)
        .tab_header(
            title=md("**Summer League Report**"),
            subtitle="Bulls 114, Pacers 105 · Jul 14, 2025",
        )
        .cols_label(
            headshot="",
            player="PLAYER",
            min="MIN",
            pts="PTS",
            fg="FG",
            three="3PT",
            reb="REB",
            ast="AST",
            efg="eFG%",
            plus_minus="+/-",
        )
        .fmt_image(columns="headshot", path=HEADSHOTS, height=52)
        .fmt_number(columns="efg", decimals=1, pattern="{x}%")
        .fmt_number(columns="plus_minus", decimals=0, force_sign=True)
        .data_color(
            columns="efg",
            domain=[45, 70],
            palette=["#F4F4F4", "#D8D8D8", "#777777"],
            autocolor_text=True,
        )
        .cols_align("left", columns="player")
        .cols_align("center", columns=["headshot", "min", "pts", "fg", "three", "reb", "ast", "efg", "plus_minus"])
        .opt_row_striping(row_striping=True)
        .tab_options(
            container_width="100%",
            table_background_color="white",
            table_font_names="Arial",
            table_font_size="17px",
            heading_title_font_size="30px",
            heading_subtitle_font_size="16px",
            column_labels_font_size="13px",
            column_labels_font_weight="bold",
            data_row_padding="8px",
            table_body_hlines_color="transparent",
            column_labels_border_top_color="#222222",
            column_labels_border_top_width="1px",
            column_labels_border_bottom_color="#D8D8D8",
            heading_border_bottom_style="none",
            table_body_border_bottom_color="#D8D8D8",
            table_border_top_style="none",
            table_border_bottom_style="none",
            source_notes_border_lr_style="none",
        )
        .opt_align_table_header(align="left")
    )


def image_data_url(path: Path) -> str:
    payload = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:image/png;base64,{payload}"


def build_player_columns_table() -> GT:
    """Transpose the same data so comparison dictates the layout."""
    rows = pd.DataFrame(
        {
            "stat": ["Points", "Minutes", "Field goals", "Three-pointers", "Rebounds", "Assists", "Effective FG%", "Plus/minus"],
            "Matas Buzelis": [28, 31, "8-14", "2-4", 5, 1, "64.3%", "+1"],
            "Noa Essengue": [21, 31, "7-14", "3-8", 3, 1, "60.7%", "+3"],
            "Javon Freeman-Liberty": [18, 28, "6-14", "2-4", 8, 5, "50.0%", "+10"],
        }
    )
    headers = {
        "Matas Buzelis": gte.img_header(
            label="Matas Buzelis",
            img_url=image_data_url(HEADSHOTS / "1641824.png"),
            height=70,
            font_size=14,
        ),
        "Noa Essengue": gte.img_header(
            label="Noa Essengue",
            img_url=image_data_url(HEADSHOTS / "1642855.png"),
            height=70,
            font_size=14,
        ),
        "Javon Freeman-Liberty": gte.img_header(
            label="J. Freeman-Liberty",
            img_url=image_data_url(HEADSHOTS / "1631241.png"),
            height=70,
            font_size=14,
        ),
    }
    return (
        GT(rows)
        .tab_header(
            title=md("**Summer League Report**"),
            subtitle="A direct comparison of the three featured Bulls",
        )
        .cols_label(stat="", **headers)
        .cols_align("left", columns="stat")
        .cols_align("center", columns=list(headers))
        .opt_row_striping(row_striping=True)
        .tab_options(
            container_width="100%",
            table_background_color="white",
            table_font_names="Arial",
            table_font_size="17px",
            heading_title_font_size="30px",
            heading_subtitle_font_size="16px",
            column_labels_font_weight="bold",
            data_row_padding="8px",
            table_body_hlines_color="transparent",
            column_labels_border_top_color="#222222",
            column_labels_border_top_width="1px",
            column_labels_border_bottom_color="#D8D8D8",
            heading_border_bottom_style="none",
            table_body_border_bottom_color="#D8D8D8",
            table_border_top_style="none",
            table_border_bottom_style="none",
            source_notes_border_lr_style="none",
        )
        .opt_align_table_header(align="left")
    )

def main():
    outputs = [
        ("2025-07-14-summer-league-great-tables-spike.png", build_table),
        ("2025-07-14-summer-league-gt-extras-columns-spike.png", build_player_columns_table),
    ]
    OUT.mkdir(parents=True, exist_ok=True)
    for name, builder in outputs:
        output = OUT / name
        builder().gtsave(output, zoom=2, expand=20)
        print(f"Saved {output}")


if __name__ == "__main__":
    main()
