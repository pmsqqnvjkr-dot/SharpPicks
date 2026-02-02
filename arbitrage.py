"""
🏀 SHARP PICKS - ARBITRAGE & MIDDLE DETECTOR
Finds guaranteed profit opportunities across sportsbooks
"""

import requests
import os
from datetime import datetime
from dataclasses import dataclass
from typing import List, Optional

API_KEY = os.environ.get('ODDS_API_KEY')

SPORTSBOOKS = ['draftkings', 'fanduel', 'betmgm', 'caesars', 'pointsbetus', 'bovada', 'betonlineag']


@dataclass
class ArbitrageOpportunity:
    """Represents an arbitrage betting opportunity"""
    game: str
    market: str  # 'moneyline', 'spread', 'total'
    book1: str
    bet1: str
    odds1: int
    stake1_pct: float
    book2: str
    bet2: str
    odds2: int
    stake2_pct: float
    profit_pct: float
    
    def calculate_stakes(self, bankroll: float):
        """Calculate exact stakes for a given bankroll"""
        stake1 = bankroll * (self.stake1_pct / 100)
        stake2 = bankroll * (self.stake2_pct / 100)
        guaranteed_profit = bankroll * (self.profit_pct / 100)
        return stake1, stake2, guaranteed_profit


def american_to_decimal(american_odds: int) -> float:
    """Convert American odds to decimal odds"""
    if american_odds > 0:
        return (american_odds / 100) + 1
    else:
        return (100 / abs(american_odds)) + 1


def decimal_to_american(decimal_odds: float) -> int:
    """Convert decimal odds to American odds"""
    if decimal_odds >= 2.0:
        return int((decimal_odds - 1) * 100)
    else:
        return int(-100 / (decimal_odds - 1))


def calculate_implied_prob(american_odds: int) -> float:
    """Calculate implied probability from American odds"""
    if american_odds > 0:
        return 100 / (american_odds + 100)
    else:
        return abs(american_odds) / (abs(american_odds) + 100)


def check_arbitrage(odds1: int, odds2: int) -> tuple:
    """
    Check if arbitrage exists between two opposing bets
    Returns: (is_arb, profit_pct, stake1_pct, stake2_pct)
    """
    dec1 = american_to_decimal(odds1)
    dec2 = american_to_decimal(odds2)
    
    total_implied = (1/dec1) + (1/dec2)
    
    if total_implied < 1:
        profit_pct = (1 - total_implied) * 100
        stake1_pct = (1/dec1) / total_implied * 100
        stake2_pct = (1/dec2) / total_implied * 100
        return True, profit_pct, stake1_pct, stake2_pct
    
    return False, 0, 50, 50


def fetch_multi_book_odds() -> Optional[List[dict]]:
    """Fetch odds from multiple sportsbooks"""
    if not API_KEY:
        print("❌ ODDS_API_KEY not set")
        return None
    
    url = "https://api.the-odds-api.com/v4/sports/basketball_nba/odds/"
    
    params = {
        'apiKey': API_KEY,
        'regions': 'us',
        'markets': 'spreads,h2h,totals',
        'oddsFormat': 'american',
        'bookmakers': ','.join(SPORTSBOOKS)
    }
    
    try:
        response = requests.get(url, params=params, timeout=30)
        
        if response.status_code == 200:
            remaining = response.headers.get('x-requests-remaining', '?')
            print(f"✅ Connected! API calls left: {remaining}/500\n")
            return response.json()
        else:
            print(f"❌ API Error: {response.status_code}")
            return None
    except Exception as e:
        print(f"❌ Error: {e}")
        return None


def find_all_arbitrage(games: List[dict]) -> List[ArbitrageOpportunity]:
    """Scan all games for arbitrage opportunities across all books"""
    opportunities = []
    
    for game in games:
        home = game['home_team']
        away = game['away_team']
        game_name = f"{away} @ {home}"
        bookmakers = game.get('bookmakers', [])
        
        if len(bookmakers) < 2:
            continue
        
        # Collect odds by market
        ml_odds = {}  # book -> {home: odds, away: odds}
        spread_odds = {}  # book -> {home: {spread, odds}, away: {spread, odds}}
        total_odds = {}  # book -> {over: {line, odds}, under: {line, odds}}
        
        for book in bookmakers:
            book_name = book['key']
            
            for market in book.get('markets', []):
                if market['key'] == 'h2h':
                    outcomes = {o['name']: o['price'] for o in market['outcomes']}
                    ml_odds[book_name] = {
                        'home': outcomes.get(home),
                        'away': outcomes.get(away)
                    }
                
                elif market['key'] == 'spreads':
                    outcomes = {}
                    for o in market['outcomes']:
                        outcomes[o['name']] = {'spread': o['point'], 'odds': o['price']}
                    spread_odds[book_name] = {
                        'home': outcomes.get(home, {}),
                        'away': outcomes.get(away, {})
                    }
                
                elif market['key'] == 'totals':
                    for o in market['outcomes']:
                        if o['name'] == 'Over':
                            total_odds.setdefault(book_name, {})['over'] = {'line': o['point'], 'odds': o['price']}
                        else:
                            total_odds.setdefault(book_name, {})['under'] = {'line': o['point'], 'odds': o['price']}
        
        # Check moneyline arbitrage
        for book1 in ml_odds:
            for book2 in ml_odds:
                if book1 >= book2:
                    continue
                
                home_odds1 = ml_odds[book1].get('home')
                away_odds2 = ml_odds[book2].get('away')
                
                if home_odds1 and away_odds2:
                    is_arb, profit, s1, s2 = check_arbitrage(home_odds1, away_odds2)
                    if is_arb:
                        opportunities.append(ArbitrageOpportunity(
                            game=game_name,
                            market='moneyline',
                            book1=book1,
                            bet1=f"{home} ML",
                            odds1=home_odds1,
                            stake1_pct=s1,
                            book2=book2,
                            bet2=f"{away} ML",
                            odds2=away_odds2,
                            stake2_pct=s2,
                            profit_pct=profit
                        ))
                
                away_odds1 = ml_odds[book1].get('away')
                home_odds2 = ml_odds[book2].get('home')
                
                if away_odds1 and home_odds2:
                    is_arb, profit, s1, s2 = check_arbitrage(away_odds1, home_odds2)
                    if is_arb:
                        opportunities.append(ArbitrageOpportunity(
                            game=game_name,
                            market='moneyline',
                            book1=book1,
                            bet1=f"{away} ML",
                            odds1=away_odds1,
                            stake1_pct=s1,
                            book2=book2,
                            bet2=f"{home} ML",
                            odds2=home_odds2,
                            stake2_pct=s2,
                            profit_pct=profit
                        ))
        
        # Check spread arbitrage (same spread number, opposite sides)
        for book1 in spread_odds:
            for book2 in spread_odds:
                if book1 >= book2:
                    continue
                
                home1 = spread_odds[book1].get('home', {})
                away2 = spread_odds[book2].get('away', {})
                
                if home1.get('spread') and away2.get('spread'):
                    if abs(home1['spread'] + away2['spread']) < 0.1:
                        is_arb, profit, s1, s2 = check_arbitrage(home1['odds'], away2['odds'])
                        if is_arb:
                            opportunities.append(ArbitrageOpportunity(
                                game=game_name,
                                market='spread',
                                book1=book1,
                                bet1=f"{home} {home1['spread']:+.1f}",
                                odds1=home1['odds'],
                                stake1_pct=s1,
                                book2=book2,
                                bet2=f"{away} {away2['spread']:+.1f}",
                                odds2=away2['odds'],
                                stake2_pct=s2,
                                profit_pct=profit
                            ))
        
        # Check totals arbitrage
        for book1 in total_odds:
            for book2 in total_odds:
                if book1 >= book2:
                    continue
                
                over1 = total_odds[book1].get('over', {})
                under2 = total_odds[book2].get('under', {})
                
                if over1.get('line') and under2.get('line'):
                    if abs(over1['line'] - under2['line']) < 0.1:
                        is_arb, profit, s1, s2 = check_arbitrage(over1['odds'], under2['odds'])
                        if is_arb:
                            opportunities.append(ArbitrageOpportunity(
                                game=game_name,
                                market='total',
                                book1=book1,
                                bet1=f"Over {over1['line']}",
                                odds1=over1['odds'],
                                stake1_pct=s1,
                                book2=book2,
                                bet2=f"Under {under2['line']}",
                                odds2=under2['odds'],
                                stake2_pct=s2,
                                profit_pct=profit
                            ))
    
    return opportunities


def find_best_odds(games: List[dict]) -> dict:
    """Find best available odds for each side of every game"""
    best = {}
    
    for game in games:
        home = game['home_team']
        away = game['away_team']
        game_key = f"{away} @ {home}"
        
        best[game_key] = {
            'home_ml': {'odds': -9999, 'book': ''},
            'away_ml': {'odds': -9999, 'book': ''},
            'home_spread': {'spread': 0, 'odds': -9999, 'book': ''},
            'away_spread': {'spread': 0, 'odds': -9999, 'book': ''},
            'over': {'line': 0, 'odds': -9999, 'book': ''},
            'under': {'line': 0, 'odds': -9999, 'book': ''},
        }
        
        for book in game.get('bookmakers', []):
            book_name = book['key']
            
            for market in book.get('markets', []):
                if market['key'] == 'h2h':
                    for o in market['outcomes']:
                        if o['name'] == home and o['price'] > best[game_key]['home_ml']['odds']:
                            best[game_key]['home_ml'] = {'odds': o['price'], 'book': book_name}
                        elif o['name'] == away and o['price'] > best[game_key]['away_ml']['odds']:
                            best[game_key]['away_ml'] = {'odds': o['price'], 'book': book_name}
                
                elif market['key'] == 'spreads':
                    for o in market['outcomes']:
                        if o['name'] == home and o['price'] > best[game_key]['home_spread']['odds']:
                            best[game_key]['home_spread'] = {'spread': o['point'], 'odds': o['price'], 'book': book_name}
                        elif o['name'] == away and o['price'] > best[game_key]['away_spread']['odds']:
                            best[game_key]['away_spread'] = {'spread': o['point'], 'odds': o['price'], 'book': book_name}
                
                elif market['key'] == 'totals':
                    for o in market['outcomes']:
                        if o['name'] == 'Over' and o['price'] > best[game_key]['over']['odds']:
                            best[game_key]['over'] = {'line': o['point'], 'odds': o['price'], 'book': book_name}
                        elif o['name'] == 'Under' and o['price'] > best[game_key]['under']['odds']:
                            best[game_key]['under'] = {'line': o['point'], 'odds': o['price'], 'book': book_name}
    
    return best


def find_arbitrage_opportunities():
    """Main function to scan for all arbitrage opportunities"""
    print("\n" + "="*70)
    print("💰 ARBITRAGE SCANNER")
    print("="*70)
    print(f"\nScanning {len(SPORTSBOOKS)} sportsbooks: {', '.join(SPORTSBOOKS)}\n")
    
    games = fetch_multi_book_odds()
    
    if not games:
        print("No games found or API error.\n")
        return
    
    print(f"📊 Analyzing {len(games)} games...\n")
    
    # Find arbitrage
    arbs = find_all_arbitrage(games)
    
    if arbs:
        print("="*70)
        print("🎯 ARBITRAGE OPPORTUNITIES FOUND!")
        print("="*70)
        
        for arb in sorted(arbs, key=lambda x: x.profit_pct, reverse=True):
            print(f"\n💰 {arb.game} ({arb.market.upper()})")
            print(f"   Guaranteed Profit: {arb.profit_pct:.2f}%")
            print(f"\n   Bet 1: {arb.book1.upper()}")
            print(f"          {arb.bet1} @ {arb.odds1:+d}")
            print(f"          Stake: {arb.stake1_pct:.1f}% of bankroll")
            print(f"\n   Bet 2: {arb.book2.upper()}")
            print(f"          {arb.bet2} @ {arb.odds2:+d}")
            print(f"          Stake: {arb.stake2_pct:.1f}% of bankroll")
            
            # Calculate example stakes
            s1, s2, profit = arb.calculate_stakes(1000)
            print(f"\n   Example ($1000 bankroll):")
            print(f"          Bet ${s1:.2f} on {arb.bet1}")
            print(f"          Bet ${s2:.2f} on {arb.bet2}")
            print(f"          Guaranteed Profit: ${profit:.2f}")
    else:
        print("ℹ️  No pure arbitrage opportunities found.")
        print("   (Arbitrage is rare - lines sync within seconds)")
    
    # Find and display best odds
    print("\n" + "="*70)
    print("🏆 BEST AVAILABLE ODDS BY GAME")
    print("="*70)
    
    best = find_best_odds(games)
    
    for game_name, odds in list(best.items())[:5]:
        print(f"\n📊 {game_name}")
        
        # Moneyline
        hml = odds['home_ml']
        aml = odds['away_ml']
        home = game_name.split(' @ ')[1]
        away = game_name.split(' @ ')[0]
        
        print(f"   ML: {home} {hml['odds']:+d} ({hml['book']}) | {away} {aml['odds']:+d} ({aml['book']})")
        
        # Spread
        hs = odds['home_spread']
        as_ = odds['away_spread']
        print(f"   Spread: {home} {hs['spread']:+.1f} @ {hs['odds']:+d} ({hs['book']}) | {away} {as_['spread']:+.1f} @ {as_['odds']:+d} ({as_['book']})")
        
        # Total
        ov = odds['over']
        un = odds['under']
        print(f"   Total: O{ov['line']} @ {ov['odds']:+d} ({ov['book']}) | U{un['line']} @ {un['odds']:+d} ({un['book']})")
    
    # Line shopping value
    print("\n" + "="*70)
    print("💡 LINE SHOPPING VALUE")
    print("="*70)
    print("\nAlways bet at the book with the best odds!")
    print("Typical savings: 1-3% per bet (adds up over time)")
    print("\nExample: -110 vs -105 on same bet")
    print("   -110: Risk $110 to win $100")
    print("   -105: Risk $105 to win $100")
    print("   Savings: $5 per $100 wagered (4.5%)")
    
    print("\n" + "="*70 + "\n")


if __name__ == "__main__":
    find_arbitrage_opportunities()
