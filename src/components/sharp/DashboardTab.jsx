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
  const { data: dashData, loading } = useApi('/public/dashboard-stats');
  const { data: calibrationData } = useApi('/public/calibration');

  const isPro = user && (user.is_premium || user.subscription_status === 'active' || user.subscription_status === 'trial');

  if (loading) {
    return (
      <div style={{ padding: '20px' }}>
        <DashboardSkeleton />
      </div>
    );
  }

  if (!isPro) {
    return <FreeTierDashboard onUpgrade={() => onNavigate && onNavigate('profile', 'upgrade')} />;
  }

  const perf = dashData?.performance || {};
  const risk = dashData?.risk || {};
  const discipline = dashData?.discipline || {};
  const health = dashData?.model_health || {};
  const recentPicks = dashData?.recent_picks || [];
  const equityCurve = perf.equity_curve || [];
  const buckets = calibrationData?.buckets || [];

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
        <ModelHealthBadge health={health} />
      </div>

      <div style={{ padding: '0 20px' }}>

        <PerformanceCore perf={perf} equityCurve={equityCurve} />

        <CalibrationPanel buckets={buckets} health={calibrationData?.health} />

        <RiskProfile risk={risk} />

        <DisciplineScore discipline={discipline} />

        <RecentPickLog picks={recentPicks} />

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


function PerformanceCore({ perf, equityCurve }) {
  const pnl = perf.total_pnl || 0;
  const isPositive = pnl >= 0;

  return (
    <>
      <SectionLabel>Model Performance</SectionLabel>
      <div style={{
        backgroundColor: 'var(--surface-1)', borderRadius: '20px',
        border: '1px solid var(--stroke-subtle)', padding: '24px',
        marginBottom: '16px',
      }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
          <div>
            <div style={{
              fontFamily: 'var(--font-mono)', fontSize: '42px', fontWeight: 800,
              color: isPositive ? 'var(--green-profit)' : 'var(--red-loss)',
              lineHeight: '1', marginBottom: '8px',
            }}>
              {isPositive ? '+' : '-'}${Math.abs(pnl).toLocaleString('en-US', { minimumFractionDigits: 0, maximumFractionDigits: 0 })}
            </div>
            <div style={{
              fontFamily: 'var(--font-mono)', fontSize: '10px',
              color: 'var(--text-tertiary)', letterSpacing: '0.5px',
              marginBottom: '10px',
            }}>
              Model Only · 1u Standardized · -110 Baseline
            </div>
            <div style={{ display: 'flex', gap: '16px', flexWrap: 'wrap' }}>
              <StatChip
                value={`${perf.roi >= 0 ? '+' : ''}${perf.roi || 0}%`}
                label="ROI"
                color={perf.roi >= 0 ? 'var(--green-profit)' : 'var(--red-loss)'}
              />
              <StatChip value={perf.record || '0-0'} label="Record" />
            </div>
          </div>
          {equityCurve.length > 1 && (
            <div style={{ width: '120px', flexShrink: 0 }}>
              <MiniEquityChart data={equityCurve} />
            </div>
          )}
        </div>

        <div style={{
          marginTop: '16px', paddingTop: '14px',
          borderTop: '1px solid var(--stroke-subtle)',
          display: 'flex', gap: '6px', flexWrap: 'wrap',
        }}>
          <MetaTag label="Season" />
          <MetaTag label={`${perf.total_picks || 0} Picks`} />
          <MetaTag label={`${perf.total_passes || 0} Passes`} />
          <MetaTag label={`${perf.selectivity || 0}% Selectivity`} />
        </div>
      </div>
    </>
  );
}


function CalibrationPanel({ buckets, health }) {
  const hasSufficientData = buckets.some(b => b.picks >= 10);

  return (
    <>
      <SectionLabel>Model Integrity</SectionLabel>
      <div style={{
        backgroundColor: 'var(--surface-1)', borderRadius: '20px',
        border: '1px solid var(--stroke-subtle)', padding: '24px',
        marginBottom: '16px',
      }}>
        {buckets.map((bucket, i) => (
          <CalibrationBar key={i} bucket={bucket} />
        ))}

        {!hasSufficientData && (
          <p style={{
            fontSize: '12px', color: 'var(--text-tertiary)',
            lineHeight: '1.5', marginTop: '12px',
          }}>
            Calibration data builds as picks are graded. Minimum 10 picks per bucket for meaningful analysis.
          </p>
        )}
      </div>
    </>
  );
}

function CalibrationBar({ bucket }) {
  const actual = bucket.actual_cover_rate;
  const expected = bucket.expected_midpoint;
  const hasPicks = bucket.picks > 0;
  const maxWidth = 100;
  const expectedWidth = Math.min(expected, maxWidth);
  const actualWidth = actual !== null ? Math.min(actual, maxWidth) : 0;

  const isAligned = bucket.gap !== null && Math.abs(bucket.gap) <= 3;
  const barColor = !hasPicks ? 'var(--text-tertiary)' :
    isAligned ? 'var(--green-profit)' :
    bucket.gap < -3 ? 'var(--red-loss)' : 'var(--gold-pro)';

  return (
    <div style={{ marginBottom: '16px' }}>
      <div style={{
        display: 'flex', justifyContent: 'space-between', alignItems: 'baseline',
        marginBottom: '6px',
      }}>
        <span style={{
          fontFamily: 'var(--font-mono)', fontSize: '12px',
          color: 'var(--text-secondary)', fontWeight: 600,
        }}>{bucket.bucket}</span>
        <div style={{ display: 'flex', gap: '12px' }}>
          {hasPicks && actual !== null && (
            <span style={{
              fontFamily: 'var(--font-mono)', fontSize: '12px',
              color: barColor, fontWeight: 700,
            }}>Actual: {actual}%</span>
          )}
          <span style={{
            fontFamily: 'var(--font-mono)', fontSize: '11px',
            color: 'var(--text-tertiary)',
          }}>Expected: {expected}%</span>
        </div>
      </div>
      <div style={{
        position: 'relative', height: '6px',
        backgroundColor: 'var(--surface-2)', borderRadius: '3px',
        overflow: 'hidden',
      }}>
        <div style={{
          position: 'absolute', left: 0, top: 0, height: '100%',
          width: `${expectedWidth}%`,
          backgroundColor: 'rgba(255,255,255,0.06)',
          borderRadius: '3px',
        }} />
        {hasPicks && (
          <div style={{
            position: 'absolute', left: 0, top: 0, height: '100%',
            width: `${actualWidth}%`,
            backgroundColor: barColor,
            borderRadius: '3px',
            opacity: 0.7,
            transition: 'width 0.6s ease',
          }} />
        )}
      </div>
      {!hasPicks && (
        <span style={{
          fontFamily: 'var(--font-mono)', fontSize: '10px',
          color: 'var(--text-tertiary)', marginTop: '4px', display: 'block',
        }}>Minimum 10 picks per bucket required</span>
      )}
    </div>
  );
}


function RiskProfile({ risk }) {
  return (
    <>
      <SectionLabel>Risk Profile</SectionLabel>
      <div style={{
        backgroundColor: 'var(--surface-1)', borderRadius: '20px',
        border: '1px solid var(--stroke-subtle)', padding: '20px',
        marginBottom: '16px',
      }}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
          <RiskRow label="Max Drawdown" value={`-${risk.max_drawdown_pct || 0}%`} />
          <RiskRow label="Avg Days Between Picks" value={risk.avg_days_between_picks || '—'} />
          <RiskRow label="Avg Line Movement" value={`${risk.avg_line_move_against || 0} pts`} />
          <RiskRow label="Avg Edge Published" value={`${risk.avg_edge_published || 0}%`} />
        </div>
      </div>
    </>
  );
}

function RiskRow({ label, value }) {
  return (
    <div style={{
      display: 'flex', justifyContent: 'space-between', alignItems: 'center',
      paddingBottom: '12px', borderBottom: '1px solid var(--stroke-subtle)',
    }}>
      <span style={{
        fontSize: '13px', color: 'var(--text-secondary)',
      }}>{label}</span>
      <span style={{
        fontFamily: 'var(--font-mono)', fontSize: '14px',
        color: 'var(--text-primary)', fontWeight: 600,
      }}>{value}</span>
    </div>
  );
}


function DisciplineScore({ discipline }) {
  return (
    <>
      <SectionLabel>Discipline Score</SectionLabel>
      <div style={{
        backgroundColor: 'var(--surface-1)', borderRadius: '20px',
        border: '1px solid var(--stroke-subtle)', padding: '24px',
        marginBottom: '16px',
      }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'baseline', gap: '12px', marginBottom: '4px' }}>
              <span style={{
                fontSize: '13px', color: 'var(--text-secondary)',
              }}>Selectivity Rate</span>
              <span style={{
                fontFamily: 'var(--font-mono)', fontSize: '22px',
                color: 'var(--text-primary)', fontWeight: 700,
              }}>{discipline.selectivity_rate || 0}%</span>
            </div>
            <div style={{
              fontSize: '12px', color: 'var(--text-tertiary)',
            }}>Industry Avg: {discipline.industry_avg || 78}%</div>
          </div>
          <div style={{
            width: '56px', height: '56px', borderRadius: '14px',
            background: discipline.restraint_grade?.startsWith('A')
              ? 'linear-gradient(135deg, rgba(52,211,153,0.15), rgba(52,211,153,0.05))'
              : 'linear-gradient(135deg, rgba(255,255,255,0.08), rgba(255,255,255,0.02))',
            border: discipline.restraint_grade?.startsWith('A')
              ? '1px solid rgba(52,211,153,0.3)'
              : '1px solid var(--stroke-subtle)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
          }}>
            <span style={{
              fontFamily: 'var(--font-mono)', fontSize: '20px', fontWeight: 800,
              color: discipline.restraint_grade?.startsWith('A') ? 'var(--green-profit)' : 'var(--text-primary)',
            }}>{discipline.restraint_grade || '—'}</span>
          </div>
        </div>

        <SelectivityBar selectivity={discipline.selectivity_rate || 0} industryAvg={discipline.industry_avg || 78} />

        <div style={{
          marginTop: '16px', paddingTop: '14px',
          borderTop: '1px solid var(--stroke-subtle)',
        }}>
          <p style={{
            fontSize: '13px', color: 'var(--text-secondary)', lineHeight: '1.6',
          }}>
            Capital preserved: <span style={{
              fontFamily: 'var(--font-mono)', fontWeight: 700,
              color: 'var(--green-profit)',
            }}>+${(discipline.capital_preserved || 0).toLocaleString()}</span> from avoided -EV spots
          </p>
        </div>
      </div>
    </>
  );
}


function RecentPickLog({ picks }) {
  if (!picks || picks.length === 0) return null;

  return (
    <>
      <SectionLabel>Recent Picks</SectionLabel>
      <div style={{
        backgroundColor: 'var(--surface-1)', borderRadius: '20px',
        border: '1px solid var(--stroke-subtle)',
        marginBottom: '16px', overflow: 'hidden',
      }}>
        {picks.map((pick, i) => (
          <PickLogRow key={pick.id} pick={pick} isLast={i === picks.length - 1} />
        ))}
      </div>
    </>
  );
}

function toET(isoStr) {
  try {
    const d = new Date(isoStr);
    if (isNaN(d.getTime())) return null;
    return new Date(d.toLocaleString('en-US', { timeZone: 'America/New_York' }));
  } catch { return null; }
}

function formatPickTimestamp(gameDate, startTime, publishedAt) {
  const months = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];

  let gamePart = '';
  if (startTime && startTime.includes('T')) {
    const et = toET(startTime);
    if (et) {
      let hours = et.getHours();
      const mins = et.getMinutes().toString().padStart(2, '0');
      const ampm = hours >= 12 ? 'PM' : 'AM';
      hours = hours % 12 || 12;
      gamePart = `${months[et.getMonth()]} ${et.getDate()} · ${hours}:${mins} ${ampm} ET`;
    }
  }
  if (!gamePart && gameDate && typeof gameDate === 'string' && gameDate.match(/^\d{4}-\d{2}-\d{2}/)) {
    const [y, m, day] = gameDate.split('-');
    gamePart = `${months[parseInt(m)-1]} ${parseInt(day)}`;
  }

  let postedPart = '';
  if (publishedAt) {
    const et = toET(publishedAt);
    if (et) {
      let hours = et.getHours();
      const mins = et.getMinutes().toString().padStart(2, '0');
      const ampm = hours >= 12 ? 'PM' : 'AM';
      hours = hours % 12 || 12;
      postedPart = `Posted ${hours}:${mins} ${ampm} ET`;
    }
  }
  if (gamePart && postedPart) return `${gamePart} · ${postedPart}`;
  if (gamePart) return gamePart;
  if (postedPart) return postedPart;
  return null;
}

function PickLogRow({ pick, isLast }) {
  const isWin = pick.result === 'win';
  const isLoss = pick.result === 'loss';
  const isPending = pick.result === 'pending';
  const timestamp = formatPickTimestamp(pick.game_date, pick.start_time, pick.published_at);

  return (
    <div style={{
      padding: '16px 20px',
      borderBottom: isLast ? 'none' : '1px solid var(--stroke-subtle)',
    }}>
      <div style={{
        display: 'flex', justifyContent: 'space-between', alignItems: 'center',
        marginBottom: '4px',
      }}>
        <span style={{
          fontFamily: 'var(--font-sans)', fontSize: '14px',
          color: 'var(--text-primary)', fontWeight: 600,
        }}>{pick.side}</span>
        <span style={{
          fontFamily: 'var(--font-mono)', fontSize: '12px', fontWeight: 700,
          color: isWin ? 'var(--green-profit)' : isLoss ? 'var(--red-loss)' : 'var(--gold-pro)',
          backgroundColor: isWin ? 'rgba(52,211,153,0.1)' : isLoss ? 'rgba(239,68,68,0.1)' : 'rgba(245,158,11,0.1)',
          padding: '3px 8px', borderRadius: '4px',
        }}>
          {isWin ? 'WIN' : isLoss ? 'LOSS' : 'PENDING'}
        </span>
      </div>
      {(pick.away_team || pick.home_team) && (
        <div style={{
          fontFamily: 'var(--font-mono)', fontSize: '11px',
          color: 'var(--text-secondary)', marginBottom: '4px',
        }}>
          {pick.away_team} @ {pick.home_team}
        </div>
      )}
      {timestamp && (
        <div style={{
          fontFamily: 'var(--font-mono)', fontSize: '10px',
          color: 'var(--text-tertiary)', marginBottom: '8px',
        }}>
          {timestamp}
        </div>
      )}
      <div style={{
        display: 'flex', gap: '10px', flexWrap: 'wrap',
      }}>
        <PickMeta label="Edge" value={`${pick.edge_pct || 0}%`} />
        {pick.predicted_margin !== null && pick.predicted_margin !== undefined && (
          <PickMeta label="Margin" value={`${pick.predicted_margin > 0 ? '+' : ''}${pick.predicted_margin}`} />
        )}
        {pick.cover_prob !== null && pick.cover_prob !== undefined && (
          <PickMeta label="Cover" value={`${(pick.cover_prob * 100).toFixed(0)}%`} />
        )}
        {pick.closing_spread !== null && pick.closing_spread !== undefined && (
          <PickMeta label="Close" value={pick.closing_spread > 0 ? `+${pick.closing_spread}` : pick.closing_spread} />
        )}
        {pick.line_movement !== null && pick.line_movement !== undefined && pick.line_movement !== 0 && (
          <PickMeta label="Move" value={`${pick.line_movement > 0 ? '+' : ''}${pick.line_movement}`}
            color={Math.abs(pick.line_movement) > 1 ? 'var(--gold-pro)' : undefined} />
        )}
      </div>
    </div>
  );
}

function PickMeta({ label, value, color }) {
  return (
    <span style={{
      fontFamily: 'var(--font-mono)', fontSize: '11px',
      color: color || 'var(--text-tertiary)',
    }}>
      <span style={{ opacity: 0.6 }}>{label}</span>{' '}
      <span style={{ color: color || 'var(--text-secondary)', fontWeight: 600 }}>{value}</span>
    </span>
  );
}


function ModelHealthBadge({ health }) {
  const isCalibrated = health.status === 'calibrated';
  const statusText = isCalibrated ? 'Calibrated' : 'Calibrating';
  const dotColor = isCalibrated ? 'var(--green-profit)' : 'var(--gold-pro)';

  return (
    <div style={{
      display: 'flex', alignItems: 'center', gap: '6px',
      padding: '6px 10px', borderRadius: '8px',
      backgroundColor: 'var(--surface-1)',
      border: '1px solid var(--stroke-subtle)',
    }}>
      <div style={{
        width: '6px', height: '6px', borderRadius: '50%',
        backgroundColor: dotColor,
        boxShadow: `0 0 6px ${dotColor}`,
      }} />
      <span style={{
        fontFamily: 'var(--font-mono)', fontSize: '10px',
        color: 'var(--text-secondary)', fontWeight: 600,
        letterSpacing: '0.5px', textTransform: 'uppercase',
      }}>{statusText}</span>
      {health.sigma && (
        <span style={{
          fontFamily: 'var(--font-mono)', fontSize: '10px',
          color: 'var(--text-tertiary)',
        }}>{health.sigma}pt</span>
      )}
    </div>
  );
}


function StatChip({ value, label, color }) {
  return (
    <span style={{ fontFamily: 'var(--font-mono)', fontSize: '14px', color: 'var(--text-secondary)' }}>
      <strong style={{ color: color || 'var(--text-primary)', fontWeight: 700 }}>{value}</strong>{' '}
      <span style={{ fontSize: '12px' }}>{label}</span>
    </span>
  );
}

function MetaTag({ label }) {
  return (
    <span style={{
      fontFamily: 'var(--font-mono)', fontSize: '11px',
      color: 'var(--text-tertiary)',
      padding: '4px 8px', borderRadius: '6px',
      backgroundColor: 'var(--surface-2)',
    }}>{label}</span>
  );
}

function SelectivityBar({ selectivity, industryAvg }) {
  const userPos = Math.min(Math.max(selectivity, 0), 100);

  return (
    <div style={{ position: 'relative', height: '28px' }}>
      <div style={{
        position: 'absolute', left: '0', right: '0',
        height: '6px', top: '11px',
        backgroundColor: 'var(--surface-2)', borderRadius: '3px',
      }} />
      <div style={{
        position: 'absolute', left: '0', top: '11px',
        width: `${userPos}%`, height: '6px',
        background: 'linear-gradient(90deg, #34D399, #2563EB)',
        borderRadius: '3px',
      }} />
      <div style={{
        position: 'absolute', left: `${userPos}%`, top: '5px',
        width: '3px', height: '18px',
        backgroundColor: 'var(--green-profit)', borderRadius: '2px',
        transform: 'translateX(-50%)',
      }} />
      <div style={{
        position: 'absolute', left: `${industryAvg}%`, top: '0',
        transform: 'translateX(-50%)',
        fontSize: '8px', color: 'var(--text-tertiary)',
        whiteSpace: 'nowrap',
      }}>Industry ({industryAvg}%)</div>
      <div style={{
        position: 'absolute', left: `${industryAvg}%`, top: '11px',
        width: '1px', height: '6px',
        backgroundColor: 'var(--text-tertiary)', opacity: 0.5,
      }} />
    </div>
  );
}


function MiniEquityChart({ data }) {
  const height = 50;
  const width = 120;
  const pad = 4;

  const values = data.map(d => d.pnl);
  const minVal = Math.min(0, ...values);
  const maxVal = Math.max(0, ...values);
  const range = maxVal - minVal || 1;

  const chartH = height - pad * 2;

  const getX = (i) => pad + (i / (data.length - 1)) * (width - pad * 2);
  const getY = (v) => pad + chartH - ((v - minVal) / range) * chartH;

  const linePoints = data.map((d, i) => `${getX(i)},${getY(d.pnl)}`).join(' ');

  const lastValue = data[data.length - 1].pnl;
  const isPositive = lastValue >= 0;
  const strokeColor = isPositive ? 'var(--green-profit)' : 'var(--red-loss)';

  return (
    <svg viewBox={`0 0 ${width} ${height}`} style={{ width: '100%', display: 'block' }}>
      <polyline points={linePoints} fill="none"
        stroke={strokeColor} strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
      <circle cx={getX(data.length - 1)} cy={getY(lastValue)} r="3" fill={strokeColor} />
    </svg>
  );
}


function DashboardSkeleton() {
  const shimmer = {
    background: 'linear-gradient(90deg, var(--surface-1) 25%, var(--surface-2) 50%, var(--surface-1) 75%)',
    backgroundSize: '200% 100%',
    animation: 'shimmer 1.5s infinite',
    borderRadius: '8px',
  };

  return (
    <div style={{ padding: '0 20px' }}>
      <style>{`@keyframes shimmer { 0% { background-position: 200% 0; } 100% { background-position: -200% 0; } }`}</style>
      <div style={{ ...shimmer, height: '180px', marginBottom: '16px', borderRadius: '20px' }} />
      <div style={{ ...shimmer, height: '120px', marginBottom: '16px', borderRadius: '20px' }} />
      <div style={{ ...shimmer, height: '100px', marginBottom: '16px', borderRadius: '20px' }} />
      <div style={{ ...shimmer, height: '140px', marginBottom: '16px', borderRadius: '20px' }} />
    </div>
  );
}
