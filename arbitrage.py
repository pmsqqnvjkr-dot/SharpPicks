"""
🏀 SHARP PICKS - ARBITRAGE & MIDDLE DETECTOR
Finds guaranteed profit opportunities across sportsbooks
"""

import requests
import os
from datetime import datetime

API_KEY = os.environ.get('ODDS_API_KEY')


def american_to_decimal(american_odds):
    """Convert American odds to decimal odds"""
    if american_odds > 0:
        return (american_odds / 100) + 1
    else:
        return (100 / abs(american_odds)) + 1


def calculate_implied_prob(american_odds):
    """Calculate implied probability from American odds"""
    if american_odds > 0:
        return 100 / (american_odds + 100)
    else:
        return abs(american_odds) / (abs(american_odds) + 100)


def calculate_arbitrage(odds1, odds2):
    """
    Calculate if arbitrage exists and the profit margin
    Returns: (is_arb, margin, stake1_pct, stake2_pct)
    """
    dec1 = american_to_decimal(odds1)
    dec2 = american_to_decimal(odds2)
    
    total_implied = (1/dec1) + (1/dec2)
    
    if total_implied < 1:
        margin = (1 - total_implied) * 100
        stake1_pct = (1/dec1) / total_implied * 100
        stake2_pct = (1/dec2) / total_implied * 100
        return True, margin, stake1_pct, stake2_pct
    
    return False, 0, 50, 50


def find_spread_middles(game_spreads):
    """
    Find middle opportunities on spreads
    A middle exists when you can bet both sides with overlapping coverage
    """
    middles = []
    
    books = list(game_spreads.keys())
    
    for i, book1 in enumerate(books):
        for book2 in books[i+1:]:
            spread1 = game_spreads[book1]
            spread2 = game_spreads[book2]
            
            home_spread1 = spread1.get('home_spread', 0)
            home_odds1 = spread1.get('home_odds', -110)
            away_spread1 = spread1.get('away_spread', 0)
            away_odds1 = spread1.get('away_odds', -110)
            
            home_spread2 = spread2.get('home_spread', 0)
            home_odds2 = spread2.get('home_odds', -110)
            away_spread2 = spread2.get('away_spread', 0)
            away_odds2 = spread2.get('away_odds', -110)
            
            if home_spread1 < away_spread2:
                middle_size = away_spread2 - home_spread1
                middles.append({
                    'type': 'MIDDLE',
                    'book1': book1,
                    'book2': book2,
                    'bet1': f"Home {home_spread1:+.1f} @ {home_odds1}",
                    'bet2': f"Away {away_spread2:+.1f} @ {away_odds2}",
                    'middle_size': middle_size,
                    'middle_range': f"Home wins by {int(-away_spread2)+1} to {int(-home_spread1)}"
                })
            
            if away_spread1 < home_spread2:
                middle_size = home_spread2 - away_spread1
                middles.append({
                    'type': 'MIDDLE',
                    'book1': book1,
                    'book2': book2,
                    'bet1': f"Away {away_spread1:+.1f} @ {away_odds1}",
                    'bet2': f"Home {home_spread2:+.1f} @ {home_odds2}",
                    'middle_size': middle_size,
                    'middle_range': f"Away wins by {int(-home_spread2)+1} to {int(-away_spread1)}"
                })
    
    return middles


def fetch_all_odds():
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
        'bookmakers': 'draftkings,fanduel,betmgm,caesars,pointsbetus,bovada,betonlineag'
    }
    
    try:
        response = requests.get(url, params=params, timeout=30)
        
        if response.status_code == 200:
            return response.json()
        else:
            print(f"❌ API Error: {response.status_code}")
            return None
    except Exception as e:
        print(f"❌ Error: {e}")
        return None


def find_arbitrage_opportunities():
    """Scan all games for arbitrage and middle opportunities"""
    print("\n" + "="*70)
    print("🔍 SCANNING FOR ARBITRAGE & MIDDLE OPPORTUNITIES")
    print("="*70 + "\n")
    
    games = fetch_all_odds()
    
    if not games:
        print("No games found or API error.\n")
        return
    
    print(f"📊 Analyzing {len(games)} games across multiple sportsbooks...\n")
    
    all_arbs = []
    all_middles = []
    
    for game in games:
        home = game['home_team']
        away = game['away_team']
        bookmakers = game.get('bookmakers', [])
        
        if len(bookmakers) < 2:
            continue
        
        ml_odds = {}
        spread_data = {}
        total_data = {}
        
        for book in bookmakers:
            book_name = book['key']
            
            for market in book.get('markets', []):
                if market['key'] == 'h2h':
                    outcomes = {o['name']: o['price'] for o in market['outcomes']}
                    ml_odds[book_name] = {
                        'home': outcomes.get(home, 0),
                        'away': outcomes.get(away, 0)
                    }
                
                elif market['key'] == 'spreads':
                    outcomes = {o['name']: {'spread': o['point'], 'price': o['price']} 
                               for o in market['outcomes']}
                    if home in outcomes and away in outcomes:
                        spread_data[book_name] = {
                            'home_spread': outcomes[home]['spread'],
                            'home_odds': outcomes[home]['price'],
                            'away_spread': outcomes[away]['spread'],
                            'away_odds': outcomes[away]['price']
                        }
                
                elif market['key'] == 'totals':
                    outcomes = {o['name']: {'total': o['point'], 'price': o['price']} 
                               for o in market['outcomes']}
                    total_data[book_name] = outcomes
        
        books = list(ml_odds.keys())
        for i, book1 in enumerate(books):
            for book2 in books[i+1:]:
                is_arb, margin, stake1, stake2 = calculate_arbitrage(
                    ml_odds[book1]['home'], 
                    ml_odds[book2]['away']
                )
                if is_arb:
                    all_arbs.append({
                        'game': f"{away} @ {home}",
                        'type': 'MONEYLINE',
                        'book1': book1,
                        'bet1': f"{home} ML @ {ml_odds[book1]['home']:+d}",
                        'stake1': stake1,
                        'book2': book2,
                        'bet2': f"{away} ML @ {ml_odds[book2]['away']:+d}",
                        'stake2': stake2,
                        'profit': margin
                    })
                
                is_arb, margin, stake1, stake2 = calculate_arbitrage(
                    ml_odds[book1]['away'], 
                    ml_odds[book2]['home']
                )
                if is_arb:
                    all_arbs.append({
                        'game': f"{away} @ {home}",
                        'type': 'MONEYLINE',
                        'book1': book1,
                        'bet1': f"{away} ML @ {ml_odds[book1]['away']:+d}",
                        'stake1': stake1,
                        'book2': book2,
                        'bet2': f"{home} ML @ {ml_odds[book2]['home']:+d}",
                        'stake2': stake2,
                        'profit': margin
                    })
        
        middles = find_spread_middles(spread_data)
        for m in middles:
            m['game'] = f"{away} @ {home}"
            all_middles.append(m)
    
    if all_arbs:
        print("💰 ARBITRAGE OPPORTUNITIES (Guaranteed Profit):")
        print("-" * 70)
        for arb in sorted(all_arbs, key=lambda x: x['profit'], reverse=True):
            print(f"\n🎯 {arb['game']}")
            print(f"   Type: {arb['type']}")
            print(f"   {arb['book1'].upper()}: {arb['bet1']} ({arb['stake1']:.1f}% of bankroll)")
            print(f"   {arb['book2'].upper()}: {arb['bet2']} ({arb['stake2']:.1f}% of bankroll)")
            print(f"   💵 Guaranteed Profit: {arb['profit']:.2f}%")
    else:
        print("ℹ️  No pure arbitrage opportunities found.\n")
    
    good_middles = [m for m in all_middles if m['middle_size'] >= 1]
    if good_middles:
        print("\n" + "="*70)
        print("🎯 MIDDLE OPPORTUNITIES (Win Both If Game Lands In Range):")
        print("-" * 70)
        
        for m in sorted(good_middles, key=lambda x: x['middle_size'], reverse=True)[:10]:
            print(f"\n📊 {m['game']}")
            print(f"   {m['book1'].upper()}: {m['bet1']}")
            print(f"   {m['book2'].upper()}: {m['bet2']}")
            print(f"   Middle Size: {m['middle_size']:.1f} points")
            print(f"   Win Both If: {m['middle_range']}")
    else:
        print("\nℹ️  No significant middle opportunities found (need 1+ point gap).\n")
    
    print("\n" + "="*70)
    print("📊 BEST ODDS BY GAME:")
    print("-" * 70)
    
    for game in games[:5]:
        home = game['home_team']
        away = game['away_team']
        bookmakers = game.get('bookmakers', [])
        
        best_home_ml = {'book': '', 'odds': -9999}
        best_away_ml = {'book': '', 'odds': -9999}
        best_home_spread = {'book': '', 'spread': 0, 'odds': -9999}
        best_away_spread = {'book': '', 'spread': 0, 'odds': -9999}
        
        for book in bookmakers:
            book_name = book['key']
            for market in book.get('markets', []):
                if market['key'] == 'h2h':
                    for o in market['outcomes']:
                        if o['name'] == home and o['price'] > best_home_ml['odds']:
                            best_home_ml = {'book': book_name, 'odds': o['price']}
                        elif o['name'] == away and o['price'] > best_away_ml['odds']:
                            best_away_ml = {'book': book_name, 'odds': o['price']}
                
                elif market['key'] == 'spreads':
                    for o in market['outcomes']:
                        if o['name'] == home and o['price'] > best_home_spread['odds']:
                            best_home_spread = {'book': book_name, 'spread': o['point'], 'odds': o['price']}
                        elif o['name'] == away and o['price'] > best_away_spread['odds']:
                            best_away_spread = {'book': book_name, 'spread': o['point'], 'odds': o['price']}
        
        print(f"\n{away} @ {home}")
        print(f"   Best {home} ML: {best_home_ml['odds']:+d} ({best_home_ml['book']})")
        print(f"   Best {away} ML: {best_away_ml['odds']:+d} ({best_away_ml['book']})")
        print(f"   Best {home} spread: {best_home_spread['spread']:+.1f} @ {best_home_spread['odds']:+d} ({best_home_spread['book']})")
        print(f"   Best {away} spread: {best_away_spread['spread']:+.1f} @ {best_away_spread['odds']:+d} ({best_away_spread['book']})")
    
    print("\n")


def calculate_middle_ev(home_spread1, odds1, away_spread2, odds2, middle_prob=0.10):
    """
    Calculate expected value of a middle bet
    Assumes equal stakes on both sides
    """
    dec1 = american_to_decimal(odds1)
    dec2 = american_to_decimal(odds2)
    
    win_both = middle_prob * (dec1 - 1 + dec2 - 1)
    lose_one = (1 - middle_prob) * (-1)
    
    ev = win_both + lose_one
    
    return ev * 100


if __name__ == "__main__":
    find_arbitrage_opportunities()
