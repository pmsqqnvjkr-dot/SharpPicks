"""
SHARP PICKS DASHBOARD API
Backend endpoints to power the admin dashboard
"""

from flask import Flask, jsonify, render_template
from flask_cors import CORS
import sqlite3
from datetime import datetime, timedelta

app = Flask(__name__)
CORS(app)
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0

def get_db_connection():
    """Connect to SQLite database"""
    conn = sqlite3.connect('sharp_picks.db')
    conn.row_factory = sqlite3.Row
    return conn

def calculate_streak(dates):
    """Calculate how many days in a row we've collected data"""
    if not dates:
        return 0
    
    streak = 1
    for i in range(len(dates) - 1):
        try:
            date1 = datetime.fromisoformat(dates[i])
            date2 = datetime.fromisoformat(dates[i + 1])
            
            if (date1 - date2).days == 1:
                streak += 1
            else:
                break
        except:
            break
    
    return streak

@app.route('/api/admin/stats', methods=['GET'])
def get_admin_stats():
    """Main dashboard stats endpoint"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # === DATA COLLECTION STATS ===
    cursor.execute('SELECT COUNT(*) as count FROM games')
    total_games = cursor.fetchone()['count']
    
    cursor.execute('SELECT COUNT(*) as count FROM games WHERE spread_result IS NOT NULL')
    games_with_results = cursor.fetchone()['count']
    
    # Collection streak
    cursor.execute('''
        SELECT DISTINCT DATE(game_date) as date 
        FROM games 
        ORDER BY date DESC 
        LIMIT 30
    ''')
    collection_dates = [row['date'] for row in cursor.fetchall()]
    streak = calculate_streak(collection_dates)
    
    # === BETTING STATS (from bets table) ===
    wins = 0
    losses = 0
    total_profit = 0
    total_risked = 0
    last_7_days_profit = 0
    
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='bets'")
    if cursor.fetchone():
        cursor.execute('''
            SELECT 
                SUM(CASE WHEN result = 'win' THEN 1 ELSE 0 END) as wins,
                SUM(CASE WHEN result = 'loss' THEN 1 ELSE 0 END) as losses
            FROM bets
            WHERE result IS NOT NULL
        ''')
        record = cursor.fetchone()
        wins = record['wins'] or 0
        losses = record['losses'] or 0
        
        cursor.execute('''
            SELECT SUM(payout - stake) as total_profit,
                   SUM(stake) as total_risked
            FROM bets
            WHERE result IS NOT NULL
        ''')
        profit_data = cursor.fetchone()
        total_profit = profit_data['total_profit'] or 0
        total_risked = profit_data['total_risked'] or 0
        
        seven_days_ago = (datetime.now() - timedelta(days=7)).isoformat()
        cursor.execute('''
            SELECT SUM(payout - stake) as profit
            FROM bets
            WHERE result IS NOT NULL
            AND timestamp >= ?
        ''', (seven_days_ago,))
        last_7_days_profit = cursor.fetchone()['profit'] or 0
    
    total_picks = wins + losses
    win_rate = (wins / total_picks * 100) if total_picks > 0 else 0
    roi = (total_profit / total_risked * 100) if total_risked > 0 else 0
    
    # === PROFIT HISTORY ===
    profit_history = []
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='bets'")
    if cursor.fetchone():
        cursor.execute('''
            SELECT 
                DATE(timestamp) as date,
                SUM(payout - stake) as daily_profit
            FROM bets
            WHERE result IS NOT NULL
            GROUP BY DATE(timestamp)
            ORDER BY date DESC
            LIMIT 30
        ''')
        
        cumulative = 0
        for row in reversed(list(cursor.fetchall())):
            cumulative += row['daily_profit']
            profit_history.append({
                'date': row['date'],
                'profit': round(cumulative, 2)
            })
    
    # === RECENT PICKS ===
    recent_picks = []
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='bets'")
    if cursor.fetchone():
        cursor.execute('''
            SELECT 
                game,
                pick,
                result,
                payout - stake as profit,
                DATE(timestamp) as date
            FROM bets
            ORDER BY timestamp DESC
            LIMIT 10
        ''')
        
        for row in cursor.fetchall():
            recent_picks.append({
                'date': row['date'],
                'game': row['game'],
                'pick': row['pick'],
                'result': row['result'].upper() if row['result'] else 'PENDING',
                'profit': round(row['profit'], 2) if row['profit'] else 0
            })
    
    # === SYSTEM HEALTH ===
    system_health = [
        {
            'name': 'Data Collection',
            'status': 'operational' if streak > 0 else 'warning',
            'message': f'{streak} day streak' if streak > 0 else 'No recent collection'
        },
        {
            'name': 'API Status',
            'status': 'operational',
            'message': 'All systems operational'
        },
        {
            'name': 'Database',
            'status': 'operational',
            'message': f'{total_games} games stored'
        }
    ]
    
    conn.close()
    
    return jsonify({
        'gamesCollected': total_games,
        'gamesWithResults': games_with_results,
        'collectionStreak': streak,
        'wins': wins,
        'losses': losses,
        'winRate': round(win_rate, 1),
        'totalProfit': round(total_profit, 2),
        'roi': round(roi, 1),
        'last7DaysProfit': round(last_7_days_profit, 2),
        'profitHistory': profit_history,
        'recentPicks': recent_picks,
        'systemHealth': system_health
    })

@app.route('/api/admin/stats/live', methods=['GET'])
def get_live_stats():
    """Lightweight endpoint for live updates"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    today = datetime.now().date().isoformat()
    cursor.execute('''
        SELECT COUNT(*) as count 
        FROM games 
        WHERE DATE(game_date) = ?
    ''', (today,))
    games_today = cursor.fetchone()['count']
    
    pending_picks = 0
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='bets'")
    if cursor.fetchone():
        cursor.execute('''
            SELECT COUNT(*) as count 
            FROM bets 
            WHERE result IS NULL
        ''')
        pending_picks = cursor.fetchone()['count']
    
    conn.close()
    
    return jsonify({
        'gamesToday': games_today,
        'pendingPicks': pending_picks,
        'timestamp': datetime.now().isoformat()
    })

@app.route('/api/admin/collection-log', methods=['GET'])
def get_collection_log():
    """Returns detailed collection log"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT 
            DATE(game_date) as date,
            COUNT(*) as games_collected
        FROM games
        GROUP BY DATE(game_date)
        ORDER BY date DESC
        LIMIT 30
    ''')
    
    log = []
    for row in cursor.fetchall():
        log.append({
            'date': row['date'],
            'games': row['games_collected']
        })
    
    conn.close()
    
    return jsonify({'log': log})

@app.route('/')
@app.route('/dashboard')
def dashboard():
    """Serve the React dashboard"""
    return render_template('dashboard.html')

@app.route('/api', methods=['GET'])
def api_index():
    """API health check"""
    return jsonify({
        'status': 'ok',
        'service': 'Sharp Picks Dashboard API',
        'endpoints': [
            '/api/admin/stats',
            '/api/admin/stats/live',
            '/api/admin/collection-log'
        ]
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
