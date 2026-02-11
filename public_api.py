from flask import Blueprint, jsonify
from models import db, Pick, Pass, FoundingCounter
from sqlalchemy import func

public_bp = Blueprint('public', __name__)


@public_bp.route('/record')
def record():
    picks = Pick.query.order_by(Pick.published_at.desc()).all()
    passes = Pass.query.order_by(Pass.created_at.desc()).all()

    wins = sum(1 for p in picks if p.result == 'win')
    losses = sum(1 for p in picks if p.result == 'loss')
    pending = sum(1 for p in picks if p.result == 'pending')
    total_pnl = sum(p.pnl or 0 for p in picks if p.result in ('win', 'loss'))

    return jsonify({
        'picks': [{
            'id': p.id,
            'published_at': p.published_at.isoformat() if p.published_at else None,
            'game_date': p.game_date,
            'side': p.side,
            'edge_pct': p.edge_pct,
            'result': p.result,
            'pnl': p.pnl,
            'away_team': p.away_team,
            'home_team': p.home_team,
        } for p in picks],
        'passes': [{
            'id': p.id,
            'date': p.date,
            'games_analyzed': p.games_analyzed,
            'closest_edge_pct': p.closest_edge_pct,
        } for p in passes[-30:]],
        'stats': {
            'wins': wins,
            'losses': losses,
            'pending': pending,
            'total_picks': len(picks),
            'total_passes': len(passes),
            'pnl': round(total_pnl, 2),
            'win_rate': round(wins / (wins + losses) * 100, 1) if (wins + losses) > 0 else 0,
            'selectivity': round(len(picks) / (len(picks) + len(passes)) * 100, 1) if (len(picks) + len(passes)) > 0 else 0,
        }
    })


@public_bp.route('/stats')
def stats():
    wins = Pick.query.filter_by(result='win').count()
    losses = Pick.query.filter_by(result='loss').count()
    pending = Pick.query.filter_by(result='pending').count()
    total_picks = Pick.query.count()
    total_passes = Pass.query.count()
    total_pnl = db.session.query(func.sum(Pick.pnl)).filter(
        Pick.result.in_(['win', 'loss'])
    ).scalar() or 0

    total_decided = wins + losses
    roi = round((total_pnl / (total_decided * 110)) * 100, 1) if total_decided > 0 else 0

    return jsonify({
        'record': f'{wins}-{losses}',
        'wins': wins,
        'losses': losses,
        'pending': pending,
        'total_picks': total_picks,
        'total_passes': total_passes,
        'pnl': round(total_pnl, 2),
        'roi': roi,
        'win_rate': round(wins / total_decided * 100, 1) if total_decided > 0 else 0,
        'selectivity': round(total_picks / (total_picks + total_passes) * 100, 1) if (total_picks + total_passes) > 0 else 0,
        'capital_preserved_days': total_passes,
    })


@public_bp.route('/founding-count')
def founding_count():
    counter = FoundingCounter.query.first()
    if not counter:
        counter = FoundingCounter(current_count=0, closed=False)
        db.session.add(counter)
        db.session.commit()

    return jsonify({
        'current': counter.current_count,
        'total': 500,
        'open': not counter.closed,
        'remaining': max(0, 500 - counter.current_count),
    })
