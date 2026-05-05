"""Cloudflare Web Analytics integration for the unified /api/admin/metrics
endpoint.

Queries the GraphQL Analytics API at account level via the
rumPageloadEventsAdaptiveGroups dataset, scoped by a CF Web Analytics
site tag. Cached for 30 minutes via services.metrics_cache.

Free-tier compatible with multi-day ranges. Coverage: whatever sites
have the CF Web Analytics RUM beacon installed (sharppicks.ai marketing
site). App-subdomain server-side traffic is captured separately via the
PageView table and exposed by services.sources.events.

Structurally similar to the legacy admin_api.py:cf_analytics endpoint
(same dataset, same auth model). The difference is enriched flat shape,
cache-backed, used by the unified metrics endpoint. The legacy endpoint
remains for backward compat.
"""
import os
import logging
from datetime import datetime, timedelta, timezone
from typing import Literal

import requests

from services.metrics_cache import get_or_fetch

logger = logging.getLogger(__name__)

CF_GQL_URL = 'https://api.cloudflare.com/client/v4/graphql'
CACHE_TTL_SECONDS = 5 * 60  # CF GraphQL data is at the 1-min granularity in CF, so 5 min is plenty fresh and respects rate limits

QUERY = """
query($accountTag: String!, $siteTag: String!, $since: String!, $until: String!) {
  viewer {
    accounts(filter: {accountTag: $accountTag}) {
      totals: rumPageloadEventsAdaptiveGroups(
        limit: 1
        filter: {AND: [{datetime_geq: $since, datetime_leq: $until}, {siteTag: $siteTag}]}
      ) {
        count
        sum { visits }
      }
      daily: rumPageloadEventsAdaptiveGroups(
        limit: 31
        orderBy: [date_ASC]
        filter: {AND: [{datetime_geq: $since, datetime_leq: $until}, {siteTag: $siteTag}]}
      ) {
        count
        sum { visits }
        dimensions { date: date }
      }
      topPaths: rumPageloadEventsAdaptiveGroups(
        limit: 10
        orderBy: [count_DESC]
        filter: {AND: [{datetime_geq: $since, datetime_leq: $until}, {siteTag: $siteTag}]}
      ) {
        count
        dimensions { path: requestPath }
      }
      topReferrers: rumPageloadEventsAdaptiveGroups(
        limit: 10
        orderBy: [count_DESC]
        filter: {AND: [{datetime_geq: $since, datetime_leq: $until}, {siteTag: $siteTag}]}
      ) {
        count
        dimensions { referer: refererHost }
      }
      countries: rumPageloadEventsAdaptiveGroups(
        limit: 10
        orderBy: [count_DESC]
        filter: {AND: [{datetime_geq: $since, datetime_leq: $until}, {siteTag: $siteTag}]}
      ) {
        count
        dimensions { country: countryName }
      }
    }
  }
}
"""


def _fetch_raw(range_: Literal['7d', '30d']) -> dict:
    # Prefer CLOUDFLARE_* (Phase 2 spec); fall back to legacy CF_* names
    # already set in Railway for the admin_api.py:cf_analytics endpoint.
    # Same values, same scopes work for both endpoints.
    token = os.environ.get('CLOUDFLARE_API_TOKEN') or os.environ.get('CF_API_TOKEN')
    account_id = os.environ.get('CLOUDFLARE_ACCOUNT_ID') or os.environ.get('CF_ACCOUNT_ID')
    site_tag = os.environ.get('CLOUDFLARE_SITE_TAG') or os.environ.get('CF_WEB_ANALYTICS_SITE_TAG')
    missing = [
        name for name, val in (
            ('CLOUDFLARE_API_TOKEN/CF_API_TOKEN', token),
            ('CLOUDFLARE_ACCOUNT_ID/CF_ACCOUNT_ID', account_id),
            ('CLOUDFLARE_SITE_TAG/CF_WEB_ANALYTICS_SITE_TAG', site_tag),
        ) if not val
    ]
    if missing:
        raise RuntimeError(f'Cloudflare env vars not set: {", ".join(missing)}')

    days = 7 if range_ == '7d' else 30
    today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    since = today - timedelta(days=days)
    fmt = '%Y-%m-%dT%H:%M:%SZ'

    response = requests.post(
        CF_GQL_URL,
        headers={
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json',
        },
        json={
            'query': QUERY,
            'variables': {
                'accountTag': account_id,
                'siteTag': site_tag,
                'since': since.strftime(fmt),
                'until': today.strftime(fmt),
            },
        },
        timeout=15,
    )
    response.raise_for_status()
    data = response.json()
    if data.get('errors'):
        raise RuntimeError(f'Cloudflare GraphQL errors: {data["errors"]}')
    accounts = (data.get('data') or {}).get('viewer', {}).get('accounts') or []
    if not accounts:
        raise RuntimeError(f'No account returned for accountTag={account_id}')
    return accounts[0]


def _flatten(raw: dict) -> dict:
    """Convert CF's nested GraphQL shape to a flat dashboard-ready dict."""
    totals_list = raw.get('totals') or []
    total = totals_list[0] if totals_list else {}
    total_sum = total.get('sum') or {}
    return {
        'page_views': total.get('count', 0),
        'visits': total_sum.get('visits', 0),
        'daily': [
            {
                'date': d.get('dimensions', {}).get('date'),
                'page_views': d.get('count', 0),
                'visits': (d.get('sum') or {}).get('visits', 0),
            }
            for d in (raw.get('daily') or [])
        ],
        'top_paths': [
            {
                'path': p.get('dimensions', {}).get('path'),
                'page_views': p.get('count', 0),
            }
            for p in (raw.get('topPaths') or [])
        ],
        'top_referrers': [
            {
                'referer': r.get('dimensions', {}).get('referer') or '(direct)',
                'page_views': r.get('count', 0),
            }
            for r in (raw.get('topReferrers') or [])
        ],
        'countries': [
            {
                'country': c.get('dimensions', {}).get('country'),
                'page_views': c.get('count', 0),
            }
            for c in (raw.get('countries') or [])
        ],
        'note': (
            'Cloudflare Web Analytics RUM beacon. Coverage: sharppicks.ai '
            'marketing site only (app subdomain not RUM-instrumented). '
            'page_views = pageload events. visits = CF\'s human-visit '
            'estimate. For app-side server traffic, see the events source.'
        ),
    }


def fetch(range_: Literal['7d', '30d']) -> dict:
    """Returns the cache envelope: {payload, fetched_at, stale, last_error}.
    payload is a flat dashboard-ready dict (see _flatten)."""
    if range_ not in ('7d', '30d'):
        raise ValueError(f'invalid range: {range_}')
    cache_key = f'cloudflare:{range_}'
    return get_or_fetch(
        cache_key=cache_key,
        ttl_seconds=CACHE_TTL_SECONDS,
        source='cloudflare',
        fetch_fn=lambda: _flatten(_fetch_raw(range_)),
    )
