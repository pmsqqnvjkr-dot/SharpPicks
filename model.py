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
from sklearn.metrics import accuracy_score, classification_report
import xgboost as xgb


class EnsemblePredictor:
    """Ensemble model combining multiple ML algorithms"""
    
    def __init__(self):
        self.models = {
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
        self.scaler = StandardScaler()
        self.trained = False
        self.feature_names = []
    
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
            WHERE spread_result IS NOT NULL
            AND home_score IS NOT NULL
        '''
        
        df = pd.read_sql_query(query, conn)
        conn.close()
        
        return df
    
    def engineer_features(self, df):
        """Create features from raw data"""
        features = pd.DataFrame()
        
        # Spread features
        features['spread_home'] = df['spread_home'].fillna(0)
        features['spread_open'] = df['spread_home_open'].fillna(df['spread_home'])
        features['line_movement'] = df['line_movement'].fillna(0)
        
        # Total features
        features['total'] = df['total'].fillna(220)
        features['total_open'] = df['total_open'].fillna(df['total'])
        features['total_movement'] = features['total'] - features['total_open']
        
        # Moneyline features
        features['home_ml'] = df['home_ml'].fillna(0)
        features['away_ml'] = df['away_ml'].fillna(0)
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
        
        features['home_form'] = df['home_last5'].apply(parse_form)
        features['away_form'] = df['away_last5'].apply(parse_form)
        features['form_diff'] = features['home_form'] - features['away_form']
        
        # Rest days features
        features['home_rest'] = df['home_rest_days'].fillna(1)
        features['away_rest'] = df['away_rest_days'].fillna(1)
        features['rest_advantage'] = features['home_rest'] - features['away_rest']
        
        # Spread size features
        features['spread_abs'] = features['spread_home'].abs()
        features['is_favorite'] = (features['spread_home'] < 0).astype(int)
        
        return features
    
    def prepare_target(self, df):
        """Create target variable (1 = home covers, 0 = away covers)"""
        target = (df['spread_result'] == 'HOME_COVER').astype(int)
        return target
    
    def train(self):
        """Train all models in the ensemble"""
        print("\n" + "="*60)
        print("🤖 TRAINING ENSEMBLE MODEL")
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
        
        # Split data
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42
        )
        
        # Scale features
        X_train_scaled = self.scaler.fit_transform(X_train)
        X_test_scaled = self.scaler.transform(X_test)
        
        print("Training models:")
        print("-" * 40)
        
        results = {}
        
        for name, model in self.models.items():
            print(f"   Training {name}...", end=" ")
            
            model.fit(X_train_scaled, y_train)
            
            # Evaluate
            train_score = model.score(X_train_scaled, y_train)
            test_score = model.score(X_test_scaled, y_test)
            
            # Cross-validation
            cv_scores = cross_val_score(model, X_train_scaled, y_train, cv=5)
            
            results[name] = {
                'train': train_score,
                'test': test_score,
                'cv_mean': cv_scores.mean(),
                'cv_std': cv_scores.std()
            }
            
            print(f"✅ Test Accuracy: {test_score:.1%}")
        
        print("\n" + "-" * 40)
        print("\n📈 MODEL PERFORMANCE:")
        print("-" * 60)
        print(f"{'Model':<20} {'Train':>10} {'Test':>10} {'CV Mean':>10}")
        print("-" * 60)
        
        for name, scores in results.items():
            print(f"{name:<20} {scores['train']:>10.1%} {scores['test']:>10.1%} {scores['cv_mean']:>10.1%}")
        
        # Ensemble accuracy
        ensemble_preds = self.predict_proba(X_test_scaled)
        ensemble_classes = (ensemble_preds >= 0.5).astype(int)
        ensemble_acc = accuracy_score(y_test, ensemble_classes)
        
        print("-" * 60)
        print(f"{'ENSEMBLE (avg)':<20} {'-':>10} {ensemble_acc:>10.1%}")
        print("-" * 60)
        
        self.trained = True
        
        # Save model
        self.save()
        
        print(f"\n✅ Model trained and saved!")
        print(f"   Ensemble Test Accuracy: {ensemble_acc:.1%}\n")
        
        return True
    
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
            'scaler': self.scaler,
            'feature_names': self.feature_names,
            'trained': self.trained
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
            self.scaler = model_data['scaler']
            self.feature_names = model_data['feature_names']
            self.trained = model_data['trained']
            
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
        
        rf = self.models['random_forest']
        importance = pd.DataFrame({
            'feature': self.feature_names,
            'importance': rf.feature_importances_
        }).sort_values('importance', ascending=False)
        
        for _, row in importance.head(10).iterrows():
            bar = "█" * int(row['importance'] * 50)
            print(f"   {row['feature']:<20} {bar} {row['importance']:.3f}")
        
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
        else:
            print(f"Unknown command: {cmd}")
            print_usage()
    else:
        print_usage()


def print_usage():
    print("\n🏀 SHARP PICKS MODEL")
    print("="*40)
    print("\nCommands:")
    print("   python model.py train      - Train the ensemble model")
    print("   python model.py predict    - Get predictions for today")
    print("   python model.py importance - Show feature importance")
    print()


if __name__ == "__main__":
    main()
