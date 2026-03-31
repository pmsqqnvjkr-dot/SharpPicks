"""
MLB Umpire Module — Home plate umpire run-scoring features.

Fetches umpire assignments from MLB Stats API (free, no key required)
and provides career run-scoring averages per umpire.
"""

import requests
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

LEAGUE_AVG_RPGI = 8.8
LEAGUE_AVG_K_RATE = 8.3

UMP_CAREER_STATS = {
    'Angel Hernandez':       {'rpgi': 9.4, 'k_rate': 7.9},
    'CB Bucknor':            {'rpgi': 9.3, 'k_rate': 8.0},
    'Laz Diaz':              {'rpgi': 9.2, 'k_rate': 8.0},
    'Marvin Hudson':         {'rpgi': 9.2, 'k_rate': 8.1},
    'Doug Eddings':          {'rpgi': 9.1, 'k_rate': 8.1},
    'Tom Hallion':           {'rpgi': 9.1, 'k_rate': 8.0},
    'Bill Miller':           {'rpgi': 9.1, 'k_rate': 8.2},
    'Ron Kulpa':             {'rpgi': 9.0, 'k_rate': 8.1},
    'Hunter Wendelstedt':    {'rpgi': 9.0, 'k_rate': 8.0},
    'Sam Holbrook':          {'rpgi': 9.0, 'k_rate': 8.1},
    'Ted Barrett':           {'rpgi': 9.0, 'k_rate': 8.2},
    'Marty Foster':          {'rpgi': 9.0, 'k_rate': 8.1},
    'Phil Cuzzi':            {'rpgi': 9.0, 'k_rate': 8.2},
    'Mark Carlson':          {'rpgi': 8.9, 'k_rate': 8.2},
    'Alfonso Marquez':       {'rpgi': 8.9, 'k_rate': 8.2},
    'Tony Randazzo':         {'rpgi': 8.9, 'k_rate': 8.3},
    'Cory Blaser':           {'rpgi': 8.9, 'k_rate': 8.2},
    'Mike Estabrook':        {'rpgi': 8.9, 'k_rate': 8.3},
    'Chad Whitson':          {'rpgi': 8.9, 'k_rate': 8.2},
    'Dan Iassogna':          {'rpgi': 8.9, 'k_rate': 8.3},
    'Larry Vanover':         {'rpgi': 8.9, 'k_rate': 8.2},
    'Brian Knight':          {'rpgi': 8.9, 'k_rate': 8.2},
    'James Hoye':            {'rpgi': 8.9, 'k_rate': 8.3},
    'Jeff Nelson':           {'rpgi': 8.8, 'k_rate': 8.3},
    'Mark Wegner':           {'rpgi': 8.8, 'k_rate': 8.3},
    'Adrian Johnson':        {'rpgi': 8.8, 'k_rate': 8.3},
    'Andy Fletcher':         {'rpgi': 8.8, 'k_rate': 8.3},
    'Todd Tichenor':         {'rpgi': 8.8, 'k_rate': 8.3},
    'Will Little':           {'rpgi': 8.8, 'k_rate': 8.4},
    'Ben May':               {'rpgi': 8.8, 'k_rate': 8.3},
    'Lance Barrett':         {'rpgi': 8.8, 'k_rate': 8.3},
    'Jordan Baker':          {'rpgi': 8.8, 'k_rate': 8.4},
    'John Tumpane':          {'rpgi': 8.8, 'k_rate': 8.3},
    'D.J. Reyburn':          {'rpgi': 8.8, 'k_rate': 8.3},
    'Jeremie Rehak':         {'rpgi': 8.8, 'k_rate': 8.3},
    'Chris Segal':           {'rpgi': 8.7, 'k_rate': 8.4},
    'Ryan Blakney':          {'rpgi': 8.7, 'k_rate': 8.4},
    'Ryan Additon':          {'rpgi': 8.7, 'k_rate': 8.4},
    'Pat Hoberg':            {'rpgi': 8.7, 'k_rate': 8.4},
    'Tripp Gibson':          {'rpgi': 8.7, 'k_rate': 8.4},
    'Manny Gonzalez':        {'rpgi': 8.7, 'k_rate': 8.4},
    'Mark Ripperger':        {'rpgi': 8.7, 'k_rate': 8.3},
    'Alan Porter':           {'rpgi': 8.7, 'k_rate': 8.4},
    'Clint Vondrak':         {'rpgi': 8.7, 'k_rate': 8.4},
    'Stu Scheurwater':       {'rpgi': 8.7, 'k_rate': 8.4},
    'David Rackley':         {'rpgi': 8.7, 'k_rate': 8.5},
    'Edwin Moscoso':         {'rpgi': 8.7, 'k_rate': 8.5},
    'Adam Hamari':           {'rpgi': 8.7, 'k_rate': 8.5},
    'Nic Lentz':             {'rpgi': 8.7, 'k_rate': 8.4},
    'Chris Conroy':          {'rpgi': 8.7, 'k_rate': 8.5},
    'Shane Livensparger':    {'rpgi': 8.6, 'k_rate': 8.5},
    'Nestor Ceja':           {'rpgi': 8.6, 'k_rate': 8.5},
    'Jansen Visconti':       {'rpgi': 8.6, 'k_rate': 8.5},
    'Brennan Miller':        {'rpgi': 8.6, 'k_rate': 8.5},
    'John Libka':            {'rpgi': 8.6, 'k_rate': 8.5},
    'Dan Merzel':            {'rpgi': 8.6, 'k_rate': 8.5},
    'Lance Barksdale':       {'rpgi': 8.6, 'k_rate': 8.5},
    'Gabe Morales':          {'rpgi': 8.6, 'k_rate': 8.5},
    'Quinn Wolcott':         {'rpgi': 8.5, 'k_rate': 8.5},
    'Vic Carapazza':         {'rpgi': 8.5, 'k_rate': 8.6},
    'Nate Tomlinson':        {'rpgi': 8.5, 'k_rate': 8.5},
    'Derek Thomas':          {'rpgi': 8.5, 'k_rate': 8.6},
    'Nick Mahrley':          {'rpgi': 8.5, 'k_rate': 8.6},
    'Jeremy Riggs':          {'rpgi': 8.4, 'k_rate': 8.6},
    'David Arrieta':         {'rpgi': 8.4, 'k_rate': 8.6},
    'Dan Bellino':           {'rpgi': 8.4, 'k_rate': 8.6},
    'Roberto Ortiz':         {'rpgi': 8.4, 'k_rate': 8.6},
    'Ramon De Jesus':        {'rpgi': 8.4, 'k_rate': 8.6},
    'Jacob Metz':            {'rpgi': 8.4, 'k_rate': 8.7},
    'Alex Tosi':             {'rpgi': 8.3, 'k_rate': 8.7},
    'Mike Muchlinski':       {'rpgi': 8.3, 'k_rate': 8.7},
    'Brian O\'Nora':         {'rpgi': 8.3, 'k_rate': 8.7},
    'Tom Woodring':          {'rpgi': 8.3, 'k_rate': 8.7},
    'Carlos Torres':         {'rpgi': 8.2, 'k_rate': 8.8},
    'Junior Valentine':      {'rpgi': 8.2, 'k_rate': 8.8},
    'Erich Bacchus':         {'rpgi': 8.2, 'k_rate': 8.8},
    'John Bacon':            {'rpgi': 8.1, 'k_rate': 8.8},
    'Malachi Moore':         {'rpgi': 8.1, 'k_rate': 8.8},
    'Chad Fairchild':        {'rpgi': 8.0, 'k_rate': 8.9},
    'Scott Barry':           {'rpgi': 8.0, 'k_rate': 8.9},
}

MLB_TEAM_ID_MAP = {
    108: 'LAA', 109: 'ARI', 110: 'BAL', 111: 'BOS', 112: 'CHC',
    113: 'CIN', 114: 'CLE', 115: 'COL', 116: 'DET', 117: 'HOU',
    118: 'KC',  119: 'LAD', 120: 'WSH', 121: 'NYM', 133: 'OAK',
    134: 'PIT', 135: 'SD',  136: 'SEA', 137: 'SF',  138: 'STL',
    139: 'TB',  140: 'TEX', 141: 'TOR', 142: 'MIN', 143: 'PHI',
    144: 'ATL', 145: 'CHW', 146: 'MIA', 147: 'NYY', 158: 'MIL',
}


def fetch_umpire_assignments(game_date):
    """
    Fetch home plate umpire per game from MLB Stats API.
    Returns dict keyed by (home_team_abbrev, away_team_abbrev) -> umpire_name
    """
    if isinstance(game_date, str):
        date_str = game_date
    else:
        date_str = game_date.strftime('%Y-%m-%d')

    url = f"https://statsapi.mlb.com/api/v1/schedule?date={date_str}&sportId=1&hydrate=officials"
    assignments = {}

    try:
        resp = requests.get(url, timeout=15)
        if resp.status_code != 200:
            logger.warning(f"MLB Stats API returned {resp.status_code}")
            return assignments

        data = resp.json()
        for date_entry in data.get('dates', []):
            for game in date_entry.get('games', []):
                home_id = game.get('teams', {}).get('home', {}).get('team', {}).get('id')
                away_id = game.get('teams', {}).get('away', {}).get('team', {}).get('id')
                home_abbrev = MLB_TEAM_ID_MAP.get(home_id, '')
                away_abbrev = MLB_TEAM_ID_MAP.get(away_id, '')

                officials = game.get('officials', [])
                for official in officials:
                    if official.get('officialType', '') == 'Home Plate':
                        ump_name = official.get('official', {}).get('fullName', '')
                        if ump_name and home_abbrev and away_abbrev:
                            assignments[(home_abbrev, away_abbrev)] = ump_name
                        break

    except Exception as e:
        logger.error(f"Error fetching umpire assignments: {e}")

    return assignments


def get_umpire_features(umpire_name):
    """
    Return umpire run-scoring features for a given umpire name.
    Returns (rpgi, runs_delta, k_rate_delta).
    """
    if not umpire_name:
        return LEAGUE_AVG_RPGI, 0.0, 0.0

    stats = UMP_CAREER_STATS.get(umpire_name)
    if not stats:
        for name, s in UMP_CAREER_STATS.items():
            if umpire_name.split()[-1].lower() == name.split()[-1].lower():
                stats = s
                break

    if not stats:
        return LEAGUE_AVG_RPGI, 0.0, 0.0

    rpgi = stats['rpgi']
    runs_delta = rpgi - LEAGUE_AVG_RPGI
    k_delta = stats['k_rate'] - LEAGUE_AVG_K_RATE

    return rpgi, round(runs_delta, 2), round(k_delta, 2)


if __name__ == '__main__':
    today = datetime.now().strftime('%Y-%m-%d')
    print(f"Fetching umpire assignments for {today}...")
    assignments = fetch_umpire_assignments(today)
    if not assignments:
        print("No assignments found (may not be posted yet)")
    else:
        for (home, away), ump in assignments.items():
            rpgi, rd, kd = get_umpire_features(ump)
            print(f"  {away} @ {home}: {ump} (RPGI: {rpgi}, delta: {rd:+.2f}, K delta: {kd:+.2f})")
