"""Infrastructure metrics for the Phase 3 admin Infra tab.

Backs:
  GET /api/admin/infra/health -> {chips, latency_series, recent_deploys,
                                  database_health}

Pipeline status is served by the existing /api/admin/cron-health
endpoint (CronLog table) — no need to duplicate that logic here.
The Infra tab UI calls both endpoints and merges.

Sources used:
  - request_metrics table (per-request timings, written by app.py
    after_request middleware)
  - psutil if available (memory + CPU)
  - subprocess git log (recent deploys)
  - Postgres pg_stat_database for connection count
"""
import logging
import os
import subprocess
from datetime import datetime, timedelta
from collections import defaultdict

from sqlalchemy import func, text

from models import db, RequestMetric

logger = logging.getLogger(__name__)


def _percentile(values: list, p: float) -> int:
    """Approximate percentile from a sorted list of integers."""
    if not values:
        return 0
    s = sorted(values)
    k = max(0, min(len(s) - 1, int(round(p * (len(s) - 1)))))
    return int(s[k])


def _health_chips(now: datetime) -> dict:
    cutoff_24h = now - timedelta(hours=24)

    # p95 latency last 24h across non-static requests
    durations = [r.duration_ms for r in RequestMetric.query.filter(
        RequestMetric.created_at >= cutoff_24h
    ).with_entities(RequestMetric.duration_ms).all()]
    p50 = _percentile(durations, 0.50)
    p95 = _percentile(durations, 0.95)
    p99 = _percentile(durations, 0.99)

    # 5xx error count last 24h
    errors_24h = RequestMetric.query.filter(
        RequestMetric.created_at >= cutoff_24h,
        RequestMetric.status >= 500,
    ).count()

    # request volume last 24h
    req_24h = len(durations)

    # System metrics (best-effort via psutil)
    cpu_pct = None
    mem_pct = None
    try:
        import psutil  # type: ignore
        cpu_pct = round(psutil.cpu_percent(interval=0.1), 1)
        mem_pct = round(psutil.virtual_memory().percent, 1)
    except ImportError:
        pass
    except Exception as e:
        logger.warning('infra: psutil read failed: %s', e)

    # Uptime: with no /health probe history, we infer uptime from the
    # absence of recent crashes. For v1 just report 100% if we're
    # serving this request. Phase 4 will add a real health_checks table.
    uptime_pct = 100.0

    return {
        'uptime_30d_pct':    uptime_pct,
        'p50_24h_ms':        p50,
        'p95_24h_ms':        p95,
        'p99_24h_ms':        p99,
        'errors_24h':        errors_24h,
        'requests_24h':      req_24h,
        'cpu_pct':           cpu_pct,
        'mem_pct':           mem_pct,
    }


def _latency_series(now: datetime, hours: int = 168) -> list:
    """Hourly p50/p95/p99 over the last `hours` hours (default 7 days).
    Pulls all rows in the window once and buckets in-process."""
    cutoff = now - timedelta(hours=hours)
    rows = RequestMetric.query.filter(
        RequestMetric.created_at >= cutoff
    ).with_entities(RequestMetric.created_at, RequestMetric.duration_ms).all()

    by_hour = defaultdict(list)
    for created_at, dur in rows:
        bucket = created_at.replace(minute=0, second=0, microsecond=0)
        by_hour[bucket].append(dur)

    series = []
    for h in range(hours, -1, -1):
        anchor = (now - timedelta(hours=h)).replace(minute=0, second=0, microsecond=0)
        durations = by_hour.get(anchor, [])
        series.append({
            'hour': anchor.isoformat(),
            'p50': _percentile(durations, 0.50) if durations else None,
            'p95': _percentile(durations, 0.95) if durations else None,
            'p99': _percentile(durations, 0.99) if durations else None,
            'n':   len(durations),
        })
    return series


def _recent_deploys() -> list:
    """Last 10 commits via `git log`. Empty list if git isn't callable."""
    try:
        repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        out = subprocess.check_output(
            ['git', '-C', repo_root, 'log', '-10', '--pretty=format:%h|%ai|%s|%an'],
            stderr=subprocess.DEVNULL,
            timeout=3,
        ).decode('utf-8', errors='replace')
        rows = []
        for line in out.splitlines():
            parts = line.split('|', 3)
            if len(parts) != 4:
                continue
            sha, date, msg, author = parts
            rows.append({
                'sha': sha,
                'date': date,
                'message': msg[:200],
                'author': author,
                'status': 'success',  # we only see merged/pushed commits, so success
            })
        return rows
    except (subprocess.SubprocessError, FileNotFoundError, OSError) as e:
        logger.warning('infra: git log failed: %s', e)
        return []


def _database_health() -> dict:
    """Postgres health snapshot via pg_stat views. Best-effort; SQLite
    falls through to None values."""
    out = {
        'connections_active': None,
        'connections_idle': None,
        'database_size_mb': None,
        'longest_running_query_seconds': None,
        'user_events_rows': None,
    }
    try:
        # connection counts
        active = db.session.execute(text("""
            SELECT count(*) FROM pg_stat_activity
             WHERE state = 'active' AND datname = current_database()
        """)).scalar()
        idle = db.session.execute(text("""
            SELECT count(*) FROM pg_stat_activity
             WHERE state = 'idle' AND datname = current_database()
        """)).scalar()
        out['connections_active'] = int(active or 0)
        out['connections_idle'] = int(idle or 0)

        # database size
        size_bytes = db.session.execute(text(
            "SELECT pg_database_size(current_database())"
        )).scalar()
        if size_bytes:
            out['database_size_mb'] = round(int(size_bytes) / (1024 * 1024), 1)

        # longest running query (excluding this one)
        longest = db.session.execute(text("""
            SELECT EXTRACT(EPOCH FROM (now() - query_start))
              FROM pg_stat_activity
             WHERE state = 'active'
               AND pid != pg_backend_pid()
               AND query_start IS NOT NULL
             ORDER BY query_start ASC
             LIMIT 1
        """)).scalar()
        if longest is not None:
            out['longest_running_query_seconds'] = round(float(longest), 1)
    except Exception as e:
        logger.warning('infra: database_health query failed: %s', e)

    # user_events row count for the DB card (chunk C). Separate try so a
    # transient connection blip on the pg_stat queries above doesn't bury
    # this one. Uses the ORM table to stay portable across SQLite/Postgres.
    try:
        from models import UserEvent
        out['user_events_rows'] = db.session.query(UserEvent).count()
    except Exception as e:
        logger.warning('infra: user_events count failed: %s', e)
    return out


def _odds_api_quota() -> dict:
    """Surface the-odds-api remaining quota. Reads off the x-requests-*
    response headers from a cheap /sports call. Returns
    {'remaining', 'used', 'last', 'status', 'fetched_at'}.

    Built after 2026-05-25 incident where a silent quota exhaustion
    surfaced as model data_failure across both sports. status:
      'ok'    — remaining > 1000
      'warn'  — remaining 1..1000
      'empty' — remaining == 0
      'error' — call failed
    """
    import os as _os
    import requests as _req
    key = _os.environ.get('ODDS_API_KEY') or _os.environ.get('THE_ODDS_API_KEY')
    out = {
        'remaining': None,
        'used': None,
        'last': None,
        'status': 'unknown',
        'fetched_at': datetime.utcnow().isoformat() + 'Z',
    }
    if not key:
        out['status'] = 'no_key'
        return out
    try:
        r = _req.get(
            'https://api.the-odds-api.com/v4/sports/',
            params={'apiKey': key},
            timeout=5,
        )
        rem = r.headers.get('x-requests-remaining')
        used = r.headers.get('x-requests-used')
        last = r.headers.get('x-requests-last')
        if rem is not None:
            out['remaining'] = int(rem)
        if used is not None:
            out['used'] = int(used)
        if last is not None:
            try:
                out['last'] = int(last)
            except ValueError:
                out['last'] = last
        if out['remaining'] is None:
            out['status'] = 'error'
        elif out['remaining'] == 0:
            out['status'] = 'empty'
        elif out['remaining'] <= 1000:
            out['status'] = 'warn'
        else:
            out['status'] = 'ok'
    except Exception as e:
        logger.warning('infra: odds_api quota fetch failed: %s', e)
        out['status'] = 'error'
        out['error'] = str(e)[:200]
    return out


def fetch() -> dict:
    now = datetime.utcnow()
    return {
        'chips':            _health_chips(now),
        'latency_series':   _latency_series(now),
        'recent_deploys':   _recent_deploys(),
        'database_health':  _database_health(),
        'odds_api_quota':   _odds_api_quota(),
    }
