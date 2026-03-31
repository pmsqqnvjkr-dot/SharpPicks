"""
WNBA Feature Module — Roster continuity, schedule density, and team-specific HCA.

These features exploit WNBA-specific market inefficiencies:
- Massive year-over-year roster churn (overseas leagues, expansion, free agency)
- Compressed 40-game schedule with amplified fatigue effects on 12-player rosters
- Highly variable home court advantage across venues
"""

import os
import sqlite3
import logging
import requests
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

BDL_API_KEY = os.environ.get('BALLDONTLIE_API_KEY', '')
BDL_WNBA_BASE = "https://api.balldontlie.io/wnba/v1"


def _get_sqlite_path():
    try:
        from db_path import get_sqlite_path
        return get_sqlite_path()
    except Exception:
        return 'sharppicks.db'


def _get_db():
    conn = sqlite3.connect(_get_sqlite_path())
    conn.row_factory = sqlite3.Row
    return conn


# ---------------------------------------------------------------------------
# 1. Roster Continuity / Returning Minutes Percentage
# ---------------------------------------------------------------------------

WNBA_TEAM_ABBREVS = [
    'ATL', 'CHI', 'CON', 'DAL', 'IND', 'LVA', 'LAS', 'MIN',
    'NYL', 'PHO', 'SEA', 'WAS', 'GSV', 'POR',
]


def ensure_continuity_table():
    conn = _get_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS wnba_roster_continuity (
            team TEXT,
            season INTEGER,
            returning_minutes_pct REAL,
            returning_players INTEGER,
            total_players_last_season INTEGER,
            updated_at TEXT,
            PRIMARY KEY (team, season)
        )
    """)
    conn.commit()
    conn.close()


def compute_roster_continuity(season=None):
    """
    Compute returning minutes percentage for each WNBA team.
    Compares current season's roster against prior season's minute leaders.

    Uses BallDontLie WNBA API for roster and season averages.
    Returns dict of results.
    """
    if not BDL_API_KEY:
        return {'error': 'No BALLDONTLIE_API_KEY configured'}

    ensure_continuity_table()

    if season is None:
        season = datetime.now().year

    prev_season = season - 1
    headers = {"Authorization": BDL_API_KEY}
    results = {}

    try:
        resp = requests.get(f"{BDL_WNBA_BASE}/teams", headers=headers, timeout=15)
        if resp.status_code != 200:
            return {'error': f'BDL WNBA teams API returned {resp.status_code}'}
        teams = resp.json().get('data', [])
    except Exception as e:
        return {'error': str(e)}

    conn = _get_db()

    for team in teams:
        team_id = team['id']
        abbrev = team.get('abbreviation', '')
        if not abbrev:
            continue

        try:
            prev_resp = requests.get(
                f"{BDL_WNBA_BASE}/season_averages",
                headers=headers,
                params={"season": prev_season, "team_id": team_id},
                timeout=15
            )
            curr_resp = requests.get(
                f"{BDL_WNBA_BASE}/season_averages",
                headers=headers,
                params={"season": season, "team_id": team_id},
                timeout=15
            )

            prev_players = {}
            if prev_resp.status_code == 200:
                for avg in prev_resp.json().get('data', []):
                    pid = avg.get('player_id')
                    try:
                        mpg = float(str(avg.get('min', '0')).replace(':', '.'))
                    except (ValueError, TypeError):
                        mpg = 0.0
                    gp = int(avg.get('games_played', 0) or 0)
                    if pid and gp >= 5:
                        prev_players[pid] = mpg * gp

            curr_player_ids = set()
            if curr_resp.status_code == 200:
                for avg in curr_resp.json().get('data', []):
                    pid = avg.get('player_id')
                    if pid:
                        curr_player_ids.add(pid)

            if not prev_players:
                returning_pct = 0.5
                returning_count = 0
                total_prev = 0
            else:
                total_prev_minutes = sum(prev_players.values())
                returning_minutes = sum(
                    mins for pid, mins in prev_players.items() if pid in curr_player_ids
                )
                returning_pct = returning_minutes / total_prev_minutes if total_prev_minutes > 0 else 0.5
                returning_count = sum(1 for pid in prev_players if pid in curr_player_ids)
                total_prev = len(prev_players)

            conn.execute("""
                INSERT OR REPLACE INTO wnba_roster_continuity
                (team, season, returning_minutes_pct, returning_players, total_players_last_season, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (abbrev, season, round(returning_pct, 3), returning_count, total_prev,
                  datetime.now().isoformat()))

            results[abbrev] = {
                'returning_minutes_pct': round(returning_pct, 3),
                'returning_players': returning_count,
                'total_last_season': total_prev,
            }

        except Exception as e:
            logger.warning(f"Roster continuity error for {abbrev}: {e}")
            continue

    conn.commit()
    conn.close()
    logger.info(f"WNBA roster continuity computed for {len(results)} teams (season {season})")
    return results


def get_team_continuity(team_abbrev, season=None):
    """Get cached roster continuity for a team. Returns returning_minutes_pct (0-1)."""
    if season is None:
        season = datetime.now().year
    try:
        conn = _get_db()
        row = conn.execute(
            "SELECT returning_minutes_pct FROM wnba_roster_continuity WHERE team = ? AND season = ?",
            (team_abbrev, season)
        ).fetchone()
        conn.close()
        if row:
            return float(row['returning_minutes_pct'])
    except Exception:
        pass
    return 0.5


# ---------------------------------------------------------------------------
# 2. Schedule Density (WNBA-specific, amplified)
# ---------------------------------------------------------------------------

def compute_wnba_schedule_density(team_abbrev, game_date, lookback_5=5, lookback_7=7):
    """
    Count team's games in last N days from wnba_games table.
    Returns (games_last_5d, games_last_7d).
    """
    if isinstance(game_date, str):
        gd = datetime.strptime(game_date, '%Y-%m-%d')
    else:
        gd = game_date

    try:
        conn = _get_db()
        d5 = (gd - timedelta(days=lookback_5)).strftime('%Y-%m-%d')
        d7 = (gd - timedelta(days=lookback_7)).strftime('%Y-%m-%d')
        gd_str = gd.strftime('%Y-%m-%d')

        count_5 = conn.execute(
            "SELECT COUNT(*) FROM wnba_games WHERE (home_team = ? OR away_team = ?) "
            "AND game_date > ? AND game_date < ?",
            (team_abbrev, team_abbrev, d5, gd_str)
        ).fetchone()[0]

        count_7 = conn.execute(
            "SELECT COUNT(*) FROM wnba_games WHERE (home_team = ? OR away_team = ?) "
            "AND game_date > ? AND game_date < ?",
            (team_abbrev, team_abbrev, d7, gd_str)
        ).fetchone()[0]

        conn.close()
        return int(count_5), int(count_7)
    except Exception:
        return 0, 0


# ---------------------------------------------------------------------------
# 3. Team-Specific Home Court Advantage
# ---------------------------------------------------------------------------

def compute_team_hca(season=None, min_games=10):
    """
    Compute team-specific home court advantage from historical wnba_games.
    Returns dict: team -> hca_points (home margin - away margin).
    """
    try:
        conn = _get_db()
        if season:
            season_start = f"{season}-01-01"
            season_end = f"{season}-12-31"
            rows = conn.execute("""
                SELECT home_team, away_team, home_score, away_score
                FROM wnba_games
                WHERE home_score IS NOT NULL AND away_score IS NOT NULL
                AND game_date >= ? AND game_date <= ?
            """, (season_start, season_end)).fetchall()
        else:
            rows = conn.execute("""
                SELECT home_team, away_team, home_score, away_score
                FROM wnba_games
                WHERE home_score IS NOT NULL AND away_score IS NOT NULL
            """).fetchall()
        conn.close()
    except Exception:
        return {}

    home_margins = {}
    away_margins = {}

    for r in rows:
        ht, at = r['home_team'], r['away_team']
        margin = r['home_score'] - r['away_score']

        home_margins.setdefault(ht, []).append(margin)
        away_margins.setdefault(at, []).append(-margin)

    hca = {}
    for team in set(list(home_margins.keys()) + list(away_margins.keys())):
        h_games = home_margins.get(team, [])
        a_games = away_margins.get(team, [])
        if len(h_games) >= min_games and len(a_games) >= min_games:
            h_avg = sum(h_games) / len(h_games)
            a_avg = sum(a_games) / len(a_games)
            hca[team] = round((h_avg - a_avg) / 2.0, 2)
        else:
            hca[team] = 2.5

    return hca


_hca_cache = {}
_hca_cache_time = None


def get_team_hca(team_abbrev, season=None):
    """Get team-specific HCA in points. Default 2.5 if insufficient data."""
    global _hca_cache, _hca_cache_time

    if not _hca_cache or _hca_cache_time is None or (datetime.now() - _hca_cache_time).seconds > 3600:
        _hca_cache = compute_team_hca(season)
        _hca_cache_time = datetime.now()

    return _hca_cache.get(team_abbrev, 2.5)


# ---------------------------------------------------------------------------
# Combined feature helper
# ---------------------------------------------------------------------------

def get_wnba_game_features(home_team, away_team, game_date, season=None):
    """
    Compute all WNBA-specific features for a game.
    Returns dict ready for shadow prediction or engineer_features merge.
    """
    if season is None:
        if isinstance(game_date, str):
            season = int(game_date[:4])
        else:
            season = game_date.year

    home_cont = get_team_continuity(home_team, season)
    away_cont = get_team_continuity(away_team, season)

    home_g5, home_g7 = compute_wnba_schedule_density(home_team, game_date)
    away_g5, away_g7 = compute_wnba_schedule_density(away_team, game_date)

    team_hca = get_team_hca(home_team, season)

    return {
        'home_continuity': home_cont,
        'away_continuity': away_cont,
        'continuity_diff': home_cont - away_cont,
        'home_games_last_5d': home_g5,
        'away_games_last_5d': away_g5,
        'home_games_last_7d': home_g7,
        'away_games_last_7d': away_g7,
        'density_diff_5d': away_g5 - home_g5,
        'density_diff_7d': away_g7 - home_g7,
        'team_hca': team_hca,
    }


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)

    print("Computing WNBA roster continuity...")
    results = compute_roster_continuity()
    if 'error' in results:
        print(f"  Error: {results['error']}")
    else:
        for team, data in sorted(results.items()):
            print(f"  {team}: {data['returning_minutes_pct']:.1%} returning "
                  f"({data['returning_players']}/{data['total_last_season']} players)")

    print("\nComputing team-specific HCA...")
    hca = compute_team_hca()
    for team, pts in sorted(hca.items(), key=lambda x: -x[1]):
        print(f"  {team}: {pts:+.1f} pts HCA")
