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
"""

import argparse
import sqlite3
import sys

try:
    from db_path import get_sqlite_path  # type: ignore
except Exception:  # pragma: no cover - script is best-effort
    def get_sqlite_path() -> str:
        return "sharp_picks.db"


WHIP_DEFAULT = 1.30
IP_DEFAULT = 0


def pct(n: int, d: int) -> str:
    return f"{(100.0 * n / d):.1f}%" if d else "n/a"


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

    db_path = args.db or get_sqlite_path()
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    if args.last_completed:
        cur.execute("SELECT MAX(game_date) FROM mlb_games WHERE home_score IS NOT NULL")
        anchor = cur.fetchone()[0]
        if not anchor:
            print(f"No completed games in {db_path}", file=sys.stderr)
            return 1
        anchor_clause = "date(?, '-{} days')".format(args.days)
        params = (anchor,)
        window_label = f"{args.days} days ending {anchor} (last completed game in DB)"
    else:
        anchor_clause = "date('now', '-{} days')".format(args.days)
        params = ()
        window_label = f"last {args.days} days (today-anchored)"

    sql = f"""
        SELECT
          COUNT(*)                                                                    AS n,
          SUM(CASE WHEN home_pitcher_whip IS NOT NULL AND home_pitcher_whip != ?
                   THEN 1 ELSE 0 END)                                                  AS h_whip,
          SUM(CASE WHEN away_pitcher_whip IS NOT NULL AND away_pitcher_whip != ?
                   THEN 1 ELSE 0 END)                                                  AS a_whip,
          SUM(CASE WHEN home_pitcher_ip   IS NOT NULL AND home_pitcher_ip   != ?
                   THEN 1 ELSE 0 END)                                                  AS h_ip,
          SUM(CASE WHEN away_pitcher_ip   IS NOT NULL AND away_pitcher_ip   != ?
                   THEN 1 ELSE 0 END)                                                  AS a_ip,
          SUM(CASE WHEN home_pitcher_era  IS NOT NULL THEN 1 ELSE 0 END)               AS h_era,
          SUM(CASE WHEN away_pitcher_era  IS NOT NULL THEN 1 ELSE 0 END)               AS a_era
        FROM mlb_games
        WHERE home_score IS NOT NULL
          AND game_date >= {anchor_clause}
    """
    cur.execute(sql, (WHIP_DEFAULT, WHIP_DEFAULT, IP_DEFAULT, IP_DEFAULT, *params))
    n, h_whip, a_whip, h_ip, a_ip, h_era, a_era = cur.fetchone()

    print(f"DB:       {db_path}")
    print(f"Window:   {window_label}")
    print(f"Games:    {n}")
    if not n:
        print("No completed games in window. Cannot compute coverage.")
        return 0
    print()
    print("Real (non-default) coverage:")
    print(f"  home_pitcher_whip   {h_whip:>5}/{n}  {pct(h_whip, n)}")
    print(f"  away_pitcher_whip   {a_whip:>5}/{n}  {pct(a_whip, n)}")
    print(f"  home_pitcher_ip     {h_ip:>5}/{n}  {pct(h_ip, n)}")
    print(f"  away_pitcher_ip     {a_ip:>5}/{n}  {pct(a_ip, n)}")
    print()
    print("Reference (ERA non-null, no league-default check):")
    print(f"  home_pitcher_era    {h_era:>5}/{n}  {pct(h_era, n)}")
    print(f"  away_pitcher_era    {a_era:>5}/{n}  {pct(a_era, n)}")

    avg_whip = (h_whip + a_whip) / (2 * n)
    avg_ip = (h_ip + a_ip) / (2 * n)
    print()
    print(f"Aggregate WHIP coverage: {avg_whip*100:.1f}%")
    print(f"Aggregate IP   coverage: {avg_ip*100:.1f}%")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
