"""
🏀 SHARP PICKS - LIVE GAME PREDICTION MODEL
Real-time predictions based on in-game data
"""

import requests
import sqlite3
import numpy as np
from datetime import datetime, timedelta
from db_path import get_sqlite_path


class LiveGamePredictor:
    """Predicts final outcomes during live NBA games"""
    
    def __init__(self):
        self.momentum_window = 5  # Last 5 minutes for momentum calc
    
    def get_live_games(self):
        """Fetch live NBA games from ESPN"""
        url = "https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard"
        
        try:
            response = requests.get(url, timeout=10)
            if response.status_code != 200:
                return []
            
            data = response.json()
            events = data.get('events', [])
            
            live_games = []
            for event in events:
                status = event.get('status', {}).get('type', {}).get('name', '')
                
                if status == 'STATUS_IN_PROGRESS':
                    game_data = self._parse_live_game(event)
                    if game_data:
                        live_games.append(game_data)
            
            return live_games
            
        except Exception as e:
            print(f"Error fetching live games: {e}")
            return []
    
    def _parse_live_game(self, event):
        """Parse live game data from ESPN event"""
        try:
            competitions = event.get('competitions', [{}])[0]
            competitors = competitions.get('competitors', [])
            
            home = away = None
            for comp in competitors:
                team_data = {
                    'name': comp.get('team', {}).get('displayName', ''),
                    'abbr': comp.get('team', {}).get('abbreviation', ''),
                    'score': int(comp.get('score', 0)),
                    'record': comp.get('records', [{}])[0].get('summary', ''),
                }
                
                # Get detailed stats if available
                stats = comp.get('statistics', [])
                for stat in stats:
                    if stat.get('name') == 'fieldGoalPct':
                        team_data['fg_pct'] = float(stat.get('displayValue', '0').replace('%', ''))
                    elif stat.get('name') == 'turnovers':
                        team_data['turnovers'] = int(stat.get('displayValue', 0))
                    elif stat.get('name') == 'rebounds':
                        team_data['rebounds'] = int(stat.get('displayValue', 0))
                
                if comp.get('homeAway') == 'home':
                    home = team_data
                else:
                    away = team_data
            
            # Get game clock
            status = event.get('status', {})
            period = status.get('period', 1)
            clock = status.get('displayClock', '12:00')
            
            # Parse clock
            try:
                parts = clock.split(':')
                minutes = int(parts[0])
                seconds = int(parts[1]) if len(parts) > 1 else 0
            except:
                minutes, seconds = 12, 0
            
            return {
                'id': event.get('id'),
                'home': home,
                'away': away,
                'quarter': period,
                'clock': clock,
                'minutes_left': minutes + (seconds / 60),
                'total_minutes_remaining': self._calc_time_remaining(period, minutes, seconds),
            }
            
        except Exception as e:
            print(f"Error parsing game: {e}")
            return None
    
    def _calc_time_remaining(self, quarter, minutes, seconds):
        """Calculate total minutes remaining in game"""
        quarters_left = max(0, 4 - quarter)
        current_quarter_time = minutes + (seconds / 60)
        return (quarters_left * 12) + current_quarter_time
    
    def get_pregame_spread(self, home_team, away_team):
        """Get pregame spread from database"""
        try:
            conn = sqlite3.connect(get_sqlite_path())
            cursor = conn.cursor()
            
            try:
                from zoneinfo import ZoneInfo
                today = datetime.now(ZoneInfo('America/New_York')).strftime('%Y-%m-%d')
            except ImportError:
                today = (datetime.utcnow() - timedelta(hours=5)).strftime('%Y-%m-%d')
            
            cursor.execute('''
                SELECT spread_home, spread_home_open, total
                FROM games 
                WHERE home_team LIKE ? AND away_team LIKE ?
                AND game_date >= ?
                ORDER BY game_date DESC LIMIT 1
            ''', (f'%{home_team}%', f'%{away_team}%', today))
            
            result = cursor.fetchone()
            conn.close()
            
            if result:
                return {
                    'spread': result[0] or result[1],
                    'total': result[2]
                }
            return None
            
        except:
            return None
    
    def calculate_momentum(self, game_state):
        """Calculate momentum score based on recent scoring"""
        score_diff = game_state['home']['score'] - game_state['away']['score']
        time_elapsed = 48 - game_state['total_minutes_remaining']
        
        if time_elapsed <= 0:
            return 0
        
        # Points per minute differential
        pace = score_diff / time_elapsed
        
        # Normalize to -1 to 1 scale
        momentum = np.tanh(pace / 2)
        
        return momentum
    
    def extract_features(self, game_state, pregame_data=None):
        """Extract prediction features from live game state"""
        home = game_state['home']
        away = game_state['away']
        
        features = {
            'current_score_diff': home['score'] - away['score'],
            'time_remaining': game_state['total_minutes_remaining'],
            'time_elapsed_pct': 1 - (game_state['total_minutes_remaining'] / 48),
            'quarter': game_state['quarter'],
            'home_fg_pct': home.get('fg_pct', 45),
            'away_fg_pct': away.get('fg_pct', 45),
            'fg_pct_diff': home.get('fg_pct', 45) - away.get('fg_pct', 45),
            'turnover_diff': away.get('turnovers', 0) - home.get('turnovers', 0),
            'rebound_diff': home.get('rebounds', 0) - away.get('rebounds', 0),
            'momentum': self.calculate_momentum(game_state),
        }
        
        if pregame_data:
            features['pregame_spread'] = pregame_data.get('spread', 0)
            features['pregame_total'] = pregame_data.get('total', 220)
        else:
            features['pregame_spread'] = 0
            features['pregame_total'] = 220
        
        return features
    
    def predict_final_outcome(self, features):
        """Predict final game outcome based on current state"""
        score_diff = features['current_score_diff']
        time_remaining = features['time_remaining']
        time_pct = features['time_elapsed_pct']
        pregame_spread = features['pregame_spread']
        momentum = features['momentum']
        
        # Weight current score more as game progresses
        current_weight = time_pct ** 0.5
        pregame_weight = 1 - current_weight
        
        # Project final margin
        if time_remaining > 0:
            pace = score_diff / (48 - time_remaining) if time_remaining < 48 else 0
            projected_final_diff = score_diff + (pace * time_remaining * 0.5)
        else:
            projected_final_diff = score_diff
        
        # Blend with pregame expectation
        # Negative spread means home favored, so we flip sign
        pregame_expected_margin = -pregame_spread
        
        blended_margin = (current_weight * projected_final_diff) + (pregame_weight * pregame_expected_margin)
        
        # Adjust for momentum
        blended_margin += momentum * 2 * (1 - time_pct)
        
        # Calculate win probability using logistic function
        # Standard deviation decreases as game progresses
        std_dev = 12 * (time_remaining / 48) ** 0.5
        std_dev = max(std_dev, 1)  # Minimum uncertainty
        
        home_win_prob = 1 / (1 + np.exp(-blended_margin / std_dev))
        
        # Cover probability (against pregame spread)
        cover_margin = blended_margin + pregame_spread
        home_cover_prob = 1 / (1 + np.exp(-cover_margin / std_dev))
        
        return {
            'projected_margin': round(blended_margin, 1),
            'home_win_prob': round(home_win_prob * 100, 1),
            'away_win_prob': round((1 - home_win_prob) * 100, 1),
            'home_cover_prob': round(home_cover_prob * 100, 1),
            'away_cover_prob': round((1 - home_cover_prob) * 100, 1),
            'confidence': round(time_pct * 100, 0),
            'pregame_spread': pregame_spread,
        }
    
    def analyze_live_game(self, game_state):
        """Full analysis of a live game"""
        home = game_state['home']
        away = game_state['away']
        
        # Get pregame data
        pregame = self.get_pregame_spread(home['name'], away['name'])
        
        # Extract features
        features = self.extract_features(game_state, pregame)
        
        # Make prediction
        prediction = self.predict_final_outcome(features)
        
        return {
            'game': f"{away['name']} @ {home['name']}",
            'score': f"{away['score']} - {home['score']}",
            'quarter': f"Q{game_state['quarter']} {game_state['clock']}",
            'current_diff': features['current_score_diff'],
            'momentum': features['momentum'],
            'features': features,
            'prediction': prediction,
        }
    
    def show_live_predictions(self):
        """Display predictions for all live games"""
        print("\n" + "="*70)
        print("🔴 LIVE GAME PREDICTIONS")
        print("="*70 + "\n")
        
        games = self.get_live_games()
        
        if not games:
            print("ℹ️  No live NBA games right now.\n")
            print("   Games typically start around 7 PM ET on weeknights")
            print("   and earlier on weekends.\n")
            return
        
        print(f"📺 {len(games)} game(s) in progress\n")
        
        for game_state in games:
            analysis = self.analyze_live_game(game_state)
            pred = analysis['prediction']
            
            home = game_state['home']
            away = game_state['away']
            
            print("-" * 70)
            print(f"🏀 {away['name']} @ {home['name']}")
            print(f"   Score: {away['abbr']} {away['score']} - {home['score']} {home['abbr']}")
            print(f"   Time: Q{game_state['quarter']} {game_state['clock']}")
            
            # Current lead
            diff = analysis['current_diff']
            if diff > 0:
                print(f"   Lead: {home['abbr']} by {diff}")
            elif diff < 0:
                print(f"   Lead: {away['abbr']} by {abs(diff)}")
            else:
                print(f"   Lead: TIED")
            
            # Momentum indicator
            mom = analysis['momentum']
            if mom > 0.3:
                mom_str = f"🔥 {home['abbr']} HOT"
            elif mom < -0.3:
                mom_str = f"🔥 {away['abbr']} HOT"
            else:
                mom_str = "➡️ Even"
            print(f"   Momentum: {mom_str}")
            
            print()
            print(f"   📊 LIVE PREDICTION (Confidence: {pred['confidence']:.0f}%)")
            print(f"   Projected Final Margin: {home['abbr']} {pred['projected_margin']:+.1f}")
            print(f"   Win Probability: {home['abbr']} {pred['home_win_prob']:.1f}% | {away['abbr']} {pred['away_win_prob']:.1f}%")
            
            if pred['pregame_spread']:
                spread = pred['pregame_spread']
                print(f"\n   📈 SPREAD ANALYSIS (Pregame: {home['abbr']} {spread:+.1f})")
                print(f"   Cover Probability: {home['abbr']} {pred['home_cover_prob']:.1f}% | {away['abbr']} {pred['away_cover_prob']:.1f}%")
                
                if pred['home_cover_prob'] >= 65:
                    print(f"   🎯 LEAN: {home['abbr']} to cover")
                elif pred['away_cover_prob'] >= 65:
                    print(f"   🎯 LEAN: {away['abbr']} to cover")
            
            print()
        
        print("-" * 70)
        print("\n💡 Predictions update in real-time based on:")
        print("   • Current score differential")
        print("   • Time remaining")
        print("   • Shooting percentages")
        print("   • Momentum (recent scoring pace)")
        print("   • Pregame spread expectations\n")


def main():
    """Run live predictions"""
    predictor = LiveGamePredictor()
    predictor.show_live_predictions()


if __name__ == "__main__":
    main()
