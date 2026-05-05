#!/usr/bin/env python3
"""
One-shot cleanup for misdated FINAL rows in the games tables.

Background: collect_mlb_scores in main.py used the iteration's check_date
(an ET date) to look up rows for ESPN events whose timestamps ESPN classifies
by UTC date. Late-night ET games landed on the next UTC date in ESPN's filter,
which led to today's upcoming rows being overwritten with last night's
results. The collector is fixed forward; this script unfixes any rows that
already got corrupted.

Logic: any row with game_status='final' whose game_time is still in the
future has not actually finished and is corrupted. Clear the score and status
fields so the next collector run can repopulate correctly.

Run:
  python3 scripts/cleanup_misdated_finals.py            # dry-run, prints what would change
  python3 scripts/cleanup_misdated_finals.py --apply    # apply the cleanup

Safe to run on production. Operates on SQLite games tables only (mlb_games,
games, wnba_games). Picks/Users tables in Postgres are untouched.
"""

import argparse
import os
import sqlite3
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db_path import get_sqlite_path


TABLES = ['mlb_games', 'games', 'wnba_games']


def find_corrupted(cursor, table, now_utc_iso):
    cursor.execute(
        f"""SELECT id, game_date, game_time, home_team, away_team,
                   home_score, away_score, game_status
            FROM {table}
            WHERE game_status = 'final'
              AND game_time IS NOT NULL
              AND game_time > ?
            ORDER BY game_date""",
        (now_utc_iso,),
    )
    return cursor.fetchall()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--apply',
        action='store_true',
        help='Apply the cleanup. Default is dry-run.',
    )
    args = parser.parse_args()

    now_utc_iso = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    db_path = get_sqlite_path()
    print(f"Reference time (UTC): {now_utc_iso}")
    print(f"Database:             {db_path}")
    print(f"Mode:                 {'APPLY' if args.apply else 'DRY-RUN'}")
    print()

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    total = 0
    for table in TABLES:
        try:
            rows = find_corrupted(cursor, table, now_utc_iso)
        except sqlite3.OperationalError as e:
            print(f"[{table}] skipped: {e}")
            continue

        if not rows:
            print(f"[{table}] no corrupted rows")
            continue

        print(f"[{table}] {len(rows)} corrupted row(s):")
        for r in rows:
            rid, gdate, gtime, home, away, hs, as_, status = r
            print(f"  id={rid}  game_date={gdate}  game_time={gtime}  {away} @ {home}  score={hs}-{as_}  status={status}")
        total += len(rows)

        if args.apply:
            cursor.execute(
                f"""UPDATE {table}
                    SET home_score = NULL,
                        away_score = NULL,
                        spread_result = NULL,
                        game_status = NULL,
                        scores_updated_at = NULL
                    WHERE game_status = 'final'
                      AND game_time IS NOT NULL
                      AND game_time > ?""",
                (now_utc_iso,),
            )

    if args.apply:
        conn.commit()
        print(f"\nApplied. Cleared {total} row(s) total.")
    else:
        print(f"\nDry-run. Would clear {total} row(s). Re-run with --apply to commit.")

    conn.close()


if __name__ == '__main__':
    main()
