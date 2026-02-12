"""
📊 PERFORMANCE TRACKER - Track live model predictions vs actual results
Logs predictions daily and calculates rolling performance metrics
"""

import sqlite3
from datetime import datetime, timedelta
import pickle
import numpy as np
import pandas as pd


def ensure_tracking_table():
    """Create prediction tracking table"""
    conn = sqlite3.connect('sharp_picks.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS prediction_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            game_id TEXT,
            game_date TEXT,
            home_team TEXT,
            away_team TEXT,
            spread_home REAL,
            prediction TEXT,
            confidence REAL,
            home_cover_prob REAL,
            actual_result TEXT,
            is_correct INTEGER,
            logged_at TEXT,
            resolved_at TEXT,
            opening_line REAL,
            closing_line REAL,
            beat_close INTEGER,
            implied_prob REAL,
            edge_vs_market REAL,
            expected_value REAL,
            recommended_book TEXT,
            market_odds INTEGER,
            explanation TEXT
        )
    ''')
    
    for col, coltype in [
        ('opening_line', 'REAL'), ('closing_line', 'REAL'), ('beat_close', 'INTEGER'),
        ('implied_prob', 'REAL'), ('edge_vs_market', 'REAL'), ('expected_value', 'REAL'),
        ('recommended_book', 'TEXT'), ('market_odds', 'INTEGER'), ('explanation', 'TEXT'),
        ('predicted_margin', 'REAL'),
    ]:
        try:
            cursor.execute(f'ALTER TABLE prediction_log ADD COLUMN {col} {coltype}')
        except:
            pass
    
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_pred_date ON prediction_log(game_date)
    ''')
    
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_pred_game ON prediction_log(game_id)
    ''')
    
    conn.commit()
    conn.close()


def odds_to_implied_prob(odds=-110):
    """Convert American odds to implied probability"""
    if odds < 0:
        return abs(odds) / (abs(odds) + 100)
    else:
        return 100 / (odds + 100)


def calculate_ev(model_prob, odds=-110):
    """Calculate expected value: EV = (prob * payout) - ((1-prob) * stake)"""
    if odds < 0:
        payout = 100 / abs(odds)
    else:
        payout = odds / 100
    ev = (model_prob * payout) - ((1 - model_prob) * 1)
    return round(ev * 100, 2)


def log_prediction(game_id, game_date, home_team, away_team, spread_home, 
                   prediction, confidence, home_cover_prob, opening_line=None,
                   market_odds=-110, recommended_book=None, explanation=None,
                   predicted_margin=None):
    """Log a new prediction with margin, EV, implied prob, and audit trail"""
    ensure_tracking_table()
    conn = sqlite3.connect('sharp_picks.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT id FROM prediction_log WHERE game_id = ?
    ''', (game_id,))
    
    if cursor.fetchone():
        conn.close()
        return False
    
    implied = odds_to_implied_prob(market_odds)
    edge = round((confidence - implied) * 100, 2)
    ev = calculate_ev(confidence, market_odds)
    
    cursor.execute('''
        INSERT INTO prediction_log 
        (game_id, game_date, home_team, away_team, spread_home, prediction, 
         confidence, home_cover_prob, logged_at, opening_line,
         implied_prob, edge_vs_market, expected_value, recommended_book, market_odds, explanation,
         predicted_margin)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        game_id, game_date, home_team, away_team, spread_home,
        prediction, confidence, home_cover_prob,
        datetime.now().isoformat(),
        opening_line if opening_line else spread_home,
        round(implied, 4), edge, ev, recommended_book, market_odds, explanation,
        predicted_margin
    ))
    
    conn.commit()
    conn.close()
    return True


def update_closing_line(game_id, closing_line):
    """Update closing line for a game and calculate if we beat it"""
    ensure_tracking_table()
    conn = sqlite3.connect('sharp_picks.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT opening_line, prediction, spread_home FROM prediction_log WHERE game_id = ?
    ''', (game_id,))
    
    row = cursor.fetchone()
    if not row:
        conn.close()
        return False
    
    opening_line, prediction, spread_at_pick = row
    
    beat_close = 0
    if spread_at_pick is not None and closing_line is not None:
        clv = closing_line - spread_at_pick
        
        is_home_pick = prediction and ('home' in prediction.lower() or 'cover' in prediction.lower())
        
        if is_home_pick:
            beat_close = 1 if clv < 0 else 0
        else:
            beat_close = 1 if clv > 0 else 0
    
    cursor.execute('''
        UPDATE prediction_log 
        SET closing_line = ?, beat_close = ?
        WHERE game_id = ?
    ''', (closing_line, beat_close, game_id))
    
    conn.commit()
    conn.close()
    return True


def get_closing_line_stats():
    """Get stats on how often we beat the closing line"""
    ensure_tracking_table()
    conn = sqlite3.connect('sharp_picks.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT 
            COUNT(*) as total_with_close,
            SUM(beat_close) as beat_count,
            AVG(closing_line - opening_line) as avg_line_movement
        FROM prediction_log
        WHERE closing_line IS NOT NULL AND opening_line IS NOT NULL
    ''')
    
    row = cursor.fetchone()
    conn.close()
    
    if row and row[0] > 0:
        return {
            'total_tracked': row[0],
            'beat_closing': row[1] or 0,
            'beat_rate': round((row[1] or 0) / row[0] * 100, 1),
            'avg_line_movement': round(row[2] or 0, 2)
        }
    
    return {
        'total_tracked': 0,
        'beat_closing': 0,
        'beat_rate': 0,
        'avg_line_movement': 0
    }


def update_results():
    """Update prediction results from completed games"""
    ensure_tracking_table()
    conn = sqlite3.connect('sharp_picks.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT p.id, p.game_id, p.home_cover_prob, g.spread_result
        FROM prediction_log p
        JOIN games g ON p.game_id = g.id
        WHERE p.actual_result IS NULL
        AND g.spread_result IS NOT NULL
    ''')
    
    updates = cursor.fetchall()
    updated = 0
    
    for pred_id, game_id, home_prob, result in updates:
        predicted_home = home_prob >= 0.5
        actual_home = result == 'HOME_COVER'
        is_correct = 1 if predicted_home == actual_home else 0
        
        if result == 'PUSH':
            is_correct = None
        
        cursor.execute('''
            UPDATE prediction_log 
            SET actual_result = ?, is_correct = ?, resolved_at = ?
            WHERE id = ?
        ''', (result, is_correct, datetime.now().isoformat(), pred_id))
        
        updated += 1
    
    conn.commit()
    conn.close()
    
    return updated


def get_performance_stats(days=None):
    """Get performance statistics"""
    ensure_tracking_table()
    conn = sqlite3.connect('sharp_picks.db')
    
    if days:
        cutoff = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
        query = '''
            SELECT * FROM prediction_log 
            WHERE actual_result IS NOT NULL
            AND game_date >= ?
        '''
        df = pd.read_sql_query(query, conn, params=(cutoff,))
    else:
        query = '''
            SELECT * FROM prediction_log 
            WHERE actual_result IS NOT NULL
        '''
        df = pd.read_sql_query(query, conn)
    
    conn.close()
    
    if len(df) == 0:
        return None
    
    df = df[df['actual_result'] != 'PUSH']
    
    total = len(df)
    correct = df['is_correct'].sum()
    accuracy = (correct / total * 100) if total > 0 else 0
    
    brier = np.mean((df['home_cover_prob'] - (df['actual_result'] == 'HOME_COVER').astype(int)) ** 2)
    
    confidence_buckets = []
    for low, high in [(0.5, 0.55), (0.55, 0.60), (0.60, 0.65), (0.65, 0.70), (0.70, 0.80), (0.80, 1.0)]:
        mask = (df['confidence'] >= low) & (df['confidence'] < high)
        if mask.sum() > 0:
            bucket_acc = df.loc[mask, 'is_correct'].mean() * 100
            confidence_buckets.append({
                'range': f"{low*100:.0f}%-{high*100:.0f}%",
                'count': int(mask.sum()),
                'accuracy': bucket_acc
            })
    
    stake = 100
    wins = int(correct)
    losses = total - wins
    profit = (wins * 90.91) - (losses * 100)
    roi = (profit / (total * stake) * 100) if total > 0 else 0
    
    return {
        'total_predictions': total,
        'correct': int(correct),
        'accuracy': accuracy,
        'brier_score': brier,
        'confidence_buckets': confidence_buckets,
        'simulated_profit': profit,
        'simulated_roi': roi,
        'period_days': days
    }


def get_recent_predictions(limit=20):
    """Get recent prediction results"""
    ensure_tracking_table()
    conn = sqlite3.connect('sharp_picks.db')
    
    query = '''
        SELECT game_date, home_team, away_team, prediction, confidence,
               actual_result, is_correct
        FROM prediction_log
        ORDER BY game_date DESC, logged_at DESC
        LIMIT ?
    '''
    
    df = pd.read_sql_query(query, conn, params=(limit,))
    conn.close()
    
    return df


def check_calibration():
    """Check model calibration by confidence bucket"""
    ensure_tracking_table()
    conn = sqlite3.connect('sharp_picks.db')
    
    query = '''
        SELECT confidence, is_correct, actual_result
        FROM prediction_log 
        WHERE actual_result IS NOT NULL
        AND actual_result != 'PUSH'
    '''
    df = pd.read_sql_query(query, conn)
    conn.close()
    
    if len(df) == 0:
        print("\n⚠️ No resolved predictions for calibration check")
        return None
    
    print("\n" + "="*60)
    print("📊 MODEL CALIBRATION CHECK")
    print("="*60)
    print(f"{'Confidence':<15} {'Expected':>10} {'Actual':>10} {'Count':>8} {'Error':>10}")
    print("-"*60)
    
    calibration_data = []
    for conf_bucket in [50, 55, 60, 65, 70, 80]:
        high = conf_bucket + 5 if conf_bucket < 80 else 100
        mask = (df['confidence'] * 100 >= conf_bucket) & (df['confidence'] * 100 < high)
        picks = df[mask]
        
        if len(picks) > 0:
            actual_win_rate = picks['is_correct'].mean() * 100
            expected = (conf_bucket + high) / 2
            error = actual_win_rate - expected
            
            status = "✅" if abs(error) < 5 else "⚠️" if abs(error) < 10 else "❌"
            
            print(f"{conf_bucket}-{high}%{'':<7} {expected:>9.1f}% {actual_win_rate:>9.1f}% {len(picks):>8} {error:>+9.1f}% {status}")
            
            calibration_data.append({
                'bucket': f"{conf_bucket}-{high}%",
                'expected': expected,
                'actual': actual_win_rate,
                'count': len(picks),
                'error': error
            })
    
    if calibration_data:
        mean_error = np.mean([abs(d['error']) for d in calibration_data])
        print("-"*60)
        print(f"Mean Absolute Error: {mean_error:.1f}%")
        if mean_error < 3:
            print("📈 Excellent calibration!")
        elif mean_error < 5:
            print("👍 Good calibration")
        elif mean_error < 10:
            print("⚠️ Moderate calibration - may need adjustment")
        else:
            print("❌ Poor calibration - model overconfident or underconfident")
    
    print("="*60 + "\n")
    return calibration_data


def show_performance_report():
    """Display performance tracking report"""
    update_results()
    
    print("\n" + "="*70)
    print("📊 MODEL PERFORMANCE TRACKER")
    print("="*70)
    
    all_time = get_performance_stats()
    last_30 = get_performance_stats(days=30)
    last_7 = get_performance_stats(days=7)
    
    if not all_time:
        print("\n⚠️ No resolved predictions yet. Predictions will be logged automatically.")
        print("   Check back after games complete!\n")
        return
    
    print(f"\n📈 OVERALL PERFORMANCE")
    print("-"*50)
    print(f"   Total Predictions: {all_time['total_predictions']}")
    print(f"   Accuracy: {all_time['accuracy']:.1f}% ({all_time['correct']}/{all_time['total_predictions']})")
    print(f"   Brier Score: {all_time['brier_score']:.4f}")
    print(f"   Simulated ROI: {all_time['simulated_roi']:+.1f}%")
    
    if last_30:
        print(f"\n📅 LAST 30 DAYS")
        print("-"*50)
        print(f"   Accuracy: {last_30['accuracy']:.1f}% ({last_30['correct']}/{last_30['total_predictions']})")
        print(f"   ROI: {last_30['simulated_roi']:+.1f}%")
    
    if last_7:
        print(f"\n📅 LAST 7 DAYS")
        print("-"*50)
        print(f"   Accuracy: {last_7['accuracy']:.1f}% ({last_7['correct']}/{last_7['total_predictions']})")
        print(f"   ROI: {last_7['simulated_roi']:+.1f}%")
    
    print(f"\n📊 ACCURACY BY CONFIDENCE")
    print("-"*50)
    for bucket in all_time['confidence_buckets']:
        bar = "█" * int(bucket['accuracy'] / 5)
        print(f"   {bucket['range']:<12} {bar} {bucket['accuracy']:.1f}% ({bucket['count']} games)")
    
    recent = get_recent_predictions(10)
    if len(recent) > 0:
        print(f"\n🎯 RECENT PREDICTIONS")
        print("-"*70)
        print(f"{'Date':<12} {'Game':<25} {'Pick':<15} {'Conf':>6} {'Result':>8}")
        print("-"*70)
        
        for _, row in recent.iterrows():
            game = f"{row['away_team']}@{row['home_team']}"[:24]
            result = "✅" if row['is_correct'] == 1 else "❌" if row['is_correct'] == 0 else "⏳"
            conf = f"{row['confidence']*100:.0f}%"
            print(f"{row['game_date']:<12} {game:<25} {row['prediction']:<15} {conf:>6} {result:>8}")
    
    print("\n" + "="*70 + "\n")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        if sys.argv[1] == 'update':
            updated = update_results()
            print(f"✅ Updated {updated} prediction results")
        elif sys.argv[1] == 'report':
            show_performance_report()
        elif sys.argv[1] == 'calibration':
            check_calibration()
    else:
        show_performance_report()
