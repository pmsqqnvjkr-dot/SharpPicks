import { useAuth } from '../../hooks/useAuth';
import { useApi } from '../../hooks/useApi';

export default function DashboardTab() {
  const { user } = useAuth();
  const { data: stats, loading } = useApi('/public/stats');
  const { data: record } = useApi('/public/record');
  const { data: todayData } = useApi('/picks/today');

  if (loading) {
    return (
      <div style={{ padding: '20px', textAlign: 'center' }}>
        <p style={{ color: 'var(--text-secondary)', fontSize: '14px' }}>Loading dashboard...</p>
      </div>
    );
  }

  const picks = record?.picks || [];
  const resolvedPicks = [...picks].filter(p => p.result === 'win' || p.result === 'loss');
  resolvedPicks.sort((a, b) => (a.game_date || '').localeCompare(b.game_date || ''));

  let equityData = [];
  let running = 0;
  resolvedPicks.forEach(p => {
    running += (p.pnl || 0);
    equityData.push({ date: p.game_date, value: running });
  });

  const monthlyData = computeMonthly(resolvedPicks);
  const todayIsPass = todayData?.type === 'pass';
  const todayIsPick = todayData?.type === 'pick';

  return (
    <div style={{ padding: '0', paddingBottom: '100px' }}>
      <div style={{
        padding: '16px 20px',
        display: 'flex', justifyContent: 'space-between', alignItems: 'center',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <img src="/logo-1024.png" alt="" style={{ width: '28px', height: '28px', borderRadius: '6px' }} />
          <span style={{
            fontFamily: 'var(--font-sans)', fontSize: '13px', fontWeight: 700,
            color: 'var(--text-primary)', letterSpacing: '0.12em', textTransform: 'uppercase',
          }}>Sharp Picks</span>
        </div>
        {user && (
          <div style={{
            width: '32px', height: '32px', borderRadius: '50%',
            backgroundColor: 'var(--surface-2)', border: '1px solid var(--stroke-subtle)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            fontSize: '13px', fontWeight: 600, color: 'var(--text-secondary)',
          }}>
            {user.email ? user.email[0].toUpperCase() : 'U'}
          </div>
        )}
      </div>

      <div style={{ padding: '0 20px' }}>
        <div style={{
          fontSize: '11px', fontWeight: 600, color: 'var(--text-tertiary)',
          textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: '10px',
        }}>Performance</div>

        <div style={{
          backgroundColor: 'var(--surface-1)', borderRadius: '16px',
          border: '1px solid var(--stroke-subtle)', padding: '24px 20px 16px',
          marginBottom: '12px',
        }}>
          <div style={{
            fontFamily: 'var(--font-mono)', fontSize: '48px', fontWeight: 700,
            color: stats?.pnl >= 0 ? 'var(--green-profit)' : 'var(--red-loss)',
            lineHeight: '1',
            marginBottom: '12px',
          }}>
            {stats?.pnl >= 0 ? '+' : ''}${Math.abs(stats?.pnl || 0)}
          </div>

          <div style={{
            display: 'flex', gap: '16px', marginBottom: '20px',
          }}>
            <span style={{
              fontFamily: 'var(--font-mono)', fontSize: '13px', color: 'var(--text-secondary)',
            }}>
              {stats?.roi >= 0 ? '+' : ''}{stats?.roi || 0}% ROI
            </span>
            <span style={{
              fontFamily: 'var(--font-mono)', fontSize: '13px', color: 'var(--text-secondary)',
            }}>
              {stats?.record || '0-0'} Record
            </span>
          </div>

          {equityData.length > 1 && (
            <div style={{ position: 'relative' }}>
              <EquityChart data={equityData} />
            </div>
          )}
        </div>

        <div style={{
          backgroundColor: 'var(--surface-1)', borderRadius: '12px',
          border: '1px solid var(--stroke-subtle)', padding: '14px 16px',
          marginBottom: '12px',
          display: 'flex', alignItems: 'center', gap: '10px',
        }}>
          <div style={{
            width: '8px', height: '8px', borderRadius: '50%',
            backgroundColor: todayIsPick ? 'var(--green-profit)' : todayIsPass ? 'var(--text-tertiary)' : 'var(--gold-pro)',
          }} />
          <span style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>
            {todayIsPass
              ? `Analyzing ${todayData.games_analyzed} games · Market efficient today`
              : todayIsPick
                ? 'Pick published today'
                : 'Waiting for game data'}
          </span>
        </div>

        {todayData && (todayIsPass || todayIsPick) && (
          <>
            <div style={{
              fontSize: '11px', fontWeight: 600, color: 'var(--text-tertiary)',
              textTransform: 'uppercase', letterSpacing: '0.06em',
              marginBottom: '10px', marginTop: '8px',
            }}>Expected Edge</div>

            <div style={{
              backgroundColor: 'var(--surface-1)', borderRadius: '16px',
              border: '1px solid var(--stroke-subtle)', padding: '20px',
              marginBottom: '12px',
            }}>
              <div style={{
                fontFamily: 'var(--font-mono)', fontSize: '32px', fontWeight: 700,
                color: todayIsPick ? 'var(--green-profit)' : 'var(--text-primary)',
                marginBottom: '12px',
              }}>
                {todayIsPick
                  ? `+${todayData.edge_pct || 0}%`
                  : todayData.closest_edge_pct
                    ? `+${todayData.closest_edge_pct}%`
                    : '--'}
              </div>
              {todayIsPick ? (
                <div style={{ display: 'flex', gap: '24px' }}>
                  <div>
                    <div style={{
                      fontSize: '10px', color: 'var(--text-tertiary)',
                      textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: '4px',
                    }}>Model Line</div>
                    <div style={{
                      fontFamily: 'var(--font-mono)', fontSize: '18px', fontWeight: 600,
                      color: 'var(--text-primary)',
                    }}>{todayData.line || '--'}</div>
                  </div>
                  <div>
                    <div style={{
                      fontSize: '10px', color: 'var(--text-tertiary)',
                      textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: '4px',
                    }}>Market</div>
                    <div style={{
                      fontFamily: 'var(--font-mono)', fontSize: '18px', fontWeight: 600,
                      color: 'var(--text-primary)',
                    }}>{todayData.market_line || '--'}</div>
                  </div>
                </div>
              ) : (
                <p style={{ fontSize: '13px', color: 'var(--text-secondary)', lineHeight: '1.5' }}>
                  Best edge found was {todayData.closest_edge_pct || 0}% — below the 3.5% threshold. No action.
                </p>
              )}
            </div>
          </>
        )}

        <div style={{
          fontSize: '11px', fontWeight: 600, color: 'var(--text-tertiary)',
          textTransform: 'uppercase', letterSpacing: '0.06em',
          marginBottom: '10px', marginTop: '8px',
        }}>Behavioral Edge</div>

        <div style={{
          backgroundColor: 'var(--surface-1)', borderRadius: '16px',
          border: '1px solid var(--stroke-subtle)', padding: '20px',
          marginBottom: '12px',
        }}>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
            <EdgeStat label="Selectivity" value={`${stats?.selectivity || 0}%`} context="vs 78% industry" />
            <EdgeStat label="Pass Days" value={stats?.capital_preserved_days || 0} context="capital preserved" />
            <EdgeStat label="Win Rate" value={`${stats?.win_rate || 0}%`} context="on picks taken" />
            <EdgeStat label="Avg Edge" value={`${stats?.avg_edge || 0}%`} context="when firing" />
          </div>
        </div>

        {monthlyData.length > 0 && (
          <>
            <div style={{
              fontSize: '11px', fontWeight: 600, color: 'var(--text-tertiary)',
              textTransform: 'uppercase', letterSpacing: '0.06em',
              marginBottom: '10px', marginTop: '8px',
            }}>Monthly Breakdown</div>

            <div style={{
              backgroundColor: 'var(--surface-1)', borderRadius: '16px',
              border: '1px solid var(--stroke-subtle)', overflow: 'hidden',
              marginBottom: '12px',
            }}>
              {monthlyData.map((m, i) => (
                <div key={i} style={{
                  padding: '14px 20px',
                  borderBottom: i < monthlyData.length - 1 ? '1px solid var(--stroke-subtle)' : 'none',
                  display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                }}>
                  <div>
                    <div style={{ fontSize: '14px', fontWeight: 500, color: 'var(--text-primary)' }}>
                      {m.label}
                    </div>
                    <div style={{
                      fontFamily: 'var(--font-mono)', fontSize: '12px',
                      color: 'var(--text-tertiary)', marginTop: '2px',
                    }}>
                      {m.wins}W-{m.losses}L ({m.picks} picks)
                    </div>
                  </div>
                  <div style={{
                    fontFamily: 'var(--font-mono)', fontSize: '14px', fontWeight: 600,
                    color: m.pnl >= 0 ? 'var(--green-profit)' : 'var(--red-loss)',
                  }}>
                    {m.pnl >= 0 ? '+' : ''}{m.pnl}u
                  </div>
                </div>
              ))}
            </div>
          </>
        )}
      </div>
    </div>
  );
}

function EdgeStat({ label, value, context }) {
  return (
    <div>
      <div style={{
        fontFamily: 'var(--font-mono)', fontSize: '20px', fontWeight: 700,
        color: 'var(--text-primary)', marginBottom: '2px',
      }}>{value}</div>
      <div style={{
        fontSize: '11px', color: 'var(--text-tertiary)',
        textTransform: 'uppercase', letterSpacing: '0.05em',
      }}>{label}</div>
      {context && (
        <div style={{
          fontSize: '11px', color: 'var(--text-tertiary)', marginTop: '2px',
          fontStyle: 'italic',
        }}>{context}</div>
      )}
    </div>
  );
}

function computeMonthly(picks) {
  const months = {};
  for (const p of picks) {
    const date = p.game_date || '';
    const key = date.substring(0, 7);
    if (!key) continue;
    if (!months[key]) months[key] = { wins: 0, losses: 0, pnl: 0, picks: 0 };
    months[key].picks++;
    if (p.result === 'win') months[key].wins++;
    else months[key].losses++;
    months[key].pnl += (p.pnl || 0);
  }

  const monthNames = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
  return Object.entries(months)
    .sort(([a], [b]) => b.localeCompare(a))
    .map(([key, data]) => {
      const [year, month] = key.split('-');
      return {
        label: `${monthNames[parseInt(month) - 1]} ${year}`,
        ...data,
        pnl: Math.round(data.pnl),
      };
    });
}

function EquityChart({ data }) {
  const height = 120;
  const width = 300;
  const padL = 0;
  const padR = 0;
  const padT = 5;
  const padB = 24;

  const values = data.map(d => d.value);
  const minVal = Math.min(0, ...values);
  const maxVal = Math.max(0, ...values);
  const range = maxVal - minVal || 1;

  const chartW = width - padL - padR;
  const chartH = height - padT - padB;

  const getX = (i) => padL + (i / (data.length - 1)) * chartW;
  const getY = (v) => padT + chartH - ((v - minVal) / range) * chartH;

  const linePoints = data.map((d, i) => `${getX(i)},${getY(d.value)}`).join(' ');

  const areaPoints = [
    `${getX(0)},${height - padB}`,
    ...data.map((d, i) => `${getX(i)},${getY(d.value)}`),
    `${getX(data.length - 1)},${height - padB}`,
  ].join(' ');

  const lastValue = data[data.length - 1].value;
  const isPositive = lastValue >= 0;

  const months = {};
  data.forEach((d, i) => {
    if (d.date) {
      const monthNames = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
      const m = parseInt(d.date.substring(5, 7)) - 1;
      const key = d.date.substring(0, 7);
      if (!months[key]) months[key] = { label: monthNames[m], x: getX(i) };
    }
  });

  return (
    <div style={{ position: 'relative' }}>
      <svg viewBox={`0 0 ${width} ${height}`} style={{ width: '100%', display: 'block' }}>
        <defs>
          <linearGradient id="dashEquityGrad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={isPositive ? 'var(--green-profit)' : 'var(--red-loss)'} stopOpacity="0.2" />
            <stop offset="100%" stopColor={isPositive ? 'var(--green-profit)' : 'var(--red-loss)'} stopOpacity="0" />
          </linearGradient>
        </defs>

        <polygon points={areaPoints} fill="url(#dashEquityGrad)" />

        <polyline points={linePoints} fill="none"
          stroke={isPositive ? 'var(--green-profit)' : 'var(--red-loss)'}
          strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />

        <circle
          cx={getX(data.length - 1)} cy={getY(lastValue)} r="3"
          fill={isPositive ? 'var(--green-profit)' : 'var(--red-loss)'}
        />

        {Object.values(months).map((m, i) => (
          <text key={i} x={m.x} y={height - 4}
            textAnchor="middle" fill="var(--text-tertiary)"
            fontSize="9" fontFamily="var(--font-mono)">
            {m.label}
          </text>
        ))}
      </svg>
    </div>
  );
}
