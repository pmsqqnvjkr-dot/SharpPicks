"""
Model Run Service
Bridges the existing ML prediction pipeline with the new picks/passes tables.
model.py is the single source of truth for all decision logic.
This service only: runs the model, reads outputs, stores to DB.
"""

import time
from datetime import datetime, timedelta
from models import db, Pick, Pass, ModelRun
from sport_config import get_sport_config, get_live_sports


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
    """Get current Eastern Time date string."""
    try:
        from zoneinfo import ZoneInfo
        now_et = datetime.now(ZoneInfo('America/New_York'))
    except ImportError:
        now_et = datetime.utcnow() - timedelta(hours=5)
    return now_et.strftime('%Y-%m-%d')


def run_model_and_log(app, sport='nba'):
    """Run the model for today and log either a pick or pass."""
    cfg = get_sport_config(sport)

    is_live = cfg.get('live', False)
    is_active = cfg.get('active', True)

    if not is_active:
        return {'status': 'inactive', 'sport': sport, 'message': f'{cfg["name"]} is inactive.'}

    start_time = time.time()
    today_str = _get_et_date()

    with app.app_context():
        existing_pick = Pick.query.filter(
            Pick.game_date == today_str,
            Pick.sport == sport,
        ).first()
        existing_pass = Pass.query.filter_by(date=today_str, sport=sport).first()

        if existing_pick or existing_pass:
            return {'status': 'already_run', 'date': today_str, 'sport': sport}

        try:
            from model import EnsemblePredictor

            model = EnsemblePredictor(sport=sport)
            if not model.load_model():
                return {'status': 'error', 'error': 'Model not trained', 'date': today_str}

            predictions = model.predict_games(log_predictions=True)

            if not predictions:
                pass_entry = Pass(
                    date=today_str,
                    sport=sport,
                    games_analyzed=0,
                    closest_edge_pct=0,
                    pass_reason='No games available today',
                )
                db.session.add(pass_entry)

                model_run = ModelRun(
                    date=today_str,
                    sport=sport,
                    games_analyzed=0,
                    pick_generated=False,
                    pass_id=pass_entry.id,
                    run_duration_ms=int((time.time() - start_time) * 1000),
                )
                db.session.add(model_run)
                db.session.commit()

                try:
                    from notification_service import send_pass_notification
                    send_pass_notification(pass_entry)
                except Exception as notif_err:
                    import logging
                    logging.error(f"No-games pass notification failed: {notif_err}")

                return {'status': 'pass', 'reason': 'no_games', 'date': today_str, 'sport': sport}

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

                if is_live:
                    pick = Pick(
                        sport=sport,
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
                        sportsbook=best.get('best_book', 'DraftKings'),
                        notes=' | '.join(best.get('explanation', [])) if isinstance(best.get('explanation'), list) else (best.get('explanation') or ''),
                    )
                    db.session.add(pick)

                    model_run = ModelRun(
                        date=today_str,
                        sport=sport,
                        games_analyzed=len(predictions),
                        pick_generated=True,
                        pick_id=pick.id,
                        run_duration_ms=duration_ms,
                    )
                    db.session.add(model_run)
                    db.session.commit()

                    try:
                        from notification_service import send_pick_notification
                        send_pick_notification(pick)
                    except Exception as notif_err:
                        import logging
                        logging.error(f"Pick notification failed: {notif_err}")

                    return {
                        'status': 'pick',
                        'pick_id': pick.id,
                        'side': pick.side,
                        'edge': pick.edge_pct,
                        'date': today_str,
                        'sport': sport,
                    }
                else:
                    paper_trade_notes = f"Paper trade - not live | {best['away_team']} @ {best['home_team']} | {best.get('pick')} {pick_spread:+.1f} | Edge: {best.get('adjusted_edge', 0):+.1f}% | Confidence: {best.get('confidence', 0.5):.1%}"
                    if isinstance(best.get('explanation'), list):
                        paper_trade_notes += ' | ' + ' | '.join(best.get('explanation', []))
                    
                    pass_entry = Pass(
                        date=today_str,
                        sport=sport,
                        games_analyzed=len(predictions),
                        closest_edge_pct=round(best.get('adjusted_edge', 0), 1),
                        pass_reason='Paper trade - not live',
                        notes=paper_trade_notes,
                    )
                    db.session.add(pass_entry)

                    model_run = ModelRun(
                        date=today_str,
                        sport=sport,
                        games_analyzed=len(predictions),
                        pick_generated=False,
                        pass_id=pass_entry.id,
                        run_duration_ms=duration_ms,
                    )
                    db.session.add(model_run)
                    db.session.commit()

                    try:
                        from notification_service import send_pass_notification
                        send_pass_notification(pass_entry)
                    except Exception as notif_err:
                        import logging
                        logging.error(f"Paper trade pass notification failed: {notif_err}")

                    return {
                        'status': 'paper_trade',
                        'side': best.get('pick'),
                        'edge': round(best.get('adjusted_edge', 0), 1),
                        'away_team': best['away_team'],
                        'home_team': best['home_team'],
                        'line': _to_python(round(pick_spread, 1)),
                        'confidence': _to_python(round(best.get('confidence', 0.5), 4)),
                        'date': today_str,
                        'sport': sport,
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

                whatif_best = max(predictions, key=lambda p: p.get('adjusted_edge', 0)) if predictions else None
                whatif_kwargs = {}
                if whatif_best:
                    wh_spread = whatif_best.get('spread', 0) or 0
                    wh_is_home = whatif_best.get('pick_side') == 'home'
                    wh_line = wh_spread if wh_is_home else -wh_spread
                    whatif_kwargs = {
                        'whatif_side': whatif_best.get('pick'),
                        'whatif_home_team': whatif_best.get('home_team'),
                        'whatif_away_team': whatif_best.get('away_team'),
                        'whatif_pick_side': whatif_best.get('pick_side'),
                        'whatif_line': _to_python(round(wh_line, 1)),
                        'whatif_edge': _to_python(round(whatif_best.get('adjusted_edge', 0), 1)),
                        'whatif_cover_prob': _to_python(round(whatif_best.get('cover_prob', 0.5), 4)),
                        'whatif_pred_margin': _to_python(round(whatif_best['predicted_margin'], 1)) if whatif_best.get('predicted_margin') is not None else None,
                    }

                pass_entry = Pass(
                    date=today_str,
                    sport=sport,
                    games_analyzed=len(predictions),
                    closest_edge_pct=round(closest_edge, 1),
                    pass_reason=top_pass_reason,
                    **whatif_kwargs,
                )
                db.session.add(pass_entry)

                model_run = ModelRun(
                    date=today_str,
                    sport=sport,
                    games_analyzed=len(predictions),
                    pick_generated=False,
                    pass_id=pass_entry.id,
                    run_duration_ms=duration_ms,
                )
                db.session.add(model_run)
                db.session.commit()

                try:
                    from notification_service import send_pass_notification
                    send_pass_notification(pass_entry)
                except Exception as notif_err:
                    import logging
                    logging.error(f"Pass notification failed: {notif_err}")

                return {
                    'status': 'pass',
                    'closest_edge': round(closest_edge, 1),
                    'games_analyzed': len(predictions),
                    'pass_reason': top_pass_reason,
                    'date': today_str,
                    'sport': sport,
                }

        except Exception as e:
            return {'status': 'error', 'error': str(e), 'date': today_str}
