"""
🏀 SHARP PICKS - ENSEMBLE PREDICTION MODEL
Uses multiple ML models to predict NBA spread outcomes
"""

import sqlite3
import pandas as pd
import numpy as np
from datetime import datetime
import pickle
import os

from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier, AdaBoostClassifier
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.preprocessing import StandardScaler
from sklearn.calibration import CalibratedClassifierCV, calibration_curve
from sklearn.metrics import accuracy_score, classification_report, brier_score_loss
import xgboost as xgb


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
        """Load training data from database"""
        conn = sqlite3.connect('sharp_picks.db')
        
        query = '''
            SELECT 
                home_team, away_team, game_date,
                spread_home, spread_home_open, spread_home_close,
                total, total_open, total_close,
                home_ml, away_ml,
                home_record, away_record,
                home_home_record, away_away_record,
                home_last5, away_last5,
                home_rest_days, away_rest_days,
                line_movement,
                spread_result, home_score, away_score
            FROM games
            WHERE home_score IS NOT NULL
            AND away_score IS NOT NULL
        '''
        
        df = pd.read_sql_query(query, conn)
        conn.close()
        
        return df
    
    def engineer_features(self, df):
        """Create features from raw data"""
        features = pd.DataFrame()
        
        # Spread features (default to 0 if missing)
        features['spread_home'] = pd.to_numeric(df['spread_home'], errors='coerce').fillna(0)
        spread_open = pd.to_numeric(df.get('spread_home_open', pd.Series([0]*len(df))), errors='coerce')
        features['spread_open'] = spread_open.fillna(features['spread_home'])
        features['line_movement'] = pd.to_numeric(df.get('line_movement', pd.Series([0]*len(df))), errors='coerce').fillna(0)
        
        # Total features
        features['total'] = pd.to_numeric(df.get('total', pd.Series([220]*len(df))), errors='coerce').fillna(220)
        total_open = pd.to_numeric(df.get('total_open', pd.Series([220]*len(df))), errors='coerce')
        features['total_open'] = total_open.fillna(features['total'])
        features['total_movement'] = features['total'] - features['total_open']
        
        # Moneyline features
        features['home_ml'] = pd.to_numeric(df.get('home_ml', pd.Series([0]*len(df))), errors='coerce').fillna(0)
        features['away_ml'] = pd.to_numeric(df.get('away_ml', pd.Series([0]*len(df))), errors='coerce').fillna(0)
        features['ml_diff'] = features['home_ml'] - features['away_ml']
        
        # Record features (parse W-L records)
        def parse_record(record):
            if pd.isna(record) or record == 'N/A':
                return 0.5
            try:
                parts = record.split('-')
                wins = int(parts[0])
                losses = int(parts[1])
                return wins / (wins + losses) if (wins + losses) > 0 else 0.5
            except:
                return 0.5
        
        features['home_win_pct'] = df['home_record'].apply(parse_record)
        features['away_win_pct'] = df['away_record'].apply(parse_record)
        features['win_pct_diff'] = features['home_win_pct'] - features['away_win_pct']
        
        # Home/Away split features
        features['home_home_pct'] = df['home_home_record'].apply(parse_record)
        features['away_away_pct'] = df['away_away_record'].apply(parse_record)
        features['split_advantage'] = features['home_home_pct'] - features['away_away_pct']
        
        # Form features (parse L5 string like "WWLWL")
        def parse_form(form_str):
            if pd.isna(form_str) or not form_str:
                return 0.5
            wins = form_str.count('W')
            total = len(form_str)
            return wins / total if total > 0 else 0.5
        
        home_last5 = df.get('home_last5', pd.Series(['']*len(df)))
        away_last5 = df.get('away_last5', pd.Series(['']*len(df)))
        features['home_form'] = home_last5.apply(parse_form)
        features['away_form'] = away_last5.apply(parse_form)
        features['form_diff'] = features['home_form'] - features['away_form']
        
        # Rest days features
        features['home_rest'] = pd.to_numeric(df.get('home_rest_days', pd.Series([1]*len(df))), errors='coerce').fillna(1)
        features['away_rest'] = pd.to_numeric(df.get('away_rest_days', pd.Series([1]*len(df))), errors='coerce').fillna(1)
        features['rest_advantage'] = features['home_rest'] - features['away_rest']
        
        # Spread size features
        features['spread_abs'] = features['spread_home'].abs()
        features['is_favorite'] = (features['spread_home'] < 0).astype(int)
        
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
    
    def train(self):
        """Train all models in the ensemble with probability calibration"""
        print("\n" + "="*60)
        print("🤖 TRAINING CALIBRATED ENSEMBLE MODEL")
        print("="*60 + "\n")
        
        # Load data
        df = self.load_data()
        
        if len(df) < 20:
            print(f"❌ Not enough data to train. Need at least 20 games with results.")
            print(f"   Current: {len(df)} games")
            print(f"   Keep collecting data!\n")
            return False
        
        print(f"📊 Training on {len(df)} games with results\n")
        
        # Filter out pushes for binary classification
        df = df[df['spread_result'] != 'PUSH']
        
        # Prepare features and target
        X = self.engineer_features(df)
        y = self.prepare_target(df)
        
        self.feature_names = X.columns.tolist()
        
        # Split data - need extra split for calibration
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42
        )
        
        # Scale features
        X_train_scaled = self.scaler.fit_transform(X_train)
        X_test_scaled = self.scaler.transform(X_test)
        
        print("Training and calibrating models:")
        print("-" * 50)
        
        results = {}
        
        for name, base_model in self.base_models.items():
            print(f"   Training {name}...", end=" ")
            
            # Wrap with CalibratedClassifierCV for probability calibration
            # Uses isotonic regression for calibration (better for larger datasets)
            # method='sigmoid' uses Platt scaling (better for smaller datasets)
            calibration_method = 'isotonic' if len(X_train) > 100 else 'sigmoid'
            
            calibrated_model = CalibratedClassifierCV(
                base_model,
                method=calibration_method,
                cv=5  # 5-fold cross-validation for calibration
            )
            
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
    
    def predict_games(self):
        """Make predictions for today's upcoming games"""
        print("\n" + "="*60)
        print("🎯 TODAY'S PREDICTIONS")
        print("="*60 + "\n")
        
        if not self.trained:
            self.load_model()
            if not self.trained:
                print("❌ No trained model found. Run training first.\n")
                return
        
        conn = sqlite3.connect('sharp_picks.db')
        
        query = '''
            SELECT 
                id, home_team, away_team, game_date, game_time,
                spread_home, spread_home_open, spread_home_close,
                total, total_open, total_close,
                home_ml, away_ml,
                home_record, away_record,
                home_home_record, away_away_record,
                home_last5, away_last5,
                home_rest_days, away_rest_days,
                line_movement
            FROM games
            WHERE home_score IS NULL
            AND spread_home IS NOT NULL
        '''
        
        df = pd.read_sql_query(query, conn)
        conn.close()
        
        if len(df) == 0:
            print("ℹ️  No upcoming games to predict.\n")
            return
        
        print(f"📊 Analyzing {len(df)} upcoming games...\n")
        
        # Prepare features
        X = self.engineer_features(df)
        X_scaled = self.scaler.transform(X)
        
        # Get predictions from each model
        all_predictions = {}
        for name, model in self.models.items():
            all_predictions[name] = model.predict_proba(X_scaled)[:, 1]
        
        # Ensemble prediction
        ensemble_proba = self.predict_proba(X_scaled)
        
        print("-" * 70)
        print(f"{'Game':<35} {'Pick':<15} {'Confidence':>10} {'Edge':>8}")
        print("-" * 70)
        
        picks = []
        
        for i, row in df.iterrows():
            idx = df.index.get_loc(i)
            
            home = row['home_team']
            away = row['away_team']
            spread = row['spread_home']
            
            proba = ensemble_proba[idx]
            
            # Determine pick
            if proba >= 0.5:
                pick = f"{home} {spread:+.1f}"
                confidence = proba
            else:
                pick = f"{away} {-spread:+.1f}"
                confidence = 1 - proba
            
            # Calculate edge (how far from 50%)
            edge = abs(proba - 0.5) * 2
            
            # Star rating based on confidence
            if confidence >= 0.65:
                stars = "⭐⭐⭐"
                rating = "STRONG"
            elif confidence >= 0.58:
                stars = "⭐⭐"
                rating = "LEAN"
            else:
                stars = "⭐"
                rating = "SLIGHT"
            
            game_str = f"{away} @ {home}"[:34]
            
            print(f"{game_str:<35} {pick:<15} {confidence:>9.1%} {edge:>7.1%}")
            
            picks.append({
                'game': f"{away} @ {home}",
                'pick': pick,
                'confidence': confidence,
                'edge': edge,
                'rating': rating,
                'home_proba': proba
            })
        
        print("-" * 70)
        
        # Show top picks
        strong_picks = [p for p in picks if p['confidence'] >= 0.58]
        if strong_picks:
            print("\n🔥 TOP PICKS (58%+ confidence):")
            for pick in sorted(strong_picks, key=lambda x: x['confidence'], reverse=True):
                print(f"   {pick['rating']}: {pick['pick']} ({pick['confidence']:.1%})")
        
        print()
    
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
