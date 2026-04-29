"""
DIAGNOSTIC TOOL — NOT PRODUCTION CODE.

Reports the % of completed `mlb_games` rows in the last 30 days that have
real (non-null, non-default) values for the four ESPN-sourced pitcher fields
WHIP and IP (home & away). Used to validate Phase 2C of the model feature
pipeline restoration: the ESPN pitcher parser fix that captures WHIP/IP from
the nested `athlete.statistics` path.

Defaults that count as "missing":
  WHIP -> 1.30 (league average used as fallback in feature engineering)
  IP   -> 0    (sentinel)

ERA is reported for reference (it was already ~100% pre-fix).

Usage:
  python3 scripts/check_pitcher_coverage.py [--days 30] [--db PATH] [--last-completed]

  --last-completed   anchor the 30-day window on the most recent completed
                     game in the DB instead of `date('now')`. Useful on dev
                     DBs that lag prod by weeks/months.

The actual coverage computation lives in `services.pitcher_coverage` and is
shared with the `/api/admin/diagnose-pitcher-coverage` admin endpoint so the
script and the endpoint cannot drift.
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from services.pitcher_coverage import compute_coverage  # noqa: E402


def _pct_str(p):
    return f"{p:.1f}%" if p is not None else "n/a"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--days", type=int, default=30, help="window size in days (default 30)")
    parser.add_argument("--db", type=str, default=None, help="explicit sqlite path")
    parser.add_argument(
        "--last-completed",
        action="store_true",
        help="anchor window on most recent completed game instead of today",
    )
    args = parser.parse_args()

    result = compute_coverage(
        days=args.days,
        last_completed=args.last_completed,
        db_path=args.db,
    )

    print(f"DB:       {result['db_path']}")
    if result.get("anchor_mode") == "last_completed":
        anchor = result.get("window_end") or "n/a"
        window_label = f"{result['days']} days ending {anchor} (last completed game in DB)"
    else:
        window_label = f"last {result['days']} days (today-anchored)"
    print(f"Window:   {window_label}")

    n = result["total_games_in_window"]
    print(f"Games:    {n}")
    if not n:
        print("No completed games in window. Cannot compute coverage.")
        return 1 if result.get("error") == "no_completed_games" else 0

    cov = result["coverage"]
    print()
    print("Real (non-default) coverage:")
    for field in ("home_pitcher_whip", "away_pitcher_whip", "home_pitcher_ip", "away_pitcher_ip"):
        c = cov[field]
        print(f"  {field:<20} {c['count']:>5}/{n}  {_pct_str(c['pct'])}")

    era = result["era_reference"]
    print()
    print("Reference (ERA non-null, no league-default check):")
    for field in ("home_pitcher_era", "away_pitcher_era"):
        c = era[field]
        print(f"  {field:<20} {c['count']:>5}/{n}  {_pct_str(c['pct'])}")

    agg = result["aggregate"]
    print()
    print(f"Aggregate WHIP coverage: {agg['whip_avg_pct']:.1f}%")
    print(f"Aggregate IP   coverage: {agg['ip_avg_pct']:.1f}%")
    print(f"Min field coverage:      {agg['min_field_pct']:.1f}%")
    print(f"Recommendation:          {result['recommendation']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
