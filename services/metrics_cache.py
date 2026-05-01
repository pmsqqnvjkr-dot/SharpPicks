"""Single-source-of-truth cache for the unified /api/admin/metrics endpoint.

get_or_fetch() either returns a fresh cached payload or calls fetch_fn(),
writes the result, and returns it. On fetch failure, the previously good
payload is preserved and last_error is recorded so Phase 3 UI can render
"stale" state without losing data.
"""
import logging
from datetime import datetime, timedelta, timezone
from typing import Callable

from models import db, MetricsCache

logger = logging.getLogger(__name__)


def _ensure_utc(dt):
    """SQLite (used in tests) drops tz info on DateTime(timezone=True)
    round-trip; Postgres preserves it. Treat naive values as UTC so
    comparisons work in both backends."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def get_or_fetch(
    cache_key: str,
    ttl_seconds: int,
    source: str,
    fetch_fn: Callable[[], dict],
) -> dict:
    """Look up cache_key. If fresh, return it. Otherwise call fetch_fn().

    On fetch_fn success: upsert payload, extend expiry, clear last_error.
    On fetch_fn exception: preserve previously cached payload (if any),
    record last_error, return stale=True envelope. If no prior row exists,
    return payload=None with stale=True (no row written, since payload is
    NOT NULL).

    Returns:
      {
        "payload": dict | None,
        "fetched_at": datetime | None,
        "stale": bool,
        "last_error": str | None,
      }
    """
    now = datetime.now(timezone.utc)
    row = db.session.get(MetricsCache, cache_key)

    if row is not None and _ensure_utc(row.expires_at) > now:
        return {
            'payload': row.payload,
            'fetched_at': _ensure_utc(row.fetched_at),
            'stale': False,
            'last_error': row.last_error,
        }

    try:
        new_payload = fetch_fn()
    except Exception as e:
        err = str(e)[:500] or e.__class__.__name__
        logger.exception('metrics_cache fetch failed for cache_key=%s', cache_key)
        if row is not None:
            row.last_error = err
            db.session.commit()
            return {
                'payload': row.payload,
                'fetched_at': _ensure_utc(row.fetched_at),
                'stale': True,
                'last_error': err,
            }
        return {
            'payload': None,
            'fetched_at': None,
            'stale': True,
            'last_error': err,
        }

    expires_at = now + timedelta(seconds=ttl_seconds)
    if row is None:
        row = MetricsCache(
            cache_key=cache_key, payload=new_payload, fetched_at=now,
            expires_at=expires_at, source=source, last_error=None,
        )
        db.session.add(row)
    else:
        row.payload = new_payload
        row.fetched_at = now
        row.expires_at = expires_at
        row.source = source
        row.last_error = None
    db.session.commit()

    return {
        'payload': new_payload,
        'fetched_at': now,
        'stale': False,
        'last_error': None,
    }


def invalidate(cache_key: str) -> bool:
    """Force expiry on a cache key. Returns True if a row was found."""
    row = db.session.get(MetricsCache, cache_key)
    if row is None:
        return False
    row.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
    db.session.commit()
    return True
