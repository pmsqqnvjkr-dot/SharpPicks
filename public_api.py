from flask import Blueprint, jsonify
from models import db, Pick, Pass, ModelRun, FoundingCounter
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

    from datetime import datetime
    CALIBRATION_DATE = datetime(2026, 2, 12)

    return jsonify({
        'calibration_note': 'Model calibrated Feb 12, 2026. Prior picks used raw predictions without market-aware shrinkage.',
        'calibration_date': '2026-02-12',
        'picks': [{
            'id': p.id,
            'published_at': (p.published_at.isoformat() + 'Z') if p.published_at else None,
            'game_date': p.game_date,
            'side': p.side,
            'edge_pct': p.edge_pct,
            'result': p.result,
            'pnl': p.pnl,
            'away_team': p.away_team,
            'home_team': p.home_team,
            'pre_calibration': p.published_at < CALIBRATION_DATE if p.published_at else False,
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


@public_bp.route('/dashboard-stats')
def dashboard_stats():
    from datetime import timedelta
    from datetime import datetime as dt

    picks = Pick.query.order_by(Pick.game_date.asc()).all()
    passes = Pass.query.all()
    resolved = [p for p in picks if p.result in ('win', 'loss')]
    resolved.sort(key=lambda p: p.game_date or '')

    total_picks = len(picks)
    total_passes = len(passes)
    total_days = total_picks + total_passes
    wins = sum(1 for p in resolved if p.result == 'win')
    losses = sum(1 for p in resolved if p.result == 'loss')
    total_pnl = sum(p.pnl or 0 for p in resolved)

    total_wagered = len(resolved) * 110
    roi = round((total_pnl / total_wagered) * 100, 1) if total_wagered > 0 else 0

    equity_curve = []
    running_pnl = 0
    max_pnl = 0
    max_drawdown = 0
    for p in resolved:
        running_pnl += (p.pnl or 0)
        max_pnl = max(max_pnl, running_pnl)
        drawdown = max_pnl - running_pnl
        if drawdown > max_drawdown:
            max_drawdown = drawdown
        equity_curve.append({
            'date': p.game_date,
            'pnl': round(running_pnl, 2),
            'side': p.side,
            'result': p.result,
        })

    if max_pnl > 0:
        drawdown_pct = round((max_drawdown / max_pnl) * 100, 1)
    elif max_drawdown > 0 and total_wagered > 0:
        drawdown_pct = round((max_drawdown / total_wagered) * 100, 1)
    else:
        drawdown_pct = 0

    pick_dates = sorted([p.game_date for p in picks if p.game_date])
    if len(pick_dates) >= 2:
        gaps = []
        for i in range(1, len(pick_dates)):
            try:
                d1 = dt.strptime(pick_dates[i-1], '%Y-%m-%d')
                d2 = dt.strptime(pick_dates[i], '%Y-%m-%d')
                gaps.append((d2 - d1).days)
            except (ValueError, TypeError):
                pass
        avg_days_between = round(sum(gaps) / len(gaps), 1) if gaps else 0
    else:
        avg_days_between = 0

    edges = [p.edge_pct for p in picks if p.edge_pct is not None]
    avg_edge = round(sum(edges) / len(edges), 1) if edges else 0

    line_moves = []
    for p in picks:
        if p.line_open is not None and p.line is not None:
            line_moves.append(abs(p.line - p.line_open))
    avg_line_move = round(sum(line_moves) / len(line_moves), 1) if line_moves else 0

    selectivity = round((total_picks / total_days) * 100, 1) if total_days > 0 else 0

    capital_preserved = round(total_passes * 110 * 0.04, 0)

    if selectivity <= 20:
        restraint_grade = 'A+'
    elif selectivity <= 30:
        restraint_grade = 'A'
    elif selectivity <= 40:
        restraint_grade = 'B+'
    elif selectivity <= 50:
        restraint_grade = 'B'
    else:
        restraint_grade = 'C'

    latest_sigma = None
    for p in reversed(picks):
        if p.sigma is not None:
            latest_sigma = round(p.sigma, 1)
            break

    last_run = ModelRun.query.order_by(ModelRun.created_at.desc()).first()
    last_retrain_date = last_run.date if last_run else None

    using_fallback = latest_sigma is None

    most_recent = sorted(picks, key=lambda p: p.game_date or '', reverse=True)[:10]

    recent_picks = []
    for p in most_recent:
        line_move = None
        if p.line_open is not None and p.line is not None:
            line_move = round(p.line - p.line_open, 1)
        recent_picks.append({
            'id': p.id,
            'side': p.side,
            'line': p.line,
            'edge_pct': p.edge_pct,
            'result': p.result,
            'model_confidence': p.model_confidence,
            'predicted_margin': p.predicted_margin,
            'cover_prob': p.cover_prob,
            'closing_spread': p.closing_spread,
            'line_open': p.line_open,
            'line_close': p.line_close,
            'line_movement': line_move,
            'game_date': p.game_date,
            'start_time': p.start_time,
            'published_at': (p.published_at.isoformat() + 'Z') if p.published_at else None,
            'away_team': p.away_team,
            'home_team': p.home_team,
            'pnl': p.pnl,
        })

    return jsonify({
        'performance': {
            'total_pnl': round(total_pnl, 2),
            'roi': roi,
            'record': f'{wins}-{losses}',
            'wins': wins,
            'losses': losses,
            'win_rate': round(wins / (wins + losses) * 100, 1) if (wins + losses) > 0 else 0,
            'total_picks': total_picks,
            'total_passes': total_passes,
            'selectivity': selectivity,
            'equity_curve': equity_curve,
        },
        'risk': {
            'max_drawdown_pct': drawdown_pct,
            'max_drawdown_dollars': round(max_drawdown, 0),
            'avg_days_between_picks': avg_days_between,
            'avg_line_move_against': avg_line_move,
            'avg_edge_published': avg_edge,
        },
        'discipline': {
            'selectivity_rate': selectivity,
            'industry_avg': 78,
            'restraint_grade': restraint_grade,
            'capital_preserved': capital_preserved,
            'total_passes': total_passes,
        },
        'model_health': {
            'status': 'calibration_in_progress' if using_fallback else 'calibrated',
            'sigma': latest_sigma,
            'last_retrain': last_retrain_date,
            'model_version': last_run.model_version if last_run else 'v1.0',
        },
        'recent_picks': recent_picks,
    })


@public_bp.route('/model-info')
def model_info():
    total_picks = Pick.query.count()
    total_passes = Pass.query.count()
    last_run = ModelRun.query.order_by(ModelRun.created_at.desc()).first()

    model_accuracy = 79.4
    model_brier = 0.139
    num_features = 36
    training_size = 15131
    try:
        import pickle, os
        model_path = os.path.join(os.path.dirname(__file__), 'calibrated_model.pkl')
        with open(model_path, 'rb') as f:
            model_data = pickle.load(f)
        if 'ensemble_accuracy' in model_data:
            model_accuracy = round(model_data['ensemble_accuracy'] * 100, 1)
        if 'ensemble_brier' in model_data:
            model_brier = round(model_data['ensemble_brier'], 3)
        if 'feature_names' in model_data:
            num_features = len(model_data['feature_names'])
        if 'training_size' in model_data:
            training_size = model_data['training_size']
    except Exception:
        pass

    return jsonify({
        'accuracy': model_accuracy,
        'brier_score': model_brier,
        'num_features': num_features,
        'training_size': training_size,
        'total_picks': total_picks,
        'total_passes': total_passes,
        'last_retrain': last_run.date if last_run else None,
        'model_version': last_run.model_version if last_run else 'v1.0',
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
