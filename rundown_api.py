"""
THE RUNDOWN API INTEGRATION
Fetches NBA and MLB odds from The Rundown via RapidAPI
"""

import requests
import os
import statistics
from datetime import datetime, timedelta, timezone

RAPIDAPI_KEY = os.environ.get('RAPIDAPI_KEY')


def _get_et_date_str():
    """Return today's date in Eastern Time (YYYY-MM-DD). Server may be UTC."""
    try:
        from zoneinfo import ZoneInfo
        return datetime.now(ZoneInfo("America/New_York")).strftime('%Y-%m-%d')
    except ImportError:
        return (datetime.now(timezone.utc) - timedelta(hours=5)).strftime('%Y-%m-%d')

_rundown_session = None

def _get_rundown_session():
    global _rundown_session
    if _rundown_session is None:
        _rundown_session = requests.Session()
        _rundown_session.headers.update({
            "x-rapidapi-key": RAPIDAPI_KEY or "",
            "x-rapidapi-host": "therundown-therundown-v1.p.rapidapi.com"
        })
    return _rundown_session

NBA_SPORT_ID = 4
MLB_SPORT_ID = 3
SPORT_ID = NBA_SPORT_ID

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

RUNDOWN_NAME_FIX = {
    'LA': 'Los Angeles Clippers',
    'Los Angeles': 'Los Angeles Lakers',
    'LA Clippers': 'Los Angeles Clippers',
    'LA Lakers': 'Los Angeles Lakers',
    'New York': 'New York Knicks',
    'Golden State': 'Golden State Warriors',
    'Oklahoma City': 'Oklahoma City Thunder',
    'San Antonio': 'San Antonio Spurs',
    'New Orleans': 'New Orleans Pelicans',
    'Portland': 'Portland Trail Blazers',
}

def normalize_team_name(name):
    if name in RUNDOWN_NAME_FIX:
        return RUNDOWN_NAME_FIX[name]
    for full_name in TEAM_NAME_MAP.values():
        if name in full_name or full_name.startswith(name):
            return full_name
    return name


def get_nba_events():
    """Fetch today's NBA events from The Rundown"""
    if not RAPIDAPI_KEY:
        print("   ⚠️ No RAPIDAPI_KEY found")
        return None
    
    today = _get_et_date_str()
    
    try:
        response = _get_rundown_session().get(
            f"https://therundown-therundown-v1.p.rapidapi.com/sports/{SPORT_ID}/events/{today}",
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
    
    try:
        response = _get_rundown_session().get(
            f"https://therundown-therundown-v1.p.rapidapi.com/sports/{SPORT_ID}/odds",
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
            
            away_team = normalize_team_name(teams[0].get('name', '') if isinstance(teams[0], dict) else teams[0])
            home_team = normalize_team_name(teams[1].get('name', '') if isinstance(teams[1], dict) else teams[1])
            
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


MLB_TEAM_NAME_MAP = {
    'Arizona Diamondbacks': 'Arizona Diamondbacks',
    'Atlanta Braves': 'Atlanta Braves',
    'Baltimore Orioles': 'Baltimore Orioles',
    'Boston Red Sox': 'Boston Red Sox',
    'Chicago Cubs': 'Chicago Cubs',
    'Chicago White Sox': 'Chicago White Sox',
    'Cincinnati Reds': 'Cincinnati Reds',
    'Cleveland Guardians': 'Cleveland Guardians',
    'Colorado Rockies': 'Colorado Rockies',
    'Detroit Tigers': 'Detroit Tigers',
    'Houston Astros': 'Houston Astros',
    'Kansas City Royals': 'Kansas City Royals',
    'Los Angeles Angels': 'Los Angeles Angels',
    'Los Angeles Dodgers': 'Los Angeles Dodgers',
    'Miami Marlins': 'Miami Marlins',
    'Milwaukee Brewers': 'Milwaukee Brewers',
    'Minnesota Twins': 'Minnesota Twins',
    'New York Mets': 'New York Mets',
    'New York Yankees': 'New York Yankees',
    'Oakland Athletics': 'Oakland Athletics',
    'Philadelphia Phillies': 'Philadelphia Phillies',
    'Pittsburgh Pirates': 'Pittsburgh Pirates',
    'San Diego Padres': 'San Diego Padres',
    'San Francisco Giants': 'San Francisco Giants',
    'Seattle Mariners': 'Seattle Mariners',
    'St. Louis Cardinals': 'St. Louis Cardinals',
    'Tampa Bay Rays': 'Tampa Bay Rays',
    'Texas Rangers': 'Texas Rangers',
    'Toronto Blue Jays': 'Toronto Blue Jays',
    'Washington Nationals': 'Washington Nationals',
}

MLB_RUNDOWN_NAME_FIX = {
    'Arizona': 'Arizona Diamondbacks',
    'Atlanta': 'Atlanta Braves',
    'Baltimore': 'Baltimore Orioles',
    'Boston': 'Boston Red Sox',
    'Chi Cubs': 'Chicago Cubs',
    'Chi Sox': 'Chicago White Sox',
    'Chicago': 'Chicago Cubs',
    'Cincinnati': 'Cincinnati Reds',
    'Cleveland': 'Cleveland Guardians',
    'Colorado': 'Colorado Rockies',
    'Detroit': 'Detroit Tigers',
    'Houston': 'Houston Astros',
    'Kansas City': 'Kansas City Royals',
    'LA Angels': 'Los Angeles Angels',
    'LA Dodgers': 'Los Angeles Dodgers',
    'Miami': 'Miami Marlins',
    'Milwaukee': 'Milwaukee Brewers',
    'Minnesota': 'Minnesota Twins',
    'NY Mets': 'New York Mets',
    'NY Yankees': 'New York Yankees',
    'Oakland': 'Oakland Athletics',
    'Philadelphia': 'Philadelphia Phillies',
    'Pittsburgh': 'Pittsburgh Pirates',
    'San Diego': 'San Diego Padres',
    'San Francisco': 'San Francisco Giants',
    'St Louis': 'St. Louis Cardinals',
    'St. Louis': 'St. Louis Cardinals',
    'Tampa Bay': 'Tampa Bay Rays',
    'Texas': 'Texas Rangers',
    'Toronto': 'Toronto Blue Jays',
    'Washington': 'Washington Nationals',
}


def normalize_mlb_team_name(name):
    """Normalize Rundown MLB team name to full canonical name."""
    if name in MLB_RUNDOWN_NAME_FIX:
        return MLB_RUNDOWN_NAME_FIX[name]
    if name in MLB_TEAM_NAME_MAP:
        return name
    for full_name in MLB_TEAM_NAME_MAP.values():
        if name in full_name or full_name.startswith(name):
            return full_name
    return name


def get_mlb_events(date_str=None):
    """Fetch MLB events from The Rundown for a given date."""
    if not RAPIDAPI_KEY:
        print("   No RAPIDAPI_KEY found")
        return None

    if date_str is None:
        date_str = _get_et_date_str()

    try:
        response = _get_rundown_session().get(
            f"https://therundown-therundown-v1.p.rapidapi.com/sports/{MLB_SPORT_ID}/events/{date_str}",
            timeout=15
        )
        if response.status_code == 200:
            return response.json()
        else:
            print(f"   Rundown MLB API error: {response.status_code}")
            return None
    except Exception as e:
        print(f"   Rundown MLB API exception: {e}")
        return None


def parse_rundown_mlb_games(data):
    """Parse Rundown API MLB response into standardized format with multi-book consensus."""
    if not data:
        return []

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

            away_team = normalize_mlb_team_name(
                teams[0].get('name', '') if isinstance(teams[0], dict) else teams[0]
            )
            home_team = normalize_mlb_team_name(
                teams[1].get('name', '') if isinstance(teams[1], dict) else teams[1]
            )

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
                    if s is not None and abs(s) > 0.01 and abs(s) < 10:
                        all_spreads.append(s)
                        if spread_home is None:
                            spread_home = s

                total_data = book_lines.get('total', {})
                if total_data:
                    t = total_data.get('total_over')
                    if t is not None and 3 < t < 20:
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
                spread_std = round(statistics.stdev(all_spreads), 2) if len(all_spreads) >= 2 else 0.0

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

        except Exception:
            continue

    return games


def fetch_rundown_mlb_data(date_str=None):
    """Fetch and parse Rundown MLB data for a given date."""
    if not RAPIDAPI_KEY:
        return []

    data = get_mlb_events(date_str)
    if data:
        games = parse_rundown_mlb_games(data)
        return games
    return []


def test_connection():
    """Test The Rundown API connection"""
    print("\n" + "="*50)
    print("TESTING THE RUNDOWN API CONNECTION")
    print("="*50 + "\n")

    if not RAPIDAPI_KEY:
        print("RAPIDAPI_KEY not found in environment")
        return False

    print(f"API Key found: {RAPIDAPI_KEY[:10]}...")

    today = _get_et_date_str()

    try:
        response = _get_rundown_session().get(
            f"https://therundown-therundown-v1.p.rapidapi.com/sports/{SPORT_ID}/events/{today}",
            timeout=15
        )

        print(f"Response status: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            events = data.get('events', [])
            print(f"Connection successful! Found {len(events)} NBA events")
            return True
        else:
            print(f"API Error: {response.status_code}")
            return False

    except Exception as e:
        print(f"Connection error: {e}")
        return False


if __name__ == '__main__':
    test_connection()
