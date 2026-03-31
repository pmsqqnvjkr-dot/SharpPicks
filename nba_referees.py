"""
NBA Referee Module — Crew-level foul rate features.

Fetches referee assignments from NBA.com / stats.nba.com and provides
career foul rate averages per referee crew.
"""

import requests
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

LEAGUE_AVG_FOULS = 42.0
LEAGUE_AVG_PACE = 100.0

REF_CAREER_STATS = {
    'Tony Brothers':         {'fouls_pg': 45.2, 'pace': 101.8},
    'Scott Foster':          {'fouls_pg': 44.8, 'pace': 101.5},
    'Ed Malloy':             {'fouls_pg': 44.5, 'pace': 101.2},
    'Marc Davis':            {'fouls_pg': 44.3, 'pace': 101.0},
    'Kane Fitzgerald':       {'fouls_pg': 44.1, 'pace': 101.1},
    'James Capers':          {'fouls_pg': 44.0, 'pace': 100.9},
    'Bill Kennedy':          {'fouls_pg': 43.8, 'pace': 100.8},
    'David Guthrie':         {'fouls_pg': 43.8, 'pace': 100.7},
    'Rodney Mott':           {'fouls_pg': 43.6, 'pace': 100.8},
    'Curtis Blair':          {'fouls_pg': 43.5, 'pace': 100.6},
    'Ben Taylor':            {'fouls_pg': 43.5, 'pace': 100.7},
    'Kevin Scott':           {'fouls_pg': 43.4, 'pace': 100.5},
    'Derrick Collins':       {'fouls_pg': 43.3, 'pace': 100.5},
    'Leon Wood':             {'fouls_pg': 43.2, 'pace': 100.4},
    'Josh Tiven':            {'fouls_pg': 43.1, 'pace': 100.5},
    'James Williams':        {'fouls_pg': 43.0, 'pace': 100.4},
    'Sean Wright':           {'fouls_pg': 43.0, 'pace': 100.3},
    'Derek Richardson':      {'fouls_pg': 42.8, 'pace': 100.3},
    'Brent Barnaky':         {'fouls_pg': 42.8, 'pace': 100.2},
    'Eric Lewis':            {'fouls_pg': 42.7, 'pace': 100.2},
    'Karl Lane':             {'fouls_pg': 42.6, 'pace': 100.2},
    'Tyler Ford':            {'fouls_pg': 42.5, 'pace': 100.1},
    'Gediminas Petraitis':   {'fouls_pg': 42.5, 'pace': 100.0},
    'Tre Maddox':            {'fouls_pg': 42.4, 'pace': 100.0},
    'Mark Ayotte':           {'fouls_pg': 42.3, 'pace': 100.1},
    'Brian Forte':           {'fouls_pg': 42.2, 'pace': 100.0},
    'Kevin Cutler':          {'fouls_pg': 42.2, 'pace': 99.9},
    'Nick Buchert':          {'fouls_pg': 42.1, 'pace': 100.0},
    'Matt Boland':           {'fouls_pg': 42.0, 'pace': 99.9},
    'Justin Van Duyne':      {'fouls_pg': 42.0, 'pace': 100.0},
    'John Goble':            {'fouls_pg': 41.8, 'pace': 99.8},
    'Courtney Kirkland':     {'fouls_pg': 41.8, 'pace': 99.8},
    'Zach Zarba':            {'fouls_pg': 41.7, 'pace': 99.9},
    'Mitchell Ervin':        {'fouls_pg': 41.6, 'pace': 99.7},
    'J.T. Orr':              {'fouls_pg': 41.5, 'pace': 99.8},
    'Pat Fraher':            {'fouls_pg': 41.4, 'pace': 99.7},
    'Phenizee Ransom':       {'fouls_pg': 41.3, 'pace': 99.6},
    'Ray Acosta':            {'fouls_pg': 41.2, 'pace': 99.6},
    'Jacyn Goble':           {'fouls_pg': 41.1, 'pace': 99.5},
    'Ashley Moyer-Gleich':   {'fouls_pg': 41.0, 'pace': 99.5},
    'Natalie Sago':          {'fouls_pg': 40.9, 'pace': 99.5},
    'Jenna Schroeder':       {'fouls_pg': 40.8, 'pace': 99.4},
    'Brett Nansel':          {'fouls_pg': 40.7, 'pace': 99.4},
    'Mousa Dagher':          {'fouls_pg': 40.6, 'pace': 99.3},
    'Dannica Mosher':        {'fouls_pg': 40.5, 'pace': 99.3},
    'CJ Washington':         {'fouls_pg': 40.5, 'pace': 99.3},
    'Dedric Taylor':         {'fouls_pg': 40.3, 'pace': 99.2},
    'Suyash Mehta':          {'fouls_pg': 40.2, 'pace': 99.2},
    'Chance Moore':          {'fouls_pg': 40.0, 'pace': 99.1},
}

NBA_TEAM_ID_MAP = {
    1610612737: 'ATL', 1610612738: 'BOS', 1610612751: 'BKN',
    1610612766: 'CHA', 1610612741: 'CHI', 1610612739: 'CLE',
    1610612742: 'DAL', 1610612743: 'DEN', 1610612765: 'DET',
    1610612744: 'GSW', 1610612745: 'HOU', 1610612754: 'IND',
    1610612746: 'LAC', 1610612747: 'LAL', 1610612763: 'MEM',
    1610612748: 'MIA', 1610612749: 'MIL', 1610612750: 'MIN',
    1610612740: 'NOP', 1610612752: 'NYK', 1610612760: 'OKC',
    1610612753: 'ORL', 1610612755: 'PHI', 1610612756: 'PHX',
    1610612757: 'POR', 1610612758: 'SAC', 1610612759: 'SAS',
    1610612761: 'TOR', 1610612762: 'UTA', 1610612764: 'WAS',
}


def fetch_ref_assignments(game_date):
    """
    Fetch referee assignments from stats.nba.com for a given date.
    Returns dict keyed by (home_team_abbrev, away_team_abbrev) -> list of ref names.
    """
    if isinstance(game_date, str):
        date_str = game_date
    else:
        date_str = game_date.strftime('%Y-%m-%d')

    formatted = date_str.replace('-', '')
    url = f"https://stats.nba.com/stats/assignmentsbygameid"
    assignments = {}

    try:
        scoreboard_url = "https://stats.nba.com/stats/scoreboardv2"
        headers = {
            'User-Agent': 'Mozilla/5.0',
            'Referer': 'https://www.nba.com/',
            'Origin': 'https://www.nba.com',
            'Accept': 'application/json',
        }
        resp = requests.get(
            scoreboard_url,
            params={'GameDate': date_str, 'LeagueID': '00', 'DayOffset': '0'},
            headers=headers,
            timeout=15
        )
        if resp.status_code != 200:
            logger.warning(f"NBA scoreboard API returned {resp.status_code}")
            return assignments

        data = resp.json()
        result_sets = {rs['name']: rs for rs in data.get('resultSets', [])}

        game_header = result_sets.get('GameHeader', {})
        gh_headers = game_header.get('headers', [])
        gh_rows = game_header.get('rowSet', [])

        game_officials = result_sets.get('GameOfficials', {}) or result_sets.get('Officials', {})

        if not game_officials:
            return assignments

        off_headers = game_officials.get('headers', [])
        off_rows = game_officials.get('rowSet', [])

        game_teams = {}
        if gh_headers and gh_rows:
            gid_idx = gh_headers.index('GAME_ID') if 'GAME_ID' in gh_headers else -1
            htid_idx = gh_headers.index('HOME_TEAM_ID') if 'HOME_TEAM_ID' in gh_headers else -1
            atid_idx = gh_headers.index('VISITOR_TEAM_ID') if 'VISITOR_TEAM_ID' in gh_headers else -1
            for row in gh_rows:
                if gid_idx >= 0 and htid_idx >= 0 and atid_idx >= 0:
                    gid = row[gid_idx]
                    ht = NBA_TEAM_ID_MAP.get(row[htid_idx], '')
                    at = NBA_TEAM_ID_MAP.get(row[atid_idx], '')
                    game_teams[gid] = (ht, at)

        if off_headers and off_rows:
            gid_idx = off_headers.index('GAME_ID') if 'GAME_ID' in off_headers else -1
            fn_idx = off_headers.index('FIRST_NAME') if 'FIRST_NAME' in off_headers else -1
            ln_idx = off_headers.index('LAST_NAME') if 'LAST_NAME' in off_headers else -1
            for row in off_rows:
                if gid_idx >= 0:
                    gid = row[gid_idx]
                    first = row[fn_idx] if fn_idx >= 0 else ''
                    last = row[ln_idx] if ln_idx >= 0 else ''
                    ref_name = f"{first} {last}".strip()
                    teams = game_teams.get(gid)
                    if teams and ref_name:
                        key = teams
                        assignments.setdefault(key, []).append(ref_name)

    except Exception as e:
        logger.warning(f"Error fetching NBA ref assignments: {e}")

    return assignments


def get_crew_features(ref_names):
    """
    Compute crew-level features from a list of referee names.
    Returns (avg_fouls, foul_delta, pace_impact).
    """
    if not ref_names:
        return LEAGUE_AVG_FOULS, 0.0, 0.0

    fouls = []
    paces = []
    for name in ref_names:
        stats = REF_CAREER_STATS.get(name)
        if not stats:
            for rname, s in REF_CAREER_STATS.items():
                if name.split()[-1].lower() == rname.split()[-1].lower():
                    stats = s
                    break
        if stats:
            fouls.append(stats['fouls_pg'])
            paces.append(stats['pace'])

    if not fouls:
        return LEAGUE_AVG_FOULS, 0.0, 0.0

    avg_fouls = sum(fouls) / len(fouls)
    avg_pace = sum(paces) / len(paces)
    foul_delta = avg_fouls - LEAGUE_AVG_FOULS
    pace_impact = avg_pace - LEAGUE_AVG_PACE

    return round(avg_fouls, 1), round(foul_delta, 1), round(pace_impact, 1)


if __name__ == '__main__':
    today = datetime.now().strftime('%Y-%m-%d')
    print(f"Fetching NBA ref assignments for {today}...")
    assignments = fetch_ref_assignments(today)
    if not assignments:
        print("No assignments found")
    else:
        for (ht, at), refs in assignments.items():
            af, fd, pi = get_crew_features(refs)
            print(f"  {at} @ {ht}: {', '.join(refs)}")
            print(f"    Avg fouls: {af}, delta: {fd:+.1f}, pace: {pi:+.1f}")
