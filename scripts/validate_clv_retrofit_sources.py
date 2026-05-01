#!/usr/bin/env python3
"""
DIAGNOSTIC TOOL — read-only.

Two validations to inform the Step-2 retrofit decision:

1. NBA: pick a random sample of resolved post-2026-04-10 NBA picks. For
   each, compare picks.closing_spread (Postgres) to the last
   line_snapshots snap whose snapped_at < games.game_time (Railway
   SQLite volume). Report match/divergence.

2. MLB: distribution of mlb_games.close_collected_at vs game_time for
   resolved MLB picks. How often was the close captured AFTER first
   pitch (contaminated by in-game spread movement).

Must run from inside the Railway environment (or anywhere with both
the production DATABASE_URL and access to the SQLite volume mount):

  railway run python3 scripts/validate_clv_retrofit_sources.py

If running locally with explicit env vars:
  DATABASE_URL=postgresql://... \
  SQLITE_VOLUME_PATH=/path/to/prod/sharp_picks.db \
  python3 scripts/validate_clv_retrofit_sources.py
"""
import os
import sys
import sqlite3
import random
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


CUTOFF = '2026-04-10'
NBA_SAMPLE = 5
MLB_SAMPLE = 30  # for capture-timing distribution


def _resolve_sqlite_path():
    """Use SQLITE_VOLUME_PATH if set; otherwise db_path.get_sqlite_path()."""
    explicit = os.environ.get('SQLITE_VOLUME_PATH')
    if explicit:
        return explicit
    from db_path import get_sqlite_path
    return get_sqlite_path()


def _resolve_pg_url():
    raw = (
        os.environ.get("SQLALCHEMY_DATABASE_URI")
        or os.environ.get("DATABASE_URL")
        or os.environ.get("DATABASE_PRIVATE_URL")
        or ""
    )
    if not raw:
        print("ERROR: no DATABASE_URL", file=sys.stderr)
        sys.exit(1)
    if raw.startswith("postgres://"):
        raw = "postgresql://" + raw[len("postgres://"):]
    return raw


def _parse_iso(s):
    """Best-effort parse of stored timestamp strings."""
    if not s:
        return None
    s = s.strip()
    # strip trailing Z
    if s.endswith('Z'):
        s = s[:-1]
    for fmt in (
        '%Y-%m-%dT%H:%M:%S',
        '%Y-%m-%dT%H:%M',
        '%Y-%m-%dT%H:%M:%S.%f',
        '%Y-%m-%d %H:%M:%S',
    ):
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue
    return None


def validate_nba(pg_engine, sqlite_conn):
    """For NBA_SAMPLE random NBA picks resolved post-CUTOFF, compare
    picks.closing_spread to last line_snapshots row before game_time."""
    from sqlalchemy import text

    with pg_engine.connect() as c:
        rows = c.execute(text("""
            SELECT id, game_date, home_team, away_team, line, closing_spread, clv, side
            FROM picks
            WHERE sport='nba'
              AND result IS NOT NULL
              AND game_date >= :cutoff
              AND closing_spread IS NOT NULL
            ORDER BY game_date DESC
        """), {'cutoff': CUTOFF}).fetchall()

    if len(rows) <= NBA_SAMPLE:
        sample = rows
    else:
        random.seed(42)
        sample = random.sample(rows, NBA_SAMPLE)

    print(f"=== NBA validation (sample {len(sample)} of {len(rows)} eligible post-{CUTOFF}) ===")
    print()

    cur = sqlite_conn.cursor()
    matches = 0
    divergent = 0
    no_snap_data = 0

    for r in sample:
        m = r._mapping
        # find game_time from games table
        gt_row = cur.execute(
            """SELECT game_time FROM games
               WHERE game_date = ? AND home_team = ? AND away_team = ?""",
            (m['game_date'], m['home_team'], m['away_team']),
        ).fetchone()
        game_time = gt_row[0] if gt_row else None

        # find last snapshot before game_time (or just last snapshot if no gt)
        if game_time:
            snap = cur.execute(
                """SELECT spread_home, snapped_at FROM line_snapshots
                   WHERE game_date = ? AND home_team = ? AND away_team = ?
                     AND snapped_at < ?
                   ORDER BY snapped_at DESC LIMIT 1""",
                (m['game_date'], m['home_team'], m['away_team'], game_time),
            ).fetchone()
        else:
            snap = cur.execute(
                """SELECT spread_home, snapped_at FROM line_snapshots
                   WHERE game_date = ? AND home_team = ? AND away_team = ?
                   ORDER BY snapped_at DESC LIMIT 1""",
                (m['game_date'], m['home_team'], m['away_team']),
            ).fetchone()

        if snap is None:
            no_snap_data += 1
            print(f"  {m['game_date']} {m['away_team']} @ {m['home_team']}")
            print(f"    pick.line={m['line']}  pick.closing_spread={m['closing_spread']}  pick.clv={m['clv']}")
            print(f"    NO line_snapshots row found")
            print()
            continue

        snap_spread, snap_at = snap[0], snap[1]
        diff = (snap_spread - m['closing_spread']) if (snap_spread is not None and m['closing_spread'] is not None) else None
        agrees = abs(diff) < 0.01 if diff is not None else False
        if agrees:
            matches += 1
        else:
            divergent += 1

        print(f"  {m['game_date']} {m['away_team']} @ {m['home_team']}")
        print(f"    pick.line={m['line']}  pick.closing_spread={m['closing_spread']}  pick.clv={m['clv']}")
        print(f"    last snap before tip: spread_home={snap_spread} snapped_at={snap_at}  game_time={game_time}")
        print(f"    diff snap-stored={diff:+.2f}  {'MATCH' if agrees else 'DIVERGENT'}")
        print()

    print(f"NBA summary: matches={matches}  divergent={divergent}  no_snap_data={no_snap_data}")
    print()


def audit_mlb_capture_timing(pg_engine, sqlite_conn):
    """For resolved MLB picks, look up close_collected_at and game_time
    from mlb_games. Categorize: captured pre-tip vs post-tip vs missing
    timestamp. Distribution of pre-tip lead time and post-tip lag."""
    from sqlalchemy import text

    with pg_engine.connect() as c:
        rows = c.execute(text("""
            SELECT id, game_date, home_team, away_team
            FROM picks
            WHERE sport='mlb' AND result IS NOT NULL
            ORDER BY game_date DESC
        """)).fetchall()

    if len(rows) <= MLB_SAMPLE:
        sample = rows
    else:
        random.seed(43)
        sample = random.sample(rows, MLB_SAMPLE)

    print(f"=== MLB capture-timing audit (sample {len(sample)} of {len(rows)} resolved) ===")
    print()

    cur = sqlite_conn.cursor()
    pre_tip = []      # list of seconds of lead (positive = capture before tip)
    post_tip = []     # list of seconds of lag (positive = capture after tip)
    no_data = 0

    for r in sample:
        m = r._mapping
        row = cur.execute(
            """SELECT game_time, close_collected_at FROM mlb_games
               WHERE game_date LIKE ? AND home_team = ? AND away_team = ?
               LIMIT 1""",
            (f"{m['game_date']}%", m['home_team'], m['away_team']),
        ).fetchone()
        if row is None:
            no_data += 1
            print(f"  {m['game_date']} {m['away_team']} @ {m['home_team']}: NO mlb_games row")
            continue
        gt_str, cca_str = row[0], row[1]
        gt = _parse_iso(gt_str)
        cca = _parse_iso(cca_str)
        if gt is None or cca is None:
            no_data += 1
            print(f"  {m['game_date']} {m['away_team']} @ {m['home_team']}: game_time={gt_str!r} close_collected_at={cca_str!r} (unparsable)")
            continue
        delta = (cca - gt).total_seconds()  # seconds; positive = after tip
        if delta <= 0:
            pre_tip.append(-delta)
            tag = f"PRE-TIP by {-delta/60:.1f} min"
        else:
            post_tip.append(delta)
            tag = f"POST-TIP by {delta/60:.1f} min"
        print(f"  {m['game_date']} {m['away_team']:25s} @ {m['home_team']:25s}  game_time={gt_str}  close_at={cca_str}  {tag}")

    print()
    print(f"MLB capture-timing summary:")
    print(f"  pre-tip captures:  {len(pre_tip)}")
    if pre_tip:
        avg = sum(pre_tip) / len(pre_tip) / 60
        mn = min(pre_tip) / 60
        mx = max(pre_tip) / 60
        print(f"    lead min/avg/max minutes: {mn:.1f} / {avg:.1f} / {mx:.1f}")
    print(f"  post-tip captures: {len(post_tip)}  <-- contaminated by in-game spread")
    if post_tip:
        avg = sum(post_tip) / len(post_tip) / 60
        mn = min(post_tip) / 60
        mx = max(post_tip) / 60
        print(f"    lag min/avg/max minutes: {mn:.1f} / {avg:.1f} / {mx:.1f}")
    print(f"  no_data:           {no_data}")
    print()


def main():
    pg_url = _resolve_pg_url()
    sqlite_path = _resolve_sqlite_path()
    print(f"Postgres: {pg_url[:30]}...")
    print(f"SQLite:   {sqlite_path}")
    print()

    from sqlalchemy import create_engine
    pg = create_engine(pg_url)
    sq = sqlite3.connect(sqlite_path)

    validate_nba(pg, sq)
    audit_mlb_capture_timing(pg, sq)

    sq.close()


if __name__ == '__main__':
    main()
