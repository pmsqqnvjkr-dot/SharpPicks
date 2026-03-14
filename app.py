"""
SHARP PICKS - ALL-IN-ONE APP
Flask server with API endpoints, dashboard, authentication, and scheduled tasks
"""

import os
import sys
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

@app.route('/health')
def health():
    return {'status': 'ok'}, 200

@app.route('/')
def root_health():
    dist_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'dist')
    index_path = os.path.join(dist_dir, 'index.html')
    if os.path.isfile(index_path):
        from flask import send_from_directory, make_response
        resp = make_response(send_from_directory(dist_dir, 'index.html'))
        resp.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        return resp
    return 'ok', 200

is_production = os.environ.get('REPLIT_DEPLOYMENT') == '1'

CRON_SECRET = os.environ.get('CRON_SECRET', '')

def verify_cron(f):
    from functools import wraps
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not CRON_SECRET or request.headers.get('X-Cron-Secret') != CRON_SECRET:
            return jsonify({'error': 'unauthorized'}), 403
        return f(*args, **kwargs)
    return wrapper

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

from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_login import LoginManager, login_required, current_user, login_user, logout_user
from werkzeug.middleware.proxy_fix import ProxyFix
import sqlite3
import subprocess
from db_path import get_sqlite_path
import requests as http_requests
from datetime import datetime, timedelta

def _get_et_today():
    """Get current Eastern Time date string (YYYY-MM-DD)."""
    try:
        from zoneinfo import ZoneInfo
        now_et = datetime.now(ZoneInfo('America/New_York'))
    except ImportError:
        now_et = datetime.utcnow() - timedelta(hours=5)
    return now_et.strftime('%Y-%m-%d')

from models import db, User, TrackedBet, Pick, Pass, ModelRun, FoundingCounter, Insight, ProcessedEvent, CronLog
from picks_api import picks_bp
from public_api import public_bp
from insights_api import insights_bp
from model_service import run_model_and_log
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
    stored_token = session.get('session_token')
    if not stored_token or stored_token != user.session_token:
        session.pop('user_id', None)
        session.pop('session_token', None)
        return None
    return user

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
        'is_superuser': user.is_superuser,
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

@app.route('/admin')
def admin_dashboard():
    from flask import render_template
    return render_template('admin.html')

MANIFESTO_CONTENT = """When I started building SharpPicks, I wasn\u2019t trying to create another betting app. The market already has plenty of those.

Most focus on action \u2014 more picks, more volume, more reasons to bet every game on the board. But anyone who has spent real time studying sports markets eventually arrives at the same conclusion: the majority of opportunities simply aren\u2019t worth taking.

Sports betting is a market. Every spread, total, and moneyline is a price shaped by probability, information, and behavior. Like any market, it becomes efficient quickly. And when markets are efficient, edges become rare.

That reality is the foundation of SharpPicks.

The model was designed to analyze every game on the board \u2014 measuring statistical signals, market movement, and probability gaps. But identifying edges is only part of the equation. The harder part is restraint. The discipline to wait. The discipline to pass. The discipline to accept that most slates will produce very few genuine opportunities.

SharpPicks exists to enforce that discipline.

---

> **SHARP PRINCIPLE**
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
                db.session.execute(db.text("ALTER TABLE model_runs ADD COLUMN IF NOT EXISTS games_detail TEXT"))
                db.session.execute(db.text("ALTER TABLE insights ADD COLUMN IF NOT EXISTS related_pick_ids JSONB DEFAULT '[]'"))
                db.session.execute(db.text("ALTER TABLE insights ADD COLUMN IF NOT EXISTS date_range_start VARCHAR"))
                db.session.execute(db.text("ALTER TABLE insights ADD COLUMN IF NOT EXISTS date_range_end VARCHAR"))
                db.session.execute(db.text("ALTER TABLE tracked_bets ADD COLUMN IF NOT EXISTS bet_type VARCHAR DEFAULT 'spread'"))
                db.session.execute(db.text("ALTER TABLE tracked_bets ADD COLUMN IF NOT EXISTS parlay_legs INTEGER"))
                db.session.commit()
            except Exception as e:
                db.session.rollback()
                logging.warning(f"Column migration note: {e}")

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
                sconn = sqlite3.connect(get_sqlite_path())
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
                {'email': 'erin.m.donnelly@gmail.com', 'first_name': 'Evan', 'password': 'H@rp2019*'},
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

> **SHARP PRINCIPLE**
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

> **SHARP PRINCIPLE**
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

> **SHARP PRINCIPLE**
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

> **SHARP PRINCIPLE**
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

> **SHARP PRINCIPLE**
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

> **SHARP PRINCIPLE**
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

> **Most of our value comes from the days we don\u2019t publish. Restraint is the edge nobody wants to sell.**

---

## What Our Threshold Actually Does

SharpPicks publishes at most one pick per day. Some days, zero. The ensemble model evaluates every game on the board. If nothing clears a 3.5% expected edge, the system stays silent.

That silence isn\u2019t a failure. It\u2019s the system working exactly as designed. It means the market is priced efficiently that night, and there\u2019s nothing worth risking capital on.

Over a long enough sample, the nights you sit out contribute just as much to your ROI as the nights you fire.

> **WHY THIS MATTERS**
>
> This principle defines the product. SharpPicks will never pad your card to justify a subscription. If the edge isn\u2019t there, you\u2019ll hear nothing. That\u2019s the point.

*Evan Cole*
Founder, SharpPicks""",
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
Founder, SharpPicks""",
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
Founder, SharpPicks""",
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
Founder, SharpPicks""",
                    status="scheduled", publish_date=datetime(2026, 3, 22), reading_time_minutes=3,
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

> **SHARP PRINCIPLE**
>
> Volume without discipline is just noise. But volume with selectivity is the ideal environment for quantitative edge detection. Baseball provides exactly that.

---

## What This Means for SharpPicks

SharpPicks was built for exactly this kind of environment: large slates, deep data, and a market that rewards patience over action. The model scans every game, identifies probability gaps, and filters aggressively. Most games get passed. The few that qualify earn a signal.

That philosophy doesn't change with the sport. It intensifies. A 15-game slate with 2 signals is discipline in action. A 15-game slate with 0 signals is the system protecting your bankroll.

Baseball is a quant market. SharpPicks is a quant product. The fit is natural.

*Evan Cole*
Founder, SharpPicks""",
                    status="published", publish_date=datetime(2026, 3, 1), reading_time_minutes=4,
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

> **SHARP PRINCIPLE**
>
> Price is information. Every spread, total, and moneyline is a statement about probability. Sharp bettors don't argue with the statement — they measure whether it's accurate.

---

## Why This Is Hard

Focusing on price requires ignoring narratives. It means passing on your favorite team when the number is wrong. It means betting on teams you don't like when the number is right. It means accepting that the market is usually correct — and only acting when it demonstrably isn't.

That kind of discipline is uncomfortable. But it's the only approach that compounds over time.

SharpPicks enforces this automatically. The model doesn't know team names. It knows probabilities, prices, and gaps. When the gap is large enough, it signals. When it isn't, it stays silent. No narrative. No bias. Just math.

*Evan Cole*
Founder, SharpPicks""",
                    status="published", publish_date=datetime(2026, 3, 2), reading_time_minutes=4,
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

> **SHARP PRINCIPLE**
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
Founder, SharpPicks""",
                    status="published", publish_date=datetime(2026, 3, 3), reading_time_minutes=4,
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

> **SHARP PRINCIPLE**
>
> The market overweights what's visible (starting pitchers) and underweights what's hidden (bullpen fatigue, schedule density, reliever workload). Models that factor rest and usage patterns find edges the public doesn't see.

---

## Why SharpPicks Tracks This

The SharpPicks model incorporates rest days, schedule density, and back-to-back indicators as features. When one team's bullpen is taxed and the opponent's is fresh, that asymmetry feeds directly into the probability calculation.

It's not glamorous analysis. Nobody tweets about bullpen availability. But it's the kind of structural edge that compounds over a 162-game season — quietly, consistently, and invisibly to the casual market.

The best edges aren't the ones that make headlines. They're the ones nobody else is looking at.

*Evan Cole*
Founder, SharpPicks""",
                    status="published", publish_date=datetime(2026, 3, 4), reading_time_minutes=4,
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

> **SHARP PRINCIPLE**
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
Founder, SharpPicks""",
                    status="published", publish_date=datetime(2026, 3, 5), reading_time_minutes=5,
                ))
            if incremental_insights:
                for ins in incremental_insights:
                    db.session.add(ins)
                db.session.commit()
                logging.info(f"Added {len(incremental_insights)} new insights")

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
        from main import collect_todays_games as _collect
        _collect()
        logging.info("[collect] Completed")
    except Exception as e:
        logging.error(f"[collect] Error: {e}")
        raise

def grade_pending_picks():
    """Check game results and grade pending picks as win/loss"""
    with app.app_context():
        pending_picks = Pick.query.filter_by(result='pending').all()
        logging.info(f"[Auto-grade] Found {len(pending_picks)} pending picks")
        if not pending_picks:
            return

        try:
            sqlite_conn = None
            try:
                sqlite_conn = sqlite3.connect(get_sqlite_path())
                sqlite_conn.row_factory = sqlite3.Row
                sqlite_cursor = sqlite_conn.cursor()
            except Exception:
                sqlite_cursor = None

            for pick in pending_picks:
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
                            if espn_home['team']['displayName'] == pick.home_team and espn_away['team']['displayName'] == pick.away_team:
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
                        table_name = 'wnba_games' if pick.sport == 'wnba' else 'games'
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

                side_lower = pick.side.lower()
                home_lower = pick.home_team.lower()
                away_lower = pick.away_team.lower()
                is_home_pick = home_lower in side_lower or any(
                    word in side_lower for word in home_lower.split() if len(word) > 3
                )
                is_away_pick = away_lower in side_lower or any(
                    word in side_lower for word in away_lower.split() if len(word) > 3
                )
                if not is_home_pick and not is_away_pick:
                    print(f"[Auto-grade] Cannot determine side for: {pick.side} ({pick.home_team} vs {pick.away_team})")
                    continue

                if is_home_pick and not is_away_pick:
                    ats_margin = spread_result + line_value
                else:
                    ats_margin = -spread_result + line_value

                pick.home_score = home_score
                pick.away_score = away_score

                if ats_margin == 0:
                    pick.result = 'push'
                    pick.result_ats = 'P'
                    pick.profit_units = 0.0
                    pick.pnl = 0
                elif ats_margin > 0:
                    pick.result = 'win'
                    pick.result_ats = 'W'
                    actual_odds = pick.market_odds or -110
                    if actual_odds < 0:
                        pick.profit_units = round(100 / abs(actual_odds), 2)
                    else:
                        pick.profit_units = round(actual_odds / 100, 2)
                    pick.pnl = round(pick.profit_units * 100, 0)
                else:
                    pick.result = 'loss'
                    pick.result_ats = 'L'
                    pick.profit_units = -1.0
                    pick.pnl = -100

                pick.result_resolved_at = datetime.now()

                print(f"[Auto-grade] {pick.game_date}: {pick.side} -> {pick.result} (score: {home_score}-{away_score})")

                try:
                    from notification_service import send_result_notification
                    send_result_notification(pick, pick.result)
                except Exception as e:
                    print(f"[Auto-grade] Result notification error: {e}")

                linked_bets = TrackedBet.query.filter_by(pick_id=pick.id, result=None).all()
                for tb in linked_bets:
                    tb.result = pick.result_ats
                    if pick.result_ats == 'W':
                        if tb.odds < 0:
                            tb.profit = round(tb.bet_amount * (100 / abs(tb.odds)), 2)
                        else:
                            tb.profit = round(tb.bet_amount * (tb.odds / 100), 2)
                    elif pick.result_ats == 'P':
                        tb.profit = 0.0
                    else:
                        tb.profit = -tb.bet_amount
                    print(f"[Auto-grade] Tracked bet #{tb.id} for user {tb.user_id} -> {pick.result_ats}")

            if sqlite_conn:
                sqlite_conn.close()
            db.session.commit()
        except Exception as e:
            print(f"[Auto-grade] Error: {e}")

def collect_closing_lines():
    """Snapshot current lines as closing lines from local SQLite.
    Fetches all today's games, then filters for those tipping off within
    the next 10 minutes that haven't been scored yet.
    Does NOT re-fetch from external APIs — relies on refresh-lines cron
    to keep lines current."""
    with app.app_context():
        try:
            conn = sqlite3.connect(get_sqlite_path())
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
                        pick_line = today_pick.line
                        today_pick.clv = closing - pick_line

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
            conn = sqlite3.connect(get_sqlite_path())
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
                        today_pick.clv = closing - today_pick.line
            
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
        conn = sqlite3.connect(get_sqlite_path())
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        today_str = _get_et_today()
        
        cursor.execute('''
            SELECT COUNT(*) as cnt FROM games
            WHERE game_date LIKE ? AND spread_home IS NULL
        ''', (f'{today_str}%',))
        missing_spreads = cursor.fetchone()['cnt']
        if missing_spreads > 0:
            issues.append(f"WARN: {missing_spreads} games today missing spread data")
        
        cursor.execute('''
            SELECT home_team, away_team, COUNT(*) as cnt
            FROM games WHERE game_date LIKE ?
            GROUP BY home_team, away_team HAVING cnt > 1
        ''', (f'{today_str}%',))
        dupes = cursor.fetchall()
        if dupes:
            for d in dupes:
                issues.append(f"WARN: Duplicate game {d['away_team']}@{d['home_team']} ({d['cnt']}x)")
        
        cursor.execute('''
            SELECT collected_at FROM games
            WHERE game_date LIKE ?
            ORDER BY collected_at DESC LIMIT 1
        ''', (f'{today_str}%',))
        latest = cursor.fetchone()
        if latest and latest['collected_at']:
            from datetime import datetime as dt
            collected = dt.fromisoformat(latest['collected_at'])
            hours_old = (datetime.now() - collected).total_seconds() / 3600
            if hours_old > 6:
                issues.append(f"WARN: Lines are {hours_old:.1f}h old — may be stale")
        
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

            conn = sqlite3.connect(get_sqlite_path())
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            graded = 0
            for p in ungraded:
                cursor.execute('''
                    SELECT home_score, away_score, spread_home
                    FROM games
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
                is_home_pick = p.whatif_pick_side == 'home'

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
    'wnba_collect': 600,
    'wnba_closing_lines': 60,
    'wnba_shadow': 600,
    'wnba_grade': 300,
    'mlb_collect': 600,
    'mlb_closing_lines': 60,
    'mlb_run_model': 600,
    'mlb_grade': 300,
    'retrain_model': 86400,
}

def log_cron(job_name, fn, skip_throttle=False):
    min_interval = CRON_MIN_INTERVAL.get(job_name, 0)
    if min_interval and not skip_throttle:
        last_ok = CronLog.query.filter_by(job_name=job_name, status='ok')\
            .order_by(CronLog.executed_at.desc()).first()
        if last_ok:
            seconds_since = (datetime.utcnow() - last_ok.executed_at).total_seconds()
            if seconds_since < min_interval:
                return jsonify({'status': 'skipped', 'job': job_name,
                                'reason': f'throttled ({int(seconds_since)}s since last run, min {min_interval}s)'}), 200

    with _cron_lock_mutex:
        now = _time.time()
        if job_name in _cron_locks:
            lock_time, running = _cron_locks[job_name]
            if running:
                return jsonify({'status': 'skipped', 'job': job_name,
                                'reason': 'already running'}), 200
        _cron_locks[job_name] = (now, True)

    start = _time.time()
    try:
        result = fn()
        dur = int((_time.time() - start) * 1000)
        log = CronLog(job_name=job_name, status='ok', duration_ms=dur,
                      message=str(result) if result else None)
        db.session.add(log)
        db.session.commit()
        resp = {'status': 'done', 'job': job_name, 'duration_ms': dur}
        if isinstance(result, dict):
            resp.update(result)
        return jsonify(resp)
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
        return jsonify({'status': 'error', 'job': job_name, 'message': str(e)}), 500
    finally:
        with _cron_lock_mutex:
            _cron_locks[job_name] = (_time.time(), False)


@app.route('/api/cron/collect-games', methods=['GET', 'POST'])
@verify_cron
def cron_collect_games():
    return log_cron('collect_games', collect_todays_games)


@app.route('/api/cron/refresh-lines', methods=['GET', 'POST'])
@verify_cron
def cron_refresh_lines():
    force = request.args.get('force', '').lower() == 'true'
    return log_cron('refresh_lines', collect_todays_games, skip_throttle=force)


@app.route('/api/cron/closing-lines', methods=['GET', 'POST'])
@verify_cron
def cron_closing_lines():
    return log_cron('closing_lines', collect_closing_lines)


@app.route('/api/cron/wnba-collect', methods=['GET', 'POST'])
@verify_cron
def cron_wnba_collect():
    return log_cron('wnba_collect', collect_wnba_games_job)


@app.route('/api/cron/wnba-closing-lines', methods=['GET', 'POST'])
@verify_cron
def cron_wnba_closing_lines():
    return log_cron('wnba_closing_lines', collect_wnba_closing_lines_job)


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
            conn = sqlite3.connect(get_sqlite_path())
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            today_str = _get_et_today()
            cursor.execute('''
                SELECT id, home_team, away_team, spread_home, total,
                       home_ml, away_ml
                FROM mlb_games
                WHERE game_date LIKE ?
                AND home_score IS NULL
                AND spread_home IS NOT NULL
            ''', (f'{today_str}%',))

            games = cursor.fetchall()
            updated = 0

            for game in games:
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
                        today_pick.clv = closing - today_pick.line

            conn.commit()
            conn.close()
            db.session.commit()
            print(f"[{datetime.now()}] Captured MLB closing lines for {updated} games")
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

            conn = sqlite3.connect(get_sqlite_path())
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            for pick in pending:
                cursor.execute(
                    "SELECT home_score, away_score FROM mlb_games WHERE home_team = ? AND away_team = ? AND game_date = ?",
                    (pick.home_team, pick.away_team, pick.game_date)
                )
                row = cursor.fetchone()
                if not row or row['home_score'] is None:
                    continue

                home_score = int(row['home_score'])
                away_score = int(row['away_score'])
                pick.home_score = home_score
                pick.away_score = away_score

                run_diff = home_score - away_score
                line_val = pick.line or 0

                if pick.side == 'home':
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
    return log_cron('mlb_collect', collect_mlb_games_job)


@app.route('/api/cron/mlb-closing-lines', methods=['GET', 'POST'])
@verify_cron
def cron_mlb_closing_lines():
    return log_cron('mlb_closing_lines', collect_mlb_closing_lines_job)


def run_mlb_model_job():
    """Run the MLB model to generate picks."""
    print(f"[{datetime.now()}] Running MLB model...")
    with app.app_context():
        try:
            from model_service import run_model_and_log
            force = request.args.get('force', 'false').lower() == 'true'
            run_model_and_log(app, sport='mlb', force=force)
            print(f"[{datetime.now()}] MLB model run completed!")
        except Exception as e:
            print(f"[{datetime.now()}] MLB model error: {e}")


@app.route('/api/cron/mlb-run-model', methods=['GET', 'POST'])
@verify_cron
def cron_mlb_run_model():
    return log_cron('mlb_run_model', run_mlb_model_job, skip_throttle=True)


@app.route('/api/cron/mlb-grade', methods=['GET', 'POST'])
@verify_cron
def cron_mlb_grade():
    return log_cron('mlb_grade', grade_mlb_picks_job)


@app.route('/api/cron/player-props', methods=['GET', 'POST'])
@verify_cron
def cron_player_props():
    def _collect_props():
        from main import collect_player_props
        collect_player_props()
    return log_cron('player_props', _collect_props)


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


@app.route('/api/cron/run-model', methods=['GET', 'POST'])
@verify_cron
def cron_run_model():
    force = request.args.get('force', '').lower() == 'true'
    date_override = request.args.get('date', '').strip() or None
    if date_override and len(date_override) == 10 and date_override[4] == '-' and date_override[7] == '-':
        pass
    else:
        date_override = None

    def _run():
        if force:
            today_str = date_override or _get_et_today()
            print(f"[model-run] Force mode: collecting games + clearing stale passes for {today_str}")
            try:
                collect_todays_games()
                print(f"[model-run] Force: games collected successfully")
            except Exception as e:
                print(f"[model-run] Force: game collection failed — aborting model run: {e}")
                return {'status': 'collect_failed', 'error': str(e), 'date': today_str}
            for sport in get_live_sports():
                stale_pass = Pass.query.filter_by(date=today_str, sport=sport).first()
                if stale_pass and stale_pass.games_analyzed == 0:
                    db.session.delete(stale_pass)
                    db.session.commit()
                    print(f"[model-run] Force: cleared stale pass for {today_str}/{sport}")
        results = {}
        for sport in get_live_sports():
            results[sport] = run_model_and_log(app, sport=sport, force=force, date_override=date_override)
        return results
    return log_cron('run_model', _run, skip_throttle=force)


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
    def _retrain():
        from model import EnsemblePredictor
        results = {}
        for sport in get_live_sports():
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
            model.train()
            model.save()
            results[sport] = {
                'status': 'retrained',
                'previous_age_days': age,
            }
        return results
    return log_cron('retrain_model', _retrain, skip_throttle=force)


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
    conn = sqlite3.connect(get_sqlite_path())
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
            domains = os.environ.get('REPLIT_DOMAINS', 'localhost:5000')
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
    """Verify email from link click — activates trial via Stripe card-on-file checkout"""
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
            domains = os.environ.get('REPLIT_DOMAINS', 'localhost:5000')
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

@app.route('/api/auth/logout', methods=['POST'])
def logout():
    """Logout current user"""
    session.pop('user_id', None)
    logout_user()
    return jsonify({'success': True, 'message': 'Logged out'})


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
        domains = os.environ.get('REPLIT_DOMAINS', 'localhost:5000')
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
                price_id = monthly_prices[0].id
            elif plan in ('founding', 'annual_founding') and yearly_prices:
                founding = [p for p in yearly_prices if p.unit_amount == 9900]
                price_id = founding[0].id if founding else yearly_prices[0].id
            elif plan in ('annual', 'annual_standard') and yearly_prices:
                standard = [p for p in yearly_prices if p.unit_amount == 14900]
                price_id = standard[0].id if standard else yearly_prices[-1].id
            elif prices.data:
                price_id = prices.data[0].id

        if not price_id:
            return jsonify({'error': 'No prices configured in Stripe'}), 400

        app_domain = os.environ.get('APP_DOMAIN', '')
        if not app_domain:
            domains = os.environ.get('REPLIT_DOMAINS', 'localhost:5000')
            app_domain = domains.split(',')[0]
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
        }

        if is_trial_eligible:
            checkout_params['subscription_data']['trial_period_days'] = 14

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
        subs = stripe.Subscription.list(customer=db_user.stripe_customer_id, status='active', limit=1)
        if subs.data:
            stripe.Subscription.modify(subs.data[0].id, cancel_at_period_end=True)
            db_user.subscription_status = 'cancelling'
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
    from stripe_client import get_stripe_client
    get_stripe_client()

    payload = request.data
    sig = request.headers.get('Stripe-Signature')
    webhook_secret = os.getenv('STRIPE_WEBHOOK_SECRET')

    is_production = os.environ.get('REPLIT_DEPLOYMENT') == '1'

    try:
        if webhook_secret and sig:
            event = stripe_lib.Webhook.construct_event(payload, sig, webhook_secret)
        elif not is_production:
            import json
            event = json.loads(payload)
        else:
            return jsonify({'error': 'Webhook signature required in production'}), 400

        event_id = event.get('id', '')
        event_type = event.get('type', '')
        data_obj = event.get('data', {}).get('object', {})
        logging.info(f'Stripe webhook: {event_type} (event_id={event_id})')

        if event_id:
            try:
                db.session.add(ProcessedEvent(id=event_id, event_type=event_type))
                db.session.flush()
            except Exception:
                db.session.rollback()
                logging.info(f'Skipping duplicate webhook event: {event_id}')
                return jsonify({'success': True, 'duplicate': True}), 200

        if event_type == 'checkout.session.completed':
            user_id = data_obj.get('client_reference_id') or data_obj.get('metadata', {}).get('user_id')
            plan = data_obj.get('metadata', {}).get('plan', 'monthly')
            if user_id:
                user = db.session.get(User, user_id)
                if user:
                    user.subscription_plan = plan
                    user.subscription_start_date = datetime.now()
                    user.stripe_customer_id = data_obj.get('customer')
                    sub_id = data_obj.get('subscription')
                    if sub_id:
                        stripe_obj = get_stripe_client()
                        sub = stripe_obj.Subscription.retrieve(sub_id)
                        sub_status = sub.get('status', 'active')
                        if sub_status == 'trialing':
                            user.subscription_status = 'trial'
                            user.is_premium = True
                            user.trial_used = True
                            user.trial_start_date = datetime.now()
                            trial_end = sub.get('trial_end')
                            if trial_end:
                                user.trial_end_date = datetime.fromtimestamp(trial_end)
                                user.trial_ends = datetime.fromtimestamp(trial_end)
                        else:
                            user.subscription_status = 'active'
                            user.is_premium = True
                        period_end = sub.get('current_period_end')
                        if period_end:
                            user.current_period_end = datetime.fromtimestamp(period_end)
                    else:
                        user.subscription_status = 'active'
                        user.is_premium = True
                    db.session.commit()
                    if plan in ('annual', 'founding', 'annual_founding'):
                        maybe_assign_founding(user_id)

        elif event_type == 'customer.subscription.created':
            # Handle same as updated for new subscriptions
            cust_id = data_obj.get('customer')
            status = data_obj.get('status')
            if cust_id:
                user = User.query.filter_by(stripe_customer_id=cust_id).first()
                if user:
                    plan_meta = data_obj.get('metadata', {}).get('plan')
                    if plan_meta:
                        user.subscription_plan = plan_meta
                    if status == 'active':
                        user.subscription_status = 'active'
                        user.is_premium = True
                    elif status == 'trialing':
                        user.subscription_status = 'trial'
                        user.is_premium = True
                        trial_end = data_obj.get('trial_end')
                        if trial_end:
                            user.trial_end_date = datetime.fromtimestamp(trial_end)
                    period_end = data_obj.get('current_period_end')
                    if period_end:
                        user.current_period_end = datetime.fromtimestamp(period_end)
                    db.session.commit()

        elif event_type == 'customer.subscription.updated':
            cust_id = data_obj.get('customer')
            status = data_obj.get('status')
            if cust_id:
                user = User.query.filter_by(stripe_customer_id=cust_id).first()
                if user:
                    plan_meta = data_obj.get('metadata', {}).get('plan')
                    if plan_meta:
                        user.subscription_plan = plan_meta
                    if status == 'active':
                        user.subscription_status = 'active'
                        user.is_premium = True
                    elif status == 'trialing':
                        user.subscription_status = 'trial'
                        user.is_premium = True
                        trial_end = data_obj.get('trial_end')
                        if trial_end:
                            user.trial_end_date = datetime.fromtimestamp(trial_end)
                    elif status == 'canceled':
                        user.subscription_status = 'cancelled'
                        user.is_premium = False
                    elif status in ('unpaid', 'incomplete_expired'):
                        # Trial ended without payment or payment never completed
                        user.subscription_status = 'expired'
                        user.is_premium = False
                    elif status == 'past_due':
                        user.subscription_status = 'past_due'
                    period_end = data_obj.get('current_period_end')
                    if period_end:
                        user.current_period_end = datetime.fromtimestamp(period_end)
                    db.session.commit()

        elif event_type == 'customer.subscription.deleted':
            cust_id = data_obj.get('customer')
            if cust_id:
                user = User.query.filter_by(stripe_customer_id=cust_id).first()
                if user:
                    user.subscription_status = 'cancelled'
                    user.is_premium = False
                    db.session.commit()
                    logging.info(f'Subscription cancelled for user {user.email}')
                    try:
                        from email_service import send_cancellation_email
                        send_cancellation_email(user.email, user.first_name, user.current_period_end, user.founding_member)
                    except Exception as e:
                        logging.error(f"Cancellation email failed: {e}")

        elif event_type in ('invoice.paid', 'invoice.payment_succeeded'):
            cust_id = data_obj.get('customer')
            if cust_id:
                user = User.query.filter_by(stripe_customer_id=cust_id).first()
                if user:
                    user.subscription_status = 'active'
                    user.is_premium = True
                    lines = data_obj.get('lines', {}).get('data', [])
                    for line in lines:
                        period_end = line.get('period', {}).get('end')
                        if period_end:
                            user.current_period_end = datetime.fromtimestamp(period_end)
                            break
                    db.session.commit()
                    logging.info(f'Invoice paid for user {user.email}')

        elif event_type == 'invoice.payment_failed':
            cust_id = data_obj.get('customer')
            if cust_id:
                user = User.query.filter_by(stripe_customer_id=cust_id).first()
                if user:
                    user.subscription_status = 'past_due'
                    db.session.commit()
                    logging.warning(f'Payment failed for user {user.email}')
                    try:
                        from email_service import send_payment_failed_email
                        send_payment_failed_email(user.email, user.first_name)
                    except Exception as e:
                        logging.error(f"Payment failed email error: {e}")
                    try:
                        send_admin_alert(
                            "Payment Failed",
                            f"Payment failed for {user.email} ({user.subscription_plan})",
                        )
                    except Exception:
                        pass

        db.session.commit()

    except Exception as e:
        db.session.rollback()
        logging.error(f'Webhook error: {e}')
        try:
            send_admin_alert(
                "Stripe Webhook Error",
                f"Webhook processing failed: {str(e)[:200]}",
            )
        except Exception:
            pass
        return jsonify({'error': str(e)}), 400

    return jsonify({'success': True})

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
    """Set user's unit size"""
    from flask import request
    data = request.get_json() or {}
    unit_size = data.get('unit_size', 100)
    test_user.unit_size = unit_size
    return jsonify({'success': True, 'unit_size': unit_size})

@app.route('/api/auth/trial', methods=['POST'])
def start_trial():
    """Start free 14-day trial with just email - no card required"""
    from flask import request
    from datetime import timedelta
    import re
    
    data = request.get_json() or {}
    email = data.get('email', '').strip().lower()
    password = data.get('password', '')
    
    if not email:
        return jsonify({'error': 'Email required'}), 400
    
    if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
        return jsonify({'error': 'Invalid email format'}), 400
    
    user = User.query.filter(func.lower(User.email) == email.lower()).first()
    
    if user:
        if user.trial_used and user.trial_ends and datetime.now() > user.trial_ends:
            return jsonify({
                'success': False,
                'error': 'Trial already used for this email. Subscribe to continue.',
                'trial_expired': True
            }), 400
        
        if user.trial_ends and datetime.now() < user.trial_ends:
            user.is_premium = True
            user.subscription_status = 'trial'
            user.trial_end_date = user.trial_ends
            db.session.commit()
            login_user(user, remember=True)
        
        return jsonify({
            'success': True,
            'user': {
                'id': user.id,
                'email': user.email,
                'is_premium': user.is_premium,
                'subscription_status': 'trial',
                'trial_ends': user.trial_ends.isoformat() if user.trial_ends else None
            }
        })
    
    if not password or len(password) < 6:
        return jsonify({'error': 'Password required (6+ characters)'}), 400
    
    user = User()
    user.email = email
    user.first_name = email.split('@')[0]
    user.set_password(password)
    user.is_premium = True
    user.subscription_status = 'trial'
    user.trial_ends = datetime.now() + timedelta(days=14)
    user.trial_end_date = user.trial_ends
    user.trial_used = True
    
    db.session.add(user)
    db.session.commit()
    login_user(user, remember=True)
    
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
    
    settled = [b for b in bets if b.result]
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
    
    sharp_bets = [b for b in bets if b.source == 'sharp_pick' or (b.source is None and b.pick_id)]
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

    return jsonify({
        'totalProfit': round(total_profit, 2),
        'roi': round(roi, 1),
        'totalBets': len(settled),
        'pendingBets': len(bets) - len(settled),
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
    bets = TrackedBet.query.filter_by(user_id=user.id).order_by(TrackedBet.created_at.desc()).all()
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
            'pick_result': pick_result,
            'source': b.source or 'sharp_pick',
            'follow_type': b.follow_type or 'exact',
            'line_at_bet': b.line_at_bet,
            'odds_at_publish': b.odds_at_publish,
            'bet_type': b.bet_type or 'spread',
            'parlay_legs': b.parlay_legs,
            'created_at': b.created_at.isoformat() if b.created_at else None,
            'linked_pick': pick_detail,
        })
    return jsonify({'bets': bet_list, 'tracked_pick_ids': list(tracked_pick_ids)})

@app.route('/api/bets/trackable', methods=['GET'])
def get_trackable_picks():
    """Get recent picks the user hasn't tracked yet"""
    user = get_current_user_obj()
    if not user:
        return jsonify({'error': 'Login required'}), 401
    already_tracked = db.session.query(TrackedBet.pick_id).filter(
        TrackedBet.user_id == user.id,
        TrackedBet.pick_id.isnot(None)
    ).all()
    tracked_ids = {t[0] for t in already_tracked}

    recent_picks = Pick.query.order_by(Pick.published_at.desc()).limit(30).all()
    trackable = []
    for p in recent_picks:
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
    return jsonify({'picks': trackable})

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

    bet_amount = data.get('bet_amount', 100)
    odds = data.get('odds', -110)

    # Use pick's live market odds when tracking a Sharp Pick (not generic -110)
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

    bet.result = new_result
    bet.profit = profit_val
    db.session.commit()
    
    return jsonify({'success': True})

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
  <p style="font-size:13px;font-weight:800;letter-spacing:0.3em;text-transform:uppercase;color:#FFFFFF;margin:0 0 32px;">
    SHARP<span style="opacity:0.5;margin:0 0.35em;font-weight:500;letter-spacing:0.15em;">||</span>PICKS
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
    db.session.commit()
    logging.info("[FCM] token registered: user=%s platform=%s", user.email, platform)
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


def _get_firebase_credentials_and_project():
    """Get (credentials, project_id) or raise. Tries file-based load first (most reliable), then dict-based."""
    import json
    import tempfile
    import google.auth.transport.requests
    from google.oauth2 import service_account
    from models import FCMToken  # noqa: F401 - for imports

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
        return creds, project_id
    except Exception as e2:
        raise ValueError(
            f"Firebase private key format invalid. Set FIREBASE_PRIVATE_KEY and FIREBASE_CLIENT_EMAIL as separate env vars "
            "(paste PEM with \\n for newlines), or use FIREBASE_SERVICE_ACCOUNT_JSON with full JSON. {e2}"
        ) from e2


def send_push_notification(user_id, title, body, data=None):
    from models import FCMToken

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
        if not token or len(token) < 100:
            logging.warning(f"Skipping invalid FCM token (too short or empty) for user {user_id}")
            continue
        payload = {
            'message': {
                'token': token,
                'notification': {'title': title or ' ', 'body': body or ' '}
            }
        }
        if data:
            payload['message']['data'] = {str(k): str(v) for k, v in data.items()}
        try:
            resp = http_requests.post(url, json=payload, headers=headers, timeout=10)
            if resp.status_code == 200:
                sent += 1
            elif resp.status_code in (404, 410):
                t.enabled = False
                db.session.commit()
                logging.info(f"Disabled stale FCM token for user {user_id}")
            elif resp.status_code == 401:
                err_text = resp.text[:300]
                logging.warning(f"FCM 401 (APNs/credentials): {err_text}")
            else:
                logging.warning(f"FCM send failed ({resp.status_code}): {resp.text[:200]}")
        except Exception as e:
            logging.error(f"FCM send error: {e}")
    return sent


def send_push_to_all(title, body, data=None, premium_only=False, notification_type=None):
    users = User.query.all()
    if premium_only:
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

        total += send_push_notification(u.id, title, body, data)
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

    import sqlite3
    conn = sqlite3.connect(get_sqlite_path())
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


@app.route('/api/admin/stats')
def get_stats():
    user = get_current_user_from_session()
    if not user:
        return jsonify({'error': 'Authentication required'}), 401
    db_user = db.session.get(User, user['id'])
    if not db_user or not db_user.is_superuser:
        return jsonify({'error': 'Unauthorized'}), 403
    conn = get_db()
    cur = conn.cursor()
    
    cur.execute('SELECT COUNT(*) as c FROM games')
    total = cur.fetchone()['c']
    
    cur.execute('SELECT COUNT(*) as c FROM games WHERE spread_result IS NOT NULL')
    with_results = cur.fetchone()['c']
    
    cur.execute('SELECT DISTINCT DATE(game_date) as d FROM games ORDER BY d DESC LIMIT 30')
    dates = [r['d'] for r in cur.fetchall()]
    streak = calculate_streak(dates)
    
    cur.execute("SELECT spread_result, COUNT(*) as c FROM games WHERE spread_result IN ('HOME_COVER', 'AWAY_COVER', 'PUSH') GROUP BY spread_result")
    spread_stats = {r['spread_result']: r['c'] for r in cur.fetchall()}
    home_cover = spread_stats.get('HOME_COVER', 0)
    away_cover = spread_stats.get('AWAY_COVER', 0)
    pushes = spread_stats.get('PUSH', 0)
    total_spreads = home_cover + away_cover + pushes
    
    model_accuracy = 79.5
    model_brier = 0.139
    try:
        import pickle
        with open('calibrated_model.pkl', 'rb') as f:
            model_data = pickle.load(f)
            if 'ensemble_accuracy' in model_data:
                model_accuracy = round(model_data['ensemble_accuracy'] * 100, 1)
            if 'ensemble_brier' in model_data:
                model_brier = round(model_data['ensemble_brier'], 3)
    except:
        pass
    
    conn.close()
    
    return jsonify({
        'gamesCollected': total,
        'gamesWithResults': with_results,
        'collectionStreak': streak,
        'wins': home_cover,
        'losses': away_cover,
        'winRate': round(home_cover/total_spreads*100, 1) if total_spreads > 0 else 0,
        'totalProfit': model_accuracy,
        'roi': model_brier,
        'modelAccuracy': model_accuracy,
        'modelBrier': model_brier,
        'homeCover': home_cover,
        'awayCover': away_cover,
        'pushes': pushes,
        'systemHealth': [
            {'name': 'Data Collection', 'status': 'operational' if streak > 0 else 'warning', 'message': f'{streak} day streak'},
            {'name': 'API Status', 'status': 'operational', 'message': 'All systems operational'},
            {'name': 'Database', 'status': 'operational', 'message': f'{total} games stored'},
            {'name': 'Model', 'status': 'operational', 'message': f'{model_accuracy}% accuracy'}
        ]
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

@app.route('/<path:path>')
def serve_spa(path):
    dist_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'dist')
    full_path = os.path.join(dist_dir, path)
    if os.path.isfile(full_path):
        from flask import send_from_directory, make_response
        resp = make_response(send_from_directory(dist_dir, path))
        if path.startswith('assets/'):
            resp.headers['Cache-Control'] = 'public, max-age=31536000, immutable'
        else:
            resp.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        return resp
    index_path = os.path.join(dist_dir, 'index.html')
    if os.path.isfile(index_path):
        from flask import send_from_directory, make_response
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
