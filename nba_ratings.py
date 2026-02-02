"""
🏀 NBA RATINGS - Fetch team pace/offensive/defensive ratings
Uses NBA stats API for advanced team metrics
"""

import requests
import sqlite3
from datetime import datetime
import time

NBA_STATS_HEADERS = {
    'Host': 'stats.nba.com',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Accept': 'application/json, text/plain, */*',
    'Accept-Language': 'en-US,en;q=0.5',
    'Referer': 'https://stats.nba.com/',
    'x-nba-stats-origin': 'stats',
    'x-nba-stats-token': 'true',
    'Connection': 'keep-alive',
}

TEAM_ID_MAP = {
    'ATL': 1610612737, 'BOS': 1610612738, 'BKN': 1610612751, 'CHA': 1610612766,
    'CHI': 1610612741, 'CLE': 1610612739, 'DAL': 1610612742, 'DEN': 1610612743,
    'DET': 1610612765, 'GSW': 1610612744, 'HOU': 1610612745, 'IND': 1610612754,
    'LAC': 1610612746, 'LAL': 1610612747, 'MEM': 1610612763, 'MIA': 1610612748,
    'MIL': 1610612749, 'MIN': 1610612750, 'NOP': 1610612740, 'NYK': 1610612752,
    'OKC': 1610612760, 'ORL': 1610612753, 'PHI': 1610612755, 'PHX': 1610612756,
    'POR': 1610612757, 'SAC': 1610612758, 'SAS': 1610612759, 'TOR': 1610612761,
    'UTA': 1610612762, 'WAS': 1610612764
}

def ensure_ratings_table():
    """Create team_ratings table if not exists"""
    conn = sqlite3.connect('sharp_picks.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS team_ratings (
            team_abbr TEXT PRIMARY KEY,
            team_id INTEGER,
            pace REAL,
            off_rating REAL,
            def_rating REAL,
            net_rating REAL,
            wins INTEGER,
            losses INTEGER,
            last_updated TEXT
        )
    ''')
    
    conn.commit()
    conn.close()


def fetch_team_stats(season='2025-26'):
    """Fetch team advanced stats from NBA API"""
    print(f"\n📊 Fetching NBA team ratings for {season}...")
    
    url = 'https://stats.nba.com/stats/leaguedashteamstats'
    params = {
        'Conference': '',
        'DateFrom': '',
        'DateTo': '',
        'Division': '',
        'GameScope': '',
        'GameSegment': '',
        'Height': '',
        'LastNGames': 0,
        'LeagueID': '00',
        'Location': '',
        'MeasureType': 'Advanced',
        'Month': 0,
        'OpponentTeamID': 0,
        'Outcome': '',
        'PORound': 0,
        'PaceAdjust': 'N',
        'PerMode': 'PerGame',
        'Period': 0,
        'PlayerExperience': '',
        'PlayerPosition': '',
        'PlusMinus': 'N',
        'Rank': 'N',
        'Season': season,
        'SeasonSegment': '',
        'SeasonType': 'Regular Season',
        'ShotClockRange': '',
        'StarterBench': '',
        'TeamID': 0,
        'TwoWay': 0,
        'VsConference': '',
        'VsDivision': ''
    }
    
    try:
        response = requests.get(url, headers=NBA_STATS_HEADERS, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()
        
        headers = data['resultSets'][0]['headers']
        rows = data['resultSets'][0]['rowSet']
        
        team_stats = []
        for row in rows:
            stats = dict(zip(headers, row))
            team_stats.append({
                'team_id': stats.get('TEAM_ID'),
                'team_name': stats.get('TEAM_NAME'),
                'team_abbr': stats.get('TEAM_ABBREVIATION'),
                'wins': stats.get('W', 0),
                'losses': stats.get('L', 0),
                'pace': stats.get('PACE', 100.0),
                'off_rating': stats.get('OFF_RATING', 110.0),
                'def_rating': stats.get('DEF_RATING', 110.0),
                'net_rating': stats.get('NET_RATING', 0.0),
            })
        
        print(f"   ✅ Fetched stats for {len(team_stats)} teams")
        return team_stats
        
    except requests.exceptions.RequestException as e:
        print(f"   ⚠️ NBA API error: {e}")
        return None


def save_team_ratings(team_stats):
    """Save team ratings to database"""
    if not team_stats:
        return
    
    ensure_ratings_table()
    conn = sqlite3.connect('sharp_picks.db')
    cursor = conn.cursor()
    
    now = datetime.now().isoformat()
    
    for team in team_stats:
        cursor.execute('''
            INSERT OR REPLACE INTO team_ratings 
            (team_abbr, team_id, pace, off_rating, def_rating, net_rating, wins, losses, last_updated)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            team['team_abbr'],
            team['team_id'],
            team['pace'],
            team['off_rating'],
            team['def_rating'],
            team['net_rating'],
            team['wins'],
            team['losses'],
            now
        ))
    
    conn.commit()
    conn.close()
    print(f"   ✅ Saved ratings to database")


def get_team_ratings():
    """Get team ratings from database as dict"""
    ensure_ratings_table()
    conn = sqlite3.connect('sharp_picks.db')
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM team_ratings')
    rows = cursor.fetchall()
    conn.close()
    
    ratings = {}
    for row in rows:
        ratings[row[0]] = {
            'team_id': row[1],
            'pace': row[2],
            'off_rating': row[3],
            'def_rating': row[4],
            'net_rating': row[5],
            'wins': row[6],
            'losses': row[7],
            'last_updated': row[8]
        }
    
    return ratings


def update_ratings():
    """Main function to update team ratings"""
    current_year = datetime.now().year
    current_month = datetime.now().month
    
    if current_month >= 10:
        season = f"{current_year}-{str(current_year + 1)[2:]}"
    else:
        season = f"{current_year - 1}-{str(current_year)[2:]}"
    
    stats = fetch_team_stats(season)
    if stats:
        save_team_ratings(stats)
        return True
    return False


def show_ratings():
    """Display current team ratings"""
    ratings = get_team_ratings()
    
    if not ratings:
        print("\n⚠️ No team ratings in database. Run update first.")
        return
    
    print("\n" + "="*70)
    print("🏀 NBA TEAM RATINGS (Pace / Off Rating / Def Rating)")
    print("="*70)
    
    sorted_teams = sorted(ratings.items(), key=lambda x: x[1]['net_rating'], reverse=True)
    
    print(f"{'Team':<6} {'Pace':>8} {'OffRtg':>8} {'DefRtg':>8} {'NetRtg':>8} {'Record':>10}")
    print("-"*70)
    
    for abbr, data in sorted_teams:
        record = f"{data['wins']}-{data['losses']}"
        print(f"{abbr:<6} {data['pace']:>8.1f} {data['off_rating']:>8.1f} {data['def_rating']:>8.1f} {data['net_rating']:>+8.1f} {record:>10}")
    
    print()


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == 'update':
        update_ratings()
    else:
        show_ratings()
