from flask import Blueprint, jsonify, request
from models import db, Pick, Pass, ModelRun, UserBet, TrackedBet, WatchedGame
from datetime import datetime, timedelta, timezone
from sport_config import get_sport_config, get_phase_label
import sqlite3

picks_bp = Blueprint('picks', __name__)

try:
    from db_path import get_sqlite_path
except ImportError:
    def get_sqlite_path():
        return 'sharp_picks.db'

EDGE_THRESHOLD = 3.5
PROB_PER_POINT = 2.5


def _calc_line_stability(snapshots, game_data):
    """Compute line stability from spread snapshots and book disagreement.
    Returns {level, label, total_move, changes, spread_range} or None."""
    spreads = [s['spread'] for s in snapshots if s.get('spread') is not None]
    if len(spreads) < 2:
        return None

    changes = sum(1 for i in range(1, len(spreads)) if spreads[i] != spreads[i - 1])
    total_move = abs(spreads[-1] - spreads[0]) if len(spreads) >= 2 else 0
    max_swing = max(spreads) - min(spreads) if spreads else 0

    spread_range = None
    try:
        sr = game_data.get('spread_range')
        if sr and isinstance(sr, str) and ' to ' in sr:
            parts = sr.split(' to ')
            spread_range = abs(float(parts[1]) - float(parts[0]))
    except (ValueError, IndexError):
        pass

    volatility = max_swing + (changes * 0.5) + (spread_range or 0) * 0.5

    if volatility >= 4.0:
        level, label = 'low', 'Low'
    elif volatility >= 2.0:
        level, label = 'medium', 'Medium'
    else:
        level, label = 'high', 'High'

    return {
        'level': level,
        'label': label,
        'total_move': round(total_move, 1),
        'changes': changes,
        'max_swing': round(max_swing, 1),
        'spread_range': round(spread_range, 1) if spread_range else None,
    }


def _detect_sharp_action(spread_open, spread_now, snapshots, game_data, model_data=None):
    """Composite sharp-money detection using all available market signals.

    Returns dict with side, confidence (0-100), evidence list, or None.
    """
    if spread_open is None or spread_now is None:
        return None

    spread_move = spread_now - spread_open
    abs_move = abs(spread_move)
    if abs_move < 0.5:
        return None

    # Primary signal: which direction did the line move?
    # Negative move = home got more points (line moved toward home)
    # Books move lines AGAINST sharp money, so if line moves toward home,
    # sharps are on the away side (betting away, forcing books to give home more points)
    move_side = 'away' if spread_move < 0 else 'home'

    evidence = []
    score = 0.0

    # --- Signal 1: Spread movement magnitude ---
    if abs_move >= 2.0:
        score += 30
        evidence.append(f"Spread moved {abs_move:.1f}pts. Significant sharp pressure")
    elif abs_move >= 1.0:
        score += 20
        evidence.append(f"Spread moved {abs_move:.1f}pts from open")
    else:
        score += 8
        evidence.append(f"Spread moved {abs_move:.1f}pts. Minor shift")

    # --- Signal 2: Snapshot trend consistency ---
    if snapshots and len(snapshots) >= 3:
        spreads = [s['spread'] for s in snapshots if s.get('spread') is not None]
        if len(spreads) >= 3:
            directional = sum(
                1 for i in range(1, len(spreads))
                if (spreads[i] - spreads[i - 1]) * spread_move > 0
            )
            consistency = directional / (len(spreads) - 1) if len(spreads) > 1 else 0
            if consistency >= 0.75:
                score += 15
                evidence.append("Sustained one-directional movement across snapshots")
            elif consistency >= 0.5:
                score += 8
                evidence.append("Line trending in one direction")

    # --- Signal 3: Juice / odds shift ---
    home_odds = game_data.get('home_spread_odds')
    away_odds = game_data.get('away_spread_odds')
    if home_odds and away_odds:
        # Standard juice is -110/-110. Heavier juice on a side means books
        # are trying to balance action — sharps are on the cheaper side.
        # More negative = more expensive for that side's bettors.
        juice_diff = abs(home_odds) - abs(away_odds)
        # If sharps are on 'home', books make home cheaper (less negative)
        # and away more expensive (more negative) to attract public to away.
        # Actually: books make the sharp side MORE expensive to discourage it.
        # So heavier juice on a side = books think sharps are there.
        if move_side == 'home' and juice_diff > 5:
            # Home is more expensive — books pricing against home bettors
            score += 10
            evidence.append(f"Juice favors away side ({home_odds}/{away_odds}). Books pricing against sharp side")
        elif move_side == 'away' and juice_diff < -5:
            score += 10
            evidence.append(f"Juice favors home side ({home_odds}/{away_odds}). Books pricing against sharp side")
        elif (move_side == 'home' and juice_diff < -10) or (move_side == 'away' and juice_diff > 10):
            score -= 5  # Juice contradicts the move direction

    # --- Signal 4: Book disagreement (spread range) ---
    spread_range_str = game_data.get('spread_range')
    if spread_range_str and isinstance(spread_range_str, str) and ' to ' in spread_range_str:
        try:
            parts = spread_range_str.split(' to ')
            sr = abs(float(parts[1]) - float(parts[0]))
            if sr >= 2.0:
                score += 10
                evidence.append(f"Books disagree by {sr:.1f}pts. Market still adjusting")
            elif sr >= 1.0:
                score += 5
                evidence.append(f"Moderate book disagreement ({sr:.1f}pt range)")
        except (ValueError, IndexError):
            pass

    # --- Signal 5: Consensus vs current spread ---
    consensus = game_data.get('consensus_spread')
    if consensus is not None and spread_now is not None:
        consensus_diff = spread_now - consensus
        # If current differs from consensus in the same direction as the move,
        # the best-line book has moved further than the market — steam move
        if abs(consensus_diff) >= 0.5 and (consensus_diff * spread_move > 0):
            score += 10
            evidence.append(f"Best line ({spread_now:+.1f}) ahead of consensus ({consensus:+.1f}). Steam detected")

    # --- Signal 6: Moneyline confirmation ---
    home_ml = game_data.get('home_ml')
    away_ml = game_data.get('away_ml')
    home_ml_open = game_data.get('home_ml_open')
    away_ml_open = game_data.get('away_ml_open')
    if home_ml and away_ml and home_ml_open and away_ml_open:
        # Convert MLs to implied probability shift
        def ml_to_prob(ml):
            if ml is None:
                return None
            return abs(ml) / (abs(ml) + 100) if ml < 0 else 100 / (ml + 100)

        h_prob_now = ml_to_prob(home_ml)
        h_prob_open = ml_to_prob(home_ml_open)
        if h_prob_now is not None and h_prob_open is not None:
            ml_shift = h_prob_now - h_prob_open
            # If spread moved toward home (sharps on away) AND home ML implied prob dropped,
            # that confirms sharps are on away
            if move_side == 'away' and ml_shift < -0.02:
                score += 12
                evidence.append("Moneyline confirms: home implied probability dropped")
            elif move_side == 'home' and ml_shift > 0.02:
                score += 12
                evidence.append("Moneyline confirms: home implied probability rose")
            elif (move_side == 'away' and ml_shift > 0.03) or (move_side == 'home' and ml_shift < -0.03):
                score -= 5  # ML contradicts spread direction

    # --- Signal 7: Model alignment ---
    if model_data:
        model_side = model_data.get('pick_side')
        if model_side:
            model_side_lower = model_side.lower()
            if model_side_lower == move_side:
                score += 15
                evidence.append("Model projection aligns with sharp-side movement")
            elif model_side_lower in ('home', 'away') and model_side_lower != move_side:
                score -= 5

    # Clamp and classify
    score = max(0, min(score, 100))
    if score < 15:
        return None

    if score >= 60:
        confidence = 'high'
    elif score >= 35:
        confidence = 'moderate'
    else:
        confidence = 'low'

    return {
        'side': move_side,
        'confidence': confidence,
        'score': round(score),
        'evidence': evidence,
        'spread_open': spread_open,
        'spread_now': spread_now,
        'move': round(abs_move, 1),
    }


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

        # Model vs Market: market_line = spread we're betting at; model_projection = model's fair spread
        market_line = round(pick.line, 1) if pick.line is not None else None
        if pick.predicted_margin is not None:
            # predicted_margin = home - away; our side's fair spread = -predicted_margin (home or away)
            model_projection = round(-float(pick.predicted_margin), 1)
        else:
            model_projection = None

        # Daily market context (today's signal from market report) for this pick's date/sport
        market_context = None
        try:
            from public_api import build_market_report_dict
            report = build_market_report_dict(pick.game_date, pick.sport)
            if report.get('available') and report.get('insight'):
                market_context = report['insight']
        except Exception:
            pass

        actual_odds = pick.market_odds or -110
        stake = calculate_stake_guidance(pick.edge_pct or 0, pick.model_confidence or 0.5, actual_odds)

        cfg = get_sport_config(sport)
        phase = cfg.get('model_phase', 'deployment')
        pick_data = {
            'type': 'pick',
            'id': pick.id,
            'sport': pick.sport,
            'model_phase': phase,
            'phase_label': get_phase_label(phase),
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
            'market_line': market_line,
            'model_projection': model_projection,
            'market_context': market_context,
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
            pick_data['line'] = None
            pick_data['edge_pct'] = None
            pick_data['model_confidence'] = None
            pick_data['predicted_margin'] = None
            pick_data['sigma'] = None
            pick_data['z_score'] = None
            pick_data['raw_edge'] = None
            pick_data['cover_prob'] = None
            pick_data['implied_prob'] = None
            pick_data['model_signals'] = []
            pick_data['market_line'] = None
            pick_data['model_projection'] = None
            pick_data['market_context'] = None
            pick_data['market_odds'] = None
            pick_data['stake_guidance'] = None
            pick_data['playable_to'] = None
            pick_data['closing_spread'] = None
            pick_data['clv'] = None
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
        try:
            from zoneinfo import ZoneInfo
            _now_et = datetime.now(ZoneInfo('America/New_York'))
        except ImportError:
            _now_et = datetime.utcnow() - timedelta(hours=5)
        week_start = (_now_et - timedelta(days=_now_et.weekday())).strftime('%Y-%m-%d')
        picks_this_week = Pick.query.filter(Pick.game_date >= week_start, Pick.sport == sport).count()
        passes_this_week = Pass.query.filter(Pass.date >= week_start, Pass.sport == sport).count()
        total_picks = Pick.query.filter(Pick.sport == sport).count()
        total_passes = Pass.query.filter(Pass.sport == sport).count()
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
                'home_team': pass_entry.whatif_home_team,
                'away_team': pass_entry.whatif_away_team,
                'pick_side': pass_entry.whatif_pick_side,
                'line': pass_entry.whatif_line,
                'cover_prob': pass_entry.whatif_cover_prob,
            }

        cfg = get_sport_config(sport)
        phase = cfg.get('model_phase', 'deployment')
        return jsonify({
            'type': pass_type,
            'model_phase': phase,
            'phase_label': get_phase_label(phase),
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
    cfg_wait = get_sport_config(sport)
    model_run_hour = cfg_wait.get('model_run_hour', 10)
    model_runs_at = f'{model_run_hour}:00 AM ET' if model_run_hour <= 12 else f'{model_run_hour - 12}:00 PM ET'

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

    espn_sport_map = {
        'nba': 'basketball/nba',
        'wnba': 'womens-basketball/wnba',
        'mlb': 'baseball/mlb',
    }
    espn_sport = espn_sport_map.get(sport, 'basketball/nba')
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
        games_table = 'mlb_games' if sport == 'mlb' else ('wnba_games' if sport == 'wnba' else 'games')
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
        'model_run_hour': model_run_hour,
    })


@picks_bp.route('/last-resolved')
def last_resolved():
    """Return the most recently graded pick (win/loss/push) for resolution banner"""
    today_str = _get_et_date()
    sport = request.args.get('sport', 'nba')
    pick = Pick.query.filter(
        Pick.result.in_(['win', 'loss', 'push']),
        Pick.game_date != today_str,
        Pick.sport == sport,
    ).order_by(Pick.published_at.desc()).first()

    if not pick:
        return jsonify(None)

    from app import get_current_user_obj
    cu = get_current_user_obj()
    is_pro = cu is not None and cu.is_pro
    if not is_pro:
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
        'clv': pick.clv,
        'closing_spread': pick.closing_spread,
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
                'summary': f"{p.away_team} @ {p.home_team} · {p.side} {p.line}",
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
    Falls back to the next upcoming date if today has no games.
    Optional ?date=YYYY-MM-DD to fetch a specific date."""
    today_str = request.args.get('date', '').strip() or _get_et_date()
    sport = request.args.get('sport', 'nba')
    games_table = 'mlb_games' if sport == 'mlb' else ('wnba_games' if sport == 'wnba' else 'games')

    _live_cols = ', game_status, current_period, game_clock'
    if sport == 'mlb':
        _select_cols = """id, home_team, away_team, game_time, game_date,
                    spread_home, spread_away, total, home_ml, away_ml,
                    spread_home_open, total_open, home_ml_open, away_ml_open,
                    home_spread_odds, away_spread_odds,
                    home_spread_book, away_spread_book,
                    home_record, away_record,
                    home_score, away_score,
                    home_pitcher, away_pitcher"""
    else:
        _select_cols = """id, home_team, away_team, game_time, game_date,
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
        try:
            cur.execute(
                f"SELECT {_select_cols}{_live_cols} FROM {games_table} WHERE game_date = ? ORDER BY game_time",
                (today_str,)
            )
        except Exception:
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
                try:
                    cur.execute(
                        f"SELECT {_select_cols}{_live_cols} FROM {games_table} WHERE game_date = ? ORDER BY game_time",
                        (next_date,)
                    )
                except Exception:
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
            return et.strftime('%-I:%M %p ET')
        except Exception:
            return None

    pick_results = {}
    try:
        today_picks = Pick.query.filter_by(game_date=active_date, sport=sport).all()
        for p in today_picks:
            pk = (p.away_team, p.home_team)
            pick_results[pk] = {
                'result': p.result,
                'units': p.profit_units,
                'side': p.side,
                'line': p.line,
            }
    except Exception:
        pass

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

        db_status = None
        try:
            db_status = r['game_status']
        except (KeyError, IndexError):
            pass

        if db_status in ('in_progress', 'final'):
            status = db_status
        else:
            status = 'scheduled'

        current_period = None
        game_clock = None
        try:
            current_period = r['current_period']
            game_clock = r['game_clock']
        except (KeyError, IndexError):
            pass

        spread_open = r['spread_home_open']
        spread_now = r['spread_home']

        game_data = {
            'id': r['id'],
            'away': r['away_team'],
            'home': r['home_team'],
            'time': _fmt_time(r['game_time']),
            'game_date': r['game_date'] if 'game_date' in r.keys() else active_date,
            'status': status,
            'current_period': current_period,
            'game_clock': game_clock,
            'spread_home': r['spread_home'],
            'spread_away': r['spread_away'],
            'spread_home_open': spread_open,
            'total': r['total'],
            'total_open': r['total_open'],
            'home_ml': r['home_ml'],
            'away_ml': r['away_ml'],
            'home_ml_open': r['home_ml_open'],
            'away_ml_open': r['away_ml_open'],
            'home_spread_odds': r['home_spread_odds'],
            'away_spread_odds': r['away_spread_odds'],
            'home_spread_book': r['home_spread_book'],
            'away_spread_book': r['away_spread_book'],
            'spread_h1_home': r['spread_h1_home'] if sport != 'mlb' else None,
            'spread_h1_away': r['spread_h1_away'] if sport != 'mlb' else None,
            'total_h1': r['total_h1'] if sport != 'mlb' else None,
            'home_record': r['home_record'] if r['home_record'] and r['home_record'] != 'N/A' else None,
            'away_record': r['away_record'] if r['away_record'] and r['away_record'] != 'N/A' else None,
            'home_score': r['home_score'] if status != 'scheduled' else None,
            'away_score': r['away_score'] if status != 'scheduled' else None,
            'snapshots': line_snapshots.get(key, []),
        }

        if sport == 'mlb':
            try:
                game_data['home_pitcher'] = r['home_pitcher']
                game_data['away_pitcher'] = r['away_pitcher']
            except (KeyError, IndexError):
                pass

        try:
            game_data['consensus_spread'] = r['rundown_spread_consensus']
            game_data['spread_range'] = r['rundown_spread_range']
            game_data['num_books'] = r['rundown_num_books']
        except (KeyError, IndexError):
            pass

        snaps = line_snapshots.get(key, [])
        game_data['line_stability'] = _calc_line_stability(snaps, game_data)

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

        sharp = _detect_sharp_action(
            spread_open, spread_now, snaps, game_data, ma
        )
        game_data['rlm'] = sharp['side'] if sharp else None
        game_data['sharp_action'] = sharp

        pr = pick_results.get(key)
        if pr:
            game_data['pick_result'] = pr

        if status == 'in_progress' and ma and ma.get('passes'):
            pick_side = ma.get('pick_side', '')
            h_score = r['home_score'] or 0
            a_score = r['away_score'] or 0
            spread_val = ma.get('line') or r['spread_home']
            if spread_val is not None:
                is_home_pick = 'home' in pick_side.lower() if pick_side else False
                if is_home_pick:
                    margin = h_score - a_score
                    adjusted = margin + spread_val
                else:
                    margin = a_score - h_score
                    adjusted = margin + (r['spread_away'] or -spread_val if r['spread_away'] else -spread_val)

                game_data['cover'] = {
                    'status': 'covering' if adjusted > 0 else 'not_covering',
                    'margin': round(abs(adjusted), 1),
                }

        games.append(game_data)

    conn.close()
    return jsonify({'games': games, 'date': active_date, 'count': len(games)})


_live_scores_cache = {}

@picks_bp.route('/live-scores')
def live_scores():
    """Poll ESPN scoreboard for live game data (scores, quarter, clock)."""
    import time as _time
    import requests as http_requests
    sport = request.args.get('sport', 'nba')

    cached = _live_scores_cache.get(sport)
    if cached and (_time.time() - cached['ts']) < 10:
        return jsonify({'scores': cached['scores']})

    espn_sport_paths = {
        'nba': 'basketball/nba',
        'wnba': 'basketball/wnba',
        'mlb': 'baseball/mlb',
    }
    espn_url = f"https://site.api.espn.com/apis/site/v2/sports/{espn_sport_paths.get(sport, 'basketball/nba')}/scoreboard"

    try:
        resp = http_requests.get(espn_url, timeout=10)
        resp.raise_for_status()
        data = resp.json()
    except Exception:
        if cached:
            return jsonify({'scores': cached['scores']})
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

        home_records = home.get('records', [])
        away_records = away.get('records', [])
        home_record = next((r.get('summary') for r in home_records if r.get('type') == 'total'), None)
        away_record = next((r.get('summary') for r in away_records if r.get('type') == 'total'), None)

        scores.append({
            'home': home_name,
            'away': away_name,
            'home_score': int(home.get('score', 0)),
            'away_score': int(away.get('score', 0)),
            'clock': clock,
            'period': period,
            'state': state,
            'home_record': home_record,
            'away_record': away_record,
        })

    _live_scores_cache[sport] = {'scores': scores, 'ts': _time.time()}
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
    sport = data.get('sport', 'nba')
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
        sport=sport,
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
    sport = request.args.get('sport', 'nba')
    watched = WatchedGame.query.filter_by(user_id=user.id, game_date=today_str, sport=sport).all()
    return jsonify({'game_ids': [w.game_id for w in watched]})
