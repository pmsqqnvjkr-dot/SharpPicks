"""
SHARP PICKS - HISTORICAL DATA IMPORTER
Fetches past NBA games to speed up model training
"""

import sqlite3
import requests
from datetime import datetime, timedelta
import time
import os

API_KEY = os.environ.get('ODDS_API_KEY')
BASE_URL = "https://api.the-odds-api.com/v4"

def get_db():
    conn = sqlite3.connect('sharp_picks.db')
    conn.row_factory = sqlite3.Row
    return conn

def fetch_historical_scores(days_back=14):
    """Fetch completed games from the past N days"""
    print(f"\n{'='*60}")
    print(f"📜 IMPORTING HISTORICAL NBA DATA")
    print(f"{'='*60}")
    print(f"Fetching games from the past {days_back} days...\n")
    
    if not API_KEY:
        print("❌ ODDS_API_KEY not found in environment!")
        return 0
    
    conn = get_db()
    cursor = conn.cursor()
    games_added = 0
    
    url = f"{BASE_URL}/sports/basketball_nba/scores"
    params = {
        'apiKey': API_KEY,
        'daysFrom': days_back,
        'dateFormat': 'iso'
    }
    
    try:
        response = requests.get(url, params=params, timeout=30)
        
        if response.status_code != 200:
            print(f"❌ API Error: {response.status_code}")
            return 0
        
        remaining = response.headers.get('x-requests-remaining', '?')
        print(f"📡 API calls remaining: {remaining}")
        
        games = response.json()
        completed = [g for g in games if g.get('completed')]
        
        print(f"✅ Found {len(completed)} completed games\n")
        
        for game in completed:
            game_id = game['id']
            home = game['home_team']
            away = game['away_team']
            game_date = game['commence_time'][:10]
            
            scores = game.get('scores', [])
            home_score = away_score = None
            for s in scores:
                if s['name'] == home:
                    home_score = int(s['score'])
                elif s['name'] == away:
                    away_score = int(s['score'])
            
            if home_score is None or away_score is None:
                continue
            
            cursor.execute('SELECT id FROM games WHERE id = ?', (game_id,))
            if cursor.fetchone():
                cursor.execute('''
                    UPDATE games SET home_score = ?, away_score = ?, spread_result = ?
                    WHERE id = ?
                ''', (home_score, away_score, 'completed', game_id))
                print(f"   📝 Updated: {away} @ {home} ({away_score}-{home_score})")
            else:
                cursor.execute('''
                    INSERT INTO games (id, home_team, away_team, game_date, 
                                      home_score, away_score, spread_result)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (game_id, home, away, game_date, home_score, away_score, 'completed'))
                games_added += 1
                print(f"   ✅ Added: {away} @ {home} ({away_score}-{home_score})")
        
        conn.commit()
        conn.close()
        
        print(f"\n{'='*60}")
        print(f"📊 IMPORT COMPLETE")
        print(f"   New games added: {games_added}")
        print(f"{'='*60}\n")
        
        return games_added
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return 0

def fetch_espn_historical(days_back=30):
    """Fetch historical data from ESPN (free, no API key needed)"""
    print(f"\n{'='*60}")
    print(f"📜 IMPORTING FROM ESPN (FREE)")
    print(f"{'='*60}")
    print(f"Fetching games from the past {days_back} days...\n")
    
    conn = get_db()
    cursor = conn.cursor()
    games_added = 0
    
    for day_offset in range(1, days_back + 1):
        date = datetime.now() - timedelta(days=day_offset)
        date_str = date.strftime('%Y%m%d')
        
        url = f"https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard"
        params = {'dates': date_str}
        
        try:
            response = requests.get(url, params=params, timeout=10)
            if response.status_code != 200:
                continue
            
            data = response.json()
            events = data.get('events', [])
            
            for event in events:
                game_id = f"espn_{event['id']}"
                game_date = date.strftime('%Y-%m-%d')
                
                competition = event.get('competitions', [{}])[0]
                competitors = competition.get('competitors', [])
                if len(competitors) != 2:
                    continue
                
                home = away = None
                home_score = away_score = None
                
                for team in competitors:
                    team_name = team.get('team', {}).get('displayName', '')
                    score_str = team.get('score', '0')
                    try:
                        score = int(score_str) if score_str else 0
                    except:
                        score = 0
                    
                    if team.get('homeAway') == 'home':
                        home = team_name
                        home_score = score
                    else:
                        away = team_name
                        away_score = score
                
                if not home or not away:
                    continue
                
                if home_score == 0 and away_score == 0:
                    continue
                
                status_type = event.get('status', {}).get('type', {})
                is_completed = status_type.get('completed', False)
                
                if not is_completed:
                    continue
                
                cursor.execute('SELECT id FROM games WHERE id = ?', (game_id,))
                if cursor.fetchone():
                    continue
                
                cursor.execute('''
                    INSERT INTO games (id, home_team, away_team, game_date,
                                      home_score, away_score, spread_result)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (game_id, home, away, game_date, home_score, away_score, 'completed'))
                games_added += 1
                print(f"   ✅ {game_date}: {away} @ {home} ({away_score}-{home_score})")
            
            time.sleep(0.2)
            
        except Exception as e:
            print(f"   ⚠️ Error on {date_str}: {e}")
            continue
    
    conn.commit()
    conn.close()
    
    print(f"\n{'='*60}")
    print(f"📊 ESPN IMPORT COMPLETE")
    print(f"   New games added: {games_added}")
    print(f"{'='*60}\n")
    
    return games_added

def show_status():
    """Show current database status"""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('SELECT COUNT(*) FROM games')
    total = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM games WHERE spread_result IS NOT NULL')
    with_results = cursor.fetchone()[0]
    
    conn.close()
    
    print(f"\n📊 DATABASE STATUS")
    print(f"   Total games: {total}")
    print(f"   With results: {with_results}")
    print(f"   Progress: {with_results}/50 ({with_results/50*100:.0f}%)")
    
    if with_results >= 50:
        print(f"\n🎉 READY TO TRAIN MODEL!")
        print(f"   Run: python model.py train")
    else:
        print(f"\n   Need {50 - with_results} more games with results")

def main():
    print("\n🏀 SHARP PICKS - HISTORICAL DATA IMPORTER")
    print("="*50)
    print("1. ESPN (Free, no API key)")
    print("2. The Odds API (uses API calls)")
    print("="*50)
    
    added = fetch_espn_historical(days_back=30)
    
    if added < 30 and API_KEY:
        print("\nAlso checking The Odds API...")
        fetch_historical_scores(days_back=14)
    
    show_status()

if __name__ == "__main__":
    main()
