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

from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier, AdaBoostClassifier
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.preprocessing import StandardScaler
from sklearn.calibration import CalibratedClassifierCV, calibration_curve
from sklearn.metrics import accuracy_score, classification_report, brier_score_loss
import xgboost as xgb

MIN_CONFIDENCE_THRESHOLD = 0.55
STRONG_CONFIDENCE_THRESHOLD = 0.60
EDGE_THRESHOLD_PCT = 3.5
STANDARD_ODDS = -110


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
        
        self.feature_names = X.columns.tolist()
        print(f"   📋 Using {len(self.feature_names)} features\n")
        
        indices = np.arange(len(X))
        train_idx, test_idx = train_test_split(indices, test_size=0.2, random_state=42)
        
        X_train, X_test = X.iloc[train_idx], X.iloc[test_idx]
        y_train, y_test = y.iloc[train_idx], y.iloc[test_idx]
        weights_train = sample_weights[train_idx]
        
        # Scale features
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
        
        self.trained = True
        
        # Save model
        self.save()
        
        print(f"\n✅ Calibrated model trained and saved!")
        print(f"   Ensemble Test Accuracy: {ensemble_acc:.1%}")
        print(f"   Brier Score: {ensemble_brier:.3f} (lower is better)\n")
        
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
        
        picks = []
        
        from performance_tracker import odds_to_implied_prob, calculate_ev
        implied_prob = odds_to_implied_prob(STANDARD_ODDS)
        
        for i, row in df.iterrows():
            idx = df.index.get_loc(i)
            
            home = row['home_team']
            away = row['away_team']
            spread = row['spread_home']
            proba = ensemble_proba[idx]
            
            if proba >= 0.5:
                pick = f"{home} {spread:+.1f}"
                confidence = proba
            else:
                pick = f"{away} {-spread:+.1f}"
                confidence = 1 - proba
            
            edge_vs_market = round((confidence - implied_prob) * 100, 2)
            ev = calculate_ev(confidence, STANDARD_ODDS)
            
            line_move = row.get('line_movement', 0) or 0
            open_spread = row.get('spread_home_open', None)
            line_moved_against = False
            if open_spread is not None and spread is not None:
                move = spread - open_spread
                if proba >= 0.5 and move > 2:
                    line_moved_against = True
                elif proba < 0.5 and move < -2:
                    line_moved_against = True

            explanation = self._generate_explanation(row, proba, confidence, edge_vs_market)
            
            if confidence >= STRONG_CONFIDENCE_THRESHOLD:
                rating = "STRONG"
            elif confidence >= MIN_CONFIDENCE_THRESHOLD:
                rating = "LEAN"
            else:
                rating = "SLIGHT"
            
            picks.append({
                'game_id': row['id'],
                'game_date': row['game_date'],
                'game': f"{away} @ {home}",
                'home_team': home,
                'away_team': away,
                'spread': spread,
                'pick': pick,
                'confidence': confidence,
                'edge': edge_vs_market,
                'ev': ev,
                'implied_prob': implied_prob,
                'rating': rating,
                'home_proba': proba,
                'line_moved_against': line_moved_against,
                'explanation': explanation,
                'passes_filter': confidence >= min_confidence and edge_vs_market >= EDGE_THRESHOLD_PCT and not line_moved_against
            })
        
        filtered_picks = [p for p in picks if p['passes_filter']]
        excluded_count = len(picks) - len(filtered_picks)
        
        print("-" * 90)
        print(f"{'Game':<30} {'Pick':<18} {'Conf':>8} {'Edge':>7} {'EV':>8} {'Rating':>10}")
        print("-" * 90)
        
        for pick in sorted(filtered_picks, key=lambda x: x['edge'], reverse=True):
            game_str = pick['game'][:29]
            flag = " !" if pick['line_moved_against'] else ""
            print(f"{game_str:<30} {pick['pick']:<18} {pick['confidence']:>7.1%} {pick['edge']:>+6.1f}% {pick['ev']:>+7.1f}% {pick['rating']:>10}{flag}")
        
        print("-" * 90)
        
        moved_count = sum(1 for p in picks if p['line_moved_against'])
        if excluded_count > 0:
            print(f"\n   {excluded_count} games excluded (below {EDGE_THRESHOLD_PCT}% edge or line moved against)")
        if moved_count > 0:
            print(f"   {moved_count} games flagged: line moved against position >2pts")
        
        if log_predictions:
            try:
                from performance_tracker import log_prediction
                logged = 0
                for pick in picks:
                    if log_prediction(
                        pick['game_id'], pick['game_date'], pick['home_team'], pick['away_team'],
                        pick['spread'], pick['pick'], pick['confidence'], pick['home_proba'],
                        market_odds=STANDARD_ODDS,
                        recommended_book='DraftKings',
                        explanation='|'.join(pick['explanation']) if pick['explanation'] else None
                    ):
                        logged += 1
                if logged > 0:
                    print(f"   Logged {logged} predictions with EV and audit trail")
            except Exception as e:
                pass
        
        qualified = [p for p in filtered_picks if p['edge'] >= EDGE_THRESHOLD_PCT]
        if qualified:
            print(f"\n   QUALIFIED OPPORTUNITIES ({EDGE_THRESHOLD_PCT}%+ edge):")
            for pick in sorted(qualified, key=lambda x: x['edge'], reverse=True):
                print(f"   {pick['rating']}: {pick['pick']} (edge: +{pick['edge']:.1f}%, EV: {pick['ev']:+.1f}%)")
                if pick['explanation']:
                    for reason in pick['explanation']:
                        print(f"      - {reason}")
        
        print()
        return filtered_picks
    
    def _generate_explanation(self, row, proba, confidence, edge):
        """Generate 2-4 human-readable reasons for why this pick qualifies"""
        reasons = []
        
        spread = row.get('spread_home', 0) or 0
        open_spread = row.get('spread_home_open', None)
        home = row['home_team']
        away = row['away_team']
        
        pick_home = proba >= 0.5
        pick_team = home if pick_home else away
        
        if open_spread is not None and spread is not None:
            move = abs(spread - open_spread)
            if move >= 1.0:
                if (pick_home and spread < open_spread) or (not pick_home and spread > open_spread):
                    reasons.append(f"Line moved {move:.1f}pts in our favor since open")
                elif move >= 2.0:
                    reasons.append(f"Line moved {move:.1f}pts against — monitor closely")
        
        consensus = row.get('rundown_spread_consensus', None)
        if consensus is not None and spread is not None:
            diff = abs(spread - consensus)
            if diff >= 1.5:
                reasons.append(f"Model line differs from {len(str(row.get('rundown_num_books',0)))} book consensus by {diff:.1f}pts")
        
        home_margin = row.get('bdl_home_scoring_margin', None)
        away_margin = row.get('bdl_away_scoring_margin', None)
        if home_margin is not None and away_margin is not None:
            margin_diff = home_margin - away_margin
            if pick_home and margin_diff > 5:
                reasons.append(f"Scoring margin advantage: {home} {margin_diff:+.1f}pts better recently")
            elif not pick_home and margin_diff < -5:
                reasons.append(f"Scoring margin advantage: {away} {abs(margin_diff):.1f}pts better recently")
        
        home_rest = row.get('home_rest_days', None)
        away_rest = row.get('away_rest_days', None)
        if home_rest is not None and away_rest is not None:
            try:
                h_rest = int(home_rest) if home_rest else 1
                a_rest = int(away_rest) if away_rest else 1
                if pick_home and h_rest > a_rest + 1:
                    reasons.append(f"Rest advantage: {home} {h_rest}d rest vs {away} {a_rest}d")
                elif not pick_home and a_rest > h_rest + 1:
                    reasons.append(f"Rest advantage: {away} {a_rest}d rest vs {home} {h_rest}d")
            except (ValueError, TypeError):
                pass
        
        home_net = row.get('home_net_rtg', None)
        away_net = row.get('away_net_rtg', None)
        if home_net is not None and away_net is not None:
            try:
                net_diff = float(home_net) - float(away_net)
                if pick_home and net_diff > 3:
                    reasons.append(f"Net rating edge: {home} {net_diff:+.1f} better")
                elif not pick_home and net_diff < -3:
                    reasons.append(f"Net rating edge: {away} {abs(net_diff):.1f} better")
            except (ValueError, TypeError):
                pass
        
        if edge >= EDGE_THRESHOLD_PCT and not reasons:
            implied = abs(STANDARD_ODDS) / (abs(STANDARD_ODDS) + 100) if STANDARD_ODDS < 0 else 100 / (STANDARD_ODDS + 100)
            reasons.append(f"Model probability ({confidence:.0%}) exceeds market implied ({implied:.0%})")
        
        return reasons[:4]
    
    def walk_forward_validate(self):
        """Walk-forward validation: train on past seasons, test on next season. No future leakage."""
        print("\n" + "="*60)
        print("WALK-FORWARD VALIDATION (by season)")
        print("="*60 + "\n")
        
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
        
        seasons = sorted(df['season'].unique())
        if len(seasons) < 2:
            print("Need at least 2 seasons for walk-forward validation")
            return None
        
        results = []
        
        for i in range(1, len(seasons)):
            train_seasons = seasons[:i]
            test_season = seasons[i]
            
            train_df = df[df['season'].isin(train_seasons)]
            test_df = df[df['season'] == test_season]
            
            if len(train_df) < 50 or len(test_df) < 20:
                continue
            
            X_train = self.engineer_features(train_df)
            y_train = self.prepare_target(train_df)
            X_test = self.engineer_features(test_df)
            y_test = self.prepare_target(test_df)
            
            all_features = list(set(X_train.columns) | set(X_test.columns))
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
            
            from sklearn.ensemble import GradientBoostingClassifier
            model = GradientBoostingClassifier(n_estimators=200, max_depth=4, random_state=42)
            model.fit(X_train_s, y_train)
            
            preds = model.predict(X_test_s)
            proba = model.predict_proba(X_test_s)[:, 1]
            acc = accuracy_score(y_test, preds)
            brier = brier_score_loss(y_test, proba)
            
            season_label = f"{test_season}-{test_season+1}"
            results.append({
                'season': season_label,
                'train_games': len(train_df),
                'test_games': len(test_df),
                'accuracy': acc,
                'brier': brier,
            })
            
            print(f"   {season_label}: {acc:.1%} accuracy, {brier:.3f} brier ({len(test_df)} games, trained on {len(train_df)})")
        
        if results:
            avg_acc = np.mean([r['accuracy'] for r in results])
            avg_brier = np.mean([r['brier'] for r in results])
            print(f"\n   Walk-forward average: {avg_acc:.1%} accuracy, {avg_brier:.3f} brier")
            print(f"   Seasons tested: {len(results)}")
        
        return results

    def save(self, filepath='sharp_picks_model.pkl'):
        """Save the trained model"""
        model_data = {
            'models': self.models,
            'base_models': self.base_models,
            'scaler': self.scaler,
            'feature_names': self.feature_names,
            'trained': self.trained,
            'calibration_stats': self.calibration_stats
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
