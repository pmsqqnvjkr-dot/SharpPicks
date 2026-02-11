import { useAuth } from '../../hooks/useAuth';
import { useApi } from '../../hooks/useApi';

export default function DashboardTab() {
  const { user } = useAuth();
  const { data: stats, loading } = useApi('/public/stats');
  const { data: record } = useApi('/public/record');

  const isPro = user && (user.is_premium || user.subscription_status === 'active' || user.subscription_status === 'trial');

  if (loading) {
    return (
      <div style={{ padding: '20px', textAlign: 'center' }}>
        <p style={{ color: 'var(--text-secondary)', fontSize: '14px' }}>Loading dashboard...</p>
      </div>
    );
  }

  const picks = record?.picks || [];
  const resolvedPicks = picks.filter(p => p.result === 'win' || p.result === 'loss');

  let equityData = [];
  let running = 0;
  resolvedPicks.reverse().forEach(p => {
    running += (p.pnl || 0);
    equityData.push({ date: p.game_date, value: running });
  });

  return (
    <div style={{ padding: '0' }}>
      <div style={{ padding: '20px 20px 16px' }}>
        <h1 style={{
          fontFamily: 'var(--font-serif)',
          fontSize: '22px',
          fontWeight: 600,
          color: 'var(--text-primary)',
        }}>
          Dashboard
        </h1>
        <p style={{
          fontFamily: 'var(--font-mono)',
          fontSize: '12px',
          color: 'var(--text-tertiary)',
          marginTop: '2px',
        }}>
          Performance overview
        </p>
      </div>

      <div style={{ padding: '0 20px' }}>
        <div style={{
          backgroundColor: 'var(--surface-1)',
          borderRadius: '16px',
          padding: '20px',
          border: '1px solid var(--stroke-subtle)',
          marginBottom: '12px',
        }}>
          <h3 style={{
            fontSize: '12px',
            fontWeight: 600,
            color: 'var(--text-tertiary)',
            textTransform: 'uppercase',
            letterSpacing: '0.05em',
            marginBottom: '16px',
          }}>
            Overall Performance
          </h3>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
            <StatCard label="Record" value={stats?.record || '0-0'} />
            <StatCard
              label="P&L"
              value={`${stats?.pnl >= 0 ? '+' : ''}${stats?.pnl || 0}u`}
              color={stats?.pnl >= 0 ? 'var(--green-profit)' : 'var(--red-loss)'}
            />
            <StatCard label="Win Rate" value={`${stats?.win_rate || 0}%`} />
            <StatCard
              label="ROI"
              value={`${stats?.roi >= 0 ? '+' : ''}${stats?.roi || 0}%`}
              color={stats?.roi >= 0 ? 'var(--green-profit)' : 'var(--red-loss)'}
            />
          </div>
        </div>

        <div style={{
          backgroundColor: 'var(--surface-1)',
          borderRadius: '16px',
          padding: '20px',
          border: '1px solid var(--stroke-subtle)',
          marginBottom: '12px',
        }}>
          <h3 style={{
            fontSize: '12px',
            fontWeight: 600,
            color: 'var(--text-tertiary)',
            textTransform: 'uppercase',
            letterSpacing: '0.05em',
            marginBottom: '16px',
          }}>
            Equity Curve
          </h3>
          {equityData.length > 0 ? (
            <EquityChart data={equityData} />
          ) : (
            <div style={{
              textAlign: 'center',
              padding: '24px',
              color: 'var(--text-tertiary)',
              fontSize: '13px',
            }}>
              No resolved picks yet. The equity curve will appear as picks are settled.
            </div>
          )}
        </div>

        <div style={{
          backgroundColor: 'var(--surface-1)',
          borderRadius: '16px',
          padding: '20px',
          border: '1px solid var(--stroke-subtle)',
          marginBottom: '12px',
        }}>
          <h3 style={{
            fontSize: '12px',
            fontWeight: 600,
            color: 'var(--text-tertiary)',
            textTransform: 'uppercase',
            letterSpacing: '0.05em',
            marginBottom: '16px',
          }}>
            Discipline Stats
          </h3>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '12px' }}>
            <MiniCard label="Total Picks" value={stats?.total_picks || 0} />
            <MiniCard label="Total Passes" value={stats?.total_passes || 0} />
            <MiniCard label="Selectivity" value={`${stats?.selectivity || 0}%`} />
          </div>
        </div>

        {picks.length > 0 && (
          <div style={{
            backgroundColor: 'var(--surface-1)',
            borderRadius: '16px',
            padding: '20px',
            border: '1px solid var(--stroke-subtle)',
          }}>
            <h3 style={{
              fontSize: '12px',
              fontWeight: 600,
              color: 'var(--text-tertiary)',
              textTransform: 'uppercase',
              letterSpacing: '0.05em',
              marginBottom: '16px',
            }}>
              Recent Picks
            </h3>
            {picks.slice(0, 10).map(p => (
              <div key={p.id} style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                padding: '12px 0',
                borderBottom: '1px solid var(--stroke-subtle)',
              }}>
                <div>
                  <div style={{
                    fontSize: '14px',
                    fontWeight: 500,
                    color: 'var(--text-primary)',
                  }}>
                    {p.side}
                  </div>
                  <div style={{
                    fontSize: '12px',
                    color: 'var(--text-tertiary)',
                    marginTop: '2px',
                  }}>
                    {p.away_team} @ {p.home_team}
                  </div>
                </div>
                <div style={{
                  fontFamily: 'var(--font-mono)',
                  fontSize: '13px',
                  fontWeight: 600,
                  color: p.result === 'win' ? 'var(--green-profit)'
                    : p.result === 'loss' ? 'var(--red-loss)'
                    : 'var(--text-tertiary)',
                }}>
                  {p.result === 'win' ? `+${p.pnl || 91}u` : p.result === 'loss' ? `${p.pnl || -110}u` : 'Pending'}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

function StatCard({ label, value, color }) {
  return (
    <div style={{
      backgroundColor: 'var(--surface-2)',
      borderRadius: '10px',
      padding: '14px',
    }}>
      <div style={{
        fontFamily: 'var(--font-mono)',
        fontSize: '20px',
        fontWeight: 700,
        color: color || 'var(--text-primary)',
      }}>
        {value}
      </div>
      <div style={{
        fontSize: '11px',
        color: 'var(--text-tertiary)',
        textTransform: 'uppercase',
        letterSpacing: '0.05em',
        marginTop: '4px',
      }}>
        {label}
      </div>
    </div>
  );
}

function MiniCard({ label, value }) {
  return (
    <div style={{
      backgroundColor: 'var(--surface-2)',
      borderRadius: '10px',
      padding: '12px',
      textAlign: 'center',
    }}>
      <div style={{
        fontFamily: 'var(--font-mono)',
        fontSize: '18px',
        fontWeight: 600,
        color: 'var(--text-primary)',
      }}>
        {value}
      </div>
      <div style={{
        fontSize: '10px',
        color: 'var(--text-tertiary)',
        textTransform: 'uppercase',
        letterSpacing: '0.05em',
        marginTop: '4px',
      }}>
        {label}
      </div>
    </div>
  );
}

function EquityChart({ data }) {
  if (data.length < 2) {
    return (
      <div style={{ textAlign: 'center', padding: '24px', color: 'var(--text-tertiary)', fontSize: '13px' }}>
        Need at least 2 resolved picks to show equity curve.
      </div>
    );
  }

  const maxVal = Math.max(...data.map(d => Math.abs(d.value)), 1);
  const height = 120;
  const width = 280;
  const padding = 20;

  const points = data.map((d, i) => {
    const x = padding + (i / (data.length - 1)) * (width - padding * 2);
    const y = height / 2 - (d.value / maxVal) * (height / 2 - padding);
    return `${x},${y}`;
  }).join(' ');

  const lastValue = data[data.length - 1].value;

  return (
    <div style={{ textAlign: 'center' }}>
      <svg viewBox={`0 0 ${width} ${height}`} style={{ width: '100%', maxWidth: '300px' }}>
        <line x1={padding} y1={height/2} x2={width-padding} y2={height/2}
          stroke="var(--stroke-subtle)" strokeWidth="1" strokeDasharray="4,4" />
        <polyline
          points={points}
          fill="none"
          stroke={lastValue >= 0 ? 'var(--green-profit)' : 'var(--red-loss)'}
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      </svg>
    </div>
  );
}
