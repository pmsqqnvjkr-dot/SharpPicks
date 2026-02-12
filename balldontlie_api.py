"""
BallDontLie API Integration
Fetches team advanced stats and season averages for model enrichment
"""

import os
import json
import requests
from datetime import datetime, timedelta

API_KEY = os.environ.get('BALLDONTLIE_API_KEY')
BASE_URL = "https://api.balldontlie.io"
CACHE_FILE = 'bdl_cache.json'
CACHE_TTL_HOURS = 12

TEAM_ABBREV_TO_BDL = {
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
}

BDL_NAME_TO_FULL = {v: k for k, v in TEAM_ABBREV_TO_BDL.items()}


def _headers():
    return {"Authorization": API_KEY}


def _load_cache():
    if not os.path.exists(CACHE_FILE):
        return None
    try:
        with open(CACHE_FILE, 'r') as f:
            cache = json.load(f)
        cached_at = datetime.fromisoformat(cache.get('cached_at', '2000-01-01'))
        if datetime.now() - cached_at < timedelta(hours=CACHE_TTL_HOURS):
            return cache.get('data')
    except Exception:
        pass
    return None


def _save_cache(data):
    try:
        with open(CACHE_FILE, 'w') as f:
            json.dump({'cached_at': datetime.now().isoformat(), 'data': data}, f)
    except Exception:
        pass


def get_teams():
    """Fetch all NBA teams and their IDs"""
    if not API_KEY:
        print("   ⚠️ No BALLDONTLIE_API_KEY found")
        return {}

    try:
        resp = requests.get(
            f"{BASE_URL}/nba/v1/teams",
            headers=_headers(),
            timeout=15
        )
        if resp.status_code == 200:
            teams = {}
            for t in resp.json().get('data', []):
                teams[t['full_name']] = t['id']
            return teams
        else:
            print(f"   ⚠️ BDL teams API error: {resp.status_code}")
            return {}
    except Exception as e:
        print(f"   ⚠️ BDL teams exception: {e}")
        return {}


def get_team_season_stats():
    """Fetch team stats from BallDontLie using games endpoint (free tier)"""
    if not API_KEY:
        print("   ⚠️ No BALLDONTLIE_API_KEY found")
        return {}

    cached = _load_cache()
    if cached:
        print("   ✅ BDL: Using cached team stats")
        return cached

    print("   📡 Fetching BallDontLie team stats...")

    try:
        team_stats = _fetch_recent_game_stats()
        if team_stats:
            _save_cache(team_stats)
        return team_stats

    except Exception as e:
        print(f"   ⚠️ BDL exception: {e}")
        return {}


def _fetch_recent_game_stats():
    """Fetch recent game results for scoring averages and win rates"""
    try:
        all_games = []
        end_date = datetime.now().strftime('%Y-%m-%d')

        for days_back in [14, 30]:
            start_date = (datetime.now() - timedelta(days=days_back)).strftime('%Y-%m-%d')
            cursor = None

            while True:
                params = {
                    "start_date": start_date,
                    "end_date": end_date,
                    "per_page": 100,
                }
                if cursor:
                    params["cursor"] = cursor

                resp = requests.get(
                    f"{BASE_URL}/nba/v1/games",
                    headers=_headers(),
                    params=params,
                    timeout=15
                )

                if resp.status_code != 200:
                    print(f"   ⚠️ BDL games error: {resp.status_code}")
                    break

                data = resp.json()
                batch = data.get('data', [])
                all_games.extend(batch)

                next_cursor = data.get('meta', {}).get('next_cursor')
                if not next_cursor or len(batch) < 100:
                    break
                cursor = next_cursor

            if all_games:
                break

        if not all_games:
            print("   ⚠️ BDL: No games found")
            return {}

        team_scores = {}

        for g in all_games:
            if g.get('status') != 'Final':
                continue

            home = g.get('home_team', {}).get('full_name', '')
            away = g.get('visitor_team', {}).get('full_name', '')
            home_score = g.get('home_team_score', 0)
            away_score = g.get('visitor_team_score', 0)

            if home and home_score:
                if home not in team_scores:
                    team_scores[home] = {'pts_for': [], 'pts_against': [], 'wins': 0, 'losses': 0}
                team_scores[home]['pts_for'].append(home_score)
                team_scores[home]['pts_against'].append(away_score)
                if home_score > away_score:
                    team_scores[home]['wins'] += 1
                else:
                    team_scores[home]['losses'] += 1

            if away and away_score:
                if away not in team_scores:
                    team_scores[away] = {'pts_for': [], 'pts_against': [], 'wins': 0, 'losses': 0}
                team_scores[away]['pts_for'].append(away_score)
                team_scores[away]['pts_against'].append(home_score)
                if away_score > home_score:
                    team_scores[away]['wins'] += 1
                else:
                    team_scores[away]['losses'] += 1

        result = {}
        for team, scores in team_scores.items():
            if scores['pts_for']:
                avg_pts = sum(scores['pts_for']) / len(scores['pts_for'])
                avg_pts_against = sum(scores['pts_against']) / len(scores['pts_against'])
                total_games = scores['wins'] + scores['losses']
                win_pct = round(scores['wins'] / max(total_games, 1), 3)

                result[team] = {
                    'win_pct': win_pct,
                    'bdl_avg_pts_l14': round(avg_pts, 1),
                    'bdl_avg_pts_against_l14': round(avg_pts_against, 1),
                    'bdl_scoring_margin_l14': round(avg_pts - avg_pts_against, 1),
                    'bdl_games_l14': len(scores['pts_for']),
                }

        print(f"   ✅ BDL: Loaded recent stats for {len(result)} teams ({len(all_games)} games)")
        return result

    except Exception as e:
        print(f"   ⚠️ BDL recent games error: {e}")
        return {}


def get_team_data_for_game(team_name, bdl_stats):
    """Get BDL stats for a specific team"""
    return bdl_stats.get(team_name, {})


def test_connection():
    """Test BallDontLie API connection"""
    print("\n" + "=" * 50)
    print("TESTING BALLDONTLIE API CONNECTION")
    print("=" * 50 + "\n")

    if not API_KEY:
        print("No BALLDONTLIE_API_KEY found")
        return False

    print(f"API Key found: {API_KEY[:10]}...")

    try:
        resp = requests.get(
            f"{BASE_URL}/nba/v1/teams",
            headers=_headers(),
            timeout=15
        )

        print(f"Response status: {resp.status_code}")

        if resp.status_code == 200:
            teams = resp.json().get('data', [])
            print(f"Connection successful! Found {len(teams)} teams")
            return True
        else:
            print(f"API Error: {resp.status_code}")
            print(f"Response: {resp.text[:200]}")
            return False

    except Exception as e:
        print(f"Connection error: {e}")
        return False


if __name__ == '__main__':
    test_connection()
    stats = get_team_season_stats()
    for team, data in list(stats.items())[:5]:
        print(f"\n{team}:")
        for k, v in data.items():
            print(f"  {k}: {v}")
