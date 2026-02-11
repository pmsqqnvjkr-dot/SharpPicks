"""
Model Run Service
Bridges the existing ML prediction pipeline with the new picks/passes tables.
Called after the model generates predictions to log picks or passes.
"""

import sqlite3
import time
from datetime import datetime
from models import db, Pick, Pass, ModelRun

EDGE_THRESHOLD = 3.5


def run_model_and_log(app):
    """Run the model for today and log either a pick or pass."""
    start_time = time.time()
    today_str = datetime.now().strftime('%Y-%m-%d')

    with app.app_context():
        existing_pick = Pick.query.filter(
            Pick.game_date.like(f'{today_str}%')
        ).first()
        existing_pass = Pass.query.filter_by(date=today_str).first()

        if existing_pick or existing_pass:
            return {'status': 'already_run', 'date': today_str}

        try:
            conn = sqlite3.connect('sharp_picks.db')
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute('''
                SELECT g.id, g.home_team, g.away_team, g.game_date, g.spread_home,
                       p.home_cover_prob, p.confidence, p.prediction
                FROM games g
                LEFT JOIN prediction_log p ON g.id = p.game_id
                WHERE g.game_date LIKE ?
                AND p.id IS NOT NULL
                ORDER BY p.confidence DESC
            ''', (f'{today_str}%',))

            predictions = cursor.fetchall()
            conn.close()

            if not predictions:
                pass_entry = Pass(
                    date=today_str,
                    sport='nba',
                    games_analyzed=0,
                    closest_edge_pct=0,
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

            best_pred = None
            best_edge = 0
            closest_edge = 0

            for pred in predictions:
                confidence = pred['confidence'] or 0.5
                edge = abs(confidence - 0.5) * 100 * 2
                if edge > closest_edge:
                    closest_edge = edge
                if edge >= EDGE_THRESHOLD and (best_pred is None or edge > best_edge):
                    best_pred = pred
                    best_edge = edge

            duration_ms = int((time.time() - start_time) * 1000)

            if best_pred:
                pick = Pick(
                    sport='nba',
                    away_team=best_pred['away_team'],
                    home_team=best_pred['home_team'],
                    game_date=best_pred['game_date'],
                    side=best_pred['prediction'],
                    line=-110,
                    edge_pct=round(best_edge, 1),
                    model_confidence=round(best_pred['confidence'], 4),
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
                pass_entry = Pass(
                    date=today_str,
                    sport='nba',
                    games_analyzed=len(predictions),
                    closest_edge_pct=round(closest_edge, 1),
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
                    'date': today_str,
                }

        except Exception as e:
            return {'status': 'error', 'error': str(e), 'date': today_str}
