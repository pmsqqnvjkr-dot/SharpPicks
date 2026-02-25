"""
Model Run Service
Bridges the existing ML prediction pipeline with the new picks/passes tables.
model.py is the single source of truth for all decision logic.
This service only: runs the model, reads outputs, stores to DB.
"""

import json
import time
import sqlite3
from datetime import datetime, timedelta
from models import db, Pick, Pass, ModelRun, EdgeSnapshot, KillSwitch
from sport_config import get_sport_config, get_live_sports


def _build_games_detail(predictions):
    if not predictions:
        return None
    details = []
    for p in sorted(predictions, key=lambda x: x.get('adjusted_edge', 0), reverse=True):
        spread = p.get('spread', 0) or 0
        is_home = p.get('pick_side') == 'home'
        pick_line = spread if is_home else -spread
        details.append({
            'away': p.get('away_team', '?'),
            'home': p.get('home_team', '?'),
            'pick': p.get('pick', ''),
            'line': round(pick_line, 1),
            'edge': round(p.get('adjusted_edge', 0), 1),
            'cover_prob': round(p.get('cover_prob', 0.5), 3),
            'passes': bool(p.get('passes_filter')),
            'reason': p.get('pass_reason', ''),
        })
    return json.dumps(details)


def _diagnose_no_games(today_str, sport='nba'):
    """Diagnose WHY the model found no games.

    Returns a dict with:
        situation: 'off_day' | 'no_spreads' | 'data_failure'
        total_games: int — rows in SQLite for today
        games_with_spreads: int — rows with spread_home set
        message: str — human-readable explanation
    """
    games_table = 'wnba_games' if sport == 'wnba' else 'games'
    try:
        conn = sqlite3.connect('sharp_picks.db')
        cur = conn.cursor()

        has_table = cur.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
            (games_table,)
        ).fetchone()
        if not has_table:
            conn.close()
            return {
                'situation': 'data_failure',
                'total_games': 0,
                'games_with_spreads': 0,
                'message': f'SQLite table {games_table} does not exist',
            }

        total = cur.execute(
            f"SELECT COUNT(*) FROM {games_table} WHERE game_date = ?",
            (today_str,)
        ).fetchone()[0]

        with_spreads = cur.execute(
            f"SELECT COUNT(*) FROM {games_table} WHERE game_date = ? AND spread_home IS NOT NULL",
            (today_str,)
        ).fetchone()[0]

        unscored = cur.execute(
            f"SELECT COUNT(*) FROM {games_table} WHERE game_date = ? AND home_score IS NULL",
            (today_str,)
        ).fetchone()[0]

        conn.close()

        if total == 0:
            return {
                'situation': 'data_failure',
                'total_games': 0,
                'games_with_spreads': 0,
                'message': 'No games in database — data collection may have failed',
            }

        if with_spreads == 0:
            return {
                'situation': 'no_spreads',
                'total_games': total,
                'games_with_spreads': 0,
                'message': f'{total} games found but none have spreads — lines may not be posted yet',
            }

        if unscored == 0:
            return {
                'situation': 'stale_data',
                'total_games': total,
                'games_with_spreads': with_spreads,
                'message': f'All {total} games already scored — data stale or not refreshed',
            }

        return {
            'situation': 'no_eligible',
            'total_games': total,
            'games_with_spreads': with_spreads,
            'message': f'{total} games, {with_spreads} with spreads — model found none eligible (time filter or other)',
        }

    except Exception as e:
        return {
            'situation': 'data_failure',
            'total_games': 0,
            'games_with_spreads': 0,
            'message': f'SQLite diagnostic error: {e}',
        }


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


def log_edge_snapshots(predictions, snapshot_label, hours_to_tip=None, pick_id=None, sport='nba'):
    today_str = _get_et_date()
    for p in predictions:
        if not p.get('passes_filter', False) and not pick_id:
            continue
        if pick_id and p.get('home_team') != None:
            pass

        snap = EdgeSnapshot(
            pick_id=pick_id,
            game_date=today_str,
            sport=sport,
            home_team=p.get('home_team', ''),
            away_team=p.get('away_team', ''),
            side=p.get('pick', '').split()[0] if p.get('pick') else p.get('pick_side', ''),
            snapshot_label=snapshot_label,
            hours_to_tip=_to_python(hours_to_tip),
            edge_pct=_to_python(p.get('adjusted_edge', p.get('edge', 0))),
            spread=_to_python(p.get('spread')),
            confidence=_to_python(p.get('cover_prob')),
            steam_fragility=_to_python(p.get('steam_fragility', 0)),
            line_move_against=_to_python(p.get('line_move_against', 0)),
        )
        db.session.add(snap)
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        import logging
        logging.error(f"Edge snapshot logging failed: {e}")


def _get_et_date():
    """Get current 'betting day' date string in Eastern Time.
    
    The betting day runs until 2:30 AM ET the following morning.
    Before 2:30 AM, we still use the previous day's date.
    After 2:30 AM, the slate resets to the new calendar day.
    """
    try:
        from zoneinfo import ZoneInfo
        now_et = datetime.now(ZoneInfo('America/New_York'))
    except ImportError:
        now_et = datetime.utcnow() - timedelta(hours=5)
    if now_et.hour < 2 or (now_et.hour == 2 and now_et.minute < 30):
        now_et = now_et - timedelta(days=1)
    return now_et.strftime('%Y-%m-%d')


def _get_et_now():
    """Get current Eastern Time datetime."""
    try:
        from zoneinfo import ZoneInfo
        return datetime.now(ZoneInfo('America/New_York'))
    except ImportError:
        return datetime.utcnow() - timedelta(hours=5)


def pretip_revalidate(app, sport='nba'):
    """
    Pre-tip re-validation: runs 2-3 hours before first tip-off.
    Re-fetches odds/injuries, re-runs model on today's pick,
    and revokes if the edge has evaporated or injury status changed.
    """
    today_str = _get_et_date()

    with app.app_context():
        pick = Pick.query.filter(
            Pick.game_date == today_str,
            Pick.sport == sport,
            Pick.result == 'pending',
        ).first()

        if not pick:
            return {'status': 'no_pick', 'date': today_str, 'sport': sport}

        try:
            import subprocess
            subprocess.run(['python', 'main.py'], timeout=300)
        except Exception as e:
            import logging
            logging.error(f"Pre-tip data refresh failed: {e}")

        try:
            from model import EnsemblePredictor
            model = EnsemblePredictor(sport=sport)
            if not model.load_model():
                return {'status': 'error', 'error': 'Model not trained'}

            predictions = model.predict_games(log_predictions=False)
            if not predictions:
                return {'status': 'no_games', 'date': today_str}

            matching = None
            for p in predictions:
                if p.get('home_team') == pick.home_team and p.get('away_team') == pick.away_team:
                    matching = p
                    break

            if not matching:
                return {'status': 'game_not_found', 'pick_id': pick.id}

            try:
                log_edge_snapshots([matching], 'pre_tip', hours_to_tip=None, pick_id=pick.id, sport=sport)
            except Exception:
                pass

            still_passes = matching.get('passes_filter', False)
            new_edge = matching.get('risk_weighted_edge', matching.get('adjusted_edge', 0))
            old_edge = pick.edge_pct or 0
            new_line = matching.get('spread')
            old_line = pick.line

            line_drift = abs((new_line or 0) - (old_line or 0)) if new_line is not None and old_line is not None else 0

            revoke = False
            revoke_reason = None

            if not still_passes:
                revoke = True
                revoke_reason = f"Pre-tip re-check: no longer passes filters — {matching.get('pass_reason', 'edge evaporated')}"
            elif new_edge < 1.5:
                revoke = True
                revoke_reason = f"Pre-tip re-check: edge dropped to {new_edge:+.1f}% (was {old_edge:+.1f}%)"
            elif line_drift >= 2.0:
                revoke = True
                revoke_reason = f"Pre-tip re-check: line moved {line_drift:.1f}pts since publication ({old_line:+.1f} → {new_line:+.1f})"

            if revoke:
                pick.result = 'revoked'
                pick.notes = (pick.notes or '') + f' | REVOKED: {revoke_reason}'
                db.session.commit()

                try:
                    from notification_service import send_revoke_notification
                    send_revoke_notification(pick, revoke_reason)
                except Exception as notif_err:
                    import logging
                    logging.error(f"Revoke notification failed: {notif_err}")

                pass_entry = Pass(
                    date=today_str,
                    sport=sport,
                    games_analyzed=len(predictions),
                    closest_edge_pct=round(new_edge, 1),
                    pass_reason=revoke_reason,
                )
                db.session.add(pass_entry)
                db.session.commit()

                return {
                    'status': 'revoked',
                    'pick_id': pick.id,
                    'reason': revoke_reason,
                    'old_edge': old_edge,
                    'new_edge': round(new_edge, 1),
                    'line_drift': round(line_drift, 1),
                }

            return {
                'status': 'confirmed',
                'pick_id': pick.id,
                'edge': round(new_edge, 1),
                'line_drift': round(line_drift, 1),
            }

        except Exception as e:
            import logging
            logging.error(f"Pre-tip revalidation error: {e}")
            return {'status': 'error', 'error': str(e)}


def run_model_and_log(app, sport='nba'):
    """Run the model for today and log either a pick or pass."""
    cfg = get_sport_config(sport)

    is_live = cfg.get('live', False)
    is_active = cfg.get('active', True)

    if not is_active:
        print(f"[model-run] {sport} is inactive, skipping")
        return {'status': 'inactive', 'sport': sport, 'message': f'{cfg["name"]} is inactive.'}

    start_time = time.time()
    today_str = _get_et_date()
    print(f"[model-run] Starting {sport} run for {today_str} (live={is_live})")

    with app.app_context():
        existing_pick = Pick.query.filter(
            Pick.game_date == today_str,
            Pick.sport == sport,
        ).first()
        existing_pass = Pass.query.filter_by(date=today_str, sport=sport).first()

        if existing_pick or existing_pass:
            print(f"[model-run] Already run for {today_str} — pick={'yes' if existing_pick else 'no'}, pass={'yes' if existing_pass else 'no'}")
            return {'status': 'already_run', 'date': today_str, 'sport': sport}

        try:
            from model import EnsemblePredictor

            model = EnsemblePredictor(sport=sport)
            if not model.load_model():
                print(f"[model-run] ERROR: Model not trained for {sport}")
                return {'status': 'error', 'error': 'Model not trained', 'date': today_str}

            predictions = model.predict_games(log_predictions=True)
            print(f"[model-run] Games found: {len(predictions) if predictions else 0}")

            if not predictions:
                diag = _diagnose_no_games(today_str, sport=sport)
                situation = diag['situation']
                print(f"[model-run] No-games diagnostic: {situation} — {diag['message']}")

                if situation == 'data_failure':
                    duration_ms = int((time.time() - start_time) * 1000)
                    print(f"[model-run] DATA FAILURE — not creating pass, will retry later")
                    return {
                        'status': 'data_failure',
                        'reason': diag['message'],
                        'date': today_str,
                        'sport': sport,
                        'duration_ms': duration_ms,
                    }

                if situation == 'no_spreads':
                    duration_ms = int((time.time() - start_time) * 1000)
                    print(f"[model-run] NO SPREADS — {diag['total_games']} games but lines not posted yet, will retry later")
                    return {
                        'status': 'no_spreads',
                        'reason': diag['message'],
                        'total_games': diag['total_games'],
                        'date': today_str,
                        'sport': sport,
                        'duration_ms': duration_ms,
                    }

                if situation == 'stale_data':
                    duration_ms = int((time.time() - start_time) * 1000)
                    print(f"[model-run] STALE DATA — {diag['total_games']} games all scored, not creating pass, will retry later")
                    return {
                        'status': 'stale_data',
                        'reason': diag['message'],
                        'total_games': diag['total_games'],
                        'date': today_str,
                        'sport': sport,
                        'duration_ms': duration_ms,
                    }

                if situation == 'no_eligible':
                    duration_ms = int((time.time() - start_time) * 1000)
                    print(f"[model-run] NO ELIGIBLE — {diag['total_games']} games, {diag['games_with_spreads']} with spreads but none passed filters — creating pass")

                    pass_entry = Pass(
                        date=today_str,
                        sport=sport,
                        games_analyzed=diag['games_with_spreads'],
                        closest_edge_pct=0,
                        pass_reason=f"No eligible games — {diag['games_with_spreads']} analyzed, none passed filters",
                    )
                    db.session.add(pass_entry)

                    model_run = ModelRun(
                        date=today_str,
                        sport=sport,
                        games_analyzed=diag['games_with_spreads'],
                        pick_generated=False,
                        pass_id=pass_entry.id,
                        run_duration_ms=duration_ms,
                        games_detail=None,
                    )
                    db.session.add(model_run)
                    db.session.commit()

                    try:
                        from notification_service import send_pass_notification
                        send_pass_notification(pass_entry)
                    except Exception as notif_err:
                        import logging
                        logging.error(f"No-eligible pass notification failed: {notif_err}")

                    return {
                        'status': 'pass',
                        'reason': 'no_eligible',
                        'date': today_str,
                        'sport': sport,
                        'games_analyzed': diag['games_with_spreads'],
                        'duration_ms': duration_ms,
                    }

                duration_ms = int((time.time() - start_time) * 1000)
                print(f"[model-run] Unknown no-games situation '{situation}' — not creating pass, will retry")
                return {
                    'status': 'unknown_no_games',
                    'reason': diag['message'],
                    'date': today_str,
                    'sport': sport,
                    'duration_ms': duration_ms,
                }

            qualified = [p for p in predictions if p.get('passes_filter')]
            all_edges = [p.get('adjusted_edge', 0) for p in predictions]
            closest_edge = max(all_edges) if all_edges else 0

            duration_ms = int((time.time() - start_time) * 1000)
            print(f"[model-run] Eligible: {len(qualified)}, Max edge: {closest_edge:+.1f}%, Duration: {duration_ms}ms")

            if qualified:
                best = max(qualified, key=lambda p: p.get('adjusted_edge', 0))

                home_cover_prob = best.get('cover_prob', 0.5)
                is_home_pick = best.get('pick_side') == 'home'
                spread = best.get('spread', 0) or 0
                pick_spread = spread if is_home_pick else -spread

                if is_live:
                    ks = KillSwitch.query.filter_by(sport=sport).first()
                    position_pct = ks.position_size_pct if ks and ks.active else 100

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
                        position_size_pct=position_pct,
                        model_only_cover_prob=_to_python(round(best['model_only_cover_prob'], 4)) if best.get('model_only_cover_prob') is not None else None,
                        model_only_edge=_to_python(round(best['model_only_edge'], 2)) if best.get('model_only_edge') is not None else None,
                    )
                    db.session.add(pick)

                    model_run = ModelRun(
                        date=today_str,
                        sport=sport,
                        games_analyzed=len(predictions),
                        pick_generated=True,
                        pick_id=pick.id,
                        run_duration_ms=duration_ms,
                        games_detail=_build_games_detail(predictions),
                    )
                    db.session.add(model_run)
                    db.session.commit()

                    try:
                        log_edge_snapshots([best], 'open', hours_to_tip=None, pick_id=pick.id, sport=sport)
                    except Exception:
                        pass

                    try:
                        from notification_service import send_pick_notification
                        send_pick_notification(pick)
                    except Exception as notif_err:
                        import logging
                        logging.error(f"Pick notification failed: {notif_err}")

                    print(f"[model-run] Published: {pick.side} | Edge: {pick.edge_pct}% | {best['away_team']} @ {best['home_team']}")
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
                        games_detail=_build_games_detail(predictions),
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
                    games_detail=_build_games_detail(predictions),
                )
                db.session.add(model_run)
                db.session.commit()

                try:
                    from notification_service import send_pass_notification
                    send_pass_notification(pass_entry)
                except Exception as notif_err:
                    import logging
                    logging.error(f"Pass notification failed: {notif_err}")

                print(f"[model-run] Pass: {top_pass_reason} | Max edge: {closest_edge:+.1f}% | {len(predictions)} games")
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
