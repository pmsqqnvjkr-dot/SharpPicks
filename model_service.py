"""
Model Run Service
Bridges the existing ML prediction pipeline with the new picks/passes tables.
model.py is the single source of truth for all decision logic.
This service only: runs the model, reads outputs, stores to DB.
"""

import time
from datetime import datetime, timedelta
from models import db, Pick, Pass, ModelRun


def _to_python(val):
    if val is None:
        return None
    try:
        import numpy as np
        if isinstance(val, (np.floating, np.float64, np.float32)):
            return float(val)
        if isinstance(val, (np.integer, np.int64, np.int32)):
            return int(val)
    except ImportError:
        pass
    return val


def _get_et_date():
    """Get current Eastern Time date string (NBA schedule runs on ET)."""
    try:
        from zoneinfo import ZoneInfo
        now_et = datetime.now(ZoneInfo('America/New_York'))
    except ImportError:
        now_et = datetime.utcnow() - timedelta(hours=5)
    return now_et.strftime('%Y-%m-%d')


def run_model_and_log(app):
    """Run the model for today and log either a pick or pass."""
    start_time = time.time()
    today_str = _get_et_date()

    with app.app_context():
        existing_pick = Pick.query.filter(
            Pick.game_date == today_str
        ).first()
        existing_pass = Pass.query.filter_by(date=today_str).first()

        if existing_pick or existing_pass:
            return {'status': 'already_run', 'date': today_str}

        try:
            from model import EnsemblePredictor

            model = EnsemblePredictor()
            if not model.load_model():
                return {'status': 'error', 'error': 'Model not trained', 'date': today_str}

            predictions = model.predict_games(log_predictions=True)

            if not predictions:
                pass_entry = Pass(
                    date=today_str,
                    sport='nba',
                    games_analyzed=0,
                    closest_edge_pct=0,
                    pass_reason='No games available today',
                )
                db.session.add(pass_entry)

                model_run = ModelRun(
                    date=today_str,
                    sport='nba',
                    games_analyzed=0,
                    pick_generated=False,
                    pass_id=pass_entry.id,
                    run_duration_ms=int((time.time() - start_time) * 1000),
                )
                db.session.add(model_run)
                db.session.commit()

                return {'status': 'pass', 'reason': 'no_games', 'date': today_str}

            qualified = [p for p in predictions if p.get('passes_filter')]
            all_edges = [p.get('adjusted_edge', 0) for p in predictions]
            closest_edge = max(all_edges) if all_edges else 0

            duration_ms = int((time.time() - start_time) * 1000)

            if qualified:
                best = max(qualified, key=lambda p: p.get('adjusted_edge', 0))

                home_cover_prob = best.get('cover_prob', 0.5)
                is_home_pick = best.get('pick_side') == 'home'
                spread = best.get('spread', 0) or 0
                pick_spread = spread if is_home_pick else -spread

                pick = Pick(
                    sport='nba',
                    away_team=best['away_team'],
                    home_team=best['home_team'],
                    game_date=today_str,
                    side=best.get('pick'),
                    line=_to_python(round(pick_spread, 1)),
                    line_open=_to_python(best.get('spread_home_open')) if 'spread_home_open' in best else None,
                    start_time=best.get('game_time') or best.get('game_date'),
                    edge_pct=_to_python(round(best.get('adjusted_edge', 0), 1)),
                    model_confidence=_to_python(round(best.get('confidence', 0.5), 4)),
                    predicted_margin=_to_python(round(best['predicted_margin'], 1)) if best.get('predicted_margin') is not None else None,
                    sigma=_to_python(round(best['sigma'], 2)) if best.get('sigma') is not None else None,
                    z_score=_to_python(round(best['z_score'], 3)) if best.get('z_score') is not None else None,
                    raw_edge=_to_python(round(best['raw_edge'], 2)) if best.get('raw_edge') is not None else None,
                    cover_prob=_to_python(round(home_cover_prob, 4)),
                    implied_prob=_to_python(round(best.get('implied_prob', 0.5238), 4)),
                    market_odds=_to_python(best.get('market_odds', -110)),
                    sportsbook='DraftKings',
                    notes=' | '.join(best.get('explanation', [])) if isinstance(best.get('explanation'), list) else (best.get('explanation') or ''),
                )
                db.session.add(pick)

                model_run = ModelRun(
                    date=today_str,
                    sport='nba',
                    games_analyzed=len(predictions),
                    pick_generated=True,
                    pick_id=pick.id,
                    run_duration_ms=duration_ms,
                )
                db.session.add(model_run)
                db.session.commit()

                return {
                    'status': 'pick',
                    'pick_id': pick.id,
                    'side': pick.side,
                    'edge': pick.edge_pct,
                    'date': today_str,
                }
            else:
                top_pass_reason = None
                for p in sorted(predictions, key=lambda x: x.get('adjusted_edge', 0), reverse=True):
                    if p.get('pass_reason'):
                        top_pass_reason = p['pass_reason']
                        break

                if not top_pass_reason:
                    if closest_edge > 0:
                        top_pass_reason = f"Edge below threshold ({closest_edge:+.1f}%)"
                    else:
                        top_pass_reason = "No statistical edge detected"

                pass_entry = Pass(
                    date=today_str,
                    sport='nba',
                    games_analyzed=len(predictions),
                    closest_edge_pct=round(closest_edge, 1),
                    pass_reason=top_pass_reason,
                )
                db.session.add(pass_entry)

                model_run = ModelRun(
                    date=today_str,
                    sport='nba',
                    games_analyzed=len(predictions),
                    pick_generated=False,
                    pass_id=pass_entry.id,
                    run_duration_ms=duration_ms,
                )
                db.session.add(model_run)
                db.session.commit()

                return {
                    'status': 'pass',
                    'closest_edge': round(closest_edge, 1),
                    'games_analyzed': len(predictions),
                    'pass_reason': top_pass_reason,
                    'date': today_str,
                }

        except Exception as e:
            return {'status': 'error', 'error': str(e), 'date': today_str}
