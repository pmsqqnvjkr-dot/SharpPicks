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
  const passes = record?.passes || [];
  const resolvedPicks = [...picks].filter(p => p.result === 'win' || p.result === 'loss');
  resolvedPicks.sort((a, b) => (a.game_date || '').localeCompare(b.game_date || ''));

  let equityData = [];
  let running = 0;
  resolvedPicks.forEach(p => {
    running += (p.pnl || 0);
    equityData.push({ date: p.game_date, value: running });
  });

  const streakInfo = computeStreak(resolvedPicks);
  const monthlyData = computeMonthly(resolvedPicks);

  return (
    <div style={{ padding: '0', paddingBottom: '100px' }}>
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
        <SectionCard title="Overall Performance">
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
        </SectionCard>

        <SectionCard title="Current Streak">
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '12px' }}>
            <MiniCard
              label="Current"
              value={`${streakInfo.current}${streakInfo.currentType}`}
              color={streakInfo.currentType === 'W' ? 'var(--green-profit)' : streakInfo.currentType === 'L' ? 'var(--red-loss)' : 'var(--text-primary)'}
            />
            <MiniCard
              label="Best Win"
              value={`${streakInfo.bestWin}W`}
              color="var(--green-profit)"
            />
            <MiniCard
              label="Worst Loss"
              value={`${streakInfo.worstLoss}L`}
              color="var(--red-loss)"
            />
          </div>
          {resolvedPicks.length > 0 && (
            <div style={{
              marginTop: '16px',
              display: 'flex',
              gap: '4px',
              flexWrap: 'wrap',
            }}>
              {resolvedPicks.slice(-20).map((p, i) => (
                <div key={i} style={{
                  width: '24px',
                  height: '24px',
                  borderRadius: '4px',
                  backgroundColor: p.result === 'win' ? 'rgba(52, 211, 153, 0.2)' : 'rgba(239, 68, 68, 0.2)',
                  border: `1px solid ${p.result === 'win' ? 'rgba(52, 211, 153, 0.4)' : 'rgba(239, 68, 68, 0.4)'}`,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  fontSize: '10px',
                  fontWeight: 600,
                  fontFamily: 'var(--font-mono)',
                  color: p.result === 'win' ? 'var(--green-profit)' : 'var(--red-loss)',
                }}>
                  {p.result === 'win' ? 'W' : 'L'}
                </div>
              ))}
            </div>
          )}
        </SectionCard>

        <SectionCard title="Equity Curve">
          {equityData.length > 1 ? (
            <EquityChart data={equityData} />
          ) : (
            <div style={{
              textAlign: 'center',
              padding: '24px',
              color: 'var(--text-tertiary)',
              fontSize: '13px',
            }}>
              Need at least 2 resolved picks to show equity curve.
            </div>
          )}
        </SectionCard>

        <SectionCard title="Discipline Stats">
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '12px' }}>
            <MiniCard label="Total Picks" value={stats?.total_picks || 0} />
            <MiniCard label="Total Passes" value={stats?.total_passes || 0} />
            <MiniCard label="Selectivity" value={`${stats?.selectivity || 0}%`} />
          </div>
        </SectionCard>

        {monthlyData.length > 0 && (
          <SectionCard title="Monthly Breakdown">
            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
              {monthlyData.map((m, i) => (
                <div key={i} style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  padding: '12px 14px',
                  backgroundColor: 'var(--surface-2)',
                  borderRadius: '10px',
                }}>
                  <div>
                    <div style={{
                      fontSize: '14px',
                      fontWeight: 500,
                      color: 'var(--text-primary)',
                    }}>
                      {m.label}
                    </div>
                    <div style={{
                      fontFamily: 'var(--font-mono)',
                      fontSize: '12px',
                      color: 'var(--text-tertiary)',
                      marginTop: '2px',
                    }}>
                      {m.wins}W-{m.losses}L ({m.picks} picks)
                    </div>
                  </div>
                  <div style={{
                    fontFamily: 'var(--font-mono)',
                    fontSize: '14px',
                    fontWeight: 600,
                    color: m.pnl >= 0 ? 'var(--green-profit)' : 'var(--red-loss)',
                  }}>
                    {m.pnl >= 0 ? '+' : ''}{m.pnl}u
                  </div>
                </div>
              ))}
            </div>
          </SectionCard>
        )}

        {picks.length > 0 && (
          <SectionCard title="Recent Picks">
            {picks.slice(0, 10).map((p, i) => (
              <div key={p.id} style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                padding: '12px 0',
                borderBottom: i < Math.min(picks.length, 10) - 1 ? '1px solid var(--stroke-subtle)' : 'none',
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
          </SectionCard>
        )}
      </div>
    </div>
  );
}

function computeStreak(picks) {
  if (picks.length === 0) return { current: 0, currentType: '', bestWin: 0, worstLoss: 0 };

  let current = 0;
  let currentType = '';
  let bestWin = 0;
  let worstLoss = 0;
  let streak = 0;
  let lastResult = '';

  for (let i = picks.length - 1; i >= 0; i--) {
    if (i === picks.length - 1) {
      lastResult = picks[i].result;
      streak = 1;
    } else if (picks[i].result === lastResult) {
      streak++;
    } else {
      break;
    }
  }
  current = streak;
  currentType = lastResult === 'win' ? 'W' : 'L';

  let ws = 0, ls = 0;
  for (const p of picks) {
    if (p.result === 'win') {
      ws++;
      ls = 0;
      bestWin = Math.max(bestWin, ws);
    } else {
      ls++;
      ws = 0;
      worstLoss = Math.max(worstLoss, ls);
    }
  }

  return { current, currentType, bestWin, worstLoss };
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

function SectionCard({ title, children }) {
  return (
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
        {title}
      </h3>
      {children}
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

function MiniCard({ label, value, color }) {
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
        color: color || 'var(--text-primary)',
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
  const height = 140;
  const width = 320;
  const padL = 40;
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
  const steps = 3;
  for (let i = 0; i <= steps; i++) {
    const v = minVal + (range / steps) * i;
    ticks.push({ value: Math.round(v), y: getY(v) });
  }

  return (
    <div>
      <svg viewBox={`0 0 ${width} ${height}`} style={{ width: '100%' }}>
        <defs>
          <linearGradient id="equityGrad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={isPositive ? 'var(--green-profit)' : 'var(--red-loss)'} stopOpacity="0.3" />
            <stop offset="100%" stopColor={isPositive ? 'var(--green-profit)' : 'var(--red-loss)'} stopOpacity="0" />
          </linearGradient>
        </defs>

        {ticks.map((t, i) => (
          <g key={i}>
            <line x1={padL} y1={t.y} x2={width - padR} y2={t.y}
              stroke="var(--stroke-subtle)" strokeWidth="0.5" strokeDasharray="3,3" />
            <text x={padL - 6} y={t.y + 3}
              textAnchor="end"
              fill="var(--text-tertiary)"
              fontSize="8"
              fontFamily="var(--font-mono)">
              {t.value}u
            </text>
          </g>
        ))}

        <polygon points={areaPoints} fill="url(#equityGrad)" />

        <polyline
          points={linePoints}
          fill="none"
          stroke={isPositive ? 'var(--green-profit)' : 'var(--red-loss)'}
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
        />

        <circle
          cx={getX(data.length - 1)}
          cy={getY(lastValue)}
          r="4"
          fill={isPositive ? 'var(--green-profit)' : 'var(--red-loss)'}
          stroke="var(--surface-1)"
          strokeWidth="2"
        />

        {data.length <= 10 && data.map((d, i) => {
          const label = d.date ? d.date.substring(5) : '';
          return (
            <text key={i} x={getX(i)} y={height - 5}
              textAnchor="middle"
              fill="var(--text-tertiary)"
              fontSize="7"
              fontFamily="var(--font-mono)">
              {label}
            </text>
          );
        })}
      </svg>

      <div style={{
        textAlign: 'center',
        marginTop: '8px',
        fontFamily: 'var(--font-mono)',
        fontSize: '14px',
        fontWeight: 600,
        color: isPositive ? 'var(--green-profit)' : 'var(--red-loss)',
      }}>
        {isPositive ? '+' : ''}{lastValue}u total
      </div>
    </div>
  );
}
