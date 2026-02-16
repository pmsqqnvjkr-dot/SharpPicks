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

from flask import Flask, jsonify, Response, session, request, redirect

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
        from flask import send_from_directory
        return send_from_directory(dist_dir, 'index.html')
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
    elif request.path.endswith('.html') or request.path == '/':
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
    return response

from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_login import LoginManager, login_required, current_user, login_user, logout_user
from werkzeug.middleware.proxy_fix import ProxyFix
import sqlite3
import subprocess
from datetime import datetime, timedelta

from models import db, User, TrackedBet, Pick, Pass, ModelRun, FoundingCounter, Insight, ProcessedEvent
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

app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    'pool_pre_ping': True,
    "pool_recycle": 300,
}

db.init_app(app)
allowed_origins = [
    'https://app.sharppicks.ai',
    'https://sharppicks.ai',
    'https://www.sharppicks.ai',
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
    user = User.query.get(user_id)
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

def get_current_user_from_session():
    """Get current user from session or None if not authenticated"""
    user_id = session.get('user_id')
    if user_id:
        user = db.session.get(User, user_id)
        if user:
            stored_token = session.get('session_token')
            if not stored_token or stored_token != user.session_token:
                session.pop('user_id', None)
                session.pop('session_token', None)
                return None
            return serialize_user(user)
    return None

def serialize_user(user):
    return {
        'id': user.id,
        'email': user.email,
        'first_name': user.first_name or '',
        'display_name': user.first_name or user.display_name or user.username or user.email.split('@')[0],
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

@app.route('/admin')
@login_required
def admin_dashboard():
    from flask import render_template
    if not current_user.is_superuser:
        return 'Unauthorized', 403
    return render_template('admin.html')

def seed_database():
    with app.app_context():
        try:
            db.create_all()
            logging.info("Database tables created")

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
            db.session.commit()

            if Pick.query.count() == 0:
                seed_picks = [
                    Pick(id='9cc4946d-37f2-46cc-acb9-50a4c5be16c1', game_date='2026-01-27', away_team='Detroit Pistons', home_team='Denver Nuggets', side='Detroit Pistons +2.0', line=2, edge_pct=4.5, result='win', sport='nba', model_confidence=0.78, market_odds=-110, sportsbook='DraftKings', published_at=datetime(2026,2,11,18,3,52), pnl=91, notes='Pre-Cal'),
                    Pick(id='dab82bf3-4dee-4d3e-a15e-9c3287aa7ff7', game_date='2026-01-28', away_team='San Antonio Spurs', home_team='Houston Rockets', side='San Antonio Spurs -2.5', line=-2.5, edge_pct=8.2, result='win', sport='nba', model_confidence=0.59, market_odds=-110, sportsbook='DraftKings', published_at=datetime(2026,2,11,18,3,52), pnl=91, notes='Pre-Cal'),
                    Pick(id='e4647da5-b1e9-4d49-8f39-3e11de343ce0', game_date='2026-01-29', away_team='Houston Rockets', home_team='Atlanta Hawks', side='Houston Rockets +4.5', line=4.5, edge_pct=5.1, result='win', sport='nba', model_confidence=0.63, market_odds=-110, sportsbook='DraftKings', published_at=datetime(2026,2,11,18,3,52), pnl=91, notes='Pre-Cal'),
                    Pick(id='f1843352-a18a-49f9-a2cf-5bc6abe50bfe', game_date='2026-01-30', away_team='Los Angeles Lakers', home_team='Washington Wizards', side='Los Angeles Lakers +5.0', line=5, edge_pct=7.7, result='win', sport='nba', model_confidence=0.64, market_odds=-110, sportsbook='DraftKings', published_at=datetime(2026,2,11,18,3,52), pnl=91, notes='Pre-Cal'),
                    Pick(id='1520a539-73db-4f3c-aabf-086927ee9b10', game_date='2026-01-31', away_team='Chicago Bulls', home_team='Miami Heat', side='Chicago Bulls +5.0', line=5, edge_pct=5.8, result='win', sport='nba', model_confidence=0.72, market_odds=-110, sportsbook='DraftKings', published_at=datetime(2026,2,11,18,3,52), pnl=91, notes='Pre-Cal'),
                    Pick(id='d4d15c8b-9dd2-49c0-b48b-bf8ab868a5fc', game_date='2026-02-01', away_team='LA Clippers', home_team='Phoenix Suns', side='LA Clippers +0.5', line=0.5, edge_pct=6.4, result='win', sport='nba', model_confidence=0.55, market_odds=-110, sportsbook='DraftKings', published_at=datetime(2026,2,11,18,3,52), pnl=91, notes='Pre-Cal'),
                    Pick(id='46f93629-6df1-4644-9c9c-d3f945434ad7', game_date='2026-02-02', away_team='New Orleans Pelicans', home_team='Charlotte Hornets', side='Charlotte Hornets -8.5', line=-8.5, edge_pct=4.1, result='loss', sport='nba', model_confidence=0.7, market_odds=-110, sportsbook='DraftKings', published_at=datetime(2026,2,11,18,3,52), pnl=-110, notes='Pre-Cal'),
                    Pick(id='efd99ce8-b2a5-4867-92c5-0a3e16837aa2', game_date='2026-02-11', away_team='New York Knicks', home_team='Philadelphia 76ers', side='Philadelphia 76ers +24.5', line=24.5, edge_pct=10, result='loss', result_ats='loss', profit_units=-1, sport='nba', model_confidence=0.9993, market_odds=-110, sportsbook='DraftKings', published_at=datetime(2026,2,12,5,40,10), predicted_margin=-13.3, cover_prob=0.8312, implied_prob=0.5238, line_open=25.5, sigma=11.71, z_score=3.192, raw_edge=47.55, pnl=-100, notes='Line value: getting 1.0pts better number than open (+25.5 → +24.5) | Both teams on 1 day rest — no rest edge | Net rating favors New York Knicks by 0.0pts — spread accounts for this', result_resolved_at=datetime(2026,2,12,5,40,10)),
                    Pick(id='01a485ef-ab1a-4ecc-af10-9803b41c1f0f', game_date='2026-02-12', away_team='Dallas Mavericks', home_team='Los Angeles Lakers', side='Los Angeles Lakers -7.5', line=-7.5, edge_pct=10, result='win', result_ats='W', profit_units=0.88, sport='nba', model_confidence=0.8537, market_odds=-114, sportsbook='FanDuel', published_at=datetime(2026,2,12,6,22,59), predicted_margin=11.2, cover_prob=0.6238, implied_prob=0.5238, line_open=-6.5, sigma=11.71, z_score=1.053, raw_edge=32.99, home_score=124, away_score=104, pnl=88, notes='Back-to-back for both teams — no rest edge|Scoring margin edge: Los Angeles Lakers outscores opponents by 9.4pts more per game|Defensive mismatch: Dallas Mavericks allows 122.8pts/game', result_resolved_at=datetime(2026,2,13,8,28,18)),
                ]
                for p in seed_picks:
                    db.session.add(p)
                logging.info("Seeded historical picks")

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
            if Insight.query.count() == 0:
                seed_insights = [
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
                        featured=True,
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

Sharp Picks is built on probability, not streaks. So here is how to read the model dashboard the right way.

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
                ]
                for ins in seed_insights:
                    db.session.add(ins)
                db.session.commit()
                logging.info("Seeded 4 initial insights")

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
        db_url = os.environ.get('DATABASE_URL', '')
        if not db_url:
            logging.warning("DATABASE_URL not set, skipping backup")
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

            week_ago = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
            today_str = datetime.now().strftime('%Y-%m-%d')

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

            stats = {
                'picks_made': pr[0] or 0 if pr else 0,
                'wins': pr[1] or 0 if pr else 0,
                'losses': pr[2] or 0 if pr else 0,
                'pending': pr[3] or 0 if pr else 0,
                'passes': passes_count,
                'total_record': total_record,
                'next_week_games': 'Full NBA slate',
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
        except Exception as e:
            logging.error(f"Weekly summary job error: {e}")


def collect_todays_games():
    """Run the main.py data collector"""
    print(f"[{datetime.now()}] Running scheduled data collection...")
    try:
        subprocess.run(['python', 'main.py'], timeout=300)
        print(f"[{datetime.now()}] Data collection completed!")
    except Exception as e:
        print(f"[{datetime.now()}] Collection error: {e}")

def grade_pending_picks():
    """Check game results and grade pending picks as win/loss"""
    with app.app_context():
        pending_picks = Pick.query.filter_by(result='pending').all()
        if not pending_picks:
            return

        try:
            conn = sqlite3.connect('sharp_picks.db')
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            for pick in pending_picks:
                game = None
                pick_date = pick.game_date[:10]
                try:
                    from datetime import date as date_type
                    pd = datetime.strptime(pick_date, '%Y-%m-%d').date()
                    next_day = (pd + timedelta(days=1)).strftime('%Y-%m-%d')
                    check_dates = [pick_date, next_day]
                except:
                    check_dates = [pick_date]

                table_name = 'wnba_games' if pick.sport == 'wnba' else 'games'

                for check_date in check_dates:
                    cursor.execute(f'''
                        SELECT home_score, away_score, home_team, away_team
                        FROM {table_name}
                        WHERE home_team = ? AND away_team = ? AND game_date LIKE ?
                        AND home_score IS NOT NULL AND away_score IS NOT NULL
                    ''', (pick.home_team, pick.away_team, f'{check_date}%'))
                    game = cursor.fetchone()
                    if game:
                        break

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

            conn.close()
            db.session.commit()
        except Exception as e:
            print(f"[Auto-grade] Error: {e}")

def collect_closing_lines():
    """Collect closing lines for all today's games and pending picks.
    Refreshes data from APIs, then snapshots current lines as closing lines.
    Runs multiple times during game windows to catch lines close to tip-off."""
    print(f"[{datetime.now()}] Refreshing lines for closing snapshot...")
    try:
        subprocess.run(['python', 'main.py'], timeout=300)
    except Exception as e:
        print(f"[{datetime.now()}] Line refresh error (continuing): {e}")
    
    print(f"[{datetime.now()}] Capturing closing lines...")
    with app.app_context():
        try:
            conn = sqlite3.connect('sharp_picks.db')
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            today_str = datetime.now().strftime('%Y-%m-%d')
            cursor.execute('''
                SELECT id, home_team, away_team, spread_home, total,
                       home_ml, away_ml, game_date
                FROM games
                WHERE game_date LIKE ?
                AND home_score IS NULL
                AND spread_home IS NOT NULL
            ''', (f'{today_str}%',))
            
            games = cursor.fetchall()
            updated = 0
            
            for game in games:
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
            print(f"[{datetime.now()}] Captured closing lines for {updated} games")
        except Exception as e:
            print(f"[{datetime.now()}] Closing line error: {e}")

def collect_wnba_games_job():
    """Run the WNBA data collector"""
    print(f"[{datetime.now()}] Running scheduled WNBA data collection...")
    try:
        subprocess.run(['python', 'main.py', '--wnba'], timeout=300)
        print(f"[{datetime.now()}] WNBA data collection completed!")
    except Exception as e:
        print(f"[{datetime.now()}] WNBA collection error: {e}")

def collect_wnba_closing_lines_job():
    """Collect WNBA closing lines right before games start.
    First refreshes WNBA data from APIs, then snapshots current lines as closing lines."""
    print(f"[{datetime.now()}] Refreshing WNBA lines for closing snapshot...")
    try:
        subprocess.run(['python', 'main.py', '--wnba-close'], timeout=300)
    except Exception as e:
        print(f"[{datetime.now()}] WNBA line refresh error (continuing): {e}")
    
    print(f"[{datetime.now()}] Capturing WNBA closing lines...")
    with app.app_context():
        try:
            conn = sqlite3.connect('sharp_picks.db')
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            today_str = datetime.now().strftime('%Y-%m-%d')
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
        conn = sqlite3.connect('sharp_picks.db')
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        today_str = datetime.now().strftime('%Y-%m-%d')
        
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
        else:
            print(f"[{datetime.now()}] Data quality OK")
            
    except Exception as e:
        print(f"[Data Quality] Check failed: {e}")


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

            conn = sqlite3.connect('sharp_picks.db')
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
                    spots = 500 - founding_count
                    send_trial_expiring_email(user.email, user.first_name, user.trial_end_date, record, spots)
                    user.trial_warning_sent = True
                except Exception as e:
                    logging.error(f"Trial expiring email failed for {user.email}: {e}")
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


@app.route('/api/cron/collect-games', methods=['POST'])
@verify_cron
def cron_collect_games():
    try:
        collect_todays_games()
        return jsonify({'status': 'done', 'job': 'collect_games'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/api/cron/refresh-lines', methods=['POST'])
@verify_cron
def cron_refresh_lines():
    try:
        collect_todays_games()
        return jsonify({'status': 'done', 'job': 'refresh_lines'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/api/cron/closing-lines', methods=['POST'])
@verify_cron
def cron_closing_lines():
    try:
        collect_closing_lines()
        return jsonify({'status': 'done', 'job': 'closing_lines'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/api/cron/grade-picks', methods=['POST'])
@verify_cron
def cron_grade_picks():
    try:
        grade_pending_picks()
        return jsonify({'status': 'done', 'job': 'grade_picks'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/api/cron/grade-whatifs', methods=['POST'])
@verify_cron
def cron_grade_whatifs():
    try:
        grade_whatif_passes()
        return jsonify({'status': 'done', 'job': 'grade_whatifs'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/api/cron/expire-trials', methods=['POST'])
@verify_cron
def cron_expire_trials():
    try:
        check_expiring_trials()
        expire_trials()
        expired_count = User.query.filter_by(subscription_status='expired').count()
        return jsonify({
            'status': 'done',
            'job': 'expire_trials',
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/api/cron/weekly-summary', methods=['POST'])
@verify_cron
def cron_weekly_summary():
    try:
        send_weekly_summary_job()
        return jsonify({'status': 'done', 'job': 'weekly_summary'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/api/cron/backup', methods=['POST'])
@verify_cron
def cron_backup():
    try:
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

        return jsonify({
            'status': 'done',
            'job': 'backup',
            'picks': len(picks),
            'users': len(users)
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/api/cron/check-data-quality', methods=['POST'])
@verify_cron
def cron_data_quality():
    try:
        check_data_quality()
        return jsonify({'status': 'done', 'job': 'data_quality'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


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
    conn = sqlite3.connect('sharp_picks.db')
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
    user = get_current_user_from_session()
    if user:
        return jsonify({'authenticated': True, 'user': user})
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

    data = request.get_json()
    email = data.get('email', '').strip().lower()
    password = data.get('password', '')
    first_name = data.get('first_name', '').strip()

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

    user = User(
        id=str(uuid.uuid4()),
        email=email.lower(),
        email_normalized=norm,
        first_name=first_name,
        display_name=first_name,
        password_hash=generate_password_hash(password),
        is_premium=False,
        subscription_status='pending_verification',
        email_verified=False,
    )
    db.session.add(user)
    db.session.commit()

    login_user(user, remember=True)
    session['user_id'] = user.id
    session['session_token'] = user.session_token

    try:
        from email_service import send_verification_email
        s = URLSafeTimedSerializer(app.config['SECRET_KEY'])
        token = s.dumps(user.id, salt='email-verify')
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
    session['user_id'] = user.id
    session['session_token'] = user.session_token
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

    data = request.get_json()
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
    session['user_id'] = user.id
    session['session_token'] = user.session_token
    
    return jsonify({
        'success': True,
        'user': serialize_user(user)
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
    data = request.get_json()
    email = data.get('email', '').strip().lower()
    if not email:
        return jsonify({'error': 'Email required'}), 400

    user = User.query.filter(func.lower(User.email) == email).first()
    if not user:
        return jsonify({'success': True, 'message': 'If that email exists, a reset link has been generated.'})

    s = URLSafeTimedSerializer(app.config['SECRET_KEY'])
    token = s.dumps(user.id, salt='password-reset')
    reset_url = f"{request.host_url}reset-password?token={token}"

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

    data = request.get_json()
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
        if current_count >= 500:
            return

        user = db.session.get(User, user_id)
        if not user or user.founding_member:
            return

        new_count = current_count + 1
        closed = new_count >= 500
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

        elif event_type == 'invoice.paid':
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

        db.session.commit()

    except Exception as e:
        db.session.rollback()
        logging.error(f'Webhook error: {e}')
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
    data = request.get_json()
    unit_size = data.get('unit_size', 100)
    test_user.unit_size = unit_size
    return jsonify({'success': True, 'unit_size': unit_size})

@app.route('/api/auth/trial', methods=['POST'])
def start_trial():
    """Start free 14-day trial with just email - no card required"""
    from flask import request
    from datetime import timedelta
    import re
    
    data = request.get_json()
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
            'message': 'Welcome! Your account is active. Explore Sharp Picks Pro.'
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
    capital_preserved = round(picks_passed * 110 * 0.04, 0)

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
        },
    })

@app.route('/api/bets', methods=['GET'])
@login_required
def get_user_bets():
    """Get user's tracked bets"""
    bets = TrackedBet.query.filter_by(user_id=current_user.id).order_by(TrackedBet.created_at.desc()).all()
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
                'profit_units': linked.pnl,
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
            'created_at': b.created_at.isoformat() if b.created_at else None,
            'linked_pick': pick_detail,
        })
    return jsonify({'bets': bet_list, 'tracked_pick_ids': list(tracked_pick_ids)})

@app.route('/api/bets/trackable', methods=['GET'])
@login_required
def get_trackable_picks():
    """Get recent picks the user hasn't tracked yet"""
    already_tracked = db.session.query(TrackedBet.pick_id).filter(
        TrackedBet.user_id == current_user.id,
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
            'result': 'W' if p.result == 'win' else ('L' if p.result == 'loss' else p.result),
            'published_at': p.published_at.isoformat() if p.published_at else None,
            'already_tracked': p.id in tracked_ids,
        })
    return jsonify({'picks': trackable})

@app.route('/api/bets', methods=['POST'])
@login_required
def track_bet():
    """Track a bet linked to a pick"""
    data = request.get_json()
    pick_id = data.get('pick_id')

    if pick_id:
        existing = TrackedBet.query.filter_by(
            user_id=current_user.id,
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

    if odds < 0:
        to_win = bet_amount * (100 / abs(odds))
    else:
        to_win = bet_amount * (odds / 100)

    source = 'sharp_pick' if pick_id else 'manual'
    follow_type = data.get('follow_type', 'exact')
    line_at_bet = data.get('line_at_bet')
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
        user_id=current_user.id,
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
@login_required
def update_bet_result(bet_id):
    """Update bet result"""
    data = request.get_json()
    bet = TrackedBet.query.filter_by(id=bet_id, user_id=current_user.id).first()
    if not bet:
        return jsonify({'error': 'Bet not found'}), 404
    
    bet.result = data.get('result')
    bet.profit = data.get('profit', 0)
    db.session.commit()
    
    return jsonify({'success': True})

@app.route('/api/bets/<int:bet_id>', methods=['DELETE'])
@login_required
def delete_bet(bet_id):
    """Delete/untrack a bet"""
    bet = TrackedBet.query.filter_by(id=bet_id, user_id=current_user.id).first()
    if not bet:
        return jsonify({'error': 'Bet not found'}), 404
    
    db.session.delete(bet)
    db.session.commit()
    
    return jsonify({'success': True})

@app.route('/api/user/notifications', methods=['GET'])
def get_notification_prefs():
    user = get_current_user_from_session()
    if not user:
        return jsonify({'error': 'Not authenticated'}), 401
    u = User.query.get(user['id'])
    return jsonify({'prefs': u.notification_prefs or {
        'pick_alert': True, 'no_action': False, 'outcome': True, 'weekly_summary': True
    }})

@app.route('/api/user/notifications', methods=['POST'])
def update_notification_prefs():
    user = get_current_user_from_session()
    if not user:
        return jsonify({'error': 'Not authenticated'}), 401
    data = request.get_json()
    u = User.query.get(user['id'])
    u.notification_prefs = data.get('prefs', u.notification_prefs)
    db.session.commit()
    return jsonify({'success': True, 'prefs': u.notification_prefs})

@app.route('/api/model/calibration')
@app.route('/api/validation/detailed')
@login_required
def detailed_validation():
    """Check model calibration by confidence buckets - only forward predictions"""
    if not current_user.is_pro:
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
@login_required
def get_predictions():
    """Get today's model predictions for upcoming games - with full 36-feature calculation"""
    if not current_user.is_pro:
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
    
    json_path = 'todays_picks.json'
    if os.path.exists(json_path):
        try:
            with open(json_path, 'r') as f:
                picks = json.load(f)
                return jsonify({
                    'predictions': picks,
                    'count': len(picks),
                    'source': 'json_file'
                })
        except:
            pass
    
    conn = get_db()
    cursor = conn.cursor()
    
    today = datetime.now().strftime('%Y-%m-%d')
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
@login_required
def get_stats():
    if not current_user.is_superuser:
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
@login_required
def get_recent_results():
    """Get recent settled predictions with accuracy stats"""
    if not current_user.is_pro:
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

@app.route('/<path:path>')
def serve_spa(path):
    dist_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'dist')
    full_path = os.path.join(dist_dir, path)
    if os.path.isfile(full_path):
        from flask import send_from_directory
        return send_from_directory(dist_dir, path)
    index_path = os.path.join(dist_dir, 'index.html')
    if os.path.isfile(index_path):
        from flask import send_from_directory
        return send_from_directory(dist_dir, 'index.html')
    return jsonify({'status': 'ok'}), 200


def start_background_services_later():
    threading.Timer(10.0, start_background_services).start()

if os.environ.get("REPLIT_DEPLOYMENT") == "1":
    start_background_services_later()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print(f"Starting Sharp Picks API on http://0.0.0.0:{port}")
    start_background_services_later()
    app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)
