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


@public_bp.route('/calibration')
def calibration():
    """Production calibration tracking.
    Buckets resolved picks by confidence tier and reports actual cover rates.
    Institutional honesty: does 60% confidence actually win ~60%?"""
    resolved = Pick.query.filter(Pick.result_ats.in_(['W', 'L'])).all()

    buckets = [
        {'label': '55-57%', 'low': 0.55, 'high': 0.57},
        {'label': '57-60%', 'low': 0.57, 'high': 0.60},
        {'label': '60%+', 'low': 0.60, 'high': 1.01},
    ]

    results = []
    for bucket in buckets:
        in_bucket = [p for p in resolved if p.model_confidence is not None
                     and bucket['low'] <= p.model_confidence < bucket['high']]
        wins = sum(1 for p in in_bucket if p.result_ats == 'W')
        total = len(in_bucket)
        actual_rate = round(wins / total * 100, 1) if total > 0 else None

        if total > 0 and bucket['high'] > 1.0:
            empirical_mean = sum(p.model_confidence for p in in_bucket) / total
            expected_mid = round(empirical_mean * 100, 1)
        elif bucket['high'] > 1.0:
            expected_mid = 62.5
        else:
            expected_mid = round((bucket['low'] + bucket['high']) / 2 * 100, 1)

        gap = round(actual_rate - expected_mid, 1) if actual_rate is not None else None

        results.append({
            'bucket': bucket['label'],
            'picks': total,
            'wins': wins,
            'losses': total - wins,
            'actual_cover_rate': actual_rate,
            'expected_midpoint': expected_mid,
            'gap': gap,
            'status': 'insufficient_data' if total < 10 else (
                'overconfident' if gap is not None and gap < -3.0 else (
                'underconfident' if gap is not None and gap > 3.0 else 'calibrated'
                )
            ),
        })

    total_resolved = len(resolved)
    total_wins = sum(1 for p in resolved if p.result_ats == 'W')

    from datetime import timedelta
    from datetime import datetime as dt
    week_ago = dt.now() - timedelta(days=7)
    recent = [p for p in resolved if p.result_resolved_at and p.result_resolved_at >= week_ago]
    recent_wins = sum(1 for p in recent if p.result_ats == 'W')
    recent_total = len(recent)

    has_data = any(b['status'] != 'insufficient_data' for b in results)
    has_problem = any(b['status'] in ('overconfident', 'underconfident') for b in results)
    if not has_data:
        health = 'insufficient_data'
    elif has_problem:
        health = 'needs_review'
    else:
        health = 'calibrated'

    return jsonify({
        'buckets': results,
        'overall': {
            'total_graded': total_resolved,
            'wins': total_wins,
            'losses': total_resolved - total_wins,
            'cover_rate': round(total_wins / total_resolved * 100, 1) if total_resolved > 0 else None,
        },
        'last_7_days': {
            'graded': recent_total,
            'wins': recent_wins,
            'cover_rate': round(recent_wins / recent_total * 100, 1) if recent_total > 0 else None,
        },
        'health': health,
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
