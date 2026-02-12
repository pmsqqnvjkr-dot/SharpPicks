"""
🏀 THE RUNDOWN API INTEGRATION
Fetches NBA odds from The Rundown via RapidAPI
"""

import requests
import os
from datetime import datetime

RAPIDAPI_KEY = os.environ.get('RAPIDAPI_KEY')

SPORT_ID = 4  # NBA

TEAM_NAME_MAP = {
    'ATL': 'Atlanta Hawks',
    'BOS': 'Boston Celtics', 
    'BKN': 'Brooklyn Nets',
    'CHA': 'Charlotte Hornets',
    'CHI': 'Chicago Bulls',
    'CLE': 'Cleveland Cavaliers',
    'DAL': 'Dallas Mavericks',
    'DEN': 'Denver Nuggets',
    'DET': 'Detroit Pistons',
    'GSW': 'Golden State Warriors',
    'HOU': 'Houston Rockets',
    'IND': 'Indiana Pacers',
    'LAC': 'Los Angeles Clippers',
    'LAL': 'Los Angeles Lakers',
    'MEM': 'Memphis Grizzlies',
    'MIA': 'Miami Heat',
    'MIL': 'Milwaukee Bucks',
    'MIN': 'Minnesota Timberwolves',
    'NOP': 'New Orleans Pelicans',
    'NYK': 'New York Knicks',
    'OKC': 'Oklahoma City Thunder',
    'ORL': 'Orlando Magic',
    'PHI': 'Philadelphia 76ers',
    'PHX': 'Phoenix Suns',
    'POR': 'Portland Trail Blazers',
    'SAC': 'Sacramento Kings',
    'SAS': 'San Antonio Spurs',
    'TOR': 'Toronto Raptors',
    'UTA': 'Utah Jazz',
    'WAS': 'Washington Wizards',
}


def get_nba_events():
    """Fetch today's NBA events from The Rundown"""
    if not RAPIDAPI_KEY:
        print("   ⚠️ No RAPIDAPI_KEY found")
        return None
    
    today = datetime.now().strftime('%Y-%m-%d')
    
    headers = {
        "x-rapidapi-key": RAPIDAPI_KEY,
        "x-rapidapi-host": "therundown-therundown-v1.p.rapidapi.com"
    }
    
    try:
        response = requests.get(
            f"https://therundown-therundown-v1.p.rapidapi.com/sports/{SPORT_ID}/events/{today}",
            headers=headers,
            timeout=15
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            print(f"   ⚠️ Rundown API error: {response.status_code}")
            return None
            
    except Exception as e:
        print(f"   ⚠️ Rundown API exception: {e}")
        return None


def get_nba_odds():
    """Fetch NBA odds from The Rundown with line comparison"""
    if not RAPIDAPI_KEY:
        return None
    
    headers = {
        "x-rapidapi-key": RAPIDAPI_KEY,
        "x-rapidapi-host": "therundown-therundown-v1.p.rapidapi.com"
    }
    
    try:
        response = requests.get(
            f"https://therundown-therundown-v1.p.rapidapi.com/sports/{SPORT_ID}/odds",
            headers=headers,
            params={
                "include": "scores",
                "affiliate_ids": "1,2,3,4,6"  # DraftKings, FanDuel, BetMGM, Caesars, etc.
            },
            timeout=15
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            return None
            
    except Exception as e:
        print(f"   ⚠️ Error fetching odds: {e}")
        return None


def parse_rundown_games(data):
    """Parse Rundown API response into standardized format with multi-book consensus"""
    if not data:
        return []
    
    import statistics
    
    games = []
    events = data.get('events', [])
    
    for event in events:
        try:
            event_id = event.get('event_id', '')
            event_date = event.get('event_date', '')[:10]
            
            teams = event.get('teams_normalized', [])
            if len(teams) < 2:
                teams = event.get('teams', [])
            
            if len(teams) < 2:
                continue
            
            away_team = teams[0].get('name', '') if isinstance(teams[0], dict) else teams[0]
            home_team = teams[1].get('name', '') if isinstance(teams[1], dict) else teams[1]
            
            lines = event.get('lines', {})
            
            all_spreads = []
            all_totals = []
            spread_home = None
            total = None
            home_ml = None
            away_ml = None
            
            for book_id, book_lines in lines.items():
                if not book_lines:
                    continue
                    
                spread_data = book_lines.get('spread', {})
                if spread_data:
                    s = spread_data.get('point_spread_home')
                    if s is not None and abs(s) > 0.01 and abs(s) < 50:
                        all_spreads.append(s)
                        if spread_home is None:
                            spread_home = s
                
                total_data = book_lines.get('total', {})
                if total_data:
                    t = total_data.get('total_over')
                    if t is not None and t > 100 and t < 300:
                        all_totals.append(t)
                        if total is None:
                            total = t
                
                ml_data = book_lines.get('moneyline', {})
                if ml_data:
                    hm = ml_data.get('moneyline_home')
                    am = ml_data.get('moneyline_away')
                    if hm and abs(hm) > 1:
                        home_ml = hm
                        away_ml = am
            
            consensus_spread = None
            spread_std = None
            num_books = len(all_spreads)
            
            if all_spreads:
                consensus_spread = round(statistics.mean(all_spreads), 1)
                if len(all_spreads) >= 2:
                    spread_std = round(statistics.stdev(all_spreads), 2)
                else:
                    spread_std = 0.0
            
            games.append({
                'id': event_id,
                'game_date': event_date,
                'home_team': home_team,
                'away_team': away_team,
                'spread_home': spread_home or consensus_spread,
                'total': total,
                'home_ml': home_ml,
                'away_ml': away_ml,
                'consensus_spread': consensus_spread,
                'spread_std': spread_std,
                'num_books': num_books,
                'source': 'rundown'
            })
            
        except Exception as e:
            continue
    
    return games


def fetch_rundown_data():
    """Main function to fetch and parse Rundown data"""
    print("\n📡 Connecting to The Rundown API...")
    
    if not RAPIDAPI_KEY:
        print("   ❌ RAPIDAPI_KEY not configured")
        return []
    
    data = get_nba_events()
    
    if data:
        games = parse_rundown_games(data)
        print(f"   ✅ Rundown: Found {len(games)} games")
        return games
    else:
        print("   ⚠️ Rundown: No data available")
        return []


def test_connection():
    """Test The Rundown API connection"""
    print("\n" + "="*50)
    print("🔌 TESTING THE RUNDOWN API CONNECTION")
    print("="*50 + "\n")
    
    if not RAPIDAPI_KEY:
        print("❌ RAPIDAPI_KEY not found in environment")
        print("\nTo fix:")
        print("  1. Go to RapidAPI dashboard")
        print("  2. Copy your API key")
        print("  3. Add it as RAPIDAPI_KEY secret")
        return False
    
    print(f"✅ API Key found: {RAPIDAPI_KEY[:10]}...")
    
    headers = {
        "x-rapidapi-key": RAPIDAPI_KEY,
        "x-rapidapi-host": "therundown-therundown-v1.p.rapidapi.com"
    }
    
    today = datetime.now().strftime('%Y-%m-%d')
    
    try:
        response = requests.get(
            f"https://therundown-therundown-v1.p.rapidapi.com/sports/{SPORT_ID}/events/{today}",
            headers=headers,
            timeout=15
        )
        
        print(f"📊 Response status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            events = data.get('events', [])
            print(f"✅ Connection successful!")
            print(f"   Found {len(events)} NBA events")
            
            if events:
                print("\n📅 Today's games:")
                for event in events[:5]:
                    teams = event.get('teams_normalized', event.get('teams', []))
                    if len(teams) >= 2:
                        away = teams[0].get('name', teams[0]) if isinstance(teams[0], dict) else teams[0]
                        home = teams[1].get('name', teams[1]) if isinstance(teams[1], dict) else teams[1]
                        print(f"   🏀 {away} @ {home}")
            
            return True
        else:
            print(f"❌ API Error: {response.status_code}")
            print(f"   Response: {response.text[:200]}")
            return False
            
    except Exception as e:
        print(f"❌ Connection error: {e}")
        return False


if __name__ == '__main__':
    test_connection()
