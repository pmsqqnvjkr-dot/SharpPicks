"""
MLB Bullpen Fatigue Module — Computes rolling reliever workload scores.

Fetches recent game pitching logs from ESPN box scores to identify
which relievers pitched and how much, then computes a fatigue score.
"""

import requests
import logging
import sqlite3
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

RECENCY_WEIGHTS = {1: 1.0, 2: 0.6, 3: 0.3}

ESPN_MLB_TEAM_MAP = {
    'ATL': 15, 'ARI': 29, 'BAL': 1, 'BOS': 2, 'CHC': 16,
    'CHW': 4, 'CIN': 17, 'CLE': 5, 'COL': 27, 'DET': 6,
    'HOU': 18, 'KC': 7, 'LAA': 3, 'LAD': 19, 'MIA': 28,
    'MIL': 8, 'MIN': 9, 'NYM': 21, 'NYY': 10, 'OAK': 11,
    'PHI': 22, 'PIT': 23, 'SD': 25, 'SEA': 12, 'SF': 26,
    'STL': 24, 'TB': 30, 'TEX': 13, 'TOR': 14, 'WSH': 20,
}

HEAVY_BULLPEN_IP_THRESHOLD = 4.0


def _parse_innings(ip_str):
    """Parse innings pitched string like '6.1' -> 6.333"""
    try:
        parts = str(ip_str).split('.')
        full = int(parts[0])
        thirds = int(parts[1]) if len(parts) > 1 else 0
        return full + thirds / 3.0
    except (ValueError, IndexError):
        return 0.0


def fetch_recent_pitching_logs(team_abbrev, lookback_days=3, game_date=None):
    """
    Fetch recent game pitching logs for a team from ESPN.
    Returns list of dicts with pitcher appearances per game.
    Each entry: {'date': str, 'pitchers': [{'name': str, 'ip': float, 'is_starter': bool}]}
    """
    espn_id = ESPN_MLB_TEAM_MAP.get(team_abbrev)
    if not espn_id:
        return []

    if game_date is None:
        base_date = datetime.now()
    elif isinstance(game_date, str):
        base_date = datetime.strptime(game_date, '%Y-%m-%d')
    else:
        base_date = game_date

    logs = []
    try:
        url = f"https://site.api.espn.com/apis/site/v2/sports/baseball/mlb/teams/{espn_id}/schedule"
        headers = {'User-Agent': 'Mozilla/5.0'}
        resp = requests.get(url, headers=headers, timeout=15)
        if resp.status_code != 200:
            logger.warning(f"ESPN schedule API returned {resp.status_code} for {team_abbrev}")
            return []

        data = resp.json()
        events = data.get('events', [])

        recent_game_ids = []
        for event in events:
            game_date_str = event.get('date', '')[:10]
            try:
                gd = datetime.strptime(game_date_str, '%Y-%m-%d')
            except (ValueError, TypeError):
                continue
            days_ago = (base_date - gd).days
            if 1 <= days_ago <= lookback_days:
                status = event.get('competitions', [{}])[0].get('status', {}).get('type', {}).get('name', '')
                if status == 'STATUS_FINAL':
                    game_id = event.get('id', '')
                    if game_id:
                        recent_game_ids.append((game_id, game_date_str, days_ago))

        for game_id, gdate, days_ago in recent_game_ids:
            try:
                box_url = f"https://site.api.espn.com/apis/site/v2/sports/baseball/mlb/summary?event={game_id}"
                box_resp = requests.get(box_url, headers=headers, timeout=15)
                if box_resp.status_code != 200:
                    continue
                box_data = box_resp.json()

                boxscore = box_data.get('boxscore', {})
                players_list = boxscore.get('players', [])

                for team_players in players_list:
                    team_info = team_players.get('team', {})
                    team_id = team_info.get('id', '')
                    if str(team_id) != str(espn_id):
                        continue

                    pitchers = []
                    for stat_group in team_players.get('statistics', []):
                        if stat_group.get('name', '') != 'pitching':
                            continue
                        athletes = stat_group.get('athletes', [])
                        for i, athlete in enumerate(athletes):
                            name = athlete.get('athlete', {}).get('displayName', '')
                            stats_arr = athlete.get('stats', [])
                            ip = _parse_innings(stats_arr[0]) if stats_arr else 0.0
                            pitchers.append({
                                'name': name,
                                'ip': ip,
                                'is_starter': (i == 0),
                            })

                    if pitchers:
                        logs.append({
                            'date': gdate,
                            'days_ago': days_ago,
                            'pitchers': pitchers,
                        })
                    break

            except Exception as e:
                logger.warning(f"Error fetching box score {game_id}: {e}")
                continue

    except Exception as e:
        logger.error(f"Error fetching schedule for {team_abbrev}: {e}")

    return logs


def compute_bullpen_fatigue(logs):
    """
    Compute bullpen fatigue score from recent pitching logs.

    Returns dict:
        fatigue_score: float, recency-weighted reliever IP over last 3 days
        heavy_usage_yesterday: 1 if bullpen threw 4+ IP yesterday, else 0
    """
    result = {'fatigue_score': 0.0, 'heavy_usage_yesterday': 0}

    if not logs:
        return result

    total_weighted_ip = 0.0

    for game_log in logs:
        days_ago = game_log.get('days_ago', 3)
        weight = RECENCY_WEIGHTS.get(days_ago, 0.2)
        relievers_ip = sum(
            p['ip'] for p in game_log.get('pitchers', []) if not p['is_starter']
        )
        total_weighted_ip += relievers_ip * weight

        if days_ago == 1 and relievers_ip >= HEAVY_BULLPEN_IP_THRESHOLD:
            result['heavy_usage_yesterday'] = 1

    result['fatigue_score'] = round(total_weighted_ip, 2)
    return result


def get_team_bullpen_fatigue(team_abbrev, game_date=None):
    """
    High-level: fetch logs and compute fatigue for one team.
    Returns (fatigue_score, heavy_usage_yesterday).
    """
    logs = fetch_recent_pitching_logs(team_abbrev, lookback_days=3, game_date=game_date)
    result = compute_bullpen_fatigue(logs)
    return result['fatigue_score'], result['heavy_usage_yesterday']


if __name__ == '__main__':
    import sys
    team = sys.argv[1] if len(sys.argv) > 1 else 'NYY'
    print(f"Computing bullpen fatigue for {team}...")
    fatigue, heavy = get_team_bullpen_fatigue(team)
    print(f"  Fatigue score: {fatigue}")
    print(f"  Heavy usage yesterday: {'Yes' if heavy else 'No'}")
