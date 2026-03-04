"""
🏀 SHARP PICKS - ENSEMBLE PREDICTION MODEL
Uses multiple ML models to predict NBA spread outcomes
Enhanced with pace/ratings features, sample weighting, and betting filters
"""

import sqlite3
import pandas as pd
from db_path import get_sqlite_path
import numpy as np
from datetime import datetime, timedelta, timezone
import pickle
import os

from scipy.stats import norm
from sport_config import get_sport_config
from sklearn.ensemble import GradientBoostingClassifier, GradientBoostingRegressor, RandomForestClassifier, AdaBoostClassifier
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.preprocessing import StandardScaler
from sklearn.calibration import CalibratedClassifierCV, calibration_curve
from sklearn.metrics import accuracy_score, classification_report, brier_score_loss
import xgboost as xgb

MIN_CONFIDENCE_THRESHOLD = 0.55
STRONG_CONFIDENCE_THRESHOLD = 0.60
EDGE_THRESHOLD_PCT = 3.5
STANDARD_ODDS = -110
MARGIN_STD_DEV = 12.0
MARGIN_STD_FLOOR = 8.0
MARGIN_STD_CEILING = 15.0
LINE_MOVE_PENALTY_PER_PT = 1.0
LINE_MOVE_HARD_STOP = 2.5
LINE_MOVE_HARD_STOP_MIN_EDGE = 8.0

SHARP_MOVE_STD_THRESHOLD = 0.8
PUBLIC_MOVE_STD_THRESHOLD = 0.3

SFS_MAGNITUDE_WEIGHT = 0.35
SFS_SPREAD_WEIGHT = 0.25
SFS_DISPERSION_WEIGHT = 0.40
SFS_MAX = 0.60
SFS_MIN = 0.0
MODEL_WEIGHT = 0.3
MAX_EDGE_PCT = 8.0

SPREAD_EDGE_BASE = 3.0
SPREAD_EDGE_ELASTICITY = 0.167
SPREAD_EDGE_MAX = 7.0

SPREAD_RISK_SCALE_BASE = 7.0
SPREAD_RISK_SCALE_RATE = 0.25
STAR_QUESTIONABLE_EDGE_PENALTY = 2.0
STAR_QUESTIONABLE_SPREAD_THRESHOLD = 10.0

LONG_REST_THRESHOLD = 5
LONG_REST_SPREAD_THRESHOLD = 8.0
LONG_REST_PENALTY_PER_DAY = 0.3

ASB_SPREAD_THRESHOLD = 8.0
ASB_PENALTY_PCT = 3.0

NBA_ALL_STAR_BREAK_WINDOWS = {
    2013: ('2013-02-15', '2013-02-19'),
    2014: ('2014-02-14', '2014-02-18'),
    2015: ('2015-02-13', '2015-02-18'),
    2016: ('2016-02-12', '2016-02-17'),
    2017: ('2017-02-17', '2017-02-22'),
    2018: ('2018-02-16', '2018-02-21'),
    2019: ('2019-02-15', '2019-02-20'),
    2020: ('2020-02-14', '2020-02-19'),
    2021: ('2021-03-05', '2021-03-10'),
    2022: ('2022-02-18', '2022-02-23'),
    2023: ('2023-02-17', '2023-02-22'),
    2024: ('2024-02-16', '2024-02-21'),
    2025: ('2025-02-14', '2025-02-19'),
    2026: ('2026-02-13', '2026-02-18'),
}


def is_all_star_first_game(game_date):
    if game_date is None:
        return False
    if isinstance(game_date, str):
        try:
            game_date = pd.to_datetime(game_date)
        except Exception:
            return False
    gd = game_date.date() if hasattr(game_date, 'date') and callable(game_date.date) else game_date
    cal_year = gd.year
    if cal_year not in NBA_ALL_STAR_BREAK_WINDOWS:
        return False
    _, resume_date_str = NBA_ALL_STAR_BREAK_WINDOWS[cal_year]
    resume = pd.to_datetime(resume_date_str).date()
    from datetime import timedelta
    return resume <= gd <= resume + timedelta(days=1)


def get_edge_threshold_for_spread(spread_abs):
    threshold = SPREAD_EDGE_BASE + (spread_abs * SPREAD_EDGE_ELASTICITY)
    return min(threshold, SPREAD_EDGE_MAX)


def calculate_long_rest_penalty(pick_side, spread_abs, home_rest, away_rest):
    fav_rest = home_rest if pick_side == 'home' else away_rest
    if fav_rest is None or spread_abs < LONG_REST_SPREAD_THRESHOLD or fav_rest < LONG_REST_THRESHOLD:
        return 0.0, None

    excess_days = fav_rest - LONG_REST_THRESHOLD + 1
    penalty = excess_days * LONG_REST_PENALTY_PER_DAY
    reason = f"Long rest: {fav_rest}d rest on {spread_abs:.0f}pt fav (-{penalty:.1f}% edge)"
    return penalty, reason


def calculate_asb_penalty(spread_abs, game_date):
    if not is_all_star_first_game(game_date):
        return 0.0, None
    if spread_abs < ASB_SPREAD_THRESHOLD:
        return 0.0, None
    reason = f"All-Star break first game: {spread_abs:.0f}pt fav (-{ASB_PENALTY_PCT:.1f}% edge, 42.4% ATS historical)"
    return ASB_PENALTY_PCT, reason


def calculate_steam_fragility_score(line_move_magnitude, spread_abs, rundown_std, rundown_num_books):
    magnitude_score = min(line_move_magnitude / 4.0, 1.0)

    spread_score = min(max(spread_abs - 3.0, 0.0) / 12.0, 1.0)

    dispersion_score = 0.5
    if rundown_std is not None and rundown_num_books is not None and rundown_num_books >= 3:
        if rundown_std >= SHARP_MOVE_STD_THRESHOLD:
            dispersion_score = min(0.6 + (rundown_std - SHARP_MOVE_STD_THRESHOLD) * 0.4, 1.0)
        elif rundown_std <= PUBLIC_MOVE_STD_THRESHOLD:
            dispersion_score = max(rundown_std / PUBLIC_MOVE_STD_THRESHOLD * 0.3, 0.05)
        else:
            dispersion_score = 0.3 + (rundown_std - PUBLIC_MOVE_STD_THRESHOLD) / (SHARP_MOVE_STD_THRESHOLD - PUBLIC_MOVE_STD_THRESHOLD) * 0.3

    raw_sfs = (
        SFS_MAGNITUDE_WEIGHT * magnitude_score +
        SFS_SPREAD_WEIGHT * spread_score +
        SFS_DISPERSION_WEIGHT * dispersion_score
    )

    sfs = max(SFS_MIN, min(raw_sfs, SFS_MAX))

    if rundown_std is not None and rundown_std >= SHARP_MOVE_STD_THRESHOLD:
        move_type = 'sharp_disagree'
    elif rundown_std is not None and rundown_std <= PUBLIC_MOVE_STD_THRESHOLD:
        move_type = 'public'
    elif rundown_num_books is not None and rundown_num_books >= 3:
        move_type = 'mixed'
    else:
        move_type = 'unknown'

    components = {
        'magnitude': round(magnitude_score, 3),
        'spread': round(spread_score, 3),
        'dispersion': round(dispersion_score, 3),
    }
    reason = (
        f"SFS={sfs:.1%} [{move_type}] — "
        f"mag={magnitude_score:.2f}({line_move_magnitude:.1f}pts), "
        f"spread={spread_score:.2f}({spread_abs:.0f}pt), "
        f"disp={dispersion_score:.2f}"
        f"({f'{rundown_std:.1f}std' if rundown_std is not None else 'n/a'})"
    )

    return sfs, move_type, reason, components


def apply_steam_fragility(edge, line_move_against, spread_abs, rundown_std, rundown_num_books):
    if line_move_against <= 0:
        return edge, 0.0, 'no_move', None

    sfs, move_type, reason, components = calculate_steam_fragility_score(
        line_move_against, spread_abs, rundown_std, rundown_num_books
    )

    adjusted_edge = edge * (1.0 - sfs)

    return adjusted_edge, sfs, move_type, reason


def spread_risk_adjusted_edge(adjusted_edge, spread_abs):
    if spread_abs <= SPREAD_RISK_SCALE_BASE:
        return adjusted_edge
    excess = spread_abs - SPREAD_RISK_SCALE_BASE
    discount = 1.0 - (excess * SPREAD_RISK_SCALE_RATE / 10.0)
    discount = max(discount, 0.4)
    return adjusted_edge * discount


def check_star_injury_risk(home_injuries, away_injuries, pick_side, spread_abs):
    star_keywords = ['questionable', 'doubtful', 'game-time decision']
    penalty = 0.0
    reason = None

    fav_injuries = home_injuries if pick_side == 'home' else away_injuries
    if fav_injuries and isinstance(fav_injuries, str):
        injury_lower = fav_injuries.lower()
        star_flags = sum(1 for kw in star_keywords if kw in injury_lower)
        if star_flags > 0 and spread_abs >= STAR_QUESTIONABLE_SPREAD_THRESHOLD:
            penalty = STAR_QUESTIONABLE_EDGE_PENALTY * star_flags
            reason = f"Star questionable on {spread_abs:.0f}pt spread — edge penalized {penalty:+.1f}%"

    return penalty, reason


class EnsemblePredictor:
    """Ensemble model combining multiple ML algorithms with probability calibration"""
    
    def __init__(self, sport='nba'):
        self.sport = sport
        self.cfg = get_sport_config(sport)
        self.margin_std_dev = self.cfg.get('sigma', MARGIN_STD_DEV)
        self.model_weight = self.cfg.get('model_weight', MODEL_WEIGHT)
        self.max_edge_pct = self.cfg.get('max_edge_pct', MAX_EDGE_PCT)
        self.margin_std_floor = self.cfg.get('margin_std_floor', MARGIN_STD_FLOOR)
        self.margin_std_ceiling = self.cfg.get('margin_std_ceiling', MARGIN_STD_CEILING)
        self.edge_threshold_pct = self.cfg.get('edge_threshold_pct', EDGE_THRESHOLD_PCT)
        self.base_models = {
            'gradient_boosting': GradientBoostingClassifier(
                n_estimators=100,
                max_depth=5,
                learning_rate=0.1,
                random_state=42
            ),
            'random_forest': RandomForestClassifier(
                n_estimators=100,
                max_depth=10,
                random_state=42
            ),
            'xgboost': xgb.XGBClassifier(
                n_estimators=100,
                max_depth=5,
                learning_rate=0.1,
                random_state=42,
                eval_metric='logloss'
            ),
            'adaboost': AdaBoostClassifier(
                n_estimators=100,
                learning_rate=0.1,
                random_state=42
            )
        }
        self.models = {}
        self.margin_model = None
        self.scaler = StandardScaler()
        self.trained = False
        self.feature_names = []
        self.calibration_stats = {}
    
    def _games_table(self):
        return 'wnba_games' if self.sport == 'wnba' else 'games'

    def _ratings_table(self):
        return 'wnba_team_ratings' if self.sport == 'wnba' else 'team_ratings'

    def _has_table(self, conn, table_name):
        cur = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table_name,))
        return cur.fetchone() is not None

    def load_data(self):
        """Load training data from database with team ratings"""
        conn = sqlite3.connect(get_sqlite_path())

        games_tbl = self._games_table()
        ratings_tbl = self._ratings_table()
        has_ratings = self._has_table(conn, ratings_tbl)

        ratings_cols = ""
        ratings_join = ""
        if has_ratings:
            ratings_cols = """,
                hr.pace as home_pace, hr.off_rating as home_off_rtg, 
                hr.def_rating as home_def_rtg, hr.net_rating as home_net_rtg,
                ar.pace as away_pace, ar.off_rating as away_off_rtg,
                ar.def_rating as away_def_rtg, ar.net_rating as away_net_rtg"""
            ratings_join = f"""
            LEFT JOIN {ratings_tbl} hr ON g.home_team = hr.team_abbr
            LEFT JOIN {ratings_tbl} ar ON g.away_team = ar.team_abbr"""

        query = f'''
            SELECT 
                g.home_team, g.away_team, g.game_date,
                g.spread_home, g.spread_home_open, g.spread_home_close,
                g.total, g.total_open, g.total_close,
                g.home_ml, g.away_ml,
                g.home_record, g.away_record,
                g.home_home_record, g.away_away_record,
                g.home_last5, g.away_last5,
                g.home_rest_days, g.away_rest_days,
                g.line_movement,
                g.spread_result, g.home_score, g.away_score{ratings_cols},
                g.rundown_spread_consensus, g.rundown_spread_std,
                g.rundown_spread_range, g.rundown_num_books,
                g.bdl_home_win_pct, g.bdl_away_win_pct,
                g.bdl_home_conf_rank, g.bdl_away_conf_rank,
                g.bdl_home_scoring_margin, g.bdl_away_scoring_margin,
                g.bdl_home_avg_pts, g.bdl_away_avg_pts,
                g.bdl_home_avg_pts_against, g.bdl_away_avg_pts_against,
                g.home_spread_odds, g.away_spread_odds,
                g.home_spread_book, g.away_spread_book
            FROM {games_tbl} g{ratings_join}
            WHERE g.home_score IS NOT NULL
            AND g.away_score IS NOT NULL
        '''
        
        df = pd.read_sql_query(query, conn)
        conn.close()
        
        return df
    
    def calculate_sample_weights(self, df):
        """Calculate sample weights - recent games weighted higher"""
        weights = np.ones(len(df))
        
        if 'game_date' not in df.columns:
            return weights
        
        try:
            dates = pd.to_datetime(df['game_date'], errors='coerce')
            valid_mask = dates.notna()
            
            if valid_mask.sum() == 0:
                return weights
            
            max_date = dates[valid_mask].max()
            min_date = dates[valid_mask].min()
            date_range = (max_date - min_date).days
            
            if date_range > 0:
                days_ago = (max_date - dates).dt.days.fillna(date_range)
                recency = 1 - (days_ago / date_range)
                weights = 1.0 + recency
                
                current_season_start = datetime(max_date.year if max_date.month >= 10 else max_date.year - 1, 10, 1)
                current_season_mask = dates >= current_season_start
                weights = np.where(current_season_mask, weights * 1.5, weights)
            
            weights = weights / weights.mean()
            
        except Exception as e:
            print(f"   ⚠️ Weight calculation error: {e}")
            weights = np.ones(len(df))
        
        return weights
    
    def engineer_features(self, df):
        """Create features from raw data including pace/ratings"""
        features = pd.DataFrame()
        
        features['spread_home'] = pd.to_numeric(df['spread_home'], errors='coerce').fillna(0)
        spread_open = pd.to_numeric(df.get('spread_home_open', pd.Series([0]*len(df))), errors='coerce')
        features['spread_open'] = spread_open.fillna(features['spread_home'])
        features['line_movement'] = pd.to_numeric(df.get('line_movement', pd.Series([0]*len(df))), errors='coerce').fillna(0)
        
        features['total'] = pd.to_numeric(df.get('total', pd.Series([220]*len(df))), errors='coerce').fillna(220)
        total_open = pd.to_numeric(df.get('total_open', pd.Series([220]*len(df))), errors='coerce')
        features['total_open'] = total_open.fillna(features['total'])
        features['total_movement'] = features['total'] - features['total_open']
        
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
        
        home_last5 = df.get('home_last5', pd.Series(['']*len(df)))
        away_last5 = df.get('away_last5', pd.Series(['']*len(df)))
        features['home_form'] = home_last5.apply(parse_form)
        features['away_form'] = away_last5.apply(parse_form)
        features['form_diff'] = features['home_form'] - features['away_form']
        
        features['home_rest'] = pd.to_numeric(df.get('home_rest_days', pd.Series([1]*len(df))), errors='coerce').fillna(1)
        features['away_rest'] = pd.to_numeric(df.get('away_rest_days', pd.Series([1]*len(df))), errors='coerce').fillna(1)
        features['rest_advantage'] = features['home_rest'] - features['away_rest']
        
        features['spread_abs'] = features['spread_home'].abs()
        features['is_favorite'] = (features['spread_home'] < 0).astype(int)
        
        features['home_pace'] = pd.to_numeric(df.get('home_pace', pd.Series([100.0]*len(df))), errors='coerce').fillna(100.0)
        features['away_pace'] = pd.to_numeric(df.get('away_pace', pd.Series([100.0]*len(df))), errors='coerce').fillna(100.0)
        features['pace_diff'] = features['home_pace'] - features['away_pace']
        features['combined_pace'] = (features['home_pace'] + features['away_pace']) / 2
        
        features['home_off_rtg'] = pd.to_numeric(df.get('home_off_rtg', pd.Series([110.0]*len(df))), errors='coerce').fillna(110.0)
        features['home_def_rtg'] = pd.to_numeric(df.get('home_def_rtg', pd.Series([110.0]*len(df))), errors='coerce').fillna(110.0)
        features['away_off_rtg'] = pd.to_numeric(df.get('away_off_rtg', pd.Series([110.0]*len(df))), errors='coerce').fillna(110.0)
        features['away_def_rtg'] = pd.to_numeric(df.get('away_def_rtg', pd.Series([110.0]*len(df))), errors='coerce').fillna(110.0)
        
        features['home_net_rtg'] = pd.to_numeric(df.get('home_net_rtg', pd.Series([0.0]*len(df))), errors='coerce').fillna(0.0)
        features['away_net_rtg'] = pd.to_numeric(df.get('away_net_rtg', pd.Series([0.0]*len(df))), errors='coerce').fillna(0.0)
        features['net_rtg_diff'] = features['home_net_rtg'] - features['away_net_rtg']
        
        features['off_matchup'] = features['home_off_rtg'] - features['away_def_rtg']
        features['def_matchup'] = features['away_off_rtg'] - features['home_def_rtg']

        features['rundown_consensus'] = pd.to_numeric(df.get('rundown_spread_consensus', pd.Series([0]*len(df))), errors='coerce').fillna(features['spread_home'])
        features['spread_vs_consensus'] = features['spread_home'] - features['rundown_consensus']
        features['rundown_spread_std'] = pd.to_numeric(df.get('rundown_spread_std', pd.Series([0]*len(df))), errors='coerce').fillna(0)
        features['rundown_spread_range'] = pd.to_numeric(df.get('rundown_spread_range', pd.Series([0]*len(df))), errors='coerce').fillna(0)
        features['rundown_num_books'] = pd.to_numeric(df.get('rundown_num_books', pd.Series([0]*len(df))), errors='coerce').fillna(0)

        features['bdl_home_win_pct'] = pd.to_numeric(df.get('bdl_home_win_pct', pd.Series([0.5]*len(df))), errors='coerce').fillna(0.5)
        features['bdl_away_win_pct'] = pd.to_numeric(df.get('bdl_away_win_pct', pd.Series([0.5]*len(df))), errors='coerce').fillna(0.5)
        features['bdl_win_pct_diff'] = features['bdl_home_win_pct'] - features['bdl_away_win_pct']
        features['bdl_home_conf_rank'] = pd.to_numeric(df.get('bdl_home_conf_rank', pd.Series([15]*len(df))), errors='coerce').fillna(15)
        features['bdl_away_conf_rank'] = pd.to_numeric(df.get('bdl_away_conf_rank', pd.Series([15]*len(df))), errors='coerce').fillna(15)
        features['bdl_conf_rank_diff'] = features['bdl_away_conf_rank'] - features['bdl_home_conf_rank']
        features['bdl_home_scoring_margin'] = pd.to_numeric(df.get('bdl_home_scoring_margin', pd.Series([0]*len(df))), errors='coerce').fillna(0)
        features['bdl_away_scoring_margin'] = pd.to_numeric(df.get('bdl_away_scoring_margin', pd.Series([0]*len(df))), errors='coerce').fillna(0)
        features['bdl_scoring_margin_diff'] = features['bdl_home_scoring_margin'] - features['bdl_away_scoring_margin']
        features['bdl_home_avg_pts'] = pd.to_numeric(df.get('bdl_home_avg_pts', pd.Series([110]*len(df))), errors='coerce').fillna(110)
        features['bdl_away_avg_pts'] = pd.to_numeric(df.get('bdl_away_avg_pts', pd.Series([110]*len(df))), errors='coerce').fillna(110)
        features['bdl_projected_total'] = features['bdl_home_avg_pts'] + features['bdl_away_avg_pts']

        def parse_injury_impact(injury_text):
            if pd.isna(injury_text) or not injury_text or injury_text == '':
                return 0.0
            text = str(injury_text)
            out_count = text.lower().count('out')
            questionable_count = text.lower().count('questionable') + text.lower().count('doubtful')
            return float(out_count * 5.0 + questionable_count * 2.0)

        features['home_injury_impact'] = df.get('home_injuries', pd.Series(['']*len(df))).apply(parse_injury_impact)
        features['away_injury_impact'] = df.get('away_injuries', pd.Series(['']*len(df))).apply(parse_injury_impact)
        features['injury_diff'] = features['away_injury_impact'] - features['home_injury_impact']

        return features
    
    def prepare_target(self, df):
        """Create target variable (1 = home wins/covers, 0 = away wins/covers)"""
        # Calculate score margin
        margin = df['home_score'] - df['away_score']
        
        # If we have spread data, use actual cover result
        # Otherwise, use home win as proxy (home team wins = 1)
        if 'spread_home' in df.columns and df['spread_home'].notna().sum() > len(df) * 0.5:
            # Use spread cover: home covers if margin > -spread
            spread = df['spread_home'].fillna(0)
            target = (margin + spread > 0).astype(int)
        else:
            # Use simple home win as target
            target = (margin > 0).astype(int)
        
        return target
    
    def train(self, use_sample_weights=True):
        """Train all models in the ensemble with probability calibration and sample weighting"""
        print("\n" + "="*60)
        print("🤖 TRAINING CALIBRATED ENSEMBLE MODEL")
        print("="*60 + "\n")
        
        df = self.load_data()
        
        if len(df) < 20:
            print(f"❌ Not enough data to train. Need at least 20 games with results.")
            print(f"   Current: {len(df)} games")
            print(f"   Keep collecting data!\n")
            return False
        
        print(f"📊 Training on {len(df)} games with results")
        
        df = df[df['spread_result'] != 'PUSH']
        
        X = self.engineer_features(df)
        y = self.prepare_target(df)
        
        if use_sample_weights:
            sample_weights = self.calculate_sample_weights(df)
            print(f"   📈 Using recency-weighted samples (current season 1.5x)")
        else:
            sample_weights = np.ones(len(df))
        
        X = X.fillna(0)
        self.feature_names = X.columns.tolist()
        print(f"   📋 Using {len(self.feature_names)} features\n")
        
        indices = np.arange(len(X))
        train_idx, test_idx = train_test_split(indices, test_size=0.2, random_state=42)
        
        X_train, X_test = X.iloc[train_idx], X.iloc[test_idx]
        y_train, y_test = y.iloc[train_idx], y.iloc[test_idx]
        weights_train = sample_weights[train_idx]
        
        X_train_scaled = self.scaler.fit_transform(X_train)
        X_test_scaled = self.scaler.transform(X_test)
        
        print("Training and calibrating models:")
        print("-" * 50)
        
        results = {}
        
        for name, base_model in self.base_models.items():
            print(f"   Training {name}...", end=" ")
            
            import copy
            weighted_base = copy.deepcopy(base_model)
            
            try:
                weighted_base.fit(X_train_scaled, y_train, sample_weight=weights_train)
            except TypeError:
                weighted_base.fit(X_train_scaled, y_train)
            
            calibration_method = 'isotonic' if len(X_train) > 100 else 'sigmoid'
            
            calibrated_model = CalibratedClassifierCV(
                base_model,
                method=calibration_method,
                cv=5
            )
            
            try:
                calibrated_model.fit(X_train_scaled, y_train, sample_weight=weights_train)
            except TypeError:
                calibrated_model.fit(X_train_scaled, y_train)
            
            self.models[name] = calibrated_model
            
            # Evaluate
            train_preds = calibrated_model.predict(X_train_scaled)
            test_preds = calibrated_model.predict(X_test_scaled)
            train_score = accuracy_score(y_train, train_preds)
            test_score = accuracy_score(y_test, test_preds)
            
            # Brier score (lower is better - measures probability calibration)
            test_proba = calibrated_model.predict_proba(X_test_scaled)[:, 1]
            brier = brier_score_loss(y_test, test_proba)
            
            results[name] = {
                'train': train_score,
                'test': test_score,
                'brier': brier
            }
            
            print(f"✅ Acc: {test_score:.1%} | Brier: {brier:.3f}")
        
        print("\n" + "-" * 50)
        print("\n📈 MODEL PERFORMANCE (Calibrated):")
        print("-" * 70)
        print(f"{'Model':<20} {'Train Acc':>12} {'Test Acc':>12} {'Brier Score':>12}")
        print("-" * 70)
        
        for name, scores in results.items():
            print(f"{name:<20} {scores['train']:>12.1%} {scores['test']:>12.1%} {scores['brier']:>12.3f}")
        
        # Ensemble accuracy and calibration
        ensemble_proba = self.predict_proba(X_test_scaled)
        ensemble_classes = (ensemble_proba >= 0.5).astype(int)
        ensemble_acc = accuracy_score(y_test, ensemble_classes)
        ensemble_brier = brier_score_loss(y_test, ensemble_proba)
        
        print("-" * 70)
        print(f"{'ENSEMBLE (avg)':<20} {'-':>12} {ensemble_acc:>12.1%} {ensemble_brier:>12.3f}")
        print("-" * 70)
        
        # Calculate calibration curve for ensemble
        self._analyze_calibration(y_test, ensemble_proba)
        
        print("\n   Training margin regression model...")
        margin_target = (df['home_score'] - df['away_score']).astype(float)
        margin_train = margin_target.iloc[train_idx]
        margin_test = margin_target.iloc[test_idx]
        
        self.margin_model = GradientBoostingRegressor(
            n_estimators=200, max_depth=4, learning_rate=0.1, random_state=42
        )
        try:
            self.margin_model.fit(X_train_scaled, margin_train, sample_weight=weights_train)
        except TypeError:
            self.margin_model.fit(X_train_scaled, margin_train)
        
        margin_preds = self.margin_model.predict(X_test_scaled)
        margin_mae = np.mean(np.abs(margin_preds - margin_test))
        self.margin_mae = margin_mae

        from sklearn.model_selection import KFold
        X_all_scaled = self.scaler.transform(X)
        kf = KFold(n_splits=5, shuffle=True, random_state=42)
        cv_residuals = []
        for cv_train, cv_test in kf.split(X_all_scaled, margin_target):
            cv_model = GradientBoostingRegressor(
                n_estimators=200, max_depth=4, learning_rate=0.1, random_state=42
            )
            cv_model.fit(X_all_scaled[cv_train], margin_target.iloc[cv_train])
            cv_preds = cv_model.predict(X_all_scaled[cv_test])
            cv_residuals.extend(cv_preds - margin_target.iloc[cv_test].values)
        cv_std_raw = np.std(cv_residuals)
        self.margin_std = min(max(cv_std_raw, self.margin_std_floor), self.margin_std_ceiling)
        self.using_fallback_sigma = (self.margin_std != cv_std_raw)

        print(f"   Margin MAE: {margin_mae:.1f} pts")
        print(f"   Margin STD (raw): {cv_std_raw:.1f} pts")
        print(f"   Margin STD (used): {self.margin_std:.1f} pts (clamped [{self.margin_std_floor}, {self.margin_std_ceiling}])")
        print(f"   USING_FALLBACK_SIGMA = {self.using_fallback_sigma}")
        
        self.trained = True
        
        self.save()
        
        print(f"\n   Calibrated model trained and saved!")
        print(f"   Ensemble Test Accuracy: {ensemble_acc:.1%}")
        print(f"   Brier Score: {ensemble_brier:.3f} (lower is better)")
        print(f"   Margin MAE: {self.margin_mae:.1f} pts")
        print(f"   Margin Std Dev: {self.margin_std:.1f} pts\n")
        
        return True
    
    def _analyze_calibration(self, y_true, y_prob, n_bins=5):
        """Analyze probability calibration quality"""
        print("\n📊 CALIBRATION ANALYSIS:")
        print("-" * 50)
        
        # Get calibration curve
        prob_true, prob_pred = calibration_curve(y_true, y_prob, n_bins=n_bins, strategy='uniform')
        
        self.calibration_stats = {
            'prob_true': prob_true.tolist(),
            'prob_pred': prob_pred.tolist()
        }
        
        print(f"{'Predicted':>12} {'Actual':>12} {'Diff':>10}")
        print("-" * 40)
        
        for pred, true in zip(prob_pred, prob_true):
            diff = pred - true
            indicator = "✓" if abs(diff) < 0.05 else "⚠️" if abs(diff) < 0.10 else "❌"
            print(f"{pred:>12.1%} {true:>12.1%} {diff:>+9.1%} {indicator}")
        
        # Overall calibration error
        cal_error = np.mean(np.abs(prob_pred - prob_true))
        print("-" * 40)
        print(f"Mean Calibration Error: {cal_error:.1%}")
        
        if cal_error < 0.05:
            print("✅ Excellent calibration - probabilities match reality well!")
        elif cal_error < 0.10:
            print("👍 Good calibration - probabilities are reasonably accurate")
        else:
            print("⚠️ Fair calibration - probabilities may need adjustment")
    
    def predict_proba(self, X):
        """Get averaged probability predictions from all models"""
        if isinstance(X, pd.DataFrame):
            X = self.scaler.transform(X)
        
        predictions = []
        
        for name, model in self.models.items():
            proba = model.predict_proba(X)[:, 1]
            predictions.append(proba)
        
        # Average all model predictions
        ensemble_proba = np.mean(predictions, axis=0)
        
        return ensemble_proba
    
    def predict(self, X):
        """Get binary predictions from ensemble"""
        proba = self.predict_proba(X)
        return (proba >= 0.5).astype(int)
    
    def _get_betting_date(self):
        """Get current betting day in ET (rollover at 2:30 AM)."""
        try:
            from zoneinfo import ZoneInfo
            now_et = datetime.now(ZoneInfo('America/New_York'))
        except ImportError:
            now_et = datetime.utcnow() - timedelta(hours=5)
        if now_et.hour < 2 or (now_et.hour == 2 and now_et.minute < 30):
            now_et = now_et - timedelta(days=1)
        return now_et.strftime('%Y-%m-%d')

    def predict_games(self, min_confidence=None, log_predictions=True, date_str=None, min_minutes_to_tip=30):
        """Make predictions for today's upcoming games with filtering.
        min_minutes_to_tip: buffer before tip (0 = include all unscored games, 30 = default)."""
        if date_str is None:
            date_str = self._get_betting_date()
        print("\n" + "="*60)
        print(f"🎯 PREDICTIONS FOR {date_str}")
        print("="*60 + "\n")

        if min_confidence is None:
            min_confidence = MIN_CONFIDENCE_THRESHOLD

        if not self.trained:
            self.load_model()
            if not self.trained:
                print("❌ No trained model found. Run training first.\n")
                return []

        conn = sqlite3.connect(get_sqlite_path())

        games_tbl = self._games_table()
        ratings_tbl = self._ratings_table()
        has_ratings = self._has_table(conn, ratings_tbl)

        ratings_cols = ""
        ratings_join = ""
        if has_ratings:
            ratings_cols = """,
                hr.pace as home_pace, hr.off_rating as home_off_rtg,
                hr.def_rating as home_def_rtg, hr.net_rating as home_net_rtg,
                ar.pace as away_pace, ar.off_rating as away_off_rtg,
                ar.def_rating as away_def_rtg, ar.net_rating as away_net_rtg"""
            ratings_join = f"""
            LEFT JOIN {ratings_tbl} hr ON g.home_team = hr.team_abbr
            LEFT JOIN {ratings_tbl} ar ON g.away_team = ar.team_abbr"""

        # Time filter: America/New_York. Eligible until min_minutes_to_tip before tip (0 = all unscored).
        try:
            from zoneinfo import ZoneInfo
            et = ZoneInfo("America/New_York")
        except ImportError:
            from datetime import timezone as tz
            et = tz(timedelta(hours=-5))
        now_et = datetime.now(et)
        cutoff_et = now_et + timedelta(minutes=min_minutes_to_tip)
        cutoff_utc_iso = cutoff_et.astimezone(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
        # Include NULL/empty game_time as upcoming; otherwise require game_time > cutoff
        query = f'''
            SELECT
                g.id, g.home_team, g.away_team, g.game_date, g.game_time,
                g.spread_home, g.spread_home_open, g.spread_home_close,
                g.total, g.total_open, g.total_close,
                g.home_ml, g.away_ml,
                g.home_record, g.away_record,
                g.home_home_record, g.away_away_record,
                g.home_last5, g.away_last5,
                g.home_rest_days, g.away_rest_days,
                g.line_movement{ratings_cols},
                g.rundown_spread_consensus, g.rundown_spread_std,
                g.rundown_spread_range, g.rundown_num_books,
                g.bdl_home_win_pct, g.bdl_away_win_pct,
                g.bdl_home_conf_rank, g.bdl_away_conf_rank,
                g.bdl_home_scoring_margin, g.bdl_away_scoring_margin,
                g.bdl_home_avg_pts, g.bdl_away_avg_pts,
                g.bdl_home_avg_pts_against, g.bdl_away_avg_pts_against,
                g.home_spread_odds, g.away_spread_odds,
                g.home_spread_book, g.away_spread_book
            FROM {games_tbl} g{ratings_join}
            WHERE g.game_date = ?
            AND g.home_score IS NULL
            AND g.spread_home IS NOT NULL
            AND (g.game_time IS NULL OR COALESCE(TRIM(g.game_time), '') = '' OR g.game_time > ?)
        '''

        df = pd.read_sql_query(query, conn, params=(date_str, cutoff_utc_iso))
        conn.close()
        
        if len(df) == 0:
            print("ℹ️  No upcoming games to predict.\n")
            return []
        
        print(f"📊 Analyzing {len(df)} upcoming games...")
        print(f"   🎚️  Minimum confidence filter: {min_confidence*100:.0f}%\n")
        
        X = self.engineer_features(df)
        
        missing_features = [f for f in self.feature_names if f not in X.columns]
        for feat in missing_features:
            X[feat] = 0
        X = X[self.feature_names]
        
        X_scaled = self.scaler.transform(X)
        
        ensemble_proba = self.predict_proba(X_scaled)
        
        predicted_margins = None
        sigma = self.margin_std_dev
        using_fallback = True
        if self.margin_model is not None:
            predicted_margins = self.margin_model.predict(X_scaled)
            saved_sigma = getattr(self, 'margin_std', None)
            if saved_sigma is not None:
                sigma = saved_sigma
                using_fallback = False
            else:
                sigma = self.margin_std_dev
        
        print(f"   USING_FALLBACK_SIGMA = {using_fallback} (sigma={sigma:.1f})")
        if getattr(self, 'margin_mae', None):
            print(f"   Margin MAE: {self.margin_mae:.1f} pts")
        
        picks = []
        
        from performance_tracker import odds_to_implied_prob, calculate_ev
        
        for i, row in df.iterrows():
            idx = df.index.get_loc(i)
            
            home = row['home_team']
            away = row['away_team']
            spread = row['spread_home']
            proba = ensemble_proba[idx]
            
            home_spread_odds = row.get('home_spread_odds', None)
            away_spread_odds = row.get('away_spread_odds', None)
            home_ml = row.get('home_ml', None)
            away_ml = row.get('away_ml', None)
            
            pred_margin_raw = predicted_margins[idx] if predicted_margins is not None else None
            
            used_fallback = False
            model_only_home_cover = None
            if pred_margin_raw is not None and spread is not None:
                market_margin = -spread
                pred_margin = self.model_weight * pred_margin_raw + (1 - self.model_weight) * market_margin
                home_cover_prob = float(norm.cdf((pred_margin + spread) / sigma))
                model_only_home_cover = float(norm.cdf((pred_margin_raw + spread) / sigma))
            else:
                used_fallback = True
                pred_margin = pred_margin_raw
                home_cover_prob = proba
            
            if home_cover_prob >= 0.5:
                pick_side = 'home'
                pick_label = f"{home} {spread:+.1f}"
                confidence = home_cover_prob
            else:
                pick_side = 'away'
                pick_label = f"{away} {-spread:+.1f}"
                confidence = 1 - home_cover_prob
            
            home_spread_book = row.get('home_spread_book', None)
            away_spread_book = row.get('away_spread_book', None)
            if pick_side == 'home':
                market_odds = int(home_spread_odds) if home_spread_odds is not None and not pd.isna(home_spread_odds) else STANDARD_ODDS
                best_book = home_spread_book if home_spread_book is not None and not (isinstance(home_spread_book, float) and pd.isna(home_spread_book)) else 'DraftKings'
            else:
                market_odds = int(away_spread_odds) if away_spread_odds is not None and not pd.isna(away_spread_odds) else STANDARD_ODDS
                best_book = away_spread_book if away_spread_book is not None and not (isinstance(away_spread_book, float) and pd.isna(away_spread_book)) else 'DraftKings'
            
            implied_prob = odds_to_implied_prob(market_odds)
            edge_vs_market = (confidence - implied_prob) * 100
            ev = calculate_ev(confidence, market_odds)
            
            spread_abs = abs(spread) if spread is not None else 0
            open_spread = row.get('spread_home_open', None)
            line_move_against = 0.0
            line_move_in_favor = 0.0
            steam_fragility = 0.0
            line_move_type = 'no_move'
            line_move_decomp_reason = None
            r_std = None
            r_num = None
            if open_spread is not None and spread is not None:
                move = spread - open_spread
                if hasattr(row, 'get'):
                    r_std_raw = row.get('rundown_spread_std', None)
                    r_num_raw = row.get('rundown_num_books', None)
                    try:
                        r_std = float(r_std_raw) if r_std_raw is not None and not pd.isna(r_std_raw) else None
                        r_num = int(r_num_raw) if r_num_raw is not None and not pd.isna(r_num_raw) else None
                    except (ValueError, TypeError):
                        r_std, r_num = None, None

                if pick_side == 'home':
                    adverse_move = -move
                else:
                    adverse_move = move

                if adverse_move >= 1.0:
                    line_move_against = adverse_move
                elif adverse_move <= -1.0:
                    line_move_in_favor = abs(adverse_move)
                    if r_std is not None and r_std >= SHARP_MOVE_STD_THRESHOLD and r_num is not None and r_num >= 3:
                        line_move_type = 'sharp_agree'
                        line_move_decomp_reason = f"Sharp steam supports model ({r_std:.1f} book std, {line_move_in_favor:.1f}pts in our favor)"

            adjusted_edge = edge_vs_market
            if line_move_against >= 1.0:
                adjusted_edge, steam_fragility, line_move_type, line_move_decomp_reason = apply_steam_fragility(
                    edge_vs_market, line_move_against, spread_abs, r_std, r_num
                )
            adjusted_edge = min(adjusted_edge, self.max_edge_pct)
            
            fail_reasons = []
            pass_reason = None
            if spread is None:
                fail_reasons.append('missing_spread')
            if pred_margin is None and proba is None:
                fail_reasons.append('missing_prediction')
            if using_fallback:
                fail_reasons.append('fallback_sigma')
                pass_reason = "Model calibration in progress. No qualifying pick today."
            if line_move_against >= LINE_MOVE_HARD_STOP and adjusted_edge < LINE_MOVE_HARD_STOP_MIN_EDGE:
                fail_reasons.append('extreme_line_move')
                pass_reason = f"Extreme line movement ({line_move_against:+.1f}pts against) — auto-pass unless edge >= {LINE_MOVE_HARD_STOP_MIN_EDGE}%"
            
            spread_abs = abs(spread) if spread is not None else 0
            required_edge = get_edge_threshold_for_spread(spread_abs)
            if adjusted_edge < required_edge:
                if spread_abs >= 11:
                    fail_reasons.append(f'spread_too_large ({spread_abs:.1f}, need {required_edge}% edge)')
                    pass_reason = f"Spread too large ({spread_abs:.1f}pts) for available edge ({adjusted_edge:+.1f}%)"
                elif spread_abs >= 7:
                    fail_reasons.append(f'mid_spread_insufficient_edge ({spread_abs:.1f}, need {required_edge}%)')
                    pass_reason = f"Mid-range spread ({spread_abs:.1f}pts) requires {required_edge}% edge, have {adjusted_edge:+.1f}%"
            
            home_injuries = row.get('home_injuries', None) if hasattr(row, 'get') else None
            away_injuries = row.get('away_injuries', None) if hasattr(row, 'get') else None

            injury_penalty, injury_reason = check_star_injury_risk(
                home_injuries, away_injuries, pick_side, spread_abs
            )
            if injury_penalty > 0:
                adjusted_edge -= injury_penalty
                if injury_reason:
                    fail_reasons.append('star_questionable')
                    pass_reason = injury_reason

            home_rest_val = row.get('home_rest_days', None) if hasattr(row, 'get') else None
            away_rest_val = row.get('away_rest_days', None) if hasattr(row, 'get') else None
            try:
                home_rest_int = int(home_rest_val) if home_rest_val is not None and not pd.isna(home_rest_val) else None
                away_rest_int = int(away_rest_val) if away_rest_val is not None and not pd.isna(away_rest_val) else None
            except (ValueError, TypeError):
                home_rest_int, away_rest_int = None, None

            game_date_val = row.get('game_date', None) if hasattr(row, 'get') else None

            is_fav = (pick_side == 'home' and spread < 0) or (pick_side == 'away' and spread > 0)
            if is_fav:
                asb_penalty, asb_reason = calculate_asb_penalty(spread_abs, game_date_val)
                if asb_penalty > 0:
                    adjusted_edge -= asb_penalty
                    if asb_reason and 'star_questionable' not in fail_reasons:
                        pass_reason = asb_reason

                rest_penalty, rest_reason = calculate_long_rest_penalty(
                    pick_side, spread_abs, home_rest_int, away_rest_int
                )
                if rest_penalty > 0 and asb_penalty == 0:
                    adjusted_edge -= rest_penalty
                    if rest_reason and not pass_reason:
                        pass_reason = rest_reason

            risk_weighted_edge = spread_risk_adjusted_edge(adjusted_edge, spread_abs)

            explanation = self._generate_explanation(row, proba, confidence, adjusted_edge, pred_margin)
            
            if confidence >= STRONG_CONFIDENCE_THRESHOLD:
                rating = "STRONG"
            elif confidence >= MIN_CONFIDENCE_THRESHOLD:
                rating = "LEAN"
            else:
                rating = "SLIGHT"
            
            if len(fail_reasons) == 0 and risk_weighted_edge < self.edge_threshold_pct:
                if spread_abs > SPREAD_RISK_SCALE_BASE and adjusted_edge >= self.edge_threshold_pct:
                    pass_reason = f"Edge {adjusted_edge:+.1f}% discounted to {risk_weighted_edge:+.1f}% for {spread_abs:.0f}pt spread risk"
                else:
                    pass_reason = f"Edge below threshold ({risk_weighted_edge:+.1f}% < {self.edge_threshold_pct}%)"
            if len(fail_reasons) == 0 and confidence < min_confidence:
                pass_reason = f"Confidence below minimum ({confidence:.1%} < {min_confidence:.0%})"
            if steam_fragility > 0 and risk_weighted_edge < self.edge_threshold_pct and edge_vs_market >= self.edge_threshold_pct:
                pass_reason = f"Steam fragility {steam_fragility:.0%} on {line_move_against:+.1f}pt move, edge {edge_vs_market:+.1f}% → {adjusted_edge:+.1f}%"

            passes = (
                len(fail_reasons) == 0
                and confidence >= min_confidence
                and risk_weighted_edge >= required_edge
            )
            
            z_score_val = None
            if pred_margin is not None and spread is not None:
                z_score_val = (pred_margin + spread) / sigma
                if pick_side == 'away':
                    z_score_val = -z_score_val

            model_only_conf = None
            model_only_edge_val = None
            if model_only_home_cover is not None:
                model_only_conf = model_only_home_cover if pick_side == 'home' else 1 - model_only_home_cover
                model_only_edge_val = round((model_only_conf - implied_prob) * 100, 2)

            picks.append({
                'game_id': row['id'],
                'game_date': row['game_date'],
                'game_time': row.get('game_time', None) if hasattr(row, 'get') else None,
                'game': f"{away} @ {home}",
                'home_team': home,
                'away_team': away,
                'spread': spread,
                'spread_home_open': open_spread,
                'pick': pick_label,
                'pick_side': pick_side,
                'predicted_margin': round(pred_margin, 1) if pred_margin is not None else None,
                'predicted_margin_raw': round(pred_margin_raw, 1) if pred_margin_raw is not None else None,
                'sigma': round(sigma, 2),
                'z_score': round(z_score_val, 3) if z_score_val is not None else None,
                'raw_edge': round(min(edge_vs_market, self.max_edge_pct), 2),
                'cover_prob': round(confidence, 4),
                'confidence': confidence,
                'edge': round(min(edge_vs_market, self.max_edge_pct), 2),
                'adjusted_edge': round(adjusted_edge, 2),
                'ev': ev,
                'implied_prob': round(implied_prob, 4),
                'market_odds': market_odds,
                'best_book': best_book,
                'home_spread_odds': int(home_spread_odds) if home_spread_odds is not None and not pd.isna(home_spread_odds) else None,
                'away_spread_odds': int(away_spread_odds) if away_spread_odds is not None and not pd.isna(away_spread_odds) else None,
                'rating': rating,
                'home_proba': proba,
                'line_move_against': round(line_move_against, 1),
                'steam_fragility': round(steam_fragility, 3),
                'line_move_type': line_move_type,
                'line_move_decomp_reason': line_move_decomp_reason,
                'injury_penalty': round(injury_penalty, 1),
                'risk_weighted_edge': round(risk_weighted_edge, 2),
                'model_only_cover_prob': round(model_only_conf, 4) if model_only_conf is not None else None,
                'model_only_edge': model_only_edge_val,
                'fail_reasons': fail_reasons,
                'pass_reason': pass_reason,
                'required_edge': required_edge,
                'explanation': explanation,
                'passes_filter': passes,
            })
        
        filtered_picks = [p for p in picks if p['passes_filter']]
        excluded_count = len(picks) - len(filtered_picks)
        
        print("-" * 100)
        print(f"{'Game':<28} {'Pick':<16} {'Margin':>7} {'Cover':>7} {'Edge':>6} {'Adj':>6} {'EV':>7} {'Rating':>8}")
        print("-" * 100)
        
        for pick in sorted(filtered_picks, key=lambda x: x['adjusted_edge'], reverse=True):
            game_str = pick['game'][:27]
            margin_str = f"{pick['predicted_margin']:+.1f}" if pick['predicted_margin'] is not None else "  --"
            penalty_str = f" (SFS:{pick['steam_fragility']:.0%})" if pick['steam_fragility'] > 0 else ""
            print(f"{game_str:<28} {pick['pick']:<16} {margin_str:>7} {pick['cover_prob']:>6.1%} {pick['edge']:>+5.1f}% {pick['adjusted_edge']:>+5.1f}% {pick['ev']:>+6.1f}% {pick['rating']:>8}{penalty_str}")
        
        print("-" * 100)
        
        failed = [p for p in picks if p['fail_reasons']]
        if failed:
            print(f"\n   {len(failed)} games hard-passed: {', '.join(set(r for p in failed for r in p['fail_reasons']))}")
        if excluded_count > 0:
            print(f"   {excluded_count} games excluded (below {self.edge_threshold_pct}% adjusted edge)")

        all_adj = [p['adjusted_edge'] for p in picks]
        all_rw = [p['risk_weighted_edge'] for p in picks]
        all_req = [p['required_edge'] for p in picks]
        if all_adj:
            max_adj = max(all_adj)
            max_rw = max(all_rw)
            min_req = min(all_req)
            best_game = max(picks, key=lambda p: p['adjusted_edge'])
            print(f"\n   Max edge today: {max_adj:+.1f}% (risk-weighted: {max_rw:+.1f}%)")
            print(f"   Lowest threshold: {min_req:.1f}% (base: {self.edge_threshold_pct}%)")
            print(f"   Best game: {best_game['game']} — need {best_game['required_edge']:.1f}%, have {best_game['adjusted_edge']:+.1f}%")
            if best_game['pass_reason']:
                print(f"   Pass reason: {best_game['pass_reason']}")

        if log_predictions:
            try:
                from performance_tracker import log_prediction
                logged = 0
                for pick in picks:
                    if log_prediction(
                        pick['game_id'], pick['game_date'], pick['home_team'], pick['away_team'],
                        pick['spread'], pick['pick'], pick['confidence'], pick['home_proba'],
                        market_odds=pick['market_odds'],
                        recommended_book='DraftKings',
                        explanation='|'.join(pick['explanation']) if pick['explanation'] else None,
                        predicted_margin=pick.get('predicted_margin'),
                        sigma=pick.get('sigma'),
                        z_score=pick.get('z_score'),
                        raw_edge=pick.get('raw_edge'),
                        adjusted_edge=pick.get('adjusted_edge'),
                    ):
                        logged += 1
                if logged > 0:
                    print(f"   Logged {logged} predictions with margin + EV audit trail")
            except Exception as e:
                pass
        
        qualified = [p for p in filtered_picks if p['adjusted_edge'] >= self.edge_threshold_pct]
        if qualified:
            print(f"\n   QUALIFIED OPPORTUNITIES ({self.edge_threshold_pct}%+ adjusted edge):")
            for pick in sorted(qualified, key=lambda x: x['adjusted_edge'], reverse=True):
                margin_str = f", margin: {pick['predicted_margin']:+.1f}" if pick['predicted_margin'] is not None else ""
                print(f"   {pick['rating']}: {pick['pick']} (edge: +{pick['adjusted_edge']:.1f}%{margin_str})")
                if pick['explanation']:
                    for reason in pick['explanation']:
                        print(f"      - {reason}")
        
        print()
        return picks
    
    def _generate_explanation(self, row, proba, confidence, edge, pred_margin=None):
        """Generate exactly 3 structured reasoning bullets from data.
        Always picks from: rest advantage, net rating gap, pace/matchup, line value.
        Same structure every time."""
        
        spread = row.get('spread_home', 0) or 0
        open_spread = row.get('spread_home_open', None)
        home = row['home_team']
        away = row['away_team']
        pick_home = proba >= 0.5
        pick_team = home if pick_home else away
        opp_team = away if pick_home else home
        
        candidates = []
        
        home_rest = row.get('home_rest_days', None)
        away_rest = row.get('away_rest_days', None)
        try:
            h_rest = int(home_rest) if home_rest is not None else None
            a_rest = int(away_rest) if away_rest is not None else None
            if h_rest is not None and a_rest is not None:
                rest_diff = (h_rest - a_rest) if pick_home else (a_rest - h_rest)
                if rest_diff > 0:
                    candidates.append(('rest', 3, f"Rest advantage: {pick_team} on {max(h_rest,a_rest)}d rest vs {opp_team} {min(h_rest,a_rest)}d"))
                elif h_rest == a_rest:
                    if h_rest == 0:
                        candidates.append(('rest', 1, f"Back-to-back for both teams — no rest edge"))
                    else:
                        candidates.append(('rest', 1, f"Both teams on {h_rest}d rest — no rest edge"))
                elif rest_diff < 0:
                    candidates.append(('rest', 1, f"Rest disadvantage: {pick_team} {h_rest if pick_home else a_rest}d vs {opp_team} {a_rest if pick_home else h_rest}d — edge overcomes this"))
                else:
                    candidates.append(('rest', 1, f"Rest neutral: {home} {h_rest}d, {away} {a_rest}d"))
            else:
                candidates.append(('rest', 0, f"Rest data unavailable"))
        except (ValueError, TypeError):
            candidates.append(('rest', 0, f"Rest data unavailable"))
        
        home_margin = row.get('bdl_home_scoring_margin', None)
        away_margin = row.get('bdl_away_scoring_margin', None)
        home_net = row.get('home_net_rtg', None)
        away_net = row.get('away_net_rtg', None)
        try:
            if home_net is not None and away_net is not None:
                h_net = float(home_net)
                a_net = float(away_net)
                net_diff = (h_net - a_net) if pick_home else (a_net - h_net)
                if net_diff > 3:
                    candidates.append(('net_rating', 3, f"Net rating edge: {pick_team} {abs(net_diff):.1f}pts better per 100 possessions"))
                elif net_diff > 0:
                    candidates.append(('net_rating', 2, f"Net rating slightly favors {pick_team} ({abs(net_diff):.1f}pts)"))
                else:
                    candidates.append(('net_rating', 1, f"Net rating favors {opp_team} by {abs(net_diff):.1f}pts — spread accounts for this"))
            elif home_margin is not None and away_margin is not None:
                h_margin = float(home_margin)
                a_margin = float(away_margin)
                margin_diff = (h_margin - a_margin) if pick_home else (a_margin - h_margin)
                if margin_diff > 3:
                    candidates.append(('net_rating', 3, f"Scoring margin edge: {pick_team} outscores opponents by {abs(margin_diff):.1f}pts more per game"))
                elif margin_diff > 0:
                    candidates.append(('net_rating', 2, f"Scoring margin slightly favors {pick_team} ({abs(margin_diff):.1f}pts better)"))
                else:
                    candidates.append(('net_rating', 1, f"Scoring margin favors {opp_team} by {abs(margin_diff):.1f}pts — spread accounts for this"))
            else:
                candidates.append(('net_rating', 0, f"Rating data unavailable"))
        except (ValueError, TypeError):
            candidates.append(('net_rating', 0, f"Rating data unavailable"))
        
        home_pace = row.get('home_pace', None)
        away_pace = row.get('away_pace', None)
        home_avg_pts = row.get('bdl_home_avg_pts', None)
        away_avg_pts = row.get('bdl_away_avg_pts', None)
        home_avg_against = row.get('bdl_home_avg_pts_against', None)
        away_avg_against = row.get('bdl_away_avg_pts_against', None)
        try:
            if home_pace is not None and away_pace is not None:
                h_pace = float(home_pace)
                a_pace = float(away_pace)
                pace_diff = abs(h_pace - a_pace)
                if home_margin is not None and away_margin is not None:
                    h_margin = float(home_margin)
                    a_margin = float(away_margin)
                    margin_diff = (h_margin - a_margin) if pick_home else (a_margin - h_margin)
                    if margin_diff > 3:
                        candidates.append(('matchup', 3, f"Scoring margin: {pick_team} {abs(margin_diff):.1f}pts better, combined pace {(h_pace+a_pace)/2:.1f}"))
                    else:
                        candidates.append(('matchup', 1, f"Combined pace {(h_pace+a_pace)/2:.1f}, scoring margins close"))
                elif pace_diff > 3:
                    candidates.append(('matchup', 2, f"Pace mismatch: {h_pace:.1f} vs {a_pace:.1f} possessions per game"))
                else:
                    candidates.append(('matchup', 1, f"Pace similar ({(h_pace+a_pace)/2:.1f}), neutral matchup factor"))
            elif home_avg_against is not None and away_avg_against is not None:
                h_against = float(home_avg_against)
                a_against = float(away_avg_against)
                if pick_home:
                    def_diff = a_against - h_against
                else:
                    def_diff = h_against - a_against
                if def_diff > 3:
                    opp_against = a_against if pick_home else h_against
                    candidates.append(('matchup', 3, f"Defensive mismatch: {opp_team} allows {opp_against:.1f}pts/game"))
                elif home_avg_pts is not None and away_avg_pts is not None:
                    h_pts = float(home_avg_pts)
                    a_pts = float(away_avg_pts)
                    pick_pts = h_pts if pick_home else a_pts
                    candidates.append(('matchup', 2, f"{pick_team} averaging {pick_pts:.1f}pts vs defense allowing {(a_against if pick_home else h_against):.1f}"))
                else:
                    candidates.append(('matchup', 1, f"Matchup data limited"))
            else:
                candidates.append(('matchup', 0, f"Matchup data unavailable"))
        except (ValueError, TypeError):
            candidates.append(('matchup', 0, f"Matchup data unavailable"))
        
        if open_spread is not None and spread is not None:
            move = spread - open_spread
            move_abs = abs(move)
            if move_abs < 0.5:
                candidates.append(('line_value', 2, f"Line stable since open ({spread:+.1f}), market agrees with number"))
            elif (pick_home and move < -0.5) or (not pick_home and move > 0.5):
                candidates.append(('line_value', 3, f"Line value: getting {move_abs:.1f}pts better number than open ({open_spread:+.1f} → {spread:+.1f})"))
            else:
                candidates.append(('line_value', 1, f"Line moved {move_abs:.1f}pts against since open — still playable at current edge"))
        else:
            implied = abs(STANDARD_ODDS) / (abs(STANDARD_ODDS) + 100) if STANDARD_ODDS < 0 else 100 / (STANDARD_ODDS + 100)
            candidates.append(('line_value', 2, f"Model confidence ({confidence:.0%}) exceeds market implied ({implied:.0%})"))
        
        candidates.sort(key=lambda x: x[1], reverse=True)
        
        seen_types = set()
        result = []
        for cat, score, text in candidates:
            if cat not in seen_types:
                seen_types.add(cat)
                result.append(text)
            if len(result) == 3:
                break
        
        while len(result) < 3:
            result.append(f"Edge {edge:+.1f}% exceeds {self.edge_threshold_pct}% threshold")
        
        return result[:3]
    
    def walk_forward_validate(self):
        """Walk-forward validation using margin GBR model with production filters.
        Train on past seasons, test on next. No future leakage.
        Reports: sigma, MAE, Brier, calibration buckets, filtered ROI."""
        print("\n" + "="*60)
        print("WALK-FORWARD VALIDATION (margin model + production filters)")
        print("="*60 + "\n")

        from performance_tracker import odds_to_implied_prob

        df = self.load_data()
        if len(df) < 100:
            print("Not enough data for walk-forward validation")
            return None

        df = df[df['spread_result'] != 'PUSH'].copy()
        df['game_date_parsed'] = pd.to_datetime(df['game_date'].str[:10], errors='coerce')
        df = df.dropna(subset=['game_date_parsed'])
        df['season'] = df['game_date_parsed'].apply(
            lambda d: d.year if d.month >= 10 else d.year - 1
        )

        if 'home_rest_days' not in df.columns or df['home_rest_days'].isna().sum() > len(df) * 0.5:
            team_last = {}
            computed_home_rest = []
            computed_away_rest = []
            for _, row in df.iterrows():
                d = row['game_date_parsed']
                h, a = row['home_team'], row['away_team']
                hr = (d - team_last[h]).days if h in team_last else 3
                ar = (d - team_last[a]).days if a in team_last else 3
                computed_home_rest.append(hr)
                computed_away_rest.append(ar)
                team_last[h] = d
                team_last[a] = d
            df['home_rest_days'] = computed_home_rest
            df['away_rest_days'] = computed_away_rest

        margin_target = (df['home_score'] - df['away_score']).astype(float)

        seasons = sorted(df['season'].unique())
        if len(seasons) < 2:
            print("Need at least 2 seasons for walk-forward validation")
            return None

        results = []
        all_bets = []

        for i in range(1, len(seasons)):
            train_seasons = seasons[:i]
            test_season = seasons[i]

            train_mask = df['season'].isin(train_seasons)
            test_mask = df['season'] == test_season

            train_df = df[train_mask]
            test_df = df[test_mask]

            if len(train_df) < 50 or len(test_df) < 20:
                continue

            X_train = self.engineer_features(train_df).fillna(0)
            X_test = self.engineer_features(test_df).fillna(0)
            y_train = self.prepare_target(train_df)
            y_test = self.prepare_target(test_df)

            margin_train = margin_target[train_mask]
            margin_test = margin_target[test_mask]

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
            sigma = min(max(sigma_raw, self.margin_std_floor), self.margin_std_ceiling)
            mae = np.mean(np.abs(residuals))

            spreads = test_df['spread_home'].values
            open_spreads = test_df['spread_home_open'].values if 'spread_home_open' in test_df.columns else [None] * len(test_df)
            actual_margins = margin_test.values
            actual_covers = y_test.values

            home_rest_vals = test_df['home_rest_days'].values if 'home_rest_days' in test_df.columns else [None] * len(test_df)
            away_rest_vals = test_df['away_rest_days'].values if 'away_rest_days' in test_df.columns else [None] * len(test_df)

            implied_prob = odds_to_implied_prob(STANDARD_ODDS)

            season_bets = []
            all_edges = []

            for j in range(len(test_df)):
                spread = spreads[j]
                pred_margin_raw = margin_preds[j]

                if spread is None or pd.isna(spread):
                    continue

                market_margin = -spread
                pred_margin = self.model_weight * pred_margin_raw + (1 - self.model_weight) * market_margin
                z_score = (pred_margin + spread) / sigma
                home_cover_prob = float(norm.cdf(z_score))

                if home_cover_prob >= 0.5:
                    pick_side = 'home'
                    confidence = home_cover_prob
                else:
                    pick_side = 'away'
                    confidence = 1 - home_cover_prob

                raw_edge = min((confidence - implied_prob) * 100, self.max_edge_pct)

                line_move_against = 0.0
                open_spread = open_spreads[j] if j < len(open_spreads) else None
                if open_spread is not None and not pd.isna(open_spread):
                    move = spread - open_spread
                    if pick_side == 'home':
                        adverse_move = -move
                    else:
                        adverse_move = move
                    if adverse_move >= 1.0:
                        line_move_against = adverse_move

                adjusted_edge = raw_edge
                if line_move_against >= 1.0:
                    wf_r_std = test_df['rundown_spread_std'].iloc[j] if 'rundown_spread_std' in test_df.columns else None
                    wf_r_num = test_df['rundown_num_books'].iloc[j] if 'rundown_num_books' in test_df.columns else None
                    try:
                        wf_r_std = float(wf_r_std) if wf_r_std is not None and not pd.isna(wf_r_std) else None
                        wf_r_num = int(wf_r_num) if wf_r_num is not None and not pd.isna(wf_r_num) else None
                    except (ValueError, TypeError):
                        wf_r_std, wf_r_num = None, None
                    adjusted_edge, _, _, _ = apply_steam_fragility(
                        raw_edge, line_move_against, abs(spread), wf_r_std, wf_r_num
                    )
                adjusted_edge = min(adjusted_edge, self.max_edge_pct)

                spread_abs = abs(spread)

                is_fav = (pick_side == 'home' and spread < 0) or (pick_side == 'away' and spread > 0)
                if is_fav:
                    h_rest = int(home_rest_vals[j]) if j < len(home_rest_vals) and home_rest_vals[j] is not None and not pd.isna(home_rest_vals[j]) else None
                    a_rest = int(away_rest_vals[j]) if j < len(away_rest_vals) and away_rest_vals[j] is not None and not pd.isna(away_rest_vals[j]) else None

                    game_dt = test_df.iloc[j].get('game_date_parsed', None) if hasattr(test_df.iloc[j], 'get') else test_df['game_date_parsed'].iloc[j] if 'game_date_parsed' in test_df.columns else None

                    asb_pen, _ = calculate_asb_penalty(spread_abs, game_dt)
                    if asb_pen > 0:
                        adjusted_edge -= asb_pen
                    else:
                        rest_pen, _ = calculate_long_rest_penalty(pick_side, spread_abs, h_rest, a_rest)
                        if rest_pen > 0:
                            adjusted_edge -= rest_pen

                risk_weighted = spread_risk_adjusted_edge(adjusted_edge, spread_abs)
                all_edges.append(risk_weighted)

                if line_move_against >= LINE_MOVE_HARD_STOP and adjusted_edge < LINE_MOVE_HARD_STOP_MIN_EDGE:
                    continue

                required_edge = get_edge_threshold_for_spread(spread_abs)
                if risk_weighted < required_edge:
                    continue
                if confidence < MIN_CONFIDENCE_THRESHOLD:
                    continue

                actual_margin = actual_margins[j]
                covered = actual_covers[j]
                if pick_side == 'away':
                    covered = 1 - covered

                won = bool(covered)
                profit = 0.9091 if won else -1.0

                season_bets.append({
                    'won': won,
                    'profit': profit,
                    'edge': adjusted_edge,
                    'confidence': confidence,
                    'sigma': sigma,
                    'z_score': z_score if pick_side == 'home' else -z_score,
                    'pred_margin': pred_margin,
                    'spread': spread,
                })

            all_bets.extend(season_bets)

            n_bets = len(season_bets)
            wins = sum(1 for b in season_bets if b['won'])
            total_profit = sum(b['profit'] for b in season_bets)
            roi = (total_profit / n_bets * 100) if n_bets > 0 else 0
            win_rate = (wins / n_bets * 100) if n_bets > 0 else 0

            edge_arr = np.array(all_edges)
            cal_buckets = []
            for low, high in [(3.5, 5.0), (5.0, 7.0), (7.0, 10.0), (10.0, 100.0)]:
                mask = (edge_arr >= low) & (edge_arr < high)
                cal_buckets.append(f"{low:.0f}-{high:.0f}%: {mask.sum()}")

            season_label = f"{test_season}-{test_season+1}"
            results.append({
                'season': season_label,
                'train_games': len(train_df),
                'test_games': len(test_df),
                'sigma': sigma,
                'sigma_raw': sigma_raw,
                'mae': mae,
                'n_bets': n_bets,
                'wins': wins,
                'win_rate': win_rate,
                'roi': roi,
                'total_profit': total_profit,
                'edge_distribution': cal_buckets,
            })

            print(f"   {season_label}:")
            print(f"     Games: {len(test_df)} | Sigma: {sigma:.1f} (raw {sigma_raw:.1f}) | MAE: {mae:.1f} pts")
            print(f"     Filtered bets: {n_bets} | W-L: {wins}-{n_bets-wins} | Win%: {win_rate:.1f}% | ROI: {roi:+.1f}%")
            print(f"     Edge dist: {', '.join(cal_buckets)}")
            print()

        if results:
            total_bets = sum(r['n_bets'] for r in results)
            total_wins = sum(r['wins'] for r in results)
            total_profit = sum(r['total_profit'] for r in results)
            overall_roi = (total_profit / total_bets * 100) if total_bets > 0 else 0
            overall_wr = (total_wins / total_bets * 100) if total_bets > 0 else 0
            avg_sigma = np.mean([r['sigma'] for r in results])
            avg_mae = np.mean([r['mae'] for r in results])

            print("=" * 60)
            print(f"   OVERALL WALK-FORWARD RESULTS")
            print(f"   Seasons: {len(results)} | Total bets: {total_bets}")
            print(f"   Record: {total_wins}-{total_bets-total_wins} ({overall_wr:.1f}%)")
            print(f"   Total profit: {total_profit:+.1f}u | ROI: {overall_roi:+.1f}%")
            print(f"   Avg sigma: {avg_sigma:.1f} | Avg MAE: {avg_mae:.1f}")
            print("=" * 60)

            if overall_roi > 14:
                print("\n   WARNING: ROI > 14% — check for leakage")
            elif overall_roi > 8:
                print(f"\n   NOTE: ROI {overall_roi:+.1f}% is strong — monitor for regression")
            elif overall_roi > 0:
                print(f"\n   OK: ROI {overall_roi:+.1f}% is realistic for filtered ATS")

        return {'seasons': results, 'all_bets': all_bets}

    def calibration_check(self, bets=None):
        """Bucket predictions by confidence and check actual win rates.
        Uses walk-forward bets if available, otherwise runs walk-forward first."""
        if bets is None:
            print("Running walk-forward to collect bets for calibration...")
            result = self.walk_forward_validate()
            if result is None:
                return None
            bets = result['all_bets']

        print("\n" + "="*60)
        print("CALIBRATION CHECK — confidence vs actual win rate")
        print("="*60)

        from performance_tracker import odds_to_implied_prob
        implied = odds_to_implied_prob(STANDARD_ODDS)

        buckets = [
            (0.50, 0.55),
            (0.55, 0.60),
            (0.60, 0.65),
            (0.65, 0.70),
            (0.70, 1.00),
        ]

        print(f"\n{'Confidence':<14} {'N':>6} {'Win%':>7} {'AvgConf':>8} {'AvgEdge':>8} {'Brier':>7} {'Status':>10}")
        print("-" * 70)

        results = []
        for lo, hi in buckets:
            bucket_bets = [b for b in bets if lo <= b['confidence'] < hi]
            if not bucket_bets:
                print(f"  {lo:.0%}-{hi:.0%}      {'(no bets)':>6}")
                continue

            n = len(bucket_bets)
            wins = sum(1 for b in bucket_bets if b['won'])
            actual_wr = wins / n
            avg_conf = np.mean([b['confidence'] for b in bucket_bets])
            avg_edge = np.mean([b['edge'] for b in bucket_bets])
            brier = np.mean([(b['confidence'] - (1.0 if b['won'] else 0.0))**2 for b in bucket_bets])

            cal_diff = abs(actual_wr - avg_conf)
            if cal_diff < 0.03:
                status = "CALIBRATED"
            elif actual_wr > avg_conf:
                status = "UNDERCONF"
            else:
                status = "OVERCONF"

            results.append({
                'range': f"{lo:.0%}-{hi:.0%}",
                'n': n, 'win_rate': actual_wr, 'avg_conf': avg_conf,
                'avg_edge': avg_edge, 'brier': brier, 'status': status,
            })

            print(f"  {lo:.0%}-{hi:.0%}     {n:>6} {actual_wr:>6.1%} {avg_conf:>7.1%} {avg_edge:>+7.1f}% {brier:>6.3f} {status:>10}")

        print("-" * 70)

        overall_brier = np.mean([(b['confidence'] - (1.0 if b['won'] else 0.0))**2 for b in bets])
        print(f"  Overall Brier: {overall_brier:.3f}")

        overconf_buckets = [r for r in results if r['status'] == 'OVERCONF']
        if overconf_buckets:
            print(f"\n  WARNING: {len(overconf_buckets)} bucket(s) overconfident — model may need recalibration")
        else:
            print(f"\n  OK: No overconfident buckets detected")

        return results

    def backtest_sweep(self, edge_range=None, conf_range=None, penalty_range=None):
        """Sweep edge threshold, min_confidence, and line move penalty.
        Returns optimal combo for ROI with acceptable pick frequency."""

        print("\n" + "="*60)
        print("BACKTEST PARAMETER SWEEP")
        print("="*60)

        from performance_tracker import odds_to_implied_prob

        if edge_range is None:
            edge_range = np.arange(2.0, 10.5, 0.5)
        if conf_range is None:
            conf_range = np.arange(0.52, 0.61, 0.01)
        if penalty_range is None:
            penalty_range = [0.0, 0.5, 1.0, 1.5, 2.0]

        df = self.load_data()
        df = df[df['spread_result'] != 'PUSH'].copy()
        df['game_date_parsed'] = pd.to_datetime(df['game_date'].str[:10], errors='coerce')
        df = df.dropna(subset=['game_date_parsed'])
        df['season'] = df['game_date_parsed'].apply(lambda d: d.year if d.month >= 10 else d.year - 1)

        margin_target = (df['home_score'] - df['away_score']).astype(float)
        seasons = sorted(df['season'].unique())

        print(f"  Building walk-forward predictions for {len(seasons)-1} test seasons...")

        all_game_data = []

        for i in range(1, len(seasons)):
            train_seasons = seasons[:i]
            test_season = seasons[i]
            train_mask = df['season'].isin(train_seasons)
            test_mask = df['season'] == test_season
            train_df = df[train_mask]
            test_df = df[test_mask]

            if len(train_df) < 50 or len(test_df) < 20:
                continue

            X_train = self.engineer_features(train_df).fillna(0)
            X_test = self.engineer_features(test_df).fillna(0)
            y_test = self.prepare_target(test_df)
            margin_train = margin_target[train_mask]
            margin_test = margin_target[test_mask]

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
            sigma = min(max(np.std(residuals), self.margin_std_floor), self.margin_std_ceiling)

            spreads = pd.to_numeric(test_df['spread_home'], errors='coerce').values
            open_spreads = pd.to_numeric(test_df['spread_home_open'], errors='coerce').values if 'spread_home_open' in test_df.columns else np.full(len(test_df), np.nan)
            actual_covers = y_test.values
            dates = test_df['game_date_parsed'].values

            implied_prob = odds_to_implied_prob(STANDARD_ODDS)

            for j in range(len(test_df)):
                spread = spreads[j]
                if pd.isna(spread):
                    continue
                pred_margin_raw = margin_preds[j]
                market_margin = -spread
                pred_margin = self.model_weight * pred_margin_raw + (1 - self.model_weight) * market_margin
                z_score = (pred_margin + spread) / sigma
                home_cover_prob = float(norm.cdf(z_score))

                if home_cover_prob >= 0.5:
                    pick_side = 'home'
                    confidence = home_cover_prob
                else:
                    pick_side = 'away'
                    confidence = 1 - home_cover_prob

                raw_edge = min((confidence - implied_prob) * 100, self.max_edge_pct)

                open_spread = open_spreads[j]
                line_move = 0.0
                if not pd.isna(open_spread):
                    move = spread - open_spread
                    if move > 0 and move >= 1.0:
                        line_move = move

                covered = actual_covers[j]
                if pick_side == 'away':
                    covered = 1 - covered
                won = bool(covered)

                all_game_data.append({
                    'confidence': confidence,
                    'raw_edge': raw_edge,
                    'line_move': line_move,
                    'spread_abs': abs(spread),
                    'won': won,
                    'season': test_season,
                    'date': dates[j],
                })

        print(f"  Total game predictions: {len(all_game_data)}")

        print(f"\n  Sweeping {len(penalty_range)} penalties x {len(edge_range)} edges x {len(conf_range)} confs...")

        best = None
        sweep_results = []
        weeks_per_season = 26

        for penalty in penalty_range:
            for edge_thresh in edge_range:
                for min_conf in conf_range:
                    wins = 0
                    losses = 0
                    total_profit = 0
                    season_profits = {}
                    cumulative = [0]

                    for g in all_game_data:
                        adj_edge = g['raw_edge'] - (g['line_move'] * penalty)

                        if g['line_move'] >= LINE_MOVE_HARD_STOP and adj_edge < LINE_MOVE_HARD_STOP_MIN_EDGE:
                            continue

                        req_edge = get_edge_threshold_for_spread(g['spread_abs'])
                        actual_req = max(edge_thresh, req_edge) if g['spread_abs'] >= 7 else edge_thresh

                        if g['confidence'] < min_conf:
                            continue
                        if adj_edge < actual_req:
                            continue

                        profit = 0.9091 if g['won'] else -1.0
                        total_profit += profit
                        cumulative.append(cumulative[-1] + profit)

                        if g['won']:
                            wins += 1
                        else:
                            losses += 1

                        s = g['season']
                        if s not in season_profits:
                            season_profits[s] = 0
                        season_profits[s] += profit

                    total_bets = wins + losses
                    if total_bets < 50:
                        continue

                    roi = total_profit / total_bets * 100
                    win_rate = wins / total_bets * 100
                    picks_per_week = total_bets / (len(season_profits) * weeks_per_season)
                    max_dd = min(cumulative) - max(cumulative[:cumulative.index(min(cumulative))+1]) if len(cumulative) > 1 else 0
                    peak = 0
                    dd = 0
                    for v in cumulative:
                        if v > peak:
                            peak = v
                        if v - peak < dd:
                            dd = v - peak
                    max_dd = dd

                    season_rois = [v / max(1, total_bets // len(season_profits)) * 100 for v in season_profits.values()]
                    stability = np.std(season_rois) if len(season_rois) > 1 else 0

                    result = {
                        'edge': edge_thresh, 'conf': min_conf, 'penalty': penalty,
                        'bets': total_bets, 'wins': wins, 'win_rate': win_rate,
                        'roi': roi, 'profit': total_profit, 'picks_per_week': picks_per_week,
                        'max_drawdown': max_dd, 'stability': stability,
                        'profitable_seasons': sum(1 for v in season_profits.values() if v > 0),
                        'total_seasons': len(season_profits),
                    }
                    sweep_results.append(result)

                    if best is None or (roi > best['roi'] and picks_per_week <= 4):
                        best = result

        sweep_results.sort(key=lambda x: x['roi'], reverse=True)

        print(f"\n  Total valid combos: {len(sweep_results)}")

        brand_matches = [r for r in sweep_results if 0.5 <= r['picks_per_week'] <= 3.0 and r['roi'] > 0]
        brand_matches.sort(key=lambda x: x['roi'], reverse=True)

        print(f"\n{'='*90}")
        print(f"TOP 10 COMBOS (ROI-optimized)")
        print(f"{'='*90}")
        print(f"{'Edge':>6} {'Conf':>6} {'Pen':>5} {'Bets':>6} {'Win%':>6} {'ROI':>7} {'P/wk':>5} {'MaxDD':>7} {'ProfSzn':>8}")
        print("-" * 90)
        for r in sweep_results[:10]:
            print(f"{r['edge']:>5.1f}% {r['conf']:>5.0%} {r['penalty']:>5.1f} {r['bets']:>6} {r['win_rate']:>5.1f}% {r['roi']:>+6.1f}% {r['picks_per_week']:>4.1f} {r['max_drawdown']:>+6.1f}u {r['profitable_seasons']:>3}/{r['total_seasons']}")

        if brand_matches:
            print(f"\n{'='*90}")
            print(f"TOP 10 BRAND-FIT COMBOS (1-3 picks/week, ROI > 0)")
            print(f"{'='*90}")
            print(f"{'Edge':>6} {'Conf':>6} {'Pen':>5} {'Bets':>6} {'Win%':>6} {'ROI':>7} {'P/wk':>5} {'MaxDD':>7} {'ProfSzn':>8}")
            print("-" * 90)
            for r in brand_matches[:10]:
                print(f"{r['edge']:>5.1f}% {r['conf']:>5.0%} {r['penalty']:>5.1f} {r['bets']:>6} {r['win_rate']:>5.1f}% {r['roi']:>+6.1f}% {r['picks_per_week']:>4.1f} {r['max_drawdown']:>+6.1f}u {r['profitable_seasons']:>3}/{r['total_seasons']}")

        print(f"\nLine move penalty sweep (at best edge/conf):")
        if best:
            be, bc = best['edge'], best['conf']
            for pen in penalty_range:
                pen_results = [r for r in sweep_results if r['edge'] == be and r['conf'] == bc and r['penalty'] == pen]
                if pen_results:
                    r = pen_results[0]
                    print(f"  penalty={pen:.1f}: bets={r['bets']}, ROI={r['roi']:+.1f}%, picks/wk={r['picks_per_week']:.1f}")

        return {'all_results': sweep_results, 'brand_matches': brand_matches, 'best': best}

    def _default_filepath(self):
        return f'sharp_picks_{"wnba_" if self.sport == "wnba" else ""}model.pkl'

    def save(self, filepath=None):
        """Save the trained model"""
        if filepath is None:
            filepath = self._default_filepath()
        model_data = {
            'models': self.models,
            'base_models': self.base_models,
            'scaler': self.scaler,
            'feature_names': self.feature_names,
            'trained': self.trained,
            'calibration_stats': self.calibration_stats,
            'margin_model': self.margin_model,
            'margin_std': getattr(self, 'margin_std', None),
            'margin_mae': getattr(self, 'margin_mae', None),
            'using_fallback_sigma': getattr(self, 'using_fallback_sigma', None),
        }
        
        with open(filepath, 'wb') as f:
            pickle.dump(model_data, f)
    
    def load_model(self, filepath=None):
        """Load a saved model"""
        if filepath is None:
            filepath = self._default_filepath()
        if not os.path.exists(filepath):
            return False
        
        try:
            with open(filepath, 'rb') as f:
                model_data = pickle.load(f)
            
            self.models = model_data['models']
            self.base_models = model_data.get('base_models', self.base_models)
            self.scaler = model_data['scaler']
            self.feature_names = model_data['feature_names']
            self.trained = model_data['trained']
            self.calibration_stats = model_data.get('calibration_stats', {})
            self.margin_model = model_data.get('margin_model', None)
            saved_std = model_data.get('margin_std', None)
            self.margin_std = min(max(saved_std, self.margin_std_floor), self.margin_std_ceiling) if saved_std is not None else None
            self.margin_mae = model_data.get('margin_mae', None)
            self.using_fallback_sigma = model_data.get('using_fallback_sigma', None)
            
            return True
        except:
            return False
    
    def show_feature_importance(self):
        """Display feature importance from the models"""
        if not self.trained:
            print("❌ Model not trained yet.\n")
            return
        
        print("\n📊 FEATURE IMPORTANCE (Random Forest):")
        print("-" * 40)
        
        rf_calibrated = self.models['random_forest']
        rf_base = rf_calibrated.calibrated_classifiers_[0].estimator
        
        importance = pd.DataFrame({
            'feature': self.feature_names,
            'importance': rf_base.feature_importances_
        }).sort_values('importance', ascending=False)
        
        for _, row in importance.head(10).iterrows():
            bar = "█" * int(row['importance'] * 50)
            print(f"   {row['feature']:<20} {bar} {row['importance']:.3f}")
        
        print()
    
    def show_calibration(self):
        """Display calibration statistics"""
        if not self.trained:
            print("❌ Model not trained yet.\n")
            return
        
        if not self.calibration_stats:
            print("ℹ️  No calibration stats available. Retrain the model.\n")
            return
        
        print("\n📊 PROBABILITY CALIBRATION:")
        print("-" * 50)
        print("How well do predicted probabilities match actual outcomes?\n")
        
        prob_true = self.calibration_stats.get('prob_true', [])
        prob_pred = self.calibration_stats.get('prob_pred', [])
        
        print(f"{'Predicted':>12} {'Actual':>12} {'Status':>12}")
        print("-" * 40)
        
        for pred, true in zip(prob_pred, prob_true):
            diff = abs(pred - true)
            if diff < 0.05:
                status = "✅ Perfect"
            elif diff < 0.10:
                status = "👍 Good"
            else:
                status = "⚠️ Off"
            print(f"{pred:>12.1%} {true:>12.1%} {status:>12}")
        
        if prob_pred and prob_true:
            cal_error = np.mean([abs(p - t) for p, t in zip(prob_pred, prob_true)])
            print("-" * 40)
            print(f"\nMean Calibration Error: {cal_error:.1%}")
            print("\nInterpretation: When model says 60% confidence,")
            print(f"actual win rate should be ~60%. Current error: {cal_error:.1%}")
        
        print()


def main():
    """Main function for model operations"""
    import sys
    
    sport = 'nba'
    args = list(sys.argv[1:])
    if '--sport' in args:
        idx = args.index('--sport')
        if idx + 1 < len(args):
            sport = args[idx + 1].lower()
            args = args[:idx] + args[idx + 2:]
        else:
            print("Error: --sport requires a value (nba or wnba)")
            return

    predictor = EnsemblePredictor(sport=sport)
    print(f"   Sport: {sport.upper()}")
    
    if len(args) > 0:
        cmd = args[0]
        
        if cmd == 'train':
            predictor.train()
        elif cmd == 'predict':
            predictor.predict_games()
        elif cmd == 'validate':
            result = predictor.walk_forward_validate()
            if result:
                predictor.calibration_check(result['all_bets'])
        elif cmd == 'sweep':
            predictor.backtest_sweep()
        elif cmd == 'calibration':
            predictor.calibration_check()
        elif cmd == 'importance':
            predictor.load_model()
            predictor.show_feature_importance()
        else:
            print(f"Unknown command: {cmd}")
            print_usage()
    else:
        print_usage()


def print_usage():
    print("\n🏀 SHARP PICKS MODEL (Calibrated Ensemble)")
    print("="*50)
    print("\nCommands:")
    print("   python model.py train       - Train the calibrated ensemble")
    print("   python model.py predict     - Get predictions for today")
    print("   python model.py validate    - Walk-forward + calibration check")
    print("   python model.py sweep       - Backtest parameter sweep")
    print("   python model.py calibration - Confidence calibration check")
    print("   python model.py importance  - Show feature importance")
    print("\nOptions:")
    print("   --sport nba|wnba            - Select sport (default: nba)")
    print("\nExamples:")
    print("   python model.py train --sport wnba")
    print("   python model.py predict --sport wnba")
    print()


if __name__ == "__main__":
    main()
