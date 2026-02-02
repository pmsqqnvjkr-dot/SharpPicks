"""
🏀 SHARP PICKS - NBA DATA COLLECTOR
Run this daily to build your dataset
"""

import requests
import sqlite3
import os
from datetime import datetime, timedelta

# Get API key from Replit Secrets
API_KEY = os.environ.get('ODDS_API_KEY')

# Team name mapping (Odds API -> ESPN)
TEAM_NAME_MAP = {
    'Los Angeles Lakers': 'LA Lakers',
    'Los Angeles Clippers': 'LA Clippers',
}

def setup_database():
    """Create database if it doesn't exist"""
    conn = sqlite3.connect('sharp_picks.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS games (
            id TEXT PRIMARY KEY,
            game_date TEXT,
            home_team TEXT,
            away_team TEXT,
            spread_home REAL,
            spread_away REAL,
            total REAL,
            home_ml INTEGER,
            away_ml INTEGER,
            collected_at TEXT,
            home_score INTEGER,
            away_score INTEGER,
            spread_result TEXT,
            total_result TEXT,
            scores_updated_at TEXT
        )
    ''')
    
    # Add new columns if they don't exist (for existing databases)
    try:
        cursor.execute('ALTER TABLE games ADD COLUMN home_score INTEGER')
    except:
        pass
    try:
        cursor.execute('ALTER TABLE games ADD COLUMN away_score INTEGER')
    except:
        pass
    try:
        cursor.execute('ALTER TABLE games ADD COLUMN spread_result TEXT')
    except:
        pass
    try:
        cursor.execute('ALTER TABLE games ADD COLUMN total_result TEXT')
    except:
        pass
    try:
        cursor.execute('ALTER TABLE games ADD COLUMN scores_updated_at TEXT')
    except:
        pass
    
    conn.commit()
    conn.close()

def normalize_team_name(name):
    """Normalize team names for matching between APIs"""
    return TEAM_NAME_MAP.get(name, name)

def collect_yesterdays_scores():
    """Fetch yesterday's final scores from ESPN API"""
    print("\n" + "="*60)
    print("📊 COLLECTING YESTERDAY'S FINAL SCORES")
    print("="*60 + "\n")
    
    # Get yesterday's date
    yesterday = datetime.now() - timedelta(days=1)
    date_str = yesterday.strftime('%Y%m%d')
    display_date = yesterday.strftime('%B %d, %Y')
    
    print(f"📅 Fetching scores for: {display_date}\n")
    
    url = f"https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard?dates={date_str}"
    
    try:
        response = requests.get(url)
        
        if response.status_code != 200:
            print(f"❌ ESPN API Error: {response.status_code}")
            return
        
        data = response.json()
        events = data.get('events', [])
        
        if not events:
            print("ℹ️  No games found for yesterday\n")
            return
        
        print(f"✅ Found {len(events)} games\n")
        
        conn = sqlite3.connect('sharp_picks.db')
        cursor = conn.cursor()
        
        updated_count = 0
        
        for event in events:
            # Only process completed games
            status = event.get('status', {}).get('type', {}).get('name', '')
            if status != 'STATUS_FINAL':
                continue
            
            competitions = event.get('competitions', [])
            if not competitions:
                continue
            
            competition = competitions[0]
            competitors = competition.get('competitors', [])
            
            home_team = None
            away_team = None
            home_score = None
            away_score = None
            
            for competitor in competitors:
                team_name = competitor.get('team', {}).get('displayName', '')
                score = int(competitor.get('score', 0))
                
                if competitor.get('homeAway') == 'home':
                    home_team = team_name
                    home_score = score
                else:
                    away_team = team_name
                    away_score = score
            
            if not all([home_team, away_team, home_score is not None, away_score is not None]):
                continue
            
            # Find matching game in database
            game_date = yesterday.strftime('%Y-%m-%d')
            
            cursor.execute('''
                SELECT id, spread_home, total FROM games 
                WHERE game_date = ? 
                AND (home_team LIKE ? OR home_team LIKE ?)
                AND home_score IS NULL
            ''', (game_date, f'%{home_team.split()[-1]}%', f'%{normalize_team_name(home_team).split()[-1]}%'))
            
            game = cursor.fetchone()
            
            if game:
                game_id, spread_home, total = game
                
                # Calculate spread result
                margin = home_score - away_score
                spread_result = None
                if spread_home is not None:
                    adjusted_margin = margin + spread_home
                    if adjusted_margin > 0:
                        spread_result = 'HOME_COVER'
                    elif adjusted_margin < 0:
                        spread_result = 'AWAY_COVER'
                    else:
                        spread_result = 'PUSH'
                
                # Calculate total result
                total_result = None
                actual_total = home_score + away_score
                if total is not None:
                    if actual_total > total:
                        total_result = 'OVER'
                    elif actual_total < total:
                        total_result = 'UNDER'
                    else:
                        total_result = 'PUSH'
                
                # Update database
                cursor.execute('''
                    UPDATE games 
                    SET home_score = ?, away_score = ?, 
                        spread_result = ?, total_result = ?,
                        scores_updated_at = ?
                    WHERE id = ?
                ''', (home_score, away_score, spread_result, total_result, 
                      datetime.now().isoformat(), game_id))
                
                updated_count += 1
                
                # Display result
                print(f"🏀 {away_team} {away_score} @ {home_team} {home_score}")
                if spread_result:
                    emoji = "✅" if spread_result != 'PUSH' else "➖"
                    print(f"   {emoji} Spread: {spread_result} (line was {spread_home:+.1f})")
                if total_result:
                    emoji = "✅" if total_result != 'PUSH' else "➖"
                    print(f"   {emoji} Total: {total_result} (line was {total}, actual {actual_total})")
                print()
        
        conn.commit()
        conn.close()
        
        print("="*60)
        print(f"\n📈 Updated {updated_count} games with final scores\n")
        
        # Show spread tracking stats
        show_spread_stats()
        
    except Exception as e:
        print(f"\n❌ Error: {e}\n")

def show_spread_stats():
    """Show spread hit/miss statistics"""
    conn = sqlite3.connect('sharp_picks.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT spread_result, COUNT(*) 
        FROM games 
        WHERE spread_result IS NOT NULL 
        GROUP BY spread_result
    ''')
    results = cursor.fetchall()
    
    if results:
        print("📊 SPREAD TRACKING STATS:")
        for result, count in results:
            print(f"   {result}: {count}")
    
    cursor.execute('''
        SELECT total_result, COUNT(*) 
        FROM games 
        WHERE total_result IS NOT NULL 
        GROUP BY total_result
    ''')
    total_results = cursor.fetchall()
    
    if total_results:
        print("\n📊 TOTAL TRACKING STATS:")
        for result, count in total_results:
            print(f"   {result}: {count}")
    
    conn.close()
    print()

def collect_todays_games():
    """Fetch today's NBA games from The Odds API"""
    print("\n" + "="*60)
    print("🏀 SHARP PICKS DATA COLLECTOR")
    print("="*60 + "\n")
    
    if not API_KEY:
        print("❌ ERROR: No API key found!")
        print("\n📝 TO FIX:")
        print("   1. Click 🔒 'Secrets' icon on left")
        print("   2. Click 'New Secret'")
        print("   3. Key: ODDS_API_KEY")
        print("   4. Value: Your API key from the-odds-api.com")
        print("   5. Click 'Add'")
        print("   6. Click 'Run' again\n")
        return
    
    url = "https://api.the-odds-api.com/v4/sports/basketball_nba/odds/"
    params = {
        'apiKey': API_KEY,
        'regions': 'us',
        'markets': 'spreads,totals,h2h',
        'oddsFormat': 'american',
        'bookmakers': 'draftkings'
    }
    
    try:
        print("📡 Connecting to The Odds API...")
        response = requests.get(url, params=params)
        
        if response.status_code != 200:
            print(f"\n❌ API Error {response.status_code}")
            print(f"   {response.text}\n")
            return
        
        games = response.json()
        remaining = response.headers.get('x-requests-remaining', '?')
        
        print(f"✅ API Connected!")
        print(f"   Games found: {len(games)}")
        print(f"   API calls left: {remaining}/500\n")
        
        if len(games) == 0:
            print("ℹ️  No NBA games today (off-day)\n")
            show_stats()
            return
        
        # Store in database
        conn = sqlite3.connect('sharp_picks.db')
        cursor = conn.cursor()
        
        for game in games:
            game_id = game['id']
            home = game['home_team']
            away = game['away_team']
            commence_time = game['commence_time'][:10]
            
            # Extract odds
            spread_home = None
            spread_away = None
            total = None
            home_ml = None
            away_ml = None
            
            if game.get('bookmakers'):
                bookmaker = game['bookmakers'][0]
                
                for market in bookmaker.get('markets', []):
                    if market['key'] == 'spreads':
                        for outcome in market['outcomes']:
                            if outcome['name'] == home:
                                spread_home = outcome['point']
                            else:
                                spread_away = outcome['point']
                    
                    elif market['key'] == 'totals':
                        total = market['outcomes'][0]['point']
                    
                    elif market['key'] == 'h2h':
                        for outcome in market['outcomes']:
                            if outcome['name'] == home:
                                home_ml = outcome['price']
                            else:
                                away_ml = outcome['price']
            
            # Save to database (preserve existing score data if any)
            cursor.execute('''
                INSERT INTO games 
                (id, game_date, home_team, away_team, 
                 spread_home, spread_away, total, home_ml, away_ml, collected_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    spread_home = excluded.spread_home,
                    spread_away = excluded.spread_away,
                    total = excluded.total,
                    home_ml = excluded.home_ml,
                    away_ml = excluded.away_ml,
                    collected_at = excluded.collected_at
            ''', (
                game_id, commence_time, home, away,
                spread_home, spread_away, total, home_ml, away_ml,
                datetime.now().isoformat()
            ))
            
            # Display
            print(f"📊 {away} @ {home}")
            if spread_home:
                print(f"   Spread: {home} {spread_home:+.1f}")
            if total:
                print(f"   Total: {total}")
            print()
        
        conn.commit()
        conn.close()
        
        print("="*60)
        show_stats()
        
    except Exception as e:
        print(f"\n❌ Error: {e}\n")

def show_stats():
    """Display collection statistics"""
    conn = sqlite3.connect('sharp_picks.db')
    cursor = conn.cursor()
    
    cursor.execute('SELECT COUNT(*) FROM games')
    total = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM games WHERE home_score IS NOT NULL')
    with_scores = cursor.fetchone()[0]
    
    conn.close()
    
    print("\n📈 DATABASE STATS:")
    print(f"   Total games: {total}")
    print(f"   Games with scores: {with_scores}")
    
    if total < 50:
        progress = int((total / 50) * 30)
        bar = "█" * progress + "░" * (30 - progress)
        print(f"   Progress: [{bar}] {total}/50")
        print(f"   Need: {50 - total} more games\n")
    else:
        print("   ✅ Ready to train model!\n")
    
    print("="*60)

# Main execution
if __name__ == "__main__":
    setup_database()
    collect_yesterdays_scores()  # First, update yesterday's scores
    collect_todays_games()       # Then collect today's odds
    print("\n💡 Run daily to collect data!\n")
