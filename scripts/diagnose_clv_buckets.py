#!/usr/bin/env python3
"""
DIAGNOSTIC TOOL - NOT PRODUCTION CODE.

Aggregates resolved picks (result IS NOT NULL) by sport and a pre/post
2026-04-10 bucket. Reports count, mean, median, stdev of CLV per bucket.

Excludes rows with clv IS NULL (moneyline picks and rows with missing
closing_spread); CLV statistics on NULLs are meaningless. Count is the
number of rows with a non-null clv contributing to the stats, not the
total resolved-pick count in the bucket.

Run with: railway run python scripts/diagnose_clv_buckets.py
Or locally: DATABASE_URL=postgresql://... python scripts/diagnose_clv_buckets.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


QUERY = """
SELECT
    sport,
    CASE
        WHEN game_date < DATE '2026-04-10' THEN 'pre_2026_04_10'
        ELSE 'post_2026_04_10'
    END AS bucket,
    COUNT(*) AS n,
    AVG(clv)::float AS mean_clv,
    PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY clv)::float AS median_clv,
    STDDEV_SAMP(clv)::float AS stdev_clv
FROM picks
WHERE result IS NOT NULL
  AND clv IS NOT NULL
GROUP BY sport, bucket
ORDER BY sport, bucket
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
        print("Run with: railway run python scripts/diagnose_clv_buckets.py")
        sys.exit(1)

    if raw.startswith("postgres://"):
        raw = "postgresql://" + raw[len("postgres://"):]

    from sqlalchemy import create_engine, text
    engine = create_engine(raw)
    with engine.connect() as conn:
        rows = conn.execute(text(QUERY)).fetchall()

    if not rows:
        print("No resolved picks with non-null CLV found.")
        return

    header = f"{'sport':<8} {'bucket':<18} {'n':>6} {'mean':>10} {'median':>10} {'stdev':>10}"
    print(header)
    print("-" * len(header))
    for r in rows:
        d = r._mapping
        mean = d['mean_clv']
        median = d['median_clv']
        stdev = d['stdev_clv']
        print(
            f"{(d['sport'] or '?'):<8} "
            f"{d['bucket']:<18} "
            f"{d['n']:>6} "
            f"{(f'{mean:+.3f}' if mean is not None else 'NA'):>10} "
            f"{(f'{median:+.3f}' if median is not None else 'NA'):>10} "
            f"{(f'{stdev:.3f}' if stdev is not None else 'NA'):>10}"
        )


if __name__ == "__main__":
    main()
