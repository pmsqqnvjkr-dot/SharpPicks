from flask import Blueprint, jsonify, request
from models import db, Pick, Pass, ModelRun, UserBet, TrackedBet
from datetime import datetime, timedelta, timezone
import sqlite3

picks_bp = Blueprint('picks', __name__)

try:
    from db_path import get_sqlite_path
except ImportError:
    def get_sqlite_path():
        return 'sharp_picks.db'

EDGE_THRESHOLD = 3.5


def calculate_stake_guidance(edge_pct, confidence, market_odds=-110):
    """Generate bankroll guidance: flat staking + fractional Kelly
    
    Uses actual market odds when available, defaults to -110 standard juice.
    """
    if market_odds and market_odds < 0:
        odds_decimal = 1 + (100 / abs(market_odds))
    elif market_odds and market_odds > 0:
        odds_decimal = 1 + (market_odds / 100)
    else:
        odds_decimal = 1 + (100 / 110)
    
    model_prob = confidence
    
    kelly_full = (model_prob * odds_decimal - 1) / (odds_decimal - 1)
    kelly_full = max(0, kelly_full)
    kelly_fraction = kelly_full * 0.25
    
    kelly_units = round(kelly_fraction * 100, 1)
    kelly_units = min(kelly_units, 5.0)
    kelly_units = max(kelly_units, 0)
    
    if edge_pct >= 10:
        confidence_tier = 'high'
        flat_units = 2.0
    elif edge_pct >= 6:
        confidence_tier = 'standard'
        flat_units = 1.5
    else:
        confidence_tier = 'minimum'
        flat_units = 1.0
    
    return {
        'flat_stake': flat_units,
        'kelly_stake': kelly_units,
        'confidence_tier': confidence_tier,
        'kelly_fraction': round(kelly_fraction * 100, 2),
        'guidance': f"{flat_units}u flat / {kelly_units}u Kelly (quarter-Kelly)",
    }


def _get_et_date():
    """Get current 'betting day' date string in Eastern Time.
    
    The betting day runs until 2:30 AM ET the following morning.
    Before 2:30 AM, we still show the previous day's pick/pass.
    After 2:30 AM, the slate resets to the new day.
    """
    try:
        from zoneinfo import ZoneInfo
        now_et = datetime.now(ZoneInfo('America/New_York'))
    except ImportError:
        now_et = datetime.utcnow() - timedelta(hours=5)
    
    if now_et.hour < 2 or (now_et.hour == 2 and now_et.minute < 30):
        now_et = now_et - timedelta(days=1)
    
    return now_et.strftime('%Y-%m-%d')


@picks_bp.route('/today')
def today():
    today_str = _get_et_date()
    sport = request.args.get('sport', 'nba')

    pick = Pick.query.filter(
        Pick.game_date == today_str,
        Pick.sport == sport,
    ).order_by(Pick.published_at.desc()).first()

    if pick:
        model_signals = []
        if pick.notes:
            model_signals = [s.strip() for s in pick.notes.split('|') if s.strip()]

        model_line = pick.line
        market_line = round(pick.line + (pick.edge_pct * 0.3 if pick.edge_pct else 0), 1) if pick.line else None

        actual_odds = pick.market_odds or -110
        stake = calculate_stake_guidance(pick.edge_pct or 0, pick.model_confidence or 0.5, actual_odds)

        pick_data = {
            'type': 'pick',
            'id': pick.id,
            'sport': pick.sport,
            'away_team': pick.away_team,
            'home_team': pick.home_team,
            'game_date': pick.game_date,
            'side': pick.side,
            'line': pick.line,
            'edge_pct': pick.edge_pct,
            'model_confidence': pick.model_confidence,
            'predicted_margin': pick.predicted_margin,
            'sigma': pick.sigma,
            'z_score': pick.z_score,
            'raw_edge': pick.raw_edge,
            'cover_prob': pick.cover_prob,
            'implied_prob': pick.implied_prob,
            'market_odds': pick.market_odds,
            'closing_spread': pick.closing_spread,
            'clv': pick.clv,
            'position_size_pct': pick.position_size_pct or 100,
            'model_line': model_line,
            'market_line': market_line,
            'model_signals': model_signals,
            'start_time': pick.start_time,
            'result': pick.result,
            'result_ats': pick.result_ats,
            'pnl': pick.pnl,
            'profit_units': pick.profit_units,
            'home_score': pick.home_score,
            'away_score': pick.away_score,
            'published_at': (pick.published_at.isoformat() + 'Z') if pick.published_at else None,
            'posted_time': '2h before tip',
            'best_book': pick.sportsbook or 'DraftKings',
            'stake_guidance': stake,
            'disclaimer': 'For informational and entertainment purposes only. No guaranteed outcomes. Past performance does not guarantee future results. Please gamble responsibly.',
        }
        from app import get_current_user_obj
        cu = get_current_user_obj()
        is_pro = cu is not None and cu.is_pro
        if not is_pro:
            pick_data['side'] = 'Upgrade to see pick'
            pick_data['edge_pct'] = None
            pick_data['model_confidence'] = None
            pick_data['predicted_margin'] = None
            pick_data['sigma'] = None
            pick_data['z_score'] = None
            pick_data['raw_edge'] = None
            pick_data['cover_prob'] = None
            pick_data['implied_prob'] = None
            pick_data['model_signals'] = []
            pick_data['model_line'] = None
            pick_data['market_line'] = None
            pick_data['stake_guidance'] = None
            pick_data['locked'] = True
        else:
            pick_data['locked'] = False
            if cu:
                existing_bet = TrackedBet.query.filter_by(
                    user_id=cu.id,
                    pick_id=pick.id
                ).first()
                pick_data['already_tracked'] = existing_bet is not None
                if existing_bet:
                    pick_data['tracked_bet_id'] = existing_bet.id
        return jsonify(pick_data)

    pass_entry = Pass.query.filter_by(date=today_str, sport=sport).first()
    if pass_entry:
        from datetime import timedelta
        week_start = (datetime.now() - timedelta(days=datetime.now().weekday())).strftime('%Y-%m-%d')
        picks_this_week = Pick.query.filter(Pick.game_date >= week_start).count()
        passes_this_week = Pass.query.filter(Pass.date >= week_start).count()
        total_picks = Pick.query.count()
        total_passes = Pass.query.count()
        total_days = total_picks + total_passes
        selectivity = round((total_picks / total_days) * 100) if total_days > 0 else 0
        days_per_bet = round(total_days / total_picks, 1) if total_picks > 0 else 0

        pass_type = 'pass'
        message = 'No qualifying edge found today. The model analyzed all available games and none met the threshold. Discipline preserved.'

        whatif = None
        if pass_entry.whatif_side and pass_entry.whatif_edge is not None:
            whatif = {
                'side': pass_entry.whatif_side,
                'edge_pct': pass_entry.whatif_edge,
            }

        return jsonify({
            'type': pass_type,
            'date': pass_entry.date,
            'games_analyzed': pass_entry.games_analyzed,
            'closest_edge_pct': pass_entry.closest_edge_pct,
            'whatif': whatif,
            'pass_reason': pass_entry.pass_reason,
            'picks_this_week': picks_this_week,
            'passes_this_week': passes_this_week,
            'selectivity': selectivity,
            'days_per_bet': days_per_bet,
            'message': message,
        })

    allstar_ranges = [
        ('2025-02-14', '2025-02-18', '2025-02-20'),
        ('2026-02-13', '2026-02-18', '2026-02-19'),
        ('2027-02-12', '2027-02-17', '2027-02-18'),
    ]
    for break_start, break_end, resume in allstar_ranges:
        if break_start <= today_str <= break_end:
            return jsonify({
                'type': 'allstar_break',
                'date': today_str,
                'resume_date': resume,
                'message': 'The NBA All-Star break is underway. No regular season games are scheduled. The model will resume when the regular season continues.'
            })

    # Enrich waiting state with today's slate info for daily insight screen
    games_scheduled = 0
    games_preview = []
    model_runs_at = '10:00 AM ET'
    games_table = 'wnba_games' if sport == 'wnba' else 'games'
    try:
        conn = sqlite3.connect(get_sqlite_path())
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute(
            f"SELECT away_team, home_team, MIN(game_time) as game_time "
            f"FROM {games_table} WHERE game_date = ? AND home_score IS NULL "
            f"GROUP BY away_team, home_team ORDER BY game_time",
            (today_str,)
        )
        rows = cur.fetchall()
        games_scheduled = len(rows)

        def _format_game_time(utc_str):
            """Convert UTC ISO timestamp to ET display time like '7:30 PM'."""
            if not utc_str:
                return None
            try:
                from zoneinfo import ZoneInfo
                dt = datetime.fromisoformat(utc_str.replace('Z', '+00:00'))
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                et = dt.astimezone(ZoneInfo('America/New_York'))
                return et.strftime('%-I:%M %p')
            except Exception:
                return None

        games_preview = [
            {'away': r['away_team'], 'home': r['home_team'], 'time': _format_game_time(r['game_time'])}
            for r in rows[:12]
        ]
        conn.close()
    except Exception:
        pass

    return jsonify({
        'type': 'waiting',
        'message': 'Model has not run yet today. Check back later.',
        'games_scheduled': games_scheduled,
        'games_preview': games_preview,
        'model_runs_at': model_runs_at,
    })


@picks_bp.route('/last-resolved')
def last_resolved():
    """Return the most recently graded pick (win/loss/push) for resolution banner"""
    today_str = _get_et_date()
    pick = Pick.query.filter(
        Pick.result.in_(['win', 'loss', 'push']),
        Pick.game_date != today_str
    ).order_by(Pick.published_at.desc()).first()

    if not pick:
        return jsonify(None)

    from app import get_current_user_obj
    cu = get_current_user_obj()
    is_pro = cu is not None and cu.is_pro
    if not is_pro:
        return jsonify(None)

    from flask import session
    dismissed_key = f'dismissed_resolution_{pick.id}'
    if session.get(dismissed_key):
        return jsonify(None)

    return jsonify({
        'id': pick.id,
        'type': 'resolved',
        'away_team': pick.away_team,
        'home_team': pick.home_team,
        'game_date': pick.game_date,
        'side': pick.side,
        'line': pick.line,
        'edge_pct': pick.edge_pct,
        'result': pick.result,
        'pnl': pick.pnl,
        'profit_units': pick.profit_units,
        'home_score': pick.home_score,
        'away_score': pick.away_score,
        'market_odds': pick.market_odds,
        'published_at': (pick.published_at.isoformat() + 'Z') if pick.published_at else None,
    })


@picks_bp.route('/dismiss-resolution', methods=['POST'])
def dismiss_resolution():
    """Dismiss the resolution banner for a specific pick"""
    data = request.get_json()
    pick_id = data.get('pick_id')
    if pick_id:
        from flask import session
        session[f'dismissed_resolution_{pick_id}'] = True
    return jsonify({'success': True})


@picks_bp.route('/history')
def history():
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    sport = request.args.get('sport')

    q = Pick.query
    if sport:
        q = q.filter(Pick.sport == sport)
    picks = q.order_by(Pick.published_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )

    return jsonify({
        'picks': [{
            'id': p.id,
            'published_at': (p.published_at.isoformat() + 'Z') if p.published_at else None,
            'sport': p.sport,
            'away_team': p.away_team,
            'home_team': p.home_team,
            'game_date': p.game_date,
            'side': p.side,
            'line': p.line,
            'line_open': p.line_open,
            'line_close': p.line_close,
            'start_time': p.start_time,
            'edge_pct': p.edge_pct,
            'model_confidence': p.model_confidence,
            'predicted_margin': p.predicted_margin,
            'cover_prob': p.cover_prob,
            'implied_prob': p.implied_prob,
            'market_odds': p.market_odds,
            'sportsbook': p.sportsbook,
            'result': p.result,
            'result_ats': p.result_ats,
            'pnl': p.pnl,
            'profit_units': p.profit_units,
            'home_score': p.home_score,
            'away_score': p.away_score,
        } for p in picks.items],
        'total': picks.total,
        'page': picks.page,
        'pages': picks.pages,
    })


@picks_bp.route('/weekly-summary')
def weekly_summary():
    from app import get_current_user_obj
    cu = get_current_user_obj()
    is_pro = cu is not None and cu.is_pro
    if not is_pro:
        return jsonify({'error': 'Pro subscription required'}), 403

    sport = request.args.get('sport', 'nba')

    try:
        from zoneinfo import ZoneInfo
        now_et = datetime.now(ZoneInfo('America/New_York'))
    except ImportError:
        now_et = datetime.utcnow() - timedelta(hours=5)

    today = now_et.date()
    days_since_monday = today.weekday()
    week_start = today - timedelta(days=days_since_monday)
    week_end = week_start + timedelta(days=6)

    week_start_str = week_start.strftime('%Y-%m-%d')
    week_end_str = week_end.strftime('%Y-%m-%d')

    picks = Pick.query.filter(
        Pick.game_date >= week_start_str,
        Pick.game_date <= week_end_str,
        Pick.sport == sport,
    ).order_by(Pick.game_date, Pick.published_at.desc()).all()

    passes = Pass.query.filter(
        Pass.date >= week_start_str,
        Pass.date <= week_end_str,
        Pass.sport == sport,
    ).order_by(Pass.date).all()

    wins = sum(1 for p in picks if p.result == 'win')
    losses = sum(1 for p in picks if p.result == 'loss')
    pnl = round(sum(p.profit_units or 0 for p in picks if p.result in ('win', 'loss', 'push')), 2)

    pick_by_date = {}
    for p in picks:
        if p.game_date not in pick_by_date:
            pick_by_date[p.game_date] = p
    pass_dates = {p.date for p in passes}

    days = []
    for i in range(7):
        day_date = week_start + timedelta(days=i)
        day_str = day_date.strftime('%Y-%m-%d')
        if day_str in pick_by_date:
            p = pick_by_date[day_str]
            days.append({
                'type': 'pick',
                'date': day_str,
                'summary': f"{p.away_team} @ {p.home_team} — {p.side} {p.line}",
                'result': p.result if p.result in ('win', 'loss', 'push') else None,
                'pnl': p.profit_units,
            })
        elif day_str in pass_dates:
            days.append({
                'type': 'pass',
                'date': day_str,
                'summary': 'No qualifying edge',
            })
        elif day_date > today:
            days.append({
                'type': 'upcoming',
                'date': day_str,
                'summary': 'Upcoming',
            })
        else:
            days.append({
                'type': 'no_games',
                'date': day_str,
                'summary': 'No games',
            })

    return jsonify({
        'record': f"{wins}-{losses}",
        'wins': wins,
        'losses': losses,
        'passes': len(passes),
        'pnl': pnl,
        'week_start': week_start_str,
        'week_end': week_end_str,
        'days': days,
    })


@picks_bp.route('/<pick_id>')
def get_pick(pick_id):
    pick = Pick.query.get_or_404(pick_id)

    model_signals = []
    if pick.notes:
        model_signals = [s.strip() for s in pick.notes.split('|') if s.strip()]

    actual_odds = pick.market_odds or -110
    stake = calculate_stake_guidance(pick.edge_pct or 0, pick.model_confidence or 0.5, actual_odds)

    return jsonify({
        'id': pick.id,
        'published_at': (pick.published_at.isoformat() + 'Z') if pick.published_at else None,
        'sport': pick.sport,
        'away_team': pick.away_team,
        'home_team': pick.home_team,
        'game_date': pick.game_date,
        'start_time': pick.start_time,
        'side': pick.side,
        'line': pick.line,
        'line_open': pick.line_open,
        'line_close': pick.line_close,
        'edge_pct': pick.edge_pct,
        'model_confidence': pick.model_confidence,
        'predicted_margin': pick.predicted_margin,
        'cover_prob': pick.cover_prob,
        'implied_prob': pick.implied_prob,
        'market_odds': pick.market_odds,
        'sportsbook': pick.sportsbook,
        'model_signals': model_signals,
        'stake_guidance': stake,
        'result': pick.result,
        'result_ats': pick.result_ats,
        'pnl': pick.pnl,
        'profit_units': pick.profit_units,
        'home_score': pick.home_score,
        'away_score': pick.away_score,
        'notes': pick.notes,
        'disclaimer': 'For informational and entertainment purposes only. No guaranteed outcomes. Past performance does not guarantee future results. Please gamble responsibly.',
    })
