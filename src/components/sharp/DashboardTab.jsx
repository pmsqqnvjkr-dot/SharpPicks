import { useAuth } from '../../hooks/useAuth';
import { useApi } from '../../hooks/useApi';

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

  const totalPicks = stats?.total_picks || 0;
  const passDays = stats?.capital_preserved_days || 0;
  const totalDays = totalPicks + passDays || 1;
  const selectivity = stats?.selectivity || Math.round((totalPicks / totalDays) * 100);
  const daysPerBet = totalPicks > 0 ? (totalDays / totalPicks).toFixed(1) : '—';
  const capitalPreserved = passDays * 100;

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
        <SectionLabel>Performance</SectionLabel>

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
            {stats?.pnl >= 0 ? '+' : ''}${Math.abs(stats?.pnl || 0)}
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
            <div style={{ marginTop: '8px' }}><SectionLabel>Expected Edge</SectionLabel></div>

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
          display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px',
          marginBottom: '12px',
        }}>
          <div style={{
            backgroundColor: 'var(--surface-1)', borderRadius: '16px',
            border: '1px solid var(--stroke-subtle)', padding: '20px',
            textAlign: 'center',
          }}>
            <div style={{
              fontFamily: 'var(--font-mono)', fontSize: '28px', fontWeight: 700,
              color: 'var(--text-primary)', marginBottom: '6px',
            }}>{selectivity}%</div>
            <div style={{
              fontSize: '10px', fontWeight: 600, color: 'var(--text-tertiary)',
              textTransform: 'uppercase', letterSpacing: '0.08em',
            }}>Selectivity</div>
          </div>
          <div style={{
            backgroundColor: 'var(--surface-1)', borderRadius: '16px',
            border: '1px solid var(--stroke-subtle)', padding: '20px',
            textAlign: 'center',
          }}>
            <div style={{
              fontFamily: 'var(--font-mono)', fontSize: '28px', fontWeight: 700,
              color: 'var(--text-primary)', marginBottom: '6px',
            }}>{daysPerBet}</div>
            <div style={{
              fontSize: '10px', fontWeight: 600, color: 'var(--text-tertiary)',
              textTransform: 'uppercase', letterSpacing: '0.08em',
            }}>Days / Bet</div>
          </div>
        </div>

        <div style={{
          backgroundColor: 'var(--surface-1)', borderRadius: '16px',
          border: '1px solid var(--stroke-subtle)', padding: '20px',
          marginBottom: '12px',
        }}>
          <SectionLabel>Capital Preserved</SectionLabel>
          <div style={{
            fontFamily: 'var(--font-mono)', fontSize: '32px', fontWeight: 700,
            color: 'var(--green-profit)', marginBottom: '10px',
          }}>+${capitalPreserved.toLocaleString()}</div>
          <p style={{ fontSize: '13px', color: 'var(--text-secondary)', lineHeight: '1.6' }}>
            Estimated bankroll saved by passing on {passDays} low-edge opportunities this season.
          </p>
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
            You bet on <span style={{ fontWeight: 700, color: 'var(--text-primary)' }}>{selectivity}%</span> of opportunities. The industry average is 78%. Fewer decisions, better decisions.
          </p>
        </div>

        <div style={{
          backgroundColor: 'var(--surface-1)', borderRadius: '16px',
          border: '1px solid var(--stroke-subtle)', padding: '20px',
          marginBottom: '12px',
        }}>
          <div style={{
            fontFamily: 'var(--font-mono)',
            fontSize: '10px', fontWeight: 600, color: 'var(--green-profit)',
            letterSpacing: '2px', textTransform: 'uppercase',
            marginBottom: '10px',
          }}>Behavioral Edge</div>
          <p style={{ fontSize: '13px', color: 'var(--text-secondary)', lineHeight: '1.6' }}>
            Your selectivity rate is <span style={{ fontWeight: 700, color: 'var(--text-primary)' }}>{selectivity}%</span> — industry average is 78%. This restraint compounds over time.
          </p>
        </div>

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
            <stop offset="0%" stopColor={isPositive ? 'var(--green-profit)' : 'var(--red-loss)'} stopOpacity="0.25" />
            <stop offset="100%" stopColor={isPositive ? 'var(--green-profit)' : 'var(--red-loss)'} stopOpacity="0" />
          </linearGradient>
          <filter id="glow">
            <feGaussianBlur stdDeviation="3" result="coloredBlur" />
            <feMerge>
              <feMergeNode in="coloredBlur" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>
        </defs>

        <polygon points={areaPoints} fill="url(#dashEquityGrad)" />

        <polyline points={linePoints} fill="none"
          stroke={isPositive ? 'var(--green-profit)' : 'var(--red-loss)'}
          strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"
          filter="url(#glow)" />

        <circle
          cx={getX(data.length - 1)} cy={getY(lastValue)} r="4"
          fill={isPositive ? 'var(--green-profit)' : 'var(--red-loss)'}
          filter="url(#glow)"
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
