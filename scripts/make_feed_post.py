#!/usr/bin/env python3
"""Generate single-image Bulls feed posts."""

from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path
import sys

# Allow running as a plain script from repo root.
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from bulls import data, graphics
from bulls.config import CURRENT_SEASON


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate a single-image Bulls feed post")
    parser.add_argument(
        "--post-type",
        choices=["zone-pps"],
        default="zone-pps",
        help="Post type to generate",
    )
    parser.add_argument(
        "--season",
        default=CURRENT_SEASON,
        help="NBA season string (default: current season from config)",
    )
    parser.add_argument(
        "--last-n-games",
        type=int,
        default=None,
        help="Optional game window for shot data",
    )
    parser.add_argument(
        "--min-shots",
        type=int,
        default=20,
        help="Minimum shots per zone to include in chart",
    )
    parser.add_argument(
        "--output",
        default="",
        help="Output PNG path (default: output/feed/<date>-zone-pps.png)",
    )
    return parser.parse_args()


def default_output(post_type: str) -> str:
    stamp = datetime.now().strftime("%Y-%m-%d")
    return str(Path("output/feed") / f"{stamp}-{post_type}.png")


def main() -> None:
    args = parse_args()
    output_path = args.output or default_output(args.post_type)

    if args.post_type == "zone-pps":
        shots = data.get_team_shots(season=args.season, last_n_games=args.last_n_games)
        title = "Bulls Shot Value by Zone"
        subtitle = (
            f"{args.season} Regular Season"
            if args.last_n_games is None
            else f"Last {args.last_n_games} Games"
        )
        fig = graphics.build_zone_pps_post(
            shots,
            title=title,
            subtitle=subtitle,
            min_shots=args.min_shots,
        )
    else:
        raise ValueError(f"Unsupported post type: {args.post_type}")

    saved = graphics.save_feed_post(fig, output_path)
    print(f"Saved post image: {saved}")


if __name__ == "__main__":
    main()
