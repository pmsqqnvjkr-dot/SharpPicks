"""
🏀 SHARP PICKS - ENSEMBLE PREDICTION MODEL
Uses multiple ML models to predict NBA spread outcomes
Enhanced with pace/ratings features, sample weighting, and betting filters
"""

import sqlite3
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import pickle
import os

from scipy.stats import norm
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
MAX_SPREAD_DEFAULT = 11.0
LINE_MOVE_PENALTY_PER_PT = 1.5


class EnsemblePredictor:
    """Ensemble model combining multiple ML algorithms with probability calibration"""
    
    def __init__(self):
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
    
    def load_data(self):
        """Load training data from database with team ratings"""
        conn = sqlite3.connect('sharp_picks.db')
        
        query = '''
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
                g.spread_result, g.home_score, g.away_score,
                hr.pace as home_pace, hr.off_rating as home_off_rtg, 
                hr.def_rating as home_def_rtg, hr.net_rating as home_net_rtg,
                ar.pace as away_pace, ar.off_rating as away_off_rtg,
                ar.def_rating as away_def_rtg, ar.net_rating as away_net_rtg,
                g.rundown_spread_consensus, g.rundown_spread_std,
                g.rundown_spread_range, g.rundown_num_books,
                g.bdl_home_win_pct, g.bdl_away_win_pct,
                g.bdl_home_conf_rank, g.bdl_away_conf_rank,
                g.bdl_home_scoring_margin, g.bdl_away_scoring_margin,
                g.bdl_home_avg_pts, g.bdl_away_avg_pts,
                g.bdl_home_avg_pts_against, g.bdl_away_avg_pts_against
            FROM games g
            LEFT JOIN team_ratings hr ON g.home_team = hr.team_abbr
            LEFT JOIN team_ratings ar ON g.away_team = ar.team_abbr
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
        self.margin_std = min(max(cv_std_raw, MARGIN_STD_FLOOR), MARGIN_STD_CEILING)
        print(f"   Margin MAE: {margin_mae:.1f} pts")
        print(f"   CV residual std: {cv_std_raw:.1f} pts (clamped [{MARGIN_STD_FLOOR}, {MARGIN_STD_CEILING}], using {self.margin_std:.1f})")
        
        self.trained = True
        
        self.save()
        
        print(f"\n   Calibrated model trained and saved!")
        print(f"   Ensemble Test Accuracy: {ensemble_acc:.1%}")
        print(f"   Brier Score: {ensemble_brier:.3f} (lower is better)")
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
    
    def predict_games(self, min_confidence=None, log_predictions=True):
        """Make predictions for today's upcoming games with filtering"""
        print("\n" + "="*60)
        print("🎯 TODAY'S PREDICTIONS")
        print("="*60 + "\n")
        
        if min_confidence is None:
            min_confidence = MIN_CONFIDENCE_THRESHOLD
        
        if not self.trained:
            self.load_model()
            if not self.trained:
                print("❌ No trained model found. Run training first.\n")
                return []
        
        conn = sqlite3.connect('sharp_picks.db')
        
        query = '''
            SELECT 
                g.id, g.home_team, g.away_team, g.game_date, g.game_time,
                g.spread_home, g.spread_home_open, g.spread_home_close,
                g.total, g.total_open, g.total_close,
                g.home_ml, g.away_ml,
                g.home_record, g.away_record,
                g.home_home_record, g.away_away_record,
                g.home_last5, g.away_last5,
                g.home_rest_days, g.away_rest_days,
                g.line_movement,
                hr.pace as home_pace, hr.off_rating as home_off_rtg,
                hr.def_rating as home_def_rtg, hr.net_rating as home_net_rtg,
                ar.pace as away_pace, ar.off_rating as away_off_rtg,
                ar.def_rating as away_def_rtg, ar.net_rating as away_net_rtg,
                g.rundown_spread_consensus, g.rundown_spread_std,
                g.rundown_spread_range, g.rundown_num_books,
                g.bdl_home_win_pct, g.bdl_away_win_pct,
                g.bdl_home_conf_rank, g.bdl_away_conf_rank,
                g.bdl_home_scoring_margin, g.bdl_away_scoring_margin,
                g.bdl_home_avg_pts, g.bdl_away_avg_pts,
                g.bdl_home_avg_pts_against, g.bdl_away_avg_pts_against
            FROM games g
            LEFT JOIN team_ratings hr ON g.home_team = hr.team_abbr
            LEFT JOIN team_ratings ar ON g.away_team = ar.team_abbr
            WHERE g.home_score IS NULL
            AND g.spread_home IS NOT NULL
        '''
        
        df = pd.read_sql_query(query, conn)
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
        sigma = MARGIN_STD_DEV
        if self.margin_model is not None:
            predicted_margins = self.margin_model.predict(X_scaled)
            sigma = getattr(self, 'margin_std', MARGIN_STD_DEV) or MARGIN_STD_DEV
        
        picks = []
        
        from performance_tracker import odds_to_implied_prob, calculate_ev
        
        for i, row in df.iterrows():
            idx = df.index.get_loc(i)
            
            home = row['home_team']
            away = row['away_team']
            spread = row['spread_home']
            proba = ensemble_proba[idx]
            
            market_odds = STANDARD_ODDS
            home_ml = row.get('home_ml', None)
            away_ml = row.get('away_ml', None)
            
            pred_margin = predicted_margins[idx] if predicted_margins is not None else None
            
            used_fallback = False
            if pred_margin is not None and spread is not None:
                home_cover_prob = float(norm.cdf((pred_margin + spread) / sigma))
            else:
                used_fallback = True
                home_cover_prob = proba
            
            if home_cover_prob >= 0.5:
                pick_side = 'home'
                pick_label = f"{home} {spread:+.1f}"
                confidence = home_cover_prob
            else:
                pick_side = 'away'
                pick_label = f"{away} {-spread:+.1f}"
                confidence = 1 - home_cover_prob
            
            implied_prob = odds_to_implied_prob(market_odds)
            edge_vs_market = (confidence - implied_prob) * 100
            ev = calculate_ev(confidence, market_odds)
            
            open_spread = row.get('spread_home_open', None)
            line_move_against = 0.0
            line_move_penalty = 0.0
            if open_spread is not None and spread is not None:
                move = spread - open_spread
                if pick_side == 'home' and move > 0:
                    line_move_against = move
                elif pick_side == 'away' and move > 0:
                    line_move_against = move
                
                if line_move_against >= 1.0:
                    line_move_penalty = line_move_against * LINE_MOVE_PENALTY_PER_PT
            
            adjusted_edge = edge_vs_market - line_move_penalty
            
            fail_reasons = []
            if spread is None:
                fail_reasons.append('missing_spread')
            if pred_margin is None and proba is None:
                fail_reasons.append('missing_prediction')
            if used_fallback:
                fail_reasons.append('no_margin_sigma_for_ats')
            
            spread_abs = abs(spread) if spread is not None else 0
            if spread_abs > MAX_SPREAD_DEFAULT and adjusted_edge < 8.0:
                fail_reasons.append(f'spread_too_large ({spread_abs:.1f})')
            
            home_injuries = row.get('home_injuries', None) if hasattr(row, 'get') else None
            away_injuries = row.get('away_injuries', None) if hasattr(row, 'get') else None

            explanation = self._generate_explanation(row, proba, confidence, adjusted_edge, pred_margin)
            
            if confidence >= STRONG_CONFIDENCE_THRESHOLD:
                rating = "STRONG"
            elif confidence >= MIN_CONFIDENCE_THRESHOLD:
                rating = "LEAN"
            else:
                rating = "SLIGHT"
            
            passes = (
                len(fail_reasons) == 0
                and confidence >= min_confidence
                and adjusted_edge >= EDGE_THRESHOLD_PCT
            )
            
            z_score_val = None
            if pred_margin is not None and spread is not None:
                z_score_val = (pred_margin + spread) / sigma
                if pick_side == 'away':
                    z_score_val = -z_score_val

            picks.append({
                'game_id': row['id'],
                'game_date': row['game_date'],
                'game': f"{away} @ {home}",
                'home_team': home,
                'away_team': away,
                'spread': spread,
                'pick': pick_label,
                'pick_side': pick_side,
                'predicted_margin': round(pred_margin, 1) if pred_margin is not None else None,
                'sigma': round(sigma, 2),
                'z_score': round(z_score_val, 3) if z_score_val is not None else None,
                'raw_edge': round(edge_vs_market, 2),
                'cover_prob': round(confidence, 4),
                'confidence': confidence,
                'edge': round(edge_vs_market, 2),
                'adjusted_edge': round(adjusted_edge, 2),
                'ev': ev,
                'implied_prob': round(implied_prob, 4),
                'market_odds': market_odds,
                'rating': rating,
                'home_proba': proba,
                'line_move_against': round(line_move_against, 1),
                'line_move_penalty': round(line_move_penalty, 1),
                'fail_reasons': fail_reasons,
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
            penalty_str = f" (-{pick['line_move_penalty']:.0f}%)" if pick['line_move_penalty'] > 0 else ""
            print(f"{game_str:<28} {pick['pick']:<16} {margin_str:>7} {pick['cover_prob']:>6.1%} {pick['edge']:>+5.1f}% {pick['adjusted_edge']:>+5.1f}% {pick['ev']:>+6.1f}% {pick['rating']:>8}{penalty_str}")
        
        print("-" * 100)
        
        failed = [p for p in picks if p['fail_reasons']]
        if failed:
            print(f"\n   {len(failed)} games hard-passed: {', '.join(set(r for p in failed for r in p['fail_reasons']))}")
        if excluded_count > 0:
            print(f"   {excluded_count} games excluded (below {EDGE_THRESHOLD_PCT}% adjusted edge)")
        
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
        
        qualified = [p for p in filtered_picks if p['adjusted_edge'] >= EDGE_THRESHOLD_PCT]
        if qualified:
            print(f"\n   QUALIFIED OPPORTUNITIES ({EDGE_THRESHOLD_PCT}%+ adjusted edge):")
            for pick in sorted(qualified, key=lambda x: x['adjusted_edge'], reverse=True):
                margin_str = f", margin: {pick['predicted_margin']:+.1f}" if pick['predicted_margin'] is not None else ""
                print(f"   {pick['rating']}: {pick['pick']} (edge: +{pick['adjusted_edge']:.1f}%{margin_str})")
                if pick['explanation']:
                    for reason in pick['explanation']:
                        print(f"      - {reason}")
        
        print()
        return filtered_picks
    
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
            h_rest = int(home_rest) if home_rest else 1
            a_rest = int(away_rest) if away_rest else 1
            rest_diff = (h_rest - a_rest) if pick_home else (a_rest - h_rest)
            if rest_diff > 0:
                candidates.append(('rest', 3, f"Rest advantage: {pick_team} on {max(h_rest,a_rest)}d rest vs {opp_team} {min(h_rest,a_rest)}d"))
            elif h_rest == 1 and a_rest == 1:
                candidates.append(('rest', 1, f"Both teams on 1 day rest — no rest edge"))
            else:
                candidates.append(('rest', 1, f"Rest neutral: {home} {h_rest}d, {away} {a_rest}d"))
        except (ValueError, TypeError):
            candidates.append(('rest', 0, f"Rest data unavailable"))
        
        home_net = row.get('home_net_rtg', None)
        away_net = row.get('away_net_rtg', None)
        try:
            h_net = float(home_net) if home_net is not None else 0
            a_net = float(away_net) if away_net is not None else 0
            net_diff = (h_net - a_net) if pick_home else (a_net - h_net)
            if net_diff > 3:
                candidates.append(('net_rating', 3, f"Net rating edge: {pick_team} {abs(net_diff):.1f}pts better per 100 possessions"))
            elif net_diff > 0:
                candidates.append(('net_rating', 2, f"Net rating slightly favors {pick_team} ({abs(net_diff):.1f}pts)"))
            else:
                candidates.append(('net_rating', 1, f"Net rating favors {opp_team} by {abs(net_diff):.1f}pts — spread accounts for this"))
        except (ValueError, TypeError):
            candidates.append(('net_rating', 0, f"Net rating data unavailable"))
        
        home_pace = row.get('home_pace', None)
        away_pace = row.get('away_pace', None)
        home_margin = row.get('bdl_home_scoring_margin', None)
        away_margin = row.get('bdl_away_scoring_margin', None)
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
            else:
                candidates.append(('matchup', 0, f"Pace/matchup data unavailable"))
        except (ValueError, TypeError):
            candidates.append(('matchup', 0, f"Pace/matchup data unavailable"))
        
        if open_spread is not None and spread is not None:
            move = spread - open_spread
            move_abs = abs(move)
            if pick_home and move < -0.5:
                candidates.append(('line_value', 3, f"Line value: getting {move_abs:.1f}pts better number than open ({open_spread:+.1f} → {spread:+.1f})"))
            elif not pick_home and move > 0.5:
                candidates.append(('line_value', 3, f"Line value: getting {move_abs:.1f}pts better number than open ({open_spread:+.1f} → {spread:+.1f})"))
            elif move_abs < 0.5:
                candidates.append(('line_value', 2, f"Line stable since open ({spread:+.1f}), market agrees with number"))
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
            result.append(f"Edge {edge:+.1f}% exceeds {EDGE_THRESHOLD_PCT}% threshold")
        
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
            sigma = min(max(sigma_raw, MARGIN_STD_FLOOR), MARGIN_STD_CEILING)
            mae = np.mean(np.abs(residuals))

            spreads = test_df['spread_home'].values
            open_spreads = test_df['spread_home_open'].values if 'spread_home_open' in test_df.columns else [None] * len(test_df)
            actual_margins = margin_test.values
            actual_covers = y_test.values

            implied_prob = odds_to_implied_prob(STANDARD_ODDS)

            season_bets = []
            all_edges = []

            for j in range(len(test_df)):
                spread = spreads[j]
                pred_margin = margin_preds[j]

                if spread is None or pd.isna(spread):
                    continue

                z_score = (pred_margin + spread) / sigma
                home_cover_prob = float(norm.cdf(z_score))

                if home_cover_prob >= 0.5:
                    pick_side = 'home'
                    confidence = home_cover_prob
                else:
                    pick_side = 'away'
                    confidence = 1 - home_cover_prob

                raw_edge = (confidence - implied_prob) * 100

                line_move_penalty = 0.0
                open_spread = open_spreads[j] if j < len(open_spreads) else None
                if open_spread is not None and not pd.isna(open_spread):
                    move = spread - open_spread
                    if move > 0 and move >= 1.0:
                        line_move_penalty = move * LINE_MOVE_PENALTY_PER_PT

                adjusted_edge = raw_edge - line_move_penalty
                all_edges.append(adjusted_edge)

                spread_abs = abs(spread)
                if spread_abs > MAX_SPREAD_DEFAULT and adjusted_edge < 8.0:
                    continue
                if adjusted_edge < EDGE_THRESHOLD_PCT:
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

    def save(self, filepath='sharp_picks_model.pkl'):
        """Save the trained model"""
        model_data = {
            'models': self.models,
            'base_models': self.base_models,
            'scaler': self.scaler,
            'feature_names': self.feature_names,
            'trained': self.trained,
            'calibration_stats': self.calibration_stats,
            'margin_model': self.margin_model,
            'margin_std': getattr(self, 'margin_std', None),
        }
        
        with open(filepath, 'wb') as f:
            pickle.dump(model_data, f)
    
    def load_model(self, filepath='sharp_picks_model.pkl'):
        """Load a saved model"""
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
            self.margin_std = min(max(saved_std, MARGIN_STD_FLOOR), MARGIN_STD_CEILING) if saved_std is not None else None
            
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
    
    predictor = EnsemblePredictor()
    
    if len(sys.argv) > 1:
        cmd = sys.argv[1]
        
        if cmd == 'train':
            predictor.train()
        elif cmd == 'predict':
            predictor.predict_games()
        elif cmd == 'importance':
            predictor.load_model()
            predictor.show_feature_importance()
        elif cmd == 'calibration':
            predictor.load_model()
            predictor.show_calibration()
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
    print("   python model.py importance  - Show feature importance")
    print("   python model.py calibration - Show probability calibration")
    print()
    print("Calibration ensures that when the model says")
    print("60% confidence, it actually wins ~60% of the time.")
    print()


if __name__ == "__main__":
    main()
