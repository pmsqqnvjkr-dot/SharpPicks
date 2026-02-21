import { useState, useEffect } from 'react';
import { useAuth } from '../../hooks/useAuth';
import { useApi, apiGet } from '../../hooks/useApi';
import { useSport, sportQuery } from '../../hooks/useSport';
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

export default function DashboardTab({ onNavigate, embedded = false }) {
  const { user } = useAuth();
  const { sport } = useSport();
  const { data: dashData, loading } = useApi(sportQuery('/public/dashboard-stats', sport), { pollInterval: 60000 });

  if (loading) {
    return (
      <div style={{ padding: '20px' }}>
        <DashboardSkeleton />
      </div>
    );
  }

  const perf = dashData?.performance || {};
  const risk = dashData?.risk || {};
  const discipline = dashData?.discipline || {};
  const health = dashData?.model_health || {};
  const recentPicks = dashData?.recent_picks || [];
  const equityCurve = perf.equity_curve || [];
  return (
    <div style={{ padding: '0', paddingBottom: embedded ? '0' : '100px' }}>
      {!embedded && (
        <div style={{
          padding: '16px 20px',
          display: 'flex', justifyContent: 'space-between', alignItems: 'center',
        }}>
          <div style={{ display: 'flex', alignItems: 'center' }}>
            <img src="/images/crest.png" alt="" width="26" height="26" style={{ display: 'block', marginRight: '16px', flexShrink: 0, objectFit: 'contain' }} />
            <span style={{
              fontFamily: 'var(--font-sans)', fontSize: '13px', fontWeight: 600,
              color: '#F2F4F8', letterSpacing: '3.9px', textTransform: 'uppercase',
              lineHeight: 1,
            }}>SHARP<span style={{ opacity: 0.65, margin: '0 0.45em', fontWeight: 500, letterSpacing: '0.18em' }}>||</span>PICKS</span>
          </div>
          <ModelHealthBadge health={health} />
        </div>
      )}

      <div style={{ padding: '0 20px' }}>
        {embedded && <ModelHealthBadge health={health} />}

        <PerformanceCore perf={perf} equityCurve={equityCurve} />

        <LatestResultCard picks={recentPicks} />

        <RecentPickLog picks={recentPicks} />

        <DisciplineScore discipline={discipline} />

        <div style={{
          textAlign: 'center', padding: '16px 20px 8px',
        }}>
          <p style={{
            fontFamily: 'var(--font-serif)', fontStyle: 'italic',
            fontSize: '15px', color: 'var(--text-primary)',
            letterSpacing: '0.3px', lineHeight: '1.5',
            opacity: 0.85,
          }}>
            This dashboard measures discipline, not excitement.
          </p>
        </div>
        <p style={{
          fontSize: '11px', color: 'var(--text-tertiary)', lineHeight: '1.5',
          textAlign: 'center', padding: '0 20px 16px',
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
              <InfoTooltip text="ROI measures efficiency, not streaks. Short samples swing. Long samples tell the truth." />
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




function DisciplineScore({ discipline }) {
  return (
    <>
      <SectionLabel>Discipline Score</SectionLabel>
      <InfoCallout
        header="Passing Is a Position"
        text="Volume increases variance. Filtration preserves capital. Edge only matters when it exceeds risk."
      />
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


function LatestResultCard({ picks }) {
  if (!picks || picks.length === 0) return null;
  const latest = picks[0];
  if (!latest || (latest.result !== 'win' && latest.result !== 'loss' && latest.result !== 'push')) return null;

  const isWin = latest.result === 'win';
  const isPush = latest.result === 'push';

  const sideDisplay = latest.side && latest.line != null && latest.side.includes(String(Math.abs(latest.line)))
    ? latest.side
    : `${latest.side} ${latest.line > 0 ? '+' : ''}${latest.line}`;

  return (
    <>
      <SectionLabel>Latest Result</SectionLabel>
      <div style={{
        backgroundColor: 'var(--surface-1)',
        borderRadius: '20px',
        border: '1px solid var(--stroke-subtle)',
        padding: '20px 24px',
        marginBottom: '16px',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <div style={{ flex: 1 }}>
            <div style={{
              fontFamily: 'var(--font-mono)', fontSize: '10px', fontWeight: 600,
              letterSpacing: '1.5px', textTransform: 'uppercase',
              color: 'var(--text-tertiary)', marginBottom: '3px',
            }}>Outcome Resolved</div>
            <div style={{
              fontFamily: 'var(--font-sans)', fontSize: '15px', fontWeight: 600,
              color: 'var(--text-primary)',
            }}>
              {sideDisplay}
            </div>
            {(latest.away_team || latest.home_team) && (
              <div style={{
                fontFamily: 'var(--font-mono)', fontSize: '11px',
                color: 'var(--text-secondary)', marginTop: '2px',
              }}>
                {latest.away_team} @ {latest.home_team}
              </div>
            )}
          </div>
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
  const isRevoked = pick.result === 'revoked';
  const timestamp = formatPickTimestamp(pick.game_date, pick.start_time, pick.published_at);

  return (
    <div style={{
      padding: '16px 20px',
      borderBottom: isLast ? 'none' : '1px solid var(--stroke-subtle)',
      opacity: isRevoked ? 0.7 : 1,
    }}>
      <div style={{
        display: 'flex', justifyContent: 'space-between', alignItems: 'center',
        marginBottom: '4px',
      }}>
        <span style={{
          fontFamily: 'var(--font-sans)', fontSize: '14px',
          color: isRevoked ? 'var(--text-secondary)' : 'var(--text-primary)', fontWeight: 600,
        }}>{pick.side}</span>
        <span style={{
          fontFamily: 'var(--font-mono)', fontSize: '11px', fontWeight: 600,
          color: isWin ? 'var(--green-profit)' : isLoss ? 'var(--text-tertiary)' : isRevoked ? 'rgba(99,102,241,0.7)' : 'var(--text-tertiary)',
          opacity: isLoss ? 0.8 : 1,
        }}>
          {isWin ? 'W' : isLoss ? 'L' : isRevoked ? 'WD' : '...'}
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

function InfoTooltip({ text }) {
  const [open, setOpen] = useState(false);
  return (
    <span style={{ position: 'relative', display: 'inline-flex', alignItems: 'center', marginLeft: '6px', verticalAlign: 'middle' }}>
      <button
        onClick={() => setOpen(!open)}
        style={{
          width: '18px', height: '18px', borderRadius: '50%',
          backgroundColor: open ? 'rgba(255,255,255,0.12)' : 'rgba(255,255,255,0.06)',
          border: '1px solid var(--stroke-subtle)',
          color: 'var(--text-tertiary)', cursor: 'pointer',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          padding: 0, fontSize: '11px', fontFamily: 'var(--font-sans)', fontWeight: 600,
          lineHeight: 1, transition: 'background-color 0.15s ease',
        }}
        aria-label="More info"
      >i</button>
      {open && (
        <div style={{
          position: 'absolute', top: '24px', left: '50%', transform: 'translateX(-50%)',
          backgroundColor: 'var(--surface-1)', border: '1px solid var(--stroke-subtle)',
          borderRadius: '10px', padding: '10px 12px',
          width: '220px', zIndex: 10,
          boxShadow: '0 4px 12px rgba(0,0,0,0.3)',
        }}>
          <p style={{
            fontFamily: 'var(--font-serif)', fontStyle: 'italic',
            fontSize: '12px', color: 'var(--text-secondary)',
            lineHeight: '1.5', margin: 0,
          }}>{text}</p>
        </div>
      )}
    </span>
  );
}

function InfoCallout({ header, text }) {
  const [open, setOpen] = useState(false);
  return (
    <div style={{ marginBottom: '12px' }}>
      <button
        onClick={() => setOpen(!open)}
        style={{
          display: 'flex', alignItems: 'center', gap: '6px',
          background: 'none', border: 'none', cursor: 'pointer', padding: '4px 0',
          color: 'var(--text-tertiary)', fontFamily: 'var(--font-sans)', fontSize: '12px',
          fontWeight: 500, transition: 'color 0.15s ease',
        }}
      >
        <span style={{
          width: '16px', height: '16px', borderRadius: '50%',
          backgroundColor: 'rgba(255,255,255,0.06)',
          border: '1px solid var(--stroke-subtle)',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          fontSize: '10px', fontWeight: 600, lineHeight: 1, flexShrink: 0,
        }}>?</span>
        <span>{header}</span>
        <span style={{
          fontSize: '10px', transition: 'transform 0.2s ease',
          transform: open ? 'rotate(180deg)' : 'rotate(0deg)',
        }}>▾</span>
      </button>
      <div style={{
        maxHeight: open ? '200px' : '0px',
        overflow: 'hidden',
        transition: 'max-height 0.25s ease',
      }}>
        <div style={{
          backgroundColor: 'var(--surface-1)', border: '1px solid var(--stroke-subtle)',
          borderRadius: '10px', padding: '12px 14px', marginTop: '6px',
        }}>
          <p style={{
            fontFamily: 'var(--font-serif)', fontStyle: 'italic',
            fontSize: '12px', color: 'var(--text-secondary)',
            lineHeight: '1.6', margin: 0,
          }}>{text}</p>
        </div>
      </div>
    </div>
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
