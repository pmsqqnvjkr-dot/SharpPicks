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
        <ScreenHeader onBack={onBack} title="Bet Tracking" />
        <div style={{ padding: '40px 20px', textAlign: 'center' }}>
          <p style={{ color: 'var(--text-secondary)', fontSize: '14px' }}>
            Sign in to track your bets
          </p>
        </div>
      </div>
    );
  }

  return (
    <div style={{ padding: '0' }}>
      <ScreenHeader onBack={onBack} title="Bet Tracking" />

      {stats && stats.totalBets > 0 && (
        <div style={{ padding: '0 20px 12px' }}>
          <div style={{
            backgroundColor: 'var(--surface-1)', borderRadius: '16px',
            padding: '20px', border: '1px solid var(--stroke-subtle)',
          }}>
            <h3 style={{
              fontSize: '12px', fontWeight: 600, color: 'var(--text-tertiary)',
              textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '14px',
            }}>Your Performance</h3>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '12px' }}>
              <MiniStat label="P&L" value={`${stats.totalProfit >= 0 ? '+' : ''}$${stats.totalProfit}`}
                color={stats.totalProfit >= 0 ? 'var(--green-profit)' : 'var(--red-loss)'} />
              <MiniStat label="Record" value={`${stats.wins}-${stats.losses}`} />
              <MiniStat label="ROI" value={`${stats.roi >= 0 ? '+' : ''}${stats.roi}%`}
                color={stats.roi >= 0 ? 'var(--green-profit)' : 'var(--red-loss)'} />
            </div>
          </div>
        </div>
      )}

      <div style={{ padding: '0 20px 12px' }}>
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

      <div style={{ padding: '0 20px' }}>
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
            <p style={{
              fontSize: '14px', color: 'var(--text-secondary)', lineHeight: '1.6',
            }}>
              No bets tracked yet. When a pick is published, track your wager here to monitor your personal performance.
            </p>
          </div>
        ) : (
          <div style={{
            backgroundColor: 'var(--surface-1)', borderRadius: '16px',
            overflow: 'hidden', border: '1px solid var(--stroke-subtle)',
          }}>
            {bets.map((bet, i) => (
              <div key={bet.id} style={{
                padding: '14px 20px',
                borderBottom: i < bets.length - 1 ? '1px solid var(--stroke-subtle)' : 'none',
              }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                  <div style={{ flex: 1 }}>
                    <div style={{
                      fontSize: '14px', fontWeight: 500, color: 'var(--text-primary)',
                    }}>{bet.pick}</div>
                    <div style={{
                      fontSize: '12px', color: 'var(--text-tertiary)', marginTop: '2px',
                    }}>{bet.game}</div>
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
                      <div style={{
                        display: 'flex', gap: '6px',
                      }}>
                        <button onClick={() => handleMarkResult(bet.id, 'W')} style={{
                          padding: '4px 10px', fontSize: '11px', fontWeight: 600,
                          backgroundColor: 'rgba(52, 211, 153, 0.1)', color: 'var(--green-profit)',
                          border: '1px solid rgba(52, 211, 153, 0.3)', borderRadius: '6px',
                          cursor: 'pointer', fontFamily: 'var(--font-mono)',
                        }}>W</button>
                        <button onClick={() => handleMarkResult(bet.id, 'L')} style={{
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
                    <button onClick={() => handleDelete(bet.id)} style={{
                      padding: '3px 10px', fontSize: '11px', fontWeight: 600,
                      backgroundColor: 'rgba(239, 68, 68, 0.1)', color: 'var(--red-loss)',
                      border: '1px solid rgba(239, 68, 68, 0.3)', borderRadius: '6px',
                      cursor: 'pointer',
                    }}>Yes</button>
                    <button onClick={() => setConfirmDelete(null)} style={{
                      padding: '3px 10px', fontSize: '11px',
                      backgroundColor: 'transparent', color: 'var(--text-tertiary)',
                      border: '1px solid var(--stroke-subtle)', borderRadius: '6px',
                      cursor: 'pointer',
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
            ))}
          </div>
        )}
      </div>

      {showAddForm && <AddBetModal onClose={() => setShowAddForm(false)} onSubmit={handleAddBet} />}
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

function MiniStat({ label, value, color }) {
  return (
    <div style={{
      backgroundColor: 'var(--surface-2)', borderRadius: '10px', padding: '12px', textAlign: 'center',
    }}>
      <div style={{
        fontFamily: 'var(--font-mono)', fontSize: '16px',
        fontWeight: 600, color: color || 'var(--text-primary)',
      }}>{value}</div>
      <div style={{
        fontSize: '10px', color: 'var(--text-tertiary)',
        textTransform: 'uppercase', letterSpacing: '0.05em', marginTop: '4px',
      }}>{label}</div>
    </div>
  );
}
