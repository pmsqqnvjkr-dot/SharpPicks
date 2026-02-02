"""
🏀 SHARP PICKS - STATS DASHBOARD
Quick overview of your betting data
"""

import sqlite3
from datetime import datetime, timedelta


def get_collection_stats():
    """Get game collection statistics"""
    conn = sqlite3.connect('sharp_picks.db')
    cursor = conn.cursor()
    
    # Total games
    cursor.execute('SELECT COUNT(*) FROM games')
    total = cursor.fetchone()[0] or 0
    
    # Games with results
    cursor.execute('SELECT COUNT(*) FROM games WHERE spread_result IS NOT NULL')
    with_results = cursor.fetchone()[0] or 0
    
    # Pending games
    pending = total - with_results
    
    # Calculate streak
    cursor.execute('SELECT DISTINCT DATE(game_date) FROM games ORDER BY game_date DESC')
    dates = [row[0] for row in cursor.fetchall()]
    
    streak = 0
    if dates:
        sorted_dates = sorted(set(dates), reverse=True)
        streak = 1
        for i in range(len(sorted_dates) - 1):
            try:
                d1 = datetime.strptime(sorted_dates[i], '%Y-%m-%d').date()
                d2 = datetime.strptime(sorted_dates[i+1], '%Y-%m-%d').date()
                if (d1 - d2).days == 1:
                    streak += 1
                else:
                    break
            except:
                break
    
    conn.close()
    
    return {
        'total': total,
        'with_results': with_results,
        'pending': pending,
        'streak': streak,
        'first_date': min(dates) if dates else None,
        'last_date': max(dates) if dates else None,
    }


def get_betting_stats():
    """Get betting performance stats"""
    conn = sqlite3.connect('sharp_picks.db')
    cursor = conn.cursor()
    
    # Check if bets table exists
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='bets'")
    if not cursor.fetchone():
        conn.close()
        return None
    
    cursor.execute('SELECT COUNT(*), SUM(stake), SUM(payout) FROM bets WHERE result IS NOT NULL')
    row = cursor.fetchone()
    total_bets = row[0] or 0
    total_staked = row[1] or 0
    total_payout = row[2] or 0
    
    cursor.execute('SELECT COUNT(*) FROM bets WHERE result = "win"')
    wins = cursor.fetchone()[0] or 0
    
    cursor.execute('SELECT COUNT(*) FROM bets WHERE result = "loss"')
    losses = cursor.fetchone()[0] or 0
    
    conn.close()
    
    if total_bets == 0:
        return None
    
    return {
        'total_bets': total_bets,
        'wins': wins,
        'losses': losses,
        'win_rate': (wins / (wins + losses) * 100) if (wins + losses) > 0 else 0,
        'total_staked': total_staked,
        'total_payout': total_payout,
        'profit': total_payout - total_staked,
        'roi': ((total_payout - total_staked) / total_staked * 100) if total_staked > 0 else 0,
    }


def show_stats():
    """Display the stats dashboard"""
    stats = get_collection_stats()
    betting = get_betting_stats()
    
    print()
    print("╔══════════════════════════════════════════════════════════╗")
    print("║            🏀 SHARP PICKS - STATS DASHBOARD              ║")
    print("╚══════════════════════════════════════════════════════════╝")
    print()
    
    # Collection Stats
    print("┌──────────────────────────────────────────────────────────┐")
    print("│  📊 DATA COLLECTION                                      │")
    print("├──────────────────────────────────────────────────────────┤")
    
    # Progress bar (50 game goal)
    goal = 50
    progress = min(stats['with_results'] / goal, 1.0)
    bar_width = 30
    filled = int(progress * bar_width)
    bar = "█" * filled + "░" * (bar_width - filled)
    pct = progress * 100
    
    print(f"│  Games with Results: {stats['with_results']}/{goal}                              │")
    print(f"│  [{bar}] {pct:>5.1f}%   │")
    print(f"│                                                          │")
    print(f"│  📈 Total Collected:    {stats['total']:<5}                            │")
    print(f"│  ✅ With Results:       {stats['with_results']:<5}                            │")
    print(f"│  ⏳ Pending:            {stats['pending']:<5}                            │")
    print("└──────────────────────────────────────────────────────────┘")
    print()
    
    # Streak
    print("┌──────────────────────────────────────────────────────────┐")
    print("│  🔥 COLLECTION STREAK                                    │")
    print("├──────────────────────────────────────────────────────────┤")
    
    streak = stats['streak']
    if streak >= 7:
        streak_display = f"🔥🔥🔥 {streak} DAYS - ON FIRE!"
    elif streak >= 3:
        streak_display = f"🔥 {streak} days - Keep it up!"
    elif streak == 1:
        streak_display = f"📅 {streak} day - Just getting started"
    else:
        streak_display = f"📅 {streak} days"
    
    print(f"│  {streak_display:<56} │")
    
    if stats['first_date'] and stats['last_date']:
        print(f"│                                                          │")
        print(f"│  First: {stats['first_date']}   Latest: {stats['last_date']}              │")
    
    print("└──────────────────────────────────────────────────────────┘")
    print()
    
    # Betting Performance (if available)
    if betting:
        print("┌──────────────────────────────────────────────────────────┐")
        print("│  💰 BETTING PERFORMANCE                                  │")
        print("├──────────────────────────────────────────────────────────┤")
        
        record = f"{betting['wins']}W - {betting['losses']}L ({betting['win_rate']:.1f}%)"
        profit = betting['profit']
        profit_str = f"+${profit:.2f}" if profit >= 0 else f"-${abs(profit):.2f}"
        roi_str = f"{betting['roi']:+.1f}%"
        
        if profit >= 0:
            profit_emoji = "📈"
        else:
            profit_emoji = "📉"
        
        print(f"│  Record:     {record:<42} │")
        print(f"│  {profit_emoji} Profit:    {profit_str:<42} │")
        print(f"│  📊 ROI:       {roi_str:<41} │")
        print(f"│                                                          │")
        print(f"│  Total Staked:  ${betting['total_staked']:<8.2f}                          │")
        print(f"│  Total Payout:  ${betting['total_payout']:<8.2f}                          │")
        print("└──────────────────────────────────────────────────────────┘")
        print()
    
    # Model Status
    print("┌──────────────────────────────────────────────────────────┐")
    print("│  🤖 MODEL STATUS                                         │")
    print("├──────────────────────────────────────────────────────────┤")
    
    if stats['with_results'] >= 50:
        print("│  ✅ READY TO TRAIN!                                      │")
        print("│  Run: python model.py train                              │")
    else:
        needed = 50 - stats['with_results']
        games_per_day = 6
        days_left = (needed // games_per_day) + 1
        print(f"│  ⏳ Need {needed} more games with results                      │")
        print(f"│  📅 Estimated: ~{days_left} days at current pace                   │")
    
    print("└──────────────────────────────────────────────────────────┘")
    print()
    
    # Quick Commands
    print("┌──────────────────────────────────────────────────────────┐")
    print("│  💡 QUICK COMMANDS                                       │")
    print("├──────────────────────────────────────────────────────────┤")
    print("│  python main.py          - Collect today's data          │")
    print("│  python main.py --viz    - Visual progress charts        │")
    print("│  python arbitrage.py     - Find betting opportunities    │")
    print("│  python live_model.py    - Live game predictions         │")
    print("└──────────────────────────────────────────────────────────┘")
    print()


if __name__ == "__main__":
    show_stats()
