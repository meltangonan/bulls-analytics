#!/usr/bin/env python3
"""One-command check that live NBA Stats access works from this machine.

    venv/bin/python scripts/check_nba_api.py

NBA.com's Akamai edge blocks datacenter/cloud IPs, so on Cursor Cloud (and any
blocked network) this needs the ``NBA_STATS_PROXY`` secret pointed at a
non-blocked proxy. See DEVELOPMENT.md > Network access. Exit code is 0 when the
API is reachable, 1 otherwise, so it doubles as a CI/precondition gate.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from bulls.data import fetch


def main() -> int:
    result = fetch.verify_api_access()
    print("NBA_STATS_PROXY:", "configured" if result["proxy_configured"] else "not set")
    if result["ok"]:
        print(f"OK - {result['detail']} ({result['rows']} roster rows)")
        return 0

    print(f"FAIL - {result['detail']}")
    if not result["proxy_configured"]:
        print(
            "Hint: this IP is likely blocked by NBA.com. Add the NBA_STATS_PROXY "
            "secret (a residential/mobile proxy URL like "
            "http://user:pass@host:port) and re-run."
        )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
