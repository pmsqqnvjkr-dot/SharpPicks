"""
WNBA BACKTESTING PIPELINE
Collects historical data, runs walk-forward backtest with shrinkage sweep,
simulates product constraints, and reports whether WNBA adds value.

Data sources:
  - ESPN: free scores (no API key)
  - balldontlie: game schedule, team info (uses BALLDONTLIE_API_KEY)
  - CSV import: closing spreads from BigDataBall or similar

Usage:
  python wnba_backtest.py collect          # Collect scores from ESPN + balldontlie
  python wnba_backtest.py import_spreads FILE.csv   # Import spread data from CSV
  python wnba_backtest.py status           # Show data readiness
  python wnba_backtest.py backtest         # Run full walk-forward backtest
  python wnba_backtest.py report           # Generate final report
"""

import sqlite3
import pandas as pd
import numpy as np
import requests
import time
import os
import sys
import json
from datetime import datetime, timedelta
from scipy.stats import norm
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.preprocessing import StandardScaler


DB_PATH = 'sharp_picks.db'

WNBA_SEASONS = {
    2022: ('2022-05-06', '2022-09-18'),
    2023: ('2023-05-19', '2023-09-17'),
    2024: ('2024-05-14', '2024-10-21'),
}

WNBA_TEAMS = {
    'Atlanta Dream': 'ATL',
    'Chicago Sky': 'CHI',
    'Connecticut Sun': 'CON',
    'Dallas Wings': 'DAL',
    'Golden State Valkyries': 'GSV',
    'Indiana Fever': 'IND',
    'Las Vegas Aces': 'LVA',
    'Los Angeles Sparks': 'LAS',
    'Minnesota Lynx': 'MIN',
    'New York Liberty': 'NYL',
    'Phoenix Mercury': 'PHO',
    'Seattle Storm': 'SEA',
    'Washington Mystics': 'WAS',
}

SHRINKAGE_WEIGHTS = [0.3, 0.4, 0.5, 0.6, 0.7]
EDGE_THRESHOLDS = [3.0, 3.5, 4.0, 5.0]
SIGMA_FLOOR = 7.0
SIGMA_CEILING = 13.0
MAX_EDGE_PCT = 8.0
STANDARD_ODDS = -110

LINE_MOVE_PENALTY_PER_PT = 1.0
LINE_MOVE_HARD_STOP = 2.5
LINE_MOVE_HARD_STOP_MIN_EDGE = 8.0


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def odds_to_implied_prob(odds):
    if odds < 0:
        return abs(odds) / (abs(odds) + 100)
    else:
        return 100 / (odds + 100)


def create_wnba_table():
    conn = get_db()
    conn.execute('''
        CREATE TABLE IF NOT EXISTS wnba_games (
            id TEXT PRIMARY KEY,
            game_date TEXT,
            home_team TEXT,
            away_team TEXT,
            home_score INTEGER,
            away_score INTEGER,
            spread_home REAL,
            spread_away REAL,
            spread_home_open REAL,
            spread_home_close REAL,
            total REAL,
            total_open REAL,
            total_close REAL,
            home_ml INTEGER,
            away_ml INTEGER,
            home_record TEXT,
            away_record TEXT,
            home_home_record TEXT DEFAULT 'N/A',
            away_away_record TEXT DEFAULT 'N/A',
            home_last5 TEXT DEFAULT '',
            away_last5 TEXT DEFAULT '',
            home_rest_days INTEGER DEFAULT 1,
            away_rest_days INTEGER DEFAULT 1,
            home_injuries TEXT DEFAULT '',
            away_injuries TEXT DEFAULT '',
            game_time TEXT,
            line_movement REAL DEFAULT 0,
            spread_result TEXT,
            collected_at TEXT,
            scores_updated_at TEXT,
            home_spread_odds INTEGER DEFAULT -110,
            away_spread_odds INTEGER DEFAULT -110,
            home_spread_book TEXT,
            away_spread_book TEXT,
            rundown_spread_consensus REAL,
            rundown_spread_std REAL DEFAULT 0,
            rundown_spread_range REAL DEFAULT 0,
            rundown_num_books INTEGER DEFAULT 0,
            bdl_home_win_pct REAL DEFAULT 0.5,
            bdl_away_win_pct REAL DEFAULT 0.5,
            bdl_home_conf_rank INTEGER DEFAULT 8,
            bdl_away_conf_rank INTEGER DEFAULT 8,
            bdl_home_scoring_margin REAL DEFAULT 0,
            bdl_away_scoring_margin REAL DEFAULT 0,
            bdl_home_avg_pts REAL DEFAULT 80,
            bdl_away_avg_pts REAL DEFAULT 80,
            bdl_home_avg_pts_against REAL DEFAULT 80,
            bdl_away_avg_pts_against REAL DEFAULT 80,
            season INTEGER
        )
    ''')
    conn.commit()
    conn.close()
    print("wnba_games table ready")


def collect_espn_scores():
    print("\n" + "=" * 60)
    print("COLLECTING WNBA SCORES FROM ESPN (FREE)")
    print("=" * 60)

    conn = get_db()
    create_wnba_table()
    total_added = 0
    total_updated = 0

    for season, (start_date, end_date) in WNBA_SEASONS.items():
        print(f"\n  Season {season}: {start_date} to {end_date}")
        start = datetime.strptime(start_date, '%Y-%m-%d')
        end = datetime.strptime(end_date, '%Y-%m-%d')
        current = start
        season_added = 0

        while current <= end:
            date_str = current.strftime('%Y%m%d')
            url = f"https://site.api.espn.com/apis/site/v2/sports/basketball/wnba/scoreboard?dates={date_str}"

            try:
                resp = requests.get(url, timeout=10)
                if resp.status_code != 200:
                    current += timedelta(days=1)
                    continue

                data = resp.json()
                events = data.get('events', [])

                for event in events:
                    competition = event.get('competitions', [{}])[0]
                    competitors = competition.get('competitors', [])
                    if len(competitors) != 2:
                        continue

                    status_type = event.get('status', {}).get('type', {})
                    if not status_type.get('completed', False):
                        continue

                    home = away = None
                    home_score = away_score = None

                    for team in competitors:
                        team_name = team.get('team', {}).get('displayName', '')
                        score_str = team.get('score', '0')
                        try:
                            score = int(score_str) if score_str else 0
                        except:
                            score = 0

                        if team.get('homeAway') == 'home':
                            home = team_name
                            home_score = score
                        else:
                            away = team_name
                            away_score = score

                    if not home or not away or home_score == 0 or away_score == 0:
                        continue

                    game_id = f"espn_wnba_{event['id']}"
                    game_date = current.strftime('%Y-%m-%d')

                    existing = conn.execute('SELECT id FROM wnba_games WHERE id = ?', (game_id,)).fetchone()
                    if existing:
                        conn.execute('''
                            UPDATE wnba_games SET home_score = ?, away_score = ?,
                            scores_updated_at = ? WHERE id = ?
                        ''', (home_score, away_score, datetime.now().isoformat(), game_id))
                        total_updated += 1
                    else:
                        conn.execute('''
                            INSERT INTO wnba_games (id, game_date, home_team, away_team,
                                home_score, away_score, season, collected_at)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        ''', (game_id, game_date, home, away, home_score, away_score,
                              season, datetime.now().isoformat()))
                        season_added += 1
                        total_added += 1

            except Exception as e:
                pass

            current += timedelta(days=1)
            time.sleep(0.15)

        conn.commit()
        print(f"    Added {season_added} games")

    conn.close()
    print(f"\n  Total: {total_added} new, {total_updated} updated")
    return total_added


def collect_balldontlie_games():
    print("\n" + "=" * 60)
    print("COLLECTING WNBA DATA FROM BALLDONTLIE")
    print("=" * 60)

    api_key = os.environ.get('BALLDONTLIE_API_KEY')
    if not api_key:
        print("  BALLDONTLIE_API_KEY not set")
        return 0

    conn = get_db()
    create_wnba_table()
    headers = {'Authorization': api_key}
    base = 'https://api.balldontlie.io/wnba/v1'
    total_added = 0

    for season in WNBA_SEASONS.keys():
        print(f"\n  Season {season}...")
        cursor_val = None
        page_count = 0

        while True:
            params = {'seasons[]': season, 'per_page': 100}
            if cursor_val:
                params['cursor'] = cursor_val

            try:
                resp = requests.get(f'{base}/games', headers=headers, params=params, timeout=15)
                if resp.status_code == 429:
                    print("    Rate limited, waiting 2s...")
                    time.sleep(2)
                    continue
                if resp.status_code != 200:
                    print(f"    Error: {resp.status_code}")
                    break

                data = resp.json()
                games = data.get('data', [])
                if not games:
                    break

                for game in games:
                    if game.get('status') != 'post':
                        continue

                    home_team = game.get('home_team', {}).get('full_name', '')
                    away_team = game.get('visitor_team', {}).get('full_name', '')
                    home_score = game.get('home_score')
                    away_score = game.get('away_score')

                    if not home_team or not away_team or not home_score or not away_score:
                        continue

                    game_date = game['date'][:10]
                    game_id = f"bdl_wnba_{game['id']}"

                    existing = conn.execute('SELECT id FROM wnba_games WHERE id = ?', (game_id,)).fetchone()
                    if existing:
                        continue

                    espn_match = conn.execute('''
                        SELECT id FROM wnba_games WHERE game_date = ?
                        AND home_team = ? AND away_team = ?
                    ''', (game_date, home_team, away_team)).fetchone()

                    if espn_match:
                        continue

                    conn.execute('''
                        INSERT INTO wnba_games (id, game_date, home_team, away_team,
                            home_score, away_score, season, collected_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (game_id, game_date, home_team, away_team, home_score, away_score,
                          season, datetime.now().isoformat()))
                    total_added += 1

                meta = data.get('meta', {})
                cursor_val = meta.get('next_cursor')
                if not cursor_val:
                    break

                page_count += 1
                time.sleep(0.3)

            except Exception as e:
                print(f"    Error: {e}")
                break

        conn.commit()
        print(f"    Page count: {page_count + 1}")

    conn.close()
    print(f"\n  Total new from balldontlie: {total_added}")
    return total_added


def compute_rolling_stats(conn):
    print("\n  Computing rolling stats (records, rest days, form)...")

    games = pd.read_sql_query('''
        SELECT id, game_date, home_team, away_team, home_score, away_score, season
        FROM wnba_games
        WHERE home_score IS NOT NULL
        ORDER BY game_date
    ''', conn)

    if len(games) == 0:
        return

    team_records = {}
    team_home_records = {}
    team_away_records = {}
    team_last_game = {}
    team_last5 = {}

    updates = []

    for _, game in games.iterrows():
        ht = game['home_team']
        at = game['away_team']
        gd = game['game_date']

        if ht not in team_records:
            team_records[ht] = [0, 0]
        if at not in team_records:
            team_records[at] = [0, 0]
        if ht not in team_home_records:
            team_home_records[ht] = [0, 0]
        if at not in team_away_records:
            team_away_records[at] = [0, 0]

        hr = f"{team_records[ht][0]}-{team_records[ht][1]}"
        ar = f"{team_records[at][0]}-{team_records[at][1]}"
        hhr = f"{team_home_records[ht][0]}-{team_home_records[ht][1]}"
        aar = f"{team_away_records[at][0]}-{team_away_records[at][1]}"

        h_rest = 1
        a_rest = 1
        try:
            gd_dt = datetime.strptime(gd, '%Y-%m-%d')
            if ht in team_last_game:
                h_rest = max(1, (gd_dt - team_last_game[ht]).days)
            if at in team_last_game:
                a_rest = max(1, (gd_dt - team_last_game[at]).days)
        except:
            pass

        h_form = ''.join(team_last5.get(ht, [])[-5:])
        a_form = ''.join(team_last5.get(at, [])[-5:])

        updates.append((hr, ar, hhr, aar, h_rest, a_rest, h_form, a_form, game['id']))

        home_won = game['home_score'] > game['away_score']
        if home_won:
            team_records[ht][0] += 1
            team_records[at][1] += 1
            team_home_records[ht][0] += 1
            team_away_records[at][1] += 1
            team_last5.setdefault(ht, []).append('W')
            team_last5.setdefault(at, []).append('L')
        else:
            team_records[ht][1] += 1
            team_records[at][0] += 1
            team_home_records[ht][1] += 1
            team_away_records[at][0] += 1
            team_last5.setdefault(ht, []).append('L')
            team_last5.setdefault(at, []).append('W')

        try:
            team_last_game[ht] = datetime.strptime(gd, '%Y-%m-%d')
            team_last_game[at] = datetime.strptime(gd, '%Y-%m-%d')
        except:
            pass

    for hr, ar, hhr, aar, h_rest, a_rest, h_form, a_form, gid in updates:
        conn.execute('''
            UPDATE wnba_games SET home_record=?, away_record=?,
            home_home_record=?, away_away_record=?,
            home_rest_days=?, away_rest_days=?,
            home_last5=?, away_last5=?
            WHERE id = ?
        ''', (hr, ar, hhr, aar, h_rest, a_rest, h_form, a_form, gid))

    conn.commit()
    print(f"    Updated {len(updates)} games with rolling stats")


def compute_team_metrics(conn):
    print("  Computing scoring averages and margins...")

    games = pd.read_sql_query('''
        SELECT id, game_date, home_team, away_team, home_score, away_score, season
        FROM wnba_games
        WHERE home_score IS NOT NULL
        ORDER BY game_date
    ''', conn)

    team_scores = {}
    team_against = {}

    for _, game in games.iterrows():
        ht = game['home_team']
        at = game['away_team']
        hs = game['home_score']
        as_ = game['away_score']

        team_scores.setdefault(ht, [])
        team_scores.setdefault(at, [])
        team_against.setdefault(ht, [])
        team_against.setdefault(at, [])

        h_avg_pts = np.mean(team_scores[ht][-20:]) if team_scores[ht] else 80
        a_avg_pts = np.mean(team_scores[at][-20:]) if team_scores[at] else 80
        h_avg_against = np.mean(team_against[ht][-20:]) if team_against[ht] else 80
        a_avg_against = np.mean(team_against[at][-20:]) if team_against[at] else 80
        h_margin = h_avg_pts - h_avg_against
        a_margin = a_avg_pts - a_avg_against

        h_games = len(team_scores[ht])
        a_games = len(team_scores[at])
        h_wins = sum(1 for s, a in zip(team_scores[ht], team_against[ht]) if s > a)
        a_wins = sum(1 for s, a in zip(team_scores[at], team_against[at]) if s > a)
        h_pct = h_wins / h_games if h_games > 0 else 0.5
        a_pct = a_wins / a_games if a_games > 0 else 0.5

        conn.execute('''
            UPDATE wnba_games SET
            bdl_home_avg_pts=?, bdl_away_avg_pts=?,
            bdl_home_avg_pts_against=?, bdl_away_avg_pts_against=?,
            bdl_home_scoring_margin=?, bdl_away_scoring_margin=?,
            bdl_home_win_pct=?, bdl_away_win_pct=?
            WHERE id = ?
        ''', (round(h_avg_pts, 1), round(a_avg_pts, 1),
              round(h_avg_against, 1), round(a_avg_against, 1),
              round(h_margin, 1), round(a_margin, 1),
              round(h_pct, 3), round(a_pct, 3),
              game['id']))

        team_scores[ht].append(hs)
        team_scores[at].append(as_)
        team_against[ht].append(as_)
        team_against[at].append(hs)

    conn.commit()
    print(f"    Updated {len(games)} games with team metrics")


def compute_spread_results(conn):
    print("  Computing spread results...")
    conn.execute('''
        UPDATE wnba_games SET spread_result = 
        CASE
            WHEN spread_home IS NULL THEN NULL
            WHEN (home_score - away_score + spread_home) > 0 THEN 'HOME_COVER'
            WHEN (home_score - away_score + spread_home) < 0 THEN 'AWAY_COVER'
            ELSE 'PUSH'
        END
        WHERE home_score IS NOT NULL AND away_score IS NOT NULL
    ''')
    conn.commit()

    result = conn.execute('''
        SELECT spread_result, COUNT(*) as cnt FROM wnba_games
        WHERE spread_result IS NOT NULL GROUP BY spread_result
    ''').fetchall()

    for r in result:
        print(f"    {r['spread_result']}: {r['cnt']}")


def import_spreads_csv(filepath):
    """Import spread data from CSV.
    Expected columns: date, home_team, away_team, spread_home
    Optional: spread_home_open, total, home_ml, away_ml
    """
    print(f"\n{'='*60}")
    print(f"IMPORTING SPREAD DATA FROM {filepath}")
    print(f"{'='*60}")

    if not os.path.exists(filepath):
        print(f"  File not found: {filepath}")
        return 0

    df = pd.read_csv(filepath)
    print(f"  Rows in CSV: {len(df)}")
    print(f"  Columns: {list(df.columns)}")

    required = ['date', 'home_team', 'spread_home']
    for col in required:
        alt_names = {
            'date': ['date', 'game_date', 'Date', 'DATE'],
            'home_team': ['home_team', 'Home', 'HOME', 'home', 'Home Team'],
            'spread_home': ['spread_home', 'spread', 'Spread', 'SPREAD', 'closing_spread',
                           'close_spread', 'home_spread'],
        }
        found = False
        for alt in alt_names.get(col, [col]):
            if alt in df.columns:
                if alt != col:
                    df = df.rename(columns={alt: col})
                found = True
                break
        if not found:
            print(f"  Missing required column: {col} (tried: {alt_names.get(col, [col])})")
            return 0

    conn = get_db()
    matched = 0
    unmatched = 0

    for _, row in df.iterrows():
        game_date = str(row['date'])[:10]
        home = row.get('home_team', '')
        spread = row.get('spread_home')

        if pd.isna(spread):
            continue

        game = conn.execute('''
            SELECT id FROM wnba_games
            WHERE game_date = ? AND (home_team = ? OR home_team LIKE ?)
            LIMIT 1
        ''', (game_date, home, f'%{home}%')).fetchone()

        if game:
            updates = {'spread_home': float(spread)}
            if 'spread_home_open' in df.columns and not pd.isna(row.get('spread_home_open')):
                updates['spread_home_open'] = float(row['spread_home_open'])
                updates['line_movement'] = float(spread) - float(row['spread_home_open'])
            if 'total' in df.columns and not pd.isna(row.get('total')):
                updates['total'] = float(row['total'])
            if 'home_ml' in df.columns and not pd.isna(row.get('home_ml')):
                updates['home_ml'] = int(row['home_ml'])
            if 'away_ml' in df.columns and not pd.isna(row.get('away_ml')):
                updates['away_ml'] = int(row['away_ml'])

            set_clause = ', '.join(f"{k} = ?" for k in updates.keys())
            values = list(updates.values()) + [game['id']]
            conn.execute(f'UPDATE wnba_games SET {set_clause} WHERE id = ?', values)
            matched += 1
        else:
            unmatched += 1

    conn.commit()
    compute_spread_results(conn)
    conn.close()

    print(f"\n  Matched: {matched}")
    print(f"  Unmatched: {unmatched}")
    return matched


def show_status():
    print(f"\n{'='*60}")
    print("WNBA DATA STATUS")
    print(f"{'='*60}")

    conn = get_db()

    try:
        conn.execute('SELECT 1 FROM wnba_games LIMIT 1')
    except:
        print("  wnba_games table does not exist yet. Run: python wnba_backtest.py collect")
        conn.close()
        return

    total = conn.execute('SELECT COUNT(*) as c FROM wnba_games').fetchone()['c']
    with_scores = conn.execute('SELECT COUNT(*) as c FROM wnba_games WHERE home_score IS NOT NULL').fetchone()['c']
    with_spreads = conn.execute('SELECT COUNT(*) as c FROM wnba_games WHERE spread_home IS NOT NULL').fetchone()['c']
    with_results = conn.execute('SELECT COUNT(*) as c FROM wnba_games WHERE spread_result IS NOT NULL').fetchone()['c']

    print(f"  Total games:       {total}")
    print(f"  With scores:       {with_scores}")
    print(f"  With spreads:      {with_spreads}")
    print(f"  With ATS results:  {with_results}")

    print(f"\n  By season:")
    for season in sorted(WNBA_SEASONS.keys()):
        row = conn.execute('''
            SELECT COUNT(*) as total,
                   SUM(CASE WHEN spread_home IS NOT NULL THEN 1 ELSE 0 END) as spreads
            FROM wnba_games WHERE season = ?
        ''', (season,)).fetchone()
        if row:
            pct = (row['spreads'] / row['total'] * 100) if row['total'] > 0 else 0
            status = "READY" if pct > 80 else "NEEDS SPREADS" if pct < 50 else "PARTIAL"
            print(f"    {season}: {row['total']} games, {row['spreads']} with spreads ({pct:.0f}%) — {status}")

    if with_spreads < 100:
        print(f"\n  BACKTEST BLOCKED: Need spread data for at least 2 seasons.")
        print(f"  Options:")
        print(f"    1. BigDataBall WNBA datasets (recommended, ~$20/season)")
        print(f"    2. Upgrade Odds API plan for historical access")
        print(f"    3. Provide CSV with columns: date, home_team, spread_home")
        print(f"       Run: python wnba_backtest.py import_spreads YOUR_FILE.csv")
    else:
        print(f"\n  BACKTEST READY: sufficient data for walk-forward validation")

    conn.close()


def engineer_features(df):
    features = pd.DataFrame()

    features['spread_home'] = pd.to_numeric(df['spread_home'], errors='coerce').fillna(0)
    spread_open = pd.to_numeric(df.get('spread_home_open', pd.Series([0]*len(df))), errors='coerce')
    features['spread_open'] = spread_open.fillna(features['spread_home'])
    features['line_movement'] = pd.to_numeric(df.get('line_movement', pd.Series([0]*len(df))), errors='coerce').fillna(0)

    features['total'] = pd.to_numeric(df.get('total', pd.Series([155]*len(df))), errors='coerce').fillna(155)

    features['home_ml'] = pd.to_numeric(df.get('home_ml', pd.Series([0]*len(df))), errors='coerce').fillna(0)
    features['away_ml'] = pd.to_numeric(df.get('away_ml', pd.Series([0]*len(df))), errors='coerce').fillna(0)
    features['ml_diff'] = features['home_ml'] - features['away_ml']

    def parse_record(record):
        if pd.isna(record) or record == 'N/A':
            return 0.5
        try:
            parts = str(record).split('-')
            wins = int(parts[0])
            losses = int(parts[1])
            return wins / (wins + losses) if (wins + losses) > 0 else 0.5
        except:
            return 0.5

    features['home_win_pct'] = df['home_record'].apply(parse_record)
    features['away_win_pct'] = df['away_record'].apply(parse_record)
    features['win_pct_diff'] = features['home_win_pct'] - features['away_win_pct']

    features['home_home_pct'] = df['home_home_record'].apply(parse_record)
    features['away_away_pct'] = df['away_away_record'].apply(parse_record)
    features['split_advantage'] = features['home_home_pct'] - features['away_away_pct']

    def parse_form(form_str):
        if pd.isna(form_str) or not form_str:
            return 0.5
        wins = str(form_str).count('W')
        total = len(str(form_str))
        return wins / total if total > 0 else 0.5

    features['home_form'] = df.get('home_last5', pd.Series(['']*len(df))).apply(parse_form)
    features['away_form'] = df.get('away_last5', pd.Series(['']*len(df))).apply(parse_form)
    features['form_diff'] = features['home_form'] - features['away_form']

    features['home_rest'] = pd.to_numeric(df.get('home_rest_days', pd.Series([1]*len(df))), errors='coerce').fillna(1)
    features['away_rest'] = pd.to_numeric(df.get('away_rest_days', pd.Series([1]*len(df))), errors='coerce').fillna(1)
    features['rest_advantage'] = features['home_rest'] - features['away_rest']

    features['spread_abs'] = features['spread_home'].abs()
    features['is_favorite'] = (features['spread_home'] < 0).astype(int)

    features['bdl_home_win_pct'] = pd.to_numeric(df.get('bdl_home_win_pct', pd.Series([0.5]*len(df))), errors='coerce').fillna(0.5)
    features['bdl_away_win_pct'] = pd.to_numeric(df.get('bdl_away_win_pct', pd.Series([0.5]*len(df))), errors='coerce').fillna(0.5)
    features['bdl_win_pct_diff'] = features['bdl_home_win_pct'] - features['bdl_away_win_pct']
    features['bdl_home_scoring_margin'] = pd.to_numeric(df.get('bdl_home_scoring_margin', pd.Series([0]*len(df))), errors='coerce').fillna(0)
    features['bdl_away_scoring_margin'] = pd.to_numeric(df.get('bdl_away_scoring_margin', pd.Series([0]*len(df))), errors='coerce').fillna(0)
    features['bdl_scoring_margin_diff'] = features['bdl_home_scoring_margin'] - features['bdl_away_scoring_margin']
    features['bdl_home_avg_pts'] = pd.to_numeric(df.get('bdl_home_avg_pts', pd.Series([80]*len(df))), errors='coerce').fillna(80)
    features['bdl_away_avg_pts'] = pd.to_numeric(df.get('bdl_away_avg_pts', pd.Series([80]*len(df))), errors='coerce').fillna(80)
    features['bdl_projected_total'] = features['bdl_home_avg_pts'] + features['bdl_away_avg_pts']

    return features


def run_backtest():
    print("\n" + "=" * 70)
    print("WNBA WALK-FORWARD BACKTEST WITH SHRINKAGE SWEEP")
    print("=" * 70)

    conn = get_db()

    try:
        conn.execute('SELECT 1 FROM wnba_games LIMIT 1')
    except:
        print("  No wnba_games table. Run: python wnba_backtest.py collect")
        conn.close()
        return None

    df = pd.read_sql_query('''
        SELECT * FROM wnba_games
        WHERE home_score IS NOT NULL AND away_score IS NOT NULL
        AND spread_home IS NOT NULL AND spread_result IS NOT NULL
        AND spread_result != 'PUSH'
    ''', conn)
    conn.close()

    if len(df) < 100:
        print(f"  Only {len(df)} games with spreads + results. Need at least 100.")
        print(f"  Import spread data first: python wnba_backtest.py import_spreads FILE.csv")
        return None

    print(f"  Games with spread data: {len(df)}")

    df['game_date_parsed'] = pd.to_datetime(df['game_date'], errors='coerce')
    df = df.dropna(subset=['game_date_parsed']).copy()
    df['season'] = df['season'].astype(int)

    margin = (df['home_score'] - df['away_score']).astype(float)
    spreads = pd.to_numeric(df['spread_home'], errors='coerce')
    target = (margin + spreads > 0).astype(int)

    seasons = sorted(df['season'].unique())
    if len(seasons) < 2:
        print(f"  Need at least 2 seasons for walk-forward. Have: {seasons}")
        return None

    print(f"  Seasons: {seasons}")
    print(f"  Sweeping shrinkage weights: {SHRINKAGE_WEIGHTS}")
    print(f"  Edge thresholds: {EDGE_THRESHOLDS}")

    implied_prob = odds_to_implied_prob(STANDARD_ODDS)

    all_game_predictions = []

    for i in range(1, len(seasons)):
        train_seasons = seasons[:i]
        test_season = seasons[i]
        train_mask = df['season'].isin(train_seasons)
        test_mask = df['season'] == test_season
        train_df = df[train_mask]
        test_df = df[test_mask]

        if len(train_df) < 50 or len(test_df) < 20:
            print(f"  Skipping season {test_season}: train={len(train_df)}, test={len(test_df)}")
            continue

        X_train = engineer_features(train_df).fillna(0)
        X_test = engineer_features(test_df).fillna(0)
        y_test = target[test_mask]
        margin_train = margin[train_mask]
        margin_test = margin[test_mask]

        all_features = sorted(set(X_train.columns) | set(X_test.columns))
        for f in all_features:
            if f not in X_train.columns:
                X_train[f] = 0
            if f not in X_test.columns:
                X_test[f] = 0
        X_train = X_train[all_features]
        X_test = X_test[all_features]

        scaler = StandardScaler()
        X_train_s = scaler.fit_transform(X_train)
        X_test_s = scaler.transform(X_test)

        margin_gbr = GradientBoostingRegressor(
            n_estimators=200, max_depth=4, learning_rate=0.1, random_state=42
        )
        margin_gbr.fit(X_train_s, margin_train)
        margin_preds = margin_gbr.predict(X_test_s)

        residuals = margin_preds - margin_test.values
        sigma_raw = np.std(residuals)
        sigma = min(max(sigma_raw, SIGMA_FLOOR), SIGMA_CEILING)
        model_mae = np.mean(np.abs(residuals))

        market_mae = np.mean(np.abs(-spreads[test_mask].values - margin_test.values))

        model_closer = np.sum(
            np.abs(margin_preds - margin_test.values) <
            np.abs(-spreads[test_mask].values - margin_test.values)
        )
        model_closer_pct = model_closer / len(test_df) * 100

        test_spreads = spreads[test_mask].values
        open_spreads_vals = pd.to_numeric(test_df['spread_home_open'], errors='coerce').values
        actual_covers = y_test.values
        dates = test_df['game_date_parsed'].values

        print(f"\n  Season {test_season} (test={len(test_df)} games):")
        print(f"    Sigma: {sigma:.1f} (raw {sigma_raw:.1f}) | Model MAE: {model_mae:.1f} | Market MAE: {market_mae:.1f}")
        print(f"    Model closer: {model_closer_pct:.1f}%")

        for j in range(len(test_df)):
            spread = test_spreads[j]
            if pd.isna(spread):
                continue

            pred_margin_raw = margin_preds[j]
            market_margin = -spread

            open_spread = open_spreads_vals[j] if j < len(open_spreads_vals) else np.nan
            line_move = 0.0
            if not pd.isna(open_spread):
                move = spread - open_spread
                if move > 0 and move >= 1.0:
                    line_move = move

            covered = actual_covers[j]

            all_game_predictions.append({
                'season': test_season,
                'date': dates[j],
                'spread': spread,
                'pred_margin_raw': pred_margin_raw,
                'market_margin': market_margin,
                'sigma': sigma,
                'sigma_raw': sigma_raw,
                'model_mae': model_mae,
                'market_mae': market_mae,
                'model_closer_pct': model_closer_pct,
                'line_move': line_move,
                'spread_abs': abs(spread),
                'home_cover': covered,
            })

    if not all_game_predictions:
        print("\n  No predictions generated. Check data.")
        return None

    print(f"\n  Total game predictions: {len(all_game_predictions)}")

    print(f"\n{'='*90}")
    print("SHRINKAGE SWEEP RESULTS")
    print(f"{'='*90}")

    sweep_results = []

    for shrinkage in SHRINKAGE_WEIGHTS:
        for edge_thresh in EDGE_THRESHOLDS:
            wins = 0
            losses = 0
            total_profit = 0
            cumulative = [0]
            season_bets = {}

            for g in all_game_predictions:
                pred_margin = (1 - shrinkage) * g['pred_margin_raw'] + shrinkage * g['market_margin']
                z_score = (pred_margin + g['spread']) / g['sigma']
                home_cover_prob = float(norm.cdf(z_score))

                if home_cover_prob >= 0.5:
                    confidence = home_cover_prob
                    pick_side = 'home'
                else:
                    confidence = 1 - home_cover_prob
                    pick_side = 'away'

                raw_edge = min((confidence - implied_prob) * 100, MAX_EDGE_PCT)

                adj_edge = raw_edge - (g['line_move'] * LINE_MOVE_PENALTY_PER_PT)
                if g['line_move'] >= LINE_MOVE_HARD_STOP and adj_edge < LINE_MOVE_HARD_STOP_MIN_EDGE:
                    continue
                if adj_edge < edge_thresh:
                    continue
                if confidence < 0.55:
                    continue

                covered = g['home_cover']
                if pick_side == 'away':
                    covered = 1 - covered

                won = bool(covered)
                profit = 0.9091 if won else -1.0
                total_profit += profit
                cumulative.append(cumulative[-1] + profit)

                if won:
                    wins += 1
                else:
                    losses += 1

                s = g['season']
                season_bets.setdefault(s, {'wins': 0, 'losses': 0, 'profit': 0})
                season_bets[s]['wins' if won else 'losses'] += 1
                season_bets[s]['profit'] += profit

            total_bets = wins + losses
            if total_bets < 5:
                continue

            roi = total_profit / total_bets * 100
            win_rate = wins / total_bets * 100

            num_seasons = len(season_bets)
            total_season_games = sum(
                len([g for g in all_game_predictions if g['season'] == s])
                for s in season_bets
            )
            selectivity = total_bets / total_season_games * 100 if total_season_games > 0 else 0

            picks_per_season = total_bets / num_seasons if num_seasons > 0 else 0

            peak = 0
            max_dd = 0
            for v in cumulative:
                if v > peak:
                    peak = v
                if v - peak < max_dd:
                    max_dd = v - peak

            profitable_seasons = sum(1 for s in season_bets.values() if s['profit'] > 0)

            sweep_results.append({
                'shrinkage': shrinkage,
                'edge_thresh': edge_thresh,
                'bets': total_bets,
                'wins': wins,
                'win_rate': win_rate,
                'roi': roi,
                'profit': total_profit,
                'selectivity': selectivity,
                'picks_per_season': picks_per_season,
                'max_drawdown': max_dd,
                'profitable_seasons': profitable_seasons,
                'total_seasons': num_seasons,
                'season_detail': season_bets,
            })

    if not sweep_results:
        print("  No valid sweep results. Data may be insufficient.")
        return None

    sweep_results.sort(key=lambda x: x['roi'], reverse=True)

    print(f"\n{'Shrink':>7} {'Edge':>6} {'Bets':>6} {'Win%':>6} {'ROI':>7} {'P/Szn':>6} {'Select':>7} {'MaxDD':>7} {'ProfS':>6}")
    print("-" * 70)
    for r in sweep_results[:20]:
        print(f"{r['shrinkage']:>6.1f}  {r['edge_thresh']:>5.1f}% {r['bets']:>6} "
              f"{r['win_rate']:>5.1f}% {r['roi']:>+6.1f}% {r['picks_per_season']:>5.0f} "
              f"{r['selectivity']:>6.1f}% {r['max_drawdown']:>+6.1f}u "
              f"{r['profitable_seasons']:>2}/{r['total_seasons']}")

    brand_fit = [r for r in sweep_results
                 if 5 <= r['picks_per_season'] <= 25
                 and r['roi'] > 0
                 and r['win_rate'] > 52]
    brand_fit.sort(key=lambda x: x['roi'], reverse=True)

    if brand_fit:
        print(f"\n{'='*70}")
        print("BRAND-FIT COMBOS (5-25 picks/season, ROI > 0, WR > 52%)")
        print(f"{'='*70}")
        print(f"{'Shrink':>7} {'Edge':>6} {'Bets':>6} {'Win%':>6} {'ROI':>7} {'P/Szn':>6} {'Select':>7}")
        print("-" * 55)
        for r in brand_fit[:10]:
            print(f"{r['shrinkage']:>6.1f}  {r['edge_thresh']:>5.1f}% {r['bets']:>6} "
                  f"{r['win_rate']:>5.1f}% {r['roi']:>+6.1f}% {r['picks_per_season']:>5.0f} "
                  f"{r['selectivity']:>6.1f}%")

    avg_sigma = np.mean([g['sigma'] for g in all_game_predictions])
    avg_model_mae = np.mean([g['model_mae'] for g in all_game_predictions])
    avg_market_mae = np.mean([g['market_mae'] for g in all_game_predictions])
    avg_model_closer = np.mean([g['model_closer_pct'] for g in all_game_predictions])

    report = {
        'games_analyzed': len(all_game_predictions),
        'seasons': sorted(set(g['season'] for g in all_game_predictions)),
        'avg_sigma': round(avg_sigma, 1),
        'avg_model_mae': round(avg_model_mae, 1),
        'avg_market_mae': round(avg_market_mae, 1),
        'model_closer_pct': round(avg_model_closer, 1),
        'sweep_results': sweep_results,
        'brand_fit': brand_fit,
        'best_overall': sweep_results[0] if sweep_results else None,
        'best_brand': brand_fit[0] if brand_fit else None,
    }

    generate_report(report)
    return report


def generate_report(report):
    print(f"\n{'='*70}")
    print("WNBA BACKTEST FINAL REPORT")
    print(f"{'='*70}")

    print(f"\n  DATA SUMMARY")
    print(f"    Games analyzed:  {report['games_analyzed']}")
    print(f"    Seasons:         {report['seasons']}")
    print(f"    Avg sigma:       {report['avg_sigma']} pts")
    print(f"    Model MAE:       {report['avg_model_mae']} pts")
    print(f"    Market MAE:      {report['avg_market_mae']} pts")
    print(f"    Model closer:    {report['model_closer_pct']}%")

    model_adds_value = report['avg_model_mae'] < report['avg_market_mae'] * 1.2

    print(f"\n  MODEL vs MARKET")
    if report['avg_model_mae'] < report['avg_market_mae']:
        print(f"    Model is MORE accurate than market (MAE {report['avg_model_mae']} < {report['avg_market_mae']})")
        print(f"    Model is closer to reality {report['model_closer_pct']}% of the time")
    else:
        gap = report['avg_model_mae'] - report['avg_market_mae']
        print(f"    Market is more accurate (Market MAE {report['avg_market_mae']} < Model MAE {report['avg_model_mae']})")
        print(f"    Gap: {gap:.1f} pts — {'manageable with shrinkage' if gap < 3 else 'significant'}")

    best = report.get('best_brand') or report.get('best_overall')

    if best and best['roi'] > 0 and best['win_rate'] > 52:
        print(f"\n  RECOMMENDATION: PROCEED WITH WNBA")
        print(f"    Recommended shrinkage: {best['shrinkage']}")
        print(f"    Recommended edge threshold: {best['edge_thresh']}%")
        print(f"    Expected selectivity: {best['selectivity']:.1f}%")
        print(f"    Expected picks/season: {best['picks_per_season']:.0f}")
        print(f"    Backtest win rate: {best['win_rate']:.1f}%")
        print(f"    Backtest ROI: {best['roi']:+.1f}%")
        print(f"    Recommended sigma: {report['avg_sigma']}")

        print(f"\n  SPORT_CONFIG VALUES:")
        print(f"    'sigma': {report['avg_sigma']},")
        print(f"    'model_weight': {round(1 - best['shrinkage'], 1)},  # model_weight = 1 - shrinkage")
        print(f"    'edge_threshold_pct': {best['edge_thresh']},")
        print(f"    'max_edge_pct': {MAX_EDGE_PCT},")
        print(f"    'margin_std_floor': {SIGMA_FLOOR},")
        print(f"    'margin_std_ceiling': {SIGMA_CEILING},")
    else:
        print(f"\n  RECOMMENDATION: DO NOT SHIP WNBA")
        print(f"    The model does not demonstrate sufficient edge over the market.")
        if best:
            print(f"    Best ROI found: {best['roi']:+.1f}% (need > 0%)")
            print(f"    Best win rate: {best['win_rate']:.1f}% (need > 52%)")
        print(f"    A bad WNBA launch would hurt the NBA brand.")

    print(f"\n{'='*70}")


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return

    cmd = sys.argv[1].lower()

    if cmd == 'collect':
        collect_espn_scores()
        collect_balldontlie_games()
        conn = get_db()
        compute_rolling_stats(conn)
        compute_team_metrics(conn)
        conn.close()
        show_status()

    elif cmd == 'import_spreads':
        if len(sys.argv) < 3:
            print("Usage: python wnba_backtest.py import_spreads FILE.csv")
            print("\nExpected CSV columns:")
            print("  Required: date, home_team, spread_home")
            print("  Optional: spread_home_open, total, home_ml, away_ml")
            return
        import_spreads_csv(sys.argv[2])

    elif cmd == 'status':
        show_status()

    elif cmd == 'backtest':
        run_backtest()

    elif cmd == 'report':
        run_backtest()

    else:
        print(f"Unknown command: {cmd}")
        print(__doc__)


if __name__ == '__main__':
    main()
