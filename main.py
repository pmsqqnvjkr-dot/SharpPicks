"""
🏀 SHARP PICKS - NBA DATA COLLECTOR
Run this daily to build your dataset
"""

import requests
import sqlite3
import os
from db_path import get_sqlite_path
import time
import random
import statistics
from datetime import datetime, timedelta, timezone

def utc_to_eastern_date(utc_str):
    """Convert UTC ISO timestamp to Eastern Time date string (YYYY-MM-DD)."""
    try:
        utc_str = utc_str.replace('Z', '+00:00')
        utc_dt = datetime.fromisoformat(utc_str)
        if utc_dt.tzinfo is None:
            utc_dt = utc_dt.replace(tzinfo=timezone.utc)
        eastern_offset = timedelta(hours=-5)
        try:
            import zoneinfo
            eastern = zoneinfo.ZoneInfo("America/New_York")
            et_dt = utc_dt.astimezone(eastern)
        except ImportError:
            et_dt = utc_dt + eastern_offset
        return et_dt.strftime('%Y-%m-%d')
    except Exception:
        return utc_str[:10]

# Get API key from Replit Secrets
API_KEY = os.environ.get('ODDS_API_KEY')

# API usage tracking
API_USAGE = {'remaining': 500, 'used': 0}


def api_request_with_retry(url, params, max_retries=3):
    """Make API request with retry logic and usage tracking"""
    global API_USAGE
    
    for attempt in range(max_retries):
        try:
            response = requests.get(url, params=params, timeout=30)
            
            # Track API usage from headers
            remaining = response.headers.get('x-requests-remaining')
            used = response.headers.get('x-requests-used')
            
            if remaining:
                API_USAGE['remaining'] = int(remaining)
            if used:
                API_USAGE['used'] = int(used)
            
            # Check for rate limiting
            if response.status_code == 429:
                wait_time = (attempt + 1) * 5
                print(f"   ⏳ Rate limited. Waiting {wait_time}s... (attempt {attempt + 1}/{max_retries})")
                time.sleep(wait_time)
                continue
            
            # Success
            if response.status_code == 200:
                return response
            
            # Other errors
            if response.status_code >= 500:
                wait_time = (attempt + 1) * 2
                print(f"   ⚠️ Server error {response.status_code}. Retrying in {wait_time}s... (attempt {attempt + 1}/{max_retries})")
                time.sleep(wait_time)
                continue
            
            # Client error - don't retry
            return response
            
        except requests.exceptions.Timeout:
            wait_time = (attempt + 1) * 2
            print(f"   ⏱️ Request timeout. Retrying in {wait_time}s... (attempt {attempt + 1}/{max_retries})")
            time.sleep(wait_time)
            
        except requests.exceptions.ConnectionError:
            wait_time = (attempt + 1) * 3
            print(f"   🔌 Connection error. Retrying in {wait_time}s... (attempt {attempt + 1}/{max_retries})")
            time.sleep(wait_time)
            
        except Exception as e:
            print(f"   ❌ Unexpected error: {e}")
            if attempt < max_retries - 1:
                time.sleep(2)
    
    return None


def check_api_usage():
    """Check and warn about API usage"""
    remaining = API_USAGE['remaining']
    used = API_USAGE['used']
    
    if remaining <= 50:
        print("\n" + "!"*50)
        print(f"🚨 CRITICAL: Only {remaining} API calls remaining!")
        print("   Your monthly limit resets on the 1st.")
        print("   Consider pausing collection to save calls.")
        print("!"*50 + "\n")
    elif remaining <= 100:
        print(f"\n⚠️ WARNING: {remaining} API calls remaining (approaching limit)")
    elif remaining <= 200:
        print(f"\n📊 API Usage: {used}/500 used, {remaining} remaining")


def show_no_games_message():
    """Show encouraging message when no games today"""
    messages = [
        "🌴 No NBA games today - enjoy the break!",
        "📺 Off-day! Perfect time to review your data.",
        "☕ No games scheduled. Your streak continues tomorrow!",
        "🏖️ Rest day for the NBA. Check back tomorrow!",
        "📊 No games today, but your model keeps learning!",
    ]
    
    print(f"\n{random.choice(messages)}")
    print("\n💡 While you wait, try:")
    print("   python main.py --report - View your collection stats")
    print("   python main.py --viz    - See progress visualization")
    print("   python model.py train   - Train model (if 50+ games)\n")

# Team name mapping (Odds API -> ESPN abbreviation)
TEAM_ABBR_MAP = {
    'Atlanta Hawks': 'ATL',
    'Boston Celtics': 'BOS',
    'Brooklyn Nets': 'BKN',
    'Charlotte Hornets': 'CHA',
    'Chicago Bulls': 'CHI',
    'Cleveland Cavaliers': 'CLE',
    'Dallas Mavericks': 'DAL',
    'Denver Nuggets': 'DEN',
    'Detroit Pistons': 'DET',
    'Golden State Warriors': 'GS',
    'Houston Rockets': 'HOU',
    'Indiana Pacers': 'IND',
    'Los Angeles Clippers': 'LAC',
    'Los Angeles Lakers': 'LAL',
    'Memphis Grizzlies': 'MEM',
    'Miami Heat': 'MIA',
    'Milwaukee Bucks': 'MIL',
    'Minnesota Timberwolves': 'MIN',
    'New Orleans Pelicans': 'NO',
    'New York Knicks': 'NYK',
    'Oklahoma City Thunder': 'OKC',
    'Orlando Magic': 'ORL',
    'Philadelphia 76ers': 'PHI',
    'Phoenix Suns': 'PHX',
    'Portland Trail Blazers': 'POR',
    'Sacramento Kings': 'SAC',
    'San Antonio Spurs': 'SA',
    'Toronto Raptors': 'TOR',
    'Utah Jazz': 'UTA',
    'Washington Wizards': 'WAS',
}

WNBA_TEAM_ABBR_MAP = {
    'Atlanta Dream': 'ATL',
    'Chicago Sky': 'CHI',
    'Connecticut Sun': 'CON',
    'Dallas Wings': 'DAL',
    'Indiana Fever': 'IND',
    'Las Vegas Aces': 'LVA',
    'Los Angeles Sparks': 'LAS',
    'Minnesota Lynx': 'MIN',
    'New York Liberty': 'NYL',
    'Phoenix Mercury': 'PHO',
    'Seattle Storm': 'SEA',
    'Washington Mystics': 'WAS',
    'Golden State Valkyries': 'GSV',
}

def setup_database():
    """Create database if it doesn't exist"""
    conn = sqlite3.connect(get_sqlite_path())
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS games (
            id TEXT PRIMARY KEY,
            game_date TEXT,
            game_time TEXT,
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
            scores_updated_at TEXT,
            home_record TEXT,
            away_record TEXT,
            home_home_record TEXT,
            away_away_record TEXT,
            home_last5 TEXT,
            away_last5 TEXT,
            home_rest_days INTEGER,
            away_rest_days INTEGER,
            home_injuries TEXT,
            away_injuries TEXT,
            spread_home_open REAL,
            total_open REAL,
            home_ml_open INTEGER,
            away_ml_open INTEGER,
            open_collected_at TEXT,
            spread_home_close REAL,
            total_close REAL,
            home_ml_close INTEGER,
            away_ml_close INTEGER,
            close_collected_at TEXT,
            line_movement REAL
        )
    ''')
    
    # Add new columns if they don't exist
    new_columns = [
        ('game_time', 'TEXT'),
        ('home_score', 'INTEGER'),
        ('away_score', 'INTEGER'),
        ('spread_result', 'TEXT'),
        ('total_result', 'TEXT'),
        ('scores_updated_at', 'TEXT'),
        ('home_record', 'TEXT'),
        ('away_record', 'TEXT'),
        ('home_home_record', 'TEXT'),
        ('away_away_record', 'TEXT'),
        ('home_last5', 'TEXT'),
        ('away_last5', 'TEXT'),
        ('home_rest_days', 'INTEGER'),
        ('away_rest_days', 'INTEGER'),
        ('home_injuries', 'TEXT'),
        ('away_injuries', 'TEXT'),
        ('spread_home_open', 'REAL'),
        ('total_open', 'REAL'),
        ('home_ml_open', 'INTEGER'),
        ('away_ml_open', 'INTEGER'),
        ('open_collected_at', 'TEXT'),
        ('spread_home_close', 'REAL'),
        ('total_close', 'REAL'),
        ('home_ml_close', 'INTEGER'),
        ('away_ml_close', 'INTEGER'),
        ('close_collected_at', 'TEXT'),
        ('line_movement', 'REAL'),
        ('rundown_spread_consensus', 'REAL'),
        ('rundown_spread_std', 'REAL'),
        ('rundown_spread_range', 'REAL'),
        ('rundown_best_book', 'TEXT'),
        ('rundown_num_books', 'INTEGER'),
        ('bdl_home_win_pct', 'REAL'),
        ('bdl_away_win_pct', 'REAL'),
        ('bdl_home_conf_rank', 'INTEGER'),
        ('bdl_away_conf_rank', 'INTEGER'),
        ('bdl_home_scoring_margin', 'REAL'),
        ('bdl_away_scoring_margin', 'REAL'),
        ('bdl_home_avg_pts', 'REAL'),
        ('bdl_away_avg_pts', 'REAL'),
        ('bdl_home_avg_pts_against', 'REAL'),
        ('bdl_away_avg_pts_against', 'REAL'),
        ('home_spread_odds', 'INTEGER'),
        ('away_spread_odds', 'INTEGER'),
        ('home_spread_odds_open', 'INTEGER'),
        ('away_spread_odds_open', 'INTEGER'),
        ('home_spread_odds_close', 'INTEGER'),
        ('away_spread_odds_close', 'INTEGER'),
        ('home_spread_book', 'TEXT'),
        ('away_spread_book', 'TEXT'),
        ('spread_h1_home', 'REAL'),
        ('spread_h1_away', 'REAL'),
        ('spread_h1_home_odds', 'INTEGER'),
        ('spread_h1_away_odds', 'INTEGER'),
        ('total_h1', 'REAL'),
        ('spread_h1_home_open', 'REAL'),
        ('total_h1_open', 'REAL'),
        ('alt_spread_minus_1', 'INTEGER'),
        ('alt_spread_minus_3', 'INTEGER'),
        ('alt_spread_minus_5', 'INTEGER'),
        ('alt_spread_minus_7', 'INTEGER'),
        ('alt_spread_plus_1', 'INTEGER'),
        ('alt_spread_plus_3', 'INTEGER'),
        ('alt_spread_plus_5', 'INTEGER'),
        ('alt_spread_plus_7', 'INTEGER'),
        ('commence_time', 'TEXT'),
        ('spread_h1_home_close', 'REAL'),
        ('total_h1_close', 'REAL'),
    ]
    
    for col_name, col_type in new_columns:
        try:
            cursor.execute(f'ALTER TABLE games ADD COLUMN {col_name} {col_type}')
        except:
            pass

    cursor.execute("UPDATE games SET game_time = NULL WHERE game_time = ''")

    cursor.execute('''CREATE TABLE IF NOT EXISTS nba_player_props (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        game_id TEXT NOT NULL,
        game_date TEXT,
        player_name TEXT NOT NULL,
        team TEXT,
        market TEXT NOT NULL,
        line REAL,
        over_odds INTEGER,
        under_odds INTEGER,
        book TEXT,
        collected_at TEXT,
        UNIQUE(game_id, player_name, market, book)
    )''')

    conn.commit()
    conn.close()


def get_team_data():
    """Fetch team records, home/away splits from ESPN team endpoints"""
    print("📊 Fetching team records...")
    
    team_data = {}
    
    for team_name, abbr in TEAM_ABBR_MAP.items():
        try:
            url = f"https://site.api.espn.com/apis/site/v2/sports/basketball/nba/teams/{abbr.lower()}"
            response = requests.get(url, timeout=5)
            
            if response.status_code != 200:
                continue
            
            data = response.json()
            team = data.get('team', {})
            records = team.get('record', {}).get('items', [])
            
            record = 'N/A'
            home_record = 'N/A'
            away_record = 'N/A'
            
            for item in records:
                rec_type = item.get('type', '')
                summary = item.get('summary', '')
                
                if rec_type == 'total':
                    record = summary
                elif rec_type == 'home':
                    home_record = summary
                elif rec_type == 'road':
                    away_record = summary
            
            team_data[team_name] = {
                'record': record,
                'home_record': home_record,
                'away_record': away_record,
            }
            
        except Exception:
            continue
    
    print(f"   ✅ Loaded records for {len(team_data)} teams")
    
    return team_data


def get_wnba_team_data():
    """Fetch WNBA team records, home/away splits from ESPN team endpoints"""
    from sport_config import get_sport_config
    cfg = get_sport_config('wnba')
    print("📊 Fetching WNBA team records...")

    team_data = {}

    for team_name, abbr in WNBA_TEAM_ABBR_MAP.items():
        try:
            url = f"{cfg['espn_teams']}/{abbr.lower()}"
            response = requests.get(url, timeout=5)

            if response.status_code != 200:
                continue

            data = response.json()
            team = data.get('team', {})
            records = team.get('record', {}).get('items', [])

            record = 'N/A'
            home_record = 'N/A'
            away_record = 'N/A'

            for item in records:
                rec_type = item.get('type', '')
                summary = item.get('summary', '')

                if rec_type == 'total':
                    record = summary
                elif rec_type == 'home':
                    home_record = summary
                elif rec_type == 'road':
                    away_record = summary

            team_data[team_name] = {
                'record': record,
                'home_record': home_record,
                'away_record': away_record,
            }

        except Exception:
            continue

    print(f"   ✅ Loaded records for {len(team_data)} WNBA teams")

    return team_data


def get_wnba_team_schedule(team_abbr):
    """Get WNBA team's recent games for form and rest days calculation"""
    from sport_config import get_sport_config
    cfg = get_sport_config('wnba')
    try:
        url = f"{cfg['espn_teams']}/{team_abbr}/schedule"
        response = requests.get(url, timeout=10)

        if response.status_code != 200:
            return None, None

        data = response.json()
        events = data.get('events', [])

        completed_games = []

        for event in events:
            status = event.get('competitions', [{}])[0].get('status', {}).get('type', {}).get('name', '')
            if status == 'STATUS_FINAL':
                game_date = event.get('date', '')[:10]

                competitions = event.get('competitions', [{}])[0]
                competitors = competitions.get('competitors', [])

                won = False
                for comp in competitors:
                    if comp.get('team', {}).get('abbreviation', '').upper() == team_abbr.upper():
                        won = comp.get('winner', False)
                        break

                completed_games.append({
                    'date': game_date,
                    'won': won
                })

        completed_games.sort(key=lambda x: x['date'], reverse=True)

        last5 = ""
        last_game_date = None
        if completed_games:
            for game in completed_games[:5]:
                last5 += "W" if game['won'] else "L"
            last_game_date = completed_games[0]['date']

        return last5, last_game_date

    except Exception:
        return None, None


def get_team_schedule(team_abbr):
    """Get team's recent games for form and rest days calculation"""
    try:
        url = f"https://site.api.espn.com/apis/site/v2/sports/basketball/nba/teams/{team_abbr}/schedule"
        response = requests.get(url, timeout=10)
        
        if response.status_code != 200:
            return None, None
        
        data = response.json()
        events = data.get('events', [])
        
        # Find completed games and sort by date
        completed_games = []
        last_game_date = None
        
        for event in events:
            status = event.get('competitions', [{}])[0].get('status', {}).get('type', {}).get('name', '')
            if status == 'STATUS_FINAL':
                game_date = event.get('date', '')[:10]
                
                # Determine if team won
                competitions = event.get('competitions', [{}])[0]
                competitors = competitions.get('competitors', [])
                
                won = False
                for comp in competitors:
                    if comp.get('team', {}).get('abbreviation', '').upper() == team_abbr.upper():
                        won = comp.get('winner', False)
                        break
                
                completed_games.append({
                    'date': game_date,
                    'won': won
                })
        
        # Sort by date descending
        completed_games.sort(key=lambda x: x['date'], reverse=True)
        
        # Last 5 form (e.g., "WWLWL")
        last5 = ""
        if completed_games:
            for game in completed_games[:5]:
                last5 += "W" if game['won'] else "L"
            last_game_date = completed_games[0]['date']
        
        return last5, last_game_date
        
    except Exception as e:
        return None, None


def calculate_rest_days(last_game_date):
    """Calculate days of rest before today's game"""
    if not last_game_date:
        return None
    
    try:
        last_date = datetime.strptime(last_game_date, '%Y-%m-%d')
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        days_diff = (today - last_date).days
        # Rest days = days since last game - 1 (game day doesn't count as rest)
        # Minimum is 0 (back-to-back)
        return max(0, days_diff - 1)
    except:
        return None


def get_injuries():
    """Fetch injury reports from ESPN"""
    print("🏥 Fetching injury reports...")
    
    injuries = {}
    
    try:
        url = "https://site.api.espn.com/apis/site/v2/sports/basketball/nba/injuries"
        response = requests.get(url, timeout=15)
        
        if response.status_code != 200:
            print(f"   ⚠️ Injuries API error: {response.status_code}")
            return injuries
        
        data = response.json()
        
        for team_data in data.get('injuries', []):
            team_name = team_data.get('team', {}).get('displayName', '')
            
            team_injuries = []
            for injury in team_data.get('injuries', []):
                player = injury.get('athlete', {}).get('displayName', 'Unknown')
                status = injury.get('status', 'Unknown')
                injury_type = injury.get('type', {}).get('description', '')
                
                # Only include significant injuries (Out, Doubtful, Questionable)
                if status.lower() in ['out', 'doubtful', 'questionable', 'day-to-day']:
                    team_injuries.append(f"{player} ({status})")
            
            if team_injuries:
                injuries[team_name] = "; ".join(team_injuries[:5])  # Top 5 injuries
        
        print(f"   ✅ Loaded injuries for {len(injuries)} teams")
        
    except Exception as e:
        print(f"   ⚠️ Injuries error: {e}")
    
    return injuries


def get_wnba_injuries():
    """Fetch WNBA injury reports from ESPN"""
    from sport_config import get_sport_config
    cfg = get_sport_config('wnba')
    print("🏥 Fetching WNBA injury reports...")

    injuries = {}

    try:
        url = cfg['espn_injuries']
        response = requests.get(url, timeout=15)

        if response.status_code != 200:
            print(f"   ⚠️ WNBA Injuries API error: {response.status_code}")
            return injuries

        data = response.json()

        for team_data in data.get('injuries', []):
            team_name = team_data.get('team', {}).get('displayName', '')

            team_injuries = []
            for injury in team_data.get('injuries', []):
                player = injury.get('athlete', {}).get('displayName', 'Unknown')
                status = injury.get('status', 'Unknown')
                injury_type = injury.get('type', {}).get('description', '')

                if status.lower() in ['out', 'doubtful', 'questionable', 'day-to-day']:
                    team_injuries.append(f"{player} ({status})")

            if team_injuries:
                injuries[team_name] = "; ".join(team_injuries[:5])

        print(f"   ✅ Loaded WNBA injuries for {len(injuries)} teams")

    except Exception as e:
        print(f"   ⚠️ WNBA Injuries error: {e}")

    return injuries


def collect_yesterdays_scores():
    """Fetch yesterday's final scores from ESPN API"""
    print("\n" + "="*60)
    print("📊 COLLECTING YESTERDAY'S FINAL SCORES")
    print("="*60 + "\n")
    
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
        
        conn = sqlite3.connect(get_sqlite_path())
        cursor = conn.cursor()
        
        updated_count = 0
        
        for event in events:
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
            
            # Use ESPN event's actual date — never match yesterday's scores to today's games
            espn_date_str = event.get('date', '')[:10]  # e.g. 2026-03-01 from 2026-03-01T00:00Z
            if not espn_date_str or len(espn_date_str) < 10:
                continue
            try_date = espn_date_str[:10]  # YYYY-MM-DD
            
            game = None
            cursor.execute('''
                SELECT id, spread_home, total FROM games 
                WHERE game_date = ? 
                AND (home_team LIKE ? OR home_team LIKE ?)
                AND home_score IS NULL
            ''', (try_date, f'%{home_team.split()[-1]}%', f'%{home_team}%'))
            game = cursor.fetchone()
            
            if game:
                game_id, spread_home, total = game
                
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
                
                total_result = None
                actual_total = home_score + away_score
                if total is not None:
                    if actual_total > total:
                        total_result = 'OVER'
                    elif actual_total < total:
                        total_result = 'UNDER'
                    else:
                        total_result = 'PUSH'
                
                cursor.execute('''
                    UPDATE games 
                    SET home_score = ?, away_score = ?, 
                        spread_result = ?, total_result = ?,
                        scores_updated_at = ?
                    WHERE id = ?
                ''', (home_score, away_score, spread_result, total_result, 
                      datetime.now().isoformat(), game_id))
                
                updated_count += 1
                
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
        
        show_spread_stats()
        
    except Exception as e:
        print(f"\n❌ Error: {e}\n")


def show_spread_stats():
    """Show spread hit/miss statistics"""
    conn = sqlite3.connect(get_sqlite_path())
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
    """Fetch today's NBA games with enhanced data"""
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
    
    # Fetch supplementary data
    team_data = get_team_data()
    injuries = get_injuries()

    rundown_games = {}
    try:
        from rundown_api import fetch_rundown_data
        rd_data = fetch_rundown_data()
        if rd_data:
            for g in rd_data:
                key = f"{g['away_team']}@{g['home_team']}"
                if g.get('consensus_spread') is not None:
                    g['consensus'] = g['consensus_spread']
                    g['spread_range'] = 0
                    g['best_book'] = None
                rundown_games[key] = g
            with_consensus = sum(1 for g in rundown_games.values() if g.get('consensus') is not None)
            print(f"   ✅ Rundown: {len(rundown_games)} games, {with_consensus} with multi-book consensus")
    except Exception as e:
        print(f"   ⚠️ Rundown API skipped: {e}")

    # Fetch BallDontLie team stats
    bdl_stats = {}
    try:
        from balldontlie_api import get_team_season_stats
        bdl_stats = get_team_season_stats()
    except Exception as e:
        print(f"   ⚠️ BallDontLie skipped: {e}")

    print("\n📡 Connecting to The Odds API...")
    
    PREFERRED_BOOKS = ['draftkings', 'fanduel', 'betmgm', 'caesars_sportsbook', 'pointsbetus', 'betrivers']
    BOOK_DISPLAY = {
        'draftkings': 'DraftKings',
        'fanduel': 'FanDuel', 
        'betmgm': 'BetMGM',
        'caesars_sportsbook': 'Caesars',
        'pointsbetus': 'PointsBet',
        'betrivers': 'BetRivers',
    }

    url = "https://api.the-odds-api.com/v4/sports/basketball_nba/odds/"
    params = {
        'apiKey': API_KEY,
        'regions': 'us',
        'markets': 'spreads,totals,h2h,spreads_h1,totals_h1,alternate_spreads',
        'oddsFormat': 'american',
        'bookmakers': ','.join(PREFERRED_BOOKS)
    }
    
    odds_api_ok = False
    games_to_process = []
    using_rundown = False

    try:
        response = api_request_with_retry(url, params)
        
        if response is None:
            print("\n⚠️ Failed to connect to Odds API after 3 attempts.")
        elif response.status_code != 200:
            print(f"\n⚠️ Odds API Error {response.status_code}")
            print(f"   {response.text}\n")
        else:
            games = response.json()
            print(f"✅ Odds API Connected!")
            print(f"   Games found: {len(games)}")
            print(f"   API calls left: {API_USAGE['remaining']}/500\n")
            check_api_usage()
            odds_api_ok = True

            for game in games:
                game_id = game['id']
                home = game['home_team']
                away = game['away_team']
                commence_time = utc_to_eastern_date(game['commence_time'])

                spread_home = None
                spread_away = None
                total = None
                home_ml = None
                away_ml = None
                home_spread_odds = None
                away_spread_odds = None
                home_spread_book = None
                away_spread_book = None

                spread_h1_home = None
                spread_h1_away = None
                spread_h1_home_odds = None
                spread_h1_away_odds = None
                total_h1 = None

                alt_spreads = {}

                def is_better_odds(new_odds, current_odds):
                    if current_odds is None:
                        return True
                    return new_odds > current_odds

                for bookmaker in game.get('bookmakers', []):
                    book_key = bookmaker.get('key', '')
                    book_name = BOOK_DISPLAY.get(book_key, book_key)

                    for market in bookmaker.get('markets', []):
                        if market['key'] == 'spreads':
                            for outcome in market['outcomes']:
                                if outcome['name'] == home:
                                    if spread_home is None:
                                        spread_home = outcome['point']
                                    price = outcome.get('price')
                                    if price is not None and is_better_odds(price, home_spread_odds):
                                        home_spread_odds = price
                                        home_spread_book = book_name
                                else:
                                    if spread_away is None:
                                        spread_away = outcome['point']
                                    price = outcome.get('price')
                                    if price is not None and is_better_odds(price, away_spread_odds):
                                        away_spread_odds = price
                                        away_spread_book = book_name

                        elif market['key'] == 'totals' and total is None:
                            total = market['outcomes'][0]['point']

                        elif market['key'] == 'h2h':
                            for outcome in market['outcomes']:
                                if outcome['name'] == home:
                                    if home_ml is None or outcome['price'] > home_ml:
                                        home_ml = outcome['price']
                                else:
                                    if away_ml is None or outcome['price'] > away_ml:
                                        away_ml = outcome['price']

                        elif market['key'] == 'spreads_h1':
                            for outcome in market.get('outcomes', []):
                                if outcome['name'] == home:
                                    if spread_h1_home is None:
                                        spread_h1_home = outcome.get('point')
                                    price = outcome.get('price')
                                    if price is not None and is_better_odds(price, spread_h1_home_odds):
                                        spread_h1_home_odds = price
                                else:
                                    if spread_h1_away is None:
                                        spread_h1_away = outcome.get('point')
                                    price = outcome.get('price')
                                    if price is not None and is_better_odds(price, spread_h1_away_odds):
                                        spread_h1_away_odds = price

                        elif market['key'] == 'totals_h1' and total_h1 is None:
                            outcomes = market.get('outcomes', [])
                            if outcomes:
                                total_h1 = outcomes[0].get('point')

                        elif market['key'] == 'alternate_spreads':
                            for outcome in market.get('outcomes', []):
                                if outcome['name'] == home:
                                    pt = outcome.get('point')
                                    price = outcome.get('price')
                                    if pt is not None and price is not None:
                                        pt_round = round(pt)
                                        if pt_round in [-1, -3, -5, -7, 1, 3, 5, 7]:
                                            key = f"alt_{pt_round}"
                                            if key not in alt_spreads or price > alt_spreads[key]:
                                                alt_spreads[key] = price

                games_to_process.append({
                    'game_id': game_id, 'home': home, 'away': away,
                    'commence_time': commence_time, 'game_time': game.get('commence_time') or None,
                    'spread_home': spread_home, 'spread_away': spread_away,
                    'total': total, 'home_ml': home_ml, 'away_ml': away_ml,
                    'home_spread_odds': home_spread_odds, 'away_spread_odds': away_spread_odds,
                    'home_spread_book': home_spread_book, 'away_spread_book': away_spread_book,
                    'spread_h1_home': spread_h1_home, 'spread_h1_away': spread_h1_away,
                    'spread_h1_home_odds': spread_h1_home_odds, 'spread_h1_away_odds': spread_h1_away_odds,
                    'total_h1': total_h1,
                    'alt_spreads': alt_spreads,
                })
    except Exception as e:
        print(f"\n⚠️ Odds API exception: {e}")

    if not odds_api_ok or len(games_to_process) == 0:
        if rundown_games:
            print("🔄 Falling back to The Rundown API for today's games...")
            using_rundown = True
            from datetime import date as _date
            today_str = _date.today().strftime('%Y-%m-%d')
            for key, rg in rundown_games.items():
                away_t = rg.get('away_team', '')
                home_t = rg.get('home_team', '')
                if not away_t or not home_t:
                    continue
                rd_spread = rg.get('spread_home') or rg.get('consensus_spread')
                games_to_process.append({
                    'game_id': f"rundown_{away_t}_{home_t}_{today_str}".replace(' ', '_').lower(),
                    'home': home_t, 'away': away_t,
                    'commence_time': rg.get('game_date', today_str),
                    'game_time': '',
                    'spread_home': rd_spread,
                    'spread_away': -rd_spread if rd_spread is not None else None,
                    'total': rg.get('total'),
                    'home_ml': rg.get('home_ml'), 'away_ml': rg.get('away_ml'),
                    'home_spread_odds': -110, 'away_spread_odds': -110,
                    'home_spread_book': 'Rundown Consensus', 'away_spread_book': 'Rundown Consensus',
                })
            print(f"   ✅ Rundown fallback: {len(games_to_process)} games loaded\n")
        else:
            print("❌ No odds source available. No games collected.\n")
            return

    if len(games_to_process) == 0:
        show_no_games_message()
        show_stats()
        return

    try:
        conn = sqlite3.connect(get_sqlite_path())
        cursor = conn.cursor()

        for gp in games_to_process:
            game_id = gp['game_id']
            home = gp['home']
            away = gp['away']
            commence_time = gp['commence_time']
            game_time = gp['game_time']
            spread_home = gp['spread_home']
            spread_away = gp['spread_away']
            total = gp['total']
            home_ml = gp['home_ml']
            away_ml = gp['away_ml']
            home_spread_odds = gp['home_spread_odds']
            away_spread_odds = gp['away_spread_odds']
            home_spread_book = gp['home_spread_book']
            away_spread_book = gp['away_spread_book']
            
            # Get enhanced data
            home_info = team_data.get(home, {})
            away_info = team_data.get(away, {})
            
            home_record = home_info.get('record', 'N/A')
            away_record = away_info.get('record', 'N/A')
            home_home_record = home_info.get('home_record', 'N/A')
            away_away_record = away_info.get('away_record', 'N/A')
            
            # Get form and rest days
            home_abbr = TEAM_ABBR_MAP.get(home, '')
            away_abbr = TEAM_ABBR_MAP.get(away, '')
            
            home_last5, home_last_game = get_team_schedule(home_abbr) if home_abbr else (None, None)
            away_last5, away_last_game = get_team_schedule(away_abbr) if away_abbr else (None, None)
            
            home_rest = calculate_rest_days(home_last_game)
            away_rest = calculate_rest_days(away_last_game)
            
            # Get injuries
            home_injuries = injuries.get(home, '')
            away_injuries = injuries.get(away, '')
            
            # Get game time (already set from gp above)

            rd_game = {}
            rd_key_full = f"{away}@{home}"
            rd_game = rundown_games.get(rd_key_full, {})
            if not rd_game:
                for rk, rv in rundown_games.items():
                    rk_away, rk_home = rk.split('@', 1) if '@' in rk else ('', '')
                    if (rk_away in away or away.startswith(rk_away)) and (rk_home in home or home.startswith(rk_home)):
                        rd_game = rv
                        break
            rd_consensus = rd_game.get('consensus')
            rd_std = rd_game.get('spread_std')
            rd_range = rd_game.get('spread_range')
            rd_best_book = rd_game.get('best_book')
            rd_num_books = rd_game.get('num_books')

            # Get BallDontLie team stats
            bdl_home = bdl_stats.get(home, {})
            bdl_away = bdl_stats.get(away, {})
            bdl_home_win_pct = bdl_home.get('win_pct')
            bdl_away_win_pct = bdl_away.get('win_pct')
            bdl_home_conf_rank = bdl_home.get('conference_rank')
            bdl_away_conf_rank = bdl_away.get('conference_rank')
            bdl_home_scoring_margin = bdl_home.get('bdl_scoring_margin_l14')
            bdl_away_scoring_margin = bdl_away.get('bdl_scoring_margin_l14')
            bdl_home_avg_pts = bdl_home.get('bdl_avg_pts_l14')
            bdl_away_avg_pts = bdl_away.get('bdl_avg_pts_l14')
            bdl_home_avg_pts_against = bdl_home.get('bdl_avg_pts_against_l14')
            bdl_away_avg_pts_against = bdl_away.get('bdl_avg_pts_against_l14')

            # Check if game already exists (to preserve opening line)
            cursor.execute('SELECT id, spread_home_open FROM games WHERE id = ?', (game_id,))
            existing = cursor.fetchone()
            
            is_new_game = existing is None
            has_opening = existing and existing[1] is not None
            
            spread_h1_home = gp.get('spread_h1_home')
            spread_h1_away = gp.get('spread_h1_away')
            spread_h1_home_odds = gp.get('spread_h1_home_odds')
            spread_h1_away_odds = gp.get('spread_h1_away_odds')
            total_h1 = gp.get('total_h1')
            alt_sp = gp.get('alt_spreads', {})

            if is_new_game:
                cursor.execute('''
                    INSERT INTO games 
                    (id, game_date, game_time, home_team, away_team, 
                     spread_home, spread_away, total, home_ml, away_ml, collected_at,
                     spread_home_open, total_open, home_ml_open, away_ml_open, open_collected_at,
                     home_record, away_record, home_home_record, away_away_record,
                     home_last5, away_last5, home_rest_days, away_rest_days,
                     home_injuries, away_injuries,
                     rundown_spread_consensus, rundown_spread_std, rundown_spread_range,
                     rundown_best_book, rundown_num_books,
                     bdl_home_win_pct, bdl_away_win_pct,
                     bdl_home_conf_rank, bdl_away_conf_rank,
                     bdl_home_scoring_margin, bdl_away_scoring_margin,
                     bdl_home_avg_pts, bdl_away_avg_pts,
                     bdl_home_avg_pts_against, bdl_away_avg_pts_against,
                     home_spread_odds, away_spread_odds,
                     home_spread_odds_open, away_spread_odds_open,
                     home_spread_book, away_spread_book,
                     spread_h1_home, spread_h1_away, spread_h1_home_odds, spread_h1_away_odds,
                     total_h1, spread_h1_home_open, total_h1_open,
                     alt_spread_minus_1, alt_spread_minus_3, alt_spread_minus_5, alt_spread_minus_7,
                     alt_spread_plus_1, alt_spread_plus_3, alt_spread_plus_5, alt_spread_plus_7,
                     commence_time)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                            ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                            ?, ?, ?, ?, ?, ?, ?,
                            ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    game_id, commence_time, game_time, home, away,
                    spread_home, spread_away, total, home_ml, away_ml,
                    datetime.now().isoformat(),
                    spread_home, total, home_ml, away_ml, datetime.now().isoformat(),
                    home_record, away_record, home_home_record, away_away_record,
                    home_last5, away_last5, home_rest, away_rest,
                    home_injuries, away_injuries,
                    rd_consensus, rd_std, rd_range, rd_best_book, rd_num_books,
                    bdl_home_win_pct, bdl_away_win_pct,
                    bdl_home_conf_rank, bdl_away_conf_rank,
                    bdl_home_scoring_margin, bdl_away_scoring_margin,
                    bdl_home_avg_pts, bdl_away_avg_pts,
                    bdl_home_avg_pts_against, bdl_away_avg_pts_against,
                    home_spread_odds, away_spread_odds,
                    home_spread_odds, away_spread_odds,
                    home_spread_book, away_spread_book,
                    spread_h1_home, spread_h1_away, spread_h1_home_odds, spread_h1_away_odds,
                    total_h1, spread_h1_home, total_h1,
                    alt_sp.get('alt_-1'), alt_sp.get('alt_-3'), alt_sp.get('alt_-5'), alt_sp.get('alt_-7'),
                    alt_sp.get('alt_1'), alt_sp.get('alt_3'), alt_sp.get('alt_5'), alt_sp.get('alt_7'),
                    game_time,
                ))
                line_status = "📌 OPENING"
            else:
                # Odds API still lists this game = not final — clear any wrongly-applied scores
                cursor.execute('''
                    UPDATE games SET
                        spread_home = ?, spread_away = ?, total = ?, 
                        home_ml = ?, away_ml = ?, collected_at = ?,
                        game_time = ?,
                        home_record = ?, away_record = ?, 
                        home_home_record = ?, away_away_record = ?,
                        home_last5 = ?, away_last5 = ?, 
                        home_rest_days = ?, away_rest_days = ?,
                        home_injuries = ?, away_injuries = ?,
                        rundown_spread_consensus = ?, rundown_spread_std = ?,
                        rundown_spread_range = ?, rundown_best_book = ?, rundown_num_books = ?,
                        bdl_home_win_pct = ?, bdl_away_win_pct = ?,
                        bdl_home_conf_rank = ?, bdl_away_conf_rank = ?,
                        bdl_home_scoring_margin = ?, bdl_away_scoring_margin = ?,
                        bdl_home_avg_pts = ?, bdl_away_avg_pts = ?,
                        bdl_home_avg_pts_against = ?, bdl_away_avg_pts_against = ?,
                        home_spread_odds = ?, away_spread_odds = ?,
                        home_spread_book = ?, away_spread_book = ?,
                        spread_h1_home = ?, spread_h1_away = ?,
                        spread_h1_home_odds = ?, spread_h1_away_odds = ?,
                        total_h1 = ?,
                        alt_spread_minus_1 = ?, alt_spread_minus_3 = ?,
                        alt_spread_minus_5 = ?, alt_spread_minus_7 = ?,
                        alt_spread_plus_1 = ?, alt_spread_plus_3 = ?,
                        alt_spread_plus_5 = ?, alt_spread_plus_7 = ?,
                        home_score = NULL, away_score = NULL, spread_result = NULL, total_result = NULL
                    WHERE id = ?
                ''', (
                    spread_home, spread_away, total, home_ml, away_ml,
                    datetime.now().isoformat(), game_time,
                    home_record, away_record, home_home_record, away_away_record,
                    home_last5, away_last5, home_rest, away_rest,
                    home_injuries, away_injuries,
                    rd_consensus, rd_std, rd_range, rd_best_book, rd_num_books,
                    bdl_home_win_pct, bdl_away_win_pct,
                    bdl_home_conf_rank, bdl_away_conf_rank,
                    bdl_home_scoring_margin, bdl_away_scoring_margin,
                    bdl_home_avg_pts, bdl_away_avg_pts,
                    bdl_home_avg_pts_against, bdl_away_avg_pts_against,
                    home_spread_odds, away_spread_odds,
                    home_spread_book, away_spread_book,
                    spread_h1_home, spread_h1_away,
                    spread_h1_home_odds, spread_h1_away_odds,
                    total_h1,
                    alt_sp.get('alt_-1'), alt_sp.get('alt_-3'),
                    alt_sp.get('alt_-5'), alt_sp.get('alt_-7'),
                    alt_sp.get('alt_1'), alt_sp.get('alt_3'),
                    alt_sp.get('alt_5'), alt_sp.get('alt_7'),
                    game_id
                ))
                
                # Calculate line movement if we have opening
                if has_opening:
                    cursor.execute('SELECT spread_home_open FROM games WHERE id = ?', (game_id,))
                    open_spread = cursor.fetchone()[0]
                    if open_spread and spread_home:
                        movement = spread_home - open_spread
                        cursor.execute('UPDATE games SET line_movement = ? WHERE id = ?', 
                                      (movement, game_id))
                        line_status = f"📊 CURRENT (moved {movement:+.1f})" if movement != 0 else "📊 CURRENT"
                    else:
                        line_status = "📊 CURRENT"
                else:
                    line_status = "📊 CURRENT"
            
            # Display enhanced info
            print(f"{line_status} {away} @ {home}")
            print(f"   📈 Records: {away} ({away_record}) vs {home} ({home_record})")
            if spread_home:
                odds_info = ""
                if home_spread_odds:
                    odds_info = f" ({home_spread_odds:+d} @ {home_spread_book})"
                print(f"   📉 Spread: {home} {spread_home:+.1f}{odds_info}")
            if total:
                print(f"   📉 Total: {total}")
            if home_last5 or away_last5:
                print(f"   🔥 Form (L5): {away} [{away_last5 or 'N/A'}] vs {home} [{home_last5 or 'N/A'}]")
            if home_home_record or away_away_record:
                print(f"   🏠 Splits: {home} home ({home_home_record}) | {away} away ({away_away_record})")
            if home_rest is not None or away_rest is not None:
                print(f"   😴 Rest: {home} ({home_rest or '?'} days) | {away} ({away_rest or '?'} days)")
            if spread_h1_home is not None:
                h1_odds_str = f" ({spread_h1_home_odds:+d})" if spread_h1_home_odds else ""
                print(f"   🏀 1H Spread: {home} {spread_h1_home:+.1f}{h1_odds_str}")
            if total_h1 is not None:
                print(f"   🏀 1H Total: {total_h1}")
            if alt_sp:
                alt_parts = []
                for k in sorted(alt_sp.keys(), key=lambda x: int(x.split('_')[1])):
                    pt = int(k.split('_')[1])
                    alt_parts.append(f"{pt:+d}={alt_sp[k]:+d}")
                if alt_parts:
                    print(f"   🎰 Alt Spreads: {', '.join(alt_parts)}")
            if home_injuries or away_injuries:
                if home_injuries:
                    print(f"   🏥 {home}: {home_injuries[:60]}...")
                if away_injuries:
                    print(f"   🏥 {away}: {away_injuries[:60]}...")
            print()
        
        conn.commit()
        conn.close()
        
        print("="*60)
        show_stats()
        
    except Exception as e:
        print(f"\n❌ Error: {e}\n")


def show_stats():
    """Display collection statistics"""
    conn = sqlite3.connect(get_sqlite_path())
    cursor = conn.cursor()
    
    cursor.execute('SELECT COUNT(*) FROM games')
    total = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM games WHERE home_score IS NOT NULL')
    with_scores = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM games WHERE home_record IS NOT NULL AND home_record != "N/A"')
    with_records = cursor.fetchone()[0]
    
    conn.close()
    
    print("\n📈 DATABASE STATS:")
    print(f"   Total games: {total}")
    print(f"   Games with scores: {with_scores}")
    print(f"   Games with full data: {with_records}")
    
    if total < 50:
        progress = int((total / 50) * 30)
        bar = "█" * progress + "░" * (30 - progress)
        print(f"   Progress: [{bar}] {total}/50")
        print(f"   Need: {50 - total} more games\n")
    else:
        print("   ✅ Ready to train model!\n")
    
    print("="*60)


def collect_player_props():
    """Collect player props (points, rebounds, assists) for today's games.
    Uses per-event endpoint: 1 credit per market per region per event.
    """
    print("\n" + "="*60)
    print("🎯 COLLECTING PLAYER PROPS")
    print("="*60 + "\n")

    API_KEY = os.environ.get('ODDS_API_KEY', '')
    if not API_KEY:
        print("❌ No ODDS_API_KEY set")
        return

    PROP_MARKETS = ['player_points', 'player_rebounds', 'player_assists']
    PREFERRED_BOOKS = ['fanduel', 'draftkings', 'betmgm', 'caesars', 'pointsbetus', 'betrivers']

    events_url = "https://api.the-odds-api.com/v4/sports/basketball_nba/events/"
    params = {'apiKey': API_KEY}

    try:
        resp = requests.get(events_url, params=params, timeout=15)
        resp.raise_for_status()
        events = resp.json()
    except Exception as e:
        print(f"❌ Failed to fetch events: {e}")
        return

    today_et = datetime.now(pytz.timezone('US/Eastern')).strftime('%Y-%m-%d')
    today_events = []
    for ev in events:
        ct = ev.get('commence_time', '')
        game_date = utc_to_eastern_date(ct)
        if game_date == today_et:
            today_events.append(ev)

    if not today_events:
        print(f"   No games found for {today_et}")
        return

    print(f"   Found {len(today_events)} games for {today_et}")
    credit_cost = len(today_events) * len(PROP_MARKETS)
    print(f"   Estimated API cost: {credit_cost} credits")

    init_db()
    conn = sqlite3.connect(get_sqlite_path())
    cursor = conn.cursor()
    total_props = 0

    for ev in today_events:
        event_id = ev['id']
        home = ev.get('home_team', '')
        away = ev.get('away_team', '')
        game_date = utc_to_eastern_date(ev.get('commence_time', ''))
        print(f"\n   {away} @ {home}")

        for mk in PROP_MARKETS:
            props_url = f"https://api.the-odds-api.com/v4/sports/basketball_nba/events/{event_id}/odds"
            props_params = {
                'apiKey': API_KEY,
                'regions': 'us',
                'markets': mk,
                'oddsFormat': 'american',
                'bookmakers': ','.join(PREFERRED_BOOKS),
            }

            try:
                r = requests.get(props_url, params=props_params, timeout=15)
                remaining = r.headers.get('x-requests-remaining', '?')
                r.raise_for_status()
                data = r.json()
            except Exception as e:
                print(f"     ❌ {mk}: {e}")
                continue

            market_label = mk.replace('player_', '').upper()
            count = 0

            for bookmaker in data.get('bookmakers', []):
                book_key = bookmaker.get('key', '')
                for market in bookmaker.get('markets', []):
                    if market['key'] != mk:
                        continue
                    for outcome in market.get('outcomes', []):
                        player = outcome.get('description', '')
                        line = outcome.get('point')
                        price = outcome.get('price')
                        name = outcome.get('name', '')
                        if not player or line is None or price is None:
                            continue

                        over_odds = price if name == 'Over' else None
                        under_odds = price if name == 'Under' else None

                        try:
                            cursor.execute('''
                                INSERT INTO nba_player_props 
                                (game_id, game_date, player_name, team, market, line, 
                                 over_odds, under_odds, book, collected_at)
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                                ON CONFLICT(game_id, player_name, market, book) 
                                DO UPDATE SET 
                                    line = excluded.line,
                                    over_odds = COALESCE(excluded.over_odds, nba_player_props.over_odds),
                                    under_odds = COALESCE(excluded.under_odds, nba_player_props.under_odds),
                                    collected_at = excluded.collected_at
                            ''', (
                                event_id, game_date, player, None, mk, line,
                                over_odds, under_odds, book_key,
                                datetime.now().isoformat()
                            ))
                            count += 1
                        except Exception as e:
                            pass

            print(f"     {market_label}: {count} lines (API remaining: {remaining})")
            total_props += count
            time.sleep(0.3)

    conn.commit()
    conn.close()
    print(f"\n   Total props stored: {total_props}")
    print("="*60)


def collect_closing_lines():
    """Collect closing lines for games starting soon (within 30 min)"""
    print("\n" + "="*60)
    print("⏰ COLLECTING CLOSING LINES")
    print("="*60 + "\n")
    
    if not API_KEY:
        print("❌ ERROR: No API key found!")
        return
    
    PREFERRED_BOOKS = ['draftkings', 'fanduel', 'betmgm', 'caesars_sportsbook', 'pointsbetus', 'betrivers']
    BOOK_DISPLAY = {
        'draftkings': 'DraftKings', 'fanduel': 'FanDuel', 'betmgm': 'BetMGM',
        'caesars_sportsbook': 'Caesars', 'pointsbetus': 'PointsBet', 'betrivers': 'BetRivers',
    }

    url = "https://api.the-odds-api.com/v4/sports/basketball_nba/odds/"
    params = {
        'apiKey': API_KEY,
        'regions': 'us',
        'markets': 'spreads,totals,h2h,spreads_h1,totals_h1',
        'oddsFormat': 'american',
        'bookmakers': ','.join(PREFERRED_BOOKS)
    }
    
    try:
        response = api_request_with_retry(url, params)
        
        if response is None:
            print("\n❌ Failed to connect after 3 attempts.")
            print("   Please check your internet connection and try again.\n")
            return
        
        if response.status_code != 200:
            print(f"❌ API Error: {response.status_code}")
            return
        
        games = response.json()
        
        print(f"✅ Connected! API calls left: {API_USAGE['remaining']}/500\n")
        
        check_api_usage()
        
        conn = sqlite3.connect(get_sqlite_path())
        cursor = conn.cursor()
        
        updated = 0
        
        for game in games:
            game_id = game['id']
            home = game['home_team']
            away = game['away_team']
            
            cursor.execute('SELECT id, spread_home_open FROM games WHERE id = ? AND home_score IS NULL', (game_id,))
            existing = cursor.fetchone()
            
            if not existing:
                continue
            
            spread_home = None
            total = None
            home_ml = None
            away_ml = None
            home_spread_odds = None
            away_spread_odds = None
            spread_h1_close = None
            total_h1_close = None
            
            def is_better_odds(new_odds, current_odds):
                if current_odds is None:
                    return True
                return new_odds > current_odds

            for bookmaker in game.get('bookmakers', []):
                for market in bookmaker.get('markets', []):
                    if market['key'] == 'spreads':
                        for outcome in market['outcomes']:
                            if outcome['name'] == home:
                                if spread_home is None:
                                    spread_home = outcome['point']
                                price = outcome.get('price')
                                if price is not None and is_better_odds(price, home_spread_odds):
                                    home_spread_odds = price
                            else:
                                price = outcome.get('price')
                                if price is not None and is_better_odds(price, away_spread_odds):
                                    away_spread_odds = price
                    elif market['key'] == 'totals' and total is None:
                        total = market['outcomes'][0]['point']
                    elif market['key'] == 'h2h':
                        for outcome in market['outcomes']:
                            if outcome['name'] == home:
                                if home_ml is None or outcome['price'] > home_ml:
                                    home_ml = outcome['price']
                            else:
                                if away_ml is None or outcome['price'] > away_ml:
                                    away_ml = outcome['price']
                    elif market['key'] == 'spreads_h1' and spread_h1_close is None:
                        for outcome in market.get('outcomes', []):
                            if outcome['name'] == home:
                                spread_h1_close = outcome.get('point')
                                break
                    elif market['key'] == 'totals_h1' and total_h1_close is None:
                        outcomes = market.get('outcomes', [])
                        if outcomes:
                            total_h1_close = outcomes[0].get('point')
            
            cursor.execute('''
                UPDATE games SET
                    spread_home_close = ?, total_close = ?,
                    home_ml_close = ?, away_ml_close = ?,
                    home_spread_odds_close = ?, away_spread_odds_close = ?,
                    spread_h1_home_close = ?, total_h1_close = ?,
                    close_collected_at = ?
                WHERE id = ?
            ''', (spread_home, total, home_ml, away_ml,
                  home_spread_odds, away_spread_odds,
                  spread_h1_close, total_h1_close,
                  datetime.now().isoformat(), game_id))
            
            # Calculate total line movement
            open_spread = existing[1]
            if open_spread and spread_home:
                movement = spread_home - open_spread
                cursor.execute('UPDATE games SET line_movement = ? WHERE id = ?', 
                              (movement, game_id))
                move_str = f" (moved {movement:+.1f})" if movement != 0 else ""
            else:
                move_str = ""
            
            updated += 1
            print(f"🔒 {away} @ {home}: Close {spread_home:+.1f}{move_str}")
        
        conn.commit()
        conn.close()
        
        print(f"\n✅ Captured closing lines for {updated} games\n")
        
    except Exception as e:
        print(f"❌ Error: {e}\n")


def collect_wnba_closing_lines():
    """Collect closing lines for WNBA games starting soon"""
    from sport_config import get_odds_api_url
    print("\n" + "="*60)
    print("⏰ COLLECTING WNBA CLOSING LINES")
    print("="*60 + "\n")

    if not API_KEY:
        print("❌ ERROR: No API key found!")
        return

    PREFERRED_BOOKS = ['draftkings', 'fanduel', 'betmgm', 'caesars_sportsbook', 'pointsbetus', 'betrivers']

    url = get_odds_api_url('wnba')
    params = {
        'apiKey': API_KEY,
        'regions': 'us',
        'markets': 'spreads,totals,h2h',
        'oddsFormat': 'american',
        'bookmakers': ','.join(PREFERRED_BOOKS)
    }

    try:
        response = api_request_with_retry(url, params)

        if response is None:
            print("\n❌ Failed to connect after 3 attempts.")
            return

        if response.status_code != 200:
            print(f"❌ API Error: {response.status_code}")
            return

        games = response.json()

        print(f"✅ Connected! API calls left: {API_USAGE['remaining']}/500\n")

        check_api_usage()

        conn = sqlite3.connect(get_sqlite_path())
        cursor = conn.cursor()

        updated = 0

        for game in games:
            game_id = game['id']
            home = game['home_team']
            away = game['away_team']

            cursor.execute('SELECT id, spread_home_open FROM wnba_games WHERE id = ? AND home_score IS NULL', (game_id,))
            existing = cursor.fetchone()

            if not existing:
                continue

            spread_home = None
            total = None
            home_ml = None
            away_ml = None
            home_spread_odds = None
            away_spread_odds = None

            def is_better_odds(new_odds, current_odds):
                if current_odds is None:
                    return True
                return new_odds > current_odds

            for bookmaker in game.get('bookmakers', []):
                for market in bookmaker.get('markets', []):
                    if market['key'] == 'spreads':
                        for outcome in market['outcomes']:
                            if outcome['name'] == home:
                                if spread_home is None:
                                    spread_home = outcome['point']
                                price = outcome.get('price')
                                if price is not None and is_better_odds(price, home_spread_odds):
                                    home_spread_odds = price
                            else:
                                price = outcome.get('price')
                                if price is not None and is_better_odds(price, away_spread_odds):
                                    away_spread_odds = price
                    elif market['key'] == 'totals' and total is None:
                        total = market['outcomes'][0]['point']
                    elif market['key'] == 'h2h':
                        for outcome in market['outcomes']:
                            if outcome['name'] == home:
                                if home_ml is None or outcome['price'] > home_ml:
                                    home_ml = outcome['price']
                            else:
                                if away_ml is None or outcome['price'] > away_ml:
                                    away_ml = outcome['price']

            cursor.execute('''
                UPDATE wnba_games SET
                    spread_home_close = ?, total_close = ?,
                    home_ml_close = ?, away_ml_close = ?,
                    home_spread_odds_close = ?, away_spread_odds_close = ?,
                    close_collected_at = ?
                WHERE id = ?
            ''', (spread_home, total, home_ml, away_ml,
                  home_spread_odds, away_spread_odds,
                  datetime.now().isoformat(), game_id))

            open_spread = existing[1]
            if open_spread and spread_home:
                movement = spread_home - open_spread
                cursor.execute('UPDATE wnba_games SET line_movement = ? WHERE id = ?',
                              (movement, game_id))
                move_str = f" (moved {movement:+.1f})" if movement != 0 else ""
            else:
                move_str = ""

            updated += 1
            spread_display = f"{spread_home:+.1f}" if spread_home else "N/A"
            print(f"🔒 {away} @ {home}: Close {spread_display}{move_str}")

        conn.commit()
        conn.close()

        print(f"\n✅ Captured WNBA closing lines for {updated} games\n")

    except Exception as e:
        print(f"❌ Error: {e}\n")


def show_visualization():
    """Display ASCII charts of collection progress"""
    print("\n" + "="*60)
    print("📈 SHARP PICKS - COLLECTION VISUALIZATION")
    print("="*60 + "\n")
    
    conn = sqlite3.connect(get_sqlite_path())
    cursor = conn.cursor()
    
    # Get games per day
    cursor.execute('''
        SELECT DATE(game_date) as day, COUNT(*) as count
        FROM games
        GROUP BY day
        ORDER BY day
    ''')
    
    daily_data = cursor.fetchall()
    conn.close()
    
    if not daily_data:
        print("No data to visualize yet. Run the collector first!\n")
        return
    
    # BAR CHART - Games per day
    print("📊 GAMES COLLECTED PER DAY")
    print("-" * 50)
    
    max_count = max(d[1] for d in daily_data)
    bar_width = 30
    
    for date, count in daily_data:
        short_date = date[5:] if date else "?"  # MM-DD format
        bar_len = int(count / max_count * bar_width) if max_count > 0 else 0
        bar = "█" * bar_len + "░" * (bar_width - bar_len)
        print(f"   {short_date} │{bar}│ {count}")
    
    print()
    
    # CUMULATIVE LINE GRAPH
    print("📈 CUMULATIVE TOTAL (Progress Over Time)")
    print("-" * 50)
    
    cumulative = []
    total = 0
    for date, count in daily_data:
        total += count
        cumulative.append((date, total))
    
    # ASCII line graph
    height = 8
    width = min(len(cumulative) * 4, 40)
    max_val = cumulative[-1][1] if cumulative else 1
    
    # Create graph grid
    graph = [[' ' for _ in range(width + 10)] for _ in range(height + 1)]
    
    # Y-axis labels
    for i in range(height + 1):
        val = int(max_val * (height - i) / height)
        label = f"{val:>3}"
        for j, c in enumerate(label):
            graph[i][j] = c
        graph[i][4] = '│'
    
    # Plot points
    for idx, (date, val) in enumerate(cumulative):
        x = 5 + idx * 3
        if x < width + 5:
            y = height - int(val / max_val * height) if max_val > 0 else height
            y = max(0, min(height, y))
            
            # Draw vertical line from bottom to point
            for row in range(y, height + 1):
                if graph[row][x] == ' ':
                    graph[row][x] = '│' if row > y else '●'
            graph[y][x] = '●'
    
    # Print graph
    for row in graph:
        print("   " + "".join(row))
    
    # X-axis
    print("   " + " " * 4 + "└" + "─" * (width))
    
    # X-axis labels
    x_labels = "     "
    for idx, (date, _) in enumerate(cumulative):
        if idx < (width // 3):
            x_labels += date[8:10] + " "  # Day only
    print("   " + x_labels)
    
    # Summary stats
    print(f"\n   Total Collected: {cumulative[-1][1]} games")
    print(f"   Collection Days: {len(daily_data)}")
    avg = sum(d[1] for d in daily_data) / len(daily_data)
    print(f"   Average Per Day: {avg:.1f} games")
    
    # Progress to goal
    goal = 50
    current = cumulative[-1][1]
    pct = min(current / goal * 100, 100)
    
    print(f"\n🎯 PROGRESS TO 50-GAME GOAL")
    print("-" * 50)
    
    prog_bar = "█" * int(pct / 2) + "░" * (50 - int(pct / 2))
    print(f"   [{prog_bar}]")
    print(f"   {current}/50 games ({pct:.0f}%)")
    
    if current >= goal:
        print("\n   ✨ Goal reached! Ready to train the model!")
    else:
        remaining = goal - current
        days_left = int(remaining / avg) + 1 if avg > 0 else 999
        print(f"\n   ⏳ {remaining} games to go (~{days_left} days at current pace)")
    
    print("\n" + "="*60 + "\n")


def generate_report():
    """Generate a summary report of collected data"""
    print("\n" + "="*60)
    print("📊 SHARP PICKS - DATA COLLECTION REPORT")
    print("="*60 + "\n")
    
    conn = sqlite3.connect(get_sqlite_path())
    cursor = conn.cursor()
    
    # 1. Total games collected
    cursor.execute('SELECT COUNT(*) FROM games')
    total_games = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM games WHERE home_score IS NOT NULL')
    completed_games = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM games WHERE home_score IS NULL')
    upcoming_games = cursor.fetchone()[0]
    
    print("📈 TOTAL GAMES COLLECTED")
    print("-" * 40)
    print(f"   Total Games: {total_games}")
    print(f"   Completed (with scores): {completed_games}")
    print(f"   Upcoming (no scores yet): {upcoming_games}")
    
    # 2. Breakdown by team
    print("\n📋 GAMES BY TEAM (Top 10)")
    print("-" * 40)
    
    cursor.execute('''
        SELECT team, COUNT(*) as games FROM (
            SELECT home_team as team FROM games
            UNION ALL
            SELECT away_team as team FROM games
        ) GROUP BY team ORDER BY games DESC LIMIT 10
    ''')
    
    teams = cursor.fetchall()
    for team, count in teams:
        bar = "█" * (count * 2)
        print(f"   {team:<25} {bar} {count}")
    
    # 3. Average spreads
    print("\n📐 SPREAD STATISTICS")
    print("-" * 40)
    
    cursor.execute('''
        SELECT 
            AVG(ABS(spread_home)) as avg_spread,
            MIN(spread_home) as biggest_dog,
            MAX(spread_home) as biggest_fav,
            AVG(line_movement) as avg_movement
        FROM games WHERE spread_home IS NOT NULL
    ''')
    
    stats = cursor.fetchone()
    if stats[0]:
        print(f"   Average Spread Size: {stats[0]:.1f} points")
        print(f"   Biggest Home Dog: +{abs(stats[1]):.1f}")
        print(f"   Biggest Home Favorite: {stats[2]:.1f}")
        if stats[3]:
            print(f"   Average Line Movement: {stats[3]:+.2f}")
    
    # Spread distribution
    cursor.execute('''
        SELECT 
            CASE 
                WHEN ABS(spread_home) <= 3 THEN '1-3 pts'
                WHEN ABS(spread_home) <= 6 THEN '4-6 pts'
                WHEN ABS(spread_home) <= 9 THEN '7-9 pts'
                ELSE '10+ pts'
            END as bucket,
            COUNT(*) as count
        FROM games WHERE spread_home IS NOT NULL
        GROUP BY bucket ORDER BY bucket
    ''')
    
    print("\n   Spread Distribution:")
    for bucket, count in cursor.fetchall():
        pct = (count / total_games * 100) if total_games > 0 else 0
        bar = "█" * int(pct / 2)
        print(f"      {bucket:<10} {bar} {count} ({pct:.0f}%)")
    
    # 4. Most common totals
    print("\n🎯 TOTAL (O/U) STATISTICS")
    print("-" * 40)
    
    cursor.execute('''
        SELECT 
            AVG(total) as avg_total,
            MIN(total) as min_total,
            MAX(total) as max_total
        FROM games WHERE total IS NOT NULL
    ''')
    
    total_stats = cursor.fetchone()
    if total_stats[0]:
        print(f"   Average Total: {total_stats[0]:.1f}")
        print(f"   Lowest Total: {total_stats[1]:.1f}")
        print(f"   Highest Total: {total_stats[2]:.1f}")
    
    cursor.execute('''
        SELECT ROUND(total, 0) as rounded_total, COUNT(*) as count
        FROM games WHERE total IS NOT NULL
        GROUP BY rounded_total ORDER BY count DESC LIMIT 5
    ''')
    
    print("\n   Most Common Totals:")
    for total, count in cursor.fetchall():
        print(f"      {total:.0f}: {count} games")
    
    # 5. Collection streak
    print("\n📅 COLLECTION STREAK")
    print("-" * 40)
    
    cursor.execute('''
        SELECT DISTINCT DATE(game_date) as d 
        FROM games 
        ORDER BY d DESC
    ''')
    
    dates = [row[0] for row in cursor.fetchall()]
    
    if dates:
        streak = 1
        today = datetime.now().date()
        
        sorted_dates = sorted(set(dates), reverse=True)
        
        for i in range(len(sorted_dates) - 1):
            try:
                d1 = datetime.strptime(sorted_dates[i], '%Y-%m-%d').date()
                d2 = datetime.strptime(sorted_dates[i+1], '%Y-%m-%d').date()
                
                if (d1 - d2).days == 1:
                    streak += 1
                else:
                    break
            except:
                break
        
        first_date = min(dates) if dates else 'N/A'
        last_date = max(dates) if dates else 'N/A'
        
        print(f"   First Collection: {first_date}")
        print(f"   Latest Collection: {last_date}")
        print(f"   Consecutive Days: {streak}")
        print(f"   Total Days with Data: {len(set(dates))}")
    
    # Spread results (if we have completed games)
    if completed_games > 0:
        print("\n🏆 SPREAD RESULTS (Completed Games)")
        print("-" * 40)
        
        cursor.execute('''
            SELECT spread_result, COUNT(*) as count
            FROM games WHERE spread_result IS NOT NULL
            GROUP BY spread_result
        ''')
        
        results = cursor.fetchall()
        for result, count in results:
            pct = (count / completed_games * 100)
            print(f"   {result}: {count} ({pct:.1f}%)")
    
    conn.close()
    
    print("\n" + "="*60 + "\n")


def show_welcome():
    """Show welcome message with progress stats"""
    conn = sqlite3.connect(get_sqlite_path())
    cursor = conn.cursor()
    
    # Total games
    cursor.execute('SELECT COUNT(*) FROM games')
    total_games = cursor.fetchone()[0]
    
    # Games with results (needed for training)
    cursor.execute('SELECT COUNT(*) FROM games WHERE spread_result IS NOT NULL')
    completed_games = cursor.fetchone()[0]
    
    # Calculate streak
    cursor.execute('SELECT DISTINCT DATE(game_date) FROM games ORDER BY game_date DESC')
    dates = [row[0] for row in cursor.fetchall()]
    
    streak = 0
    if dates:
        sorted_dates = sorted(set(dates), reverse=True)
        streak = 1
        for i in range(len(sorted_dates) - 1):
            try:
                d1 = datetime.strptime(sorted_dates[i], '%Y-%m-%d').date()
                d2 = datetime.strptime(sorted_dates[i+1], '%Y-%m-%d').date()
                if (d1 - d2).days == 1:
                    streak += 1
                else:
                    break
            except:
                break
    
    conn.close()
    
    # Progress calculations
    goal = 50
    progress = min(completed_games / goal * 100, 100)
    games_needed = max(0, goal - completed_games)
    
    # Estimate days until ready (assume ~6 games per day complete)
    games_per_day = 6
    days_until_ready = max(0, (games_needed + games_per_day - 1) // games_per_day)
    
    # Display welcome
    print("\n" + "="*50)
    print("🏀 SHARP PICKS - NBA DATA COLLECTOR")
    print("="*50)
    
    # Streak display
    if streak >= 7:
        streak_emoji = "🔥🔥🔥"
    elif streak >= 3:
        streak_emoji = "🔥"
    else:
        streak_emoji = "📅"
    
    print(f"\n{streak_emoji} Collection Streak: {streak} day{'s' if streak != 1 else ''}")
    print(f"📊 Total Games Collected: {total_games}")
    print(f"✅ Games with Results: {completed_games}")
    
    # Progress bar
    bar_length = 20
    filled = int(progress / 100 * bar_length)
    bar = "█" * filled + "░" * (bar_length - filled)
    print(f"\n🎯 Progress to Training: [{bar}] {progress:.0f}%")
    print(f"   {completed_games}/50 games with results")
    
    if completed_games >= goal:
        print("\n✨ READY TO TRAIN! Run: python model.py train")
    else:
        print(f"\n⏳ ~{days_until_ready} day{'s' if days_until_ready != 1 else ''} until ready to train")
        print(f"   Need {games_needed} more completed games")
    
    print("\n" + "-"*50 + "\n")


def setup_wnba_table(cursor):
    """Create wnba_games table with full schema matching NBA games table"""
    cursor.execute('''CREATE TABLE IF NOT EXISTS wnba_games (
        id TEXT PRIMARY KEY,
        game_date TEXT,
        game_time TEXT,
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
        scores_updated_at TEXT,
        home_record TEXT,
        away_record TEXT,
        home_home_record TEXT,
        away_away_record TEXT,
        home_last5 TEXT,
        away_last5 TEXT,
        home_rest_days INTEGER,
        away_rest_days INTEGER,
        home_injuries TEXT,
        away_injuries TEXT,
        spread_home_open REAL,
        total_open REAL,
        home_ml_open INTEGER,
        away_ml_open INTEGER,
        open_collected_at TEXT,
        spread_home_close REAL,
        total_close REAL,
        home_ml_close INTEGER,
        away_ml_close INTEGER,
        close_collected_at TEXT,
        line_movement REAL,
        home_spread_odds INTEGER,
        away_spread_odds INTEGER,
        home_spread_odds_open INTEGER,
        away_spread_odds_open INTEGER,
        home_spread_odds_close INTEGER,
        away_spread_odds_close INTEGER,
        home_spread_book TEXT,
        away_spread_book TEXT,
        commence_time TEXT
    )''')

    new_columns = [
        ('game_time', 'TEXT'),
        ('spread_result', 'TEXT'),
        ('total_result', 'TEXT'),
        ('scores_updated_at', 'TEXT'),
        ('home_record', 'TEXT'),
        ('away_record', 'TEXT'),
        ('home_home_record', 'TEXT'),
        ('away_away_record', 'TEXT'),
        ('home_last5', 'TEXT'),
        ('away_last5', 'TEXT'),
        ('home_rest_days', 'INTEGER'),
        ('away_rest_days', 'INTEGER'),
        ('home_injuries', 'TEXT'),
        ('away_injuries', 'TEXT'),
        ('total_open', 'REAL'),
        ('total_close', 'REAL'),
        ('home_ml_open', 'INTEGER'),
        ('away_ml_open', 'INTEGER'),
        ('home_ml_close', 'INTEGER'),
        ('away_ml_close', 'INTEGER'),
        ('spread_home_close', 'REAL'),
        ('open_collected_at', 'TEXT'),
        ('close_collected_at', 'TEXT'),
        ('line_movement', 'REAL'),
        ('home_spread_odds_open', 'INTEGER'),
        ('away_spread_odds_open', 'INTEGER'),
        ('home_spread_odds_close', 'INTEGER'),
        ('away_spread_odds_close', 'INTEGER'),
    ]

    for col_name, col_type in new_columns:
        try:
            cursor.execute(f'ALTER TABLE wnba_games ADD COLUMN {col_name} {col_type}')
        except:
            pass


def collect_wnba_scores(date_offset=1):
    """Fetch WNBA final scores from ESPN API for a given date offset (1=yesterday)"""
    from sport_config import get_sport_config
    cfg = get_sport_config('wnba')

    target = datetime.now() - timedelta(days=date_offset)
    date_str = target.strftime('%Y%m%d')
    display_date = target.strftime('%B %d, %Y')

    print(f"\n{'='*60}")
    print(f"🏀 WNBA SCORE COLLECTOR - {display_date}")
    print(f"{'='*60}\n")

    url = f"{cfg['espn_scoreboard']}?dates={date_str}"

    try:
        response = requests.get(url, timeout=15)
        if response.status_code != 200:
            print(f"❌ ESPN WNBA Error: {response.status_code}")
            return

        data = response.json()
        events = data.get('events', [])

        if not events:
            print("ℹ️  No WNBA games found\n")
            return

        print(f"✅ Found {len(events)} WNBA games\n")

        conn = sqlite3.connect(get_sqlite_path())
        cursor = conn.cursor()

        setup_wnba_table(cursor)

        updated = 0
        for event in events:
            status = event.get('status', {}).get('type', {}).get('name', '')
            if status != 'STATUS_FINAL':
                continue

            competitions = event.get('competitions', [])
            if not competitions:
                continue
            competition = competitions[0]
            competitors = competition.get('competitors', [])

            home_team = away_team = None
            home_score = away_score = None
            for comp in competitors:
                team_name = comp.get('team', {}).get('displayName', '')
                score = int(comp.get('score', 0))
                if comp.get('homeAway') == 'home':
                    home_team = team_name
                    home_score = score
                else:
                    away_team = team_name
                    away_score = score

            if not all([home_team, away_team, home_score is not None, away_score is not None]):
                continue

            game_date = target.strftime('%Y-%m-%d')
            next_date = (target + timedelta(days=1)).strftime('%Y-%m-%d')
            game_id = event.get('id', f"wnba_{game_date}_{away_team}_{home_team}")

            game = None
            for try_date in [game_date, next_date]:
                cursor.execute('''
                    SELECT id, spread_home, total FROM wnba_games
                    WHERE game_date = ?
                    AND (home_team LIKE ? OR home_team LIKE ?)
                    AND home_score IS NULL
                ''', (try_date, f'%{home_team.split()[-1]}%', f'%{home_team}%'))
                game = cursor.fetchone()
                if game:
                    break

            if not game:
                cursor.execute('SELECT id, spread_home, total FROM wnba_games WHERE id = ?', (game_id,))
                game = cursor.fetchone()

            if game:
                found_id, spread_home, total = game

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

                total_result = None
                actual_total = home_score + away_score
                if total is not None:
                    if actual_total > total:
                        total_result = 'OVER'
                    elif actual_total < total:
                        total_result = 'UNDER'
                    else:
                        total_result = 'PUSH'

                cursor.execute('''
                    UPDATE wnba_games
                    SET home_score = ?, away_score = ?,
                        spread_result = ?, total_result = ?,
                        scores_updated_at = ?
                    WHERE id = ?
                ''', (home_score, away_score, spread_result, total_result,
                      datetime.now().isoformat(), found_id))

                updated += 1

                print(f"🏀 {away_team} {away_score} @ {home_team} {home_score}")
                if spread_result:
                    emoji = "✅" if spread_result != 'PUSH' else "➖"
                    print(f"   {emoji} Spread: {spread_result} (line was {spread_home:+.1f})")
                if total_result:
                    emoji = "✅" if total_result != 'PUSH' else "➖"
                    print(f"   {emoji} Total: {total_result} (line was {total}, actual {actual_total})")
                print()
            else:
                cursor.execute('''INSERT OR IGNORE INTO wnba_games
                    (id, game_date, home_team, away_team, home_score, away_score, collected_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)''',
                    (game_id, game_date, home_team, away_team, home_score, away_score,
                     datetime.now().isoformat()))
                if cursor.rowcount > 0:
                    updated += 1
                    print(f"   {away_team} {away_score} @ {home_team} {home_score}")

        conn.commit()
        conn.close()
        print(f"\n✅ Updated {updated} WNBA games\n")

    except Exception as e:
        print(f"❌ WNBA score collection error: {e}")


def update_wnba_rolling_ratings():
    """Compute rolling team ratings from game-by-game results (no leakage).
    Uses last 20 games with 50% prior-season carry-over.
    Stores in wnba_rolling_ratings table for live prediction use."""
    import numpy as np

    print(f"\n{'='*60}")
    print("📊 WNBA ROLLING RATINGS UPDATE")
    print(f"{'='*60}\n")

    conn = sqlite3.connect(get_sqlite_path())
    cursor = conn.cursor()

    cursor.execute('''CREATE TABLE IF NOT EXISTS wnba_rolling_ratings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        team TEXT NOT NULL,
        game_date TEXT NOT NULL,
        season INTEGER,
        games_played INTEGER,
        ortg REAL,
        drtg REAL,
        nrtg REAL,
        pace_proxy REAL,
        avg_pf REAL,
        avg_pa REAL,
        margin_avg REAL,
        margin_std REAL,
        win_pct REAL,
        updated_at TEXT,
        UNIQUE(team, game_date)
    )''')

    cursor.execute('''
        SELECT game_date, season, home_team, away_team, home_score, away_score
        FROM wnba_games
        WHERE home_score IS NOT NULL AND away_score IS NOT NULL
        ORDER BY game_date ASC
    ''')
    all_games = cursor.fetchall()

    if not all_games:
        print("  No completed WNBA games found.")
        conn.close()
        return

    PRIOR_SEASON_DECAY = 0.5
    MIN_GAMES = 5
    WINDOW = 20

    team_stats = {}
    ratings_computed = 0

    for game_date, season, ht, at, hs, as_ in all_games:
        hs, as_ = float(hs), float(as_)

        for team in [ht, at]:
            if team not in team_stats:
                team_stats[team] = {
                    'pts_for': [], 'pts_against': [], 'margins': [],
                    'season': None
                }

        for team in [ht, at]:
            ts = team_stats[team]
            if ts['season'] is not None and ts['season'] != season:
                if len(ts['pts_for']) > 0:
                    n = len(ts['pts_for'])
                    keep = max(1, int(n * PRIOR_SEASON_DECAY))
                    ts['pts_for'] = ts['pts_for'][-keep:]
                    ts['pts_against'] = ts['pts_against'][-keep:]
                    ts['margins'] = ts['margins'][-keep:]
                    ts['has_prior'] = True
                    ts['season'] = season

        for team in [ht, at]:
            ts = team_stats[team]
            total_games = len(ts['pts_for'])
            if total_games >= MIN_GAMES or (total_games >= 1 and ts.get('has_prior', False)):
                use_count = max(MIN_GAMES, total_games) if total_games >= MIN_GAMES else total_games
                pf = np.array(ts['pts_for'][-WINDOW:])
                pa = np.array(ts['pts_against'][-WINDOW:])
                margins = np.array(ts['margins'][-WINDOW:])

                avg_pf = float(np.mean(pf))
                avg_pa = float(np.mean(pa))
                pace_proxy = (avg_pf + avg_pa) / 2.0

                ortg = (avg_pf / pace_proxy) * 100 if pace_proxy > 0 else 100
                drtg = (avg_pa / pace_proxy) * 100 if pace_proxy > 0 else 100
                nrtg = ortg - drtg

                margin_avg = float(np.mean(margins))
                margin_std = float(np.std(margins)) if len(margins) > 2 else 12.0
                w = sum(1 for m in margins if m > 0)
                win_pct = w / len(margins)

                cursor.execute('''INSERT OR REPLACE INTO wnba_rolling_ratings
                    (team, game_date, season, games_played, ortg, drtg, nrtg,
                     pace_proxy, avg_pf, avg_pa, margin_avg, margin_std, win_pct, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                    (team, game_date, season, total_games,
                     round(ortg, 2), round(drtg, 2), round(nrtg, 2),
                     round(pace_proxy, 1), round(avg_pf, 1), round(avg_pa, 1),
                     round(margin_avg, 2), round(margin_std, 2), round(win_pct, 3),
                     datetime.now().isoformat()))
                ratings_computed += 1

        team_stats[ht]['pts_for'].append(hs)
        team_stats[ht]['pts_against'].append(as_)
        team_stats[ht]['margins'].append(hs - as_)
        team_stats[ht]['season'] = season

        team_stats[at]['pts_for'].append(as_)
        team_stats[at]['pts_against'].append(hs)
        team_stats[at]['margins'].append(as_ - hs)
        team_stats[at]['season'] = season

    conn.commit()

    cursor.execute('SELECT COUNT(DISTINCT team) FROM wnba_rolling_ratings')
    team_count = cursor.fetchone()[0]
    cursor.execute('SELECT MAX(game_date) FROM wnba_rolling_ratings')
    latest = cursor.fetchone()[0]

    print(f"  ✅ {ratings_computed} rolling ratings computed for {team_count} teams")
    print(f"  📅 Latest rating date: {latest}")

    cursor.execute('''
        SELECT team, nrtg, ortg, drtg, win_pct, games_played
        FROM wnba_rolling_ratings
        WHERE game_date = ?
        ORDER BY nrtg DESC
    ''', (latest,))
    latest_ratings = cursor.fetchall()
    if latest_ratings:
        print(f"\n  Current ratings (as of {latest}):")
        print(f"  {'Team':<25} {'NRtg':>6} {'ORtg':>6} {'DRtg':>6} {'Win%':>6} {'GP':>4}")
        print(f"  {'-'*55}")
        for team, nrtg, ortg, drtg, wpct, gp in latest_ratings:
            print(f"  {team:<25} {nrtg:>+6.1f} {ortg:>6.1f} {drtg:>6.1f} {wpct:>6.1%} {gp:>4}")

    conn.close()
    print()


def check_wnba_star_availability(home_team, away_team, home_injuries_str, away_injuries_str):
    """Cross-reference ESPN injury report against prior-season top-5 players.
    Parses per-player entries from semicolon-delimited injury strings.
    Format expected: 'Player Name (Status - Injury Type); Player2 (Status)'
    Returns structured availability data for both teams."""
    import re

    conn = sqlite3.connect(get_sqlite_path())
    cursor = conn.cursor()

    cursor.execute('SELECT MAX(season) FROM wnba_top_players')
    row = cursor.fetchone()
    if not row or not row[0]:
        conn.close()
        return {'home': {}, 'away': {}}

    latest_season = row[0]

    def parse_injury_entries(inj_str):
        """Parse 'Name (Status - Detail); Name2 (Status)' into per-player dicts."""
        if not inj_str:
            return {}
        entries = {}
        for entry in re.split(r';\s*', inj_str):
            entry = entry.strip()
            if not entry:
                continue
            match = re.match(r'^(.+?)\s*\(([^)]+)\)', entry)
            if match:
                name = match.group(1).strip()
                status_str = match.group(2).strip().lower()
                if 'out' in status_str:
                    entries[name.lower()] = 'OUT'
                elif 'doubtful' in status_str:
                    entries[name.lower()] = 'DOUBTFUL'
                elif 'questionable' in status_str:
                    entries[name.lower()] = 'QUESTIONABLE'
                elif 'day-to-day' in status_str or 'day to day' in status_str:
                    entries[name.lower()] = 'DTD'
                elif 'probable' in status_str:
                    entries[name.lower()] = 'PROBABLE'
                else:
                    entries[name.lower()] = status_str.upper()
        return entries

    result = {'home': {}, 'away': {}}

    for side, team, inj_str in [('home', home_team, home_injuries_str),
                                 ('away', away_team, away_injuries_str)]:
        cursor.execute('''
            SELECT player_name, player_rank, ppg, rpg, apg
            FROM wnba_top_players
            WHERE season = ? AND team = ?
            ORDER BY player_rank
        ''', (latest_season, team))
        top_players = cursor.fetchall()

        if not top_players:
            continue

        injury_entries = parse_injury_entries(inj_str)

        stars_out = []
        stars_questionable = []
        total_ppg_at_risk = 0.0

        for name, rank, ppg, rpg, apg in top_players:
            name_lower = name.lower()
            last_name = name_lower.split()[-1] if name_lower.split() else ''

            player_status = None
            for inj_name, status in injury_entries.items():
                if name_lower in inj_name or inj_name in name_lower or last_name in inj_name:
                    player_status = status
                    break

            if not player_status:
                continue

            if player_status in ('OUT', 'DOUBTFUL'):
                stars_out.append({'name': name, 'rank': rank, 'ppg': ppg, 'status': player_status})
                total_ppg_at_risk += ppg
            elif player_status in ('QUESTIONABLE', 'DTD'):
                stars_questionable.append({'name': name, 'rank': rank, 'ppg': ppg, 'status': player_status})
                total_ppg_at_risk += ppg * 0.3

        star1_names_out = [s['name'] for s in stars_out]
        result[side] = {
            'top5_from_season': latest_season,
            'stars_out': stars_out,
            'stars_questionable': stars_questionable,
            'ppg_at_risk': round(total_ppg_at_risk, 1),
            'star1_available': not top_players or top_players[0][0] not in star1_names_out,
        }

    conn.close()
    return result


def setup_wnba_shadow_table(cursor):
    """Create shadow mode logging table for WNBA predictions."""
    cursor.execute('''CREATE TABLE IF NOT EXISTS wnba_shadow_picks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        game_id TEXT NOT NULL,
        game_date TEXT,
        home_team TEXT,
        away_team TEXT,
        spread_home REAL,
        predicted_margin REAL,
        model_edge REAL,
        adjusted_edge REAL,
        cover_prob REAL,
        sigma REAL,
        pick_side TEXT,
        pick_spread REAL,
        would_have_picked INTEGER DEFAULT 0,
        home_nrtg REAL,
        away_nrtg REAL,
        home_star_available INTEGER,
        away_star_available INTEGER,
        ppg_at_risk_home REAL,
        ppg_at_risk_away REAL,
        shrinkage REAL,
        edge_threshold REAL,
        home_score INTEGER,
        away_score INTEGER,
        spread_result TEXT,
        result TEXT,
        units REAL,
        graded_at TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(game_id)
    )''')


def run_wnba_shadow_predictions():
    """Run WNBA model predictions in shadow mode — log everything, publish nothing.
    Uses rolling ratings + prior-season player data for leak-free predictions."""
    from scipy.stats import norm
    import numpy as np

    print(f"\n{'='*60}")
    print("🔮 WNBA SHADOW MODE — PREDICTIONS (NOT PUBLISHED)")
    print(f"{'='*60}\n")

    conn = sqlite3.connect(get_sqlite_path())
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    setup_wnba_shadow_table(cursor)

    cursor.execute('''
        SELECT id, game_date, home_team, away_team, spread_home,
               home_injuries, away_injuries
        FROM wnba_games
        WHERE home_score IS NULL
        AND spread_home IS NOT NULL
        AND game_date >= date('now', '-1 day')
        ORDER BY game_date
    ''')
    upcoming = cursor.fetchall()

    if not upcoming:
        print("  No upcoming WNBA games with spreads.")
        conn.close()
        return

    print(f"  Found {len(upcoming)} upcoming WNBA games\n")

    SHRINKAGE = 0.7
    EDGE_THRESHOLD = 0.035
    SIGMA_DEFAULT = 11.0
    STANDARD_JUICE = 0.9091

    shadow_count = 0
    pick_count = 0

    for game in upcoming:
        game_id = game['id']
        game_date = game['game_date']
        home = game['home_team']
        away = game['away_team']
        spread_home = float(game['spread_home'])
        home_injuries = game['home_injuries'] or ''
        away_injuries = game['away_injuries'] or ''

        cursor.execute('''
            SELECT nrtg, ortg, drtg, margin_avg, margin_std, win_pct, games_played
            FROM wnba_rolling_ratings
            WHERE team = ?
            ORDER BY game_date DESC LIMIT 1
        ''', (home,))
        h_rating = cursor.fetchone()

        cursor.execute('''
            SELECT nrtg, ortg, drtg, margin_avg, margin_std, win_pct, games_played
            FROM wnba_rolling_ratings
            WHERE team = ?
            ORDER BY game_date DESC LIMIT 1
        ''', (away,))
        a_rating = cursor.fetchone()

        if not h_rating or not a_rating:
            print(f"  ⏭️  {away} @ {home} — insufficient rolling ratings, skipping")
            continue

        h_nrtg, h_ortg, h_drtg, h_margin, h_std, h_wpct, h_gp = h_rating
        a_nrtg, a_ortg, a_drtg, a_margin, a_std, a_wpct, a_gp = a_rating

        hca = 2.5
        model_margin = (h_margin - a_margin) / 2.0 + hca
        nrtg_margin = ((h_nrtg - a_nrtg) / 2.0) * 0.8 + hca
        raw_margin = (model_margin + nrtg_margin) / 2.0

        market_margin = -spread_home
        blended_margin = SHRINKAGE * raw_margin + (1 - SHRINKAGE) * market_margin

        sigma = (h_std + a_std) / 2.0
        sigma = max(7.0, min(13.0, sigma))

        z = (blended_margin + spread_home) / sigma
        cover_prob = float(norm.cdf(z))

        implied_prob = STANDARD_JUICE / (1 + STANDARD_JUICE)
        edge = cover_prob - implied_prob

        if cover_prob < 0.5:
            edge = (1 - cover_prob) - implied_prob
            pick_side = 'AWAY'
            pick_spread = -spread_home
        else:
            pick_side = 'HOME'
            pick_spread = spread_home

        spread_abs = abs(spread_home)
        if spread_abs <= 7:
            req_edge = EDGE_THRESHOLD
        elif spread_abs <= 11:
            req_edge = 0.05
        else:
            req_edge = 0.08

        would_pick = 1 if edge >= req_edge else 0

        avail = check_wnba_star_availability(home, away, home_injuries or '', away_injuries or '')

        cursor.execute('''INSERT OR REPLACE INTO wnba_shadow_picks
            (game_id, game_date, home_team, away_team, spread_home,
             predicted_margin, model_edge, adjusted_edge, cover_prob, sigma,
             pick_side, pick_spread, would_have_picked,
             home_nrtg, away_nrtg,
             home_star_available, away_star_available,
             ppg_at_risk_home, ppg_at_risk_away,
             shrinkage, edge_threshold, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
            (game_id, game_date, home, away, spread_home,
             round(blended_margin, 2), round(edge, 4), round(edge, 4),
             round(cover_prob, 4), round(sigma, 2),
             pick_side, round(pick_spread, 1), would_pick,
             round(h_nrtg, 2), round(a_nrtg, 2),
             1 if avail['home'].get('star1_available', True) else 0,
             1 if avail['away'].get('star1_available', True) else 0,
             avail['home'].get('ppg_at_risk', 0),
             avail['away'].get('ppg_at_risk', 0),
             SHRINKAGE, req_edge, datetime.now().isoformat()))

        shadow_count += 1
        if would_pick:
            pick_count += 1

        emoji = "✅" if would_pick else "⏸️"
        print(f"  {emoji} {away} @ {home} (spread {spread_home:+.1f})")
        print(f"     Model margin: {blended_margin:+.1f} | Edge: {edge:.1%} (need {req_edge:.1%}) | σ={sigma:.1f}")
        print(f"     NRtg: {home} {h_nrtg:+.1f} vs {away} {a_nrtg:+.1f}")
        if avail['home'].get('ppg_at_risk', 0) > 0 or avail['away'].get('ppg_at_risk', 0) > 0:
            print(f"     ⚠️  PPG at risk: {home} {avail['home'].get('ppg_at_risk', 0):.1f} | {away} {avail['away'].get('ppg_at_risk', 0):.1f}")
        print()

    conn.commit()
    conn.close()

    print(f"  📊 Shadow summary: {shadow_count} games analyzed, {pick_count} would have been picked\n")


def grade_wnba_shadow_picks():
    """Grade completed shadow picks by matching final scores."""
    print(f"\n{'='*60}")
    print("📝 GRADING WNBA SHADOW PICKS")
    print(f"{'='*60}\n")

    conn = sqlite3.connect(get_sqlite_path())
    cursor = conn.cursor()

    setup_wnba_shadow_table(cursor)

    cursor.execute('''
        SELECT sp.game_id, sp.pick_side, sp.pick_spread, sp.would_have_picked,
               g.home_score, g.away_score, g.spread_result
        FROM wnba_shadow_picks sp
        JOIN wnba_games g ON sp.game_id = g.id
        WHERE sp.result IS NULL
        AND g.home_score IS NOT NULL
    ''')
    ungraded = cursor.fetchall()

    if not ungraded:
        print("  No ungraded shadow picks.")
        conn.close()
        return

    graded = 0
    wins = 0
    losses = 0

    for game_id, pick_side, pick_spread, would_pick, hs, as_, spread_result in ungraded:
        margin = float(hs) - float(as_)

        if pick_side == 'HOME':
            adjusted = margin + pick_spread
        else:
            adjusted = -margin + pick_spread

        if adjusted > 0:
            result = 'WIN'
            units = 1.0
            if would_pick:
                wins += 1
        elif adjusted < 0:
            result = 'LOSS'
            units = -1.1
            if would_pick:
                losses += 1
        else:
            result = 'PUSH'
            units = 0.0

        cursor.execute('''UPDATE wnba_shadow_picks
            SET home_score = ?, away_score = ?, spread_result = ?,
                result = ?, units = ?, graded_at = ?
            WHERE game_id = ?''',
            (hs, as_, spread_result, result, round(units, 2),
             datetime.now().isoformat(), game_id))
        graded += 1

    conn.commit()

    cursor.execute('''
        SELECT COUNT(*), SUM(CASE WHEN result='WIN' THEN 1 ELSE 0 END),
               SUM(CASE WHEN result='LOSS' THEN 1 ELSE 0 END),
               SUM(units)
        FROM wnba_shadow_picks
        WHERE result IS NOT NULL AND would_have_picked = 1
    ''')
    total, total_wins, total_losses, total_units = cursor.fetchone()

    print(f"  ✅ Graded {graded} shadow picks")
    if total and total > 0:
        total_wins = total_wins or 0
        total_losses = total_losses or 0
        total_units = total_units or 0
        pct = total_wins / (total_wins + total_losses) * 100 if (total_wins + total_losses) > 0 else 0
        print(f"\n  📊 Shadow Record (would-pick only): {total_wins}-{total_losses} ({pct:.1f}%)")
        print(f"  💰 Shadow Units: {total_units:+.1f}u")

    conn.close()
    print()


def collect_wnba_odds():
    """Fetch today's WNBA odds from The Odds API with enriched data"""
    from sport_config import get_odds_api_url

    print(f"\n{'='*60}")
    print("🏀 WNBA ODDS COLLECTOR")
    print(f"{'='*60}\n")

    if not API_KEY:
        print("❌ No API key found")
        return

    team_data = get_wnba_team_data()
    injuries = get_wnba_injuries()

    PREFERRED_BOOKS = ['draftkings', 'fanduel', 'betmgm', 'caesars_sportsbook', 'pointsbetus', 'betrivers']
    BOOK_DISPLAY = {
        'draftkings': 'DraftKings', 'fanduel': 'FanDuel', 'betmgm': 'BetMGM',
        'caesars_sportsbook': 'Caesars', 'pointsbetus': 'PointsBet', 'betrivers': 'BetRivers',
    }

    url = get_odds_api_url('wnba')
    params = {
        'apiKey': API_KEY,
        'regions': 'us',
        'markets': 'spreads,totals,h2h',
        'oddsFormat': 'american',
        'bookmakers': ','.join(PREFERRED_BOOKS)
    }

    try:
        response = api_request_with_retry(url, params)
        if response is None or response.status_code != 200:
            print("❌ Failed to fetch WNBA odds")
            return

        games = response.json()
        print(f"✅ Found {len(games)} WNBA games")
        print(f"   API calls left: {API_USAGE['remaining']}/500\n")

        if not games:
            print("ℹ️  No WNBA games available today\n")
            return

        conn = sqlite3.connect(get_sqlite_path())
        cursor = conn.cursor()

        setup_wnba_table(cursor)

        stored = 0
        for game in games:
            game_id = game['id']
            home = game['home_team']
            away = game['away_team']
            commence_time = utc_to_eastern_date(game.get('commence_time', ''))
            game_time = game.get('commence_time') or None

            spread_home = None
            spread_away = None
            total = None
            home_ml = None
            away_ml = None
            best_home_odds = None
            best_away_odds = None
            best_home_book = None
            best_away_book = None

            def is_better_odds(new_odds, current_odds):
                if current_odds is None:
                    return True
                return new_odds > current_odds

            for bookmaker in game.get('bookmakers', []):
                book_key = bookmaker.get('key', '')
                book_name = BOOK_DISPLAY.get(book_key, book_key)
                for market in bookmaker.get('markets', []):
                    if market['key'] == 'spreads':
                        for outcome in market.get('outcomes', []):
                            if outcome['name'] == home:
                                if spread_home is None:
                                    spread_home = outcome.get('point')
                                price = outcome.get('price')
                                if price is not None and is_better_odds(price, best_home_odds):
                                    best_home_odds = price
                                    best_home_book = book_name
                            else:
                                if spread_away is None:
                                    spread_away = outcome.get('point')
                                price = outcome.get('price')
                                if price is not None and is_better_odds(price, best_away_odds):
                                    best_away_odds = price
                                    best_away_book = book_name
                    elif market['key'] == 'totals' and total is None:
                        total = market['outcomes'][0].get('point')
                    elif market['key'] == 'h2h':
                        for outcome in market.get('outcomes', []):
                            if outcome['name'] == home:
                                if home_ml is None or outcome['price'] > home_ml:
                                    home_ml = outcome['price']
                            else:
                                if away_ml is None or outcome['price'] > away_ml:
                                    away_ml = outcome['price']

            home_info = team_data.get(home, {})
            away_info = team_data.get(away, {})

            home_record = home_info.get('record', 'N/A')
            away_record = away_info.get('record', 'N/A')
            home_home_record = home_info.get('home_record', 'N/A')
            away_away_record = away_info.get('away_record', 'N/A')

            home_abbr = WNBA_TEAM_ABBR_MAP.get(home, '')
            away_abbr = WNBA_TEAM_ABBR_MAP.get(away, '')

            home_last5, home_last_game = get_wnba_team_schedule(home_abbr) if home_abbr else (None, None)
            away_last5, away_last_game = get_wnba_team_schedule(away_abbr) if away_abbr else (None, None)

            home_rest = calculate_rest_days(home_last_game)
            away_rest = calculate_rest_days(away_last_game)

            home_injuries = injuries.get(home, '')
            away_injuries = injuries.get(away, '')

            cursor.execute('SELECT id, spread_home_open FROM wnba_games WHERE id = ?', (game_id,))
            existing = cursor.fetchone()

            is_new_game = existing is None
            has_opening = existing and existing[1] is not None

            if is_new_game:
                cursor.execute('''INSERT INTO wnba_games
                    (id, game_date, game_time, home_team, away_team,
                     spread_home, spread_away, total, home_ml, away_ml, collected_at,
                     spread_home_open, total_open, home_ml_open, away_ml_open, open_collected_at,
                     home_record, away_record, home_home_record, away_away_record,
                     home_last5, away_last5, home_rest_days, away_rest_days,
                     home_injuries, away_injuries,
                     home_spread_odds, away_spread_odds,
                     home_spread_odds_open, away_spread_odds_open,
                     home_spread_book, away_spread_book,
                     commence_time)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                    (game_id, commence_time, game_time, home, away,
                     spread_home, spread_away, total, home_ml, away_ml,
                     datetime.now().isoformat(),
                     spread_home, total, home_ml, away_ml, datetime.now().isoformat(),
                     home_record, away_record, home_home_record, away_away_record,
                     home_last5, away_last5, home_rest, away_rest,
                     home_injuries, away_injuries,
                     best_home_odds, best_away_odds,
                     best_home_odds, best_away_odds,
                     best_home_book, best_away_book,
                     game.get('commence_time', '')))
                line_status = "📌 OPENING"
            else:
                cursor.execute('''UPDATE wnba_games SET
                    spread_home = ?, spread_away = ?, total = ?,
                    home_ml = ?, away_ml = ?, collected_at = ?,
                    game_time = ?,
                    home_record = ?, away_record = ?,
                    home_home_record = ?, away_away_record = ?,
                    home_last5 = ?, away_last5 = ?,
                    home_rest_days = ?, away_rest_days = ?,
                    home_injuries = ?, away_injuries = ?,
                    home_spread_odds = ?, away_spread_odds = ?,
                    home_spread_book = ?, away_spread_book = ?
                    WHERE id = ?''',
                    (spread_home, spread_away, total,
                     home_ml, away_ml, datetime.now().isoformat(),
                     game_time,
                     home_record, away_record, home_home_record, away_away_record,
                     home_last5, away_last5, home_rest, away_rest,
                     home_injuries, away_injuries,
                     best_home_odds, best_away_odds,
                     best_home_book, best_away_book,
                     game_id))

                if has_opening:
                    open_spread = existing[1]
                    if open_spread and spread_home:
                        movement = spread_home - open_spread
                        cursor.execute('UPDATE wnba_games SET line_movement = ? WHERE id = ?',
                                      (movement, game_id))
                        line_status = f"📊 CURRENT (moved {movement:+.1f})" if movement != 0 else "📊 CURRENT"
                    else:
                        line_status = "📊 CURRENT"
                else:
                    line_status = "📊 CURRENT"

            stored += 1
            spread_display = f"{spread_home:+.1f}" if spread_home else "N/A"
            print(f"{line_status} {away} @ {home}")
            print(f"   📈 Records: {away} ({away_record}) vs {home} ({home_record})")
            if spread_home:
                odds_info = ""
                if best_home_odds:
                    odds_info = f" ({best_home_odds:+d} @ {best_home_book})"
                print(f"   📉 Spread: {home} {spread_display}{odds_info}")
            if total:
                print(f"   📉 Total: {total}")
            if home_last5 or away_last5:
                print(f"   🔥 Form (L5): {away} [{away_last5 or 'N/A'}] vs {home} [{home_last5 or 'N/A'}]")
            if home_home_record != 'N/A' or away_away_record != 'N/A':
                print(f"   🏠 Splits: {home} home ({home_home_record}) | {away} away ({away_away_record})")
            if home_rest is not None or away_rest is not None:
                print(f"   😴 Rest: {home} ({home_rest or '?'} days) | {away} ({away_rest or '?'} days)")
            if home_injuries or away_injuries:
                if home_injuries:
                    print(f"   🏥 {home}: {home_injuries[:60]}...")
                if away_injuries:
                    print(f"   🏥 {away}: {away_injuries[:60]}...")
            print()

        conn.commit()
        conn.close()
        print(f"\n✅ Stored {stored} WNBA games\n")

    except Exception as e:
        print(f"❌ WNBA odds collection error: {e}")


# Main execution
if __name__ == "__main__":
    import sys

    setup_database()

    if len(sys.argv) > 1:
        if sys.argv[1] == '--close':
            collect_closing_lines()
        elif sys.argv[1] == '--report':
            generate_report()
        elif sys.argv[1] == '--viz':
            show_visualization()
        elif sys.argv[1] == '--wnba':
            collect_wnba_scores()
            collect_wnba_odds()
            update_wnba_rolling_ratings()
        elif sys.argv[1] == '--wnba-close':
            collect_wnba_closing_lines()
        elif sys.argv[1] == '--wnba-shadow':
            update_wnba_rolling_ratings()
            run_wnba_shadow_predictions()
        elif sys.argv[1] == '--wnba-grade':
            grade_wnba_shadow_picks()
        elif sys.argv[1] == '--wnba-ratings':
            update_wnba_rolling_ratings()
        elif sys.argv[1] == '--props':
            collect_player_props()
        else:
            print(f"Unknown command: {sys.argv[1]}")
    else:
        show_welcome()
        collect_yesterdays_scores()
        collect_todays_games()

    print("\n💡 Commands:")
    print("   python main.py              - Daily NBA collection (scores + lines)")
    print("   python main.py --close      - Capture NBA closing lines before games")
    print("   python main.py --props      - Collect NBA player props (pts/reb/ast)")
    print("   python main.py --wnba       - Collect WNBA scores + odds + rolling ratings")
    print("   python main.py --wnba-close - Capture WNBA closing lines before games")
    print("   python main.py --wnba-shadow - Run WNBA shadow predictions (log only)")
    print("   python main.py --wnba-grade - Grade completed WNBA shadow picks")
    print("   python main.py --wnba-ratings - Recompute all WNBA rolling ratings")
    print("   python main.py --report     - Show data collection report")
    print("   python main.py --viz    - Show progress visualization\n")
