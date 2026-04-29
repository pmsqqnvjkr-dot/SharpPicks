"""Compute coverage of WHIP/IP pitcher fields in mlb_games.

Backs both the `/api/admin/diagnose-pitcher-coverage` admin endpoint and the
`scripts/check_pitcher_coverage.py` CLI. Coverage = fraction of completed
games in the lookback window where the field is present and not a known
default sentinel (WHIP=1.30 league fallback, IP=0).

Used to validate the Phase 2C parser fix (commit ec87991) which extended
the ESPN pitcher parser to read WHIP/IP from `prob['athlete']['statistics']`
instead of dropping those fields. The thresholds applied to the
`recommendation` field encode the user's product decision rule:

    >= 50%  -> "ship"               (mark Phase 2C done)
    20-50%  -> "queue_fallback"     (ship as-is, queue MLB Stats API as separate work)
    <  20%  -> "fallback_required"  (block on MLB Stats API integration)

The minimum per-field coverage (across the four WHIP/IP columns) is what
gets compared to the threshold, since the model loses signal whenever any
one of the four fields is missing.
"""

import logging
import sqlite3
from typing import Optional

try:
    from db_path import get_sqlite_path  # type: ignore
except Exception:  # pragma: no cover - fallback for ad-hoc invocation
    def get_sqlite_path() -> str:
        return "sharp_picks.db"

WHIP_DEFAULT = 1.30
IP_DEFAULT = 0

SHIP_THRESHOLD = 0.50
QUEUE_FALLBACK_THRESHOLD = 0.20

logger = logging.getLogger(__name__)


def _pct(n: int, d: int) -> Optional[float]:
    return round(100.0 * n / d, 2) if d else None


def _recommendation(min_coverage: Optional[float]) -> str:
    if min_coverage is None:
        return "no_data"
    if min_coverage >= SHIP_THRESHOLD:
        return "ship"
    if min_coverage >= QUEUE_FALLBACK_THRESHOLD:
        return "queue_fallback"
    return "fallback_required"


def compute_coverage(
    days: int = 30,
    last_completed: bool = False,
    db_path: Optional[str] = None,
) -> dict:
    """Return per-field coverage of WHIP/IP for completed mlb_games rows.

    Args:
        days: Lookback window size in days.
        last_completed: Anchor the window on the most recent completed game
            in the DB instead of today. Useful when dev DB lags prod.
        db_path: Explicit SQLite path. Defaults to ``db_path.get_sqlite_path()``.

    Returns:
        JSON-serializable dict; see module docstring for the threshold
        definitions and the ``recommendation`` mapping.
    """
    resolved_db = db_path or get_sqlite_path()

    base_response = {
        "db_path": resolved_db,
        "anchor_mode": "last_completed" if last_completed else "today",
        "days": days,
        "thresholds": {
            "ship": SHIP_THRESHOLD,
            "queue_fallback": QUEUE_FALLBACK_THRESHOLD,
        },
        "pre_fix_baseline_note": (
            "Pre-ec87991 parser dropped WHIP/IP from prob['athlete']['statistics'], "
            "so real coverage on rows ingested before the fix is effectively 0%."
        ),
    }

    conn = sqlite3.connect(resolved_db)
    try:
        cur = conn.cursor()

        if last_completed:
            cur.execute(
                "SELECT MAX(game_date) FROM mlb_games WHERE home_score IS NOT NULL"
            )
            anchor_row = cur.fetchone()
            anchor = anchor_row[0] if anchor_row else None
            if not anchor:
                return {
                    **base_response,
                    "total_games_in_window": 0,
                    "window_start": None,
                    "window_end": None,
                    "coverage": {},
                    "aggregate": {},
                    "era_reference": {},
                    "recommendation": "no_data",
                    "error": "no_completed_games",
                }
            window_end = anchor
            cur.execute("SELECT date(?, ?)", (anchor, f"-{int(days)} days"))
            window_start = cur.fetchone()[0]
        else:
            cur.execute("SELECT date('now')")
            window_end = cur.fetchone()[0]
            cur.execute("SELECT date('now', ?)", (f"-{int(days)} days",))
            window_start = cur.fetchone()[0]

        sql = """
            SELECT
              COUNT(*) AS n,
              SUM(CASE WHEN home_pitcher_whip IS NOT NULL AND home_pitcher_whip != ?
                       THEN 1 ELSE 0 END),
              SUM(CASE WHEN away_pitcher_whip IS NOT NULL AND away_pitcher_whip != ?
                       THEN 1 ELSE 0 END),
              SUM(CASE WHEN home_pitcher_ip   IS NOT NULL AND home_pitcher_ip   != ?
                       THEN 1 ELSE 0 END),
              SUM(CASE WHEN away_pitcher_ip   IS NOT NULL AND away_pitcher_ip   != ?
                       THEN 1 ELSE 0 END),
              SUM(CASE WHEN home_pitcher_era  IS NOT NULL THEN 1 ELSE 0 END),
              SUM(CASE WHEN away_pitcher_era  IS NOT NULL THEN 1 ELSE 0 END)
            FROM mlb_games
            WHERE home_score IS NOT NULL
              AND game_date >= ?
              AND game_date <= ?
        """
        cur.execute(
            sql,
            (
                WHIP_DEFAULT, WHIP_DEFAULT, IP_DEFAULT, IP_DEFAULT,
                window_start, window_end,
            ),
        )
        n, h_whip, a_whip, h_ip, a_ip, h_era, a_era = cur.fetchone()
        n = int(n or 0)
    finally:
        conn.close()

    if not n:
        return {
            **base_response,
            "total_games_in_window": 0,
            "window_start": window_start,
            "window_end": window_end,
            "coverage": {},
            "aggregate": {},
            "era_reference": {},
            "recommendation": "no_data",
        }

    h_whip = int(h_whip or 0)
    a_whip = int(a_whip or 0)
    h_ip = int(h_ip or 0)
    a_ip = int(a_ip or 0)
    h_era = int(h_era or 0)
    a_era = int(a_era or 0)

    coverage = {
        "home_pitcher_whip": {"count": h_whip, "pct": _pct(h_whip, n)},
        "away_pitcher_whip": {"count": a_whip, "pct": _pct(a_whip, n)},
        "home_pitcher_ip":   {"count": h_ip,   "pct": _pct(h_ip, n)},
        "away_pitcher_ip":   {"count": a_ip,   "pct": _pct(a_ip, n)},
    }
    avg_whip = (h_whip + a_whip) / (2 * n)
    avg_ip = (h_ip + a_ip) / (2 * n)
    min_field_pct = min(v["pct"] for v in coverage.values())
    aggregate = {
        "whip_avg_pct": round(avg_whip * 100, 2),
        "ip_avg_pct": round(avg_ip * 100, 2),
        "min_field_pct": min_field_pct,
    }
    era_reference = {
        "home_pitcher_era": {"count": h_era, "pct": _pct(h_era, n)},
        "away_pitcher_era": {"count": a_era, "pct": _pct(a_era, n)},
    }

    return {
        **base_response,
        "total_games_in_window": n,
        "window_start": window_start,
        "window_end": window_end,
        "coverage": coverage,
        "aggregate": aggregate,
        "era_reference": era_reference,
        "recommendation": _recommendation(min_field_pct / 100.0),
    }
