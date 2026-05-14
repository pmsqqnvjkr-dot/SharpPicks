"""App Store Connect (Apple) metrics source for /api/admin/metrics.

Mirrors services.sources.google_play in shape so the Acquisition section
of the dashboard can render iOS + Android KPIs from a uniform structure.

Apple's Sales and Trends API returns daily gzipped TSV files with per-
country, per-SKU install counts. We sum across 28 days for the
'installs' / 'first-time downloads' tiles. DAU isn't exposed by the
Sales API; that comes from our own UserEvent table filtered to
oauth_provider='apple' users (handled outside this source).

Required env vars:
  ASC_API_KEY_ID    Key ID from App Store Connect API Keys page
  ASC_ISSUER_ID     Issuer UUID from App Store Connect API Keys page
  ASC_PRIVATE_KEY   Full PEM-formatted ES256 private key (including
                    BEGIN/END lines)
  ASC_VENDOR_NUMBER Numeric vendor number from Sales and Trends
                    (8-digit). Without this the source returns
                    'configured but vendor number missing'.

JWT lifetime is capped at 20 minutes per Apple's requirements. We sign
fresh per fetch; no token caching beyond Python locals.

Cached for 60 minutes at the dashboard layer since Apple's reports
update once per day with a 1-2 day lag.
"""
import csv
import gzip
import io
import logging
import os
import time
from datetime import datetime, date, timedelta, timezone

import jwt
import requests

from services.metrics_cache import get_or_fetch

logger = logging.getLogger(__name__)

CACHE_TTL_SECONDS = 60 * 60
API_BASE = 'https://api.appstoreconnect.apple.com/v1'

# Product Type Identifiers that count as first-time iPhone/iPad installs
# of a paid or free app. Excludes updates (7), in-app purchases (IA-1),
# and other secondary product types. See Apple's 'App Store Sales Report
# Headers' doc for the full enumeration.
FIRST_INSTALL_PRODUCT_TYPES = frozenset({
    '1',    # iPhone install
    '1F',   # Universal (iPhone + iPad) install
    '1T',   # iPad-only install
    '1E',   # iPhone install with Mac support
    '1EP',  # iPhone install on iPad (Catalyst)
    '1M',   # Apple Mac install
    'F1',   # iPad install (free)
})

# Includes first installs + redownloads. Used for 'total installs' tile.
ANY_INSTALL_PRODUCT_TYPES = FIRST_INSTALL_PRODUCT_TYPES | frozenset({
    '7',    # iPhone redownload
    '7F',   # Universal redownload
    '7T',   # iPad redownload
    '7E',   # iPhone redownload with Mac
    'F7',   # iPad redownload (free)
})


def _empty(note: str, configured: bool = False) -> dict:
    return {
        'configured': configured,
        'first_opens_28d': 0,
        'device_installs_28d': 0,
        'redownloads_28d': 0,
        'active_device_installs': 0,  # Always 0 from Apple; UserEvent
        # provides iOS DAU via a different path.
        'days_with_data': 0,
        'note': note,
    }


def _sign_jwt() -> str | None:
    """Sign a fresh ES256 JWT for App Store Connect API calls. Returns
    None and logs if any credential is missing."""
    key_id = (os.environ.get('ASC_API_KEY_ID') or '').strip()
    issuer = (os.environ.get('ASC_ISSUER_ID') or '').strip()
    pem = (os.environ.get('ASC_PRIVATE_KEY') or '').strip()
    if not (key_id and issuer and pem):
        return None
    now = int(time.time())
    payload = {
        'iss': issuer,
        'iat': now,
        'exp': now + 20 * 60,  # Apple caps lifetime at 20 minutes
        'aud': 'appstoreconnect-v1',
    }
    headers = {'kid': key_id, 'typ': 'JWT'}
    try:
        return jwt.encode(payload, pem, algorithm='ES256', headers=headers)
    except Exception as e:
        logger.warning('ASC: JWT sign failed: %s', e)
        return None


def _verify_auth(token: str) -> tuple[bool, str]:
    """Hit GET /v1/apps to confirm the JWT works + the key has scope.
    Returns (ok, message). 401/403 indicate bad credentials; other
    statuses indicate transport or rate-limit problems."""
    try:
        r = requests.get(
            f'{API_BASE}/apps?limit=1',
            headers={'Authorization': f'Bearer {token}'},
            timeout=10,
        )
    except requests.RequestException as e:
        return False, f'transport error: {e}'
    if r.status_code == 200:
        return True, 'ok'
    if r.status_code in (401, 403):
        return False, f'auth failed ({r.status_code}). Verify ASC_API_KEY_ID, ASC_ISSUER_ID, ASC_PRIVATE_KEY are correct and the key has at least App Manager role.'
    return False, f'unexpected status {r.status_code}: {r.text[:200]}'


def _fetch_sales_report(token: str, vendor: str, report_date: date) -> list[dict] | None:
    """Fetch a single daily Sales report. Returns the parsed TSV rows
    or None if Apple has no report for that date yet (typical for
    today + yesterday since reports lag 1-2 days)."""
    r = requests.get(
        f'{API_BASE}/salesReports',
        headers={
            'Authorization': f'Bearer {token}',
            'Accept': 'application/a-gzip',
        },
        params={
            'filter[frequency]': 'DAILY',
            'filter[reportType]': 'SALES',
            'filter[reportSubType]': 'SUMMARY',
            'filter[vendorNumber]': vendor,
            'filter[reportDate]': report_date.isoformat(),
            'filter[version]': '1_0',
        },
        timeout=15,
    )
    if r.status_code == 404:
        # Apple returns 404 when no report exists for that date yet
        return None
    if r.status_code != 200:
        logger.warning('ASC: salesReports %s -> %s %s', report_date, r.status_code, r.text[:200])
        return None
    try:
        body = gzip.decompress(r.content).decode('utf-8', errors='replace')
    except OSError:
        # Sometimes Apple returns text directly (older API behavior)
        body = r.content.decode('utf-8', errors='replace')
    reader = csv.DictReader(io.StringIO(body), delimiter='\t')
    return list(reader)


def _sum_window(rows_by_date: dict, window_days: int) -> dict:
    """Sum first-install + any-install units across the trailing window."""
    first = 0
    total = 0
    days_with_data = 0
    cutoff = date.today() - timedelta(days=window_days)
    for d, rows in rows_by_date.items():
        if d < cutoff:
            continue
        days_with_data += 1
        for row in rows:
            ptype = (row.get('Product Type Identifier') or '').strip()
            try:
                units = int(row.get('Units') or '0')
            except ValueError:
                units = 0
            if ptype in FIRST_INSTALL_PRODUCT_TYPES:
                first += units
            if ptype in ANY_INSTALL_PRODUCT_TYPES:
                total += units
    return {
        'first_opens_28d': first,
        'device_installs_28d': total,
        'redownloads_28d': max(0, total - first),
        'days_with_data': days_with_data,
    }


def _fetch_raw() -> dict:
    token = _sign_jwt()
    if not token:
        return _empty('ASC creds incomplete (need ASC_API_KEY_ID + ASC_ISSUER_ID + ASC_PRIVATE_KEY)')
    ok, msg = _verify_auth(token)
    if not ok:
        return _empty(msg)
    vendor = (os.environ.get('ASC_VENDOR_NUMBER') or '').strip()
    if not vendor:
        return _empty('Auth ok but ASC_VENDOR_NUMBER not set. Find it in App Store Connect -> Sales and Trends -> top-left dropdown -> "Vendor Number".', configured=True)
    # Apple sales data lags 1-2 days. Walk back from 2 days ago to
    # 30 days ago. Skip dates with no report (Apple returns 404).
    rows_by_date = {}
    for offset in range(2, 30):
        d = date.today() - timedelta(days=offset)
        rows = _fetch_sales_report(token, vendor, d)
        if rows is not None:
            rows_by_date[d] = rows
    if not rows_by_date:
        return _empty('Auth ok, vendor number set, but no sales reports returned for any date in the trailing 30d window. Either the vendor number is wrong or the app has not generated any sales/download activity.', configured=True)
    sums = _sum_window(rows_by_date, window_days=28)
    return {
        'configured': True,
        'first_opens_28d': sums['first_opens_28d'],
        'device_installs_28d': sums['device_installs_28d'],
        'redownloads_28d': sums['redownloads_28d'],
        'active_device_installs': 0,
        'days_with_data': sums['days_with_data'],
        'note': 'Apple Sales reports lag 1-2 days. DAU is computed from UserEvent (oauth_provider=apple) outside this source.',
    }


def fetch() -> dict:
    """Returns the cache envelope: {payload, fetched_at, stale, last_error}."""
    return get_or_fetch(
        cache_key='app_store_connect:summary',
        ttl_seconds=CACHE_TTL_SECONDS,
        source='app_store_connect',
        fetch_fn=_fetch_raw,
    )
