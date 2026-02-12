from flask import Blueprint, jsonify, request
from flask_login import current_user, login_required
from models import db, Pick, Pass, ModelRun, UserBet
from datetime import datetime

picks_bp = Blueprint('picks', __name__)

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


@picks_bp.route('/today')
def today():
    today_str = datetime.now().strftime('%Y-%m-%d')

    pick = Pick.query.filter(
        Pick.game_date.like(f'{today_str}%')
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
            'cover_prob': pick.cover_prob,
            'implied_prob': pick.implied_prob,
            'market_odds': pick.market_odds,
            'model_line': model_line,
            'market_line': market_line,
            'model_signals': model_signals,
            'result': pick.result,
            'pnl': pick.pnl,
            'published_at': pick.published_at.isoformat() if pick.published_at else None,
            'posted_time': '2h before tip',
            'best_book': pick.sportsbook or 'DraftKings',
            'stake_guidance': stake,
            'disclaimer': 'For informational and entertainment purposes only. No guaranteed outcomes. Past performance does not guarantee future results. Please gamble responsibly.',
        }
        is_pro = current_user.is_authenticated and current_user.is_pro
        if not is_pro:
            pick_data['side'] = 'Upgrade to see pick'
            pick_data['edge_pct'] = None
            pick_data['model_confidence'] = None
            pick_data['predicted_margin'] = None
            pick_data['cover_prob'] = None
            pick_data['implied_prob'] = None
            pick_data['model_signals'] = []
            pick_data['model_line'] = None
            pick_data['market_line'] = None
            pick_data['stake_guidance'] = None
            pick_data['locked'] = True
        else:
            pick_data['locked'] = False
        return jsonify(pick_data)

    pass_entry = Pass.query.filter_by(date=today_str).first()
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

        return jsonify({
            'type': 'pass',
            'date': pass_entry.date,
            'games_analyzed': pass_entry.games_analyzed,
            'closest_edge_pct': pass_entry.closest_edge_pct,
            'picks_this_week': picks_this_week,
            'passes_this_week': passes_this_week,
            'selectivity': selectivity,
            'days_per_bet': days_per_bet,
            'message': 'No qualifying edge found today. The model analyzed all available games and none met the threshold. Discipline preserved.'
        })

    return jsonify({
        'type': 'waiting',
        'message': 'Model has not run yet today. Check back later.'
    })


@picks_bp.route('/history')
def history():
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)

    picks = Pick.query.order_by(Pick.published_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )

    return jsonify({
        'picks': [{
            'id': p.id,
            'published_at': p.published_at.isoformat() if p.published_at else None,
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
        } for p in picks.items],
        'total': picks.total,
        'page': picks.page,
        'pages': picks.pages,
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
        'published_at': pick.published_at.isoformat() if pick.published_at else None,
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
        'notes': pick.notes,
        'disclaimer': 'For informational and entertainment purposes only. No guaranteed outcomes. Past performance does not guarantee future results. Please gamble responsibly.',
    })
