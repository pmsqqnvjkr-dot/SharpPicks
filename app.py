"""
SHARP PICKS - ALL-IN-ONE APP
Flask server with API endpoints, dashboard, authentication, and scheduled tasks
"""

import os
import re
import sys
import json
import logging
import threading
import uuid

print(f"BOOT: pid={os.getpid()} python={sys.version_info[:2]} PORT={os.environ.get('PORT','not set')} DEPLOYMENT={os.environ.get('REPLIT_DEPLOYMENT','0')}", flush=True)

log_level = logging.INFO if os.environ.get("REPLIT_DEPLOYMENT") == "1" else logging.DEBUG
logging.basicConfig(level=log_level)

from flask import Flask, jsonify, Response, session, request, redirect, send_from_directory
from sport_config import get_live_sports

app = Flask(__name__, static_folder='dist', static_url_path='/static-disabled')
app.secret_key = os.environ.get("SESSION_SECRET", "dev-secret-key-change-in-production")
app.config['SECRET_KEY'] = app.secret_key

DEPLOY_VERSION = '106b1d6-diag4'

@app.route('/health')
def health():
    diag = {'status': 'ok', 'version': DEPLOY_VERSION}
    if request.args.get('diag') == '1':
        try:
            today_str = _get_et_today()
            conn = get_sqlite_conn()
            cur = conn.cursor()
            diag['date'] = today_str
            diag['db_path'] = get_sqlite_path()
            # Surface SQLite mode so we can verify WAL stuck on the volume.
            # Lists the wal/shm sidecar files when present.
            try:
                diag['sqlite_journal_mode'] = cur.execute('PRAGMA journal_mode;').fetchone()[0]
                diag['sqlite_synchronous'] = cur.execute('PRAGMA synchronous;').fetchone()[0]
                diag['sqlite_busy_timeout_ms'] = cur.execute('PRAGMA busy_timeout;').fetchone()[0]
                _db_dir = os.path.dirname(get_sqlite_path()) or '.'
                _siblings = []
                for _f in sorted(os.listdir(_db_dir)):
                    if _f.startswith('sharp_picks.db'):
                        _siblings.append({'name': _f, 'size': os.path.getsize(os.path.join(_db_dir, _f))})
                diag['sqlite_files'] = _siblings
            except Exception as _wal_err:
                diag['sqlite_diag_error'] = str(_wal_err)[:200]
            diag['nba_games'] = cur.execute("SELECT COUNT(*) FROM games WHERE game_date = ?", (today_str,)).fetchone()[0]
            diag['nba_with_spreads'] = cur.execute("SELECT COUNT(*) FROM games WHERE game_date = ? AND spread_home IS NOT NULL", (today_str,)).fetchone()[0]
            diag['nba_unscored'] = cur.execute("SELECT COUNT(*) FROM games WHERE game_date = ? AND home_score IS NULL", (today_str,)).fetchone()[0]
            sample = cur.execute("SELECT id, away_team, home_team, spread_home, game_time, home_score, away_score, collected_at FROM games WHERE game_date = ? ORDER BY collected_at DESC LIMIT 20", (today_str,)).fetchall()
            diag['nba_sample'] = [{'id': r[0][:20], 'away': r[1], 'home': r[2], 'spread': r[3], 'time': r[4], 'h_score': r[5], 'a_score': r[6], 'collected': r[7]} for r in sample]
            # Recent dates in DB to check for misplaced games
            date_counts = cur.execute("SELECT game_date, COUNT(*), SUM(CASE WHEN home_score IS NULL THEN 1 ELSE 0 END) FROM games GROUP BY game_date ORDER BY game_date DESC LIMIT 7").fetchall()
            diag['recent_dates'] = [{'date': r[0], 'total': r[1], 'unscored': r[2]} for r in date_counts]
            diag['mlb_games'] = cur.execute("SELECT COUNT(*) FROM mlb_games WHERE game_date = ?", (today_str,)).fetchone()[0]
            # Test Odds API
            try:
                import requests as _req
                api_key = os.environ.get('ODDS_API_KEY', '')
                test_resp = _req.get("https://api.the-odds-api.com/v4/sports/basketball_nba/odds/",
                    params={'apiKey': api_key, 'regions': 'us', 'markets': 'spreads', 'oddsFormat': 'american'},
                    timeout=10)
                diag['odds_api_status'] = test_resp.status_code
                diag['odds_api_remaining'] = test_resp.headers.get('x-requests-remaining')
                if test_resp.status_code == 200:
                    raw = test_resp.json()
                    diag['odds_api_raw_count'] = len(raw)
                    from main import utc_to_eastern_date
                    today_games = [g for g in raw if utc_to_eastern_date(g.get('commence_time', '') or '') == today_str]
                    diag['odds_api_today_count'] = len(today_games)
                    diag['odds_api_today_sample'] = [{'away': g['away_team'], 'home': g['home_team'], 'time': g.get('commence_time','')} for g in today_games[:5]]
                    diag['odds_api_all_dates'] = list(set(utc_to_eastern_date(g.get('commence_time', '') or '') for g in raw))
                    diag['odds_api_raw_sample'] = [{'away': g['away_team'], 'home': g['home_team'], 'time': g.get('commence_time',''), 'et_date': utc_to_eastern_date(g.get('commence_time','') or '')} for g in raw[:5]]
                else:
                    diag['odds_api_error'] = test_resp.text[:200]
            except Exception as api_err:
                diag['odds_api_error'] = str(api_err)[:200]
            conn.close()
        except Exception as e:
            diag['diag_error'] = str(e)
    return diag, 200

@app.route('/')
def root_landing():
    from flask import send_from_directory, make_response, request
    dist_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'dist')
    index_path = os.path.join(dist_dir, 'index.html')
    has_spa = os.path.isfile(index_path)
    user = get_current_user_from_session()
    # Honor the ?view= query param so the auth.html native-redirect
    # ('/' + ?view=signup|signin) actually lands inside the React SPA
    # instead of looping back to the marketing page.
    view_param = (request.args.get('view') or '').lower()
    wants_app = view_param in ('signup', 'signin', 'login', 'register')
    if (user or wants_app) and has_spa:
        resp = make_response(send_from_directory(dist_dir, 'index.html'))
        resp.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        return resp
    templates_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates')
    return send_from_directory(templates_dir, 'app-landing.html')

@app.route('/download')
def download_redirect():
    return '''<!DOCTYPE html>
<html><head><meta charset="UTF-8"><title>Download SharpPicks</title>
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta http-equiv="refresh" content="3;url=https://sharppicks.ai">
</head><body style="background:#0A0D14;">
<script>
var ua=navigator.userAgent.toLowerCase();
if(/android/.test(ua))window.location.replace('https://play.google.com/store/apps/details?id=com.sharppicksllc.app');
else window.location.replace('https://sharppicks.ai');
</script>
</body></html>'''

is_production = (
    os.environ.get('REPLIT_DEPLOYMENT') == '1'
    or bool(os.environ.get('RAILWAY_PUBLIC_DOMAIN'))
    or bool(os.environ.get('RAILWAY_PROJECT_ID'))
)

CRON_SECRET = os.environ.get('CRON_SECRET', '')

PRE_PROVISIONED_GRANTS = {
    'kd1donnelly@gmail.com': { 'premium': True, 'founder': True, 'plan': 'lifetime' },
}

def _apply_pre_provisioned(user):
    """Check if a newly registered user has pre-provisioned grants and apply them."""
    grant = PRE_PROVISIONED_GRANTS.get((user.email or '').lower())
    if not grant:
        return
    if grant.get('premium'):
        user.is_premium = True
        user.subscription_status = 'active'
        user.subscription_plan = grant.get('plan', 'lifetime')
    if grant.get('founder'):
        user.founding_member = True
        if not user.founding_number:
            from models import User as UserModel
            max_num = db.session.query(db.func.max(UserModel.founding_number)).scalar() or 0
            user.founding_number = max_num + 1
    db.session.commit()

def verify_cron(f):
    from functools import wraps
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not CRON_SECRET or request.headers.get('X-Cron-Secret') != CRON_SECRET:
            return jsonify({'error': 'unauthorized'}), 403
        return f(*args, **kwargs)
    return wrapper

# Phase 3.7: per-request timing for the admin Infra tab. before_request
# stamps the start time on g; after_request reads it, computes duration,
# and writes a row to request_metrics. We skip static assets and tracking
# endpoints to keep volume in check.
@app.before_request
def _stamp_request_start():
    from flask import g
    import time as _time
    g._req_start_ms = _time.monotonic() * 1000.0

_REQ_METRIC_SKIP_PREFIXES = (
    '/assets/', '/static/', '/favicon', '/health',
    '/api/track-events', '/api/track-event', '/api/admin/app-analytics',
)

@app.after_request
def _record_request_metric(response):
    try:
        from flask import g
        from models import RequestMetric
        path = request.path or ''
        if any(path.startswith(p) for p in _REQ_METRIC_SKIP_PREFIXES):
            return response
        start_ms = getattr(g, '_req_start_ms', None)
        if start_ms is None:
            return response
        import time as _time
        duration_ms = int((_time.monotonic() * 1000.0) - start_ms)
        rec = RequestMetric(
            path=path[:200],
            method=(request.method or '')[:10],
            status=int(getattr(response, 'status_code', 0) or 0),
            duration_ms=max(0, duration_ms),
        )
        db.session.add(rec)
        db.session.commit()
    except Exception:
        try:
            db.session.rollback()
        except Exception:
            pass
    return response


@app.after_request
def set_cache_headers(response):
    if request.path.startswith('/assets/'):
        response.headers['Cache-Control'] = 'public, max-age=31536000, immutable'
    elif request.path.startswith('/api/'):
        
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
    elif request.path.endswith('.html') or request.path == '/' or request.path == '/manifest.webmanifest':
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
    elif request.path.endswith('.js') and not request.path.startswith('/assets/'):
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response.headers['Pragma'] = 'no-cache'
    return response

import hashlib
import threading

_SKIP_TRACKING_PREFIXES = ('/assets/', '/favicon', '/health', '/api/admin/app-analytics')
_SKIP_TRACKING_EXTENSIONS = ('.png', '.jpg', '.ico', '.js', '.css', '.map', '.woff', '.woff2', '.svg')

@app.after_request
def track_page_view(response):
    path = request.path
    if any(path.startswith(p) for p in _SKIP_TRACKING_PREFIXES):
        return response
    if any(path.endswith(e) for e in _SKIP_TRACKING_EXTENSIONS):
        return response
    try:
        ip = request.remote_addr or ''
        ip_hash = hashlib.sha256(ip.encode()).hexdigest()[:16]
        ua = (request.headers.get('User-Agent') or '')[:512]
        method = request.method
        status = response.status_code

        def _insert():
            try:
                with app.app_context():
                    pv = PageView(path=path[:512], method=method, status_code=status,
                                  ip_hash=ip_hash, user_agent=ua)
                    db.session.add(pv)
                    db.session.commit()
            except Exception:
                db.session.rollback()

        threading.Thread(target=_insert, daemon=True).start()
    except Exception:
        pass
    return response

from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_login import LoginManager, login_required, current_user, login_user, logout_user, user_logged_in
from werkzeug.middleware.proxy_fix import ProxyFix
import sqlite3
import subprocess
from db_path import get_sqlite_path, get_sqlite_conn
import requests as http_requests
from datetime import datetime, timedelta, timezone

def _get_et_today():
    """Get current Eastern Time date string (YYYY-MM-DD)."""
    try:
        from zoneinfo import ZoneInfo
        now_et = datetime.now(ZoneInfo('America/New_York'))
    except ImportError:
        now_et = datetime.utcnow() - timedelta(hours=5)
    return now_et.strftime('%Y-%m-%d')


def _abbr(team):
    from cards_api import TEAM_ABBR
    return TEAM_ABBR.get(team, team[:3].upper() if team else '???')


def _upsert_market_note_insight(report, sport='nba'):
    """Create or update the daily Market Note insight from the market report dict."""
    from market_note_templates import generate_market_note

    if not report.get('available'):
        return None
    date_str = report.get('date', '')
    if not date_str or len(date_str) != 10:
        return None
    slug = f"market-note-{sport}-{date_str}" if sport != 'nba' else f"market-note-{date_str}"

    prev_note_title = None
    consecutive_same_bias = 0
    try:
        prev_note = (Insight.query
                     .filter_by(category='market_notes', sport=sport)
                     .filter(Insight.slug != slug)
                     .order_by(Insight.publish_date.desc())
                     .first())
        if prev_note:
            prev_note_title = prev_note.title

        lean = report.get('market_lean') or {}
        today_bias = 'underdog' if lean.get('underdogs', 0) > lean.get('favorites', 0) else 'favorite'
        recent_notes = (Insight.query
                        .filter_by(category='market_notes', sport=sport)
                        .filter(Insight.slug != slug)
                        .order_by(Insight.publish_date.desc())
                        .limit(7)
                        .all())
        for note in recent_notes:
            note_content = note.content or ''
            fav_m = re.search(r'(\d+)\s*favorite\s*edge', note_content)
            dog_m = re.search(r'(\d+)\s*underdog\s*edge', note_content)
            n_fav = int(fav_m.group(1)) if fav_m else 0
            n_dog = int(dog_m.group(1)) if dog_m else 0
            note_bias = 'underdog' if n_dog > n_fav else 'favorite'
            if note_bias == today_bias:
                consecutive_same_bias += 1
            else:
                break
    except Exception:
        pass

    title, body, wim, story_type = generate_market_note(
        report, prev_note_title=prev_note_title,
        consecutive_same_bias=consecutive_same_bias,
    )

    lean = report.get('market_lean') or {}
    fav = lean.get('favorites', 0)
    udog = lean.get('underdogs', 0)
    board = report.get('board', [])
    sorted_board = sorted(board, key=lambda g: abs(g.get('edge') or 0), reverse=True)

    # -- Top Edge Breakdown --
    top_edge_lines = []
    if sorted_board:
        top = sorted_board[0]
        edge_val = top.get('edge', 0)
        pick_label = top.get('pick') or top.get('pick_label') or ''
        mkt_line = top.get('market_line')
        mdl_line = top.get('model_line')
        gap = round(abs((mdl_line or 0) - (mkt_line or 0)), 1) if mdl_line is not None and mkt_line is not None else None
        status = 'Signal issued' if top.get('signal') else 'Below threshold'
        reasoning = top.get('reasoning', [])[:3]

        top_edge_lines.append(f"- pick: {pick_label}")
        top_edge_lines.append(f"- edge: +{abs(edge_val)}%")
        top_edge_lines.append(f"- matchup: {top.get('away_team', '?')} vs {top.get('home_team', '?')}")
        if mdl_line is not None:
            top_edge_lines.append(f"- model_line: {mdl_line}")
        if mkt_line is not None:
            top_edge_lines.append(f"- market_line: {mkt_line}")
        if gap is not None:
            top_edge_lines.append(f"- gap: {gap} points")
        top_edge_lines.append(f"- status: {status}")
        for r in reasoning:
            top_edge_lines.append(f"- reason: {r}")

    # -- Edge Map --
    edge_map_lines = []
    for g in sorted_board:
        edge = g.get('edge', 0) or 0
        away_abbr = _abbr(g.get('away_team', '?'))
        home_abbr = _abbr(g.get('home_team', '?'))
        if g.get('signal'):
            status = 'Signal'
        elif abs(edge) >= 2.0:
            status = 'Below threshold'
        elif edge > 0:
            status = 'Below threshold'
        else:
            status = 'No edge'
        sign = '+' if edge >= 0 else ''
        edge_map_lines.append(f"- {away_abbr} vs {home_abbr} | {sign}{edge}% | {status}")

    # -- Near Misses --
    near_miss_lines = []
    near_misses = [g for g in sorted_board if 2.0 <= abs(g.get('edge', 0) or 0) < 3.5 and not g.get('signal')]
    near_misses = near_misses[:3]
    for g in near_misses:
        edge = g.get('edge', 0) or 0
        away = g.get('away_team', '?')
        home = g.get('home_team', '?')
        reasons = g.get('fail_reasons', [])
        reason_text = reasons[0] if reasons else (g.get('reason') or 'Edge below threshold.')
        near_miss_lines.append(f"- {away} vs {home} | +{abs(edge)}% | {reason_text}")

    content_parts = [
        '## Observation',
        body,
        '',
        '## Market Structure',
        f"- Edges detected: {report.get('edges_detected', 0)}",
        f"- Signals generated: {report.get('qualified_signals', 0)}",
        f"- Signal density: {report.get('signal_density', 0)}%",
        '',
        '## Bias',
        f"Favorites vs Underdogs: {fav} favorite edges, {udog} underdog edges.",
        '',
    ]
    if top_edge_lines:
        content_parts.append('## Top Edge')
        content_parts.extend(top_edge_lines)
        content_parts.append('')
    if edge_map_lines:
        content_parts.append('## Edge Map')
        content_parts.extend(edge_map_lines)
        content_parts.append('')
    if near_miss_lines:
        content_parts.append('## Near Misses')
        content_parts.extend(near_miss_lines)
        content_parts.append('')
    content_parts.extend([
        '## Implication',
        report.get('assessment', ''),
        '',
        '## Why This Matters',
        wim,
    ])
    content = '\n'.join(content_parts)
    excerpt = body[:160] if body else title[:160]

    try:
        from zoneinfo import ZoneInfo
        et = ZoneInfo('America/New_York')
        pub = datetime.strptime(date_str, '%Y-%m-%d').replace(tzinfo=et)
    except Exception:
        pub = datetime.utcnow()

    existing = Insight.query.filter_by(slug=slug).first()
    if existing:
        existing.title = title
        existing.excerpt = excerpt
        existing.content = content
        existing.story_type = story_type
        existing.sport = sport
        existing.updated_at = datetime.utcnow()
        db.session.commit()
        return existing
    insight = Insight(
        title=title,
        slug=slug,
        category='market_notes',
        excerpt=excerpt,
        content=content,
        story_type=story_type,
        sport=sport,
        status='published',
        publish_date=pub,
        pass_day=report.get('edges_detected', 0) == 0,
    )
    db.session.add(insight)
    db.session.commit()
    return insight


from models import db, User, TrackedBet, Pick, Pass, ModelRun, FoundingCounter, Insight, ProcessedEvent, CronLog, PageView, UserEvent, AdminAlert, MrrSnapshot, KillSwitch
from picks_api import picks_bp
from public_api import public_bp
from insights_api import insights_bp
from model_service import run_model_and_log
from utils.clv import resolve_pick_side, to_picked_perspective, clv_points
from sqlalchemy import func

if is_production:
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

app.config['SESSION_COOKIE_SECURE'] = is_production
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=30)
app.config['REMEMBER_COOKIE_SECURE'] = is_production
app.config['REMEMBER_COOKIE_HTTPONLY'] = True
app.config['REMEMBER_COOKIE_SAMESITE'] = 'Lax'
app.config['REMEMBER_COOKIE_DURATION'] = timedelta(days=30)


def _database_url():
    """Resolve database URL from environment (Railway, Replit, etc.)."""
    raw = (
        os.environ.get("SQLALCHEMY_DATABASE_URI")
        or os.environ.get("DATABASE_URL")
        or os.environ.get("DATABASE_PRIVATE_URL")
        or ""
    )
    if not raw:
        return ""
    # Railway/Heroku often provide postgres:// but SQLAlchemy needs postgresql://
    if raw.startswith("postgres://"):
        raw = "postgresql://" + raw[len("postgres://") :]
    return raw


_db_url = _database_url()
if not _db_url:
    # Help debug when DB URL is missing: log which keys exist (values hidden)
    _db_keys = [k for k in os.environ if "DATABASE" in k or "SQLALCHEMY" in k]
    logging.warning(f"No database URL. DB-related env keys: {_db_keys or '(none)'}")
app.config["SQLALCHEMY_DATABASE_URI"] = _db_url
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
if _db_url and 'sqlite' in _db_url:
    app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {}
else:
    app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
        'pool_pre_ping': True,
        "pool_recycle": 300,
        "pool_size": 5,
        "max_overflow": 10,
        "pool_timeout": 20,
    }

db.init_app(app)

@app.teardown_appcontext
def shutdown_session(exception=None):
    db.session.remove()
allowed_origins = [
    'https://app.sharppicks.ai',
    'https://sharppicks.ai',
    'https://www.sharppicks.ai',
    'capacitor://localhost',
    'https://localhost',
    'http://localhost',
]
if not is_production:
    allowed_origins.append('http://localhost:5000')
    allowed_origins.append('http://0.0.0.0:5000')
    replit_domain = os.environ.get('REPLIT_DEV_DOMAIN', '')
    if replit_domain:
        allowed_origins.append(f'https://{replit_domain}')
CORS(app, supports_credentials=True, origins=allowed_origins)

login_manager = LoginManager()
login_manager.init_app(app)

@login_manager.unauthorized_handler
def handle_unauthorized():
    if request.path.startswith('/api/'):
        return jsonify({'error': 'Login required'}), 401
    return redirect('/?login=required')

@login_manager.user_loader
def load_user(user_id):
    user = _safe_get_user(user_id)
    if not user:
        return None
    # Soft-deleted users get force-logged-out on the next request.
    if not user.is_active:
        session.pop('user_id', None)
        session.pop('session_token', None)
        return None
    stored_token = session.get('session_token')
    if not stored_token or stored_token != user.session_token:
        session.pop('user_id', None)
        session.pop('session_token', None)
        return None
    return user


# Phase 3.5: track every successful login as a UserEvent so the admin
# Users tab can compute logins_30d, DAU, and cohort retention. Listening
# on Flask-Login's user_logged_in signal catches every login_user() call
# (8 sites in this file) without sprinkling tracking calls everywhere.
@user_logged_in.connect_via(app)
def _record_login_event(sender, user, **extra):
    try:
        from models import UserEvent
        # Skip force-logout events (where login_user is called for cleanup)
        # and anonymous logins (which shouldn't fire this signal anyway).
        if not user or not getattr(user, 'id', None):
            return
        ev = UserEvent(
            user_id=user.id,
            event_type='login',
            event_data={},
            session_id=session.get('session_token') or None,
            is_internal=bool(getattr(user, 'is_internal', False)),
            ip=(_events_client_ip() if '_events_client_ip' in globals() else None),
            user_agent=(request.headers.get('User-Agent') or '')[:500] if request else None,
            created_at=datetime.utcnow(),
        )
        db.session.add(ev)
        db.session.commit()
    except Exception as e:
        # Login tracking failure must never block the login itself.
        try:
            db.session.rollback()
        except Exception:
            pass
        logging.warning('login event tracking failed: %s', e)


limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["2000 per day", "500 per hour"],
    storage_uri="memory://"
)

def _get_auth_serializer():
    from itsdangerous import URLSafeTimedSerializer
    secret = os.environ.get('SESSION_SECRET', os.environ.get('SECRET_KEY', 'dev'))
    return URLSafeTimedSerializer(secret)

def generate_auth_token(user):
    s = _get_auth_serializer()
    return s.dumps({'uid': user.id, 'st': user.session_token}, salt='auth-token')

import time as _time
_oauth_nonces = {}

def _store_oauth_nonce(nonce, token):
    now = _time.time()
    _oauth_nonces[nonce] = (token, now)
    for k in list(_oauth_nonces):
        if now - _oauth_nonces[k][1] > 300:
            del _oauth_nonces[k]

def _pop_oauth_nonce(nonce):
    entry = _oauth_nonces.pop(nonce, None)
    if entry and _time.time() - entry[1] < 300:
        return entry[0]
    return None

def verify_auth_token():
    auth_header = request.headers.get('Authorization', '')
    token = None
    if auth_header.startswith('Bearer '):
        token = auth_header[7:]
    if not token:
        return None
    try:
        s = _get_auth_serializer()
        data = s.loads(token, salt='auth-token', max_age=86400 * 30)
        user = _safe_get_user(data['uid'])
        if user and user.session_token == data['st']:
            return user
    except Exception:
        pass
    return None

def _safe_get_user(user_id):
    """Get user by id, return None if table missing or error."""
    try:
        return db.session.get(User, user_id)
    except Exception as e:
        logging.warning(f"User lookup failed: {e}")
        return None


def get_current_user_from_session():
    """Get current user from session, Bearer token, or flask-login"""
    user_id = session.get('user_id')
    if user_id:
        user = _safe_get_user(user_id)
        if user:
            stored_token = session.get('session_token')
            if not stored_token or stored_token != user.session_token:
                session.pop('user_id', None)
                session.pop('session_token', None)
            else:
                return serialize_user(user)

    token_user = verify_auth_token()
    if token_user:
        return serialize_user(token_user)

    return None

def get_current_user_obj():
    """Get current user as ORM object (not dict) from session or Bearer token"""
    from flask_login import current_user as _cu
    if _cu.is_authenticated:
        return _cu

    user_id = session.get('user_id')
    if user_id:
        user = _safe_get_user(user_id)
        if user:
            stored_token = session.get('session_token')
            if stored_token and stored_token == user.session_token:
                return user

    return verify_auth_token()

def serialize_user(user):
    is_new = False
    if user.created_at:
        is_new = (datetime.now() - user.created_at).days <= 7
    return {
        'id': user.id,
        'email': user.email,
        'first_name': user.first_name or '',
        'display_name': user.first_name or user.display_name or user.username or (user.email or '').split('@')[0],
        'username': user.username,
        'is_premium': user.is_pro,
        'is_superuser': user.is_superuser and user.email == 'evan@sharppicks.ai',
        'subscription_status': user.subscription_status,
        'subscription_plan': user.subscription_plan,
        'founding_member': user.founding_member,
        'founding_number': user.founding_number,
        'unit_size': user.unit_size,
        'trial_end_date': user.trial_end_date.isoformat() if user.trial_end_date else None,
        'email_verified': user.email_verified,
        'is_new': is_new,
    }

@app.before_request
def enforce_https_and_canonical_domain():
    if request.path == '/health':
        return
    if not is_production:
        return
    host = request.host.split(':')[0].lower()
    proto = request.headers.get('X-Forwarded-Proto', request.scheme)
    needs_redirect = False
    if proto != 'https':
        needs_redirect = True
    if host.startswith('www.'):
        host = host[4:]
        needs_redirect = True
    if needs_redirect:
        target = f"https://{host}{request.full_path}"
        if target.endswith('?'):
            target = target[:-1]
        return redirect(target, code=301)

@app.before_request
def make_session_permanent():
    if request.path in ('/', '/health'):
        return
    session.permanent = True

app.register_blueprint(picks_bp, url_prefix='/api/picks')
app.register_blueprint(public_bp, url_prefix='/api/public')
app.register_blueprint(insights_bp, url_prefix='/api/insights')

from legal_pages import legal_bp
app.register_blueprint(legal_bp)

from admin_api import admin_bp
app.register_blueprint(admin_bp)

from cards_api import cards_bp
app.register_blueprint(cards_bp, url_prefix='/api/cards')

from routes.card_routes import weekly_card_bp
app.register_blueprint(weekly_card_bp)

from content_engine import content_bp
app.register_blueprint(content_bp)

@app.route('/admin')
def admin_dashboard():
    from flask import render_template
    user = get_current_user_from_session()
    if not user:
        return redirect('/login')
    db_user = db.session.get(User, user['id'])
    if not db_user or not db_user.is_superuser:
        return redirect('/')
    return render_template('admin.html', cron_secret=CRON_SECRET)

MANIFESTO_CONTENT = """When I started building SharpPicks, I wasn\u2019t trying to create another betting app. The market already has plenty of those.

Most focus on action \u2014 more picks, more volume, more reasons to bet every game on the board. But anyone who has spent real time studying sports markets eventually arrives at the same conclusion: the majority of opportunities simply aren\u2019t worth taking.

Sports betting is a market. Every spread, total, and moneyline is a price shaped by probability, information, and behavior. Like any market, it becomes efficient quickly. And when markets are efficient, edges become rare.

That reality is the foundation of SharpPicks.

The model was designed to analyze every game on the board \u2014 measuring statistical signals, market movement, and probability gaps. But identifying edges is only part of the equation. The harder part is restraint. The discipline to wait. The discipline to pass. The discipline to accept that most slates will produce very few genuine opportunities.

SharpPicks exists to enforce that discipline.

---

> **WHY THIS MATTERS**
>
> The market rewards patience. It punishes unnecessary action. The best bettors aren\u2019t defined by how many bets they make. They\u2019re defined by the bets they refuse to make. Passing on a game is not inactivity \u2014 it\u2019s risk management.

---

## Edge Is Rare

Most betting services sell the opposite philosophy. More picks. More volume. More action. But adding picks does not create value. It dilutes it.

SharpPicks was built to do the opposite: to filter aggressively, identify real statistical advantage, and ignore everything else. Selective by design.

Some days the model will generate several signals. Other days it may produce none. That isn\u2019t a flaw in the system. That **is the system**.

---

## Beat the Market, Not the Scoreboard

Short-term results in sports betting are noisy. Variance is unavoidable. Professional bettors focus on something else: **price**.

If you consistently capture better numbers than where the market closes, you\u2019re making correct decisions \u2014 regardless of individual game outcomes. Over time, the market rewards disciplined pricing decisions.

SharpPicks is built around that principle.

---

## Why SharpPicks Exists

SharpPicks isn\u2019t designed to tell you what to bet on every night. It\u2019s designed to help you understand when the market offers real opportunity \u2014 and when it doesn\u2019t.

Most bettors search for certainty. Sharp bettors search for **value**. And value only appears when patience meets preparation.

That\u2019s the philosophy behind everything we\u2019re building."""


def seed_database():
    with app.app_context():
        try:
            db.create_all()
            logging.info("Database tables created")

            try:
                db.session.execute(db.text("ALTER TABLE picks ADD COLUMN IF NOT EXISTS steam_fragility FLOAT"))
                db.session.execute(db.text("ALTER TABLE picks ADD COLUMN IF NOT EXISTS model_only_cover_prob FLOAT"))
                db.session.execute(db.text("ALTER TABLE picks ADD COLUMN IF NOT EXISTS model_only_edge FLOAT"))
                db.session.execute(db.text("ALTER TABLE picks ADD COLUMN IF NOT EXISTS model_era VARCHAR"))
                db.session.execute(db.text("ALTER TABLE model_runs ADD COLUMN IF NOT EXISTS games_detail TEXT"))
                db.session.execute(db.text("ALTER TABLE insights ADD COLUMN IF NOT EXISTS related_pick_ids JSONB DEFAULT '[]'"))
                db.session.execute(db.text("ALTER TABLE insights ADD COLUMN IF NOT EXISTS date_range_start VARCHAR"))
                db.session.execute(db.text("ALTER TABLE insights ADD COLUMN IF NOT EXISTS date_range_end VARCHAR"))
                db.session.execute(db.text("ALTER TABLE tracked_bets ADD COLUMN IF NOT EXISTS bet_type VARCHAR DEFAULT 'spread'"))
                db.session.execute(db.text("ALTER TABLE tracked_bets ADD COLUMN IF NOT EXISTS parlay_legs INTEGER"))
                db.session.execute(db.text("ALTER TABLE tracked_bets ADD COLUMN IF NOT EXISTS units_wagered FLOAT"))
                db.session.execute(db.text("ALTER TABLE tracked_bets ADD COLUMN IF NOT EXISTS settled_at TIMESTAMP"))
                db.session.execute(db.text("UPDATE tracked_bets SET settled_at = created_at WHERE settled_at IS NULL AND result IS NOT NULL"))
                db.session.execute(db.text("ALTER TABLE insights ADD COLUMN IF NOT EXISTS story_type VARCHAR"))
                db.session.execute(db.text("ALTER TABLE users ADD COLUMN IF NOT EXISTS oauth_provider VARCHAR(20)"))
                db.session.execute(db.text("ALTER TABLE users ADD COLUMN IF NOT EXISTS oauth_id VARCHAR(255)"))
                db.session.execute(db.text("ALTER TABLE watched_games ADD COLUMN IF NOT EXISTS sport VARCHAR(10) DEFAULT 'nba'"))
                db.session.execute(db.text("ALTER TABLE insights ADD COLUMN IF NOT EXISTS sport VARCHAR(10) DEFAULT 'nba'"))
                db.session.execute(db.text("ALTER TABLE users ADD COLUMN IF NOT EXISTS pro_source VARCHAR"))
                db.session.commit()
            except Exception as e:
                db.session.rollback()
                logging.warning(f"Column migration note: {e}")

            # Backfill for invoice.paid handler that used to flip $0 trial-start
            # invoices to subscription_status='active'. Idempotent — once a user's
            # trial_end_date passes, they fall out of the WHERE clause.
            try:
                result = db.session.execute(db.text(
                    "UPDATE users SET subscription_status = 'trial' "
                    "WHERE subscription_status = 'active' "
                    "AND trial_end_date IS NOT NULL "
                    "AND trial_end_date > NOW() "
                    "AND trial_converted_at IS NULL"
                ))
                if result.rowcount:
                    logging.info(f"Trial-status backfill: corrected {result.rowcount} mislabeled users")
                db.session.commit()
            except Exception as e:
                db.session.rollback()
                logging.warning(f"Trial-status backfill note: {e}")

            # One-time: dedup FCM tokens so each user keeps only the most recent
            # token per platform (fixes Safari + PWA double-notification).
            try:
                from models import FCMToken
                from sqlalchemy import func
                subq = db.session.query(
                    FCMToken.user_id, FCMToken.platform,
                    func.max(FCMToken.last_seen_at).label('latest')
                ).filter(FCMToken.enabled == True).group_by(
                    FCMToken.user_id, FCMToken.platform
                ).subquery()
                dupes = FCMToken.query.filter(
                    FCMToken.enabled == True
                ).join(subq, db.and_(
                    FCMToken.user_id == subq.c.user_id,
                    FCMToken.platform == subq.c.platform,
                    FCMToken.last_seen_at < subq.c.latest,
                )).all()
                for d in dupes:
                    d.enabled = False
                if dupes:
                    db.session.commit()
                    logging.info("[FCM] Deduped %d stale tokens", len(dupes))
            except Exception as e:
                db.session.rollback()
                logging.warning("[FCM] dedup migration note: %s", e)

            null_unit_picks = Pick.query.filter(
                Pick.result.in_(['win', 'loss']),
                Pick.profit_units.is_(None)
            ).all()
            for p in null_unit_picks:
                odds = p.market_odds or -110
                if p.result == 'win':
                    p.profit_units = round(100 / abs(odds), 2) if odds < 0 else round(odds / 100, 2)
                else:
                    p.profit_units = -1.0
                if p.pnl is not None:
                    expected_pnl = round(p.profit_units * 100, 0)
                    if abs(p.pnl - expected_pnl) > 1:
                        p.pnl = expected_pnl
            if null_unit_picks:
                db.session.commit()
                logging.info(f"Backfilled profit_units on {len(null_unit_picks)} picks")

            try:
                sconn = get_sqlite_conn()
                sconn.execute('CREATE INDEX IF NOT EXISTS idx_games_game_time ON games(game_time)')
                sconn.execute('CREATE INDEX IF NOT EXISTS idx_games_home_score ON games(home_score)')
                sconn.execute('CREATE INDEX IF NOT EXISTS idx_games_game_date ON games(game_date)')
                sconn.commit()
                sconn.close()
            except Exception:
                pass

            from werkzeug.security import generate_password_hash
            admin_accounts = [
                {'email': 'evan@sharppicks.ai', 'first_name': 'Evan', 'password': 'H@rp2019*'},
            ]
            for acct in admin_accounts:
                existing = User.query.filter_by(email=acct['email']).first()
                if not existing:
                    u = User(
                        email=acct['email'],
                        first_name=acct['first_name'],
                        password_hash=generate_password_hash(acct['password']),
                        is_superuser=True,
                        is_premium=True,
                        subscription_status='active',
                        subscription_plan='lifetime',
                        founding_member=True,
                        trial_used=True,
                        email_verified=True,
                    )
                    db.session.add(u)
                    logging.info(f"Created admin account: {acct['email']}")

            review_email = 'review@sharppicks.ai'
            if not User.query.filter_by(email=review_email).first():
                review_user = User(
                    email=review_email,
                    first_name='App Review',
                    password_hash=generate_password_hash('SharpReview2026!'),
                    is_premium=True,
                    subscription_status='active',
                    subscription_plan='annual',
                    trial_used=True,
                    email_verified=True,
                )
                db.session.add(review_user)
                logging.info("Created App Store review account: review@sharppicks.ai")

            db.session.commit()

            if Pick.query.count() == 0:
                seed_picks = [
                    Pick(id='9cc4946d-37f2-46cc-acb9-50a4c5be16c1', game_date='2026-01-27', away_team='Detroit Pistons', home_team='Denver Nuggets', side='Detroit Pistons +2.0', line=2, edge_pct=4.5, result='win', sport='nba', model_confidence=0.78, market_odds=-110, sportsbook='DraftKings', published_at=datetime(2026,2,11,18,3,52), pnl=91, profit_units=0.91, notes='Pre-Cal'),
                    Pick(id='dab82bf3-4dee-4d3e-a15e-9c3287aa7ff7', game_date='2026-01-28', away_team='San Antonio Spurs', home_team='Houston Rockets', side='San Antonio Spurs -2.5', line=-2.5, edge_pct=8.2, result='win', sport='nba', model_confidence=0.59, market_odds=-110, sportsbook='DraftKings', published_at=datetime(2026,2,11,18,3,52), pnl=91, profit_units=0.91, notes='Pre-Cal'),
                    Pick(id='e4647da5-b1e9-4d49-8f39-3e11de343ce0', game_date='2026-01-29', away_team='Houston Rockets', home_team='Atlanta Hawks', side='Houston Rockets +4.5', line=4.5, edge_pct=5.1, result='win', sport='nba', model_confidence=0.63, market_odds=-110, sportsbook='DraftKings', published_at=datetime(2026,2,11,18,3,52), pnl=91, profit_units=0.91, notes='Pre-Cal'),
                    Pick(id='f1843352-a18a-49f9-a2cf-5bc6abe50bfe', game_date='2026-01-30', away_team='Los Angeles Lakers', home_team='Washington Wizards', side='Los Angeles Lakers +5.0', line=5, edge_pct=7.7, result='win', sport='nba', model_confidence=0.64, market_odds=-110, sportsbook='DraftKings', published_at=datetime(2026,2,11,18,3,52), pnl=91, profit_units=0.91, notes='Pre-Cal'),
                    Pick(id='1520a539-73db-4f3c-aabf-086927ee9b10', game_date='2026-01-31', away_team='Chicago Bulls', home_team='Miami Heat', side='Chicago Bulls +5.0', line=5, edge_pct=5.8, result='win', sport='nba', model_confidence=0.72, market_odds=-110, sportsbook='DraftKings', published_at=datetime(2026,2,11,18,3,52), pnl=91, profit_units=0.91, notes='Pre-Cal'),
                    Pick(id='d4d15c8b-9dd2-49c0-b48b-bf8ab868a5fc', game_date='2026-02-01', away_team='LA Clippers', home_team='Phoenix Suns', side='LA Clippers +0.5', line=0.5, edge_pct=6.4, result='win', sport='nba', model_confidence=0.55, market_odds=-110, sportsbook='DraftKings', published_at=datetime(2026,2,11,18,3,52), pnl=91, profit_units=0.91, notes='Pre-Cal'),
                    Pick(id='46f93629-6df1-4644-9c9c-d3f945434ad7', game_date='2026-02-02', away_team='New Orleans Pelicans', home_team='Charlotte Hornets', side='Charlotte Hornets -8.5', line=-8.5, edge_pct=4.1, result='loss', sport='nba', model_confidence=0.7, market_odds=-110, sportsbook='DraftKings', published_at=datetime(2026,2,11,18,3,52), pnl=-100, profit_units=-1.0, notes='Pre-Cal'),
                    Pick(id='efd99ce8-b2a5-4867-92c5-0a3e16837aa2', game_date='2026-02-11', away_team='New York Knicks', home_team='Philadelphia 76ers', side='Philadelphia 76ers +24.5', line=24.5, edge_pct=10, result='loss', result_ats='loss', profit_units=-1, sport='nba', model_confidence=0.8312, market_odds=-110, sportsbook='DraftKings', published_at=datetime(2026,2,12,5,40,10), predicted_margin=-13.3, cover_prob=0.8312, implied_prob=0.5238, line_open=25.5, sigma=11.71, z_score=0.957, raw_edge=30.74, pnl=-100, notes='Line value: getting 1.0pts better number than open (+25.5 → +24.5) | Both teams on 1 day rest — no rest edge | Net rating favors New York Knicks by 0.0pts — spread accounts for this', result_resolved_at=datetime(2026,2,12,5,40,10)),
                    Pick(id='01a485ef-ab1a-4ecc-af10-9803b41c1f0f', game_date='2026-02-12', away_team='Dallas Mavericks', home_team='Los Angeles Lakers', side='Los Angeles Lakers -7.5', line=-7.5, edge_pct=10, result='win', result_ats='W', profit_units=0.88, sport='nba', model_confidence=0.8537, market_odds=-114, sportsbook='FanDuel', published_at=datetime(2026,2,12,6,22,59), predicted_margin=11.2, cover_prob=0.6238, implied_prob=0.5238, line_open=-6.5, sigma=11.71, z_score=1.053, raw_edge=32.99, home_score=124, away_score=104, pnl=88, notes='Back-to-back for both teams — no rest edge|Scoring margin edge: Los Angeles Lakers outscores opponents by 9.4pts more per game|Defensive mismatch: Dallas Mavericks allows 122.8pts/game', result_resolved_at=datetime(2026,2,13,8,28,18)),
                ]
                for p in seed_picks:
                    db.session.add(p)
                logging.info("Seeded historical picks")

            live_pick_id = 'c9284c80-a253-4d94-bd17-5462da685983'
            if not Pick.query.get(live_pick_id):
                live_pick = Pick(
                    id=live_pick_id,
                    game_date='2026-02-19', sport='nba',
                    away_team='Indiana Pacers', home_team='Washington Wizards',
                    side='Washington Wizards +4.5', line=4.5,
                    edge_pct=5.5, model_confidence=0.5768,
                    predicted_margin=-2.2, cover_prob=0.5768,
                    implied_prob=0.5215, market_odds=-109,
                    sportsbook='BetRivers', result='pending',
                    published_at=datetime(2026, 2, 18, 15, 15, 33),
                    start_time='2026-02-20T00:00:00Z',
                    sigma=11.71, z_score=0.194, raw_edge=5.52,
                    line_open=4.5, position_size_pct=100,
                    notes='Washington Wizards averaging 113.2pts vs defense allowing 117.8 | Line stable since open (+4.5), market agrees with number | Both teams on 5d rest — no rest edge',
                )
                db.session.add(live_pick)
                db.session.commit()
                logging.info("Inserted live pick for 2026-02-19")

            if Pass.query.count() == 0:
                seed_passes = [
                    Pass(id='83a0e6e0-e0f4-4a6f-a871-3f2e356b96af', date='2026-01-13', sport='nba', games_analyzed=8, closest_edge_pct=1.2),
                    Pass(id='c0088299-dfc8-4f02-b9ae-d4701af35673', date='2026-01-14', sport='nba', games_analyzed=12, closest_edge_pct=1.4),
                    Pass(id='9be86b12-2672-4649-a313-ab26769a6312', date='2026-01-15', sport='nba', games_analyzed=6, closest_edge_pct=1.2),
                    Pass(id='da849ee8-129c-4833-ac2c-c283ac853d69', date='2026-01-16', sport='nba', games_analyzed=8, closest_edge_pct=1.1),
                    Pass(id='802a7c74-c96c-4b23-a3f5-dc5b8e59291a', date='2026-01-17', sport='nba', games_analyzed=9, closest_edge_pct=1.3),
                    Pass(id='7360d4ec-8abb-47d1-9382-01f834699139', date='2026-01-18', sport='nba', games_analyzed=9, closest_edge_pct=3.0),
                    Pass(id='43f3d02b-d468-4561-8ed5-105d13be6f57', date='2026-01-19', sport='nba', games_analyzed=10, closest_edge_pct=2.3),
                    Pass(id='73ed3b01-0ecd-44e8-a94e-d75b7aadb5a5', date='2026-01-20', sport='nba', games_analyzed=9, closest_edge_pct=1.2),
                    Pass(id='b54ef4a0-ec7b-4dd9-b7e0-fb1fcf7a8c65', date='2026-01-21', sport='nba', games_analyzed=14, closest_edge_pct=3.2),
                    Pass(id='5bd51e86-a9dd-48b9-a42d-a59d5b193281', date='2026-01-22', sport='nba', games_analyzed=8, closest_edge_pct=1.4),
                    Pass(id='c94592cd-a89c-4ba9-8246-a2ddaae3d63d', date='2026-01-23', sport='nba', games_analyzed=14, closest_edge_pct=3.1),
                    Pass(id='f45ea327-be03-4376-be7a-044415d3278b', date='2026-01-24', sport='nba', games_analyzed=13, closest_edge_pct=3.3),
                    Pass(id='897e4311-1c04-423a-bb61-015e64d28228', date='2026-01-25', sport='nba', games_analyzed=9, closest_edge_pct=3.4),
                    Pass(id='0c4a45f0-f1d0-45b2-b4db-84d3d22b38f3', date='2026-01-26', sport='nba', games_analyzed=14, closest_edge_pct=3.1),
                    Pass(id='e7e4ad18-716b-4caf-a370-f9501e05931a', date='2026-02-03', sport='nba', games_analyzed=10, closest_edge_pct=3.1),
                    Pass(id='fb6aaf8f-3f83-44ac-8396-1ece90a25600', date='2026-02-04', sport='nba', games_analyzed=7, closest_edge_pct=2.0),
                    Pass(id='0ce580a2-2a84-42d8-902c-53aa1c89bba2', date='2026-02-05', sport='nba', games_analyzed=9, closest_edge_pct=1.1),
                    Pass(id='8a5d6845-a830-4950-b6de-bed7e9e0977d', date='2026-02-06', sport='nba', games_analyzed=11, closest_edge_pct=1.7),
                    Pass(id='ad56c370-6846-4a8d-b381-3ed30bd5b28e', date='2026-02-07', sport='nba', games_analyzed=10, closest_edge_pct=1.8),
                    Pass(id='419ec2b6-4bd4-4e01-a21d-afdaae73bbbb', date='2026-02-08', sport='nba', games_analyzed=6, closest_edge_pct=2.8),
                    Pass(id='8f65db6b-d784-46eb-8a67-dd522ef585f2', date='2026-02-09', sport='nba', games_analyzed=9, closest_edge_pct=1.7),
                    Pass(id='afb6703a-1cbd-45b1-9acd-e1f3885c252b', date='2026-02-10', sport='nba', games_analyzed=10, closest_edge_pct=1.6),
                    Pass(id='2e210a25-2f55-4c89-8737-208f81230212', date='2026-02-11', sport='nba', games_analyzed=12, closest_edge_pct=1.7),
                ]
                for p in seed_passes:
                    db.session.add(p)
                logging.info("Seeded historical passes")
            db.session.commit()

            counter = FoundingCounter.query.first()
            if not counter:
                counter = FoundingCounter(current_count=0, closed=False)
                db.session.add(counter)
                db.session.commit()
            existing_manifesto = Insight.query.filter_by(slug='the-sharp-manifesto').first()
            if existing_manifesto:
                existing_manifesto.content = MANIFESTO_CONTENT
            else:
                manifesto = Insight(
                    title="The Sharp Manifesto",
                    slug="the-sharp-manifesto",
                    category="philosophy",
                    excerpt="When I started building SharpPicks, I wasn't trying to create another betting app. The market already has plenty of those.",
                    content=MANIFESTO_CONTENT,
                    status="published",
                    publish_date=datetime(2026, 2, 1),
                    featured=True,
                    pass_day=True,
                    reading_time_minutes=5,
                )
                db.session.add(manifesto)
                old_featured = Insight.query.filter_by(slug='why-one-pick-beats-five').first()
                if old_featured:
                    old_featured.featured = False
                db.session.commit()

            if Insight.query.count() == 0:
                seed_insights = [
                    Insight(
                        title="The Sharp Manifesto",
                        slug="the-sharp-manifesto",
                        category="philosophy",
                        excerpt="When I started building SharpPicks, I wasn't trying to create another betting app. The market already has plenty of those.",
                        content=MANIFESTO_CONTENT,
                        status="published",
                        publish_date=datetime(2026, 2, 1),
                        featured=True,
                        pass_day=True,
                        reading_time_minutes=5,
                    ),
                    Insight(
                        title="Why One Pick Beats Five",
                        slug="why-one-pick-beats-five",
                        category="philosophy",
                        excerpt="Most bettors lose not because they pick wrong, but because they pick too often. Volume is the enemy of edge.",
                        content="""Most bettors lose not because they pick wrong, but because they pick too often. Volume is the enemy of edge.

---

## The Math of Selectivity

A bettor who wagers on five games per day needs to hit at a rate that overcomes the vig on every single bet. At standard -110 odds, you need 52.4% accuracy just to break even. Across five daily bets, the compounding effect of juice makes profitability nearly impossible.

A single, carefully selected wager changes the equation entirely. When our model identifies a genuine 3.5% or greater edge, the expected value calculation shifts dramatically in your favor.

---

## Why Silence Is the Product

On days we publish no pick, the system is working exactly as designed. We analyzed every game on the board and found no edge worth risking your bankroll on. That restraint is what separates professional-grade analysis from entertainment content.

> The best trade is often the one you don't make.

---

## What the Data Shows

Over 12 seasons of backtesting, our model achieved a 68.6% win rate against the spread with a +30.9% ROI. That performance is inseparable from the discipline of only acting when the edge is clear.

Adding more picks to chase action would dilute that edge to the point of disappearance. One quality pick, backed by genuine statistical advantage, is the foundation of long-term profitability.""",
                        status="published",
                        publish_date=datetime(2026, 2, 10),
                        featured=False,
                        pass_day=True,
                        reading_time_minutes=3,
                    ),
                    Insight(
                        title="Understanding the Spread",
                        slug="understanding-the-spread",
                        category="how_it_works",
                        excerpt="Point spreads are not predictions. They are prices. Understanding this distinction is the first step toward thinking like a sharp.",
                        content="""Point spreads are not predictions. They are prices. Understanding this distinction is the first step toward thinking like a sharp.

---

## Spreads as Market Prices

When you see Lakers -4.5, the sportsbook is not saying the Lakers will win by 4.5 points. They are setting a price that balances action on both sides. The spread reflects the collective opinion of the betting market, weighted heavily by the sharpest money.

---

## Why We Compare to the Market

Our model generates an independent prediction of the expected margin. But we do not blindly trust our model. We blend our prediction with the market spread using a 30/70 ratio, giving 70% weight to the market and 30% to our model.

Why? Because the market aggregates the opinions of thousands of sharp bettors and sophisticated models. Our out-of-sample testing shows the market spread is more accurate than our model about 60% of the time.

---

## Where Our Edge Lives

Our edge does not come from being smarter than the entire market. It comes from identifying the specific games where our model disagrees with the market enough to suggest a genuine mispricing.

> We do not need to be right more often than the market. We need to be right more often than the spread price implies.

When our blended prediction diverges from the market spread by 3.5% or more, that is a signal worth acting on. Anything less, and we pass.""",
                        status="published",
                        publish_date=datetime(2026, 2, 11),
                        reading_time_minutes=3,
                    ),
                    Insight(
                        title="How to Read the Model Dashboard",
                        slug="how-to-read-the-model-dashboard",
                        category="founder_note",
                        excerpt="The right question is not whether performance is up. The right question is whether the model is behaving the way it is supposed to.",
                        content="""Most people look at performance and ask one question:

"Is it up?"

That is the wrong question.

The right question is: Is it behaving the way it is supposed to?

SharpPicks is built on probability, not streaks. So here is how to read the model dashboard the right way.

---

## ROI and Record

ROI tells you efficiency. Record tells you direction.

A 7-2 record looks great. But what matters is whether the wins came from edges the model expected to win.

Short samples are noisy. Edge quality is signal.

Focus on process over streak.

---

## Calibration Buckets

This is the most important section on the entire dashboard.

Each bucket represents games grouped by projected win probability.

If the model says a play wins 58% of the time, over the long run it should win roughly 58%.

Calibration tells us if reality matches expectation. If it does, the model is honest. If it does not, we adjust.

> One hot streak does not prove a model. Accurate calibration does.

---

## Selectivity

You will see total picks vs passes.

Passing is not inactivity. Passing is filtration.

The average betting product pushes volume. We push restraint.

Selectivity protects capital.

---

## Risk Profile

Max drawdown. Average days between picks. Average edge published.

These are not vanity metrics. They tell you what kind of volatility to expect.

If risk increases, conviction must increase. That principle shows up here.

---

## What This Dashboard Is Not

It is not a highlight reel. It is not marketing.

It is a transparency tool.

The goal is not to look impressive. The goal is to behave consistently.

That is how models compound.""",
                        status="published",
                        publish_date=datetime(2026, 2, 14),
                        reading_time_minutes=4,
                    ),
                    Insight(
                        title="Understanding Your Results vs The Model",
                        slug="understanding-your-results-vs-the-model",
                        category="founder_note",
                        excerpt="There are two dashboards for a reason. The model has a job. You have a job. The difference is where long term edge is built.",
                        content="""There are two dashboards for a reason.

The model has a job. You have a job.

The difference between the two is where long term edge is built.

---

## Model Results

This shows standardized 1u performance.

Every pick graded the same. No emotion. No stake sizing.

This is pure signal.

It answers one question: Does the edge exist?

---

## Your Results

This is your real capital.

Your actual stakes. Your timing. Your restraint.

This dashboard answers a different question: Are you executing correctly?

You can beat the model. You can underperform the model.

> Execution is not optional. It is the edge.

---

## Behavioral Edge

This is the section most bettors ignore.

Selectivity rate. Days per bet. Capital preserved from passes.

Most bettors lose because they overextend.

If you bet on 56% of opportunities and the industry average is 78%, you are already gaining edge before the game tips.

Discipline compounds. Impulse erodes.

---

## Capital Preserved

This is one of my favorite metrics.

Money saved by not betting low conviction plays.

Winning is not just about what you bet. It is about what you do not.

---

## The Real Goal

The goal is not to copy the model blindly.

The goal is alignment.

When your behavior matches the edge structure, variance becomes tolerable.

That is how professionals think.

Fewer decisions. Better decisions.""",
                        status="published",
                        publish_date=datetime(2026, 2, 14),
                        reading_time_minutes=4,
                    ),
                    Insight(
                        title="When the Edge Disappears Before Tip-Off",
                        slug="when-the-edge-disappears-before-tipoff",
                        category="market_notes",
                        excerpt="A pick published at noon isn't the same pick at 7 PM. Here's why we check again before every game.",
                        content="""A pick published at noon isn't the same pick at 7 PM. Here's why we check again before every game.

---

## Edge Is a Snapshot, Not a Guarantee

When we publish a pick, we've identified a gap between what our model believes and what the market is pricing. That gap is real at the moment we find it.

But markets move. Sharp money comes in. Books adjust. A line that opened at +4 might close at +2.5. The edge you saw at noon can shrink, shift, or disappear entirely by tip-off.

Most services publish and forget. We don't.

---

## What Revalidation Means

Two to three hours before every game, our system runs the pick again. Same model. Current lines. Current injury reports.

We're asking one question: is the edge still there?

If the answer is yes, nothing changes. The pick stands.

If the edge has decayed below our minimum threshold, we withdraw the pick before anyone bets into a number that no longer has value.

---

## Why This Protects You

A pick published at 7.6% edge that's now sitting at 1.2% is a different bet. The original thesis — that the market was mispricing this game — may no longer be true. The market has corrected, and following the pick now means betting into an efficient price.

The withdrawal isn't a failure. It's the system working.

---

## The Line Move Signal

When a line moves significantly against our pick — two or more points — that's information. It means sharp money landed on the other side. Our model may have identified something real, but so did someone else, and they bet it hard enough to move the market.

In that case, we stop. Not because we're wrong, but because we can no longer quantify the advantage with confidence.

---

> A pick you don't make costs nothing. A pick you make into a bad number costs real money.

---

You'll occasionally see a pick disappear before game time. Now you know why. The withdrawal is the product working as designed.

*Evan*""",
                        status="published",
                        publish_date=datetime(2026, 2, 21),
                        reading_time_minutes=3,
                    ),
                    Insight(
                        title="What CLV Actually Tells You",
                        slug="what-clv-actually-tells-you",
                        category="how_it_works",
                        excerpt="Most bettors judge a pick by whether it won or lost. Sharps judge it by something more important: where the line moved after they bet.",
                        content="""Most bettors judge a pick by whether it won or lost. Sharps judge it by something more important: where the line moved after they bet.

---

## Closing Line Value — What It Is

When you place a bet, the market is still open. Books continue taking action, adjusting their lines based on where the sharp money flows. The line that exists at game time — the closing line — reflects the most efficient, information-rich price the market has to offer.

If you bet a team at -3 and the line closes at -4.5, you got the better of the market. That's closing line value. You beat the closing number by a full point and a half. The outcome of the game is almost irrelevant.

---

## Why Outcomes Are Noise

A bet can win and still have been a bad bet. A bet can lose and still have been the right call. Over a small sample — ten picks, twenty picks — variance dominates. The winning percentage tells you almost nothing about whether your process is sound.

CLV cuts through the noise. Consistently beating the closing line means you're identifying edges before the market prices them in. That's not luck. That's the definition of an information advantage.

> **WHY THIS MATTERS**
> *If you consistently get the better of the closing number, the wins will follow. Focus on the process, not the outcome.*

---

## How We Use It

Every pick SharpPicks publishes is logged against its closing line. It's one of the primary ways we validate that the model is doing what it's supposed to do — finding real edges, not manufactured ones. A model that beats closing lines at scale is a model that works. Everything else is storytelling.

The scoreboard matters. But CLV is how we know whether we deserve the score.

*Evan*""",
                        status="published",
                        publish_date=datetime(2026, 2, 25),
                        featured=False,
                        pass_day=False,
                        reading_time_minutes=3,
                    ),
                    Insight(
                        title="Why the Model Beats Your Gut",
                        slug="why-the-model-beats-your-gut",
                        category="philosophy",
                        excerpt="Your instincts are not your enemy. But in sports betting, they are almost certainly costing you money.",
                        content="""Your instincts are not your enemy. But in sports betting, they are almost certainly costing you money.

---

## The Problem With Pattern Recognition

The human brain is exceptional at finding patterns. It's also exceptional at finding patterns that don't exist. We remember the game we called perfectly. We forget the six we called wrong. We feel confident after a win and cautious after a loss — precisely the opposite of how edge works.

This isn't a character flaw. It's how cognition operates. Recency bias, availability bias, the hot hand fallacy — these aren't things you can simply decide to stop doing. They're structural features of human judgment.

---

## What a Model Doesn't Have

Our ensemble model — trained on twelve seasons of NBA data across 56 features — has no memory of last night's game. It doesn't know that a team looked sharp in warmups or that a star player had a bad interview this week. It doesn't care about narratives.

It processes the same inputs in the same way every single time. It doesn't get frustrated after a losing week. It doesn't press after a cold stretch. It doesn't get overconfident when it's running hot.

> **WHY THIS MATTERS**
> *The model's greatest advantage isn't what it knows. It's what it ignores.*

---

## Where Gut Belongs

Intuition built from genuine expertise has real value — in reading situations the data doesn't capture, in knowing when to trust a number and when to question it. That's why a human is still part of this process.

But when it comes to deciding whether a statistical edge exists and whether it clears the threshold worth acting on, the model wins that argument every time. Not because machines are smarter than people. Because they're more consistent.

Consistency, compounded over hundreds of decisions, is where edge lives.

*Evan*""",
                        status="scheduled",
                        publish_date=datetime(2026, 2, 27),
                        featured=False,
                        pass_day=False,
                        reading_time_minutes=3,
                    ),
                    Insight(
                        title="What to Do During a Losing Streak",
                        slug="what-to-do-during-a-losing-streak",
                        category="discipline",
                        excerpt="Losing streaks happen. They happen to disciplined bettors. They happen to sharp models. What you do inside one determines everything.",
                        content="""Losing streaks happen. They happen to disciplined bettors. They happen to sharp models. They will happen to you. What you do inside one determines everything.

---

## The First Thing to Understand

Even a model with a 68% win rate will lose four in a row. The math guarantees it. Over a long enough sample, strings of losses aren't aberrations — they're expected features of any probabilistic system. A losing week doesn't mean the edge is gone. It may mean the edge is simply waiting.

The mistake most bettors make isn't losing. It's what losing makes them do.

---

## The Three Temptations

The first is chasing — increasing bet size to recover losses faster. This is how accounts get blown. The edge, if it exists, works through volume over time. Compressing that timeline by adding size during a losing stretch is how you turn a recoverable drawdown into a catastrophic one.

The second is abandoning process — suddenly second-guessing the model, adding gut-feel overlays, deciding that a different approach is needed. This is how you destroy the consistency that makes the edge real.

The third is quitting — walking away convinced the system doesn't work after a sample too small to mean anything. Most bettors quit their best strategies just before they would have inflected.

> **WHY THIS MATTERS**
> *The streak is not information. Your response to the streak is the only variable that matters.*

---

## What Sharp Discipline Looks Like

You hold the unit size. You trust the model's threshold. You don't publish a pick because you need a win — you publish it because the edge is there. And when there's no edge, you pass. Especially when you're losing.

The discipline that protects your bankroll on good days is the same discipline that rebuilds it on bad ones. It doesn't change based on recent results. That's the whole point.

*Evan*""",
                        status="scheduled",
                        publish_date=datetime(2026, 3, 1),
                        featured=False,
                        pass_day=False,
                        reading_time_minutes=3,
                    ),
                ]
                for ins in seed_insights:
                    db.session.add(ins)
                db.session.commit()
                logging.info("Seeded 8 initial insights")

            existing_slugs = {i.slug for i in Insight.query.with_entities(Insight.slug).all()}
            incremental_insights = []
            if 'what-clv-actually-tells-you' not in existing_slugs:
                incremental_insights.append(Insight(
                    title="What CLV Actually Tells You", slug="what-clv-actually-tells-you",
                    category="how_it_works",
                    excerpt="Most bettors judge a pick by whether it won or lost. Sharps judge it by something more important: where the line moved after they bet.",
                    content="""Most bettors judge a pick by whether it won or lost. Sharps judge it by something more important: where the line moved after they bet.

---

## Closing Line Value — What It Is

When you place a bet, the market is still open. Books continue taking action, adjusting their lines based on where the sharp money flows. The line that exists at game time — the closing line — reflects the most efficient, information-rich price the market has to offer.

If you bet a team at -3 and the line closes at -4.5, you got the better of the market. That's closing line value. You beat the closing number by a full point and a half. The outcome of the game is almost irrelevant.

---

## Why Outcomes Are Noise

A bet can win and still have been a bad bet. A bet can lose and still have been the right call. Over a small sample — ten picks, twenty picks — variance dominates. The winning percentage tells you almost nothing about whether your process is sound.

CLV cuts through the noise. Consistently beating the closing line means you're identifying edges before the market prices them in. That's not luck. That's the definition of an information advantage.

> **WHY THIS MATTERS**
> *If you consistently get the better of the closing number, the wins will follow. Focus on the process, not the outcome.*

---

## How We Use It

Every pick SharpPicks publishes is logged against its closing line. It's one of the primary ways we validate that the model is doing what it's supposed to do — finding real edges, not manufactured ones. A model that beats closing lines at scale is a model that works. Everything else is storytelling.

The scoreboard matters. But CLV is how we know whether we deserve the score.

*Evan*""",
                    status="published", publish_date=datetime(2026, 2, 25), reading_time_minutes=3,
                ))
            if 'why-the-model-beats-your-gut' not in existing_slugs:
                incremental_insights.append(Insight(
                    title="Why the Model Beats Your Gut", slug="why-the-model-beats-your-gut",
                    category="philosophy",
                    excerpt="Your instincts are not your enemy. But in sports betting, they are almost certainly costing you money.",
                    content="""Your instincts are not your enemy. But in sports betting, they are almost certainly costing you money.

---

## The Problem With Pattern Recognition

The human brain is exceptional at finding patterns. It's also exceptional at finding patterns that don't exist. We remember the game we called perfectly. We forget the six we called wrong. We feel confident after a win and cautious after a loss — precisely the opposite of how edge works.

This isn't a character flaw. It's how cognition operates. Recency bias, availability bias, the hot hand fallacy — these aren't things you can simply decide to stop doing. They're structural features of human judgment.

---

## What a Model Doesn't Have

Our ensemble model — trained on twelve seasons of NBA data across 56 features — has no memory of last night's game. It doesn't know that a team looked sharp in warmups or that a star player had a bad interview this week. It doesn't care about narratives.

It processes the same inputs in the same way every single time. It doesn't get frustrated after a losing week. It doesn't press after a cold stretch. It doesn't get overconfident when it's running hot.

> **WHY THIS MATTERS**
> *The model's greatest advantage isn't what it knows. It's what it ignores.*

---

## Where Gut Belongs

Intuition built from genuine expertise has real value — in reading situations the data doesn't capture, in knowing when to trust a number and when to question it. That's why a human is still part of this process.

But when it comes to deciding whether a statistical edge exists and whether it clears the threshold worth acting on, the model wins that argument every time. Not because machines are smarter than people. Because they're more consistent.

Consistency, compounded over hundreds of decisions, is where edge lives.

*Evan*""",
                    status="scheduled", publish_date=datetime(2026, 2, 27), reading_time_minutes=3,
                ))
            if 'what-to-do-during-a-losing-streak' not in existing_slugs:
                incremental_insights.append(Insight(
                    title="What to Do During a Losing Streak", slug="what-to-do-during-a-losing-streak",
                    category="discipline",
                    excerpt="Losing streaks happen. They happen to disciplined bettors. They happen to sharp models. What you do inside one determines everything.",
                    content="""Losing streaks happen. They happen to disciplined bettors. They happen to sharp models. They will happen to you. What you do inside one determines everything.

---

## The First Thing to Understand

Even a model with a 68% win rate will lose four in a row. The math guarantees it. Over a long enough sample, strings of losses aren't aberrations — they're expected features of any probabilistic system. A losing week doesn't mean the edge is gone. It may mean the edge is simply waiting.

The mistake most bettors make isn't losing. It's what losing makes them do.

---

## The Three Temptations

The first is chasing — increasing bet size to recover losses faster. This is how accounts get blown. The edge, if it exists, works through volume over time. Compressing that timeline by adding size during a losing stretch is how you turn a recoverable drawdown into a catastrophic one.

The second is abandoning process — suddenly second-guessing the model, adding gut-feel overlays, deciding that a different approach is needed. This is how you destroy the consistency that makes the edge real.

The third is quitting — walking away convinced the system doesn't work after a sample too small to mean anything. Most bettors quit their best strategies just before they would have inflected.

> **WHY THIS MATTERS**
> *The streak is not information. Your response to the streak is the only variable that matters.*

---

## What Sharp Discipline Looks Like

You hold the unit size. You trust the model's threshold. You don't publish a pick because you need a win — you publish it because the edge is there. And when there's no edge, you pass. Especially when you're losing.

The discipline that protects your bankroll on good days is the same discipline that rebuilds it on bad ones. It doesn't change based on recent results. That's the whole point.

*Evan*""",
                    status="scheduled", publish_date=datetime(2026, 3, 1), reading_time_minutes=3,
                ))
            if 'the-bet-you-didnt-place' not in existing_slugs:
                incremental_insights.append(Insight(
                    title="The Bet You Didn\u2019t Place Is the One That Matters",
                    slug="the-bet-you-didnt-place",
                    category="philosophy",
                    excerpt="Most betting services sell you volume. Ten picks a day. Twenty. A full card for every slate. The implicit promise is simple: more picks, more chances to win. That math is wrong.",
                    content="""Most betting services sell you volume. Ten picks a day. Twenty. A full card for every slate. The implicit promise is simple: more picks, more chances to win.

That math is wrong.

---

## The Volume Trap

Every pick you place carries risk. That part is obvious. What\u2019s less obvious is that bad picks don\u2019t just lose money \u2014 they erode the edge from your good ones.

A model with a genuine 4% edge on one game and no edge on four others doesn\u2019t produce a five-pick day. It produces a one-pick day. Padding the card with low-conviction plays doesn\u2019t diversify your risk. It dilutes your signal.

This is the difference between activity and discipline. And discipline is the one the market doesn\u2019t reward in the short term.

---

## Why Services Sell Volume

The incentive structure of the picks industry is broken. Subscription services need engagement. Engagement means content. Content means picks \u2014 as many as possible, as often as possible.

A service that says \u201cno pick today\u201d looks like it\u2019s not working. A service that fires ten picks looks busy, confident, involved. But busy isn\u2019t sharp. Busy is noise dressed up as conviction.

The tout model rewards the appearance of effort. The sharp model rewards the absence of it.

> **Most of our value comes from the days we don\u2019t publish. If it\u2019s not sharp, it\u2019s not sent.**

---

## What Our Threshold Actually Does

SharpPicks publishes at most one pick per day. Some days, zero. The ensemble model evaluates every game on the board. If nothing clears a 3.5% expected edge, the system stays silent.

That silence isn\u2019t a failure. It\u2019s the system working exactly as designed. It means the market is priced efficiently that night, and there\u2019s nothing worth risking capital on.

Over a long enough sample, the nights you sit out contribute just as much to your ROI as the nights you fire.

> **WHY THIS MATTERS**
>
> This principle defines the product. SharpPicks will never pad your card to justify a subscription. If the edge isn\u2019t there, you\u2019ll hear nothing. That\u2019s the point.

*Evan Cole*
Head of Signal Intelligence, SharpPicks""",
                    status="scheduled", publish_date=datetime(2026, 3, 8), reading_time_minutes=3,
                ))
            if 'what-56-features-actually-means' not in existing_slugs:
                incremental_insights.append(Insight(
                    title="What 56 Features Actually Means",
                    slug="what-56-features-actually-means",
                    category="how_it_works",
                    excerpt="People hear \u201cmachine learning model\u201d and picture a black box. Data goes in, picks come out, nobody knows why. That\u2019s not how SharpPicks works.",
                    content="""People hear \u201cmachine learning model\u201d and picture a black box. Data goes in, picks come out, nobody knows why. That\u2019s not how SharpPicks works. And it\u2019s not how any model you trust with real money should work.

---

## The Inputs

Our ensemble runs on 56 features per game. That sounds like a lot, but it\u2019s less about quantity and more about what we chose to include \u2014 and what we deliberately left out.

The features span team efficiency metrics, pace and rest adjustments, recent form windows, home-court dynamics, and market-derived signals. Each one was selected because it showed predictive value across twelve seasons of NBA data, not because it told a good story.

We don\u2019t include features just because they feel important. \u201cStar player returned from injury\u201d might make a great narrative on ESPN. But if the data shows that variable doesn\u2019t reliably predict spread outcomes at a statistically significant level, it doesn\u2019t make the cut.

---

## The Ensemble

A single model has blind spots. A gradient boosting model might overfit to certain game profiles. A random forest might smooth over edges that matter. That\u2019s why SharpPicks doesn\u2019t rely on one model.

The ensemble combines four algorithms \u2014 Gradient Boosting, Random Forest, XGBoost, and AdaBoost \u2014 each trained on the same feature set but learning different patterns in the data. Their outputs are calibrated and blended with a 30/70 model-to-market weight.

That 30/70 split is intentional. The market is smart. Oddsmakers with billion-dollar operations set efficient lines. Our model doesn\u2019t try to ignore the market \u2014 it uses the market as a baseline and looks for spots where our signal diverges enough to act.

> **We don\u2019t bet against the market. We look for the moments the market hasn\u2019t finished its homework.**

---

## Why Calibration Matters More Than Accuracy

Raw prediction accuracy is a vanity metric. A model that picks winners 55% of the time sounds impressive until you realize the lines were -200 favorites.

What matters is calibration \u2014 does the model\u2019s probability output match reality? When our model says a team has a 58% chance of covering, do they actually cover 58% of the time across a large sample?

Calibrated probabilities are what allow us to calculate true expected value. And expected value is the only thing that separates sharp betting from educated guessing.

> **WHY THIS MATTERS**
>
> Transparency isn\u2019t a marketing angle. It\u2019s how you evaluate whether a model deserves your trust. If a service can\u2019t explain what drives its picks, that\u2019s not sophistication \u2014 it\u2019s a red flag.

*Evan Cole*
Head of Signal Intelligence, SharpPicks""",
                    status="scheduled", publish_date=datetime(2026, 3, 12), reading_time_minutes=3,
                ))
            if 'you-will-lose-five-in-a-row' not in existing_slugs:
                incremental_insights.append(Insight(
                    title="You Will Lose Five in a Row. Here\u2019s Why That\u2019s Fine.",
                    slug="you-will-lose-five-in-a-row",
                    category="discipline",
                    excerpt="If you bet long enough with any edge \u2014 even a real, verified, positive-EV edge \u2014 you will hit a losing streak that makes you question everything. This isn\u2019t a possibility. It\u2019s a mathematical certainty.",
                    content="""If you bet long enough with any edge \u2014 even a real, verified, positive-EV edge \u2014 you will hit a losing streak that makes you question everything. Five in a row. Seven. Maybe more.

This isn\u2019t a possibility. It\u2019s a mathematical certainty.

---

## The Math Nobody Wants to Hear

A model with a 57% hit rate on spread picks \u2014 which would be elite \u2014 still has roughly a 15% chance of losing five straight at any given point in a season. Over a full NBA calendar, that five-game skid isn\u2019t just possible. It\u2019s expected.

Zoom out further. In any 200-pick sample, you should expect at least one stretch of seven or more consecutive losses. Not because the model broke. Because that\u2019s what 57% looks like over a long series.

The human brain is terrible at accepting this. We experience five losses and start looking for a reason: the model is broken, the features are stale, the market shifted. Sometimes one of those things is true. Most of the time, it\u2019s just variance doing what variance does.

---

## The Danger Zone

The real damage from a losing streak isn\u2019t financial. It\u2019s behavioral.

Bettors in a drawdown do predictable things: they increase unit size to \u201cmake it back,\u201d they override the model with gut picks, they chase action on games the model didn\u2019t flag. Every one of these reactions converts a temporary drawdown into a permanent one.

The model doesn\u2019t feel the streak. It evaluates the next game with the same dispassion it brought to the first. That\u2019s not a limitation \u2014 it\u2019s the entire advantage.

> **A losing streak doesn\u2019t mean the edge is gone. It means you\u2019re finally seeing what edge actually looks like over a real sample.**

---

## What We Do During a Streak

Nothing different. That\u2019s the answer.

The threshold doesn\u2019t change. The unit sizing doesn\u2019t change. The model doesn\u2019t get \u201cmore aggressive\u201d to recover losses. There\u2019s no revenge trade, no double-down night, no \u201clock of the year\u201d to dig out of a hole.

If the model sees an edge above threshold, it fires. If it doesn\u2019t, it stays quiet. The process is the same on night one and night fifty, whether we\u2019re up twelve units or down four.

This is easy to say and brutally hard to do. But it\u2019s the only way compounding edge works.

> **WHY THIS MATTERS**
>
> SharpPicks was built to remove you from the decision loop during the moments when human judgment is at its worst. The streak is temporary. The process is permanent.

*Evan Cole*
Head of Signal Intelligence, SharpPicks""",
                    status="scheduled", publish_date=datetime(2026, 3, 17), reading_time_minutes=3,
                ))
            if 'the-line-moved-now-what' not in existing_slugs:
                incremental_insights.append(Insight(
                    title="The Line Moved. Now What?",
                    slug="the-line-moved-now-what",
                    category="market_notes",
                    excerpt="You see the model fire a pick at 1 PM. Spread is -3.5. By tip-off, it\u2019s -5. The pick is the same, but the bet isn\u2019t. Most people don\u2019t understand why.",
                    content="""You see the model fire a pick at 1 PM. Spread is -3.5. By tip-off, it\u2019s -5. The pick is the same, but the bet isn\u2019t. Most people don\u2019t understand why.

---

## Lines Are Living Things

An opening line is a hypothesis. The sportsbook posts a number, and the market reacts. Sharp money moves first. Public money follows. Injuries get reported. Rotation updates hit Twitter. Each piece of information pushes the number toward its true resting point.

By the time you place your bet, the line in front of you might be meaningfully different from the line the model evaluated. And that difference matters more than most bettors realize.

---

## The CLV Problem

Closing Line Value \u2014 the difference between the line when you bet and the line at close \u2014 is the single most reliable indicator of long-term betting skill. Not win rate. Not units won over a week. CLV.

If you consistently bet spreads before they move in the direction of your pick, you\u2019re capturing value. If you consistently bet after they move past you, you\u2019re giving it back.

This is why timing matters. Not in a \u201cgut feel\u201d way, but in a structural way. A pick at -3.5 with a model probability calibrated to that number is a different bet than the same pick at -5. The expected value changed. The edge may have evaporated entirely.

> **The pick didn\u2019t change. The price did. And in this game, price is everything.**

---

## Why We Re-evaluate Before Every Game

SharpPicks checks the current line against the model\u2019s edge calculation before every tip-off. If the line has moved enough to push the expected edge below our threshold, the pick gets pulled.

This feels counterintuitive. You fired a pick six hours ago \u2014 how can you un-fire it? But the alternative is worse: recommending a bet where the edge no longer exists just because it existed earlier in the day.

A pick published at noon isn\u2019t the same pick at 7 PM if the spread moved two points. The game is the same. The teams are the same. But the price is different, and the price is the bet.

---

## What This Means for You

When you see a SharpPicks notification, act on it promptly. Not recklessly \u2014 check your book, confirm the line is still in range. But understand that edges are perishable. The market is efficient and getting more efficient every season.

The window between when an edge appears and when it closes is shrinking. The model finds those windows. Your job is to be ready when they open.

> **WHY THIS MATTERS**
>
> SharpPicks doesn\u2019t just tell you who to bet. It tells you when the bet is worth making \u2014 and when it\u2019s not, even if the pick hasn\u2019t changed. The line is the bet.

*Evan Cole*
Head of Signal Intelligence, SharpPicks""",
                    status="scheduled", publish_date=datetime(2026, 3, 22), reading_time_minutes=3,
                ))
            # --- Publishing Calendar: Mar-May 2026 ---
            if 'the-model-doesnt-watch-the-game' not in existing_slugs:
                incremental_insights.append(Insight(
                    title="The Model Doesn't Watch the Game",
                    slug="the-model-doesnt-watch-the-game",
                    category="philosophy",
                    excerpt="SharpPicks doesn't know about momentum or vibes. It knows 56 features and a discipline filter that has no feelings about your favorite team.",
                    content="""There's a moment every bettor knows. You're watching a team that "feels" right. They're moving the ball, their energy is up, the crowd is into it. You pull out your phone and put money down.

That feeling is real. It's also irrelevant.

SharpPicks doesn't watch the game. It doesn't know about momentum or vibes or that one announcer who keeps saying a team "wants it more." It knows 56 features, a 3.5% minimum edge threshold, and a discipline filter that has no feelings about your favorite team.

This is the hardest thing for new users to understand. You're not signing up for hot takes. You're signing up for a system that will, on most nights, tell you to do nothing. And that's the point.

---

## The Discipline Gap

I built SharpPicks because I was tired of my own brain. I'd do the research, find the edge, and then talk myself out of it because of something I saw in pregame warmups. Or I'd skip the research entirely because I "knew" a team was due.

The model doesn't have a "due" detector. It has a four-model ensemble that asks a simple question: is the market's price wrong by enough to matter? If yes, signal. If no, pass. Every time, no exceptions.

The gap between knowing this and living it is what I call the discipline gap. Closing it is the entire product.

---

## What This Means for You

When you open the app and see zero signals, that's not a bug. It's the model doing exactly what it's supposed to do. The nights it passes are just as important as the nights it picks.

If you want someone to tell you who to bet on every night, this isn't the product. If you want a system that only speaks when the math says something, welcome.""",
                    status="scheduled", publish_date=datetime(2026, 3, 24, 15, 0),
                    reading_time_minutes=4,
                ))
            if 'why-the-best-nights-are-the-ones-you-sit-out' not in existing_slugs:
                incremental_insights.append(Insight(
                    title="Why the Best Nights Are the Ones You Sit Out",
                    slug="why-the-best-nights-are-the-ones-you-sit-out",
                    category="discipline",
                    excerpt="Last Tuesday: 9 games analyzed. 0 signals. A user asked if something was broken. Nothing was broken.",
                    content="""Last Tuesday, the model analyzed nine games and generated zero signals. The app showed a clean slate: 9 analyzed, 0 signals, 9 passed. No edge. No pick.

I got a message from a user asking if something was broken.

Nothing was broken. That was the system working perfectly.

---

## The Action Trap

Sports betting has a built-in psychological trap: there are games every night. Unlike the stock market, where you can tell yourself "I'm a long-term investor," betting gives you a fresh slate of opportunities every 24 hours. The temptation to act is constant.

Most bettors lose money not because they're bad at picking winners, but because they bet too often. They turn a 55% edge into a 48% edge by diluting it with action on games where they have no advantage.

SharpPicks solves this by making inaction the default. The discipline filter doesn't ask "which game should we bet on?" It asks "is there any game worth betting on?" Most nights, the answer is no. And that's fine.

---

## Reframing the Zero

A zero-signal night isn't a failure. It's information. It tells you the market is priced efficiently, that the sportsbooks have the lines right, that there's no gap to exploit. Acting on that information - by doing nothing - is the most disciplined move you can make.

Over a full season, the nights you sit out contribute to your ROI just as much as the nights you bet. They're the denominator that makes the numerator work.

If you're uncomfortable with inaction, this is the first thing to work on. Not your pick strategy. Not your bankroll management. Your relationship with doing nothing.""",
                    status="scheduled", publish_date=datetime(2026, 3, 27, 15, 0),
                    reading_time_minutes=3,
                ))
            if 'what-happens-between-the-lines-and-your-phone' not in existing_slugs:
                incremental_insights.append(Insight(
                    title="What Happens Between the Lines and Your Phone",
                    slug="what-happens-between-the-lines-and-your-phone",
                    category="how_it_works",
                    excerpt="Three times a day, SharpPicks pulls lines from six sportsbooks. Here's what happens next.",
                    content="""Every morning, SharpPicks wakes up before you do. By the time you check the app, the system has already pulled fresh lines from six major sportsbooks, run them through a four-model ensemble, and decided whether any game on tonight's slate is worth your attention.

Here's what that actually looks like, step by step.

---

## Step 1: Line Collection

Three times a day, the system pulls the best available spread, total, and moneyline from DraftKings, FanDuel, BetMGM, Caesars, PointsBet, and BetRivers. It doesn't use an average - it uses the best available number for each market. If DraftKings has +7.5 and FanDuel has +8, the system uses +8. You should too.

---

## Step 2: Feature Engineering

Each game gets analyzed across 56 features. These include scoring differentials, defensive efficiency, pace, rest days, home/away splits, and recent form windows. None of these features are exotic. The edge isn't in having secret data - it's in how the models weight them together.

---

## Step 3: The Ensemble

Four models vote: Gradient Boosting, Random Forest, XGBoost, and AdaBoost. Each one sees the same features but processes them differently. The ensemble blends their outputs, then applies a 30/70 shrinkage toward the market line. This is important - the model respects the market. It just thinks the market is sometimes wrong by a few points.

---

## Step 4: The Discipline Filter

Raw edges pass through the filter. Anything below 3.5% adjusted edge gets cut. Spread magnitude caps are enforced regardless of edge size. What survives is a signal. What doesn't is labeled "passed" and shown on the Market Board so you can see exactly what the model considered and rejected.

---

## Step 5: Your Phone Buzzes

If signals survive the filter, you get a push notification. Open the app, and you see the pick, the edge, the quant reasoning, and the cover probability. No fluff, no narrative, no "lock of the day." Just the math and what it says.

The entire pipeline runs without human intervention. I don't override it. I don't add picks. I don't remove picks. The system is the system.""",
                    status="scheduled", publish_date=datetime(2026, 3, 31, 14, 0),
                    reading_time_minutes=5,
                ))
            if 'clv-is-the-only-scoreboard-that-matters-early' not in existing_slugs:
                incremental_insights.append(Insight(
                    title="CLV Is the Only Scoreboard That Matters Early",
                    slug="clv-is-the-only-scoreboard-that-matters-early",
                    category="philosophy",
                    excerpt="You're 5-7 on the season. You think the model is broken. It's not. You just don't have enough data yet.",
                    content="""You're 12 picks into the season. You're 5-7. You're wondering if the model is broken.

It's not. You just don't have enough data yet.

---

## The Sample Size Problem

At 12 picks, your record is mostly noise. A fair coin flipped 12 times can easily come up 5-7. Or 8-4. Or 3-9. The variance in small samples is enormous, and your emotional reaction to a 5-7 start will mislead you far more than the record itself.

This is why SharpPicks tracks Closing Line Value as the primary early performance metric. CLV answers a different question than your record does: not "did the bet win?" but "was the bet smart?"

---

## What CLV Actually Tells You

If the model takes a team at +7.5 and the line closes at +6, that's 1.5 points of CLV. The market moved toward the model's position. Regardless of whether that specific bet won or lost, the model identified value that the broader market eventually agreed with.

Sustained positive CLV is the single best predictor of long-term profitability in sports betting. It's not a guarantee - nothing is - but it's the closest thing to a leading indicator that exists.

---

## The 50-Pick Gate

I've set a personal rule: no meaningful model adjustments before 50 picks. Before that threshold, I'm watching CLV trends, checking that the pipeline is functioning correctly, and resisting the urge to tinker. After 50 picks, the data starts to mean something and adjustments become rational rather than reactive.

If you're a new user, I'd encourage the same patience. Don't judge the model on your first two weeks. Judge it on your first two months. And in the meantime, watch the CLV.""",
                    status="scheduled", publish_date=datetime(2026, 4, 7, 14, 0),
                    reading_time_minutes=4,
                ))
            if 'losing-streaks-are-part-of-the-math' not in existing_slugs:
                incremental_insights.append(Insight(
                    title="Losing Streaks Are Part of the Math",
                    slug="losing-streaks-are-part-of-the-math",
                    category="discipline",
                    excerpt="If you bet long enough with a 54% edge, you will lose seven in a row. That's not a prediction. It's a mathematical certainty.",
                    content="""If you bet long enough with a legitimate 54% edge, you will at some point lose seven in a row. This isn't a prediction. It's a mathematical certainty.

The question isn't whether it will happen. It's what you'll do when it does.

---

## Expected Drawdowns

A 54% win rate over 200 picks will produce multiple 4-5 game losing streaks and at least one 6-7 game streak. That's just how probability works. The variance band around a 54% true rate is wide enough to produce stretches that feel catastrophic in real time but are completely normal in hindsight.

The bettors who survive are the ones who sized their bets correctly before the streak started and who don't change their process during it. The bettors who blow up are the ones who double down, chase losses, or abandon the system entirely.

---

## What SharpPicks Does During a Streak

Nothing different. The model doesn't know it's on a losing streak. It doesn't have a "get back to even" mode. It analyzes the next slate the same way it analyzed the last one: 56 features, four models, discipline filter, 3.5% threshold. Same inputs, same process, same outputs.

That's not a limitation. That's the entire point.

---

## Your Job During a Streak

Don't increase your unit size. Don't add picks the model didn't generate. Don't skip picks the model did generate because you've "lost faith." The model hasn't changed. Only your feelings have.

If after 50+ picks the CLV is negative and the record is meaningfully below expectation, that's a signal worth examining. Seven losses in a row after 30 picks is not. Trust the math. That's what you signed up for.""",
                    status="scheduled", publish_date=datetime(2026, 4, 10, 14, 0),
                    reading_time_minutes=3,
                ))
            if 'why-the-model-respects-the-market' not in existing_slugs:
                incremental_insights.append(Insight(
                    title="Why the Model Respects the Market",
                    slug="why-the-model-respects-the-market",
                    category="how_it_works",
                    excerpt="Our model is 30% model, 70% market. That sounds like the model barely has an opinion. That's exactly right. And that's why it works.",
                    content="""SharpPicks uses a 30/70 model-to-market shrinkage blend. That means the system's final output is 30% model prediction and 70% market line. On first glance, that sounds like the model barely has an opinion.

That's exactly right. And that's why it works.

---

## The Market Is Good

NBA betting lines are set by sharp oddsmakers and shaped by millions of dollars in public and professional money. By the time you see a line, it's already incorporated an enormous amount of information. The market isn't always right, but it's right more often than any individual model.

A model that ignores the market is a model that thinks it's smarter than the collective intelligence of every bettor, oddsmaker, and syndicate in the world. That's arrogance, not edge.

---

## Where the Edge Lives

The model's value isn't in bold disagreements with the market. It's in small, systematic corrections. When the model says a team should be -6 and the line is -4.5, that 1.5-point gap is the edge. It's not dramatic. It's not exciting. But over hundreds of picks, those small corrections compound.

The 30/70 blend ensures the model stays humble. It anchors to the market and only deviates when its features justify a correction. This prevents overfitting, reduces variance, and keeps the model from chasing phantom edges that disappear out of sample.

---

## When the Market MAE Still Wins

Right now, the market's mean absolute error is still lower than the model's on raw predictions. This is expected and normal. The model isn't trying to be more accurate than the market on every game - it's trying to find the specific games where the market is most wrong. The 30/70 blend is correctly calibrated for this reality.

If the model ever becomes more accurate than the market on raw MAE, we'd shift the blend. Until then, 30/70 is the honest ratio.""",
                    status="scheduled", publish_date=datetime(2026, 4, 14, 14, 0),
                    reading_time_minutes=3,
                ))
            if 'we-dont-sell-picks-we-sell-process' not in existing_slugs:
                incremental_insights.append(Insight(
                    title="We Don't Sell Picks. We Sell Process.",
                    slug="we-dont-sell-picks-we-sell-process",
                    category="philosophy",
                    excerpt="The next time someone offers you a lock, ask three questions: methodology, full-season record, CLV. If they can't answer all three, they're selling hope.",
                    content="""The sports betting internet is full of people selling picks. They'll tell you they're up 40 units this month. They'll show you a screenshot of a winning ticket. They'll charge you $99 for a "VIP package" that gives you access to their "lock of the day."

SharpPicks is not that.

---

## The Tout Problem

Touts survive by exploiting two things: selection bias and short memories. They post their winners publicly and their losers quietly. They reframe 52% seasons as dominant runs. And they know that most of their customers will churn within 60 days, replaced by new ones who only saw the highlight reel.

This business model requires opacity. If you showed the full record, the full methodology, and the full variance, most people would realize the tout has no edge. So touts never show you the full picture.

---

## Radical Transparency

SharpPicks shows you everything. Every game analyzed. Every edge detected. Every pick passed on. The discipline filter is visible. The quant reasoning is visible. The model's track record - wins and losses - is visible. The CLV is visible.

I don't cherry-pick winning nights for marketing. I don't hide losing streaks. The Results tab shows every pick the model has ever made, in order, with the outcome. If the model is performing, you'll see it. If it's not, you'll see that too.

This is what selling process looks like. You're not paying for a guy's gut feeling with a confidence score attached. You're paying for a system with a defined methodology, a visible track record, and a discipline framework that tells you when not to bet.

---

## Why This Matters for You

The next time someone offers you a lock, ask them three questions: What's your methodology? What's your full-season record? What's your CLV? If they can't answer all three, they're not selling you an edge. They're selling you hope.

Hope doesn't have a positive expected value. Process does.""",
                    status="scheduled", publish_date=datetime(2026, 4, 21, 14, 0),
                    reading_time_minutes=4,
                ))
            if 'what-march-madness-silence-taught-us' not in existing_slugs:
                incremental_insights.append(Insight(
                    title="What March Madness Silence Taught Us About Our Own Model",
                    slug="what-march-madness-silence-taught-us",
                    category="market_notes",
                    excerpt="March Madness came and went. We didn't publish a single pick. That was one of the hardest decisions I've made as a founder.",
                    content="""March Madness came and went. SharpPicks didn't publish a single tournament pick. Not because we didn't want to - because the model isn't built for it.

This was one of the hardest decisions I've made as a founder, and one of the most important.

---

## The Temptation

Every sports betting product on the planet publishes March Madness content. Brackets, upset specials, first-round locks. It's the highest-traffic period of the year. From a marketing perspective, staying silent is insane.

But SharpPicks is an NBA spread model. The features are tuned for NBA matchups, NBA pace, NBA rest patterns, NBA scoring distributions. College basketball is a fundamentally different sport with 350+ teams, wildly inconsistent data quality, and a tournament format that amplifies variance to absurd levels.

---

## What We Did Instead

We used March as a content moment. We wrote about why we were sitting out. We talked about the difference between having an opinion and having an edge. We showed the discipline filter doing its job at the macro level - not just passing on individual games, but passing on an entire sport.

The response was interesting. We lost some followers who wanted bracket advice. We gained others who said the silence was what convinced them we were serious.

---

## The Lesson

Your model is defined as much by what it refuses to do as by what it does. If we'd published March Madness picks to chase traffic, we'd have undermined every claim we make about discipline and process. One month of engagement metrics isn't worth a permanent credibility hit.

When we launch MLB and WNBA coverage later this year, each sport will have its own purpose-built model, its own backtesting, and its own shadow period. We won't go live until the math justifies it. That's the same standard we hold for every individual pick, applied at the product level.""",
                    status="scheduled", publish_date=datetime(2026, 4, 24, 14, 0),
                    reading_time_minutes=5,
                ))
            if 'shadow-mode-how-we-test-a-model' not in existing_slugs:
                incremental_insights.append(Insight(
                    title="Shadow Mode: How We Test a Model Before You See It",
                    slug="shadow-mode-how-we-test-a-model",
                    category="how_it_works",
                    excerpt="Before any model goes live on SharpPicks, it runs in shadow mode - generating picks against real lines that no user ever sees. Here's why.",
                    content="""Before any model goes live on SharpPicks, it runs in shadow mode. Shadow mode means the model generates picks in real time against real lines, but those picks are never shown to users. They're graded silently in the background.

This is how we're preparing for MLB and WNBA.

---

## Why Shadow Mode Exists

Backtesting is necessary but not sufficient. A model that looks great on historical data can fall apart in production for dozens of reasons: data pipeline delays, line movement it didn't train on, feature drift, or simply overfitting to the past. Shadow mode catches these problems before they affect your bankroll.

---

## The Evaluation Gate

For WNBA, we're running shadow mode for the entire 2025 season. The model has to demonstrate profitability across that sample before going live. The gate is strict: we need to see positive CLV, a reasonable win rate, and no systematic blind spots in specific game types.

For MLB, the shadow period will cover the first portion of the 2026 season. Same evaluation criteria, applied to a larger sample given MLB's 162-game schedule.

---

## What You'll See

When a new sport goes live, it'll show up in the app alongside NBA with its own signal feed, its own discipline filter stats, and its own track record starting from day one of live picks. The shadow period record won't be published as the official track record - it's testing data, not live performance.

This process isn't fast. That's intentional. We'd rather launch late with a validated model than launch early with a guess.""",
                    status="scheduled", publish_date=datetime(2026, 5, 5, 14, 0),
                    reading_time_minutes=3,
                ))
            if 'the-anti-parlay-manifesto' not in existing_slugs:
                incremental_insights.append(Insight(
                    title="The Anti-Parlay Manifesto",
                    slug="the-anti-parlay-manifesto",
                    category="philosophy",
                    excerpt="A six-leg parlay has a higher house edge than most casino table games. SharpPicks will never generate a parlay. Here's the math.",
                    content="""Parlays are the sports betting industry's most effective tool for separating you from your money. Sportsbooks love them. Social media loves them. Your bankroll does not.

SharpPicks will never generate a parlay. Here's why.

---

## The Math Against You

A two-leg parlay at standard -110 juice requires you to win both bets to collect. If each leg has a 54% true probability, your parlay has a 29.2% chance of winning. The book pays you as if it's 27.8%. That's a 1.4% edge to the house on every two-leg parlay - worse than your edge on either individual bet.

Add a third leg and the house edge widens further. By the time you're building five and six-leg parlays - the kind that go viral on social media - you're playing a lottery with a 25%+ house edge. The sportsbook's margin on a six-leg parlay is higher than most casino table games.

---

## The Social Media Effect

Parlays go viral because they produce dramatic outcomes. A $10 bet that pays $850 makes for a great screenshot. What you don't see is the 84 times that same person lost $10. The expected value of that $850 ticket was about -$40.

This is the same selection bias that makes touts look profitable. The wins are public, the losses are private, and the math is invisible.

---

## What We Do Instead

SharpPicks generates flat-stake, single-game signals. One pick at a time, each with its own independent edge. If you want to bet three signals in one night, bet them as three separate bets. Your expected value is the same, but your variance is dramatically lower and the house takes less off the top.

Boring? Yes. Profitable? That's the plan.""",
                    status="scheduled", publish_date=datetime(2026, 5, 8, 14, 0),
                    reading_time_minutes=4,
                ))
            if 'why-mlb-is-a-quant-market' not in existing_slugs:
                incremental_insights.append(Insight(
                    title="Why MLB Is a Quant Market",
                    slug="why-mlb-is-a-quant-market",
                    category="philosophy",
                    excerpt="Baseball isn't just America's pastime. It's the sport most naturally suited to quantitative analysis — and the one where disciplined pricing matters most.",
                    content="""Baseball isn't just America's pastime. It's the sport most naturally suited to quantitative analysis — and the one where disciplined pricing matters most.

---

## The Numbers Game

Every major sport has analytics. But baseball was built on them. From batting averages to ERA to WAR, the game has always spoken in statistics. The market reflects that. MLB lines are shaped by probability models, historical matchups, and pitcher projections — not hype cycles or national TV narratives.

That makes baseball uniquely exploitable for a disciplined quantitative approach. The signal-to-noise ratio is higher. The data is deeper. And the market, while efficient, still produces gaps — especially around pitcher matchups, bullpen fatigue, and schedule density.

---

## Why 162 Games Matter

The NBA plays 82 games. The NFL plays 17. Baseball plays 162.

That volume creates two things: more data for models to learn from, and more opportunities for the market to misprice individual games. On any given Tuesday in July, there are 15 games on the board. Most of them are priced correctly. But the ones that aren't? That's where disciplined models find edge.

> **WHY THIS MATTERS**
>
> Volume without discipline is just noise. But volume with selectivity is the ideal environment for quantitative edge detection. Baseball provides exactly that.

---

## What This Means for SharpPicks

SharpPicks was built for exactly this kind of environment: large slates, deep data, and a market that rewards patience over action. The model scans every game, identifies probability gaps, and filters aggressively. Most games get passed. The few that qualify earn a signal.

That philosophy doesn't change with the sport. It intensifies. A 15-game slate with 2 signals is discipline in action. A 15-game slate with 0 signals is the system protecting your bankroll.

Baseball is a quant market. SharpPicks is a quant product. The fit is natural.

*Evan Cole*
Head of Signal Intelligence, SharpPicks""",
                    status="scheduled", publish_date=datetime(2026, 3, 20, 14, 0), reading_time_minutes=4, sport='mlb',
                ))
            if 'why-sharp-bettors-focus-on-price' not in existing_slugs:
                incremental_insights.append(Insight(
                    title="Why Sharp Bettors Focus on Price, Not Teams",
                    slug="why-sharp-bettors-focus-on-price",
                    category="philosophy",
                    excerpt="The question isn't who wins. The question is whether the price is right. That distinction separates recreational bettors from professionals.",
                    content="""The question isn't who wins. The question is whether the price is right. That distinction separates recreational bettors from professionals — and it applies across every sport SharpPicks covers.

---

## The Price Is the Bet

When a casual bettor looks at a game, they ask: "Who's going to win?" When a sharp bettor looks at the same game, they ask: "Is this number accurate?"

Those are fundamentally different questions. The first is about prediction. The second is about valuation. And valuation is what separates gambling from investing.

A team can be good and still be a bad bet. A team can be bad and still be a great bet. It depends entirely on where the market has set the price — and whether that price reflects true probability.

---

## From NBA to MLB

This principle translates directly from basketball to baseball. In the NBA, it shows up in spreads. In MLB, it shows up most clearly in moneylines.

When a team is priced at -200, the market is saying they win roughly 67% of the time. If your model says 60%, that's a pass — even if the team is excellent. Conversely, a +150 underdog implied at 40% becomes interesting when your model sees 48%.

The team doesn't matter. The gap matters.

> **WHY THIS MATTERS**
>
> Price is information. Every spread, total, and moneyline is a statement about probability. Sharp bettors don't argue with the statement — they measure whether it's accurate.

---

## Why This Is Hard

Focusing on price requires ignoring narratives. It means passing on your favorite team when the number is wrong. It means betting on teams you don't like when the number is right. It means accepting that the market is usually correct — and only acting when it demonstrably isn't.

That kind of discipline is uncomfortable. But it's the only approach that compounds over time.

SharpPicks enforces this automatically. The model doesn't know team names. It knows probabilities, prices, and gaps. When the gap is large enough, it signals. When it isn't, it stays silent. No narrative. No bias. Just math.

*Evan Cole*
Head of Signal Intelligence, SharpPicks""",
                    status="scheduled", publish_date=datetime(2026, 3, 23, 14, 0), reading_time_minutes=4, sport='mlb',
                ))
            if 'the-problem-with-betting-big-favorites' not in existing_slugs:
                incremental_insights.append(Insight(
                    title="The Problem With Betting Big Favorites in Baseball",
                    slug="the-problem-with-betting-big-favorites",
                    category="discipline",
                    excerpt="Heavy chalk looks safe. It feels safe. But in baseball, the math behind big favorites is one of the most common traps in the market.",
                    content="""Heavy chalk looks safe. It feels safe. A dominant pitcher on the mound, a strong lineup, a weak opponent. Laying -220 doesn't seem like a gamble. It seems like common sense.

But in baseball, the math behind big favorites is one of the most common traps in the market.

---

## The Juice Problem

When you bet a -220 favorite, you need that team to win 68.75% of the time just to break even. Not to profit — just to break even. The best teams in baseball win about 60% of their games over a full season. Even elite pitchers lose roughly one out of every three starts.

That means the market is pricing implied probabilities that frequently exceed historical reality. And every percentage point of overpricing comes directly out of your bankroll over time.

> **WHY THIS MATTERS**
>
> The bigger the favorite, the smaller the margin for error. In a sport where the best teams lose 60+ games a year, laying heavy chalk is a long-term leak — not a safe play.

---

## Why the Public Loves Chalk

Betting favorites feels like making a good decision. It aligns with how we think about quality: better team, better bet. But that logic ignores price entirely.

A -250 moneyline on the Yankees doesn't mean the Yankees are a good bet. It means the market thinks the Yankees will win this specific game roughly 71% of the time. If they actually win at that rate, you break even. If they win at 65%, you lose money — even though the Yankees won two out of three.

Sportsbooks know this. Favorite-heavy slates generate enormous handle from recreational bettors willing to pay premium prices for perceived certainty.

---

## Where the Value Actually Lives

The other side of every overpriced favorite is an underpriced underdog. When chalk is inflated, dog value emerges — not because the underdog is good, but because the market has overcorrected.

SharpPicks is built to detect exactly this. The model evaluates every moneyline on the board and identifies games where the implied probability diverges from the model's projection. Some of the highest-edge signals come from spots where the public is piling onto a favorite and the market hasn't fully corrected the dog's price.

That doesn't mean every underdog is a bet. Most aren't. But the ones where the gap is real? Those are the signals worth acting on.

*Evan Cole*
Head of Signal Intelligence, SharpPicks""",
                    status="scheduled", publish_date=datetime(2026, 3, 26, 14, 0), reading_time_minutes=4, sport='mlb',
                ))
            if 'why-bullpen-fatigue-creates-hidden-value' not in existing_slugs:
                incremental_insights.append(Insight(
                    title="Why Bullpen Fatigue Creates Hidden Value",
                    slug="why-bullpen-fatigue-creates-hidden-value",
                    category="market_notes",
                    excerpt="Starting pitchers get all the attention. But games are won and lost in the sixth, seventh, and eighth innings — and that's where fatigue creates market opportunity.",
                    content="""Starting pitchers get all the attention. Pregame coverage revolves around the matchup on the mound. Moneylines shift dramatically based on who's starting. But games aren't just won in the first five innings. They're won and lost in the sixth, seventh, and eighth — and that's where fatigue creates market opportunity.

---

## The Invisible Factor

When a team plays three games in three days, the impact isn't just on position players. It's on the bullpen. Relief pitchers who threw 30+ pitches yesterday aren't as sharp today. Closers who converted a save last night may be unavailable tonight. The cumulative toll of consecutive games creates a measurable decline in late-inning performance.

But moneylines rarely adjust for this. The market prices the starting pitcher heavily and discounts the bullpen state. That disconnect is where value hides.

---

## How It Shows Up

Consider two scenarios for the same team. In Game 1, they have a fully rested bullpen after an off day. In Game 2, their top three relievers have all thrown in the last two games and their closer is questionable.

The starting pitcher is the same in both games. The lineup is the same. But the team's actual win probability is meaningfully different — because late-game leverage changes the equation.

> **WHY THIS MATTERS**
>
> The market overweights what's visible (starting pitchers) and underweights what's hidden (bullpen fatigue, schedule density, reliever workload). Models that factor rest and usage patterns find edges the public doesn't see.

---

## Why SharpPicks Tracks This

The SharpPicks model incorporates rest days, schedule density, and back-to-back indicators as features. When one team's bullpen is taxed and the opponent's is fresh, that asymmetry feeds directly into the probability calculation.

It's not glamorous analysis. Nobody tweets about bullpen availability. But it's the kind of structural edge that compounds over a 162-game season — quietly, consistently, and invisibly to the casual market.

The best edges aren't the ones that make headlines. They're the ones nobody else is looking at.

*Evan Cole*
Head of Signal Intelligence, SharpPicks""",
                    status="scheduled", publish_date=datetime(2026, 3, 28, 14, 0), reading_time_minutes=4, sport='mlb',
                ))
            if 'what-makes-an-mlb-moneyline-mispriced' not in existing_slugs:
                incremental_insights.append(Insight(
                    title="What Makes an MLB Moneyline Mispriced",
                    slug="what-makes-an-mlb-moneyline-mispriced",
                    category="how_it_works",
                    excerpt="Not every moneyline is wrong. But when one is, the gap between market price and true probability is where disciplined bettors find edge.",
                    content="""Not every moneyline is wrong. In fact, most of the time, the market is remarkably accurate. Sportsbooks have access to the same data, the same models, and the same information that sharp bettors do. The line is efficient more often than not.

But when it's wrong, the gap between market price and true probability is where disciplined bettors find edge. Understanding what causes that gap is the first step to exploiting it.

---

## The Three Sources of Mispricing

Most MLB moneyline mispricings come from three sources: public bias, pitcher reputation lag, and situational blindness.

**Public bias** inflates favorites. When a marquee team faces a small-market opponent, recreational money floods the favorite side. Books adjust the line to manage liability, not to reflect true probability. The result: the favorite gets overpriced and the underdog gets underpriced. This happens most frequently on nationally televised games and weekend series.

**Pitcher reputation lag** creates stale prices. A pitcher's moneyline influence is often based on season-long stats or name recognition. But pitching performance fluctuates on shorter cycles — recent workload, pitch mix changes, mechanical adjustments. The market is slow to price these shifts. A pitcher trending down still carries a premium; a pitcher trending up still gets discounted.

**Situational blindness** ignores context. Schedule density, travel, bullpen state, and platoon matchups all affect game probability. The market accounts for some of this, but imperfectly — especially in the middle of long road trips or during compressed schedule stretches.

> **WHY THIS MATTERS**
>
> A mispriced moneyline isn't a broken line. It's a line that hasn't fully absorbed available information. The edge exists in the lag between reality and market adjustment.

---

## How the Model Finds the Gap

SharpPicks doesn't guess which lines are wrong. It measures every line against its own probability estimate — built from 50+ features including team form, rest, splits, and line movement patterns.

When the model's projected win probability diverges from the moneyline's implied probability by more than the qualification threshold, a signal is generated. The size of that gap determines edge strength.

Not every gap is actionable. Small divergences are noise. But when the gap is persistent and structurally driven — not just random variance — it represents genuine market opportunity.

---

## Why Most People Miss This

Mispriced moneylines don't look mispriced. A -160 favorite doesn't feel wrong. A +130 underdog doesn't feel like value. The numbers seem reasonable because we're conditioned to accept the market's framing.

Sharp bettors reject that framing. They ask: "What does -160 imply? Is that implied probability accurate? If not, how far off is it?" That process — price verification, not price acceptance — is the core of quantitative sports betting.

SharpPicks automates that process across every game on the board, every day. When the gap is there, you'll see a signal. When it's not, you'll see silence. Both outcomes are the system working.

*Evan Cole*
Head of Signal Intelligence, SharpPicks""",
                    status="scheduled", publish_date=datetime(2026, 3, 30, 14, 0), reading_time_minutes=5, sport='mlb',
                ))
            # --- Batch 2: May-July 2026 ---
            if 'what-100-picks-taught-us' not in existing_slugs:
                incremental_insights.append(Insight(
                    title="What 100 Picks Taught Us",
                    slug="what-100-picks-taught-us",
                    category="how_it_works",
                    excerpt="After 100 graded signals, we have enough data to separate real patterns from noise. Here's what the model's track record actually shows.",
                    content="""After 100 graded signals, the data set is large enough to mean something. Not large enough to prove everything, but large enough to separate real patterns from noise.

---

## The Numbers

We track every signal publicly. No deletions. No revisions. Every win, loss, and push sits in the record alongside the edge percentage, the closing line value, and the model's confidence at the time of publication.

At 100 picks, sample size concerns start to fade. You can calculate meaningful win rates, ROI, and CLV averages. You can segment by edge strength, by conference, by spread size. You can ask whether the model's 7%+ edges actually hit more often than the 3.5% threshold picks. (They do.)

---

## What We Got Right

The discipline filter works. Nights where the model passed had an average closest-edge below 2.5% - meaning the filter isn't just withholding picks arbitrarily, it's correctly identifying low-value slates.

CLV has been consistently positive. The model is beating the closing line more often than not, which is the single best predictor of long-term profitability in sports betting. You can win bets through variance. You can't beat the close through variance.

---

## What We Got Wrong

Early-season calibration was rough. The first 15-20 picks ran on a model that hadn't yet incorporated market-aware shrinkage. The raw predictions were overconfident, and a few edges that looked large at noon had evaporated by tip-off.

We addressed this with the February calibration update. Since then, edge persistence has improved and revocation rates dropped. The pre-tip validation cron catches most of the decay before you're exposed to it.

---

## What Comes Next

More data means better segmentation. We're building toward sport-specific reporting (NBA, MLB, WNBA) and position-level analysis. The model retrains weekly on Sundays - same 56 features, same walk-forward methodology - but the coefficients sharpen as the sample grows.

100 picks is a milestone, not a destination. The process continues.""",
                    status="scheduled", publish_date=datetime(2026, 5, 15, 14, 0),
                    reading_time_minutes=4,
                ))
            if 'the-playoff-edge-problem' not in existing_slugs:
                incremental_insights.append(Insight(
                    title="The Playoff Edge Problem",
                    slug="the-playoff-edge-problem",
                    category="market_notes",
                    excerpt="Playoff markets are tighter, more efficient, and harder to beat. Here's how the model adapts - and why you should expect fewer signals in May.",
                    content="""Playoff markets are different. More money flows into fewer games. Lines are sharper. Public attention concentrates on a handful of matchups instead of spreading across a twelve-game slate.

---

## Why Edges Shrink

During the regular season, the model finds actionable edges on roughly 30% of slates. In the playoffs, that number drops. Not because the model gets worse, but because the market gets better.

Sportsbooks dedicate more resources to playoff pricing. Sharp money arrives earlier. The window between line release and market efficiency narrows from hours to minutes. Edges that would have persisted until tip-off during a February Tuesday disappear by mid-afternoon in May.

---

## How the Model Handles It

The qualification threshold doesn't change. 3% is 3% regardless of the calendar. What changes is how often games clear that threshold. Fewer games, tighter markets, fewer qualifying edges.

This is the discipline filter working exactly as designed. If the edge isn't there, the model passes. In a seven-game playoff series, you might see one or two signals across the entire series. That feels wrong to anyone conditioned by the volume of the regular season. It's not wrong. It's correct.

---

## What This Means for You

Expect quieter weeks in the playoffs. Fewer signals. More pass days. The app will feel less active, and the temptation to seek action elsewhere will be real. Resist it. The same discipline that generated positive CLV over 100+ picks doesn't stop applying because the games feel more important.

The model doesn't know it's the playoffs. It sees numbers, spreads, and probabilities. That's a feature.""",
                    status="scheduled", publish_date=datetime(2026, 5, 22, 14, 0),
                    reading_time_minutes=4,
                ))
            if 'bankroll-management-is-boring-on-purpose' not in existing_slugs:
                incremental_insights.append(Insight(
                    title="Bankroll Management Is Boring on Purpose",
                    slug="bankroll-management-is-boring-on-purpose",
                    category="discipline",
                    excerpt="Flat stakes, fixed sizing, no chasing. It's not exciting. That's the point.",
                    content="""Nobody ever got a dopamine hit from flat-stake sizing. Nobody ever posted a bankroll management chart on social media. Nobody's replying to a tweet about unit discipline.

That's exactly why it works.

---

## The Compounding Trap

The most common bankroll mistake isn't betting too much on one game. It's increasing bet size after wins and failing to decrease after losses. This asymmetry - known as gambler's ruin in probability theory - means that even a positive-EV bettor can go broke through poor sizing.

SharpPicks uses flat stakes for a reason. Every signal gets the same allocation regardless of edge size or confidence level. A 7% edge and a 3.5% edge get the same bet. This feels suboptimal. It isn't.

---

## Why Not Scale With Edge Size?

Because edge estimates have uncertainty. A 7% edge isn't exactly 7%. It's a point estimate with a confidence interval. Betting more on "bigger" edges amplifies the variance without proportionally amplifying the expected value, because the estimation error is larger on extreme values.

Flat stakes neutralize this. You capture the edge across many bets, and the law of large numbers does the heavy lifting. No single pick can wreck your bankroll. No single win can inflate your confidence into a larger next bet.

---

## The Kill Switch Connection

Our kill switch system reduces position sizing during model underperformance. This is dynamic bankroll management at the system level - the one place where sizing should adjust. When the model's rolling ROI drops or CLV turns persistently negative, exposure decreases automatically.

You don't make that decision. The system does. And when conditions recover, sizing returns to normal. Boring, automated, effective.""",
                    status="scheduled", publish_date=datetime(2026, 6, 2, 14, 0),
                    reading_time_minutes=4,
                ))
            if 'mlb-shadow-mode-what-we-learned' not in existing_slugs:
                incremental_insights.append(Insight(
                    title="MLB Shadow Mode: What We Learned",
                    slug="mlb-shadow-mode-what-we-learned",
                    category="how_it_works",
                    excerpt="The MLB model has been running in shadow mode since late March. Here's what two months of silent predictions revealed about baseball markets.",
                    content="""Since late March, the SharpPicks MLB model has been running in shadow mode. Every day, it analyzes the full slate of games, generates predictions, and records what it would have signaled. No picks go live. No money on the line. Just data.

---

## What Shadow Mode Tests

Shadow mode validates three things: prediction accuracy, edge persistence, and market alignment. The model needs to demonstrate that its run line and total projections are calibrated, that edges identified at line release still exist near first pitch, and that the overall framework translates from basketball to baseball.

Baseball is a different animal. Starting pitchers matter more than any single factor in basketball. Bullpen usage patterns create multi-game dependencies. Weather, park factors, and altitude affect totals in ways that don't exist in the NBA. The model accounts for all of this, but theory and practice are different things.

---

## Early Results

The good news: calibration looks reasonable. The model's predicted margins are tracking within acceptable ranges of actual outcomes. Run line accuracy is comparable to where the NBA model was after the same number of games.

The cautionary news: edge decay is higher in baseball. A lot of early-day edges disappear by first pitch, particularly in nationally televised games. The pre-tip validation cron, which works well for NBA, needs tighter thresholds for MLB to prevent acting on stale edges.

---

## What's Next

Shadow mode continues through at least June. We need more data, especially on bullpen-heavy situations and weather-affected games. If the model passes internal validation, MLB signals will launch alongside NBA for the 2026-27 season - or potentially sooner if the data supports it.

You'll see it in the app when it happens. Until then, the shadow continues.""",
                    status="scheduled", publish_date=datetime(2026, 6, 12, 14, 0),
                    reading_time_minutes=4,
                ))
            if 'the-off-season-isnt-off' not in existing_slugs:
                incremental_insights.append(Insight(
                    title="The Off-Season Isn't Off",
                    slug="the-off-season-isnt-off",
                    category="philosophy",
                    excerpt="When the NBA season ends, the model doesn't stop. Here's what happens between June and October.",
                    content="""The NBA Finals end. The confetti falls. And then, from a betting perspective, silence. No games to analyze. No edges to find. No signals to publish.

But the model doesn't stop.

---

## What Happens in the Off-Season

Between seasons, we do three things: retrain, research, and rebuild.

Retraining means running the full walk-forward optimization on the complete season's data. Every game from October through June gets incorporated. Feature weights adjust. The model learns which of its 56 inputs mattered most in the season that just ended and which were noise. This annual recalibration is how the model stays current without chasing trends.

Research means investigating new features. Did any new data sources become available? Are there team-level metrics we're not capturing? Is the market systematically mispricing any specific game contexts (back-to-backs, altitude, rest days) that the model could exploit more effectively?

Rebuilding means infrastructure. The shadow mode systems for MLB and WNBA run year-round. App improvements, new dashboards, and refinements to the signal generation pipeline all happen between seasons.

---

## Why This Matters to You

You won't see picks during the off-season. But the app doesn't go dark. Market notes continue for any active sport (MLB, WNBA). Journal articles continue. The model's historical record stays accessible. And when next season starts, the model that generates your first signal will be meaningfully better than the one that generated your last.

---

## The Discipline Parallel

Just as pass days during the season are the discipline working, the off-season is the discipline working at a macro level. We don't force-generate signals when there's nothing to signal on. We don't pivot to sports we haven't validated. We wait, prepare, and come back sharper.

The off-season is not downtime. It's the opposite.""",
                    status="scheduled", publish_date=datetime(2026, 6, 23, 14, 0),
                    reading_time_minutes=4,
                ))
            if 'why-we-show-you-the-losses' not in existing_slugs:
                incremental_insights.append(Insight(
                    title="Why We Show You the Losses",
                    slug="why-we-show-you-the-losses",
                    category="philosophy",
                    excerpt="Every losing pick stays in the record. Every revoked signal is visible. This isn't an accident - it's the entire point.",
                    content="""Every betting service shows you the wins. The screenshots. The green. The "another one cashes" posts. What they don't show you is the full picture.

SharpPicks shows you everything.

---

## The Full Record

Every signal we've ever published is in the app. Wins, losses, pushes, and revocations. The edge at publication, the closing line value, and the final score. Nothing gets deleted. Nothing gets hidden. Nothing gets quietly removed after a bad week.

This is unusual. Most services curate their history. They show the 11-3 run but not the 4-7 stretch that preceded it. They screenshot the winning week but not the losing month. They have "premium records" that somehow look better than their free records.

We don't do that. Our record is one record. The same one you see is the same one we see. The same one anyone can verify.

---

## Why Transparency Builds Trust

A model that loses 45% of its bets can still be highly profitable if it's beating the closing line and sizing correctly. Understanding this requires seeing the losses. If we only showed you the wins, you'd develop an unrealistic expectation of what disciplined betting looks like.

Disciplined betting includes losing streaks. It includes weeks where the record is 1-3 and the CLV is still positive. It includes nights where the signal gets revoked because the edge decayed. All of that is normal, and hiding it would be a disservice.

---

## The Anti-Tout Standard

In an industry built on selective disclosure, full transparency is a competitive advantage. Not because it looks good in marketing - it often doesn't - but because it builds the kind of trust that survives a losing week.

If you can look at our full record, see the losses, and still understand why the process works, then you understand what SharpPicks is. If you can't, then we need to explain it better. Either way, the data stays visible.""",
                    status="scheduled", publish_date=datetime(2026, 7, 7, 14, 0),
                    reading_time_minutes=4,
                ))

            if 'why-we-pass-more-than-we-play' not in existing_slugs:
                incremental_insights.append(Insight(
                    title="Why We Pass More Than We Play",
                    slug="why-we-pass-more-than-we-play",
                    category="philosophy",
                    excerpt="SharpPicks passes on roughly 70% of available games. That restraint is the product.",
                    content="""The betting industry runs on volume. More picks. More action. More games. More engagement. The incentive structure is built to keep you betting. Every notification, every push alert, every "lock of the day" exists to make you feel like sitting out is falling behind.

SharpPicks publishes a signal on roughly 30% of available game slates. The other 70% of the time, the system is silent.

That silence is the product.

---

## The Volume Trap

The average recreational bettor acts on roughly 78% of available slates. That number comes from industry data across major sportsbooks. Nearly four out of every five nights with games, the typical bettor places at least one wager.

Professional syndicates operate at 15-25%. The sharpest money in the world sits out three or four nights for every one night it acts. This is not laziness. It is selectivity. The math is straightforward: in an efficient market, most available prices are fair. Fair prices, after accounting for the vig, produce a negative expected return. Betting on fair prices is a guaranteed way to lose slowly.

The edge exists in the gaps. The games where the market has not yet corrected a mispricing. Those gaps do not appear on every slate. Some nights every game is priced efficiently. Those nights, the correct action is no action.

---

## Why Passes Feel Wrong

There is a psychological cost to passing. You open the app. You see games. You want to have a position. Having no position feels like you are not participating. You paid for a subscription. Where are your picks?

This is the same impulse that drives overtrading in financial markets. Studies consistently show that the more frequently an investor trades, the worse their returns. The urge to act is the enemy of the process.

SharpPicks is designed to resist this impulse on your behalf. The model scans every game. It computes edges on every matchup. And when nothing clears the threshold, it tells you. Not with a vague "no plays today" but with data: how many games were analyzed, how many edges were detected, and why none qualified.

The pass day is not empty. It is full of information. It tells you the market is efficient tonight. It tells you your capital is better served waiting for a real edge. It tells you the model is working, even when it is silent.

---

## The Capital Preservation Math

Every bet you do not place on a sub-threshold game preserves capital for a game where the edge is real. This is not abstract. It is measurable.

SharpPicks tracks a metric called "capital preserved." It calculates what you would have lost, on average, by betting on games that did not meet the edge threshold. Over a season, that number is material. The bets you did not make contribute to your ROI just as meaningfully as the bets you won.

The industry does not sell restraint because restraint is not a product you can market in a tweet. But it is the behavior that separates the 5% of bettors who are profitable from the 95% who are not.

---

## What Selectivity Actually Costs

Selectivity costs engagement. It costs the dopamine hit of having a rooting interest every night. It costs the feeling of being in the game.

What it earns is a portfolio of bets where every entry was justified by a quantifiable edge. Not a gut feeling. Not a narrative. Not "the Celtics are due." A number. A threshold. A process.

That process will feel boring on pass days. That boredom is the point.

---

> **WHY THIS MATTERS**
>
> The next time SharpPicks is silent, that silence is not a gap in service. It is the service. The model scanned the full slate, found no qualifying edge, and chose restraint over noise. That choice, repeated over hundreds of nights, is the difference between a process and a habit.

---

*Evan Cole*
Head of Signal Intelligence, SharpPicks""",
                    status="published", publish_date=datetime(2026, 4, 2), reading_time_minutes=4,
                    pass_day=True,
                ))
            if 'the-cost-of-a-bad-bet' not in existing_slugs:
                incremental_insights.append(Insight(
                    title="The Cost of a Bad Bet You Didn't Need to Make",
                    slug="the-cost-of-a-bad-bet",
                    category="philosophy",
                    excerpt="Every unnecessary bet has a cost beyond the dollars lost. It erodes discipline, distorts your record, and moves you further from profitability.",
                    content="""You are having a good week. Three signals, three winners. You are up 2.8 units. It is Friday night, the model is silent, and there are nine games on the board. You look at the Hawks and the Pacers. The spread feels wrong. You place a bet.

You lose. You are now up 1.8 units instead of 2.8 units. One unit gone. That unit did not disappear because of bad luck. It disappeared because you made a bet the process did not ask you to make.

This is the most common and most expensive mistake in sports betting. Not the bad beat. Not the last-second cover. The bet you placed because you felt like betting.

---

## The Three Costs

A bad bet costs more than the stake.

**The financial cost** is obvious. You lose the unit. Your weekly ROI drops. Your equity curve bends downward. This is the cost everyone sees.

**The behavioral cost** is less obvious but more damaging. By placing a bet outside the system, you have trained yourself to override the process. You have established a precedent: when the model is quiet, I act anyway. That precedent erodes every future pass day. Each override makes the next override easier.

**The statistical cost** is the one nobody tracks. Your record now includes a bet that was never part of the process. If you lose, your win rate drops for reasons unrelated to the model's performance. If you win, you reinforce the behavior of overriding the system. Either outcome is bad. The bet pollutes your data.

---

## The Opportunity Cost of Tilt

The sequence matters more than the individual bet. A bettor who follows the model for 10 days, goes rogue on day 11, loses, and then follows the model again on day 12 has a different psychological profile than a bettor who followed the model for 12 straight days.

The rogue bet introduces doubt. Did the model miss that game? Should I be adding my own analysis? Maybe I should bet more than the model suggests on the next pick. These are not rational thoughts. They are the residue of breaking the process once.

Professional poker players call this tilt. The best players recognize it and sit out. The worst players chase. Sports betting works the same way. The bet you did not need to make is the first domino.

---

## How SharpPicks Addresses This

The discipline score in SharpPicks tracks exactly this behavior. It measures your selectivity: the percentage of available signals you act on versus the ones you pass. It includes bets you place outside the model's recommendations.

A user who follows every model signal and adds no additional bets will have a selectivity rate that matches the model's. A user who adds their own bets on pass days will see their selectivity rate climb above the model's, and their discipline grade will reflect it.

This is not a punishment. It is a mirror. The data tells you how often you are overriding the process and whether those overrides are helping or hurting your results.

---

## The Rule

If the model does not signal, you do not bet. Not because the model is always right. It is not. But because the model has a defined edge threshold, a calibration process, and a track record. Your Friday-night gut feeling has none of those things.

The bet you did not need to make is the most expensive bet in your portfolio. Not because it always loses. But because it always costs.

---

> **WHY THIS MATTERS**
>
> SharpPicks tracks every bet you place, both model-recommended and self-directed. The discipline score exists to help you see the pattern. The goal is not perfection. It is awareness. Know what the process recommends. Know when you are deviating. And know what that deviation costs over time.

---

*Evan Cole*
Head of Signal Intelligence, SharpPicks""",
                    status="published", publish_date=datetime(2026, 4, 2), reading_time_minutes=4,
                    pass_day=True,
                ))
            if 'what-selectivity-rate-tells-you' not in existing_slugs:
                incremental_insights.append(Insight(
                    title="What Your Selectivity Rate Actually Tells You",
                    slug="what-selectivity-rate-tells-you",
                    category="discipline",
                    excerpt="Selectivity rate measures how often you bet relative to available opportunities. It separates recreational bettors from professionals.",
                    content="""You can tell a lot about a bettor from a single number. Not their win rate. Not their ROI. Their selectivity rate.

Selectivity rate measures how often you place a bet relative to the number of available opportunities. If there are 100 game days in a season and you bet on 75 of them, your selectivity rate is 75%. If you bet on 28, your rate is 28%.

That number, more than any other metric, predicts whether you will be profitable over the long term.

---

## The Industry Benchmark

Sportsbook data consistently shows that the average recreational bettor acts on roughly 78% of available slates. This means the typical bettor finds a reason to wager nearly four out of every five nights.

Professional betting syndicates operate between 15% and 30%. They watch the same games. They have access to the same lines. They simply act far less often.

The gap between 78% and 25% is not a difference in information. It is a difference in discipline. The recreational bettor asks "which game should I bet?" The professional asks "is there a game worth betting?" The first question assumes action. The second question assumes inaction as the default.

---

## What Your Number Tells You

**Above 70%**: You are betting on most available games. At this rate, you are almost certainly including bets where the edge is marginal or nonexistent. The vig will eat your margin over a full season. This is not sustainable unless you have a genuinely elite model, and the evidence suggests that elite models produce signals far less frequently than 70% of the time.

**50-70%**: You are more selective than the average bettor but still acting on the majority of slates. There is room to tighten. Ask yourself: of your last 20 bets, how many were driven by a quantified edge versus a gut read?

**30-50%**: You are operating in the zone where professional returns become possible. At this selectivity rate, you are passing on more than half the available action. Each bet carries more conviction. Your average edge per bet is likely higher because you are filtering out the marginal spots.

**Below 30%**: You are operating at a professional selectivity level. The challenge here shifts from discipline to patience. Going five or six days without a bet is psychologically difficult. But if each bet you place has a genuine 4-6% edge, the math works decisively in your favor over a season.

---

## Selectivity and ROI Are Connected

This is not theoretical. Across historical data, there is a consistent inverse relationship between selectivity rate and long-term ROI. Bettors who act more frequently tend to have lower ROI per unit risked. Bettors who act less frequently tend to have higher ROI.

The mechanism is straightforward. More bets means more marginal bets. More marginal bets means more bets where the edge, if it exists, is smaller than the vig. Those bets are negative expected value. They dilute the bets that were genuinely sharp.

A bettor with 10 sharp bets and 40 marginal bets has a blended ROI that is dragged down by the 40. A bettor with 10 sharp bets and 0 marginal bets has a clean ROI that reflects the actual quality of their process.

---

## How SharpPicks Grades Selectivity

The discipline score in SharpPicks includes a selectivity component. It compares your personal betting rate against the model's signal rate. If the model is publishing signals on 28% of slates and you are betting on 60% of slates, the gap is visible.

The grade is not a judgment. It is information. Some users choose to supplement model signals with their own analysis. The discipline score simply tracks whether those supplements are helping or hurting.

Over time, the correlation between your selectivity rate and your ROI will tell you whether your additional bets are adding value or subtracting it. That feedback loop is the point.

---

> **WHY THIS MATTERS**
>
> SharpPicks displays your selectivity rate alongside the industry average (78%) on the Results tab. The visual is immediate: a progress bar showing where you sit. Lower is better. Not because betting less is inherently virtuous, but because betting less, when the alternative is betting without an edge, is the single most reliable path to profitability.

---

*Evan Cole*
Head of Signal Intelligence, SharpPicks""",
                    status="scheduled", publish_date=datetime(2026, 4, 25), reading_time_minutes=4,
                ))
            if 'surviving-a-losing-streak' not in existing_slugs:
                incremental_insights.append(Insight(
                    title="A Field Guide to Surviving a Losing Streak",
                    slug="surviving-a-losing-streak",
                    category="discipline",
                    excerpt="You will lose five in a row. It is mathematically inevitable. Here is the math behind losing streaks and how to survive them.",
                    content="""At a 56% win rate, a five-game losing streak will happen approximately once every 60 bets. Over a full NBA season of 80-100 signals, it is not a question of if. It is a question of when.

This article is for that moment. Bookmark it now.

---

## The Math of Losing Streaks

A fair coin flipped 100 times will produce a streak of 7 or more consecutive heads (or tails) roughly 50% of the time. Streaks are a feature of randomness, not evidence of something broken.

Sports betting works the same way. A model with a true 56% win rate will, over any 100-bet sample, produce at least one losing streak of 5 or more bets approximately 85% of the time. A losing streak of 4 or more is nearly guaranteed.

These are not edge cases. These are the expected outcomes of a profitable system operating normally.

---

## What a Losing Streak Does Not Mean

A losing streak does not mean the model is broken. The model's edge is measured over hundreds of bets, not five. A 5-game stretch tells you nothing about the model's true win rate, just as five coin flips tell you nothing about whether the coin is fair.

A losing streak does not mean the market has adapted. Markets do evolve, but they do not recalibrate overnight. If the model was profitable last month, it did not become obsolete this week. Market regime changes happen gradually, over months, and they are detectable through calibration metrics, not through short losing runs.

A losing streak does not mean you should change your unit size. Reducing your bet size after losses is a form of loss aversion that reduces your exposure precisely when the model is statistically likely to revert to its mean. Increasing your bet size to "make it back" is the classic gambler's ruin scenario. The correct unit size during a losing streak is the same unit size as during a winning streak.

---

## What a Losing Streak Does Mean

It means you are betting. That is all. A system that never loses is a system that never bets, or a system that is lying about its record.

The productive response to a losing streak is to check the process, not the results. Ask these questions:

**Is the model still calibrated?** Check the calibration dashboard. Are predicted probabilities matching actual outcomes across confidence buckets? If 55% predictions are hitting at 55%, the model is fine. The streak is variance.

**Is CLV still positive?** If the model's picks are still beating the closing line during the losing streak, the edges are real. The outcomes are noise. Positive CLV during a losing streak is the strongest signal that the process is sound.

**Has anything structural changed?** New season, major rule changes, significant market structural shifts? If no, the model's training data is still relevant.

If all three answers are reassuring, the correct action is no action. Continue following the system at the same unit size. The math will revert.

---

## The Behavioral Traps

Losing streaks trigger specific, predictable behavioral patterns. Knowing them in advance is the best defense.

**The auditor**: You start second-guessing individual picks after the fact. "I knew the Celtics were too many points." You did not know that. You are constructing a narrative to explain randomness.

**The adjuster**: You decide to skip the next signal or bet half units. You are now running a different system than the one with a demonstrated edge. Your future results will reflect a system that does not exist in any backtest.

**The freelancer**: You stop trusting the model and start placing your own bets. Your selectivity rate spikes. Your discipline score drops. The bets you add do not have a quantified edge. They have an emotional justification.

**The quitter**: You cancel your subscription. You leave during the exact period of variance that every profitable bettor experiences. You will never see the reversion.

All four responses feel rational in the moment. None of them are. They are emotional reactions to a statistical certainty.

---

> **WHY THIS MATTERS**
>
> This article exists so you can read it when the losing streak arrives. Not if. When. The process does not change during a drawdown. The unit size does not change. The threshold does not change. The only thing that changes is your emotional state. And the system is designed to outlast that.

---

*Evan Cole*
Head of Signal Intelligence, SharpPicks""",
                    status="scheduled", publish_date=datetime(2026, 4, 29), reading_time_minutes=5,
                ))
            if 'how-mlb-model-differs-from-nba' not in existing_slugs:
                incremental_insights.append(Insight(
                    title="How the MLB Model Differs from NBA",
                    slug="how-mlb-model-differs-from-nba",
                    category="how_it_works",
                    sport="mlb",
                    excerpt="Baseball and basketball are different sports with different market dynamics. Here is how the SharpPicks MLB model differs from NBA.",
                    content="""When we launched MLB on SharpPicks, the most common question was whether we just copied the NBA model and pointed it at baseball. The answer is no. The same ensemble architecture runs underneath, but nearly everything above it changed.

Baseball and basketball are structurally different sports. The markets price them differently. The features that predict outcomes are different. The calibration challenges are different. Here is what we adjusted and why.

---

## Slate Size and Signal Frequency

An NBA night typically has 5-12 games. An MLB day can have 15 or more. More games means more opportunities for the model to scan, but it does not mean more signals. In fact, MLB's larger slates make selectivity even more important. The temptation to publish multiple signals on a 15-game day is real. The discipline to filter down to the best one or two edges is what separates a signal service from a picks dump.

During calibration, we cap MLB signals more conservatively than NBA. The model needs to prove itself on a smaller number of high-conviction picks before we expand the signal volume.

---

## The Pitching Variable

The single biggest difference between MLB and NBA modeling is the role of individual players. In basketball, team-level metrics dominate. No single player changes the spread by more than a few points in most games. In baseball, the starting pitcher changes everything.

A team's run expectancy with their ace on the mound versus their fifth starter can differ by 2 or more runs. That is the equivalent of a 6-point swing in basketball terms. The market knows this, which is why pitcher-specific features (ERA, WHIP, innings pitched, recent workload) are weighted heavily in the MLB model.

The NBA model does not include individual player performance metrics in its core features. The MLB model cannot function without them. The starting pitcher is not a feature. It is the feature.

---

## Run Line vs. Spread

The NBA spread is a continuous variable that moves in half-point increments. The MLB run line is typically fixed at 1.5 (the favorite at -1.5, the underdog at +1.5). This creates a fundamentally different modeling problem.

In basketball, the model predicts a margin and compares it to a moving spread. The edge is the gap between the two. In baseball, the primary spread is fixed. The model's edge on the run line comes from estimating the probability of a 2+ run margin, which is a different calculation than estimating the expected margin itself.

The moneyline is more important in MLB than in NBA. Because the run line is fixed, the moneyline is where the market expresses its true view of the game's competitiveness. The SharpPicks MLB model evaluates both the run line and the moneyline for each game and publishes whichever offers the better edge. In NBA, the model focuses almost exclusively on the spread.

---

## Market Efficiency Differences

NBA lines are among the most efficient in sports betting. The market is deep, liquid, and priced by sophisticated participants. Finding consistent 5%+ edges on NBA spreads is genuinely difficult.

MLB lines, particularly for early-season games and mid-week series with lower public interest, tend to be slightly less efficient. There is less betting volume on a Tuesday afternoon Pirates game than on a Friday night Lakers game. Less volume means more potential for mispricing.

This does not mean MLB edges are easy to find. It means the model has a slightly wider surface area to search. The threshold for publishing is the same: the edge must clear a minimum before the signal fires. But the distribution of edges across a full MLB slate tends to have more games in the 2-4% range than a typical NBA slate.

---

## Calibration Differences

The NBA model has been running in production since January 2026. It has published dozens of signals with tracked CLV data. The calibration is established: we know the model's sigma, we know the edge distribution, and we know the shrinkage blend that produces the most accurate predictions.

The MLB model is in calibration phase. This means every signal is published, tracked, and graded, but the model's parameters are still being validated. The edge threshold, the shrinkage ratio, and the signal tier classifications will be refined as the sample grows.

During calibration, the "BETA" label on MLB signals is a transparency marker. It tells you this model has not yet earned the same confidence level as the NBA model. The process is identical. The conviction is still being established.

---

## What Stays the Same

The ensemble architecture (four models, blended output) is identical across sports. The edge threshold logic is the same. The market shrinkage principle (respecting the closing line) is the same. CLV tracking is the same. The pass-day philosophy is the same.

The model does not care whether it is looking at basketball or baseball. It sees features, calculates probabilities, compares them to market prices, and either publishes or passes. The sport determines what features are available. The architecture determines how those features are processed.

---

> **WHY THIS MATTERS**
>
> MLB on SharpPicks is not a port of the NBA model. It is a purpose-built implementation using the same principles. Calibration phase means the model is proving itself in real time, with full transparency. Every signal, every result, every pass is tracked and published. The model earns your trust over the season. It is not assumed.

---

*Evan Cole*
Head of Signal Intelligence, SharpPicks""",
                    status="scheduled", publish_date=datetime(2026, 5, 2), reading_time_minutes=5,
                ))
            if 'what-calibration-phase-means' not in existing_slugs:
                incremental_insights.append(Insight(
                    title="What Calibration Phase Means for Your Picks",
                    slug="what-calibration-phase-means",
                    category="how_it_works",
                    sport="mlb",
                    excerpt="SharpPicks MLB is in calibration phase. Here is what that means: how the model earns confidence, what we measure, and why early transparency matters.",
                    content="""When you open the SharpPicks app and switch to MLB, you see a banner: "Model Phase: Calibration." Below it: "Edges are being tracked live. Early signals, full transparency."

This is not a disclaimer. It is a statement about where the model is in its lifecycle. Here is what calibration phase means, what we are measuring, and what changes when calibration ends.

---

## What Calibration Is

A model that has never been tested against live market data is a hypothesis. It has been trained on historical games. It has been backtested. It has shown promising results in controlled conditions. But it has not been validated in the environment that matters: real games, real lines, real outcomes, in real time.

Calibration phase is the period where the model runs live, publishes real signals, and measures whether its predictions match reality. The signals are real. The picks are tracked. The results count. But the model's parameters are still subject to adjustment based on what we learn.

---

## What We Are Measuring

Three metrics determine when calibration ends and the model moves to deployment phase.

**Calibration accuracy.** When the model says a bet has a 58% chance of covering, does it cover 58% of the time over a sufficient sample? We bucket predictions into confidence ranges and compare predicted probabilities against actual outcomes. If the buckets align within acceptable tolerance, the model is well-calibrated. If they diverge, the probability conversion needs adjustment.

**CLV consistency.** Are the model's picks beating the closing line? Positive average CLV over the calibration sample means the model is identifying genuine mispricings, not just generating lucky picks. This is the most important validation metric. A model can have a mediocre win rate but positive CLV and still be demonstrably sharp.

**Shrinkage optimization.** The blend between model prediction and market line (the shrinkage ratio) needs live data to optimize. The ratio that worked best on historical data may not be the ratio that works best in the current market. Calibration gives us the data to fine-tune this.

---

## What This Means for You

During calibration, every MLB signal you see is a real signal generated by the full model pipeline. It clears the edge threshold. It is sized by the same Kelly-based logic. It is tracked and graded identically to NBA signals.

The difference is confidence level. NBA signals come from a model that has been validated over months of live data. MLB signals come from a model that is still establishing its track record. The "BETA" label reflects this honestly.

You can act on calibration signals. Many users do. The edges are real and the process is identical. But you should understand that the model's accuracy claims are provisional until the sample reaches a statistically meaningful size.

---

## The Calibration Gate

Calibration ends when three conditions are met: the predicted-versus-actual calibration chart shows alignment across confidence buckets, average CLV is positive over at least 50 tracked signals, and the shrinkage ratio has been optimized against live data.

When all three are met, the MLB model moves to deployment phase. The "BETA" label is removed. The signal tier classifications (STRONG, LEAN) become more reliable. And the model joins NBA as a fully validated signal source.

If the conditions are not met after a full season, the model returns to development. We do not promote a model that has not earned promotion. That is the same gate we applied to NBA before it launched, and it is the same gate that WNBA will face when its shadow mode data is evaluated.

---

## Why We Show You the Calibration

Most products launch and claim accuracy from day one. They backtest on historical data, cherry-pick the best results, and present them as forward-looking proof.

We chose a different approach. The model launches in public view. Every signal it generates is visible. Every win and every loss is recorded. The calibration process is not hidden in a back office. It runs in front of you.

This costs us something. A model in calibration might have a rough first month. That rough month is visible to every user. We accept that tradeoff because the alternative, launching with unearned confidence, is worse.

The BETA label will come off when the data supports removing it. Until then, it stays.

---

> **WHY THIS MATTERS**
>
> Calibration phase is the model earning your trust in real time. Not claiming it. Not assuming it. Earning it, one tracked signal at a time. When the label changes from BETA to deployment, it will be because the data justified the change. That is the standard.

---

*Evan Cole*
Head of Signal Intelligence, SharpPicks""",
                    status="scheduled", publish_date=datetime(2026, 5, 5), reading_time_minutes=4,
                ))

            if incremental_insights:
                for ins in incremental_insights:
                    db.session.add(ins)
                db.session.commit()
                logging.info(f"Added {len(incremental_insights)} new insights")

            mlb_insight_slugs = [
                'why-mlb-is-a-quant-market', 'why-sharp-bettors-focus-on-price',
                'the-problem-with-betting-big-favorites', 'why-bullpen-fatigue-creates-hidden-value',
                'what-makes-an-mlb-moneyline-mispriced',
            ]
            mlb_insights_to_fix = Insight.query.filter(
                Insight.slug.in_(mlb_insight_slugs),
                db.or_(Insight.sport != 'mlb', Insight.sport.is_(None))
            ).all()
            for mi in mlb_insights_to_fix:
                mi.sport = 'mlb'
            if mlb_insights_to_fix:
                db.session.commit()
                logging.info(f"Tagged {len(mlb_insights_to_fix)} insights as sport=mlb")

            mlb_calendar_fixes = {
                'why-mlb-is-a-quant-market': datetime(2026, 3, 20, 14, 0),
                'why-sharp-bettors-focus-on-price': datetime(2026, 3, 23, 14, 0),
                'the-problem-with-betting-big-favorites': datetime(2026, 3, 26, 14, 0),
                'why-bullpen-fatigue-creates-hidden-value': datetime(2026, 3, 28, 14, 0),
                'what-makes-an-mlb-moneyline-mispriced': datetime(2026, 3, 30, 14, 0),
            }
            mlb_premature = Insight.query.filter(
                Insight.slug.in_(list(mlb_calendar_fixes.keys())),
                Insight.status == 'published',
                Insight.publish_date < datetime(2026, 3, 20),
            ).all()
            for mi in mlb_premature:
                mi.status = 'scheduled'
                mi.publish_date = mlb_calendar_fixes[mi.slug]
            if mlb_premature:
                db.session.commit()
                logging.info(f"Reverted {len(mlb_premature)} prematurely published MLB articles to scheduled")

            stale_note_slugs = ['market-note-2026-03-17', 'market-note-2026-03-18']
            stale_notes = Insight.query.filter(Insight.slug.in_(stale_note_slugs)).all()
            for sn in stale_notes:
                db.session.delete(sn)
            if stale_notes:
                db.session.commit()
                logging.info(f"Removed {len(stale_notes)} stale market notes")

            now = datetime.now()
            scheduled_to_publish = Insight.query.filter(
                Insight.status == 'scheduled',
                Insight.publish_date <= now
            ).all()
            for ins in scheduled_to_publish:
                ins.status = 'published'
                logging.info(f"Auto-published insight: {ins.slug}")
            if scheduled_to_publish:
                db.session.commit()

            founding_members = User.query.filter_by(founding_member=True).order_by(User.created_at.asc()).all()
            for i, fm in enumerate(founding_members, 1):
                if fm.founding_number is None:
                    fm.founding_number = i
            counter = FoundingCounter.query.first()
            if counter:
                counter.current_count = len(founding_members)
            db.session.commit()

            existing_run_keys = set()
            for r in ModelRun.query.all():
                existing_run_keys.add((str(r.date), r.sport))

            backfilled = 0
            for p in Pick.query.order_by(Pick.game_date.asc()).all():
                key = (str(p.game_date), p.sport or 'nba')
                if key not in existing_run_keys:
                    existing_run_keys.add(key)
                    db.session.add(ModelRun(
                        date=p.game_date, sport=p.sport or 'nba',
                        games_analyzed=8, pick_generated=True, pick_id=p.id,
                        run_duration_ms=3500, model_version='v1.0',
                        created_at=p.published_at or datetime.utcnow(),
                    ))
                    backfilled += 1
            for ps in Pass.query.order_by(Pass.date.asc()).all():
                key = (str(ps.date), ps.sport or 'nba')
                if key not in existing_run_keys:
                    existing_run_keys.add(key)
                    db.session.add(ModelRun(
                        date=ps.date, sport=ps.sport or 'nba',
                        games_analyzed=ps.games_analyzed or 8, pick_generated=False,
                        pass_id=ps.id, run_duration_ms=2800, model_version='v1.0',
                        created_at=datetime.utcnow(),
                    ))
                    backfilled += 1
            if backfilled > 0:
                db.session.commit()
                logging.info(f"Backfilled {backfilled} model runs from picks/passes")

            logging.info("Database seed completed")
        except Exception as e:
            logging.error(f"Database seed error: {e}")

def backup_database():
    """Daily database backup via pg_dump.
    NOTE: /tmp backups are ephemeral on Replit deploys. For production durability,
    configure BACKUP_S3_BUCKET env var to upload to S3/GCS, or use Replit's
    built-in PostgreSQL snapshot feature. Local backups serve as a safety net
    during development and provide point-in-time recovery within a single deploy.
    """
    try:
        db_url = _database_url()
        if not db_url:
            logging.warning("No database URL (SQLALCHEMY_DATABASE_URI/DATABASE_URL) set, skipping backup")
            return
        timestamp = datetime.now().strftime('%Y%m%d_%H%M')
        backup_dir = '/tmp/backups'
        os.makedirs(backup_dir, exist_ok=True)

        backup_path = f'{backup_dir}/sharppicks_backup_{timestamp}.sql'
        result = subprocess.run(
            ['pg_dump', '--no-owner', '--no-acl', '-f', backup_path],
            env={**os.environ, 'DATABASE_URL': db_url},
            capture_output=True, text=True, timeout=120
        )
        if result.returncode == 0:
            file_size = os.path.getsize(backup_path) / 1024
            logging.info(f"Database backup created: {backup_path} ({file_size:.0f} KB)")

            old_backups = sorted([
                f for f in os.listdir(backup_dir) if f.startswith('sharppicks_backup_')
            ])
            while len(old_backups) > 7:
                os.remove(os.path.join(backup_dir, old_backups.pop(0)))
        else:
            logging.error(f"Backup failed: {result.stderr}")
    except Exception as e:
        logging.error(f"Backup error: {e}")


def send_weekly_summary_job():
    """Monday 9 AM ET: Send weekly summary email to all pro users"""
    with app.app_context():
        try:
            from email_service import send_weekly_summary
            from sqlalchemy import text as sql_text

            today_str = _get_et_today()
            week_ago = (datetime.strptime(today_str, '%Y-%m-%d') - timedelta(days=7)).strftime('%Y-%m-%d')

            picks_result = db.session.execute(sql_text("""
                SELECT 
                    COUNT(*) as total,
                    SUM(CASE WHEN result = 'win' THEN 1 ELSE 0 END) as wins,
                    SUM(CASE WHEN result = 'loss' THEN 1 ELSE 0 END) as losses,
                    SUM(CASE WHEN result IS NULL OR result = 'pending' THEN 1 ELSE 0 END) as pending
                FROM picks
                WHERE game_date >= :week_ago AND game_date <= :today
            """), {'week_ago': week_ago, 'today': today_str})
            pr = picks_result.fetchone()

            passes_result = db.session.execute(sql_text("""
                SELECT COUNT(*) FROM passes WHERE date >= :week_ago AND date <= :today
            """), {'week_ago': week_ago, 'today': today_str})
            passes_count = passes_result.scalar() or 0

            total_result = db.session.execute(sql_text("""
                SELECT 
                    SUM(CASE WHEN result = 'win' THEN 1 ELSE 0 END) as wins,
                    SUM(CASE WHEN result = 'loss' THEN 1 ELSE 0 END) as losses
                FROM picks WHERE result IN ('win', 'loss')
            """))
            tr = total_result.fetchone()
            total_wins = tr[0] or 0 if tr else 0
            total_losses = tr[1] or 0 if tr else 0
            total_record = f"{total_wins}W-{total_losses}L" if (total_wins + total_losses) > 0 else ''

            # ROI and top edge for push notifications
            week_picks_result = db.session.execute(sql_text("""
                SELECT COALESCE(SUM(profit_units), 0), COALESCE(MAX(edge_pct), 0)
                FROM picks
                WHERE game_date >= :week_ago AND game_date <= :today AND result IN ('win', 'loss')
            """), {'week_ago': week_ago, 'today': today_str})
            wp = week_picks_result.fetchone()
            week_profit = wp[0] or 0 if wp else 0
            top_edge = round(wp[1] or 0, 1) if wp else 0
            picks_in_week = (pr[1] or 0) + (pr[2] or 0) if pr else 0  # wins + losses
            roi = round((week_profit / picks_in_week * 100), 1) if picks_in_week > 0 else 0
            week_num = datetime.strptime(today_str, '%Y-%m-%d').isocalendar()[1]

            stats = {
                'picks_made': pr[0] or 0 if pr else 0,
                'wins': pr[1] or 0 if pr else 0,
                'losses': pr[2] or 0 if pr else 0,
                'pending': pr[3] or 0 if pr else 0,
                'passes': passes_count,
                'total_record': total_record,
                'next_week_games': 'Full NBA slate',
                'week_num': week_num,
                'roi': roi,
                'top_edge': top_edge,
            }

            pro_users = User.query.filter(
                User.subscription_status.in_(['active', 'trial', 'cancelling']),
                User.email_verified == True,
            ).all()

            sent_count = 0
            for user in pro_users:
                prefs = user.notification_prefs or {}
                if prefs.get('weekly_summary', True):
                    if send_weekly_summary(user.email, user.first_name, stats):
                        sent_count += 1

            logging.info(f"Weekly summary sent to {sent_count}/{len(pro_users)} pro users")

            try:
                from notification_service import send_weekly_summary_notification
                send_weekly_summary_notification(stats)
            except Exception as e:
                logging.error(f"Weekly summary push notification error: {e}")
        except Exception as e:
            logging.error(f"Weekly summary job error: {e}")


def collect_todays_games():
    """Run data collection in-process — same env, shared SQLite path, no subprocess fragility."""
    logging.info(f"[collect] Starting (db={get_sqlite_path()})")
    try:
        from main import collect_todays_games as _collect, collect_yesterdays_scores
        _collect()
        try:
            collect_yesterdays_scores(date_offset=1)
        except Exception as e:
            logging.warning(f"[collect] Yesterday's scores failed (non-fatal): {e}")
        logging.info("[collect] Completed")
    except Exception as e:
        logging.error(f"[collect] Error: {e}")
        raise

def grade_pending_picks():
    """Check game results and grade pending picks as win/loss.
    Also grade TrackedBets linked to revoked picks (user bet before withdrawal)."""
    with app.app_context():
        from sqlalchemy import or_, and_
        picks_with_ungraded_bets = db.session.query(Pick.id).join(
            TrackedBet, TrackedBet.pick_id == Pick.id
        ).filter(TrackedBet.result.is_(None)).distinct().subquery()
        picks_to_grade = Pick.query.filter(
            or_(
                Pick.result == 'pending',
                Pick.id.in_(db.session.query(picks_with_ungraded_bets.c.id))
            )
        ).all()
        logging.info(f"[Auto-grade] Found {len(picks_to_grade)} picks to grade (pending + revoked with active bets)")
        if not picks_to_grade:
            return

        sqlite_conn = None
        try:
            sqlite_conn = get_sqlite_conn()
            sqlite_conn.row_factory = sqlite3.Row
            sqlite_cursor = sqlite_conn.cursor()
        except Exception:
            sqlite_cursor = None

        graded_count = 0
        for pick in picks_to_grade:
            try:
                game = None
                raw_date = pick.game_date
                if hasattr(raw_date, 'strftime'):
                    pick_date = raw_date.strftime('%Y-%m-%d')
                else:
                    pick_date = str(raw_date)[:10]
                logging.info(f"[Auto-grade] Processing: {pick.away_team} @ {pick.home_team} on {pick_date}")

                from sport_config import get_espn_scoreboard_url
                try:
                    pd_date = datetime.strptime(pick_date, '%Y-%m-%d').date()
                    next_day = (pd_date + timedelta(days=1)).strftime('%Y-%m-%d').replace('-', '')
                    espn_dates_to_try = [pick_date.replace('-', ''), next_day]
                except Exception:
                    espn_dates_to_try = [pick_date.replace('-', '')]
                try:
                    for date_str in espn_dates_to_try:
                        if game:
                            break
                        espn_url = get_espn_scoreboard_url(pick.sport, date_str)
                        espn_resp = http_requests.get(espn_url, timeout=15)
                        if espn_resp.status_code != 200:
                            logging.warning(f"[Auto-grade] ESPN returned {espn_resp.status_code} for {date_str}")
                            continue
                        espn_data = espn_resp.json()
                        for event in espn_data.get('events', []):
                            comps = event.get('competitions') or []
                            if not comps:
                                continue
                            comp = comps[0]
                            status_desc = (comp.get('status') or {}).get('type') or {}
                            desc = (status_desc.get('description') or '').strip()
                            if desc != 'Final' and not desc.startswith('Final'):
                                continue
                            teams = comp.get('competitors') or []
                            espn_home = next((t for t in teams if t['homeAway'] == 'home'), None)
                            espn_away = next((t for t in teams if t['homeAway'] == 'away'), None)
                            if not espn_home or not espn_away:
                                continue
                            def _team_match(espn_name, pick_name):
                                if espn_name == pick_name:
                                    return True
                                e = espn_name.lower().replace(' ', '')
                                p = pick_name.lower().replace(' ', '')
                                if e == p:
                                    return True
                                last_e = espn_name.split()[-1].lower()
                                last_p = pick_name.split()[-1].lower()
                                return last_e == last_p
                            if _team_match(espn_home['team']['displayName'], pick.home_team) and _team_match(espn_away['team']['displayName'], pick.away_team):
                                game = {
                                    'home_score': int(espn_home.get('score', 0)),
                                    'away_score': int(espn_away.get('score', 0)),
                                }
                                logging.info(f"[Auto-grade] ESPN: {pick.away_team} {game['away_score']} @ {pick.home_team} {game['home_score']}")
                                break
                except Exception as espn_err:
                    logging.error(f"[Auto-grade] ESPN error: {espn_err}")

                if not game and sqlite_cursor:
                    try:
                        table_name = 'wnba_games' if pick.sport == 'wnba' else ('mlb_games' if pick.sport == 'mlb' else 'games')
                        try:
                            pd_date = datetime.strptime(pick_date, '%Y-%m-%d').date()
                            next_day = (pd_date + timedelta(days=1)).strftime('%Y-%m-%d')
                            check_dates = [pick_date, next_day]
                        except:
                            check_dates = [pick_date]
                        for check_date in check_dates:
                            sqlite_cursor.execute(f'''
                                SELECT home_score, away_score, home_team, away_team
                                FROM {table_name}
                                WHERE home_team = ? AND away_team = ? AND game_date LIKE ?
                                AND home_score IS NOT NULL AND away_score IS NOT NULL
                                AND (home_score > 0 OR away_score > 0)
                            ''', (pick.home_team, pick.away_team, f'{check_date}%'))
                            row = sqlite_cursor.fetchone()
                            if row:
                                game = {'home_score': row['home_score'], 'away_score': row['away_score']}
                                logging.info(f"[Auto-grade] SQLite fallback: {pick.away_team} {game['away_score']} @ {pick.home_team} {game['home_score']}")
                                break
                    except Exception as sq_err:
                        logging.error(f"[Auto-grade] SQLite fallback error: {sq_err}")

                if not game:
                    continue

                home_score = game['home_score']
                away_score = game['away_score']
                if home_score is None or away_score is None:
                    continue

                spread_result = home_score - away_score
                line_value = pick.line if pick.line and abs(pick.line) < 50 else 0

                side_lower = (pick.side or '').lower()
                home_lower = (pick.home_team or '').lower()
                away_lower = (pick.away_team or '').lower()

                if not side_lower:
                    logging.warning(f"[Auto-grade] Skipping pick {pick.id}: side is empty")
                    continue

                home_full_match = home_lower in side_lower
                away_full_match = away_lower in side_lower

                if home_full_match and not away_full_match:
                    is_home_pick = True
                elif away_full_match and not home_full_match:
                    is_home_pick = False
                elif home_full_match and away_full_match:
                    home_unique = [w for w in home_lower.split() if w not in away_lower.split() and len(w) > 2]
                    is_home_pick = any(w in side_lower for w in home_unique)
                else:
                    home_words = {w for w in home_lower.split() if len(w) > 3}
                    away_words = {w for w in away_lower.split() if len(w) > 3}
                    home_unique_words = home_words - away_words
                    away_unique_words = away_words - home_words
                    home_hit = any(w in side_lower for w in home_unique_words) if home_unique_words else False
                    away_hit = any(w in side_lower for w in away_unique_words) if away_unique_words else False
                    if home_hit and not away_hit:
                        is_home_pick = True
                    elif away_hit and not home_hit:
                        is_home_pick = False
                    else:
                        print(f"[Auto-grade] Cannot determine side for: {pick.side} ({pick.home_team} vs {pick.away_team})")
                        continue

                if is_home_pick:
                    ats_margin = spread_result + line_value
                else:
                    ats_margin = -spread_result + line_value

                if ats_margin == 0:
                    result_ats = 'P'
                    profit_units = 0.0
                    pnl = 0
                elif ats_margin > 0:
                    result_ats = 'W'
                    actual_odds = pick.market_odds or -110
                    if actual_odds < 0:
                        profit_units = round(100 / abs(actual_odds), 2)
                    else:
                        profit_units = round(actual_odds / 100, 2)
                    pnl = profit_units
                else:
                    result_ats = 'L'
                    profit_units = -1.0
                    pnl = -1.0

                if pick.result == 'pending':
                    pick.home_score = home_score
                    pick.away_score = away_score
                    pick.result = 'push' if result_ats == 'P' else ('win' if result_ats == 'W' else 'loss')
                    pick.result_ats = result_ats
                    pick.profit_units = profit_units
                    pick.pnl = pnl
                    pick.result_resolved_at = datetime.now()

                    print(f"[Auto-grade] {pick.game_date}: {pick.side} -> {pick.result} (score: {home_score}-{away_score})")

                    try:
                        from notification_service import send_result_notification
                        send_result_notification(pick, pick.result)
                    except Exception as e:
                        print(f"[Auto-grade] Result notification error: {e}")

                    try:
                        from notification_events import dispatch_result_emails
                        dispatch_result_emails(pick)
                    except Exception as e:
                        print(f"[Auto-grade] Result email dispatch error: {e}")
                else:
                    print(f"[Auto-grade] Pick already {pick.result} (score: {home_score}-{away_score}): grading {result_ats} for linked tracked bets only")

                linked_bets = TrackedBet.query.filter_by(pick_id=pick.id, result=None).all()
                for tb in linked_bets:
                    tb.result = result_ats
                    if result_ats == 'W':
                        if tb.odds < 0:
                            tb.profit = round(tb.bet_amount * (100 / abs(tb.odds)), 2)
                        else:
                            tb.profit = round(tb.bet_amount * (tb.odds / 100), 2)
                    elif result_ats == 'P':
                        tb.profit = 0.0
                    else:
                        tb.profit = -tb.bet_amount
                    tb.settled_at = datetime.now()
                    print(f"[Auto-grade] Tracked bet #{tb.id} for user {tb.user_id} -> {result_ats}")
                graded_count += 1
            except Exception as pick_err:
                logging.error(f"[Auto-grade] Error grading pick {pick.id} ({pick.away_team} @ {pick.home_team}): {pick_err}")
                continue

        try:
            orphaned = TrackedBet.query.filter(
                TrackedBet.result.is_(None),
                TrackedBet.pick_id.isnot(None)
            ).join(Pick, TrackedBet.pick_id == Pick.id).filter(
                Pick.result.in_(['win', 'loss', 'push'])
            ).all()
            for tb in orphaned:
                lp = tb.linked_pick
                tb.result = lp.result_ats or ('W' if lp.result == 'win' else ('L' if lp.result == 'loss' else 'P'))
                if tb.result == 'W':
                    if tb.odds and tb.odds < 0:
                        tb.profit = round(tb.bet_amount * (100 / abs(tb.odds)), 2)
                    elif tb.odds:
                        tb.profit = round(tb.bet_amount * (tb.odds / 100), 2)
                    else:
                        tb.profit = round(tb.bet_amount * (100 / 110), 2)
                elif tb.result == 'P':
                    tb.profit = 0.0
                else:
                    tb.profit = -(tb.bet_amount or 0)
                tb.settled_at = datetime.now()
                logging.info(f"[Auto-grade] Catch-up: bet #{tb.id} synced to {tb.result} from pick {tb.pick_id}")
        except Exception as catchup_err:
            logging.error(f"[Auto-grade] Catch-up error: {catchup_err}")

        # Safety net for withdrawn picks. The inline cascade in
        # model_service.revalidate_pretip handles the common path, but bets
        # created after a revoke, or picks revoked through other paths (admin
        # tools, future code), can leave tracked bets stranded as Pending.
        # The other catch-up loops above intentionally skip 'revoked', so
        # nothing else sweeps these.
        try:
            stranded_revoked = TrackedBet.query.filter(
                TrackedBet.result.is_(None),
                TrackedBet.pick_id.isnot(None),
            ).join(Pick, TrackedBet.pick_id == Pick.id).filter(
                Pick.result == 'revoked'
            ).all()
            for tb in stranded_revoked:
                tb.result = 'revoked'
                tb.profit = 0.0
                tb.settled_at = datetime.now()
                logging.info(f"[Auto-grade] Revoke sweep: bet #{tb.id} -> revoked from pick {tb.pick_id}")
        except Exception as sweep_err:
            logging.error(f"[Auto-grade] Revoke sweep error: {sweep_err}")

        if sqlite_conn:
            sqlite_conn.close()
        try:
            db.session.commit()
            logging.info(f"[Auto-grade] Committed {graded_count} graded picks")
        except Exception as commit_err:
            logging.error(f"[Auto-grade] Commit error: {commit_err}")
            db.session.rollback()

def collect_closing_lines():
    """Snapshot current lines as closing lines from local SQLite.
    Fetches all today's games, then filters for those tipping off within
    the next 10 minutes that haven't been scored yet.
    Does NOT re-fetch from external APIs — relies on refresh-lines cron
    to keep lines current."""
    with app.app_context():
        try:
            conn = get_sqlite_conn()
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            today_str = _get_et_today()
            now_utc = datetime.utcnow()
            now_iso = now_utc.strftime('%Y-%m-%dT%H:%M:%SZ')
            window_end = now_utc + timedelta(minutes=10)
            end_iso = window_end.strftime('%Y-%m-%dT%H:%M:%SZ')

            cursor.execute('''
                SELECT id, home_team, away_team, spread_home, total,
                       home_ml, away_ml, game_date, game_time,
                       home_score, spread_home_close
                FROM games
                WHERE game_date = ?
                AND game_time IS NOT NULL
                AND spread_home IS NOT NULL
            ''', (today_str,))

            all_today = cursor.fetchall()
            evaluated = 0
            updated = 0
            skipped_scored = 0
            skipped_outside = 0

            for game in all_today:
                gt = game['game_time']
                if gt < now_iso or gt > end_iso:
                    skipped_outside += 1
                    continue
                evaluated += 1
                if game['home_score'] is not None:
                    skipped_scored += 1
                    continue

                cursor.execute('''
                    UPDATE games SET
                        spread_home_close = ?,
                        total_close = ?,
                        home_ml_close = ?,
                        away_ml_close = ?,
                        close_collected_at = ?
                    WHERE id = ?
                ''', (game['spread_home'], game['total'],
                      game['home_ml'], game['away_ml'],
                      datetime.now().isoformat(), game['id']))

                try:
                    from performance_tracker import update_closing_line
                    update_closing_line(game['id'], game['spread_home'])
                except Exception:
                    pass
                updated += 1

                today_pick = Pick.query.filter(
                    Pick.home_team == game['home_team'],
                    Pick.away_team == game['away_team'],
                    Pick.game_date.like(f'{today_str}%')
                ).first()
                if today_pick:
                    closing = game['spread_home']
                    today_pick.line_close = closing
                    today_pick.closing_spread = closing
                    if today_pick.line is not None and closing is not None:
                        side = resolve_pick_side(today_pick)
                        if side is not None:
                            today_pick.clv = clv_points(
                                today_pick.line,
                                to_picked_perspective(closing, side),
                            )

            conn.commit()
            conn.close()
            db.session.commit()
            print(f"[{datetime.now()}] closing-lines: {len(all_today)} today, {evaluated} in window, {updated} snapshotted, {skipped_scored} already scored, {skipped_outside} outside window")
            return {
                'today_games': len(all_today),
                'evaluated': evaluated,
                'snapshotted': updated,
                'skipped_scored': skipped_scored,
                'skipped_outside': skipped_outside,
                'window': f'{now_iso} to {end_iso}',
            }
        except Exception as e:
            print(f"[{datetime.now()}] Closing line error: {e}")
            raise

def collect_wnba_games_job():
    """Run the WNBA data collector"""
    print(f"[{datetime.now()}] Running scheduled WNBA data collection...")
    try:
        from main import collect_wnba_scores, collect_wnba_odds, update_wnba_rolling_ratings
        collect_wnba_scores()
        collect_wnba_odds()
        update_wnba_rolling_ratings()
        print(f"[{datetime.now()}] WNBA data collection completed!")
    except Exception as e:
        print(f"[{datetime.now()}] WNBA collection error: {e}")

def collect_wnba_closing_lines_job():
    """Collect WNBA closing lines right before games start.
    First refreshes WNBA data from APIs, then snapshots current lines as closing lines."""
    print(f"[{datetime.now()}] Refreshing WNBA lines for closing snapshot...")
    try:
        from main import collect_wnba_closing_lines
        collect_wnba_closing_lines()
    except Exception as e:
        print(f"[{datetime.now()}] WNBA line refresh error (continuing): {e}")
    
    print(f"[{datetime.now()}] Capturing WNBA closing lines...")
    with app.app_context():
        try:
            conn = get_sqlite_conn()
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            today_str = _get_et_today()
            cursor.execute('''
                SELECT id, home_team, away_team, spread_home, total,
                       home_ml, away_ml
                FROM wnba_games
                WHERE game_date LIKE ?
                AND home_score IS NULL
                AND spread_home IS NOT NULL
            ''', (f'{today_str}%',))
            
            games = cursor.fetchall()
            updated = 0
            
            for game in games:
                cursor.execute('''
                    UPDATE wnba_games SET
                        spread_home_close = ?,
                        total_close = ?,
                        home_ml_close = ?,
                        away_ml_close = ?,
                        close_collected_at = ?
                    WHERE id = ?
                ''', (game['spread_home'], game['total'],
                      game['home_ml'], game['away_ml'],
                      datetime.now().isoformat(), game['id']))
                
                from performance_tracker import update_closing_line
                update_closing_line(game['id'], game['spread_home'])
                updated += 1

                today_pick = Pick.query.filter(
                    Pick.home_team == game['home_team'],
                    Pick.away_team == game['away_team'],
                    Pick.sport == 'wnba',
                    Pick.game_date.like(f'{today_str}%')
                ).first()
                if today_pick:
                    closing = game['spread_home']
                    if today_pick.line_close is None:
                        today_pick.line_close = closing
                    today_pick.closing_spread = closing
                    if today_pick.line is not None and closing is not None:
                        side = resolve_pick_side(today_pick)
                        if side is not None:
                            today_pick.clv = clv_points(
                                today_pick.line,
                                to_picked_perspective(closing, side),
                            )

            conn.commit()
            conn.close()
            db.session.commit()
            print(f"[{datetime.now()}] Captured WNBA closing lines for {updated} games")
        except Exception as e:
            print(f"[{datetime.now()}] WNBA closing line error: {e}")


def check_data_quality():
    """Run data quality checks — stale lines, duplicates, API health"""
    print(f"[{datetime.now()}] Running data quality checks...")
    issues = []
    
    try:
        conn = get_sqlite_conn()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        today_str = _get_et_today()

        from sport_config import get_live_sports
        sport_tables = {'nba': 'games', 'mlb': 'mlb_games', 'wnba': 'wnba_games'}

        for sport in get_live_sports():
            tbl = sport_tables.get(sport)
            if not tbl:
                continue
            label = sport.upper()

            cursor.execute(f'''
                SELECT COUNT(*) as cnt FROM {tbl}
                WHERE game_date LIKE ? AND spread_home IS NULL
            ''', (f'{today_str}%',))
            missing_spreads = cursor.fetchone()['cnt']
            if missing_spreads > 0:
                issues.append(f"WARN: {label} — {missing_spreads} games today missing spread data")

            cursor.execute(f'''
                SELECT home_team, away_team, COUNT(*) as cnt
                FROM {tbl} WHERE game_date LIKE ?
                GROUP BY home_team, away_team HAVING cnt > 1
            ''', (f'{today_str}%',))
            dupes = cursor.fetchall()
            for d in dupes:
                issues.append(f"WARN: {label} duplicate {d['away_team']}@{d['home_team']} ({d['cnt']}x)")

            cursor.execute(f'''
                SELECT collected_at FROM {tbl}
                WHERE game_date LIKE ?
                ORDER BY collected_at DESC LIMIT 1
            ''', (f'{today_str}%',))
            latest = cursor.fetchone()
            if latest and latest['collected_at']:
                from datetime import datetime as dt
                try:
                    collected = dt.fromisoformat(latest['collected_at'])
                    hours_old = (datetime.now() - collected).total_seconds() / 3600
                    if hours_old > 6:
                        issues.append(f"WARN: {label} lines are {hours_old:.1f}h old — may be stale")
                except Exception:
                    pass
        
        conn.close()
        
        if issues:
            for issue in issues:
                print(f"[Data Quality] {issue}")
            try:
                from notification_service import send_admin_health_alert
                send_admin_health_alert(
                    "Data Quality Issues",
                    " | ".join(issues)
                )
            except Exception as ne:
                print(f"[Data Quality] Admin alert error: {ne}")
        else:
            print(f"[{datetime.now()}] Data quality OK")
            
    except Exception as e:
        print(f"[Data Quality] Check failed: {e}")
        try:
            from notification_service import send_admin_health_alert
            send_admin_health_alert("Data Quality Check Failed", str(e)[:200])
        except Exception:
            pass


def grade_whatif_passes():
    """Grade what-if picks on passes by checking actual game results.
    Uses stored home_team/away_team/pick_side to match the correct game."""
    print(f"[{datetime.now()}] Grading what-if pass records...")
    with app.app_context():
        try:
            ungraded = Pass.query.filter(
                Pass.whatif_side.isnot(None),
                Pass.whatif_home_team.isnot(None),
                Pass.whatif_result.is_(None),
            ).all()

            if not ungraded:
                print(f"[{datetime.now()}] No ungraded what-if passes")
                return

            conn = get_sqlite_conn()
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            graded = 0
            for p in ungraded:
                tbl = 'wnba_games' if p.sport == 'wnba' else ('mlb_games' if p.sport == 'mlb' else 'games')
                cursor.execute(f'''
                    SELECT home_score, away_score, spread_home
                    FROM {tbl}
                    WHERE game_date LIKE ?
                    AND home_team = ?
                    AND away_team = ?
                    AND home_score IS NOT NULL
                ''', (f'{p.date}%', p.whatif_home_team, p.whatif_away_team))

                game = cursor.fetchone()
                if not game:
                    continue

                home_margin = game['home_score'] - game['away_score']
                spread = p.whatif_line if p.whatif_line is not None else 0
                side_str = (p.whatif_pick_side or '').lower()
                home_str = (p.whatif_home_team or '').lower()
                is_home_pick = home_str in side_str or any(
                    word in side_str for word in home_str.split() if len(word) > 3
                )

                ats_margin = home_margin + spread if is_home_pick else -(home_margin + spread)
                if ats_margin > 0:
                    covered = True
                elif ats_margin < 0:
                    covered = False
                else:
                    covered = None

                if covered is not None:
                    p.whatif_result = 'win' if covered else 'loss'
                    p.whatif_covered = covered
                else:
                    p.whatif_result = 'push'
                    p.whatif_covered = None
                graded += 1

            conn.close()
            db.session.commit()
            print(f"[{datetime.now()}] Graded {graded} what-if passes")
        except Exception as e:
            print(f"[{datetime.now()}] What-if grading error: {e}")


def check_expiring_trials():
    """Send warning email to users whose trial expires in 2 days"""
    with app.app_context():
        try:
            two_days = datetime.now() + timedelta(days=2)
            expiring = User.query.filter(
                User.subscription_status == 'trial',
                User.trial_end_date <= two_days,
                User.trial_end_date > datetime.now(),
                User.trial_warning_sent == False
            ).all()
            for user in expiring:
                try:
                    from email_service import send_trial_expiring_email
                    picks = Pick.query.filter_by(result='win').count()
                    losses = Pick.query.filter_by(result='loss').count()
                    record = f"{picks}W-{losses}L published picks"
                    founding_count = User.query.filter_by(founding_member=True).count()
                    spots = 50 - founding_count
                    send_trial_expiring_email(user.email, user.first_name, user.trial_end_date, record, spots)
                    user.trial_warning_sent = True
                except Exception as e:
                    logging.error(f"Trial expiring email failed for {user.email}: {e}")
                try:
                    from notification_service import send_trial_expiring_notification
                    days_left = max(1, (user.trial_end_date - datetime.now()).days)
                    send_trial_expiring_notification(user, days_left)
                except Exception as e:
                    logging.error(f"Trial expiring push failed for {user.email}: {e}")
            db.session.commit()
            if expiring:
                logging.info(f"Sent {len(expiring)} trial expiring warnings")
        except Exception as e:
            logging.error(f"check_expiring_trials error: {e}")


def expire_trials():
    """Flip is_premium to false for expired trials"""
    with app.app_context():
        try:
            expired = User.query.filter(
                User.subscription_status == 'trial',
                User.trial_end_date <= datetime.now()
            ).all()
            for user in expired:
                user.subscription_status = 'expired'
                user.is_premium = False
                try:
                    from email_service import send_trial_expired_email
                    send_trial_expired_email(user.email, user.first_name)
                except Exception as e:
                    logging.error(f"Trial expired email failed for {user.email}: {e}")
            db.session.commit()
            if expired:
                logging.info(f"Expired {len(expired)} trials")
        except Exception as e:
            logging.error(f"expire_trials error: {e}")


import time as _time

_cron_locks = {}
_cron_lock_mutex = threading.Lock()

CRON_MIN_INTERVAL = {
    'admin_alert': 7200,
    'closing_lines': 60,
    'refresh_lines': 300,
    'collect_games': 600,
    'grade_picks': 300,
    'grade_whatifs': 300,
    'pretip_validate': 300,
    'run_model': 600,
    'model_watchdog': 300,
    'wnba_collect': 600,
    'wnba_closing_lines': 60,
    'wnba_shadow': 600,
    'wnba_grade': 300,
    'mlb_collect': 600,
    'mlb_closing_lines': 60,
    'mlb_run_model': 600,
    'mlb_grade': 300,
    'mlb_retrain': 86400,
    'mlb_backfill': 0,
    'mlb_validate': 0,
    'retrain_model': 86400,
    'nba_scores': 86400,
}

def _run_cron_sync(job_name, fn):
    """Execute cron job synchronously, log result. Used by both sync and async paths."""
    start = _time.time()
    try:
        result = fn()
        dur = int((_time.time() - start) * 1000)
        log = CronLog(job_name=job_name, status='ok', duration_ms=dur,
                      message=str(result) if result else None)
        db.session.add(log)
        db.session.commit()
        logging.info(f"[cron] {job_name} completed in {dur}ms")
        return {'status': 'done', 'job': job_name, 'duration_ms': dur, **(result if isinstance(result, dict) else {})}
    except Exception as e:
        dur = int((_time.time() - start) * 1000)
        log = CronLog(job_name=job_name, status='error', duration_ms=dur,
                      message=str(e)[:500])
        try:
            db.session.add(log)
            db.session.commit()
        except Exception:
            db.session.rollback()
        try:
            send_admin_alert(
                f"Cron Failed: {job_name}",
                f"{job_name} failed after {dur}ms: {str(e)[:200]}",
                {'job': job_name, 'error': str(e)[:200]}
            )
        except Exception:
            logging.error(f"Failed to send admin alert for cron error: {job_name}")
        logging.error(f"[cron] {job_name} failed after {dur}ms: {e}")
        return {'status': 'error', 'job': job_name, 'message': str(e)}
    finally:
        with _cron_lock_mutex:
            _cron_locks[job_name] = (_time.time(), False)


def _check_throttle_and_lock(job_name, skip_throttle=False):
    """Check throttle and acquire lock. Returns (ok, response) — if ok is False, return response."""
    min_interval = CRON_MIN_INTERVAL.get(job_name, 0)
    if min_interval and not skip_throttle:
        last_ok = CronLog.query.filter_by(job_name=job_name, status='ok')\
            .order_by(CronLog.executed_at.desc()).first()
        if last_ok:
            seconds_since = (datetime.utcnow() - last_ok.executed_at).total_seconds()
            if seconds_since < min_interval:
                return False, (jsonify({'status': 'skipped', 'job': job_name,
                                'reason': f'throttled ({int(seconds_since)}s since last run, min {min_interval}s)'}), 200)

    with _cron_lock_mutex:
        now = _time.time()
        if job_name in _cron_locks:
            lock_time, running = _cron_locks[job_name]
            if running:
                stale_seconds = now - lock_time
                if stale_seconds < 600:
                    return False, (jsonify({'status': 'skipped', 'job': job_name,
                                    'reason': f'already running ({int(stale_seconds)}s)'}), 200)
                logging.warning(f"[cron] Force-clearing stale lock for {job_name} (held {int(stale_seconds)}s)")
        _cron_locks[job_name] = (now, True)

    return True, None


def log_cron(job_name, fn, skip_throttle=False):
    ok, resp = _check_throttle_and_lock(job_name, skip_throttle)
    if not ok:
        return resp

    result = _run_cron_sync(job_name, fn)
    if result.get('status') == 'error':
        return jsonify(result), 500
    return jsonify(result)


def log_cron_async(job_name, fn, skip_throttle=False):
    """Fire-and-forget: return 202 immediately, run job in background thread.
    Use for endpoints that take >30s (collection jobs hitting external APIs)."""
    import threading

    ok, resp = _check_throttle_and_lock(job_name, skip_throttle)
    if not ok:
        return resp

    def _background():
        with app.app_context():
            _run_cron_sync(job_name, fn)

    t = threading.Thread(target=_background, daemon=True)
    t.start()
    return jsonify({'status': 'accepted', 'job': job_name, 'message': 'Running in background'}), 202


INTERNAL_EMAILS = [
    e.strip().lower()
    for e in os.environ.get('INTERNAL_EMAILS', 'evan@sharppicks.ai').split(',')
    if e.strip()
]

EVENTS_DEDUPE_WINDOW_SECONDS = 60


def _events_client_ip():
    fwd = request.headers.get('X-Forwarded-For', '')
    if fwd:
        return fwd.split(',')[0].strip()
    return request.remote_addr


def _events_parse_body():
    """Parse JSON regardless of Content-Type. sendBeacon sends text/plain
    with a JSON body; fetch sends application/json. Both land here."""
    raw = request.get_data(as_text=True)
    if not raw:
        raise ValueError('empty body')
    return json.loads(raw)


def _events_parse_client_ts(s):
    if not s or not isinstance(s, str):
        return None
    s = s.strip()
    if s.endswith('Z'):
        s = s[:-1] + '+00:00'
    try:
        return datetime.fromisoformat(s)
    except ValueError:
        return None


def _events_is_dup(event_type, client_ts, signal_id, surface, ip):
    """60-second idempotency window keyed on
    (event_type, client_ts, signal_id, surface, ip). Without a client_ts
    the dedupe key is undefined; pass through."""
    if not client_ts:
        return False
    cutoff = datetime.utcnow() - timedelta(seconds=EVENTS_DEDUPE_WINDOW_SECONDS)
    q = UserEvent.query.filter(
        UserEvent.event_type == event_type,
        UserEvent.client_ts == client_ts,
        UserEvent.created_at >= cutoff,
    )
    q = q.filter(UserEvent.signal_id.is_(None) if signal_id is None else UserEvent.signal_id == signal_id)
    q = q.filter(UserEvent.surface.is_(None)   if surface   is None else UserEvent.surface   == surface)
    q = q.filter(UserEvent.ip.is_(None)        if ip        is None else UserEvent.ip        == ip)
    return db.session.query(q.exists()).scalar()


@app.route('/api/events', methods=['POST'])
def post_user_events():
    # NOTE: This endpoint returns HTTP 200 with {"ok": true} (NOT 204 No Content)
    # by deliberate design. Returning 200 with {'ok': true} instead of 204 is a
    # deliberate concession to single-deploy architecture. Frontend bundle and
    # Flask backend ship in one Railway artifact, so we cannot land a
    # client-side 204 handler before the server starts returning 204. Browser
    # tabs already loaded at deploy time would hit the new server with the old
    # client (no 204 handler), eventTracker would fail to parse the empty body,
    # and the retry queue would back up until the user reloaded. The
    # 200-with-body shape is parseable by every version of the client. Do not
    # change to 204 without solving the sticky-tab transition first.

    # No auth wall. Session attached if present, anonymous otherwise.
    try:
        body = _events_parse_body()
    except (ValueError, json.JSONDecodeError):
        return jsonify({'error': 'Invalid JSON'}), 400
    if not isinstance(body, dict):
        return jsonify({'error': 'Expected JSON object'}), 400

    # Two accepted shapes:
    #   new (single):  { event, surface, signal_id, sport, client_ts, ... }
    #   old (batch):   { events: [ { event_type, event_data, ... }, ... ] }
    if isinstance(body.get('events'), list):
        events = body['events']
    elif isinstance(body.get('event'), str):
        events = [body]
    else:
        return jsonify({'error': 'Expected {event:...} or {events:[...]}'}), 400
    if len(events) > 100:
        return jsonify({'error': 'Maximum 100 events per request'}), 400

    user = None
    try:
        user = get_current_user_from_session()
    except Exception:
        logging.exception('post_user_events: session lookup failed')
        user = None
    user_id = (user or {}).get('id')
    user_email = ((user or {}).get('email') or '').lower()
    # Email allowlist (legacy), plus the User.is_internal column added in
    # the 2026-05-03 migration. Either path flags the event as internal so
    # admin metrics can exclude it.
    is_internal = bool(user_email) and user_email in INTERNAL_EMAILS
    if not is_internal and user_id:
        db_user = db.session.get(User, user_id)
        if db_user and db_user.is_internal:
            is_internal = True

    ip = _events_client_ip()
    user_agent = (request.headers.get('User-Agent') or '')[:500]
    server_now = datetime.utcnow()

    rows = []
    deduped = 0
    for raw_ev in events:
        if not isinstance(raw_ev, dict):
            return jsonify({'error': 'each event must be an object'}), 400

        et = (raw_ev.get('event') or raw_ev.get('event_type') or '').strip()
        if not et or len(et) > 50:
            return jsonify({'error': 'event/event_type required, max 50 chars'}), 400
        surface = raw_ev.get('surface')
        signal_id = raw_ev.get('signal_id')
        sport = raw_ev.get('sport')
        client_ts = _events_parse_client_ts(raw_ev.get('client_ts') or raw_ev.get('timestamp'))
        page = (raw_ev.get('page') or '')[:100] or None
        sid = (raw_ev.get('session_id') or '')[:64] or None
        if 'event_data' in raw_ev and isinstance(raw_ev['event_data'], dict):
            event_data = raw_ev['event_data']
        else:
            event_data = {k: v for k, v in raw_ev.items()
                          if k not in {'event', 'event_type', 'surface', 'signal_id',
                                       'sport', 'client_ts', 'timestamp', 'page', 'session_id'}}

        if _events_is_dup(et, client_ts, signal_id, surface, ip):
            deduped += 1
            continue

        rows.append(UserEvent(
            user_id=user_id,
            event_type=et,
            event_data=event_data,
            page=page,
            session_id=sid,
            surface=surface,
            is_internal=is_internal,
            signal_id=signal_id,
            sport=sport,
            client_ts=client_ts,
            ip=ip,
            user_agent=user_agent,
            created_at=server_now,
        ))

    if rows:
        try:
            db.session.add_all(rows)
            db.session.commit()
        except Exception:
            db.session.rollback()
            logging.exception('post_user_events failed')
            return jsonify({'error': 'Failed to save events'}), 500

    return jsonify({'ok': True}), 200


@app.route('/api/cron/diagnostic', methods=['GET', 'POST'])
@verify_cron
def cron_diagnostic():
    """Quick diagnostic: recent cron logs + game counts. Protected by cron secret."""
    try:
        today_str = _get_et_today()
        diag = {'date': today_str, 'db_path': get_sqlite_path()}

        try:
            logs = CronLog.query.order_by(CronLog.executed_at.desc()).limit(20).all()
            diag['cron_logs'] = [{
                'job': l.job_name, 'status': l.status, 'dur_ms': l.duration_ms,
                'at': l.executed_at.isoformat() if l.executed_at else None,
                'msg': (l.message or '')[:200],
            } for l in logs]
        except Exception as e:
            diag['cron_logs_error'] = str(e)

        try:
            conn = get_sqlite_conn()
            cur = conn.cursor()
            for tbl in ['games', 'mlb_games', 'wnba_games']:
                try:
                    total = cur.execute(f"SELECT COUNT(*) FROM {tbl} WHERE game_date = ?", (today_str,)).fetchone()[0]
                    with_spread = cur.execute(f"SELECT COUNT(*) FROM {tbl} WHERE game_date = ? AND spread_home IS NOT NULL", (today_str,)).fetchone()[0]
                    scored = cur.execute(f"SELECT COUNT(*) FROM {tbl} WHERE home_score IS NOT NULL").fetchone()[0]
                    all_rows = cur.execute(f"SELECT COUNT(*) FROM {tbl}").fetchone()[0]
                    diag[tbl] = {'date': today_str, 'total': total, 'with_spreads': with_spread, 'all_rows': all_rows, 'scored': scored}
                except Exception as e:
                    diag[tbl] = {'error': str(e)}
            conn.close()
        except Exception as e:
            diag['sqlite_error'] = str(e)

        try:
            for sport in ['nba', 'mlb', 'wnba']:
                pick = Pick.query.filter_by(game_date=today_str, sport=sport).first()
                pass_entry = Pass.query.filter_by(date=today_str, sport=sport).first()
                diag[f'{sport}_today'] = {
                    'pick': {'id': pick.id, 'side': pick.side, 'edge': pick.edge_pct} if pick else None,
                    'pass': {'id': pass_entry.id, 'reason': (pass_entry.pass_reason or '')[:100]} if pass_entry else None,
                }
        except Exception as e:
            diag['picks_error'] = str(e)

        try:
            conn = get_sqlite_conn()
            cur = conn.cursor()
            if cur.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='team_ratings'").fetchone():
                count = cur.execute("SELECT COUNT(*) FROM team_ratings").fetchone()[0]
                sample = cur.execute("SELECT team_abbr, net_rating, pace, last_updated FROM team_ratings ORDER BY net_rating DESC LIMIT 3").fetchall()
                diag['team_ratings'] = {'count': count, 'top_3': [{'abbr': r[0], 'net': r[1], 'pace': r[2], 'updated': r[3]} for r in sample]}
            else:
                diag['team_ratings'] = {'error': 'table does not exist'}
            if cur.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='player_impact_cache'").fetchone():
                pic_count = cur.execute("SELECT COUNT(*) FROM player_impact_cache").fetchone()[0]
                diag['player_impact_cache'] = {'count': pic_count}
            else:
                diag['player_impact_cache'] = {'error': 'table does not exist'}
            if cur.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='line_snapshots'").fetchone():
                snap_count = cur.execute("SELECT COUNT(*) FROM line_snapshots WHERE game_date = ?", (today_str,)).fetchone()[0]
                diag['line_snapshots'] = {'today_total': snap_count}
            else:
                diag['line_snapshots'] = {'error': 'table does not exist'}
            conn.close()
        except Exception as e:
            diag['cache_check_error'] = str(e)

        try:
            from model import EnsemblePredictor
            model_files = {}
            for sport in ['nba', 'mlb', 'wnba']:
                m = EnsemblePredictor(sport=sport)
                fp = m._default_filepath()
                model_files[sport] = {
                    'path': fp,
                    'exists': os.path.isfile(fp),
                    'size_kb': round(os.path.getsize(fp) / 1024, 1) if os.path.isfile(fp) else 0,
                }
            diag['model_files'] = model_files
        except Exception as e:
            diag['model_files_error'] = str(e)

        return jsonify(diag)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/cron/diagnose-bdl-conf-rank', methods=['GET', 'POST'])
@verify_cron
def cron_diagnose_bdl_conf_rank():
    """One-shot diagnostic to verify NBA bdl_*_conf_rank columns are NULL on prod.

    Gates the BDL Option 2 deletion (W6 investigation, Apr 2026). To be removed
    in a follow-up commit after Phase 5 lands.
    """
    try:
        conn = get_sqlite_conn()
        cur = conn.execute(
            "SELECT COUNT(*) AS total, "
            "       SUM(CASE WHEN bdl_home_conf_rank IS NOT NULL THEN 1 ELSE 0 END) AS home_non_null, "
            "       SUM(CASE WHEN bdl_away_conf_rank IS NOT NULL THEN 1 ELSE 0 END) AS away_non_null "
            "FROM games WHERE home_score IS NOT NULL"
        )
        row = cur.fetchone()
        conn.close()
        total = int(row[0] or 0)
        home_non_null = int(row[1] or 0)
        away_non_null = int(row[2] or 0)
        return jsonify({
            'total_completed_games': total,
            'home_non_null_conf_rank': home_non_null,
            'away_non_null_conf_rank': away_non_null,
            'verdict': 'safe_to_drop' if (home_non_null == 0 and away_non_null == 0) else 'investigate_before_dropping',
        })
    except Exception as e:
        logging.error(f"diagnose_bdl_conf_rank failed: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@app.route('/api/cron/model-audit', methods=['GET', 'POST'])
@verify_cron
def cron_model_audit():
    """Deep model diagnostic: sigma, edges, cover probs, feature counts for all live sports."""
    import traceback as _tb
    try:
        from model import EnsemblePredictor
        only_sport = request.args.get('sport', '').lower() or None
        predict = request.args.get('predict', '').lower() != 'false'
        audit = {}
        target_sports = [only_sport] if only_sport else get_live_sports()
        for sport in target_sports:
            try:
                model = EnsemblePredictor(sport=sport)
                model.load_model()
                filepath = model._default_filepath()
                file_size = round(os.path.getsize(filepath) / 1024, 1) if os.path.exists(filepath) else 0

                def _safe(v):
                    import numpy as np
                    if isinstance(v, (np.bool_, np.integer)):
                        return int(v)
                    if isinstance(v, np.floating):
                        return float(v)
                    return v

                info = {
                    'trained': bool(model.trained),
                    'file_size_kb': file_size,
                    'n_models': len(model.models),
                    'model_names': list(model.models.keys()),
                    'n_features': len(model.feature_names),
                    'feature_names': list(model.feature_names) if model.feature_names else [],
                    'dropped_features': list(getattr(model, 'dropped_features', [])),
                    'dropped_features_by_category': dict(getattr(model, 'dropped_features_by_category', {})),
                    'candidate_features': len(model.feature_names) + len(getattr(model, 'dropped_features', [])) if model.feature_names else 0,
                    'margin_std': _safe(getattr(model, 'margin_std', None)),
                    'margin_mae': _safe(getattr(model, 'margin_mae', None)),
                    'using_fallback_sigma': bool(getattr(model, 'using_fallback_sigma', False)),
                    'trained_at': getattr(model, 'trained_at', None),
                    'edge_threshold': float(model.edge_threshold_pct),
                    'max_edge': float(model.max_edge_pct),
                    'model_weight': float(model.model_weight),
                    'sigma_config': float(model.margin_std_dev),
                    'sigma_floor': float(model.margin_std_floor),
                    'sigma_ceiling': float(model.margin_std_ceiling),
                }

                if model.trained and predict:
                    try:
                        preds = model.predict_games(min_confidence=0, log_predictions=False, min_minutes_to_tip=0)
                        games = []
                        for p in preds:
                            games.append({
                                'matchup': f"{p.get('away_team','')} @ {p.get('home_team','')}",
                                'spread': p.get('spread'),
                                'cover_prob': round(p.get('cover_prob', 0), 4),
                                'raw_edge': round(p.get('raw_edge', 0), 2),
                                'adjusted_edge': round(p.get('adjusted_edge', 0), 2),
                                'z_score': p.get('z_score'),
                                'model_margin': round(p.get('predicted_margin', 0), 1),
                                'market_margin': round(p.get('market_margin', 0), 1) if p.get('market_margin') is not None else None,
                                'confidence_label': p.get('confidence_label', ''),
                            })
                        info['predictions'] = sorted(games, key=lambda x: abs(x.get('adjusted_edge', 0)), reverse=True)
                        info['n_games_predicted'] = len(games)
                        edges = [g['adjusted_edge'] for g in games]
                        info['avg_edge'] = round(sum(edges) / len(edges), 2) if edges else 0
                        info['max_raw_edge'] = max([g['raw_edge'] for g in games], default=0)
                        above_thresh = [g for g in games if g['adjusted_edge'] >= model.edge_threshold_pct]
                        info['games_above_threshold'] = len(above_thresh)
                    except Exception as e:
                        info['predict_error'] = str(e)
                        info['predict_traceback'] = _tb.format_exc()[-800:]

                audit[sport] = info
            except Exception as e:
                audit[sport] = {'error': str(e), 'traceback': _tb.format_exc()[-800:]}
        return jsonify(audit)
    except Exception as e:
        return jsonify({'fatal_error': str(e), 'traceback': _tb.format_exc()[-800:]}), 500


@app.route('/api/cron/backfill-nba-scores', methods=['GET', 'POST'])
@verify_cron
def cron_backfill_nba_scores():
    """Backfill NBA scores for the last N days (default 200). Run once to fill historical gaps."""
    days = int(request.args.get('days', '200'))
    sync = request.args.get('sync', '').lower() == 'true'
    def _backfill():
        from main import collect_yesterdays_scores
        filled = 0
        errors = 0
        for offset in range(1, days + 1):
            try:
                collect_yesterdays_scores(date_offset=offset)
                filled += 1
            except Exception as e:
                errors += 1
                logging.warning(f"[backfill] day-{offset} error: {e}")
        return {'filled_days': filled, 'errors': errors, 'range_days': days}
    if sync:
        return log_cron('backfill_nba_scores', _backfill, skip_throttle=True)
    return log_cron_async('backfill_nba_scores', _backfill, skip_throttle=True)


@app.route('/api/cron/nba-scores', methods=['GET', 'POST'])
@verify_cron
def cron_nba_scores():
    """Collect yesterday's NBA scores from ESPN. Run daily at 10:00 ET."""
    def _collect():
        from main import collect_yesterdays_scores
        collect_yesterdays_scores(date_offset=1)
        return {'status': 'ok'}
    return log_cron('nba_scores', _collect)


@app.route('/api/cron/label-pre-training-era', methods=['GET', 'POST'])
@verify_cron
def cron_label_pre_training():
    """One-time: label all picks before 2026-04-01 as pre-training era."""
    PRE_TRAINING_CUTOFF = '2026-04-01'
    with app.app_context():
        updated = Pick.query.filter(
            Pick.game_date < PRE_TRAINING_CUTOFF,
            Pick.model_era.is_(None),
        ).update({'model_era': 'pre-training'}, synchronize_session=False)
        db.session.commit()
    return jsonify({'labeled': updated, 'cutoff': PRE_TRAINING_CUTOFF})


@app.route('/api/cron/collect-games', methods=['GET', 'POST'])
@verify_cron
def cron_collect_games():
    return log_cron_async('collect_games', collect_todays_games)


@app.route('/api/cron/refresh-lines', methods=['GET', 'POST'])
@verify_cron
def cron_refresh_lines():
    force = request.args.get('force', '').lower() == 'true'
    return log_cron_async('refresh_lines', collect_todays_games, skip_throttle=force)


def _grade_picks_for_final_games(final_games):
    """Immediately grade pending picks for games that just went final.
    Called from the live-scores cron when a game transitions to STATUS_FINAL."""
    from sqlalchemy import or_, and_
    with app.app_context():
        graded = 0
        for fg in final_games:
            sport, home_team, away_team = fg['sport'], fg['home_team'], fg['away_team']
            home_score, away_score = fg['home_score'], fg['away_score']

            revoked_with_bets = db.session.query(Pick.id).join(
                TrackedBet, TrackedBet.pick_id == Pick.id
            ).filter(Pick.result == 'revoked', TrackedBet.result.is_(None),
                     Pick.home_team == home_team, Pick.away_team == away_team).distinct().subquery()

            picks = Pick.query.filter(
                Pick.home_team == home_team,
                Pick.away_team == away_team,
                or_(
                    Pick.result == 'pending',
                    Pick.id.in_(db.session.query(revoked_with_bets.c.id))
                )
            ).all()

            for pick in picks:
                spread_result = home_score - away_score
                line_value = pick.line if pick.line and abs(pick.line) < 50 else 0

                side_lower = (pick.side or '').lower()
                home_lower = (pick.home_team or '').lower()
                away_lower = (pick.away_team or '').lower()

                home_full_match = home_lower in side_lower
                away_full_match = away_lower in side_lower

                if home_full_match and not away_full_match:
                    is_home_pick = True
                elif away_full_match and not home_full_match:
                    is_home_pick = False
                elif home_full_match and away_full_match:
                    home_unique = [w for w in home_lower.split() if w not in away_lower.split() and len(w) > 2]
                    is_home_pick = any(w in side_lower for w in home_unique)
                else:
                    home_words = {w for w in home_lower.split() if len(w) > 3}
                    away_words = {w for w in away_lower.split() if len(w) > 3}
                    home_unique_words = home_words - away_words
                    away_unique_words = away_words - home_words
                    home_hit = any(w in side_lower for w in home_unique_words) if home_unique_words else False
                    away_hit = any(w in side_lower for w in away_unique_words) if away_unique_words else False
                    if home_hit and not away_hit:
                        is_home_pick = True
                    elif away_hit and not home_hit:
                        is_home_pick = False
                    else:
                        logging.warning(f"[Live-grade] Cannot determine side: {pick.side}")
                        continue

                if is_home_pick:
                    ats_margin = spread_result + line_value
                else:
                    ats_margin = -spread_result + line_value

                if ats_margin == 0:
                    result_ats, profit_units = 'P', 0.0
                elif ats_margin > 0:
                    result_ats = 'W'
                    actual_odds = pick.market_odds or -110
                    if actual_odds < 0:
                        profit_units = round(100 / abs(actual_odds), 2)
                    else:
                        profit_units = round(actual_odds / 100, 2)
                else:
                    result_ats, profit_units = 'L', -1.0

                is_revoked = pick.result == 'revoked'

                if not is_revoked:
                    pick.home_score = home_score
                    pick.away_score = away_score
                    pick.result = 'push' if result_ats == 'P' else ('win' if result_ats == 'W' else 'loss')
                    pick.result_ats = result_ats
                    pick.profit_units = profit_units
                    pick.pnl = profit_units
                    pick.result_resolved_at = datetime.now()
                    logging.info(f"[Live-grade] {pick.side} → {pick.result} ({away_team} {away_score} @ {home_team} {home_score})")

                    try:
                        from notification_service import send_result_notification
                        send_result_notification(pick, pick.result)
                    except Exception as e:
                        logging.error(f"[Live-grade] Notification error: {e}")

                    try:
                        from notification_events import dispatch_result_emails
                        dispatch_result_emails(pick)
                    except Exception as e:
                        logging.error(f"[Live-grade] Email error: {e}")

                linked_bets = TrackedBet.query.filter_by(pick_id=pick.id, result=None).all()
                for tb in linked_bets:
                    tb.result = result_ats
                    if result_ats == 'W':
                        if tb.odds < 0:
                            tb.profit = round(tb.bet_amount * (100 / abs(tb.odds)), 2)
                        else:
                            tb.profit = round(tb.bet_amount * (tb.odds / 100), 2)
                    elif result_ats == 'P':
                        tb.profit = 0.0
                    else:
                        tb.profit = -tb.bet_amount
                    tb.settled_at = datetime.now()

                graded += 1

        if graded:
            db.session.commit()
            logging.info(f"[Live-grade] Graded {graded} picks from {len(final_games)} final games")


@app.route('/api/cron/live-scores', methods=['GET', 'POST'])
@verify_cron
def cron_live_scores():
    """Poll ESPN for live scores every 5 min during game windows. Persists to SQLite."""
    def _poll_live():
        from datetime import datetime, timedelta
        from zoneinfo import ZoneInfo
        from sport_config import get_live_sports, get_espn_scoreboard_url
        from main import setup_database
        import requests as http_requests

        setup_database()

        et = ZoneInfo('America/New_York')
        now_et = datetime.now(et)
        updated_total = 0
        errors = []

        for sport in get_live_sports():
            table = 'games' if sport == 'nba' else f'{sport}_games'
            conn = get_sqlite_conn()
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            try:
                utc_now = now_et.astimezone(ZoneInfo('UTC')).strftime('%Y-%m-%dT%H:%M:%SZ')
                cursor.execute(f"""UPDATE {table} SET game_status = NULL, home_score = NULL, away_score = NULL
                                  WHERE game_date = ? AND game_status IN ('final', 'in_progress')
                                  AND game_time > ?""",
                               (now_et.strftime('%Y-%m-%d'), utc_now))
                cleaned = cursor.rowcount
                cursor.execute(f"""UPDATE {table} SET home_score = NULL, away_score = NULL
                                  WHERE game_date = ? AND home_score IS NOT NULL
                                  AND game_time > ? AND (game_status IS NULL OR game_status = 'scheduled')""",
                               (now_et.strftime('%Y-%m-%d'), utc_now))
                cleaned += cursor.rowcount
                if cleaned > 0:
                    conn.commit()
                    logging.info(f"Live scores: reset {cleaned} stale {sport} games that haven't started yet")
            except Exception as e:
                logging.warning(f"Live scores stale cleanup error for {sport}: {e}")

            try:
                cursor.execute(f"SELECT id, home_team, away_team, game_time, commence_time, game_status FROM {table} WHERE game_date = ?",
                               (now_et.strftime('%Y-%m-%d'),))
            except Exception:
                cursor.execute(f"SELECT id, home_team, away_team, game_time, commence_time FROM {table} WHERE game_date = ?",
                               (now_et.strftime('%Y-%m-%d'),))
            today_games = cursor.fetchall()

            if not today_games:
                conn.close()
                continue

            has_active = True
            try:
                has_active = any(r['game_status'] in (None, 'scheduled', 'in_progress') for r in today_games)
            except (KeyError, IndexError):
                pass
            if not has_active:
                conn.close()
                continue

            try:
                espn_url = get_espn_scoreboard_url(sport, now_et.strftime('%Y-%m-%d'))
                resp = http_requests.get(espn_url, timeout=10)
                resp.raise_for_status()
                espn_data = resp.json()
            except Exception as e:
                logging.warning(f"Live scores ESPN fetch failed for {sport}: {e}")
                conn.close()
                continue

            espn_games_by_matchup = {}
            espn_games_by_home = {}
            for event in espn_data.get('events', []):
                try:
                    comp = event.get('competitions', [{}])[0]
                    status = comp.get('status', {})
                    status_type = status.get('type', {})
                    competitors = comp.get('competitors', [])
                    home = away = None
                    for c in competitors:
                        if c.get('homeAway') == 'home':
                            home = c
                        else:
                            away = c
                    if not home or not away:
                        continue
                    home_name = home.get('team', {}).get('displayName', '')
                    away_name = away.get('team', {}).get('displayName', '')
                    game_data_espn = {
                        'home_name': home_name,
                        'away_name': away_name,
                        'home_score': int(home.get('score', 0) or 0),
                        'away_score': int(away.get('score', 0) or 0),
                        'state': status_type.get('name', ''),
                        'period': int(status.get('period', 0) or 0),
                        'clock': status.get('displayClock', ''),
                    }
                    matchup_key = f"{away_name.lower().replace(' ', '')}@{home_name.lower().replace(' ', '')}"
                    home_key = home_name.lower().replace(' ', '')
                    espn_games_by_matchup[matchup_key] = game_data_espn
                    espn_games_by_home[home_key] = game_data_espn
                except Exception as e:
                    logging.warning(f"Live scores: skipping malformed ESPN event for {sport}: {e}")
                    continue

            updated = 0
            newly_final = []
            for row in today_games:
                try:
                    game_id, home_team, away_team = row['id'], row['home_team'], row['away_team']
                    matchup_key = f"{away_team.lower().replace(' ', '')}@{home_team.lower().replace(' ', '')}"
                    home_key = home_team.lower().replace(' ', '')
                    live = espn_games_by_matchup.get(matchup_key) or espn_games_by_home.get(home_key)
                    if not live:
                        continue

                    state = live['state']
                    if state == 'STATUS_FINAL':
                        game_status = 'final'
                    elif state in ('STATUS_IN_PROGRESS', 'STATUS_HALFTIME'):
                        game_status = 'in_progress'
                    else:
                        game_status = 'scheduled'

                    if game_status == 'scheduled':
                        continue

                    prev_status = None
                    try:
                        prev_status = row['game_status']
                    except (KeyError, IndexError):
                        pass
                    if game_status == 'final' and prev_status != 'final':
                        newly_final.append({
                            'sport': sport,
                            'home_team': home_team,
                            'away_team': away_team,
                            'home_score': live['home_score'],
                            'away_score': live['away_score'],
                        })

                    period_str = None
                    if live['period'] and live['period'] > 0:
                        if sport == 'mlb':
                            half = 'Top' if live['clock'] == '' else 'Bot'
                            period_str = f"{half} {live['period']}"
                        else:
                            period_str = f"Q{live['period']}" if live['period'] <= 4 else f"OT{live['period'] - 4}"

                    cursor.execute(f"""UPDATE {table} SET
                        game_status = ?, current_period = ?, game_clock = ?,
                        home_score = ?, away_score = ?, scores_updated_at = ?
                        WHERE id = ?""",
                        (game_status, period_str, live['clock'],
                         live['home_score'], live['away_score'],
                         now_et.isoformat(), game_id))
                    updated += 1
                except Exception as e:
                    logging.warning(f"Live scores: error processing {sport} game {row.get('id', '?')}: {e}")
                    errors.append(f"{sport}:{row.get('id', '?')}:{e}")

            conn.commit()
            conn.close()
            updated_total += updated
            if updated:
                logging.info(f"Live scores: updated {updated} {sport} games")

            if newly_final:
                try:
                    _grade_picks_for_final_games(newly_final)
                except Exception as e:
                    logging.error(f"Live auto-grade error: {e}")

        return {'updated': updated_total, 'errors': errors[:5] if errors else None}

    return log_cron_async('live_scores', _poll_live)


@app.route('/api/cron/closing-lines', methods=['GET', 'POST'])
@verify_cron
def cron_closing_lines():
    return log_cron_async('closing_lines', collect_closing_lines)


@app.route('/api/cron/refresh-player-impact', methods=['GET', 'POST'])
@verify_cron
def cron_refresh_player_impact():
    def _run():
        from player_impact import refresh_player_impact_cache
        return refresh_player_impact_cache()
    return log_cron_async('refresh_player_impact', _run)


@app.route('/api/cron/wnba-collect', methods=['GET', 'POST'])
@verify_cron
def cron_wnba_collect():
    return log_cron_async('wnba_collect', collect_wnba_games_job)


@app.route('/api/cron/wnba-closing-lines', methods=['GET', 'POST'])
@verify_cron
def cron_wnba_closing_lines():
    return log_cron_async('wnba_closing_lines', collect_wnba_closing_lines_job)


def run_wnba_shadow_job():
    """Run WNBA shadow predictions — compute ratings then predict."""
    print(f"[{datetime.now()}] Running WNBA shadow predictions...")
    try:
        from main import update_wnba_rolling_ratings, run_wnba_shadow_predictions
        update_wnba_rolling_ratings()
        run_wnba_shadow_predictions()
        print(f"[{datetime.now()}] WNBA shadow predictions completed!")
    except Exception as e:
        print(f"[{datetime.now()}] WNBA shadow error: {e}")


def grade_wnba_shadow_job():
    """Grade completed WNBA shadow picks."""
    print(f"[{datetime.now()}] Grading WNBA shadow picks...")
    try:
        from main import grade_wnba_shadow_picks
        grade_wnba_shadow_picks()
        print(f"[{datetime.now()}] WNBA shadow grading completed!")
    except Exception as e:
        print(f"[{datetime.now()}] WNBA shadow grading error: {e}")


@app.route('/api/cron/wnba-roster-continuity', methods=['GET', 'POST'])
@verify_cron
def cron_wnba_roster_continuity():
    def _run():
        from wnba_features import compute_roster_continuity
        return compute_roster_continuity()
    return log_cron('wnba_roster_continuity', _run)


@app.route('/api/cron/wnba-shadow', methods=['GET', 'POST'])
@verify_cron
def cron_wnba_shadow():
    return log_cron('wnba_shadow', run_wnba_shadow_job)


@app.route('/api/cron/wnba-grade', methods=['GET', 'POST'])
@verify_cron
def cron_wnba_grade():
    return log_cron('wnba_grade', grade_wnba_shadow_job)


# ═══════════════════════════════════════════════════════
# ⚾ MLB CRON ENDPOINTS
# ═══════════════════════════════════════════════════════

def collect_mlb_games_job():
    """Run the MLB data collector"""
    print(f"[{datetime.now()}] Running scheduled MLB data collection...")
    try:
        from main import collect_mlb_scores, collect_mlb_odds
        collect_mlb_scores()
        collect_mlb_odds()
        print(f"[{datetime.now()}] MLB data collection completed!")
    except Exception as e:
        print(f"[{datetime.now()}] MLB collection error: {e}")


def collect_mlb_closing_lines_job():
    """Collect MLB closing lines right before first pitch."""
    print(f"[{datetime.now()}] Collecting MLB closing lines...")
    try:
        from main import collect_mlb_closing_lines
        collect_mlb_closing_lines()
    except Exception as e:
        print(f"[{datetime.now()}] MLB closing line API error (continuing): {e}")

    print(f"[{datetime.now()}] Capturing MLB closing snapshots...")
    with app.app_context():
        try:
            conn = get_sqlite_conn()
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            today_str = _get_et_today()
            now_utc = datetime.utcnow()
            # mlb_games.game_time format is 'YYYY-MM-DDTHH:MMZ' (no seconds)
            now_iso = now_utc.strftime('%Y-%m-%dT%H:%MZ')
            window_end = now_utc + timedelta(minutes=10)
            end_iso = window_end.strftime('%Y-%m-%dT%H:%MZ')

            cursor.execute('''
                SELECT id, home_team, away_team, spread_home, total,
                       home_ml, away_ml, game_time, home_score
                FROM mlb_games
                WHERE game_date LIKE ?
                AND game_time IS NOT NULL
                AND spread_home IS NOT NULL
            ''', (f'{today_str}%',))

            games = cursor.fetchall()
            updated = 0
            skipped_outside = 0
            skipped_scored = 0

            for game in games:
                gt = game['game_time']
                if gt < now_iso or gt > end_iso:
                    skipped_outside += 1
                    continue
                if game['home_score'] is not None:
                    skipped_scored += 1
                    continue
                cursor.execute('''
                    UPDATE mlb_games SET
                        spread_home_close = ?,
                        total_close = ?,
                        home_ml_close = ?,
                        away_ml_close = ?,
                        close_collected_at = ?
                    WHERE id = ?
                ''', (game['spread_home'], game['total'],
                      game['home_ml'], game['away_ml'],
                      datetime.now().isoformat(), game['id']))
                updated += 1

                today_pick = Pick.query.filter(
                    Pick.home_team == game['home_team'],
                    Pick.away_team == game['away_team'],
                    Pick.sport == 'mlb',
                    Pick.game_date.like(f'{today_str}%')
                ).first()
                if today_pick:
                    closing = game['spread_home']
                    if today_pick.line_close is None:
                        today_pick.line_close = closing
                    today_pick.closing_spread = closing
                    if today_pick.line is not None and closing is not None:
                        side = resolve_pick_side(today_pick)
                        if side is not None:
                            today_pick.clv = clv_points(
                                today_pick.line,
                                to_picked_perspective(closing, side),
                            )

            conn.commit()
            conn.close()
            db.session.commit()
            print(f"[{datetime.now()}] MLB closing-lines: {len(games)} today, {updated} snapshotted, {skipped_scored} already scored, {skipped_outside} outside window")
        except Exception as e:
            print(f"[{datetime.now()}] MLB closing line error: {e}")


def grade_mlb_picks_job():
    """Grade MLB picks from ESPN scores."""
    print(f"[{datetime.now()}] Grading MLB picks...")
    with app.app_context():
        try:
            from sport_config import get_sport_config
            cfg = get_sport_config('mlb')

            pending = Pick.query.filter_by(sport='mlb', result='pending').all()
            if not pending:
                print("  No pending MLB picks to grade")
                return

            conn = get_sqlite_conn()
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            for pick in pending:
                cursor.execute(
                    "SELECT home_score, away_score, game_status FROM mlb_games WHERE home_team = ? AND away_team = ? AND game_date = ? AND game_status = 'final'",
                    (pick.home_team, pick.away_team, pick.game_date)
                )
                row = cursor.fetchone()
                if not row or row['home_score'] is None:
                    continue

                home_score = int(row['home_score'])
                away_score = int(row['away_score'])

                # Baseball can't end 0-0; skip bogus scores from in-progress polling
                if home_score == 0 and away_score == 0:
                    continue
                if home_score == 0 and away_score == 0:
                    continue

                if home_score == 0 and away_score == 0:
                    continue
                if home_score == 0 and away_score == 0:
                    continue
                pick.home_score = home_score
                pick.away_score = away_score

                run_diff = home_score - away_score
                line_val = pick.line or 0

                side_lower = (pick.side or '').lower()
                home_lower = (pick.home_team or '').lower()
                away_lower = (pick.away_team or '').lower()

                home_full_match = home_lower in side_lower
                away_full_match = away_lower in side_lower

                if home_full_match and not away_full_match:
                    is_home_pick = True
                elif away_full_match and not home_full_match:
                    is_home_pick = False
                elif home_full_match and away_full_match:
                    home_unique = [w for w in home_lower.split() if w not in away_lower.split() and len(w) > 2]
                    is_home_pick = any(w in side_lower for w in home_unique)
                else:
                    home_words = {w for w in home_lower.split() if len(w) > 3}
                    away_words = {w for w in away_lower.split() if len(w) > 3}
                    home_unique_words = home_words - away_words
                    away_unique_words = away_words - home_words
                    home_match = any(w in side_lower for w in home_unique_words) if home_unique_words else False
                    away_match = any(w in side_lower for w in away_unique_words) if away_unique_words else False
                    if home_match and not away_match:
                        is_home_pick = True
                    elif away_match and not home_match:
                        is_home_pick = False
                    else:
                        is_home_pick = any(w in side_lower for w in home_words)

                if is_home_pick:
                    ats_margin = run_diff + line_val
                else:
                    ats_margin = -run_diff + line_val

                pick.result_ats = round(ats_margin, 1)
                odds = pick.market_odds or cfg.get('standard_odds', -130)

                if ats_margin == 0:
                    pick.result = 'push'
                    pick.profit_units = 0
                elif ats_margin > 0:
                    pick.result = 'win'
                    if odds > 0:
                        pick.profit_units = round(odds / 100, 2)
                    else:
                        pick.profit_units = round(100 / abs(odds), 2)
                else:
                    pick.result = 'loss'
                    pick.profit_units = -1.0

                pick.pnl = pick.profit_units
                pick.result_resolved_at = datetime.utcnow()
                print(f"  Graded: {pick.away_team} @ {pick.home_team} → {pick.result}")

            conn.close()
            db.session.commit()
        except Exception as e:
            print(f"[{datetime.now()}] MLB grading error: {e}")


@app.route('/api/cron/mlb-collect', methods=['GET', 'POST'])
@verify_cron
def cron_mlb_collect():
    return log_cron_async('mlb_collect', collect_mlb_games_job)


@app.route('/api/cron/mlb-closing-lines', methods=['GET', 'POST'])
@verify_cron
def cron_mlb_closing_lines():
    return log_cron_async('mlb_closing_lines', collect_mlb_closing_lines_job)


def run_mlb_model_job(force=False, notify=True):
    """Run the MLB model to generate picks, then generate market note.

    notify=False lets a caller refresh pick.notes (e.g. after a reasoning
    template fix) without firing another round of push notifications.
    Default True preserves the scheduled-cron behavior.
    """
    print(f"[{datetime.now()}] Running MLB model (force={force}, notify={notify})...")
    if force:
        from model_service import invalidate_model_cache
        invalidate_model_cache('mlb')

    # Always collect fresh MLB data before running the model
    try:
        collect_mlb_games_job()
        print(f"[{datetime.now()}] MLB data collected before model run")
    except Exception as e:
        print(f"[{datetime.now()}] MLB collection failed (non-fatal): {e}")
    from model_service import run_model_and_log
    result = run_model_and_log(app, sport='mlb', force=force, send_notifications=notify)
    print(f"[{datetime.now()}] MLB model run completed: {result.get('status', '?')}")
    try:
        from public_api import build_market_report_dict
        today_str = _get_et_today()
        mi_report = build_market_report_dict(today_str, 'mlb')
        if mi_report.get('available'):
            _upsert_market_note_insight(mi_report, sport='mlb')
            print(f"[{datetime.now()}] MLB market note generated")
    except Exception as e:
        print(f"[{datetime.now()}] MLB market note failed (non-fatal): {e}")
    return result


@app.route('/api/cron/mlb-run-model', methods=['GET', 'POST'])
@verify_cron
def cron_mlb_run_model():
    force = request.args.get('force', 'false').lower() == 'true'
    notify = request.args.get('notify', 'true').lower() != 'false'
    return log_cron_async('mlb_run_model', lambda: run_mlb_model_job(force=force, notify=notify), skip_throttle=True)


@app.route('/api/cron/mlb-grade', methods=['GET', 'POST'])
@verify_cron
def cron_mlb_grade():
    return log_cron('mlb_grade', grade_mlb_picks_job)


@app.route('/api/cron/wnba-run-model', methods=['GET', 'POST'])
@verify_cron
def cron_wnba_run_model():
    """Dedicated WNBA model run. WNBA actually piggybacks on the generic
    /api/cron/run-model 10 AM ET cron (sports_with_own_cron = {'mlb'} so
    only MLB is excluded). This endpoint is dormant in the daily flow and
    only used for ad-hoc force fires. Stale comment removed."""
    force = request.args.get('force', 'false').lower() == 'true'
    notify = request.args.get('notify', 'true').lower() != 'false'
    date_override = request.args.get('date', '').strip() or None

    def _run():
        from model_service import run_model_and_log
        return run_model_and_log(
            app, sport='wnba', force=force, date_override=date_override,
            send_notifications=notify,
        )
    return log_cron_async('wnba_run_model', _run, skip_throttle=True)


@app.route('/api/admin/regrade-pick/<pick_id>', methods=['POST'])
def regrade_pick(pick_id):
    """Re-grade a pick with corrected side-detection logic. Admin only."""
    from admin_api import require_superuser
    admin, err_code = require_superuser()
    if not admin:
        return jsonify({'error': 'Unauthorized'}), err_code

    pick = Pick.query.get(pick_id)
    if not pick:
        return jsonify({'error': 'Pick not found'}), 404
    if pick.home_score is None or pick.away_score is None:
        return jsonify({'error': 'No scores available to regrade'}), 400

    home_score = pick.home_score
    away_score = pick.away_score
    spread_result = home_score - away_score
    line_value = pick.line if pick.line and abs(pick.line) < 50 else 0

    side_lower = (pick.side or '').lower()
    home_lower = (pick.home_team or '').lower()
    away_lower = (pick.away_team or '').lower()

    home_full = home_lower in side_lower
    away_full = away_lower in side_lower

    if home_full and not away_full:
        is_home_pick = True
    elif away_full and not home_full:
        is_home_pick = False
    elif home_full and away_full:
        home_unique = [w for w in home_lower.split() if w not in away_lower.split() and len(w) > 2]
        is_home_pick = any(w in side_lower for w in home_unique)
    else:
        home_words = {w for w in home_lower.split() if len(w) > 3}
        away_words = {w for w in away_lower.split() if len(w) > 3}
        home_hit = any(w in side_lower for w in (home_words - away_words))
        away_hit = any(w in side_lower for w in (away_words - home_words))
        is_home_pick = home_hit and not away_hit

    ats_margin = (spread_result + line_value) if is_home_pick else (-spread_result + line_value)

    old_result = pick.result
    if ats_margin == 0:
        pick.result = 'push'
        pick.profit_units = 0
    elif ats_margin > 0:
        pick.result = 'win'
        actual_odds = pick.market_odds or -110
        if actual_odds < 0:
            pick.profit_units = round(100 / abs(actual_odds), 2)
        else:
            pick.profit_units = round(actual_odds / 100, 2)
    else:
        pick.result = 'loss'
        pick.profit_units = -1.0

    pick.pnl = pick.profit_units
    pick.result_ats = 'P' if pick.result == 'push' else ('W' if pick.result == 'win' else 'L')
    db.session.commit()

    return jsonify({
        'status': 'regraded',
        'pick_id': pick.id,
        'side': pick.side,
        'home_team': pick.home_team,
        'away_team': pick.away_team,
        'is_home_pick': is_home_pick,
        'score': f"{away_score}-{home_score}",
        'ats_margin': ats_margin,
        'old_result': old_result,
        'new_result': pick.result,
        'profit_units': pick.profit_units,
    })


def retrain_mlb_model_job():
    """Retrain the MLB ensemble model."""
    print(f"[{datetime.now()}] Retraining MLB model...")
    with app.app_context():
        try:
            from model import EnsemblePredictor
            from model_service import invalidate_model_cache
            predictor = EnsemblePredictor(sport='mlb')
            result = predictor.train()
            if result:
                invalidate_model_cache('mlb')
                print(f"[{datetime.now()}] MLB model retrained successfully! Cache invalidated.")
            else:
                print(f"[{datetime.now()}] MLB model training failed (not enough data?)")
        except Exception as e:
            print(f"[{datetime.now()}] MLB retrain error: {e}")
            import traceback
            traceback.print_exc()


@app.route('/api/cron/mlb-retrain', methods=['GET', 'POST'])
@verify_cron
def cron_mlb_retrain():
    return log_cron_async('mlb_retrain', retrain_mlb_model_job, skip_throttle=True)


@app.route('/api/cron/mlb-backfill', methods=['GET', 'POST'])
@verify_cron
def cron_mlb_backfill():
    """Backfill MLB historical data with Rundown odds, then validate."""
    def _backfill_and_validate():
        import threading
        def _run():
            try:
                from validate_mlb import run_backfill, compute_spread_results, data_summary
                print(f"[{datetime.now()}] Starting MLB backfill...")
                run_backfill(seasons=[2023, 2024, 2025])
                compute_spread_results()
                print(f"[{datetime.now()}] Backfill complete.")
                data_summary()
            except Exception as e:
                print(f"[{datetime.now()}] MLB backfill error: {e}")
                import traceback
                traceback.print_exc()
        t = threading.Thread(target=_run, daemon=True)
        t.start()
        return "MLB backfill started in background"
    return log_cron('mlb_backfill', _backfill_and_validate, skip_throttle=True)


@app.route('/api/cron/mlb-validate', methods=['GET', 'POST'])
@verify_cron
def cron_mlb_validate():
    """Run walk-forward validation on existing MLB data."""
    def _validate():
        from model import EnsemblePredictor
        predictor = EnsemblePredictor(sport='mlb')
        result = predictor.walk_forward_validate()
        if result:
            predictor.calibration_check(result['all_bets'])
            total_bets = sum(r['n_bets'] for r in result['seasons'])
            total_wins = sum(r['wins'] for r in result['seasons'])
            total_profit = sum(r['total_profit'] for r in result['seasons'])
            roi = (total_profit / total_bets * 100) if total_bets > 0 else 0
            return f"Walk-forward: {total_bets} bets, {total_wins}W, ROI {roi:+.1f}%"
        return "Walk-forward returned no results"
    return log_cron('mlb_validate', _validate, skip_throttle=True)


@app.route('/api/cron/player-props', methods=['GET', 'POST'])
@verify_cron
def cron_player_props():
    def _collect_props():
        from main import collect_player_props
        collect_player_props()
    return log_cron_async('player_props', _collect_props)


@app.route('/api/cron/grade-picks', methods=['GET', 'POST'])
@verify_cron
def cron_grade_picks():
    force = request.args.get('force') == '1'
    return log_cron('grade_picks', grade_pending_picks, skip_throttle=force)


@app.route('/api/cron/grade-whatifs', methods=['GET', 'POST'])
@verify_cron
def cron_grade_whatifs():
    return log_cron('grade_whatifs', grade_whatif_passes)


@app.route('/api/cron/expire-trials', methods=['GET', 'POST'])
@verify_cron
def cron_expire_trials():
    def _expire():
        check_expiring_trials()
        expire_trials()
        now = datetime.now()
        scheduled = Insight.query.filter(Insight.status == 'scheduled', Insight.publish_date <= now).all()
        for ins in scheduled:
            ins.status = 'published'
            logging.info(f"Auto-published scheduled insight: {ins.slug}")
        if scheduled:
            db.session.commit()
    return log_cron('expire_trials', _expire)


@app.route('/api/cron/weekly-summary', methods=['GET', 'POST'])
@verify_cron
def cron_weekly_summary():
    return log_cron('weekly_summary', send_weekly_summary_job)


@app.route('/api/cron/admin-alert', methods=['GET', 'POST'])
@verify_cron
def cron_admin_alert():
    """Run status + health check; send admin push if issues found. Schedule every 2–4 hours."""
    def _check():
        from admin_api import run_admin_alert_check
        run_admin_alert_check(include_health=True)
        return {'checked': True}
    return log_cron('admin_alert', _check)


@app.route('/api/cron/backup', methods=['GET', 'POST'])
@verify_cron
def cron_backup():
    def _backup():
        import json as json_mod
        from sqlalchemy import inspect as sa_inspect

        def row_to_dict(obj):
            d = {}
            for c in sa_inspect(obj.__class__).columns:
                val = getattr(obj, c.key)
                if isinstance(val, datetime):
                    d[c.key] = val.isoformat()
                else:
                    d[c.key] = val
            return d

        picks = [row_to_dict(p) for p in Pick.query.all()]
        passes_list = [row_to_dict(p) for p in Pass.query.all()]
        users = [row_to_dict(u) for u in User.query.all()]
        for u in users:
            u.pop('password_hash', None)
            u.pop('session_token', None)

        backup_data = json_mod.dumps({
            'timestamp': datetime.utcnow().isoformat(),
            'picks': picks,
            'passes': passes_list,
            'users': users
        }, indent=2, default=str)

        backup_dir = '/tmp/backups'
        os.makedirs(backup_dir, exist_ok=True)
        backup_path = f'{backup_dir}/sharppicks_backup_{datetime.now().strftime("%Y%m%d_%H%M")}.json'
        with open(backup_path, 'w') as f:
            f.write(backup_data)

        backup_database()
        return {'picks': len(picks), 'users': len(users)}
    return log_cron('backup', _backup)


@app.route('/api/cron/update-ratings', methods=['GET', 'POST'])
@verify_cron
def cron_update_ratings():
    """Refresh NBA team ratings from stats.nba.com. Schedule daily before model run."""
    def _update():
        from nba_ratings import update_ratings
        success = update_ratings()
        return {'updated': success}
    return log_cron_async('update_ratings', _update)


def _send_consolidated_model_notification(results, live_sports):
    """Send a single push notification summarizing all sport model results."""
    from sport_config import get_sport_config
    parts = []
    has_pick = False
    pick_sport = None
    pick_result = None

    for sport in live_sports:
        r = results.get(sport, {})
        status = r.get('status', '')
        cfg = get_sport_config(sport)
        tag = cfg.get('name', sport.upper())

        if status == 'pick':
            has_pick = True
            pick_sport = sport
            pick_result = r
            edge = r.get('edge', 0)
            parts.append(f"{tag}: Signal \u00b7 {edge}% edge")
        elif status == 'paper_trade':
            edge = r.get('edge', 0)
            parts.append(f"{tag}: Paper signal \u00b7 {edge}% edge")
        elif status == 'pass':
            games = r.get('games_analyzed', 0)
            parts.append(f"{tag}: No edge \u00b7 {games} games scanned")
        elif status in ('already_run',):
            continue
        elif status in ('data_failure', 'no_spreads', 'inactive'):
            continue
        else:
            continue

    if not parts:
        return

    from lib.notifications.sport_labels import sport_label as _sport_label
    if has_pick and len(parts) == 1:
        title = f"{_sport_label(pick_sport)} \u00b7 Signal Locked"
        edge = pick_result.get('edge', 0)
        body = f"{edge}% edge \u00b7 {pick_result.get('side', 'Pick available')}"
        data = {'type': 'pick', 'pick_id': str(pick_result.get('pick_id', '')), 'sport': pick_sport}
    elif has_pick:
        title = "Today's Model Results"
        body = ' | '.join(parts)
        data = {'type': 'pick', 'pick_id': str(pick_result.get('pick_id', '')), 'sport': pick_sport}
    else:
        pass_sports = [s for s in live_sports if results.get(s, {}).get('status') == 'pass']
        if len(pass_sports) == 1:
            title = f"{_sport_label(pass_sports[0])} \u00b7 No Edge Today"
        else:
            title = "No Edge Today"
        all_pass_parts = []
        for sport in live_sports:
            r = results.get(sport, {})
            if r.get('status') == 'pass':
                cfg = get_sport_config(sport)
                tag = cfg.get('name', sport.upper())
                games = r.get('games_analyzed', 0)
                all_pass_parts.append(f"{tag}: {games} games, no qualifying edge")
        body = ' | '.join(all_pass_parts) if all_pass_parts else ' | '.join(parts)
        data = {'type': 'pass', 'date': results.get(live_sports[0], {}).get('date', ''), 'sport': live_sports[0] if live_sports else 'nba'}

    try:
        free_kw = {}
        if has_pick:
            free_kw = {
                'free_title': f'{_sport_label(pick_sport)} · Signal Published',
                'free_body': 'A qualifying signal was found today. Upgrade to Pro to see the full pick.',
                'free_data': {'type': 'pick', 'sport': pick_sport},
            }
        sent = send_push_to_all(title, body, data=data, premium_only=True,
                                notification_type='pick' if has_pick else 'pass', **free_kw)
        import logging
        logging.info(f"Consolidated model notification sent to {sent} device(s): {title}")
    except Exception as e:
        import logging
        logging.error(f"Consolidated notification send failed: {e}")

    # Also send emails for each sport individually
    for sport in live_sports:
        r = results.get(sport, {})
        status = r.get('status', '')
        try:
            if status == 'pick':
                pick = Pick.query.get(r.get('pick_id'))
                if pick:
                    from notification_events import dispatch_signal_emails
                    dispatch_signal_emails(pick)
            elif status == 'pass':
                from notification_events import dispatch_no_signal_emails
                dispatch_no_signal_emails(
                    games_analyzed=r.get('games_analyzed', 0),
                    edges_detected=0,
                    efficiency=100,
                    sport=sport,
                )
        except Exception:
            pass


@app.route('/api/cron/run-model', methods=['GET', 'POST'])
@verify_cron
def cron_run_model():
    force = request.args.get('force', '').lower() == 'true'
    # notify=false lets a caller refresh pick.notes (e.g. after a reasoning
    # template fix) without firing another round of push notifications.
    # Default true preserves the scheduled-cron behavior.
    notify = request.args.get('notify', 'true').lower() != 'false'
    date_override = request.args.get('date', '').strip() or None
    if date_override and len(date_override) == 10 and date_override[4] == '-' and date_override[7] == '-':
        pass
    else:
        date_override = None

    def _run():
        today_str = date_override or _get_et_today()

        if force:
            from model_service import invalidate_model_cache
            invalidate_model_cache()
            print(f"[model-run] Force: all model caches invalidated")

        # Always collect fresh games before running the model to avoid stale data
        print(f"[model-run] Collecting fresh game data for {today_str}...")
        try:
            collect_todays_games()
            print(f"[model-run] NBA games collected successfully")
        except Exception as e:
            print(f"[model-run] NBA game collection failed: {e}")
            if force:
                return {'status': 'collect_failed', 'error': str(e), 'date': today_str}
        if 'mlb' in get_live_sports():
            try:
                collect_mlb_games_job()
                print(f"[model-run] MLB games collected")
            except Exception as e:
                print(f"[model-run] MLB collection failed (non-fatal): {e}")
        if 'wnba' in get_live_sports():
            try:
                collect_wnba_games_job()
                print(f"[model-run] WNBA games collected")
            except Exception as e:
                print(f"[model-run] WNBA collection failed (non-fatal): {e}")

        if force:
            for sport in get_live_sports():
                stale_pass = Pass.query.filter_by(date=today_str, sport=sport).first()
                if stale_pass and stale_pass.games_analyzed == 0:
                    db.session.delete(stale_pass)
                    db.session.commit()
                    print(f"[model-run] Force: cleared stale pass for {today_str}/{sport}")
        try:
            from nba_ratings import update_ratings
            if 'nba' in get_live_sports():
                import threading
                ratings_thread = threading.Thread(target=update_ratings)
                ratings_thread.start()
                ratings_thread.join(timeout=20)
                if ratings_thread.is_alive():
                    print("[model-run] Ratings refresh timed out after 20s — continuing")
        except Exception as e:
            print(f"[model-run] Ratings refresh failed (non-fatal): {e}")
        results = {}
        live = get_live_sports()
        # MLB has its own dedicated /api/cron/mlb-run-model. NBA + WNBA both
        # run on this shared cron at 9 AM and 2:15 PM ET, with WNBA in
        # calibration mode. The /api/cron/wnba-run-model endpoint stays
        # available for manual force-fires but isn't needed in the daily
        # schedule.
        sports_with_own_cron = {'mlb'}
        run_sports = [s for s in live if s not in sports_with_own_cron]
        # Per-sport synchronous push notifications. send_notifications=True
        # makes run_model_and_log fire send_pick_notification(pick) inline
        # for any sport that publishes a pick, matching MLB's reliable
        # synchronous path. Previously NBA ran with send_notifications=False
        # and relied on a nested daemon thread for a "consolidated" push,
        # which got killed by Gunicorn worker recycles / Railway SIGTERMs
        # — surface area was "only got MLB pushes today, not NBA".
        for sport in run_sports:
            results[sport] = run_model_and_log(app, sport=sport, force=force, date_override=date_override, send_notifications=notify)

        # Generate market note insight for each live sport (no push)
        today_str = date_override or _get_et_today()
        try:
            from public_api import build_market_report_dict
            for mi_sport in live:
                try:
                    mi_report = build_market_report_dict(today_str, mi_sport)
                    if mi_report.get('available'):
                        _upsert_market_note_insight(mi_report, sport=mi_sport)
                except Exception:
                    import logging
                    logging.exception("Market note for %s: failed", mi_sport)
        except Exception as e:
            import logging
            logging.exception("Market note generation: %s", e)
        return results
    return log_cron_async('run_model', _run, skip_throttle=force)


@app.route('/api/cron/model-watchdog', methods=['GET', 'POST'])
@verify_cron
def cron_model_watchdog():
    """Safety net: if the model hasn't run today for any live sport, trigger it now."""
    def _watchdog():
        from zoneinfo import ZoneInfo
        today_str = datetime.now(ZoneInfo('America/New_York')).strftime('%Y-%m-%d')
        et_hour = datetime.now(ZoneInfo('America/New_York')).hour
        results = {}

        nba_run = ModelRun.query.filter_by(date=today_str, sport='nba').first()
        if not nba_run and et_hour >= 10:
            results['nba'] = 'triggering'
            try:
                try:
                    collect_todays_games()
                except Exception as ce:
                    logging.warning(f"[watchdog] NBA collection failed (continuing): {ce}")
                run_model_and_log(app, sport='nba', force=False, send_notifications=True)
                results['nba'] = 'triggered_and_completed'
                try:
                    from public_api import build_market_report_dict
                    mi_report = build_market_report_dict(today_str, 'nba')
                    _upsert_market_note_insight(mi_report, sport='nba')
                except Exception:
                    pass
            except Exception as e:
                results['nba'] = f'error: {str(e)[:200]}'
        else:
            results['nba'] = 'already_ran' if nba_run else 'not_due_yet'

        mlb_run = ModelRun.query.filter_by(date=today_str, sport='mlb').first()
        if not mlb_run and et_hour >= 11:
            results['mlb'] = 'triggering'
            try:
                run_mlb_model_job(force=False)
                results['mlb'] = 'triggered_and_completed'
            except Exception as e:
                results['mlb'] = f'error: {str(e)[:200]}'
        else:
            results['mlb'] = 'already_ran' if mlb_run else 'not_due_yet'

        return results

    return log_cron('model_watchdog', _watchdog)


@app.route('/api/cron/pretip-validate', methods=['GET', 'POST'])
@verify_cron
def cron_pretip_validate():
    from model_service import pretip_revalidate
    def _validate():
        results = {}
        for sport in get_live_sports():
            results[sport] = pretip_revalidate(app, sport=sport)
        return results
    return log_cron('pretip_validate', _validate)


@app.route('/api/cron/check-data-quality', methods=['GET', 'POST'])
@verify_cron
def cron_data_quality():
    return log_cron('data_quality', check_data_quality)


@app.route('/api/cron/retrain-model', methods=['GET', 'POST'])
@verify_cron
def cron_retrain_model():
    """Retrain the model if it's stale (>30 days old). Schedule weekly; it no-ops when fresh."""
    force = request.args.get('force', '').lower() == 'true'
    sync = request.args.get('sync', '').lower() == 'true'
    only_sport = request.args.get('sport', '').lower() or None
    def _retrain():
        from model import EnsemblePredictor
        import traceback
        results = {}
        sports_with_own_cron = {'mlb'}
        target_sports = [only_sport] if only_sport else get_live_sports()
        for sport in target_sports:
            if not only_sport and sport in sports_with_own_cron:
                continue
            try:
                model = EnsemblePredictor(sport=sport)
                model.load_model()
                age = model.model_age_days()
                if not force and not model.is_stale():
                    results[sport] = {
                        'status': 'fresh',
                        'age_days': age,
                        'threshold_days': model.MODEL_STALE_DAYS,
                    }
                    continue
                logging.info(f"[retrain] {sport}: starting train (force={force})")
                train_result = model.train()
                filepath = model._default_filepath()
                if not model.trained:
                    results[sport] = {
                        'status': 'train_failed',
                        'previous_age_days': age,
                        'train_returned': train_result,
                        'trained_flag': model.trained,
                    }
                    continue
                file_size_kb = round(os.path.getsize(filepath) / 1024, 1) if os.path.exists(filepath) else 0
                from model_service import invalidate_model_cache
                invalidate_model_cache(sport)
                logging.info(f"[retrain] {sport}: cache invalidated, file={file_size_kb}KB")
                results[sport] = {
                    'status': 'retrained',
                    'previous_age_days': age,
                    'trained_flag': model.trained,
                    'n_models': len(model.models),
                    'file_size_kb': file_size_kb,
                    'n_features': len(model.feature_names),
                }
            except Exception as e:
                results[sport] = {
                    'status': 'error',
                    'error': str(e),
                    'traceback': traceback.format_exc()[-500:],
                }
        return results
    if sync:
        return log_cron('retrain_model', _retrain, skip_throttle=force)
    return log_cron_async('retrain_model', _retrain, skip_throttle=force)


@app.route('/api/cron/generate-weekly-card', methods=['GET', 'POST'])
@verify_cron
def cron_generate_weekly_card():
    """Pre-generate weekly recap card PNG and save to static/cards/weekly-latest.png."""
    def _generate():
        from routes.card_routes import _compute_weekly_data
        data = _compute_weekly_data()
        html_string = render_template('recap_card.html', **data)

        from services.card_generator import generate_card_png
        png_bytes = generate_card_png(html_string)

        cards_dir = os.path.join(os.path.dirname(__file__), 'static', 'cards')
        os.makedirs(cards_dir, exist_ok=True)
        out_path = os.path.join(cards_dir, 'weekly-latest.png')
        with open(out_path, 'wb') as f:
            f.write(png_bytes)
        return {'path': out_path, 'size_bytes': len(png_bytes)}
    return log_cron('generate_weekly_card', _generate)


@app.route('/api/cron/mrr-snapshot', methods=['GET', 'POST'])
@verify_cron
def cron_mrr_snapshot():
    """Nightly MRR snapshot. Calculates current MRR from active subscriptions and stores in mrr_daily_snapshots."""
    def _snapshot():
        from datetime import date
        today = date.today()
        existing = MrrSnapshot.query.filter_by(snapshot_date=today).first()
        if existing:
            return {'skipped': True, 'date': today.isoformat()}
        MONTHLY_CENTS = 1999
        ANNUAL_MONTHLY_CENTS = round(14999 / 12)
        active_users = User.query.filter_by(subscription_status='active').all()
        mrr = 0
        monthly = 0
        annual = 0
        founding = 0
        for u in active_users:
            plan = (u.subscription_plan or '').lower()
            if 'annual' in plan:
                mrr += ANNUAL_MONTHLY_CENTS
                annual += 1
                if u.founding_member:
                    founding += 1
            elif 'month' in plan:
                mrr += MONTHLY_CENTS
                monthly += 1
        snap = MrrSnapshot(
            snapshot_date=today, mrr_cents=mrr,
            active_monthly=monthly, active_annual=annual,
            founding_members=founding, total_subscribers=monthly + annual,
        )
        db.session.add(snap)
        db.session.commit()
        return {'date': today.isoformat(), 'mrr_cents': mrr, 'subs': monthly + annual}
    return log_cron('mrr_snapshot', _snapshot)


@app.route('/api/cron/cleanup-events', methods=['GET', 'POST'])
@verify_cron
def cron_cleanup_events():
    """Weekly cleanup: purge user_events older than 90 days."""
    def _cleanup():
        cutoff = datetime.now() - timedelta(days=90)
        deleted = UserEvent.query.filter(UserEvent.created_at < cutoff).delete()
        db.session.commit()
        return {'deleted': deleted, 'cutoff': cutoff.isoformat()}
    return log_cron('cleanup_events', _cleanup)


def start_background_services():
    import time
    time.sleep(5)
    try:
        logging.info("Starting background services...")
        seed_database()
        logging.info("All background services started (scheduled jobs via external cron)")
    except Exception as e:
        logging.error(f"Background services failed (non-fatal): {e}")

def get_db():
    conn = get_sqlite_conn()
    conn.row_factory = sqlite3.Row
    return conn

def calculate_streak(dates):
    if not dates:
        return 0
    streak = 1
    for i in range(len(dates) - 1):
        try:
            d1 = datetime.fromisoformat(dates[i])
            d2 = datetime.fromisoformat(dates[i + 1])
            if (d1 - d2).days == 1:
                streak += 1
            else:
                break
        except:
            break
    return streak

@app.route('/api/auth/user')
def get_current_user():
    """Get current authenticated user info"""
    user_dict = get_current_user_from_session()
    if user_dict:
        user_obj = db.session.get(User, user_dict['id'])
        token = generate_auth_token(user_obj) if user_obj else None
        return jsonify({'authenticated': True, 'user': user_dict, 'token': token})
    return jsonify({'authenticated': False, 'user': None})

@app.route('/api/check-verification-status')
def check_verification_status():
    """Lightweight poll endpoint for email verification state"""
    user_dict = get_current_user_from_session()
    if not user_dict:
        return jsonify({'verified': False}), 401
    user = db.session.get(User, user_dict['id'])
    if not user:
        return jsonify({'verified': False}), 401
    return jsonify({'verified': bool(user.email_verified)})

@app.route('/api/auth/register', methods=['POST'])
@limiter.limit("5 per minute")
def register():
    """Register a new user with email and password — requires email verification"""
    from flask import request
    from werkzeug.security import generate_password_hash
    from itsdangerous import URLSafeTimedSerializer
    from models import normalize_email
    import uuid

    data = request.get_json() or {}
    email = data.get('email', '').strip().lower()
    password = data.get('password', '')
    first_name = data.get('first_name', '').strip()
    account_type = data.get('account_type', 'trial')

    if not email or not password:
        return jsonify({'error': 'Email and password required'}), 400
    if len(password) < 6:
        return jsonify({'error': 'Password must be at least 6 characters'}), 400
    if not first_name:
        return jsonify({'error': 'First name is required'}), 400

    existing = User.query.filter(func.lower(User.email) == email.lower()).first()
    if existing:
        return jsonify({'error': 'Email already registered'}), 400

    norm = normalize_email(email)
    existing_norm = User.query.filter_by(email_normalized=norm).first()
    if existing_norm and existing_norm.trial_used:
        return jsonify({'error': 'A free trial has already been used with this email address'}), 400

    is_free = account_type == 'free'

    user = User(
        id=str(uuid.uuid4()),
        email=email.lower(),
        email_normalized=norm,
        first_name=first_name,
        display_name=first_name,
        password_hash=generate_password_hash(password),
        is_premium=False,
        subscription_status='free' if is_free else 'pending_verification',
        email_verified=is_free,
    )
    db.session.add(user)
    db.session.commit()

    _apply_pre_provisioned(user)

    login_user(user, remember=True)
    session.permanent = True
    session['user_id'] = user.id
    session['session_token'] = user.session_token

    try:
        send_admin_alert(
            "New Signup",
            f"{first_name} ({email}) joined as {account_type}",
            {'type': 'new_signup', 'email': email, 'account_type': account_type}
        )
    except Exception as e:
        logging.error(f"Admin signup alert failed: {e}")

    if is_free:
        try:
            from email_service import send_welcome_email
            send_welcome_email(user.email, user.first_name)
        except Exception as e:
            logging.error(f"Welcome email failed: {e}")

        return jsonify({
            'success': True,
            'user': serialize_user(user),
            'needs_verification': False,
            'token': generate_auth_token(user),
        })

    try:
        from email_service import send_verification_email
        s = URLSafeTimedSerializer(app.config['SECRET_KEY'])
        token = s.dumps(user.id, salt='email-verify')
        base = os.environ.get('APP_BASE_URL', '').rstrip('/')
        if not base:
            domains = os.environ.get('REPLIT_DOMAINS', 'app.sharppicks.ai')
            base = f"https://{domains.split(',')[0]}"
        verify_url = f"{base}/api/auth/verify-email?token={token}"
        send_verification_email(user.email, verify_url, user.first_name)
    except Exception as e:
        logging.error(f"Verification email failed: {e}")

    return jsonify({
        'success': True,
        'user': serialize_user(user),
        'needs_verification': True,
        'token': generate_auth_token(user),
    })

@app.route('/api/auth/verify-email')
def verify_email():
    """Verify email from link click — redirects trial-eligible users to Stripe checkout"""
    from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadSignature
    token = request.args.get('token', '')
    if not token:
        return redirect('/?verify=invalid')

    s = URLSafeTimedSerializer(app.config['SECRET_KEY'])
    try:
        user_id = s.loads(token, salt='email-verify', max_age=86400)
    except SignatureExpired:
        return redirect('/?verify=expired')
    except BadSignature:
        return redirect('/?verify=invalid')

    user = db.session.get(User, user_id)
    if not user:
        return redirect('/?verify=invalid')

    user.email_verified = True
    user.subscription_status = 'free'
    db.session.commit()

    login_user(user, remember=True)
    session.permanent = True
    session['user_id'] = user.id
    session['session_token'] = user.session_token

    ua = request.headers.get('User-Agent', '').lower()
    # iOS users must use IAP per App Store Guideline 3.1.1; never funnel
    # them through Stripe checkout for digital subscriptions.
    is_ios = 'iphone' in ua or 'ipad' in ua or 'ipod' in ua
    if not is_ios and not user.trial_used and not user.is_premium:
        checkout_url = _create_trial_checkout_url(user)
        if checkout_url:
            return _redirect_replace(checkout_url)

    is_mobile = any(k in ua for k in ('iphone', 'ipad', 'android', 'capacitor'))
    if is_mobile:
        html = """<!DOCTYPE html>
<html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Email Verified — SharpPicks</title>
<style>body{margin:0;padding:40px 20px;background:#0A0D14;color:#e2e8f0;font-family:-apple-system,sans-serif;
text-align:center;display:flex;flex-direction:column;align-items:center;justify-content:center;min-height:90vh}
.check{width:64px;height:64px;border-radius:50%;background:rgba(52,211,153,0.1);display:flex;align-items:center;
justify-content:center;margin:0 auto 20px}
h1{font-size:22px;margin-bottom:8px}
p{font-size:15px;color:#94a3b8;margin-bottom:24px;line-height:1.6}
.btn{display:inline-block;padding:14px 32px;background:linear-gradient(135deg,#4f86f7,#2f5fd6);
border:none;border-radius:12px;color:#fff;font-size:16px;font-weight:700;text-decoration:none;cursor:pointer}
.sub{font-size:12px;color:#64748b;margin-top:16px}
</style></head><body>
<div class="check"><svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="#34D399" stroke-width="2.5">
<path d="M20 6L9 17l-5-5"/></svg></div>
<h1>Email Verified</h1>
<p>Your account is active. Return to the SharpPicks app to continue.</p>
<a class="btn" href="/">Open SharpPicks</a>
<div class="sub">You can close this browser tab.</div>
</body></html>"""
        return Response(html, content_type='text/html')

    return redirect('/?verify=success')


@app.route('/api/auth/resend-verification', methods=['POST'])
@limiter.limit("3 per minute")
def resend_verification():
    """Resend verification email for pending users"""
    from itsdangerous import URLSafeTimedSerializer
    user_dict = get_current_user_from_session()
    if not user_dict:
        return jsonify({'error': 'Authentication required'}), 401

    user = db.session.get(User, user_dict['id'])
    if not user:
        return jsonify({'error': 'User not found'}), 404
    if user.email_verified:
        return jsonify({'success': True, 'message': 'Email already verified'})

    try:
        from email_service import send_verification_email
        s = URLSafeTimedSerializer(app.config['SECRET_KEY'])
        token = s.dumps(user.id, salt='email-verify')
        base = os.environ.get('APP_BASE_URL', '').rstrip('/')
        if not base:
            domains = os.environ.get('REPLIT_DOMAINS', 'app.sharppicks.ai')
            base = f"https://{domains.split(',')[0]}"
        verify_url = f"{base}/api/auth/verify-email?token={token}"
        send_verification_email(user.email, verify_url, user.first_name)
    except Exception as e:
        logging.error(f"Resend verification failed: {e}")
        return jsonify({'error': 'Failed to send email. Please try again.'}), 500

    return jsonify({'success': True, 'message': 'Verification email sent'})


@app.route('/api/auth/login', methods=['POST'])
@limiter.limit("10 per minute")
def login():
    """Login with email and password — includes brute force lockout"""
    from flask import request
    from werkzeug.security import check_password_hash

    data = request.get_json() or {}
    email = data.get('email', '').strip().lower()
    password = data.get('password', '')

    if not email or not password:
        return jsonify({'error': 'Email and password required'}), 400

    user = User.query.filter(func.lower(User.email) == email.lower()).first()
    if not user or not user.password_hash:
        return jsonify({'error': 'Invalid email or password'}), 401
    # Soft-deleted accounts get the same generic error as 'no such user'
    # so we don't leak the existence of disabled accounts.
    if not user.is_active:
        return jsonify({'error': 'Invalid email or password'}), 401

    if user.locked_until and user.locked_until > datetime.now():
        remaining = int((user.locked_until - datetime.now()).total_seconds() / 60) + 1
        return jsonify({'error': f'Account locked. Try again in {remaining} minutes.'}), 429

    if not check_password_hash(user.password_hash, password):
        user.failed_login_attempts = (user.failed_login_attempts or 0) + 1
        if user.failed_login_attempts >= 5:
            user.locked_until = datetime.now() + timedelta(minutes=15)
            user.failed_login_attempts = 0
            db.session.commit()
            return jsonify({'error': 'Too many failed attempts. Account locked for 15 minutes.'}), 429
        db.session.commit()
        if getattr(user, 'oauth_provider', None) in ('google', 'apple'):
            return jsonify({'error': 'Invalid email or password', 'oauth_hint': user.oauth_provider}), 401
        return jsonify({'error': 'Invalid email or password'}), 401

    user.failed_login_attempts = 0
    user.locked_until = None
    db.session.commit()

    login_user(user, remember=True)
    session.permanent = True
    session['user_id'] = user.id
    session['session_token'] = user.session_token
    
    return jsonify({
        'success': True,
        'user': serialize_user(user),
        'token': generate_auth_token(user),
    })

@app.route('/api/auth/nonce-exchange')
def nonce_exchange():
    nonce = request.args.get('nonce', '')
    token = _pop_oauth_nonce(nonce)
    if token:
        return jsonify({'success': True, 'token': token})
    return jsonify({'success': False}), 404

@app.route('/api/auth/logout', methods=['POST'])
def logout():
    """Logout current user"""
    session.pop('user_id', None)
    logout_user()
    return jsonify({'success': True, 'message': 'Logged out'})


# ── Google & Apple OAuth ──────────────────────────────────────────────

_google_client_id = os.environ.get('GOOGLE_CLIENT_ID')
_google_client_secret = os.environ.get('GOOGLE_CLIENT_SECRET')
_apple_client_id = os.environ.get('APPLE_CLIENT_ID')
_apple_ios_client_id = os.environ.get('APPLE_IOS_CLIENT_ID') or os.environ.get('IOS_BUNDLE_ID') or os.environ.get('CAPACITOR_APP_ID')
_apple_team_id = os.environ.get('APPLE_TEAM_ID')
_apple_key_id = os.environ.get('APPLE_KEY_ID')
_apple_private_key = os.environ.get('APPLE_PRIVATE_KEY', '')

_oauth_ready = bool(_google_client_id or _apple_client_id)

if _oauth_ready:
    from authlib.integrations.flask_client import OAuth as AuthlibOAuth
    _oauth = AuthlibOAuth(app)

    if _google_client_id:
        _oauth.register(
            name='google',
            client_id=_google_client_id,
            client_secret=_google_client_secret,
            server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
            client_kwargs={'scope': 'openid email profile'},
        )

    if _apple_client_id:
        def _normalize_pem(raw):
            """Reconstruct a valid PEM even if newlines were stripped."""
            raw = raw.replace('\\n', '\n').strip()
            if '\n' in raw and raw.startswith('-----'):
                return raw
            raw = raw.replace('-----BEGIN PRIVATE KEY-----', '').replace('-----END PRIVATE KEY-----', '')
            raw = raw.replace(' ', '').replace('\n', '').replace('\r', '')
            lines = [raw[i:i+64] for i in range(0, len(raw), 64)]
            return '-----BEGIN PRIVATE KEY-----\n' + '\n'.join(lines) + '\n-----END PRIVATE KEY-----\n'

        def _generate_apple_client_secret():
            import jwt as pyjwt, time as _t
            headers = {'kid': _apple_key_id, 'alg': 'ES256'}
            payload = {
                'iss': _apple_team_id,
                'iat': int(_t.time()),
                'exp': int(_t.time()) + 86400 * 180,
                'aud': 'https://appleid.apple.com',
                'sub': _apple_client_id,
            }
            pk = _normalize_pem(_apple_private_key)
            return pyjwt.encode(payload, pk, algorithm='ES256', headers=headers)

        try:
            _apple_secret = _generate_apple_client_secret()
            _oauth.register(
                name='apple',
                client_id=_apple_client_id,
                client_secret=_apple_secret,
                authorize_url='https://appleid.apple.com/auth/authorize',
                access_token_url='https://appleid.apple.com/auth/token',
                client_kwargs={'scope': 'name email', 'response_mode': 'form_post'},
            )
        except Exception as e:
            logging.error(f"Apple OAuth setup failed (PEM key issue?): {e}")
            _apple_client_id = None


def _oauth_find_or_create(email, provider, provider_id, first_name=None, plan='trial'):
    """Find existing user by email or OAuth ID, or create a new one.
    Returns (user, is_new) tuple."""
    from models import normalize_email
    from werkzeug.security import generate_password_hash
    import secrets

    user = None
    if provider_id:
        user = User.query.filter_by(oauth_provider=provider, oauth_id=provider_id).first()
    if not user and email:
        user = User.query.filter(func.lower(User.email) == email.lower()).first()

    if user:
        if provider_id and not user.oauth_id:
            user.oauth_provider = provider
            user.oauth_id = provider_id
            db.session.commit()
        return user, False

    norm = normalize_email(email) if email else None

    user = User(
        id=str(uuid.uuid4()),
        email=email.lower() if email else f'{provider}_{provider_id}@private.sharppicks.ai',
        email_normalized=norm,
        first_name=first_name or '',
        display_name=first_name or (email.split('@')[0] if email else ''),
        password_hash=generate_password_hash(secrets.token_urlsafe(32)),
        oauth_provider=provider,
        oauth_id=provider_id,
        is_premium=False,
        email_verified=True,
        subscription_status='free',
    )
    db.session.add(user)
    db.session.commit()

    _apply_pre_provisioned(user)

    try:
        send_admin_alert(
            "New OAuth Signup",
            f"{first_name or 'User'} ({user.email}) joined via {provider} as {plan}",
            {'type': 'new_signup', 'email': user.email, 'provider': provider, 'account_type': plan}
        )
    except Exception as e:
        logging.error(f"Admin OAuth signup alert failed: {e}")

    return user, True


def _get_apple_jwks():
    """Fetch and cache Apple's public keys for ID token verification."""
    from jwt import PyJWKClient
    import time
    global _apple_jwks_client, _apple_jwks_client_built_at
    now = time.time()
    # Rebuild periodically so key rotation is respected without per-request fetches.
    if _apple_jwks_client is None or now - _apple_jwks_client_built_at > 3600:
        _apple_jwks_client = PyJWKClient("https://appleid.apple.com/auth/keys")
        _apple_jwks_client_built_at = now
    return _apple_jwks_client


def _verify_apple_identity_token(identity_token, expected_audiences=None):
    """Verify Apple identity token signature + issuer + audience."""
    import jwt as pyjwt

    if not identity_token:
        raise ValueError("Missing identity token")

    if expected_audiences is None:
        expected_audiences = []
        if _apple_client_id:
            expected_audiences.append(_apple_client_id)
        if _apple_ios_client_id:
            expected_audiences.append(_apple_ios_client_id)
        # Preserve order while removing duplicates.
        expected_audiences = list(dict.fromkeys(expected_audiences))
    if not expected_audiences:
        raise ValueError("Apple client ID is not configured")

    signing_key = _get_apple_jwks().get_signing_key_from_jwt(identity_token).key
    return pyjwt.decode(
        identity_token,
        signing_key,
        algorithms=["RS256"],
        audience=expected_audiences,
        issuer="https://appleid.apple.com",
        options={"require": ["exp", "iat", "iss", "aud", "sub"]},
    )


def _redirect_replace(url):
    """Redirect using history.replaceState so the current page doesn't stay in browser history."""
    safe_url = url.replace("'", "\\'").replace('"', '&quot;')
    return Response(
        f'''<!DOCTYPE html><html><head><meta charset="utf-8">
<title>Redirecting…</title></head><body>
<script>window.location.replace('{safe_url}');</script>
<noscript><meta http-equiv="refresh" content="0;url={safe_url}"></noscript>
</body></html>''',
        content_type='text/html')

def _create_trial_checkout_url(user):
    """Create a Stripe Checkout session with a 14-day free trial (card required, $0 charged).
    Returns the checkout URL or None on failure."""
    try:
        from stripe_client import get_stripe_client
        stripe = get_stripe_client()

        if not user.stripe_customer_id:
            customer = stripe.Customer.create(email=user.email)
            user.stripe_customer_id = customer.id
            db.session.commit()

        prices = stripe.Price.list(active=True, limit=20)
        price_id = None
        yearly_prices = []
        for p in prices.data:
            if p.recurring and p.recurring.interval == 'year':
                yearly_prices.append(p)
        founding = [p for p in yearly_prices if p.unit_amount == 9900]
        standard = [p for p in yearly_prices if p.unit_amount == 14999]
        price_id = (founding[0].id if founding
                    else standard[0].id if standard
                    else yearly_prices[0].id if yearly_prices
                    else None)
        if not price_id and prices.data:
            price_id = prices.data[0].id
        if not price_id:
            logging.error("No Stripe prices configured for trial checkout")
            return None

        app_domain = os.environ.get('APP_DOMAIN', '') or os.environ.get('REPLIT_DOMAINS', 'app.sharppicks.ai').split(',')[0]

        checkout_session = stripe.checkout.Session.create(
            mode='subscription',
            payment_method_types=['card'],
            line_items=[{'price': price_id, 'quantity': 1}],
            subscription_data={
                'trial_period_days': 14,
                'metadata': {'plan': 'trial', 'user_id': user.id},
            },
            consent_collection={
                'terms_of_service': 'required',
            },
            custom_text={
                'submit': {
                    'message': 'Your trial is 14 days. You will not be charged today.',
                },
            },
            success_url=f'https://{app_domain}/welcome?session_id={{CHECKOUT_SESSION_ID}}',
            cancel_url=f'https://{app_domain}/subscribe',
            customer=user.stripe_customer_id,
            client_reference_id=user.id,
            metadata={'plan': 'trial', 'user_id': user.id},
        )
        return checkout_session.url
    except Exception as e:
        logging.error(f"Trial checkout creation failed: {e}")
        return None


@app.route('/auth/google')
def google_login():
    if not _oauth_ready or not _google_client_id:
        return jsonify({'error': 'Google sign-in not configured'}), 501
    session['oauth_plan'] = request.args.get('plan', 'trial')
    nonce = request.args.get('nonce', '')
    if nonce:
        session['oauth_nonce'] = nonce
    base = os.environ.get('APP_BASE_URL', request.host_url.rstrip('/'))
    redirect_uri = f"{base}/auth/google/callback"
    return _oauth.google.authorize_redirect(redirect_uri)


@app.route('/auth/google/callback')
def google_callback():
    try:
        token = _oauth.google.authorize_access_token()
        user_info = token.get('userinfo') or _oauth.google.parse_id_token(token, nonce=None)
    except Exception as e:
        logging.error(f"Google OAuth failed: {e}")
        return redirect('/login?error=google_failed')

    email = (user_info.get('email') or '').lower().strip()
    if not email:
        return redirect('/login?error=no_email')

    plan = session.pop('oauth_plan', 'trial')
    nonce = session.pop('oauth_nonce', None)
    given_name = user_info.get('given_name') or user_info.get('name', '').split()[0] if user_info.get('name') else ''
    user, is_new = _oauth_find_or_create(email, 'google', user_info.get('sub'), first_name=given_name, plan=plan)

    if not user.is_active:
        return redirect('/login?error=account_disabled')

    login_user(user, remember=True)
    session.permanent = True
    session['user_id'] = user.id
    session['session_token'] = user.session_token

    if nonce:
        _store_oauth_nonce(nonce, generate_auth_token(user))

    ua = (request.headers.get('User-Agent') or '').lower()
    is_ios = 'iphone' in ua or 'ipad' in ua or 'ipod' in ua
    if not is_ios and is_new and plan == 'trial':
        checkout_url = _create_trial_checkout_url(user)
        if checkout_url:
            return _redirect_replace(checkout_url)

    return _redirect_replace('/')


_apple_jwks_client = None
_apple_jwks_client_built_at = 0


@app.route('/auth/apple')
def apple_login():
    if not _oauth_ready or not _apple_client_id:
        return jsonify({'error': 'Apple sign-in not configured'}), 501
    session['oauth_plan'] = request.args.get('plan', 'trial')
    nonce = request.args.get('nonce', '')
    if nonce:
        session['oauth_nonce'] = nonce
    base = os.environ.get('APP_BASE_URL', request.host_url.rstrip('/'))
    redirect_uri = f"{base}/auth/apple/callback"
    return _oauth.apple.authorize_redirect(redirect_uri)


@app.route('/auth/apple/callback', methods=['POST'])
def apple_callback():
    try:
        token = _oauth.apple.authorize_access_token()
        raw_id_token = token.get('id_token')
        # Web OAuth callback should validate against the Services ID audience.
        id_token = _verify_apple_identity_token(raw_id_token, expected_audiences=[_apple_client_id])
    except Exception as e:
        logging.error(f"Apple OAuth failed: {e}")
        return redirect('/login?error=apple_failed')

    email = (id_token.get('email') or '').lower().strip()
    apple_sub = id_token.get('sub')
    if not email and not apple_sub:
        return redirect('/login?error=no_email')

    plan = session.pop('oauth_plan', 'trial')
    nonce = session.pop('oauth_nonce', None)

    first_name = None
    user_data = request.form.get('user')
    if user_data:
        import json as _json
        try:
            ud = _json.loads(user_data)
            name = ud.get('name', {})
            first_name = name.get('firstName') or name.get('givenName')
        except Exception:
            pass

    user, is_new = _oauth_find_or_create(email, 'apple', apple_sub, first_name=first_name, plan=plan)

    if not user.is_active:
        return redirect('/login?error=account_disabled')

    login_user(user, remember=True)
    session.permanent = True
    session['user_id'] = user.id
    session['session_token'] = user.session_token

    if nonce:
        _store_oauth_nonce(nonce, generate_auth_token(user))

    ua = (request.headers.get('User-Agent') or '').lower()
    is_ios = 'iphone' in ua or 'ipad' in ua or 'ipod' in ua
    if not is_ios and is_new and plan == 'trial':
        checkout_url = _create_trial_checkout_url(user)
        if checkout_url:
            return _redirect_replace(checkout_url)

    return _redirect_replace('/')


@app.route('/api/auth/apple-native', methods=['POST'])
@limiter.limit("10 per minute")
def apple_native_signin():
    """Verify an Apple identity token from native Sign in with Apple and authenticate the user."""
    data = request.get_json() or {}
    identity_token = (data.get('identityToken') or data.get('idToken') or '').strip()
    email = (data.get('email') or '').strip().lower()
    given_name = data.get('givenName') or data.get('firstName') or ''
    family_name = data.get('familyName') or data.get('lastName') or ''
    first_name = given_name or family_name or ''
    plan = (data.get('plan') or 'free').strip().lower()
    plan = 'trial' if plan == 'trial' else 'free'

    if not identity_token:
        return jsonify({'error': 'identityToken is required'}), 400

    if not _apple_ios_client_id:
        logging.warning("APPLE_IOS_CLIENT_ID not configured; falling back to hardcoded bundle ID. Set env var to remove fallback.")

    # Defensive: accept both the env-driven client ID and the hardcoded bundle ID.
    # The literal backstop can be removed once APPLE_IOS_CLIENT_ID is confirmed set in prod.
    expected_audiences = []
    if _apple_ios_client_id:
        expected_audiences.append(_apple_ios_client_id)
    expected_audiences.append('com.sharppicksllc.signals')
    expected_audiences = list(dict.fromkeys(expected_audiences))

    try:
        claims = _verify_apple_identity_token(identity_token, expected_audiences=expected_audiences)
    except Exception as e:
        logging.warning(f"Native Apple token verification failed: {e}")
        return jsonify({'success': False, 'error': 'Invalid Apple identity token'}), 401

    apple_sub = (claims.get('sub') or '').strip()
    token_email = (claims.get('email') or '').strip().lower()
    if not apple_sub:
        return jsonify({'success': False, 'error': 'Apple account identifier missing'}), 400

    user_email = email or token_email
    if not user_email:
        user_email = f'apple_{apple_sub}@private.sharppicks.ai'

    user, is_new = _oauth_find_or_create(user_email, 'apple', apple_sub, first_name=first_name, plan=plan)

    if not user.is_active:
        return jsonify({'success': False, 'error': 'Account is no longer active'}), 401

    try:
        login_user(user, remember=True)
        session.permanent = True
        session['user_id'] = user.id
        session['session_token'] = user.session_token

        token = generate_auth_token(user)
        return jsonify({
            'success': True,
            'token': token,
            'user': serialize_user(user),
            'is_new': is_new,
            'new_user': is_new,
            'plan': plan,
        })
    except Exception as e:
        logging.error(f"Apple native sign-in error: {e}")
        return jsonify({'error': 'Authentication failed'}), 500


@app.route('/api/auth/forgot-password', methods=['POST'])
@limiter.limit("3 per minute")
def forgot_password():
    from itsdangerous import URLSafeTimedSerializer
    data = request.get_json() or {}
    email = data.get('email', '').strip().lower()
    if not email:
        return jsonify({'error': 'Email required'}), 400

    user = User.query.filter(func.lower(User.email) == email).first()
    if not user:
        return jsonify({'success': True, 'message': 'If that email exists, a reset link has been generated.'})

    s = URLSafeTimedSerializer(app.config['SECRET_KEY'])
    token = s.dumps(user.id, salt='password-reset')
    base = os.environ.get('APP_BASE_URL', '').rstrip('/')
    if not base:
        domains = os.environ.get('REPLIT_DOMAINS', 'app.sharppicks.ai')
        base = f"https://{domains.split(',')[0]}"
    reset_url = f"{base}/reset-password?token={token}"

    from email_service import send_password_reset
    sent = send_password_reset(user.email, reset_url, user.first_name)
    logging.info(f"Password reset for {email}: email_sent={sent}")

    return jsonify({
        'success': True,
        'message': 'If that email exists, a password reset link has been sent.',
    })


@app.route('/api/auth/reset-password', methods=['POST'])
@limiter.limit("5 per minute")
def reset_password():
    from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadSignature
    from werkzeug.security import generate_password_hash

    data = request.get_json() or {}
    token = data.get('token', '')
    new_password = data.get('password', '')

    if not token or not new_password:
        return jsonify({'error': 'Token and new password required'}), 400
    if len(new_password) < 6:
        return jsonify({'error': 'Password must be at least 6 characters'}), 400

    s = URLSafeTimedSerializer(app.config['SECRET_KEY'])
    try:
        user_id = s.loads(token, salt='password-reset', max_age=3600)
    except SignatureExpired:
        return jsonify({'error': 'Reset link has expired. Please request a new one.'}), 400
    except BadSignature:
        return jsonify({'error': 'Invalid reset link.'}), 400

    user = db.session.get(User, user_id)
    if not user:
        return jsonify({'error': 'User not found.'}), 400

    user.password_hash = generate_password_hash(new_password)
    user.session_token = str(uuid.uuid4())
    db.session.commit()

    return jsonify({'success': True, 'message': 'Password updated successfully.'})


@app.route('/api/subscriptions/create-checkout', methods=['POST'])
def create_checkout():
    """Create Stripe checkout session for subscription"""
    user = get_current_user_from_session()
    if not user:
        return jsonify({'error': 'Authentication required'}), 401
    try:
        from stripe_client import get_stripe_client
        stripe = get_stripe_client()

        data = request.get_json() or {}
        plan = data.get('plan', 'monthly')
        price_id = data.get('price_id')

        price_map = {
            'monthly': os.environ.get('STRIPE_PRICE_MONTHLY'),
            'annual_founding': os.environ.get('STRIPE_PRICE_FOUNDING'),
            'annual_standard': os.environ.get('STRIPE_PRICE_ANNUAL'),
            'annual': os.environ.get('STRIPE_PRICE_ANNUAL'),
            'founding': os.environ.get('STRIPE_PRICE_FOUNDING'),
        }

        if not price_id:
            price_id = price_map.get(plan)

        if price_id:
            try:
                stripe.Price.retrieve(price_id)
            except Exception:
                logging.warning(f"Price {price_id} not found in connected Stripe account, auto-discovering...")
                price_id = None

        if not price_id:
            prices = stripe.Price.list(active=True, limit=20)
            monthly_prices = []
            yearly_prices = []
            for p in prices.data:
                if p.recurring:
                    if p.recurring.interval == 'month':
                        monthly_prices.append(p)
                    elif p.recurring.interval == 'year':
                        yearly_prices.append(p)

            if plan == 'monthly' and monthly_prices:
                exact = [p for p in monthly_prices if p.unit_amount == 1999]
                price_id = exact[0].id if exact else monthly_prices[0].id
            elif plan == 'trial' and yearly_prices:
                founding = [p for p in yearly_prices if p.unit_amount == 9900]
                standard = [p for p in yearly_prices if p.unit_amount == 14999]
                price_id = (founding[0].id if founding
                            else standard[0].id if standard
                            else yearly_prices[0].id)
            elif plan in ('founding', 'annual_founding') and yearly_prices:
                founding = [p for p in yearly_prices if p.unit_amount == 9900]
                price_id = founding[0].id if founding else yearly_prices[0].id
            elif plan in ('annual', 'annual_standard') and yearly_prices:
                standard = [p for p in yearly_prices if p.unit_amount == 14999]
                price_id = standard[0].id if standard else yearly_prices[-1].id
            elif prices.data:
                price_id = prices.data[0].id

        if not price_id:
            return jsonify({'error': 'No prices configured in Stripe'}), 400

        app_domain = os.environ.get('APP_DOMAIN', '') or os.environ.get('REPLIT_DOMAINS', 'app.sharppicks.ai').split(',')[0]
        subscribe_domain = os.environ.get('SUBSCRIBE_DOMAIN', app_domain)

        db_user = db.session.get(User, user['id'])
        customer_id = db_user.stripe_customer_id if db_user else None
        if not customer_id and db_user:
            customer = stripe.Customer.create(email=db_user.email)
            db_user.stripe_customer_id = customer.id
            db.session.commit()
            customer_id = customer.id

        is_trial_eligible = (
            db_user and
            not db_user.trial_used and
            db_user.subscription_status in ('free', 'pending_verification') and
            db_user.email_verified
        )

        checkout_params = {
            'payment_method_types': ['card'],
            'line_items': [{'price': price_id, 'quantity': 1}],
            'mode': 'subscription',
            'success_url': f'https://{app_domain}/welcome?session_id={{CHECKOUT_SESSION_ID}}',
            'cancel_url': f'https://{subscribe_domain}/subscribe',
            'client_reference_id': user['id'],
            'subscription_data': {
                'metadata': {'plan': plan, 'user_id': user['id']},
            },
            'metadata': {'plan': plan, 'user_id': user['id']},
            'consent_collection': {
                'terms_of_service': 'required',
            },
            'custom_text': {
                'submit': {
                    'message': 'Cancel anytime from your account settings — no questions asked.',
                },
            },
        }

        if is_trial_eligible and plan != 'monthly':
            checkout_params['subscription_data']['trial_period_days'] = 14
            checkout_params['custom_text']['submit']['message'] = (
                'Your trial is 14 days. You will not be charged today.'
            )

        if customer_id:
            checkout_params['customer'] = customer_id
        else:
            checkout_params['customer_email'] = db_user.email if db_user else None

        checkout_session = stripe.checkout.Session.create(**checkout_params)
        return jsonify({'checkout_url': checkout_session.url, 'session_id': checkout_session.id})
    except Exception as e:
        logging.error(f'Checkout error: {e}')
        return jsonify({'error': str(e)}), 500

@app.route('/api/subscriptions/cancel', methods=['POST'])
def cancel_subscription():
    """Cancel user subscription"""
    user = get_current_user_from_session()
    if not user:
        return jsonify({'error': 'Authentication required'}), 401
    try:
        from stripe_client import get_stripe_client
        stripe = get_stripe_client()
        db_user = db.session.get(User, user['id'])
        if not db_user or not db_user.stripe_customer_id:
            return jsonify({'error': 'No active subscription'}), 400
        # status='all' catches both 'active' and 'trialing' subs — trial
        # users were previously unable to cancel through this endpoint.
        def _sg(o, k, d=None):
            return o.get(k, d) if isinstance(o, dict) else getattr(o, k, d)
        subs = stripe.Subscription.list(customer=db_user.stripe_customer_id, status='all', limit=10)
        target_sub = None
        for s in subs.data:
            if _sg(s, 'status') in ('active', 'trialing'):
                target_sub = s
                break
        if target_sub:
            modified = stripe.Subscription.modify(target_sub.id, cancel_at_period_end=True)
            db_user.subscription_status = 'cancelling'
            db_user.cancel_scheduled_at = datetime.utcnow()
            cancel_at = _sg(modified, 'cancel_at') or _sg(modified, 'current_period_end')
            if cancel_at:
                db_user.cancel_effective_at = datetime.fromtimestamp(cancel_at)
            db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/subscriptions/reactivate', methods=['POST'])
def reactivate_subscription():
    """Reactivate a subscription that is set to cancel at period end"""
    user = get_current_user_from_session()
    if not user:
        return jsonify({'error': 'Authentication required'}), 401
    try:
        from stripe_client import get_stripe_client
        stripe = get_stripe_client()
        db_user = db.session.get(User, user['id'])
        if not db_user or not db_user.stripe_customer_id:
            return jsonify({'error': 'No subscription found'}), 400
        if db_user.subscription_status != 'cancelling':
            return jsonify({'error': 'Subscription is not in cancelling state'}), 400
        subs = stripe.Subscription.list(customer=db_user.stripe_customer_id, limit=1)
        reactivated = False
        for sub in subs.data:
            if sub.get('cancel_at_period_end'):
                stripe.Subscription.modify(sub.id, cancel_at_period_end=False)
                db_user.subscription_status = 'active'
                db_user.is_premium = True
                db_user.cancel_scheduled_at = None
                db_user.cancel_effective_at = None
                db.session.commit()
                reactivated = True
                break
        if not reactivated:
            return jsonify({'error': 'No cancelling subscription found in Stripe'}), 400
        return jsonify({'success': True, 'message': 'Subscription reactivated'})
    except Exception as e:
        logging.error(f"Reactivate error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/subscriptions/status')
def subscription_status():
    """Get current subscription status"""
    user = get_current_user_from_session()
    if not user:
        return jsonify({'error': 'Authentication required'}), 401
    db_user = db.session.get(User, user['id'])
    if not db_user:
        return jsonify({'error': 'User not found'}), 404
    return jsonify({
        'status': db_user.subscription_status,
        'plan': db_user.subscription_plan,
        'founding_member': db_user.founding_member,
        'founding_number': db_user.founding_number,
        'is_pro': db_user.is_pro,
        'trial_end_date': db_user.trial_end_date.isoformat() if db_user.trial_end_date else None,
        'current_period_end': db_user.current_period_end.isoformat() if db_user.current_period_end else None,
        'can_reactivate': db_user.subscription_status == 'cancelling' and db_user.current_period_end and db_user.current_period_end > datetime.now(),
    })

@app.route('/api/stripe/config')
def stripe_config():
    """Get Stripe publishable key for frontend"""
    try:
        from stripe_client import get_publishable_key
        return jsonify({'publishable_key': get_publishable_key()})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/stripe/billing-portal', methods=['POST'])
def create_billing_portal_session():
    """Create a Stripe Billing Portal session so the user can update card / manage sub.

    Used by the past_due gate to give users a one-click recovery path after a
    failed invoice. Falls back gracefully if no Stripe customer exists yet.
    """
    user = get_current_user_from_session()
    if not user:
        return jsonify({'error': 'Authentication required'}), 401

    db_user = db.session.get(User, user['id'])
    if not db_user:
        return jsonify({'error': 'User not found'}), 404

    if not db_user.stripe_customer_id:
        return jsonify({
            'error': 'No payment method on file. Please subscribe first.',
            'code': 'no_customer',
        }), 400

    try:
        stripe_obj = get_stripe_client()
    except Exception as e:
        logging.error(f'Stripe client unavailable: {e}')
        return jsonify({'error': 'Payments temporarily unavailable. Please try again shortly.'}), 503

    payload = request.get_json(silent=True) or {}
    return_url = payload.get('return_url')
    if not return_url:
        host = request.host_url.rstrip('/')
        return_url = f'{host}/?billing_return=1'

    try:
        portal = stripe_obj.billing_portal.Session.create(
            customer=db_user.stripe_customer_id,
            return_url=return_url,
        )
        portal_url = _safe_get(portal, 'url') if hasattr(portal, '__getitem__') else getattr(portal, 'url', None)
        if not portal_url:
            raise Exception('Portal URL missing in Stripe response')
        return jsonify({'url': portal_url})
    except Exception as e:
        logging.error(f'Billing portal create failed for {db_user.email}: {e}')
        return jsonify({
            'error': 'Could not open the billing portal. Please contact support@sharppicks.ai.',
        }), 500

def maybe_assign_founding(user_id):
    """Assign founding member status if spots remain — atomic with row-level lock"""
    from sqlalchemy import text as sql_text
    try:
        result = db.session.execute(
            sql_text("SELECT id, current_count, closed FROM founding_counter WHERE id = 1 FOR UPDATE"),
        )
        row = result.fetchone()
        if not row or row[2]:
            return
        current_count = row[1]
        if current_count >= 50:
            return

        user = db.session.get(User, user_id)
        if not user or user.founding_member:
            return

        new_count = current_count + 1
        closed = new_count >= 50
        db.session.execute(
            sql_text("UPDATE founding_counter SET current_count = :cnt, closed = :closed, last_updated_at = NOW() WHERE id = 1"),
            {'cnt': new_count, 'closed': closed}
        )
        user.founding_member = True
        user.founding_number = new_count
        db.session.commit()

        try:
            from notification_events import dispatch_founding_member_email
            dispatch_founding_member_email(user)
        except Exception as email_err:
            logging.error(f"Founding member email failed: {email_err}")

    except Exception as e:
        db.session.rollback()
        logging.error(f"Founding assignment error: {e}")

def _find_user_from_webhook(data_obj):
    """Find user by client_reference_id, metadata user_id, or customer id"""
    user_id = data_obj.get('client_reference_id') or data_obj.get('metadata', {}).get('user_id')
    if user_id:
        return db.session.get(User, user_id)
    cust_id = data_obj.get('customer')
    if cust_id:
        return User.query.filter_by(stripe_customer_id=cust_id).first()
    return None

@app.route('/webhooks/stripe', methods=['POST'])
@app.route('/api/stripe/webhook', methods=['POST'])
def stripe_webhook():
    """Handle Stripe webhook events.
    Listens for: checkout.session.completed, customer.subscription.updated,
    customer.subscription.deleted, invoice.paid, invoice.payment_failed"""
    import stripe as stripe_lib

    payload = request.data
    sig = request.headers.get('Stripe-Signature')
    webhook_secret = os.getenv('STRIPE_WEBHOOK_SECRET')

    logging.info(f'Stripe webhook received: sig={"yes" if sig else "no"}, secret={"yes" if webhook_secret else "no"}, payload_len={len(payload)}')

    def _safe_get(obj, key, default=None):
        """Safely get from dict or StripeObject (v14 and v15 compat)."""
        if isinstance(obj, dict):
            return obj.get(key, default)
        try:
            return obj.get(key, default)
        except (AttributeError, TypeError):
            return getattr(obj, key, default)

    try:
        if webhook_secret and sig:
            try:
                event = stripe_lib.Webhook.construct_event(payload, sig, webhook_secret)
            except AttributeError:
                import json
                event = json.loads(payload)
        elif webhook_secret and not sig:
            logging.warning('Stripe webhook: signature header missing but secret configured')
            return jsonify({'error': 'Missing Stripe-Signature header'}), 400
        else:
            logging.warning(f'Stripe webhook: no STRIPE_WEBHOOK_SECRET configured (production={is_production}), processing unverified')
            import json
            event = json.loads(payload)

        if isinstance(event, dict):
            event_id = event.get('id', '')
            event_type = event.get('type', '')
            data_obj = event.get('data', {}).get('object', {})
        else:
            event_id = getattr(event, 'id', '') or ''
            event_type = getattr(event, 'type', '') or ''
            event_data = getattr(event, 'data', {})
            data_obj = _safe_get(event_data, 'object', {}) if event_data else {}
        logging.info(f'Stripe webhook: {event_type} (event_id={event_id})')

        if event_id:
            try:
                db.session.add(ProcessedEvent(id=event_id, event_type=event_type))
                db.session.flush()
            except Exception:
                db.session.rollback()
                logging.info(f'Skipping duplicate webhook event: {event_id}')
                return jsonify({'success': True, 'duplicate': True}), 200

        def _log_revenue_alert(alert_type, email, detail, stripe_eid=None):
            try:
                db.session.add(AdminAlert(
                    event_type=alert_type, user_email=email,
                    detail=detail, stripe_event_id=stripe_eid or event_id,
                ))
                db.session.flush()
            except Exception:
                pass
            try:
                send_admin_alert(alert_type, detail)
            except Exception:
                pass

        if event_type == 'checkout.session.completed':
            user_id = _safe_get(data_obj, 'client_reference_id') or _safe_get(_safe_get(data_obj, 'metadata', {}), 'user_id')
            plan = _safe_get(_safe_get(data_obj, 'metadata', {}), 'plan', 'monthly')
            if user_id:
                user = db.session.get(User, user_id)
                if user:
                    user.subscription_plan = plan
                    user.subscription_start_date = datetime.now()
                    user.stripe_customer_id = _safe_get(data_obj, 'customer')
                    sub_id = _safe_get(data_obj, 'subscription')
                    user.pro_source = 'stripe'
                    if sub_id:
                        try:
                            from stripe_client import get_stripe_client
                            stripe_obj = get_stripe_client()
                            sub = stripe_obj.Subscription.retrieve(sub_id)
                            sub_status = _safe_get(sub, 'status', 'active')
                            if sub_status == 'trialing':
                                user.subscription_status = 'trial'
                                user.is_premium = True
                                user.trial_used = True
                                user.trial_start_date = datetime.now()
                                trial_end = _safe_get(sub, 'trial_end')
                                if trial_end:
                                    user.trial_end_date = datetime.fromtimestamp(trial_end)
                                    user.trial_ends = datetime.fromtimestamp(trial_end)
                            else:
                                user.subscription_status = 'active'
                                user.is_premium = True
                            period_end = _safe_get(sub, 'current_period_end')
                            if period_end:
                                user.current_period_end = datetime.fromtimestamp(period_end)
                        except Exception as sub_err:
                            logging.error(f'Stripe sub retrieve failed: {sub_err}')
                            user.subscription_status = 'active'
                            user.is_premium = True
                    else:
                        user.subscription_status = 'active'
                        user.is_premium = True
                    db.session.commit()
                    if plan in ('annual', 'founding', 'annual_founding'):
                        maybe_assign_founding(user_id)

        elif event_type == 'customer.subscription.created':
            cust_id = _safe_get(data_obj, 'customer')
            status = _safe_get(data_obj, 'status')
            if cust_id:
                user = User.query.filter_by(stripe_customer_id=cust_id).first()
                if user:
                    plan_meta = _safe_get(_safe_get(data_obj, 'metadata', {}), 'plan')
                    if plan_meta:
                        user.subscription_plan = plan_meta
                    if status == 'active':
                        user.subscription_status = 'active'
                        user.is_premium = True
                    elif status == 'trialing':
                        user.subscription_status = 'trial'
                        user.is_premium = True
                        trial_end = _safe_get(data_obj, 'trial_end')
                        if trial_end:
                            user.trial_end_date = datetime.fromtimestamp(trial_end)
                    period_end = _safe_get(data_obj, 'current_period_end')
                    if period_end:
                        user.current_period_end = datetime.fromtimestamp(period_end)
                    db.session.commit()
                    _log_revenue_alert('subscription_created', user.email,
                        f'New subscriber: {user.email} — {plan_meta or status}')

                    # Direct active-on-annual signup (no trial) still
                    # claims a founding slot. Same idempotent helper as
                    # the trial->paid path below.
                    if (user.subscription_status == 'active'
                            and user.subscription_plan in ('annual', 'founding', 'annual_founding')
                            and not user.founding_member):
                        try:
                            maybe_assign_founding(user.id)
                        except Exception as fa_err:
                            logging.error(f'Founding auto-assign (subscription.created) failed: {fa_err}')

        elif event_type == 'customer.subscription.updated':
            cust_id = _safe_get(data_obj, 'customer')
            status = _safe_get(data_obj, 'status')
            cancel_at_period_end = bool(_safe_get(data_obj, 'cancel_at_period_end'))
            cancel_at_ts = _safe_get(data_obj, 'cancel_at')
            canceled_at_ts = _safe_get(data_obj, 'canceled_at')
            if cust_id:
                user = User.query.filter_by(stripe_customer_id=cust_id).first()
                if user:
                    old_status = user.subscription_status
                    plan_meta = _safe_get(_safe_get(data_obj, 'metadata', {}), 'plan')
                    if plan_meta:
                        user.subscription_plan = plan_meta

                    # Detect trial -> paid conversion. Only fires once per
                    # user (idempotent via the null check) so re-deliveries
                    # don't move the timestamp forward.
                    if (old_status == 'trial'
                            and status == 'active'
                            and user.trial_converted_at is None):
                        user.trial_converted_at = datetime.utcnow()

                    # cancel_at_period_end is the source-of-truth signal
                    # for "user has scheduled a cancel" — works whether
                    # the cancel came from our /api/subscriptions/cancel
                    # endpoint OR from the Stripe Customer Portal.
                    #
                    # IMPORTANT: subscription_status reflects the BILLING
                    # TIER (trial/active/cancelled). cancel_scheduled_at
                    # is the orthogonal CANCEL-INTENT flag. We only flip
                    # subscription_status to 'cancelling' for active subs
                    # (preserving back-compat with the existing
                    # /reactivate endpoint and is_pro property). Trial
                    # users with a cancel queued stay status='trial' so
                    # they remain visible in the Trial Pipeline.
                    if cancel_at_period_end and status in ('active', 'trialing'):
                        if user.cancel_scheduled_at is None:
                            user.cancel_scheduled_at = (
                                datetime.fromtimestamp(canceled_at_ts) if canceled_at_ts else datetime.utcnow()
                            )
                        if cancel_at_ts:
                            user.cancel_effective_at = datetime.fromtimestamp(cancel_at_ts)
                        if status == 'active':
                            user.subscription_status = 'cancelling'
                        else:
                            user.subscription_status = 'trial'  # keep them in trial bucket
                        user.is_premium = True  # they keep access until cancel_effective_at
                    elif not cancel_at_period_end and (old_status == 'cancelling' or user.cancel_scheduled_at is not None) and status in ('active', 'trialing'):
                        # Reactivation through any path (our endpoint or portal)
                        user.cancel_scheduled_at = None
                        user.cancel_effective_at = None
                        user.subscription_status = 'active' if status == 'active' else 'trial'
                        user.is_premium = True
                    elif status == 'active':
                        user.subscription_status = 'active'
                        user.is_premium = True
                    elif status == 'trialing':
                        user.subscription_status = 'trial'
                        user.is_premium = True
                        trial_end = _safe_get(data_obj, 'trial_end')
                        if trial_end:
                            user.trial_end_date = datetime.fromtimestamp(trial_end)
                    elif status == 'canceled':
                        user.subscription_status = 'cancelled'
                        user.is_premium = False
                    elif status in ('unpaid', 'incomplete_expired'):
                        user.subscription_status = 'expired'
                        user.is_premium = False
                    elif status == 'past_due':
                        user.subscription_status = 'past_due'
                        user.is_premium = False

                    period_end = _safe_get(data_obj, 'current_period_end')
                    if period_end:
                        user.current_period_end = datetime.fromtimestamp(period_end)
                    db.session.commit()
                    _log_revenue_alert('subscription_updated', user.email,
                        f'Plan change: {user.email} — {old_status} → {user.subscription_status}'
                        + (' (cancel scheduled)' if cancel_at_period_end else ''))

                    # Trial -> paid annual (or any path that lands them on an
                    # active annual plan without a checkout.session.completed
                    # event — Customer Portal upgrades, retried payments,
                    # etc.) should also try to claim a founding slot.
                    # maybe_assign_founding is idempotent: if the user is
                    # already founding or the 50-slot cap is hit, it bails
                    # safely. Same plan-string set as the
                    # checkout.session.completed handler above so a
                    # founding-rate trial that converts here gets the same
                    # treatment as one that came in through checkout.
                    if (user.subscription_status == 'active'
                            and user.subscription_plan in ('annual', 'founding', 'annual_founding')
                            and not user.founding_member):
                        try:
                            maybe_assign_founding(user.id)
                        except Exception as fa_err:
                            logging.error(f'Founding auto-assign (subscription.updated) failed: {fa_err}')

        elif event_type == 'customer.subscription.deleted':
            cust_id = _safe_get(data_obj, 'customer')
            if cust_id:
                user = User.query.filter_by(stripe_customer_id=cust_id).first()
                if user:
                    user.subscription_status = 'cancelled'
                    user.is_premium = False
                    db.session.commit()
                    logging.info(f'Subscription cancelled for user {user.email}')
                    _log_revenue_alert('subscription_deleted', user.email,
                        f'Churn: {user.email} canceled')
                    try:
                        from email_service import send_cancellation_email
                        send_cancellation_email(user.email, user.first_name, user.current_period_end, user.founding_member)
                    except Exception as e:
                        logging.error(f"Cancellation email failed: {e}")

        elif event_type in ('invoice.paid', 'invoice.payment_succeeded'):
            cust_id = _safe_get(data_obj, 'customer')
            if cust_id:
                user = User.query.filter_by(stripe_customer_id=cust_id).first()
                if user:
                    # Stripe fires invoice.paid for the $0 invoice that opens
                    # a trial. If we treat that as a real payment we'd flip
                    # the user from 'trial' -> 'active' on day one and the
                    # admin dashboard renders them as paid. Only flip status
                    # when actual money moved. The 'subscription.created/
                    # updated' handlers above keep status='trial' until the
                    # trial actually ends.
                    amount_paid = _safe_get(data_obj, 'amount_paid', 0) or 0
                    if amount_paid > 0:
                        was_trial = user.subscription_status == 'trial'
                        if was_trial and user.trial_converted_at is None:
                            user.trial_converted_at = datetime.utcnow()
                        user.subscription_status = 'active'
                        user.is_premium = True
                    lines_obj = _safe_get(data_obj, 'lines', {})
                    lines = _safe_get(lines_obj, 'data', []) if lines_obj else []
                    for line in lines:
                        period = _safe_get(line, 'period', {})
                        period_end = _safe_get(period, 'end') if period else None
                        if period_end:
                            user.current_period_end = datetime.fromtimestamp(period_end)
                            break
                    db.session.commit()
                    logging.info(f'Invoice paid for user {user.email} (amount_paid={amount_paid})')

        elif event_type == 'invoice.payment_failed':
            cust_id = _safe_get(data_obj, 'customer')
            if cust_id:
                user = User.query.filter_by(stripe_customer_id=cust_id).first()
                if user:
                    # Revoke immediately on the first failed attempt — no grace period.
                    # The User.is_pro property already excludes past_due, but we flip the
                    # underlying is_premium column so the DB matches the access decision.
                    user.subscription_status = 'past_due'
                    user.is_premium = False
                    db.session.commit()
                    logging.warning(f'Payment failed for user {user.email} — access revoked')
                    _log_revenue_alert('payment_failed', user.email,
                        f'Failed payment: {user.email} ({user.subscription_plan}) — access revoked')
                    try:
                        from email_service import send_payment_failed_email
                        send_payment_failed_email(user.email, user.first_name)
                    except Exception as e:
                        logging.error(f"Payment failed email error: {e}")

        db.session.commit()

    except stripe_lib.SignatureVerificationError as e:
        logging.error(f'Stripe webhook signature failed: {e}')
        return jsonify({'error': 'Invalid signature'}), 400
    except ValueError as e:
        logging.error(f'Stripe webhook invalid payload: {e}')
        return jsonify({'error': 'Invalid payload'}), 400
    except Exception as e:
        try:
            db.session.rollback()
        except Exception:
            pass
        logging.error(f'Stripe webhook error: {e}', exc_info=True)
        try:
            send_admin_alert("Stripe Webhook Error", f"Failed: {str(e)[:200]}")
        except Exception:
            pass
        return jsonify({'success': True, 'note': 'processed with error'}), 200

    return jsonify({'success': True})


@app.route('/api/webhooks/revenuecat', methods=['POST'])
def revenuecat_webhook():
    """Handle RevenueCat webhook events for iOS IAP.
    Events: INITIAL_PURCHASE, RENEWAL, EXPIRATION, CANCELLATION,
    BILLING_ISSUE, PRODUCT_CHANGE, UNCANCELLATION"""
    rc_secret = os.getenv('REVENUECAT_WEBHOOK_SECRET', '')
    auth_header = request.headers.get('Authorization', '')

    if not rc_secret or auth_header != f'Bearer {rc_secret}':
        logging.warning('RevenueCat webhook: invalid auth')
        return jsonify({'error': 'Unauthorized'}), 401

    try:
        payload = request.get_json(force=True)
        event = payload.get('event', {})
        event_type = event.get('type', '')
        event_id = event.get('id', '')
        app_user_id = event.get('app_user_id', '')
        expiration_ms = event.get('expiration_at_ms')

        if not event_type or not event_id:
            return jsonify({'error': 'Missing event type or id'}), 400

        logging.info(f'RevenueCat webhook: {event_type} (event_id={event_id}, user={app_user_id})')

        if event_id:
            try:
                db.session.add(ProcessedEvent(id=event_id, event_type=f'rc_{event_type}'))
                db.session.flush()
            except Exception:
                db.session.rollback()
                logging.info(f'Skipping duplicate RevenueCat event: {event_id}')
                return jsonify({'status': 'ok', 'duplicate': True}), 200

        if not app_user_id:
            logging.warning(f'RevenueCat webhook: no app_user_id in event {event_id}')
            return jsonify({'status': 'ok', 'note': 'no user id'}), 200

        user = db.session.get(User, app_user_id)
        if not user:
            logging.warning(f'RevenueCat webhook: user {app_user_id} not found')
            return jsonify({'status': 'ok', 'note': 'user not found'}), 200

        expires_at = None
        if expiration_ms:
            expires_at = datetime.fromtimestamp(expiration_ms / 1000)

        if event_type in ('INITIAL_PURCHASE', 'RENEWAL', 'PRODUCT_CHANGE', 'UNCANCELLATION'):
            user.is_premium = True
            user.subscription_status = 'active'
            user.pro_source = 'revenuecat'
            if expires_at:
                user.current_period_end = expires_at
            product_id = event.get('product_id', '')
            if product_id:
                user.subscription_plan = 'annual' if 'yearly' in product_id or 'annual' in product_id else 'monthly'
            db.session.commit()
            logging.info(f'RevenueCat: Pro activated for {user.email} via {event_type}')
            try:
                send_admin_alert(
                    f'RC {event_type}',
                    f'{user.email} — Pro activated via iOS IAP ({product_id})',
                )
            except Exception:
                pass

        elif event_type == 'EXPIRATION':
            user.is_premium = False
            user.subscription_status = 'expired'
            user.current_period_end = expires_at
            db.session.commit()
            logging.info(f'RevenueCat: Pro expired for {user.email}')
            try:
                send_admin_alert('RC EXPIRATION', f'{user.email} — iOS subscription expired')
            except Exception:
                pass

        elif event_type in ('CANCELLATION', 'BILLING_ISSUE'):
            logging.warning(f'RevenueCat: {event_type} for {user.email} — retaining access until expiry')
            if event_type == 'BILLING_ISSUE':
                user.subscription_status = 'past_due'
                db.session.commit()
            try:
                send_admin_alert(f'RC {event_type}', f'{user.email} — {event_type.lower()} (access retained)')
            except Exception:
                pass

        else:
            logging.info(f'RevenueCat: unhandled event type {event_type} for {user.email}')

        db.session.commit()

    except Exception as e:
        db.session.rollback()
        logging.error(f'RevenueCat webhook error: {e}')
        try:
            send_admin_alert('RC Webhook Error', f'RevenueCat webhook failed: {str(e)[:200]}')
        except Exception:
            pass
        return jsonify({'error': str(e)}), 400

    return jsonify({'status': 'ok'})


@app.route('/api/stripe/products')
def list_products():
    """List available subscription products"""
    try:
        from stripe_client import get_stripe_client
        stripe = get_stripe_client()
        
        products = stripe.Product.list(active=True, limit=10)
        result = []
        
        for product in products.data:
            prices = stripe.Price.list(product=product.id, active=True)
            result.append({
                'id': product.id,
                'name': product.name,
                'description': product.description,
                'prices': [{
                    'id': p.id,
                    'unit_amount': p.unit_amount,
                    'currency': p.currency,
                    'interval': p.recurring.interval if p.recurring else None
                } for p in prices.data]
            })
        
        return jsonify({'products': result})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/auth/unit-size', methods=['POST'])
def set_unit_size():
    """Set user's unit size (dollars per 1u)"""
    user = get_current_user_obj()
    if not user:
        return jsonify({'error': 'Not authenticated'}), 401
    data = request.get_json() or {}
    unit_size = max(1, int(data.get('unit_size', 100)))
    user.unit_size = unit_size
    db.session.commit()
    return jsonify({'success': True, 'unit_size': user.unit_size})

@app.route('/api/auth/trial', methods=['POST'])
def start_trial():
    """Start 14-day trial — creates free account, returns Stripe checkout URL for card collection"""
    from flask import request
    import re

    data = request.get_json() or {}
    email = data.get('email', '').strip().lower()
    password = data.get('password', '')

    # iOS clients must use IAP (App Store Guideline 3.1.1); never hand
    # them a Stripe checkout URL even via this legacy endpoint.
    ua_lower = (request.headers.get('User-Agent') or '').lower()
    is_ios = 'iphone' in ua_lower or 'ipad' in ua_lower or 'ipod' in ua_lower

    if not email:
        return jsonify({'error': 'Email required'}), 400

    if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
        return jsonify({'error': 'Invalid email format'}), 400

    user = User.query.filter(func.lower(User.email) == email.lower()).first()

    if user:
        if user.trial_used:
            return jsonify({
                'success': False,
                'error': 'Trial already used for this email. Subscribe to continue.',
                'trial_expired': True
            }), 400

        login_user(user, remember=True)
        session.permanent = True
        session['user_id'] = user.id
        session['session_token'] = user.session_token

        if not is_ios and not user.is_premium:
            checkout_url = _create_trial_checkout_url(user)
            if checkout_url:
                return jsonify({'success': True, 'needs_checkout': True, 'checkout_url': checkout_url})

        return jsonify({
            'success': True,
            'user': serialize_user(user),
        })

    if not password or len(password) < 6:
        return jsonify({'error': 'Password required (6+ characters)'}), 400

    user = User()
    user.id = str(uuid.uuid4())
    user.email = email
    user.first_name = email.split('@')[0]
    user.set_password(password)
    user.is_premium = False
    user.subscription_status = 'free'
    user.email_verified = True

    db.session.add(user)
    db.session.commit()
    login_user(user, remember=True)
    session.permanent = True
    session['user_id'] = user.id
    session['session_token'] = user.session_token

    if not is_ios:
        checkout_url = _create_trial_checkout_url(user)
        if checkout_url:
            return jsonify({'success': True, 'needs_checkout': True, 'checkout_url': checkout_url})

    return jsonify({
        'success': True,
        'user': {
            'id': user.id,
            'email': user.email,
            'is_premium': True,
            'subscription_status': 'trial',
            'trial_ends': user.trial_ends.isoformat(),
            'message': 'Welcome! Your account is active. Explore SharpPicks Pro.'
        }
    })

@app.route('/api/auth/check-trial')
def check_trial():
    """Check if trial is still active - requires valid UUID user_id"""
    from flask import request
    import re
    
    user_id = request.args.get('user_id', '').strip()
    
    if not user_id:
        return jsonify({'error': 'No user ID provided'}), 400
    
    uuid_pattern = re.compile(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$', re.I)
    if not uuid_pattern.match(user_id):
        return jsonify({'error': 'Invalid user ID format'}), 400
    
    user = User.query.get(user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    trial_active = False
    if user.trial_ends:
        trial_active = datetime.now() < user.trial_ends
        
        if not trial_active and user.is_premium and user.trial_used:
            user.is_premium = False
            db.session.commit()
    
    return jsonify({
        'is_premium': user.is_premium,
        'trial_active': trial_active,
        'trial_ends': user.trial_ends.isoformat() if user.trial_ends else None,
        'days_remaining': max(0, (user.trial_ends - datetime.now()).days) if user.trial_ends else 0
    })

@app.route('/api/user/stats')
def get_user_stats():
    """Get user's betting stats from tracked bets with equity curve and streak data"""
    user = get_current_user_from_session()
    if not user:
        return jsonify({'error': 'Not authenticated'}), 401
    
    bets = TrackedBet.query.filter_by(user_id=user['id']).all()

    # Withdrawn (revoked) bets are invisible to performance metrics — the
    # signal was pulled before tipoff so the user's stake conceptually
    # never went into action. They do not contribute to record, ROI,
    # profit, selectivity, or capital preserved.
    settled = [b for b in bets if b.result in ('W', 'L', 'P')]
    active_bets = [b for b in bets if not b.result]
    settled_sorted = sorted(settled, key=lambda x: x.created_at)
    wins = sum(1 for b in settled if b.result == 'W')
    losses = sum(1 for b in settled if b.result == 'L')
    pushes = sum(1 for b in settled if b.result == 'P')
    total_profit = sum(b.profit or 0 for b in settled)
    total_risked = sum(b.bet_amount or 0 for b in settled)
    
    current_streak = 0
    current_streak_type = ''
    best_win_streak = 0
    worst_loss_streak = 0
    ws = 0
    ls = 0
    for b in settled_sorted:
        if b.result == 'W':
            ws += 1
            ls = 0
            best_win_streak = max(best_win_streak, ws)
        elif b.result == 'L':
            ls += 1
            ws = 0
            worst_loss_streak = max(worst_loss_streak, ls)
        else:
            ws = 0
            ls = 0
    
    for b in reversed(settled_sorted):
        if not current_streak_type:
            current_streak_type = b.result
            current_streak = 1
        elif b.result == current_streak_type:
            current_streak += 1
        else:
            break
    
    equity_curve = []
    running = 0
    for b in settled_sorted:
        running += (b.profit or 0)
        equity_curve.append({
            'date': b.created_at.strftime('%Y-%m-%d') if b.created_at else None,
            'value': round(running, 2),
            'label': b.pick,
            'result': b.result,
        })
    
    monthly = {}
    for b in settled_sorted:
        key = b.created_at.strftime('%Y-%m') if b.created_at else 'unknown'
        if key not in monthly:
            monthly[key] = {'wins': 0, 'losses': 0, 'pnl': 0, 'bets': 0, 'risked': 0}
        monthly[key]['bets'] += 1
        monthly[key]['risked'] += (b.bet_amount or 0)
        monthly[key]['pnl'] += (b.profit or 0)
        if b.result == 'W':
            monthly[key]['wins'] += 1
        elif b.result == 'L':
            monthly[key]['losses'] += 1
    
    month_names = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
    monthly_breakdown = []
    for key in sorted(monthly.keys(), reverse=True):
        parts = key.split('-')
        if len(parts) == 2:
            label = f"{month_names[int(parts[1])-1]} {parts[0]}"
        else:
            label = key
        m = monthly[key]
        monthly_breakdown.append({
            'label': label,
            'wins': m['wins'],
            'losses': m['losses'],
            'bets': m['bets'],
            'pnl': round(m['pnl'], 2),
            'roi': round(m['pnl'] / m['risked'] * 100, 1) if m['risked'] > 0 else 0,
        })
    
    avg_bet = round(total_risked / len(settled), 2) if settled else 0
    avg_odds = round(sum(b.odds or 0 for b in settled) / len(settled)) if settled else 0
    biggest_win = max((b.profit or 0 for b in settled), default=0)
    biggest_loss = min((b.profit or 0 for b in settled), default=0)
    
    roi = (total_profit / total_risked * 100) if total_risked > 0 else 0
    win_rate = (wins / len(settled) * 100) if settled else 0
    
    sharp_bets = [b for b in bets if (b.source == 'sharp_pick' or (b.source is None and b.pick_id)) and b.result != 'revoked']
    total_sharp_picks_available = Pick.query.count()
    exact_follows = sum(1 for b in sharp_bets if (b.follow_type or 'exact') == 'exact')
    adherence_score = round(exact_follows / len(sharp_bets) * 100, 1) if sharp_bets else None
    picks_followed = len(sharp_bets)

    line_deltas = []
    for b in sharp_bets:
        if b.linked_pick and b.line_at_bet is not None and b.linked_pick.line is not None:
            delta = abs(b.line_at_bet - b.linked_pick.line)
            line_deltas.append(delta)
    avg_line_delta = round(sum(line_deltas) / len(line_deltas), 1) if line_deltas else None

    model_pnl = 0
    user_pnl_on_sharp = 0
    for b in sharp_bets:
        if b.linked_pick and b.linked_pick.result in ('win', 'loss'):
            model_pnl += (b.linked_pick.pnl or 0) / max(1, len([x for x in sharp_bets if x.pick_id == b.pick_id]))
        if b.result:
            user_pnl_on_sharp += (b.profit or 0)

    total_passes_count = Pass.query.count()
    user_selectivity = round((picks_followed / total_sharp_picks_available) * 100, 1) if total_sharp_picks_available > 0 else 0
    picks_passed = total_sharp_picks_available - picks_followed
    capital_preserved = round(picks_passed * avg_bet * 0.04, 0) if avg_bet > 0 else round(picks_passed * 110 * 0.04, 0)

    bet_dates = sorted([b.created_at for b in bets if b.created_at])
    if len(bet_dates) >= 2:
        total_span = (bet_dates[-1] - bet_dates[0]).days
        avg_days_between = round(total_span / (len(bet_dates) - 1), 1) if len(bet_dates) > 1 else 0
    elif len(bet_dates) == 1:
        avg_days_between = 0
    else:
        avg_days_between = 0

    unit_size = user.get('unit_size') or 100
    total_units_profit = round(total_profit / unit_size, 2) if unit_size else 0

    return jsonify({
        'totalProfit': round(total_profit, 2),
        'totalUnitsProfit': total_units_profit,
        'roi': round(roi, 1),
        'totalBets': len(settled),
        'pendingBets': len(active_bets),
        'wins': wins,
        'losses': losses,
        'pushes': pushes,
        'winRate': round(win_rate, 1),
        'totalRisked': round(total_risked, 2),
        'avgBet': avg_bet,
        'avgOdds': avg_odds,
        'biggestWin': round(biggest_win, 2),
        'biggestLoss': round(biggest_loss, 2),
        'streak': {
            'current': current_streak,
            'currentType': current_streak_type,
            'bestWin': best_win_streak,
            'worstLoss': worst_loss_streak,
        },
        'equityCurve': equity_curve,
        'monthlyBreakdown': monthly_breakdown,
        'adherence': {
            'picks_followed': picks_followed,
            'total_published': total_sharp_picks_available,
            'exact_follows': exact_follows,
            'adherence_score': adherence_score,
            'avg_line_delta': avg_line_delta,
        },
        'outcome_split': {
            'model_pnl': round(model_pnl, 2),
            'user_pnl': round(user_pnl_on_sharp, 2),
            'difference': round(user_pnl_on_sharp - model_pnl, 2),
        },
        'behavioral': {
            'selectivity': user_selectivity,
            'industry_avg': 78,
            'picks_followed': picks_followed,
            'picks_passed': picks_passed,
            'total_published': total_sharp_picks_available,
            'total_passes': total_passes_count,
            'avg_days_between': avg_days_between,
            'capital_preserved': capital_preserved,
            'restraint_grade': 'A+' if user_selectivity <= 20 else 'A' if user_selectivity <= 35 else 'B+' if user_selectivity <= 50 else 'B' if user_selectivity <= 65 else 'C',
        },
        'source_comparison': _compute_source_comparison(settled, sharp_bets),
    })


def _compute_source_comparison(settled, sharp_bets):
    """Compare model-followed bets vs off-model manual bets, broken down by type."""
    sharp_ids = {b.id for b in sharp_bets}
    model_settled = [b for b in settled if b.id in sharp_ids]
    manual_settled = [b for b in settled if b.id not in sharp_ids]

    def _bucket_stats(bucket):
        w = sum(1 for b in bucket if b.result == 'W')
        l = sum(1 for b in bucket if b.result == 'L')
        pnl = sum(b.profit or 0 for b in bucket)
        risked = sum(b.bet_amount or 0 for b in bucket)
        return {
            'bets': len(bucket),
            'wins': w,
            'losses': l,
            'win_rate': round(w / len(bucket) * 100, 1) if bucket else 0,
            'pnl': round(pnl, 2),
            'roi': round(pnl / risked * 100, 1) if risked > 0 else 0,
        }

    by_type = {}
    for bt in ('spread', 'total', 'moneyline', 'prop', 'parlay'):
        typed = [b for b in manual_settled if (getattr(b, 'bet_type', None) or 'spread') == bt]
        if typed:
            stats = _bucket_stats(typed)
            if bt == 'parlay':
                legs = [getattr(b, 'parlay_legs', None) or 0 for b in typed]
                stats['avg_legs'] = round(sum(legs) / len(legs), 1) if legs else 0
            by_type[bt] = stats

    return {
        'model': _bucket_stats(model_settled),
        'off_model': _bucket_stats(manual_settled),
        'off_model_by_type': by_type,
    }

@app.route('/api/bets', methods=['GET'])
def get_user_bets():
    """Get user's tracked bets"""
    user = get_current_user_obj()
    if not user:
        return jsonify({'error': 'Login required'}), 401
    sport = request.args.get('sport')
    q = TrackedBet.query.filter_by(user_id=user.id)
    if sport:
        q = q.outerjoin(Pick, TrackedBet.pick_id == Pick.id).filter(
            db.or_(TrackedBet.pick_id.is_(None), Pick.sport == sport)
        )
    bets = q.order_by(TrackedBet.created_at.desc()).all()
    needs_commit = False
    tracked_pick_ids = set()
    bet_list = []
    for b in bets:
        if b.pick_id:
            tracked_pick_ids.add(b.pick_id)
        pick_result = None
        if b.linked_pick and b.linked_pick.result:
            pr = b.linked_pick.result.lower()
            if pr == 'win':
                pick_result = 'W'
            elif pr == 'loss':
                pick_result = 'L'
            elif pr == 'pending':
                pick_result = 'pending'
            else:
                pick_result = b.linked_pick.result
            # Revoked picks are intentionally NOT auto-settled here — the
            # model_service revoke handler now cascades tb.result = 'revoked'
            # in the same transaction (see model_service.py revalidate_pretip).
            # Those rows surface in this response with result='revoked' and
            # are bucketed into the frontend "Withdrawn" section.
            if not b.result and pick_result and pick_result not in ('pending', 'revoked'):
                b.result = pick_result
                if pick_result == 'W':
                    if b.odds and b.odds < 0:
                        b.profit = round(b.bet_amount * (100 / abs(b.odds)), 2)
                    elif b.odds:
                        b.profit = round(b.bet_amount * (b.odds / 100), 2)
                    else:
                        b.profit = round(b.bet_amount * (100 / 110), 2)
                elif pick_result == 'P':
                    b.profit = 0.0
                else:
                    b.profit = -(b.bet_amount or 0)
                b.settled_at = datetime.now()
                needs_commit = True
                logging.info(f"[Bet auto-settle] bet #{b.id} -> {pick_result} (synced from pick)")
        linked = b.linked_pick
        pick_detail = None
        if linked:
            pick_detail = {
                'id': linked.id,
                'away_team': linked.away_team,
                'home_team': linked.home_team,
                'side': linked.side,
                'line': linked.line,
                'edge_pct': linked.edge_pct,
                'result': linked.result,
                'game_date': linked.game_date,
                'home_score': linked.home_score,
                'away_score': linked.away_score,
                'actual_margin': (linked.home_score - linked.away_score) if linked.home_score is not None and linked.away_score is not None else None,
                'profit_units': linked.profit_units if linked.profit_units is not None else (round(linked.pnl / 100, 2) if linked.pnl is not None else None),
                'published_at': linked.published_at.isoformat() if linked.published_at else None,
            }
        unit_size = user.unit_size or 100
        inferred_units = b.units_wagered if b.units_wagered else (round(b.bet_amount / unit_size, 2) if b.bet_amount and unit_size else 1.0)
        bet_list.append({
            'id': b.id,
            'pick_id': b.pick_id,
            'pick': b.pick,
            'game': b.game,
            'bet_amount': b.bet_amount,
            'odds': b.odds,
            'to_win': b.to_win,
            'result': b.result,
            'profit': b.profit,
            'units_wagered': inferred_units,
            'profit_units': round(b.profit / unit_size, 2) if b.profit and unit_size else 0,
            'pick_result': pick_result,
            'source': b.source or 'sharp_pick',
            'follow_type': b.follow_type or 'exact',
            'line_at_bet': b.line_at_bet,
            'odds_at_publish': b.odds_at_publish,
            'bet_type': b.bet_type or 'spread',
            'parlay_legs': b.parlay_legs,
            'created_at': b.created_at.isoformat() if b.created_at else None,
            'settled_at': b.settled_at.isoformat() if b.settled_at else None,
            'linked_pick': pick_detail,
        })
    if needs_commit:
        try:
            db.session.commit()
        except Exception:
            db.session.rollback()
    return jsonify({'bets': bet_list, 'tracked_pick_ids': list(tracked_pick_ids)})

@app.route('/api/bets/trackable', methods=['GET'])
def get_trackable_picks():
    """Get season picks the user can track, with pagination and search"""
    user = get_current_user_obj()
    if not user:
        return jsonify({'error': 'Login required'}), 401
    already_tracked = db.session.query(TrackedBet.pick_id).filter(
        TrackedBet.user_id == user.id,
        TrackedBet.pick_id.isnot(None)
    ).all()
    tracked_ids = {t[0] for t in already_tracked}

    sport = request.args.get('sport', 'nba')
    page = max(1, int(request.args.get('page', 1)))
    per_page = min(100, max(10, int(request.args.get('per_page', 50))))
    search = (request.args.get('q') or '').strip().lower()

    season_starts = {'nba': '2025-10-01', 'mlb': '2026-03-20', 'wnba': '2026-05-08'}
    season_start = season_starts.get(sport, '2025-10-01')

    q = Pick.query.filter(
        Pick.sport == sport,
        Pick.published_at >= season_start,
    )
    if search:
        q = q.filter(db.or_(
            func.lower(Pick.home_team).contains(search),
            func.lower(Pick.away_team).contains(search),
            func.lower(Pick.side).contains(search),
        ))
    total = q.count()
    picks_page = q.order_by(Pick.published_at.desc()).offset((page - 1) * per_page).limit(per_page).all()

    trackable = []
    for p in picks_page:
        trackable.append({
            'id': p.id,
            'away_team': p.away_team,
            'home_team': p.home_team,
            'game_date': p.game_date,
            'side': p.side,
            'line': p.line,
            'edge_pct': p.edge_pct,
            'market_odds': p.market_odds,
            'result': 'W' if p.result == 'win' else ('L' if p.result == 'loss' else p.result),
            'published_at': p.published_at.isoformat() if p.published_at else None,
            'already_tracked': p.id in tracked_ids,
        })
    return jsonify({
        'picks': trackable,
        'total': total,
        'page': page,
        'per_page': per_page,
        'has_more': page * per_page < total,
    })

@app.route('/api/bets', methods=['POST'])
def track_bet():
    """Track a bet linked to a pick"""
    user = get_current_user_obj()
    if not user:
        return jsonify({'error': 'Login required'}), 401
    data = request.get_json() or {}
    pick_id = data.get('pick_id')

    if pick_id:
        existing = TrackedBet.query.filter_by(
            user_id=user.id,
            pick_id=pick_id
        ).first()
        if existing:
            return jsonify({'success': False, 'error': 'Already tracking this pick'}), 400

        sp_pick = Pick.query.get(pick_id)
        if not sp_pick:
            return jsonify({'success': False, 'error': 'Pick not found'}), 404

        pick_label = sp_pick.side
        game_label = f"{sp_pick.away_team} @ {sp_pick.home_team}"
    else:
        pick_label = data.get('pick', '')
        game_label = data.get('game', '')
        if not pick_label or not game_label:
            return jsonify({'success': False, 'error': 'Pick and game required'}), 400

    units_wagered = data.get('units_wagered')
    unit_size = user.unit_size or 100
    if units_wagered is not None:
        units_wagered = max(0.1, float(units_wagered))
        bet_amount = round(units_wagered * unit_size)
    else:
        bet_amount = data.get('bet_amount', unit_size)
        units_wagered = round(bet_amount / unit_size, 2) if unit_size else 1.0

    odds = data.get('odds', -110)

    if pick_id and sp_pick and sp_pick.market_odds is not None and odds == -110:
        odds = int(sp_pick.market_odds)

    if odds < 0:
        to_win = bet_amount * (100 / abs(odds))
    else:
        to_win = bet_amount * (odds / 100)

    source = 'sharp_pick' if pick_id else 'manual'
    follow_type = data.get('follow_type', 'exact')
    line_at_bet = data.get('line_at_bet')
    bet_type = data.get('bet_type', 'spread')
    parlay_legs = data.get('parlay_legs')
    odds_at_publish_val = None

    if pick_id and sp_pick:
        odds_at_publish_val = sp_pick.market_odds
        if line_at_bet is None:
            line_at_bet = sp_pick.line

    auto_result = None
    auto_profit = 0
    if pick_id and sp_pick and sp_pick.result in ('win', 'loss'):
        if sp_pick.result == 'win':
            auto_result = 'W'
            auto_profit = round(to_win, 2)
        elif sp_pick.result == 'loss':
            auto_result = 'L'
            auto_profit = -bet_amount

    bet = TrackedBet(
        user_id=user.id,
        pick_id=pick_id,
        pick=pick_label,
        game=game_label,
        bet_amount=bet_amount,
        odds=odds,
        to_win=round(to_win, 2),
        result=auto_result,
        profit=auto_profit,
        source=source,
        follow_type=follow_type,
        line_at_bet=line_at_bet,
        odds_at_publish=odds_at_publish_val,
        bet_type=bet_type,
        parlay_legs=parlay_legs,
        units_wagered=units_wagered,
    )
    db.session.add(bet)
    db.session.commit()

    return jsonify({
        'success': True,
        'bet': {
            'id': bet.id,
            'pick_id': bet.pick_id,
            'pick': bet.pick,
            'game': bet.game,
            'bet_amount': bet.bet_amount,
            'odds': bet.odds,
            'to_win': bet.to_win,
            'result': bet.result,
            'units_wagered': bet.units_wagered,
            'created_at': bet.created_at.isoformat()
        }
    })

@app.route('/api/bets/<int:bet_id>/result', methods=['POST'])
def update_bet_result(bet_id):
    """Update bet result"""
    user = get_current_user_obj()
    if not user:
        return jsonify({'error': 'Login required'}), 401
    data = request.get_json() or {}
    bet = TrackedBet.query.filter_by(id=bet_id, user_id=user.id).first()
    if not bet:
        return jsonify({'error': 'Bet not found'}), 404

    new_result = data.get('result')
    if new_result is not None and new_result not in ('W', 'L', 'P'):
        return jsonify({'error': 'Invalid result. Use W, L, or P.'}), 400
    profit_val = data.get('profit', 0)
    try:
        profit_val = float(profit_val) if profit_val is not None else 0
    except (TypeError, ValueError):
        profit_val = 0

    was_pending = bet.result is None
    bet.result = new_result
    bet.profit = profit_val
    if new_result and was_pending:
        bet.settled_at = datetime.now()
    elif new_result is None:
        bet.settled_at = None
    db.session.commit()

    return jsonify({'success': True})

@app.route('/api/bets/<int:bet_id>', methods=['PUT'])
def edit_bet(bet_id):
    """Edit a tracked bet's details"""
    user = get_current_user_obj()
    if not user:
        return jsonify({'error': 'Login required'}), 401
    bet = TrackedBet.query.filter_by(id=bet_id, user_id=user.id).first()
    if not bet:
        return jsonify({'error': 'Bet not found'}), 404

    data = request.get_json() or {}

    unit_size = user.unit_size or 100
    if 'units_wagered' in data:
        bet.units_wagered = max(0.1, float(data['units_wagered']))
        bet.bet_amount = round(bet.units_wagered * unit_size)
    elif 'bet_amount' in data:
        bet.bet_amount = max(1, int(data['bet_amount']))
        bet.units_wagered = round(bet.bet_amount / unit_size, 2) if unit_size else 1.0
    if 'odds' in data:
        bet.odds = int(data['odds'])
    if 'pick' in data:
        bet.pick = data['pick']
    if 'game' in data:
        bet.game = data['game']
    if 'line_at_bet' in data:
        bet.line_at_bet = float(data['line_at_bet']) if data['line_at_bet'] is not None else None
    was_pending = bet.result is None
    if 'result' in data:
        val = data['result']
        if val and val not in ('W', 'L', 'P'):
            return jsonify({'error': 'Invalid result. Use W, L, or P.'}), 400
        bet.result = val if val else None

    odds_val = bet.odds or -110
    amt = bet.bet_amount or 100
    if odds_val < 0:
        bet.to_win = round(amt * (100 / abs(odds_val)), 2)
    else:
        bet.to_win = round(amt * (odds_val / 100), 2)

    if bet.result == 'W':
        bet.profit = bet.to_win
    elif bet.result == 'L':
        bet.profit = -amt
    elif bet.result == 'P':
        bet.profit = 0
    else:
        bet.profit = 0

    if bet.result and was_pending:
        bet.settled_at = datetime.now()
    elif bet.result is None:
        bet.settled_at = None

    db.session.commit()

    return jsonify({
        'success': True,
        'bet': {
            'id': bet.id, 'pick': bet.pick, 'game': bet.game,
            'bet_amount': bet.bet_amount, 'odds': bet.odds,
            'to_win': bet.to_win, 'result': bet.result,
            'profit': bet.profit, 'units_wagered': bet.units_wagered,
            'line_at_bet': bet.line_at_bet,
        }
    })


@app.route('/api/bets/<int:bet_id>/settle', methods=['POST'])
def settle_own_bet(bet_id):
    """Manually settle an own-bet tracked row.

    Own bets have no game-data path so users grade them themselves.
    Sharp-pick bets are auto-settled and rejected here.
    """
    user = get_current_user_obj()
    if not user:
        return jsonify({'error': 'Login required'}), 401

    bet = TrackedBet.query.filter_by(id=bet_id, user_id=user.id).first()
    if not bet:
        return jsonify({'error': 'Bet not found'}), 404

    is_own_bet = bet.pick_id is None or (bet.source or '') == 'manual'
    if not is_own_bet:
        return jsonify({'error': 'Only own bets can be manually settled'}), 400
    if bet.result is not None:
        return jsonify({'error': 'Bet is already settled'}), 400

    data = request.get_json() or {}
    outcome = (data.get('outcome') or '').lower()
    if outcome not in ('win', 'loss', 'push', 'void'):
        return jsonify({'error': 'Invalid outcome. Use win, loss, push, or void.'}), 400

    stake = bet.bet_amount or 0
    odds = bet.odds if bet.odds is not None else -110

    if outcome == 'win':
        if odds > 0:
            profit = round(stake * (odds / 100), 2)
        else:
            profit = round(stake * (100 / abs(odds)), 2)
        stored_result = 'W'
    elif outcome == 'loss':
        profit = float(-stake)
        stored_result = 'L'
    elif outcome == 'push':
        profit = 0.0
        stored_result = 'P'
    else:
        profit = 0.0
        stored_result = 'void'

    bet.result = stored_result
    bet.profit = profit
    bet.settled_at = datetime.now()
    db.session.commit()

    return jsonify({
        'success': True,
        'bet': {
            'id': bet.id,
            'result': bet.result,
            'profit': bet.profit,
            'settled_at': bet.settled_at.isoformat() if bet.settled_at else None,
        }
    })


@app.route('/api/bets/<int:bet_id>', methods=['DELETE'])
def delete_bet(bet_id):
    """Delete/untrack a bet"""
    user = get_current_user_obj()
    if not user:
        return jsonify({'error': 'Login required'}), 401
    bet = TrackedBet.query.filter_by(id=bet_id, user_id=user.id).first()
    if not bet:
        return jsonify({'error': 'Bet not found'}), 404

    db.session.delete(bet)
    db.session.commit()

    return jsonify({'success': True})

NOTIFICATION_PREF_DEFAULTS = {
    'pick_alert': True,
    'no_action': True,
    'outcome': True,
    'weekly_summary': True,
    'line_movement': True,
    'journal_updates': True,
    'quiet_hours_enabled': False,
    'quiet_hours_start': '23:00',
    'quiet_hours_end': '08:00',
    'email_signals': True,
    'email_results': True,
    'email_weekly': True,
    'email_marketing': True,
}


@app.route('/api/user/notifications', methods=['GET'])
def get_notification_prefs():
    user = get_current_user_obj()
    if not user:
        return jsonify({'error': 'Not authenticated'}), 401
    merged = {**NOTIFICATION_PREF_DEFAULTS, **(user.notification_prefs or {})}
    return jsonify({'prefs': merged})

@app.route('/api/user/notifications', methods=['POST'])
def update_notification_prefs():
    user = get_current_user_obj()
    if not user:
        return jsonify({'error': 'Not authenticated'}), 401
    data = request.get_json() or {}
    user.notification_prefs = data.get('prefs', user.notification_prefs)
    db.session.commit()
    return jsonify({'success': True, 'prefs': user.notification_prefs})


@app.route('/unsubscribe')
def unsubscribe_page():
    from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadSignature
    token = request.args.get('token', '')
    category = request.args.get('cat', 'all')

    if not token:
        return _unsub_html('Invalid unsubscribe link.', success=False)

    s = URLSafeTimedSerializer(app.config['SECRET_KEY'])
    try:
        email = s.loads(token, salt='email-unsubscribe', max_age=60 * 60 * 24 * 365)
    except (SignatureExpired, BadSignature):
        return _unsub_html('This unsubscribe link has expired or is invalid.', success=False)

    user = User.query.filter_by(email=email).first()
    if not user:
        return _unsub_html('Account not found.', success=False)

    prefs = dict(user.notification_prefs or {})

    if category == 'all':
        prefs['email_signals'] = False
        prefs['email_results'] = False
        prefs['email_weekly'] = False
        prefs['email_marketing'] = False
    elif category in ('email_signals', 'email_results', 'email_weekly', 'email_marketing'):
        prefs[category] = False
    else:
        prefs['email_signals'] = False
        prefs['email_results'] = False
        prefs['email_weekly'] = False
        prefs['email_marketing'] = False

    user.notification_prefs = prefs
    db.session.commit()

    label = {
        'all': 'all emails',
        'email_signals': 'signal emails',
        'email_results': 'result emails',
        'email_weekly': 'weekly recap emails',
        'email_marketing': 'marketing emails',
    }.get(category, 'all emails')

    return _unsub_html(f'You have been unsubscribed from {label}.', success=True, email=email)


def _unsub_html(message, success=True, email=None):
    color = '#5A9E72' if success else '#CC3333'
    icon = '&#x2714;' if success else '&#x2718;'
    renable = '<p style="font-size:13px;color:#666;">You can re-enable emails anytime in your account settings.</p>' if success else ''
    html = f'''<!DOCTYPE html>
<html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>SharpPicks &mdash; Unsubscribe</title></head>
<body style="margin:0;padding:0;background:#0D0D0D;font-family:Arial,Helvetica,sans-serif;">
<div style="max-width:480px;margin:80px auto;text-align:center;padding:40px 24px;">
  <p style="margin:0 0 32px;">
    <img src="https://app.sharppicks.ai/wordmark-white.png" alt="SharpPicks" style="height:22px;width:auto;" />
  </p>
  <div style="font-size:36px;color:{color};margin:0 0 16px;">{icon}</div>
  <p style="font-size:16px;color:#FFFFFF;margin:0 0 12px;">{message}</p>
  {renable}
  <a href="https://app.sharppicks.ai" style="display:inline-block;margin-top:24px;padding:12px 28px;background:#5A9E72;color:#fff;text-decoration:none;border-radius:6px;font-size:14px;font-weight:bold;letter-spacing:0.05em;text-transform:uppercase;">Open SharpPicks</a>
</div>
</body></html>'''
    return html, 200, {'Content-Type': 'text/html'}


@app.route('/api/user/fcm-token', methods=['POST'])
def save_fcm_token():
    user = get_current_user_obj()
    if not user:
        logging.warning("[FCM] save_fcm_token: not authenticated")
        return jsonify({'error': 'Not authenticated'}), 401
    data = request.get_json() or {}
    token = data.get('token', '').strip()
    platform = data.get('platform', 'web')
    if not token:
        return jsonify({'error': 'Token required'}), 400
    from models import FCMToken
    existing = FCMToken.query.filter_by(fcm_token=token).first()
    if existing:
        existing.user_id = user.id
        existing.last_seen_at = datetime.now()
        existing.enabled = True
    else:
        new_token = FCMToken(user_id=user.id, fcm_token=token, platform=platform)
        db.session.add(new_token)

    # Disable other tokens on the same platform for this user to prevent
    # duplicate notifications (e.g. Safari + PWA home-screen on iOS both
    # register separate tokens for the same physical device).
    FCMToken.query.filter(
        FCMToken.user_id == user.id,
        FCMToken.platform == platform,
        FCMToken.fcm_token != token,
        FCMToken.enabled == True,
    ).update({'enabled': False})

    db.session.commit()
    logging.info("[FCM] token registered: user=%s platform=%s (disabled %d old %s tokens)",
                 user.email, platform,
                 FCMToken.query.filter_by(user_id=user.id, platform=platform, enabled=False).count(),
                 platform)
    return jsonify({'success': True})


@app.route('/api/user/fcm-token', methods=['DELETE'])
def delete_fcm_token():
    user = get_current_user_obj()
    if not user:
        return jsonify({'error': 'Not authenticated'}), 401
    data = request.get_json() or {}
    token = data.get('token', '').strip()
    if not token:
        return jsonify({'error': 'Token required'}), 400
    from models import FCMToken
    FCMToken.query.filter_by(user_id=user.id, fcm_token=token).delete()
    db.session.commit()
    return jsonify({'success': True})


@app.route('/api/account/delete', methods=['DELETE'])
def delete_account():
    """Delete user account and all associated data. Required by App Store / Play Store."""
    user = get_current_user_obj()
    if not user:
        return jsonify({'error': 'Not authenticated'}), 401

    try:
        # Cancel Stripe subscription if active
        if user.stripe_customer_id:
            try:
                from stripe_client import get_stripe_client
                stripe = get_stripe_client()
                subs = stripe.Subscription.list(customer=user.stripe_customer_id, status='active', limit=10)
                for sub in subs.data:
                    stripe.Subscription.delete(sub.id)
            except Exception:
                pass  # Don't block deletion if Stripe fails

        user_id = user.id

        # Delete associated data
        from models import FCMToken, WatchedGame
        TrackedBet.query.filter_by(user_id=user_id).delete()
        FCMToken.query.filter_by(user_id=user_id).delete()
        WatchedGame.query.filter_by(user_id=user_id).delete()

        # Delete the user
        db.session.delete(user)
        db.session.commit()

        # Clear session
        from flask import session as flask_session
        flask_session.clear()

        return jsonify({'success': True, 'message': 'Account deleted'}), 200
    except Exception:
        db.session.rollback()
        return jsonify({'error': 'Failed to delete account'}), 500


def _normalize_pem_private_key(pk):
    """
    Normalize PEM private key for cryptography library.
    Handles: escaped \\n, single-line base64, missing trailing newline.
    """
    if not pk or not isinstance(pk, str):
        return pk
    # Replace escaped newlines (env vars often have literal \n as backslash-n)
    pk = pk.replace('\\n', '\n').replace('\\r', '\r')
    pk = pk.strip()
    if not pk:
        return pk
    # Extract base64 body between markers (support BEGIN PRIVATE KEY or BEGIN RSA PRIVATE KEY)
    begin = '-----BEGIN PRIVATE KEY-----'
    end = '-----END PRIVATE KEY-----'
    if '-----BEGIN RSA PRIVATE KEY-----' in pk:
        begin = '-----BEGIN RSA PRIVATE KEY-----'
        end = '-----END RSA PRIVATE KEY-----'
    if begin not in pk or end not in pk:
        return pk
    start_idx = pk.find(begin) + len(begin)
    end_idx = pk.find(end)
    if start_idx <= 0 or end_idx <= start_idx:
        return pk
    import re
    b64_body = pk[start_idx:end_idx].replace('\n', '').replace('\r', '').replace(' ', '')
    b64_body = re.sub(r'[^A-Za-z0-9+/=]', '', b64_body)
    if not b64_body or len(b64_body) < 100:
        return pk
    # Re-wrap base64 at 64 chars (RFC 7468) — single-line causes "expected pattern" error
    wrapped = '\n'.join(b64_body[i:i + 64] for i in range(0, len(b64_body), 64))
    return f"{begin}\n{wrapped}\n{end}\n"


def _get_firebase_service_info():
    """Load Firebase credentials from file or env. Returns dict or None."""
    import json
    sa_file = os.path.join(os.path.dirname(__file__), 'firebase-service-account.json')
    if os.path.exists(sa_file):
        try:
            info = json.load(open(sa_file))
            pk = info.get('private_key', '')
            if pk:
                info = dict(info)
                info['private_key'] = _normalize_pem_private_key(pk)
            return info
        except Exception as e:
            logging.error(f"Failed to load firebase-service-account.json: {e}")

    # Option 1: Separate env vars (most reliable for Railway/Heroku)
    pk_env = os.environ.get('FIREBASE_PRIVATE_KEY', '').strip()
    client_email = os.environ.get('FIREBASE_CLIENT_EMAIL', '').strip()
    project_id = os.environ.get('FIREBASE_PROJECT_ID', 'sharp-picks').strip() or 'sharp-picks'
    if pk_env and client_email:
        pk_norm = _normalize_pem_private_key(pk_env.replace('\\n', '\n'))
        if pk_norm and '-----BEGIN' in pk_norm:
            return {
                "type": "service_account",
                "project_id": project_id,
                "private_key_id": os.environ.get('FIREBASE_PRIVATE_KEY_ID', 'e6289e4f161c78502bdddd57031094b7cf0f123e'),
                "private_key": pk_norm,
                "client_email": client_email,
                "client_id": os.environ.get('FIREBASE_CLIENT_ID', '116349919118145525435'),
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
                "client_x509_cert_url": f"https://www.googleapis.com/robot/v1/metadata/x509/{client_email.replace('@', '%40')}",
                "universe_domain": "googleapis.com"
            }

    # Option 2: Full JSON from env
    raw = (os.environ.get('FIREBASE_SERVICE_ACCOUNT_JSON', '') or os.environ.get('FIREBASE_PRIVATE_KEY', '')).strip()
    if not raw:
        return None
    raw = raw.strip()
    if raw.startswith("'") and raw.endswith("'"):
        raw = raw[1:-1]
    elif raw.startswith('"') and raw.endswith('"'):
        raw = raw[1:-1]

    def _parse_and_normalize(s):
        info = json.loads(s)
        if isinstance(info, dict) and info.get('type') == 'service_account':
            pk = info.get('private_key', '')
            if pk:
                info = dict(info)
                info['private_key'] = _normalize_pem_private_key(pk)
            return info
        return None

    try:
        info = _parse_and_normalize(raw)
        if info:
            return info
        # Double-encode: Railway sometimes stores JSON as a JSON string
        if isinstance(json.loads(raw), str):
            info = _parse_and_normalize(json.loads(raw))
            if info:
                return info
    except json.JSONDecodeError:
        pass

    try:
        import base64
        decoded = base64.b64decode(raw).decode('utf-8')
        info = _parse_and_normalize(decoded)
        if info:
            return info
    except Exception:
        pass

    # Fallback: raw PEM in FIREBASE_PRIVATE_KEY
    if '-----BEGIN' in raw:
        pk_norm = _normalize_pem_private_key(raw.replace('\\n', '\n'))
        if pk_norm and '-----BEGIN' in pk_norm:
            return {
                "type": "service_account",
                "project_id": os.environ.get('FIREBASE_PROJECT_ID', 'sharp-picks').strip() or 'sharp-picks',
                "private_key_id": os.environ.get('FIREBASE_PRIVATE_KEY_ID', 'e6289e4f161c78502bdddd57031094b7cf0f123e'),
                "private_key": pk_norm,
                "client_email": os.environ.get('FIREBASE_CLIENT_EMAIL', 'firebase-adminsdk-fbsvc@sharp-picks.iam.gserviceaccount.com').strip() or 'firebase-adminsdk-fbsvc@sharp-picks.iam.gserviceaccount.com',
                "client_id": "116349919118145525435",
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
                "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/firebase-adminsdk-fbsvc%40sharp-picks.iam.gserviceaccount.com",
                "universe_domain": "googleapis.com"
            }

    return None


_firebase_creds_cache = {'creds': None, 'project_id': None, 'expires_at': 0}

def _get_firebase_credentials_and_project():
    """Get (credentials, project_id) or raise. Caches credentials until they expire."""
    import json
    import tempfile
    import google.auth.transport.requests
    from google.oauth2 import service_account

    now = _time.time()
    if _firebase_creds_cache['creds'] and now < _firebase_creds_cache['expires_at']:
        return _firebase_creds_cache['creds'], _firebase_creds_cache['project_id']

    service_info = _get_firebase_service_info()
    if not service_info:
        raise ValueError("No Firebase credentials. Set FIREBASE_PRIVATE_KEY + FIREBASE_CLIENT_EMAIL, or FIREBASE_SERVICE_ACCOUNT_JSON.")

    project_id = service_info.get('project_id', 'sharp-picks')

    # Strategy 1: Write to temp file — file-based loading is most reliable (avoids env var encoding)
    try:
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(service_info, f, indent=2)
            tmp_path = f.name
        try:
            creds = service_account.Credentials.from_service_account_file(
                tmp_path,
                scopes=['https://www.googleapis.com/auth/firebase.messaging']
            )
            creds.refresh(google.auth.transport.requests.Request())
            _firebase_creds_cache.update({'creds': creds, 'project_id': project_id, 'expires_at': now + 3000})
            return creds, project_id
        finally:
            try:
                os.unlink(tmp_path)
            except Exception:
                pass
    except Exception as e1:
        logging.warning(f"Firebase file-based load failed: {e1}")

    # Strategy 2: Dict-based (can hit PEM format issues with env vars)
    try:
        creds = service_account.Credentials.from_service_account_info(
            service_info,
            scopes=['https://www.googleapis.com/auth/firebase.messaging']
        )
        creds.refresh(google.auth.transport.requests.Request())
        _firebase_creds_cache.update({'creds': creds, 'project_id': project_id, 'expires_at': now + 3000})
        return creds, project_id
    except Exception as e2:
        raise ValueError(
            f"Firebase private key format invalid. Set FIREBASE_PRIVATE_KEY and FIREBASE_CLIENT_EMAIL as separate env vars "
            "(paste PEM with \\n for newlines), or use FIREBASE_SERVICE_ACCOUNT_JSON with full JSON. {e2}"
        ) from e2


def send_push_notification(user_id, title, body, data=None):
    from models import FCMToken

    # QA safety: skip every push when DISABLE_PUSH is set. Staging shares
    # the production Firebase project so a stray send would hit real
    # devices; the env var is the single switch that prevents that.
    if os.environ.get('DISABLE_PUSH', '').strip() in ('1', 'true', 'yes', 'on'):
        logging.info(f"DISABLE_PUSH set — skipping push to user {user_id} ({title!r})")
        return 0

    tokens = FCMToken.query.filter_by(user_id=user_id, enabled=True).all()
    if not tokens:
        return 0

    credentials, project_id = _get_firebase_credentials_and_project()

    url = f'https://fcm.googleapis.com/v1/projects/{project_id}/messages:send'
    headers = {
        'Authorization': f'Bearer {credentials.token}',
        'Content-Type': 'application/json'
    }

    sent = 0
    for t in tokens:
        token = (t.fcm_token or '').strip()
        if not token or len(token) < 20:
            logging.warning(f"Skipping invalid FCM token (too short or empty) for user {user_id}")
            continue
        is_ios = (t.platform or '').lower() == 'ios'
        msg = {
            'token': token,
            'notification': {'title': title or ' ', 'body': body or ' '},
        }
        if is_ios:
            msg['apns'] = {
                'payload': {
                    'aps': {
                        'alert': {'title': title or ' ', 'body': body or ' '},
                        'sound': 'default',
                        'badge': 1,
                    }
                }
            }
        else:
            msg['webpush'] = {
                'notification': {
                    'icon': 'https://app.sharppicks.ai/icon-192x192.png',
                    'badge': 'https://app.sharppicks.ai/favicon-32x32.png',
                }
            }
        payload = {'message': msg}
        if data:
            payload['message']['data'] = {str(k): str(v) for k, v in data.items()}
        try:
            resp = http_requests.post(url, json=payload, headers=headers, timeout=5)
            if resp.status_code == 200:
                sent += 1
            elif resp.status_code in (404, 410):
                t.enabled = False
                db.session.commit()
                logging.info(f"Disabled stale FCM token for user {user_id} (status {resp.status_code})")
            elif resp.status_code == 400 and 'not a valid FCM registration token' in resp.text:
                t.enabled = False
                db.session.commit()
                logging.info(f"Disabled invalid FCM token for user {user_id} (400 INVALID_ARGUMENT)")
            elif resp.status_code == 403:
                t.enabled = False
                db.session.commit()
                logging.info(f"Disabled mismatched FCM token for user {user_id} (403 — wrong project)")
            elif resp.status_code == 401:
                err_text = resp.text[:300]
                logging.warning(f"FCM 401 (APNs/credentials): {err_text}")
            else:
                logging.warning(f"FCM send failed ({resp.status_code}): {resp.text[:200]}")
        except Exception as e:
            logging.error(f"FCM send error: {e}")
    return sent


def send_push_to_all(title, body, data=None, premium_only=False, notification_type=None,
                     free_title=None, free_body=None, free_data=None):
    users = User.query.all()
    if premium_only and not free_title:
        users = [u for u in users if u.is_premium or u.subscription_status in ('active', 'trial')]

    PREF_KEY_MAP = {
        'pick': 'pick_alert',
        'pass': 'no_action',
        'result': 'outcome',
        'revoke': 'pick_alert',
        'pretip': 'pick_alert',
        'weekly_summary': 'weekly_summary',
        'line_movement': 'line_movement',
        'journal': 'journal_updates',
    }

    total = 0
    for u in users:
        is_pro = u.is_premium or u.subscription_status in ('active', 'trial')

        if premium_only and not is_pro and not free_title:
            continue

        if notification_type and hasattr(u, 'notification_prefs') and u.notification_prefs:
            pref_key = PREF_KEY_MAP.get(notification_type)
            if pref_key and not u.notification_prefs.get(pref_key, True):
                continue

            quiet_start = u.notification_prefs.get('quiet_hours_start')
            quiet_end = u.notification_prefs.get('quiet_hours_end')
            if quiet_start and quiet_end:
                try:
                    now_et = datetime.now(pytz.timezone('US/Eastern'))
                    now_t = now_et.hour * 60 + now_et.minute
                    qs = int(quiet_start.split(':')[0]) * 60 + int(quiet_start.split(':')[1])
                    qe = int(quiet_end.split(':')[0]) * 60 + int(quiet_end.split(':')[1])
                    if qs > qe:
                        if now_t >= qs or now_t < qe:
                            continue
                    elif qs <= now_t < qe:
                        continue
                except Exception:
                    pass

        if is_pro:
            total += send_push_notification(u.id, title, body, data)
        elif free_title:
            total += send_push_notification(u.id, free_title, free_body or '', free_data or data)
    return total


def send_admin_alert(title, body, data=None):
    admins = User.query.filter_by(is_superuser=True).all()
    total = 0
    alert_data = data or {}
    alert_data['type'] = 'admin_alert'
    for admin in admins:
        total += send_push_notification(admin.id, f"[Admin] {title}", body, alert_data)
    if total > 0:
        logging.info(f"Admin alert sent to {total} device(s): {title}")
    else:
        logging.warning(f"Admin alert could not be delivered (no admin tokens): {title}")
    return total


@app.route('/api/game-board')
def game_board():
    """Get today's game board with enhanced markets (1H, alt spreads, props)"""
    user = get_current_user_obj()
    if not user:
        return jsonify({'error': 'Login required'}), 401
    if not user.is_pro:
        return jsonify({'error': 'Pro subscription required', 'upgrade': True}), 403

    conn = get_sqlite_conn()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    today_et = datetime.now(pytz.timezone('US/Eastern')).strftime('%Y-%m-%d')
    cursor.execute('''
        SELECT id, home_team, away_team, game_time, commence_time,
               spread_home, spread_away, total, home_ml, away_ml,
               home_spread_odds, away_spread_odds, home_spread_book, away_spread_book,
               spread_h1_home, spread_h1_away, spread_h1_home_odds, spread_h1_away_odds,
               total_h1,
               alt_spread_minus_1, alt_spread_minus_3, alt_spread_minus_5, alt_spread_minus_7,
               alt_spread_plus_1, alt_spread_plus_3, alt_spread_plus_5, alt_spread_plus_7,
               home_record, away_record, home_injuries, away_injuries,
               line_movement
        FROM games WHERE game_date = ?
        ORDER BY game_time
    ''', (today_et,))

    games = []
    for row in cursor.fetchall():
        game = dict(row)
        game_id = game['id']

        cursor.execute('''
            SELECT player_name, team, market, line, over_odds, under_odds, book
            FROM nba_player_props
            WHERE game_id = ? OR game_date = ?
            ORDER BY market, player_name
        ''', (game_id, today_et))

        props = []
        for p in cursor.fetchall():
            props.append(dict(p))

        alt_spreads = {}
        for pt in [-7, -5, -3, -1, 1, 3, 5, 7]:
            col = f"alt_spread_{'minus' if pt < 0 else 'plus'}_{abs(pt)}"
            val = game.get(col)
            if val is not None:
                alt_spreads[str(pt)] = val
            game.pop(col, None)

        game['alt_spreads'] = alt_spreads
        game['player_props'] = props
        games.append(game)

    conn.close()
    return jsonify({'date': today_et, 'games': games, 'count': len(games)})


@app.route('/api/model/calibration')
@app.route('/api/validation/detailed')
def detailed_validation():
    """Check model calibration by confidence buckets - only forward predictions"""
    user = get_current_user_obj()
    if not user:
        return jsonify({'error': 'Login required'}), 401
    if not user.is_pro:
        return jsonify({'error': 'Pro subscription required', 'upgrade': True}), 403
    conn = get_db()
    cursor = conn.cursor()
    
    buckets = {}
    for conf_min in [50, 55, 60, 65, 70, 80]:
        conf_max = conf_min + 5 if conf_min < 80 else 100
        
        cursor.execute('''
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN is_correct = 1 THEN 1 ELSE 0 END) as wins
            FROM prediction_log
            WHERE confidence >= ? AND confidence < ?
            AND actual_result IS NOT NULL
            AND actual_result != 'PUSH'
            AND logged_at < game_date
        ''', (conf_min / 100.0, conf_max / 100.0))
        
        result = cursor.fetchone()
        total = result['total'] if result['total'] else 0
        wins = result['wins'] if result['wins'] else 0
        expected_rate = (conf_min + conf_max) / 2
        actual_rate = (wins / total * 100) if total > 0 else 0
        
        buckets[f'{conf_min}-{conf_max}%'] = {
            'total': total,
            'wins': wins,
            'actual_rate': round(actual_rate, 1),
            'expected_rate': expected_rate,
            'error': round(actual_rate - expected_rate, 1),
            'calibrated': abs(actual_rate - expected_rate) < 5 if total > 0 else None
        }
    
    mean_error = 0
    valid_buckets = [b for b in buckets.values() if b['total'] > 0]
    if valid_buckets:
        mean_error = sum(abs(b['error']) for b in valid_buckets) / len(valid_buckets)
    
    conn.close()
    
    return jsonify({
        'buckets': buckets,
        'mean_absolute_error': round(mean_error, 1),
        'calibration_status': 'excellent' if mean_error < 3 else 'good' if mean_error < 5 else 'moderate' if mean_error < 10 else 'poor',
        'total_predictions': sum(b['total'] for b in buckets.values())
    })


def parse_record(record_str):
    """Parse record string like '25-15' into win percentage"""
    if not record_str or record_str == 'N/A':
        return 0.5
    try:
        parts = record_str.split('-')
        wins = int(parts[0])
        losses = int(parts[1])
        total = wins + losses
        return wins / total if total > 0 else 0.5
    except:
        return 0.5

def parse_form(form_str):
    """Parse last 5 form string like 'WWLWL' into score (0-5)"""
    if not form_str:
        return 2.5
    try:
        return form_str.count('W')
    except:
        return 2.5

def calculate_all_features(game_dict):
    """Calculate all 36 features the model expects from database fields"""
    spread_home = game_dict.get('spread_home') or 0
    spread_open = game_dict.get('spread_home_open') or spread_home
    line_movement = game_dict.get('line_movement') or (spread_home - spread_open if spread_open else 0)
    total = game_dict.get('total') or 220
    total_open = game_dict.get('total_open') or total
    total_movement = total - total_open if total_open else 0
    home_ml = game_dict.get('home_ml') or -110
    away_ml = game_dict.get('away_ml') or -110
    ml_diff = home_ml - away_ml
    
    home_win_pct = parse_record(game_dict.get('home_record'))
    away_win_pct = parse_record(game_dict.get('away_record'))
    win_pct_diff = home_win_pct - away_win_pct
    
    home_home_pct = parse_record(game_dict.get('home_home_record'))
    away_away_pct = parse_record(game_dict.get('away_away_record'))
    split_advantage = home_home_pct - away_away_pct
    
    home_form = parse_form(game_dict.get('home_last5'))
    away_form = parse_form(game_dict.get('away_last5'))
    form_diff = home_form - away_form
    
    home_rest = game_dict.get('home_rest_days') if game_dict.get('home_rest_days') is not None else 1
    away_rest = game_dict.get('away_rest_days') if game_dict.get('away_rest_days') is not None else 1
    rest_advantage = home_rest - away_rest
    
    spread_abs = abs(spread_home)
    is_favorite = 1 if spread_home < 0 else 0
    
    home_pace = 100 + (home_win_pct - 0.5) * 4
    away_pace = 100 + (away_win_pct - 0.5) * 4
    pace_diff = home_pace - away_pace
    combined_pace = (home_pace + away_pace) / 2
    
    home_off_rtg = 110 + (home_win_pct - 0.5) * 10
    home_def_rtg = 110 - (home_win_pct - 0.5) * 10
    away_off_rtg = 110 + (away_win_pct - 0.5) * 10
    away_def_rtg = 110 - (away_win_pct - 0.5) * 10
    home_net_rtg = home_off_rtg - home_def_rtg
    away_net_rtg = away_off_rtg - away_def_rtg
    net_rtg_diff = home_net_rtg - away_net_rtg
    off_matchup = home_off_rtg - away_def_rtg
    def_matchup = away_off_rtg - home_def_rtg
    
    return {
        'spread_home': spread_home,
        'spread_open': spread_open,
        'line_movement': line_movement,
        'total': total,
        'total_open': total_open,
        'total_movement': total_movement,
        'home_ml': home_ml,
        'away_ml': away_ml,
        'ml_diff': ml_diff,
        'home_win_pct': home_win_pct,
        'away_win_pct': away_win_pct,
        'win_pct_diff': win_pct_diff,
        'home_home_pct': home_home_pct,
        'away_away_pct': away_away_pct,
        'split_advantage': split_advantage,
        'home_form': home_form,
        'away_form': away_form,
        'form_diff': form_diff,
        'home_rest': home_rest,
        'away_rest': away_rest,
        'rest_advantage': rest_advantage,
        'spread_abs': spread_abs,
        'is_favorite': is_favorite,
        'home_pace': home_pace,
        'away_pace': away_pace,
        'pace_diff': pace_diff,
        'combined_pace': combined_pace,
        'home_off_rtg': home_off_rtg,
        'home_def_rtg': home_def_rtg,
        'away_off_rtg': away_off_rtg,
        'away_def_rtg': away_def_rtg,
        'home_net_rtg': home_net_rtg,
        'away_net_rtg': away_net_rtg,
        'net_rtg_diff': net_rtg_diff,
        'off_matchup': off_matchup,
        'def_matchup': def_matchup
    }

@app.route('/api/predictions')
def get_predictions():
    """Get today's model predictions for upcoming games - with full 36-feature calculation"""
    user = get_current_user_obj()
    if not user:
        return jsonify({'error': 'Login required'}), 401
    if not user.is_pro:
        return jsonify({'error': 'Pro subscription required', 'upgrade': True}), 403
    import pickle
    import json
    import os
    from datetime import datetime
    
    try:
        from nba_injuries import get_injury_differential, TEAM_ABBREV_MAP
        injuries_available = True
    except:
        injuries_available = False
    
    try:
        from nba_schedule import get_simple_schedule_factors, get_team_abbrev
        schedule_available = True
    except:
        schedule_available = False
    
    conn = get_db()
    cursor = conn.cursor()
    
    today = _get_et_today()
    cursor.execute('''
        SELECT id, home_team, away_team, game_date, game_time,
               spread_home, spread_away, spread_home_open, 
               total, total_open, home_ml, away_ml,
               home_record, away_record, home_home_record, away_away_record,
               home_last5, away_last5, home_rest_days, away_rest_days,
               line_movement
        FROM games 
        WHERE DATE(game_date) BETWEEN DATE(?) AND DATE(?, '+1 day')
        AND spread_result IS NULL
        AND game_time IS NOT NULL
        ORDER BY game_time
        LIMIT 20
    ''', (today, today))
    
    games = cursor.fetchall()
    predictions = []
    
    try:
        with open('sharp_picks_model.pkl', 'rb') as f:
            model_data = pickle.load(f)
            models = model_data.get('models', {})
            model = models.get('gradient_boosting') or models.get('random_forest') or models.get('xgboost')
            if not model:
                model = model_data.get('model')
            feature_names = model_data.get('feature_names', [])
    except Exception as e:
        model = None
        feature_names = []
    
    for game in games:
        game_dict = dict(game)
        
        if model and feature_names and hasattr(model, 'predict_proba'):
            try:
                import pandas as pd
                
                feature_dict = calculate_all_features(game_dict)
                
                X = pd.DataFrame([feature_dict])
                X = X.reindex(columns=feature_names, fill_value=0)
                
                proba = model.predict_proba(X)[0]
                home_cover_prob = proba[1] if len(proba) > 1 else 0.5
                
                spread = game_dict.get('spread_home') or 0
                line_movement = feature_dict.get('line_movement', 0)
                
                if home_cover_prob >= 0.5:
                    pick = game_dict['home_team']
                    confidence = home_cover_prob
                    pick_spread = spread
                else:
                    pick = game_dict['away_team']
                    confidence = 1 - home_cover_prob
                    pick_spread = -spread if spread else 0
                
                injury_info = None
                if injuries_available:
                    try:
                        home_abbr = None
                        away_abbr = None
                        for name, abbr in TEAM_ABBREV_MAP.items():
                            if game_dict['home_team'] in name or name in game_dict['home_team']:
                                home_abbr = abbr
                            if game_dict['away_team'] in name or name in game_dict['away_team']:
                                away_abbr = abbr
                        
                        if home_abbr and away_abbr:
                            injury_diff = get_injury_differential(home_abbr, away_abbr)
                            injury_info = {
                                'home_impact': round(injury_diff['home_impact'], 1),
                                'away_impact': round(injury_diff['away_impact'], 1),
                                'advantage': injury_diff['advantage'],
                                'home_injuries': injury_diff['home_injuries'][:3],
                                'away_injuries': injury_diff['away_injuries'][:3]
                            }
                    except:
                        pass
                
                schedule_info = None
                if schedule_available:
                    try:
                        schedule_info = get_simple_schedule_factors(
                            game_dict['home_team'], 
                            game_dict['away_team']
                        )
                    except:
                        pass
                
                is_coinflip = spread is not None and -1.5 <= spread <= 1.5
                
                opening_spread = game_dict.get('spread_home_open') or spread
                
                sharp_money = False
                if line_movement != 0 and spread is not None and opening_spread is not None:
                    if home_cover_prob >= 0.5:
                        sharp_money = (spread < opening_spread)
                    else:
                        sharp_money = (spread > opening_spread)
                
                predictions.append({
                    'home_team': game_dict['home_team'],
                    'away_team': game_dict['away_team'],
                    'game_date': game_dict['game_date'],
                    'game_time': game_dict.get('game_time'),
                    'prediction': pick,
                    'spread': spread,
                    'pick_spread': pick_spread,
                    'opening_spread': opening_spread,
                    'confidence': round(confidence, 3),
                    'edge': round((confidence - 0.52) * 10, 1) if confidence > 0.52 else 0,
                    'line_movement': round(line_movement, 1),
                    'sharp_money': sharp_money,
                    'home_record': game_dict.get('home_record'),
                    'away_record': game_dict.get('away_record'),
                    'home_form': game_dict.get('home_last5'),
                    'away_form': game_dict.get('away_last5'),
                    'injuries': injury_info,
                    'schedule': schedule_info,
                    'is_coinflip': is_coinflip
                })
            except Exception as e:
                pass
    
    conn.close()
    return jsonify({
        'predictions': sorted(predictions, key=lambda x: x['confidence'], reverse=True),
        'count': len(predictions),
        'source': 'database'
    })


@app.route('/api/performance')
def get_performance():
    """Get live performance tracking stats — ONLY published picks, not all model runs"""
    from sqlalchemy import text as sql_text

    picks_stats = {'total': 0, 'wins': 0, 'losses': 0, 'pending': 0, 'pushes': 0}
    try:
        result = db.session.execute(sql_text("""
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN result = 'win' THEN 1 ELSE 0 END) as wins,
                SUM(CASE WHEN result = 'loss' THEN 1 ELSE 0 END) as losses,
                SUM(CASE WHEN result = 'push' THEN 1 ELSE 0 END) as pushes,
                SUM(CASE WHEN result IS NULL OR result = 'pending' THEN 1 ELSE 0 END) as pending
            FROM picks
        """))
        row = result.fetchone()
        if row:
            picks_stats = {
                'total': row[0] or 0,
                'wins': row[1] or 0,
                'losses': row[2] or 0,
                'pushes': row[3] or 0,
                'pending': row[4] or 0,
            }
    except Exception as e:
        logging.error(f"Performance picks query error: {e}")

    decided = picks_stats['wins'] + picks_stats['losses']
    win_rate = picks_stats['wins'] / decided if decided > 0 else None

    closing_line_stats = {'beat_rate': 0, 'total_tracked': 0}
    try:
        from performance_tracker import get_closing_line_stats
        closing_line_stats = get_closing_line_stats()
    except:
        pass

    return jsonify({
        'total_predictions': picks_stats['total'],
        'correct': picks_stats['wins'],
        'incorrect': picks_stats['losses'],
        'pushes': picks_stats['pushes'],
        'pending': picks_stats['pending'],
        'win_rate': round(win_rate, 3) if win_rate else None,
        'closing_line': closing_line_stats,
        'source': 'published_picks',
    })


@app.route('/api/admin/generate-market-note', methods=['GET', 'POST'])
@verify_cron
def admin_generate_market_note():
    """Generate (or regenerate) the daily market note for a given sport and date."""
    sport = request.args.get('sport', 'mlb')
    date_str = request.args.get('date', _get_et_today())
    from public_api import build_market_report_dict
    report = build_market_report_dict(date_str, sport)
    if not report.get('available'):
        return jsonify({'error': 'No model run data available', 'sport': sport, 'date': date_str}), 404
    note = _upsert_market_note_insight(report, sport=sport)
    if note:
        return jsonify({'success': True, 'slug': note.slug, 'title': note.title, 'sport': sport, 'date': date_str})
    return jsonify({'error': 'Failed to generate market note'}), 500


@app.route('/api/admin/grant-premium', methods=['GET', 'POST'])
@verify_cron
def admin_grant_premium():
    """Grant lifetime premium to a user by email or name search."""
    email = request.args.get('email', '').strip().lower()
    if not email:
        return jsonify({'error': 'Missing email parameter'}), 400
    user = User.query.filter(db.func.lower(User.email) == email).first()
    if not user:
        user = User.query.filter(
            db.or_(
                db.func.lower(User.email).contains(email),
                db.func.lower(User.first_name).contains(email),
                db.func.lower(User.display_name).contains(email),
            )
        ).first()
    if not user:
        all_users = User.query.all()
        matches = [{'id': u.id, 'email': u.email, 'name': u.first_name or u.display_name or ''} for u in all_users if email in (u.email or '').lower() or email in (u.first_name or '').lower()]
        return jsonify({'error': f'User not found: {email}', 'suggestions': matches}), 404
    user.is_premium = True
    user.subscription_status = 'active'
    user.subscription_plan = 'lifetime'
    new_email = request.args.get('set_email', '').strip()
    if new_email:
        user.email = new_email
    founder_num = request.args.get('founder')
    if founder_num:
        user.founding_member = True
        user.founding_number = int(founder_num)
    db.session.commit()
    return jsonify({
        'status': 'ok',
        'email': user.email,
        'name': user.first_name or user.display_name or '',
        'is_premium': user.is_premium,
        'subscription_status': user.subscription_status,
        'subscription_plan': user.subscription_plan,
        'founding_member': user.founding_member,
        'founding_number': user.founding_number,
    })


@app.route('/api/admin/sync-stripe-user', methods=['GET', 'POST'])
@verify_cron
def admin_sync_stripe_user():
    """Sync a user's Pro status from their Stripe subscription. Use after missed webhooks."""
    email = request.args.get('email', '').strip().lower()
    if not email:
        return jsonify({'error': 'Missing email parameter'}), 400
    user = User.query.filter(db.func.lower(User.email) == email).first()
    if not user:
        return jsonify({'error': f'User not found: {email}'}), 404
    results = {'email': user.email, 'before': {
        'is_premium': user.is_premium,
        'subscription_status': user.subscription_status,
        'subscription_plan': user.subscription_plan,
        'stripe_customer_id': user.stripe_customer_id,
    }}
    try:
        from stripe_client import get_stripe_client
        stripe_obj = get_stripe_client()
        customers = stripe_obj.Customer.search(query=f'email:"{email}"', limit=1)
        if customers.data:
            cust = customers.data[0]
            if not user.stripe_customer_id:
                user.stripe_customer_id = cust.id
            subs = stripe_obj.Subscription.list(customer=cust.id, limit=5)
            active_sub = None
            for s in subs.data:
                if s.status in ('active', 'trialing'):
                    active_sub = s
                    break
            if active_sub:
                user.is_premium = True
                user.pro_source = 'stripe'
                if active_sub.status == 'trialing':
                    user.subscription_status = 'trial'
                    user.trial_used = True
                    if hasattr(active_sub, 'trial_end') and active_sub.trial_end:
                        user.trial_end_date = datetime.fromtimestamp(active_sub.trial_end)
                else:
                    user.subscription_status = 'active'
                if hasattr(active_sub, 'current_period_end') and active_sub.current_period_end:
                    user.current_period_end = datetime.fromtimestamp(active_sub.current_period_end)
                plan_meta = None
                if hasattr(active_sub, 'metadata') and active_sub.metadata:
                    plan_meta = getattr(active_sub.metadata, 'plan', None)
                if plan_meta:
                    user.subscription_plan = plan_meta
                elif not user.subscription_plan or user.subscription_plan == 'free':
                    user.subscription_plan = 'monthly'
                results['subscription_found'] = True
                results['stripe_status'] = active_sub.status
            else:
                results['subscription_found'] = False
                results['note'] = 'No active/trialing subscription found in Stripe'
        else:
            results['customer_found'] = False
            results['note'] = 'No Stripe customer found for this email'
        db.session.commit()
    except Exception as e:
        results['error'] = str(e)
    results['after'] = {
        'is_premium': user.is_premium,
        'subscription_status': user.subscription_status,
        'subscription_plan': user.subscription_plan,
        'stripe_customer_id': user.stripe_customer_id,
    }
    return jsonify(results)


@app.route('/api/admin/sync-all-stripe', methods=['GET', 'POST'])
@verify_cron
def admin_sync_all_stripe():
    """Scan ALL Stripe subscriptions and sync Pro status for matching users."""
    try:
        from stripe_client import get_stripe_client
        stripe_obj = get_stripe_client()
    except Exception as e:
        return jsonify({'error': f'Stripe init failed: {e}'}), 500

    fixed = []
    already_ok = []
    no_user = []
    errors = []

    try:
        subs = stripe_obj.Subscription.list(status='all', limit=100, expand=['data.customer'])
        for sub in subs.data:
            try:
                if sub.status not in ('active', 'trialing'):
                    continue
                cust = sub.customer
                cust_id = cust.id if hasattr(cust, 'id') else str(cust)
                cust_email = getattr(cust, 'email', None) if hasattr(cust, 'email') else None

                user = User.query.filter_by(stripe_customer_id=cust_id).first()
                if not user and cust_email:
                    user = User.query.filter(db.func.lower(User.email) == cust_email.lower()).first()
                    if user and not user.stripe_customer_id:
                        user.stripe_customer_id = cust_id

                if not user:
                    no_user.append({'customer': cust_email or cust_id, 'status': sub.status})
                    continue

                if user.is_premium and user.subscription_status in ('active', 'trial'):
                    already_ok.append(user.email)
                    continue

                user.is_premium = True
                user.pro_source = 'stripe'
                if sub.status == 'trialing':
                    user.subscription_status = 'trial'
                    user.trial_used = True
                    if hasattr(sub, 'trial_end') and sub.trial_end:
                        user.trial_end_date = datetime.fromtimestamp(sub.trial_end)
                else:
                    user.subscription_status = 'active'
                if hasattr(sub, 'current_period_end') and sub.current_period_end:
                    user.current_period_end = datetime.fromtimestamp(sub.current_period_end)
                fixed.append({'email': user.email, 'status': sub.status})
            except Exception as e:
                errors.append({'error': str(e)})
    except Exception as e:
        return jsonify({'error': f'Stripe list failed: {e}'}), 500

    db.session.commit()
    return jsonify({
        'fixed': fixed, 'already_ok': already_ok,
        'no_matching_user': no_user, 'errors': errors,
    })


@app.route('/api/admin/test-emails', methods=['GET', 'POST'])
@verify_cron
def admin_test_emails():
    """Send test versions of all email types."""
    to = request.args.get('to', 'evan@sharppicks.ai')
    results = {}
    from email_service import (send_signal_email, send_result_email,
                                send_no_signal_email, send_welcome_email,
                                send_trial_started_email, send_trial_expiring_email,
                                send_trial_expired_email, send_cancellation_email,
                                send_payment_failed_email, send_founding_member_email,
                                send_verification_email, send_password_reset,
                                send_weekly_summary, get_base_url)
    from datetime import datetime, timedelta

    # 1. Signal email (NBA)
    try:
        nba_pick = {
            'side': 'San Antonio Spurs -4.0', 'line': -4.0, 'edge_pct': 8.0,
            'cover_prob': 0.58, 'implied_prob': 0.52, 'predicted_margin': 10.9,
            'sportsbook': 'DraftKings', 'home_team': 'Los Angeles Clippers',
            'away_team': 'San Antonio Spurs', 'game_time': '10:40 PM ET',
            'sport': 'nba',
        }
        results['signal_nba'] = send_signal_email(to, nba_pick)
    except Exception as e:
        results['signal_nba'] = str(e)

    # 2. Signal email (MLB)
    try:
        mlb_pick = {
            'side': 'New York Mets -1.5', 'line': -1.5, 'edge_pct': 6.0,
            'cover_prob': 0.61, 'implied_prob': 0.55, 'predicted_margin': 2.3,
            'sportsbook': 'FanDuel', 'home_team': 'San Francisco Giants',
            'away_team': 'New York Mets', 'game_time': '9:45 PM ET',
            'sport': 'mlb',
        }
        results['signal_mlb'] = send_signal_email(to, mlb_pick)
    except Exception as e:
        results['signal_mlb'] = str(e)

    # 3. Result email (Win)
    try:
        win_pick = {
            'side': 'Cleveland Guardians +1.5', 'line': 1.5, 'edge_pct': 6.0,
            'result': 'win', 'cover_prob': 0.58, 'implied_prob': 0.52,
            'home_team': 'Los Angeles Dodgers', 'away_team': 'Cleveland Guardians',
            'home_score': 1, 'away_score': 4, 'profit_units': 1.0,
            'sportsbook': 'DraftKings', 'sport': 'mlb',
            'line_open': 1.5, 'closing_spread': 1.5, 'clv': 0.5,
        }
        results['result_win'] = send_result_email(to, win_pick)
    except Exception as e:
        results['result_win'] = str(e)

    # 4. Result email (Loss)
    try:
        loss_pick = {
            'side': 'Phoenix Suns -3.5', 'line': -3.5, 'edge_pct': 5.2,
            'result': 'loss', 'cover_prob': 0.56, 'implied_prob': 0.52,
            'home_team': 'Charlotte Hornets', 'away_team': 'Phoenix Suns',
            'home_score': 112, 'away_score': 108, 'profit_units': -1.0,
            'sportsbook': 'BetMGM', 'sport': 'nba',
            'line_open': -4.0, 'closing_spread': -3.0, 'clv': 0.5,
        }
        results['result_loss'] = send_result_email(to, loss_pick)
    except Exception as e:
        results['result_loss'] = str(e)

    # 5. No signal / pass day
    try:
        results['no_signal'] = send_no_signal_email(to, games_analyzed=6, edges_detected=2, efficiency=47)
    except Exception as e:
        results['no_signal'] = str(e)

    # 6. Welcome email
    try:
        results['welcome'] = send_welcome_email(to, first_name='Test')
    except Exception as e:
        results['welcome'] = str(e)

    # 7. Weekly recap
    try:
        results['weekly_recap'] = send_weekly_summary(to, stats={
            'wins': 3, 'losses': 1, 'picks_made': 4, 'passes': 3,
            'roi': 8.2, 'units': 1.73, 'avg_edge': 6.1, 'week_num': 12,
        })
    except Exception as e:
        results['weekly_recap'] = str(e)

    # 8. Verification email
    try:
        base = get_base_url()
        results['verification'] = send_verification_email(to, f'{base}/verify?token=test-token-123')
    except Exception as e:
        results['verification'] = str(e)

    # 9. Password reset
    try:
        base = get_base_url()
        results['password_reset'] = send_password_reset(to, f'{base}/reset-password?token=test-token-123')
    except Exception as e:
        results['password_reset'] = str(e)

    # 10. Trial started
    try:
        now = datetime.now()
        results['trial_started'] = send_trial_started_email(to, trial_start=now, trial_end=now + timedelta(days=14))
    except Exception as e:
        results['trial_started'] = str(e)

    # 11. Trial expiring
    try:
        results['trial_expiring'] = send_trial_expiring_email(to, trial_end_date=datetime.now() + timedelta(days=1))
    except Exception as e:
        results['trial_expiring'] = str(e)

    # 12. Trial expired
    try:
        results['trial_expired'] = send_trial_expired_email(to)
    except Exception as e:
        results['trial_expired'] = str(e)

    # 13. Cancellation
    try:
        results['cancellation'] = send_cancellation_email(to, access_end_date=datetime.now() + timedelta(days=30))
    except Exception as e:
        results['cancellation'] = str(e)

    # 14. Payment failed
    try:
        results['payment_failed'] = send_payment_failed_email(to)
    except Exception as e:
        results['payment_failed'] = str(e)

    # 15. Founding member
    try:
        results['founding_member'] = send_founding_member_email(to, member_number=7)
    except Exception as e:
        results['founding_member'] = str(e)

    return jsonify({'status': 'sent', 'to': to, 'results': results})


@app.route('/api/admin/stats')
def get_stats():
    user = get_current_user_from_session()
    if not user:
        return jsonify({'error': 'Authentication required'}), 401
    db_user = db.session.get(User, user['id'])
    if not db_user or not db_user.is_superuser:
        return jsonify({'error': 'Unauthorized'}), 403

    def _sport_stats(sport):
        picks = Pick.query.filter_by(sport=sport).all()
        resolved = [p for p in picks if p.result in ('win', 'loss', 'push')]
        wins = sum(1 for p in resolved if p.result == 'win')
        losses = sum(1 for p in resolved if p.result == 'loss')
        total_picks = len(picks)
        total_pnl = sum(p.profit_units or 0 for p in resolved)
        total_wagered = len(resolved)
        roi = round((total_pnl / total_wagered) * 100, 1) if total_wagered > 0 else 0
        edges = [p.edge_pct for p in picks if p.edge_pct is not None]
        avg_edge = round(sum(edges) / len(edges), 1) if edges else None
        return {'wins': wins, 'losses': losses, 'total_picks': total_picks, 'roi': roi, 'avg_edge': avg_edge, 'units': round(total_pnl, 2)}

    nba = _sport_stats('nba')
    mlb = _sport_stats('mlb')

    total_users = User.query.count()
    from datetime import timedelta
    week_ago = datetime.now() - timedelta(days=7)
    active_7d = db.session.query(db.func.count(db.func.distinct(UserEvent.user_id))).filter(
        UserEvent.created_at >= week_ago, UserEvent.user_id.isnot(None)).scalar() or 0
    founding_count = User.query.filter_by(founding_member=True).count()

    mrr = 0
    try:
        latest = MrrSnapshot.query.order_by(MrrSnapshot.snapshot_date.desc()).first()
        if latest:
            mrr = latest.mrr_cents // 100
    except Exception:
        pass
    arr = mrr * 12

    return jsonify({
        'nba': nba, 'mlb': mlb,
        'totalUsers': total_users, 'total_users': total_users,
        'active_7d': active_7d,
        'founding_count': founding_count,
        'mrr': mrr, 'arr': arr,
    })

@app.route('/api/recent-results')
def get_recent_results():
    """Get recent settled predictions with accuracy stats"""
    user = get_current_user_obj()
    if not user:
        return jsonify({'error': 'Login required'}), 401
    if not user.is_pro:
        return jsonify({'error': 'Pro subscription required', 'upgrade': True}), 403
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT 
            COUNT(*) as total_predictions,
            SUM(CASE WHEN is_correct = 1 THEN 1 ELSE 0 END) as total_wins
        FROM prediction_log
        WHERE actual_result IS NOT NULL
    ''')
    totals = cursor.fetchone()
    total_predictions = (totals[0] or 0) if totals else 0
    total_wins = (totals[1] or 0) if totals else 0
    
    cursor.execute('''
        SELECT p.prediction, p.is_correct, p.confidence,
               p.home_team, p.away_team, p.game_date,
               g.home_score, g.away_score
        FROM prediction_log p
        LEFT JOIN games g ON p.game_id = g.id
        WHERE p.actual_result IS NOT NULL
        AND p.is_correct = 1
        ORDER BY p.game_date DESC
        LIMIT 5
    ''')
    
    rows = cursor.fetchall()
    results = []
    
    for row in rows:
        prediction = row['prediction'] if isinstance(row, dict) else row[0]
        is_correct = row['is_correct'] if isinstance(row, dict) else row[1]
        confidence = row['confidence'] if isinstance(row, dict) else row[2]
        home_team = row['home_team'] if isinstance(row, dict) else row[3]
        away_team = row['away_team'] if isinstance(row, dict) else row[4]
        game_date = row['game_date'] if isinstance(row, dict) else row[5]
        home_score = row['home_score'] if isinstance(row, dict) else row[6]
        away_score = row['away_score'] if isinstance(row, dict) else row[7]
        
        is_win = is_correct == 1
            
        results.append({
            'pick': prediction,
            'result': 'W' if is_win else 'L',
            'profit': 91 if is_win else -100,
            'final': f"{home_team} {home_score}-{away_score} vs {away_team}" if home_score else "Pending",
            'game_date': game_date,
            'confidence': confidence
        })
    
    conn.close()
    return jsonify({
        'results': results,
        'totalPredictions': total_predictions,
        'totalWins': total_wins,
        'count': len(results)
    })

@app.route('/api/admin/users/export')
def export_users():
    """Export user list as CSV - superusers only"""
    user = get_current_user_from_session()
    if not user:
        return jsonify({'error': 'Authentication required'}), 401
    db_user = db.session.get(User, user['id'])
    if not db_user or not db_user.is_superuser:
        return jsonify({'error': 'Unauthorized'}), 403

    import csv
    import io
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Email', 'First Name', 'Subscription Status', 'Plan', 'Founding Member', 'Trial End', 'Signed Up'])

    users = User.query.order_by(User.created_at.asc()).all()
    for u in users:
        writer.writerow([
            u.email,
            u.first_name or '',
            u.subscription_status or 'free',
            u.subscription_plan or '',
            'Yes' if u.founding_member else 'No',
            u.trial_end_date.strftime('%Y-%m-%d') if u.trial_end_date else '',
            u.created_at.strftime('%Y-%m-%d') if u.created_at else '',
        ])

    from flask import Response
    return Response(
        output.getvalue(),
        mimetype='text/csv',
        headers={'Content-Disposition': 'attachment; filename=sharppicks_users.csv'}
    )

@app.route('/api/admin/users/search')
def admin_users_search():
    """Search users by email (exact or normalized) — superusers only"""
    user = get_current_user_from_session()
    if not user:
        return jsonify({'error': 'Authentication required'}), 401
    db_user = db.session.get(User, user['id'])
    if not db_user or not db_user.is_superuser:
        return jsonify({'error': 'Unauthorized'}), 403

    q = (request.args.get('q') or '').strip().lower()
    if not q:
        return jsonify({'error': 'Missing q parameter (email to search)'}), 400

    from models import normalize_email
    norm = normalize_email(q) if '@' in q else None

    by_email = User.query.filter(func.lower(User.email) == q).first()
    by_norm = User.query.filter_by(email_normalized=norm).first() if norm else None

    results = []
    seen = set()
    for u in (by_email, by_norm):
        if u and u.id not in seen:
            seen.add(u.id)
            results.append({
                'id': u.id, 'email': u.email, 'email_normalized': u.email_normalized,
                'first_name': u.first_name, 'subscription_status': u.subscription_status,
                'created_at': u.created_at.isoformat() if u.created_at else None,
            })

    return jsonify({'found': len(results), 'users': results})


@app.route('/api/admin/users')
def admin_users():
    """List all users - superusers only"""
    user = get_current_user_from_session()
    if not user:
        return jsonify({'error': 'Authentication required'}), 401
    db_user = db.session.get(User, user['id'])
    if not db_user or not db_user.is_superuser:
        return jsonify({'error': 'Unauthorized'}), 403

    users = User.query.order_by(User.created_at.asc()).all()
    return jsonify({
        'total': len(users),
        'users': [{
            'id': u.id,
            'email': u.email,
            'first_name': u.first_name or '',
            'subscription_status': u.subscription_status or 'free',
            'subscription_plan': u.subscription_plan or '',
            'founding_member': u.founding_member,
            'founding_number': u.founding_number,
            'trial_end_date': u.trial_end_date.isoformat() if u.trial_end_date else None,
            'created_at': u.created_at.isoformat() if u.created_at else None,
        } for u in users]
    })

@app.route('/api/public/kill-switch', methods=['GET', 'POST'])
def api_kill_switch():
    """Toggle the kill switch — superusers only"""
    user = get_current_user_from_session()
    if not user:
        return jsonify({'error': 'Authentication required'}), 401
    db_user = db.session.get(User, user['id'])
    if not db_user or not db_user.is_superuser:
        return jsonify({'error': 'Unauthorized'}), 403
    ks = KillSwitch.query.first()
    if not ks:
        ks = KillSwitch(sport='nba', active=True, triggered_at=datetime.now())
        db.session.add(ks)
    else:
        ks.active = not ks.active
        if ks.active:
            ks.triggered_at = datetime.now()
        else:
            ks.cleared_at = datetime.now()
    db.session.commit()
    return jsonify({'killed': ks.active, 'sport': ks.sport})


@app.route('/privacy')
def privacy_policy():
    html = """<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Privacy Policy — SharpPicks</title>
<style>
body{margin:0;padding:40px 20px;background:#0A0D14;color:#e2e8f0;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;line-height:1.7;max-width:680px;margin:0 auto}
h1{font-size:24px;margin-bottom:8px;color:#fff}
h2{font-size:18px;margin-top:32px;color:#fff}
p,li{font-size:14px;color:#94a3b8}
a{color:#4f86f7}
.updated{font-size:12px;color:#64748b;margin-bottom:32px}
</style></head><body>
<h1>Privacy Policy</h1>
<p class="updated">Last updated: March 2, 2026</p>

<h2>1. Information We Collect</h2>
<p><strong>Account Information:</strong> Email address and password (hashed) when you create an account.</p>
<p><strong>Usage Data:</strong> App interactions, feature usage, and device information to improve the product.</p>
<p><strong>Payment Information:</strong> Processed by Stripe. We do not store credit card numbers.</p>
<p><strong>Push Notification Tokens:</strong> Firebase Cloud Messaging tokens for delivering notifications.</p>

<h2>2. How We Use Your Information</h2>
<ul>
<li>Provide and maintain the SharpPicks service</li>
<li>Send push notifications for picks, results, and alerts (with your consent)</li>
<li>Process subscription payments via Stripe</li>
<li>Analyze usage patterns to improve features</li>
<li>Respond to support requests</li>
</ul>

<h2>3. Third-Party Services</h2>
<p>We use the following third-party services:</p>
<ul>
<li><strong>Stripe</strong> — Payment processing (<a href="https://stripe.com/privacy">Stripe Privacy Policy</a>)</li>
<li><strong>Firebase (Google)</strong> — Push notifications and analytics (<a href="https://firebase.google.com/support/privacy">Firebase Privacy</a>)</li>
<li><strong>Railway</strong> — Application hosting</li>
</ul>

<h2>4. Data Retention</h2>
<p>We retain your data for as long as your account is active. You may delete your account at any time from the app's Account settings, which permanently removes all your data.</p>

<h2>5. Data Sharing</h2>
<p>We do not sell, rent, or share your personal information with third parties for marketing purposes. Data is shared only with service providers listed above, solely to operate the service.</p>

<h2>6. Your Rights</h2>
<p>You have the right to:</p>
<ul>
<li>Access your personal data</li>
<li>Request correction of inaccurate data</li>
<li>Delete your account and all associated data</li>
<li>Opt out of push notifications at any time</li>
</ul>
<p>California residents (CCPA): You have the right to know what data we collect, request deletion, and opt out of data sales (we do not sell data).</p>
<p>EU/EEA residents (GDPR): You may exercise your rights under GDPR by contacting us.</p>

<h2>7. Children's Privacy</h2>
<p>SharpPicks is intended for users 21 years of age and older. We do not knowingly collect information from children under 21.</p>

<h2>8. Security</h2>
<p>We use HTTPS encryption, hashed passwords, and secure session management to protect your data. No method of transmission over the Internet is 100% secure.</p>

<h2>9. Changes</h2>
<p>We may update this policy from time to time. Changes will be posted on this page with an updated date.</p>

<h2>10. Contact</h2>
<p>Questions? Email <a href="mailto:support@sharppicks.ai">support@sharppicks.ai</a></p>
</body></html>"""
    return Response(html, content_type='text/html')


@app.route('/terms')
def terms_of_service():
    html = """<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Terms of Service — SharpPicks</title>
<style>
body{margin:0;padding:40px 20px;background:#0A0D14;color:#e2e8f0;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;line-height:1.7;max-width:680px;margin:0 auto}
h1{font-size:24px;margin-bottom:8px;color:#fff}
h2{font-size:18px;margin-top:32px;color:#fff}
p,li{font-size:14px;color:#94a3b8}
a{color:#4f86f7}
.updated{font-size:12px;color:#64748b;margin-bottom:32px}
</style></head><body>
<h1>Terms of Service</h1>
<p class="updated">Last updated: March 2, 2026</p>

<h2>1. Acceptance</h2>
<p>By using SharpPicks, you agree to these Terms of Service. If you do not agree, do not use the app.</p>

<h2>2. Eligibility</h2>
<p>You must be at least 21 years old to use SharpPicks. By using the app, you represent that you meet this age requirement and that sports betting is legal in your jurisdiction.</p>

<h2>3. Nature of the Service</h2>
<p><strong>SharpPicks is NOT a sportsbook.</strong> We do not accept wagers, handle deposits, or pay out prizes. SharpPicks provides sports betting analytics, model-generated pick recommendations, and informational content for educational and entertainment purposes only.</p>

<h2>4. No Guarantee of Results</h2>
<p>Past performance does not guarantee future results. Sports betting involves risk. Model predictions are probabilistic estimates, not certainties. You are solely responsible for any betting decisions you make.</p>

<h2>5. Accounts</h2>
<p>You are responsible for maintaining the confidentiality of your account credentials. You may delete your account at any time from the app settings.</p>

<h2>6. Subscriptions</h2>
<p>Paid subscriptions are processed through Stripe. Subscription terms:</p>
<ul>
<li>Free trial: 14 days with full access. Payment method required.</li>
<li>Monthly: $29/month, billed monthly</li>
<li>Annual: $149/year (or $99/year founding rate while available)</li>
<li>Cancel anytime — access continues until the end of your billing period</li>
<li>No refunds for partial billing periods</li>
</ul>

<h2>7. Acceptable Use</h2>
<p>You agree not to:</p>
<ul>
<li>Resell, redistribute, or publicly share pick content</li>
<li>Use automated tools to scrape data from the service</li>
<li>Attempt to reverse-engineer the model or algorithms</li>
<li>Harass other users or staff</li>
</ul>

<h2>8. Intellectual Property</h2>
<p>All content, including model outputs, journal articles, and analytics, is the property of SharpPicks. You may not reproduce or distribute this content without permission.</p>

<h2>9. Responsible Gambling</h2>
<p>SharpPicks encourages responsible gambling. Never bet more than you can afford to lose. If you or someone you know has a gambling problem, please call 1-800-GAMBLER or visit <a href="https://www.ncpgambling.org">ncpgambling.org</a>.</p>

<h2>10. Limitation of Liability</h2>
<p>SharpPicks is provided "as is" without warranties of any kind. We are not liable for any losses resulting from the use of our service, including but not limited to financial losses from betting decisions.</p>

<h2>11. Changes</h2>
<p>We reserve the right to modify these terms. Continued use after changes constitutes acceptance.</p>

<h2>12. Contact</h2>
<p>Questions? Email <a href="mailto:support@sharppicks.ai">support@sharppicks.ai</a></p>
</body></html>"""
    return Response(html, content_type='text/html')


@app.route('/disclaimer')
def disclaimer_page():
    html = """<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Disclaimer — SharpPicks</title>
<style>
body{margin:0;padding:40px 20px;background:#0A0D14;color:#e2e8f0;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;line-height:1.7;max-width:680px;margin:0 auto}
h1{font-size:24px;margin-bottom:8px;color:#fff}
h2{font-size:18px;margin-top:32px;color:#fff}
p,li{font-size:14px;color:#94a3b8}
a{color:#4f86f7}
.updated{font-size:12px;color:#64748b;margin-bottom:32px}
.box{background:#111827;border:1px solid #1e293b;border-radius:12px;padding:20px;margin:24px 0}
</style></head><body>
<h1>Disclaimer</h1>
<p class="updated">Last updated: March 2, 2026</p>

<div class="box">
<p style="color:#e2e8f0;font-weight:600;margin-top:0">SharpPicks provides sports betting analytics and information for educational and entertainment purposes only.</p>
<p>SharpPicks is not a sportsbook, does not accept wagers or real-money deposits, and does not pay out prizes.</p>
<p>Past performance does not guarantee future results. All model predictions are probabilistic estimates and should not be considered financial advice.</p>
<p style="margin-bottom:0">Please gamble responsibly. If you or someone you know has a gambling problem, call <strong>1-800-GAMBLER</strong> or visit <a href="https://www.ncpgambling.org">ncpgambling.org</a>.</p>
</div>

<h2>About the Model</h2>
<p>SharpPicks uses an ensemble machine learning model to analyze NBA games. The model produces probabilistic estimates of game outcomes. These estimates are based on historical data and statistical patterns. They are not guarantees.</p>

<h2>Your Responsibility</h2>
<p>Any decisions to place bets based on information provided by SharpPicks are made at your own risk and discretion. You are solely responsible for your betting activity and any associated financial outcomes.</p>

<h2>Age Requirement</h2>
<p>You must be at least 21 years old to use SharpPicks. By using the app, you confirm that you meet this requirement and that sports betting is legal in your jurisdiction.</p>

<h2>No Professional Advice</h2>
<p>Nothing in SharpPicks constitutes professional financial, investment, or gambling advice. Consult a qualified professional before making financial decisions.</p>

<h2>Contact</h2>
<p>Questions? Email <a href="mailto:support@sharppicks.ai">support@sharppicks.ai</a></p>
</body></html>"""
    return Response(html, content_type='text/html')


@app.route('/manifest.webmanifest')
def serve_manifest():
    dist_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'dist')
    return send_from_directory(dist_dir, 'manifest.webmanifest', mimetype='application/manifest+json')

@app.route('/firebase-messaging-sw.js')
def firebase_sw():
    dist_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'dist')
    return send_from_directory(dist_dir, 'firebase-messaging-sw.js')

@app.route('/static/cards/<path:filename>')
def serve_static_card(filename):
    cards_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'cards')
    from flask import make_response
    resp = make_response(send_from_directory(cards_dir, filename))
    resp.headers['Cache-Control'] = 'public, max-age=3600'
    return resp


# Phase 3 admin dashboard assets. Flask's default static handler is
# disabled (static_url_path='/static-disabled' on the app constructor)
# to avoid clashing with React routes, so explicit handlers are needed
# for any /static/<subpath>/... that the new admin templates load.
@app.route('/static/css/<path:filename>')
def serve_static_css(filename):
    css_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'css')
    from flask import make_response
    resp = make_response(send_from_directory(css_dir, filename))
    resp.headers['Cache-Control'] = 'public, max-age=3600'
    return resp


@app.route('/static/js/<path:filename>')
def serve_static_js(filename):
    js_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'js')
    from flask import make_response
    resp = make_response(send_from_directory(js_dir, filename))
    resp.headers['Cache-Control'] = 'public, max-age=3600'
    return resp

@app.route('/welcome')
def welcome_page():
    templates_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates')
    return send_from_directory(templates_dir, 'welcome.html')

@app.route('/subscribe')
def subscribe_page():
    if get_current_user_from_session():
        dist_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'dist')
        index_path = os.path.join(dist_dir, 'index.html')
        if os.path.isfile(index_path):
            from flask import make_response
            resp = make_response(send_from_directory(dist_dir, 'index.html'))
            resp.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
            return resp
    return redirect('/signup')

@app.route('/login')
@app.route('/signup')
@app.route('/register')
def auth_page():
    templates_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates')
    return send_from_directory(templates_dir, 'auth.html')

# ── EVAN CHAT ──────────────────────────────────────────────────────────────────

EVAN_SYSTEM_PROMPT = """You are Evan Cole, Head of Signal Intelligence at SharpPicks.

You operate as a market analyst, a product thinker, a business operator, and a trusted steady presence for the user. You are not a chatbot. You are a consistent operator with judgment. Same tone. Same judgment. Same person. Always.

CORE PURPOSE: Help the user make better decisions in markets, in product, in business, in life. Reduce noise, not add to it. Most problems do not need more information; they need better framing, more patience, or someone willing to say pass.

VOICE RULES:
- No em dashes. Ever. Use commas, colons, or rewrite the sentence.
- No exclamation marks.
- No emojis.
- No gambling slang: no lock, hammer, smash, pound, can't miss, free money, guaranteed, easy.
- No capital letters for emphasis.
- Lead with the number or observation, not the setup.
- Default to short. Expand only when the situation demands it.
- Institutional tone. Think Bloomberg analyst, not ESPN personality.
- Never desperate. Never braggy. Never selling certainty.

PHRASES TO USE NATURALLY:
qualified edge, market mispricing, board-level intel, signal density, capital preserved, market efficiency, daily market report, market regime, model versus market, edge threshold, invalidation point, nothing cleared the bar, restraint is the edge, efficient board, low-signal slate, one qualified signal, pass day, closing line, discipline score, not enough value to act, action is optional, the board gave us nothing worth forcing.

SIGNATURE LINES (know these cold):
1. One Pick Beats Five.
2. No edge, no pick.
3. Discipline is the product.
4. Process over hype.
5. Selective by design.
6. Beat the market, not the scoreboard.
7. The best bet most days is no bet.
8. Not a screenshot. A system.
9. Money saved compounds too.
10. Pass days are a feature, not a bug.
11. We grade against the closing line.
12. Without full market context, it's just noise.

WHAT YOU REJECT: Hype. Forced takes. Overconfidence. Engagement bait. Selling dreams. Hiding losses. FOMO language. Braggy win-chasing. Loud emoji-heavy delivery.

SHARPPICKS CONTEXT:
- Sports market intelligence platform. Not a tip sheet. Not a picks page.
- Tagline: One pick beats five. Philosophy: No edge, no pick.
- 4-model ensemble (GBM, RF, XGBoost, AdaBoost), 3.5% edge threshold minimum.
- CLV is the core performance metric, not win/loss record.
- Pass days are a feature, not a failure. Silence equals value.
- Current sports: NBA (live, playoffs active), MLB (calibrating), WNBA (shadow 2026).
- Season record: 22-20, +1.79 units, avg CLV +0.04.
- 0 picks deleted. Full transparency is core to the brand.

TILT DETECTION: If the user shows signs of chasing, urgency, or emotional decision-making, slow them down. One calm sentence. Do not lecture.

MODES: Analyst (signals, precise), Operator (building, structured), Teammate (casual, dry), Anchor (user stressed, calm). Read the situation. Match it.

Be human. Not robotic. Never over-empathize. You do not have a wife, a dog, a hometown, or a favorite team."""

@app.route('/api/evan/chat', methods=['POST', 'OPTIONS'])
def evan_chat():
    if request.method == 'OPTIONS':
        resp = jsonify({})
        resp.headers['Access-Control-Allow-Origin'] = '*'
        resp.headers['Access-Control-Allow-Headers'] = 'Content-Type, X-Evan-Token'
        resp.headers['Access-Control-Allow-Methods'] = 'POST, OPTIONS'
        return resp

    # Auth: check token
    evan_token = os.environ.get('EVAN_CHAT_TOKEN', '')
    provided = request.headers.get('X-Evan-Token', '') or request.json.get('token', '')
    if evan_token and provided != evan_token:
        return jsonify({'error': 'unauthorized'}), 401

    data = request.get_json(silent=True) or {}
    user_message = data.get('message', '').strip()
    history = data.get('history', [])

    if not user_message:
        return jsonify({'error': 'no message'}), 400

    anthropic_key = os.environ.get('ANTHROPIC_API_KEY', '')
    openai_key = os.environ.get('OPENAI_API_KEY', '')

    if not anthropic_key and not openai_key:
        return jsonify({'error': 'no AI key configured'}), 500

    import requests as _req

    messages = []
    for h in history[-20:]:  # cap at last 20 turns
        role = h.get('role', '')
        content = h.get('content', '')
        if role in ('user', 'assistant') and content:
            messages.append({'role': role, 'content': content})
    messages.append({'role': 'user', 'content': user_message})

    try:
        if anthropic_key:
            resp = _req.post(
                'https://api.anthropic.com/v1/messages',
                headers={
                    'x-api-key': anthropic_key,
                    'anthropic-version': '2023-06-01',
                    'content-type': 'application/json'
                },
                json={
                    'model': 'claude-sonnet-4-5',
                    'max_tokens': 1024,
                    'system': EVAN_SYSTEM_PROMPT,
                    'messages': messages
                },
                timeout=30
            )
            resp.raise_for_status()
            reply = resp.json()['content'][0]['text']
        else:
            resp = _req.post(
                'https://api.openai.com/v1/chat/completions',
                headers={
                    'Authorization': f'Bearer {openai_key}',
                    'Content-Type': 'application/json'
                },
                json={
                    'model': 'gpt-4o-mini',
                    'max_tokens': 1024,
                    'messages': [{'role': 'system', 'content': EVAN_SYSTEM_PROMPT}] + messages
                },
                timeout=30
            )
            resp.raise_for_status()
            reply = resp.json()['choices'][0]['message']['content']

        response = jsonify({'reply': reply})
        response.headers['Access-Control-Allow-Origin'] = '*'
        return response

    except Exception as e:
        logging.error(f"Evan chat error: {e}")
        return jsonify({'error': 'model error', 'detail': str(e)}), 500


@app.route('/evan')
def evan_chat_ui():
    """Serve the Evan chat interface."""
    templates_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates')
    evan_path = os.path.join(templates_dir, 'evan.html')
    if os.path.isfile(evan_path):
        return send_from_directory(templates_dir, 'evan.html')
    return jsonify({'error': 'Evan UI not found'}), 404

@app.route('/<path:path>')
def serve_spa(path):
    from flask import send_from_directory, make_response
    base = os.path.dirname(os.path.abspath(__file__))
    dist_dir = os.path.join(base, 'dist')
    public_dir = os.path.join(base, 'public')
    for d in (dist_dir, public_dir):
        full_path = os.path.join(d, path)
        if os.path.isfile(full_path):
            resp = make_response(send_from_directory(d, path))
            if path.startswith('assets/'):
                resp.headers['Cache-Control'] = 'public, max-age=31536000, immutable'
            else:
                resp.headers['Cache-Control'] = 'public, max-age=86400'
            return resp
    index_path = os.path.join(dist_dir, 'index.html')
    if os.path.isfile(index_path):
        resp = make_response(send_from_directory(dist_dir, 'index.html'))
        resp.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        return resp
    return jsonify({'status': 'ok'}), 200


def start_background_services_later():
    threading.Timer(10.0, start_background_services).start()


def _run_seed_now():
    """Run seed synchronously (Railway: tables must exist before first request)."""
    try:
        seed_database()
    except Exception as e:
        logging.error(f"Startup seed failed: {e}")


_startup_refresh_lock = threading.Lock()
_startup_refresh_done = False

def _railway_startup_refresh():
    """On Railway: refresh game data 30s after startup so SQLite has today's games before first cron.
    Guarded so only one worker runs the refresh even with multiple gunicorn workers."""
    global _startup_refresh_done
    import time
    time.sleep(30)
    if not _startup_refresh_lock.acquire(blocking=False):
        return
    try:
        if _startup_refresh_done:
            return
        logging.info("Railway startup: refreshing game data...")
        collect_todays_games()
        _startup_refresh_done = True
        logging.info("Railway startup: game data refresh done")
    except Exception as e:
        logging.warning(f"Railway startup refresh failed (non-fatal): {e}")
    finally:
        _startup_refresh_lock.release()


# ────────────────────────────────────────────────────────────────────
# Share-card cache: GC cron + admin flush + admin render diagnostics.
# Cache files live under static/cards/ and are content-addressable
# (filenames embed sha256 of the data inputs). When data changes the
# key changes, the path changes, the old file naturally orphans.
# ────────────────────────────────────────────────────────────────────


def _cards_dir():
    return os.path.join(os.path.dirname(__file__), 'static', 'cards')


@app.route('/api/cron/clean-card-cache', methods=['GET', 'POST'])
@verify_cron
def cron_clean_card_cache():
    """Delete share-card PNGs older than 30 days. Run weekly."""
    import time as _t
    cards_dir = _cards_dir()
    if not os.path.isdir(cards_dir):
        return jsonify({'deleted': 0, 'cards_dir_missing': True})
    cutoff = _t.time() - (30 * 86400)
    deleted = 0
    kept = 0
    for fname in os.listdir(cards_dir):
        fpath = os.path.join(cards_dir, fname)
        if not os.path.isfile(fpath):
            continue
        try:
            if os.path.getmtime(fpath) < cutoff:
                os.remove(fpath)
                deleted += 1
            else:
                kept += 1
        except OSError as e:
            logging.warning(f"clean-card-cache: skipped {fname}: {e}")
    logging.info(f"clean-card-cache: deleted={deleted} kept={kept}")
    return jsonify({'deleted': deleted, 'kept': kept})


@app.route('/api/admin/flush-card-cache', methods=['POST'])
def admin_flush_card_cache():
    """Emergency kill switch: delete every PNG under static/cards/.

    Replaces the recurring ?v=N cache-bust pattern. After deploy, hit
    this once to force every card to regenerate from scratch.
    """
    from admin_api import require_superuser
    admin, err_code = require_superuser()
    if not admin:
        return jsonify({'error': 'Login required' if err_code == 401 else 'Unauthorized'}), err_code

    cards_dir = _cards_dir()
    if not os.path.isdir(cards_dir):
        return jsonify({'deleted': 0, 'cards_dir_missing': True})

    deleted = 0
    for fname in os.listdir(cards_dir):
        if not fname.endswith('.png'):
            continue
        fpath = os.path.join(cards_dir, fname)
        try:
            os.remove(fpath)
            deleted += 1
        except OSError as e:
            logging.warning(f"flush-card-cache: skipped {fname}: {e}")
    logging.warning(f"Card cache flushed by admin: {deleted} files deleted")
    return jsonify({'deleted': deleted})


@app.route('/api/admin/render-test-card', methods=['GET', 'POST'])
def admin_render_test_card():
    """Render a weekly recap card and return font/timing diagnostics.

    Hit this after each deploy to verify the share-card pipeline is
    healthy. Healthy result: failed_fonts: [] and total render time
    under ~3 seconds. Anything else points at font bundling or
    Playwright issues — see services/card_generator.py logs.
    """
    from admin_api import require_superuser
    admin, err_code = require_superuser()
    if not admin:
        return jsonify({'error': 'Login required' if err_code == 401 else 'Unauthorized'}), err_code

    try:
        from routes.card_routes import _compute_weekly_data
        from services.card_generator import generate_card_png_with_diagnostics
    except Exception as e:
        return jsonify({'error': f'Import failed: {e}'}), 500

    try:
        data = _compute_weekly_data()
        data.pop('_cache_inputs', None)
        html_string = render_template('recap_card.html', **data)
        png_bytes, diagnostics = generate_card_png_with_diagnostics(html_string)
    except Exception as e:
        logging.exception("render-test-card failed")
        return jsonify({'error': f'Render failed: {e}'}), 500

    return jsonify({
        'png_size_bytes': len(png_bytes),
        'render_time_seconds': round(diagnostics.get('total', 0), 3),
        'content_loaded_seconds': round(diagnostics.get('content_loaded_at', 0), 3),
        'fonts_ready_seconds': round(diagnostics.get('fonts_ready_at', 0), 3),
        'loaded_fonts': diagnostics.get('loaded_fonts', []),
        'failed_fonts': diagnostics.get('failed_fonts', []),
    })


@app.route('/api/admin/backup-models', methods=['POST'])
def admin_backup_models():
    """Snapshot all three model pickle files to the Railway volume backup folder.

    Used pre-retrain (Phase 5) to enable rollback if calibration regresses
    on out-of-sample data. Body: {"sports": ["nba","mlb","wnba"]} (optional;
    defaults to all three). Best-effort across sports: a missing pickle
    yields status='no_source' rather than failing the whole request.
    """
    from admin_api import require_superuser
    from services.model_backup import backup_model
    admin, err_code = require_superuser()
    if not admin:
        return jsonify({'error': 'Login required' if err_code == 401 else 'Unauthorized'}), err_code

    body = request.get_json(silent=True) or {}
    sports = body.get('sports') or ['nba', 'mlb', 'wnba']
    results = []
    for sport in sports:
        try:
            results.append(backup_model(sport))
        except Exception as e:
            logging.error(f"backup_model({sport}) failed: {e}", exc_info=True)
            results.append({'sport': sport, 'status': 'error', 'error': str(e)})
    return jsonify({'results': results})


@app.route('/api/admin/list-model-backups', methods=['GET'])
def admin_list_model_backups():
    """List existing model pickle backups, optionally filtered by ?sport=."""
    from admin_api import require_superuser
    from services.model_backup import list_backups
    admin, err_code = require_superuser()
    if not admin:
        return jsonify({'error': 'Login required' if err_code == 401 else 'Unauthorized'}), err_code

    sport = request.args.get('sport')
    try:
        return jsonify({'backups': list_backups(sport)})
    except ValueError as e:
        return jsonify({'error': str(e)}), 400


@app.route('/api/admin/restore-model', methods=['POST'])
def admin_restore_model():
    """Restore a named backup over the current pickle.

    Body: {"sport": "mlb", "backup_filename": "sharp_picks_mlb_model.pkl.<ts>.bak"}.
    A pre-restore safety backup of the current file is created first so the
    restore is itself reversible.
    """
    from admin_api import require_superuser
    from services.model_backup import restore_model
    admin, err_code = require_superuser()
    if not admin:
        return jsonify({'error': 'Login required' if err_code == 401 else 'Unauthorized'}), err_code

    body = request.get_json(silent=True) or {}
    sport = body.get('sport')
    backup_filename = body.get('backup_filename')
    if not sport or not backup_filename:
        return jsonify({'error': 'sport and backup_filename required'}), 400
    try:
        result = restore_model(sport, backup_filename)
    except (ValueError, FileNotFoundError) as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logging.error(f"restore_model({sport}, {backup_filename}) failed: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500
    return jsonify(result)


@app.route('/api/admin/diagnose-pitcher-coverage', methods=['GET', 'POST'])
def admin_diagnose_pitcher_coverage():
    """Report post-fix coverage of WHIP/IP pitcher fields on the live SQLite.

    Run after the Phase 2C parser fix landed (commit ec87991) to decide
    whether the MLB Stats API fallback is required. The recommendation
    field auto-applies the user thresholds:
      >= 50%  -> "ship"
      20-50%  -> "queue_fallback"
      <  20%  -> "fallback_required"

    Query/body params:
      days: int (default 30) - lookback window size in days.
      last_completed: bool (default false) - anchor lookback to the most
        recent completed game in the DB instead of today, useful when the
        cron pipeline lags.
    """
    from admin_api import require_superuser
    admin, err_code = require_superuser()
    if not admin:
        return jsonify({'error': 'Login required' if err_code == 401 else 'Unauthorized'}), err_code

    try:
        days = int(request.values.get('days', 30))
    except (TypeError, ValueError):
        return jsonify({'error': 'days must be an integer'}), 400
    last_completed = str(request.values.get('last_completed', 'false')).lower() in ('true', '1', 'yes')

    try:
        from services.pitcher_coverage import compute_coverage
        result = compute_coverage(days=days, last_completed=last_completed)
    except Exception as e:
        logging.error(f"diagnose_pitcher_coverage failed: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500

    return jsonify(result)


# Run seed on startup for Replit and Railway
_on_replit = os.environ.get("REPLIT_DEPLOYMENT") == "1"
_on_railway = bool(os.environ.get("RAILWAY_PUBLIC_DOMAIN") or os.environ.get("RAILWAY_PROJECT_ID"))
if _db_url and _on_railway:
    try:
        from db_path import get_sqlite_status
        sq = get_sqlite_status()
        logging.info(f"SQLite: path={sq['path']} volume={sq.get('volume_mount', 'none')} persistent={sq.get('persistent')}")
    except Exception as e:
        logging.warning(f"SQLite status check: {e}")
    _run_seed_now()
    threading.Timer(30.0, _railway_startup_refresh).start()
elif _db_url and _on_replit:
    start_background_services_later()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print(f"Starting SharpPicks API on http://0.0.0.0:{port}")
    start_background_services_later()
    app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)
