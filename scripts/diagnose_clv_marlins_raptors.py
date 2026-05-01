#!/usr/bin/env python3
"""
DIAGNOSTIC TOOL - NOT PRODUCTION CODE.

Pulls the Marlins and Raptors picks flagged in the CLV bug report so we can
verify what's actually stored in DB before applying the fix.

Run with: railway run python scripts/diagnose_clv_marlins_raptors.py
Or locally: DATABASE_URL=postgresql://... python scripts/diagnose_clv_marlins_raptors.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


QUERY = """
SELECT id, side, home_team, away_team, line, closing_spread, clv,
       sport, game_date, result
FROM picks
WHERE (
  (side LIKE '%Marlins%' AND ABS(line) = 1.5)
  OR (side LIKE '%Raptors%' AND line = -3.5 AND closing_spread IS NOT NULL)
)
AND result IS NOT NULL
ORDER BY game_date DESC LIMIT 10
"""


def main():
    raw = (
        os.environ.get("SQLALCHEMY_DATABASE_URI")
        or os.environ.get("DATABASE_URL")
        or os.environ.get("DATABASE_PRIVATE_URL")
        or ""
    )
    if not raw:
        print("ERROR: No DATABASE_URL found.")
        print("Run with: railway run python scripts/diagnose_clv_marlins_raptors.py")
        sys.exit(1)

    if raw.startswith("postgres://"):
        raw = "postgresql://" + raw[len("postgres://"):]

    from sqlalchemy import create_engine, text
    engine = create_engine(raw)
    with engine.connect() as conn:
        rows = conn.execute(text(QUERY)).fetchall()

    if not rows:
        print("No matching picks found.")
        return

    print(f"Found {len(rows)} matching picks:\n")
    for r in rows:
        d = r._mapping
        is_home_pick_substr = (
            (d['home_team'] or '').lower() in (d['side'] or '').lower()
        )
        side_resolved = (
            'home' if d['side'] and d['home_team'] and d['home_team'] in d['side']
            else 'away' if d['side'] and d['away_team'] and d['away_team'] in d['side']
            else None
        )
        print(f"  id:              {d['id']}")
        print(f"  sport:           {d['sport']}")
        print(f"  game_date:       {d['game_date']}")
        print(f"  side:            {d['side']!r}")
        print(f"  home_team:       {d['home_team']!r}")
        print(f"  away_team:       {d['away_team']!r}")
        print(f"  line:            {d['line']}")
        print(f"  closing_spread:  {d['closing_spread']}  (current DB value, home perspective)")
        print(f"  clv:             {d['clv']}")
        print(f"  result:          {d['result']}")
        print(f"  is_home (substr): {is_home_pick_substr}  (what the buggy detector returns)")
        print(f"  side (exact):     {side_resolved}  (what the fix-side resolver would return)")
        print("  ---")


if __name__ == "__main__":
    main()
