"""
🏀 SHARP PICKS - INJURY IMPACT ANALYZER
Quantifies how player injuries affect betting lines
"""

import requests
from datetime import datetime


PLAYER_VALUES = {
    'lebron james': {'impact': 5.5, 'position': 'star', 'team': 'Los Angeles Lakers'},
    'anthony davis': {'impact': 4.5, 'position': 'star', 'team': 'Los Angeles Lakers'},
    'stephen curry': {'impact': 5.0, 'position': 'star', 'team': 'Golden State Warriors'},
    'kevin durant': {'impact': 5.0, 'position': 'star', 'team': 'Phoenix Suns'},
    'giannis antetokounmpo': {'impact': 6.0, 'position': 'star', 'team': 'Milwaukee Bucks'},
    'nikola jokic': {'impact': 6.5, 'position': 'star', 'team': 'Denver Nuggets'},
    'luka doncic': {'impact': 5.5, 'position': 'star', 'team': 'Dallas Mavericks'},
    'jayson tatum': {'impact': 4.5, 'position': 'star', 'team': 'Boston Celtics'},
    'jaylen brown': {'impact': 3.5, 'position': 'star', 'team': 'Boston Celtics'},
    'joel embiid': {'impact': 5.5, 'position': 'star', 'team': 'Philadelphia 76ers'},
    'tyrese maxey': {'impact': 3.0, 'position': 'starter', 'team': 'Philadelphia 76ers'},
    'shai gilgeous-alexander': {'impact': 5.5, 'position': 'star', 'team': 'Oklahoma City Thunder'},
    'chet holmgren': {'impact': 3.5, 'position': 'starter', 'team': 'Oklahoma City Thunder'},
    'anthony edwards': {'impact': 4.5, 'position': 'star', 'team': 'Minnesota Timberwolves'},
    'karl-anthony towns': {'impact': 4.0, 'position': 'star', 'team': 'New York Knicks'},
    'jalen brunson': {'impact': 4.0, 'position': 'star', 'team': 'New York Knicks'},
    'donovan mitchell': {'impact': 4.0, 'position': 'star', 'team': 'Cleveland Cavaliers'},
    'darius garland': {'impact': 3.0, 'position': 'starter', 'team': 'Cleveland Cavaliers'},
    'evan mobley': {'impact': 3.0, 'position': 'starter', 'team': 'Cleveland Cavaliers'},
    'ja morant': {'impact': 4.5, 'position': 'star', 'team': 'Memphis Grizzlies'},
    'jaren jackson jr': {'impact': 3.0, 'position': 'starter', 'team': 'Memphis Grizzlies'},
    'devin booker': {'impact': 4.5, 'position': 'star', 'team': 'Phoenix Suns'},
    'bradley beal': {'impact': 3.0, 'position': 'starter', 'team': 'Phoenix Suns'},
    'jimmy butler': {'impact': 4.0, 'position': 'star', 'team': 'Miami Heat'},
    'bam adebayo': {'impact': 3.5, 'position': 'star', 'team': 'Miami Heat'},
    'damian lillard': {'impact': 4.5, 'position': 'star', 'team': 'Milwaukee Bucks'},
    'trae young': {'impact': 4.5, 'position': 'star', 'team': 'Atlanta Hawks'},
    'dejounte murray': {'impact': 3.0, 'position': 'starter', 'team': 'New Orleans Pelicans'},
    'zion williamson': {'impact': 4.0, 'position': 'star', 'team': 'New Orleans Pelicans'},
    'brandon ingram': {'impact': 3.5, 'position': 'star', 'team': 'New Orleans Pelicans'},
    'cade cunningham': {'impact': 4.0, 'position': 'star', 'team': 'Detroit Pistons'},
    'franz wagner': {'impact': 3.5, 'position': 'star', 'team': 'Orlando Magic'},
    'paolo banchero': {'impact': 4.0, 'position': 'star', 'team': 'Orlando Magic'},
    'lamelo ball': {'impact': 4.0, 'position': 'star', 'team': 'Charlotte Hornets'},
    'desmond bane': {'impact': 3.0, 'position': 'starter', 'team': 'Memphis Grizzlies'},
    'austin reaves': {'impact': 2.0, 'position': 'starter', 'team': 'Los Angeles Lakers'},
    'draymond green': {'impact': 2.5, 'position': 'starter', 'team': 'Golden State Warriors'},
    'klay thompson': {'impact': 2.5, 'position': 'starter', 'team': 'Dallas Mavericks'},
    'kyrie irving': {'impact': 4.0, 'position': 'star', 'team': 'Dallas Mavericks'},
    'kawhi leonard': {'impact': 4.5, 'position': 'star', 'team': 'Los Angeles Clippers'},
    'paul george': {'impact': 4.0, 'position': 'star', 'team': 'Philadelphia 76ers'},
    'james harden': {'impact': 3.5, 'position': 'star', 'team': 'Los Angeles Clippers'},
    'de\'aaron fox': {'impact': 4.0, 'position': 'star', 'team': 'Sacramento Kings'},
    'domantas sabonis': {'impact': 3.5, 'position': 'star', 'team': 'Sacramento Kings'},
}

POSITION_DEFAULTS = {
    'star': 4.5,
    'starter': 2.0,
    'rotation': 1.0,
    'bench': 0.5,
}

TEAM_DEPTH = {
    'Boston Celtics': 0.85,
    'Denver Nuggets': 0.80,
    'Oklahoma City Thunder': 0.90,
    'Cleveland Cavaliers': 0.85,
    'Phoenix Suns': 0.75,
    'Milwaukee Bucks': 0.80,
    'Philadelphia 76ers': 0.70,
    'New York Knicks': 0.80,
    'Dallas Mavericks': 0.75,
    'Los Angeles Lakers': 0.75,
    'Golden State Warriors': 0.80,
    'Miami Heat': 0.85,
    'Minnesota Timberwolves': 0.80,
    'Los Angeles Clippers': 0.75,
    'Memphis Grizzlies': 0.70,
    'Sacramento Kings': 0.75,
    'New Orleans Pelicans': 0.70,
    'Indiana Pacers': 0.80,
    'Orlando Magic': 0.85,
    'Detroit Pistons': 0.75,
    'Atlanta Hawks': 0.70,
    'Chicago Bulls': 0.75,
    'Houston Rockets': 0.80,
    'Brooklyn Nets': 0.65,
    'Toronto Raptors': 0.70,
    'Utah Jazz': 0.65,
    'Portland Trail Blazers': 0.65,
    'San Antonio Spurs': 0.60,
    'Charlotte Hornets': 0.65,
    'Washington Wizards': 0.60,
}


class InjuryImpactAnalyzer:
    """Analyzes how injuries affect betting lines"""
    
    def __init__(self):
        self.injury_cache = {}
    
    def get_player_value(self, player_name: str) -> dict:
        """Get a player's value and impact rating"""
        player_key = player_name.lower().strip()
        
        if player_key in PLAYER_VALUES:
            return PLAYER_VALUES[player_key]
        
        for key, data in PLAYER_VALUES.items():
            if player_key in key or key in player_key:
                return data
        
        return {'impact': 1.0, 'position': 'rotation', 'team': 'Unknown'}
    
    def get_team_depth(self, team_name: str) -> float:
        """Get team's depth rating (how well they handle injuries)"""
        for team, depth in TEAM_DEPTH.items():
            if team_name.lower() in team.lower() or team.lower() in team_name.lower():
                return depth
        return 0.75
    
    def calculate_injury_impact(self, player_name: str, team: str = None, opponent: str = None) -> dict:
        """
        Calculate the point spread impact of a player being out
        
        Returns negative number (team gets worse without player)
        """
        player_info = self.get_player_value(player_name)
        base_impact = player_info['impact']
        position = player_info['position']
        
        if team:
            team_depth = self.get_team_depth(team)
        else:
            team_depth = self.get_team_depth(player_info.get('team', ''))
        
        depth_adjustment = 1 + (1 - team_depth) * 0.5
        
        adjusted_impact = base_impact * depth_adjustment
        
        opponent_boost = 0
        if opponent:
            opp_depth = self.get_team_depth(opponent)
            if opp_depth > 0.80:
                opponent_boost = 0.5
        
        final_impact = adjusted_impact + opponent_boost
        
        return {
            'player': player_name,
            'team': team or player_info.get('team', 'Unknown'),
            'position': position,
            'base_impact': base_impact,
            'depth_factor': depth_adjustment,
            'opponent_boost': opponent_boost,
            'total_impact': round(final_impact, 1),
            'spread_adjustment': round(-final_impact, 1),
        }
    
    def fetch_current_injuries(self):
        """Fetch current NBA injuries from ESPN"""
        print("🏥 Fetching current injuries...")
        
        injuries = {}
        
        try:
            url = "https://site.api.espn.com/apis/site/v2/sports/basketball/nba/injuries"
            response = requests.get(url, timeout=10)
            
            if response.status_code != 200:
                return injuries
            
            data = response.json()
            
            for team_data in data.get('teams', []):
                team_name = team_data.get('team', {}).get('displayName', '')
                team_injuries = []
                
                for injury in team_data.get('injuries', []):
                    athlete = injury.get('athlete', {})
                    player_name = athlete.get('displayName', '')
                    status = injury.get('status', '')
                    
                    if status.lower() in ['out', 'doubtful']:
                        team_injuries.append({
                            'player': player_name,
                            'status': status,
                            'details': injury.get('details', {}).get('type', ''),
                        })
                
                if team_injuries:
                    injuries[team_name] = team_injuries
            
            return injuries
            
        except Exception as e:
            print(f"Error fetching injuries: {e}")
            return {}
    
    def analyze_game_injuries(self, home_team: str, away_team: str) -> dict:
        """Analyze total injury impact for a specific game"""
        injuries = self.fetch_current_injuries()
        
        home_impact = 0
        away_impact = 0
        home_injuries = []
        away_injuries = []
        
        for team, players in injuries.items():
            if home_team.lower() in team.lower():
                for p in players:
                    impact = self.calculate_injury_impact(p['player'], home_team, away_team)
                    home_impact += impact['total_impact']
                    home_injuries.append({
                        'player': p['player'],
                        'status': p['status'],
                        'impact': impact['total_impact']
                    })
            
            elif away_team.lower() in team.lower():
                for p in players:
                    impact = self.calculate_injury_impact(p['player'], away_team, home_team)
                    away_impact += impact['total_impact']
                    away_injuries.append({
                        'player': p['player'],
                        'status': p['status'],
                        'impact': impact['total_impact']
                    })
        
        net_impact = away_impact - home_impact
        
        return {
            'home_team': home_team,
            'away_team': away_team,
            'home_injuries': home_injuries,
            'home_total_impact': round(home_impact, 1),
            'away_injuries': away_injuries,
            'away_total_impact': round(away_impact, 1),
            'net_spread_adjustment': round(net_impact, 1),
            'recommendation': self._get_recommendation(net_impact),
        }
    
    def _get_recommendation(self, net_impact: float) -> str:
        """Generate betting recommendation based on injury impact"""
        if net_impact >= 3:
            return "STRONG lean HOME (opponent significantly weakened)"
        elif net_impact >= 1.5:
            return "Lean HOME (opponent weakened)"
        elif net_impact <= -3:
            return "STRONG lean AWAY (home significantly weakened)"
        elif net_impact <= -1.5:
            return "Lean AWAY (home weakened)"
        else:
            return "No significant injury edge"
    
    def show_injury_report(self):
        """Display comprehensive injury analysis"""
        print("\n" + "="*70)
        print("🏥 NBA INJURY IMPACT REPORT")
        print("="*70 + "\n")
        
        injuries = self.fetch_current_injuries()
        
        if not injuries:
            print("ℹ️  No significant injuries reported.\n")
            return
        
        print(f"📋 {len(injuries)} teams with injuries\n")
        
        all_impacts = []
        
        for team, players in injuries.items():
            team_total = 0
            print(f"\n{team}")
            print("-" * 40)
            
            for p in players:
                impact = self.calculate_injury_impact(p['player'], team)
                team_total += impact['total_impact']
                
                stars = "⭐" * min(int(impact['total_impact'] / 1.5), 5)
                print(f"   {p['player']:<25} {p['status']:<10} -{impact['total_impact']:.1f} pts {stars}")
                
                all_impacts.append({
                    'player': p['player'],
                    'team': team,
                    'impact': impact['total_impact']
                })
            
            if len(players) > 1:
                print(f"   {'TOTAL':<25} {'':<10} -{team_total:.1f} pts")
        
        print("\n" + "="*70)
        print("🔥 BIGGEST INJURY IMPACTS")
        print("-" * 40)
        
        for imp in sorted(all_impacts, key=lambda x: x['impact'], reverse=True)[:5]:
            print(f"   {imp['player']:<25} ({imp['team'][:15]}) -{imp['impact']:.1f} pts")
        
        print("\n" + "="*70)
        print("💡 HOW TO USE")
        print("-" * 40)
        print("   • If a team loses 5+ pts of value: Consider betting against them")
        print("   • Compare to the spread: If spread doesn't reflect injuries, there's edge")
        print("   • Star players (5+ pts impact) are often slow to be priced in")
        print("   • Check timing: Late scratches = best opportunities")
        print("="*70 + "\n")


def analyze_player(player_name: str):
    """Quick analysis of a single player's impact"""
    analyzer = InjuryImpactAnalyzer()
    impact = analyzer.calculate_injury_impact(player_name)
    
    print(f"\n🏀 Injury Impact: {player_name}")
    print("-" * 40)
    print(f"   Team: {impact['team']}")
    print(f"   Role: {impact['position'].upper()}")
    print(f"   Base Impact: {impact['base_impact']:.1f} pts")
    print(f"   With Adjustments: {impact['total_impact']:.1f} pts")
    print(f"\n   If OUT: Line moves {impact['spread_adjustment']:+.1f} for {impact['team']}\n")


def main():
    """Run injury analysis"""
    analyzer = InjuryImpactAnalyzer()
    analyzer.show_injury_report()
    
    print("\n📊 EXAMPLE PLAYER IMPACTS:")
    print("="*50)
    
    examples = ['LeBron James', 'Stephen Curry', 'Nikola Jokic', 'Giannis Antetokounmpo']
    
    for player in examples:
        impact = analyzer.calculate_injury_impact(player)
        print(f"   {player:<25} -{impact['total_impact']:.1f} pts")
    
    print("\n💡 Usage:")
    print("   from injuries import InjuryImpactAnalyzer")
    print("   analyzer = InjuryImpactAnalyzer()")
    print("   analyzer.analyze_game_injuries('Lakers', 'Warriors')\n")


if __name__ == "__main__":
    main()
