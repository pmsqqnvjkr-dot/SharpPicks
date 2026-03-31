"""
Player Impact Module — Weighted injury impact using BallDontLie season averages.

Replaces flat keyword-counting injury features with player-importance-weighted
scores based on minutes per game (mpg) and points per game (ppg).
"""

import os
import re
import sqlite3
import logging
import requests
from datetime import datetime, timedelta
from difflib import SequenceMatcher

BDL_API_KEY = os.environ.get('BALLDONTLIE_API_KEY', '')
BDL_BASE = "https://api.balldontlie.io"
DB_PATH = os.environ.get('DATABASE_PATH', 'sharppicks.db')

STATUS_MULTIPLIER = {
    'out': 1.0,
    'o': 1.0,
    'doubtful': 0.75,
    'd': 0.75,
    'questionable': 0.5,
    'q': 0.5,
    'day-to-day': 0.35,
    'dtd': 0.35,
    'gtd': 0.5,
    'game-time decision': 0.5,
    'probable': 0.0,
    'p': 0.0,
    'available': 0.0,
}

DEFAULT_MPG = 12.0
DEFAULT_PPG = 6.0
STAR_MPG_THRESHOLD = 28.0
ROTATION_MPG_THRESHOLD = 15.0
MIN_GAMES_PLAYED = 5

PLAYER_ALIASES = {
    'pj washington': 'p.j. washington',
    'nic claxton': 'nicolas claxton',
    'herb jones': 'herbert jones',
    'cj mccollum': 'c.j. mccollum',
    'cj mccollom': 'c.j. mccollum',
    'rj barrett': 'r.j. barrett',
    'og anunoby': 'o.g. anunoby',
    'svi mykhailiuk': 'sviatoslav mykhailiuk',
    'nah\'shon hyland': 'bones hyland',
    'tj warren': 't.j. warren',
    'tj mcconnell': 't.j. mcconnell',
    'ej liddell': 'e.j. liddell',
    'gg jackson': 'g.g. jackson',
    'aj green': 'a.j. green',
    'aj griffin': 'a.j. griffin',
    'kt martin': 'kenyon martin jr.',
    'kj martin': 'kenyon martin jr.',
}

BDL_TEAM_ID_TO_ABBREV = {}
BDL_ABBREV_TO_TEAM_ID = {}

logger = logging.getLogger(__name__)


def _bdl_headers():
    return {"Authorization": BDL_API_KEY}


def _get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def ensure_tables():
    conn = _get_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS player_impact_cache (
            player_id INTEGER,
            player_name TEXT,
            team_id INTEGER,
            team_abbreviation TEXT,
            season INTEGER,
            mpg REAL,
            ppg REAL,
            games_played INTEGER,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (player_id, season)
        )
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_pic_team ON player_impact_cache(team_abbreviation, season)
    """)
    conn.commit()
    conn.close()


def _populate_team_maps():
    """Fetch BDL teams and build ID <-> abbreviation maps."""
    global BDL_TEAM_ID_TO_ABBREV, BDL_ABBREV_TO_TEAM_ID
    if BDL_TEAM_ID_TO_ABBREV:
        return
    if not BDL_API_KEY:
        logger.warning("No BALLDONTLIE_API_KEY, cannot populate team maps")
        return
    try:
        resp = requests.get(f"{BDL_BASE}/nba/v1/teams", headers=_bdl_headers(), timeout=15)
        if resp.status_code == 200:
            for t in resp.json().get('data', []):
                BDL_TEAM_ID_TO_ABBREV[t['id']] = t['abbreviation']
                BDL_ABBREV_TO_TEAM_ID[t['abbreviation']] = t['id']
            logger.info(f"Loaded {len(BDL_TEAM_ID_TO_ABBREV)} BDL team mappings")
    except Exception as e:
        logger.error(f"Failed to fetch BDL teams: {e}")


ESPN_STATS_URL = "https://site.web.api.espn.com/apis/common/v3/sports/basketball/nba/statistics/byathlete"


def refresh_player_impact_cache(season=None):
    """
    Fetch active players and their season averages from ESPN (free, no API key).
    Falls back to BDL if ESPN fails and BDL key is available.
    Stores results in player_impact_cache table.
    """
    ensure_tables()

    if season is None:
        now = datetime.now()
        season = now.year if now.month >= 10 else now.year

    espn_season = season if datetime.now().month >= 10 else season
    players_with_stats = 0
    errors = 0

    try:
        resp = requests.get(ESPN_STATS_URL, params={
            "season": espn_season, "limit": 500,
        }, timeout=30)

        if resp.status_code != 200:
            logger.error(f"ESPN byathlete stats error: {resp.status_code}")
            return {'error': f'ESPN stats API returned {resp.status_code}'}

        data = resp.json()
        athletes = data.get('athletes', [])
        logger.info(f"ESPN returned {len(athletes)} player stat entries")

        conn = _get_db()
        bdl_season = season - 1 if datetime.now().month < 10 else season

        for entry in athletes:
            try:
                athlete = entry.get('athlete', {})
                name = athlete.get('displayName', '')
                espn_id = int(athlete.get('id', 0))
                teams = athlete.get('teams', [])
                team_abbrev = teams[0].get('abbreviation', '') if teams else ''

                cats = entry.get('categories', [])
                gp = 0
                mpg = 0.0
                ppg = 0.0

                for cat in cats:
                    cat_name = cat.get('name', '')
                    totals = cat.get('totals', [])
                    values = cat.get('values', [])
                    if cat_name == 'general' and len(values) >= 2:
                        gp = int(values[0])
                        mpg = float(values[1])
                    elif cat_name == 'offensive' and len(values) >= 1:
                        ppg = float(values[0])

                if gp < 5 or mpg < 1.0:
                    continue

                conn.execute("""
                    INSERT OR REPLACE INTO player_impact_cache
                    (player_id, player_name, team_id, team_abbreviation, season, mpg, ppg, games_played, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (espn_id, name, 0, team_abbrev, bdl_season, round(mpg, 1), round(ppg, 1),
                      gp, datetime.now().isoformat()))
                players_with_stats += 1
            except Exception as e:
                errors += 1
                continue

        conn.commit()
        conn.close()

    except Exception as e:
        logger.error(f"refresh_player_impact_cache failed: {e}")
        return {'error': str(e)}

    result = {
        'season': bdl_season if 'bdl_season' in dir() else season,
        'players_cached': players_with_stats,
        'errors': errors,
    }
    logger.info(f"Player impact cache refreshed: {result}")
    return result


def get_team_roster(team_abbrev, season=None):
    """Get cached roster with mpg/ppg for a team."""
    if season is None:
        now = datetime.now()
        season = now.year if now.month >= 10 else now.year - 1
    try:
        conn = _get_db()
        rows = conn.execute(
            "SELECT player_name, mpg, ppg, games_played FROM player_impact_cache WHERE team_abbreviation = ? AND season = ?",
            (team_abbrev, season)
        ).fetchall()
        conn.close()
        return [{'name': r['player_name'], 'mpg': r['mpg'], 'ppg': r['ppg'], 'gp': r['games_played']} for r in rows]
    except Exception:
        return []


# ---------------------------------------------------------------------------
# Name matching
# ---------------------------------------------------------------------------

def _normalize_name(name):
    """Normalize a player name for matching."""
    n = name.lower().strip()
    n = re.sub(r'\b(jr\.?|sr\.?|iii|ii|iv)\b', '', n)
    n = n.replace('.', '').replace("'", '').replace('-', ' ')
    n = re.sub(r'\s+', ' ', n).strip()
    return n


def _last_name(normalized):
    parts = normalized.split()
    return parts[-1] if parts else ''


def _first_initial(normalized):
    parts = normalized.split()
    return parts[0][0] if parts and parts[0] else ''


def match_player(injury_name, team_roster):
    """
    Match an injured player name against a team roster.
    Returns the best matching roster entry or None.
    """
    norm = _normalize_name(injury_name)
    alias = PLAYER_ALIASES.get(norm)
    if alias:
        norm = _normalize_name(alias)

    best_match = None
    best_score = 0

    for player in team_roster:
        pnorm = _normalize_name(player['name'])
        if norm == pnorm:
            return player

        injury_last = _last_name(norm)
        player_last = _last_name(pnorm)
        if injury_last == player_last:
            injury_first = _first_initial(norm)
            player_first = _first_initial(pnorm)
            if injury_first == player_first:
                return player
            score = 0.85
        else:
            score = SequenceMatcher(None, norm, pnorm).ratio()

        if score > best_score:
            best_score = score
            best_match = player

    return best_match if best_score > 0.65 else None


# ---------------------------------------------------------------------------
# ESPN injury string parsing
# ---------------------------------------------------------------------------

def parse_injury_string(injury_text):
    """
    Parse ESPN injury string into structured entries.
    Input: "Joel Embiid (knee) - Out, Tyrese Maxey (foot) - Questionable"
    Output: [{'name': 'Joel Embiid', 'status': 'out'}, ...]
    """
    if not injury_text or not isinstance(injury_text, str) or injury_text.strip() == '':
        return []

    entries = []
    for segment in injury_text.split(','):
        segment = segment.strip()
        if not segment:
            continue

        status = None
        for s in STATUS_MULTIPLIER:
            pattern = re.compile(r'\b' + re.escape(s) + r'\b', re.IGNORECASE)
            if pattern.search(segment):
                status = s
                break

        if status is None:
            for keyword in ['out', 'questionable', 'doubtful', 'day-to-day', 'probable']:
                if keyword in segment.lower():
                    status = keyword
                    break

        if status is None:
            status = 'questionable'

        name = re.sub(r'\(.*?\)', '', segment)
        name = re.sub(r'\s*-\s*(Out|Questionable|Doubtful|Day-To-Day|Probable|GTD|O|D|Q|P)\s*$', '', name, flags=re.IGNORECASE)
        name = name.strip().rstrip(',').strip()

        if name and len(name) > 1:
            entries.append({'name': name, 'status': status.lower()})

    return entries


# ---------------------------------------------------------------------------
# Weighted impact computation
# ---------------------------------------------------------------------------

def compute_weighted_injury_impact(injury_string, team_abbrev, season=None):
    """
    Compute player-impact-weighted injury features for a team.

    Returns dict with:
        weighted_impact: sum of mpg * status_multiplier for injured players
        mpg_at_risk: same as weighted_impact (aliased for clarity)
        ppg_at_risk: sum of ppg * status_multiplier
        star_out: bool — any 28+ mpg player listed Out
        num_rotation_out: count of 15+ mpg players Out
    """
    result = {
        'weighted_impact': 0.0,
        'mpg_at_risk': 0.0,
        'ppg_at_risk': 0.0,
        'star_out': False,
        'num_rotation_out': 0,
    }

    entries = parse_injury_string(injury_string)
    if not entries:
        return result

    roster = get_team_roster(team_abbrev, season)

    total_mpg = 0.0
    total_ppg = 0.0
    star_out = False
    rotation_out = 0

    for entry in entries:
        name = entry['name']
        status = entry['status']
        multiplier = STATUS_MULTIPLIER.get(status, 0.25)

        if multiplier == 0.0:
            continue

        matched = match_player(name, roster) if roster else None

        if matched and matched.get('gp', 0) >= MIN_GAMES_PLAYED:
            mpg = matched['mpg']
            ppg = matched['ppg']
        else:
            mpg = DEFAULT_MPG
            ppg = DEFAULT_PPG

        total_mpg += mpg * multiplier
        total_ppg += ppg * multiplier

        if status == 'out' and mpg >= STAR_MPG_THRESHOLD:
            star_out = True
        if status == 'out' and mpg >= ROTATION_MPG_THRESHOLD:
            rotation_out += 1

    result['weighted_impact'] = round(total_mpg, 1)
    result['mpg_at_risk'] = round(total_mpg, 1)
    result['ppg_at_risk'] = round(total_ppg, 1)
    result['star_out'] = star_out
    result['num_rotation_out'] = rotation_out

    return result


def compute_game_injury_features(home_injuries, away_injuries, home_abbrev, away_abbrev, season=None):
    """
    Compute all 10 injury features for a single game.
    Returns a dict ready to merge into the game DataFrame row.
    """
    home = compute_weighted_injury_impact(home_injuries, home_abbrev, season)
    away = compute_weighted_injury_impact(away_injuries, away_abbrev, season)

    return {
        'home_mpg_at_risk': home['mpg_at_risk'],
        'away_mpg_at_risk': away['mpg_at_risk'],
        'injury_mpg_diff': away['mpg_at_risk'] - home['mpg_at_risk'],
        'home_ppg_at_risk': home['ppg_at_risk'],
        'away_ppg_at_risk': away['ppg_at_risk'],
        'injury_ppg_diff': away['ppg_at_risk'] - home['ppg_at_risk'],
        'home_star_out': 1 if home['star_out'] else 0,
        'away_star_out': 1 if away['star_out'] else 0,
        'home_rotation_out': home['num_rotation_out'],
        'away_rotation_out': away['num_rotation_out'],
    }


def mpg_at_risk_edge_penalty(mpg_at_risk):
    """
    Graduated edge penalty based on mpg_at_risk for the picked-side favorite.
    Replaces the old keyword-counting penalty.
    """
    if mpg_at_risk < 30:
        return 0.0
    if mpg_at_risk < 50:
        return 2.0
    if mpg_at_risk < 70:
        return 3.0
    return 4.0


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    print("Testing player impact module...")

    test_string = "Joel Embiid (knee) - Out, Tyrese Maxey (foot) - Questionable, KJ Martin (ankle) - Out"
    parsed = parse_injury_string(test_string)
    print(f"\nParsed entries: {parsed}")

    result = compute_weighted_injury_impact(test_string, 'PHI')
    print(f"\nWeighted impact for PHI: {result}")

    print("\nRefreshing cache (requires BDL API key)...")
    refresh_result = refresh_player_impact_cache()
    print(f"Refresh result: {refresh_result}")
