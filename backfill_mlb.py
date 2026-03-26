"""
MLB Historical Data Backfill
Populates mlb_games table with 2023-2025 regular season data from ESPN + The Rundown API.
2023 is the earliest useful season (pitch clock introduced, extra-inning runner permanent).
Run locally: python3 backfill_mlb.py [--season 2023] [--season 2024] [--season 2025] [--no-rundown]
Default: backfills 2023, 2024, and 2025.
"""

import sqlite3
import requests
import time
import os
import sys
from datetime import datetime, timedelta, timezone

from db_path import get_sqlite_path
from main import setup_mlb_table, MLB_TEAM_ABBR_MAP

ESPN_SCOREBOARD = "https://site.api.espn.com/apis/site/v2/sports/baseball/mlb/scoreboard"

ABBR_TO_FULL = {v: k for k, v in MLB_TEAM_ABBR_MAP.items()}

SEASON_DATES = {
    2023: (datetime(2023, 3, 30), datetime(2023, 10, 1)),
    2024: (datetime(2024, 3, 28), datetime(2024, 9, 29)),
    2025: (datetime(2025, 3, 27), datetime(2025, 9, 28)),
}

RUNDOWN_DELAY = 1.2
ESPN_DELAY = 0.3


def fetch_espn_scoreboard(date_str):
    """Fetch ESPN scoreboard for a single date (YYYYMMDD format)."""
    url = f"{ESPN_SCOREBOARD}?dates={date_str}"
    try:
        resp = requests.get(url, timeout=15)
        if resp.status_code == 200:
            return resp.json()
    except Exception as e:
        print(f"  ESPN error for {date_str}: {e}")
    return None


def parse_espn_games(data, date_str_iso):
    """Parse ESPN scoreboard response into game dicts with pitcher info."""
    if not data:
        return []

    games = []
    for event in data.get('events', []):
        try:
            competition = event['competitions'][0]
            status_type = competition.get('status', {}).get('type', {}).get('name', '')

            competitors = competition.get('competitors', [])
            if len(competitors) < 2:
                continue

            home_comp = next((c for c in competitors if c.get('homeAway') == 'home'), None)
            away_comp = next((c for c in competitors if c.get('homeAway') == 'away'), None)
            if not home_comp or not away_comp:
                continue

            home_name = home_comp['team'].get('displayName', '')
            away_name = away_comp['team'].get('displayName', '')

            home_score = None
            away_score = None
            if status_type == 'STATUS_FINAL':
                home_score = int(home_comp.get('score', 0))
                away_score = int(away_comp.get('score', 0))

            home_record = home_comp.get('records', [{}])[0].get('summary', 'N/A') if home_comp.get('records') else 'N/A'
            away_record = away_comp.get('records', [{}])[0].get('summary', 'N/A') if away_comp.get('records') else 'N/A'

            home_home_record = 'N/A'
            away_away_record = 'N/A'
            for rec in home_comp.get('records', []):
                if rec.get('type') == 'home':
                    home_home_record = rec.get('summary', 'N/A')
            for rec in away_comp.get('records', []):
                if rec.get('type') == 'road':
                    away_away_record = rec.get('summary', 'N/A')

            game_time = event.get('date', '')

            game = {
                'espn_id': event.get('id', ''),
                'game_date': date_str_iso,
                'game_time': game_time,
                'home_team': home_name,
                'away_team': away_name,
                'home_score': home_score,
                'away_score': away_score,
                'home_record': home_record,
                'away_record': away_record,
                'home_home_record': home_home_record,
                'away_away_record': away_away_record,
                'status': status_type,
                'home_pitcher': None,
                'away_pitcher': None,
                'home_pitcher_era': None,
                'away_pitcher_era': None,
                'home_pitcher_whip': None,
                'away_pitcher_whip': None,
                'home_pitcher_wins': None,
                'away_pitcher_wins': None,
                'home_pitcher_losses': None,
                'away_pitcher_losses': None,
                'home_pitcher_ip': None,
                'away_pitcher_ip': None,
            }

            for comp_data, prefix in [(home_comp, 'home'), (away_comp, 'away')]:
                probables = comp_data.get('probables', [])
                for prob in probables:
                    if prob.get('abbreviation') == 'SP' or 'starter' in prob.get('name', '').lower() or prob.get('name') == 'probableStartingPitcher':
                        athlete = prob.get('athlete', {})
                        game[f'{prefix}_pitcher'] = athlete.get('fullName') or athlete.get('displayName')
                        for stat in prob.get('statistics', []):
                            sname = (stat.get('name') or stat.get('abbreviation') or '').lower()
                            try:
                                val = float(stat.get('value', stat.get('displayValue', 0)))
                            except (ValueError, TypeError):
                                continue
                            if sname in ('era', 'earnedrunaverage'):
                                game[f'{prefix}_pitcher_era'] = val
                            elif sname == 'whip':
                                game[f'{prefix}_pitcher_whip'] = val
                            elif sname in ('wins', 'w'):
                                game[f'{prefix}_pitcher_wins'] = int(val)
                            elif sname in ('losses', 'l'):
                                game[f'{prefix}_pitcher_losses'] = int(val)
                            elif sname in ('inningspitched', 'ip'):
                                game[f'{prefix}_pitcher_ip'] = val
                        break

            games.append(game)
        except Exception:
            continue

    return games


def compute_spread_result(home_score, away_score, spread_home):
    if home_score is None or away_score is None or spread_home is None:
        return None
    margin = home_score - away_score
    adjusted = margin + spread_home
    if adjusted > 0:
        return 'W'
    elif adjusted < 0:
        return 'L'
    return 'P'


def compute_total_result(home_score, away_score, total):
    if home_score is None or away_score is None or total is None:
        return None
    actual = home_score + away_score
    if actual > total:
        return 'O'
    elif actual < total:
        return 'U'
    return 'P'


def backfill(start_date=None, end_date=None, use_rundown=True):
    """Main backfill loop."""
    if start_date is None:
        start_date = SEASON_DATES[2024][0]
    if end_date is None:
        end_date = SEASON_DATES[2025][1]

    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    if end_date > today:
        end_date = today - timedelta(days=1)

    conn = sqlite3.connect(get_sqlite_path())
    cursor = conn.cursor()
    setup_mlb_table(cursor)
    conn.commit()

    if use_rundown:
        try:
            from rundown_api import fetch_rundown_mlb_data
        except ImportError:
            print("Warning: rundown_api not available, continuing without Rundown data")
            use_rundown = False
            fetch_rundown_mlb_data = None
    else:
        fetch_rundown_mlb_data = None

    total_inserted = 0
    total_updated = 0
    total_days = (end_date - start_date).days + 1

    current = start_date
    day_count = 0
    pitcher_stats_found = 0

    while current <= end_date:
        day_count += 1
        date_yyyymmdd = current.strftime('%Y%m%d')
        date_iso = current.strftime('%Y-%m-%d')

        print(f"[{day_count}/{total_days}] {date_iso} ", end="", flush=True)

        espn_data = fetch_espn_scoreboard(date_yyyymmdd)
        espn_games = parse_espn_games(espn_data, date_iso)
        time.sleep(ESPN_DELAY)

        rundown_games = {}
        if use_rundown:
            rd_list = fetch_rundown_mlb_data(date_iso)
            for g in rd_list:
                key = f"{g['away_team']}@{g['home_team']}"
                rundown_games[key] = g
            time.sleep(RUNDOWN_DELAY)

        if not espn_games:
            print("no games")
            current += timedelta(days=1)
            continue

        inserted = 0
        updated = 0

        for eg in espn_games:
            if eg['status'] != 'STATUS_FINAL':
                continue

            home = eg['home_team']
            away = eg['away_team']

            rd_key = f"{away}@{home}"
            rd_game = rundown_games.get(rd_key, {})
            if not rd_game:
                for rk, rv in rundown_games.items():
                    parts = rk.split('@', 1)
                    if len(parts) == 2:
                        if (parts[0] in away or away in parts[0]) and (parts[1] in home or home in parts[1]):
                            rd_game = rv
                            break

            spread_home = rd_game.get('spread_home')
            total = rd_game.get('total')
            home_ml = rd_game.get('home_ml')
            away_ml = rd_game.get('away_ml')
            consensus = rd_game.get('consensus_spread')
            spread_std = rd_game.get('spread_std')
            num_books = rd_game.get('num_books')

            if spread_home is None and consensus is not None:
                spread_home = consensus

            spread_result = compute_spread_result(eg['home_score'], eg['away_score'], spread_home)
            total_result = compute_total_result(eg['home_score'], eg['away_score'], total)

            game_id = f"backfill_{away.replace(' ', '_')}_{home.replace(' ', '_')}_{date_iso}".lower()

            if eg.get('home_pitcher_era') is not None:
                pitcher_stats_found += 1

            cursor.execute('SELECT id FROM mlb_games WHERE id = ?', (game_id,))
            if cursor.fetchone():
                cursor.execute('''UPDATE mlb_games SET
                    home_score = COALESCE(?, home_score),
                    away_score = COALESCE(?, away_score),
                    spread_result = COALESCE(?, spread_result),
                    total_result = COALESCE(?, total_result),
                    home_pitcher = COALESCE(?, home_pitcher),
                    away_pitcher = COALESCE(?, away_pitcher),
                    home_pitcher_era = COALESCE(?, home_pitcher_era),
                    away_pitcher_era = COALESCE(?, away_pitcher_era),
                    home_pitcher_whip = COALESCE(?, home_pitcher_whip),
                    away_pitcher_whip = COALESCE(?, away_pitcher_whip),
                    home_pitcher_wins = COALESCE(?, home_pitcher_wins),
                    away_pitcher_wins = COALESCE(?, away_pitcher_wins),
                    home_pitcher_losses = COALESCE(?, home_pitcher_losses),
                    away_pitcher_losses = COALESCE(?, away_pitcher_losses),
                    home_pitcher_ip = COALESCE(?, home_pitcher_ip),
                    away_pitcher_ip = COALESCE(?, away_pitcher_ip),
                    scores_updated_at = ?
                    WHERE id = ?''',
                    (eg['home_score'], eg['away_score'],
                     spread_result, total_result,
                     eg.get('home_pitcher'), eg.get('away_pitcher'),
                     eg.get('home_pitcher_era'), eg.get('away_pitcher_era'),
                     eg.get('home_pitcher_whip'), eg.get('away_pitcher_whip'),
                     eg.get('home_pitcher_wins'), eg.get('away_pitcher_wins'),
                     eg.get('home_pitcher_losses'), eg.get('away_pitcher_losses'),
                     eg.get('home_pitcher_ip'), eg.get('away_pitcher_ip'),
                     datetime.now().isoformat(), game_id))
                updated += 1
                continue

            cursor.execute('''INSERT OR IGNORE INTO mlb_games
                (id, game_date, game_time, home_team, away_team,
                 spread_home, spread_away, total, home_ml, away_ml,
                 collected_at,
                 spread_home_open, total_open, home_ml_open, away_ml_open,
                 home_record, away_record, home_home_record, away_away_record,
                 home_rest_days, away_rest_days,
                 home_score, away_score,
                 spread_result, total_result,
                 scores_updated_at,
                 line_movement,
                 commence_time,
                 rundown_spread_consensus, rundown_spread_std, rundown_num_books,
                 home_pitcher, away_pitcher,
                 home_pitcher_era, away_pitcher_era,
                 home_pitcher_whip, away_pitcher_whip,
                 home_pitcher_wins, away_pitcher_wins,
                 home_pitcher_losses, away_pitcher_losses,
                 home_pitcher_ip, away_pitcher_ip)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                        ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                (game_id, date_iso, eg.get('game_time'), home, away,
                 spread_home, -spread_home if spread_home else None, total, home_ml, away_ml,
                 datetime.now().isoformat(),
                 spread_home, total, home_ml, away_ml,
                 eg['home_record'], eg['away_record'],
                 eg['home_home_record'], eg['away_away_record'],
                 None, None,
                 eg['home_score'], eg['away_score'],
                 spread_result, total_result,
                 datetime.now().isoformat(),
                 0.0,
                 eg.get('game_time', ''),
                 consensus, spread_std, num_books,
                 eg.get('home_pitcher'), eg.get('away_pitcher'),
                 eg.get('home_pitcher_era'), eg.get('away_pitcher_era'),
                 eg.get('home_pitcher_whip'), eg.get('away_pitcher_whip'),
                 eg.get('home_pitcher_wins'), eg.get('away_pitcher_wins'),
                 eg.get('home_pitcher_losses'), eg.get('away_pitcher_losses'),
                 eg.get('home_pitcher_ip'), eg.get('away_pitcher_ip')))
            inserted += 1

        conn.commit()
        total_inserted += inserted
        total_updated += updated
        print(f"ESPN: {len(espn_games)} games, Rundown: {len(rundown_games)} odds | +{inserted} new, ~{updated} updated")
        current += timedelta(days=1)

    conn.close()
    print(f"\nBackfill complete: {total_inserted} inserted, {total_updated} updated across {day_count} days")
    print(f"Games with pitcher stats from ESPN: {pitcher_stats_found}")
    return total_inserted


if __name__ == '__main__':
    print("=" * 60)
    print("MLB HISTORICAL BACKFILL (2023 + 2024 + 2025)")
    print("=" * 60)

    use_rd = '--no-rundown' not in sys.argv

    seasons_arg = []
    for i, arg in enumerate(sys.argv):
        if arg == '--season' and i + 1 < len(sys.argv):
            seasons_arg.append(int(sys.argv[i + 1]))

    if not seasons_arg:
        seasons_arg = [2023, 2024, 2025]

    conn = sqlite3.connect(get_sqlite_path())
    cursor = conn.cursor()
    setup_mlb_table(cursor)
    conn.commit()
    conn.close()

    if not use_rd:
        print("Rundown API disabled (--no-rundown flag). ESPN scores only.")

    print(f"Seasons: {seasons_arg}")

    for season in sorted(seasons_arg):
        if season not in SEASON_DATES:
            print(f"Unknown season {season}, skipping")
            continue
        start, end = SEASON_DATES[season]
        print(f"\n{'='*40}")
        print(f"SEASON {season}: {start.strftime('%Y-%m-%d')} to {end.strftime('%Y-%m-%d')}")
        print(f"{'='*40}")
        backfill(start_date=start, end_date=end, use_rundown=use_rd)
