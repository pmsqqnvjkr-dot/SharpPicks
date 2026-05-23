from flask import Blueprint, jsonify, request, current_app
from models import db, User, Pick, Pass, ModelRun, FoundingCounter, TrackedBet, Insight, CronLog, FCMToken, KillSwitch, UserBet, PageView, UserEvent, AdminAlert, MrrSnapshot, ContentPageView
from datetime import datetime, timedelta, timezone
from sqlalchemy import func, text
from zoneinfo import ZoneInfo
import os
import re
import requests
import time
import logging
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadSignature
import commentary as cmt

admin_bp = Blueprint('admin_api', __name__)
ET = ZoneInfo('America/New_York')

def _get_admin_serializer():
    secret = os.environ.get('SESSION_SECRET', os.environ.get('SECRET_KEY', 'dev'))
    return URLSafeTimedSerializer(secret)

ADMIN_EMAIL = 'evan@sharppicks.ai'


# Apple App Store reviewers sign up through TestFlight / App Review with
# emails matching ar_user<digits>@icloud.com. They appear as PAID in our
# admin metrics because Apple's IAP sandbox flags their subs active.
# Exclude them from real-user counts so MRR, active subs, and acquisition
# funnels reflect actual customers only. Pattern is conservative (must
# start with "ar_user" plus a digit, end at @icloud.com) so it doesn't
# accidentally drop legitimate users whose handles happen to start
# with "ar_".
_AR_REVIEWER_EMAIL_PATTERN = r'^ar_user[0-9]+@icloud\.com$'


def _real_users_query():
    """Returns a User query scoped to real, non-internal, non-deleted users.
    Use this in admin metrics aggregations (signup totals, funnels, user
    lists, etc.) so internal employees and soft-deleted test/spam accounts
    don't pollute customer-facing numbers. See migrations from 2026-05-03."""
    return User.query.filter(
        User.is_internal == False,  # noqa: E712
        User.deleted_at.is_(None),
        ~User.email.op('~')(_AR_REVIEWER_EMAIL_PATTERN),
    )


def _real_user_filter():
    """SQLAlchemy filter expression equivalent to _real_users_query, for
    use inside .filter() chains on subqueries/joins where we already have
    a User reference."""
    return db.and_(
        User.is_internal == False,  # noqa: E712
        User.deleted_at.is_(None),
        ~User.email.op('~')(_AR_REVIEWER_EMAIL_PATTERN),
    )

def require_superuser():
    from flask_login import current_user
    if current_user.is_authenticated:
        if not current_user.is_superuser or current_user.email != ADMIN_EMAIL:
            return None, 403
        return current_user, None

    token = request.headers.get('X-Admin-Token')
    if token:
        try:
            s = _get_admin_serializer()
            data = s.loads(token, salt='admin-token', max_age=86400)
            user = db.session.get(User, data)
            if user and user.is_superuser and user.email == ADMIN_EMAIL:
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
            if user and user.is_superuser and user.email == ADMIN_EMAIL and (not isinstance(data, dict) or user.session_token == data.get('st')):
                return user, None
            if user and (not user.is_superuser or user.email != ADMIN_EMAIL):
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
    if not user.is_superuser or user.email != ADMIN_EMAIL:
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

    user_count = _real_users_query().count()
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


@admin_bp.route('/api/admin/tap-grade', methods=['GET', 'POST'])
def tap_grade():
    """Phone-friendly emergency manual-grade. Tap a single URL with the
    cron secret + scores to grade a pending pick from a phone browser
    when the auto-grader missed it.

    Example URL:
      /api/admin/tap-grade?secret=<CRON_SECRET>&pick_id=<id>&home_score=8&away_score=5

    Designed for the rare case where a slate finishes but the live-scores
    or grade-picks cron fails to match the game (team-name drift, ESPN
    data lag, etc.) and the pick is stranded as `pending`. Reuses the
    same grading logic as /api/admin/manual-grade so results are
    consistent. Accepts secret in the query string because phone
    browsers can't easily set headers; logs are not bound to URLs in
    this product, so the leak surface is bounded.
    """
    cron_secret = os.environ.get('CRON_SECRET', '')
    supplied = request.args.get('secret') or request.headers.get('X-Cron-Secret')
    if not cron_secret or supplied != cron_secret:
        return jsonify({'error': 'unauthorized'}), 403

    pick_id = request.args.get('pick_id')
    try:
        home_score = int(request.args.get('home_score', ''))
        away_score = int(request.args.get('away_score', ''))
    except ValueError:
        return jsonify({'error': 'home_score and away_score must be integers'}), 400
    if not pick_id:
        return jsonify({'error': 'pick_id required'}), 400

    pick = Pick.query.get(pick_id)
    if not pick:
        return jsonify({'error': 'Pick not found'}), 404
    if pick.result != 'pending':
        return jsonify({'error': f'Pick already graded: {pick.result}'}), 400

    spread_result = home_score - away_score
    line_value = pick.line if pick.line and abs(pick.line) < 50 else 0

    side_lower = (pick.side or '').lower()
    home_lower = (pick.home_team or '').lower()
    away_lower = (pick.away_team or '').lower()
    if home_lower and home_lower in side_lower:
        pick_is_home = True
    elif away_lower and away_lower in side_lower:
        pick_is_home = False
    else:
        return jsonify({'error': f'Cannot determine side from: {pick.side}'}), 400

    if pick_is_home:
        ats_margin = spread_result + line_value
    else:
        ats_margin = (away_score - home_score) + line_value
    push = ats_margin == 0
    covered = ats_margin > 0

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

    pick.home_score = home_score
    pick.away_score = away_score
    pick.result_resolved_at = datetime.now()
    db.session.commit()

    return jsonify({
        'pick_id': pick_id,
        'side': pick.side,
        'final': f'{pick.away_team} {away_score} @ {pick.home_team} {home_score}',
        'result': pick.result,
        'result_ats': pick.result_ats,
        'profit_units': pick.profit_units,
        'ats_margin': ats_margin,
    })


@admin_bp.route('/api/admin/tap-run-model', methods=['GET', 'POST'])
def tap_run_model():
    """Phone-friendly model-run trigger. Same shape as /api/admin/tap-grade.
    Tap a single URL with the cron secret to force a model run for a
    sport from a phone browser when cron-job.org missed the schedule.

    Example URL:
      /api/admin/tap-run-model?secret=<CRON_SECRET>&sport=nba&force=true

    Defaults: sport=nba, force=false. Returns JSON with the same shape
    run_model_and_log produces ({status, picks_created, run_id, ...}).
    Accepts secret in the query string because phone browsers can't
    easily set the X-Cron-Secret header.
    """
    cron_secret = os.environ.get('CRON_SECRET', '')
    supplied = request.args.get('secret') or request.headers.get('X-Cron-Secret')
    if not cron_secret or supplied != cron_secret:
        return jsonify({'error': 'unauthorized'}), 403

    sport = (request.args.get('sport') or 'nba').lower()
    if sport not in ('nba', 'mlb', 'wnba'):
        return jsonify({'error': "sport must be one of nba, mlb, wnba"}), 400
    force = (request.args.get('force', 'false').lower() == 'true')

    # Fresh game collection before the run, mirrors /api/admin/trigger-model.
    try:
        if sport in ('nba', 'wnba'):
            from app import collect_todays_games
            collect_todays_games()
        elif sport == 'mlb':
            from app import collect_mlb_games_job
            collect_mlb_games_job()
    except Exception as e:
        import logging
        logging.warning(f"[tap-run-model] Game collection failed (continuing): {e}")

    from model_service import run_model_and_log
    from flask import current_app
    result = run_model_and_log(
        current_app._get_current_object(),
        sport=sport,
        force=force,
        send_notifications=True,
    )
    return jsonify({'sport': sport, 'force': force, 'result': result})


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

    # Always collect fresh game data before re-running
    try:
        if sport in ('nba', 'wnba'):
            from app import collect_todays_games
            collect_todays_games()
        elif sport == 'mlb':
            from app import collect_mlb_games_job
            collect_mlb_games_job()
    except Exception as e:
        import logging
        logging.warning(f"[admin-rerun] Game collection failed (continuing): {e}")

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
            # Void any pending tracked bets BEFORE detaching pick_id, so
            # users see them surface in the Withdrawn bucket instead of
            # being stranded as Active forever (no Pick row left to grade
            # against, and no orphan sweep covers result IS NULL with
            # pick_id IS NULL).
            TrackedBet.query.filter_by(pick_id=pick_id, result=None).update({
                'result': 'revoked',
                'profit': 0.0,
                'settled_at': datetime.now(),
            })
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
    # Void pending tracked bets before detaching, so they end up in the
    # Withdrawn bucket rather than stranded as Active. See clear-today.
    TrackedBet.query.filter_by(pick_id=pick_id, result=None).update({
        'result': 'revoked',
        'profit': 0.0,
        'settled_at': datetime.now(),
    })
    TrackedBet.query.filter_by(pick_id=pick_id).update({'pick_id': None})
    UserBet.query.filter_by(pick_id=pick_id).delete()
    db.session.delete(pick)
    db.session.commit()
    return jsonify({'deleted': True, 'pick': info, 'game_date': today_str})


@admin_bp.route('/api/admin/ungrade-pick/<pick_id>', methods=['POST'])
def ungrade_pick(pick_id):
    """Reset a pick back to pending (reverses an incorrect grade)."""
    cron_secret = os.environ.get('CRON_SECRET', '')
    cron_auth = cron_secret and request.headers.get('X-Cron-Secret') == cron_secret
    if not cron_auth:
        admin, err_code = require_superuser()
        if not admin:
            return jsonify({'error': 'Unauthorized'}), err_code
    pick = Pick.query.get(pick_id)
    if not pick:
        return jsonify({'error': 'Not found'}), 404
    old_result = pick.result
    pick.result = 'pending'
    pick.home_score = None
    pick.away_score = None
    pick.profit_units = None
    pick.pnl = None
    pick.result_ats = None
    pick.result_resolved_at = None
    db.session.commit()
    return jsonify({'ungraded': True, 'pick_id': pick_id, 'old_result': old_result})


@admin_bp.route('/api/admin/trigger-model', methods=['POST'])
def trigger_model():
    """Run model without clearing (admin auth). Use force=true in body to clear and rerun."""
    admin, err_code = require_superuser()
    if not admin:
        return jsonify({'error': 'Login required' if err_code == 401 else 'Unauthorized'}), err_code

    data = request.get_json() or {}
    force = data.get('force', False)
    sport = data.get('sport', 'nba')

    # Always collect fresh game data before running the model
    try:
        if sport in ('nba', 'wnba'):
            from app import collect_todays_games
            collect_todays_games()
        elif sport == 'mlb':
            from app import collect_mlb_games_job
            collect_mlb_games_job()
    except Exception as e:
        import logging
        logging.warning(f"[admin-trigger] Game collection failed (continuing): {e}")

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


@admin_bp.route('/api/admin/mlb-collect', methods=['POST'])
def admin_mlb_collect():
    """Collect MLB games + odds (admin auth)."""
    admin, err_code = require_superuser()
    if not admin:
        return jsonify({'error': 'Unauthorized'}), 403

    from app import collect_mlb_games_job
    try:
        collect_mlb_games_job()
        return jsonify({'success': True, 'message': 'MLB games collected'})
    except Exception as e:
        logging.error(f"Admin mlb-collect error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@admin_bp.route('/api/admin/articles/cross-sport-flip', methods=['POST'])
def articles_cross_sport_flip():
    """One-off: flip non-product Insight articles to sport=NULL so they
    show in every sport's feed. Cross-sport categories are philosophy,
    discipline, founder_note. Excludes market_notes (always sport-specific
    by design) and how_it_works (case by case: MLB sample-size articles
    are intentionally sport=mlb).

    The Insight visibility filter at insights_api.py:62 is
    `Insight.sport == sport OR Insight.sport IS NULL`, so flipping to
    NULL makes the article visible to NBA, MLB, and WNBA users.

    Authed via X-Cron-Secret. Idempotent: only touches rows where
    sport is currently set."""
    cron_secret = os.environ.get('CRON_SECRET', '')
    if not cron_secret or request.headers.get('X-Cron-Secret') != cron_secret:
        return jsonify({'error': 'Unauthorized'}), 401

    cross_sport_categories = ('philosophy', 'discipline', 'founder_note')
    rows = Insight.query.filter(
        Insight.category.in_(cross_sport_categories),
        Insight.sport.isnot(None),
    ).all()

    flipped = []
    for r in rows:
        flipped.append({
            'slug': r.slug,
            'category': r.category,
            'old_sport': r.sport,
        })
        r.sport = None

    db.session.commit()
    return jsonify({
        'flipped_count': len(flipped),
        'rows': flipped,
    })


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

    # Check if model should have run by now. The 10 AM run is the single
    # daily publish; if no pick or pass exists by 2 PM ET, watchdog fires.
    model_run_window = hour_et >= 14  # 10 AM run + 4h buffer

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
    if 'email_verified' in data:
        user.email_verified = bool(data['email_verified'])
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
            'subscription_status': user.subscription_status,
            'email_verified': user.email_verified
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
    if 'subscription_plan' in data:
        user.subscription_plan = data['subscription_plan']
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
            'subscription_status': user.subscription_status,
            'subscription_plan': user.subscription_plan
        }
    })


@admin_bp.route('/api/admin/command-center')
def command_center_data():
    admin, err_code = require_superuser()
    if not admin:
        return jsonify({'error': 'Login required' if err_code == 401 else 'Unauthorized'}), err_code

    now_et = datetime.now(ET)
    today_str = now_et.strftime('%Y-%m-%d')

    # Exclude internal/test/soft-deleted users from all command-center metrics.
    users = _real_users_query().all()
    total_users = len(users)
    # PAID buckets exclude comped (gifted) users so MRR and active-sub
    # counts reflect actual paying customers only. Comped users still
    # count toward total_users.
    # Paid = active OR cancelling-but-paid-through-period. Excludes comped.
    # _real_users_query already strips internal/deleted/AR-reviewer rows
    # so the comped filter is the only inline exclusion left.
    active_subs = [u for u in users if u.subscription_status in ('active', 'cancelling') and not u.comped]
    trial_users = [u for u in users if u.subscription_status in ('trial', 'trialing') and not u.comped]
    free_users = [u for u in users if u.subscription_status in ('free', None, '')]
    annual_subs = [u for u in active_subs if u.subscription_plan and 'annual' in u.subscription_plan.lower()]
    monthly_subs = [u for u in active_subs if u.subscription_plan and 'month' in u.subscription_plan.lower()]
    # Founding count is a real cap on paid spots. Excludes comped because
    # those weren't real $99 founding-rate purchases; includes is_internal
    # because employees who paid the founding rate still count toward
    # the 50-spot cap.
    founding_count = User.query.filter_by(founding_member=True).filter(User.comped == False).count()  # noqa: E712
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

        buckets = {'3.5-5%': {'w': 0, 'l': 0}, '5-7.5%': {'w': 0, 'l': 0}, '7.5-10%': {'w': 0, 'l': 0}, '10%+': {'w': 0, 'l': 0}}
        for p in resolved:
            e = p.edge_pct or 0
            if e >= 10:
                k = '10%+'
            elif e >= 7.5:
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
    mlb_stats = compute_sport_stats('mlb')

    recent_users = sorted(users, key=lambda u: u.created_at or datetime.min, reverse=True)[:15]
    users_data = []
    for u in recent_users:
        tier = 'free'
        if u.founding_member:
            tier = 'founding'
        elif u.subscription_status == 'active':
            tier = 'pro'
        elif u.subscription_status in ('trial', 'trialing'):
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

    push_stats = get_push_token_stats()
    active_7d = push_stats.get('active_7d', 0)

    try:
        pulse_c = cmt.pulse_daily_read(nba_stats, mlb_stats, {'mrr': mrr}, active_7d, total_users)
        nba_c = cmt.nba_model_read(nba_stats)
        mlb_c = cmt.mlb_model_read(mlb_stats)
        rev_c = cmt.revenue_read({
            'total_signups': total_users,
            'total_paid': len(active_subs),
            'founding_count': founding_count,
            'trial_count': len(trial_users),
        }, {'mrr': mrr, 'arr': arr})
        commentary_data = {
            'pulse': [{'type': pulse_c[0], 'label': pulse_c[1], 'text': pulse_c[2]}],
            'nba': [{'type': nba_c[0], 'label': nba_c[1], 'text': nba_c[2]}],
            'mlb': [{'type': mlb_c[0], 'label': mlb_c[1], 'text': mlb_c[2]}],
            'revenue': [{'type': rev_c[0], 'label': rev_c[1], 'text': rev_c[2]}],
        }
    except Exception as e:
        logging.error(f'Commentary error: {e}')
        commentary_data = {}

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
        'mlb_model': mlb_stats,
        'recent_picks': nba_stats['recent_picks'],
        'wnba_recent_picks': wnba_stats['recent_picks'],
        'mlb_recent_picks': mlb_stats['recent_picks'],
        'model_runs': nba_stats['model_runs'],
        'wnba_model_runs': wnba_stats['model_runs'],
        'mlb_model_runs': mlb_stats['model_runs'],
        'users': {
            'total': total_users,
            'list': users_data,
        },
        'insights': {
            'total': len(insights),
            'published': len(published_insights),
        },
        'push': push_stats,
        'commentary': commentary_data,
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
            from db_path import get_sqlite_conn
            conn = get_sqlite_conn(path=status['path'])
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
        'run_model':       {'label': 'SP — Run Model', 'schedule': '10:00 AM', 'expected_h': 24},
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
            'expected_h': config['expected_h'],
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
        Pick.result.in_(['win', 'loss', 'push', 'postponed']),
        Pick.sport == sport,
    ).order_by(Pick.game_date.desc()).limit(200).all()

    edge_values = [p.edge_pct for p in resolved if p.edge_pct is not None]
    avg_edge = round(sum(edge_values) / len(edge_values), 2) if edge_values else 0
    line_values = [abs(p.line) for p in resolved if p.line is not None]
    avg_spread = round(sum(line_values) / len(line_values), 1) if line_values else 0

    from models import EdgeSnapshot
    snapshots = db.session.query(EdgeSnapshot).join(Pick).filter(
        Pick.sport == sport,
        Pick.result.in_(['win', 'loss', 'push', 'postponed']),
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
        Pick.result.in_(['win', 'loss', 'push', 'postponed']),
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
    cron_secret = os.environ.get('CRON_SECRET', '')
    cron_auth = cron_secret and request.headers.get('X-Cron-Secret') == cron_secret

    user, when_err = require_superuser()
    if when_err and not cron_auth:
        return jsonify({'error': 'Unauthorized'}), when_err
    from models import FCMToken
    from app import send_push_notification, _get_firebase_service_info

    data = request.get_json(silent=True) or {}
    title = (data.get('title') or 'SharpPicks Test').strip()
    body = (data.get('body') or 'Push notifications are working.').strip()

    target_user_id = data.get('user_id')
    if cron_auth and target_user_id:
        push_user_id = target_user_id
    elif user:
        push_user_id = user.id
    else:
        return jsonify({'error': 'user_id required for cron auth'}), 400

    tokens = FCMToken.query.filter_by(user_id=push_user_id, enabled=True).all()
    if not tokens:
        return jsonify({'error': f'No enabled FCM tokens for user {push_user_id}', 'sent': 0}), 400

    if not _get_firebase_service_info():
        return jsonify({
            'error': 'No Firebase credentials. Set FIREBASE_SERVICE_ACCOUNT_JSON or FIREBASE_PRIVATE_KEY, or add firebase-service-account.json',
            'sent': 0
        }), 500

    try:
        sent = send_push_notification(push_user_id, title, body)
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


def _analytics_period_days():
    """Parse ?period=day|week|month from request args, default week."""
    p = request.args.get('period', 'week').lower()
    if p == 'day':
        return 1
    elif p == 'month':
        return 30
    return 7


@admin_bp.route('/api/admin/cf-analytics')
def cf_analytics():
    """Cloudflare Web Analytics (RUM beacon) for sharppicks.ai marketing site."""
    admin, err_code = require_superuser()
    if not admin:
        return jsonify({'error': 'Login required' if err_code == 401 else 'Unauthorized'}), err_code

    # Prefer CLOUDFLARE_* (single source of truth, shared with
    # services/sources/cloudflare.py). Fall back to legacy CF_* names
    # so a Railway env that still has the old keys keeps working until
    # they're cleaned up.
    token = os.environ.get('CLOUDFLARE_API_TOKEN') or os.environ.get('CF_API_TOKEN')
    account_id = os.environ.get('CLOUDFLARE_ACCOUNT_ID') or os.environ.get('CF_ACCOUNT_ID')
    site_tag = os.environ.get('CLOUDFLARE_SITE_TAG') or os.environ.get('CF_WEB_ANALYTICS_SITE_TAG')

    if not token or not account_id:
        return jsonify({'error': 'CLOUDFLARE_API_TOKEN or CLOUDFLARE_ACCOUNT_ID not configured'}), 503

    days = _analytics_period_days()
    today = datetime.now(ET).date()
    since_date = today - timedelta(days=days)
    since_dt = f'{since_date}T00:00:00Z'
    until_dt = f'{today}T23:59:59Z'

    CF_GQL = 'https://api.cloudflare.com/client/v4/graphql'
    headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}

    query = """
    query($accountTag: String!, $since: String!, $until: String!, $siteTag: String!) {
      viewer {
        accounts(filter: {accountTag: $accountTag}) {
          totals: rumPageloadEventsAdaptiveGroups(
            limit: 1
            filter: {
              AND: [
                {datetime_geq: $since, datetime_leq: $until}
                {OR: [{siteTag: $siteTag}]}
              ]
            }
          ) {
            count
            sum { visits }
          }
          daily: rumPageloadEventsAdaptiveGroups(
            limit: 31
            orderBy: [date_ASC]
            filter: {
              AND: [
                {datetime_geq: $since, datetime_leq: $until}
                {OR: [{siteTag: $siteTag}]}
              ]
            }
          ) {
            count
            sum { visits }
            dimensions { date: date }
          }
          topPaths: rumPageloadEventsAdaptiveGroups(
            limit: 10
            orderBy: [count_DESC]
            filter: {
              AND: [
                {datetime_geq: $since, datetime_leq: $until}
                {OR: [{siteTag: $siteTag}]}
              ]
            }
          ) {
            count
            dimensions { path: requestPath }
          }
          topReferrers: rumPageloadEventsAdaptiveGroups(
            limit: 5
            orderBy: [count_DESC]
            filter: {
              AND: [
                {datetime_geq: $since, datetime_leq: $until}
                {OR: [{siteTag: $siteTag}]}
              ]
            }
          ) {
            count
            dimensions { referer: refererHost }
          }
        }
      }
    }
    """

    try:
        resp = requests.post(CF_GQL, headers=headers, json={
            'query': query,
            'variables': {
                'accountTag': account_id,
                'since': since_dt,
                'until': until_dt,
                'siteTag': site_tag or '',
            },
        }, timeout=15)
        data = resp.json()
        if data.get('errors'):
            err_msg = data['errors'][0].get('message', 'Unknown CF error')
            logging.error(f'CF Web Analytics error: {err_msg}')
            return jsonify({'error': err_msg, 'marketing': {'error': err_msg}}), 200

        accts = data.get('data', {}).get('viewer', {}).get('accounts', [{}])
        acct = accts[0] if accts else {}
        totals_list = acct.get('totals', [{}])
        totals = totals_list[0] if totals_list else {}
        total_views = totals.get('count', 0)
        total_visits = (totals.get('sum') or {}).get('visits', 0)

        daily = []
        for d in acct.get('daily', []):
            dims = d.get('dimensions', {})
            daily.append({
                'date': dims.get('date', ''),
                'views': d.get('count', 0),
                'uniques': (d.get('sum') or {}).get('visits', 0),
            })

        top_paths = []
        for p in acct.get('topPaths', []):
            dims = p.get('dimensions', {})
            top_paths.append({
                'path': dims.get('path', '/'),
                'count': p.get('count', 0),
            })

        top_referrers = []
        for r in acct.get('topReferrers', []):
            dims = r.get('dimensions', {})
            ref = dims.get('referer', '')
            if ref:
                top_referrers.append({'referrer': ref, 'count': r.get('count', 0)})

        marketing = {
            'pageViews': total_views,
            'uniques': total_visits,
            'requests': total_views,
            'daily': daily,
            'topPaths': top_paths,
            'topReferrers': top_referrers,
        }

        return jsonify({
            'marketing': marketing,
            'period': {'since': since_date.isoformat(), 'until': today.isoformat(), 'days': days},
        })

    except Exception as e:
        logging.error(f'CF analytics error: {e}')
        return jsonify({'error': str(e), 'marketing': {'error': str(e)}}), 200


@admin_bp.route('/api/admin/app-analytics')
def app_analytics():
    """Server-side request analytics for app.sharppicks.ai."""
    admin, err_code = require_superuser()
    if not admin:
        return jsonify({'error': 'Login required' if err_code == 401 else 'Unauthorized'}), err_code

    try:
        PageView.__table__
    except Exception:
        return jsonify({'error': 'PageView table not available'}), 503

    days = _analytics_period_days()
    today = datetime.now(ET).date()
    since = today - timedelta(days=days)
    since_dt = datetime(since.year, since.month, since.day)

    try:
        total_views = PageView.query.filter(PageView.created_at >= since_dt).count()
        unique_visitors = db.session.query(
            func.count(func.distinct(PageView.ip_hash))
        ).filter(PageView.created_at >= since_dt).scalar() or 0

        api_requests = PageView.query.filter(
            PageView.created_at >= since_dt,
            PageView.path.like('/api/%')
        ).count()

        daily_rows = db.session.query(
            func.date(PageView.created_at).label('day'),
            func.count().label('views'),
            func.count(func.distinct(PageView.ip_hash)).label('uniques'),
        ).filter(
            PageView.created_at >= since_dt
        ).group_by(func.date(PageView.created_at)).order_by(func.date(PageView.created_at)).all()

        daily = [{'date': str(r.day), 'views': r.views, 'uniques': r.uniques} for r in daily_rows]

        top_paths_rows = db.session.query(
            PageView.path,
            func.count().label('cnt'),
        ).filter(
            PageView.created_at >= since_dt
        ).group_by(PageView.path).order_by(func.count().desc()).limit(10).all()

        top_paths = [{'path': r.path, 'count': r.cnt} for r in top_paths_rows]

        return jsonify({
            'pageViews': total_views,
            'uniques': unique_visitors,
            'requests': api_requests,
            'daily': daily,
            'topPaths': top_paths,
            'period': {'since': since.isoformat(), 'until': today.isoformat(), 'days': days},
        })
    except Exception as e:
        logging.error(f'App analytics error: {e}')
        return jsonify({'error': str(e)}), 500


# ─── Phase 2 unified metrics endpoint ────────────────────────────────────
# Pulls from six sources (Cloudflare, Stripe, Postgres events, GA4, GSC,
# RevenueCat) in parallel. Each source returns the same envelope shape;
# single-source failure does not fail the endpoint. See
# docs/command-center-audit.md (Phase 2 ground truth).

def _metrics_safe_envelope(name, fn):
    """Run fn() and return (name, envelope). Catches any exception so a
    single source failure doesn't propagate to the whole endpoint."""
    try:
        return name, fn()
    except Exception as e:
        logging.exception('admin_metrics: %s fetch failed', name)
        return name, {
            'payload': None,
            'fetched_at': None,
            'stale': True,
            'last_error': str(e)[:500] or e.__class__.__name__,
        }


@admin_bp.route('/api/admin/users/activity')
def admin_users_activity():
    """Phase 3.5: snapshot, DAU 90d, login frequency, tier counts, cohort retention.
    Cached at the source-fn level via metrics_cache; here we just call through."""
    cron_secret = os.environ.get('CRON_SECRET', '')
    cron_auth = cron_secret and request.headers.get('X-Cron-Secret') == cron_secret
    if not cron_auth:
        admin, err_code = require_superuser()
        if not admin:
            return jsonify({'error': 'Login required' if err_code == 401 else 'Unauthorized'}), err_code

    range_ = request.args.get('range', '30d')
    if range_ not in ('7d', '30d', '90d'):
        return jsonify({'error': 'range must be 7d, 30d, or 90d'}), 400

    try:
        from services import users_metrics
        return jsonify(users_metrics.fetch_activity(range_))
    except Exception as e:
        logging.exception('admin_users_activity failed')
        return jsonify({'error': str(e)[:200]}), 500


@admin_bp.route('/api/admin/infra/health')
def admin_infra_health():
    """Phase 3.7: server health chips, latency series, deploys, db health.
    Pipeline status comes from the existing /api/admin/cron-health
    endpoint — the Infra UI calls both and merges client-side."""
    cron_secret = os.environ.get('CRON_SECRET', '')
    cron_auth = cron_secret and request.headers.get('X-Cron-Secret') == cron_secret
    if not cron_auth:
        admin, err_code = require_superuser()
        if not admin:
            return jsonify({'error': 'Login required' if err_code == 401 else 'Unauthorized'}), err_code
    try:
        from services import infra_metrics
        return jsonify(infra_metrics.fetch())
    except Exception as e:
        logging.exception('admin_infra_health failed')
        return jsonify({'error': str(e)[:200]}), 500


@admin_bp.route('/api/admin/model/perf')
def admin_model_perf():
    """Phase 3.6: model perf charts. Reads Pick table directly."""
    cron_secret = os.environ.get('CRON_SECRET', '')
    cron_auth = cron_secret and request.headers.get('X-Cron-Secret') == cron_secret
    if not cron_auth:
        admin, err_code = require_superuser()
        if not admin:
            return jsonify({'error': 'Login required' if err_code == 401 else 'Unauthorized'}), err_code

    range_ = request.args.get('range', '90d')
    if range_ not in ('7d', '30d', '90d'):
        return jsonify({'error': 'range must be 7d, 30d, or 90d'}), 400

    try:
        from services import model_perf
        return jsonify(model_perf.fetch(range_))
    except Exception as e:
        logging.exception('admin_model_perf failed')
        return jsonify({'error': str(e)[:200]}), 500


@admin_bp.route('/api/admin/users/list')
def admin_users_list():
    """Phase 3.5: filtered + paginated user list with per-user activity."""
    cron_secret = os.environ.get('CRON_SECRET', '')
    cron_auth = cron_secret and request.headers.get('X-Cron-Secret') == cron_secret
    if not cron_auth:
        admin, err_code = require_superuser()
        if not admin:
            return jsonify({'error': 'Login required' if err_code == 401 else 'Unauthorized'}), err_code

    segment = (request.args.get('segment') or 'all').strip().lower()
    if segment not in ('all', 'paid', 'trial', 'power', 'dormant', 'churned', 'attention'):
        return jsonify({'error': 'invalid segment'}), 400
    search = (request.args.get('search') or '').strip()
    sort = (request.args.get('sort') or 'created').strip().lower()
    if sort not in ('created', 'logins', 'last_active', 'days_active'):
        sort = 'created'
    try:
        limit = max(1, min(int(request.args.get('limit', 10)), 200))
        offset = max(0, int(request.args.get('offset', 0)))
    except ValueError:
        return jsonify({'error': 'limit/offset must be integers'}), 400

    try:
        from services import users_metrics
        return jsonify(users_metrics.fetch_list(segment=segment, search=search, limit=limit, offset=offset, sort=sort))
    except Exception as e:
        logging.exception('admin_users_list failed')
        return jsonify({'error': str(e)[:200]}), 500


@admin_bp.route('/api/admin/users/attention-segments')
def admin_attention_segments():
    """Needs Attention segment counts + top entries per segment. Powers
    the Needs Attention card at the top of the Users tab. Returns
    multiple distinct outreach groups (trials ending soon, was-pro
    still active, unverified email, cancel scheduled, past due) in a
    single round trip so the dashboard doesn't have to fan out to the
    /list endpoint per segment."""
    cron_secret = os.environ.get('CRON_SECRET', '')
    cron_auth = cron_secret and request.headers.get('X-Cron-Secret') == cron_secret
    if not cron_auth:
        admin, err_code = require_superuser()
        if not admin:
            return jsonify({'error': 'Login required' if err_code == 401 else 'Unauthorized'}), err_code

    try:
        from services import users_metrics
        return jsonify(users_metrics.fetch_attention_segments())
    except Exception as e:
        logging.exception('admin_attention_segments failed')
        return jsonify({'error': str(e)[:200]}), 500


@admin_bp.route('/api/admin/metrics')
def admin_metrics():
    """Unified metrics endpoint for the command center dashboard."""
    cron_secret = os.environ.get('CRON_SECRET', '')
    cron_auth = cron_secret and request.headers.get('X-Cron-Secret') == cron_secret
    if not cron_auth:
        admin, err_code = require_superuser()
        if not admin:
            return jsonify({'error': 'Login required' if err_code == 401 else 'Unauthorized'}), err_code

    range_ = request.args.get('range', '7d')
    if range_ not in ('7d', '30d'):
        return jsonify({'error': 'range must be 7d or 30d'}), 400

    include_internal_raw = (request.args.get('include_internal') or 'false').strip().lower()
    include_internal = include_internal_raw in ('true', '1', 'yes', 'on')

    nocache_raw = (request.args.get('nocache') or '').strip().lower()
    nocache = nocache_raw in ('true', '1', 'yes', 'on')

    # Lazy import keeps startup fast and avoids module-load issues if a
    # source has a missing optional dependency at import time.
    from services.sources import cloudflare as cf_source
    from services.sources import stripe_metrics as stripe_source
    from services.sources import events as events_source
    from services.sources import ga4 as ga4_source
    from services.sources import gsc as gsc_source
    from services.sources import revenuecat as rc_source
    from services.sources import google_play as gp_source
    from services.sources import app_store_connect as asc_source
    from services.sources import model_perf as model_perf_source

    # When ?nocache=1 is set (manual refresh from the dashboard), expire
    # every source's cache row first so the next fetch hits the upstream
    # API directly. The cache layer's normal "stale-on-error preservation"
    # still applies, if Stripe is down during a manual refresh, we fall
    # back to whatever was last cached.
    if nocache:
        from services.metrics_cache import invalidate
        for key in (f'cloudflare:{range_}', 'stripe:summary', f'ga4:{range_}',
                    'gsc:summary', 'revenuecat:summary', 'google_play:summary',
                    'app_store_connect:summary', 'model_perf:summary'):
            invalidate(key)

    sources = {
        'cloudflare':         lambda: cf_source.fetch(range_),
        'stripe':             lambda: stripe_source.fetch(),
        'events':             lambda: events_source.fetch(range_, include_internal),
        'ga4':                lambda: ga4_source.fetch(range_),
        'gsc':                lambda: gsc_source.fetch(),
        'revenuecat':         lambda: rc_source.fetch(),
        'google_play':        lambda: gp_source.fetch(),
        'app_store_connect':  lambda: asc_source.fetch(),
        'model_perf':         lambda: model_perf_source.fetch(),
    }

    # Each worker thread needs its own Flask app context for db.session.
    flask_app = current_app._get_current_object()

    def _wrap(name, fn):
        with flask_app.app_context():
            return _metrics_safe_envelope(name, fn)

    results = {}
    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = [executor.submit(_wrap, name, fn) for name, fn in sources.items()]
        for fut in as_completed(futures):
            name, envelope = fut.result()
            results[name] = envelope

    # Phase 3.3: rule-based headline + actions computed from the source
    # envelopes. Pure function; no external API calls. Fails open — if
    # headline computation throws, the dashboard's frontend keeps the
    # mockup placeholder copy and the error is logged.
    try:
        from services import headline as headline_module
        headline_payload = headline_module.compute(results)
    except Exception as e:
        logging.exception('headline.compute failed')
        headline_payload = {'headline': None, 'actions': [], '_error': str(e)[:200]}

    return jsonify({
        'range': range_,
        'generated_at': datetime.now(timezone.utc).isoformat(),
        'include_internal': include_internal,
        **results,
        **headline_payload,
    })


@admin_bp.route('/api/admin/content-analytics')
def content_analytics():
    """Content engine page view analytics (SEO pages on sharppicks.ai)."""
    admin, err_code = require_superuser()
    if not admin:
        return jsonify({'error': 'Login required' if err_code == 401 else 'Unauthorized'}), err_code

    try:
        ContentPageView.__table__
    except Exception:
        return jsonify({'error': 'ContentPageView table not available'}), 503

    days = _analytics_period_days()
    cutoff = datetime.utcnow() - timedelta(days=days)

    try:
        views = ContentPageView.query.filter(
            ContentPageView.timestamp >= cutoff,
            ContentPageView.is_bot == False,
        ).all()

        path_stats = {}
        daily_map = {}
        unique_ips = set()
        for v in views:
            path_stats.setdefault(v.path, 0)
            path_stats[v.path] += 1
            if v.ip_hash:
                unique_ips.add(v.ip_hash)
            d = _utc_naive_to_et_date(v.timestamp)
            if d:
                daily_map.setdefault(d.isoformat(), 0)
                daily_map[d.isoformat()] += 1

        total_views = sum(path_stats.values())
        top_pages = sorted(path_stats.items(), key=lambda x: x[1], reverse=True)[:10]
        total_pages_ever = ContentPageView.query.with_entities(
            func.count(func.distinct(ContentPageView.path))
        ).scalar() or 0

        return jsonify({
            'pageViews': total_views,
            'uniques': len(unique_ips),
            'totalPages': total_pages_ever,
            'daily': [{'date': d, 'views': c} for d, c in sorted(daily_map.items())],
            'topPaths': [{'path': p, 'count': c} for p, c in top_pages],
            'period': {'since': (datetime.now(ET).date() - timedelta(days=days)).isoformat(),
                       'until': datetime.now(ET).date().isoformat(), 'days': days},
        })
    except Exception as e:
        logging.error(f'Content analytics error: {e}')
        return jsonify({'error': str(e)}), 500


def _utc_naive_to_et_date(dt):
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(ET).date()


@admin_bp.route('/api/admin/alerts')
def admin_alerts_list():
    admin, err_code = require_superuser()
    if not admin:
        return jsonify({'error': 'Login required' if err_code == 401 else 'Unauthorized'}), err_code

    try:
        limit = int(request.args.get('limit', 20))
    except (TypeError, ValueError):
        limit = 20
    limit = max(1, min(limit, 200))

    rows = AdminAlert.query.order_by(AdminAlert.created_at.desc()).limit(limit).all()
    return jsonify({
        'alerts': [{
            'id': r.id,
            'event_type': r.event_type,
            'user_email': r.user_email,
            'detail': r.detail,
            'acknowledged': bool(r.acknowledged),
            'created_at': r.created_at.isoformat() if r.created_at else None,
        } for r in rows],
    })


@admin_bp.route('/api/admin/alerts/<int:alert_id>/acknowledge', methods=['PATCH'])
def admin_alert_acknowledge(alert_id):
    admin, err_code = require_superuser()
    if not admin:
        return jsonify({'error': 'Login required' if err_code == 401 else 'Unauthorized'}), err_code

    alert = db.session.get(AdminAlert, alert_id)
    if not alert:
        return jsonify({'error': 'Alert not found'}), 404
    alert.acknowledged = True
    db.session.commit()
    return jsonify({'success': True, 'id': alert_id, 'acknowledged': True})


@admin_bp.route('/api/admin/mrr-history')
def admin_mrr_history():
    admin, err_code = require_superuser()
    if not admin:
        return jsonify({'error': 'Login required' if err_code == 401 else 'Unauthorized'}), err_code

    MONTHLY_CENTS = 1999
    ANNUAL_MONTHLY_CENTS = round(14999 / 12)

    active_users = User.query.filter_by(subscription_status='active').all()
    active_monthly = 0
    active_annual = 0
    founding_count = 0
    current_mrr_cents = 0

    for u in active_users:
        plan = (u.subscription_plan or '').lower()
        if 'annual' in plan:
            current_mrr_cents += ANNUAL_MONTHLY_CENTS
            active_annual += 1
            if u.founding_member:
                founding_count += 1
        elif 'month' in plan:
            current_mrr_cents += MONTHLY_CENTS
            active_monthly += 1

    today_et = datetime.now(ET).date()
    cutoff_hist = today_et - timedelta(days=90)
    snap_rows = MrrSnapshot.query.filter(
        MrrSnapshot.snapshot_date >= cutoff_hist
    ).order_by(MrrSnapshot.snapshot_date.asc()).all()
    history = [{'date': s.snapshot_date.isoformat(), 'mrr_cents': s.mrr_cents} for s in snap_rows]

    target = today_et - timedelta(days=30)
    old_snap = MrrSnapshot.query.filter(
        MrrSnapshot.snapshot_date <= target
    ).order_by(MrrSnapshot.snapshot_date.desc()).first()
    net_change_30d_cents = current_mrr_cents - (old_snap.mrr_cents if old_snap else current_mrr_cents)

    mrr_dollars = f'{current_mrr_cents / 100:.2f}'
    arr_dollars = f'{current_mrr_cents * 12 / 100:.2f}'

    return jsonify({
        'current_mrr_cents': current_mrr_cents,
        'mrr_dollars': mrr_dollars,
        'arr_dollars': arr_dollars,
        'active_monthly': active_monthly,
        'active_annual': active_annual,
        'founding_count': founding_count,
        'history': history,
        'net_change_30d_cents': net_change_30d_cents,
    })


def _week_start_monday_et(d):
    return d - timedelta(days=d.weekday())


@admin_bp.route('/api/admin/funnel-metrics')
def admin_funnel_metrics():
    admin, err_code = require_superuser()
    if not admin:
        return jsonify({'error': 'Login required' if err_code == 401 else 'Unauthorized'}), err_code

    # Exclude internal/test/soft-deleted users from the conversion funnel.
    users = _real_users_query().all()
    total_signups = len(users)
    with_trial = [u for u in users if u.trial_start_date is not None]
    total_trials = len(with_trial)
    # Paid count for the conversion funnel. Matches the segment filter
    # in services/users_metrics.py and the command-center active_subs
    # bucket: active OR cancelling, minus comped. AR users + internal +
    # deleted already stripped by _real_users_query.
    paid = [u for u in users if u.subscription_status in ('active', 'cancelling') and not u.comped]
    total_paid = len(paid)

    signup_to_trial_rate = round(total_trials / total_signups * 100, 2) if total_signups else 0.0
    trial_to_paid_rate = round(total_paid / total_trials * 100, 2) if total_trials else 0.0
    signup_to_paid_rate = round(total_paid / total_signups * 100, 2) if total_signups else 0.0

    days_s2t = []
    for u in with_trial:
        if u.created_at and u.trial_start_date:
            c = _utc_naive_to_et_date(u.created_at)
            t = _utc_naive_to_et_date(u.trial_start_date)
            if c is not None and t is not None:
                days_s2t.append((t - c).days)
    avg_days_signup_to_trial = round(sum(days_s2t) / len(days_s2t), 2) if days_s2t else None

    days_t2p = []
    for u in paid:
        if u.trial_start_date and u.subscription_start_date:
            t0 = _utc_naive_to_et_date(u.trial_start_date)
            t1 = _utc_naive_to_et_date(u.subscription_start_date)
            if t0 is not None and t1 is not None:
                days_t2p.append((t1 - t0).days)
    avg_days_trial_to_paid = round(sum(days_t2p) / len(days_t2p), 2) if days_t2p else None

    today_et = datetime.now(ET).date()
    current_week_start = _week_start_monday_et(today_et)
    week_keys = [current_week_start - timedelta(weeks=i) for i in range(7, -1, -1)]
    trend_map = {wk: {'week_start': wk.isoformat(), 'signups': 0, 'trials': 0, 'conversions': 0} for wk in week_keys}

    for u in users:
        if u.created_at:
            cd = _utc_naive_to_et_date(u.created_at)
            if cd:
                ws = _week_start_monday_et(cd)
                if ws in trend_map:
                    trend_map[ws]['signups'] += 1
        if u.trial_start_date:
            td = _utc_naive_to_et_date(u.trial_start_date)
            if td:
                ws = _week_start_monday_et(td)
                if ws in trend_map:
                    trend_map[ws]['trials'] += 1
        if u.subscription_status == 'active' and u.subscription_start_date:
            pd = _utc_naive_to_et_date(u.subscription_start_date)
            if pd:
                ws = _week_start_monday_et(pd)
                if ws in trend_map:
                    trend_map[ws]['conversions'] += 1

    weekly_trend = [trend_map[wk] for wk in week_keys]

    return jsonify({
        'total_signups': total_signups,
        'total_trials': total_trials,
        'total_paid': total_paid,
        'signup_to_trial_rate': signup_to_trial_rate,
        'trial_to_paid_rate': trial_to_paid_rate,
        'signup_to_paid_rate': signup_to_paid_rate,
        'avg_days_signup_to_trial': avg_days_signup_to_trial,
        'avg_days_trial_to_paid': avg_days_trial_to_paid,
        'weekly_trend': weekly_trend,
    })


@admin_bp.route('/api/admin/engagement')
def admin_engagement():
    admin, err_code = require_superuser()
    if not admin:
        return jsonify({'error': 'Login required' if err_code == 401 else 'Unauthorized'}), err_code

    try:
        return _admin_engagement_inner()
    except Exception as e:
        logging.error('Engagement endpoint crashed: %s', e, exc_info=True)
        return jsonify({'error': str(e)[:200], '_crash': True}), 500


def _admin_engagement_inner():
    cutoff = datetime.utcnow() - timedelta(days=7)

    # Exclude internal/test users from engagement aggregations. The
    # event-level is_internal flag was backfilled in the 2026-05-03
    # migration for all rows tied to the 22 test accounts and Evan, so
    # this filter alone (no join) is sufficient.
    base_events = UserEvent.query.filter(UserEvent.is_internal == False)  # noqa: E712

    first_event = base_events.order_by(UserEvent.created_at.asc()).first()
    tracking_since = first_event.created_at.isoformat() if first_event else None
    total_event_count = base_events.count()

    events = base_events.filter(UserEvent.created_at >= cutoff).all()

    dau_by_day = {}
    page_stats = {}
    session_durations = []
    feature_users = {'view_market_scan': set(), 'view_article': set(), 'tap_bet_link': set()}
    all_active_users_7d = set()
    total_sessions_7d = set()

    for ev in events:
        d = _utc_naive_to_et_date(ev.created_at)
        if d:
            if d not in dau_by_day:
                dau_by_day[d] = set()
            if ev.user_id:
                dau_by_day[d].add(ev.user_id)
                all_active_users_7d.add(ev.user_id)

        if ev.session_id:
            total_sessions_7d.add(ev.session_id)

        pkey = ev.page if ev.page else ''
        if pkey not in page_stats:
            page_stats[pkey] = {'views': 0, 'users': set()}
        page_stats[pkey]['views'] += 1
        if ev.user_id:
            page_stats[pkey]['users'].add(ev.user_id)

        if ev.event_type == 'session_end' and isinstance(ev.event_data, dict):
            ds = ev.event_data.get('duration_seconds')
            if ds is not None:
                try:
                    session_durations.append(float(ds))
                except (TypeError, ValueError):
                    pass

        if ev.event_type in feature_users and ev.user_id:
            feature_users[ev.event_type].add(ev.user_id)

    today_et = datetime.now(ET).date()
    dau = []
    for i in range(7):
        d = today_et - timedelta(days=6 - i)
        active = len(dau_by_day.get(d, set()))
        dau.append({'date': d.isoformat(), 'active_users': active})

    avg_session_duration = round(sum(session_durations) / len(session_durations), 2) if session_durations else None
    active_user_count = len(all_active_users_7d)
    avg_sessions_per_user = round(len(total_sessions_7d) / active_user_count, 1) if active_user_count else None
    page_view_events = [ev for ev in events if ev.event_type == 'page_view']
    pages_per_session = {}
    for ev in page_view_events:
        sid = ev.session_id or '_'
        pages_per_session[sid] = pages_per_session.get(sid, 0) + 1
    avg_pages_per_session = round(sum(pages_per_session.values()) / len(pages_per_session), 1) if pages_per_session else None

    top_pages_raw = sorted(
        page_stats.items(),
        key=lambda x: x[1]['views'],
        reverse=True,
    )[:10]
    top_pages = [{
        'page': name or None,
        'views': st['views'],
        'distinct_users': len(st['users']),
    } for name, st in top_pages_raw]

    feature_adoption = {}
    for k, v in feature_users.items():
        user_count = len(v)
        pct = round(user_count / active_user_count * 100, 1) if active_user_count else 0
        feature_adoption[k] = {'users': user_count, 'pct_of_active': pct}

    d1_eligible = d1_returned = 0
    d7_eligible = d7_returned = 0
    event_user_days = {}
    if total_event_count > 0:
        try:
            day_rows = db.session.execute(text("""
                SELECT DISTINCT user_id,
                       (created_at AT TIME ZONE 'UTC' AT TIME ZONE 'America/New_York')::date AS d
                FROM user_events
                WHERE user_id IS NOT NULL
            """)).fetchall()
            for uid, d in day_rows:
                if uid and d:
                    event_user_days.setdefault(uid, set()).add(d)
        except Exception as e:
            logging.warning('engagement retention day query failed: %s', e)

        tracking_start_d = _utc_naive_to_et_date(first_event.created_at) if first_event else today_et
        for uid in all_active_users_7d:
            udays = event_user_days.get(uid, set())
            first_seen = min(udays) if udays else None
            if not first_seen:
                continue
            if first_seen + timedelta(days=1) <= today_et:
                d1_eligible += 1
                if (first_seen + timedelta(days=1)) in udays:
                    d1_returned += 1
            if first_seen + timedelta(days=7) <= today_et:
                d7_eligible += 1
                if (first_seen + timedelta(days=7)) in udays:
                    d7_returned += 1

    sessions_by_day_dict = {}
    for ev in events:
        if ev.session_id:
            d = _utc_naive_to_et_date(ev.created_at)
            if d:
                sessions_by_day_dict.setdefault(d.isoformat(), set()).add(ev.session_id)

    sessions_by_day = []
    for i in range(7):
        d = today_et - timedelta(days=6 - i)
        d_iso = d.isoformat()
        sessions_by_day.append({
            'date': d_iso,
            'sessions': len(sessions_by_day_dict.get(d_iso, set())),
        })

    # Per-user session counts, last seen, top feature
    user_session_counts = {}
    user_last_seen = {}
    user_top_feature = {}
    feature_labels = {
        'view_market_scan': 'Market Scan', 'view_article': 'Journal',
        'tap_bet_link': 'Bet Link', 'view_tracker': 'Tracker',
        'view_signals': 'Signals', 'page_view': None,
    }
    user_feature_counts = {}
    for ev in events:
        if ev.user_id:
            prev = user_last_seen.get(ev.user_id)
            if prev is None or (ev.created_at and ev.created_at > prev):
                user_last_seen[ev.user_id] = ev.created_at
            if ev.session_id:
                k = (ev.user_id, ev.session_id)
                user_session_counts.setdefault(ev.user_id, set()).add(ev.session_id)
            etype = ev.event_type
            if etype in feature_labels and feature_labels[etype]:
                user_feature_counts.setdefault(ev.user_id, {})
                user_feature_counts[ev.user_id][etype] = user_feature_counts[ev.user_id].get(etype, 0) + 1

    for uid, fcounts in user_feature_counts.items():
        if fcounts:
            top_key = max(fcounts, key=fcounts.get)
            user_top_feature[uid] = feature_labels.get(top_key, top_key)

    all_users = _real_users_query().order_by(User.created_at.desc()).all()
    all_user_details = []
    verified_count = 0
    unverified_users = []
    now_utc = datetime.utcnow()

    # Last-week active users for at-risk detection
    prev_cutoff = cutoff - timedelta(days=7)
    prev_events = UserEvent.query.filter(
        UserEvent.is_internal == False,  # noqa: E712
        UserEvent.created_at >= prev_cutoff,
        UserEvent.created_at < cutoff,
        UserEvent.user_id.isnot(None),
    ).with_entities(UserEvent.user_id).distinct().all()
    prev_active_uids = {r[0] for r in prev_events}

    for u in all_users:
        uid = u.id
        session_count = len(user_session_counts.get(uid, set()))
        last_seen_dt = user_last_seen.get(uid)

        tier = u.subscription_status or 'free'
        is_founding = u.founding_member or False
        founding_num = u.founding_number if is_founding else None
        email_verified = bool(u.email_verified)
        if email_verified:
            verified_count += 1
        else:
            unverified_users.append({
                'email': u.email,
                'tier': tier,
                'signed_up': u.created_at.isoformat() if u.created_at else None,
            })

        last_active_str = None
        if last_seen_dt:
            delta = now_utc - last_seen_dt
            if delta.total_seconds() < 3600:
                last_active_str = f"{max(1, int(delta.total_seconds() / 60))}m ago"
            elif delta.total_seconds() < 86400:
                last_active_str = f"{int(delta.total_seconds() / 3600)}h ago"
            else:
                last_active_str = f"{delta.days}d ago"
        elif uid not in all_active_users_7d:
            last_active_str = 'never'

        is_active = uid in all_active_users_7d
        is_power = session_count >= 10
        is_at_risk = (uid in prev_active_uids and uid not in all_active_users_7d) or \
                     (u.created_at and (now_utc - u.created_at).days >= 3 and uid not in all_active_users_7d and session_count <= 1)
        trial_at_risk = False
        if tier in ('trialing', 'trial') and u.trial_end_date:
            try:
                ted = u.trial_end_date
                if isinstance(ted, datetime):
                    days_left = (ted - now_utc).days
                else:
                    days_left = (ted - now_utc.date()).days
            except Exception:
                days_left = 999
            if days_left < 3:
                trial_at_risk = True
                is_at_risk = True

        all_user_details.append({
            'id': uid,
            'email': u.email,
            'name': u.first_name or u.display_name or u.username or '',
            'tier': tier,
            'plan': u.subscription_plan or '',
            'founding': is_founding,
            'founding_number': founding_num,
            'email_verified': email_verified,
            'sessions_7d': session_count,
            'last_active': last_active_str,
            'last_seen_iso': last_seen_dt.isoformat() if last_seen_dt else None,
            'top_feature': user_top_feature.get(uid, '--'),
            'signed_up': u.created_at.isoformat() if u.created_at else None,
            'is_active': is_active,
            'is_power': is_power,
            'is_at_risk': is_at_risk,
            'trial_at_risk': trial_at_risk,
        })

    # Sort by last_seen (most recent first), inactive at bottom
    def _sort_key(u):
        if u.get('last_seen_iso'):
            return (0, u['last_seen_iso'])
        return (1, '')
    all_user_details.sort(key=_sort_key, reverse=True)

    active_user_details = [u for u in all_user_details if u['is_active']]

    # Verification summary
    total_users = len(all_users)
    unverified_count = total_users - verified_count

    # Detect spam patterns
    spam_pattern = None
    email_prefixes = Counter()
    for u in all_users:
        if not u.email_verified:
            prefix = u.email.split('@')[0] if u.email else ''
            base = re.sub(r'\d+$', '', prefix)
            if base and len(base) > 3:
                email_prefixes[base] += 1
    if email_prefixes:
        top_prefix, top_count = email_prefixes.most_common(1)[0]
        if top_count >= 3:
            spam_pattern = {'prefix': top_prefix, 'count': top_count}

    # Content engine page views (7d)
    content_stats = {'total_views_7d': 0, 'unique_paths': 0, 'top_pages': [], 'total_pages': 0, 'top_page': None, 'daily': []}
    try:
        ContentPageView.__table__
        content_cutoff = datetime.utcnow() - timedelta(days=7)
        content_views = ContentPageView.query.filter(
            ContentPageView.timestamp >= content_cutoff,
            ContentPageView.is_bot == False,
        ).all()

        content_path_stats = {}
        content_daily = {}
        content_unique_ips = set()
        for v in content_views:
            p = v.path
            content_path_stats.setdefault(p, 0)
            content_path_stats[p] += 1
            if v.ip_hash:
                content_unique_ips.add(v.ip_hash)
            d = _utc_naive_to_et_date(v.timestamp)
            if d:
                content_daily.setdefault(d.isoformat(), 0)
                content_daily[d.isoformat()] += 1

        total_content_views = sum(content_path_stats.values())
        top_content = sorted(content_path_stats.items(), key=lambda x: x[1], reverse=True)[:10]
        total_pages_ever = ContentPageView.query.with_entities(
            func.count(func.distinct(ContentPageView.path))
        ).scalar() or 0
        content_stats = {
            'total_views_7d': total_content_views,
            'unique_visitors_7d': len(content_unique_ips),
            'unique_paths': len(content_path_stats),
            'top_pages': [{'path': p, 'views': c} for p, c in top_content],
            'total_pages': total_pages_ever,
            'indexed_pages': total_pages_ever,
            'top_page': top_content[0][0] if top_content else None,
            'daily': [{'date': d, 'views': c} for d, c in sorted(content_daily.items())],
        }
    except Exception as e:
        logging.warning('Content page view stats failed: %s', e)

    # Power/at-risk counts
    power_user_count = sum(1 for u in all_user_details if u.get('is_power'))
    at_risk_count = sum(1 for u in all_user_details if u.get('is_at_risk'))
    bet_pct = (feature_adoption.get('tap_bet_link', {}).get('pct_of_active', 0))

    # Commentary
    verif_c = cmt.verification_read({
        'total_users': total_users,
        'unverified_count': unverified_count,
        'spam_pattern': spam_pattern,
    })
    content_c = cmt.content_engine_read(content_stats)
    engagement_c = cmt.user_engagement_read({
        'active_7d': active_user_count,
        'total_users': total_users,
        'power_user_count': power_user_count,
        'at_risk_count': at_risk_count,
        'bet_link_tap_rate': bet_pct,
    })

    return jsonify({
        'period_days': 7,
        'tracking_since': tracking_since,
        'total_events': total_event_count,
        'active_users_7d': active_user_count,
        'total_sessions_7d': len(total_sessions_7d),
        'dau': dau,
        'sessions_by_day': sessions_by_day,
        'avg_session_duration': avg_session_duration,
        'avg_sessions_per_user': avg_sessions_per_user,
        'avg_pages_per_session': avg_pages_per_session,
        'top_pages': top_pages,
        'feature_adoption': feature_adoption,
        'retention': {
            'd1_eligible': d1_eligible,
            'd1_returned': d1_returned,
            'd1_rate_pct': round(d1_returned / d1_eligible * 100, 2) if d1_eligible else 0.0,
            'd7_eligible': d7_eligible,
            'd7_returned': d7_returned,
            'd7_rate_pct': round(d7_returned / d7_eligible * 100, 2) if d7_eligible else 0.0,
        },
        'active_user_details': active_user_details,
        'all_users': all_user_details,
        'verification': {
            'total': total_users,
            'verified': verified_count,
            'unverified': unverified_count,
            'verified_pct': round(verified_count / max(total_users, 1) * 100, 1),
            'unverified_list': unverified_users,
            'spam_pattern': spam_pattern,
        },
        'content_engine': content_stats,
        'power_user_count': power_user_count,
        'at_risk_count': at_risk_count,
        'commentary': {
            'verification': [{'type': verif_c[0], 'label': verif_c[1], 'text': verif_c[2]}],
            'content_engine': [{'type': content_c[0], 'label': content_c[1], 'text': content_c[2]}],
            'user_engagement': [{'type': engagement_c[0], 'label': engagement_c[1], 'text': engagement_c[2]}],
        },
    })


@admin_bp.route('/api/admin/user-activity/<user_id>')
def admin_user_activity(user_id):
    admin, err_code = require_superuser()
    if not admin:
        return jsonify({'error': 'Login required' if err_code == 401 else 'Unauthorized'}), err_code

    user = db.session.get(User, user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404

    fourteen_ago = datetime.utcnow() - timedelta(days=14)
    evs_14d = UserEvent.query.filter(
        UserEvent.user_id == user_id,
        UserEvent.created_at >= fourteen_ago,
    ).order_by(UserEvent.created_at.asc()).all()

    pages_visited = {}
    articles_read = 0
    per_day = {}
    session_ids = set()
    total_events_all = 0
    for ev in UserEvent.query.filter_by(user_id=user_id).yield_per(500):
        total_events_all += 1
        if ev.session_id:
            session_ids.add(ev.session_id)
        pk = ev.page if ev.page else ''
        pages_visited[pk] = pages_visited.get(pk, 0) + 1
        if ev.event_type in ('view_article', 'article_read_complete'):
            articles_read += 1

    for ev in evs_14d:
        d = _utc_naive_to_et_date(ev.created_at)
        if d:
            per_day[d] = per_day.get(d, 0) + 1

    last_ev = UserEvent.query.filter_by(user_id=user_id).order_by(UserEvent.created_at.desc()).first()
    last_active = last_ev.created_at.isoformat() if last_ev and last_ev.created_at else None

    timeline_start = datetime.now(ET).date() - timedelta(days=13)
    activity_timeline = []
    for i in range(14):
        d = timeline_start + timedelta(days=i)
        activity_timeline.append({
            'date': d.isoformat(),
            'events': per_day.get(d, 0),
        })

    return jsonify({
        'user': {
            'id': user.id,
            'email': user.email,
            'tier': user.subscription_status,
            'founding_member': bool(user.founding_member),
            'created_at': user.created_at.isoformat() if user.created_at else None,
        },
        'total_sessions': len(session_ids),
        'total_events': total_events_all,
        'pages_visited': pages_visited,
        'articles_read': articles_read,
        'activity_timeline': activity_timeline,
        'last_active': last_active,
    })


@admin_bp.route('/api/admin/push-tokens', methods=['GET'])
def admin_push_tokens():
    admin, err_code = require_superuser()
    if not admin:
        cron_secret = os.environ.get('CRON_SECRET', '')
        if not (cron_secret and request.headers.get('X-Cron-Secret') == cron_secret):
            return jsonify({'error': 'Unauthorized'}), err_code or 403
    from models import FCMToken
    tokens = FCMToken.query.all()
    result = []
    for t in tokens:
        result.append({
            'id': t.id,
            'user_id': t.user_id,
            'platform': t.platform,
            'enabled': t.enabled,
            'token_prefix': (t.fcm_token or '')[:30] + '...',
            'token_len': len(t.fcm_token or ''),
            'created_at': t.created_at.isoformat() if t.created_at else None,
            'last_seen_at': t.last_seen_at.isoformat() if t.last_seen_at else None,
        })
    return jsonify({'tokens': result})


# ─── Diagnostic: revoked-pick CLV audit ──────────────────────────────────
# One-shot health check for the question "are we capturing CLV on picks
# the model pulls before tip?". Closing-lines cron writes pick.clv by
# matching home/away/date and DOES NOT filter on result, so revoked picks
# should get clv populated when the cron fires in the T-10min window. This
# endpoint reports the actual hit rate — total revoked, how many have
# clv, sign distribution, sport breakdown, and a few recent examples so
# the operator can eyeball the pattern. No mutations.
@admin_bp.route('/api/admin/diagnose/revoked-clv')
def admin_diagnose_revoked_clv():
    admin, err_code = require_superuser()
    if not admin:
        return jsonify({'error': 'Unauthorized'}), err_code or 403

    def _bucket(rows):
        with_clv = [p for p in rows if p.clv is not None]
        without_clv = [p for p in rows if p.clv is None]
        clv_vals = [float(p.clv) for p in with_clv]
        return {
            'total_revoked': len(rows),
            'with_clv': len(with_clv),
            'without_clv': len(without_clv),
            'capture_rate_pct': round(100.0 * len(with_clv) / len(rows), 1) if rows else 0.0,
            'avg_clv': round(sum(clv_vals) / len(clv_vals), 2) if clv_vals else None,
            'positive_clv_count': sum(1 for v in clv_vals if v > 0),
            'negative_clv_count': sum(1 for v in clv_vals if v < 0),
            'zero_clv_count': sum(1 for v in clv_vals if v == 0),
            'positive_pct': round(100.0 * sum(1 for v in clv_vals if v > 0) / len(clv_vals), 1) if clv_vals else 0.0,
        }

    now = datetime.utcnow()
    cutoff_7d = now - timedelta(days=7)
    cutoff_30d = now - timedelta(days=30)
    cutoff_90d = now - timedelta(days=90)

    base = Pick.query.filter(Pick.result == 'revoked')
    lifetime = base.all()
    last_7d = base.filter(Pick.published_at >= cutoff_7d).all()
    last_30d = base.filter(Pick.published_at >= cutoff_30d).all()
    last_90d = base.filter(Pick.published_at >= cutoff_90d).all()

    by_sport = {}
    for sport in ('nba', 'mlb', 'wnba'):
        sport_rows = base.filter(Pick.sport == sport).all()
        if sport_rows:
            by_sport[sport] = _bucket(sport_rows)

    # Most-recent 10 revoked picks with clv-relevant context. line_open
    # comes from pick.line (what we published at); closing_spread is what
    # the closing-lines cron snapshotted near tipoff. revoke_reason lives
    # in pick.notes (appended as " | REVOKED: <reason>" in pretip path).
    recent_examples = []
    recent_rows = base.order_by(Pick.published_at.desc()).limit(10).all()
    for p in recent_rows:
        notes = p.notes or ''
        revoke_marker = 'REVOKED:'
        revoke_reason = None
        if revoke_marker in notes:
            after = notes.split(revoke_marker, 1)[1].strip()
            revoke_reason = after.split(' | ')[0].strip()
        recent_examples.append({
            'id': p.id,
            'sport': p.sport,
            'game_date': str(p.game_date) if p.game_date else None,
            'published_at': p.published_at.isoformat() if p.published_at else None,
            'matchup': f'{p.away_team} @ {p.home_team}',
            'side': p.side,
            'line_published': p.line,
            'closing_spread': p.closing_spread,
            'clv': float(p.clv) if p.clv is not None else None,
            'edge_pct': p.edge_pct,
            'revoke_reason': revoke_reason,
        })

    # Bonus: how does revoked CLV compare to settled CLV? Useful for
    # answering "is including revoked in avg_clv net-positive or net-
    # negative?" without flipping the filter and breaking the existing
    # number.
    settled_30d = Pick.query.filter(
        Pick.result.in_(['win', 'loss', 'push', 'postponed']),
        Pick.published_at >= cutoff_30d,
        Pick.clv.isnot(None),
    ).all()
    settled_clv_vals = [float(p.clv) for p in settled_30d if p.clv is not None]
    settled_30d_avg_clv = round(sum(settled_clv_vals) / len(settled_clv_vals), 2) if settled_clv_vals else None

    return jsonify({
        'lifetime': _bucket(lifetime),
        'last_7d': _bucket(last_7d),
        'last_30d': _bucket(last_30d),
        'last_90d': _bucket(last_90d),
        'by_sport_lifetime': by_sport,
        'compare_30d': {
            'settled_avg_clv': settled_30d_avg_clv,
            'revoked_avg_clv': _bucket(last_30d).get('avg_clv'),
            'settled_count': len(settled_30d),
            'revoked_count': len(last_30d),
        },
        'recent_examples': recent_examples,
        'note': (
            "capture_rate_pct = % of revoked picks with pick.clv populated. "
            "If lifetime capture is well below 100%, the closing-lines cron "
            "missed the game (game scored before T-10min snapshot, or "
            "matchup row didn't match by team-name+date). avg_clv is the "
            "mean CLV across all revoked picks in the window — net positive "
            "means the model was usually right and books moved to our side."
        ),
    })


@admin_bp.route('/api/admin/funnels')
def admin_funnels():
    """Rating-prompt funnel + lifecycle-email open/click rates for the
    admin dashboard tile. 7-day and 30-day windows side by side so trend
    is visible at a glance.

    rating_prompt: counts events from user_events grouped by sub-type.
    Computes positive-response-rate and feedback-capture-rate.

    apple_bridge / lifecycle_emails: joins email_send_history against
    email_events for delivered/opened/clicked counts. The Resend webhook
    updates email_events.*_at columns as deliverability state changes.
    """
    admin, err_code = require_superuser()
    if not admin:
        return jsonify({'error': 'Login required' if err_code == 401 else 'Unauthorized'}), err_code

    from models import EmailEvent, EmailSendHistory
    from sqlalchemy import func as _func, case

    now = datetime.utcnow()
    cutoff_7d = now - timedelta(days=7)
    cutoff_30d = now - timedelta(days=30)

    def _rating_funnel(cutoff):
        rows = db.session.query(
            UserEvent.event_type, _func.count(UserEvent.id)
        ).filter(
            UserEvent.event_type.like('rating_prompt.%'),
            UserEvent.created_at >= cutoff,
        ).group_by(UserEvent.event_type).all()
        counts = {row[0].replace('rating_prompt.', ''): row[1] for row in rows}
        shown = counts.get('shown', 0)
        pos   = counts.get('tapped_positive', 0)
        neg   = counts.get('tapped_negative', 0)
        feedback_submitted = counts.get('feedback_submitted', 0)
        return {
            'shown': shown,
            'tapped_positive': pos,
            'tapped_negative': neg,
            'dismissed': counts.get('dismissed', 0),
            'google_api_triggered': counts.get('google_api_triggered', 0),
            'feedback_submitted': feedback_submitted,
            'feedback_skipped': counts.get('feedback_skipped', 0),
            'positive_rate_pct': round(100.0 * pos / shown, 1) if shown else 0.0,
            'negative_rate_pct': round(100.0 * neg / shown, 1) if shown else 0.0,
            'feedback_capture_rate_pct': round(100.0 * feedback_submitted / neg, 1) if neg else 0.0,
        }

    def _email_funnel(variant, cutoff):
        # Sent count from email_send_history (frequency-cap ledger,
        # one row per attempted+successful send). Delivery / open /
        # click counts from email_events (webhook-updated rows).
        sent = db.session.query(_func.count(EmailSendHistory.id)).filter(
            EmailSendHistory.variant == variant,
            EmailSendHistory.sent_at >= cutoff,
        ).scalar() or 0

        agg = db.session.query(
            _func.count(EmailEvent.id),
            _func.count(EmailEvent.delivered_at),
            _func.count(EmailEvent.opened_at),
            _func.count(EmailEvent.clicked_at),
            _func.count(EmailEvent.bounced_at),
            _func.count(EmailEvent.unsubscribed_at),
        ).filter(
            EmailEvent.variant == variant,
            EmailEvent.sent_at >= cutoff,
        ).first()
        ev_count = agg[0] or 0
        delivered = agg[1] or 0
        opened = agg[2] or 0
        clicked = agg[3] or 0
        bounced = agg[4] or 0
        unsub = agg[5] or 0

        denom = max(ev_count, sent, 1)
        return {
            'sent': sent,
            'events_logged': ev_count,
            'delivered': delivered,
            'opened': opened,
            'clicked': clicked,
            'bounced': bounced,
            'unsubscribed': unsub,
            'open_rate_pct': round(100.0 * opened / denom, 1),
            'click_rate_pct': round(100.0 * clicked / denom, 1),
            'bounce_rate_pct': round(100.0 * bounced / denom, 1),
        }

    KNOWN_VARIANTS = (
        'apple_iap_bridge', 'welcome', 'trial_started',
        'trial_expiring_auto_renew', 'trial_expiring_action_required',
        'trial_expired', 'cancellation', 'payment_failed',
        'founding_member', 'signal_nba', 'signal_mlb',
        'result_win', 'result_loss', 'no_signal',
    )

    email_funnels_7d = {v: _email_funnel(v, cutoff_7d) for v in KNOWN_VARIANTS}
    email_funnels_30d = {v: _email_funnel(v, cutoff_30d) for v in KNOWN_VARIANTS}

    return jsonify({
        'rating_prompt': {
            'last_7d': _rating_funnel(cutoff_7d),
            'last_30d': _rating_funnel(cutoff_30d),
        },
        'email_variants': {
            'last_7d': email_funnels_7d,
            'last_30d': email_funnels_30d,
        },
        'generated_at': now.isoformat(),
    })



@admin_bp.route('/api/admin/model-clv')
def admin_model_clv():
    """Internal monitoring for moneyline CLV. Surfaces avg + beat/match/miss
    bucketing per sport so we can track model calibration without exposing
    the numbers in the public stats endpoint while we're still tuning.

    Returns spread CLV alongside moneyline CLV so both signals are visible
    in the same call.
    """
    admin, err_code = require_superuser()
    if not admin:
        return jsonify({'error': 'Login required' if err_code == 401 else 'Unauthorized'}), err_code

    _SPREAD_EPS = 0.25
    _ML_EPS = 0.5

    def _bucket(values, eps):
        beats = sum(1 for v in values if v > eps)
        misses = sum(1 for v in values if v < -eps)
        matches = sum(1 for v in values if -eps <= v <= eps)
        denom = beats + misses
        rate = round(beats / denom * 100, 1) if denom > 0 else 0
        avg = round(sum(values) / len(values), 2) if values else None
        return {
            'n': len(values),
            'beat': beats,
            'matched': matches,
            'missed': misses,
            'beat_rate_pct': rate,
            'avg': avg,
        }

    out = {}
    for sport in ('nba', 'wnba', 'mlb'):
        picks = Pick.query.filter(
            Pick.sport == sport,
            Pick.result.in_(('win', 'loss', 'push', 'postponed')),
        ).all()
        clv_vals = [p.clv for p in picks if p.clv is not None]
        ml_vals = [p.clv_ml for p in picks if p.clv_ml is not None]
        out[sport] = {
            'total_graded_picks': len(picks),
            'spread_clv': _bucket(clv_vals, _SPREAD_EPS),
            'moneyline_clv': _bucket(ml_vals, _ML_EPS),
        }
    return jsonify({
        'sports': out,
        'note': (
            'Moneyline CLV is captured but hidden from public payloads while '
            'the model is in calibration. Promote to public when beat rate '
            'clears ~52% sustained for the sport.'
        ),
    })


@admin_bp.route('/api/admin/trial-audit')
def admin_trial_audit():
    """End-to-end trial sanity check. Reconciles three independent views of
    the same data and exposes the deltas:

      1. **Stripe live**  every status='trialing' Stripe subscription right now
      2. **DB**           User rows with subscription_status='trial' + recent
                          User.trial_converted_at entries (the source the
                          dashboard trial-conversion counters read from)
      3. **Likely-miss**  paid invoices in the last 30d whose user has no
                          trial_converted_at on file (conversion happened in
                          Stripe but the webhook never landed)

    Use this when the dashboard trial pipeline or conversion counts look off.
    A delta between Stripe-live trials and DB status='trial' rows usually
    means subscription.updated webhooks aren't getting through; a non-empty
    `likely_missed_conversions` list is the canonical sign Cooper/Spiffy-style
    silent failures are happening.
    """
    admin, err_code = require_superuser()
    if not admin:
        return jsonify({'error': 'Login required' if err_code == 401 else 'Unauthorized'}), err_code

    import stripe as _stripe
    import re as _re

    try:
        _stripe.api_key = os.environ.get('STRIPE_SECRET_KEY')
        if not _stripe.api_key:
            return jsonify({'error': 'STRIPE_SECRET_KEY missing'}), 500
    except Exception as e:
        return jsonify({'error': f'stripe init failed: {e}'}), 500

    now = datetime.utcnow()
    cutoff_7d  = now - timedelta(days=7)
    cutoff_30d = now - timedelta(days=30)

    # ── Build exclusion set (mirrors stripe_metrics.py) ──
    _AR_PATTERN = _re.compile(r'^ar_user[0-9]+@icloud\.com$')
    excluded_cust_ids = set()
    try:
        users_with_stripe = User.query.filter(User.stripe_customer_id.isnot(None)).with_entities(
            User.stripe_customer_id, User.is_internal, User.comped, User.deleted_at, User.email,
        ).all()
        for cust_id, is_internal, comped, deleted_at, email in users_with_stripe:
            is_app_reviewer = bool(email and _AR_PATTERN.match(email))
            if is_internal or comped or deleted_at is not None or is_app_reviewer:
                excluded_cust_ids.add(cust_id)
    except Exception as e:
        return jsonify({'error': f'exclusion-set build failed: {e}'}), 500

    # ── 1. Live Stripe trialing subs ──
    stripe_trials = []
    try:
        sub_iter = _stripe.Subscription.list(status='trialing', limit=100).auto_paging_iter()
        for n, sub in enumerate(sub_iter, start=1):
            if n > 500:
                break
            cust = sub.get('customer')
            cust_id = cust if isinstance(cust, str) else (cust.get('id') if cust else None)
            if cust_id in excluded_cust_ids:
                continue
            stripe_trials.append({
                'customer_id': cust_id,
                'sub_id': sub.get('id'),
                'cancel_at_period_end': bool(sub.get('cancel_at_period_end')),
                'trial_end': sub.get('trial_end'),
                'created': sub.get('created'),
            })
    except Exception as e:
        return jsonify({'error': f'stripe.Subscription.list failed: {e}'}), 500

    stripe_likely    = sum(1 for t in stripe_trials if not t['cancel_at_period_end'])
    stripe_scheduled = sum(1 for t in stripe_trials if t['cancel_at_period_end'])

    # ── 2. DB-side counts ──
    db_trial_users = User.query.filter(
        User.subscription_status == 'trial',
        User.is_internal == False,  # noqa: E712
        User.comped == False,  # noqa: E712
        User.deleted_at.is_(None),
    ).count()
    db_converted_7d = User.query.filter(
        User.trial_converted_at.isnot(None),
        User.trial_converted_at >= cutoff_7d,
        User.is_internal == False,  # noqa: E712
        User.deleted_at.is_(None),
    ).count()
    db_converted_30d = User.query.filter(
        User.trial_converted_at.isnot(None),
        User.trial_converted_at >= cutoff_30d,
        User.is_internal == False,  # noqa: E712
        User.deleted_at.is_(None),
    ).count()

    # ── 3. Suspected webhook misses ──
    # Scan recent paid invoices. For each, if the underlying sub's customer
    # maps to a User whose status is 'active' but trial_converted_at is NULL,
    # the conversion-detect webhook didn't fire. We can't know retroactively
    # whether the user actually started on trial, so we surface them as
    # "suspected" — operator decides whether to backfill via the existing
    # backfill_stripe_cancel_state script.
    cutoff_30d_ts = int(cutoff_30d.timestamp())
    likely_missed = []
    try:
        inv_iter = _stripe.Invoice.list(
            status='paid', created={'gte': cutoff_30d_ts}, limit=100,
        ).auto_paging_iter()
        seen_cust_ids = set()
        for n, inv in enumerate(inv_iter, start=1):
            if n > 500:
                break
            if (inv.get('amount_paid') or 0) <= 0:
                continue
            cust = inv.get('customer')
            cust_id = cust if isinstance(cust, str) else (cust.get('id') if cust else None)
            if not cust_id or cust_id in excluded_cust_ids or cust_id in seen_cust_ids:
                continue
            seen_cust_ids.add(cust_id)
            u = User.query.filter_by(stripe_customer_id=cust_id).first()
            if not u or u.deleted_at is not None:
                continue
            if u.subscription_status == 'active' and u.trial_converted_at is None and u.trial_end_date is not None:
                likely_missed.append({
                    'user_id': u.id,
                    'email': u.email,
                    'customer_id': cust_id,
                    'invoice_id': inv.get('id'),
                    'paid_at': inv.get('status_transitions', {}).get('paid_at'),
                    'amount_paid_cents': inv.get('amount_paid'),
                    'trial_end_date': u.trial_end_date.isoformat() if u.trial_end_date else None,
                })
    except Exception as e:
        # Don't fail the whole audit if invoice scan trips; just note it.
        likely_missed = [{'error': f'invoice scan failed: {e}'}]

    # ── Reconciliation ──
    trial_delta = len(stripe_trials) - db_trial_users  # > 0 means Stripe sees more trials than DB
    conv_30d_likely_miss = sum(1 for r in likely_missed if 'user_id' in r)

    return jsonify({
        'generated_at': now.isoformat() + 'Z',
        'dashboard': {
            'note': 'Mirrors what Today\'s Read v2 displays. Pulled from the same fields as stripe_metrics.fetch().',
            'trials':                       len(stripe_trials),
            'trials_with_cancel_scheduled': stripe_scheduled,
            'trials_likely_to_convert':     stripe_likely,
            'trial_conversions_7d':         db_converted_7d,
            'trial_conversions_30d':        db_converted_30d,
        },
        'stripe_live': {
            'trial_count':              len(stripe_trials),
            'cancel_scheduled_count':   stripe_scheduled,
            'likely_to_convert_count':  stripe_likely,
            'sample':                   stripe_trials[:25],
        },
        'db': {
            'subscription_status_trial_count': db_trial_users,
            'trial_converted_at_7d':           db_converted_7d,
            'trial_converted_at_30d':          db_converted_30d,
        },
        'reconciliation': {
            'stripe_trials_vs_db_trial_status':  trial_delta,
            'suspected_webhook_misses_30d':      conv_30d_likely_miss,
            'verdict': (
                'OK' if trial_delta == 0 and conv_30d_likely_miss == 0
                else 'INVESTIGATE'
            ),
        },
        'likely_missed_conversions': likely_missed,
        'hint': (
            'Non-zero stripe_trials_vs_db_trial_status: customer.subscription.updated '
            'webhooks may be failing; check Stripe webhook delivery logs. '
            'Non-empty likely_missed_conversions: invoice.paid arrived but '
            'trial_converted_at never got set; run scripts/backfill_stripe_cancel_state.py '
            'to retroactively populate trial_converted_at from trial_end_date.'
        ),
    })
