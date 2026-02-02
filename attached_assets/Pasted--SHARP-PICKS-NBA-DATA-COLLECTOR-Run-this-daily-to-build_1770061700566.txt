"""
🏀 SHARP PICKS - NBA DATA COLLECTOR
Run this daily to build your dataset
"""

import requests
import sqlite3
import os
from datetime import datetime

# Get API key from Replit Secrets
API_KEY = os.environ.get('ODDS_API_KEY')

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
            collected_at TEXT
        )
    ''')
    
    conn.commit()
    conn.close()

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
        print("   4. Value: 7689606c3d61f0da7cebd6d8aa27f265")
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
            
            # Save to database
            cursor.execute('''
                INSERT OR REPLACE INTO games 
                (id, game_date, home_team, away_team, 
                 spread_home, spread_away, total, home_ml, away_ml, collected_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
    
    conn.close()
    
    print("\n📈 DATABASE STATS:")
    print(f"   Total games: {total}")
    
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
    collect_todays_games()
    print("\n💡 Run daily to collect data!\n")
