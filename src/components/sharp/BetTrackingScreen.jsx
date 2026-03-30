import { useState, useEffect, useRef, useCallback } from 'react';
import { useAuth } from '../../hooks/useAuth';
import { apiGet, apiPost, apiDelete } from '../../hooks/useApi';
import { useSport, sportQuery } from '../../hooks/useSport';

export default function BetTrackingScreen({ onBack, pickToTrack }) {
  const { user } = useAuth();
  const { sport } = useSport();
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
        apiGet(sportQuery('/bets', sport)),
        apiGet(sportQuery('/user/stats', sport)),
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
        await loadBets();
      } else {
        alert(res.error || 'Failed to track bet');
      }
    } catch (e) {
      alert('Failed to track bet');
    }
  };

  const handleDelete = async (betId) => {
    try {
      const res = await apiDelete(`/bets/${betId}`);
      if (res.success) {
        setConfirmDelete(null);
        await loadBets();
      }
    } catch (e) {
      alert('Failed to delete bet');
    }
  };

  const isTab = !onBack;

  if (!user) {
    return (
      <div style={{ padding: '0' }}>
        {isTab ? <TabHeader title="Dashboard" /> : <ScreenHeader onBack={onBack} title="Your Performance" />}
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
      {isTab ? <TabHeader title="Dashboard" /> : <ScreenHeader onBack={onBack} title="Your Performance" />}

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
          ) : !hasBets && pendingBets.length === 0 && !(stats && stats.behavioral) ? (
            <EmptyDashboard onTrack={() => setShowTrackModal(true)} />
          ) : (
            <>
              {!hasBets && pendingBets.length === 0 && (
                <EmptyDashboard onTrack={() => setShowTrackModal(true)} />
              )}
              {pendingBets.length > 0 && (
                <SectionCard title={`Active (${pendingBets.length})`}>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                    {pendingBets.map(bet => (
                      <PendingBetCard key={bet.id} bet={bet} onGraded={loadBets} />
                    ))}
                  </div>
                </SectionCard>
              )}

              {hasBets && stats && (
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

              {stats.adherence && stats.adherence.picks_followed > 0 && (
                <SectionCard title="System Adherence">
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px', marginBottom: '14px' }}>
                    <MiniCard
                      label="Picks Followed"
                      value={`${stats.adherence.picks_followed} of ${stats.adherence.total_published}`}
                    />
                    <MiniCard
                      label="Exact Follows"
                      value={stats.adherence.adherence_score !== null ? `${stats.adherence.adherence_score}%` : '—'}
                      color={stats.adherence.adherence_score >= 80 ? 'var(--green-profit)' : 'var(--text-primary)'}
                    />
                  </div>
                  {stats.adherence.avg_line_delta !== null && (
                    <div style={{
                      padding: '10px 14px', backgroundColor: 'var(--surface-2)',
                      borderRadius: '10px', marginBottom: '8px',
                    }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                        <span style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>
                          Avg line delta vs publish
                        </span>
                        <span style={{
                          fontFamily: 'var(--font-mono)', fontSize: '13px', fontWeight: 600,
                          color: stats.adherence.avg_line_delta > 1 ? 'var(--gold-pro)' : 'var(--text-primary)',
                        }}>
                          {stats.adherence.avg_line_delta} pts
                        </span>
                      </div>
                    </div>
                  )}
                  {stats.outcome_split && (
                    <div style={{
                      padding: '12px 14px', backgroundColor: 'var(--surface-2)',
                      borderRadius: '10px',
                    }}>
                      <div style={{
                        fontFamily: 'var(--font-mono)', fontSize: '10px', fontWeight: 600,
                        letterSpacing: '1.5px', textTransform: 'uppercase',
                        color: 'var(--text-tertiary)', marginBottom: '10px',
                      }}>Outcome Split</div>
                      <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                          <span style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>Model (1u flat)</span>
                          <span style={{
                            fontFamily: 'var(--font-mono)', fontSize: '13px', fontWeight: 600,
                            color: stats.outcome_split.model_pnl >= 0 ? 'var(--green-profit)' : 'var(--red-loss)',
                          }}>{stats.outcome_split.model_pnl >= 0 ? '+' : ''}${stats.outcome_split.model_pnl}</span>
                        </div>
                        <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                          <span style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>You (actual stakes)</span>
                          <span style={{
                            fontFamily: 'var(--font-mono)', fontSize: '13px', fontWeight: 600,
                            color: stats.outcome_split.user_pnl >= 0 ? 'var(--green-profit)' : 'var(--red-loss)',
                          }}>{stats.outcome_split.user_pnl >= 0 ? '+' : ''}${stats.outcome_split.user_pnl}</span>
                        </div>
                        <div style={{
                          marginTop: '4px', paddingTop: '6px',
                          borderTop: '1px solid var(--stroke-subtle)',
                          display: 'flex', justifyContent: 'space-between',
                        }}>
                          <span style={{ fontSize: '11px', color: 'var(--text-tertiary)' }}>Execution delta</span>
                          <span style={{
                            fontFamily: 'var(--font-mono)', fontSize: '12px', fontWeight: 600,
                            color: stats.outcome_split.difference >= 0 ? 'var(--green-profit)' : 'var(--red-loss)',
                          }}>{stats.outcome_split.difference >= 0 ? '+' : ''}${stats.outcome_split.difference}</span>
                        </div>
                      </div>
                    </div>
                  )}
                </SectionCard>
              )}

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
                        backgroundColor: p.result === 'W' ? 'rgba(90, 158, 114, 0.2)' : 'rgba(196, 104, 107, 0.2)',
                        border: `1px solid ${p.result === 'W' ? 'rgba(90, 158, 114, 0.4)' : 'rgba(196, 104, 107, 0.4)'}`,
                        display: 'flex', alignItems: 'center', justifyContent: 'center',
                        fontSize: '10px', fontWeight: 500, fontFamily: 'var(--font-mono)',
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
              </>
              )}

              {stats && stats.behavioral && (
                <SectionCard title="Discipline Score">
                  <div style={{
                    display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px',
                  }}>
                    <div>
                      <div style={{ display: 'flex', alignItems: 'baseline', gap: '12px', marginBottom: '4px' }}>
                        <span style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>Selectivity Rate</span>
                        <span style={{
                          fontFamily: 'var(--font-mono)', fontSize: '22px',
                          color: 'var(--text-primary)', fontWeight: 700,
                        }}>{stats.behavioral.selectivity || 0}%</span>
                      </div>
                      <div style={{ fontSize: '12px', color: 'var(--text-tertiary)' }}>
                        Industry Avg: {stats.behavioral.industry_avg || 78}%
                      </div>
                    </div>
                    <div style={{
                      width: '56px', height: '56px', borderRadius: '14px',
                      background: stats.behavioral.restraint_grade?.startsWith('A')
                        ? 'linear-gradient(135deg, rgba(52,211,153,0.15), rgba(52,211,153,0.05))'
                        : 'linear-gradient(135deg, rgba(255,255,255,0.08), rgba(255,255,255,0.02))',
                      border: stats.behavioral.restraint_grade?.startsWith('A')
                        ? '1px solid rgba(52,211,153,0.3)'
                        : '1px solid var(--stroke-subtle)',
                      display: 'flex', alignItems: 'center', justifyContent: 'center',
                    }}>
                      <span style={{
                        fontFamily: 'var(--font-mono)', fontSize: '20px', fontWeight: 800,
                        color: stats.behavioral.restraint_grade?.startsWith('A') ? 'var(--green-profit)' : 'var(--text-primary)',
                      }}>{stats.behavioral.restraint_grade || '—'}</span>
                    </div>
                  </div>
                  <div style={{ position: 'relative', height: '28px', marginBottom: '16px' }}>
                    <div style={{
                      position: 'absolute', left: 0, right: 0, height: '6px', top: '11px',
                      backgroundColor: 'var(--surface-2)', borderRadius: '3px',
                    }} />
                    <div style={{
                      position: 'absolute', left: 0, top: '11px',
                      width: `${Math.min(Math.max(stats.behavioral.selectivity || 0, 0), 100)}%`,
                      height: '6px',
                      background: 'linear-gradient(90deg, #34D399, #2563EB)',
                      borderRadius: '3px',
                    }} />
                    <div style={{
                      position: 'absolute', left: `${Math.min(Math.max(stats.behavioral.selectivity || 0, 0), 100)}%`,
                      top: '5px', width: '3px', height: '18px',
                      backgroundColor: 'var(--green-profit)', borderRadius: '2px',
                      transform: 'translateX(-50%)',
                    }} />
                    <div style={{
                      position: 'absolute', left: `${stats.behavioral.industry_avg || 78}%`,
                      top: 0, transform: 'translateX(-50%)',
                      fontSize: '8px', color: 'var(--text-tertiary)', whiteSpace: 'nowrap',
                    }}>Industry ({stats.behavioral.industry_avg || 78}%)</div>
                    <div style={{
                      position: 'absolute', left: `${stats.behavioral.industry_avg || 78}%`,
                      top: '11px', width: '1px', height: '6px',
                      backgroundColor: 'var(--text-tertiary)', opacity: 0.5,
                    }} />
                  </div>
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px', marginBottom: '12px' }}>
                    <MiniCard label="Picks Followed" value={stats.behavioral.picks_followed || 0} />
                    <MiniCard label="Picks Passed" value={stats.behavioral.picks_passed || 0} />
                  </div>
                  <div style={{
                    paddingTop: '12px', borderTop: '1px solid var(--stroke-subtle)',
                  }}>
                    <p style={{ fontSize: '13px', color: 'var(--text-secondary)', lineHeight: '1.6' }}>
                      Capital preserved: <span style={{
                        fontFamily: 'var(--font-mono)', fontWeight: 500, color: 'var(--green-profit)',
                      }}>+${(stats.behavioral.capital_preserved || 0).toLocaleString()}</span> from avoided -EV spots
                    </p>
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
                        confirmDelete={confirmDelete}
                        setConfirmDelete={setConfirmDelete} onDelete={handleDelete} onGraded={loadBets} />
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
                        confirmDelete={confirmDelete}
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

export function TrackBetModal({ initialPick, onClose, onSubmit }) {
  const [step, setStep] = useState(initialPick ? 'wager' : 'picks');
  const [mode, setMode] = useState('model');
  const [picks, setPicks] = useState([]);
  const [loadingPicks, setLoadingPicks] = useState(!initialPick);
  const [selected, setSelected] = useState(initialPick || null);
  const [amount, setAmount] = useState('100');
  const [odds, setOdds] = useState(initialPick?.market_odds != null ? String(initialPick.market_odds) : '-110');
  const [followType, setFollowType] = useState('exact');
  const [submitting, setSubmitting] = useState(false);

  const [manualGame, setManualGame] = useState('');
  const [manualPick, setManualPick] = useState('');
  const [manualLine, setManualLine] = useState('');
  const [manualBetType, setManualBetType] = useState('spread');
  const [parlayLegs, setParlayLegs] = useState('2');
  const [parlayDesc, setParlayDesc] = useState('');

  useEffect(() => {
    if (!initialPick) {
      loadTrackablePicks();
    }
  }, []);

  const loadTrackablePicks = async () => {
    try {
      const data = await apiGet(sportQuery('/bets/trackable', sport));
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
    setOdds(pick.market_odds != null ? String(pick.market_odds) : '-110');
    setStep('wager');
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (mode === 'model' && !selected) return;
    if (mode === 'manual') {
      if (manualBetType === 'parlay' && !parlayDesc.trim()) return;
      if (manualBetType !== 'parlay' && (!manualGame.trim() || !manualPick.trim())) return;
    }
    setSubmitting(true);
    const userOdds = parseInt(odds) || -110;

    if (mode === 'model') {
      await onSubmit({
        pick_id: selected.id,
        bet_amount: parseInt(amount) || 100,
        odds: userOdds,
        follow_type: followType,
        line_at_bet: selected.line,
        bet_type: 'spread',
      });
    } else if (manualBetType === 'parlay') {
      const legs = parseInt(parlayLegs) || 2;
      await onSubmit({
        game: `${legs}-Leg Parlay`,
        pick: parlayDesc.trim(),
        bet_amount: parseInt(amount) || 100,
        odds: userOdds,
        bet_type: 'parlay',
        parlay_legs: legs,
      });
    } else {
      const lineVal = parseFloat(manualLine) || 0;
      let pickLabel;
      if (manualBetType === 'moneyline') pickLabel = `${manualPick.trim()} ML`;
      else if (manualBetType === 'total') pickLabel = manualPick.trim();
      else if (manualBetType === 'prop') pickLabel = manualPick.trim();
      else pickLabel = `${manualPick.trim()} ${lineVal >= 0 ? '+' : ''}${lineVal}`;

      await onSubmit({
        game: manualGame.trim(),
        pick: pickLabel,
        bet_amount: parseInt(amount) || 100,
        odds: userOdds,
        line_at_bet: (manualBetType === 'moneyline' || manualBetType === 'prop') ? null : lineVal,
        bet_type: manualBetType,
      });
    }
    setSubmitting(false);
  };

  const toWin = (() => {
    const amt = parseInt(amount) || 100;
    const o = parseInt(odds) || -110;
    if (o < 0) return (amt * (100 / Math.abs(o))).toFixed(2);
    return (amt * (o / 100)).toFixed(2);
  })();

  const stepTitle = step === 'picks'
    ? 'Track a Bet'
    : 'Enter Your Wager';

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
            }}>{stepTitle}</h2>
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
            {/* Mode toggle */}
            <div style={{
              display: 'flex', gap: '4px', marginBottom: '16px',
              backgroundColor: 'var(--surface-2)', borderRadius: '10px', padding: '3px',
            }}>
              <button onClick={() => setMode('model')} style={{
                flex: 1, padding: '9px 12px', borderRadius: '8px', border: 'none',
                fontSize: '13px', fontWeight: 600, cursor: 'pointer',
                fontFamily: 'var(--font-mono)', transition: 'all 0.15s',
                backgroundColor: mode === 'model' ? 'var(--blue-primary)' : 'transparent',
                color: mode === 'model' ? '#fff' : 'var(--text-tertiary)',
              }}>Model Pick</button>
              <button onClick={() => setMode('manual')} style={{
                flex: 1, padding: '9px 12px', borderRadius: '8px', border: 'none',
                fontSize: '13px', fontWeight: 600, cursor: 'pointer',
                fontFamily: 'var(--font-mono)', transition: 'all 0.15s',
                backgroundColor: mode === 'manual' ? '#f59e0b' : 'transparent',
                color: mode === 'manual' ? '#fff' : 'var(--text-tertiary)',
              }}>My Own Bet</button>
            </div>

            {mode === 'model' ? (
              <>
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
              </>
            ) : (
              /* Manual bet entry form */
              <form onSubmit={(e) => {
                e.preventDefault();
                if (manualBetType === 'parlay' && parlayDesc.trim()) setStep('wager');
                else if (manualBetType !== 'parlay' && manualGame.trim() && manualPick.trim()) setStep('wager');
              }}>
                <div style={{ marginBottom: '12px' }}>
                  <div style={{
                    fontFamily: 'var(--font-mono)', fontSize: '10px', fontWeight: 600,
                    letterSpacing: '1.2px', textTransform: 'uppercase',
                    color: 'var(--text-tertiary)', marginBottom: '6px',
                  }}>Bet Type</div>
                  <div style={{ display: 'flex', gap: '5px', flexWrap: 'wrap' }}>
                    {[
                      { value: 'spread', label: 'Spread' },
                      { value: 'total', label: 'Total' },
                      { value: 'moneyline', label: 'ML' },
                      { value: 'prop', label: 'Prop' },
                      { value: 'parlay', label: 'Parlay' },
                    ].map(opt => (
                      <button
                        key={opt.value}
                        type="button"
                        onClick={() => setManualBetType(opt.value)}
                        style={{
                          padding: '6px 12px', borderRadius: '8px',
                          fontSize: '12px', fontWeight: 600,
                          fontFamily: 'var(--font-mono)', cursor: 'pointer',
                          backgroundColor: manualBetType === opt.value ? 'var(--blue-primary)' : 'var(--surface-1)',
                          color: manualBetType === opt.value ? '#fff' : 'var(--text-secondary)',
                          border: `1px solid ${manualBetType === opt.value ? 'var(--blue-primary)' : 'var(--stroke-subtle)'}`,
                          transition: 'all 0.15s',
                        }}
                      >{opt.label}</button>
                    ))}
                  </div>
                </div>

                {manualBetType === 'parlay' ? (
                  <>
                    <FormField label="Number of Legs" placeholder="2" value={parlayLegs} onChange={setParlayLegs} type="number" />
                    <div style={{ marginBottom: '12px' }}>
                      <label style={{
                        display: 'block', fontSize: '12px', fontWeight: 600,
                        color: 'var(--text-tertiary)', textTransform: 'uppercase',
                        letterSpacing: '0.05em', marginBottom: '6px',
                      }}>Parlay Legs</label>
                      <textarea
                        placeholder={"e.g.\nLakers -3.5\nCeltics ML\nOver 218.5"}
                        value={parlayDesc}
                        onChange={e => setParlayDesc(e.target.value)}
                        rows={3}
                        style={{
                          width: '100%', padding: '12px 14px',
                          backgroundColor: 'var(--surface-1)', border: '1px solid var(--stroke-subtle)',
                          borderRadius: '10px', color: 'var(--text-primary)',
                          fontSize: '14px', fontFamily: 'var(--font-sans)',
                          outline: 'none', boxSizing: 'border-box', resize: 'vertical',
                        }}
                      />
                    </div>
                  </>
                ) : (
                  <>
                    <FormField label="Game" placeholder="e.g. Lakers @ Celtics" value={manualGame} onChange={setManualGame} />
                    <FormField
                      label={
                        manualBetType === 'prop' ? 'Prop (e.g. LeBron Over 25.5 pts)'
                        : manualBetType === 'total' ? 'Pick (e.g. Over 218.5)'
                        : manualBetType === 'moneyline' ? 'Pick (e.g. Lakers)'
                        : 'Pick (e.g. Lakers)'
                      }
                      placeholder={
                        manualBetType === 'prop' ? 'LeBron Over 25.5 pts'
                        : manualBetType === 'total' ? 'Over 218.5'
                        : manualBetType === 'moneyline' ? 'Lakers'
                        : 'Lakers'
                      }
                      value={manualPick}
                      onChange={setManualPick}
                    />
                    {manualBetType === 'spread' && (
                      <FormField label="Spread" placeholder="-3.5" value={manualLine} onChange={setManualLine} type="number" />
                    )}
                    {manualBetType === 'total' && (
                      <FormField label="Line" placeholder="218.5" value={manualLine} onChange={setManualLine} type="number" />
                    )}
                  </>
                )}

                <button
                  type="submit"
                  disabled={manualBetType === 'parlay' ? !parlayDesc.trim() : (!manualGame.trim() || !manualPick.trim())}
                  style={{
                    width: '100%', padding: '14px',
                    backgroundColor: 'var(--blue-primary)', color: '#fff',
                    border: 'none', borderRadius: '12px',
                    fontSize: '15px', fontWeight: 600, cursor: 'pointer',
                    fontFamily: 'var(--font-sans)',
                    opacity: (manualBetType === 'parlay' ? !parlayDesc.trim() : (!manualGame.trim() || !manualPick.trim())) ? 0.4 : 1,
                  }}
                >Next: Enter Wager</button>
              </form>
            )}
          </div>
        ) : (
          <div>
            <div style={{
              backgroundColor: 'var(--surface-1)', borderRadius: '12px',
              padding: '14px 16px', marginBottom: '16px',
              border: '1px solid var(--stroke-subtle)',
            }}>
              {mode === 'model' ? (
                <>
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
                </>
              ) : (
                <>
                  <div style={{
                    display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '4px',
                  }}>
                    <span style={{
                      fontFamily: 'var(--font-mono)', fontSize: '9px', fontWeight: 700,
                      padding: '2px 6px', borderRadius: '4px',
                      backgroundColor: manualBetType === 'parlay' ? 'rgba(168,85,247,0.12)'
                        : manualBetType === 'prop' ? 'rgba(59,130,246,0.12)'
                        : 'rgba(251,191,36,0.12)',
                      color: manualBetType === 'parlay' ? '#a855f7'
                        : manualBetType === 'prop' ? '#3b82f6'
                        : '#f59e0b',
                      textTransform: 'uppercase', letterSpacing: '0.5px',
                    }}>{manualBetType === 'parlay' ? `${parlayLegs}-Leg Parlay` : manualBetType === 'prop' ? 'Player Prop' : 'Personal'}</span>
                  </div>
                  <div style={{ fontSize: '14px', fontWeight: 500, color: 'var(--text-primary)' }}>
                    {manualBetType === 'parlay' ? `${parlayLegs}-Leg Parlay` : manualGame}
                  </div>
                  <div style={{
                    fontSize: manualBetType === 'parlay' ? '13px' : '15px',
                    color: manualBetType === 'parlay' ? '#a855f7'
                      : manualBetType === 'prop' ? '#3b82f6'
                      : '#f59e0b',
                    fontWeight: 700, marginTop: '6px',
                    whiteSpace: manualBetType === 'parlay' ? 'pre-line' : 'normal',
                    lineHeight: manualBetType === 'parlay' ? '1.5' : 'inherit',
                  }}>
                    {manualBetType === 'parlay' ? parlayDesc
                      : manualBetType === 'moneyline' ? `${manualPick} ML`
                      : manualBetType === 'prop' ? manualPick
                      : manualBetType === 'total' ? manualPick
                      : `${manualPick} ${parseFloat(manualLine) >= 0 ? '+' : ''}${manualLine || '0'}`}
                  </div>
                </>
              )}
            </div>

            <form onSubmit={handleSubmit}>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                <FormField label="Wager ($)" placeholder="100" value={amount} onChange={setAmount} type="number" />
                <FormField label="Odds" placeholder="-110" value={odds} onChange={setOdds} type="number" />
              </div>

              {mode === 'model' && (
                <div style={{ marginBottom: '12px' }}>
                  <div style={{
                    fontFamily: 'var(--font-mono)', fontSize: '10px', fontWeight: 600,
                    letterSpacing: '1.2px', textTransform: 'uppercase',
                    color: 'var(--text-tertiary)', marginBottom: '6px',
                  }}>How did you follow this pick?</div>
                  <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap' }}>
                    {[
                      { value: 'exact', label: 'Exact' },
                      { value: 'partial', label: 'Partial' },
                      { value: 'late_line', label: 'Late Line' },
                      { value: 'parlayed', label: 'Parlayed' },
                    ].map(opt => (
                      <button
                        key={opt.value}
                        type="button"
                        onClick={() => setFollowType(opt.value)}
                        style={{
                          padding: '6px 12px', borderRadius: '8px',
                          fontSize: '12px', fontWeight: 600,
                          fontFamily: 'var(--font-mono)',
                          cursor: 'pointer',
                          backgroundColor: followType === opt.value ? 'var(--blue-primary)' : 'var(--surface-1)',
                          color: followType === opt.value ? '#fff' : 'var(--text-secondary)',
                          border: `1px solid ${followType === opt.value ? 'var(--blue-primary)' : 'var(--stroke-subtle)'}`,
                          transition: 'all 0.15s',
                        }}
                      >{opt.label}</button>
                    ))}
                  </div>
                </div>
              )}

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

function PendingBetCard({ bet, onGraded }) {
  const [grading, setGrading] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const isManual = !bet.pick_id;
  const betTypeMeta = bet.bet_type === 'parlay'
    ? { label: `${bet.parlay_legs || ''}L Parlay`, color: '#a855f7', bg: 'rgba(168,85,247,0.15)' }
    : bet.bet_type === 'prop'
    ? { label: 'Prop', color: '#3b82f6', bg: 'rgba(59,130,246,0.15)' }
    : null;

  const handleGrade = async (result) => {
    setSubmitting(true);
    const profit = result === 'W' ? (bet.to_win || 0) : result === 'P' ? 0 : -(bet.bet_amount || 0);
    try {
      await apiPost(`/bets/${bet.id}/result`, { result, profit });
      onGraded();
    } catch { /* silent */ }
    setSubmitting(false);
    setGrading(false);
  };

  return (
    <div style={{
      padding: '12px 14px', backgroundColor: 'var(--surface-2)', borderRadius: '10px',
      border: `1px solid ${grading ? 'rgba(79,134,247,0.3)' : 'rgba(79, 134, 247, 0.15)'}`,
      transition: 'border-color 0.15s',
    }}>
      <div style={{
        display: 'flex', justifyContent: 'space-between', alignItems: 'center',
      }}>
        <div style={{ flex: 1 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <div style={{ fontSize: '14px', fontWeight: 500, color: 'var(--text-primary)' }}>
              {bet.pick}
            </div>
            {betTypeMeta && (
              <span style={{
                fontFamily: 'var(--font-mono)', fontSize: '9px', fontWeight: 600,
                padding: '2px 6px', borderRadius: '4px',
                backgroundColor: betTypeMeta.bg, color: betTypeMeta.color,
                textTransform: 'uppercase', letterSpacing: '0.5px',
              }}>{betTypeMeta.label}</span>
            )}
          </div>
          <div style={{ fontSize: '12px', color: 'var(--text-tertiary)', marginTop: '2px' }}>
            {bet.game}
          </div>
          <div style={{
            fontFamily: 'var(--font-mono)', fontSize: '11px',
            color: 'var(--text-tertiary)', marginTop: '4px',
          }}>
            ${bet.bet_amount} at {bet.odds != null ? (bet.odds > 0 ? `+${bet.odds}` : bet.odds) : '-110'} · to win ${bet.to_win || '—'}
          </div>
        </div>
        {!grading && (
          <button
            onClick={() => setGrading(true)}
            style={{
              fontFamily: 'var(--font-mono)', fontSize: '11px', fontWeight: 600,
              padding: '4px 10px', borderRadius: '6px',
              backgroundColor: isManual ? 'rgba(251,191,36,0.12)' : 'rgba(79, 134, 247, 0.12)',
              color: isManual ? '#f59e0b' : 'var(--blue-primary)',
              letterSpacing: '0.3px', border: 'none', cursor: 'pointer',
            }}
          >
            {isManual ? 'Grade' : 'Awaiting'}
          </button>
        )}
      </div>
      {grading && (
        <div style={{
          marginTop: '10px', paddingTop: '10px',
          borderTop: '1px solid var(--stroke-subtle)',
          display: 'flex', gap: '8px', justifyContent: 'center',
        }}>
          {[
            { result: 'W', label: 'Win', color: 'var(--green-profit)', bg: 'rgba(52,211,153,0.12)' },
            { result: 'L', label: 'Loss', color: 'var(--red-loss)', bg: 'rgba(239,68,68,0.12)' },
            { result: 'P', label: 'Push', color: 'var(--text-tertiary)', bg: 'rgba(100,116,139,0.12)' },
          ].map(opt => (
            <button
              key={opt.result}
              onClick={() => handleGrade(opt.result)}
              disabled={submitting}
              style={{
                flex: 1, padding: '8px 12px', borderRadius: '8px',
                fontSize: '13px', fontWeight: 700, cursor: 'pointer',
                fontFamily: 'var(--font-mono)', border: 'none',
                backgroundColor: opt.bg, color: opt.color,
                opacity: submitting ? 0.5 : 1,
                transition: 'opacity 0.15s',
              }}
            >{opt.label}</button>
          ))}
          <button
            onClick={() => setGrading(false)}
            style={{
              padding: '8px', borderRadius: '8px', border: 'none',
              backgroundColor: 'transparent', cursor: 'pointer',
              color: 'var(--text-tertiary)', fontSize: '12px',
            }}
          >✕</button>
        </div>
      )}
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
      }}>No bets tracked yet</h3>
      <p style={{
        fontSize: '13px', color: 'var(--text-secondary)', lineHeight: '1.6', marginBottom: '8px',
      }}>
        When a pick is published, tap "Track outcome" to log your wager. Your equity curve, streaks, and ROI will build here over time.
      </p>
      <p style={{
        fontSize: '12px', color: 'var(--text-tertiary)', lineHeight: '1.5', marginBottom: '20px',
        fontStyle: 'italic', fontFamily: 'var(--font-serif)',
      }}>
        Bets are graded automatically when picks settle.
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

function BetRow({ bet, isLast, confirmDelete, setConfirmDelete, onDelete, onGraded }) {
  const pickResultLabel = bet.pick_result && bet.pick_result !== 'pending'
    ? bet.pick_result : null;

  const rowRef = useRef(null);
  const startX = useRef(0);
  const currentX = useRef(0);
  const swiping = useRef(false);
  const [offset, setOffset] = useState(0);
  const [showConfirm, setShowConfirm] = useState(false);
  const [grading, setGrading] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const deleteThreshold = 80;

  const handleGrade = async (result) => {
    setSubmitting(true);
    const profit = result === 'W' ? (bet.to_win || 0) : result === 'P' ? 0 : -(bet.bet_amount || 0);
    try {
      await apiPost(`/bets/${bet.id}/result`, { result, profit });
      if (onGraded) onGraded();
    } catch { /* silent */ }
    setSubmitting(false);
    setGrading(false);
  };

  const onTouchStart = useCallback((e) => {
    startX.current = e.touches[0].clientX;
    currentX.current = 0;
    swiping.current = true;
  }, []);

  const onTouchMove = useCallback((e) => {
    if (!swiping.current) return;
    const diff = startX.current - e.touches[0].clientX;
    if (diff > 0) {
      const clamped = Math.min(diff, deleteThreshold + 20);
      currentX.current = clamped;
      setOffset(clamped);
    } else {
      currentX.current = 0;
      setOffset(0);
    }
  }, []);

  const onTouchEnd = useCallback(() => {
    swiping.current = false;
    if (currentX.current >= deleteThreshold) {
      setOffset(deleteThreshold);
      setShowConfirm(true);
    } else {
      setOffset(0);
      setShowConfirm(false);
    }
  }, []);

  const resetSwipe = () => {
    setOffset(0);
    setShowConfirm(false);
  };

  return (
    <div style={{
      position: 'relative',
      overflow: 'hidden',
      borderBottom: isLast ? 'none' : '1px solid var(--stroke-subtle)',
    }}>
      <div style={{
        position: 'absolute', right: 0, top: 0, bottom: 0,
        width: `${deleteThreshold + 20}px`,
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        backgroundColor: showConfirm ? '#dc2626' : 'rgba(239, 68, 68, 0.85)',
        transition: showConfirm ? 'background-color 0.2s' : 'none',
      }}>
        {showConfirm ? (
          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '4px' }}>
            <button onClick={() => { onDelete(bet.id); resetSwipe(); }} style={{
              background: 'none', border: 'none', color: '#fff',
              fontSize: '12px', fontWeight: 700, cursor: 'pointer',
              fontFamily: 'var(--font-sans)', padding: '6px 12px',
            }}>Delete</button>
            <button onClick={resetSwipe} style={{
              background: 'none', border: 'none',
              color: 'rgba(255,255,255,0.7)', fontSize: '10px',
              cursor: 'pointer', fontFamily: 'var(--font-sans)', padding: '2px 8px',
            }}>Cancel</button>
          </div>
        ) : (
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#fff" strokeWidth="2">
            <polyline points="3 6 5 6 21 6"/>
            <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>
          </svg>
        )}
      </div>

      <div
        ref={rowRef}
        onTouchStart={onTouchStart}
        onTouchMove={onTouchMove}
        onTouchEnd={onTouchEnd}
        style={{
          padding: '14px 20px',
          backgroundColor: 'var(--surface-1)',
          transform: `translateX(-${offset}px)`,
          transition: swiping.current ? 'none' : 'transform 0.25s ease',
          position: 'relative', zIndex: 1,
        }}
      >
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
          <div style={{ flex: 1 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px', flexWrap: 'wrap' }}>
              <div style={{ fontSize: '14px', fontWeight: 500, color: 'var(--text-primary)' }}>{bet.pick}</div>
              {bet.pick_id && (
                <span style={{
                  fontFamily: 'var(--font-mono)', fontSize: '9px', fontWeight: 600,
                  padding: '2px 6px', borderRadius: '4px',
                  backgroundColor: 'rgba(79, 134, 247, 0.15)', color: 'var(--blue-primary)',
                  textTransform: 'uppercase', letterSpacing: '0.5px',
                }}>SP</span>
              )}
              {bet.bet_type === 'parlay' && (
                <span style={{
                  fontFamily: 'var(--font-mono)', fontSize: '9px', fontWeight: 600,
                  padding: '2px 6px', borderRadius: '4px',
                  backgroundColor: 'rgba(168,85,247,0.15)', color: '#a855f7',
                  textTransform: 'uppercase', letterSpacing: '0.5px',
                }}>{bet.parlay_legs || ''}L Parlay</span>
              )}
              {bet.bet_type === 'prop' && (
                <span style={{
                  fontFamily: 'var(--font-mono)', fontSize: '9px', fontWeight: 600,
                  padding: '2px 6px', borderRadius: '4px',
                  backgroundColor: 'rgba(59,130,246,0.15)', color: '#3b82f6',
                  textTransform: 'uppercase', letterSpacing: '0.5px',
                }}>Prop</span>
              )}
            </div>
            <div style={{ fontSize: '12px', color: 'var(--text-tertiary)', marginTop: '2px' }}>{bet.game}</div>
            <div style={{
              fontSize: '11px', color: 'var(--text-tertiary)', marginTop: '4px',
              fontFamily: 'var(--font-mono)',
            }}>
              ${bet.bet_amount} at {bet.odds != null ? (bet.odds > 0 ? `+${bet.odds}` : bet.odds) : '-110'} · to win ${bet.to_win || '—'}
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
                color: bet.result === 'W' ? 'var(--green-profit)' : bet.result === 'P' ? 'var(--text-tertiary)' : 'var(--red-loss)',
              }}>
                {bet.result === 'W' ? `+$${Math.abs(bet.profit || 0).toFixed(0)}` : bet.result === 'P' ? 'Push' : `-$${Math.abs(bet.profit || 0).toFixed(0)}`}
              </div>
            ) : (
              <button
                onClick={(e) => { e.stopPropagation(); setGrading(!grading); }}
                style={{
                  fontFamily: 'var(--font-mono)', fontSize: '11px', fontWeight: 600,
                  padding: '4px 10px', borderRadius: '6px',
                  backgroundColor: grading ? 'rgba(251,191,36,0.18)' : 'rgba(251,191,36,0.12)',
                  color: '#f59e0b',
                  letterSpacing: '0.3px', border: 'none', cursor: 'pointer',
                  transition: 'background-color 0.15s',
                }}>Grade</button>
            )}
          </div>
        </div>
        {!bet.result && grading && (
          <div style={{
            marginTop: '10px', paddingTop: '10px',
            borderTop: '1px solid var(--stroke-subtle)',
            display: 'flex', gap: '8px', justifyContent: 'center',
          }}>
            {[
              { result: 'W', label: 'Win', color: 'var(--green-profit)', bg: 'rgba(52,211,153,0.12)' },
              { result: 'L', label: 'Loss', color: 'var(--red-loss)', bg: 'rgba(239,68,68,0.12)' },
              { result: 'P', label: 'Push', color: 'var(--text-tertiary)', bg: 'rgba(100,116,139,0.12)' },
            ].map(opt => (
              <button
                key={opt.result}
                onClick={() => handleGrade(opt.result)}
                disabled={submitting}
                style={{
                  flex: 1, padding: '8px 12px', borderRadius: '8px',
                  fontSize: '13px', fontWeight: 700, cursor: 'pointer',
                  fontFamily: 'var(--font-mono)', border: 'none',
                  backgroundColor: opt.bg, color: opt.color,
                  opacity: submitting ? 0.5 : 1,
                  transition: 'opacity 0.15s',
                }}
              >{opt.label}</button>
            ))}
            <button
              onClick={() => setGrading(false)}
              style={{
                padding: '8px', borderRadius: '8px', border: 'none',
                backgroundColor: 'transparent', cursor: 'pointer',
                color: 'var(--text-tertiary)', fontSize: '12px',
              }}
            >✕</button>
          </div>
        )}
      </div>
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

        {(() => {
          const seenLabels = new Set();
          return data.length <= 12 && data.map((d, i) => {
            const label = d.date ? d.date.substring(5) : '';
            if (!label || seenLabels.has(label)) return null;
            seenLabels.add(label);
            return (
              <text key={i} x={getX(i)} y={height - 5}
                textAnchor="middle" fill="var(--text-tertiary)"
                fontSize="7" fontFamily="var(--font-mono)">
                {label}
              </text>
            );
          });
        })()}
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

function TabHeader({ title }) {
  return (
    <div style={{ padding: '20px 20px 16px' }}>
      <h1 style={{
        fontFamily: 'var(--font-serif)', fontSize: '22px',
        fontWeight: 600, color: 'var(--text-primary)',
      }}>{title}</h1>
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
        fontWeight: 500, color: color || 'var(--text-primary)',
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
        fontWeight: 500, color: color || 'var(--text-primary)',
      }}>{value}</div>
      <div style={{
        fontSize: '10px', color: 'var(--text-tertiary)',
        textTransform: 'uppercase', letterSpacing: '0.05em', marginTop: '4px',
      }}>{label}</div>
    </div>
  );
}
