"""
WNBA Historical Data Pipeline
Backfills historical odds from The Odds API and enriches game data.
Usage:
    python wnba_data_pipeline.py --backfill-odds        Backfill historical odds (uses API quota)
    python wnba_data_pipeline.py --backfill-scores       Backfill scores from ESPN (free)
    python wnba_data_pipeline.py --enrich                Add rest days, form, schedule features
    python wnba_data_pipeline.py --report                Show data completeness report
    python wnba_data_pipeline.py --quota                 Check API quota remaining
"""

import sqlite3
import requests
import os
import sys
import time
from datetime import datetime, timedelta

ODDS_API_KEY = os.environ.get('ODDS_API_KEY', '')
DB_PATH = 'sharp_picks.db'

WNBA_SEASONS = {
    2022: ('2022-05-06', '2022-09-18'),
    2023: ('2023-05-19', '2023-10-18'),
    2024: ('2024-05-14', '2024-10-20'),
    2025: ('2025-05-16', '2025-09-14'),
}

SPORTSBOOKS = ['draftkings', 'fanduel', 'betmgm', 'caesars', 'pointsbetus', 'betrivers']


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def check_quota():
    resp = requests.get(
        'https://api.the-odds-api.com/v4/sports/',
        params={'apiKey': ODDS_API_KEY}
    )
    used = resp.headers.get('x-requests-used', '?')
    remaining = resp.headers.get('x-requests-remaining', '?')
    print(f"API Quota — Used: {used}, Remaining: {remaining}")
    return int(remaining) if remaining != '?' else 0


def setup_tables(cursor):
    cursor.execute('''CREATE TABLE IF NOT EXISTS wnba_games (
        id TEXT PRIMARY KEY,
        game_date TEXT,
        game_time TEXT,
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
        moneyline_home_open INTEGER,
        moneyline_away_open INTEGER,
        line_movement REAL,
        home_rest_days INTEGER,
        away_rest_days INTEGER,
        home_last5 TEXT,
        away_last5 TEXT,
        home_record TEXT,
        away_record TEXT,
        home_home_record TEXT,
        away_away_record TEXT,
        home_spread_odds INTEGER,
        away_spread_odds INTEGER,
        home_spread_book TEXT,
        away_spread_book TEXT,
        num_books INTEGER DEFAULT 0,
        spread_consensus REAL,
        spread_dispersion REAL,
        season INTEGER,
        collected_at TEXT,
        scores_updated_at TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )''')

    for col_name, col_type in [
        ('total_close', 'REAL'),
        ('moneyline_home_open', 'INTEGER'),
        ('moneyline_away_open', 'INTEGER'),
        ('spread_dispersion', 'REAL'),
        ('spread_consensus', 'REAL'),
        ('num_books', 'INTEGER DEFAULT 0'),
        ('home_spread_odds', 'INTEGER'),
        ('away_spread_odds', 'INTEGER'),
        ('home_spread_book', 'TEXT'),
        ('away_spread_book', 'TEXT'),
        ('season', 'INTEGER'),
    ]:
        try:
            cursor.execute(f'ALTER TABLE wnba_games ADD COLUMN {col_name} {col_type}')
        except:
            pass
    cursor.connection.commit()


def backfill_scores():
    """Backfill WNBA scores from ESPN for all seasons"""
    conn = get_db()
    cursor = conn.cursor()
    setup_tables(cursor)

    total_added = 0

    for year, (start, end) in WNBA_SEASONS.items():
        if year > 2025:
            continue
        print(f"\n{'='*50}")
        print(f"  WNBA {year} Season: {start} to {end}")
        print(f"{'='*50}")

        current = datetime.strptime(start, '%Y-%m-%d')
        end_dt = min(datetime.strptime(end, '%Y-%m-%d'), datetime.now())
        season_added = 0

        while current <= end_dt:
            date_str = current.strftime('%Y%m%d')
            display_date = current.strftime('%Y-%m-%d')

            url = f"https://site.api.espn.com/apis/site/v2/sports/basketball/wnba/scoreboard?dates={date_str}"
            try:
                resp = requests.get(url, timeout=10)
                if resp.status_code == 200:
                    data = resp.json()
                    events = data.get('events', [])
                    if events:
                        for event in events:
                            comps = event.get('competitions', [{}])
                            comp = comps[0] if comps else {}
                            competitors = comp.get('competitors', [])
                            if len(competitors) < 2:
                                continue

                            home = next((c for c in competitors if c.get('homeAway') == 'home'), competitors[0])
                            away = next((c for c in competitors if c.get('homeAway') == 'away'), competitors[1])

                            home_team = home.get('team', {}).get('displayName', '')
                            away_team = away.get('team', {}).get('displayName', '')
                            home_score = int(home.get('score', 0)) if home.get('score') else None
                            away_score = int(away.get('score', 0)) if away.get('score') else None

                            game_id = event.get('id', f"wnba_{display_date}_{away_team}_{home_team}")
                            game_time = event.get('date', '')

                            status = comp.get('status', {}).get('type', {}).get('name', '')
                            if status != 'STATUS_FINAL' and home_score is not None:
                                continue

                            cursor.execute('SELECT id FROM wnba_games WHERE id = ?', (game_id,))
                            if cursor.fetchone():
                                if home_score is not None:
                                    cursor.execute('''UPDATE wnba_games SET
                                        home_score = COALESCE(?, home_score),
                                        away_score = COALESCE(?, away_score)
                                        WHERE id = ?''',
                                        (home_score, away_score, game_id))
                            else:
                                cursor.execute('''INSERT OR IGNORE INTO wnba_games
                                    (id, game_date, game_time, home_team, away_team, home_score, away_score)
                                    VALUES (?, ?, ?, ?, ?, ?, ?)''',
                                    (game_id, display_date, game_time, home_team, away_team, home_score, away_score))
                                season_added += 1

                        conn.commit()
            except Exception as e:
                print(f"  Error on {display_date}: {e}")

            current += timedelta(days=1)
            time.sleep(0.2)

        total_added += season_added
        print(f"  Added {season_added} new games for {year}")

    cursor.execute('SELECT COUNT(*) FROM wnba_games')
    total = cursor.fetchone()[0]
    cursor.execute('SELECT COUNT(*) FROM wnba_games WHERE home_score IS NOT NULL')
    scored = cursor.fetchone()[0]
    print(f"\nTotal WNBA games in DB: {total} ({scored} with scores)")
    conn.close()
    return total_added


def backfill_odds(max_requests=100, year=None):
    """Backfill historical odds from The Odds API for games missing spread data"""
    if not ODDS_API_KEY:
        print("ERROR: ODDS_API_KEY environment variable not set")
        return 0

    conn = get_db()
    cursor = conn.cursor()
    setup_tables(cursor)

    remaining = check_quota()
    if remaining <= 0:
        print("ERROR: No API quota remaining")
        conn.close()
        return 0

    cost_per_call = 10
    max_calls = min(max_requests, remaining // cost_per_call)
    print(f"Budget: {max_calls} API calls (~{max_calls * cost_per_call} quota)")

    if year:
        cursor.execute('''SELECT DISTINCT game_date FROM wnba_games
            WHERE spread_home IS NULL AND game_date LIKE ?
            ORDER BY game_date''', (f'{year}%',))
    else:
        cursor.execute('''SELECT DISTINCT game_date FROM wnba_games
            WHERE spread_home IS NULL
            ORDER BY game_date''')
    dates_needing_odds = [row[0] for row in cursor.fetchall()]
    print(f"Game dates needing odds: {len(dates_needing_odds)}")

    if not dates_needing_odds:
        print("All games already have odds data!")
        conn.close()
        return 0

    calls_made = 0
    games_updated = 0
    unmatched_total = 0

    for game_date in dates_needing_odds:
        if calls_made >= max_calls:
            print(f"\nReached budget limit ({max_calls} calls)")
            break

        dt = datetime.strptime(game_date, '%Y-%m-%d')
        snapshot_time = dt.strftime('%Y-%m-%dT14:00:00Z')

        url = 'https://api.the-odds-api.com/v4/historical/sports/basketball_wnba/odds/'
        params = {
            'apiKey': ODDS_API_KEY,
            'regions': 'us',
            'markets': 'spreads,totals,h2h',
            'oddsFormat': 'american',
            'date': snapshot_time,
        }

        try:
            resp = requests.get(url, params=params, timeout=15)
            calls_made += 1

            if resp.status_code != 200:
                print(f"  {game_date}: API error {resp.status_code}")
                time.sleep(1)
                continue

            data = resp.json()
            api_games = data.get('data', [])

            remaining_now = resp.headers.get('x-requests-remaining', '?')
            print(f"  {game_date}: {len(api_games)} games (quota left: {remaining_now})")

            for api_game in api_games:
                home = api_game.get('home_team', '')
                away = api_game.get('away_team', '')
                commence = api_game.get('commence_time', '')

                api_date = commence[:10] if commence else game_date

                cursor.execute('''SELECT id FROM wnba_games
                    WHERE home_team = ? AND away_team = ?
                    AND game_date BETWEEN ? AND ?''',
                    (home, away,
                     (dt - timedelta(days=1)).strftime('%Y-%m-%d'),
                     (dt + timedelta(days=1)).strftime('%Y-%m-%d')))
                match = cursor.fetchone()
                if not match:
                    unmatched_total += 1
                    continue

                game_id = match[0]
                bookmakers = api_game.get('bookmakers', [])
                if not bookmakers:
                    continue

                spreads = {}
                totals = {}
                moneylines = {}
                spread_odds = {}

                for book in bookmakers:
                    book_key = book.get('key', '')
                    for market in book.get('markets', []):
                        mk = market.get('key', '')
                        outcomes = market.get('outcomes', [])
                        if mk == 'spreads':
                            for o in outcomes:
                                if o.get('name') == home:
                                    spreads[book_key] = o.get('point')
                                    spread_odds[book_key] = o.get('price')
                        elif mk == 'totals':
                            for o in outcomes:
                                if o.get('name') == 'Over':
                                    totals[book_key] = o.get('point')
                        elif mk == 'h2h':
                            for o in outcomes:
                                if o.get('name') == home:
                                    moneylines[f'{book_key}_home'] = o.get('price')
                                elif o.get('name') == away:
                                    moneylines[f'{book_key}_away'] = o.get('price')

                if not spreads:
                    continue

                consensus_spread = sum(spreads.values()) / len(spreads)
                if len(spreads) > 1:
                    dispersion = max(spreads.values()) - min(spreads.values())
                else:
                    dispersion = 0

                best_home = max(spreads.values())
                best_away = -min(spreads.values())
                best_home_book = max(spreads, key=spreads.get)
                best_away_book = min(spreads, key=spreads.get)

                primary_book = next((b for b in ['draftkings', 'fanduel', 'betmgm'] if b in spreads), list(spreads.keys())[0])
                primary_spread = spreads[primary_book]
                primary_total = totals.get(primary_book) or (sum(totals.values()) / len(totals) if totals else None)

                ml_home = moneylines.get(f'{primary_book}_home')
                ml_away = moneylines.get(f'{primary_book}_away')

                cursor.execute('''UPDATE wnba_games SET
                    spread_home = ?,
                    spread_away = ?,
                    spread_home_open = COALESCE(spread_home_open, ?),
                    total = ?,
                    total_open = COALESCE(total_open, ?),
                    home_ml = ?,
                    away_ml = ?,
                    moneyline_home_open = COALESCE(moneyline_home_open, ?),
                    moneyline_away_open = COALESCE(moneyline_away_open, ?),
                    num_books = ?,
                    spread_consensus = ?,
                    spread_dispersion = ?,
                    home_spread_odds = ?,
                    away_spread_odds = ?,
                    home_spread_book = ?,
                    away_spread_book = ?
                    WHERE id = ?''', (
                    primary_spread, -primary_spread, primary_spread,
                    primary_total, primary_total,
                    ml_home, ml_away, ml_home, ml_away,
                    len(bookmakers),
                    round(consensus_spread, 1), round(dispersion, 1),
                    best_home, best_away, best_home_book, best_away_book,
                    game_id
                ))
                games_updated += 1

            conn.commit()
            time.sleep(0.5)

        except Exception as e:
            print(f"  {game_date}: Error - {e}")
            time.sleep(1)

    print(f"\nBackfill complete: {games_updated} games updated, {calls_made} API calls used, {unmatched_total} odds unmatched")
    conn.close()
    return games_updated


def enrich_schedule_features():
    """Add rest days, home/away records, and form data to existing games"""
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute('''SELECT id, game_date, home_team, away_team
        FROM wnba_games
        WHERE home_score IS NOT NULL
        ORDER BY game_date''')
    games = cursor.fetchall()
    print(f"Enriching schedule features for {len(games)} games...")

    team_last_game = {}
    team_form = {}
    updated = 0

    for game in games:
        game_id, game_date, home_team, away_team = game
        game_dt = datetime.strptime(game_date, '%Y-%m-%d')

        home_rest = None
        away_rest = None

        if home_team in team_last_game:
            delta = (game_dt - team_last_game[home_team]).days
            home_rest = delta
        if away_team in team_last_game:
            delta = (game_dt - team_last_game[away_team]).days
            away_rest = delta

        cursor.execute('''SELECT home_team, away_team, home_score, away_score
            FROM wnba_games
            WHERE (home_team = ? OR away_team = ?) AND game_date < ? AND home_score IS NOT NULL
            ORDER BY game_date DESC LIMIT 5''', (home_team, home_team, game_date))
        home_recent = cursor.fetchall()
        home_wins = sum(1 for g in home_recent if
            (g[0] == home_team and g[2] > g[3]) or
            (g[1] == home_team and g[3] > g[2]))
        home_last5 = f"{home_wins}-{len(home_recent)-home_wins}" if home_recent else None

        cursor.execute('''SELECT home_team, away_team, home_score, away_score
            FROM wnba_games
            WHERE (home_team = ? OR away_team = ?) AND game_date < ? AND home_score IS NOT NULL
            ORDER BY game_date DESC LIMIT 5''', (away_team, away_team, game_date))
        away_recent = cursor.fetchall()
        away_wins = sum(1 for g in away_recent if
            (g[0] == away_team and g[2] > g[3]) or
            (g[1] == away_team and g[3] > g[2]))
        away_last5 = f"{away_wins}-{len(away_recent)-away_wins}" if away_recent else None

        cursor.execute('''UPDATE wnba_games SET
            home_rest_days = ?,
            away_rest_days = ?,
            home_last5 = ?,
            away_last5 = ?
            WHERE id = ?''', (home_rest, away_rest, home_last5, away_last5, game_id))

        team_last_game[home_team] = game_dt
        team_last_game[away_team] = game_dt
        updated += 1

    conn.commit()
    print(f"Enriched {updated} games with rest days and form data")
    conn.close()
    return updated


def report():
    """Show data completeness report"""
    conn = get_db()
    cursor = conn.cursor()

    print("\n" + "="*60)
    print("  WNBA DATA COMPLETENESS REPORT")
    print("="*60)

    cursor.execute('SELECT COUNT(*) FROM wnba_games')
    total = cursor.fetchone()[0]

    cursor.execute('SELECT COUNT(*) FROM wnba_games WHERE home_score IS NOT NULL')
    scored = cursor.fetchone()[0]

    cursor.execute('SELECT COUNT(*) FROM wnba_games WHERE spread_home IS NOT NULL')
    spreads = cursor.fetchone()[0]

    cursor.execute('SELECT COUNT(*) FROM wnba_games WHERE spread_home_close IS NOT NULL')
    closing = cursor.fetchone()[0]

    cursor.execute('SELECT COUNT(*) FROM wnba_games WHERE total IS NOT NULL')
    totals = cursor.fetchone()[0]

    cursor.execute('SELECT COUNT(*) FROM wnba_games WHERE home_ml IS NOT NULL')
    ml = cursor.fetchone()[0]

    cursor.execute('SELECT COUNT(*) FROM wnba_games WHERE home_rest_days IS NOT NULL')
    rest = cursor.fetchone()[0]

    cursor.execute('SELECT COUNT(*) FROM wnba_games WHERE home_last5 IS NOT NULL')
    form = cursor.fetchone()[0]

    cursor.execute('SELECT COUNT(*) FROM wnba_games WHERE num_books >= 3')
    multi_book = cursor.fetchone()[0]

    print(f"\n  Total games:          {total}")
    print(f"  With scores:          {scored:>5} ({scored/total*100:.0f}%)" if total else "")
    print(f"  With spreads:         {spreads:>5} ({spreads/total*100:.0f}%)" if total else "")
    print(f"  With closing lines:   {closing:>5} ({closing/total*100:.0f}%)" if total else "")
    print(f"  With totals:          {totals:>5} ({totals/total*100:.0f}%)" if total else "")
    print(f"  With moneylines:      {ml:>5} ({ml/total*100:.0f}%)" if total else "")
    print(f"  With rest days:       {rest:>5} ({rest/total*100:.0f}%)" if total else "")
    print(f"  With form (L5):       {form:>5} ({form/total*100:.0f}%)" if total else "")
    print(f"  Multi-book (3+):      {multi_book:>5} ({multi_book/total*100:.0f}%)" if total else "")

    print(f"\n  {'Year':<8}{'Games':<8}{'Scores':<8}{'Spreads':<8}{'CLV':<8}{'Totals':<8}")
    print(f"  {'-'*48}")
    cursor.execute('''SELECT
        SUBSTR(game_date,1,4) as yr,
        COUNT(*) as total,
        SUM(CASE WHEN home_score IS NOT NULL THEN 1 ELSE 0 END) as scored,
        SUM(CASE WHEN spread_home IS NOT NULL THEN 1 ELSE 0 END) as sp,
        SUM(CASE WHEN spread_home_close IS NOT NULL THEN 1 ELSE 0 END) as cl,
        SUM(CASE WHEN total IS NOT NULL THEN 1 ELSE 0 END) as tot
        FROM wnba_games GROUP BY yr ORDER BY yr''')
    for row in cursor.fetchall():
        print(f"  {row[0]:<8}{row[1]:<8}{row[2]:<8}{row[3]:<8}{row[4]:<8}{row[5]:<8}")

    print(f"\n  Ready for modeling: {spreads} games with spread + score data")
    if spreads >= 200:
        print(f"  Status: SUFFICIENT for walk-forward backtesting")
    elif spreads >= 100:
        print(f"  Status: MARGINAL — backfill more odds data")
    else:
        print(f"  Status: INSUFFICIENT — need more odds backfill")

    print("="*60)
    conn.close()


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(0)

    cmd = sys.argv[1]

    if cmd == '--backfill-scores':
        backfill_scores()
    elif cmd == '--backfill-odds':
        max_req = int(sys.argv[2]) if len(sys.argv) > 2 else 100
        year = sys.argv[3] if len(sys.argv) > 3 else None
        backfill_odds(max_requests=max_req, year=year)
    elif cmd == '--enrich':
        enrich_schedule_features()
    elif cmd == '--report':
        report()
    elif cmd == '--quota':
        check_quota()
    else:
        print(f"Unknown command: {cmd}")
        print(__doc__)
