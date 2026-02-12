import { useState } from 'react';
import { useApi } from '../../hooks/useApi';
import { useAuth } from '../../hooks/useAuth';

export default function PickHistoryScreen({ onBack, onViewResolution }) {
  const { data, loading } = useApi('/public/record');
  const { user } = useAuth();
  const [filter, setFilter] = useState('all');

  const isPro = user && (user.is_premium || user.subscription_status === 'active' || user.subscription_status === 'trial');
  const picks = data?.picks || [];
  const filtered = filter === 'all' ? picks
    : filter === 'wins' ? picks.filter(p => p.result === 'win')
    : filter === 'losses' ? picks.filter(p => p.result === 'loss')
    : picks.filter(p => p.result === 'pending');

  return (
    <div style={{ padding: '0' }}>
      <div style={{
        padding: '20px 20px 16px',
        display: 'flex',
        alignItems: 'center',
        gap: '12px',
      }}>
        <button onClick={onBack} style={{
          background: 'none', border: 'none', cursor: 'pointer',
          color: 'var(--text-secondary)', padding: '4px',
        }}>
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <polyline points="15 18 9 12 15 6"/>
          </svg>
        </button>
        <div>
          <h1 style={{
            fontFamily: 'var(--font-serif)', fontSize: '22px',
            fontWeight: 600, color: 'var(--text-primary)',
          }}>Pick History</h1>
          <p style={{
            fontFamily: 'var(--font-mono)', fontSize: '12px',
            color: 'var(--text-tertiary)', marginTop: '2px',
          }}>{picks.length} total picks</p>
        </div>
      </div>

      {data?.stats && (
        <div style={{ padding: '0 20px 12px' }}>
          <div style={{
            backgroundColor: 'var(--surface-1)', borderRadius: '12px',
            padding: '16px 20px', border: '1px solid var(--stroke-subtle)',
            display: 'flex', justifyContent: 'space-between', alignItems: 'center',
          }}>
            <div style={{ display: 'flex', gap: '20px' }}>
              <SmallStat label="Record" value={`${data.stats.wins}-${data.stats.losses}`} />
              <SmallStat label="Win Rate" value={`${data.stats.win_rate}%`} />
              <SmallStat label="P&L" value={`${data.stats.pnl >= 0 ? '+' : ''}${data.stats.pnl}u`}
                color={data.stats.pnl >= 0 ? 'var(--green-profit)' : 'var(--red-loss)'} />
            </div>
          </div>
        </div>
      )}

      <div style={{
        padding: '0 20px 12px', display: 'flex', gap: '8px',
      }}>
        {['all', 'wins', 'losses', 'pending'].map(f => (
          <button key={f} onClick={() => setFilter(f)} style={{
            padding: '8px 16px', borderRadius: '8px', fontSize: '13px',
            fontWeight: 600, border: 'none', cursor: 'pointer',
            textTransform: 'capitalize', fontFamily: 'var(--font-sans)',
            backgroundColor: filter === f ? 'var(--blue-primary)' : 'var(--surface-2)',
            color: filter === f ? '#fff' : 'var(--text-secondary)',
          }}>{f}</button>
        ))}
      </div>

      <div style={{ padding: '0 20px' }}>
        {loading ? (
          <p style={{ color: 'var(--text-secondary)', fontSize: '14px', textAlign: 'center', padding: '40px 0' }}>
            Loading history...
          </p>
        ) : filtered.length === 0 ? (
          <p style={{ color: 'var(--text-tertiary)', fontSize: '14px', textAlign: 'center', padding: '40px 0' }}>
            No picks found
          </p>
        ) : (
          <div style={{
            backgroundColor: 'var(--surface-1)', borderRadius: '16px',
            overflow: 'hidden', border: '1px solid var(--stroke-subtle)',
          }}>
            {filtered.map((pick, i) => {
              const isResolved = pick.result === 'win' || pick.result === 'loss';
              const canViewResolution = isPro && isResolved && onViewResolution;
              return (
                <div key={pick.id} onClick={() => canViewResolution && onViewResolution(pick)} style={{
                  padding: '14px 20px',
                  borderBottom: i < filtered.length - 1 ? '1px solid var(--stroke-subtle)' : 'none',
                  display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                  cursor: canViewResolution ? 'pointer' : 'default',
                }}>
                  <div>
                    <div style={{
                      fontSize: '14px', fontWeight: 500, color: 'var(--text-primary)',
                    }}>
                      {isPro ? pick.side : (
                        <span style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="var(--text-tertiary)" strokeWidth="2">
                            <rect x="3" y="11" width="18" height="11" rx="2" ry="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/>
                          </svg>
                          <span style={{ color: 'var(--text-tertiary)' }}>Upgrade to view</span>
                        </span>
                      )}
                    </div>
                    <div style={{
                      fontSize: '13px', fontWeight: 500, color: 'var(--text-tertiary)', marginTop: '2px',
                    }}>{pick.away_team} @ {pick.home_team}</div>
                    <div style={{
                      fontSize: '12px', fontWeight: 600, color: 'var(--text-tertiary)', marginTop: '2px',
                      fontFamily: 'var(--font-mono)',
                    }}>{pick.game_date}</div>
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <div style={{ textAlign: 'right' }}>
                      <div style={{
                        fontFamily: 'var(--font-mono)', fontSize: '14px', fontWeight: 700,
                        color: pick.result === 'win' ? 'var(--green-profit)'
                          : pick.result === 'loss' ? 'var(--red-loss)' : 'var(--text-tertiary)',
                      }}>
                        {pick.result === 'win' ? `+${pick.pnl != null ? pick.pnl : 91}u`
                          : pick.result === 'loss' ? `${pick.pnl != null ? pick.pnl : -100}u`
                          : 'Pending'}
                      </div>
                      {isPro && pick.edge_pct && (
                        <div style={{
                          fontSize: '12px', fontWeight: 600, color: 'var(--text-tertiary)', marginTop: '2px',
                          fontFamily: 'var(--font-mono)',
                        }}>{pick.edge_pct}% edge</div>
                      )}
                    </div>
                    {canViewResolution && (
                      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="var(--text-tertiary)" strokeWidth="2">
                        <polyline points="9 18 15 12 9 6"/>
                      </svg>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}

function SmallStat({ label, value, color }) {
  return (
    <div>
      <div style={{
        fontFamily: 'var(--font-mono)', fontSize: '15px',
        fontWeight: 700, color: color || 'var(--text-primary)',
      }}>{value}</div>
      <div style={{
        fontSize: '11px', fontWeight: 600, color: 'var(--text-tertiary)',
        textTransform: 'uppercase', letterSpacing: '0.05em',
      }}>{label}</div>
    </div>
  );
}
