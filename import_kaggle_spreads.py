"""
Import Kaggle NBA Historical Spread Data
"""

import pandas as pd
import sqlite3
from datetime import datetime

DATA_PATH = "/home/runner/.cache/kagglehub/datasets/ehallmar/nba-historical-stats-and-betting-data/versions/1"

TEAM_ID_MAP = {
    1610612737: 'Atlanta Hawks',
    1610612738: 'Boston Celtics',
    1610612739: 'Cleveland Cavaliers',
    1610612740: 'New Orleans Pelicans',
    1610612741: 'Chicago Bulls',
    1610612742: 'Dallas Mavericks',
    1610612743: 'Denver Nuggets',
    1610612744: 'Golden State Warriors',
    1610612745: 'Houston Rockets',
    1610612746: 'Los Angeles Clippers',
    1610612747: 'Los Angeles Lakers',
    1610612748: 'Miami Heat',
    1610612749: 'Milwaukee Bucks',
    1610612750: 'Minnesota Timberwolves',
    1610612751: 'Brooklyn Nets',
    1610612752: 'New York Knicks',
    1610612753: 'Orlando Magic',
    1610612754: 'Indiana Pacers',
    1610612755: 'Philadelphia 76ers',
    1610612756: 'Phoenix Suns',
    1610612757: 'Portland Trail Blazers',
    1610612758: 'Sacramento Kings',
    1610612759: 'San Antonio Spurs',
    1610612760: 'Oklahoma City Thunder',
    1610612761: 'Toronto Raptors',
    1610612762: 'Utah Jazz',
    1610612763: 'Memphis Grizzlies',
    1610612764: 'Washington Wizards',
    1610612765: 'Detroit Pistons',
    1610612766: 'Charlotte Hornets',
}


def load_and_process_data():
    """Load and merge games with spread data"""
    print("📂 Loading datasets...")
    
    games_df = pd.read_csv(f"{DATA_PATH}/nba_games_all.csv")
    spreads_df = pd.read_csv(f"{DATA_PATH}/nba_betting_spread.csv")
    
    print(f"   Games: {len(games_df)} records")
    print(f"   Spreads: {len(spreads_df)} records")
    
    home_games = games_df[games_df['is_home'] == 't'].copy()
    away_games = games_df[games_df['is_home'] == 'f'].copy()
    
    home_games = home_games.rename(columns={
        'team_id': 'home_team_id',
        'pts': 'home_score',
        'w': 'home_wins',
        'l': 'home_losses',
        'wl': 'home_wl'
    })
    
    away_games = away_games.rename(columns={
        'team_id': 'away_team_id', 
        'pts': 'away_score',
        'w': 'away_wins',
        'l': 'away_losses',
        'wl': 'away_wl'
    })
    
    merged = home_games.merge(
        away_games[['game_id', 'away_team_id', 'away_score', 'away_wins', 'away_losses']],
        on='game_id',
        how='inner'
    )
    
    print(f"   Merged games: {len(merged)}")
    
    spreads_agg = spreads_df.groupby('game_id').agg({
        'spread1': 'mean',
        'spread2': 'mean',
        'team_id': 'first',
        'a_team_id': 'first'
    }).reset_index()
    
    spreads_agg = spreads_agg.rename(columns={
        'spread1': 'spread_home',
        'spread2': 'spread_away'
    })
    
    final = merged.merge(spreads_agg, on='game_id', how='inner')
    
    print(f"   Games with spreads: {len(final)}")
    
    return final


def calculate_spread_results(df):
    """Calculate if home team covered the spread"""
    df = df.copy()
    
    df['margin'] = df['home_score'] - df['away_score']
    df['adjusted_margin'] = df['margin'] + df['spread_home']
    
    def get_result(adj_margin):
        if adj_margin > 0:
            return 'HOME_COVER'
        elif adj_margin < 0:
            return 'AWAY_COVER'
        else:
            return 'PUSH'
    
    df['spread_result'] = df['adjusted_margin'].apply(get_result)
    
    return df


def import_to_database(df, limit=None):
    """Import processed data to SQLite database"""
    print("\n📥 Importing to database...")
    
    if limit:
        df = df.tail(limit)
        print(f"   Limiting to most recent {limit} games")
    
    conn = sqlite3.connect('sharp_picks.db')
    cursor = conn.cursor()
    
    imported = 0
    skipped = 0
    
    for _, row in df.iterrows():
        try:
            game_id = f"kaggle_{row['game_id']}"
            game_date = row['game_date']
            
            home_team = TEAM_ID_MAP.get(row['home_team_id'], 'Unknown')
            away_team = TEAM_ID_MAP.get(row['away_team_id'], 'Unknown')
            
            if home_team == 'Unknown' or away_team == 'Unknown':
                skipped += 1
                continue
            
            cursor.execute('SELECT id FROM games WHERE id = ?', (game_id,))
            if cursor.fetchone():
                skipped += 1
                continue
            
            home_record = f"{int(row['home_wins'])}-{int(row['home_losses'])}"
            away_record = f"{int(row['away_wins'])}-{int(row['away_losses'])}"
            
            cursor.execute('''
                INSERT INTO games (
                    id, game_date, home_team, away_team,
                    spread_home, spread_away,
                    home_score, away_score, spread_result,
                    home_record, away_record,
                    collected_at, scores_updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                game_id, game_date, home_team, away_team,
                row['spread_home'], row['spread_away'],
                int(row['home_score']), int(row['away_score']), row['spread_result'],
                home_record, away_record,
                datetime.now().isoformat(), datetime.now().isoformat()
            ))
            
            imported += 1
            
            if imported % 500 == 0:
                print(f"   Imported {imported} games...")
                conn.commit()
                
        except Exception as e:
            skipped += 1
            continue
    
    conn.commit()
    conn.close()
    
    print(f"\n✅ Import complete!")
    print(f"   Imported: {imported} games")
    print(f"   Skipped: {skipped} games")
    
    return imported


def show_stats():
    """Show database statistics after import"""
    conn = sqlite3.connect('sharp_picks.db')
    cursor = conn.cursor()
    
    cursor.execute('SELECT COUNT(*) FROM games')
    total = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM games WHERE spread_result IS NOT NULL')
    with_result = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM games WHERE spread_home IS NOT NULL')
    with_spread = cursor.fetchone()[0]
    
    cursor.execute('''
        SELECT spread_result, COUNT(*) 
        FROM games 
        WHERE spread_result IS NOT NULL 
        GROUP BY spread_result
    ''')
    results = cursor.fetchall()
    
    print("\n" + "="*50)
    print("📊 DATABASE STATISTICS")
    print("="*50)
    print(f"Total games:        {total}")
    print(f"Games with spreads: {with_spread}")
    print(f"Games with results: {with_result}")
    print()
    
    if results:
        print("Spread Results:")
        for result, count in results:
            pct = count / with_result * 100 if with_result > 0 else 0
            print(f"   {result}: {count} ({pct:.1f}%)")
    
    conn.close()


if __name__ == '__main__':
    import sys
    
    limit = None
    if len(sys.argv) > 1:
        try:
            limit = int(sys.argv[1])
        except:
            pass
    
    print("="*50)
    print("🏀 KAGGLE NBA SPREAD DATA IMPORTER")
    print("="*50 + "\n")
    
    df = load_and_process_data()
    
    df = calculate_spread_results(df)
    
    home_cover = (df['spread_result'] == 'HOME_COVER').sum()
    away_cover = (df['spread_result'] == 'AWAY_COVER').sum()
    push = (df['spread_result'] == 'PUSH').sum()
    
    print(f"\n📈 Spread Results Preview:")
    print(f"   HOME_COVER: {home_cover} ({home_cover/len(df)*100:.1f}%)")
    print(f"   AWAY_COVER: {away_cover} ({away_cover/len(df)*100:.1f}%)")
    print(f"   PUSH: {push} ({push/len(df)*100:.1f}%)")
    
    imported = import_to_database(df, limit=limit)
    
    show_stats()
    
    if imported > 50:
        print("\n💡 Now run: python model.py train")
        print("   to retrain with historical spread data!")
