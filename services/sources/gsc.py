"""Google Search Console source for /api/admin/metrics.

Queries the Search Analytics API (searchconsole v1) for site
sc-domain:sharppicks.ai over the last 28 days. Cached for 12 hours
since GSC data updates infrequently anyway.

Reuses services.google_auth.get_credentials() — same OAuth identity
as services.sources.ga4 (dev@sharppicks.ai). The webmasters.readonly
scope is already in the refresh token.

GSC data lags ~2-3 days. endDate is set to today - 3 days to land in
the guaranteed-available window. date_range in the response surfaces
this for dashboard rendering.
"""
import logging
from datetime import datetime, timedelta, timezone

from services.google_auth import get_credentials
from services.metrics_cache import get_or_fetch

logger = logging.getLogger(__name__)

SITE_URL = 'sc-domain:sharppicks.ai'
CACHE_TTL_SECONDS = 12 * 60 * 60
LAG_DAYS = 3
WINDOW_DAYS = 28


def _service():
    from googleapiclient.discovery import build
    return build('searchconsole', 'v1', credentials=get_credentials(), cache_discovery=False)


def _date_range():
    today = datetime.now(timezone.utc).date()
    end = today - timedelta(days=LAG_DAYS)
    start = end - timedelta(days=WINDOW_DAYS)
    return start.isoformat(), end.isoformat()


def _query(service, dimensions, row_limit=25):
    start, end = _date_range()
    body = {
        'startDate': start,
        'endDate': end,
        'dimensions': dimensions,
        'rowLimit': row_limit,
    }
    return service.searchanalytics().query(siteUrl=SITE_URL, body=body).execute()


def _fetch_raw():
    service = _service()

    totals_resp = _query(service, dimensions=[], row_limit=1)
    rows = totals_resp.get('rows') or []
    if rows:
        clicks = int(rows[0].get('clicks', 0))
        impressions = int(rows[0].get('impressions', 0))
        ctr = float(rows[0].get('ctr', 0.0))
        position = float(rows[0].get('position', 0.0))
    else:
        clicks = impressions = 0
        ctr = position = 0.0

    # Daily breakdown for the dashboard sparkline. GSC returns the
    # 28-day window already so we just group by date and sort ascending.
    daily_resp = _query(service, dimensions=['date'], row_limit=30)
    daily = sorted(
        [
            {
                'date': (r.get('keys') or [''])[0],
                'clicks': int(r.get('clicks', 0)),
                'impressions': int(r.get('impressions', 0)),
            }
            for r in (daily_resp.get('rows') or [])
        ],
        key=lambda d: d['date'],
    )

    top_queries = [
        {
            'query': (r.get('keys') or [''])[0],
            'clicks': int(r.get('clicks', 0)),
            'impressions': int(r.get('impressions', 0)),
            'ctr': float(r.get('ctr', 0.0)),
            'position': float(r.get('position', 0.0)),
        }
        for r in (_query(service, ['query'], 25).get('rows') or [])
    ]

    top_pages = [
        {
            'page': (r.get('keys') or [''])[0],
            'clicks': int(r.get('clicks', 0)),
            'impressions': int(r.get('impressions', 0)),
            'ctr': float(r.get('ctr', 0.0)),
            'position': float(r.get('position', 0.0)),
        }
        for r in (_query(service, ['page'], 25).get('rows') or [])
    ]

    devices = [
        {
            'device': (r.get('keys') or [''])[0],
            'clicks': int(r.get('clicks', 0)),
            'impressions': int(r.get('impressions', 0)),
            'ctr': float(r.get('ctr', 0.0)),
        }
        for r in (_query(service, ['device'], 10).get('rows') or [])
    ]

    start, end = _date_range()
    return {
        'clicks': clicks,
        'impressions': impressions,
        'ctr': ctr,
        'avg_position': position,
        'daily': daily,
        'top_queries': top_queries,
        'top_pages': top_pages,
        'devices': devices,
        'date_range': {
            'start': start,
            'end': end,
            'note': 'GSC data lags 2-3 days; endDate is today - 3',
        },
    }


def fetch() -> dict:
    """Returns the cache envelope: {payload, fetched_at, stale, last_error}."""
    return get_or_fetch(
        cache_key='gsc:summary',
        ttl_seconds=CACHE_TTL_SECONDS,
        source='gsc',
        fetch_fn=_fetch_raw,
    )
