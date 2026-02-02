"""
SHARP PICKS - ALL-IN-ONE APP
Flask server with API endpoints and dashboard
"""

from flask import Flask, jsonify, Response
from flask_cors import CORS
import sqlite3
from datetime import datetime, timedelta

app = Flask(__name__)
CORS(app)

def get_db():
    conn = sqlite3.connect('sharp_picks.db')
    conn.row_factory = sqlite3.Row
    return conn

def calculate_streak(dates):
    if not dates:
        return 0
    streak = 1
    for i in range(len(dates) - 1):
        try:
            d1 = datetime.fromisoformat(dates[i])
            d2 = datetime.fromisoformat(dates[i + 1])
            if (d1 - d2).days == 1:
                streak += 1
            else:
                break
        except:
            break
    return streak

@app.route('/')
def index():
    return "Sharp Picks API is running!"

@app.route('/api/admin/stats')
def get_stats():
    conn = get_db()
    cur = conn.cursor()
    
    cur.execute('SELECT COUNT(*) as c FROM games')
    total = cur.fetchone()['c']
    
    cur.execute('SELECT COUNT(*) as c FROM games WHERE spread_result IS NOT NULL')
    with_results = cur.fetchone()['c']
    
    cur.execute('SELECT DISTINCT DATE(game_date) as d FROM games ORDER BY d DESC LIMIT 30')
    dates = [r['d'] for r in cur.fetchall()]
    streak = calculate_streak(dates)
    
    wins, losses, profit, risked = 0, 0, 0, 0
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='bets'")
    if cur.fetchone():
        cur.execute('SELECT SUM(CASE WHEN result="win" THEN 1 ELSE 0 END) as w, SUM(CASE WHEN result="loss" THEN 1 ELSE 0 END) as l FROM bets WHERE result IS NOT NULL')
        r = cur.fetchone()
        wins, losses = r['w'] or 0, r['l'] or 0
        cur.execute('SELECT SUM(payout-stake) as p, SUM(stake) as r FROM bets WHERE result IS NOT NULL')
        r = cur.fetchone()
        profit, risked = r['p'] or 0, r['r'] or 0
    
    conn.close()
    
    return jsonify({
        'gamesCollected': total,
        'gamesWithResults': with_results,
        'collectionStreak': streak,
        'wins': wins,
        'losses': losses,
        'winRate': round(wins/(wins+losses)*100, 1) if wins+losses > 0 else 0,
        'totalProfit': round(profit, 2),
        'roi': round(profit/risked*100, 1) if risked > 0 else 0,
        'systemHealth': [
            {'name': 'Data Collection', 'status': 'operational' if streak > 0 else 'warning', 'message': f'{streak} day streak'},
            {'name': 'API Status', 'status': 'operational', 'message': 'All systems operational'},
            {'name': 'Database', 'status': 'operational', 'message': f'{total} games stored'}
        ]
    })

DASHBOARD_HTML = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Sharp Picks Dashboard</title>
    <style>
        *{margin:0;padding:0;box-sizing:border-box}
        body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;background:#0F172A;min-height:100vh;color:#fff}
        .container{max-width:1200px;margin:0 auto;padding:24px}
        .header{text-align:center;padding:40px 0;margin-bottom:32px}
        .header h1{font-size:2.5rem;font-weight:700;background:linear-gradient(135deg,#3B82F6,#6366F1);-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text}
        .header p{color:#94A3B8;margin-top:8px}
        .grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:24px}
        .card{background:rgba(30,41,59,0.8);border-radius:16px;padding:28px;border:1px solid rgba(148,163,184,0.1);transition:transform 0.2s}
        .card:hover{transform:translateY(-4px);box-shadow:0 12px 40px rgba(0,0,0,0.3)}
        .card-label{font-size:0.75rem;font-weight:600;color:#94A3B8;text-transform:uppercase;letter-spacing:0.1em;margin-bottom:16px}
        .card-value{font-size:3rem;font-weight:700;color:#fff}
        .card-sub{font-size:0.875rem;color:#64748B;margin-top:12px}
        .progress{margin-top:20px}
        .progress-bar{width:100%;height:10px;background:rgba(148,163,184,0.2);border-radius:5px;overflow:hidden}
        .progress-fill{height:100%;background:linear-gradient(90deg,#3B82F6,#6366F1);border-radius:5px;transition:width 0.6s}
        .progress-text{display:flex;justify-content:space-between;margin-top:8px;font-size:0.75rem;color:#64748B}
        .streak{background:linear-gradient(135deg,rgba(59,130,246,0.15),rgba(99,102,241,0.15));border-color:rgba(99,102,241,0.3)}
        .streak-row{display:flex;align-items:center;gap:16px}
        .fire{font-size:2.5rem}
        .streak-msg{margin-top:12px;padding:8px 16px;background:rgba(99,102,241,0.2);border-radius:8px;display:inline-block;font-size:0.875rem;color:#A5B4FC}
        .health{grid-column:1/-1}
        .health-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:16px;margin-top:16px}
        .health-item{display:flex;align-items:center;gap:12px;padding:16px;background:rgba(15,23,42,0.6);border-radius:12px;border:1px solid rgba(148,163,184,0.1)}
        .dot{width:12px;height:12px;border-radius:50%;flex-shrink:0}
        .dot.operational{background:#22C55E;box-shadow:0 0 12px rgba(34,197,94,0.5)}
        .dot.warning{background:#F59E0B;box-shadow:0 0 12px rgba(245,158,11,0.5)}
        .health-name{font-weight:600;font-size:0.875rem}
        .health-msg{font-size:0.75rem;color:#64748B;margin-top:2px}
        .perf{grid-column:1/-1}
        .stats-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:16px;margin-top:16px}
        .stat{text-align:center;padding:20px;background:rgba(15,23,42,0.6);border-radius:12px;border:1px solid rgba(148,163,184,0.1)}
        .stat-val{font-size:1.5rem;font-weight:700}
        .stat-val.pos{color:#22C55E}.stat-val.neg{color:#EF4444}
        .stat-lbl{font-size:0.75rem;color:#64748B;margin-top:4px}
        .badge{position:fixed;bottom:24px;right:24px;background:rgba(30,41,59,0.9);padding:10px 18px;border-radius:24px;font-size:0.75rem;color:#64748B;border:1px solid rgba(148,163,184,0.2)}
        .pulse{display:inline-block;width:8px;height:8px;background:#22C55E;border-radius:50%;margin-right:8px;animation:pulse 2s infinite}
        @keyframes pulse{0%,100%{opacity:1}50%{opacity:0.5}}
        .loading{display:flex;justify-content:center;align-items:center;min-height:400px}
        .spinner{width:48px;height:48px;border:4px solid rgba(148,163,184,0.2);border-top-color:#3B82F6;border-radius:50%;animation:spin 1s linear infinite}
        @keyframes spin{to{transform:rotate(360deg)}}
        @media(max-width:768px){.container{padding:16px}.header h1{font-size:1.75rem}.card-value{font-size:2.25rem}.grid{grid-template-columns:1fr}}
    </style>
</head>
<body>
    <div class="container">
        <header class="header"><h1>Sharp Picks Dashboard</h1><p>NBA Betting Analysis System</p></header>
        <div id="content"><div class="loading"><div class="spinner"></div></div></div>
    </div>
    <div class="badge"><span class="pulse"></span><span id="time">Loading...</span></div>
    <script>
        async function load(){
            try{
                const r=await fetch('/api/admin/stats');
                const s=await r.json();
                render(s);
                document.getElementById('time').textContent='Updated '+new Date().toLocaleTimeString();
            }catch(e){console.error(e)}
        }
        function render(s){
            const pct=Math.min((s.gamesWithResults/50)*100,100);
            const fire='🔥'.repeat(s.collectionStreak>=7?3:s.collectionStreak>=3?2:1);
            const msg=s.collectionStreak>=7?'On fire!':s.collectionStreak>=3?'Great streak!':'Building...';
            document.getElementById('content').innerHTML=`
                <div class="grid">
                    <div class="card">
                        <div class="card-label">Games Collected</div>
                        <div class="card-value">${s.gamesCollected}</div>
                        <div class="card-sub">${s.gamesWithResults} of 50 with results</div>
                        <div class="progress"><div class="progress-bar"><div class="progress-fill" style="width:${pct}%"></div></div>
                        <div class="progress-text"><span>Progress</span><span>${pct.toFixed(0)}%</span></div></div>
                    </div>
                    <div class="card streak">
                        <div class="card-label">Collection Streak</div>
                        <div class="streak-row"><span class="fire">${fire}</span><span class="card-value">${s.collectionStreak}</span></div>
                        <div class="streak-msg">${msg}</div>
                    </div>
                    <div class="card health">
                        <div class="card-label">System Health</div>
                        <div class="health-grid">${s.systemHealth.map(h=>`
                            <div class="health-item"><div class="dot ${h.status}"></div><div><div class="health-name">${h.name}</div><div class="health-msg">${h.message}</div></div></div>
                        `).join('')}</div>
                    </div>
                    <div class="card perf">
                        <div class="card-label">Performance</div>
                        <div class="stats-grid">
                            <div class="stat"><div class="stat-val">${s.wins}W-${s.losses}L</div><div class="stat-lbl">Record</div></div>
                            <div class="stat"><div class="stat-val">${s.winRate>0?s.winRate+'%':'--'}</div><div class="stat-lbl">Win Rate</div></div>
                            <div class="stat"><div class="stat-val ${s.totalProfit>=0?'pos':'neg'}">${s.totalProfit?'$'+s.totalProfit.toFixed(2):'--'}</div><div class="stat-lbl">Profit</div></div>
                            <div class="stat"><div class="stat-val ${s.roi>=0?'pos':'neg'}">${s.roi?s.roi+'%':'--'}</div><div class="stat-lbl">ROI</div></div>
                        </div>
                    </div>
                </div>`;
        }
        load();
        setInterval(load,30000);
    </script>
</body>
</html>'''

@app.route('/dashboard')
def dashboard():
    return Response(DASHBOARD_HTML, mimetype='text/html')

if __name__ == '__main__':
    print("Starting Sharp Picks API on http://0.0.0.0:5000")
    print("Dashboard: http://0.0.0.0:5000/dashboard")
    app.run(host='0.0.0.0', port=5000, debug=True)
