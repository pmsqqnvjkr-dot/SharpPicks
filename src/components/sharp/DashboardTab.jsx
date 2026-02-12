import { useState, useEffect } from 'react';
import { useAuth } from '../../hooks/useAuth';
import { useApi, apiGet } from '../../hooks/useApi';
import FreeTierDashboard from './FreeTierDashboard';

function SectionLabel({ children }) {
  return (
    <div style={{
      fontFamily: 'var(--font-mono)',
      fontSize: '10px', fontWeight: 600,
      letterSpacing: '2px', textTransform: 'uppercase',
      color: 'var(--text-tertiary)',
      marginBottom: '10px',
    }}>{children}</div>
  );
}

export default function DashboardTab({ onNavigate }) {
  const { user } = useAuth();
  const { data: stats, loading } = useApi('/public/stats');
  const { data: record } = useApi('/public/record');
  const { data: todayData } = useApi('/picks/today');
  const [userStats, setUserStats] = useState(null);

  const isPro = user && (user.is_premium || user.subscription_status === 'active' || user.subscription_status === 'trial');

  useEffect(() => {
    if (isPro && user) {
      apiGet('/user/stats').then(data => {
        if (data && !data.error) setUserStats(data);
      }).catch(() => {});
    }
  }, [isPro, user]);

  if (loading) {
    return (
      <div style={{ padding: '20px', textAlign: 'center' }}>
        <p style={{ color: 'var(--text-secondary)', fontSize: '14px' }}>Loading dashboard...</p>
      </div>
    );
  }

  if (!isPro) {
    return <FreeTierDashboard onUpgrade={() => onNavigate && onNavigate('profile', 'upgrade')} />;
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

  const todayIsPass = todayData?.type === 'pass';
  const todayIsPick = todayData?.type === 'pick';

  const totalPicks = stats?.total_picks || 0;
  const passDays = stats?.capital_preserved_days || 0;
  const totalDays = totalPicks + passDays || 1;
  const selectivity = stats?.selectivity || Math.round((totalPicks / totalDays) * 100);
  const daysPerBet = totalPicks > 0 ? (totalDays / totalPicks).toFixed(1) : '—';

  const hasUserBets = userStats && userStats.totalBets > 0;

  return (
    <div style={{ padding: '0', paddingBottom: '100px' }}>
      <div style={{
        padding: '16px 20px',
        display: 'flex', justifyContent: 'space-between', alignItems: 'center',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <svg viewBox="0 0 40 40" width="24" height="24" fill="none">
            <path d="M20 4L6 10v10c0 9.2 6 17.4 14 20 8-2.6 14-10.8 14-20V10L20 4z" stroke="white" strokeWidth="1.8" fill="none"/>
            <rect x="12" y="24" width="3" height="6" rx="1" fill="rgba(255,255,255,0.3)"/>
            <rect x="17" y="20" width="3" height="10" rx="1" fill="rgba(255,255,255,0.4)"/>
            <rect x="22" y="22" width="3" height="8" rx="1" fill="rgba(255,255,255,0.35)"/>
            <path d="M11 22L17 16L22 19L30 11" stroke="white" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"/>
            <path d="M26 11h4v4" stroke="white" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"/>
          </svg>
          <span style={{
            fontFamily: 'var(--font-sans)', fontSize: '13px', fontWeight: 700,
            color: 'var(--text-primary)', letterSpacing: '2px', textTransform: 'uppercase',
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

        <SectionLabel>Algorithm Record</SectionLabel>

        <div style={{
          backgroundColor: 'var(--surface-1)', borderRadius: '20px',
          border: '1px solid var(--stroke-subtle)', padding: '24px',
          marginBottom: '16px',
        }}>
          <div style={{
            fontFamily: 'var(--font-mono)', fontSize: '48px', fontWeight: 800,
            color: stats?.pnl >= 0 ? 'var(--green-profit)' : 'var(--red-loss)',
            lineHeight: '1',
            marginBottom: '4px',
          }}>
            {stats?.pnl >= 0 ? '+' : ''}{stats?.pnl || 0}u
          </div>

          <div style={{
            display: 'flex', gap: '16px', marginBottom: '20px',
          }}>
            <span style={{ fontFamily: 'var(--font-mono)', fontSize: '13px', color: 'var(--text-secondary)' }}>
              <strong style={{ color: 'var(--text-primary)', fontWeight: 600 }}>{stats?.roi >= 0 ? '+' : ''}{stats?.roi || 0}%</strong> ROI
            </span>
            <span style={{ fontFamily: 'var(--font-mono)', fontSize: '13px', color: 'var(--text-secondary)' }}>
              <strong style={{ color: 'var(--text-primary)', fontWeight: 600 }}>{stats?.record || '0-0'}</strong> Record
            </span>
            <span style={{ fontFamily: 'var(--font-mono)', fontSize: '13px', color: 'var(--text-secondary)' }}>
              <strong style={{ color: 'var(--text-primary)', fontWeight: 600 }}>{stats?.win_rate || 0}%</strong> Win Rate
            </span>
          </div>

          {equityData.length > 1 && (
            <div style={{ position: 'relative' }}>
              <EquityChart data={equityData} />
            </div>
          )}

          <p style={{
            fontSize: '11px', color: 'var(--text-tertiary)', marginTop: '12px',
            lineHeight: '1.5',
          }}>
            All {totalPicks} picks tracked publicly. No deletes. No hindsight editing.
          </p>
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
              ? `Analyzed ${todayData.games_analyzed} games · Market efficient today`
              : todayIsPick
                ? 'Pick published today'
                : 'Waiting for game data'}
          </span>
        </div>

        <SectionLabel>Discipline Metrics</SectionLabel>

        <div style={{
          display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px',
          marginBottom: '12px',
        }}>
          <MetricCard value={`${selectivity}%`} label="Selectivity" />
          <MetricCard value={daysPerBet} label="Days / Bet" />
          <MetricCard value={totalPicks} label="Picks" />
          <MetricCard value={passDays} label="Passes" />
        </div>

        <div style={{
          backgroundColor: 'var(--surface-1)', borderRadius: '16px',
          border: '1px solid var(--stroke-subtle)', padding: '20px',
          marginBottom: '12px',
        }}>
          <SectionLabel>Selectivity Spectrum</SectionLabel>
          <SelectivityBar selectivity={selectivity} />
          <div style={{
            display: 'flex', justifyContent: 'space-between', marginTop: '8px',
          }}>
            <span style={{
              fontSize: '9px', fontWeight: 600, color: 'var(--text-tertiary)',
              textTransform: 'uppercase', letterSpacing: '0.06em',
            }}>Sharp (Selective)</span>
            <span style={{
              fontSize: '9px', fontWeight: 600, color: 'var(--text-tertiary)',
              textTransform: 'uppercase', letterSpacing: '0.06em',
            }}>Square (Volume)</span>
          </div>
          <p style={{
            fontSize: '13px', color: 'var(--text-secondary)', lineHeight: '1.6',
            marginTop: '14px',
          }}>
            The algorithm acts on <span style={{ fontWeight: 700, color: 'var(--text-primary)' }}>{selectivity}%</span> of opportunities. Industry average is 78%.
          </p>
        </div>

        {hasUserBets && (
          <>
            <div style={{
              height: '1px', backgroundColor: 'var(--stroke-subtle)',
              margin: '20px 0',
            }} />

            <SectionLabel>Your Betting Record</SectionLabel>

            <div style={{
              backgroundColor: 'var(--surface-1)', borderRadius: '20px',
              border: '1px solid var(--stroke-subtle)', padding: '24px',
              marginBottom: '16px',
            }}>
              <div style={{
                display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px',
                marginBottom: '16px',
              }}>
                <div>
                  <div style={{
                    fontFamily: 'var(--font-mono)', fontSize: '32px', fontWeight: 800,
                    color: userStats.totalProfit >= 0 ? 'var(--green-profit)' : 'var(--red-loss)',
                    lineHeight: '1',
                  }}>
                    {userStats.totalProfit >= 0 ? '+' : ''}${Math.abs(userStats.totalProfit).toFixed(0)}
                  </div>
                  <div style={{
                    fontSize: '10px', fontWeight: 600, color: 'var(--text-tertiary)',
                    textTransform: 'uppercase', letterSpacing: '0.08em', marginTop: '6px',
                  }}>Your P&L</div>
                </div>
                <div>
                  <div style={{
                    fontFamily: 'var(--font-mono)', fontSize: '32px', fontWeight: 800,
                    color: 'var(--text-primary)', lineHeight: '1',
                  }}>
                    {userStats.wins}-{userStats.losses}
                  </div>
                  <div style={{
                    fontSize: '10px', fontWeight: 600, color: 'var(--text-tertiary)',
                    textTransform: 'uppercase', letterSpacing: '0.08em', marginTop: '6px',
                  }}>Your Record</div>
                </div>
              </div>

              {userStats.equityCurve && userStats.equityCurve.length > 1 && (
                <UserEquityChart data={userStats.equityCurve} />
              )}

              <button
                onClick={() => onNavigate && onNavigate('profile', 'bets')}
                style={{
                  width: '100%', padding: '12px', marginTop: '16px',
                  backgroundColor: 'transparent',
                  border: '1px solid var(--stroke-muted)', borderRadius: '10px',
                  color: 'var(--text-secondary)', fontSize: '13px',
                  fontWeight: 600, cursor: 'pointer', fontFamily: 'var(--font-sans)',
                }}
              >View Full Bet Log</button>
            </div>
          </>
        )}

        {!hasUserBets && (
          <>
            <div style={{
              height: '1px', backgroundColor: 'var(--stroke-subtle)',
              margin: '20px 0',
            }} />

            <SectionLabel>Your Betting Record</SectionLabel>

            <div style={{
              backgroundColor: 'var(--surface-1)', borderRadius: '20px',
              border: '1px solid var(--stroke-subtle)', padding: '24px',
              marginBottom: '16px', textAlign: 'center',
            }}>
              <div style={{
                width: '56px', height: '56px', borderRadius: '14px',
                backgroundColor: 'var(--surface-2)',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                margin: '0 auto 16px',
              }}>
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="var(--text-tertiary)" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M9 11l3 3L22 4"/>
                  <path d="M21 12v7a2 2 0 01-2 2H5a2 2 0 01-2-2V5a2 2 0 012-2h11"/>
                </svg>
              </div>
              <div style={{
                fontFamily: 'var(--font-serif)', fontSize: '18px', fontWeight: 600,
                color: 'var(--text-primary)', marginBottom: '8px',
              }}>No tracked bets yet</div>
              <p style={{
                fontSize: '13px', color: 'var(--text-secondary)', lineHeight: '1.6',
                marginBottom: '16px',
              }}>
                Track your wagers against the algorithm's picks to build your personal performance record.
              </p>
              <button
                onClick={() => onNavigate && onNavigate('profile', 'bets')}
                style={{
                  padding: '12px 24px',
                  backgroundColor: 'transparent',
                  border: '1px solid var(--stroke-muted)', borderRadius: '10px',
                  color: 'var(--text-secondary)', fontSize: '13px',
                  fontWeight: 600, cursor: 'pointer', fontFamily: 'var(--font-sans)',
                }}
              >Start Tracking</button>
            </div>
          </>
        )}

        <p style={{
          fontSize: '11px', color: 'var(--text-tertiary)', lineHeight: '1.5',
          textAlign: 'center', padding: '8px 20px 16px',
        }}>
          Past performance does not guarantee future results. This analysis reflects probabilities, not certainty.
        </p>
      </div>
    </div>
  );
}

function MetricCard({ value, label }) {
  return (
    <div style={{
      backgroundColor: 'var(--surface-1)', borderRadius: '16px',
      border: '1px solid var(--stroke-subtle)', padding: '20px',
      textAlign: 'center',
    }}>
      <div style={{
        fontFamily: 'var(--font-mono)', fontSize: '28px', fontWeight: 700,
        color: 'var(--text-primary)', marginBottom: '6px',
      }}>{value}</div>
      <div style={{
        fontSize: '10px', fontWeight: 600, color: 'var(--text-tertiary)',
        textTransform: 'uppercase', letterSpacing: '0.08em',
      }}>{label}</div>
    </div>
  );
}

function SelectivityBar({ selectivity }) {
  const industryAvg = 78;
  const userPos = Math.min(Math.max(selectivity, 0), 100);

  return (
    <div style={{ position: 'relative', height: '28px' }}>
      <div style={{
        position: 'absolute', left: '0', right: '0',
        height: '8px', top: '10px',
        backgroundColor: 'var(--surface-2)', borderRadius: '4px',
      }} />
      <div style={{
        position: 'absolute', left: '0', top: '10px',
        width: `${userPos}%`, height: '8px',
        background: 'linear-gradient(90deg, #4A90D9, #2563EB)',
        borderRadius: '4px',
      }} />
      <div style={{
        position: 'absolute', left: `${userPos}%`, top: '4px',
        width: '4px', height: '20px',
        backgroundColor: 'var(--text-primary)', borderRadius: '2px',
        transform: 'translateX(-50%)',
      }} />
      <div style={{
        position: 'absolute', left: `${industryAvg}%`, top: '0',
        transform: 'translateX(-50%)',
        fontSize: '8px', color: 'var(--text-tertiary)',
        whiteSpace: 'nowrap',
      }}>Industry avg ({industryAvg}%)</div>
      <div style={{
        position: 'absolute', left: `${industryAvg}%`, top: '10px',
        width: '1px', height: '8px',
        backgroundColor: 'var(--text-tertiary)',
        opacity: 0.5,
      }} />
    </div>
  );
}

function EquityChart({ data }) {
  const height = 120;
  const width = 300;
  const padT = 5;
  const padB = 24;

  const values = data.map(d => d.value);
  const minVal = Math.min(0, ...values);
  const maxVal = Math.max(0, ...values);
  const range = maxVal - minVal || 1;

  const chartH = height - padT - padB;

  const getX = (i) => (i / (data.length - 1)) * width;
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
          <linearGradient id="algoEquityGrad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={isPositive ? 'var(--green-profit)' : 'var(--red-loss)'} stopOpacity="0.25" />
            <stop offset="100%" stopColor={isPositive ? 'var(--green-profit)' : 'var(--red-loss)'} stopOpacity="0" />
          </linearGradient>
          <filter id="algoGlow">
            <feGaussianBlur stdDeviation="3" result="coloredBlur" />
            <feMerge>
              <feMergeNode in="coloredBlur" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>
        </defs>
        <polygon points={areaPoints} fill="url(#algoEquityGrad)" />
        <polyline points={linePoints} fill="none"
          stroke={isPositive ? 'var(--green-profit)' : 'var(--red-loss)'}
          strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"
          filter="url(#algoGlow)" />
        <circle
          cx={getX(data.length - 1)} cy={getY(lastValue)} r="4"
          fill={isPositive ? 'var(--green-profit)' : 'var(--red-loss)'}
          filter="url(#algoGlow)"
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

function UserEquityChart({ data }) {
  const height = 80;
  const width = 280;
  const padT = 5;
  const padB = 5;

  const values = data.map(d => d.cumProfit || 0);
  const minVal = Math.min(0, ...values);
  const maxVal = Math.max(0, ...values);
  const range = maxVal - minVal || 1;

  const chartH = height - padT - padB;

  const getX = (i) => (i / (data.length - 1)) * width;
  const getY = (v) => padT + chartH - ((v - minVal) / range) * chartH;

  const linePoints = data.map((d, i) => `${getX(i)},${getY(d.cumProfit || 0)}`).join(' ');

  const lastValue = values[values.length - 1];
  const isPositive = lastValue >= 0;

  return (
    <svg viewBox={`0 0 ${width} ${height}`} style={{ width: '100%', display: 'block' }}>
      <polyline points={linePoints} fill="none"
        stroke={isPositive ? 'var(--blue-primary)' : 'var(--red-loss)'}
        strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
      <circle
        cx={getX(data.length - 1)} cy={getY(lastValue)} r="3"
        fill={isPositive ? 'var(--blue-primary)' : 'var(--red-loss)'}
      />
    </svg>
  );
}
