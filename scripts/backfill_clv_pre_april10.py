#!/usr/bin/env python3
"""
ONE-OFF BACKFILL — historical CLV residue from before commit 84f877c
(2026-04-10), which replaced the broken `clv = closing - pick.line`
formula with the current substring-detector branched form.

Picks resolved before 2026-04-10 carry CLV values computed with the
old formula. This script recomputes them using utils/clv (the cleaner
exact-match resolver introduced after the audit) and updates rows
whose recomputed value differs from what's stored.

CONVENTION (unchanged in this script):
  - pick.line is picked-side perspective.
  - pick.closing_spread is HOME perspective in DB (TODO: future PR
    normalizes at write time).
  - This script reads closing_spread, converts to picked-side via
    utils.clv.to_picked_perspective, then computes
    clv_points(line, closing_picked).

Filter: game_date < '2026-04-10' AND result IS NOT NULL.

Skip rules:
  - resolve_pick_side returns None (malformed side string, mid-season
    rename, abbreviated form, etc.) -> log for manual review.
  - closing_spread is NULL (close never captured) -> skip.
  - pick.line is NULL (moneyline pick, no spread to compare) -> skip.

Usage:
  Dry-run (default):
    DATABASE_URL=postgresql://... python3 scripts/backfill_clv_pre_april10.py

  Apply (writes to DB):
    DATABASE_URL=postgresql://... python3 scripts/backfill_clv_pre_april10.py --apply

Per-row entries are written to BOTH stdout AND
scripts/backfill_log_<timestamp>.txt.
"""
import os
import sys
import argparse
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.clv import resolve_pick_side, to_picked_perspective, clv_points


CUTOFF_DATE = '2026-04-10'

QUERY = """
SELECT id, sport, game_date, side, home_team, away_team,
       line, closing_spread, clv, result
FROM picks
WHERE game_date < :cutoff
  AND result IS NOT NULL
ORDER BY game_date ASC, id ASC
"""


class _PickShim:
    """Lightweight stand-in for a Pick row so utils.clv.resolve_pick_side
    (which uses getattr) can read fields off a SQLAlchemy Row."""
    __slots__ = ('id', 'side', 'home_team', 'away_team', 'line', 'closing_spread')

    def __init__(self, row):
        m = row._mapping
        self.id = m['id']
        self.side = m['side']
        self.home_team = m['home_team']
        self.away_team = m['away_team']
        self.line = m['line']
        self.closing_spread = m['closing_spread']


def _values_equal(a, b):
    """Treat None, and floats within 1e-9, as equal. Avoids spurious
    UPDATEs from float roundtrip noise."""
    if a is None and b is None:
        return True
    if a is None or b is None:
        return False
    return abs(float(a) - float(b)) < 1e-9


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--apply', action='store_true',
                        help='Actually write changes. Default is dry-run.')
    args = parser.parse_args()

    raw = (
        os.environ.get("SQLALCHEMY_DATABASE_URI")
        or os.environ.get("DATABASE_URL")
        or os.environ.get("DATABASE_PRIVATE_URL")
        or ""
    )
    if not raw:
        print("ERROR: No DATABASE_URL found.", file=sys.stderr)
        sys.exit(1)
    if raw.startswith("postgres://"):
        raw = "postgresql://" + raw[len("postgres://"):]

    timestamp = datetime.utcnow().strftime('%Y-%m-%dT%H-%M-%SZ')
    log_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        f'backfill_log_{timestamp}.txt',
    )

    mode = 'APPLY' if args.apply else 'DRY-RUN'
    header = (
        f"CLV backfill — pre-{CUTOFF_DATE} historical residue\n"
        f"Mode: {mode}\n"
        f"Started: {datetime.utcnow().isoformat()}Z\n"
        f"Log: {log_path}\n"
        f"---\n"
    )
    print(header, end='')

    counts = {
        'examined': 0,
        'updated': 0,
        'no_change': 0,
        'skipped_side_unresolved': 0,
        'skipped_null_closing': 0,
        'skipped_null_line': 0,
        'errors': 0,
    }

    from sqlalchemy import create_engine, text

    engine = create_engine(raw)
    with open(log_path, 'w') as logf:
        logf.write(header)

        with engine.begin() as conn:
            rows = conn.execute(text(QUERY), {'cutoff': CUTOFF_DATE}).fetchall()
            counts['examined'] = len(rows)

            for row in rows:
                m = row._mapping
                pick = _PickShim(row)
                clv_before = m['clv']

                if m['line'] is None:
                    counts['skipped_null_line'] += 1
                    line_msg = (
                        f"SKIP (null line) id={pick.id} side={pick.side!r} "
                        f"sport={m['sport']} date={m['game_date']}"
                    )
                    print(line_msg)
                    logf.write(line_msg + '\n')
                    continue

                if m['closing_spread'] is None:
                    counts['skipped_null_closing'] += 1
                    line_msg = (
                        f"SKIP (null closing) id={pick.id} side={pick.side!r} "
                        f"line={m['line']} clv_before={clv_before}"
                    )
                    print(line_msg)
                    logf.write(line_msg + '\n')
                    continue

                side = resolve_pick_side(pick)
                if side is None:
                    counts['skipped_side_unresolved'] += 1
                    line_msg = (
                        f"SKIP (side unresolved) id={pick.id} "
                        f"side={pick.side!r} home={pick.home_team!r} "
                        f"away={pick.away_team!r} -- MANUAL REVIEW"
                    )
                    print(line_msg)
                    logf.write(line_msg + '\n')
                    continue

                try:
                    closing_picked = to_picked_perspective(m['closing_spread'], side)
                    clv_after = clv_points(m['line'], closing_picked)
                    if clv_after is not None:
                        clv_after = round(clv_after, 1)
                except Exception as e:  # noqa: BLE001
                    counts['errors'] += 1
                    line_msg = (
                        f"ERROR id={pick.id} side={pick.side!r} "
                        f"line={m['line']} closing={m['closing_spread']} -- {e}"
                    )
                    print(line_msg)
                    logf.write(line_msg + '\n')
                    continue

                if _values_equal(clv_before, clv_after):
                    counts['no_change'] += 1
                    continue

                counts['updated'] += 1
                line_msg = (
                    f"CHANGE id={pick.id} sport={m['sport']} date={m['game_date']} "
                    f"side={pick.side!r} line={m['line']} "
                    f"closing_home={m['closing_spread']} -> closing_picked={closing_picked} "
                    f"clv {clv_before} -> {clv_after}"
                )
                print(line_msg)
                logf.write(line_msg + '\n')

                if args.apply:
                    conn.execute(
                        text("UPDATE picks SET clv = :clv WHERE id = :id"),
                        {'clv': clv_after, 'id': pick.id},
                    )

            # engine.begin() commits on context exit; if --apply is False,
            # we still issued no UPDATEs so the commit is a no-op.

        summary = (
            f"---\n"
            f"Mode: {mode}\n"
            f"Examined:                 {counts['examined']}\n"
            f"Updated (clv changed):    {counts['updated']}\n"
            f"No change:                {counts['no_change']}\n"
            f"Skipped (side unresolved):{counts['skipped_side_unresolved']}\n"
            f"Skipped (null closing):   {counts['skipped_null_closing']}\n"
            f"Skipped (null line):      {counts['skipped_null_line']}\n"
            f"Errors:                   {counts['errors']}\n"
            f"Finished: {datetime.utcnow().isoformat()}Z\n"
        )
        print(summary, end='')
        logf.write(summary)


if __name__ == '__main__':
    main()
