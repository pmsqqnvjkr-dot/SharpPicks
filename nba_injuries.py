"""
NBA Injuries Fetcher
Fetches current NBA injury reports from ESPN (free, no API key required)
"""

import os
import json
import requests
from datetime import datetime, timedelta

TEAM_ABBREV_MAP = {
    'Atlanta Hawks': 'ATL', 'Boston Celtics': 'BOS', 'Brooklyn Nets': 'BKN',
    'Charlotte Hornets': 'CHA', 'Chicago Bulls': 'CHI', 'Cleveland Cavaliers': 'CLE',
    'Dallas Mavericks': 'DAL', 'Denver Nuggets': 'DEN', 'Detroit Pistons': 'DET',
    'Golden State Warriors': 'GSW', 'Houston Rockets': 'HOU', 'Indiana Pacers': 'IND',
    'Los Angeles Clippers': 'LAC', 'Los Angeles Lakers': 'LAL', 'Memphis Grizzlies': 'MEM',
    'Miami Heat': 'MIA', 'Milwaukee Bucks': 'MIL', 'Minnesota Timberwolves': 'MIN',
    'New Orleans Pelicans': 'NOP', 'New York Knicks': 'NYK', 'Oklahoma City Thunder': 'OKC',
    'Orlando Magic': 'ORL', 'Philadelphia 76ers': 'PHI', 'Phoenix Suns': 'PHX',
    'Portland Trail Blazers': 'POR', 'Sacramento Kings': 'SAC', 'San Antonio Spurs': 'SAS',
    'Toronto Raptors': 'TOR', 'Utah Jazz': 'UTA', 'Washington Wizards': 'WAS',
    'Atlanta': 'ATL', 'Boston': 'BOS', 'Brooklyn': 'BKN', 'Charlotte': 'CHA',
    'Chicago': 'CHI', 'Cleveland': 'CLE', 'Dallas': 'DAL', 'Denver': 'DEN',
    'Detroit': 'DET', 'Golden State': 'GSW', 'Houston': 'HOU', 'Indiana': 'IND',
    'LA Clippers': 'LAC', 'LA Lakers': 'LAL', 'Los Angeles': 'LAL', 'Memphis': 'MEM',
    'Miami': 'MIA', 'Milwaukee': 'MIL', 'Minnesota': 'MIN', 'New Orleans': 'NOP',
    'New York': 'NYK', 'Oklahoma City': 'OKC', 'Orlando': 'ORL', 'Philadelphia': 'PHI',
    'Phoenix': 'PHX', 'Portland': 'POR', 'Sacramento': 'SAC', 'San Antonio': 'SAS',
    'Toronto': 'TOR', 'Utah': 'UTA', 'Washington': 'WAS'
}

STAR_PLAYERS = {
    'Luka Doncic': 10, 'Giannis Antetokounmpo': 10, 'Nikola Jokic': 10,
    'Joel Embiid': 10, 'Jayson Tatum': 9, 'Kevin Durant': 9,
    'Stephen Curry': 9, 'LeBron James': 9, 'Anthony Davis': 9,
    'Shai Gilgeous-Alexander': 9, 'Donovan Mitchell': 8, 'Jaylen Brown': 8,
    'Ja Morant': 8, 'Anthony Edwards': 8, 'Trae Young': 8,
    'Devin Booker': 8, 'Damian Lillard': 8, 'Karl-Anthony Towns': 8,
    'Paolo Banchero': 7, 'Cade Cunningham': 7, 'Tyrese Haliburton': 7,
    'Darius Garland': 7, 'De\'Aaron Fox': 7, 'Zion Williamson': 7,
    'Jimmy Butler': 8, 'Bam Adebayo': 7, 'Jalen Brunson': 8,
    'Victor Wembanyama': 8, 'Tyrese Maxey': 7, 'Scottie Barnes': 7,
    'Evan Mobley': 7, 'Franz Wagner': 7, 'Lauri Markkanen': 7,
}

STATUS_IMPACT = {
    'Out': 1.0,
    'O': 1.0,
    'Doubtful': 0.85,
    'D': 0.85,
    'Questionable': 0.5,
    'Q': 0.5,
    'Probable': 0.15,
    'P': 0.15,
    'Day-To-Day': 0.4,
    'DTD': 0.4,
    'GTD': 0.5,
}

_injury_cache = {}
_cache_time = None
CACHE_DURATION = timedelta(hours=1)

ESPN_TEAMS = {
    'ATL': 1, 'BOS': 2, 'BKN': 17, 'CHA': 30, 'CHI': 4, 'CLE': 5,
    'DAL': 6, 'DEN': 7, 'DET': 8, 'GSW': 9, 'HOU': 10, 'IND': 11,
    'LAC': 12, 'LAL': 13, 'MEM': 29, 'MIA': 14, 'MIL': 15, 'MIN': 16,
    'NOP': 3, 'NYK': 18, 'OKC': 25, 'ORL': 19, 'PHI': 20, 'PHX': 21,
    'POR': 22, 'SAC': 23, 'SAS': 24, 'TOR': 28, 'UTA': 26, 'WAS': 27
}


def get_injuries():
    """Fetch current NBA injuries from ESPN API (free, no key required)"""
    global _injury_cache, _cache_time
    
    if _cache_time and datetime.now() - _cache_time < CACHE_DURATION:
        return _injury_cache
    
    injuries_by_team = {}
    
    try:
        url = "https://site.api.espn.com/apis/site/v2/sports/basketball/nba/injuries"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            
            for team_data in data.get('injuries', []):
                team_name = team_data.get('displayName', '')
                team_abbr = TEAM_ABBREV_MAP.get(team_name, team_name[:3].upper())
                
                if team_abbr not in injuries_by_team:
                    injuries_by_team[team_abbr] = []
                
                for injury in team_data.get('injuries', []):
                    athlete = injury.get('athlete', {})
                    player_name = athlete.get('displayName', 'Unknown')
                    status = injury.get('status', 'Unknown')
                    reason = injury.get('shortComment', '') or injury.get('longComment', '')
                    
                    injuries_by_team[team_abbr].append({
                        'player': player_name,
                        'status': status,
                        'reason': reason[:100] if reason else '',
                        'impact': get_player_impact(player_name, status)
                    })
            
            _injury_cache = injuries_by_team
            _cache_time = datetime.now()
            print(f"Fetched injuries for {len(injuries_by_team)} teams from ESPN")
            return injuries_by_team
        else:
            print(f"ESPN API returned status {response.status_code}")
            
    except Exception as e:
        print(f"Error fetching injuries from ESPN: {e}")
    
    return _injury_cache if _injury_cache else {}


def get_player_impact(player_name, status):
    """Calculate impact score for a player being out/questionable"""
    base_impact = STAR_PLAYERS.get(player_name, 3)
    status_multiplier = STATUS_IMPACT.get(status, 0.5)
    return base_impact * status_multiplier


def get_team_injury_score(team_abbr, injuries_data=None):
    """
    Get total injury impact score for a team
    Higher score = more impacted by injuries (bad for the team)
    """
    if injuries_data is None:
        injuries_data = get_injuries()
    
    team_injuries = injuries_data.get(team_abbr, [])
    total_impact = sum(inj['impact'] for inj in team_injuries)
    
    return {
        'team': team_abbr,
        'total_impact': total_impact,
        'injured_count': len(team_injuries),
        'key_players_out': [inj for inj in team_injuries if inj['impact'] >= 5],
        'injuries': team_injuries
    }


def get_injury_differential(home_team, away_team):
    """
    Calculate injury advantage/disadvantage
    Positive = home team has injury advantage (opponent more hurt)
    Negative = home team has injury disadvantage
    """
    injuries_data = get_injuries()
    
    home_score = get_team_injury_score(home_team, injuries_data)
    away_score = get_team_injury_score(away_team, injuries_data)
    
    differential = away_score['total_impact'] - home_score['total_impact']
    
    return {
        'differential': differential,
        'home_impact': home_score['total_impact'],
        'away_impact': away_score['total_impact'],
        'home_injuries': home_score['injuries'],
        'away_injuries': away_score['injuries'],
        'advantage': 'home' if differential > 0 else 'away' if differential < 0 else 'even'
    }


def format_injury_summary(team_abbr):
    """Get a human-readable injury summary for a team"""
    score = get_team_injury_score(team_abbr)
    
    if score['injured_count'] == 0:
        return f"{team_abbr}: Healthy"
    
    key_outs = [inj['player'] for inj in score['key_players_out']]
    
    if key_outs:
        return f"{team_abbr}: {', '.join(key_outs[:2])} OUT (+{score['injured_count'] - len(key_outs)} more)"
    else:
        return f"{team_abbr}: {score['injured_count']} player(s) injured (minor)"


if __name__ == '__main__':
    print("NBA Injury Report (via ESPN)")
    print("=" * 50)
    
    injuries = get_injuries()
    
    if not injuries:
        print("No injury data available")
    else:
        for team, players in sorted(injuries.items()):
            if players:
                print(f"\n{team}:")
                for p in players:
                    print(f"  - {p['player']}: {p['status']} (impact: {p['impact']:.1f})")
