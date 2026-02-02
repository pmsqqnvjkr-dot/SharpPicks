"""
🏀 SHARP PICKS - BANKROLL & TILT MANAGEMENT
Responsible gambling tools and behavior monitoring
"""

import sqlite3
from datetime import datetime, timedelta
from dataclasses import dataclass
from typing import List, Optional
import os


@dataclass
class Bet:
    """Represents a single bet"""
    id: int
    timestamp: str
    game: str
    bet_type: str
    pick: str
    odds: int
    stake: float
    result: Optional[str]  # 'win', 'loss', 'push', None (pending)
    payout: float
    was_recommended: bool


class BankrollManager:
    """Manages bankroll tracking and responsible gambling features"""
    
    def __init__(self, db_path='sharp_picks.db'):
        self.db_path = db_path
        self.setup_tables()
    
    def setup_tables(self):
        """Create betting log tables"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS bets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                game TEXT,
                bet_type TEXT,
                pick TEXT,
                odds INTEGER,
                stake REAL,
                result TEXT,
                payout REAL,
                was_recommended INTEGER DEFAULT 0
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS bankroll_settings (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS tilt_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                warning_type TEXT,
                details TEXT,
                action_taken TEXT
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def log_bet(self, game: str, bet_type: str, pick: str, odds: int, 
                stake: float, was_recommended: bool = False) -> int:
        """Log a new bet"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO bets (timestamp, game, bet_type, pick, odds, stake, was_recommended)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (datetime.now().isoformat(), game, bet_type, pick, odds, stake, int(was_recommended)))
        
        bet_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        self.check_for_tilt()
        
        return bet_id
    
    def update_bet_result(self, bet_id: int, result: str, payout: float):
        """Update bet with result"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE bets SET result = ?, payout = ? WHERE id = ?
        ''', (result, payout, bet_id))
        
        conn.commit()
        conn.close()
    
    def get_recent_bets(self, num_bets: int = 10) -> List[Bet]:
        """Get most recent bets"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, timestamp, game, bet_type, pick, odds, stake, result, payout, was_recommended
            FROM bets ORDER BY timestamp DESC LIMIT ?
        ''', (num_bets,))
        
        bets = []
        for row in cursor.fetchall():
            bets.append(Bet(
                id=row[0],
                timestamp=row[1],
                game=row[2],
                bet_type=row[3],
                pick=row[4],
                odds=row[5],
                stake=row[6],
                result=row[7],
                payout=row[8] or 0,
                was_recommended=bool(row[9])
            ))
        
        conn.close()
        return bets
    
    def detect_tilt(self) -> dict:
        """
        Analyze recent betting behavior for tilt indicators
        
        Tilt signs:
        1. Bet size increasing after losses
        2. Betting outside recommended picks
        3. Betting frequency increasing
        4. Chasing losses (bigger bets after losses)
        5. Late night betting
        """
        bets = self.get_recent_bets(20)
        
        if len(bets) < 3:
            return {
                'tilt_detected': False, 
                'warnings': [], 
                'risk_level': 'LOW',
                'risk_score': 0,
                'recommended_action': 'Not enough data yet',
                'bets_analyzed': len(bets)
            }
        
        warnings = []
        risk_score = 0
        
        # 1. Check for increasing bet sizes after losses
        loss_streak = 0
        increasing_stakes = 0
        prev_stake = None
        
        for bet in bets:
            if bet.result == 'loss':
                loss_streak += 1
                if prev_stake and bet.stake > prev_stake * 1.2:
                    increasing_stakes += 1
            else:
                loss_streak = 0
            prev_stake = bet.stake
        
        if increasing_stakes >= 2:
            warnings.append({
                'type': 'CHASING_LOSSES',
                'severity': 'HIGH',
                'message': 'Bet sizes increasing after losses - classic tilt sign'
            })
            risk_score += 3
        
        if loss_streak >= 4:
            warnings.append({
                'type': 'LOSS_STREAK',
                'severity': 'MEDIUM',
                'message': f'{loss_streak} losses in a row - consider a break'
            })
            risk_score += 2
        
        # 2. Check for non-recommended bets
        non_recommended = sum(1 for b in bets[:10] if not b.was_recommended)
        if non_recommended >= 7:
            warnings.append({
                'type': 'IGNORING_MODEL',
                'severity': 'MEDIUM',
                'message': f'{non_recommended}/10 recent bets were NOT model recommendations'
            })
            risk_score += 2
        
        # 3. Check betting frequency
        if len(bets) >= 5:
            recent_5 = bets[:5]
            time_span = (datetime.fromisoformat(recent_5[0].timestamp) - 
                        datetime.fromisoformat(recent_5[-1].timestamp))
            
            if time_span.total_seconds() < 3600:  # 5+ bets in 1 hour
                warnings.append({
                    'type': 'RAPID_BETTING',
                    'severity': 'HIGH',
                    'message': '5+ bets placed within 1 hour - slow down'
                })
                risk_score += 3
            elif time_span.total_seconds() < 7200:  # 5+ bets in 2 hours
                warnings.append({
                    'type': 'FREQUENT_BETTING',
                    'severity': 'MEDIUM',
                    'message': 'Betting frequency is elevated'
                })
                risk_score += 1
        
        # 4. Check for late night betting (2am-6am)
        late_bets = 0
        for bet in bets[:10]:
            try:
                bet_time = datetime.fromisoformat(bet.timestamp)
                if 2 <= bet_time.hour < 6:
                    late_bets += 1
            except:
                pass
        
        if late_bets >= 3:
            warnings.append({
                'type': 'LATE_NIGHT_BETTING',
                'severity': 'MEDIUM',
                'message': 'Multiple bets placed between 2am-6am'
            })
            risk_score += 2
        
        # 5. Check stake sizes relative to bankroll
        total_staked_today = sum(b.stake for b in bets[:10])
        avg_stake = total_staked_today / min(len(bets), 10)
        
        if any(b.stake > avg_stake * 3 for b in bets[:5]):
            warnings.append({
                'type': 'OVERSIZED_BET',
                'severity': 'HIGH',
                'message': 'Recent bet 3x larger than average - possible tilt'
            })
            risk_score += 3
        
        # Determine risk level
        if risk_score >= 6:
            risk_level = 'CRITICAL'
            recommended_action = 'STOP: Take at least 24 hours off'
        elif risk_score >= 4:
            risk_level = 'HIGH'
            recommended_action = 'Take a break for a few hours'
        elif risk_score >= 2:
            risk_level = 'MEDIUM'
            recommended_action = 'Review your betting strategy'
        else:
            risk_level = 'LOW'
            recommended_action = 'Continue responsibly'
        
        return {
            'tilt_detected': risk_score >= 4,
            'risk_level': risk_level,
            'risk_score': risk_score,
            'warnings': warnings,
            'recommended_action': recommended_action,
            'bets_analyzed': len(bets),
        }
    
    def check_for_tilt(self):
        """Check for tilt after each bet and log if detected"""
        result = self.detect_tilt()
        
        if result['tilt_detected']:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO tilt_events (timestamp, warning_type, details, action_taken)
                VALUES (?, ?, ?, ?)
            ''', (
                datetime.now().isoformat(),
                result['risk_level'],
                str(result['warnings']),
                result['recommended_action']
            ))
            
            conn.commit()
            conn.close()
    
    def get_stats(self) -> dict:
        """Get overall betting statistics"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT COUNT(*), SUM(stake), SUM(payout) FROM bets')
        total_bets, total_staked, total_payout = cursor.fetchone()
        
        cursor.execute('SELECT COUNT(*) FROM bets WHERE result = "win"')
        wins = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM bets WHERE result = "loss"')
        losses = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM bets WHERE was_recommended = 1 AND result = "win"')
        model_wins = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM bets WHERE was_recommended = 1 AND result IS NOT NULL')
        model_total = cursor.fetchone()[0]
        
        conn.close()
        
        total_staked = total_staked or 0
        total_payout = total_payout or 0
        
        return {
            'total_bets': total_bets or 0,
            'wins': wins or 0,
            'losses': losses or 0,
            'win_rate': (wins / (wins + losses) * 100) if (wins + losses) > 0 else 0,
            'total_staked': total_staked,
            'total_payout': total_payout,
            'profit_loss': total_payout - total_staked,
            'roi': ((total_payout - total_staked) / total_staked * 100) if total_staked > 0 else 0,
            'model_accuracy': (model_wins / model_total * 100) if model_total > 0 else 0,
        }
    
    def show_dashboard(self):
        """Display bankroll and tilt status dashboard"""
        print("\n" + "="*60)
        print("💰 BANKROLL & RESPONSIBLE GAMBLING DASHBOARD")
        print("="*60 + "\n")
        
        # Stats
        stats = self.get_stats()
        
        print("📊 BETTING STATISTICS")
        print("-" * 40)
        print(f"   Total Bets: {stats['total_bets']}")
        print(f"   Record: {stats['wins']}W - {stats['losses']}L ({stats['win_rate']:.1f}%)")
        print(f"   Total Staked: ${stats['total_staked']:.2f}")
        print(f"   Total Payout: ${stats['total_payout']:.2f}")
        
        pl = stats['profit_loss']
        pl_str = f"+${pl:.2f}" if pl >= 0 else f"-${abs(pl):.2f}"
        print(f"   Profit/Loss: {pl_str} ({stats['roi']:+.1f}% ROI)")
        
        if stats['model_accuracy'] > 0:
            print(f"\n   Model Pick Accuracy: {stats['model_accuracy']:.1f}%")
        
        # Tilt check
        tilt = self.detect_tilt()
        
        print("\n" + "="*60)
        print("🧠 TILT ANALYSIS")
        print("-" * 40)
        
        risk_emoji = {
            'LOW': '✅',
            'MEDIUM': '⚠️',
            'HIGH': '🟠',
            'CRITICAL': '🔴'
        }
        
        emoji = risk_emoji.get(tilt['risk_level'], '❓')
        print(f"   Risk Level: {emoji} {tilt['risk_level']}")
        print(f"   Bets Analyzed: {tilt['bets_analyzed']}")
        
        if tilt['warnings']:
            print("\n   ⚠️ WARNINGS:")
            for w in tilt['warnings']:
                print(f"      [{w['severity']}] {w['message']}")
        else:
            print("\n   ✅ No warning signs detected")
        
        print(f"\n   📋 Recommendation: {tilt['recommended_action']}")
        
        # Recent bets
        recent = self.get_recent_bets(5)
        if recent:
            print("\n" + "="*60)
            print("📝 RECENT BETS")
            print("-" * 40)
            
            for bet in recent:
                result_emoji = {'win': '✅', 'loss': '❌', 'push': '➡️'}.get(bet.result, '⏳')
                rec = '📊' if bet.was_recommended else '🎲'
                print(f"   {result_emoji} {bet.pick} @ {bet.odds:+d} (${bet.stake:.0f}) {rec}")
        
        # Tips
        print("\n" + "="*60)
        print("💡 RESPONSIBLE GAMBLING TIPS")
        print("-" * 40)
        print("   • Never bet more than 1-3% of bankroll per bet")
        print("   • Follow the model's recommendations")
        print("   • Take breaks after losing streaks")
        print("   • Set daily/weekly loss limits")
        print("   • Gambling should be entertainment, not income")
        print("="*60 + "\n")


def main():
    """Demo the bankroll manager"""
    manager = BankrollManager()
    
    manager.show_dashboard()
    
    print("\n💡 Usage:")
    print("   from bankroll import BankrollManager")
    print("   manager = BankrollManager()")
    print("   manager.log_bet('Lakers vs Warriors', 'spread', 'Lakers -3', -110, 100, True)")
    print("   manager.update_bet_result(bet_id, 'win', 190.91)")
    print("   manager.detect_tilt()")
    print("   manager.show_dashboard()\n")


if __name__ == "__main__":
    main()
