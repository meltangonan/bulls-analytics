#!/usr/bin/env python3
"""Generate zone leaders graphics with player headshots."""

from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from bulls import data, graphics
from bulls.config import CURRENT_SEASON


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate zone leaders graphic")
    parser.add_argument(
        "--season", default=CURRENT_SEASON,
        help="NBA season string (default: current season)",
    )
    parser.add_argument(
        "--last-n-games", type=int, default=None,
        help="Limit to last N games (omit for full season)",
    )
    parser.add_argument(
        "--min-shots", type=int, default=None,
        help="Minimum shots per zone to qualify (default: 30 season, 10 last-N)",
    )
    parser.add_argument(
        "--mode", choices=["ppg", "frequency"], default="ppg",
        help="Leader metric: ppg (points per game) or frequency (shot attempts per game)",
    )
    parser.add_argument(
        "--output", default="",
        help="Output PNG path",
    )
    return parser.parse_args()


def default_output(mode: str, last_n: int | None) -> str:
    stamp = datetime.now().strftime("%Y-%m-%d")
    suffix = f"last-{last_n}" if last_n else "season"
    return str(Path("output/feed") / f"{stamp}-zone-{mode}-{suffix}.png")


def _format_date() -> str:
    """Human-readable date for the graphic subtitle."""
    return datetime.now().strftime("%B %-d, %Y")


def main() -> None:
    args = parse_args()
    output_path = args.output or default_output(args.mode, args.last_n_games)

    # Scale min_shots to the timeframe
    if args.min_shots is not None:
        min_shots = args.min_shots
    elif args.last_n_games:
        min_shots = 10
    else:
        min_shots = 30

    print(f"Fetching team shots (last_n_games={args.last_n_games})...")
    shots = data.get_team_shots(season=args.season, last_n_games=args.last_n_games)
    print(f"  -> {len(shots)} shots loaded (min_shots={min_shots})")

    date_str = _format_date()
    if args.last_n_games:
        subtitle = f"Chicago Bulls | Last {args.last_n_games} Games | {date_str}"
    else:
        subtitle = f"Chicago Bulls | {args.season} Season | {date_str}"

    if args.mode == "frequency":
        fig = graphics.build_zone_frequency_post(
            shots,
            title="Shot Frequency By Zone",
            subtitle=subtitle,
            min_shots=min_shots,
        )
    else:
        fig = graphics.build_zone_leaders_post(
            shots,
            title="Leading Scorers By Zone",
            subtitle=subtitle,
            min_shots=min_shots,
        )

    saved = graphics.save_feed_post(fig, output_path)
    print(f"Saved: {saved}")


if __name__ == "__main__":
    main()
