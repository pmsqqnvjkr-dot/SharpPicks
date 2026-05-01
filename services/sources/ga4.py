"""GA4 metrics source for the unified /api/admin/metrics endpoint.

Queries the Google Analytics Data API v1 (BetaAnalyticsDataClient) for
property 532291721. Cached for 60 minutes via services.metrics_cache.

Uses services.google_auth.get_credentials() — same OAuth refresh-token
identity as services.sources.gsc.
"""
import logging
from datetime import datetime, timedelta, timezone
from typing import Literal

from services.google_auth import get_credentials
from services.metrics_cache import get_or_fetch

logger = logging.getLogger(__name__)

PROPERTY_ID = '532291721'
CACHE_TTL_SECONDS = 60 * 60


def _client():
    from google.analytics.data_v1beta import BetaAnalyticsDataClient
    return BetaAnalyticsDataClient(credentials=get_credentials())


def _date_range(range_):
    days = 7 if range_ == '7d' else 30
    today = datetime.now(timezone.utc).date()
    return (today - timedelta(days=days)).isoformat(), today.isoformat()


def _run(client, request_kwargs):
    from google.analytics.data_v1beta.types import (
        DateRange, Dimension, Metric, RunReportRequest,
    )
    return client.run_report(RunReportRequest(
        property=f'properties/{PROPERTY_ID}',
        date_ranges=[DateRange(**request_kwargs.pop('date_range'))],
        dimensions=[Dimension(name=d) for d in request_kwargs.pop('dimensions', [])],
        metrics=[Metric(name=m) for m in request_kwargs.pop('metrics', [])],
        limit=request_kwargs.pop('limit', 10),
    ))


def _row_value(row, idx, kind='metric'):
    if kind == 'metric':
        return row.metric_values[idx].value if idx < len(row.metric_values) else ''
    return row.dimension_values[idx].value if idx < len(row.dimension_values) else ''


def _fetch_raw(range_):
    client = _client()
    since, until = _date_range(range_)
    date_range = {'start_date': since, 'end_date': until}

    totals_resp = _run(client, {
        'date_range': dict(date_range),
        'metrics': ['sessions', 'totalUsers', 'engagedSessions', 'engagementRate'],
        'limit': 1,
    })
    if totals_resp.rows:
        sessions = int(_row_value(totals_resp.rows[0], 0))
        users = int(_row_value(totals_resp.rows[0], 1))
        engaged_sessions = int(_row_value(totals_resp.rows[0], 2))
        engagement_rate = float(_row_value(totals_resp.rows[0], 3))
    else:
        sessions = users = engaged_sessions = 0
        engagement_rate = 0.0

    landing_resp = _run(client, {
        'date_range': dict(date_range),
        'dimensions': ['landingPagePlusQueryString'],
        'metrics': ['sessions'],
        'limit': 10,
    })
    top_landing = [
        {'page': _row_value(r, 0, 'dim'), 'sessions': int(_row_value(r, 0))}
        for r in landing_resp.rows
    ]

    source_resp = _run(client, {
        'date_range': dict(date_range),
        'dimensions': ['sessionSource', 'sessionMedium'],
        'metrics': ['sessions'],
        'limit': 10,
    })
    acquisition = [
        {
            'source': _row_value(r, 0, 'dim'),
            'medium': _row_value(r, 1, 'dim'),
            'sessions': int(_row_value(r, 0)),
        }
        for r in source_resp.rows
    ]

    try:
        conv_resp = _run(client, {
            'date_range': dict(date_range),
            'dimensions': ['eventName'],
            'metrics': ['conversions'],
            'limit': 25,
        })
        conversions = [
            {'event_name': _row_value(r, 0, 'dim'),
             'count': int(float(_row_value(r, 0)))}
            for r in conv_resp.rows
        ]
    except Exception as e:
        logger.warning('ga4 conversions query failed: %s', e)
        conversions = []

    return {
        'sessions': sessions,
        'users': users,
        'engaged_sessions': engaged_sessions,
        'engagement_rate': engagement_rate,
        'top_landing_pages': top_landing,
        'acquisition': acquisition,
        'conversions': conversions,
        'date_range': {'start': since, 'end': until},
    }


def fetch(range_: Literal['7d', '30d']) -> dict:
    """Returns the cache envelope: {payload, fetched_at, stale, last_error}."""
    if range_ not in ('7d', '30d'):
        raise ValueError(f'invalid range: {range_}')
    return get_or_fetch(
        cache_key=f'ga4:{range_}',
        ttl_seconds=CACHE_TTL_SECONDS,
        source='ga4',
        fetch_fn=lambda: _fetch_raw(range_),
    )
