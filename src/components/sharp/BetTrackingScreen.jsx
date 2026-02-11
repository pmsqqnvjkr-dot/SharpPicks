import { useState, useEffect } from 'react';
import { useAuth } from '../../hooks/useAuth';
import { apiGet, apiPost, apiDelete } from '../../hooks/useApi';

export default function BetTrackingScreen({ onBack }) {
  const { user } = useAuth();
  const [bets, setBets] = useState([]);
  const [loading, setLoading] = useState(true);
  const [stats, setStats] = useState(null);
  const [showAddForm, setShowAddForm] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState(null);
  const [activeView, setActiveView] = useState('dashboard');

  useEffect(() => {
    if (user) loadBets();
    else setLoading(false);
  }, [user]);

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

  const handleAddBet = async (betData) => {
    try {
      const res = await apiPost('/bets', betData);
      if (res.success) {
        setShowAddForm(false);
        loadBets();
      } else {
        alert(res.error || 'Failed to add bet');
      }
    } catch (e) {
      alert('Failed to add bet');
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
            <EmptyDashboard onAddBet={() => setShowAddForm(true)} />
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
                <button onClick={() => setShowAddForm(true)} style={{
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
            <button onClick={() => setShowAddForm(true)} style={{
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

      {showAddForm && <AddBetModal onClose={() => setShowAddForm(false)} onSubmit={handleAddBet} />}
    </div>
  );
}

function EmptyDashboard({ onAddBet }) {
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
        Track your bets here and watch your personal equity curve, win streaks, and ROI build over time.
      </p>
      <button onClick={onAddBet} style={{
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
  return (
    <div style={{
      padding: '14px 20px',
      borderBottom: isLast ? 'none' : '1px solid var(--stroke-subtle)',
    }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <div style={{ flex: 1 }}>
          <div style={{ fontSize: '14px', fontWeight: 500, color: 'var(--text-primary)' }}>{bet.pick}</div>
          <div style={{ fontSize: '12px', color: 'var(--text-tertiary)', marginTop: '2px' }}>{bet.game}</div>
          <div style={{
            fontSize: '11px', color: 'var(--text-tertiary)', marginTop: '4px',
            fontFamily: 'var(--font-mono)',
          }}>
            ${bet.bet_amount} at {bet.odds > 0 ? `+${bet.odds}` : bet.odds}
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

      <div style={{
        textAlign: 'center', marginTop: '8px',
        fontFamily: 'var(--font-mono)', fontSize: '16px', fontWeight: 600,
        color: isPositive ? 'var(--green-profit)' : 'var(--red-loss)',
      }}>
        {isPositive ? '+' : '-'}${Math.abs(lastValue).toFixed(0)} total
      </div>
    </div>
  );
}

function AddBetModal({ onClose, onSubmit }) {
  const [pick, setPick] = useState('');
  const [game, setGame] = useState('');
  const [amount, setAmount] = useState('100');
  const [odds, setOdds] = useState('-110');
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!pick.trim() || !game.trim()) return;
    setSubmitting(true);
    await onSubmit({
      pick: pick.trim(),
      game: game.trim(),
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
      }} onClick={e => e.stopPropagation()}>
        <div style={{
          display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px',
        }}>
          <h2 style={{
            fontFamily: 'var(--font-serif)', fontSize: '20px',
            fontWeight: 600, color: 'var(--text-primary)',
          }}>Track a Bet</h2>
          <button onClick={onClose} style={{
            background: 'none', border: 'none', cursor: 'pointer',
            color: 'var(--text-tertiary)', padding: '4px',
          }}>
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
            </svg>
          </button>
        </div>

        <form onSubmit={handleSubmit}>
          <FormField label="Pick" placeholder="e.g. Lakers -4.5" value={pick} onChange={setPick} />
          <FormField label="Game" placeholder="e.g. Lakers vs Celtics" value={game} onChange={setGame} />
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

          <button type="submit" disabled={submitting || !pick.trim() || !game.trim()} style={{
            width: '100%', padding: '14px',
            backgroundColor: 'var(--blue-primary)', color: '#fff',
            border: 'none', borderRadius: '12px',
            fontSize: '15px', fontWeight: 600, cursor: 'pointer',
            fontFamily: 'var(--font-sans)',
            opacity: submitting || !pick.trim() || !game.trim() ? 0.5 : 1,
          }}>
            {submitting ? 'Adding...' : 'Track This Bet'}
          </button>
        </form>
      </div>
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
