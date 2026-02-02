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
            away_injuries TEXT
        )
    ''')
    
    # Add new columns if they don't exist
    new_columns = [
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
            
            # Save to database
            cursor.execute('''
                INSERT INTO games 
                (id, game_date, home_team, away_team, 
                 spread_home, spread_away, total, home_ml, away_ml, collected_at,
                 home_record, away_record, home_home_record, away_away_record,
                 home_last5, away_last5, home_rest_days, away_rest_days,
                 home_injuries, away_injuries)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    spread_home = excluded.spread_home,
                    spread_away = excluded.spread_away,
                    total = excluded.total,
                    home_ml = excluded.home_ml,
                    away_ml = excluded.away_ml,
                    collected_at = excluded.collected_at,
                    home_record = excluded.home_record,
                    away_record = excluded.away_record,
                    home_home_record = excluded.home_home_record,
                    away_away_record = excluded.away_away_record,
                    home_last5 = excluded.home_last5,
                    away_last5 = excluded.away_last5,
                    home_rest_days = excluded.home_rest_days,
                    away_rest_days = excluded.away_rest_days,
                    home_injuries = excluded.home_injuries,
                    away_injuries = excluded.away_injuries
            ''', (
                game_id, commence_time, home, away,
                spread_home, spread_away, total, home_ml, away_ml,
                datetime.now().isoformat(),
                home_record, away_record, home_home_record, away_away_record,
                home_last5, away_last5, home_rest, away_rest,
                home_injuries, away_injuries
            ))
            
            # Display enhanced info
            print(f"📊 {away} @ {home}")
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


# Main execution
if __name__ == "__main__":
    setup_database()
    collect_yesterdays_scores()
    collect_todays_games()
    print("\n💡 Run daily to collect data!\n")
