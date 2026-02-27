import { useState } from 'react';
import { useApi } from '../../hooks/useApi';
import { useAuth } from '../../hooks/useAuth';
import EdgeDots from './EdgeDots';

export default function PickHistoryScreen({ onBack, onViewResolution }) {
  const { data, loading } = useApi('/public/record');
  const { user } = useAuth();
  const [filter, setFilter] = useState('all');

  const [showAll, setShowAll] = useState(false);
  const INITIAL_LIMIT = 6;

  const isPro = user && (user.is_premium || user.subscription_status === 'active' || user.subscription_status === 'trial' || user.founding_member);
  const picks = data?.picks || [];
  const filtered = filter === 'all' ? picks
    : filter === 'wins' ? picks.filter(p => p.result === 'win')
    : filter === 'losses' ? picks.filter(p => p.result === 'loss')
    : picks.filter(p => p.result === 'pending');
  const visible = showAll ? filtered : filtered.slice(0, INITIAL_LIMIT);
  const hasMore = filtered.length > INITIAL_LIMIT;

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

      {data?.calibration_note && data.picks?.some(p => p.pre_calibration) && (
        <div style={{ padding: '0 20px 8px' }}>
          <div style={{
            backgroundColor: 'rgba(255, 183, 77, 0.08)', borderRadius: '10px',
            padding: '12px 16px', border: '1px solid rgba(255, 183, 77, 0.15)',
            display: 'flex', alignItems: 'flex-start', gap: '10px',
          }}>
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="rgba(255, 183, 77, 0.7)" strokeWidth="2" style={{ flexShrink: 0, marginTop: '1px' }}>
              <circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/>
            </svg>
            <p style={{
              fontFamily: 'var(--font-sans)', fontSize: '12px', lineHeight: '1.5',
              color: 'rgba(255, 183, 77, 0.85)', margin: 0,
            }}>{data.calibration_note}</p>
          </div>
        </div>
      )}

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
          <button key={f} onClick={() => { setFilter(f); setShowAll(false); }} style={{
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
            {visible.map((pick, i) => {
              const isResolved = pick.result === 'win' || pick.result === 'loss';
              const isRevoked = pick.result === 'revoked';
              const canViewResolution = isPro && isResolved && onViewResolution;
              const borderColor = pick.result === 'win' ? '#22c55e'
                : pick.result === 'loss' ? '#ef4444'
                : isRevoked ? '#7c3aed' : '#6b7280';
              return (
                <div key={pick.id} onClick={() => canViewResolution && onViewResolution(pick)} style={{
                  padding: '16px 16px 16px 18px',
                  borderLeft: `4px solid ${borderColor}`,
                  borderBottom: i < visible.length - 1 ? '1px solid rgba(255,255,255,0.06)' : 'none',
                  display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                  cursor: canViewResolution ? 'pointer' : 'default',
                  minHeight: '72px',
                }}>
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{
                      fontSize: '16px', fontWeight: 700, color: '#f9fafb', lineHeight: 1.3,
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
                      fontSize: '13px', fontWeight: 400, color: '#9ca3af', marginTop: '2px',
                    }}>{pick.away_team} @ {pick.home_team}</div>
                    <div style={{
                      fontSize: '11px', fontWeight: 400, color: '#6b7280', marginTop: '2px',
                      fontFamily: 'var(--font-mono)', display: 'flex', alignItems: 'center', gap: '6px',
                    }}>
                      {pick.game_date}
                      {pick.pre_calibration && (
                        <span style={{
                          fontSize: '9px', fontWeight: 700, textTransform: 'uppercase',
                          letterSpacing: '0.05em', color: 'rgba(255, 183, 77, 0.7)',
                          backgroundColor: 'rgba(255, 183, 77, 0.1)',
                          padding: '1px 5px', borderRadius: '3px',
                        }}>Pre-Cal</span>
                      )}
                    </div>
                  </div>
                  <div style={{
                    display: 'flex', flexDirection: 'column', alignItems: 'flex-end',
                    justifyContent: 'center', gap: '4px', flexShrink: 0, marginLeft: '12px',
                  }}>
                    {isResolved ? (
                      <div style={{
                        fontFamily: 'var(--font-mono)', fontSize: '17px', fontWeight: 700,
                        lineHeight: 1,
                        color: pick.result === 'win' ? '#22c55e' : '#ef4444',
                      }}>
                        {pick.result === 'win' ? `+${pick.pnl != null ? pick.pnl : 91}u`
                          : `${pick.pnl != null ? pick.pnl : -100}u`}
                      </div>
                    ) : (
                      <span style={{
                        display: 'inline-flex', alignItems: 'center',
                        padding: '3px 10px', borderRadius: '999px',
                        fontSize: '11px', fontWeight: 600, letterSpacing: '0.04em',
                        textTransform: 'uppercase',
                        backgroundColor: isRevoked ? 'rgba(124,58,237,0.12)' : 'rgba(107,114,128,0.15)',
                        color: isRevoked ? '#a78bfa' : '#9ca3af',
                      }}>{isRevoked ? 'Withdrawn' : 'Pending'}</span>
                    )}
                    {isPro && pick.edge_pct && (
                      <>
                        <div style={{
                          fontSize: '11px', fontWeight: 500, color: '#6b7280',
                          fontFamily: 'var(--font-mono)', textAlign: 'right',
                        }}>{pick.edge_pct}% edge</div>
                        <EdgeDots edge={parseFloat(pick.edge_pct)} />
                      </>
                    )}
                    {canViewResolution && (
                      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#4b5563" strokeWidth="2" style={{ marginTop: '4px' }}>
                        <polyline points="9 18 15 12 9 6"/>
                      </svg>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
          {hasMore && !showAll && (
            <button onClick={() => setShowAll(true)} style={{
              width: '100%', padding: '14px', marginTop: '12px',
              backgroundColor: 'var(--surface-2)', border: '1px solid var(--stroke-subtle)',
              borderRadius: '12px', cursor: 'pointer',
              fontFamily: 'var(--font-sans)', fontSize: '14px', fontWeight: 600,
              color: 'var(--blue-primary)',
              display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '6px',
            }}>
              Show All ({filtered.length - INITIAL_LIMIT} more)
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <polyline points="6 9 12 15 18 9"/>
              </svg>
            </button>
          )}
          {showAll && hasMore && (
            <button onClick={() => setShowAll(false)} style={{
              width: '100%', padding: '14px', marginTop: '12px',
              backgroundColor: 'var(--surface-2)', border: '1px solid var(--stroke-subtle)',
              borderRadius: '12px', cursor: 'pointer',
              fontFamily: 'var(--font-sans)', fontSize: '14px', fontWeight: 600,
              color: 'var(--text-secondary)',
              display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '6px',
            }}>
              Show Less
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <polyline points="18 15 12 9 6 15"/>
              </svg>
            </button>
          )}
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
