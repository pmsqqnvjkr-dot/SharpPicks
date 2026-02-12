import { useState, useEffect } from 'react';
import { useAuth } from '../../hooks/useAuth';
import { apiGet, apiPost, apiDelete } from '../../hooks/useApi';

export default function BetTrackingScreen({ onBack, pickToTrack }) {
  const { user } = useAuth();
  const [bets, setBets] = useState([]);
  const [loading, setLoading] = useState(true);
  const [stats, setStats] = useState(null);
  const [confirmDelete, setConfirmDelete] = useState(null);
  const [activeView, setActiveView] = useState('dashboard');
  const [showTrackModal, setShowTrackModal] = useState(false);
  const [selectedPick, setSelectedPick] = useState(null);

  useEffect(() => {
    if (user) loadBets();
    else setLoading(false);
  }, [user]);

  useEffect(() => {
    if (pickToTrack && user) {
      setSelectedPick(pickToTrack);
      setShowTrackModal(true);
    }
  }, [pickToTrack, user]);

  const loadBets = async () => {
    try {
      const [betsData, statsData] = await Promise.all([
        apiGet('/bets'),
        apiGet('/user/stats'),
      ]);
      setBets(betsData.bets || []);
      setStats(statsData);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  const handleTrackPick = (pick) => {
    setSelectedPick(pick);
    setShowTrackModal(true);
  };

  const handleSubmitBet = async (betData) => {
    try {
      const res = await apiPost('/bets', betData);
      if (res.success) {
        setShowTrackModal(false);
        setSelectedPick(null);
        loadBets();
      } else {
        alert(res.error || 'Failed to track bet');
      }
    } catch (e) {
      alert('Failed to track bet');
    }
  };

  const handleMarkResult = async (betId, result) => {
    const bet = bets.find(b => b.id === betId);
    if (!bet) return;

    let profit = 0;
    if (result === 'W') {
      if (bet.odds < 0) {
        profit = bet.bet_amount * (100 / Math.abs(bet.odds));
      } else {
        profit = bet.bet_amount * (bet.odds / 100);
      }
    } else if (result === 'L') {
      profit = -bet.bet_amount;
    }

    try {
      await apiPost(`/bets/${betId}/result`, { result, profit: Math.round(profit * 100) / 100 });
      loadBets();
    } catch (e) {
      alert('Failed to update result');
    }
  };

  const handleDelete = async (betId) => {
    try {
      await apiDelete(`/bets/${betId}`);
      setConfirmDelete(null);
      loadBets();
    } catch (e) {
      alert('Failed to delete bet');
    }
  };

  if (!user) {
    return (
      <div style={{ padding: '0' }}>
        <ScreenHeader onBack={onBack} title="My Bets" />
        <div style={{ padding: '40px 20px', textAlign: 'center' }}>
          <div style={{
            width: '56px', height: '56px', borderRadius: '14px',
            backgroundColor: 'var(--surface-1)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            margin: '0 auto 16px',
          }}>
            <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="var(--text-tertiary)" strokeWidth="1.5">
              <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2z"/>
              <path d="M12 6v6l4 2"/>
            </svg>
          </div>
          <p style={{ color: 'var(--text-secondary)', fontSize: '14px', lineHeight: '1.6' }}>
            Sign in to track your bets and build your personal performance dashboard.
          </p>
        </div>
      </div>
    );
  }

  const hasBets = stats && stats.totalBets > 0;
  const pendingBets = bets.filter(b => !b.result);
  const settledBets = bets.filter(b => b.result);

  return (
    <div style={{ padding: '0', paddingBottom: '100px' }}>
      <ScreenHeader onBack={onBack} title="My Bets" />

      <div style={{ padding: '0 20px 12px', display: 'flex', gap: '8px' }}>
        <ViewToggle label="Dashboard" active={activeView === 'dashboard'} onClick={() => setActiveView('dashboard')} />
        <ViewToggle label="Bet Log" active={activeView === 'log'} onClick={() => setActiveView('log')} />
      </div>

      {activeView === 'dashboard' ? (
        <div style={{ padding: '0 20px' }}>
          {loading ? (
            <div style={{ padding: '40px 0', textAlign: 'center' }}>
              <p style={{ color: 'var(--text-secondary)', fontSize: '14px' }}>Loading your dashboard...</p>
            </div>
          ) : !hasBets ? (
            <EmptyDashboard onTrack={() => setShowTrackModal(true)} />
          ) : (
            <>
              <SectionCard>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                  <StatCard
                    label="P&L"
                    value={`${stats.totalProfit >= 0 ? '+' : ''}$${Math.abs(stats.totalProfit).toFixed(0)}`}
                    color={stats.totalProfit >= 0 ? 'var(--green-profit)' : 'var(--red-loss)'}
                    large
                  />
                  <StatCard
                    label="ROI"
                    value={`${stats.roi >= 0 ? '+' : ''}${stats.roi}%`}
                    color={stats.roi >= 0 ? 'var(--green-profit)' : 'var(--red-loss)'}
                    large
                  />
                  <StatCard label="Record" value={`${stats.wins}-${stats.losses}${stats.pushes ? `-${stats.pushes}` : ''}`} />
                  <StatCard label="Win Rate" value={`${stats.winRate}%`} />
                </div>
              </SectionCard>

              <SectionCard title="Your Equity Curve">
                {stats.equityCurve && stats.equityCurve.length > 1 ? (
                  <PersonalEquityChart data={stats.equityCurve} />
                ) : (
                  <div style={{
                    textAlign: 'center', padding: '24px',
                    color: 'var(--text-tertiary)', fontSize: '13px',
                  }}>
                    Need at least 2 settled bets to show your equity curve.
                  </div>
                )}
              </SectionCard>

              <SectionCard title="Streak">
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '10px' }}>
                  <MiniCard
                    label="Current"
                    value={`${stats.streak?.current || 0}${stats.streak?.currentType === 'W' ? 'W' : stats.streak?.currentType === 'L' ? 'L' : ''}`}
                    color={stats.streak?.currentType === 'W' ? 'var(--green-profit)' : stats.streak?.currentType === 'L' ? 'var(--red-loss)' : 'var(--text-primary)'}
                  />
                  <MiniCard label="Best Win" value={`${stats.streak?.bestWin || 0}W`} color="var(--green-profit)" />
                  <MiniCard label="Worst Loss" value={`${stats.streak?.worstLoss || 0}L`} color="var(--red-loss)" />
                </div>
                {stats.equityCurve && stats.equityCurve.length > 0 && (
                  <div style={{ marginTop: '14px', display: 'flex', gap: '4px', flexWrap: 'wrap' }}>
                    {stats.equityCurve.slice(-20).map((p, i) => (
                      <div key={i} style={{
                        width: '24px', height: '24px', borderRadius: '4px',
                        backgroundColor: p.result === 'W' ? 'rgba(52, 211, 153, 0.2)' : 'rgba(239, 68, 68, 0.2)',
                        border: `1px solid ${p.result === 'W' ? 'rgba(52, 211, 153, 0.4)' : 'rgba(239, 68, 68, 0.4)'}`,
                        display: 'flex', alignItems: 'center', justifyContent: 'center',
                        fontSize: '10px', fontWeight: 600, fontFamily: 'var(--font-mono)',
                        color: p.result === 'W' ? 'var(--green-profit)' : 'var(--red-loss)',
                      }}>
                        {p.result === 'W' ? 'W' : 'L'}
                      </div>
                    ))}
                  </div>
                )}
              </SectionCard>

              <SectionCard title="Betting Details">
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px' }}>
                  <MiniCard label="Total Risked" value={`$${stats.totalRisked?.toFixed(0) || 0}`} />
                  <MiniCard label="Avg Bet" value={`$${stats.avgBet?.toFixed(0) || 0}`} />
                  <MiniCard label="Biggest Win" value={`+$${Math.abs(stats.biggestWin || 0).toFixed(0)}`} color="var(--green-profit)" />
                  <MiniCard label="Biggest Loss" value={`-$${Math.abs(stats.biggestLoss || 0).toFixed(0)}`} color="var(--red-loss)" />
                </div>
              </SectionCard>

              {stats.monthlyBreakdown && stats.monthlyBreakdown.length > 0 && (
                <SectionCard title="Monthly Breakdown">
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                    {stats.monthlyBreakdown.map((m, i) => (
                      <div key={i} style={{
                        display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                        padding: '12px 14px', backgroundColor: 'var(--surface-2)', borderRadius: '10px',
                      }}>
                        <div>
                          <div style={{ fontSize: '14px', fontWeight: 500, color: 'var(--text-primary)' }}>
                            {m.label}
                          </div>
                          <div style={{
                            fontFamily: 'var(--font-mono)', fontSize: '12px',
                            color: 'var(--text-tertiary)', marginTop: '2px',
                          }}>
                            {m.wins}W-{m.losses}L ({m.bets} bets) · {m.roi >= 0 ? '+' : ''}{m.roi}% ROI
                          </div>
                        </div>
                        <div style={{
                          fontFamily: 'var(--font-mono)', fontSize: '14px', fontWeight: 600,
                          color: m.pnl >= 0 ? 'var(--green-profit)' : 'var(--red-loss)',
                        }}>
                          {m.pnl >= 0 ? '+' : ''}${Math.abs(m.pnl).toFixed(0)}
                        </div>
                      </div>
                    ))}
                  </div>
                </SectionCard>
              )}

              <div style={{ padding: '4px 0 12px' }}>
                <button onClick={() => setShowTrackModal(true)} style={{
                  width: '100%', padding: '14px',
                  backgroundColor: 'var(--blue-primary)', color: '#fff',
                  border: 'none', borderRadius: '12px',
                  fontSize: '14px', fontWeight: 600, cursor: 'pointer',
                  fontFamily: 'var(--font-sans)',
                  display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '8px',
                }}>
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                    <line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/>
                  </svg>
                  Track a Bet
                </button>
              </div>
            </>
          )}
        </div>
      ) : (
        <div style={{ padding: '0 20px' }}>
          <div style={{ marginBottom: '12px' }}>
            <button onClick={() => setShowTrackModal(true)} style={{
              width: '100%', padding: '14px',
              backgroundColor: 'var(--blue-primary)', color: '#fff',
              border: 'none', borderRadius: '12px',
              fontSize: '14px', fontWeight: 600, cursor: 'pointer',
              fontFamily: 'var(--font-sans)',
              display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '8px',
            }}>
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                <line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/>
              </svg>
              Track a Bet
            </button>
          </div>

          {loading ? (
            <p style={{ color: 'var(--text-secondary)', fontSize: '14px', textAlign: 'center', padding: '40px 0' }}>
              Loading bets...
            </p>
          ) : bets.length === 0 ? (
            <div style={{
              backgroundColor: 'var(--surface-1)', borderRadius: '16px',
              padding: '32px 24px', border: '1px solid var(--stroke-subtle)',
              textAlign: 'center',
            }}>
              <div style={{
                width: '48px', height: '48px', borderRadius: '12px',
                backgroundColor: 'var(--surface-2)',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                margin: '0 auto 16px',
              }}>
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="var(--text-tertiary)" strokeWidth="2">
                  <rect x="2" y="3" width="20" height="14" rx="2"/><line x1="8" y1="21" x2="16" y2="21"/><line x1="12" y1="17" x2="12" y2="21"/>
                </svg>
              </div>
              <p style={{ fontSize: '14px', color: 'var(--text-secondary)', lineHeight: '1.6' }}>
                No bets tracked yet. When a pick is published, track your wager here to monitor your personal performance.
              </p>
            </div>
          ) : (
            <>
              {pendingBets.length > 0 && (
                <div style={{ marginBottom: '12px' }}>
                  <h3 style={{
                    fontSize: '11px', fontWeight: 600, color: 'var(--text-tertiary)',
                    textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: '8px',
                  }}>Pending ({pendingBets.length})</h3>
                  <div style={{
                    backgroundColor: 'var(--surface-1)', borderRadius: '16px',
                    overflow: 'hidden', border: '1px solid var(--stroke-subtle)',
                  }}>
                    {pendingBets.map((bet, i) => (
                      <BetRow key={bet.id} bet={bet} isLast={i === pendingBets.length - 1}
                        onMarkResult={handleMarkResult} confirmDelete={confirmDelete}
                        setConfirmDelete={setConfirmDelete} onDelete={handleDelete} />
                    ))}
                  </div>
                </div>
              )}

              {settledBets.length > 0 && (
                <div>
                  <h3 style={{
                    fontSize: '11px', fontWeight: 600, color: 'var(--text-tertiary)',
                    textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: '8px',
                  }}>Settled ({settledBets.length})</h3>
                  <div style={{
                    backgroundColor: 'var(--surface-1)', borderRadius: '16px',
                    overflow: 'hidden', border: '1px solid var(--stroke-subtle)',
                  }}>
                    {settledBets.map((bet, i) => (
                      <BetRow key={bet.id} bet={bet} isLast={i === settledBets.length - 1}
                        onMarkResult={handleMarkResult} confirmDelete={confirmDelete}
                        setConfirmDelete={setConfirmDelete} onDelete={handleDelete} />
                    ))}
                  </div>
                </div>
              )}
            </>
          )}
        </div>
      )}

      {showTrackModal && (
        <TrackBetModal
          initialPick={selectedPick}
          onClose={() => { setShowTrackModal(false); setSelectedPick(null); }}
          onSubmit={handleSubmitBet}
        />
      )}
    </div>
  );
}

function TrackBetModal({ initialPick, onClose, onSubmit }) {
  const [step, setStep] = useState(initialPick ? 'wager' : 'picks');
  const [picks, setPicks] = useState([]);
  const [loadingPicks, setLoadingPicks] = useState(!initialPick);
  const [selected, setSelected] = useState(initialPick || null);
  const [amount, setAmount] = useState('100');
  const [odds, setOdds] = useState('-110');
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (!initialPick) {
      loadTrackablePicks();
    }
  }, []);

  const loadTrackablePicks = async () => {
    try {
      const data = await apiGet('/bets/trackable');
      setPicks(data.picks || []);
    } catch (e) {
      console.error(e);
    } finally {
      setLoadingPicks(false);
    }
  };

  const handleSelectPick = (pick) => {
    if (pick.already_tracked) return;
    setSelected(pick);
    setStep('wager');
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!selected) return;
    setSubmitting(true);
    await onSubmit({
      pick_id: selected.id,
      bet_amount: parseInt(amount) || 100,
      odds: parseInt(odds) || -110,
    });
    setSubmitting(false);
  };

  const toWin = (() => {
    const amt = parseInt(amount) || 100;
    const o = parseInt(odds) || -110;
    if (o < 0) return (amt * (100 / Math.abs(o))).toFixed(2);
    return (amt * (o / 100)).toFixed(2);
  })();

  return (
    <div style={{
      position: 'fixed', inset: 0, backgroundColor: 'rgba(0,0,0,0.7)',
      display: 'flex', alignItems: 'flex-end', justifyContent: 'center',
      zIndex: 1000,
    }} onClick={onClose}>
      <div style={{
        backgroundColor: 'var(--surface-0)', borderRadius: '20px 20px 0 0',
        padding: '24px 20px 32px', width: '100%', maxWidth: '480px',
        maxHeight: '80vh', overflowY: 'auto',
      }} onClick={e => e.stopPropagation()}>
        <div style={{
          display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px',
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            {step === 'wager' && !initialPick && (
              <button onClick={() => { setStep('picks'); setSelected(null); }} style={{
                background: 'none', border: 'none', cursor: 'pointer',
                color: 'var(--text-tertiary)', padding: '4px',
              }}>
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <polyline points="15 18 9 12 15 6"/>
                </svg>
              </button>
            )}
            <h2 style={{
              fontFamily: 'var(--font-serif)', fontSize: '20px',
              fontWeight: 600, color: 'var(--text-primary)',
            }}>{step === 'picks' ? 'Select a Pick' : 'Enter Your Wager'}</h2>
          </div>
          <button onClick={onClose} style={{
            background: 'none', border: 'none', cursor: 'pointer',
            color: 'var(--text-tertiary)', padding: '4px',
          }}>
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
            </svg>
          </button>
        </div>

        {step === 'picks' ? (
          <div>
            {loadingPicks ? (
              <div style={{ padding: '40px 0', textAlign: 'center' }}>
                <p style={{ color: 'var(--text-secondary)', fontSize: '14px' }}>Loading picks...</p>
              </div>
            ) : picks.length === 0 ? (
              <div style={{ padding: '40px 0', textAlign: 'center' }}>
                <p style={{ color: 'var(--text-secondary)', fontSize: '14px', lineHeight: '1.6' }}>
                  No picks available to track yet. Picks appear here when the model publishes them.
                </p>
              </div>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                {picks.map(p => (
                  <button
                    key={p.id}
                    onClick={() => handleSelectPick(p)}
                    disabled={p.already_tracked}
                    style={{
                      width: '100%', textAlign: 'left',
                      padding: '14px 16px',
                      backgroundColor: p.already_tracked ? 'var(--surface-2)' : 'var(--surface-1)',
                      border: '1px solid var(--stroke-subtle)',
                      borderRadius: '12px', cursor: p.already_tracked ? 'default' : 'pointer',
                      opacity: p.already_tracked ? 0.5 : 1,
                      transition: 'background-color 0.15s',
                    }}
                  >
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <div>
                        <div style={{
                          fontFamily: 'var(--font-mono)', fontSize: '10px', fontWeight: 600,
                          letterSpacing: '1.2px', textTransform: 'uppercase',
                          color: 'var(--text-tertiary)', marginBottom: '4px',
                        }}>
                          {p.game_date}
                        </div>
                        <div style={{ fontSize: '14px', fontWeight: 500, color: 'var(--text-primary)' }}>
                          {p.away_team} @ {p.home_team}
                        </div>
                        <div style={{
                          fontSize: '13px', color: 'var(--blue-primary)', fontWeight: 600, marginTop: '4px',
                        }}>
                          {p.side} {p.line > 0 ? `+${p.line}` : p.line}
                        </div>
                      </div>
                      <div style={{ textAlign: 'right', flexShrink: 0 }}>
                        {p.already_tracked ? (
                          <span style={{
                            fontFamily: 'var(--font-mono)', fontSize: '10px', fontWeight: 600,
                            color: 'var(--text-tertiary)', textTransform: 'uppercase',
                          }}>Tracked</span>
                        ) : p.result && p.result !== 'pending' ? (
                          <span style={{
                            fontFamily: 'var(--font-mono)', fontSize: '12px', fontWeight: 700,
                            color: p.result === 'W' ? 'var(--green-profit)' : 'var(--red-loss)',
                          }}>{p.result}</span>
                        ) : (
                          <span style={{
                            fontFamily: 'var(--font-mono)', fontSize: '11px', fontWeight: 500,
                            color: 'var(--text-tertiary)',
                          }}>
                            {p.edge_pct.toFixed(1)}% edge
                          </span>
                        )}
                      </div>
                    </div>
                  </button>
                ))}
              </div>
            )}
          </div>
        ) : (
          <div>
            <div style={{
              backgroundColor: 'var(--surface-1)', borderRadius: '12px',
              padding: '14px 16px', marginBottom: '16px',
              border: '1px solid var(--stroke-subtle)',
            }}>
              <div style={{
                fontFamily: 'var(--font-mono)', fontSize: '10px', fontWeight: 600,
                letterSpacing: '1.2px', textTransform: 'uppercase',
                color: 'var(--text-tertiary)', marginBottom: '4px',
              }}>{selected?.game_date}</div>
              <div style={{ fontSize: '14px', fontWeight: 500, color: 'var(--text-primary)' }}>
                {selected?.away_team} @ {selected?.home_team}
              </div>
              <div style={{
                fontSize: '15px', color: 'var(--blue-primary)', fontWeight: 700, marginTop: '6px',
              }}>
                {selected?.side} {selected?.line > 0 ? `+${selected.line}` : selected?.line}
              </div>
            </div>

            <form onSubmit={handleSubmit}>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                <FormField label="Wager ($)" placeholder="100" value={amount} onChange={setAmount} type="number" />
                <FormField label="Odds" placeholder="-110" value={odds} onChange={setOdds} type="number" />
              </div>

              <div style={{
                backgroundColor: 'var(--surface-1)', borderRadius: '10px',
                padding: '12px 16px', marginBottom: '16px',
                display: 'flex', justifyContent: 'space-between', alignItems: 'center',
              }}>
                <span style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>To win</span>
                <span style={{
                  fontFamily: 'var(--font-mono)', fontSize: '16px',
                  fontWeight: 600, color: 'var(--green-profit)',
                }}>${toWin}</span>
              </div>

              <button type="submit" disabled={submitting} style={{
                width: '100%', padding: '14px',
                backgroundColor: 'var(--blue-primary)', color: '#fff',
                border: 'none', borderRadius: '12px',
                fontSize: '15px', fontWeight: 600, cursor: 'pointer',
                fontFamily: 'var(--font-sans)',
                opacity: submitting ? 0.5 : 1,
              }}>
                {submitting ? 'Tracking...' : 'Track This Bet'}
              </button>
            </form>
          </div>
        )}
      </div>
    </div>
  );
}

function EmptyDashboard({ onTrack }) {
  return (
    <div style={{
      backgroundColor: 'var(--surface-1)', borderRadius: '16px',
      padding: '40px 24px', border: '1px solid var(--stroke-subtle)',
      textAlign: 'center',
    }}>
      <div style={{
        width: '64px', height: '64px', borderRadius: '16px',
        backgroundColor: 'var(--surface-2)',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        margin: '0 auto 20px',
      }}>
        <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="var(--blue-primary)" strokeWidth="1.5">
          <path d="M3 3v18h18"/>
          <path d="M7 16l4-4 4 4 5-5"/>
        </svg>
      </div>
      <h3 style={{
        fontFamily: 'var(--font-serif)', fontSize: '18px',
        fontWeight: 600, color: 'var(--text-primary)', marginBottom: '8px',
      }}>Your personal dashboard</h3>
      <p style={{
        fontSize: '13px', color: 'var(--text-secondary)', lineHeight: '1.6', marginBottom: '20px',
      }}>
        Track your wagers on Sharp Picks and watch your personal equity curve, win streaks, and ROI build over time.
      </p>
      <button onClick={onTrack} style={{
        padding: '12px 24px',
        backgroundColor: 'var(--blue-primary)', color: '#fff',
        border: 'none', borderRadius: '10px',
        fontSize: '14px', fontWeight: 600, cursor: 'pointer',
        fontFamily: 'var(--font-sans)',
        display: 'inline-flex', alignItems: 'center', gap: '8px',
      }}>
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
          <line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/>
        </svg>
        Track Your First Bet
      </button>
    </div>
  );
}

function BetRow({ bet, isLast, onMarkResult, confirmDelete, setConfirmDelete, onDelete }) {
  const pickResultLabel = bet.pick_result && bet.pick_result !== 'pending'
    ? bet.pick_result : null;

  return (
    <div style={{
      padding: '14px 20px',
      borderBottom: isLast ? 'none' : '1px solid var(--stroke-subtle)',
    }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <div style={{ flex: 1 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <div style={{ fontSize: '14px', fontWeight: 500, color: 'var(--text-primary)' }}>{bet.pick}</div>
            {bet.pick_id && (
              <span style={{
                fontFamily: 'var(--font-mono)', fontSize: '9px', fontWeight: 600,
                padding: '2px 6px', borderRadius: '4px',
                backgroundColor: 'rgba(79, 134, 247, 0.15)', color: 'var(--blue-primary)',
                textTransform: 'uppercase', letterSpacing: '0.5px',
              }}>SP</span>
            )}
          </div>
          <div style={{ fontSize: '12px', color: 'var(--text-tertiary)', marginTop: '2px' }}>{bet.game}</div>
          <div style={{
            fontSize: '11px', color: 'var(--text-tertiary)', marginTop: '4px',
            fontFamily: 'var(--font-mono)',
          }}>
            ${bet.bet_amount} at {bet.odds > 0 ? `+${bet.odds}` : bet.odds}
            {pickResultLabel && (
              <span style={{
                marginLeft: '8px',
                color: pickResultLabel === 'W' ? 'var(--green-profit)' : 'var(--red-loss)',
                fontWeight: 600,
              }}>
                Pick: {pickResultLabel}
              </span>
            )}
          </div>
        </div>
        <div style={{ textAlign: 'right', flexShrink: 0 }}>
          {bet.result ? (
            <div style={{
              fontFamily: 'var(--font-mono)', fontSize: '14px', fontWeight: 600,
              color: bet.result === 'W' ? 'var(--green-profit)' : 'var(--red-loss)',
            }}>
              {bet.result === 'W' ? `+$${Math.abs(bet.profit).toFixed(0)}` : `-$${Math.abs(bet.profit).toFixed(0)}`}
            </div>
          ) : (
            <div style={{ display: 'flex', gap: '6px' }}>
              <button onClick={() => onMarkResult(bet.id, 'W')} style={{
                padding: '4px 10px', fontSize: '11px', fontWeight: 600,
                backgroundColor: 'rgba(52, 211, 153, 0.1)', color: 'var(--green-profit)',
                border: '1px solid rgba(52, 211, 153, 0.3)', borderRadius: '6px',
                cursor: 'pointer', fontFamily: 'var(--font-mono)',
              }}>W</button>
              <button onClick={() => onMarkResult(bet.id, 'L')} style={{
                padding: '4px 10px', fontSize: '11px', fontWeight: 600,
                backgroundColor: 'rgba(239, 68, 68, 0.1)', color: 'var(--red-loss)',
                border: '1px solid rgba(239, 68, 68, 0.3)', borderRadius: '6px',
                cursor: 'pointer', fontFamily: 'var(--font-mono)',
              }}>L</button>
            </div>
          )}
        </div>
      </div>
      {confirmDelete === bet.id ? (
        <div style={{ marginTop: '8px', display: 'flex', gap: '8px', alignItems: 'center' }}>
          <span style={{ fontSize: '12px', color: 'var(--text-tertiary)' }}>Remove this bet?</span>
          <button onClick={() => onDelete(bet.id)} style={{
            padding: '3px 10px', fontSize: '11px', fontWeight: 600,
            backgroundColor: 'rgba(239, 68, 68, 0.1)', color: 'var(--red-loss)',
            border: '1px solid rgba(239, 68, 68, 0.3)', borderRadius: '6px', cursor: 'pointer',
          }}>Yes</button>
          <button onClick={() => setConfirmDelete(null)} style={{
            padding: '3px 10px', fontSize: '11px',
            backgroundColor: 'transparent', color: 'var(--text-tertiary)',
            border: '1px solid var(--stroke-subtle)', borderRadius: '6px', cursor: 'pointer',
          }}>No</button>
        </div>
      ) : (
        <button onClick={() => setConfirmDelete(bet.id)} style={{
          marginTop: '6px', background: 'none', border: 'none',
          fontSize: '11px', color: 'var(--text-tertiary)', cursor: 'pointer',
          padding: '2px 0', fontFamily: 'var(--font-sans)',
        }}>Remove</button>
      )}
    </div>
  );
}

function ViewToggle({ label, active, onClick }) {
  return (
    <button onClick={onClick} style={{
      flex: 1, padding: '10px 16px',
      backgroundColor: active ? 'var(--surface-1)' : 'transparent',
      color: active ? 'var(--text-primary)' : 'var(--text-tertiary)',
      border: active ? '1px solid var(--stroke-subtle)' : '1px solid transparent',
      borderRadius: '10px', fontSize: '13px', fontWeight: 600,
      cursor: 'pointer', fontFamily: 'var(--font-sans)',
      transition: 'all 0.2s',
    }}>{label}</button>
  );
}

function PersonalEquityChart({ data }) {
  const height = 160;
  const width = 320;
  const padL = 45;
  const padR = 10;
  const padT = 10;
  const padB = 30;

  const values = data.map(d => d.value);
  const minVal = Math.min(0, ...values);
  const maxVal = Math.max(0, ...values);
  const range = maxVal - minVal || 1;

  const chartW = width - padL - padR;
  const chartH = height - padT - padB;

  const getX = (i) => padL + (i / (data.length - 1)) * chartW;
  const getY = (v) => padT + chartH - ((v - minVal) / range) * chartH;

  const zeroY = getY(0);
  const linePoints = data.map((d, i) => `${getX(i)},${getY(d.value)}`).join(' ');
  const areaPoints = [
    `${getX(0)},${zeroY}`,
    ...data.map((d, i) => `${getX(i)},${getY(d.value)}`),
    `${getX(data.length - 1)},${zeroY}`,
  ].join(' ');

  const lastValue = data[data.length - 1].value;
  const isPositive = lastValue >= 0;

  const ticks = [];
  const steps = 4;
  for (let i = 0; i <= steps; i++) {
    const v = minVal + (range / steps) * i;
    ticks.push({ value: Math.round(v), y: getY(v) });
  }

  return (
    <div>
      <svg viewBox={`0 0 ${width} ${height}`} style={{ width: '100%' }}>
        <defs>
          <linearGradient id="personalEquityGrad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={isPositive ? 'var(--green-profit)' : 'var(--red-loss)'} stopOpacity="0.3" />
            <stop offset="100%" stopColor={isPositive ? 'var(--green-profit)' : 'var(--red-loss)'} stopOpacity="0" />
          </linearGradient>
        </defs>

        {ticks.map((t, i) => (
          <g key={i}>
            <line x1={padL} y1={t.y} x2={width - padR} y2={t.y}
              stroke="var(--stroke-subtle)" strokeWidth="0.5" strokeDasharray="3,3" />
            <text x={padL - 6} y={t.y + 3}
              textAnchor="end" fill="var(--text-tertiary)"
              fontSize="8" fontFamily="var(--font-mono)">
              ${t.value}
            </text>
          </g>
        ))}

        <polygon points={areaPoints} fill="url(#personalEquityGrad)" />

        <polyline points={linePoints} fill="none"
          stroke={isPositive ? 'var(--green-profit)' : 'var(--red-loss)'}
          strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />

        {data.map((d, i) => (
          <circle key={i}
            cx={getX(i)} cy={getY(d.value)} r={i === data.length - 1 ? 4 : 3}
            fill={d.result === 'W' ? 'var(--green-profit)' : 'var(--red-loss)'}
            stroke="var(--surface-1)" strokeWidth="1.5" />
        ))}

        {data.length <= 12 && data.map((d, i) => {
          const label = d.date ? d.date.substring(5) : '';
          return (
            <text key={i} x={getX(i)} y={height - 5}
              textAnchor="middle" fill="var(--text-tertiary)"
              fontSize="7" fontFamily="var(--font-mono)">
              {label}
            </text>
          );
        })}
      </svg>
    </div>
  );
}

function FormField({ label, placeholder, value, onChange, type = 'text' }) {
  return (
    <div style={{ marginBottom: '12px' }}>
      <label style={{
        display: 'block', fontSize: '12px', fontWeight: 600,
        color: 'var(--text-tertiary)', textTransform: 'uppercase',
        letterSpacing: '0.05em', marginBottom: '6px',
      }}>{label}</label>
      <input
        type={type}
        placeholder={placeholder}
        value={value}
        onChange={e => onChange(e.target.value)}
        style={{
          width: '100%', padding: '12px 14px',
          backgroundColor: 'var(--surface-1)', border: '1px solid var(--stroke-subtle)',
          borderRadius: '10px', color: 'var(--text-primary)',
          fontSize: '14px', fontFamily: 'var(--font-sans)',
          outline: 'none', boxSizing: 'border-box',
        }}
      />
    </div>
  );
}

function ScreenHeader({ onBack, title }) {
  return (
    <div style={{
      padding: '20px 20px 16px', display: 'flex', alignItems: 'center', gap: '12px',
    }}>
      <button onClick={onBack} style={{
        background: 'none', border: 'none', cursor: 'pointer',
        color: 'var(--text-secondary)', padding: '4px',
      }}>
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <polyline points="15 18 9 12 15 6"/>
        </svg>
      </button>
      <h1 style={{
        fontFamily: 'var(--font-serif)', fontSize: '22px',
        fontWeight: 600, color: 'var(--text-primary)',
      }}>{title}</h1>
    </div>
  );
}

function SectionCard({ title, children }) {
  return (
    <div style={{
      backgroundColor: 'var(--surface-1)', borderRadius: '16px',
      padding: '20px', border: '1px solid var(--stroke-subtle)',
      marginBottom: '12px',
    }}>
      {title && (
        <h3 style={{
          fontSize: '12px', fontWeight: 600, color: 'var(--text-tertiary)',
          textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '14px',
        }}>{title}</h3>
      )}
      {children}
    </div>
  );
}

function StatCard({ label, value, color, large }) {
  return (
    <div style={{
      backgroundColor: 'var(--surface-2)', borderRadius: '10px', padding: large ? '16px' : '12px',
    }}>
      <div style={{
        fontFamily: 'var(--font-mono)', fontSize: large ? '22px' : '16px',
        fontWeight: 700, color: color || 'var(--text-primary)',
      }}>{value}</div>
      <div style={{
        fontSize: '10px', color: 'var(--text-tertiary)',
        textTransform: 'uppercase', letterSpacing: '0.05em', marginTop: '4px',
      }}>{label}</div>
    </div>
  );
}

function MiniCard({ label, value, color }) {
  return (
    <div style={{
      backgroundColor: 'var(--surface-2)', borderRadius: '10px',
      padding: '12px', textAlign: 'center',
    }}>
      <div style={{
        fontFamily: 'var(--font-mono)', fontSize: '15px',
        fontWeight: 600, color: color || 'var(--text-primary)',
      }}>{value}</div>
      <div style={{
        fontSize: '10px', color: 'var(--text-tertiary)',
        textTransform: 'uppercase', letterSpacing: '0.05em', marginTop: '4px',
      }}>{label}</div>
    </div>
  );
}
