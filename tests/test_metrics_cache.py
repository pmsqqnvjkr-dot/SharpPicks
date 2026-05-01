"""Unit tests for services.metrics_cache.get_or_fetch.

Uses the existing TESTING=1 / SQLite db fixture from tests/conftest.py.
"""
from datetime import datetime, timedelta, timezone

from services.metrics_cache import get_or_fetch, invalidate
from models import MetricsCache


def test_first_call_fetches_and_caches(db):
    calls = []

    def fetch_fn():
        calls.append(1)
        return {'x': 1}

    result = get_or_fetch('test:k', 60, 'cloudflare', fetch_fn)
    assert result['payload'] == {'x': 1}
    assert result['stale'] is False
    assert result['last_error'] is None
    assert len(calls) == 1
    row = db.session.get(MetricsCache, 'test:k')
    assert row.source == 'cloudflare'
    assert row.payload == {'x': 1}


def test_second_call_within_ttl_uses_cache(db):
    calls = []

    def fetch_fn():
        calls.append(1)
        return {'x': 1}

    get_or_fetch('test:k', 60, 'cloudflare', fetch_fn)
    result = get_or_fetch('test:k', 60, 'cloudflare', fetch_fn)
    assert result['payload'] == {'x': 1}
    assert result['stale'] is False
    assert len(calls) == 1


def test_call_after_expiry_refetches(db):
    calls = []

    def fetch_fn():
        calls.append(1)
        return {'n': len(calls)}

    get_or_fetch('test:k', 60, 'cloudflare', fetch_fn)
    row = db.session.get(MetricsCache, 'test:k')
    row.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
    db.session.commit()
    result = get_or_fetch('test:k', 60, 'cloudflare', fetch_fn)
    assert result['payload'] == {'n': 2}
    assert len(calls) == 2


def test_fetch_failure_returns_stale_with_prior_payload(db):
    def fetch_ok():
        return {'good': True}

    get_or_fetch('test:k', 60, 'cloudflare', fetch_ok)
    row = db.session.get(MetricsCache, 'test:k')
    row.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
    db.session.commit()

    def fetch_boom():
        raise RuntimeError('upstream timeout')

    result = get_or_fetch('test:k', 60, 'cloudflare', fetch_boom)
    assert result['payload'] == {'good': True}
    assert result['stale'] is True
    assert 'upstream timeout' in result['last_error']

    refreshed = db.session.get(MetricsCache, 'test:k')
    assert refreshed.payload == {'good': True}
    assert refreshed.last_error == 'upstream timeout'


def test_fetch_failure_with_no_prior_row_returns_null_payload(db):
    def fetch_boom():
        raise RuntimeError('first fetch failed')

    result = get_or_fetch('test:k', 60, 'cloudflare', fetch_boom)
    assert result['payload'] is None
    assert result['stale'] is True
    assert 'first fetch failed' in result['last_error']
    assert db.session.get(MetricsCache, 'test:k') is None


def test_invalidate_forces_refetch(db):
    calls = []

    def fetch_fn():
        calls.append(1)
        return {'x': len(calls)}

    get_or_fetch('test:k', 60, 'cloudflare', fetch_fn)
    assert invalidate('test:k') is True
    result = get_or_fetch('test:k', 60, 'cloudflare', fetch_fn)
    assert len(calls) == 2
    assert result['payload'] == {'x': 2}


def test_invalidate_unknown_key(db):
    assert invalidate('does-not-exist') is False
