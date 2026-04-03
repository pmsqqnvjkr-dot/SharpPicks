from flask import Blueprint, jsonify, request
from models import db, Pick, Pass, ModelRun, FoundingCounter, EdgeSnapshot, KillSwitch, User
from sqlalchemy import func
from sqlalchemy.exc import ProgrammingError, OperationalError
from sport_config import get_active_sports, get_sport_config, get_phase_label
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import logging

public_bp = Blueprint('public', __name__)


def _get_sport_filter():
    sport = request.args.get('sport', 'all')
    if sport == 'all':
        return None
    if sport in get_active_sports():
        return sport
    return 'nba'



def _empty_record():
    return jsonify({
        'calibration_note': 'Model calibrated Feb 12, 2026.',
        'calibration_date': '2026-02-12', 'picks': [], 'passes': [],
        'stats': {'wins': 0, 'losses': 0, 'pending': 0, 'total_picks': 0, 'total_passes': 0, 'pnl': 0, 'win_rate': 0, 'selectivity': 0},
    })


def _record_pick_to_dict(p):
    """Serialize a pick for public record with model vs market fields."""
    market_line = round(p.line, 1) if p.line is not None else None
    model_projection = round(-float(p.predicted_margin), 1) if p.predicted_margin is not None else None
    CALIBRATION_DATE = datetime(2026, 2, 12)
    return {
        'id': p.id,
        'published_at': (p.published_at.isoformat() + 'Z') if p.published_at else None,
        'game_date': p.game_date,
        'side': p.side,
        'line': p.line,
        'edge_pct': p.edge_pct,
        'result': p.result,
        'pnl': p.pnl,
        'profit_units': p.profit_units if p.profit_units is not None else (round(p.pnl / 100, 2) if p.pnl else None),
        'away_team': p.away_team,
        'home_team': p.home_team,
        'clv': p.clv,
        'closing_spread': p.closing_spread,
        'home_score': p.home_score,
        'away_score': p.away_score,
        'pre_calibration': p.published_at < CALIBRATION_DATE if p.published_at else False,
        'market_line': market_line,
        'model_projection': model_projection,
        'market_odds': p.market_odds,
        'start_time': p.start_time,
        'sport': p.sport,
    }


@public_bp.route('/record')
def record():
    sport = _get_sport_filter()
    try:
        pick_q = Pick.query
        pass_q = Pass.query
        if sport:
            pick_q = pick_q.filter(Pick.sport == sport)
            pass_q = pass_q.filter(Pass.sport == sport)
        picks = pick_q.order_by(Pick.published_at.desc()).all()
        passes = pass_q.order_by(Pass.created_at.desc()).all()
    except (ProgrammingError, OperationalError) as e:
        logging.warning(f"Public record DB error: {e}")
        return _empty_record()

    # Exclude very old pending picks (game_date > 7 days ago) so they don't clutter the UI
    today_et = datetime.now(ZoneInfo('America/New_York')).date()
    cutoff_str = (today_et - timedelta(days=7)).strftime('%Y-%m-%d')
    picks = [p for p in picks if not (
        p.result == 'pending' and p.game_date and str(p.game_date)[:10] < cutoff_str
    )]

    wins = sum(1 for p in picks if p.result == 'win')
    losses = sum(1 for p in picks if p.result == 'loss')
    pending = sum(1 for p in picks if p.result == 'pending')
    total_pnl_units = sum(
        (p.profit_units if p.profit_units is not None else (p.pnl / 100 if p.pnl else 0))
        for p in picks if p.result in ('win', 'loss')
    )

    CALIBRATION_DATE = datetime(2026, 2, 12)

    cfg = get_sport_config(sport or 'nba')
    phase = cfg.get('model_phase', 'deployment')
    return jsonify({
        'calibration_note': 'Model calibrated Feb 12, 2026. Prior picks used raw predictions without market-aware shrinkage.',
        'calibration_date': '2026-02-12',
        'model_phase': phase,
        'phase_label': get_phase_label(phase),
        'picks': [_record_pick_to_dict(p) for p in picks],
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
            'pnl': round(total_pnl_units, 2),
            'win_rate': round(wins / (wins + losses) * 100, 1) if (wins + losses) > 0 else 0,
            'selectivity': round(len(picks) / (len(picks) + len(passes)) * 100, 1) if (len(picks) + len(passes)) > 0 else 0,
        }
    })


@public_bp.route('/stats')
def stats():
    sport = _get_sport_filter()
    try:
        pick_q = Pick.query
        pass_q = Pass.query
        if sport:
            pick_q = pick_q.filter(Pick.sport == sport)
            pass_q = pass_q.filter(Pass.sport == sport)
        wins = pick_q.filter(Pick.result == 'win').count()
        losses = pick_q.filter(Pick.result == 'loss').count()
        pending = pick_q.filter(Pick.result == 'pending').count()
        total_picks = pick_q.count()
        total_passes = pass_q.count()
        pnl_q = db.session.query(func.sum(Pick.pnl)).filter(Pick.result.in_(['win', 'loss']))
        if sport:
            pnl_q = pnl_q.filter(Pick.sport == sport)
        total_pnl_dollars = pnl_q.scalar() or 0

        unit_q = db.session.query(func.sum(Pick.profit_units)).filter(Pick.result.in_(['win', 'loss']))
        if sport:
            unit_q = unit_q.filter(Pick.sport == sport)
        total_pnl_units = unit_q.scalar()
        if total_pnl_units is None:
            total_pnl_units = total_pnl_dollars / 100 if total_pnl_dollars else 0

        total_decided = wins + losses
        roi = round((total_pnl_dollars / (total_decided * 110)) * 100, 1) if total_decided > 0 else 0
    except (ProgrammingError, OperationalError) as e:
        logging.warning(f"Public stats DB error: {e}")
        return jsonify({'record': '0-0', 'wins': 0, 'losses': 0, 'pending': 0, 'total_picks': 0, 'total_passes': 0, 'pnl': 0, 'roi': 0, 'win_rate': 0, 'selectivity': 0, 'capital_preserved_days': 0})

    clv_q = pick_q.filter(Pick.clv.isnot(None), Pick.result.in_(['win', 'loss', 'push']))
    clv_picks = clv_q.all()
    clv_values = [p.clv for p in clv_picks if p.clv is not None]
    clv_positive = sum(1 for v in clv_values if v > 0)
    avg_clv = round(sum(clv_values) / len(clv_values), 2) if clv_values else None
    clv_beat_rate = round(clv_positive / len(clv_values) * 100, 1) if clv_values else 0

    cfg = get_sport_config(sport or 'nba')
    phase = cfg.get('model_phase', 'deployment')

    founding_claimed = User.query.filter_by(founding_member=True).count()

    return jsonify({
        'record': f'{wins}-{losses}',
        'wins': wins,
        'losses': losses,
        'pending': pending,
        'total_picks': total_picks,
        'total_passes': total_passes,
        'pnl': round(total_pnl_units, 2),
        'units': round(total_pnl_units, 2),
        'roi': roi,
        'win_rate': round(wins / total_decided * 100, 1) if total_decided > 0 else 0,
        'selectivity': round(total_picks / (total_picks + total_passes) * 100, 1) if (total_picks + total_passes) > 0 else 0,
        'capital_preserved_days': total_passes,
        'avg_clv': avg_clv,
        'clv_beat_rate': clv_beat_rate,
        'model_phase': phase,
        'phase_label': get_phase_label(phase),
        'founding_spots_claimed': founding_claimed,
    })


@public_bp.route('/calibration')
def calibration():
    """Production calibration tracking.
    Buckets resolved picks by confidence tier and reports actual cover rates.
    Institutional honesty: does 60% confidence actually win ~60%?"""
    sport = _get_sport_filter()
    q = Pick.query.filter(Pick.result_ats.in_(['W', 'L']))
    if sport:
        q = q.filter(Pick.sport == sport)
    resolved = q.all()

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
    import math
    from datetime import timedelta
    from datetime import datetime as dt

    sport = _get_sport_filter()
    pick_q = Pick.query
    pass_q = Pass.query
    if sport:
        pick_q = pick_q.filter(Pick.sport == sport)
        pass_q = pass_q.filter(Pass.sport == sport)
    picks = pick_q.order_by(Pick.game_date.asc()).all()
    passes = pass_q.all()
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
    unit_results = []
    for p in resolved:
        pnl = p.pnl or 0
        running_pnl += pnl
        max_pnl = max(max_pnl, running_pnl)
        drawdown = max_pnl - running_pnl
        if drawdown > max_drawdown:
            max_drawdown = drawdown
        unit_return = pnl / 110.0 if pnl != 0 else (-1.0 if p.result == 'loss' else 0.0)
        unit_results.append(unit_return)
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

    import numpy as np
    rolling_50 = None
    rolling_100 = None
    if len(unit_results) >= 50:
        last_50 = unit_results[-50:]
        rolling_50 = round(sum(last_50) / (50 * 1.0) * 100, 2)
    if len(unit_results) >= 100:
        last_100 = unit_results[-100:]
        rolling_100 = round(sum(last_100) / (100 * 1.0) * 100, 2)

    return_std = round(float(np.std(unit_results)) * 100, 2) if len(unit_results) >= 10 else None

    bankroll_units = 100

    if len(unit_results) >= 20:
        win_rate_decimal = wins / (wins + losses) if (wins + losses) > 0 else 0.5
        avg_win = 100.0 / 110.0
        avg_loss = 1.0
        if win_rate_decimal > 0 and win_rate_decimal < 1:
            p = win_rate_decimal
            q = 1 - p
            edge = p * avg_win - q * avg_loss
            if edge > 0:
                try:
                    import math
                    r = (q * avg_loss) / (p * avg_win)
                    if r < 1:
                        ror = r ** bankroll_units
                        ror = min(ror, 1.0)
                        risk_of_ruin_pct = round(ror * 100, 4)
                    else:
                        risk_of_ruin_pct = 100.0
                except (OverflowError, ZeroDivisionError):
                    risk_of_ruin_pct = 0.0
            else:
                risk_of_ruin_pct = 100.0
        else:
            risk_of_ruin_pct = 0.0 if win_rate_decimal == 1 else 100.0
    else:
        risk_of_ruin_pct = None

    rolling_50_series = []
    if len(unit_results) >= 50:
        for i in range(50, len(unit_results) + 1):
            window = unit_results[i-50:i]
            rolling_50_series.append(round(sum(window) / 50 * 100, 2))

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
            mv = abs(p.line - p.line_open)
            if not (isinstance(mv, float) and (math.isnan(mv) or math.isinf(mv))):
                line_moves.append(mv)
    avg_line_move = round(sum(line_moves) / len(line_moves), 1) if line_moves else 0

    clv_values = [p.clv for p in picks if p.clv is not None]
    clv_positive = sum(1 for v in clv_values if v > 0)
    avg_clv = round(sum(clv_values) / len(clv_values), 2) if clv_values else None
    clv_beat_rate = round(clv_positive / len(clv_values) * 100, 1) if clv_values else 0

    selectivity = round((total_picks / total_days) * 100, 1) if total_days > 0 else 0

    capital_preserved = round(total_passes * 110 * 0.04, 0)

    if selectivity < 25:
        restraint_grade = 'A+'
    elif selectivity < 35:
        restraint_grade = 'A'
    elif selectivity < 50:
        restraint_grade = 'B'
    elif selectivity < 65:
        restraint_grade = 'C'
    else:
        restraint_grade = 'D'

    latest_sigma = None
    for p in reversed(picks):
        if p.sigma is not None:
            latest_sigma = round(p.sigma, 1)
            break

    last_run_q = ModelRun.query
    if sport:
        last_run_q = last_run_q.filter(ModelRun.sport == sport)
    last_run = last_run_q.order_by(ModelRun.created_at.desc()).first()
    last_retrain_date = last_run.date if last_run else None

    using_fallback = latest_sigma is None

    most_recent = sorted(picks, key=lambda p: p.game_date or '', reverse=True)[:10]

    def _sanitize(v):
        """Replace NaN/Inf with None so JSON serialization stays clean."""
        if v is None:
            return None
        if isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
            return None
        return v

    recent_picks = []
    for p in most_recent:
        line_move = None
        if p.line_open is not None and p.line is not None:
            raw = p.line - p.line_open
            line_move = _sanitize(round(raw, 1))
        recent_picks.append({
            'id': p.id,
            'side': p.side,
            'line': p.line,
            'edge_pct': p.edge_pct,
            'result': p.result,
            'model_confidence': p.model_confidence,
            'predicted_margin': p.predicted_margin,
            'cover_prob': p.cover_prob,
            'closing_spread': _sanitize(p.closing_spread),
            'line_open': _sanitize(p.line_open),
            'line_close': _sanitize(p.line_close),
            'line_movement': line_move,
            'game_date': p.game_date,
            'start_time': p.start_time,
            'published_at': (p.published_at.isoformat() + 'Z') if p.published_at else None,
            'away_team': p.away_team,
            'home_team': p.home_team,
            'pnl': p.pnl,
        })

    cfg = get_sport_config(sport or 'nba')
    phase = cfg.get('model_phase', 'deployment')
    return jsonify({
        'model_phase': phase,
        'phase_label': get_phase_label(phase),
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
        'clv': {
            'avg_clv': avg_clv,
            'beat_rate': clv_beat_rate,
            'total_tracked': len(clv_values),
            'positive': clv_positive,
        },
        'risk': {
            'max_drawdown_pct': drawdown_pct,
            'max_drawdown_dollars': round(max_drawdown, 0),
            'avg_days_between_picks': avg_days_between,
            'avg_line_move_against': avg_line_move,
            'avg_edge_published': avg_edge,
            'rolling_50_roi': rolling_50,
            'rolling_100_roi': rolling_100,
            'return_std_dev': return_std,
            'risk_of_ruin_pct': risk_of_ruin_pct,
            'rolling_50_series': rolling_50_series,
            'total_resolved': len(resolved),
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
    sport = _get_sport_filter()
    if sport:
        total_picks = Pick.query.filter(Pick.sport == sport).count()
        total_passes = Pass.query.filter(Pass.sport == sport).count()
        last_run = ModelRun.query.filter(ModelRun.sport == sport).order_by(ModelRun.created_at.desc()).first()
    else:
        total_picks = Pick.query.count()
        total_passes = Pass.query.count()
        last_run = ModelRun.query.order_by(ModelRun.created_at.desc()).first()

    model_accuracy = 57.3
    model_brier = 0.139
    num_features = 56
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
        'walk_forward_ats': 68.6,
        'walk_forward_roi': 30.9,
        'edge_threshold_base': 3.0,
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
        'total': 50,
        'open': not counter.closed,
        'remaining': max(0, 50 - counter.current_count),
    })


@public_bp.route('/edge-decay')
def edge_decay():
    sport = _get_sport_filter()
    query = db.session.query(EdgeSnapshot)
    if sport:
        query = query.filter(EdgeSnapshot.sport == sport)

    snapshots = query.order_by(EdgeSnapshot.game_date.desc(), EdgeSnapshot.created_at.desc()).all()

    pick_snapshots = {}
    for s in snapshots:
        key = s.pick_id or f"{s.game_date}_{s.home_team}_{s.away_team}"
        if key not in pick_snapshots:
            pick_snapshots[key] = {}
        pick_snapshots[key][s.snapshot_label] = {
            'edge_pct': s.edge_pct,
            'spread': s.spread,
            'confidence': s.confidence,
            'steam_fragility': s.steam_fragility,
            'line_move_against': s.line_move_against,
            'created_at': s.created_at.isoformat() if s.created_at else None,
        }

    decay_records = []
    for key, labels in pick_snapshots.items():
        if 'open' in labels and 'pre_tip' in labels:
            open_edge = labels['open']['edge_pct'] or 0
            pretip_edge = labels['pre_tip']['edge_pct'] or 0
            decay_pct = ((open_edge - pretip_edge) / open_edge * 100) if open_edge != 0 else 0
            decay_records.append({
                'pick_id': key if isinstance(key, str) and not key.startswith('20') else key,
                'open_edge': round(open_edge, 2),
                'pre_tip_edge': round(pretip_edge, 2),
                'decay_pct': round(decay_pct, 1),
                'open_spread': labels['open'].get('spread'),
                'pre_tip_spread': labels['pre_tip'].get('spread'),
                'open_sfs': labels['open'].get('steam_fragility', 0),
                'pre_tip_sfs': labels['pre_tip'].get('steam_fragility', 0),
            })

    avg_decay = round(sum(d['decay_pct'] for d in decay_records) / len(decay_records), 1) if decay_records else None
    picks_with_decay = len(decay_records)
    edge_collapsed = sum(1 for d in decay_records if d['decay_pct'] > 50) if decay_records else 0
    edge_persisted = sum(1 for d in decay_records if d['decay_pct'] < 20) if decay_records else 0

    signal_type = None
    if picks_with_decay >= 10:
        if avg_decay is not None and avg_decay > 40:
            signal_type = 'stale'
        elif avg_decay is not None and avg_decay < 15:
            signal_type = 'structural'
        else:
            signal_type = 'mixed'

    return jsonify({
        'avg_decay_pct': avg_decay,
        'picks_tracked': picks_with_decay,
        'edge_collapsed_count': edge_collapsed,
        'edge_persisted_count': edge_persisted,
        'signal_type': signal_type,
        'records': decay_records[-20:],
    })


@public_bp.route('/regime-stats')
def regime_stats():
    sport = _get_sport_filter()
    query = Pick.query.filter(Pick.result_ats.in_(['W', 'L', 'P', 'win', 'loss', 'push']))
    if sport:
        query = query.filter(Pick.sport == sport)

    picks = query.order_by(Pick.game_date.desc()).all()

    if not picks:
        return jsonify({'segments': {}, 'total_picks': 0})

    def segment_record(picks_list):
        wins = sum(1 for p in picks_list if p.result_ats in ('W', 'win'))
        losses = sum(1 for p in picks_list if p.result_ats in ('L', 'loss'))
        pushes = sum(1 for p in picks_list if p.result_ats in ('P', 'push'))
        total = wins + losses
        wr = round(wins / total * 100, 1) if total > 0 else None
        pnl = round(sum(p.profit_units or 0 for p in picks_list), 2)
        return {
            'wins': wins,
            'losses': losses,
            'pushes': pushes,
            'total': wins + losses + pushes,
            'win_rate': wr,
            'pnl_units': pnl,
        }

    fav_picks = [p for p in picks if p.line is not None and p.line < 0]
    dog_picks = [p for p in picks if p.line is not None and p.line > 0]

    spread_buckets = {
        '0-3': [p for p in picks if p.line is not None and abs(p.line) <= 3],
        '3.5-7': [p for p in picks if p.line is not None and 3 < abs(p.line) <= 7],
        '7.5-10': [p for p in picks if p.line is not None and 7 < abs(p.line) <= 10],
        '10+': [p for p in picks if p.line is not None and abs(p.line) > 10],
    }

    home_picks = [p for p in picks if p.side and 'home' in (p.side or '').lower()]
    away_picks = [p for p in picks if p.side and 'away' in (p.side or '').lower()]
    if not home_picks and not away_picks:
        home_picks = [p for p in picks if p.side and p.home_team and p.home_team.lower() in (p.side or '').lower()]
        away_picks = [p for p in picks if p.side and p.away_team and p.away_team.lower() in (p.side or '').lower()]

    segments = {}
    segments['favorite'] = segment_record(fav_picks) if fav_picks else None
    segments['underdog'] = segment_record(dog_picks) if dog_picks else None

    segments['spread_buckets'] = {}
    for bucket_name, bucket_picks in spread_buckets.items():
        if bucket_picks:
            segments['spread_buckets'][bucket_name] = segment_record(bucket_picks)

    if home_picks or away_picks:
        segments['home'] = segment_record(home_picks) if home_picks else None
        segments['away'] = segment_record(away_picks) if away_picks else None

    concentration_warning = None
    if len(picks) >= 10:
        bucket_records = segments.get('spread_buckets', {})
        total_pnl = sum(abs(b.get('pnl_units', 0)) for b in bucket_records.values())
        if total_pnl > 0:
            for bname, brec in bucket_records.items():
                if abs(brec.get('pnl_units', 0)) / total_pnl > 0.7:
                    concentration_warning = f"Profit concentrated in {bname} spread bucket ({abs(brec['pnl_units'])/total_pnl:.0%} of total P&L)"
                    break

        if not concentration_warning:
            fav_rec = segments.get('favorite')
            dog_rec = segments.get('underdog')
            if fav_rec and dog_rec:
                fav_pnl = abs(fav_rec.get('pnl_units', 0))
                dog_pnl = abs(dog_rec.get('pnl_units', 0))
                total_side = fav_pnl + dog_pnl
                if total_side > 0:
                    if fav_pnl / total_side > 0.8:
                        concentration_warning = f"Favorite-heavy: {fav_pnl/total_side:.0%} of P&L from favorites"
                    elif dog_pnl / total_side > 0.8:
                        concentration_warning = f"Underdog-heavy: {dog_pnl/total_side:.0%} of P&L from dogs"

    return jsonify({
        'segments': segments,
        'total_picks': len(picks),
        'concentration_warning': concentration_warning,
    })


KILL_SWITCH_ROI_THRESHOLD = -8.0
KILL_SWITCH_CLV_WINDOW = 50
KILL_SWITCH_ROLLING_WINDOW = 100
KILL_SWITCH_POSITION_REDUCTION = 50
KILL_SWITCH_RECOVERY_ROI = 0.0
KILL_SWITCH_RECOVERY_CLV_POSITIVE = 20


def evaluate_kill_switch(sport=None):
    from datetime import datetime as dt

    pick_q = Pick.query.filter(Pick.result.in_(['win', 'loss']))
    if sport:
        pick_q = pick_q.filter(Pick.sport == sport)
    resolved = pick_q.order_by(Pick.game_date.asc()).all()

    conditions = {
        'rolling_roi_triggered': False,
        'clv_negative_triggered': False,
        'edge_decay_stale': False,
    }
    diagnostics = {
        'rolling_100_roi': None,
        'clv_negative_count': 0,
        'clv_window': KILL_SWITCH_CLV_WINDOW,
        'edge_decay_signal': None,
        'total_resolved': len(resolved),
        'min_sample': KILL_SWITCH_ROLLING_WINDOW,
    }

    if len(resolved) >= KILL_SWITCH_ROLLING_WINDOW:
        last_n = resolved[-KILL_SWITCH_ROLLING_WINDOW:]
        total_pnl = sum(p.pnl or 0 for p in last_n)
        total_wagered = len(last_n) * 110
        rolling_roi = round((total_pnl / total_wagered) * 100, 2) if total_wagered > 0 else 0
        diagnostics['rolling_100_roi'] = rolling_roi
        if rolling_roi < KILL_SWITCH_ROI_THRESHOLD:
            conditions['rolling_roi_triggered'] = True

    clv_window = resolved[-KILL_SWITCH_CLV_WINDOW:] if len(resolved) >= KILL_SWITCH_CLV_WINDOW else resolved
    clv_negative_count = sum(1 for p in clv_window if p.clv is not None and p.clv < 0)
    clv_total_with_data = sum(1 for p in clv_window if p.clv is not None)
    diagnostics['clv_negative_count'] = clv_negative_count
    diagnostics['clv_total_with_data'] = clv_total_with_data
    if clv_total_with_data >= 30 and clv_negative_count > clv_total_with_data * 0.6:
        conditions['clv_negative_triggered'] = True

    snapshot_q = db.session.query(EdgeSnapshot)
    if sport:
        snapshot_q = snapshot_q.filter(EdgeSnapshot.sport == sport)
    snapshots = snapshot_q.order_by(EdgeSnapshot.game_date.desc(), EdgeSnapshot.created_at.desc()).all()

    pick_snapshots = {}
    for s in snapshots:
        key = s.pick_id or f"{s.game_date}_{s.home_team}_{s.away_team}"
        if key not in pick_snapshots:
            pick_snapshots[key] = {}
        pick_snapshots[key][s.snapshot_label] = s.edge_pct or 0

    decay_records = []
    for key, labels in pick_snapshots.items():
        if 'open' in labels and 'pre_tip' in labels:
            open_e = labels['open']
            pretip_e = labels['pre_tip']
            decay_pct = ((open_e - pretip_e) / open_e * 100) if open_e != 0 else 0
            decay_records.append(decay_pct)

    edge_decay_signal = None
    if len(decay_records) >= 10:
        avg_decay = sum(decay_records) / len(decay_records)
        if avg_decay > 40:
            edge_decay_signal = 'stale'
        elif avg_decay < 15:
            edge_decay_signal = 'structural'
        else:
            edge_decay_signal = 'mixed'
    diagnostics['edge_decay_signal'] = edge_decay_signal
    diagnostics['edge_decay_picks_tracked'] = len(decay_records)

    if edge_decay_signal == 'stale':
        conditions['edge_decay_stale'] = True

    all_triggered = all(conditions.values())
    any_triggered = any(conditions.values())
    triggers_met = sum(1 for v in conditions.values() if v)

    ks = KillSwitch.query.filter_by(sport=sport or 'nba').first()
    if not ks:
        ks = KillSwitch(sport=sport or 'nba', active=False, position_size_pct=100)
        db.session.add(ks)

    if all_triggered and not ks.active:
        ks.active = True
        ks.position_size_pct = KILL_SWITCH_POSITION_REDUCTION
        ks.triggered_at = dt.now()
        ks.cleared_at = None
        reasons = []
        if conditions['rolling_roi_triggered']:
            reasons.append(f"Rolling {KILL_SWITCH_ROLLING_WINDOW}-bet ROI at {diagnostics['rolling_100_roi']}% (threshold: {KILL_SWITCH_ROI_THRESHOLD}%)")
        if conditions['clv_negative_triggered']:
            reasons.append(f"CLV negative on {clv_negative_count}/{clv_total_with_data} of last {KILL_SWITCH_CLV_WINDOW} picks")
        if conditions['edge_decay_stale']:
            reasons.append(f"Edge decay signal: stale (avg decay >{40}%)")
        ks.trigger_reasons = reasons
        ks.rolling_roi = diagnostics['rolling_100_roi']
        ks.clv_negative_streak = clv_negative_count
        ks.edge_decay_signal = edge_decay_signal
        db.session.commit()

    elif ks.active:
        recovery_met = True
        if diagnostics['rolling_100_roi'] is not None and diagnostics['rolling_100_roi'] < KILL_SWITCH_RECOVERY_ROI:
            recovery_met = False
        recent_clv = resolved[-KILL_SWITCH_RECOVERY_CLV_POSITIVE:] if len(resolved) >= KILL_SWITCH_RECOVERY_CLV_POSITIVE else resolved
        recent_clv_positive = sum(1 for p in recent_clv if p.clv is not None and p.clv > 0)
        recent_clv_total = sum(1 for p in recent_clv if p.clv is not None)
        if recent_clv_total < 10 or recent_clv_positive < recent_clv_total * 0.5:
            recovery_met = False

        if recovery_met:
            ks.active = False
            ks.position_size_pct = 100
            ks.cleared_at = dt.now()
            ks.trigger_reasons = None
            db.session.commit()
        else:
            ks.rolling_roi = diagnostics['rolling_100_roi']
            ks.clv_negative_streak = clv_negative_count
            ks.edge_decay_signal = edge_decay_signal
            db.session.commit()
    else:
        db.session.commit()

    return {
        'active': ks.active,
        'position_size_pct': ks.position_size_pct,
        'triggered_at': ks.triggered_at.isoformat() if ks.triggered_at else None,
        'cleared_at': ks.cleared_at.isoformat() if ks.cleared_at else None,
        'trigger_reasons': ks.trigger_reasons or [],
        'conditions': conditions,
        'diagnostics': diagnostics,
        'triggers_met': triggers_met,
        'triggers_required': 3,
    }


@public_bp.route('/kill-switch')
def kill_switch_status():
    sport = _get_sport_filter()
    result = evaluate_kill_switch(sport)
    return jsonify(result)


def build_market_report_dict(date_param, sport=None):
    """Build the daily market report dict for a given date and optional sport. Used by /market-report and cron."""
    import json
    query = ModelRun.query.filter_by(date=date_param)
    if sport:
        query = query.filter_by(sport=sport)
    run = query.order_by(ModelRun.created_at.desc()).first()

    if not run:
        return {'available': False, 'date': date_param}

    games_analyzed = run.games_analyzed or 0
    edges_detected = 0
    qualified_signals = 0
    detail = []

    if run.games_detail:
        try:
            detail = json.loads(run.games_detail)
        except Exception:
            detail = []

    edge_threshold = 2.0
    all_edges = []
    largest_edge_val = 0
    largest_edge_game = None
    largest_edge_team = None
    strong_edges = 0
    moderate_edges = 0
    weak_edges = 0
    underdog_edges = 0
    favorite_edges = 0
    totals_efficient = True
    edge_spread_mags = []

    for g in detail:
        edge = abs(g.get('edge', 0) or 0)
        if edge >= edge_threshold:
            edges_detected += 1
            all_edges.append(edge)
            if edge >= 10:
                strong_edges += 1
            elif edge >= 7:
                moderate_edges += 1
            else:
                weak_edges += 1
            spread = g.get('spread') or g.get('line') or 0
            edge_spread_mags.append(abs(spread))
            if spread > 0:
                underdog_edges += 1
            else:
                favorite_edges += 1
            if edge > largest_edge_val:
                largest_edge_val = edge
                away = g.get('away_team', '')
                home = g.get('home_team', '')
                largest_edge_game = f'{away} @ {home}' if away and home else None
                pick_side = g.get('pick_side', '')
                if pick_side == 'home':
                    largest_edge_team = home or largest_edge_game
                elif pick_side == 'away':
                    largest_edge_team = away or largest_edge_game
                else:
                    largest_edge_team = g.get('pick', largest_edge_game)
        if g.get('passes'):
            qualified_signals += 1

    spread_mag_avg = round(sum(edge_spread_mags) / len(edge_spread_mags), 1) if edge_spread_mags else 0.0

    no_edge_count = games_analyzed - edges_detected
    efficiency = round(no_edge_count / games_analyzed * 100, 0) if games_analyzed > 0 else 100

    # Signal density (0-100)
    signal_density = round(qualified_signals / games_analyzed * 100, 0) if games_analyzed > 0 else 0

    # Market Efficiency Index (MEI): 0-100, higher = more inefficient (more opportunity)
    edge_count_score = min(edges_detected * 12, 100)
    avg_edge = sum(all_edges) / len(all_edges) if all_edges else 0
    avg_edge_score = min(avg_edge * 10, 100)
    signal_density_score = min(signal_density, 100)  # already 0-100
    top_edge_score = min(largest_edge_val * 10, 100) if largest_edge_val else 0
    mei_raw = (
        edge_count_score * 0.35
        + avg_edge_score * 0.35
        + signal_density_score * 0.20
        + top_edge_score * 0.10
    )
    market_efficiency_index = max(0, min(round(mei_raw, 0), 100))

    # Market regime from MEI (0-30 QUIET, 30-50 NORMAL, 50-70 ACTIVE, 70-85 HIGH OPPORTUNITY, 85+ RARE INEFFICIENCY)
    if market_efficiency_index >= 85:
        regime = 'RARE INEFFICIENCY'
        regime_micro = 'Unusual market opportunity detected'
    elif market_efficiency_index >= 70:
        regime = 'HIGH OPPORTUNITY'
        regime_micro = 'Strong opportunity detected'
    elif market_efficiency_index >= 50:
        regime = 'ACTIVE'
        regime_micro = 'Moderate opportunity detected'
    elif market_efficiency_index >= 30:
        regime = 'NORMAL'
        regime_micro = 'Typical market conditions'
    else:
        regime = 'QUIET'
        regime_micro = 'Markets priced efficiently. Passing is a position.'

    assessment = regime_micro

    # Dynamic briefing via template system
    try:
        from market_note_templates import generate_market_note
        _temp_report = {
            'edges_detected': edges_detected,
            'qualified_signals': qualified_signals,
            'signal_density': signal_density,
            'games_analyzed': games_analyzed,
            'top_edge_pct': round(largest_edge_val, 1) if largest_edge_val > 0 else 0,
            'top_edge_team': largest_edge_team,
            'largest_edge_game': largest_edge_game,
            'market_efficiency_index': int(market_efficiency_index),
            'regime': regime,
            'regime_micro': regime_micro,
            'spread_mag_avg': spread_mag_avg,
            'market_lean': {
                'favorites': favorite_edges,
                'underdogs': underdog_edges,
            },
        }
        _title, _body, _wim, _story = generate_market_note(_temp_report)
        briefing_lines = [_body]
        insight = _title
    except Exception:
        briefing_lines = []
        if edges_detected == 0:
            briefing_lines.append('No exploitable inefficiencies detected. Markets are pricing correctly today.')
        elif qualified_signals > 0:
            briefing_lines.append(f'{qualified_signals} signal{"s" if qualified_signals != 1 else ""} generated across {games_analyzed} markets.')
        else:
            briefing_lines.append('Mixed edge profile across today\'s slate.')
        insight = briefing_lines[0]

    updated_at = run.created_at.isoformat() + 'Z' if run.created_at else None

    # Aggregate line stability from snapshots
    market_stability = None
    try:
        import sqlite3
        db_path = current_app.config.get('SQLALCHEMY_DATABASE_URI', '').replace('sqlite:///', '')
        if db_path:
            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()
            cur.execute(
                "SELECT away_team, home_team, spread_home FROM line_snapshots WHERE game_date = ? ORDER BY snapped_at",
                (date_param,)
            )
            game_snaps = {}
            for row in cur.fetchall():
                k = (row['away_team'], row['home_team'])
                game_snaps.setdefault(k, []).append(row['spread_home'])
            conn.close()

            if game_snaps:
                stabilities = []
                for spreads in game_snaps.values():
                    if len(spreads) < 2:
                        continue
                    changes = sum(1 for i in range(1, len(spreads)) if spreads[i] != spreads[i - 1])
                    max_swing = max(spreads) - min(spreads) if spreads else 0
                    stabilities.append(max_swing + changes * 0.5)
                if stabilities:
                    avg_vol = sum(stabilities) / len(stabilities)
                    low_count = sum(1 for v in stabilities if v >= 4.0)
                    high_count = sum(1 for v in stabilities if v < 2.0)
                    if avg_vol >= 4.0:
                        ms_level, ms_label = 'low', 'Low'
                    elif avg_vol >= 2.0:
                        ms_level, ms_label = 'medium', 'Medium'
                    else:
                        ms_level, ms_label = 'high', 'High'
                    market_stability = {
                        'level': ms_level,
                        'label': ms_label,
                        'avg_volatility': round(avg_vol, 1),
                        'low_stability_games': low_count,
                        'high_stability_games': high_count,
                    }
    except Exception:
        pass

    if market_stability:
        if market_stability['level'] == 'low' and edges_detected > 0:
            briefing_lines.append('Line instability detected. Markets still adjusting. Potential for further movement.')
        elif market_stability['level'] == 'high' and edges_detected > 0:
            briefing_lines.append('Lines are stable across the board. Remaining edges may hold through tip-off.')

    # Market Board: all analyzed games with market line, model line, edge, signal (for Market page)
    board = []
    for g in detail:
        away = g.get('away_team') or g.get('away', '?')
        home = g.get('home_team') or g.get('home', '?')
        market_line = round(g.get('line', 0), 1) if g.get('line') is not None else None
        pm = g.get('predicted_margin')
        if pm is not None:
            model_line = round(-float(pm), 1) if g.get('pick_side') == 'home' else round(float(pm), 1)
        else:
            model_line = None
        edge_val = g.get('edge', 0) or 0
        pick_label = g.get('pick') or (f"{home} {market_line}" if market_line is not None else f'{away} vs {home}')
        board.append({
            'game': f'{away} vs {home}',
            'away_team': away,
            'home_team': home,
            'pick_label': pick_label,
            'market_line': market_line,
            'model_line': model_line,
            'edge': round(edge_val, 1) if edge_val is not None else None,
            'signal': bool(g.get('passes', False)),
            'pick_side': g.get('pick_side'),
            'pick': g.get('pick', ''),
            'reasoning': g.get('signals', []),
            'predicted_margin': g.get('predicted_margin'),
            'fail_reasons': g.get('fail_reasons', []),
        })

    # Persist MEI to daily_market_reports for sparkline history
    try:
        import sqlite3 as _sq_persist
        from db_path import get_sqlite_path as _get_sq_persist
        _conn_p = _sq_persist.connect(_get_sq_persist())
        _cur_p = _conn_p.cursor()
        _s_p = sport or 'nba'
        _cur_p.execute(
            """INSERT INTO daily_market_reports (date, sport, mei_value, regime, games_analyzed, edges_detected, qualified_signals, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(date, sport) DO UPDATE SET
                 mei_value = excluded.mei_value, regime = excluded.regime,
                 games_analyzed = excluded.games_analyzed, edges_detected = excluded.edges_detected,
                 qualified_signals = excluded.qualified_signals""",
            (date_param, _s_p, market_efficiency_index, regime, games_analyzed, edges_detected, qualified_signals,
             datetime.now(ZoneInfo('America/New_York')).isoformat())
        )
        _conn_p.commit()
        _conn_p.close()
    except Exception:
        pass

    # MEI sparkline: last 7 days of MEI values
    mei_sparkline = []
    mei_7d_avg = None
    mei_season_avg = None
    try:
        import sqlite3 as _sq
        from db_path import get_sqlite_path as _get_sq
        _conn = _sq.connect(_get_sq())
        _conn.row_factory = _sq.Row
        _cur = _conn.cursor()

        _s = sport or 'nba'
        _cur.execute("SELECT date, mei_value FROM daily_market_reports WHERE sport = ? ORDER BY date DESC LIMIT 7", (_s,))
        mei_rows = _cur.fetchall()
        mei_sparkline = [r['mei_value'] for r in reversed(mei_rows) if r['mei_value'] is not None]
        if mei_sparkline:
            mei_7d_avg = round(sum(mei_sparkline) / len(mei_sparkline), 0)
        _cur.execute("SELECT AVG(mei_value) as avg_mei FROM daily_market_reports WHERE sport = ?", (_s,))
        avg_row = _cur.fetchone()
        if avg_row and avg_row['avg_mei'] is not None:
            mei_season_avg = round(avg_row['avg_mei'], 0)
        _conn.close()
    except Exception:
        pass

    # Line movement and model-market delta
    use_moneyline = sport == 'mlb'
    line_movement_data = {
        'toward_model': 0, 'away_from_model': 0, 'no_movement': 0, 'games': [],
        'movement_type': 'moneyline' if use_moneyline else 'spread',
    }
    model_market_delta_data = {'avg_delta': 0, 'games': []}
    try:
        import sqlite3 as _sq2
        from db_path import get_sqlite_path as _get_sq2
        _conn2 = _sq2.connect(_get_sq2())
        _conn2.row_factory = _sq2.Row
        _cur2 = _conn2.cursor()
        _tbl = 'mlb_games' if sport == 'mlb' else ('wnba_games' if sport == 'wnba' else 'games')
        _ml_cols = ', home_ml, away_ml, home_ml_open, away_ml_open' if use_moneyline else ''
        _cur2.execute(
            f"SELECT home_team, away_team, spread_home, spread_home_open{_ml_cols} FROM {_tbl} WHERE game_date = ?",
            (date_param,)
        )
        game_rows = _cur2.fetchall()
        _conn2.close()

        deltas = []
        for gr in game_rows:
            away = gr['away_team']
            home = gr['home_team']
            spread_now = gr['spread_home']
            spread_open = gr['spread_home_open']
            matchup = f"{away} @ {home}"

            ga = None
            for g in detail:
                if g.get('away_team') == away or g.get('away') == away:
                    ga = g
                    break

            if use_moneyline:
                home_ml = gr['home_ml']
                home_ml_open = gr['home_ml_open']
                if home_ml is not None and home_ml_open is not None:
                    ml_shift = int(home_ml) - int(home_ml_open)
                    mvmt_cents = abs(ml_shift)
                    if ga and ga.get('pick_side'):
                        model_favors_home = ga['pick_side'] == 'home'
                        if model_favors_home:
                            moved_toward = ml_shift < 0
                        else:
                            moved_toward = ml_shift > 0
                        if ml_shift == 0:
                            direction = 'flat'
                            line_movement_data['no_movement'] += 1
                        elif moved_toward:
                            direction = 'toward'
                            line_movement_data['toward_model'] += 1
                        else:
                            direction = 'away'
                            line_movement_data['away_from_model'] += 1
                    else:
                        direction = 'flat'
                        line_movement_data['no_movement'] += 1
                    line_movement_data['games'].append({
                        'matchup': matchup, 'movement': mvmt_cents, 'direction': direction,
                        'ml_open': int(home_ml_open), 'ml_now': int(home_ml),
                    })
            else:
                if spread_open is not None and spread_now is not None:
                    mvmt = round(spread_now - spread_open, 1)
                    if ga and ga.get('pick_side'):
                        model_favors_home = ga['pick_side'] == 'home'
                        if model_favors_home:
                            moved_toward = mvmt < 0
                        else:
                            moved_toward = mvmt > 0
                        if mvmt == 0:
                            direction = 'flat'
                            line_movement_data['no_movement'] += 1
                        elif moved_toward:
                            direction = 'toward'
                            line_movement_data['toward_model'] += 1
                        else:
                            direction = 'away'
                            line_movement_data['away_from_model'] += 1
                    else:
                        direction = 'flat'
                        line_movement_data['no_movement'] += 1

                    line_movement_data['games'].append({
                        'matchup': matchup, 'movement': abs(mvmt), 'direction': direction,
                    })

            if ga:
                pm = ga.get('predicted_margin')
                line_val = ga.get('line') or spread_now
                if pm is not None and line_val is not None:
                    model_spread = -float(pm) if ga.get('pick_side') == 'home' else float(pm)
                    delta = round(abs(model_spread - (line_val or 0)), 1)
                    pick_label = ga.get('pick') or matchup
                    deltas.append(delta)
                    model_market_delta_data['games'].append({
                        'side': pick_label, 'delta': delta,
                    })

        model_market_delta_data['games'].sort(key=lambda x: x['delta'], reverse=True)
        if deltas:
            model_market_delta_data['avg_delta'] = round(sum(deltas) / len(deltas), 1)
    except Exception:
        pass

    return {
        'available': True,
        'date': date_param,
        'games_analyzed': games_analyzed,
        'edges_detected': edges_detected,
        'qualified_signals': qualified_signals,
        'market_efficiency_pct': efficiency,
        'market_efficiency_index': int(market_efficiency_index),
        'regime': regime,
        'regime_micro': regime_micro,
        'assessment': assessment,
        'signal_density': signal_density,
        'largest_edge': round(largest_edge_val, 1) if largest_edge_val > 0 else None,
        'largest_edge_game': largest_edge_game,
        'top_edge_team': largest_edge_team,
        'top_edge_pct': round(largest_edge_val, 1) if largest_edge_val > 0 else 0,
        'spread_mag_avg': spread_mag_avg,
        'market_stability': market_stability,
        'edge_distribution': {
            'strong': strong_edges,
            'moderate': moderate_edges,
            'weak': weak_edges,
        },
        'market_lean': {
            'favorites': favorite_edges,
            'underdogs': underdog_edges,
            'total_edges': edges_detected,
            'favorite_pct': round(favorite_edges / edges_detected * 100) if edges_detected > 0 else 0,
            'underdog_pct': round(underdog_edges / edges_detected * 100) if edges_detected > 0 else 0,
        },
        'mei': {
            'current': int(market_efficiency_index),
            'seven_day_avg': int(mei_7d_avg) if mei_7d_avg is not None else None,
            'season_avg': int(mei_season_avg) if mei_season_avg is not None else None,
            'sparkline': mei_sparkline,
        },
        'line_movement': line_movement_data,
        'model_market_delta': model_market_delta_data,
        'insight': insight,
        'briefing': briefing_lines,
        'last_updated': updated_at,
        'board': board,
    }


@public_bp.route('/market-report')
def market_report():
    sport = _get_sport_filter()
    et = ZoneInfo('America/New_York')
    today = datetime.now(et).strftime('%Y-%m-%d')
    date_param = request.args.get('date', today)
    return jsonify(build_market_report_dict(date_param, sport))


@public_bp.route('/discipline')
def discipline_score():
    sport = _get_sport_filter()

    pick_q = Pick.query
    pass_q = Pass.query
    if sport:
        pick_q = pick_q.filter_by(sport=sport)
        pass_q = pass_q.filter_by(sport=sport)

    total_picks = pick_q.filter(Pick.result != 'revoked').count()
    total_passes = pass_q.count()
    total_games = total_picks + total_passes

    if total_games == 0:
        selectivity = 0
    else:
        selectivity = round(total_picks / total_games * 100, 1)

    if selectivity < 25:
        grade = 'A+'
    elif selectivity < 35:
        grade = 'A'
    elif selectivity < 50:
        grade = 'B'
    elif selectivity < 65:
        grade = 'C'
    else:
        grade = 'D'

    avg_bet = 25
    capital_preserved = round(total_passes * avg_bet * 0.045, 2)

    return jsonify({
        'grade': grade,
        'selectivity': selectivity,
        'industry_avg': 78,
        'capital_preserved': capital_preserved,
        'games_passed': total_passes,
        'games_bet': total_picks,
        'total_games': total_games,
    })
