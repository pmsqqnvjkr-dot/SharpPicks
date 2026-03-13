from flask import Blueprint, jsonify, request
from models import db, Pick, Pass, ModelRun, UserBet, TrackedBet, WatchedGame
from datetime import datetime, timedelta, timezone
import sqlite3

picks_bp = Blueprint('picks', __name__)

try:
    from db_path import get_sqlite_path
except ImportError:
    def get_sqlite_path():
        return 'sharp_picks.db'

EDGE_THRESHOLD = 3.5
PROB_PER_POINT = 2.5


def _calc_playable_to(line, side, edge_pct):
    """Calculate worst spread at which the edge still exceeds threshold."""
    if line is None or edge_pct is None:
        return None
    cushion = edge_pct - EDGE_THRESHOLD
    if cushion <= 0:
        return None
    pts = cushion / PROB_PER_POINT
    if side == 'home':
        return round((line + pts) * 2) / 2
    else:
        return round((line - pts) * 2) / 2


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
        withdraw_reason = None
        if pick.notes:
            for s in pick.notes.split('|'):
                s = s.strip()
                if not s:
                    continue
                if s.startswith('REVOKED:'):
                    withdraw_reason = s[len('REVOKED:'):].strip()
                else:
                    model_signals.append(s)

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
            'playable_to': _calc_playable_to(pick.line, pick.side, pick.edge_pct),
            'withdraw_reason': withdraw_reason,
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
    games_preview = []
    model_runs_at = '10:00 AM ET'

    def _format_utc_to_et(utc_str):
        """Convert UTC ISO timestamp to ET display string like '7:30 PM ET'."""
        if not utc_str:
            return None
        try:
            from zoneinfo import ZoneInfo
            dt = datetime.fromisoformat(utc_str.replace('Z', '+00:00'))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            et = dt.astimezone(ZoneInfo('America/New_York'))
            return et.strftime('%-I:%M %p ET')
        except Exception:
            return None

    espn_sport = 'womens-basketball/wnba' if sport == 'wnba' else 'basketball/nba'
    try:
        import requests as _req
        espn_date = today_str.replace('-', '')
        espn_url = f'https://site.api.espn.com/apis/site/v2/sports/{espn_sport}/scoreboard?dates={espn_date}'
        resp = _req.get(espn_url, timeout=5)
        if resp.status_code == 200:
            for ev in resp.json().get('events', []):
                comp = ev.get('competitions', [{}])[0]
                teams = comp.get('competitors', [])
                if len(teams) == 2:
                    home_t = next((t for t in teams if t.get('homeAway') == 'home'), teams[0])
                    away_t = next((t for t in teams if t.get('homeAway') == 'away'), teams[1])
                    games_preview.append({
                        'away': away_t.get('team', {}).get('displayName', ''),
                        'home': home_t.get('team', {}).get('displayName', ''),
                        'time': _format_utc_to_et(ev.get('date', '')),
                    })
    except Exception:
        pass

    # Fallback to SQLite if ESPN returned nothing
    if not games_preview:
        games_table = 'wnba_games' if sport == 'wnba' else 'games'
        try:
            conn = sqlite3.connect(get_sqlite_path())
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()
            cur.execute(
                f"SELECT away_team, home_team, "
                f"COALESCE(NULLIF(game_time, ''), NULLIF(commence_time, '')) as game_time "
                f"FROM {games_table} WHERE game_date = ? AND home_score IS NULL "
                f"GROUP BY away_team, home_team ORDER BY game_time",
                (today_str,)
            )
            for r in cur.fetchall():
                games_preview.append({
                    'away': r['away_team'],
                    'home': r['home_team'],
                    'time': _format_utc_to_et(r['game_time']),
                })
            conn.close()
        except Exception:
            pass

    return jsonify({
        'type': 'waiting',
        'message': 'Model has not run yet today. Check back later.',
        'games_scheduled': len(games_preview),
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
    withdraw_reason = None
    if pick.notes:
        for s in pick.notes.split('|'):
            s = s.strip()
            if not s:
                continue
            if s.startswith('REVOKED:'):
                withdraw_reason = s[len('REVOKED:'):].strip()
            else:
                model_signals.append(s)

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
        'withdraw_reason': withdraw_reason,
        'disclaimer': 'For informational and entertainment purposes only. No guaranteed outcomes. Past performance does not guarantee future results. Please gamble responsibly.',
    })


@picks_bp.route('/market')
def market_view():
    """Today's game board with spreads, totals, moneylines, and 1H lines.
    Falls back to the next upcoming date if today has no games."""
    today_str = _get_et_date()
    sport = request.args.get('sport', 'nba')
    games_table = 'wnba_games' if sport == 'wnba' else 'games'

    _select_cols = f"""id, home_team, away_team, game_time,
                spread_home, spread_away, total, home_ml, away_ml,
                spread_home_open, total_open, home_ml_open, away_ml_open,
                home_spread_odds, away_spread_odds,
                home_spread_book, away_spread_book,
                spread_h1_home, spread_h1_away,
                spread_h1_home_odds, spread_h1_away_odds, total_h1,
                home_record, away_record,
                home_score, away_score,
                rundown_spread_consensus, rundown_spread_range, rundown_num_books"""

    try:
        conn = sqlite3.connect(get_sqlite_path())
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute(
            f"SELECT {_select_cols} FROM {games_table} WHERE game_date = ? ORDER BY game_time",
            (today_str,)
        )
        rows = cur.fetchall()

        active_date = today_str
        if not rows:
            cur.execute(
                f"SELECT MIN(game_date) FROM {games_table} WHERE game_date > ?",
                (today_str,)
            )
            next_date = cur.fetchone()[0]
            if next_date:
                active_date = next_date
                cur.execute(
                    f"SELECT {_select_cols} FROM {games_table} WHERE game_date = ? ORDER BY game_time",
                    (next_date,)
                )
                rows = cur.fetchall()
    except Exception:
        active_date = today_str
        return jsonify({'games': [], 'date': today_str})

    def _fmt_time(utc_str):
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

    # Load model analysis if available
    model_analysis = {}
    pick_signals = {}
    try:
        model_run = ModelRun.query.filter_by(date=active_date, sport=sport).order_by(ModelRun.created_at.desc()).first()
        if model_run and model_run.games_detail:
            import json as _json
            try:
                details = _json.loads(model_run.games_detail)
                if isinstance(details, list):
                    for ga in details:
                        ga_key = (ga.get('away'), ga.get('home'))
                        model_analysis[ga_key] = ga
            except Exception:
                pass
        if model_run and model_run.pick_id:
            pick_obj = Pick.query.get(model_run.pick_id)
            if pick_obj and pick_obj.notes:
                pick_signals[(pick_obj.away_team, pick_obj.home_team)] = [
                    s.strip() for s in pick_obj.notes.split('|') if s.strip()
                ]
    except Exception:
        pass

    # Load line snapshots for sparklines
    line_snapshots = {}
    try:
        cur.execute(
            f"""SELECT away_team, home_team, spread_home, total,
                       snapped_at FROM line_snapshots
                WHERE game_date = ? ORDER BY snapped_at""",
            (active_date,)
        )
        for snap in cur.fetchall():
            sk = (snap['away_team'], snap['home_team'])
            if sk not in line_snapshots:
                line_snapshots[sk] = []
            line_snapshots[sk].append({
                'spread': snap['spread_home'],
                'total': snap['total'],
                'at': snap['snapped_at'],
            })
    except Exception:
        pass

    seen = set()
    games = []
    for r in rows:
        key = (r['away_team'], r['home_team'])
        if key in seen:
            continue
        seen.add(key)

        is_live = r['home_score'] is not None and r['away_score'] is not None
        status = 'final' if is_live else 'scheduled'

        spread_open = r['spread_home_open']
        spread_now = r['spread_home']
        rlm = None
        if spread_open is not None and spread_now is not None:
            move = spread_now - spread_open
            if abs(move) >= 1.0:
                rlm = 'home' if move < 0 else 'away'

        game_data = {
            'id': r['id'],
            'away': r['away_team'],
            'home': r['home_team'],
            'time': _fmt_time(r['game_time']),
            'status': status,
            'spread_home': r['spread_home'],
            'spread_away': r['spread_away'],
            'spread_home_open': spread_open,
            'total': r['total'],
            'total_open': r['total_open'],
            'home_ml': r['home_ml'],
            'away_ml': r['away_ml'],
            'home_spread_odds': r['home_spread_odds'],
            'away_spread_odds': r['away_spread_odds'],
            'home_spread_book': r['home_spread_book'],
            'away_spread_book': r['away_spread_book'],
            'spread_h1_home': r['spread_h1_home'],
            'spread_h1_away': r['spread_h1_away'],
            'total_h1': r['total_h1'],
            'home_record': r['home_record'],
            'away_record': r['away_record'],
            'home_score': r['home_score'],
            'away_score': r['away_score'],
            'rlm': rlm,
            'snapshots': line_snapshots.get(key, []),
        }

        try:
            game_data['consensus_spread'] = r['rundown_spread_consensus']
            game_data['spread_range'] = r['rundown_spread_range']
            game_data['num_books'] = r['rundown_num_books']
        except (KeyError, IndexError):
            pass

        ma = model_analysis.get(key)
        if ma:
            game_data['model'] = {
                'predicted_margin': ma.get('predicted_margin'),
                'cover_prob': ma.get('cover_prob'),
                'edge': ma.get('edge', ma.get('adjusted_edge')),
                'raw_edge': ma.get('raw_edge'),
                'rating': ma.get('rating'),
                'pick_side': ma.get('pick_side'),
                'pick': ma.get('pick'),
                'line': ma.get('line'),
                'passes': ma.get('passes', False),
                'reason': ma.get('reason', ''),
                'fail_reasons': ma.get('fail_reasons', []),
                'signals': ma.get('signals') or pick_signals.get(key, []),
                'playable_to': ma.get('playable_to'),
            }

        games.append(game_data)

    conn.close()
    return jsonify({'games': games, 'date': active_date, 'count': len(games)})


@picks_bp.route('/live-scores')
def live_scores():
    """Poll ESPN scoreboard for live game data (scores, quarter, clock)."""
    import requests as http_requests
    sport = request.args.get('sport', 'nba')

    espn_url = 'https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard'
    if sport == 'wnba':
        espn_url = 'https://site.api.espn.com/apis/site/v2/sports/basketball/wnba/scoreboard'

    try:
        resp = http_requests.get(espn_url, timeout=10)
        resp.raise_for_status()
        data = resp.json()
    except Exception:
        return jsonify({'scores': [], 'error': 'ESPN unavailable'})

    scores = []
    for event in data.get('events', []):
        comp = event.get('competitions', [{}])[0]
        status = comp.get('status', {})
        status_type = status.get('type', {})
        clock = status.get('displayClock', '')
        period = status.get('period', 0)
        state = status_type.get('name', '')

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

        scores.append({
            'home': home_name,
            'away': away_name,
            'home_score': int(home.get('score', 0)),
            'away_score': int(away.get('score', 0)),
            'clock': clock,
            'period': period,
            'state': state,
        })

    return jsonify({'scores': scores})


@picks_bp.route('/watch', methods=['POST'])
def watch_game():
    """Toggle watching a game for line movement alerts."""
    from app import get_current_user_obj
    user = get_current_user_obj()
    if not user:
        return jsonify({'error': 'Login required'}), 401

    data = request.get_json() or {}
    game_id = data.get('game_id')
    if not game_id:
        return jsonify({'error': 'game_id required'}), 400

    existing = WatchedGame.query.filter_by(user_id=user.id, game_id=game_id).first()
    if existing:
        db.session.delete(existing)
        db.session.commit()
        return jsonify({'watching': False})

    wg = WatchedGame(
        user_id=user.id,
        game_id=game_id,
        game_date=data.get('game_date', ''),
        home_team=data.get('home', ''),
        away_team=data.get('away', ''),
        line_at_watch=data.get('spread_home'),
    )
    db.session.add(wg)
    db.session.commit()
    return jsonify({'watching': True})


@picks_bp.route('/watched', methods=['GET'])
def get_watched_games():
    """Return IDs of games the current user is watching."""
    from app import get_current_user_obj
    user = get_current_user_obj()
    if not user:
        return jsonify({'game_ids': []})

    today_str = _get_et_date()
    watched = WatchedGame.query.filter_by(user_id=user.id, game_date=today_str).all()
    return jsonify({'game_ids': [w.game_id for w in watched]})
