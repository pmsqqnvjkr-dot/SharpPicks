"""Google Play Console metrics source for /api/admin/metrics.

Pulls install + active-user numbers from the Play Console "Bulk Reports"
exports. Google publishes daily CSV reports to a Cloud Storage bucket
your service account has read access to. The bucket is named
`pubsite_prod_<DEVELOPER_ID>` where DEVELOPER_ID is the numeric ID
visible in your Play Console URL.

Why this path: Google's public Play Developer APIs do NOT expose
install/MAU/DAU numbers programmatically. The only documented way
to get those metrics is the Bulk Reports CSV export. The
Play Developer Reporting API exposes app vitals (crash rate, ANRs)
but not the user metrics the dashboard wants.

Required env vars:
  GOOGLE_PLAY_SERVICE_ACCOUNT_JSON  full JSON contents of the SA key
  GOOGLE_PLAY_DEVELOPER_ID          numeric account id (URL segment)
  GOOGLE_PLAY_PACKAGE_NAME          e.g. com.sharppicksllc.signals

Returns zeros + a configuration note if any var is missing.

Cached for 60 minutes since the CSVs themselves update once per day.
"""
import csv
import io
import json
import logging
import os
from datetime import datetime, date, timedelta, timezone

import requests
from google.oauth2 import service_account
from google.auth.transport.requests import Request as AuthRequest

from services.metrics_cache import get_or_fetch

logger = logging.getLogger(__name__)

CACHE_TTL_SECONDS = 60 * 60

GCS_API = 'https://storage.googleapis.com/storage/v1/b'
GCS_DOWNLOAD = 'https://storage.googleapis.com'
SCOPES = ['https://www.googleapis.com/auth/devstorage.read_only']


def _empty(note: str) -> dict:
    return {
        'configured': False,
        'daily_28d': [],
        'device_installs_28d': 0,
        'device_uninstalls_28d': 0,
        'first_opens_28d': 0,
        'active_device_installs': 0,
        'mau': 0,
        'dau_avg_28d': 0.0,
        'note': note,
    }


def _get_sa_credentials():
    raw = os.environ.get('GOOGLE_PLAY_SERVICE_ACCOUNT_JSON', '').strip()
    if not raw:
        return None
    try:
        info = json.loads(raw)
    except json.JSONDecodeError as e:
        logger.warning('GOOGLE_PLAY_SERVICE_ACCOUNT_JSON failed to parse: %s', e)
        return None
    creds = service_account.Credentials.from_service_account_info(info, scopes=SCOPES)
    creds.refresh(AuthRequest())
    return creds


def _list_objects(creds, bucket: str, prefix: str) -> list:
    """List GCS objects under bucket+prefix. Returns object names."""
    headers = {'Authorization': f'Bearer {creds.token}'}
    url = f'{GCS_API}/{bucket}/o?prefix={prefix}'
    resp = requests.get(url, headers=headers, timeout=15)
    if resp.status_code == 404:
        raise RuntimeError(f'GCS bucket not found: {bucket} (check GOOGLE_PLAY_DEVELOPER_ID, or SA bucket access)')
    resp.raise_for_status()
    items = (resp.json() or {}).get('items') or []
    return [item['name'] for item in items]


def _download_csv(creds, bucket: str, name: str) -> list:
    """Download GCS object as CSV rows (list of dicts)."""
    headers = {'Authorization': f'Bearer {creds.token}'}
    url = f'{GCS_DOWNLOAD}/{bucket}/{name}'
    resp = requests.get(url, headers=headers, timeout=30)
    resp.raise_for_status()
    # Play Console CSVs are UTF-16 with BOM. Standard library handles it
    # with utf-16 codec; default utf-8 returns gibberish.
    text = resp.content.decode('utf-16')
    reader = csv.DictReader(io.StringIO(text))
    return list(reader)


def _latest_files(names: list, package: str) -> list:
    """Filter names to the package's CSVs and return them in YYYYMM
    order, newest last. Pattern: <type>_<package>_YYYYMM_<scope>.csv"""
    matches = [n for n in names if package in n and n.endswith('.csv')]
    matches.sort()  # YYYYMM is in the filename, lex sort = chronological
    return matches


def _sum_window(rows: list, days: int, date_col: str, value_cols: list) -> dict:
    """Sum integer values across `value_cols` for rows within the last
    `days` calendar days. Skips rows with non-integer values gracefully."""
    cutoff = date.today() - timedelta(days=days)
    totals = {col: 0 for col in value_cols}
    for r in rows:
        raw_date = (r.get(date_col) or '').strip()
        try:
            d = datetime.strptime(raw_date, '%Y-%m-%d').date()
        except ValueError:
            continue
        if d < cutoff:
            continue
        for col in value_cols:
            val = (r.get(col) or '').strip()
            if not val:
                continue
            try:
                totals[col] += int(val)
            except ValueError:
                try:
                    totals[col] += int(float(val))
                except ValueError:
                    pass
    return totals


def _daily_series(rows: list, days: int, date_col: str, value_cols: list) -> list:
    """Return one row per day across the trailing window, each row a
    dict {date, <col1>, <col2>, ...}. Missing days are zero-filled so
    the resulting series has uniform length for sparkline rendering.
    Skips CSV rows with un-parseable dates or numeric values (they're
    typically header carryovers or empty cells)."""
    cutoff = date.today() - timedelta(days=days)
    today = date.today()
    by_date = {}
    for r in rows:
        raw_date = (r.get(date_col) or '').strip()
        try:
            d = datetime.strptime(raw_date, '%Y-%m-%d').date()
        except ValueError:
            continue
        if d < cutoff or d > today:
            continue
        bucket = by_date.setdefault(d, {col: 0 for col in value_cols})
        for col in value_cols:
            val = (r.get(col) or '').strip()
            if not val:
                continue
            try:
                bucket[col] += int(val)
            except ValueError:
                try:
                    bucket[col] += int(float(val))
                except ValueError:
                    pass
    out = []
    for offset in range(days, -1, -1):
        d = today - timedelta(days=offset)
        row = {'date': d.isoformat()}
        row.update(by_date.get(d, {col: 0 for col in value_cols}))
        out.append(row)
    return out


def _latest_active_devices(rows: list, date_col: str, value_col: str) -> int:
    """Active devices is a snapshot, not a sum. Take the latest row's
    value, parsed as int. Returns 0 if no parseable value."""
    latest = 0
    latest_date = None
    for r in rows:
        raw_date = (r.get(date_col) or '').strip()
        try:
            d = datetime.strptime(raw_date, '%Y-%m-%d').date()
        except ValueError:
            continue
        if latest_date is None or d > latest_date:
            val = (r.get(value_col) or '').strip()
            try:
                latest = int(val) if val else 0
                latest_date = d
            except ValueError:
                pass
    return latest


def _fetch_raw() -> dict:
    dev_id = (os.environ.get('GOOGLE_PLAY_DEVELOPER_ID') or '').strip()
    package = (os.environ.get('GOOGLE_PLAY_PACKAGE_NAME') or '').strip()
    if not dev_id:
        return _empty('GOOGLE_PLAY_DEVELOPER_ID env var not set')
    if not package:
        return _empty('GOOGLE_PLAY_PACKAGE_NAME env var not set')

    creds = _get_sa_credentials()
    if not creds:
        return _empty('GOOGLE_PLAY_SERVICE_ACCOUNT_JSON env var not set or invalid JSON')

    bucket = f'pubsite_prod_{dev_id}'

    # Installs report: one CSV per package per month, aggregated daily.
    # Columns include Date, Daily Device Installs, Daily Device Uninstalls,
    # Active Device Installs, Daily User Acquisition (= first opens).
    try:
        installs_files = _latest_files(
            _list_objects(creds, bucket, 'stats/installs/'),
            package,
        )
    except RuntimeError as e:
        return _empty(str(e))
    except requests.HTTPError as e:
        # 403 here usually means SA missing storage.objects.get on the bucket.
        # Permissions take ~24h to propagate after granting in Play Console.
        return _empty(f'GCS access error: {e.response.status_code}. Permissions may still be propagating (24h after Play Console grant).')

    if not installs_files:
        return _empty(f'No installs CSV found in gs://{bucket}/stats/installs/ for package {package}')

    # Fetch the last 2 monthly CSVs so a 28-day window straddling a
    # month boundary still has full coverage.
    rows = []
    for name in installs_files[-2:]:
        try:
            rows.extend(_download_csv(creds, bucket, name))
        except Exception as e:
            logger.warning('google_play: download failed for %s: %s', name, e)

    if not rows:
        return _empty('Installs CSV could not be parsed')

    # Column names per Play Console bulk-export schema
    DATE_COL = 'Date'
    DEVICE_INSTALLS = 'Daily Device Installs'
    DEVICE_UNINSTALLS = 'Daily Device Uninstalls'
    ACTIVE_DEVICES = 'Active Device Installs'
    USER_ACQUISITIONS = 'Daily User Acquisitions'  # "first opens"
    USER_INSTALLS = 'Daily User Installs'

    sums = _sum_window(rows, 28, DATE_COL, [
        DEVICE_INSTALLS, DEVICE_UNINSTALLS, USER_ACQUISITIONS, USER_INSTALLS,
    ])
    daily = _daily_series(rows, 28, DATE_COL, [
        DEVICE_INSTALLS, DEVICE_UNINSTALLS, USER_ACQUISITIONS, USER_INSTALLS,
        ACTIVE_DEVICES,
    ])
    # Reshape daily rows to the dashboard-friendly key names so the
    # frontend doesn't need to know Google's column titles.
    daily_clean = [{
        'date': r['date'],
        'first_opens': r[USER_ACQUISITIONS],
        'installs':    r[DEVICE_INSTALLS],
        'uninstalls':  r[DEVICE_UNINSTALLS],
        'user_installs': r[USER_INSTALLS],
        'active_devices': r[ACTIVE_DEVICES],
    } for r in daily]
    active = _latest_active_devices(rows, DATE_COL, ACTIVE_DEVICES)

    return {
        'configured': True,
        'device_installs_28d':   sums[DEVICE_INSTALLS],
        'device_uninstalls_28d': sums[DEVICE_UNINSTALLS],
        'first_opens_28d':       sums[USER_ACQUISITIONS],
        'user_installs_28d':     sums[USER_INSTALLS],
        'active_device_installs': active,
        # Daily series for sparklines. 29 rows: trailing 28 days + today.
        # Zero-filled for any date Google's CSV didn't cover.
        'daily_28d': daily_clean,
        # MAU and DAU live in a different CSV (stats/store_performance/)
        # that's harder to align. Stub for now; populate in a follow-up
        # commit once we confirm the column names against a real export.
        'mau': 0,
        'dau_avg_28d': 0.0,
        'package_name': package,
        'developer_id': dev_id,
        'bucket': bucket,
        'rows_seen': len(rows),
        'note': 'Bulk-report CSVs update once per day; data lags 24-48h.',
    }


def fetch() -> dict:
    """Returns the cache envelope: {payload, fetched_at, stale, last_error}."""
    return get_or_fetch(
        cache_key='google_play:summary',
        ttl_seconds=CACHE_TTL_SECONDS,
        source='google_play',
        fetch_fn=_fetch_raw,
    )
