import { useState, useEffect } from 'react';
import { useAuth } from '../../hooks/useAuth';
import { apiGet, apiPost } from '../../hooks/useApi';

export default function BetTrackingScreen({ onBack }) {
  const { user } = useAuth();
  const [bets, setBets] = useState([]);
  const [loading, setLoading] = useState(true);
  const [stats, setStats] = useState(null);

  useEffect(() => {
    loadBets();
  }, []);

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

      {stats && (
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
              <MiniStat label="P&L" value={`$${stats.totalProfit || 0}`}
                color={stats.totalProfit >= 0 ? 'var(--green-profit)' : 'var(--red-loss)'} />
              <MiniStat label="Record" value={`${stats.wins || 0}-${stats.losses || 0}`} />
              <MiniStat label="ROI" value={`${stats.roi || 0}%`}
                color={stats.roi >= 0 ? 'var(--green-profit)' : 'var(--red-loss)'} />
            </div>
          </div>
        </div>
      )}

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
            <p style={{
              fontSize: '14px', color: 'var(--text-secondary)', lineHeight: '1.6',
            }}>
              No bets tracked yet. When a pick is published, you can track your wager here to monitor your personal performance over time.
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
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <div>
                    <div style={{
                      fontSize: '14px', fontWeight: 500, color: 'var(--text-primary)',
                    }}>{bet.pick}</div>
                    <div style={{
                      fontSize: '12px', color: 'var(--text-tertiary)', marginTop: '2px',
                    }}>{bet.game}</div>
                  </div>
                  <div style={{ textAlign: 'right' }}>
                    <div style={{
                      fontFamily: 'var(--font-mono)', fontSize: '13px', fontWeight: 600,
                      color: bet.result === 'W' ? 'var(--green-profit)'
                        : bet.result === 'L' ? 'var(--red-loss)' : 'var(--text-tertiary)',
                    }}>
                      {bet.result === 'W' ? `+$${bet.profit}` : bet.result === 'L' ? `-$${Math.abs(bet.profit)}` : `$${bet.bet_amount}`}
                    </div>
                    <div style={{
                      fontSize: '11px', color: 'var(--text-tertiary)', marginTop: '2px',
                      fontFamily: 'var(--font-mono)',
                    }}>{bet.odds > 0 ? `+${bet.odds}` : bet.odds}</div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
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
