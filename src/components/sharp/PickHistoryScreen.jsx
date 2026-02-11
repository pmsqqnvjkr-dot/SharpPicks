import { useState } from 'react';
import { useApi } from '../../hooks/useApi';

export default function PickHistoryScreen({ onBack }) {
  const { data, loading } = useApi('/public/record');
  const [filter, setFilter] = useState('all');

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

      <div style={{
        padding: '0 20px 12px', display: 'flex', gap: '8px',
      }}>
        {['all', 'wins', 'losses', 'pending'].map(f => (
          <button key={f} onClick={() => setFilter(f)} style={{
            padding: '6px 14px', borderRadius: '8px', fontSize: '12px',
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
            {filtered.map((pick, i) => (
              <div key={pick.id} style={{
                padding: '14px 20px',
                borderBottom: i < filtered.length - 1 ? '1px solid var(--stroke-subtle)' : 'none',
                display: 'flex', justifyContent: 'space-between', alignItems: 'center',
              }}>
                <div>
                  <div style={{
                    fontSize: '14px', fontWeight: 500, color: 'var(--text-primary)',
                  }}>{pick.side}</div>
                  <div style={{
                    fontSize: '12px', color: 'var(--text-tertiary)', marginTop: '2px',
                  }}>{pick.away_team} @ {pick.home_team}</div>
                  <div style={{
                    fontSize: '11px', color: 'var(--text-tertiary)', marginTop: '2px',
                    fontFamily: 'var(--font-mono)',
                  }}>{pick.game_date}</div>
                </div>
                <div style={{ textAlign: 'right' }}>
                  <div style={{
                    fontFamily: 'var(--font-mono)', fontSize: '13px', fontWeight: 600,
                    color: pick.result === 'win' ? 'var(--green-profit)'
                      : pick.result === 'loss' ? 'var(--red-loss)' : 'var(--text-tertiary)',
                  }}>
                    {pick.result === 'win' ? `+${pick.pnl || 91}u`
                      : pick.result === 'loss' ? `${pick.pnl || -110}u`
                      : 'Pending'}
                  </div>
                  {pick.edge_pct && (
                    <div style={{
                      fontSize: '11px', color: 'var(--text-tertiary)', marginTop: '2px',
                      fontFamily: 'var(--font-mono)',
                    }}>{pick.edge_pct}% edge</div>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
