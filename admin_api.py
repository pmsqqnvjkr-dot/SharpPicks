from flask import Blueprint, jsonify, request
from models import db, User, Pick, Pass, ModelRun, FoundingCounter, TrackedBet, Insight
from datetime import datetime, timedelta
from sqlalchemy import func, text
from zoneinfo import ZoneInfo
import os
import requests
import time
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

admin_bp = Blueprint('admin_api', __name__)
ET = ZoneInfo('America/New_York')

def require_superuser():
    from flask_login import current_user
    if not current_user.is_authenticated:
        return None
    if not current_user.is_superuser:
        return None
    return current_user


@admin_bp.route('/api/admin/command-center')
def command_center_data():
    admin = require_superuser()
    if not admin:
        return jsonify({'error': 'Unauthorized'}), 403

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

    monthly_rev = len(monthly_subs) * 29
    annual_rev = len(annual_subs) * (99 / 12)
    mrr = round(monthly_rev + annual_rev, 2)
    arr = round(mrr * 12, 2)

    counter = FoundingCounter.query.first()
    founding_count = counter.current_count if counter else len(founding_members)
    founding_cap = 500

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
            'email': u.email,
            'first_name': u.first_name or '',
            'tier': tier,
            'plan': u.subscription_plan or '',
            'founding_number': u.founding_number,
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
        'timestamp': now_et.strftime('%b %d, %Y · %-I:%M:%S %p EST'),
    })


@admin_bp.route('/api/admin/health-checks')
def health_checks():
    admin = require_superuser()
    if not admin:
        return jsonify({'error': 'Unauthorized'}), 403

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
                timeout=8
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
        except requests.Timeout:
            return {'status': 'warn', 'message': 'Timeout (8s)'}
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
