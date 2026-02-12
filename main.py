"""
🏀 SHARP PICKS - NBA DATA COLLECTOR
Run this daily to build your dataset
"""

import requests
import sqlite3
import os
import time
import random
import statistics
from datetime import datetime, timedelta

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

def setup_database():
    """Create database if it doesn't exist"""
    conn = sqlite3.connect('sharp_picks.db')
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
    ]
    
    for col_name, col_type in new_columns:
        try:
            cursor.execute(f'ALTER TABLE games ADD COLUMN {col_name} {col_type}')
        except:
            pass
    
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
        
        conn = sqlite3.connect('sharp_picks.db')
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
            
            game_date = yesterday.strftime('%Y-%m-%d')
            
            cursor.execute('''
                SELECT id, spread_home, total FROM games 
                WHERE game_date = ? 
                AND (home_team LIKE ? OR home_team LIKE ?)
                AND home_score IS NULL
            ''', (game_date, f'%{home_team.split()[-1]}%', f'%{home_team}%'))
            
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
    
    url = "https://api.the-odds-api.com/v4/sports/basketball_nba/odds/"
    params = {
        'apiKey': API_KEY,
        'regions': 'us',
        'markets': 'spreads,totals,h2h',
        'oddsFormat': 'american',
        'bookmakers': 'draftkings'
    }
    
    try:
        response = api_request_with_retry(url, params)
        
        if response is None:
            print("\n❌ Failed to connect after 3 attempts.")
            print("   Please check your internet connection and try again.\n")
            return
        
        if response.status_code != 200:
            print(f"\n❌ API Error {response.status_code}")
            print(f"   {response.text}\n")
            return
        
        games = response.json()
        
        print(f"✅ API Connected!")
        print(f"   Games found: {len(games)}")
        print(f"   API calls left: {API_USAGE['remaining']}/500\n")
        
        # Check API usage and warn if needed
        check_api_usage()
        
        if len(games) == 0:
            show_no_games_message()
            show_stats()
            return
        
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
            
            # Get game time
            game_time = game.get('commence_time', '')

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
                     bdl_home_avg_pts_against, bdl_away_avg_pts_against)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                            ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                ))
                line_status = "📌 OPENING"
            else:
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
                        bdl_home_avg_pts_against = ?, bdl_away_avg_pts_against = ?
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
                print(f"   📉 Spread: {home} {spread_home:+.1f}")
            if total:
                print(f"   📉 Total: {total}")
            if home_last5 or away_last5:
                print(f"   🔥 Form (L5): {away} [{away_last5 or 'N/A'}] vs {home} [{home_last5 or 'N/A'}]")
            if home_home_record or away_away_record:
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


def collect_closing_lines():
    """Collect closing lines for games starting soon (within 30 min)"""
    print("\n" + "="*60)
    print("⏰ COLLECTING CLOSING LINES")
    print("="*60 + "\n")
    
    if not API_KEY:
        print("❌ ERROR: No API key found!")
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
        
        # Check API usage and warn if needed
        check_api_usage()
        
        conn = sqlite3.connect('sharp_picks.db')
        cursor = conn.cursor()
        
        updated = 0
        
        for game in games:
            game_id = game['id']
            home = game['home_team']
            away = game['away_team']
            
            # Check if game exists and hasn't started
            cursor.execute('SELECT id, spread_home_open FROM games WHERE id = ? AND home_score IS NULL', (game_id,))
            existing = cursor.fetchone()
            
            if not existing:
                continue
            
            # Extract odds
            spread_home = None
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
                    elif market['key'] == 'totals':
                        total = market['outcomes'][0]['point']
                    elif market['key'] == 'h2h':
                        for outcome in market['outcomes']:
                            if outcome['name'] == home:
                                home_ml = outcome['price']
                            else:
                                away_ml = outcome['price']
            
            # Update closing line
            cursor.execute('''
                UPDATE games SET
                    spread_home_close = ?, total_close = ?,
                    home_ml_close = ?, away_ml_close = ?,
                    close_collected_at = ?
                WHERE id = ?
            ''', (spread_home, total, home_ml, away_ml, 
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


def show_visualization():
    """Display ASCII charts of collection progress"""
    print("\n" + "="*60)
    print("📈 SHARP PICKS - COLLECTION VISUALIZATION")
    print("="*60 + "\n")
    
    conn = sqlite3.connect('sharp_picks.db')
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
    
    conn = sqlite3.connect('sharp_picks.db')
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
    conn = sqlite3.connect('sharp_picks.db')
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


# Main execution
if __name__ == "__main__":
    import sys
    
    setup_database()
    
    # Check for command line argument
    if len(sys.argv) > 1:
        if sys.argv[1] == '--close':
            collect_closing_lines()
        elif sys.argv[1] == '--report':
            generate_report()
        elif sys.argv[1] == '--viz':
            show_visualization()
        else:
            print(f"Unknown command: {sys.argv[1]}")
    else:
        # Show welcome and run normal collection
        show_welcome()
        collect_yesterdays_scores()
        collect_todays_games()
    
    print("\n💡 Commands:")
    print("   python main.py          - Daily collection (scores + opening/current lines)")
    print("   python main.py --close  - Capture closing lines before games")
    print("   python main.py --report - Show data collection report")
    print("   python main.py --viz    - Show progress visualization\n")
