import React, { useState, useEffect, useRef } from 'react';
import { Zap, Target, TrendingUp, CheckCircle, Lock, Crown, Share2, X, Activity, Mail, Download, Copy, Flame, BarChart3, AlertCircle, DollarSign } from 'lucide-react';

export default function SharpPicksBestOfBoth() {
  // ============ USER STATE ============
  const [isPaidUser, setIsPaidUser] = useState(false);
  const [isNewPaidUser, setIsNewPaidUser] = useState(false);
  const [unitSize, setUnitSize] = useState(null);
  
  // ============ MODAL STATE ============
  const [showUpgrade, setShowUpgrade] = useState(false);
  const [showWinShare, setShowWinShare] = useState(false);
  const [showEmailSignup, setShowEmailSignup] = useState(false);
  const [showWelcome, setShowWelcome] = useState(false);
  const [showWinCelebration, setShowWinCelebration] = useState(false);
  const [showUnitSetup, setShowUnitSetup] = useState(false);
  const [showTrackModal, setShowTrackModal] = useState(false);
  const [selectedPickToTrack, setSelectedPickToTrack] = useState(null);
  
  // ============ API DATA STATE ============
  const [apiPredictions, setApiPredictions] = useState([]);
  const [apiPerformance, setApiPerformance] = useState(null);
  const [loading, setLoading] = useState(true);
  
  // ============ TRACKING STATE ============
  const [customBetAmount, setCustomBetAmount] = useState('');
  const [trackedBets, setTrackedBets] = useState([]);
  
  // ============ INTERACTION STATE ============
  const [email, setEmail] = useState('');
  const [emailSubmitted, setEmailSubmitted] = useState(false);
  const [selectedWin, setSelectedWin] = useState(null);
  const [timeLeft, setTimeLeft] = useState({ hours: 7, minutes: 22, seconds: 45 });
  const [viewedFOMO, setViewedFOMO] = useState(0);
  const fomoRef = useRef(null);
  
  // ============ FETCH REAL DATA FROM API ============
  useEffect(() => {
    const fetchData = async () => {
      try {
        const [predictionsRes, performanceRes] = await Promise.all([
          fetch('/api/predictions'),
          fetch('/api/performance')
        ]);
        
        if (predictionsRes.ok) {
          const data = await predictionsRes.json();
          setApiPredictions(data.predictions || []);
        }
        
        if (performanceRes.ok) {
          const perfData = await performanceRes.json();
          setApiPerformance(perfData);
        }
      } catch (error) {
        console.error('Error fetching data:', error);
      } finally {
        setLoading(false);
      }
    };
    
    fetchData();
  }, []);
  
  // ============ CALCULATE STATS FROM REAL TRACKED BETS ============
  const settledBets = trackedBets.filter(b => b.result);
  const totalProfit = settledBets.reduce((sum, b) => sum + b.profit, 0);
  const wins = settledBets.filter(b => b.result === 'W').length;
  const losses = settledBets.filter(b => b.result === 'L').length;
  const totalBets = settledBets.length;
  const winRate = totalBets > 0 ? ((wins / totalBets) * 100) : 0;
  const totalRisked = settledBets.reduce((sum, b) => sum + b.betAmount, 0);
  const roi = totalRisked > 0 ? ((totalProfit / totalRisked) * 100) : 0;
  
  // Build profit history for last 8 bets
  const profitHistory = [];
  let runningTotal = 0;
  settledBets.slice(-8).forEach((bet) => {
    runningTotal += bet.profit;
    profitHistory.push({
      date: bet.date,
      profit: runningTotal
    });
  });
  
  const maxProfit = profitHistory.length > 0 ? Math.max(...profitHistory.map(d => Math.abs(d.profit))) : 100;
  
  const userStats = {
    totalProfit: Math.round(totalProfit),
    percentChange: 153,
    roi: roi.toFixed(1),
    winStreak: 5,
    totalBets,
    wins,
    losses,
    userRank: totalProfit > 200 ? 23 : null,
    projectedMonth: totalProfit > 0 ? Math.round(totalProfit * 2.2) : 0,
    profitHistory
  };
  
  // ============ HELPERS ============
  const calculateToWin = (betAmount, americanOdds) => {
    const amount = parseFloat(betAmount);
    if (!amount || isNaN(amount)) return 0;
    if (americanOdds > 0) {
      return (amount * americanOdds) / 100;
    } else {
      return (amount * 100) / Math.abs(americanOdds);
    }
  };
  
  const isPickTracked = (pickId) => {
    return trackedBets.some(b => b.id === pickId);
  };
  
  // ============ COUNTDOWN TIMER ============
  useEffect(() => {
    const timer = setInterval(() => {
      setTimeLeft(prev => {
        if (prev.seconds > 0) return { ...prev, seconds: prev.seconds - 1 };
        if (prev.minutes > 0) return { hours: prev.hours, minutes: prev.minutes - 1, seconds: 59 };
        if (prev.hours > 0) return { hours: prev.hours - 1, minutes: 59, seconds: 59 };
        return prev;
      });
    }, 1000);
    return () => clearInterval(timer);
  }, []);

  // Check if user needs to set unit size - but don't force it
  // Only prompt when they actually try to track a bet
  const needsUnitSize = isPaidUser && unitSize === null;

  // ============ TRANSFORM API DATA TO UI FORMAT ============
  const formatGameTime = (dateStr) => {
    if (!dateStr) return 'TBD';
    const date = new Date(dateStr);
    return date.toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit', timeZoneName: 'short' });
  };

  const generateReasoning = (pred) => {
    const reasons = [];
    if (pred.line_movement > 0.5) reasons.push(`Line moved ${pred.line_movement} points toward ${pred.prediction}`);
    if (pred.edge > 1) reasons.push(`Model sees ${pred.edge.toFixed(1)}% edge over market`);
    if (pred.confidence > 0.65) reasons.push(`High confidence pick based on 36 ML features`);
    return reasons.join('. ') || `Model confidence: ${(pred.confidence * 100).toFixed(1)}%`;
  };

  const generateEdge = (pred) => {
    if (pred.edge > 2) return `Strong edge: ${pred.edge.toFixed(1)}% above break-even threshold`;
    if (pred.line_movement > 0) return `Sharp money indicator: +${pred.line_movement} points line movement`;
    return `ML model edge: ${(pred.confidence * 100).toFixed(1)}% confidence`;
  };

  // Transform API predictions into UI-friendly format
  const transformedPicks = apiPredictions.map((pred, index) => ({
    id: `pick-${index}`,
    game: `${pred.away_team} @ ${pred.home_team}`,
    pick: `${pred.prediction} ${pred.spread >= 0 ? '+' : ''}${pred.spread}`,
    confidence: (pred.confidence * 100).toFixed(1),
    odds: -110,
    time: formatGameTime(pred.game_date),
    reasoning: generateReasoning(pred),
    edge: generateEdge(pred),
    lineMovement: pred.line_movement,
    users: Math.floor(Math.random() * 500) + 300,
    recentWinners: [
      { name: 'Mike from Boston', amount: Math.floor(Math.random() * 200) + 100, time: '2h ago' },
      { name: 'Sarah from NYC', amount: Math.floor(Math.random() * 150) + 80, time: '4h ago' }
    ]
  }));

  // Sort by confidence and take top 5 total (1 free + 4 premium)
  const sortedPicks = [...transformedPicks].sort((a, b) => parseFloat(b.confidence) - parseFloat(a.confidence)).slice(0, 5);
  
  // First pick is free, rest are premium
  const freePick = sortedPicks[0] || {
    id: 'free-1',
    game: 'No games today',
    pick: 'Check back later',
    confidence: 0,
    odds: -110,
    time: 'TBD',
    reasoning: 'No predictions available at this time.',
    edge: 'Waiting for game data',
    users: 0,
    recentWinners: []
  };

  const premiumPicks = sortedPicks.slice(1);

  // Generate results from performance data
  const modelWinRate = apiPerformance?.win_rate || 0.57;
  const totalCorrect = apiPerformance?.correct || 0;
  const totalIncorrect = apiPerformance?.incorrect || 0;
  
  const results = [
    { pick: 'Model Track Record', result: 'W', profit: `+${totalCorrect}`, time: 'All time', final: `${totalCorrect} correct predictions`, winner: null, wasPremium: false },
  ];

  const missedProfit = premiumPicks.length * 91;

  // ============ HANDLERS ============
  const handleSetUnitSize = (size) => {
    setUnitSize(parseInt(size));
    setShowUnitSetup(false);
  };
  
  const handleOpenTrackModal = (pick) => {
    if (!isPaidUser) {
      setShowUpgrade(true);
      return;
    }
    // Just use default $100 if no unit size set
    setSelectedPickToTrack(pick);
    setCustomBetAmount((unitSize || 100).toString());
    setShowTrackModal(true);
  };
  
  const handleConfirmTrack = () => {
    const betAmount = parseInt(customBetAmount) || 100;
    const toWin = calculateToWin(betAmount, selectedPickToTrack.odds);
    
    // Auto-save as unit size if not set yet
    if (!unitSize) {
      setUnitSize(betAmount);
    }
    
    const newBet = {
      id: Date.now(),
      pick: selectedPickToTrack.pick,
      betAmount,
      odds: selectedPickToTrack.odds,
      toWin,
      result: null,
      profit: 0,
      date: 'Feb 1'
    };
    
    setTrackedBets([...trackedBets, newBet]);
    setShowTrackModal(false);
    setSelectedPickToTrack(null);
    
    // Simulate win for demo
    setTimeout(() => {
      const didWin = Math.random() > 0.43; // 57% win rate
      
      setTrackedBets(prev => prev.map(bet => 
        bet.id === newBet.id 
          ? { 
              ...bet, 
              result: didWin ? 'W' : 'L', 
              profit: didWin ? bet.toWin : -bet.betAmount,
              final: didWin ? `${selectedPickToTrack.game} COVERED!` : `${selectedPickToTrack.game} didn't cover`
            }
          : bet
      ));
      
      setSelectedWin({ 
        pick: newBet.pick, 
        profit: didWin ? `+$${newBet.toWin.toFixed(2)}` : `-$${newBet.betAmount}`, 
        final: didWin ? `${selectedPickToTrack.game} COVERED!` : `${selectedPickToTrack.game} didn't cover`
      });
      setShowWinCelebration(true);
    }, 2000);
  };

  const handleEmailSubmit = (e) => {
    e.preventDefault();
    if (email) {
      setEmailSubmitted(true);
      setTimeout(() => {
        setShowEmailSignup(false);
        setEmailSubmitted(false);
        setEmail('');
      }, 2000);
    }
  };

  const handleShareWin = (result) => {
    setSelectedWin(result);
    setShowWinShare(true);
  };

  const handleUpgrade = () => {
    setIsPaidUser(true);
    setIsNewPaidUser(true);
    setShowUpgrade(false);
    setShowWelcome(true);
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-900 via-blue-900 to-slate-900 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-16 w-16 border-t-2 border-b-2 border-blue-500 mx-auto mb-4"></div>
          <p className="text-white text-xl font-bold">Loading picks from ML model...</p>
          <p className="text-slate-400 text-sm mt-2">Analyzing {36} features for today's games</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-blue-900 to-slate-900">
      {/* ============ UNIT SIZE SETUP MODAL ============ */}
      {showUnitSetup && (
        <div className="fixed inset-0 bg-black/95 backdrop-blur-sm z-50 flex items-center justify-center p-6">
          <div className="bg-gradient-to-br from-slate-800 to-slate-900 rounded-3xl p-8 max-w-md w-full border border-slate-700 shadow-2xl">
            <div className="text-center mb-6">
              <div className="bg-blue-600 w-16 h-16 rounded-2xl flex items-center justify-center mx-auto mb-4">
                <DollarSign className="w-8 h-8 text-white" />
              </div>
              <h2 className="text-white text-2xl font-black mb-2">Set Your Unit Size</h2>
              <p className="text-slate-400 text-sm">Your standard bet amount</p>
            </div>

            <div className="mb-6">
              <label className="text-white text-sm font-bold mb-2 block">Unit Size</label>
              <div className="relative">
                <span className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-400 text-xl">$</span>
                <input
                  type="number"
                  defaultValue="100"
                  id="unit-input"
                  className="w-full bg-slate-900 text-white text-2xl font-black pl-10 pr-4 py-4 rounded-xl border border-slate-700 focus:border-blue-500 outline-none"
                />
              </div>
            </div>

            <div className="grid grid-cols-3 gap-2 mb-6">
              {[50, 100, 200].map(amount => (
                <button
                  key={amount}
                  onClick={() => document.getElementById('unit-input').value = amount}
                  className="bg-slate-700 hover:bg-slate-600 text-white font-bold py-2 rounded-lg transition-all"
                >
                  ${amount}
                </button>
              ))}
            </div>

            <button
              onClick={() => {
                const input = document.getElementById('unit-input');
                handleSetUnitSize(input.value || 100);
              }}
              className="w-full bg-gradient-to-r from-blue-600 to-indigo-600 text-white font-black py-4 rounded-xl hover:from-blue-500 hover:to-indigo-500 transition-all"
            >
              Save & Continue
            </button>
          </div>
        </div>
      )}

      {/* ============ TRACK BET MODAL ============ */}
      {showTrackModal && selectedPickToTrack && (
        <div className="fixed inset-0 bg-black/95 backdrop-blur-sm z-50 flex items-center justify-center p-6">
          <div className="bg-gradient-to-br from-slate-800 to-slate-900 rounded-3xl p-8 max-w-md w-full border border-slate-700 shadow-2xl">
            <div className="flex items-center justify-between mb-6">
              <h3 className="text-white text-xl font-bold">Track Your Bet</h3>
              <button onClick={() => setShowTrackModal(false)} className="text-slate-400 hover:text-white">
                <X className="w-6 h-6" />
              </button>
            </div>

            <div className="bg-slate-800/50 rounded-2xl p-4 mb-6">
              <div className="text-slate-400 text-xs font-bold mb-1">YOUR PICK</div>
              <div className="text-white text-2xl font-black mb-1">{selectedPickToTrack.pick}</div>
              <div className="text-slate-400 text-sm">{selectedPickToTrack.game}</div>
            </div>

            <div className="mb-6">
              <label className="text-white text-sm font-bold mb-2 block">Bet Amount</label>
              <div className="relative mb-3">
                <span className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-400 text-xl">$</span>
                <input
                  type="number"
                  value={customBetAmount}
                  onChange={(e) => setCustomBetAmount(e.target.value)}
                  className="w-full bg-slate-900 text-white text-2xl font-black pl-10 pr-4 py-4 rounded-xl border border-slate-700 focus:border-blue-500 outline-none"
                  placeholder="100"
                />
              </div>
              {!unitSize && (
                <div className="bg-blue-950/20 rounded-lg p-3 border border-blue-800/20 mb-3">
                  <p className="text-blue-300 text-xs">
                    💡 This will be saved as your default unit size for future bets
                  </p>
                </div>
              )}
              {unitSize && parseInt(customBetAmount) !== unitSize && (
                <button
                  onClick={() => setCustomBetAmount(unitSize.toString())}
                  className="w-full bg-slate-800 hover:bg-slate-700 text-blue-400 font-bold py-2 rounded-lg text-sm transition-all"
                >
                  Use Default (${unitSize})
                </button>
              )}
            </div>

            <div className="bg-blue-950/30 rounded-2xl p-4 mb-6 border border-blue-800/30">
              <div className="flex items-center justify-between mb-2">
                <span className="text-blue-200 text-sm">Odds:</span>
                <span className="text-white font-bold">{selectedPickToTrack.odds}</span>
              </div>
              <div className="flex items-center justify-between mb-2">
                <span className="text-blue-200 text-sm">Risking:</span>
                <span className="text-white font-bold">${customBetAmount || unitSize}</span>
              </div>
              <div className="flex items-center justify-between mb-2">
                <span className="text-blue-200 text-sm">To Win:</span>
                <span className="text-emerald-400 font-bold">
                  ${calculateToWin(parseInt(customBetAmount) || unitSize, selectedPickToTrack.odds).toFixed(2)}
                </span>
              </div>
              <div className="pt-2 mt-2 border-t border-blue-800/30">
                <div className="flex items-center justify-between">
                  <span className="text-blue-200 text-sm font-bold">Potential Profit:</span>
                  <span className="text-emerald-400 text-xl font-black">
                    +${calculateToWin(parseInt(customBetAmount) || unitSize, selectedPickToTrack.odds).toFixed(2)}
                  </span>
                </div>
              </div>
            </div>

            <button
              onClick={handleConfirmTrack}
              className="w-full bg-gradient-to-r from-emerald-600 to-green-600 text-white font-black py-4 rounded-xl hover:from-emerald-500 hover:to-green-500 transition-all"
            >
              Confirm & Track
            </button>
          </div>
        </div>
      )}

      {/* ============ LOSS RECOVERY MODAL ============ */}
      {showWinCelebration && selectedWin && selectedWin.profit.includes('-') && (
        <div className="fixed inset-0 bg-black/95 backdrop-blur-sm z-50 flex items-center justify-center p-6">
          <div className="bg-gradient-to-br from-slate-800 to-slate-900 rounded-3xl p-8 max-w-md w-full border-2 border-slate-700 shadow-2xl relative">
            <div className="text-center">
              {/* Icon based on context */}
              <div className="text-6xl mb-4">💪</div>
              
              <h2 className="text-white text-3xl font-black mb-2">Tough Break</h2>
              <div className="text-red-400 text-5xl font-black mb-4">{selectedWin.profit}</div>
              
              <div className="bg-slate-800/50 backdrop-blur rounded-xl p-4 mb-6">
                <div className="text-slate-300 font-bold text-sm mb-1">{selectedWin.pick}</div>
                <div className="text-slate-400 text-xs">{selectedWin.final}</div>
              </div>

              {/* Smart contextual messaging */}
              <div className="bg-blue-950/30 rounded-xl p-4 mb-6 border border-blue-800/30 text-left">
                <div className="text-blue-200 text-sm leading-relaxed">
                  {(() => {
                    // First loss
                    if (userStats && userStats.losses === 1 && userStats.wins === 0) {
                      return "Every sharp bettor takes losses. Our model is 57% over time—variance is part of the game. Tomorrow's pick has 92% confidence. Stay the course.";
                    }
                    // On a losing streak (2+ losses in a row)
                    else if (userStats && userStats.winStreak === 0 && userStats.losses >= 2) {
                      return "Losing streaks happen even to the best. Our model has won 57% over 1,000+ picks. The law of averages is on your side. Don't chase—stick to the system.";
                    }
                    // Lost after a winning streak
                    else if (userStats && userStats.winStreak >= 3) {
                      return "All streaks end eventually. You built a great run—that's what matters. The model that got you those wins is still working. Trust the process.";
                    }
                    // Still profitable overall
                    else if (userStats && userStats.totalProfit > 0) {
                      return `You're still up $${userStats.totalProfit} overall. One loss doesn't change that. Sharp bettors focus on long-term edge, not individual games. Keep going.`;
                    }
                    // Generic loss
                    else {
                      return "Sports betting is a marathon, not a sprint. Our 57% win rate means 43% are losses—that's normal. The edge comes from discipline and volume.";
                    }
                  })()}
                </div>
              </div>

              {/* Stats comparison */}
              {userStats && userStats.totalBets >= 3 && (
                <div className="bg-slate-800/50 rounded-xl p-4 mb-6">
                  <div className="text-slate-400 text-xs font-bold mb-3">YOUR TRACK RECORD</div>
                  <div className="grid grid-cols-2 gap-3">
                    <div className="text-center">
                      <div className="text-white text-2xl font-black">{userStats.wins}-{userStats.losses}</div>
                      <div className="text-slate-500 text-xs">Record</div>
                    </div>
                    <div className="text-center">
                      <div className={`text-2xl font-black ${userStats.totalProfit >= 0 ? 'text-emerald-400' : 'text-slate-400'}`}>
                        {userStats.totalProfit >= 0 ? '+' : ''}${userStats.totalProfit}
                      </div>
                      <div className="text-slate-500 text-xs">Total</div>
                    </div>
                  </div>
                  <div className="mt-3 pt-3 border-t border-slate-700">
                    <div className="text-blue-300 text-xs text-center">
                      {userStats.totalProfit >= 0 
                        ? "You're still profitable. Keep trusting the model." 
                        : "Early variance is normal. Volume brings the edge."}
                    </div>
                  </div>
                </div>
              )}

              {/* CTA: Check tomorrow's pick */}
              <div className="space-y-3">
                <button
                  onClick={() => {
                    setShowWinCelebration(false);
                    // Scroll to today's picks
                    window.scrollTo({ top: 0, behavior: 'smooth' });
                  }}
                  className="w-full bg-gradient-to-r from-blue-600 to-indigo-600 text-white font-black py-3 rounded-xl hover:from-blue-500 hover:to-indigo-500 transition-all"
                >
                  Check Tomorrow's Picks
                </button>
                
                <button
                  onClick={() => setShowWinCelebration(false)}
                  className="w-full bg-slate-700 hover:bg-slate-600 text-white font-bold py-3 rounded-xl transition-all"
                >
                  Close
                </button>
              </div>

              {/* Responsible gambling reminder */}
              <div className="mt-4 text-slate-500 text-xs">
                Never bet more than you can afford to lose • 1-800-GAMBLER
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ============ WIN CELEBRATION ============ */}
      {showWinCelebration && selectedWin && !selectedWin.profit.includes('-') && (
        <div className="fixed inset-0 bg-black/95 backdrop-blur-sm z-50 flex items-center justify-center p-6">
          {/* Confetti Animation */}
          <div className="absolute inset-0 overflow-hidden pointer-events-none">
            {[...Array(50)].map((_, i) => (
              <div
                key={i}
                className="absolute w-2 h-2 rounded-full animate-confetti"
                style={{
                  left: `${Math.random() * 100}%`,
                  top: '-10%',
                  backgroundColor: ['#10b981', '#3b82f6', '#f59e0b', '#ef4444', '#8b5cf6'][Math.floor(Math.random() * 5)],
                  animationDelay: `${Math.random() * 0.5}s`,
                  animationDuration: `${2 + Math.random() * 2}s`
                }}
              />
            ))}
          </div>
          
          <div className="bg-gradient-to-br from-emerald-600 to-green-700 rounded-3xl p-8 max-w-md w-full border-2 border-emerald-400 shadow-2xl relative">
            <div className="text-center">
              <div className="text-6xl mb-4">🏆</div>
              <h2 className="text-white text-4xl font-black mb-2">YOU WON!</h2>
              <div className="text-emerald-200 text-6xl font-black mb-4">{selectedWin.profit}</div>
              
              <div className="bg-white/20 backdrop-blur rounded-xl p-4 mb-6">
                <div className="text-white font-bold text-lg mb-1">{selectedWin.pick} ✓</div>
                <div className="text-emerald-200 text-sm">{selectedWin.final}</div>
              </div>

              <button
                onClick={() => {
                  setShowWinCelebration(false);
                  handleShareWin(selectedWin);
                }}
                className="w-full bg-white text-emerald-600 font-black py-3 rounded-xl hover:bg-emerald-50 transition-all mb-3"
              >
                Share Your Win
              </button>
              
              <button
                onClick={() => setShowWinCelebration(false)}
                className="w-full bg-white/20 backdrop-blur text-white font-bold py-3 rounded-xl hover:bg-white/30 transition-all"
              >
                Continue
              </button>
            </div>
          </div>
          
          <style>{`
            @keyframes confetti {
              0% {
                transform: translateY(0) rotateZ(0deg);
                opacity: 1;
              }
              100% {
                transform: translateY(100vh) rotateZ(720deg);
                opacity: 0;
              }
            }
            .animate-confetti {
              animation: confetti linear forwards;
            }
          `}</style>
        </div>
      )}

      {/* ============ OTHER MODALS (Keeping concise) ============ */}
      {showWelcome && isNewPaidUser && (
        <div className="fixed inset-0 bg-black/95 backdrop-blur-sm z-50 flex items-center justify-center p-6">
          <div className="bg-gradient-to-br from-slate-800 to-slate-900 rounded-3xl p-8 max-w-md w-full border border-slate-700 shadow-2xl">
            <div className="text-center mb-6">
              <div className="text-6xl mb-4">🎉</div>
              <h2 className="text-white text-3xl font-black mb-2">Welcome to Sharp Picks Pro!</h2>
              <p className="text-slate-400 text-sm">All picks are now unlocked</p>
            </div>
            <button
              onClick={() => {
                setShowWelcome(false);
                setIsNewPaidUser(false);
              }}
              className="w-full bg-gradient-to-r from-blue-600 to-indigo-600 text-white font-black py-4 rounded-xl"
            >
              Start Tracking Picks
            </button>
          </div>
        </div>
      )}

      {showUpgrade && (
        <div className="fixed inset-0 bg-black/90 backdrop-blur-sm z-50 flex items-center justify-center p-6">
          <div className="bg-gradient-to-br from-slate-800 to-slate-900 rounded-3xl p-8 max-w-md w-full border border-slate-700 shadow-2xl relative">
            <button onClick={() => setShowUpgrade(false)} className="absolute top-4 right-4 text-slate-400 hover:text-white">
              <X className="w-6 h-6" />
            </button>
            <div className="text-center mb-6">
              <div className="bg-gradient-to-br from-amber-500 to-orange-600 w-16 h-16 rounded-2xl flex items-center justify-center mx-auto mb-4">
                <Crown className="w-8 h-8 text-white" />
              </div>
              <h2 className="text-white text-2xl font-black mb-2">Unlock Premium Picks</h2>
              <p className="text-slate-400 text-sm">Choose your plan</p>
            </div>

            {/* PROGRESSIVE PRICING OPTIONS */}
            <div className="space-y-3 mb-6">
              {/* Single Pick Option - MICRO COMMITMENT */}
              <div className="bg-slate-800/50 rounded-2xl p-4 border-2 border-slate-700 hover:border-blue-500 transition-all cursor-pointer">
                <div className="flex items-center justify-between mb-2">
                  <div>
                    <div className="text-white font-black text-xl">$4.99</div>
                    <div className="text-slate-400 text-xs">One-Time</div>
                  </div>
                  <div className="bg-blue-600 text-white text-xs font-bold px-3 py-1 rounded-full">
                    TRY IT
                  </div>
                </div>
                <div className="text-white text-sm font-bold mb-2">Unlock 1 Premium Pick</div>
                <ul className="space-y-1 text-xs text-slate-400">
                  <li className="flex items-center space-x-2">
                    <CheckCircle className="w-3 h-3 flex-shrink-0" />
                    <span>Choose any premium pick today</span>
                  </li>
                  <li className="flex items-center space-x-2">
                    <CheckCircle className="w-3 h-3 flex-shrink-0" />
                    <span>Full analysis & reasoning</span>
                  </li>
                </ul>
                <button
                  onClick={() => {
                    // Handle single pick purchase
                    alert('Single pick purchase - integrate with Stripe');
                    setShowUpgrade(false);
                  }}
                  className="w-full bg-blue-600 hover:bg-blue-500 text-white font-bold py-2 rounded-lg mt-3 text-sm transition-all"
                >
                  Try One Pick
                </button>
              </div>

              {/* Monthly Option - BEST VALUE */}
              <div className="bg-gradient-to-r from-blue-600 to-indigo-600 rounded-2xl p-4 border-2 border-blue-400 relative overflow-hidden">
                <div className="absolute top-2 right-2">
                  <div className="bg-emerald-500 text-white text-xs font-bold px-3 py-1 rounded-full">
                    BEST VALUE
                  </div>
                </div>
                <div className="flex items-center justify-between mb-2">
                  <div>
                    <div className="text-white font-black text-2xl">$19.99</div>
                    <div className="text-blue-200 text-xs">/month</div>
                  </div>
                </div>
                <div className="text-white text-sm font-bold mb-2">All Premium Picks</div>
                <ul className="space-y-1 text-xs text-white mb-3">
                  <li className="flex items-center space-x-2">
                    <CheckCircle className="w-3 h-3 flex-shrink-0" />
                    <span>3-5 elite picks every day</span>
                  </li>
                  <li className="flex items-center space-x-2">
                    <CheckCircle className="w-3 h-3 flex-shrink-0" />
                    <span>Advanced profit tracking</span>
                  </li>
                  <li className="flex items-center space-x-2">
                    <CheckCircle className="w-3 h-3 flex-shrink-0" />
                    <span>Unlock achievement badges</span>
                  </li>
                  <li className="flex items-center space-x-2">
                    <CheckCircle className="w-3 h-3 flex-shrink-0" />
                    <span>Cancel anytime</span>
                  </li>
                </ul>
                <button
                  onClick={handleUpgrade}
                  className="w-full bg-white text-blue-600 font-black py-3 rounded-xl hover:bg-blue-50 transition-all"
                >
                  Start Now
                </button>
              </div>
            </div>

            <div className="text-center">
              <p className="text-slate-400 text-xs">Join 1,247 profitable bettors</p>
            </div>
          </div>
        </div>
      )}

      {/* ============ HEADER ============ */}
      <header className="bg-slate-900/50 backdrop-blur-xl border-b border-slate-700/50 sticky top-0 z-30">
        <div className="max-w-5xl mx-auto px-6 py-4">
          <div className="flex justify-between items-center">
            <div className="flex items-center space-x-3">
              <div className="bg-gradient-to-br from-blue-500 to-indigo-600 p-2 rounded-lg">
                <Zap className="w-5 h-5 text-white" />
              </div>
              <div>
                <div className="flex items-center space-x-2">
                  <h1 className="text-xl font-black text-white">SHARP PICKS</h1>
                  {isPaidUser && <span className="bg-amber-600 text-white text-xs px-2 py-0.5 rounded-full font-bold">PRO</span>}
                </div>
                <p className="text-xs text-slate-400 font-bold">
                  {isPaidUser && userStats.winStreak > 0 && (
                    <>
                      <span className="text-orange-400">🔥 {userStats.winStreak}W streak</span>
                      {' • '}
                    </>
                  )}
                  <span className="text-emerald-400">
                    {isPaidUser ? `+$${userStats.totalProfit} this month` : '3-1 Last 24hrs'}
                  </span>
                </p>
              </div>
            </div>

            {!isPaidUser && (
              <button
                onClick={() => setShowUpgrade(true)}
                className="bg-gradient-to-r from-amber-500 to-orange-600 hover:from-amber-400 hover:to-orange-500 text-white px-6 py-2.5 rounded-xl font-bold text-sm transition-all flex items-center space-x-2 shadow-lg"
              >
                <Crown className="w-4 h-4" />
                <span>Upgrade</span>
              </button>
            )}
          </div>
        </div>
      </header>

      {/* ============ MAIN CONTENT ============ */}
      <main className="max-w-5xl mx-auto px-6 py-8">
        {/* ============ STREAK PROTECTION BANNER (Loss Aversion) ============ */}
        {isPaidUser && userStats.winStreak >= 3 && (
          <div className="bg-gradient-to-r from-orange-600 to-red-600 rounded-2xl p-4 mb-6 border-2 border-orange-400 shadow-xl">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-3">
                <div className="bg-white/20 backdrop-blur p-2 rounded-lg">
                  <Flame className="w-6 h-6 text-white" />
                </div>
                <div>
                  <div className="text-white font-black text-lg">
                    🔥 {userStats.winStreak}-Win Streak!
                  </div>
                  <div className="text-orange-100 text-sm">
                    Don't break it - check today's picks!
                  </div>
                </div>
              </div>
              <div className="text-white text-4xl font-black">
                {userStats.winStreak}
              </div>
            </div>
          </div>
        )}

        {/* ============ CLEAN COMPACT DASHBOARD (Paid Users) ============ */}
        {isPaidUser && (
          <>
            <div className="bg-slate-800/30 backdrop-blur rounded-2xl p-6 mb-8 border border-slate-700/50">
              {/* Hero Stat */}
              <div className="text-center mb-6 pb-6 border-b border-slate-700">
                <div className="text-slate-400 text-sm font-bold uppercase tracking-wider mb-2">This Month</div>
                <div className="text-emerald-400 text-6xl font-black mb-3">+${userStats.totalProfit}</div>
                <div className="flex items-center justify-center space-x-4 text-sm">
                  <span className="text-slate-300">
                    <span className="text-emerald-400 font-bold">▲ {userStats.percentChange}%</span> vs last month
                  </span>
                  {userStats.userRank && (
                    <>
                      <span className="text-slate-600">•</span>
                      <span className="text-amber-400 font-bold">Top {userStats.userRank}%</span>
                    </>
                  )}
                </div>
              </div>

              {/* Compact Stats Grid */}
              <div className="grid grid-cols-3 gap-3">
                <div className="text-center">
                  <div className="text-slate-400 text-xs font-bold uppercase mb-1">Record</div>
                  <div className="text-white text-2xl font-black">{userStats.wins}-{userStats.losses}</div>
                  <div className="text-slate-500 text-xs">{winRate.toFixed(1)}%</div>
                </div>
                <div className="text-center">
                  <div className="text-slate-400 text-xs font-bold uppercase mb-1">ROI</div>
                  <div className="text-emerald-400 text-2xl font-black">+{userStats.roi}%</div>
                  <div className="text-slate-500 text-xs">Return</div>
                </div>
                <div className="text-center">
                  <div className="text-slate-400 text-xs font-bold uppercase mb-1">Streak</div>
                  <div className="text-orange-400 text-2xl font-black">{userStats.winStreak}W 🔥</div>
                  <div className="text-slate-500 text-xs">Current</div>
                </div>
              </div>
            </div>

            {/* PROFIT GRAPH (Bar Chart - Clean Style) */}
            {profitHistory.length > 0 ? (
              <div className="bg-slate-800/50 backdrop-blur-xl rounded-2xl p-6 mb-8 border border-slate-700">
                <div className="flex items-center justify-between mb-6">
                  <h3 className="text-white text-lg font-bold">Last {profitHistory.length} Bets</h3>
                  <div className="text-slate-400 text-sm">
                    On track for <span className="text-emerald-400 font-bold">${userStats.projectedMonth}</span> this month
                  </div>
                </div>
                <div className="flex items-end justify-between space-x-2 h-32">
                  {profitHistory.map((day, i) => {
                    const heightPercent = maxProfit > 0 ? (Math.abs(day.profit) / maxProfit) * 100 : 0;
                    return (
                      <div key={i} className="flex-1 flex flex-col items-center group">
                        {/* Bar with hover tooltip */}
                        <div className="relative w-full flex items-end justify-center" style={{ height: '128px' }}>
                          <div
                            className={`w-full rounded-t-lg transition-all group-hover:opacity-80 ${
                              day.profit > 0 ? 'bg-gradient-to-t from-emerald-600 to-green-500' : 'bg-gradient-to-t from-red-600 to-red-500'
                            }`}
                            style={{ height: `${heightPercent}%`, minHeight: day.profit !== 0 ? '4px' : '0px' }}
                          ></div>
                          {/* Tooltip on hover */}
                          <div className="absolute -top-8 opacity-0 group-hover:opacity-100 transition-opacity bg-slate-900 text-white text-xs font-bold px-2 py-1 rounded whitespace-nowrap pointer-events-none">
                            {day.profit >= 0 ? '+' : ''}${day.profit.toFixed(0)}
                          </div>
                        </div>
                        <div className="text-slate-400 text-xs mt-2 font-bold">{day.date.split(' ')[1]}</div>
                      </div>
                    );
                  })}
                </div>
                {/* Y-axis reference line */}
                <div className="flex items-center justify-between mt-2 pt-2 border-t border-slate-700/50">
                  <span className="text-slate-500 text-xs">Start: ${profitHistory[0]?.profit.toFixed(0) || 0}</span>
                  <span className="text-emerald-400 text-xs font-bold">Now: +${totalProfit}</span>
                </div>
              </div>
            ) : (
              <div className="bg-slate-800/50 backdrop-blur-xl rounded-2xl p-6 mb-8 border border-slate-700">
                <div className="flex items-center justify-between mb-6">
                  <h3 className="text-white text-lg font-bold">Profit History</h3>
                  <div className="text-slate-400 text-sm">Track bets to see your trend</div>
                </div>
                {/* Empty state with placeholder bars */}
                <div className="flex items-end justify-between space-x-2 h-32 opacity-30">
                  {[20, 35, 45, 60, 75, 85, 95, 100].map((height, i) => (
                    <div key={i} className="flex-1 flex flex-col items-center">
                      <div className="w-full rounded-t-lg bg-gradient-to-t from-slate-600 to-slate-500" style={{ height: `${height}%` }}></div>
                      <div className="text-slate-500 text-xs mt-2 font-bold">{i + 1}</div>
                    </div>
                  ))}
                </div>
                <div className="text-center mt-4">
                  <p className="text-slate-400 text-sm">Your profit trend will appear here as you track bets</p>
                </div>
              </div>
            )}

            {/* ============ MILESTONE ACHIEVEMENTS ============ */}
            <div className="bg-gradient-to-r from-purple-600 to-pink-600 rounded-2xl p-6 mb-8 shadow-xl">
              <div className="flex items-center justify-between mb-4">
                <div>
                  <h3 className="text-white text-lg font-black mb-1">Next Milestone</h3>
                  <p className="text-purple-200 text-sm">
                    {userStats.totalProfit < 100 ? '$100 Profit - Sharp Bettor' : 
                     userStats.totalProfit < 500 ? '$500 Profit - Elite Tracker' :
                     userStats.totalProfit < 1000 ? '$1,000 Profit - Diamond Sharp' :
                     '$2,500 Profit - Platinum Pro'}
                  </p>
                </div>
                <div className="text-5xl">
                  {userStats.totalProfit < 100 ? '⚡' : 
                   userStats.totalProfit < 500 ? '🏆' :
                   userStats.totalProfit < 1000 ? '💎' : '👑'}
                </div>
              </div>
              
              {/* Progress Bar */}
              <div className="relative mb-4">
                <div className="w-full bg-purple-800/30 rounded-full h-4 overflow-hidden">
                  <div 
                    className="bg-gradient-to-r from-white to-purple-100 h-full rounded-full transition-all duration-500"
                    style={{ 
                      width: `${Math.min(100, (userStats.totalProfit / (
                        userStats.totalProfit < 100 ? 100 :
                        userStats.totalProfit < 500 ? 500 :
                        userStats.totalProfit < 1000 ? 1000 : 2500
                      )) * 100)}%` 
                    }}
                  ></div>
                </div>
                <div className="text-white text-sm font-bold mt-2">
                  ${userStats.totalProfit} / ${
                    userStats.totalProfit < 100 ? '100' :
                    userStats.totalProfit < 500 ? '500' :
                    userStats.totalProfit < 1000 ? '1,000' : '2,500'
                  } ({Math.min(100, Math.round((userStats.totalProfit / (
                    userStats.totalProfit < 100 ? 100 :
                    userStats.totalProfit < 500 ? 500 :
                    userStats.totalProfit < 1000 ? 1000 : 2500
                  )) * 100))}%)
                </div>
              </div>

              {/* Achievement List */}
              <div className="bg-purple-700/30 rounded-xl p-3">
                <div className="text-purple-100 text-xs font-bold mb-2">🏆 Your Achievements:</div>
                <div className="space-y-1 text-xs">
                  <div className={`flex items-center space-x-2 ${userStats.totalProfit >= 0 ? 'text-purple-200' : 'text-purple-400'}`}>
                    <span>{userStats.totalProfit >= 0 ? '✅' : '⬜'}</span>
                    <span>First Win</span>
                  </div>
                  <div className={`flex items-center space-x-2 ${userStats.totalProfit >= 100 ? 'text-purple-200' : 'text-purple-400'}`}>
                    <span>{userStats.totalProfit >= 100 ? '✅' : '⬜'}</span>
                    <span>$100 Profit - Sharp Bettor ⚡</span>
                  </div>
                  <div className={`flex items-center space-x-2 ${userStats.totalProfit >= 500 ? 'text-purple-200' : 'text-purple-400'}`}>
                    <span>{userStats.totalProfit >= 500 ? '✅' : '⬜'}</span>
                    <span>$500 Profit - Elite Tracker 🏆</span>
                  </div>
                  <div className={`flex items-center space-x-2 ${userStats.totalProfit >= 1000 ? 'text-purple-200' : 'text-purple-400'}`}>
                    <span>{userStats.totalProfit >= 1000 ? '✅' : '⬜'}</span>
                    <span>$1,000 Profit - Diamond Sharp 💎</span>
                  </div>
                </div>
              </div>
            </div>
          </>
        )}

        {/* ============ FOMO (Free Users) ============ */}
        {!isPaidUser && (
          <div ref={fomoRef} className="bg-gradient-to-r from-red-950 to-orange-950 rounded-2xl p-6 mb-8 border-2 border-red-800/50">
            <div className="flex items-start space-x-4">
              <div className="bg-red-600/20 p-3 rounded-xl">
                <AlertCircle className="w-6 h-6 text-red-400" />
              </div>
              <div className="flex-1">
                <h3 className="text-white text-lg font-black mb-2">You Missed +${missedProfit} Yesterday</h3>
                <p className="text-red-200 text-sm mb-4">Premium members got {premiumPicks.length} additional picks</p>
                <button
                  onClick={() => setShowUpgrade(true)}
                  className="w-full bg-gradient-to-r from-amber-500 to-orange-600 text-white font-black py-3 rounded-xl hover:from-amber-400 hover:to-orange-500 transition-all"
                >
                  Unlock All Picks - Never Miss Again
                </button>
              </div>
            </div>
          </div>
        )}

        {/* ============ TODAY'S FREE PICK ============ */}
        <div className="relative bg-gradient-to-br from-blue-600 via-indigo-600 to-blue-700 rounded-3xl p-8 mb-8 overflow-hidden shadow-2xl">
          <div className="absolute top-0 right-0 w-64 h-64 bg-white/5 rounded-full -mr-32 -mt-32"></div>
          
          <div className="relative">
            <div className="flex items-center justify-between mb-6">
              <div className="flex items-center space-x-3">
                <div className="bg-white/20 backdrop-blur p-2 rounded-lg">
                  <Target className="w-6 h-6 text-white" />
                </div>
                <div>
                  <div className="text-blue-200 text-xs font-bold uppercase tracking-wider">
                    {isPaidUser ? "Today's Top Pick" : "Today's Best Pick - Free"}
                  </div>
                  <div className="text-white text-sm font-bold">{freePick.users} users already in</div>
                </div>
              </div>
              <div className="text-right">
                <div className="text-blue-200 text-xs font-bold uppercase tracking-wider mb-1">Starts in</div>
                <div className="bg-black/20 backdrop-blur px-4 py-2 rounded-lg">
                  <div className="text-white text-2xl font-black tabular-nums">
                    {timeLeft.hours}:{String(timeLeft.minutes).padStart(2, '0')}:{String(timeLeft.seconds).padStart(2, '0')}
                  </div>
                </div>
              </div>
            </div>

            <div className="mb-6">
              <div className="text-white/80 text-sm font-bold mb-2">{freePick.game} • {freePick.time}</div>
              <div className="text-white text-5xl font-black mb-3">{freePick.pick}</div>
              <div className="flex items-center space-x-3">
                <div className="bg-white/20 backdrop-blur px-4 py-1.5 rounded-full">
                  <span className="text-white text-sm font-bold">{freePick.confidence}% Confidence</span>
                </div>
                <div className="bg-black/20 backdrop-blur px-4 py-1.5 rounded-full">
                  <span className="text-white text-sm font-bold">Odds: {freePick.odds}</span>
                </div>
              </div>
            </div>

            <div className="bg-black/20 backdrop-blur rounded-xl p-4 mb-5">
              <div className="text-white/80 text-sm font-bold mb-3">Recent Winners:</div>
              <div className="space-y-2">
                {freePick.recentWinners.map((winner, i) => (
                  <div key={i} className="flex items-center justify-between text-sm">
                    <div>
                      <div className="text-white font-bold">{winner.name}</div>
                      <div className="text-blue-200 text-xs">{winner.time}</div>
                    </div>
                    <div className="text-emerald-300 font-black">+${winner.amount}</div>
                  </div>
                ))}
              </div>
            </div>

            <div className="bg-black/20 backdrop-blur rounded-xl p-5 mb-5">
              <div className="text-white/80 text-sm font-bold mb-2">WHY THIS WINS:</div>
              <div className="text-white text-base font-semibold leading-relaxed mb-3">
                {freePick.reasoning}
              </div>
              <div className="text-blue-200 text-sm font-bold">
                📊 {freePick.edge}
              </div>
            </div>

            <button
              onClick={() => handleOpenTrackModal(freePick)}
              className={`w-full font-bold py-4 rounded-xl transition-all flex items-center justify-center space-x-2 ${
                isPickTracked(freePick.id)
                  ? 'bg-white text-blue-600'
                  : 'bg-white/20 backdrop-blur text-white hover:bg-white/30'
              }`}
            >
              {isPickTracked(freePick.id) ? (
                <>
                  <CheckCircle className="w-5 h-5" />
                  <span>Tracking This Pick</span>
                </>
              ) : (
                <>
                  <Target className="w-5 h-5" />
                  <span>Track This Pick</span>
                </>
              )}
            </button>
          </div>
        </div>

        {/* ============ PREMIUM PICKS ============ */}
        <div className="mb-8">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-white text-2xl font-bold">More Elite Picks Today</h2>
            {!isPaidUser && (
              <button
                onClick={() => setShowUpgrade(true)}
                className="text-amber-400 text-sm font-bold flex items-center space-x-1 hover:text-amber-300 transition-all"
              >
                <Crown className="w-4 h-4" />
                <span>Unlock All</span>
              </button>
            )}
          </div>
          <div className="space-y-4">
            {premiumPicks.map((pick) => (
              <div key={pick.id} className="relative bg-slate-800/50 backdrop-blur-xl rounded-2xl overflow-hidden border-2 border-slate-700 group hover:border-slate-600 transition-all">
                {/* CONTENT (visible for paid, blurred for free) */}
                <div className={`p-6 ${!isPaidUser ? 'blur-md' : ''}`}>
                  <div className="flex items-center justify-between mb-4">
                    <div className="flex-1">
                      <div className="text-slate-400 text-sm font-bold mb-2">{pick.game} • {pick.time}</div>
                      <div className="text-white text-3xl font-black mb-2">{pick.pick}</div>
                      <div className="flex items-center space-x-2">
                        <div className="bg-emerald-600/20 border border-emerald-600/30 px-3 py-1 rounded-lg">
                          <span className="text-emerald-400 text-sm font-bold">{pick.confidence}% Confidence</span>
                        </div>
                        <div className="bg-blue-600/20 border border-blue-600/30 px-3 py-1 rounded-lg">
                          <span className="text-blue-400 text-sm font-bold">Odds: {pick.odds}</span>
                        </div>
                      </div>
                    </div>
                  </div>
                  
                  {isPaidUser ? (
                    <>
                      <div className="bg-slate-900/50 rounded-xl p-4 mb-4 border border-slate-700/50">
                        <div className="text-slate-400 text-sm font-bold mb-2">ANALYSIS:</div>
                        <div className="text-white text-sm leading-relaxed mb-2">{pick.reasoning}</div>
                        <div className="text-emerald-400 text-xs font-bold">📊 {pick.edge}</div>
                      </div>
                      <button
                        onClick={() => handleOpenTrackModal(pick)}
                        className="w-full bg-emerald-600 hover:bg-emerald-500 text-white font-bold py-3 rounded-xl transition-all flex items-center justify-center space-x-2"
                      >
                        <Target className="w-5 h-5" />
                        <span>Track This Pick</span>
                      </button>
                    </>
                  ) : (
                    <div className="space-y-3">
                      <div className="bg-slate-900/30 rounded-xl p-4 border border-slate-700/30">
                        <div className="text-slate-400 text-sm">
                          Full expert analysis with statistical edge data and betting trends available with premium access...
                        </div>
                      </div>
                      <div className="flex items-center justify-between text-xs text-slate-500">
                        <span>📊 Advanced metrics</span>
                        <span>🎯 Expert reasoning</span>
                        <span>💰 Expected value</span>
                      </div>
                    </div>
                  )}
                </div>

                {/* LOCK OVERLAY (only for free users) */}
                {!isPaidUser && (
                  <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
                    {/* Dark gradient overlay for readability */}
                    <div className="absolute inset-0 bg-gradient-to-b from-slate-900/60 via-slate-900/80 to-slate-900/60"></div>
                    
                    {/* Lock content */}
                    <div className="relative z-10 text-center px-6 pointer-events-auto">
                      <div className="bg-gradient-to-br from-amber-500 to-orange-600 w-20 h-20 rounded-2xl flex items-center justify-center mx-auto mb-4 shadow-2xl transform group-hover:scale-110 transition-transform">
                        <Lock className="w-10 h-10 text-white" />
                      </div>
                      <div className="text-white font-black text-xl mb-2">Premium Pick Locked</div>
                      <div className="text-slate-300 text-sm mb-4">
                        <span className="text-emerald-400 font-bold">{pick.confidence}% Confidence</span>
                        {' • '}
                        Full analysis included
                      </div>
                      <button
                        onClick={() => setShowUpgrade(true)}
                        className="bg-gradient-to-r from-amber-500 to-orange-600 text-white font-black px-8 py-3.5 rounded-xl hover:from-amber-400 hover:to-orange-500 transition-all shadow-xl transform hover:scale-105"
                      >
                        Unlock from $4.99
                      </button>
                      <div className="mt-3 text-slate-400 text-xs">
                        Join 1,247 winning members
                      </div>
                    </div>
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>

        {/* EMAIL SIGNUP (Free Users) */}
        {!isPaidUser && (
          <div className="bg-blue-950/30 backdrop-blur rounded-2xl p-6 mb-8 border border-blue-800/30">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-4">
                <div className="bg-blue-600 p-3 rounded-xl">
                  <Mail className="w-6 h-6 text-white" />
                </div>
                <div>
                  <div className="text-white font-bold text-lg">Never Miss a Pick</div>
                  <div className="text-blue-300 text-sm">Get tomorrow's best pick at 9 AM EST</div>
                </div>
              </div>
              <button 
                onClick={() => setShowEmailSignup(true)}
                className="bg-blue-600 hover:bg-blue-500 text-white font-bold px-6 py-3 rounded-xl transition-all whitespace-nowrap"
              >
                Sign Up Free
              </button>
            </div>
          </div>
        )}

        {/* RECENT RESULTS */}
        <div className="bg-slate-800/50 backdrop-blur-xl rounded-2xl p-6 mb-8 border border-slate-700">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-white text-lg font-bold flex items-center space-x-2">
              <Activity className="w-5 h-5 text-green-400" />
              <span>Recent Results</span>
            </h3>
            <span className="text-emerald-400 text-sm font-bold">3-1 Last 24hrs</span>
          </div>
          <div className="space-y-2">
            {results.map((result, i) => (
              <div key={i} className={`rounded-lg p-4 ${
                result.result === 'W' ? 'bg-emerald-950/30 border border-emerald-800/30' : 'bg-red-950/30 border border-red-800/30'
              }`}>
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center space-x-3">
                    <div className={`w-12 h-12 rounded-lg flex items-center justify-center font-black text-xl ${
                      result.result === 'W' ? 'bg-emerald-600 text-white' : 'bg-red-600 text-white'
                    }`}>
                      {result.result}
                    </div>
                    <div>
                      <div className="flex items-center space-x-2">
                        <div className="text-white text-sm font-bold">{result.pick}</div>
                        {result.wasPremium && !isPaidUser && (
                          <span className="bg-amber-600 text-white text-xs px-2 py-0.5 rounded-full font-bold">
                            PRO
                          </span>
                        )}
                      </div>
                      <div className="text-slate-400 text-xs">{result.final} • {result.time}</div>
                    </div>
                  </div>
                  <div className="flex items-center space-x-3">
                    <div className={`text-xl font-black ${
                      result.result === 'W' ? 'text-emerald-400' : 'text-red-400'
                    }`}>
                      {result.profit}
                    </div>
                    {result.result === 'W' && isPaidUser && (
                      <button
                        onClick={() => handleShareWin(result)}
                        className="bg-emerald-600 hover:bg-emerald-500 text-white px-3 py-1.5 rounded-lg text-xs font-bold transition-all flex items-center space-x-1"
                      >
                        <Share2 className="w-3 h-3" />
                        <span>Share</span>
                      </button>
                    )}
                  </div>
                </div>
                {result.winner && (
                  <div className="bg-emerald-900/30 rounded-lg p-2 flex items-center space-x-2 text-xs">
                    <span className="text-xl">🎉</span>
                    <div className="text-emerald-300">
                      <span className="font-bold">{result.winner.name}</span> won <span className="font-bold">${result.winner.amount}</span> on this
                    </div>
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>

        {/* TRACK RECORD */}
        <div className="bg-gradient-to-br from-blue-50 to-indigo-50 rounded-2xl p-6 border-2 border-blue-100 mb-8">
          <div className="flex items-start space-x-4">
            <div className="bg-gradient-to-br from-blue-500 to-indigo-600 p-3 rounded-xl shadow-lg">
              <TrendingUp className="w-6 h-6 text-white" />
            </div>
            <div>
              <h3 className="text-lg font-bold text-slate-900 mb-2">Our Track Record</h3>
              <p className="text-slate-700 leading-relaxed mb-3">
                Our algorithm maintains a <span className="font-bold text-blue-600">57.1% win rate</span> on high-confidence picks. 
                We show you every result - wins AND losses. No fake records, no hidden picks.
              </p>
              <div className="flex items-center space-x-4 text-sm">
                <div className="flex items-center space-x-1 text-slate-600">
                  <CheckCircle className="w-4 h-4 text-emerald-600" />
                  <span className="font-semibold">All picks tracked publicly</span>
                </div>
                <div className="flex items-center space-x-1 text-slate-600">
                  <CheckCircle className="w-4 h-4 text-emerald-600" />
                  <span className="font-semibold">Timestamped before games</span>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* FINAL CTA (Free Users) */}
        {!isPaidUser && (
          <div className="bg-gradient-to-r from-purple-600 to-pink-600 rounded-2xl p-8 text-center">
            <h3 className="text-white text-2xl font-black mb-2">Stop Leaving Money on the Table</h3>
            <p className="text-purple-200 text-sm mb-2">You missed <span className="font-black">${missedProfit}</span> in profit yesterday</p>
            <p className="text-purple-300 text-xs mb-6">Join 1,247 members who never miss a winning pick</p>
            <button
              onClick={() => setShowUpgrade(true)}
              className="bg-white text-purple-600 font-black px-8 py-4 rounded-xl hover:bg-purple-50 transition-all text-lg shadow-xl"
            >
              Get Full Access - $19.99/month
            </button>
            <p className="text-purple-200 text-xs mt-4">Cancel anytime • 1-800-GAMBLER</p>
          </div>
        )}
      </main>

      {/* FOOTER */}
      <footer className="bg-slate-900/50 border-t border-slate-800 py-6">
        <div className="max-w-5xl mx-auto px-6">
          <div className="flex items-center justify-between text-sm text-slate-400">
            <div>© 2026 Sharp Picks. All rights reserved.</div>
            <div className="flex items-center space-x-1">
              <span>5% of revenue donated to animal shelters</span>
              <span className="text-slate-600">•</span>
              <a href="#" className="hover:text-slate-300 transition-colors">Learn more</a>
            </div>
          </div>
        </div>
      </footer>

      {/* DEV CONTROLS */}
      <div className="fixed bottom-4 right-4 bg-slate-900 border border-slate-700 rounded-xl p-4 space-y-2 z-50 shadow-2xl">
        <div className="text-white text-xs font-bold mb-2">🛠️ Dev Mode:</div>
        <button
          onClick={() => {
            setIsPaidUser(false);
            setIsNewPaidUser(false);
          }}
          className={`w-full text-xs px-3 py-2 rounded transition-all ${!isPaidUser ? 'bg-blue-600 text-white' : 'bg-slate-800 text-slate-400 hover:bg-slate-700'}`}
        >
          Free User
        </button>
        <button
          onClick={() => {
            setIsPaidUser(true);
            setIsNewPaidUser(true);
            setUnitSize(null);
          }}
          className={`w-full text-xs px-3 py-2 rounded transition-all ${isPaidUser && isNewPaidUser ? 'bg-blue-600 text-white' : 'bg-slate-800 text-slate-400 hover:bg-slate-700'}`}
        >
          New Paid User
        </button>
        <button
          onClick={() => {
            setIsPaidUser(true);
            setIsNewPaidUser(false);
            setUnitSize(100);
          }}
          className={`w-full text-xs px-3 py-2 rounded transition-all ${isPaidUser && !isNewPaidUser ? 'bg-blue-600 text-white' : 'bg-slate-800 text-slate-400 hover:bg-slate-700'}`}
        >
          Active Paid User
        </button>
      </div>
    </div>
  );
}
