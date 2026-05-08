"""Model performance summary source for /api/admin/metrics.

Lightweight aggregate of last-30d pick results per sport, intended for
the Today's Read action item — not the full Model tab data. Returns
win/loss counts, win rate, and unit ROI per sport so the headline
generator can surface "NBA model: 8-3 (72.7%, +4.2u) over 30d" without
having to call the heavier services/model_perf module.

Pick.result is stored as 'win' | 'loss' | 'push' | 'revoked' | 'pending'
(the same enum services/model_perf.py operates on after the
2026-05-08 fix).
"""
import logging
from datetime import datetime, timedelta

from services.metrics_cache import get_or_fetch

logger = logging.getLogger(__name__)

CACHE_TTL_SECONDS = 30 * 60  # 30 minutes — picks resolve overnight
WINDOW_DAYS = 30


def _fetch_raw() -> dict:
    """Aggregate pick results by sport across the last 30 days."""
    from models import db, Pick

    cutoff = datetime.utcnow() - timedelta(days=WINDOW_DAYS)

    rows = db.session.query(
        Pick.sport, Pick.result, Pick.profit_units,
    ).filter(
        Pick.published_at >= cutoff,
        Pick.result.in_(('win', 'loss', 'push')),
    ).all()

    by_sport: dict = {}
    for sport, result, profit_units in rows:
        s = (sport or 'unknown').lower()
        bucket = by_sport.setdefault(s, {'wins': 0, 'losses': 0, 'pushes': 0, 'profit_units': 0.0})
        if result == 'win':
            bucket['wins'] += 1
        elif result == 'loss':
            bucket['losses'] += 1
        elif result == 'push':
            bucket['pushes'] += 1
        if profit_units is not None:
            bucket['profit_units'] += float(profit_units)

    summary = {}
    for s, bucket in by_sport.items():
        graded = bucket['wins'] + bucket['losses']
        win_rate = round(100.0 * bucket['wins'] / graded, 1) if graded else None
        summary[s] = {
            'wins': bucket['wins'],
            'losses': bucket['losses'],
            'pushes': bucket['pushes'],
            'graded': graded,
            'win_rate': win_rate,
            'profit_units': round(bucket['profit_units'], 2),
        }

    return {
        'window_days': WINDOW_DAYS,
        'by_sport': summary,
    }


def fetch() -> dict:
    """Returns the cache envelope: {payload, fetched_at, stale, last_error}."""
    return get_or_fetch(
        cache_key='model_perf:summary',
        ttl_seconds=CACHE_TTL_SECONDS,
        source='model_perf',
        fetch_fn=_fetch_raw,
    )
