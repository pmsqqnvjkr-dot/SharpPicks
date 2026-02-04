"""
NBA Injuries Fetcher
Fetches current NBA injury reports and calculates team impact scores
"""

import os
import json
from datetime import datetime, timedelta
from balldontlie import BalldontlieAPI

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
    'Toronto Raptors': 'TOR', 'Utah Jazz': 'UTA', 'Washington Wizards': 'WAS'
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
    'Doubtful': 0.85,
    'Questionable': 0.5,
    'Probable': 0.15,
    'Day-To-Day': 0.4,
    'GTD': 0.5,
}

_injury_cache = {}
_cache_time = None
CACHE_DURATION = timedelta(hours=1)


def get_injuries():
    """Fetch current NBA injuries from BALLDONTLIE API"""
    global _injury_cache, _cache_time
    
    if _cache_time and datetime.now() - _cache_time < CACHE_DURATION:
        return _injury_cache
    
    api_key = os.environ.get('BALLDONTLIE_API_KEY')
    if not api_key:
        print("Warning: BALLDONTLIE_API_KEY not set, skipping injury data")
        return {}
    
    try:
        api = BalldontlieAPI(api_key=api_key)
        injuries_response = api.nba.injuries.list()
        
        injuries_by_team = {}
        
        for injury in injuries_response.data:
            team_name = injury.team.full_name if hasattr(injury, 'team') else None
            if not team_name:
                continue
                
            team_abbr = TEAM_ABBREV_MAP.get(team_name, team_name[:3].upper())
            
            if team_abbr not in injuries_by_team:
                injuries_by_team[team_abbr] = []
            
            player_name = f"{injury.player.first_name} {injury.player.last_name}" if hasattr(injury, 'player') else "Unknown"
            status = injury.status if hasattr(injury, 'status') else 'Unknown'
            reason = injury.comment if hasattr(injury, 'comment') else ''
            
            injuries_by_team[team_abbr].append({
                'player': player_name,
                'status': status,
                'reason': reason,
                'impact': get_player_impact(player_name, status)
            })
        
        _injury_cache = injuries_by_team
        _cache_time = datetime.now()
        
        print(f"Fetched injuries for {len(injuries_by_team)} teams")
        return injuries_by_team
        
    except Exception as e:
        print(f"Error fetching injuries: {e}")
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
        return f"{team_abbr}: {', '.join(key_outs[:2])} {'OUT' if len(key_outs) == 1 else 'OUT'} (+{score['injured_count'] - len(key_outs)} more)"
    else:
        return f"{team_abbr}: {score['injured_count']} player(s) injured (minor)"


if __name__ == '__main__':
    print("NBA Injury Report")
    print("=" * 50)
    
    injuries = get_injuries()
    
    if not injuries:
        print("No injury data available (API key may not be set)")
    else:
        for team, players in sorted(injuries.items()):
            print(f"\n{team}:")
            for p in players:
                print(f"  - {p['player']}: {p['status']} (impact: {p['impact']:.1f})")
