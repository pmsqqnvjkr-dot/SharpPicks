"""
MLB Historical Data Backfill
Populates mlb_games table with 2025 regular season data from ESPN + The Rundown API.
Run locally: python backfill_mlb.py
"""

import sqlite3
import requests
import time
import os
import sys
from datetime import datetime, timedelta, timezone

from db_path import get_sqlite_path
from main import setup_mlb_table, MLB_TEAM_ABBR_MAP
from rundown_api import fetch_rundown_mlb_data, normalize_mlb_team_name

ESPN_SCOREBOARD = "https://site.api.espn.com/apis/site/v2/sports/baseball/mlb/scoreboard"

ABBR_TO_FULL = {v: k for k, v in MLB_TEAM_ABBR_MAP.items()}

# 2025 MLB regular season: March 27 - September 28
SEASON_START = datetime(2025, 3, 27)
SEASON_END = datetime(2025, 9, 28)

RUNDOWN_DELAY = 1.2  # seconds between Rundown API calls (rate limit)
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
    """Parse ESPN scoreboard response into game dicts."""
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

            games.append({
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
            })
        except Exception as e:
            continue

    return games


def compute_spread_result(home_score, away_score, spread_home):
    """Determine spread result: W/L/P from home perspective."""
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
    """Main backfill loop. Iterates each day, fetches ESPN + Rundown, inserts into mlb_games."""
    if start_date is None:
        start_date = SEASON_START
    if end_date is None:
        end_date = SEASON_END

    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    if end_date > today:
        end_date = today - timedelta(days=1)

    conn = sqlite3.connect(get_sqlite_path())
    cursor = conn.cursor()
    setup_mlb_table(cursor)
    conn.commit()

    total_inserted = 0
    total_updated = 0
    total_days = (end_date - start_date).days + 1

    current = start_date
    day_count = 0

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
            line_movement = 0.0

            game_id = f"backfill_{away.replace(' ', '_')}_{home.replace(' ', '_')}_{date_iso}".lower()

            cursor.execute('SELECT id FROM mlb_games WHERE id = ?', (game_id,))
            if cursor.fetchone():
                cursor.execute('''UPDATE mlb_games SET
                    home_score = ?, away_score = ?,
                    spread_result = ?, total_result = ?,
                    scores_updated_at = ?
                    WHERE id = ? AND home_score IS NULL''',
                    (eg['home_score'], eg['away_score'],
                     spread_result, total_result,
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
                 rundown_spread_consensus, rundown_spread_std, rundown_num_books)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
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
                 line_movement,
                 eg.get('game_time', ''),
                 consensus, spread_std, num_books))
            inserted += 1

        conn.commit()
        total_inserted += inserted
        total_updated += updated
        print(f"ESPN: {len(espn_games)} games, Rundown: {len(rundown_games)} odds | +{inserted} new, ~{updated} updated")
        current += timedelta(days=1)

    conn.close()
    print(f"\nBackfill complete: {total_inserted} inserted, {total_updated} updated across {day_count} days")
    return total_inserted


def add_rundown_columns(cursor):
    """Ensure rundown columns exist on mlb_games (for older table schemas)."""
    for col, ctype in [
        ('rundown_spread_consensus', 'REAL'),
        ('rundown_spread_std', 'REAL'),
        ('rundown_spread_range', 'REAL'),
        ('rundown_best_book', 'TEXT'),
        ('rundown_num_books', 'INTEGER'),
    ]:
        try:
            cursor.execute(f'ALTER TABLE mlb_games ADD COLUMN {col} {ctype}')
        except Exception:
            pass


if __name__ == '__main__':
    print("=" * 60)
    print("MLB HISTORICAL BACKFILL")
    print("=" * 60)

    use_rd = '--no-rundown' not in sys.argv

    conn = sqlite3.connect(get_sqlite_path())
    cursor = conn.cursor()
    setup_mlb_table(cursor)
    add_rundown_columns(cursor)
    conn.commit()
    conn.close()

    if not use_rd:
        print("Rundown API disabled (--no-rundown flag). ESPN scores only.")

    backfill(use_rundown=use_rd)
