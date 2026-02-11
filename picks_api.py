from flask import Blueprint, jsonify, request
from flask_login import current_user, login_required
from models import db, Pick, Pass, ModelRun, UserBet
from datetime import datetime

picks_bp = Blueprint('picks', __name__)

EDGE_THRESHOLD = 3.5


@picks_bp.route('/today')
def today():
    today_str = datetime.now().strftime('%Y-%m-%d')

    pick = Pick.query.filter(
        Pick.game_date.like(f'{today_str}%')
    ).order_by(Pick.published_at.desc()).first()

    if pick:
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
            'result': pick.result,
            'pnl': pick.pnl,
            'published_at': pick.published_at.isoformat() if pick.published_at else None,
        }
        is_pro = current_user.is_authenticated and current_user.is_pro
        if not is_pro:
            pick_data['side'] = 'Upgrade to see pick'
            pick_data['edge_pct'] = None
            pick_data['model_confidence'] = None
            pick_data['locked'] = True
        else:
            pick_data['locked'] = False
        return jsonify(pick_data)

    pass_entry = Pass.query.filter_by(date=today_str).first()
    if pass_entry:
        return jsonify({
            'type': 'pass',
            'date': pass_entry.date,
            'games_analyzed': pass_entry.games_analyzed,
            'closest_edge_pct': pass_entry.closest_edge_pct,
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
            'edge_pct': p.edge_pct,
            'model_confidence': p.model_confidence,
            'result': p.result,
            'pnl': p.pnl,
        } for p in picks.items],
        'total': picks.total,
        'page': picks.page,
        'pages': picks.pages,
    })


@picks_bp.route('/<pick_id>')
def get_pick(pick_id):
    pick = Pick.query.get_or_404(pick_id)
    return jsonify({
        'id': pick.id,
        'published_at': pick.published_at.isoformat() if pick.published_at else None,
        'sport': pick.sport,
        'away_team': pick.away_team,
        'home_team': pick.home_team,
        'game_date': pick.game_date,
        'side': pick.side,
        'line': pick.line,
        'edge_pct': pick.edge_pct,
        'model_confidence': pick.model_confidence,
        'result': pick.result,
        'pnl': pick.pnl,
        'notes': pick.notes,
    })
