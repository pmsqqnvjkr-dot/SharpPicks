"""
MLB Bullpen Fatigue Module — Computes rolling reliever workload scores.

Fetches recent game pitching logs from ESPN box scores to identify
which relievers pitched and how much, then computes a fatigue score.
"""

import requests
import logging
import sqlite3
import json
import os
import hashlib
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

# League-average bullpen workload fallback used when ESPN returns no
# pitching logs for the requested date (e.g., older seasons whose schedule
# isn't surfaced by the team-schedule endpoint, off-season/All-Star windows,
# or transient ESPN errors). Calibration: ~2-3 relievers @ ~1.0 IP under
# recency weight 1.0 ≈ a 3.0 weighted-IP score. Using a non-zero default
# keeps the feature distribution centered on a sensible league mean instead
# of collapsing every fallback row to 0.0 (which previously made the four
# bullpen features zero-variance during MLB training).
LEAGUE_AVG_FATIGUE = 3.0
LEAGUE_AVG_HEAVY_USAGE = 0

# Per-process flag so we only warn ONCE per training session when ESPN
# returns no logs, instead of spamming WARN per-row.
_warned_no_data = False

_BULLPEN_CACHE_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), '.cache', 'bullpen'
)
try:
    os.makedirs(_BULLPEN_CACHE_DIR, exist_ok=True)
except Exception:
    pass


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
        # Pin the schedule request to the season of base_date. Without the
        # season query param ESPN returns the *current* season only, so any
        # historical training row (e.g. 2023-2024 dates during a 2026
        # training run) saw zero events and silently fell through to the
        # (0.0, 0) default — the root cause of the zero-variance drop.
        season_year = base_date.year
        url = (
            f"https://site.api.espn.com/apis/site/v2/sports/baseball/mlb/"
            f"teams/{espn_id}/schedule?season={season_year}"
        )
        headers = {'User-Agent': 'Mozilla/5.0'}
        resp = requests.get(url, headers=headers, timeout=8)
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
                box_resp = requests.get(box_url, headers=headers, timeout=8)
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
                        # ESPN switched the pitching stat-group identifier
                        # from `name` to `type`; check both so old and new
                        # response shapes work. Previously this filter never
                        # matched (`name` is empty in current responses),
                        # which is the underlying bug that made every row
                        # produce 0 pitchers and the (0.0, 0) zero-variance
                        # default.
                        sg_kind = stat_group.get('type', '') or stat_group.get('name', '')
                        if sg_kind != 'pitching':
                            continue
                        athletes = stat_group.get('athletes', [])
                        for i, athlete in enumerate(athletes):
                            name = athlete.get('athlete', {}).get('displayName', '')
                            stats_arr = athlete.get('stats', [])
                            ip = _parse_innings(stats_arr[0]) if stats_arr else 0.0
                            # ESPN pitching stat array: [IP, H, R, ER, BB,
                            # K, HR, ERA]. ER lives at index 3. Captured
                            # so the bullpen-form (14d ERA) feature can
                            # compute (ER*9)/IP without a second fetch.
                            er = 0
                            if len(stats_arr) > 3:
                                try:
                                    er = int(float(stats_arr[3]))
                                except (TypeError, ValueError):
                                    er = 0
                            # Prefer ESPN's explicit `starter` flag; fall
                            # back to "first listed pitcher is the starter"
                            # for older payload shapes.
                            is_starter = bool(athlete.get('starter', i == 0))
                            pitchers.append({
                                'name': name,
                                'ip': ip,
                                'er': er,
                                'is_starter': is_starter,
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

    When ESPN returns no usable pitching logs for the requested date
    (historical season, off-season, transient API failure), we fall back
    to a league-average fatigue score rather than (0.0, 0). The previous
    silent zero default caused all four bullpen features to be dropped at
    training as zero-variance.
    """
    global _warned_no_data
    logs = fetch_recent_pitching_logs(team_abbrev, lookback_days=3, game_date=game_date)
    if not logs:
        if not _warned_no_data:
            logger.warning(
                f"No ESPN bullpen data for {team_abbrev} game_date={game_date}; "
                f"falling back to league-average fatigue ({LEAGUE_AVG_FATIGUE} IP). "
                f"This warning is suppressed for the rest of the process."
            )
            _warned_no_data = True
        return LEAGUE_AVG_FATIGUE, LEAGUE_AVG_HEAVY_USAGE
    result = compute_bullpen_fatigue(logs)
    return result['fatigue_score'], result['heavy_usage_yesterday']


def _cached_bullpen(team_abbrev, game_date):
    """
    Disk-cached wrapper around get_team_bullpen_fatigue.

    Training calls bullpen for ~1500 rows × 2 teams = ~3000 ESPN requests
    per run. The JSON disk cache (one tiny file per team-date pair) makes
    repeat runs essentially free and lets the very first run be the only
    expensive one. Cache files live in mlb_bullpen.py's sibling .cache/
    directory, which is gitignored.
    """
    if not team_abbrev or not game_date:
        return LEAGUE_AVG_FATIGUE, LEAGUE_AVG_HEAVY_USAGE
    try:
        key = hashlib.md5(f"{team_abbrev}:{game_date}".encode()).hexdigest()
        cache_path = os.path.join(_BULLPEN_CACHE_DIR, f"{key}.json")
    except Exception:
        return get_team_bullpen_fatigue(team_abbrev, game_date=game_date)

    if os.path.exists(cache_path):
        try:
            with open(cache_path) as f:
                d = json.load(f)
            return float(d.get('fatigue', LEAGUE_AVG_FATIGUE)), int(d.get('heavy', LEAGUE_AVG_HEAVY_USAGE))
        except Exception:
            pass

    fatigue, heavy = get_team_bullpen_fatigue(team_abbrev, game_date=game_date)
    try:
        with open(cache_path, 'w') as f:
            json.dump({'fatigue': fatigue, 'heavy': heavy}, f)
    except Exception:
        pass
    return fatigue, heavy


LEAGUE_AVG_BULLPEN_ERA = 4.20


def _parse_er(stat_str):
    """Earned runs is stat index 3 in ESPN's pitching stat array
    [IP, H, R, ER, BB, K, HR, ERA]. Returns 0 on parse failure rather
    than raising so a malformed row doesn't poison the per-team total.
    """
    try:
        return int(float(stat_str))
    except Exception:
        return 0


def get_team_bullpen_form(team_abbrev, game_date=None, days=14):
    """Bullpen ERA over the trailing `days` window (default 14). Sums
    reliever IP + reliever ER across each game in the window, returns
    (ER * 9) / IP. Falls back to LEAGUE_AVG_BULLPEN_ERA when no usable
    data is found.

    Orthogonal to get_team_bullpen_fatigue: that one captures workload
    (how much they've thrown), this one captures form (how well).
    """
    logs = fetch_recent_pitching_logs(team_abbrev, lookback_days=days, game_date=game_date)
    if not logs:
        return LEAGUE_AVG_BULLPEN_ERA

    total_ip = 0.0
    total_er = 0
    for game_log in logs:
        for p in game_log.get('pitchers', []):
            if p.get('is_starter'):
                continue
            total_ip += float(p.get('ip', 0.0) or 0.0)
            # ESPN stat array is captured at fetch-time but only the IP
            # is unpacked into `pitchers`. The ER is in p.get('er'),
            # added below via a parallel fetch pass (see fetch helper).
            total_er += int(p.get('er', 0) or 0)
    if total_ip < 1.0:
        return LEAGUE_AVG_BULLPEN_ERA
    return round((total_er * 9.0) / total_ip, 2)


def _cached_bullpen_form(team_abbrev, game_date):
    """Disk-cached wrapper around get_team_bullpen_form. Same caching
    pattern as _cached_bullpen — one JSON file per team-date pair.
    """
    if not team_abbrev or not game_date:
        return LEAGUE_AVG_BULLPEN_ERA
    try:
        key = hashlib.md5(f"form:{team_abbrev}:{game_date}".encode()).hexdigest()
        cache_path = os.path.join(_BULLPEN_CACHE_DIR, f"{key}.json")
    except Exception:
        return get_team_bullpen_form(team_abbrev, game_date=game_date)

    if os.path.exists(cache_path):
        try:
            with open(cache_path) as f:
                d = json.load(f)
            return float(d.get('era_14d', LEAGUE_AVG_BULLPEN_ERA))
        except Exception:
            pass

    era_14d = get_team_bullpen_form(team_abbrev, game_date=game_date)
    try:
        with open(cache_path, 'w') as f:
            json.dump({'era_14d': era_14d}, f)
    except Exception:
        pass
    return era_14d


if __name__ == '__main__':
    import sys
    team = sys.argv[1] if len(sys.argv) > 1 else 'NYY'
    print(f"Computing bullpen fatigue for {team}...")
    fatigue, heavy = get_team_bullpen_fatigue(team)
    print(f"  Fatigue score: {fatigue}")
    print(f"  Heavy usage yesterday: {'Yes' if heavy else 'No'}")
