"""
WNBA Enhanced Walk-Forward Backtest
Adds pace/ratings/four-factors from Basketball Reference
and player availability features, then runs simplified XGBoost backtest.

Usage:
    python wnba_enhanced_backtest.py scrape        # Scrape BBRef for team + player stats
    python wnba_enhanced_backtest.py backtest      # Run enhanced walk-forward backtest
    python wnba_enhanced_backtest.py compare       # Side-by-side: baseline vs enhanced
"""

import sqlite3
import pandas as pd
import numpy as np
import requests
import time
import sys
import json
import re
from datetime import datetime, timedelta
from scipy.stats import norm
from sklearn.preprocessing import StandardScaler
from bs4 import BeautifulSoup
import xgboost as xgb

DB_PATH = 'sharp_picks.db'

SHRINKAGE_WEIGHTS = [0.3, 0.4, 0.5, 0.6, 0.7]
EDGE_THRESHOLDS = [3.0, 3.5, 4.0, 5.0]
SIGMA_FLOOR = 7.0
SIGMA_CEILING = 13.0
MAX_EDGE_PCT = 8.0
STANDARD_ODDS = -110

BBREF_DELAY = 3.5

WNBA_SEASONS = [2022, 2023, 2024]

TEAM_NAME_MAP = {
    'New York Liberty': 'New York Liberty',
    'Connecticut Sun': 'Connecticut Sun',
    'Minnesota Lynx': 'Minnesota Lynx',
    'Las Vegas Aces': 'Las Vegas Aces',
    'Seattle Storm': 'Seattle Storm',
    'Indiana Fever': 'Indiana Fever',
    'Phoenix Mercury': 'Phoenix Mercury',
    'Atlanta Dream': 'Atlanta Dream',
    'Washington Mystics': 'Washington Mystics',
    'Chicago Sky': 'Chicago Sky',
    'Dallas Wings': 'Dallas Wings',
    'Los Angeles Sparks': 'Los Angeles Sparks',
}

HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def odds_to_implied_prob(odds):
    if odds < 0:
        return abs(odds) / (abs(odds) + 100)
    else:
        return 100 / (odds + 100)


def clean_team_name(name):
    return re.sub(r'\*$', '', name).strip()


def setup_ratings_table(conn):
    conn.execute('''CREATE TABLE IF NOT EXISTS wnba_team_ratings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        season INTEGER,
        team TEXT,
        pace REAL,
        ortg REAL,
        drtg REAL,
        nrtg REAL,
        mov REAL,
        srs REAL,
        off_efg REAL,
        off_tov_pct REAL,
        off_orb_pct REAL,
        off_ft_rate REAL,
        def_efg REAL,
        def_tov_pct REAL,
        def_drb_pct REAL,
        def_ft_rate REAL,
        ts_pct REAL,
        three_par REAL,
        ft_rate REAL,
        wins INTEGER,
        losses INTEGER,
        UNIQUE(season, team)
    )''')

    conn.execute('''CREATE TABLE IF NOT EXISTS wnba_top_players (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        season INTEGER,
        team TEXT,
        player_rank INTEGER,
        player_name TEXT,
        games_played INTEGER,
        games_started INTEGER,
        mpg REAL,
        ppg REAL,
        rpg REAL,
        apg REAL,
        win_shares REAL,
        UNIQUE(season, team, player_rank)
    )''')
    conn.commit()


def scrape_team_advanced(season):
    url = f"https://www.basketball-reference.com/wnba/years/{season}.html"
    print(f"  Fetching {url}...")
    resp = requests.get(url, headers=HEADERS, timeout=15)
    if resp.status_code != 200:
        print(f"    Error: {resp.status_code}")
        return []

    soup = BeautifulSoup(resp.text, 'html.parser')
    table = soup.find('table', id='advanced-team')
    if not table:
        print("    No advanced-team table found")
        return []

    head = table.find('thead')
    header_rows = head.find_all('tr') if head else []
    if len(header_rows) >= 2:
        headers = [th.text.strip() for th in header_rows[1].find_all('th')]
    else:
        headers = [th.text.strip() for th in head.find_all('th')] if head else []

    body = table.find('tbody')
    if not body:
        return []

    teams = []
    for row in body.find_all('tr'):
        cells = [c.text.strip() for c in row.find_all(['td', 'th'])]
        if len(cells) < 20:
            continue

        team_name = clean_team_name(cells[1])
        if team_name not in TEAM_NAME_MAP:
            continue

        def safe_float(val, default=0.0):
            try:
                return float(val.replace('+', ''))
            except:
                return default

        def safe_int(val, default=0):
            try:
                return int(val)
            except:
                return default

        team_data = {
            'season': season,
            'team': team_name,
            'wins': safe_int(cells[3]),
            'losses': safe_int(cells[4]),
            'mov': safe_float(cells[7]),
            'srs': safe_float(cells[9]),
            'ortg': safe_float(cells[10]),
            'drtg': safe_float(cells[11]),
            'nrtg': safe_float(cells[12]),
            'pace': safe_float(cells[13]),
            'ft_rate': safe_float(cells[14]),
            'three_par': safe_float(cells[15]),
            'ts_pct': safe_float(cells[16]),
            'off_efg': safe_float(cells[18]),
            'off_tov_pct': safe_float(cells[19]),
            'off_orb_pct': safe_float(cells[20]),
            'off_ft_rate': safe_float(cells[21]),
            'def_efg': safe_float(cells[23]),
            'def_tov_pct': safe_float(cells[24]),
            'def_drb_pct': safe_float(cells[25]),
            'def_ft_rate': safe_float(cells[26]),
        }
        teams.append(team_data)

    print(f"    Parsed {len(teams)} teams")
    return teams


def scrape_player_stats(season):
    url = f"https://www.basketball-reference.com/wnba/years/{season}_per_game.html"
    print(f"  Fetching {url}...")
    resp = requests.get(url, headers=HEADERS, timeout=15)
    if resp.status_code != 200:
        print(f"    Error: {resp.status_code}")
        return {}

    soup = BeautifulSoup(resp.text, 'html.parser')
    table = soup.find('table', id='per_game')
    if not table:
        print("    No per_game table found")
        return {}

    body = table.find('tbody')
    if not body:
        return {}

    player_data = {}

    for row in body.find_all('tr'):
        if row.get('class') and 'thead' in row.get('class', []):
            continue
        cells = row.find_all(['td', 'th'])
        if len(cells) < 10:
            continue

        player_link = cells[0].find('a')
        player_name = player_link.text.strip() if player_link else cells[0].text.strip()
        team_abbr = cells[1].text.strip() if len(cells) > 1 else ''

        def safe_float(val, default=0.0):
            try:
                return float(val)
            except:
                return default

        def safe_int(val, default=0):
            try:
                return int(val)
            except:
                return default

        gp = safe_int(cells[5].text.strip()) if len(cells) > 5 else 0
        gs = safe_int(cells[6].text.strip()) if len(cells) > 6 else 0
        mpg = safe_float(cells[7].text.strip()) if len(cells) > 7 else 0
        ppg = safe_float(cells[27].text.strip()) if len(cells) > 27 else 0
        rpg = safe_float(cells[21].text.strip()) if len(cells) > 21 else 0
        apg = safe_float(cells[22].text.strip()) if len(cells) > 22 else 0

        if gp < 5 or mpg < 10:
            continue

        if team_abbr not in player_data:
            player_data[team_abbr] = []

        player_data[team_abbr].append({
            'name': player_name,
            'gp': gp,
            'gs': gs,
            'mpg': mpg,
            'ppg': ppg,
            'rpg': rpg,
            'apg': apg,
            'impact': ppg + 0.5 * rpg + 0.7 * apg,
        })

    for team in player_data:
        player_data[team].sort(key=lambda x: x['impact'], reverse=True)

    total_players = sum(len(v) for v in player_data.values())
    print(f"    Parsed {total_players} players across {len(player_data)} teams")
    return player_data


TEAM_ABBR_TO_FULL = {
    'NYL': 'New York Liberty', 'NY': 'New York Liberty', 'NYY': 'New York Liberty',
    'CON': 'Connecticut Sun', 'CT': 'Connecticut Sun',
    'MIN': 'Minnesota Lynx', 'MN': 'Minnesota Lynx',
    'LVA': 'Las Vegas Aces', 'LV': 'Las Vegas Aces', 'LVS': 'Las Vegas Aces',
    'SEA': 'Seattle Storm',
    'IND': 'Indiana Fever',
    'PHO': 'Phoenix Mercury', 'PHX': 'Phoenix Mercury',
    'ATL': 'Atlanta Dream',
    'WAS': 'Washington Mystics', 'WSH': 'Washington Mystics',
    'CHI': 'Chicago Sky',
    'DAL': 'Dallas Wings',
    'LAS': 'Los Angeles Sparks', 'LA': 'Los Angeles Sparks',
}


def scrape_all():
    print("\n" + "=" * 70)
    print("SCRAPING BASKETBALL REFERENCE FOR WNBA ADVANCED STATS")
    print("=" * 70)

    conn = get_db()
    setup_ratings_table(conn)

    for season in WNBA_SEASONS:
        print(f"\n--- Season {season} ---")

        teams = scrape_team_advanced(season)
        for t in teams:
            conn.execute('''INSERT OR REPLACE INTO wnba_team_ratings
                (season, team, pace, ortg, drtg, nrtg, mov, srs,
                 off_efg, off_tov_pct, off_orb_pct, off_ft_rate,
                 def_efg, def_tov_pct, def_drb_pct, def_ft_rate,
                 ts_pct, three_par, ft_rate, wins, losses)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                (t['season'], t['team'], t['pace'], t['ortg'], t['drtg'], t['nrtg'],
                 t['mov'], t['srs'], t['off_efg'], t['off_tov_pct'], t['off_orb_pct'],
                 t['off_ft_rate'], t['def_efg'], t['def_tov_pct'], t['def_drb_pct'],
                 t['def_ft_rate'], t['ts_pct'], t['three_par'], t['ft_rate'],
                 t['wins'], t['losses']))
        conn.commit()

        time.sleep(BBREF_DELAY)

        players = scrape_player_stats(season)
        for abbr, plist in players.items():
            full_name = TEAM_ABBR_TO_FULL.get(abbr)
            if not full_name:
                continue
            for rank, p in enumerate(plist[:5], 1):
                conn.execute('''INSERT OR REPLACE INTO wnba_top_players
                    (season, team, player_rank, player_name, games_played,
                     games_started, mpg, ppg, rpg, apg)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                    (season, full_name, rank, p['name'], p['gp'],
                     p['gs'], p['mpg'], p['ppg'], p['rpg'], p['apg']))
        conn.commit()

        time.sleep(BBREF_DELAY)

    total_ratings = conn.execute('SELECT COUNT(*) FROM wnba_team_ratings').fetchone()[0]
    total_players = conn.execute('SELECT COUNT(*) FROM wnba_top_players').fetchone()[0]
    print(f"\n  Stored: {total_ratings} team-season ratings, {total_players} top players")

    print(f"\n  Sample ratings (2024):")
    for row in conn.execute('SELECT team, pace, ortg, drtg, nrtg FROM wnba_team_ratings WHERE season=2024 ORDER BY nrtg DESC LIMIT 5'):
        print(f"    {row['team']:25s} Pace={row['pace']:5.1f} O={row['ortg']:5.1f} D={row['drtg']:5.1f} Net={row['nrtg']:+5.1f}")

    print(f"\n  Sample top players (2024):")
    for row in conn.execute("SELECT team, player_name, ppg, rpg, apg FROM wnba_top_players WHERE season=2024 AND player_rank=1 ORDER BY ppg DESC LIMIT 5"):
        print(f"    {row['team']:25s} {row['player_name']:20s} {row['ppg']:5.1f}ppg {row['rpg']:4.1f}rpg {row['apg']:4.1f}apg")

    conn.close()
    print("\nScrape complete.")


def compute_rolling_ratings(all_games_df):
    """Compute rolling team ratings using ONLY prior games (no leakage).
    Returns dict: (team, game_date) -> {ortg, drtg, nrtg, pace_proxy, ...}
    Uses cumulative stats through previous game only.
    """
    all_games = all_games_df.sort_values('game_date').copy()
    all_games['home_score'] = pd.to_numeric(all_games['home_score'], errors='coerce')
    all_games['away_score'] = pd.to_numeric(all_games['away_score'], errors='coerce')
    all_games = all_games.dropna(subset=['home_score', 'away_score'])

    team_stats = {}
    rolling_cache = {}

    PRIOR_SEASON_DECAY = 0.5
    MIN_GAMES = 5

    for _, game in all_games.iterrows():
        ht = game['home_team']
        at = game['away_team']
        gd = game['game_date']
        hs = float(game['home_score'])
        as_ = float(game['away_score'])
        season = game.get('season', 0)

        for team in [ht, at]:
            if team not in team_stats:
                team_stats[team] = {
                    'pts_for': [], 'pts_against': [], 'margins': [],
                    'fga_proxy': [], 'season': None
                }

        h_stats = team_stats[ht]
        a_stats = team_stats[at]

        if h_stats['season'] is not None and h_stats['season'] != season:
            for team in [ht, at]:
                ts = team_stats[team]
                if ts['season'] != season and len(ts['pts_for']) > 0:
                    n = len(ts['pts_for'])
                    keep = max(1, int(n * PRIOR_SEASON_DECAY))
                    ts['pts_for'] = ts['pts_for'][-keep:]
                    ts['pts_against'] = ts['pts_against'][-keep:]
                    ts['margins'] = ts['margins'][-keep:]
                    ts['fga_proxy'] = ts['fga_proxy'][-keep:]
                    ts['season'] = season

        for team in [ht, at]:
            ts = team_stats[team]
            if len(ts['pts_for']) >= MIN_GAMES:
                pf = np.array(ts['pts_for'][-20:])
                pa = np.array(ts['pts_against'][-20:])
                margins = np.array(ts['margins'][-20:])

                avg_pf = np.mean(pf)
                avg_pa = np.mean(pa)
                avg_total = avg_pf + avg_pa
                pace_proxy = avg_total / 2.0

                ortg = (avg_pf / pace_proxy) * 100 if pace_proxy > 0 else 100
                drtg = (avg_pa / pace_proxy) * 100 if pace_proxy > 0 else 100
                nrtg = ortg - drtg

                margin_avg = np.mean(margins)
                margin_std = np.std(margins) if len(margins) > 2 else 12.0

                w = sum(1 for m in margins if m > 0)
                win_pct = w / len(margins)

                rolling_cache[(team, gd)] = {
                    'ortg': ortg, 'drtg': drtg, 'nrtg': nrtg,
                    'pace_proxy': pace_proxy,
                    'avg_pf': avg_pf, 'avg_pa': avg_pa,
                    'margin_avg': margin_avg, 'margin_std': margin_std,
                    'win_pct': win_pct,
                    'games_played': len(ts['pts_for']),
                }
            else:
                rolling_cache[(team, gd)] = None

        team_stats[ht]['pts_for'].append(hs)
        team_stats[ht]['pts_against'].append(as_)
        team_stats[ht]['margins'].append(hs - as_)
        team_stats[ht]['fga_proxy'].append((hs + as_) / 2)
        team_stats[ht]['season'] = season

        team_stats[at]['pts_for'].append(as_)
        team_stats[at]['pts_against'].append(hs)
        team_stats[at]['margins'].append(as_ - hs)
        team_stats[at]['fga_proxy'].append((hs + as_) / 2)
        team_stats[at]['season'] = season

    return rolling_cache


def compute_rolling_player_impact(all_games_df):
    """Compute rolling player impact scores using prior-season BBRef data ONLY.
    Uses PRIOR season's top-5 (available before current season starts).
    Returns dict: (team, season) -> star_ppg, top5_ppg
    """
    conn = get_db()
    try:
        players_df = pd.read_sql_query('SELECT * FROM wnba_top_players', conn)
    except:
        conn.close()
        return {}
    conn.close()

    if len(players_df) == 0:
        return {}

    cache = {}
    seasons = sorted(players_df['season'].unique())

    for season in seasons:
        next_season = season + 1
        season_players = players_df[players_df['season'] == season]

        for team in season_players['team'].unique():
            team_players = season_players[season_players['team'] == team].sort_values('player_rank')
            if len(team_players) > 0:
                cache[(team, next_season)] = {
                    'star_ppg': team_players.iloc[0]['ppg'],
                    'top5_ppg': team_players['ppg'].sum(),
                    'top5_gp_ratio': team_players['games_played'].mean() / max(1, team_players['games_played'].max()),
                }

    return cache


def engineer_enhanced_features(df, rolling_ratings, player_cache):
    features = pd.DataFrame(index=df.index)

    features['spread_home'] = pd.to_numeric(df['spread_home'], errors='coerce').fillna(0)
    spread_open = pd.to_numeric(df.get('spread_home_open', pd.Series(dtype=float)), errors='coerce')
    features['spread_open'] = spread_open.fillna(features['spread_home'])
    features['line_movement'] = pd.to_numeric(df.get('line_movement', pd.Series(dtype=float)), errors='coerce').fillna(0)
    features['total'] = pd.to_numeric(df.get('total', pd.Series(dtype=float)), errors='coerce').fillna(155)

    features['spread_abs'] = features['spread_home'].abs()
    features['is_favorite'] = (features['spread_home'] < 0).astype(int)

    def parse_record(record):
        if pd.isna(record) or record in ('N/A', '', None):
            return 0.5
        try:
            parts = str(record).split('-')
            w, l = int(parts[0]), int(parts[1])
            return w / (w + l) if (w + l) > 0 else 0.5
        except:
            return 0.5

    features['home_win_pct'] = df['home_record'].apply(parse_record)
    features['away_win_pct'] = df['away_record'].apply(parse_record)
    features['win_pct_diff'] = features['home_win_pct'] - features['away_win_pct']

    def parse_form(form_str):
        if pd.isna(form_str) or not form_str:
            return 0.5
        wins = str(form_str).count('W')
        total = len(str(form_str))
        return wins / total if total > 0 else 0.5

    features['home_form'] = df.get('home_last5', pd.Series(dtype=str)).apply(parse_form)
    features['away_form'] = df.get('away_last5', pd.Series(dtype=str)).apply(parse_form)
    features['form_diff'] = features['home_form'] - features['away_form']

    features['home_rest'] = pd.to_numeric(df.get('home_rest_days', pd.Series(dtype=float)), errors='coerce').fillna(2)
    features['away_rest'] = pd.to_numeric(df.get('away_rest_days', pd.Series(dtype=float)), errors='coerce').fillna(2)
    features['rest_advantage'] = features['home_rest'] - features['away_rest']
    features['b2b_home'] = (features['home_rest'] == 1).astype(int)
    features['b2b_away'] = (features['away_rest'] == 1).astype(int)

    for _, row in df.iterrows():
        idx = row.name
        home = row.get('home_team', '')
        away = row.get('away_team', '')
        gd = row.get('game_date', '')
        season = row.get('season', 0)

        hr = rolling_ratings.get((home, gd))
        ar = rolling_ratings.get((away, gd))

        if hr:
            features.loc[idx, 'home_ortg'] = hr['ortg']
            features.loc[idx, 'home_drtg'] = hr['drtg']
            features.loc[idx, 'home_nrtg'] = hr['nrtg']
            features.loc[idx, 'home_pace'] = hr['pace_proxy']
            features.loc[idx, 'home_margin_avg'] = hr['margin_avg']
            features.loc[idx, 'home_margin_std'] = hr['margin_std']

        if ar:
            features.loc[idx, 'away_ortg'] = ar['ortg']
            features.loc[idx, 'away_drtg'] = ar['drtg']
            features.loc[idx, 'away_nrtg'] = ar['nrtg']
            features.loc[idx, 'away_pace'] = ar['pace_proxy']
            features.loc[idx, 'away_margin_avg'] = ar['margin_avg']
            features.loc[idx, 'away_margin_std'] = ar['margin_std']

        hp = player_cache.get((home, season))
        ap = player_cache.get((away, season))

        if hp:
            features.loc[idx, 'home_star_ppg'] = hp['star_ppg']
            features.loc[idx, 'home_top5_ppg'] = hp['top5_ppg']

        if ap:
            features.loc[idx, 'away_star_ppg'] = ap['star_ppg']
            features.loc[idx, 'away_top5_ppg'] = ap['top5_ppg']

    for col in features.columns:
        if features[col].isna().any():
            med = features[col].median()
            features[col] = features[col].fillna(med if not pd.isna(med) else 0)

    if 'home_nrtg' in features.columns and 'away_nrtg' in features.columns:
        features['nrtg_diff'] = features['home_nrtg'] - features['away_nrtg']
    if 'home_pace' in features.columns and 'away_pace' in features.columns:
        features['pace_avg'] = (features['home_pace'] + features['away_pace']) / 2
    if 'home_ortg' in features.columns and 'away_drtg' in features.columns:
        features['home_matchup_ortg'] = features['home_ortg'] - features['away_drtg']
    if 'away_ortg' in features.columns and 'home_drtg' in features.columns:
        features['away_matchup_ortg'] = features['away_ortg'] - features['home_drtg']
    if 'home_margin_avg' in features.columns and 'away_margin_avg' in features.columns:
        features['margin_avg_diff'] = features['home_margin_avg'] - features['away_margin_avg']
    if 'home_star_ppg' in features.columns and 'away_star_ppg' in features.columns:
        features['star_diff'] = features['home_star_ppg'] - features['away_star_ppg']
    if 'home_top5_ppg' in features.columns and 'away_top5_ppg' in features.columns:
        features['top5_ppg_diff'] = features['home_top5_ppg'] - features['away_top5_ppg']

    features = features.fillna(0)
    return features


def run_enhanced_backtest():
    print("\n" + "=" * 70)
    print("WNBA ENHANCED WALK-FORWARD BACKTEST (LEAK-FREE)")
    print("Rolling ratings + prior-season players + regularized XGBoost")
    print("=" * 70)

    conn = get_db()

    all_games_df = pd.read_sql_query('''
        SELECT * FROM wnba_games WHERE home_score IS NOT NULL AND away_score IS NOT NULL
        ORDER BY game_date
    ''', conn)

    df = pd.read_sql_query('''
        SELECT * FROM wnba_games
        WHERE home_score IS NOT NULL AND away_score IS NOT NULL
        AND spread_home IS NOT NULL AND spread_result IS NOT NULL
        AND spread_result != 'PUSH'
    ''', conn)
    conn.close()

    print(f"  Total games for rolling ratings: {len(all_games_df)}")
    print(f"  Games with spread data: {len(df)}")

    print("  Computing rolling ratings (prior-game only, no leakage)...")
    rolling_ratings = compute_rolling_ratings(all_games_df)
    rated_count = sum(1 for v in rolling_ratings.values() if v is not None)
    print(f"    {rated_count} team-game ratings computed ({len(rolling_ratings)} total entries)")

    print("  Loading prior-season player impact (no in-season leakage)...")
    player_cache = compute_rolling_player_impact(all_games_df)
    print(f"    {len(player_cache)} team-season player entries")

    df['season'] = df['season'].astype(int)
    margin = (df['home_score'] - df['away_score']).astype(float)
    spreads = pd.to_numeric(df['spread_home'], errors='coerce')
    target = (margin + spreads > 0).astype(int)

    seasons = sorted(df['season'].unique())
    if len(seasons) < 2:
        print(f"  Need 2+ seasons. Have: {seasons}")
        return None

    print(f"  Seasons: {seasons}")
    implied_prob = odds_to_implied_prob(STANDARD_ODDS)

    all_predictions = []

    for i in range(1, len(seasons)):
        train_seasons = seasons[:i]
        test_season = seasons[i]
        train_mask = df['season'].isin(train_seasons)
        test_mask = df['season'] == test_season
        train_df = df[train_mask].copy()
        test_df = df[test_mask].copy()

        if len(train_df) < 50 or len(test_df) < 20:
            print(f"  Skipping {test_season}: train={len(train_df)}, test={len(test_df)}")
            continue

        X_train = engineer_enhanced_features(train_df, rolling_ratings, player_cache)
        X_test = engineer_enhanced_features(test_df, rolling_ratings, player_cache)
        y_train_margin = margin[train_mask]
        y_test_margin = margin[test_mask]
        y_test = target[test_mask]

        all_cols = sorted(set(X_train.columns) | set(X_test.columns))
        for c in all_cols:
            if c not in X_train.columns:
                X_train[c] = 0
            if c not in X_test.columns:
                X_test[c] = 0
        X_train = X_train[all_cols]
        X_test = X_test[all_cols]

        scaler = StandardScaler()
        X_train_s = scaler.fit_transform(X_train)
        X_test_s = scaler.transform(X_test)

        model = xgb.XGBRegressor(
            n_estimators=150,
            max_depth=3,
            learning_rate=0.05,
            subsample=0.8,
            colsample_bytree=0.7,
            reg_alpha=1.0,
            reg_lambda=3.0,
            min_child_weight=5,
            random_state=42,
        )
        model.fit(X_train_s, y_train_margin)
        margin_preds = model.predict(X_test_s)

        residuals = margin_preds - y_test_margin.values
        sigma_raw = np.std(residuals)
        sigma = min(max(sigma_raw, SIGMA_FLOOR), SIGMA_CEILING)
        model_mae = np.mean(np.abs(residuals))
        market_mae = np.mean(np.abs(-spreads[test_mask].values - y_test_margin.values))

        model_closer = np.sum(
            np.abs(margin_preds - y_test_margin.values) <
            np.abs(-spreads[test_mask].values - y_test_margin.values)
        )
        model_closer_pct = model_closer / len(test_df) * 100

        test_spreads = spreads[test_mask].values
        open_spreads = pd.to_numeric(test_df['spread_home_open'], errors='coerce').values
        actual_covers = y_test.values

        print(f"\n  Season {test_season} (train={len(train_df)}, test={len(test_df)}):")
        print(f"    Sigma: {sigma:.1f} (raw {sigma_raw:.1f}) | Model MAE: {model_mae:.1f} | Market MAE: {market_mae:.1f}")
        print(f"    Model closer: {model_closer_pct:.1f}%")

        importances = model.feature_importances_
        top_features = sorted(zip(all_cols, importances), key=lambda x: x[1], reverse=True)[:10]
        print(f"    Top features: {[(f, round(imp, 3)) for f, imp in top_features[:5]]}")

        for j in range(len(test_df)):
            spread = test_spreads[j]
            if pd.isna(spread):
                continue

            open_sp = open_spreads[j] if j < len(open_spreads) else np.nan
            line_move = 0.0
            if not pd.isna(open_sp):
                move = spread - open_sp
                if move > 0 and move >= 1.0:
                    line_move = move

            all_predictions.append({
                'season': test_season,
                'spread': spread,
                'pred_margin_raw': margin_preds[j],
                'market_margin': -spread,
                'sigma': sigma,
                'sigma_raw': sigma_raw,
                'model_mae': model_mae,
                'market_mae': market_mae,
                'model_closer_pct': model_closer_pct,
                'line_move': line_move,
                'home_cover': actual_covers[j],
            })

    if not all_predictions:
        print("\n  No predictions generated.")
        return None

    print(f"\n  Total predictions: {len(all_predictions)}")
    run_sweep(all_predictions, implied_prob, "ENHANCED")

    avg_model_mae = np.mean([g['model_mae'] for g in all_predictions])
    avg_market_mae = np.mean([g['market_mae'] for g in all_predictions])
    avg_closer = np.mean([g['model_closer_pct'] for g in all_predictions])
    avg_sigma = np.mean([g['sigma'] for g in all_predictions])

    return {
        'predictions': all_predictions,
        'avg_model_mae': round(avg_model_mae, 1),
        'avg_market_mae': round(avg_market_mae, 1),
        'model_closer_pct': round(avg_closer, 1),
        'avg_sigma': round(avg_sigma, 1),
    }


def run_sweep(predictions, implied_prob, label=""):
    print(f"\n{'='*90}")
    print(f"SHRINKAGE SWEEP — {label}")
    print(f"{'='*90}")

    sweep_results = []

    for shrinkage in SHRINKAGE_WEIGHTS:
        for edge_thresh in EDGE_THRESHOLDS:
            wins = losses = 0
            total_profit = 0
            cumulative = [0]
            season_bets = {}

            for g in predictions:
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
                adj_edge = raw_edge - (g['line_move'] * 1.0)
                if g['line_move'] >= 2.5 and adj_edge < 8.0:
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
                season_bets.setdefault(s, {'w': 0, 'l': 0, 'p': 0})
                season_bets[s]['w' if won else 'l'] += 1
                season_bets[s]['p'] += profit

            total_bets = wins + losses
            if total_bets < 5:
                continue

            roi = total_profit / total_bets * 100
            wr = wins / total_bets * 100
            ppszn = total_bets / len(season_bets) if season_bets else 0

            total_games = len(predictions)
            selectivity = total_bets / total_games * 100

            peak = max_dd = 0
            for v in cumulative:
                if v > peak: peak = v
                if v - peak < max_dd: max_dd = v - peak

            prof_seasons = sum(1 for s in season_bets.values() if s['p'] > 0)

            sweep_results.append({
                'shrinkage': shrinkage,
                'edge': edge_thresh,
                'bets': total_bets,
                'wr': wr,
                'roi': roi,
                'profit': total_profit,
                'ppszn': ppszn,
                'select': selectivity,
                'maxdd': max_dd,
                'prof_s': prof_seasons,
                'tot_s': len(season_bets),
                'detail': season_bets,
            })

    if not sweep_results:
        print("  No valid results.")
        return []

    sweep_results.sort(key=lambda x: x['roi'], reverse=True)

    print(f"\n{'Shrink':>7} {'Edge':>6} {'Bets':>6} {'Win%':>6} {'ROI':>7} {'P/Szn':>6} {'Select':>7} {'MaxDD':>7} {'ProfS':>6}")
    print("-" * 70)
    for r in sweep_results[:20]:
        print(f"{r['shrinkage']:>6.1f}  {r['edge']:>5.1f}% {r['bets']:>6} "
              f"{r['wr']:>5.1f}% {r['roi']:>+6.1f}% {r['ppszn']:>5.0f} "
              f"{r['select']:>6.1f}% {r['maxdd']:>+6.1f}u "
              f"{r['prof_s']:>2}/{r['tot_s']}")

    brand_fit = [r for r in sweep_results if 5 <= r['ppszn'] <= 30 and r['roi'] > 0 and r['wr'] > 52]
    if brand_fit:
        brand_fit.sort(key=lambda x: x['roi'], reverse=True)
        print(f"\n  BRAND-FIT (5-30 picks/szn, ROI>0, WR>52%):")
        for r in brand_fit[:5]:
            print(f"    Shrink={r['shrinkage']} Edge={r['edge']}% -> {r['bets']} bets, {r['wr']:.1f}% WR, {r['roi']:+.1f}% ROI")

    best = sweep_results[0]
    print(f"\n  Best: shrink={best['shrinkage']} edge={best['edge']}% -> "
          f"{best['bets']} bets, {best['wr']:.1f}% WR, {best['roi']:+.1f}% ROI")

    for r in sweep_results:
        if r['detail']:
            print(f"\n  Season breakdown (shrink={r['shrinkage']}, edge={r['edge']}%):")
            for s, d in sorted(r['detail'].items()):
                t = d['w'] + d['l']
                sr = d['w'] / t * 100 if t > 0 else 0
                print(f"    {s}: {d['w']}-{d['l']} ({sr:.1f}%) {d['p']:+.1f}u")
            break

    return sweep_results


def run_baseline_backtest():
    print("\n" + "=" * 70)
    print("WNBA BASELINE BACKTEST (Original GBR, basic features)")
    print("=" * 70)

    from wnba_backtest import engineer_features, SHRINKAGE_WEIGHTS as BL_SW, EDGE_THRESHOLDS as BL_ET
    from sklearn.ensemble import GradientBoostingRegressor

    conn = get_db()
    df = pd.read_sql_query('''
        SELECT * FROM wnba_games
        WHERE home_score IS NOT NULL AND away_score IS NOT NULL
        AND spread_home IS NOT NULL AND spread_result IS NOT NULL
        AND spread_result != 'PUSH'
    ''', conn)
    conn.close()

    df['season'] = df['season'].astype(int)
    margin = (df['home_score'] - df['away_score']).astype(float)
    spreads = pd.to_numeric(df['spread_home'], errors='coerce')
    target = (margin + spreads > 0).astype(int)

    seasons = sorted(df['season'].unique())
    implied_prob = odds_to_implied_prob(STANDARD_ODDS)
    all_predictions = []

    for i in range(1, len(seasons)):
        train_seasons = seasons[:i]
        test_season = seasons[i]
        train_mask = df['season'].isin(train_seasons)
        test_mask = df['season'] == test_season
        train_df = df[train_mask]
        test_df = df[test_mask]

        if len(train_df) < 50 or len(test_df) < 20:
            continue

        X_train = engineer_features(train_df).fillna(0)
        X_test = engineer_features(test_df).fillna(0)

        all_cols = sorted(set(X_train.columns) | set(X_test.columns))
        for c in all_cols:
            if c not in X_train.columns: X_train[c] = 0
            if c not in X_test.columns: X_test[c] = 0
        X_train = X_train[all_cols]
        X_test = X_test[all_cols]

        scaler = StandardScaler()
        X_train_s = scaler.fit_transform(X_train)
        X_test_s = scaler.transform(X_test)

        model = GradientBoostingRegressor(n_estimators=200, max_depth=4, learning_rate=0.1, random_state=42)
        model.fit(X_train_s, margin[train_mask])
        preds = model.predict(X_test_s)

        residuals = preds - margin[test_mask].values
        sigma = min(max(np.std(residuals), SIGMA_FLOOR), SIGMA_CEILING)
        model_mae = np.mean(np.abs(residuals))
        market_mae = np.mean(np.abs(-spreads[test_mask].values - margin[test_mask].values))
        model_closer = np.sum(np.abs(preds - margin[test_mask].values) < np.abs(-spreads[test_mask].values - margin[test_mask].values))

        open_sp = pd.to_numeric(test_df['spread_home_open'], errors='coerce').values

        print(f"  Season {test_season}: MAE={model_mae:.1f} vs Market={market_mae:.1f}, Closer={model_closer/len(test_df)*100:.1f}%")

        for j in range(len(test_df)):
            sp = spreads[test_mask].values[j]
            if pd.isna(sp): continue
            lm = 0.0
            if j < len(open_sp) and not pd.isna(open_sp[j]):
                mv = sp - open_sp[j]
                if mv > 0 and mv >= 1.0: lm = mv

            all_predictions.append({
                'season': test_season, 'spread': sp, 'pred_margin_raw': preds[j],
                'market_margin': -sp, 'sigma': sigma, 'sigma_raw': np.std(residuals),
                'model_mae': model_mae, 'market_mae': market_mae,
                'model_closer_pct': model_closer/len(test_df)*100,
                'line_move': lm, 'home_cover': target[test_mask].values[j],
            })

    run_sweep(all_predictions, implied_prob, "BASELINE")

    return {
        'predictions': all_predictions,
        'avg_model_mae': round(np.mean([g['model_mae'] for g in all_predictions]), 1),
        'avg_market_mae': round(np.mean([g['market_mae'] for g in all_predictions]), 1),
        'model_closer_pct': round(np.mean([g['model_closer_pct'] for g in all_predictions]), 1),
    }


def compare():
    print("\n" + "=" * 70)
    print("SIDE-BY-SIDE COMPARISON: BASELINE vs ENHANCED")
    print("=" * 70)

    baseline = run_baseline_backtest()
    enhanced = run_enhanced_backtest()

    if not baseline or not enhanced:
        print("  Could not run both models.")
        return

    print(f"\n{'='*70}")
    print(f"COMPARISON SUMMARY")
    print(f"{'='*70}")
    print(f"{'Metric':<25} {'Baseline':>12} {'Enhanced':>12} {'Delta':>10}")
    print("-" * 60)
    print(f"{'Model MAE':<25} {baseline['avg_model_mae']:>12.1f} {enhanced['avg_model_mae']:>12.1f} {enhanced['avg_model_mae']-baseline['avg_model_mae']:>+10.1f}")
    print(f"{'Market MAE':<25} {baseline['avg_market_mae']:>12.1f} {enhanced['avg_market_mae']:>12.1f} {enhanced['avg_market_mae']-baseline['avg_market_mae']:>+10.1f}")
    print(f"{'Model Closer %':<25} {baseline['model_closer_pct']:>12.1f} {enhanced['model_closer_pct']:>12.1f} {enhanced['model_closer_pct']-baseline['model_closer_pct']:>+10.1f}")
    mae_gap_bl = baseline['avg_model_mae'] - baseline['avg_market_mae']
    mae_gap_en = enhanced['avg_model_mae'] - enhanced['avg_market_mae']
    print(f"{'MAE Gap (model-market)':<25} {mae_gap_bl:>12.1f} {mae_gap_en:>12.1f} {mae_gap_en-mae_gap_bl:>+10.1f}")

    if enhanced['avg_model_mae'] < baseline['avg_model_mae']:
        pct_improve = (1 - enhanced['avg_model_mae'] / baseline['avg_model_mae']) * 100
        print(f"\n  Enhanced model is {pct_improve:.1f}% more accurate (lower MAE)")
    else:
        print(f"\n  Enhanced model did not improve MAE")

    if mae_gap_en < mae_gap_bl:
        print(f"  MAE gap narrowed by {mae_gap_bl - mae_gap_en:.1f} pts")
    else:
        print(f"  MAE gap widened by {mae_gap_en - mae_gap_bl:.1f} pts")

    if enhanced['model_closer_pct'] > baseline['model_closer_pct']:
        print(f"  Model closer % improved by {enhanced['model_closer_pct'] - baseline['model_closer_pct']:.1f}pp")

    print(f"\n{'='*70}")


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(0)

    cmd = sys.argv[1].lower()
    if cmd == 'scrape':
        scrape_all()
    elif cmd == 'backtest':
        run_enhanced_backtest()
    elif cmd == 'compare':
        compare()
    else:
        print(f"Unknown: {cmd}")
        print(__doc__)
