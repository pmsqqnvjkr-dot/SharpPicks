"""
MLB Model Validation — Full Pipeline
Run on Railway where RAPIDAPI_KEY is available for real historical odds.

Usage:
  python3 validate_mlb.py                    # Full: backfill + walk-forward + calibration
  python3 validate_mlb.py --skip-backfill    # Skip backfill, run validation on existing data
  python3 validate_mlb.py --backfill-only    # Only run backfill (no validation)
  python3 validate_mlb.py --season 2023      # Backfill single season
"""

import sys
import os
import sqlite3
import time
import json
from datetime import datetime

from db_path import get_sqlite_path


def data_summary():
    """Print current MLB data in the database."""
    conn = sqlite3.connect(get_sqlite_path())
    c = conn.cursor()

    c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='mlb_games'")
    if not c.fetchone():
        print("  mlb_games table does not exist")
        conn.close()
        return 0

    c.execute('SELECT COUNT(*) FROM mlb_games')
    total = c.fetchone()[0]

    c.execute('SELECT COUNT(*) FROM mlb_games WHERE home_score IS NOT NULL')
    graded = c.fetchone()[0]

    c.execute('SELECT COUNT(*) FROM mlb_games WHERE spread_home IS NOT NULL AND spread_home != 0')
    with_real_odds = c.fetchone()[0]

    c.execute('SELECT COUNT(*) FROM mlb_games WHERE home_pitcher_era IS NOT NULL')
    with_era = c.fetchone()[0]

    c.execute('SELECT COUNT(*) FROM mlb_games WHERE spread_result IS NOT NULL')
    with_result = c.fetchone()[0]

    c.execute('SELECT COUNT(*) FROM mlb_games WHERE rundown_spread_consensus IS NOT NULL')
    with_rundown = c.fetchone()[0]

    c.execute("SELECT SUBSTR(game_date,1,4) as yr, COUNT(*) FROM mlb_games WHERE home_score IS NOT NULL GROUP BY yr ORDER BY yr")
    by_year = c.fetchall()

    c.execute('SELECT MIN(game_date), MAX(game_date) FROM mlb_games')
    dr = c.fetchone()

    print(f"  Total games: {total}")
    print(f"  Graded (with scores): {graded}")
    print(f"  With real odds (spread != 0): {with_real_odds}")
    print(f"  With Rundown consensus: {with_rundown}")
    print(f"  With pitcher ERA: {with_era}")
    print(f"  With spread result: {with_result}")
    print(f"  Date range: {dr[0]} to {dr[1]}")
    print(f"  By year: {by_year}")

    conn.close()
    return with_real_odds


def run_backfill(seasons=None):
    """Run the MLB backfill with Rundown API data."""
    from backfill_mlb import backfill, SEASON_DATES
    from main import setup_mlb_table

    api_key = os.environ.get('RAPIDAPI_KEY')
    use_rundown = bool(api_key)

    if not use_rundown:
        print("\n  WARNING: RAPIDAPI_KEY not set. Backfilling without Rundown odds.")
        print("  Walk-forward results will be limited without real market data.\n")

    if seasons is None:
        seasons = [2023, 2024, 2025]

    conn = sqlite3.connect(get_sqlite_path())
    cursor = conn.cursor()
    setup_mlb_table(cursor)
    conn.commit()
    conn.close()

    for season in sorted(seasons):
        if season not in SEASON_DATES:
            print(f"  Unknown season {season}, skipping")
            continue

        start, end = SEASON_DATES[season]
        print(f"\n{'='*50}")
        print(f"  BACKFILLING {season}: {start.strftime('%Y-%m-%d')} to {end.strftime('%Y-%m-%d')}")
        print(f"  Rundown API: {'ENABLED' if use_rundown else 'DISABLED'}")
        print(f"{'='*50}")
        backfill(start_date=start, end_date=end, use_rundown=use_rundown)


def compute_spread_results():
    """Compute spread_result for any games that have scores + spreads but no result."""
    conn = sqlite3.connect(get_sqlite_path())
    c = conn.cursor()

    c.execute('''
        UPDATE mlb_games SET spread_result = CASE
            WHEN (home_score - away_score) + spread_home > 0 THEN 'W'
            WHEN (home_score - away_score) + spread_home < 0 THEN 'L'
            ELSE 'PUSH' END
        WHERE home_score IS NOT NULL AND away_score IS NOT NULL
        AND spread_home IS NOT NULL
        AND (spread_result IS NULL OR spread_result = '')
    ''')
    updated = c.rowcount
    conn.commit()
    conn.close()

    if updated > 0:
        print(f"  Computed spread_result for {updated} games")


def run_validation():
    """Run walk-forward validation and calibration check."""
    from model import EnsemblePredictor
    import numpy as np

    predictor = EnsemblePredictor(sport='mlb')

    print("\n" + "=" * 70)
    print("  STEP 1: WALK-FORWARD VALIDATION")
    print("=" * 70)
    result = predictor.walk_forward_validate()

    if not result:
        print("  Walk-forward returned no results. Not enough data?")
        return None

    print("\n" + "=" * 70)
    print("  STEP 2: CALIBRATION CHECK")
    print("=" * 70)
    predictor.calibration_check(result['all_bets'])

    print("\n" + "=" * 70)
    print("  STEP 3: FEATURE IMPORTANCE ANALYSIS")
    print("=" * 70)
    print("  Training full model for feature analysis...")
    predictor.train(use_sample_weights=True)

    if 'gradient_boosting' in predictor.models:
        cal_model = predictor.models['gradient_boosting']
        if hasattr(cal_model, 'calibrated_classifiers_'):
            base = cal_model.calibrated_classifiers_[0].estimator
            if hasattr(base, 'feature_importances_'):
                importances = base.feature_importances_
                features = predictor.feature_names
                sorted_idx = np.argsort(importances)[::-1]

                print(f"\n  TOP 20 FEATURES:")
                print("  " + "-" * 50)
                for i in range(min(20, len(sorted_idx))):
                    idx = sorted_idx[i]
                    bar = "█" * int(importances[idx] * 200)
                    print(f"  {i+1:2d}. {features[idx]:<30} {importances[idx]:.4f} {bar}")

                active = sum(1 for imp in importances if imp > 0.001)
                print(f"\n  Active features (importance > 0.001): {active}/{len(features)}")

    print("\n" + "=" * 70)
    print("  STEP 4: MARGIN MODEL R² (5-fold CV)")
    print("=" * 70)
    from sklearn.ensemble import GradientBoostingRegressor
    from sklearn.preprocessing import StandardScaler
    from sklearn.model_selection import cross_val_score
    import pandas as pd

    df = predictor.load_data()
    df = df[df['spread_result'] != 'PUSH'].copy()
    X = predictor.engineer_features(df).fillna(0)
    y = (df['home_score'] - df['away_score']).astype(float)

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    margin_gbr = GradientBoostingRegressor(
        n_estimators=200, max_depth=4, learning_rate=0.1, random_state=42
    )
    scores = cross_val_score(margin_gbr, X_scaled, y, cv=5, scoring='r2')
    print(f"  R² scores: {[f'{s:.3f}' for s in scores]}")
    print(f"  Mean R²:   {scores.mean():.3f} ± {scores.std():.3f}")

    mae_scores = cross_val_score(
        margin_gbr, X_scaled, y, cv=5, scoring='neg_mean_absolute_error'
    )
    print(f"  MAE:       {-mae_scores.mean():.2f} ± {mae_scores.std():.2f} runs")

    summary = {
        'timestamp': datetime.now().isoformat(),
        'total_games': len(df),
        'seasons': len(result['seasons']),
        'walk_forward': result['seasons'],
        'total_bets': sum(r['n_bets'] for r in result['seasons']),
        'overall_win_rate': (
            sum(r['wins'] for r in result['seasons']) /
            max(sum(r['n_bets'] for r in result['seasons']), 1) * 100
        ),
        'overall_roi': (
            sum(r['total_profit'] for r in result['seasons']) /
            max(sum(r['n_bets'] for r in result['seasons']), 1) * 100
        ),
        'margin_r2': float(scores.mean()),
        'margin_mae': float(-mae_scores.mean()),
        'has_real_odds': any(
            r.get('sigma_raw', 0) != r.get('sigma', 0) for r in result['seasons']
        ),
    }

    return summary


def main():
    args = sys.argv[1:]
    skip_backfill = '--skip-backfill' in args
    backfill_only = '--backfill-only' in args

    seasons_arg = []
    for i, arg in enumerate(args):
        if arg == '--season' and i + 1 < len(args):
            seasons_arg.append(int(args[i + 1]))

    print("=" * 70)
    print("  MLB MODEL VALIDATION PIPELINE")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  RAPIDAPI_KEY: {'SET' if os.environ.get('RAPIDAPI_KEY') else 'NOT SET'}")
    print("=" * 70)

    print("\n  CURRENT DATA:")
    has_odds = data_summary()

    if not skip_backfill:
        print("\n" + "=" * 70)
        print("  BACKFILLING HISTORICAL DATA")
        print("=" * 70)
        t0 = time.time()
        run_backfill(seasons=seasons_arg if seasons_arg else None)
        elapsed = time.time() - t0
        print(f"\n  Backfill completed in {elapsed:.0f}s")

        compute_spread_results()

        print("\n  POST-BACKFILL DATA:")
        has_odds = data_summary()

    if backfill_only:
        print("\n  --backfill-only: skipping validation")
        return

    if not skip_backfill:
        compute_spread_results()

    print("\n" + "=" * 70)
    print("  RUNNING VALIDATION")
    print("=" * 70)

    t0 = time.time()
    summary = run_validation()
    elapsed = time.time() - t0

    if summary:
        print("\n" + "=" * 70)
        print("  VALIDATION SUMMARY")
        print("=" * 70)
        print(f"  Games:     {summary['total_games']}")
        print(f"  Seasons:   {summary['seasons']}")
        print(f"  Bets:      {summary['total_bets']}")
        print(f"  Win Rate:  {summary['overall_win_rate']:.1f}%")
        print(f"  ROI:       {summary['overall_roi']:+.1f}%")
        print(f"  Margin R²: {summary['margin_r2']:.3f}")
        print(f"  Margin MAE:{summary['margin_mae']:.2f} runs")
        print(f"  Runtime:   {elapsed:.0f}s")

        roi = summary['overall_roi']
        if roi > 14:
            print(f"\n  ⚠️  ROI {roi:+.1f}% is suspiciously high. Check for data leakage.")
            if not summary.get('has_real_odds'):
                print("  NOTE: No real odds data — ROI is inflated against fake baseline.")
        elif roi > 8:
            print(f"\n  Strong: ROI {roi:+.1f}%. Monitor for regression in live trading.")
        elif roi > 2:
            print(f"\n  Viable: ROI {roi:+.1f}%. Edge exists but margins are thin.")
        elif roi > 0:
            print(f"\n  Marginal: ROI {roi:+.1f}%. Edge may not survive vig + variance.")
        else:
            print(f"\n  Negative: ROI {roi:+.1f}%. Model is not finding real edge.")

        print("=" * 70)


if __name__ == '__main__':
    main()
