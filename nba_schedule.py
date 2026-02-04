"""
NBA Schedule & Fatigue Analysis Module
Calculates rest days, back-to-backs, travel distance, and altitude effects
"""
import os
import requests
from datetime import datetime, timedelta
from functools import lru_cache

TEAM_CITIES = {
    'ATL': {'city': 'Atlanta', 'lat': 33.757, 'lon': -84.396, 'altitude': 1050, 'timezone': 'EST'},
    'BOS': {'city': 'Boston', 'lat': 42.366, 'lon': -71.062, 'altitude': 20, 'timezone': 'EST'},
    'BKN': {'city': 'Brooklyn', 'lat': 40.683, 'lon': -73.976, 'altitude': 30, 'timezone': 'EST'},
    'CHA': {'city': 'Charlotte', 'lat': 35.225, 'lon': -80.839, 'altitude': 751, 'timezone': 'EST'},
    'CHI': {'city': 'Chicago', 'lat': 41.881, 'lon': -87.674, 'altitude': 594, 'timezone': 'CST'},
    'CLE': {'city': 'Cleveland', 'lat': 41.497, 'lon': -81.688, 'altitude': 653, 'timezone': 'EST'},
    'DAL': {'city': 'Dallas', 'lat': 32.790, 'lon': -96.810, 'altitude': 430, 'timezone': 'CST'},
    'DEN': {'city': 'Denver', 'lat': 39.749, 'lon': -105.010, 'altitude': 5280, 'timezone': 'MST'},
    'DET': {'city': 'Detroit', 'lat': 42.341, 'lon': -83.055, 'altitude': 600, 'timezone': 'EST'},
    'GSW': {'city': 'San Francisco', 'lat': 37.768, 'lon': -122.388, 'altitude': 52, 'timezone': 'PST'},
    'HOU': {'city': 'Houston', 'lat': 29.751, 'lon': -95.362, 'altitude': 80, 'timezone': 'CST'},
    'IND': {'city': 'Indianapolis', 'lat': 39.764, 'lon': -86.156, 'altitude': 715, 'timezone': 'EST'},
    'LAC': {'city': 'Los Angeles', 'lat': 34.043, 'lon': -118.267, 'altitude': 305, 'timezone': 'PST'},
    'LAL': {'city': 'Los Angeles', 'lat': 34.043, 'lon': -118.267, 'altitude': 305, 'timezone': 'PST'},
    'MEM': {'city': 'Memphis', 'lat': 35.138, 'lon': -90.051, 'altitude': 337, 'timezone': 'CST'},
    'MIA': {'city': 'Miami', 'lat': 25.781, 'lon': -80.187, 'altitude': 6, 'timezone': 'EST'},
    'MIL': {'city': 'Milwaukee', 'lat': 43.045, 'lon': -87.917, 'altitude': 617, 'timezone': 'CST'},
    'MIN': {'city': 'Minneapolis', 'lat': 44.980, 'lon': -93.276, 'altitude': 830, 'timezone': 'CST'},
    'NOP': {'city': 'New Orleans', 'lat': 29.949, 'lon': -90.082, 'altitude': 3, 'timezone': 'CST'},
    'NYK': {'city': 'New York', 'lat': 40.751, 'lon': -73.994, 'altitude': 33, 'timezone': 'EST'},
    'OKC': {'city': 'Oklahoma City', 'lat': 35.463, 'lon': -97.515, 'altitude': 1201, 'timezone': 'CST'},
    'ORL': {'city': 'Orlando', 'lat': 28.539, 'lon': -81.384, 'altitude': 82, 'timezone': 'EST'},
    'PHI': {'city': 'Philadelphia', 'lat': 39.901, 'lon': -75.172, 'altitude': 39, 'timezone': 'EST'},
    'PHX': {'city': 'Phoenix', 'lat': 33.446, 'lon': -112.071, 'altitude': 1086, 'timezone': 'MST'},
    'POR': {'city': 'Portland', 'lat': 45.532, 'lon': -122.667, 'altitude': 50, 'timezone': 'PST'},
    'SAC': {'city': 'Sacramento', 'lat': 38.580, 'lon': -121.500, 'altitude': 30, 'timezone': 'PST'},
    'SAS': {'city': 'San Antonio', 'lat': 29.427, 'lon': -98.438, 'altitude': 650, 'timezone': 'CST'},
    'TOR': {'city': 'Toronto', 'lat': 43.643, 'lon': -79.379, 'altitude': 249, 'timezone': 'EST'},
    'UTA': {'city': 'Salt Lake City', 'lat': 40.768, 'lon': -111.901, 'altitude': 4226, 'timezone': 'MST'},
    'WAS': {'city': 'Washington', 'lat': 38.898, 'lon': -77.021, 'altitude': 125, 'timezone': 'EST'},
}

TIMEZONE_OFFSET = {
    'EST': 0, 'CST': -1, 'MST': -2, 'PST': -3
}

TEAM_NAME_TO_ABBREV = {
    'Atlanta Hawks': 'ATL', 'Boston Celtics': 'BOS', 'Brooklyn Nets': 'BKN',
    'Charlotte Hornets': 'CHA', 'Chicago Bulls': 'CHI', 'Cleveland Cavaliers': 'CLE',
    'Dallas Mavericks': 'DAL', 'Denver Nuggets': 'DEN', 'Detroit Pistons': 'DET',
    'Golden State Warriors': 'GSW', 'Houston Rockets': 'HOU', 'Indiana Pacers': 'IND',
    'LA Clippers': 'LAC', 'Los Angeles Clippers': 'LAC', 'Los Angeles Lakers': 'LAL',
    'LA Lakers': 'LAL', 'Memphis Grizzlies': 'MEM', 'Miami Heat': 'MIA',
    'Milwaukee Bucks': 'MIL', 'Minnesota Timberwolves': 'MIN', 'New Orleans Pelicans': 'NOP',
    'New York Knicks': 'NYK', 'Oklahoma City Thunder': 'OKC', 'Orlando Magic': 'ORL',
    'Philadelphia 76ers': 'PHI', 'Phoenix Suns': 'PHX', 'Portland Trail Blazers': 'POR',
    'Sacramento Kings': 'SAC', 'San Antonio Spurs': 'SAS', 'Toronto Raptors': 'TOR',
    'Utah Jazz': 'UTA', 'Washington Wizards': 'WAS',
    'Hawks': 'ATL', 'Celtics': 'BOS', 'Nets': 'BKN', 'Hornets': 'CHA', 'Bulls': 'CHI',
    'Cavaliers': 'CLE', 'Mavericks': 'DAL', 'Nuggets': 'DEN', 'Pistons': 'DET',
    'Warriors': 'GSW', 'Rockets': 'HOU', 'Pacers': 'IND', 'Clippers': 'LAC',
    'Lakers': 'LAL', 'Grizzlies': 'MEM', 'Heat': 'MIA', 'Bucks': 'MIL',
    'Timberwolves': 'MIN', 'Pelicans': 'NOP', 'Knicks': 'NYK', 'Thunder': 'OKC',
    'Magic': 'ORL', '76ers': 'PHI', 'Sixers': 'PHI', 'Suns': 'PHX',
    'Trail Blazers': 'POR', 'Blazers': 'POR', 'Kings': 'SAC', 'Spurs': 'SAS',
    'Raptors': 'TOR', 'Jazz': 'UTA', 'Wizards': 'WAS'
}

def get_team_abbrev(team_name):
    """Convert team name to abbreviation"""
    if team_name in TEAM_NAME_TO_ABBREV:
        return TEAM_NAME_TO_ABBREV[team_name]
    for name, abbrev in TEAM_NAME_TO_ABBREV.items():
        if name in team_name or team_name in name:
            return abbrev
    return None

def calculate_distance(team1_abbrev, team2_abbrev):
    """Calculate approximate distance in miles between two teams"""
    import math
    
    if team1_abbrev not in TEAM_CITIES or team2_abbrev not in TEAM_CITIES:
        return 0
    
    city1 = TEAM_CITIES[team1_abbrev]
    city2 = TEAM_CITIES[team2_abbrev]
    
    lat1, lon1 = math.radians(city1['lat']), math.radians(city1['lon'])
    lat2, lon2 = math.radians(city2['lat']), math.radians(city2['lon'])
    
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
    c = 2 * math.asin(math.sqrt(a))
    
    return round(c * 3956, 0)

def get_timezone_change(from_team, to_team):
    """Calculate timezone change in hours"""
    if from_team not in TEAM_CITIES or to_team not in TEAM_CITIES:
        return 0
    
    from_tz = TIMEZONE_OFFSET[TEAM_CITIES[from_team]['timezone']]
    to_tz = TIMEZONE_OFFSET[TEAM_CITIES[to_team]['timezone']]
    
    return abs(to_tz - from_tz)

def get_altitude_factor(team_abbrev):
    """Get altitude effect - Denver and Utah have significant home court advantage due to altitude"""
    if team_abbrev not in TEAM_CITIES:
        return 0
    
    altitude = TEAM_CITIES[team_abbrev]['altitude']
    
    if altitude >= 5000:
        return 2.5
    elif altitude >= 4000:
        return 1.5
    elif altitude >= 3000:
        return 0.5
    return 0

def calculate_fatigue_score(rest_days, is_b2b, travel_miles, timezone_change, altitude_factor, is_away):
    """
    Calculate fatigue score (negative = more tired, positive = well rested)
    Returns a score from -5 to +3
    """
    score = 0
    
    if rest_days == 0:
        score -= 2.0
    elif rest_days == 1:
        score -= 0.5
    elif rest_days == 2:
        score += 1.0
    elif rest_days >= 3:
        score += 1.5
    
    if is_b2b:
        score -= 1.5
    
    if travel_miles > 2000:
        score -= 1.0
    elif travel_miles > 1000:
        score -= 0.5
    
    if timezone_change >= 3:
        score -= 1.0
    elif timezone_change >= 2:
        score -= 0.5
    
    if is_away and altitude_factor > 0:
        score -= altitude_factor * 0.5
    
    return round(max(-5, min(3, score)), 1)

def get_schedule_factors(home_team, away_team, home_last_game=None, away_last_game=None, home_prev_location=None, away_prev_location=None):
    """
    Get schedule-based fatigue factors for both teams
    
    Args:
        home_team: Home team name or abbreviation
        away_team: Away team name or abbreviation
        home_last_game: Dict with 'date' and 'location' of home team's last game
        away_last_game: Dict with 'date' and 'location' of away team's last game
        home_prev_location: Previous game location for home team (team abbrev)
        away_prev_location: Previous game location for away team (team abbrev)
    
    Returns:
        Dict with fatigue analysis for both teams
    """
    home_abbrev = get_team_abbrev(home_team) if len(home_team) > 3 else home_team
    away_abbrev = get_team_abbrev(away_team) if len(away_team) > 3 else away_team
    
    if not home_abbrev or not away_abbrev:
        return None
    
    today = datetime.now().date()
    
    home_rest = 2
    away_rest = 2
    home_b2b = False
    away_b2b = False
    
    if home_last_game and 'date' in home_last_game:
        try:
            last_date = datetime.strptime(home_last_game['date'], '%Y-%m-%d').date()
            home_rest = (today - last_date).days
            home_b2b = home_rest <= 1
        except:
            pass
    
    if away_last_game and 'date' in away_last_game:
        try:
            last_date = datetime.strptime(away_last_game['date'], '%Y-%m-%d').date()
            away_rest = (today - last_date).days
            away_b2b = away_rest <= 1
        except:
            pass
    
    away_travel = 0
    away_tz_change = 0
    if away_prev_location:
        away_travel = calculate_distance(away_prev_location, home_abbrev)
        away_tz_change = get_timezone_change(away_prev_location, home_abbrev)
    
    home_travel = 0
    home_tz_change = 0
    if home_prev_location and home_prev_location != home_abbrev:
        home_travel = calculate_distance(home_prev_location, home_abbrev)
        home_tz_change = get_timezone_change(home_prev_location, home_abbrev)
    
    altitude = get_altitude_factor(home_abbrev)
    
    home_fatigue = calculate_fatigue_score(
        home_rest, home_b2b, home_travel, home_tz_change, 0, False
    )
    
    away_fatigue = calculate_fatigue_score(
        away_rest, away_b2b, away_travel, away_tz_change, altitude, True
    )
    
    fatigue_edge = home_fatigue - away_fatigue
    
    if fatigue_edge > 1.5:
        advantage = f"{home_abbrev} well-rested edge"
    elif fatigue_edge < -1.5:
        advantage = f"{away_abbrev} well-rested edge"
    else:
        advantage = "Even rest situation"
    
    factors = []
    if home_b2b:
        factors.append(f"{home_abbrev} on B2B")
    if away_b2b:
        factors.append(f"{away_abbrev} on B2B")
    if altitude >= 2:
        factors.append(f"Altitude advantage ({TEAM_CITIES[home_abbrev]['altitude']}ft)")
    if away_travel > 1500:
        factors.append(f"{away_abbrev} traveled {int(away_travel)} miles")
    if away_tz_change >= 2:
        factors.append(f"{away_abbrev} crossed {away_tz_change} time zones")
    
    return {
        'home_team': home_abbrev,
        'away_team': away_abbrev,
        'home_rest_days': home_rest,
        'away_rest_days': away_rest,
        'home_b2b': home_b2b,
        'away_b2b': away_b2b,
        'home_fatigue_score': home_fatigue,
        'away_fatigue_score': away_fatigue,
        'fatigue_edge': round(fatigue_edge, 1),
        'advantage': advantage,
        'altitude_factor': altitude,
        'away_travel_miles': away_travel,
        'factors': factors
    }

def get_simple_schedule_factors(home_team, away_team, home_rest=2, away_rest=2, away_prev_city=None):
    """
    Simplified version when full schedule data isn't available
    """
    home_abbrev = get_team_abbrev(home_team) if len(home_team) > 3 else home_team
    away_abbrev = get_team_abbrev(away_team) if len(away_team) > 3 else away_team
    
    if not home_abbrev or not away_abbrev:
        return None
    
    home_b2b = home_rest <= 1
    away_b2b = away_rest <= 1
    
    away_travel = 0
    if away_prev_city:
        away_travel = calculate_distance(away_prev_city, home_abbrev)
    
    altitude = get_altitude_factor(home_abbrev)
    
    home_fatigue = calculate_fatigue_score(home_rest, home_b2b, 0, 0, 0, False)
    away_fatigue = calculate_fatigue_score(away_rest, away_b2b, away_travel, 0, altitude, True)
    
    fatigue_edge = home_fatigue - away_fatigue
    
    factors = []
    if home_b2b:
        factors.append(f"{home_abbrev} B2B")
    if away_b2b:
        factors.append(f"{away_abbrev} B2B")
    if altitude >= 2:
        factors.append(f"Altitude ({int(TEAM_CITIES[home_abbrev]['altitude'])}ft)")
    
    return {
        'home_fatigue': home_fatigue,
        'away_fatigue': away_fatigue,
        'fatigue_edge': round(fatigue_edge, 1),
        'home_b2b': home_b2b,
        'away_b2b': away_b2b,
        'altitude': altitude,
        'factors': factors
    }
