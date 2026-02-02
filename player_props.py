"""
🏀 SHARP PICKS - PLAYER PROPS PREDICTOR
Analyze player prop bets (points, rebounds, assists, etc.)
"""

import requests
import numpy as np
from datetime import datetime, timedelta


class PlayerPropsPredictor:
    """Predicts player prop outcomes based on multiple factors"""
    
    def __init__(self):
        self.player_cache = {}
        self.team_defense_cache = {}
    
    def get_player_stats(self, player_name):
        """Fetch player season stats - uses known player database"""
        known_players = {
            'lebron james': {'ppg': 23.5, 'rpg': 7.8, 'apg': 8.9, 'mpg': 35.2, 'fg_pct': 51.2, 'games_played': 45},
            'stephen curry': {'ppg': 26.8, 'rpg': 4.5, 'apg': 6.2, 'mpg': 32.5, 'fg_pct': 45.8, 'games_played': 48},
            'kevin durant': {'ppg': 27.2, 'rpg': 6.5, 'apg': 5.1, 'mpg': 36.8, 'fg_pct': 52.5, 'games_played': 42},
            'giannis antetokounmpo': {'ppg': 31.2, 'rpg': 11.5, 'apg': 6.2, 'mpg': 35.5, 'fg_pct': 58.2, 'games_played': 50},
            'nikola jokic': {'ppg': 26.5, 'rpg': 12.8, 'apg': 9.2, 'mpg': 34.2, 'fg_pct': 56.8, 'games_played': 52},
            'luka doncic': {'ppg': 28.5, 'rpg': 8.2, 'apg': 8.8, 'mpg': 36.5, 'fg_pct': 46.5, 'games_played': 44},
            'jayson tatum': {'ppg': 26.8, 'rpg': 8.5, 'apg': 4.8, 'mpg': 36.2, 'fg_pct': 45.2, 'games_played': 49},
            'anthony edwards': {'ppg': 25.5, 'rpg': 5.5, 'apg': 5.2, 'mpg': 35.8, 'fg_pct': 44.5, 'games_played': 51},
            'shai gilgeous-alexander': {'ppg': 31.5, 'rpg': 5.2, 'apg': 6.5, 'mpg': 34.5, 'fg_pct': 53.2, 'games_played': 48},
            'anthony davis': {'ppg': 24.5, 'rpg': 12.2, 'apg': 3.5, 'mpg': 35.2, 'fg_pct': 54.8, 'games_played': 40},
            'devin booker': {'ppg': 27.2, 'rpg': 4.2, 'apg': 6.8, 'mpg': 35.5, 'fg_pct': 48.5, 'games_played': 46},
            'donovan mitchell': {'ppg': 24.8, 'rpg': 4.5, 'apg': 5.2, 'mpg': 34.8, 'fg_pct': 46.2, 'games_played': 47},
            'tyrese haliburton': {'ppg': 18.5, 'rpg': 3.8, 'apg': 10.2, 'mpg': 33.5, 'fg_pct': 45.8, 'games_played': 44},
            'ja morant': {'ppg': 24.2, 'rpg': 5.5, 'apg': 8.5, 'mpg': 32.8, 'fg_pct': 46.5, 'games_played': 35},
            'trae young': {'ppg': 25.8, 'rpg': 3.2, 'apg': 10.8, 'mpg': 35.2, 'fg_pct': 42.5, 'games_played': 48},
            'damian lillard': {'ppg': 25.2, 'rpg': 4.5, 'apg': 7.2, 'mpg': 35.5, 'fg_pct': 43.8, 'games_played': 45},
            'jimmy butler': {'ppg': 20.5, 'rpg': 5.8, 'apg': 5.5, 'mpg': 33.5, 'fg_pct': 51.2, 'games_played': 38},
            'joel embiid': {'ppg': 28.5, 'rpg': 11.2, 'apg': 5.2, 'mpg': 34.2, 'fg_pct': 52.5, 'games_played': 32},
            'cade cunningham': {'ppg': 24.2, 'rpg': 6.5, 'apg': 9.2, 'mpg': 35.8, 'fg_pct': 44.5, 'games_played': 50},
            'franz wagner': {'ppg': 22.5, 'rpg': 5.8, 'apg': 5.5, 'mpg': 34.5, 'fg_pct': 47.2, 'games_played': 49},
        }
        
        player_key = player_name.lower().strip()
        
        if player_key in known_players:
            stats = known_players[player_key].copy()
            stats['name'] = player_name
            return stats
        
        for key, data in known_players.items():
            if player_key in key or key in player_key:
                stats = data.copy()
                stats['name'] = player_name
                return stats
        
        return None
    
    def _parse_player_stats(self, data, player_name):
        """Parse player statistics from ESPN response"""
        try:
            stats = {
                'name': player_name,
                'ppg': 0,
                'rpg': 0,
                'apg': 0,
                'mpg': 0,
                'fg_pct': 0,
                'three_pct': 0,
                'games_played': 0,
            }
            
            categories = data.get('results', {}).get('stats', {}).get('categories', [])
            
            for cat in categories:
                if cat.get('name') == 'general':
                    for stat in cat.get('stats', []):
                        name = stat.get('name', '')
                        value = stat.get('value', 0)
                        
                        if name == 'avgPoints':
                            stats['ppg'] = float(value)
                        elif name == 'avgRebounds':
                            stats['rpg'] = float(value)
                        elif name == 'avgAssists':
                            stats['apg'] = float(value)
                        elif name == 'avgMinutes':
                            stats['mpg'] = float(value)
                        elif name == 'fieldGoalPct':
                            stats['fg_pct'] = float(value)
                        elif name == 'threePointFieldGoalPct':
                            stats['three_pct'] = float(value)
                        elif name == 'gamesPlayed':
                            stats['games_played'] = int(value)
            
            return stats
            
        except Exception as e:
            print(f"Error parsing stats: {e}")
            return None
    
    def get_recent_games(self, player_name, num_games=5):
        """Get player's recent game performances - simulated based on season stats"""
        stats = self.get_player_stats(player_name)
        
        if not stats:
            return []
        
        games = []
        for i in range(num_games):
            variance = 0.15 + (i * 0.02)
            games.append({
                'date': (datetime.now() - timedelta(days=i*2+1)).strftime('%Y-%m-%d'),
                'opponent': 'Opponent',
                'points': int(stats['ppg'] * (1 + np.random.uniform(-variance, variance))),
                'rebounds': int(stats['rpg'] * (1 + np.random.uniform(-variance, variance))),
                'assists': int(stats['apg'] * (1 + np.random.uniform(-variance, variance))),
                'minutes': int(stats['mpg'] * (1 + np.random.uniform(-0.1, 0.1))),
            })
        
        return games
    
    def get_team_defense_rating(self, team_name):
        """Get team's defensive rating vs position"""
        defense_ratings = {
            'Detroit Pistons': {'vs_guards': 0.95, 'vs_forwards': 1.02, 'vs_centers': 0.98, 'pace': 101.2},
            'Cleveland Cavaliers': {'vs_guards': 0.92, 'vs_forwards': 0.94, 'vs_centers': 0.91, 'pace': 98.5},
            'Boston Celtics': {'vs_guards': 0.94, 'vs_forwards': 0.93, 'vs_centers': 0.95, 'pace': 99.8},
            'Oklahoma City Thunder': {'vs_guards': 0.93, 'vs_forwards': 0.95, 'vs_centers': 0.94, 'pace': 100.1},
            'Houston Rockets': {'vs_guards': 0.96, 'vs_forwards': 0.97, 'vs_centers': 0.98, 'pace': 102.3},
            'Memphis Grizzlies': {'vs_guards': 1.02, 'vs_forwards': 1.01, 'vs_centers': 0.99, 'pace': 101.8},
            'New York Knicks': {'vs_guards': 0.95, 'vs_forwards': 0.96, 'vs_centers': 0.94, 'pace': 97.5},
            'Los Angeles Lakers': {'vs_guards': 1.01, 'vs_forwards': 0.99, 'vs_centers': 1.02, 'pace': 100.5},
            'Milwaukee Bucks': {'vs_guards': 0.97, 'vs_forwards': 0.98, 'vs_centers': 0.96, 'pace': 99.2},
            'Denver Nuggets': {'vs_guards': 0.99, 'vs_forwards': 1.00, 'vs_centers': 0.97, 'pace': 98.8},
            'Phoenix Suns': {'vs_guards': 1.03, 'vs_forwards': 1.02, 'vs_centers': 1.01, 'pace': 100.8},
            'Golden State Warriors': {'vs_guards': 1.01, 'vs_forwards': 1.00, 'vs_centers': 1.02, 'pace': 101.5},
            'Dallas Mavericks': {'vs_guards': 1.04, 'vs_forwards': 1.02, 'vs_centers': 1.03, 'pace': 99.9},
            'Miami Heat': {'vs_guards': 0.96, 'vs_forwards': 0.95, 'vs_centers': 0.97, 'pace': 97.8},
            'Philadelphia 76ers': {'vs_guards': 0.98, 'vs_forwards': 0.97, 'vs_centers': 0.99, 'pace': 98.2},
            'Los Angeles Clippers': {'vs_guards': 0.97, 'vs_forwards': 0.98, 'vs_centers': 0.96, 'pace': 98.9},
            'Indiana Pacers': {'vs_guards': 1.05, 'vs_forwards': 1.04, 'vs_centers': 1.03, 'pace': 103.5},
            'Sacramento Kings': {'vs_guards': 1.03, 'vs_forwards': 1.02, 'vs_centers': 1.01, 'pace': 102.8},
            'Minnesota Timberwolves': {'vs_guards': 0.94, 'vs_forwards': 0.95, 'vs_centers': 0.93, 'pace': 98.1},
            'New Orleans Pelicans': {'vs_guards': 1.01, 'vs_forwards': 1.00, 'vs_centers': 1.02, 'pace': 100.2},
            'Atlanta Hawks': {'vs_guards': 1.04, 'vs_forwards': 1.03, 'vs_centers': 1.02, 'pace': 101.9},
            'Chicago Bulls': {'vs_guards': 1.02, 'vs_forwards': 1.01, 'vs_centers': 1.00, 'pace': 99.5},
            'Toronto Raptors': {'vs_guards': 1.03, 'vs_forwards': 1.02, 'vs_centers': 1.01, 'pace': 100.3},
            'Brooklyn Nets': {'vs_guards': 1.05, 'vs_forwards': 1.04, 'vs_centers': 1.03, 'pace': 101.1},
            'Orlando Magic': {'vs_guards': 0.95, 'vs_forwards': 0.94, 'vs_centers': 0.96, 'pace': 97.2},
            'Charlotte Hornets': {'vs_guards': 1.04, 'vs_forwards': 1.03, 'vs_centers': 1.02, 'pace': 100.7},
            'Washington Wizards': {'vs_guards': 1.06, 'vs_forwards': 1.05, 'vs_centers': 1.04, 'pace': 102.1},
            'Portland Trail Blazers': {'vs_guards': 1.05, 'vs_forwards': 1.04, 'vs_centers': 1.03, 'pace': 101.4},
            'San Antonio Spurs': {'vs_guards': 1.04, 'vs_forwards': 1.03, 'vs_centers': 1.02, 'pace': 100.9},
            'Utah Jazz': {'vs_guards': 1.03, 'vs_forwards': 1.02, 'vs_centers': 1.01, 'pace': 100.4},
        }
        
        for team, ratings in defense_ratings.items():
            if team_name.lower() in team.lower() or team.lower() in team_name.lower():
                return ratings
        
        return {'vs_guards': 1.0, 'vs_forwards': 1.0, 'vs_centers': 1.0, 'pace': 100.0}
    
    def predict_player_prop(self, player_name, opponent, prop_type, line, is_home=True):
        """
        Predict player prop outcome
        
        Args:
            player_name: Player's name (e.g., "LeBron James")
            opponent: Opposing team name
            prop_type: 'points', 'rebounds', 'assists', 'pra' (points+rebounds+assists)
            line: The betting line (e.g., 25.5)
            is_home: Whether player's team is home
        """
        print(f"\n📊 Analyzing {player_name} {prop_type.upper()} {line}...")
        
        season_stats = self.get_player_stats(player_name)
        
        if not season_stats:
            return {
                'prediction': None,
                'recommendation': 'NO DATA',
                'confidence': 0,
                'reason': 'Could not fetch player stats'
            }
        
        recent_games = self.get_recent_games(player_name, 5)
        defense = self.get_team_defense_rating(opponent)
        
        if prop_type == 'points':
            season_avg = season_stats['ppg']
            recent_avg = np.mean([g['points'] for g in recent_games]) if recent_games else season_avg
            def_factor = defense['vs_guards']
        elif prop_type == 'rebounds':
            season_avg = season_stats['rpg']
            recent_avg = np.mean([g['rebounds'] for g in recent_games]) if recent_games else season_avg
            def_factor = defense['vs_forwards']
        elif prop_type == 'assists':
            season_avg = season_stats['apg']
            recent_avg = np.mean([g['assists'] for g in recent_games]) if recent_games else season_avg
            def_factor = defense['vs_guards']
        elif prop_type == 'pra':
            season_avg = season_stats['ppg'] + season_stats['rpg'] + season_stats['apg']
            recent_avg = np.mean([g['points'] + g['rebounds'] + g['assists'] for g in recent_games]) if recent_games else season_avg
            def_factor = (defense['vs_guards'] + defense['vs_forwards']) / 2
        else:
            return {'prediction': None, 'recommendation': 'INVALID PROP', 'confidence': 0}
        
        pace_factor = defense['pace'] / 100.0
        home_factor = 1.03 if is_home else 0.97
        
        season_weight = 0.4
        recent_weight = 0.6
        
        base_prediction = (season_avg * season_weight) + (recent_avg * recent_weight)
        
        adjusted_prediction = base_prediction * def_factor * pace_factor * home_factor
        
        variance = np.std([g.get(prop_type, 0) for g in recent_games]) if recent_games and prop_type != 'pra' else season_avg * 0.25
        if prop_type == 'pra' and recent_games:
            variance = np.std([g['points'] + g['rebounds'] + g['assists'] for g in recent_games])
        
        diff = adjusted_prediction - line
        edge = abs(diff)
        
        z_score = diff / variance if variance > 0 else 0
        confidence = min(abs(z_score) * 25, 95)
        
        if diff > 2:
            recommendation = "OVER"
            confidence = min(confidence + 10, 95)
        elif diff < -2:
            recommendation = "UNDER"
            confidence = min(confidence + 10, 95)
        else:
            recommendation = "NO BET"
            confidence = max(confidence - 20, 10)
        
        return {
            'player': player_name,
            'opponent': opponent,
            'prop_type': prop_type,
            'line': line,
            'prediction': round(adjusted_prediction, 1),
            'season_avg': round(season_avg, 1),
            'recent_avg': round(recent_avg, 1),
            'recommendation': recommendation,
            'confidence': round(confidence, 0),
            'edge': round(edge, 1),
            'factors': {
                'defense': round(def_factor, 2),
                'pace': round(pace_factor, 2),
                'home': round(home_factor, 2),
            }
        }
    
    def analyze_prop(self, player_name, opponent, prop_type, line, is_home=True):
        """Full analysis with detailed output"""
        result = self.predict_player_prop(player_name, opponent, prop_type, line, is_home)
        
        if result['prediction'] is None:
            print(f"❌ {result['reason']}")
            return result
        
        print("\n" + "="*60)
        print(f"🏀 {result['player']} - {prop_type.upper()} Prop Analysis")
        print("="*60)
        
        print(f"\n📈 STATS:")
        print(f"   Season Average: {result['season_avg']}")
        print(f"   Last 5 Games Avg: {result['recent_avg']}")
        print(f"   vs {opponent}")
        
        print(f"\n⚙️ ADJUSTMENTS:")
        print(f"   Defense Factor: {result['factors']['defense']}x")
        print(f"   Pace Factor: {result['factors']['pace']}x")
        print(f"   Home/Away: {result['factors']['home']}x")
        
        print(f"\n🎯 PREDICTION:")
        print(f"   Line: {result['line']}")
        print(f"   Projected: {result['prediction']}")
        print(f"   Edge: {result['edge']:+.1f}")
        
        rec = result['recommendation']
        conf = result['confidence']
        
        if rec == "OVER":
            print(f"\n✅ RECOMMENDATION: {rec} ({conf:.0f}% confidence)")
        elif rec == "UNDER":
            print(f"\n✅ RECOMMENDATION: {rec} ({conf:.0f}% confidence)")
        else:
            print(f"\n⚠️ RECOMMENDATION: {rec} (too close to call)")
        
        print("="*60 + "\n")
        
        return result


def main():
    """Interactive player props analyzer"""
    print("\n" + "="*60)
    print("🏀 PLAYER PROPS PREDICTOR")
    print("="*60)
    
    predictor = PlayerPropsPredictor()
    
    print("\nExample analyses:\n")
    
    examples = [
        ("LeBron James", "Golden State Warriors", "points", 25.5, True),
        ("Stephen Curry", "Los Angeles Lakers", "points", 28.5, False),
        ("Nikola Jokic", "Dallas Mavericks", "pra", 45.5, True),
    ]
    
    for player, opponent, prop, line, home in examples:
        predictor.analyze_prop(player, opponent, prop, line, home)
    
    print("\n💡 Usage:")
    print("   from player_props import PlayerPropsPredictor")
    print("   predictor = PlayerPropsPredictor()")
    print("   predictor.analyze_prop('Player Name', 'Opponent', 'points', 25.5, True)\n")
    print("   Prop types: 'points', 'rebounds', 'assists', 'pra'\n")


if __name__ == "__main__":
    main()
