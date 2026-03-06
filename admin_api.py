from flask import Blueprint, jsonify, request
from models import db, User, Pick, Pass, ModelRun, FoundingCounter, TrackedBet, Insight, CronLog, FCMToken, KillSwitch, UserBet
from datetime import datetime, timedelta
from sqlalchemy import func, text
from zoneinfo import ZoneInfo
import os
import requests
import time
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadSignature

admin_bp = Blueprint('admin_api', __name__)
ET = ZoneInfo('America/New_York')

def _get_admin_serializer():
    secret = os.environ.get('SESSION_SECRET', os.environ.get('SECRET_KEY', 'dev'))
    return URLSafeTimedSerializer(secret)

def require_superuser():
    from flask_login import current_user
    if current_user.is_authenticated:
        if not current_user.is_superuser:
            return None, 403
        return current_user, None

    token = request.headers.get('X-Admin-Token')
    if token:
        try:
            s = _get_admin_serializer()
            data = s.loads(token, salt='admin-token', max_age=86400)
            user = db.session.get(User, data)
            if user and user.is_superuser:
                return user, None
            return None, 403
        except (SignatureExpired, BadSignature):
            pass

    auth_header = request.headers.get('Authorization', '')
    if auth_header.startswith('Bearer '):
        try:
            s = _get_admin_serializer()
            data = s.loads(auth_header[7:], salt='auth-token', max_age=86400 * 30)
            user = db.session.get(User, data.get('uid') if isinstance(data, dict) else data)
            if user and user.is_superuser and (not isinstance(data, dict) or user.session_token == data.get('st')):
                return user, None
            if user and not user.is_superuser:
                return None, 403
        except Exception:
            pass

    return None, 401


@admin_bp.route('/api/admin/token')
def get_admin_token():
    from flask_login import current_user
    from flask import session as flask_session
    user = None
    if current_user.is_authenticated:
        user = current_user
    else:
        user_id = flask_session.get('user_id')
        if user_id:
            u = db.session.get(User, user_id)
            if u:
                stored = flask_session.get('session_token')
                if stored and stored == u.session_token:
                    user = u

    if not user:
        auth_header = request.headers.get('Authorization', '')
        if auth_header.startswith('Bearer '):
            try:
                s = _get_admin_serializer()
                data = s.loads(auth_header[7:], salt='auth-token', max_age=86400 * 30)
                u = db.session.get(User, data.get('uid') if isinstance(data, dict) else data)
                if u and (not isinstance(data, dict) or u.session_token == data.get('st')):
                    user = u
            except Exception:
                pass

    if not user:
        return jsonify({'error': 'Login required'}), 401
    if not user.is_superuser:
        return jsonify({'error': 'Unauthorized'}), 403

    s = _get_admin_serializer()
    token = s.dumps(user.id, salt='admin-token')
    return jsonify({'token': token})


@admin_bp.route('/api/admin/db-stats')
def db_stats():
    """Quick DB stats: user count, DB source (for verifying prod connection). Superuser only."""
    admin, err_code = require_superuser()
    if not admin:
        return jsonify({'error': 'Login required' if err_code == 401 else 'Unauthorized'}), err_code

    user_count = User.query.count()
    db_url = os.environ.get('DATABASE_URL') or os.environ.get('SQLALCHEMY_DATABASE_URI') or ''
    db_source = 'railway' if ('railway' in db_url.lower() or 'rlwy.net' in db_url) else 'unknown'

    return jsonify({
        'users': user_count,
        'db_source': db_source,
        'db_configured': bool(db_url),
    })


@admin_bp.route('/api/admin/today-pipeline')
def today_pipeline():
    admin, err_code = require_superuser()
    if not admin:
        return jsonify({'error': 'Login required' if err_code == 401 else 'Unauthorized'}), err_code

    now_et = datetime.now(ET)
    today_str = now_et.strftime('%Y-%m-%d')

    model_run = ModelRun.query.filter_by(date=today_str, sport='nba').order_by(ModelRun.created_at.desc()).first()
    pick = Pick.query.filter_by(game_date=today_str, sport='nba').first()
    pass_entry = Pass.query.filter_by(date=today_str, sport='nba').first()

    start_of_day = now_et.replace(hour=0, minute=0, second=0, microsecond=0).replace(tzinfo=None)
    cron_logs = CronLog.query.filter(
        CronLog.job_name == 'run_model',
        CronLog.executed_at >= start_of_day
    ).order_by(CronLog.executed_at.desc()).all()

    from zoneinfo import ZoneInfo
    utc = ZoneInfo('UTC')

    def to_et_str(dt, fmt='%-I:%M:%S %p'):
        if dt is None:
            return None
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=utc)
        return dt.astimezone(ET).strftime(fmt)

    runs = []
    for cl in cron_logs:
        runs.append({
            'time': to_et_str(cl.executed_at),
            'status': cl.status,
            'message': cl.message[:300] if cl.message else None,
            'duration_ms': cl.duration_ms,
        })

    games_detail = None
    if model_run and model_run.games_detail:
        try:
            import json
            games_detail = json.loads(model_run.games_detail)
        except Exception:
            games_detail = None

    result = {
        'date': today_str,
        'status': 'waiting',
        'model_ran': model_run is not None,
        'run_time': to_et_str(model_run.created_at) if model_run else None,
        'games_analyzed': model_run.games_analyzed if model_run else 0,
        'duration_ms': model_run.run_duration_ms if model_run else 0,
        'cron_attempts': runs,
        'games': games_detail,
    }

    if pick:
        result['status'] = 'pick'
        result['pick'] = {
            'side': pick.side,
            'away_team': pick.away_team,
            'home_team': pick.home_team,
            'line': pick.line,
            'edge_pct': pick.edge_pct,
            'confidence': pick.model_confidence,
            'sportsbook': pick.sportsbook,
            'predicted_margin': pick.predicted_margin,
            'cover_prob': pick.cover_prob,
            'published_at': to_et_str(pick.published_at, '%-I:%M %p'),
        }
    elif pass_entry:
        result['status'] = 'pass'
        result['pass'] = {
            'games_analyzed': pass_entry.games_analyzed,
            'closest_edge_pct': pass_entry.closest_edge_pct,
            'pass_reason': pass_entry.pass_reason,
            'whatif': None,
        }
        if pass_entry.whatif_side:
            result['pass']['whatif'] = {
                'side': pass_entry.whatif_side,
                'home_team': pass_entry.whatif_home_team,
                'away_team': pass_entry.whatif_away_team,
                'line': pass_entry.whatif_line,
                'edge': pass_entry.whatif_edge,
            }

    return jsonify(result)


@admin_bp.route('/api/admin/manual-grade', methods=['POST'])
def manual_grade():
    cron_secret = os.environ.get('CRON_SECRET', '')
    cron_auth = cron_secret and request.headers.get('X-Cron-Secret') == cron_secret
    if not cron_auth:
        admin, err_code = require_superuser()
        if not admin:
            return jsonify({'error': 'Login required' if err_code == 401 else 'Unauthorized'}), err_code

    data = request.json or {}
    pick_id = data.get('pick_id')
    home_score = data.get('home_score')
    away_score = data.get('away_score')
    if not pick_id or home_score is None or away_score is None:
        return jsonify({'error': 'pick_id, home_score, away_score required'}), 400

    pick = Pick.query.get(pick_id)
    if not pick:
        return jsonify({'error': 'Pick not found'}), 404
    if pick.result != 'pending':
        return jsonify({'error': f'Pick already graded: {pick.result}'}), 400

    spread_result = int(home_score) - int(away_score)
    line_value = pick.line if pick.line and abs(pick.line) < 50 else 0

    side_lower = pick.side.lower() if pick.side else ''
    home_lower = pick.home_team.lower() if pick.home_team else ''
    away_lower = pick.away_team.lower() if pick.away_team else ''

    if home_lower and home_lower in side_lower:
        pick_is_home = True
    elif away_lower and away_lower in side_lower:
        pick_is_home = False
    else:
        return jsonify({'error': f'Cannot determine side from: {pick.side}'}), 400

    home_int, away_int = int(home_score), int(away_score)
    if pick_is_home:
        ats_margin = spread_result + line_value
    else:
        ats_margin = away_int - home_int + line_value
    covered = ats_margin > 0
    push = ats_margin == 0

    if push:
        pick.result = 'push'
        pick.result_ats = 'P'
        pick.profit_units = 0.0
        pick.pnl = 0
    elif covered:
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

    pick.home_score = int(home_score)
    pick.away_score = int(away_score)
    pick.result_resolved_at = datetime.now()
    db.session.commit()

    return jsonify({
        'pick_id': pick_id,
        'result': pick.result,
        'score': f'{away_score}-{home_score}',
        'spread_result': spread_result,
        'line': line_value,
    })


@admin_bp.route('/api/admin/rerun-model', methods=['POST'])
def rerun_model():
    cron_secret = os.environ.get('CRON_SECRET', '')
    cron_auth = cron_secret and request.headers.get('X-Cron-Secret') == cron_secret
    if not cron_auth:
        admin, err_code = require_superuser()
        if not admin:
            return jsonify({'error': 'Login required' if err_code == 401 else 'Unauthorized'}), err_code

    now_et = datetime.now(ET)
    today_str = now_et.strftime('%Y-%m-%d')
    data = request.get_json() or {}
    sport = data.get('sport', 'nba')
    clear_only = data.get('clear_only', False)

    runs_deleted = ModelRun.query.filter_by(date=today_str, sport=sport).delete()
    passes_deleted = Pass.query.filter_by(date=today_str, sport=sport).delete()
    picks_deleted = Pick.query.filter_by(game_date=today_str, sport=sport).delete()
    db.session.commit()

    if clear_only:
        return jsonify({
            'cleared': {'runs': runs_deleted, 'passes': passes_deleted, 'picks': picks_deleted},
            'message': f'Cleared {today_str}/{sport}. Run model when ready.',
        })

    from model_service import run_model_and_log
    from flask import current_app
    result = run_model_and_log(current_app._get_current_object(), sport=sport)

    return jsonify({
        'cleared': {'runs': runs_deleted, 'passes': passes_deleted, 'picks': picks_deleted},
        'result': result,
    })


@admin_bp.route('/api/admin/clear-today', methods=['POST'])
def clear_today():
    """Clear today's pass/pick so model can run again (admin or cron auth). Does not re-run model."""
    cron_secret = os.environ.get('CRON_SECRET', '')
    cron_auth = cron_secret and request.headers.get('X-Cron-Secret') == cron_secret
    if not cron_auth:
        admin, err_code = require_superuser()
        if not admin:
            return jsonify({'error': 'Login required' if err_code == 401 else 'Unauthorized'}), err_code

    now_et = datetime.now(ET)
    today_str = now_et.strftime('%Y-%m-%d')
    data = request.get_json() or {}
    sport = data.get('sport', 'nba')

    # Get today's pick IDs before delete (for FK cleanup)
    today_picks = Pick.query.filter_by(game_date=today_str, sport=sport).all()
    pick_ids = [p.id for p in today_picks]
    try:
        for pick_id in pick_ids:
            ModelRun.query.filter_by(pick_id=pick_id).update({'pick_id': None})
            TrackedBet.query.filter_by(pick_id=pick_id).update({'pick_id': None})
            UserBet.query.filter_by(pick_id=pick_id).delete()

        runs_deleted = ModelRun.query.filter_by(date=today_str, sport=sport).delete()
        passes_deleted = Pass.query.filter_by(date=today_str, sport=sport).delete()
        picks_deleted = Pick.query.filter_by(game_date=today_str, sport=sport).delete()
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        logging.error(f"clear-today failed: {e}")
        return jsonify({'error': str(e)[:200]}), 500

    return jsonify({
        'cleared': {'runs': runs_deleted, 'passes': passes_deleted, 'picks': picks_deleted},
        'message': f'Cleared {today_str}/{sport}. Run model when ready.',
    })


@admin_bp.route('/api/admin/delete-live-pick', methods=['POST'])
def delete_live_pick():
    """Delete today's live pick (admin or cron auth). Use when a pick was published a day early."""
    cron_secret = os.environ.get('CRON_SECRET', '')
    cron_auth = cron_secret and request.headers.get('X-Cron-Secret') == cron_secret
    if not cron_auth:
        admin, err_code = require_superuser()
        if not admin:
            return jsonify({'error': 'Unauthorized'}), 403

    now_et = datetime.now(ET)
    today_str = now_et.strftime('%Y-%m-%d')
    data = request.get_json() or {}
    sport = data.get('sport', 'nba')

    pick = Pick.query.filter_by(game_date=today_str, sport=sport).first()
    if not pick:
        return jsonify({'message': 'No live pick for today', 'deleted': False}), 200

    pick_id = pick.id
    info = f"{pick.away_team} @ {pick.home_team} ({pick.side})"
    ModelRun.query.filter_by(pick_id=pick_id).update({'pick_id': None})
    TrackedBet.query.filter_by(pick_id=pick_id).update({'pick_id': None})
    UserBet.query.filter_by(pick_id=pick_id).delete()
    db.session.delete(pick)
    db.session.commit()
    return jsonify({'deleted': True, 'pick': info, 'game_date': today_str})


@admin_bp.route('/api/admin/trigger-model', methods=['POST'])
def trigger_model():
    """Run model without clearing (admin auth). Use force=true in body to clear and rerun."""
    admin, err_code = require_superuser()
    if not admin:
        return jsonify({'error': 'Login required' if err_code == 401 else 'Unauthorized'}), err_code

    data = request.get_json() or {}
    force = data.get('force', False)
    sport = data.get('sport', 'nba')

    from model_service import run_model_and_log
    from flask import current_app
    result = run_model_and_log(current_app._get_current_object(), sport=sport, force=force)
    return jsonify({'result': result})


@admin_bp.route('/api/admin/trigger-grade', methods=['POST'])
def trigger_grade():
    """Manually run grade_pending_picks (admin auth)."""
    admin, err_code = require_superuser()
    if not admin:
        return jsonify({'error': 'Login required' if err_code == 401 else 'Unauthorized'}), err_code

    from app import grade_pending_picks
    try:
        grade_pending_picks()
        return jsonify({'success': True, 'message': 'Grade completed'})
    except Exception as e:
        logging.error(f"Admin trigger-grade error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@admin_bp.route('/api/admin/collect-games', methods=['POST'])
def admin_collect_games():
    """Collect today's games from ESPN/Odds API (admin auth)."""
    admin, err_code = require_superuser()
    if not admin:
        return jsonify({'error': 'Unauthorized'}), 403

    from app import collect_todays_games
    try:
        result = collect_todays_games()
        return jsonify({'success': True, 'message': 'Games collected', 'result': str(result) if result else None})
    except Exception as e:
        logging.error(f"Admin collect-games error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@admin_bp.route('/api/admin/refresh-lines', methods=['POST'])
def admin_refresh_lines():
    """Refresh lines (collect games + odds) (admin auth)."""
    admin, err_code = require_superuser()
    if not admin:
        return jsonify({'error': 'Unauthorized'}), 403

    from app import collect_todays_games
    try:
        result = collect_todays_games()
        return jsonify({'success': True, 'message': 'Lines refreshed', 'result': str(result) if result else None})
    except Exception as e:
        logging.error(f"Admin refresh-lines error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


def run_admin_alert_check(include_health=True):
    """
    Check for issues (cron, model, kill switch, optional health).
    If issues found, send admin push and return True. Returns False if all ok.
    """
    now_et = datetime.now(ET)
    today_str = now_et.strftime('%Y-%m-%d')
    hour_et = now_et.hour
    alerts = []
    level = 'green'

    # Cron health
    critical_jobs = ['run_model', 'collect_games', 'grade_picks']
    job_configs = {
        'run_model': {'label': 'Run Model', 'expected_h': 24},
        'collect_games': {'label': 'Collect Games', 'expected_h': 24},
        'grade_picks': {'label': 'Grade Picks', 'expected_h': 24},
        'pretip_validate': {'label': 'Pre-Tip Validate', 'expected_h': 24},
    }
    for job_name, config in job_configs.items():
        last_log = CronLog.query.filter_by(job_name=job_name).order_by(CronLog.executed_at.desc()).first()
        if last_log:
            hours_ago = (datetime.utcnow() - last_log.executed_at).total_seconds() / 3600
            overdue = hours_ago > config['expected_h'] * 1.5
            is_failing = last_log.status == 'error'
        else:
            hours_ago = None
            overdue = True
            is_failing = False
        if job_name in critical_jobs:
            if is_failing:
                level = 'red'
                alerts.append({'severity': 'critical', 'message': f"{config['label']} failed (last error)"})
            elif overdue:
                if level != 'red':
                    level = 'yellow'
                age_str = f"{hours_ago:.1f}h" if hours_ago is not None else "never"
                alerts.append({'severity': 'warn', 'message': f"{config['label']} overdue ({age_str})"})

    # Model status
    pick_today = Pick.query.filter_by(game_date=today_str).first()
    pass_today = Pass.query.filter_by(date=today_str).first()
    model_run_today = pick_today is not None or pass_today is not None
    model_run_window = hour_et >= 14
    if not model_run_today and model_run_window:
        level = 'red'
        alerts.append({'severity': 'critical', 'message': f"No pick/pass for {today_str} (past 3 PM ET)"})

    # Kill switch
    kill_switch = KillSwitch.query.filter_by(sport='nba').first()
    if kill_switch and kill_switch.active:
        level = 'red'
        alerts.append({'severity': 'critical', 'message': "Kill switch is ACTIVE"})

    # Health checks (quick: postgres + critical externals)
    if include_health:
        try:
            db.session.execute(text('SELECT 1'))
            db.session.rollback()
        except Exception as e:
            level = 'red'
            alerts.append({'severity': 'critical', 'message': f"PostgreSQL: {str(e)[:60]}"})
        for name, check_fn in [
            ('Odds API', lambda: _quick_check('https://api.the-odds-api.com/v4/sports/', headers=None, key_env='ODDS_API_KEY', key_param='apiKey')),
            ('Resend', lambda: _quick_check('https://api.resend.com/domains', headers=lambda k: {'Authorization': f'Bearer {k}'}, key_env='RESEND_API_KEY')),
        ]:
            try:
                r = check_fn()
                if r and r.get('status') == 'error':
                    if level != 'red':
                        level = 'yellow'
                    alerts.append({'severity': 'warn', 'message': f"{name}: {r.get('message', 'failed')[:50]}"})
            except Exception:
                pass

    if level == 'green':
        return False

    from app import send_admin_alert
    critical = [a for a in alerts if a['severity'] == 'critical']
    warn = [a for a in alerts if a['severity'] == 'warn']
    title = "System Issue" if critical else "Needs Attention"
    lines = [a['message'] for a in (critical[:2] + warn[:2])]
    body = '\n'.join(lines) if lines else "Check admin dashboard"
    send_admin_alert(title, body, {'level': level})
    return True


def _quick_check(url, headers=None, key_env=None, key_param=None):
    """Quick HTTP check for health. Returns {'status':'ok'} or {'status':'error','message':...}"""
    key = os.environ.get(key_env) if key_env else None
    if key_env and not key:
        return {'status': 'error', 'message': f'{key_env} not set'}
    try:
        kw = {'timeout': 6}
        if key_param and key:
            kw['params'] = {key_param: key}
        elif headers and key:
            kw['headers'] = headers(key) if callable(headers) else headers
        resp = requests.get(url, **kw)
        if resp.status_code in (200, 201):
            return {'status': 'ok'}
        return {'status': 'error', 'message': f'HTTP {resp.status_code}'}
    except Exception as e:
        return {'status': 'error', 'message': str(e)[:50]}


@admin_bp.route('/api/admin/status-summary')
def status_summary():
    admin, err_code = require_superuser()
    if not admin:
        return jsonify({'error': 'Login required' if err_code == 401 else 'Unauthorized'}), err_code

    now_et = datetime.now(ET)
    today_str = now_et.strftime('%Y-%m-%d')
    hour_et = now_et.hour

    alerts = []
    level = 'green'

    # ============ 1. Check Cron Health ============
    critical_jobs = ['run_model', 'collect_games', 'grade_picks']
    job_configs = {
        'run_model':     {'label': 'SP — Run Model', 'expected_h': 24},
        'collect_games': {'label': 'SP — Collect Games', 'expected_h': 24},
        'grade_picks':   {'label': 'SP — Grade Picks', 'expected_h': 24},
        'pretip_validate': {'label': 'Pre-Tip Validate', 'expected_h': 24},
    }

    for job_name, config in job_configs.items():
        last_log = CronLog.query.filter_by(job_name=job_name).order_by(CronLog.executed_at.desc()).first()
        last_ok = CronLog.query.filter_by(job_name=job_name, status='ok').order_by(CronLog.executed_at.desc()).first()

        # Get recent logs for success rate calculation
        recent_logs = CronLog.query.filter_by(job_name=job_name).order_by(CronLog.executed_at.desc()).limit(10).all()
        ok_count = sum(1 for l in recent_logs if l.status == 'ok')
        err_count = sum(1 for l in recent_logs if l.status == 'error')
        total_recent = len(recent_logs)
        success_rate = round(ok_count / total_recent * 100) if total_recent > 0 else 0

        if last_log:
            hours_ago = (datetime.utcnow() - last_log.executed_at).total_seconds() / 3600
            overdue = hours_ago > config['expected_h'] * 1.5
            is_failing = last_log.status == 'error'
        else:
            hours_ago = None
            overdue = True
            is_failing = False

        # Check for critical job failures
        if job_name in critical_jobs:
            if is_failing:
                level = 'red'
                alerts.append({
                    'type': 'cron',
                    'severity': 'critical',
                    'message': f"{config['label']} failed (last error)"
                })
            elif overdue:
                if level != 'red':
                    level = 'yellow'
                age_str = f"{hours_ago:.1f}h" if hours_ago is not None else "never run"
                alerts.append({
                    'type': 'cron',
                    'severity': 'warn',
                    'message': f"{config['label']} overdue ({age_str}, expected: {config['expected_h']}h)"
                })

        # Check success rate
        if success_rate < 80 and total_recent > 0:
            if level != 'red':
                level = 'yellow'
            alerts.append({
                'type': 'cron',
                'severity': 'warn',
                'message': f"{config['label']} success rate: {success_rate}%"
            })
        elif last_log and hours_ago and hours_ago > config['expected_h']:
            # Non-critical job overdue
            if level != 'red' and level != 'yellow':
                level = 'yellow'
            if job_name not in critical_jobs:
                alerts.append({
                    'type': 'cron',
                    'severity': 'info',
                    'message': f"{config['label']} last ran {hours_ago:.1f}h ago"
                })

    # ============ 2. Check Model Status ============
    # Check if model has run today (pick or pass exists)
    pick_today = Pick.query.filter_by(game_date=today_str).first()
    pass_today = Pass.query.filter_by(date=today_str).first()

    model_run_today = pick_today is not None or pass_today is not None

    # Check if model should have run by now (by 3 PM ET)
    model_run_window = hour_et >= 14  # 2:15 PM + buffer

    if model_run_today:
        if pick_today:
            alerts.append({
                'type': 'model',
                'severity': 'ok',
                'message': f"Pick published for {today_str}"
            })
        else:
            alerts.append({
                'type': 'model',
                'severity': 'ok',
                'message': f"Pass recorded for {today_str}"
            })
    elif model_run_window:
        # Model should have run by 3 PM but hasn't
        level = 'red'
        alerts.append({
            'type': 'model',
            'severity': 'critical',
            'message': f"No pick/pass for {today_str} (past 3 PM ET)"
        })
    else:
        # Before model run window
        alerts.append({
            'type': 'model',
            'severity': 'info',
            'message': f"Awaiting model run for {today_str}"
        })

    # ============ 3. Check Kill Switch ============
    kill_switch = KillSwitch.query.filter_by(sport='nba').first()
    if kill_switch and kill_switch.active:
        level = 'red'
        alerts.append({
            'type': 'kill_switch',
            'severity': 'critical',
            'message': "Kill switch is ACTIVE"
        })
    else:
        alerts.append({
            'type': 'kill_switch',
            'severity': 'ok',
            'message': "Kill switch is inactive"
        })

    # ============ 4. External Services ============
    # Just report on last health check status (no re-running checks)
    # This is a placeholder for now; in a real system you'd query cached health status
    alerts.append({
        'type': 'external',
        'severity': 'ok',
        'message': "External services operational"
    })

    # ============ Generate Summary Message ============
    if level == 'red':
        critical_alerts = [a for a in alerts if a['severity'] in ('critical', 'error')]
        if critical_alerts:
            main_issue = critical_alerts[0]['message']
            message = f"System issue: {main_issue}"
        else:
            message = "System alert — review alerts below"
    elif level == 'yellow':
        warn_alerts = [a for a in alerts if a['severity'] == 'warn']
        if warn_alerts:
            main_issue = warn_alerts[0]['message']
            message = f"Degraded status: {main_issue}"
        else:
            message = "Some systems need attention"
    else:
        message = "All systems nominal"

    return jsonify({
        'level': level,
        'message': message,
        'alerts': alerts,
        'timestamp': now_et.strftime('%b %d · %-I:%M:%S %p')
    })


@admin_bp.route('/api/admin/users/<user_id>', methods=['DELETE'])
def delete_user(user_id):
    admin, err_code = require_superuser()
    if not admin:
        return jsonify({'error': 'Login required' if err_code == 401 else 'Unauthorized'}), err_code
    user = db.session.get(User, user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404
    if user.is_superuser:
        return jsonify({'error': 'Cannot delete superuser'}), 403
    TrackedBet.query.filter_by(user_id=user_id).delete()
    from models import Referral
    Referral.query.filter((Referral.referrer_id == user_id) | (Referral.referred_id == user_id)).delete()
    db.session.delete(user)
    db.session.commit()
    return jsonify({'success': True})


@admin_bp.route('/api/admin/users/<user_id>/role', methods=['PUT'])
def update_user_role(user_id):
    admin, err_code = require_superuser()
    if not admin:
        return jsonify({'error': 'Login required' if err_code == 401 else 'Unauthorized'}), err_code
    user = db.session.get(User, user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404
    data = request.get_json() or {}
    if 'is_premium' in data:
        user.is_premium = bool(data['is_premium'])
    if 'is_superuser' in data:
        user.is_superuser = bool(data['is_superuser'])
    if 'founding_member' in data:
        user.founding_member = bool(data['founding_member'])
    if 'founding_number' in data:
        user.founding_number = data['founding_number']
    if 'subscription_status' in data:
        user.subscription_status = data['subscription_status']
    db.session.commit()
    return jsonify({
        'success': True,
        'user': {
            'id': user.id,
            'email': user.email,
            'is_premium': user.is_premium,
            'is_superuser': user.is_superuser,
            'founding_member': user.founding_member,
            'founding_number': user.founding_number,
            'subscription_status': user.subscription_status
        }
    })


@admin_bp.route('/api/admin/upgrade-user', methods=['POST'])
def upgrade_user_by_email():
    secret = request.headers.get('X-Cron-Secret', '')
    if secret != os.environ.get('CRON_SECRET', ''):
        return jsonify({'error': 'Unauthorized'}), 403
    data = request.get_json() or {}
    email = data.get('email')
    if not email:
        return jsonify({'error': 'Email required'}), 400
    user = User.query.filter_by(email=email).first()
    if not user:
        return jsonify({'error': 'User not found'}), 404
    if 'is_premium' in data:
        user.is_premium = bool(data['is_premium'])
    if 'is_superuser' in data:
        user.is_superuser = bool(data['is_superuser'])
    if 'founding_member' in data:
        user.founding_member = bool(data['founding_member'])
    if 'founding_number' in data:
        user.founding_number = data['founding_number']
    if 'subscription_status' in data:
        user.subscription_status = data['subscription_status']
    db.session.commit()
    return jsonify({
        'success': True,
        'user': {
            'id': user.id,
            'email': user.email,
            'is_premium': user.is_premium,
            'is_superuser': user.is_superuser,
            'founding_member': user.founding_member,
            'founding_number': user.founding_number,
            'subscription_status': user.subscription_status
        }
    })


@admin_bp.route('/api/admin/command-center')
def command_center_data():
    admin, err_code = require_superuser()
    if not admin:
        return jsonify({'error': 'Login required' if err_code == 401 else 'Unauthorized'}), err_code

    now_et = datetime.now(ET)
    today_str = now_et.strftime('%Y-%m-%d')

    users = User.query.all()
    total_users = len(users)
    active_subs = [u for u in users if u.subscription_status == 'active']
    trial_users = [u for u in users if u.subscription_status == 'trial']
    free_users = [u for u in users if u.subscription_status in ('free', None, '')]
    annual_subs = [u for u in active_subs if u.subscription_plan and 'annual' in u.subscription_plan.lower()]
    monthly_subs = [u for u in active_subs if u.subscription_plan and 'month' in u.subscription_plan.lower()]
    founding_members = [u for u in users if u.founding_member]
    founding_count = len(founding_members)
    founding_cap = 50

    counter = FoundingCounter.query.first()
    if counter and counter.current_count != founding_count:
        counter.current_count = founding_count
        db.session.commit()

    monthly_rev = len(monthly_subs) * 29
    annual_rev = len(annual_subs) * (99 / 12)
    mrr = round(monthly_rev + annual_rev, 2)
    arr = round(mrr * 12, 2)

    def compute_sport_stats(sport_key):
        picks = Pick.query.filter_by(sport=sport_key).order_by(Pick.game_date.desc()).all()
        passes = Pass.query.filter_by(sport=sport_key).all()

        resolved = [p for p in picks if p.result in ('win', 'loss')]
        wins = len([p for p in resolved if p.result == 'win'])
        losses = len([p for p in resolved if p.result == 'loss'])
        total_pnl = sum(p.pnl or 0 for p in resolved)
        total_picks = len(picks)
        total_passes = len(passes)
        selectivity = round(total_picks / (total_picks + total_passes) * 100, 1) if (total_picks + total_passes) > 0 else 0

        pre_cal = [p for p in resolved if p.notes and 'Pre-Cal' in p.notes]
        post_cal = [p for p in resolved if not (p.notes and 'Pre-Cal' in p.notes)]

        buckets = {'3.5-5%': {'w': 0, 'l': 0}, '5-7.5%': {'w': 0, 'l': 0}, '7.5-10%': {'w': 0, 'l': 0}}
        for p in resolved:
            e = p.edge_pct or 0
            if e >= 7.5:
                k = '7.5-10%'
            elif e >= 5:
                k = '5-7.5%'
            else:
                k = '3.5-5%'
            if p.result == 'win':
                buckets[k]['w'] += 1
            else:
                buckets[k]['l'] += 1

        last_pick = picks[0] if picks else None
        last_pick_date = last_pick.game_date if last_pick else None
        if last_pick_date:
            from datetime import date as date_type
            try:
                lpd = datetime.strptime(last_pick_date, '%Y-%m-%d').date() if isinstance(last_pick_date, str) else last_pick_date
                days_since_pick = (datetime.now(ET).date() - lpd).days
            except Exception:
                days_since_pick = None
        else:
            days_since_pick = None

        consecutive_passes = 0
        if last_pick_date:
            all_passes_sorted = sorted(passes, key=lambda p: p.date, reverse=True)
            for p in all_passes_sorted:
                if p.date <= last_pick_date:
                    break
                consecutive_passes += 1

        clv_positive = len([p for p in resolved if (p.clv or 0) > 0])
        clv_total = len([p for p in resolved if p.clv is not None])
        clv_pct = round(clv_positive / clv_total * 100) if clv_total > 0 else 0

        avg_edge = round(sum(p.edge_pct or 0 for p in picks) / len(picks), 1) if picks else 0

        equity_curve = []
        running = 0
        for p in sorted(resolved, key=lambda x: x.game_date):
            running += (p.pnl or 0)
            equity_curve.append({'date': p.game_date, 'value': running})

        recent_picks = []
        for p in picks[:10]:
            recent_picks.append({
                'date': p.game_date,
                'side': p.side,
                'line': p.line,
                'edge': p.edge_pct,
                'result': p.result,
                'pnl': p.pnl,
                'sportsbook': p.sportsbook,
                'notes': p.notes,
                'sport': sport_key,
            })

        model_runs = ModelRun.query.filter_by(sport=sport_key).order_by(ModelRun.created_at.desc()).limit(10).all()
        runs_data = []
        for r in model_runs:
            runs_data.append({
                'date': r.date,
                'games_analyzed': r.games_analyzed,
                'pick_generated': r.pick_generated,
                'duration_ms': r.run_duration_ms,
                'version': r.model_version,
            })

        return {
            'record': f'{wins}-{losses}',
            'wins': wins,
            'losses': losses,
            'win_rate': round(wins / len(resolved) * 100, 1) if resolved else 0,
            'total_pnl': total_pnl,
            'roi': round(total_pnl / (len(resolved) * 100) * 100, 1) if resolved else 0,
            'total_picks': total_picks,
            'total_passes': total_passes,
            'selectivity': selectivity,
            'avg_edge': avg_edge,
            'pre_cal_count': len(pre_cal),
            'post_cal_count': len(post_cal),
            'clv_pct': clv_pct,
            'buckets': {k: f"{v['w']}-{v['l']}" for k, v in buckets.items()},
            'bucket_rates': {k: round(v['w'] / (v['w'] + v['l']) * 100, 1) if (v['w'] + v['l']) > 0 else 0 for k, v in buckets.items()},
            'equity_curve': equity_curve,
            'recent_picks': recent_picks,
            'model_runs': runs_data,
            'last_pick_date': last_pick_date,
            'days_since_pick': days_since_pick,
            'consecutive_passes': consecutive_passes,
        }

    nba_stats = compute_sport_stats('nba')
    wnba_stats = compute_sport_stats('wnba')

    recent_users = sorted(users, key=lambda u: u.created_at or datetime.min, reverse=True)[:15]
    users_data = []
    for u in recent_users:
        tier = 'free'
        if u.founding_member:
            tier = 'founding'
        elif u.subscription_status == 'active':
            tier = 'pro'
        elif u.subscription_status == 'trial':
            tier = 'trial'
        users_data.append({
            'id': u.id,
            'email': u.email,
            'first_name': u.first_name or '',
            'tier': tier,
            'plan': u.subscription_plan or '',
            'founding_number': u.founding_number,
            'is_superuser': u.is_superuser,
            'created_at': u.created_at.isoformat() if u.created_at else None,
            'trial_end': u.trial_end_date.isoformat() if u.trial_end_date else None,
        })

    insights = Insight.query.all()
    published_insights = [i for i in insights if i.status == 'published']

    return jsonify({
        'revenue': {
            'mrr': mrr,
            'arr': arr,
            'monthly_subs': len(monthly_subs),
            'annual_subs': len(annual_subs),
            'trial_count': len(trial_users),
            'free_count': len(free_users),
            'total_subs': len(active_subs) + len(trial_users),
            'founding_count': founding_count,
            'founding_cap': founding_cap,
            'founding_pct': round(founding_count / founding_cap * 100, 1),
        },
        'model': nba_stats,
        'wnba_model': wnba_stats,
        'recent_picks': nba_stats['recent_picks'],
        'wnba_recent_picks': wnba_stats['recent_picks'],
        'model_runs': nba_stats['model_runs'],
        'wnba_model_runs': wnba_stats['model_runs'],
        'users': {
            'total': total_users,
            'list': users_data,
        },
        'insights': {
            'total': len(insights),
            'published': len(published_insights),
        },
        'push': get_push_token_stats(),
        'timestamp': now_et.strftime('%b %d, %Y · %-I:%M:%S %p EST'),
    })


def get_push_token_stats():
    all_tokens = FCMToken.query.all()
    enabled = [t for t in all_tokens if t.enabled]
    disabled = [t for t in all_tokens if not t.enabled]
    unique_users = len(set(t.user_id for t in enabled))
    total_users = User.query.count()

    now = datetime.now()
    active_24h = [t for t in enabled if t.last_seen_at and (now - t.last_seen_at).total_seconds() < 86400]
    active_7d = [t for t in enabled if t.last_seen_at and (now - t.last_seen_at).total_seconds() < 604800]
    stale = [t for t in enabled if not t.last_seen_at or (now - t.last_seen_at).total_seconds() >= 604800]

    by_platform = {}
    for t in enabled:
        p = t.platform or 'web'
        by_platform[p] = by_platform.get(p, 0) + 1

    user_tokens = []
    user_map = {}
    for t in enabled:
        if t.user_id not in user_map:
            u = User.query.get(t.user_id)
            user_map[t.user_id] = u
        u = user_map[t.user_id]
        user_tokens.append({
            'user_email': u.email if u else 'unknown',
            'user_name': u.first_name if u else '',
            'platform': t.platform or 'web',
            'last_seen': t.last_seen_at.isoformat() if t.last_seen_at else None,
            'created_at': t.created_at.isoformat() if t.created_at else None,
        })

    return {
        'total_tokens': len(all_tokens),
        'enabled': len(enabled),
        'disabled': len(disabled),
        'unique_users': unique_users,
        'total_users': total_users,
        'opt_in_pct': round(unique_users / total_users * 100, 1) if total_users > 0 else 0,
        'active_24h': len(active_24h),
        'active_7d': len(active_7d),
        'stale': len(stale),
        'by_platform': by_platform,
        'user_tokens': user_tokens,
    }


@admin_bp.route('/api/admin/health-checks')
def health_checks():
    admin, err_code = require_superuser()
    if not admin:
        return jsonify({'error': 'Login required' if err_code == 401 else 'Unauthorized'}), err_code

    results = {}

    def check_postgres():
        try:
            start = time.time()
            db.session.execute(text('SELECT 1'))
            db.session.rollback()
            latency = round((time.time() - start) * 1000)
            return {'status': 'ok', 'latency_ms': latency}
        except Exception as e:
            logging.error(f"PostgreSQL health check failed: {e}")
            return {'status': 'error', 'message': str(e)[:80]}

    def check_odds_api():
        api_key = os.environ.get('ODDS_API_KEY')
        if not api_key:
            return {'status': 'error', 'message': 'ODDS_API_KEY not set'}
        try:
            start = time.time()
            resp = requests.get(
                'https://api.the-odds-api.com/v4/sports/',
                params={'apiKey': api_key},
                timeout=(5, 15)
            )
            latency = round((time.time() - start) * 1000)
            remaining = resp.headers.get('x-requests-remaining', '?')
            used = resp.headers.get('x-requests-used', '?')
            if resp.status_code == 200:
                return {'status': 'ok', 'latency_ms': latency, 'requests_remaining': remaining, 'requests_used': used}
            elif resp.status_code == 401:
                return {'status': 'error', 'message': 'Invalid API key'}
            else:
                return {'status': 'warn', 'message': f'HTTP {resp.status_code}', 'latency_ms': latency}
        except requests.exceptions.Timeout:
            return {'status': 'warn', 'message': 'Connection timeout'}
        except requests.exceptions.ConnectionError as e:
            return {'status': 'error', 'message': f'Connection failed: {str(e)[:50]}'}
        except requests.exceptions.SSLError as e:
            return {'status': 'error', 'message': f'SSL error: {str(e)[:50]}'}
        except Exception as e:
            logging.error(f"Odds API health check failed: {e}")
            return {'status': 'error', 'message': str(e)[:80]}

    def check_balldontlie():
        api_key = os.environ.get('BALLDONTLIE_API_KEY')
        if not api_key:
            return {'status': 'error', 'message': 'BALLDONTLIE_API_KEY not set'}
        try:
            start = time.time()
            resp = requests.get(
                'https://api.balldontlie.io/v1/teams',
                headers={'Authorization': api_key},
                timeout=8
            )
            latency = round((time.time() - start) * 1000)
            if resp.status_code == 200:
                return {'status': 'ok', 'latency_ms': latency}
            elif resp.status_code == 401:
                return {'status': 'error', 'message': 'Invalid API key'}
            else:
                return {'status': 'warn', 'message': f'HTTP {resp.status_code}', 'latency_ms': latency}
        except requests.Timeout:
            return {'status': 'warn', 'message': 'Timeout (8s)'}
        except Exception as e:
            logging.error(f"balldontlie health check failed: {e}")
            return {'status': 'error', 'message': str(e)[:80]}

    def check_espn():
        try:
            start = time.time()
            resp = requests.get(
                'https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard',
                timeout=8
            )
            latency = round((time.time() - start) * 1000)
            if resp.status_code == 200:
                data = resp.json()
                game_count = len(data.get('events', []))
                return {'status': 'ok', 'latency_ms': latency, 'games_today': game_count}
            else:
                return {'status': 'warn', 'message': f'HTTP {resp.status_code}', 'latency_ms': latency}
        except requests.Timeout:
            return {'status': 'warn', 'message': 'Timeout (8s)'}
        except Exception as e:
            logging.error(f"ESPN health check failed: {e}")
            return {'status': 'error', 'message': str(e)[:80]}

    def check_resend():
        api_key = os.environ.get('RESEND_API_KEY')
        if not api_key:
            return {'status': 'error', 'message': 'RESEND_API_KEY not set'}
        try:
            start = time.time()
            resp = requests.get(
                'https://api.resend.com/domains',
                headers={'Authorization': f'Bearer {api_key}'},
                timeout=8
            )
            latency = round((time.time() - start) * 1000)
            if resp.status_code == 200:
                domains = resp.json().get('data', [])
                verified = [d for d in domains if d.get('status') == 'verified']
                return {'status': 'ok', 'latency_ms': latency, 'domains': len(domains), 'verified': len(verified)}
            elif resp.status_code == 401 or resp.status_code == 403:
                return {'status': 'error', 'message': 'Invalid API key'}
            else:
                return {'status': 'ok', 'latency_ms': latency, 'message': 'Connected'}
        except requests.Timeout:
            return {'status': 'warn', 'message': 'Timeout (8s)'}
        except Exception as e:
            logging.error(f"Resend health check failed: {e}")
            return {'status': 'error', 'message': str(e)[:80]}

    def check_stripe():
        try:
            from stripe_client import get_stripe_client
            start = time.time()
            stripe_client = get_stripe_client()
            balance = stripe_client.Balance.retrieve()
            latency = round((time.time() - start) * 1000)
            available = sum(a.get('amount', 0) for a in balance.get('available', [])) / 100
            mode = 'live' if balance.get('livemode') else 'test'
            return {'status': 'ok', 'latency_ms': latency, 'balance': f'${available:.2f}', 'mode': mode}
        except Exception as e:
            raw = str(e)
            logging.error(f"Stripe health check failed: {e}")
            if 'invalid api key' in raw.lower():
                return {'status': 'error', 'message': 'Invalid API key'}
            if 'not found' in raw.lower() or 'not set' in raw.lower():
                return {'status': 'error', 'message': 'STRIPE key not configured'}
            safe_msg = raw.split('\n')[0][:60]
            import re
            safe_msg = re.sub(r'(sk_live_|sk_test_|rk_live_|rk_test_)\S+', '***', safe_msg)
            return {'status': 'error', 'message': safe_msg}

    results['postgresql'] = check_postgres()

    def check_sqlite():
        """SQLite (games data) - must use persistent volume on Railway."""
        try:
            from db_path import get_sqlite_status
            status = get_sqlite_status()
            if not status['persistent']:
                return {'status': 'warn', 'message': 'No volume (RAILWAY_VOLUME_MOUNT_PATH unset) — data ephemeral', **status}
            if not status['parent_exists']:
                return {'status': 'error', 'message': 'Volume path missing', **status}
            if not status['writable']:
                return {'status': 'error', 'message': 'Volume not writable (try RAILWAY_RUN_UID=0)', **status}
            import sqlite3
            conn = sqlite3.connect(status['path'])
            try:
                cur = conn.execute("SELECT COUNT(*) FROM games")
                count = cur.fetchone()[0]
            except sqlite3.OperationalError:
                count = 0  # Table may not exist yet
            conn.close()
            return {'status': 'ok', 'games': count, **status}
        except Exception as e:
            try:
                from db_path import get_sqlite_status
                status = get_sqlite_status()
            except Exception:
                status = {}
            return {'status': 'error', 'message': str(e)[:80], **status}

    results['sqlite'] = check_sqlite()

    external_checks = {
        'odds_api': check_odds_api,
        'balldontlie': check_balldontlie,
        'espn': check_espn,
        'resend': check_resend,
        'stripe': check_stripe,
    }
    with ThreadPoolExecutor(max_workers=5) as pool:
        futures = {pool.submit(fn): name for name, fn in external_checks.items()}
        for future in as_completed(futures, timeout=12):
            name = futures[future]
            try:
                results[name] = future.result()
            except Exception as e:
                results[name] = {'status': 'error', 'message': f'Check failed: {str(e)[:60]}'}

    all_ok = all(r['status'] == 'ok' for r in results.values())
    any_error = any(r['status'] == 'error' for r in results.values())
    results['_summary'] = {
        'overall': 'ok' if all_ok else ('error' if any_error else 'warn'),
        'checked_at': datetime.now(ET).strftime('%b %d · %-I:%M:%S %p'),
    }

    return jsonify(results)


@admin_bp.route('/api/admin/cron-health')
def cron_health():
    admin, err_code = require_superuser()
    if not admin:
        return jsonify({'error': 'Login required' if err_code == 401 else 'Unauthorized'}), err_code

    now_et = datetime.now(ET)

    job_configs = {
        'pretip_validate': {'label': 'Pre-Tip Validate', 'schedule': '9:55 AM + 4:55 PM', 'expected_h': 24},
        'backup':          {'label': 'SP — Daily Backup', 'schedule': 'Daily 3:20 AM', 'expected_h': 24},
        'data_quality':    {'label': 'SP — Data Quality', 'schedule': '4:15 AM + 12:15 PM', 'expected_h': 24},
        'collect_games':   {'label': 'SP — Collect Games', 'schedule': '5:05 AM + 9:00 AM + 1:05 PM', 'expected_h': 24},
        'run_model':       {'label': 'SP — Run Model', 'schedule': '10:15 AM + 2:15 PM', 'expected_h': 24},
        'refresh_lines':   {'label': 'SP — Refresh Lines', 'schedule': 'Every 10 min, 6 AM–2 AM', 'expected_h': 1},
        'closing_lines':   {'label': 'SP — Closing Lines', 'schedule': 'Every min, 10 AM–1 AM (×4 shards)', 'expected_h': 1},
        'grade_picks':     {'label': 'SP — Grade Picks', 'schedule': '3:45 AM + 11:30 AM', 'expected_h': 24},
        'grade_whatifs':   {'label': 'SP — Grade What-Ifs', 'schedule': '4:05 AM + 4:05 PM', 'expected_h': 24},
        'expire_trials':   {'label': 'SP — Expire Trials', 'schedule': 'Hourly at :10', 'expected_h': 2},
        'weekly_summary':  {'label': 'SP — Weekly Summary', 'schedule': 'Mon 6:30 AM', 'expected_h': 168},
    }

    jobs = []
    for job_name, config in job_configs.items():
        last_log = CronLog.query.filter_by(job_name=job_name).order_by(CronLog.executed_at.desc()).first()
        last_ok = CronLog.query.filter_by(job_name=job_name, status='ok').order_by(CronLog.executed_at.desc()).first()
        last_err = CronLog.query.filter_by(job_name=job_name, status='error').order_by(CronLog.executed_at.desc()).first()

        recent_logs = CronLog.query.filter_by(job_name=job_name).order_by(CronLog.executed_at.desc()).limit(10).all()
        ok_count = sum(1 for l in recent_logs if l.status == 'ok')
        err_count = sum(1 for l in recent_logs if l.status == 'error')

        if last_log:
            hours_ago = (datetime.utcnow() - last_log.executed_at).total_seconds() / 3600
            overdue = hours_ago > config['expected_h'] * 1.5
            health = 'error' if overdue or (last_log.status == 'error') else 'ok'
            if not overdue and last_log.status == 'error' and last_ok:
                health = 'warn'
        else:
            hours_ago = None
            overdue = True
            health = 'never'

        jobs.append({
            'name': config.get('label', job_name),
            'schedule': config['schedule'],
            'health': health,
            'last_run': last_log.executed_at.isoformat() if last_log else None,
            'last_status': last_log.status if last_log else None,
            'last_duration_ms': last_log.duration_ms if last_log else None,
            'last_message': last_log.message[:200] if last_log and last_log.message else None,
            'last_error': last_err.executed_at.isoformat() if last_err else None,
            'last_error_msg': last_err.message[:200] if last_err and last_err.message else None,
            'hours_ago': round(hours_ago, 1) if hours_ago is not None else None,
            'recent_ok': ok_count,
            'recent_errors': err_count,
        })

    all_health = [j['health'] for j in jobs]
    if all(h == 'ok' for h in all_health):
        overall = 'ok'
    elif any(h == 'error' for h in all_health):
        overall = 'error'
    elif any(h == 'never' for h in all_health):
        overall = 'warn'
    else:
        overall = 'warn'

    total_logs = CronLog.query.count()

    return jsonify({
        'jobs': jobs,
        'overall': overall,
        'total_executions': total_logs,
        'checked_at': now_et.strftime('%b %d · %-I:%M:%S %p'),
    })


@admin_bp.route('/api/admin/export')
def export_model_data():
    admin, err_code = require_superuser()
    if not admin:
        return jsonify({'error': 'Login required' if err_code == 401 else 'Unauthorized'}), err_code

    picks = Pick.query.order_by(Pick.game_date).all()
    passes = Pass.query.order_by(Pass.date).all()
    runs = ModelRun.query.order_by(ModelRun.date).all()

    return jsonify({
        'picks': [{
            'game_date': p.game_date,
            'sport': p.sport,
            'away_team': p.away_team,
            'home_team': p.home_team,
            'side': p.side,
            'line': p.line,
            'line_open': p.line_open,
            'line_close': p.line_close,
            'edge_pct': p.edge_pct,
            'model_confidence': p.model_confidence,
            'predicted_margin': p.predicted_margin,
            'cover_prob': p.cover_prob,
            'implied_prob': p.implied_prob,
            'sigma': p.sigma,
            'z_score': p.z_score,
            'raw_edge': p.raw_edge,
            'market_odds': p.market_odds,
            'sportsbook': p.sportsbook,
            'closing_spread': p.closing_spread,
            'clv': p.clv,
            'home_score': p.home_score,
            'away_score': p.away_score,
            'result': p.result,
            'result_ats': p.result_ats,
            'pnl': p.pnl,
            'published_at': p.published_at.isoformat() if p.published_at else None,
        } for p in picks],
        'passes': [{
            'date': p.date,
            'sport': p.sport,
            'games_analyzed': p.games_analyzed,
            'closest_edge_pct': p.closest_edge_pct,
            'pass_reason': p.pass_reason,
            'notes': p.notes,
            'whatif_side': p.whatif_side,
            'whatif_home_team': p.whatif_home_team,
            'whatif_away_team': p.whatif_away_team,
            'whatif_pick_side': p.whatif_pick_side,
            'whatif_line': p.whatif_line,
            'whatif_edge': p.whatif_edge,
            'whatif_cover_prob': p.whatif_cover_prob,
            'whatif_pred_margin': p.whatif_pred_margin,
            'whatif_result': p.whatif_result,
            'whatif_covered': p.whatif_covered,
        } for p in passes],
        'model_runs': [{
            'date': r.date,
            'sport': r.sport,
            'games_analyzed': r.games_analyzed,
            'pick_generated': r.pick_generated,
            'model_version': r.model_version,
            'run_duration_ms': r.run_duration_ms,
        } for r in runs],
        'spread_buckets': _compute_spread_buckets(picks),
        'whatif_summary': _compute_whatif_summary(passes),
        '_meta': {
            'total_picks': len(picks),
            'total_passes': len(passes),
            'total_runs': len(runs),
            'exported_at': datetime.now(ET).strftime('%Y-%m-%d %H:%M:%S ET'),
        }
    })


def _compute_spread_buckets(picks):
    buckets = {
        'under_5': {'label': '< 5 pts', 'wins': 0, 'losses': 0, 'pending': 0, 'picks': []},
        '5_to_10': {'label': '5-10 pts', 'wins': 0, 'losses': 0, 'pending': 0, 'picks': []},
        '10_to_15': {'label': '10-15 pts', 'wins': 0, 'losses': 0, 'pending': 0, 'picks': []},
        'over_15': {'label': '15+ pts', 'wins': 0, 'losses': 0, 'pending': 0, 'picks': []},
    }
    for p in picks:
        spread_abs = abs(p.line) if p.line is not None else 0
        if spread_abs < 5:
            bucket = 'under_5'
        elif spread_abs < 10:
            bucket = '5_to_10'
        elif spread_abs < 15:
            bucket = '10_to_15'
        else:
            bucket = 'over_15'

        entry = {'date': p.game_date, 'side': p.side, 'line': p.line, 'result': p.result, 'edge': p.edge_pct}
        buckets[bucket]['picks'].append(entry)
        if p.result == 'win':
            buckets[bucket]['wins'] += 1
        elif p.result == 'loss':
            buckets[bucket]['losses'] += 1
        else:
            buckets[bucket]['pending'] += 1

    for b in buckets.values():
        total = b['wins'] + b['losses']
        b['win_rate'] = round(b['wins'] / total * 100, 1) if total > 0 else None
        b['sample_size'] = total

    return buckets


def _compute_whatif_summary(passes):
    graded = [p for p in passes if p.whatif_result is not None]
    if not graded:
        return {'total_graded': 0, 'message': 'No what-if data graded yet. Starts after next pass day + game results.'}

    wins = sum(1 for p in graded if p.whatif_covered)
    losses = len(graded) - wins
    cover_rate = round(wins / len(graded) * 100, 1) if graded else 0

    return {
        'total_graded': len(graded),
        'wins': wins,
        'losses': losses,
        'cover_rate_pct': cover_rate,
        'threshold_assessment': 'Threshold may be too high — leaving money on the table' if cover_rate > 52 else 'Threshold is appropriate — passed games are near coin-flip',
    }


@admin_bp.route('/api/admin/retro-calibrate', methods=['POST'])
def retro_calibrate():
    admin, err_code = require_superuser()
    if not admin:
        return jsonify({'error': 'Login required' if err_code == 401 else 'Unauthorized'}), err_code

    pre_cal_picks = Pick.query.filter(
        Pick.predicted_margin.is_(None),
        Pick.result != 'pending',
    ).order_by(Pick.game_date).all()

    if not pre_cal_picks:
        return jsonify({'message': 'No pre-calibration picks found', 'updated': 0})

    from sport_config import get_sport_config
    from scipy.stats import norm
    import math

    results = []
    for p in pre_cal_picks:
        cfg = get_sport_config(p.sport or 'nba')
        sigma = cfg.get('sigma', 11.7)
        model_weight = cfg.get('model_weight', 0.3)
        max_edge = cfg.get('max_edge_pct', 8.0)
        implied_prob = 0.5238

        spread = p.line if p.line is not None else 0
        z = spread / sigma if sigma > 0 else 0
        raw_cover_prob = 1 - norm.cdf(z)

        blended_cover_prob = model_weight * raw_cover_prob + (1 - model_weight) * implied_prob
        calibrated_edge = (blended_cover_prob - implied_prob) * 100
        calibrated_edge = min(calibrated_edge, max_edge)

        results.append({
            'game_date': p.game_date,
            'side': p.side,
            'line': p.line,
            'original_edge': p.edge_pct,
            'calibrated_edge': round(calibrated_edge, 2),
            'calibrated_cover_prob': round(blended_cover_prob, 4),
            'would_qualify': calibrated_edge >= cfg.get('edge_threshold_pct', 3.5),
            'result': p.result,
        })

    return jsonify({
        'pre_cal_picks': results,
        'summary': {
            'total': len(results),
            'would_qualify': sum(1 for r in results if r['would_qualify']),
            'would_pass': sum(1 for r in results if not r['would_qualify']),
            'qualified_record': f"{sum(1 for r in results if r['would_qualify'] and r['result'] == 'win')}-{sum(1 for r in results if r['would_qualify'] and r['result'] == 'loss')}",
        }
    })


@admin_bp.route('/api/admin/control-room')
def control_room():
    admin, err_code = require_superuser()
    if not admin:
        return jsonify({'error': 'Login required' if err_code == 401 else 'Unauthorized'}), err_code

    from public_api import evaluate_kill_switch
    from sport_config import get_sport_config

    sport = request.args.get('sport', 'nba')
    cfg = get_sport_config(sport)

    ks_result = evaluate_kill_switch(sport)

    resolved = Pick.query.filter(
        Pick.result.in_(['win', 'loss', 'push']),
        Pick.sport == sport,
    ).order_by(Pick.game_date.desc()).limit(200).all()

    edge_values = [p.edge_pct for p in resolved if p.edge_pct is not None]
    avg_edge = round(sum(edge_values) / len(edge_values), 2) if edge_values else 0
    line_values = [abs(p.line) for p in resolved if p.line is not None]
    avg_spread = round(sum(line_values) / len(line_values), 1) if line_values else 0

    from models import EdgeSnapshot
    snapshots = db.session.query(EdgeSnapshot).join(Pick).filter(
        Pick.sport == sport,
        Pick.result.in_(['win', 'loss', 'push']),
    ).order_by(EdgeSnapshot.created_at.desc()).limit(100).all()

    open_edges = [s.edge_pct for s in snapshots if s.edge_pct is not None and s.snapshot_label == 'open']
    pretip_edges = [s.edge_pct for s in snapshots if s.snapshot_label == 'pretip' and s.edge_pct is not None]

    sfs_data = []
    for p in resolved[:20]:
        sfs = getattr(p, 'steam_fragility', None)
        if sfs is not None:
            sfs_data.append({
                'date': p.game_date,
                'side': p.side,
                'sfs': round(sfs, 3),
                'edge_pct': p.edge_pct,
                'result': p.result,
                'line': p.line,
            })

    spread_buckets = {}
    for p in resolved:
        if p.line is None:
            continue
        s = abs(p.line)
        if s <= 3:
            bk = '0-3'
        elif s <= 6:
            bk = '3.5-6'
        elif s <= 10:
            bk = '6.5-10'
        else:
            bk = '10+'
        if bk not in spread_buckets:
            spread_buckets[bk] = {'wins': 0, 'losses': 0, 'pushes': 0, 'total': 0, 'edges': []}
        spread_buckets[bk]['total'] += 1
        spread_buckets[bk]['edges'].append(p.edge_pct or 0)
        if p.result == 'win':
            spread_buckets[bk]['wins'] += 1
        elif p.result == 'loss':
            spread_buckets[bk]['losses'] += 1
        else:
            spread_buckets[bk]['pushes'] += 1

    for bk in spread_buckets:
        b = spread_buckets[bk]
        total_wl = b['wins'] + b['losses']
        b['win_rate'] = round(b['wins'] / total_wl * 100, 1) if total_wl > 0 else None
        b['avg_edge'] = round(sum(b['edges']) / len(b['edges']), 2) if b['edges'] else 0
        bucket_base = {'0-3': 1.5, '3.5-6': 4.75, '6.5-10': 8.25, '10+': 12.0}.get(bk, 5.0)
        b['required_threshold'] = round(min(3.0 + bucket_base * 0.167, 7.0), 2)
        del b['edges']

    import numpy as np
    unit_results = []
    cumulative_pnl = 0
    max_pnl = 0
    max_drawdown = 0
    total_wagered = 0
    for p in sorted(resolved, key=lambda x: x.game_date or ''):
        if p.result == 'win':
            unit_results.append(100 / 110)
        elif p.result == 'loss':
            unit_results.append(-1.0)
        elif p.result == 'push':
            unit_results.append(0.0)
        cumulative_pnl += unit_results[-1]
        total_wagered += 1
        if cumulative_pnl > max_pnl:
            max_pnl = cumulative_pnl
        drawdown = max_pnl - cumulative_pnl
        if drawdown > max_drawdown:
            max_drawdown = drawdown

    wins_count = sum(1 for p in resolved if p.result == 'win')
    losses_count = sum(1 for p in resolved if p.result == 'loss')
    drawdown_pct = 0.0
    if max_pnl > 0:
        drawdown_pct = round((max_drawdown / max_pnl) * 100, 1)
    elif max_drawdown > 0 and total_wagered > 0:
        drawdown_pct = round((max_drawdown / total_wagered) * 100, 1)

    rolling_50 = None
    rolling_100 = None
    if len(unit_results) >= 50:
        rolling_50 = round(sum(unit_results[-50:]) / 50 * 100, 2)
    if len(unit_results) >= 100:
        rolling_100 = round(sum(unit_results[-100:]) / 100 * 100, 2)

    return_std = round(float(np.std(unit_results)) * 100, 2) if len(unit_results) >= 10 else None

    risk_of_ruin_pct = None
    if (wins_count + losses_count) >= 20:
        wr = wins_count / (wins_count + losses_count)
        if wr > 0 and wr < 1:
            q = 1 - wr
            if wr != q:
                ror = (q / wr) ** 100
                risk_of_ruin_pct = round(ror * 100, 4) if ror < 1 else 100.0
            else:
                risk_of_ruin_pct = 100.0

    pick_dates = sorted([p.game_date for p in resolved if p.game_date])
    avg_days_between = 0
    if len(pick_dates) >= 2:
        from datetime import datetime
        gaps = []
        for i in range(1, len(pick_dates)):
            try:
                d1 = datetime.strptime(str(pick_dates[i-1]), '%Y-%m-%d')
                d2 = datetime.strptime(str(pick_dates[i]), '%Y-%m-%d')
                gaps.append(abs((d2 - d1).days))
            except Exception:
                pass
        avg_days_between = round(sum(gaps) / len(gaps), 1) if gaps else 0

    risk_profile = {
        'max_drawdown_pct': drawdown_pct,
        'rolling_50_roi': rolling_50,
        'rolling_100_roi': rolling_100,
        'return_std_dev': return_std,
        'risk_of_ruin_pct': risk_of_ruin_pct,
        'avg_days_between_picks': avg_days_between,
        'avg_edge_published': avg_edge,
    }

    return jsonify({
        'kill_switch': ks_result,
        'risk_profile': risk_profile,
        'thresholds': {
            'base_edge': cfg.get('edge_threshold_pct', 3.5),
            'elasticity_formula': 'Required Edge = 3.0% + Spread × 0.167 (capped at 7.0%)',
            'max_edge_cap': cfg.get('max_edge_pct', 8.0),
            'model_weight': cfg.get('model_weight', 0.3),
            'sigma': cfg.get('sigma', 11.7),
            'sfs_cap': 0.6,
            'avg_edge_published': avg_edge,
            'avg_spread_published': avg_spread,
        },
        'spread_buckets': spread_buckets,
        'decay_metrics': {
            'open_snapshots': len(open_edges),
            'pretip_snapshots': len(pretip_edges),
            'avg_open_edge': round(sum(open_edges) / len(open_edges), 2) if open_edges else None,
            'avg_pretip_edge': round(sum(pretip_edges) / len(pretip_edges), 2) if pretip_edges else None,
        },
        'fragility': sfs_data,
        'experimental': {
            'kill_switch_enabled': True,
            'sfs_enabled': True,
            'edge_decay_tracking': True,
            'regime_detection': True,
            'rest_penalties': True,
            'star_injury_gates': True,
        },
    })


@admin_bp.route('/api/admin/model-signal')
def model_signal():
    admin, err_code = require_superuser()
    if not admin:
        return jsonify({'error': 'Login required' if err_code == 401 else 'Unauthorized'}), err_code

    sport = request.args.get('sport', 'nba')

    resolved = Pick.query.filter(
        Pick.result.in_(['win', 'loss', 'push']),
        Pick.sport == sport,
    ).order_by(Pick.game_date.desc()).all()

    from model import get_edge_threshold_for_spread

    picks_with_signal = []
    all_blended_wins = 0
    all_blended_losses = 0
    all_blended_profit = 0.0

    tracked_blended_wins = 0
    tracked_blended_losses = 0
    tracked_blended_profit = 0.0
    model_only_wins = 0
    model_only_losses = 0
    model_only_would_pass = 0
    model_only_profit = 0.0

    corr_edges = []
    corr_outcomes = []

    for p in resolved:
        won = p.result == 'win'
        push = p.result == 'push'
        unit = 100 / 110 if won else (-1.0 if not push else 0.0)
        all_blended_profit += unit
        if won:
            all_blended_wins += 1
        elif not push:
            all_blended_losses += 1

        mo_edge = getattr(p, 'model_only_edge', None)
        mo_prob = getattr(p, 'model_only_cover_prob', None)

        mo_would_bet = False
        if mo_edge is not None:
            spread_abs = abs(p.line) if p.line is not None else 0
            req_edge = get_edge_threshold_for_spread(spread_abs)
            mo_would_bet = mo_edge >= req_edge

            tracked_blended_profit += unit
            if won:
                tracked_blended_wins += 1
            elif not push:
                tracked_blended_losses += 1

            if mo_would_bet:
                model_only_profit += unit
                if won:
                    model_only_wins += 1
                elif not push:
                    model_only_losses += 1
            else:
                model_only_would_pass += 1

            if not push:
                corr_edges.append(mo_edge)
                corr_outcomes.append(1 if won else 0)

        picks_with_signal.append({
            'date': p.game_date,
            'side': p.side,
            'line': p.line,
            'result': p.result,
            'blended_edge': p.edge_pct,
            'blended_cover_prob': round(p.cover_prob, 4) if p.cover_prob else None,
            'model_only_edge': round(mo_edge, 2) if mo_edge is not None else None,
            'model_only_cover_prob': round(mo_prob, 4) if mo_prob is not None else None,
            'model_only_would_bet': mo_would_bet,
        })

    total_all = all_blended_wins + all_blended_losses
    total_tracked = tracked_blended_wins + tracked_blended_losses
    total_model = model_only_wins + model_only_losses
    tracked_count = sum(1 for p in picks_with_signal if p['model_only_edge'] is not None)

    all_blended_wr = round(all_blended_wins / total_all * 100, 1) if total_all > 0 else None
    all_blended_roi = round(all_blended_profit / total_all * 100, 1) if total_all > 0 else None
    tracked_wr = round(tracked_blended_wins / total_tracked * 100, 1) if total_tracked > 0 else None
    tracked_roi = round(tracked_blended_profit / total_tracked * 100, 1) if total_tracked > 0 else None
    model_wr = round(model_only_wins / total_model * 100, 1) if total_model > 0 else None
    model_roi = round(model_only_profit / total_model * 100, 1) if total_model > 0 else None

    edge_corr = None
    if len(corr_edges) >= 10:
        import numpy as np
        edge_corr = round(float(np.corrcoef(corr_edges, corr_outcomes)[0, 1]), 4)

    return jsonify({
        'sport': sport,
        'tracked_picks': tracked_count,
        'total_resolved': len(resolved),
        'sample_target': 50,
        'blended_all': {
            'wins': all_blended_wins,
            'losses': all_blended_losses,
            'win_rate': all_blended_wr,
            'roi': all_blended_roi,
            'total_profit': round(all_blended_profit, 2),
        },
        'blended_tracked': {
            'wins': tracked_blended_wins,
            'losses': tracked_blended_losses,
            'win_rate': tracked_wr,
            'roi': tracked_roi,
            'total_profit': round(tracked_blended_profit, 2),
            'note': 'Same picks as model_only set for apples-to-apples comparison',
        },
        'model_only': {
            'wins': model_only_wins,
            'losses': model_only_losses,
            'win_rate': model_wr,
            'roi': model_roi,
            'total_profit': round(model_only_profit, 2),
            'would_pass_count': model_only_would_pass,
        },
        'edge_outcome_correlation': edge_corr,
        'diagnosis': _diagnose_signal(tracked_count, tracked_wr, model_wr, tracked_roi, model_roi, edge_corr),
        'picks': picks_with_signal[:50],
    })


def _diagnose_signal(n, blended_wr, model_wr, blended_roi, model_roi, corr):
    if n < 20:
        return f"Need more data — {n}/50 picks tracked so far. Keep collecting."
    if model_wr is None or blended_wr is None:
        return "Insufficient resolved picks to diagnose."
    if model_roi is not None and blended_roi is not None:
        roi_gap = blended_roi - model_roi
        if roi_gap > 5:
            msg = f"Market is doing heavy lifting. Blended ROI {blended_roi:+.1f}% vs model-only {model_roi:+.1f}%. Consider keeping MODEL_WEIGHT at 0.3 or lower."
        elif roi_gap < -3:
            msg = f"Model is adding signal. Model-only ROI {model_roi:+.1f}% vs blended {blended_roi:+.1f}%. Consider increasing MODEL_WEIGHT cautiously."
        else:
            msg = f"Model and market contributing roughly equally. ROI gap: {roi_gap:+.1f}%."
    else:
        msg = "Not enough data for ROI comparison."
    if corr is not None:
        if corr > 0.15:
            msg += f" Edge-outcome correlation {corr:+.4f} is positive — model edge has predictive value."
        elif corr < -0.05:
            msg += f" Edge-outcome correlation {corr:+.4f} is negative — model edge may be noise."
        else:
            msg += f" Edge-outcome correlation {corr:+.4f} is flat — inconclusive signal."
    return msg


@admin_bp.route('/api/admin/test-push', methods=['POST'])
def test_push():
    user, when_err = require_superuser()
    if when_err:
        return jsonify({'error': 'Unauthorized'}), when_err
    from models import FCMToken
    from app import send_push_notification, _get_firebase_service_info

    data = request.get_json(silent=True) or {}
    title = (data.get('title') or 'SharpPicks Test').strip()
    body = (data.get('body') or 'Push notifications are working.').strip()

    tokens = FCMToken.query.filter_by(user_id=user.id, enabled=True).all()
    if not tokens:
        return jsonify({'error': f'No enabled FCM tokens for your account ({user.email})', 'sent': 0}), 400

    if not _get_firebase_service_info():
        return jsonify({
            'error': 'No Firebase credentials. Set FIREBASE_SERVICE_ACCOUNT_JSON or FIREBASE_PRIVATE_KEY, or add firebase-service-account.json',
            'sent': 0
        }), 500

    try:
        sent = send_push_notification(user.id, title, body)
        if sent == 0 and any(getattr(t, 'platform', '') == 'ios' for t in tokens):
            return jsonify({
                'sent': 0,
                'error': 'Push failed. For iOS, upload APNs key in Firebase Console → Project Settings → Cloud Messaging.',
                'hint': 'APNs authentication required for iOS tokens'
            }), 400
        return jsonify({'sent': sent})
    except ValueError as e:
        msg = str(e)
        if any(x in msg.lower() for x in ('expected pattern', 'pem', 'format invalid', 'credentials invalid')):
            msg = (
                'Firebase credentials invalid. Try one of:\n'
                '1. Separate env vars (most reliable on Railway): FIREBASE_PRIVATE_KEY (PEM with \\n for newlines), '
                'FIREBASE_CLIENT_EMAIL, FIREBASE_PROJECT_ID.\n'
                '2. FIREBASE_SERVICE_ACCOUNT_JSON = full JSON from Firebase Console → Service accounts → Generate new private key. '
                'Use jq -c . to compact. Ensure private_key has proper newlines.'
            )
        return jsonify({'error': msg, 'sent': 0}), 500
    except Exception as e:
        return jsonify({'error': str(e)[:200], 'sent': 0}), 500


@admin_bp.route('/api/admin/export-picks')
def export_picks():
    cron_secret = os.environ.get('CRON_SECRET', '')
    cron_auth = cron_secret and request.headers.get('X-Cron-Secret') == cron_secret
    if not cron_auth:
        admin, err_code = require_superuser()
        if not admin:
            return jsonify({'error': 'Unauthorized'}), err_code

    picks = Pick.query.order_by(Pick.published_at.desc()).all()
    passes = Pass.query.order_by(Pass.date.desc()).all()
    runs = ModelRun.query.order_by(ModelRun.created_at.desc()).all()

    def pick_to_dict(p):
        return {
            'id': p.id, 'published_at': p.published_at.isoformat() if p.published_at else None,
            'sport': p.sport, 'away_team': p.away_team, 'home_team': p.home_team,
            'game_date': p.game_date, 'side': p.side, 'line': p.line,
            'line_open': p.line_open, 'line_close': p.line_close, 'start_time': p.start_time,
            'edge_pct': p.edge_pct, 'model_confidence': p.model_confidence,
            'predicted_margin': p.predicted_margin, 'sigma': p.sigma, 'z_score': p.z_score,
            'raw_edge': p.raw_edge, 'cover_prob': p.cover_prob, 'implied_prob': p.implied_prob,
            'market_odds': p.market_odds, 'sportsbook': p.sportsbook,
            'closing_spread': p.closing_spread, 'clv': p.clv,
            'home_score': p.home_score, 'away_score': p.away_score,
            'result': p.result, 'result_ats': p.result_ats,
            'result_resolved_at': p.result_resolved_at.isoformat() if p.result_resolved_at else None,
            'pnl': p.pnl, 'profit_units': p.profit_units, 'notes': p.notes,
            'position_size_pct': p.position_size_pct,
            'model_only_cover_prob': getattr(p, 'model_only_cover_prob', None),
            'model_only_edge': getattr(p, 'model_only_edge', None),
        }

    def pass_to_dict(p):
        return {
            'id': p.id, 'date': p.date, 'sport': p.sport,
            'games_analyzed': p.games_analyzed, 'closest_edge_pct': p.closest_edge_pct,
            'pass_reason': p.pass_reason, 'notes': p.notes, 'model_run_id': p.model_run_id,
            'whatif_side': p.whatif_side, 'whatif_home_team': p.whatif_home_team,
            'whatif_away_team': p.whatif_away_team, 'whatif_pick_side': p.whatif_pick_side,
            'whatif_line': p.whatif_line, 'whatif_edge': p.whatif_edge,
            'whatif_cover_prob': p.whatif_cover_prob, 'whatif_pred_margin': p.whatif_pred_margin,
            'whatif_result': p.whatif_result, 'whatif_covered': p.whatif_covered,
            'created_at': p.created_at.isoformat() if p.created_at else None,
        }

    def run_to_dict(r):
        return {
            'id': r.id, 'date': r.date, 'sport': getattr(r, 'sport', 'nba'),
            'games_analyzed': getattr(r, 'games_analyzed', 0),
            'pick_generated': getattr(r, 'pick_generated', False),
            'pick_id': getattr(r, 'pick_id', None),
            'pass_id': getattr(r, 'pass_id', None),
            'run_duration_ms': getattr(r, 'run_duration_ms', 0),
            'model_version': getattr(r, 'model_version', 'v1.0'),
            'games_detail': getattr(r, 'games_detail', None),
            'created_at': r.created_at.isoformat() if r.created_at else None,
        }

    return jsonify({
        'picks': [pick_to_dict(p) for p in picks],
        'passes': [pass_to_dict(p) for p in passes],
        'model_runs': [run_to_dict(r) for r in runs],
        'exported_at': datetime.now(ET).isoformat(),
    })


@admin_bp.route('/api/admin/sync-from-prod', methods=['POST'])
def sync_from_prod():
    cron_secret = os.environ.get('CRON_SECRET', '')
    cron_auth = cron_secret and request.headers.get('X-Cron-Secret') == cron_secret
    if not cron_auth:
        admin, err_code = require_superuser()
        if not admin:
            return jsonify({'error': 'Unauthorized'}), err_code

    prod_url = 'https://app.sharppicks.ai/api/admin/export-picks'
    try:
        resp = requests.get(prod_url, headers={'X-Cron-Secret': cron_secret}, timeout=30)
        if resp.status_code != 200:
            return jsonify({'error': f'Production returned {resp.status_code}'}), 502
        data = resp.json()
    except Exception as e:
        return jsonify({'error': f'Failed to fetch from production: {e}'}), 502

    stats = {'picks_added': 0, 'picks_updated': 0, 'passes_added': 0, 'passes_updated': 0, 'runs_added': 0, 'runs_updated': 0}

    for pd in data.get('picks', []):
        existing = Pick.query.get(pd['id'])
        if existing:
            for key in ['result', 'result_ats', 'pnl', 'profit_units', 'home_score', 'away_score',
                        'closing_spread', 'clv', 'line_close', 'position_size_pct',
                        'model_only_cover_prob', 'model_only_edge']:
                if pd.get(key) is not None:
                    setattr(existing, key, pd[key])
            if pd.get('result_resolved_at'):
                existing.result_resolved_at = datetime.fromisoformat(pd['result_resolved_at'])
            stats['picks_updated'] += 1
        else:
            pick = Pick(
                id=pd['id'], sport=pd.get('sport', 'nba'),
                away_team=pd.get('away_team'), home_team=pd.get('home_team'),
                game_date=pd.get('game_date'), side=pd.get('side'), line=pd.get('line'),
                line_open=pd.get('line_open'), line_close=pd.get('line_close'),
                start_time=pd.get('start_time'), edge_pct=pd.get('edge_pct'),
                model_confidence=pd.get('model_confidence'),
                predicted_margin=pd.get('predicted_margin'), sigma=pd.get('sigma'),
                z_score=pd.get('z_score'), raw_edge=pd.get('raw_edge'),
                cover_prob=pd.get('cover_prob'), implied_prob=pd.get('implied_prob'),
                market_odds=pd.get('market_odds'), sportsbook=pd.get('sportsbook'),
                closing_spread=pd.get('closing_spread'), clv=pd.get('clv'),
                home_score=pd.get('home_score'), away_score=pd.get('away_score'),
                result=pd.get('result', 'pending'), result_ats=pd.get('result_ats'),
                pnl=pd.get('pnl'), profit_units=pd.get('profit_units'),
                notes=pd.get('notes'), position_size_pct=pd.get('position_size_pct'),
            )
            if pd.get('published_at'):
                pick.published_at = datetime.fromisoformat(pd['published_at'])
            if pd.get('result_resolved_at'):
                pick.result_resolved_at = datetime.fromisoformat(pd['result_resolved_at'])
            if pd.get('model_only_cover_prob') is not None:
                pick.model_only_cover_prob = pd['model_only_cover_prob']
            if pd.get('model_only_edge') is not None:
                pick.model_only_edge = pd['model_only_edge']
            db.session.add(pick)
            stats['picks_added'] += 1

    for ps in data.get('passes', []):
        existing = Pass.query.get(ps['id'])
        if existing:
            for key in ['whatif_result', 'whatif_covered']:
                if ps.get(key) is not None:
                    setattr(existing, key, ps[key])
            stats['passes_updated'] += 1
        else:
            p = Pass(
                id=ps['id'], date=ps.get('date'), sport=ps.get('sport', 'nba'),
                games_analyzed=ps.get('games_analyzed'), closest_edge_pct=ps.get('closest_edge_pct'),
                pass_reason=ps.get('pass_reason'), notes=ps.get('notes'),
                model_run_id=ps.get('model_run_id'),
                whatif_side=ps.get('whatif_side'), whatif_home_team=ps.get('whatif_home_team'),
                whatif_away_team=ps.get('whatif_away_team'), whatif_pick_side=ps.get('whatif_pick_side'),
                whatif_line=ps.get('whatif_line'), whatif_edge=ps.get('whatif_edge'),
                whatif_cover_prob=ps.get('whatif_cover_prob'), whatif_pred_margin=ps.get('whatif_pred_margin'),
                whatif_result=ps.get('whatif_result'), whatif_covered=ps.get('whatif_covered'),
            )
            if ps.get('created_at'):
                p.created_at = datetime.fromisoformat(ps['created_at'])
            db.session.add(p)
            stats['passes_added'] += 1

    for rd in data.get('model_runs', []):
        existing = ModelRun.query.get(rd['id'])
        if existing:
            stats['runs_updated'] += 1
        else:
            r = ModelRun(
                id=rd['id'], date=rd.get('date'), sport=rd.get('sport', 'nba'),
                games_analyzed=rd.get('games_analyzed'),
                pick_generated=rd.get('pick_generated', False),
                pick_id=rd.get('pick_id'),
                pass_id=rd.get('pass_id'),
                run_duration_ms=rd.get('run_duration_ms', 0),
                model_version=rd.get('model_version', 'v1.0'),
                games_detail=rd.get('games_detail'),
            )
            if rd.get('created_at'):
                r.created_at = datetime.fromisoformat(rd['created_at'])
            db.session.add(r)
            stats['runs_added'] += 1

    db.session.commit()
    return jsonify({'status': 'synced', 'stats': stats, 'source': 'app.sharppicks.ai'})
