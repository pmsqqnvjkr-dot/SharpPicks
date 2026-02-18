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
  const discipline = dashData?.discipline || {};
  const health = dashData?.model_health || {};
  const clv = dashData?.clv || {};
  const founding = dashData?.founding || {};
  const recentPicks = dashData?.recent_picks || [];
  const equityCurve = perf.equity_curve || [];
  const risk = dashData?.risk || {};

  return (
    <div style={{ padding: '0', paddingBottom: embedded ? '0' : '100px' }}>
      {!embedded && (
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
      )}

      <div style={{ padding: '0 20px' }}>
        {embedded && <ModelHealthBadge health={health} />}

        <PerformanceSnapshot perf={perf} equityCurve={equityCurve} risk={risk} />

        <SelectivityPanel discipline={discipline} perf={perf} />

        <CLVPanel clv={clv} />

        <PickTimingLog picks={recentPicks} />

        <PhilosophyPanel />

        <FoundingPanel founding={founding} />

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


function PerformanceSnapshot({ perf, equityCurve, risk }) {
  const pnl = perf.total_pnl || 0;
  const isPositive = pnl >= 0;
  const unitsWon = pnl / 110;

  return (
    <>
      <SectionLabel>Performance</SectionLabel>
      <div style={{
        backgroundColor: 'var(--surface-1)', borderRadius: '20px',
        border: '1px solid var(--stroke-subtle)', padding: '24px',
        marginBottom: '16px',
      }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
          <div>
            <div style={{
              fontFamily: 'var(--font-mono)', fontSize: '13px', fontWeight: 600,
              color: 'var(--text-secondary)', letterSpacing: '1px',
              textTransform: 'uppercase', marginBottom: '8px',
            }}>Season Record</div>
            <div style={{
              fontFamily: 'var(--font-mono)', fontSize: '36px', fontWeight: 800,
              color: 'var(--text-primary)', lineHeight: '1', marginBottom: '12px',
            }}>{perf.record || '0-0'}</div>
          </div>
          {equityCurve.length > 1 && (
            <div style={{ width: '120px', flexShrink: 0 }}>
              <MiniEquityChart data={equityCurve} />
            </div>
          )}
        </div>

        <div style={{
          display: 'grid', gridTemplateColumns: '1fr 1fr 1fr',
          gap: '12px', marginTop: '8px',
        }}>
          <StatBlock
            label="ROI"
            value={`${perf.roi >= 0 ? '+' : ''}${perf.roi || 0}%`}
            color={perf.roi >= 0 ? 'var(--green-profit)' : 'var(--red-loss)'}
          />
          <StatBlock
            label="Units Won"
            value={`${unitsWon >= 0 ? '+' : ''}${unitsWon.toFixed(1)}u`}
            color={unitsWon >= 0 ? 'var(--green-profit)' : 'var(--red-loss)'}
          />
          <StatBlock
            label="Avg Edge"
            value={`${risk.avg_edge_published || perf.avg_edge || 0}%`}
            color="var(--text-primary)"
          />
        </div>

        <div style={{
          marginTop: '16px', paddingTop: '14px',
          borderTop: '1px solid var(--stroke-subtle)',
          display: 'flex', gap: '6px', flexWrap: 'wrap',
        }}>
          <MetaTag label={`${perf.total_picks || 0} Picks`} />
          <MetaTag label={`${perf.total_passes || 0} Pass Days`} />
        </div>
      </div>
    </>
  );
}


function SelectivityPanel({ discipline, perf }) {
  const pickRate = 100 - (discipline.selectivity_rate || 0);
  const industryPickRate = 100 - (discipline.industry_avg || 78);

  return (
    <>
      <SectionLabel>Selectivity</SectionLabel>
      <div style={{
        backgroundColor: 'var(--surface-1)', borderRadius: '20px',
        border: '1px solid var(--stroke-subtle)', padding: '24px',
        marginBottom: '16px',
      }}>
        <div style={{
          fontFamily: 'var(--font-serif)', fontStyle: 'italic',
          fontSize: '16px', color: 'var(--text-primary)',
          lineHeight: '1.5', marginBottom: '20px',
        }}>
          One sharp pick beats five gut plays.
        </div>

        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
          <div>
            <div style={{
              fontFamily: 'var(--font-mono)', fontSize: '28px', fontWeight: 800,
              color: 'var(--green-profit)', lineHeight: '1',
            }}>{discipline.selectivity_rate || 0}%</div>
            <div style={{
              fontSize: '12px', color: 'var(--text-tertiary)', marginTop: '4px',
            }}>of games passed</div>
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
            }}>{discipline.restraint_grade || '--'}</span>
          </div>
        </div>

        <SelectivityBar selectivity={discipline.selectivity_rate || 0} industryAvg={discipline.industry_avg || 78} />

        <div style={{
          marginTop: '20px', paddingTop: '16px',
          borderTop: '1px solid var(--stroke-subtle)',
        }}>
          <div style={{
            display: 'flex', justifyContent: 'space-between', alignItems: 'center',
            marginBottom: '8px',
          }}>
            <span style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>
              Industry avg plays per slate
            </span>
            <span style={{
              fontFamily: 'var(--font-mono)', fontSize: '14px',
              color: 'var(--text-tertiary)', fontWeight: 600,
            }}>3-5 picks</span>
          </div>
          <div style={{
            display: 'flex', justifyContent: 'space-between', alignItems: 'center',
            marginBottom: '8px',
          }}>
            <span style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>
              SharpPicks per slate
            </span>
            <span style={{
              fontFamily: 'var(--font-mono)', fontSize: '14px',
              color: 'var(--green-profit)', fontWeight: 600,
            }}>0-1 picks</span>
          </div>
          <div style={{
            display: 'flex', justifyContent: 'space-between', alignItems: 'center',
          }}>
            <span style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>
              Capital preserved from passing
            </span>
            <span style={{
              fontFamily: 'var(--font-mono)', fontSize: '14px',
              color: 'var(--green-profit)', fontWeight: 600,
            }}>+${(discipline.capital_preserved || 0).toLocaleString()}</span>
          </div>
        </div>
      </div>
    </>
  );
}


function CLVPanel({ clv }) {
  if (!clv || clv.total_tracked === 0) {
    return (
      <>
        <SectionLabel>Closing Line Value</SectionLabel>
        <div style={{
          backgroundColor: 'var(--surface-1)', borderRadius: '20px',
          border: '1px solid var(--stroke-subtle)', padding: '24px',
          marginBottom: '16px', textAlign: 'center',
        }}>
          <div style={{
            fontSize: '13px', color: 'var(--text-tertiary)',
            fontFamily: 'var(--font-serif)', fontStyle: 'italic',
          }}>CLV tracking begins once closing lines are captured.</div>
        </div>
      </>
    );
  }

  return (
    <>
      <SectionLabel>Closing Line Value</SectionLabel>
      <div style={{
        backgroundColor: 'var(--surface-1)', borderRadius: '20px',
        border: '1px solid var(--stroke-subtle)', padding: '24px',
        marginBottom: '16px',
      }}>
        <div style={{
          fontFamily: 'var(--font-serif)', fontStyle: 'italic',
          fontSize: '13px', color: 'var(--text-tertiary)',
          marginBottom: '16px', lineHeight: '1.5',
        }}>
          Consistently beating the closing line is the strongest indicator of long-term profitability.
        </div>

        <div style={{
          display: 'grid', gridTemplateColumns: '1fr 1fr',
          gap: '12px',
        }}>
          <div style={{
            backgroundColor: 'var(--surface-2)', borderRadius: '14px',
            padding: '16px', textAlign: 'center',
          }}>
            <div style={{
              fontFamily: 'var(--font-mono)', fontSize: '28px', fontWeight: 800,
              color: clv.beat_close_pct >= 50 ? 'var(--green-profit)' : 'var(--text-primary)',
              lineHeight: '1', marginBottom: '6px',
            }}>{clv.beat_close_pct}%</div>
            <div style={{
              fontSize: '11px', color: 'var(--text-tertiary)',
              textTransform: 'uppercase', letterSpacing: '0.5px',
            }}>Beating Close</div>
          </div>
          <div style={{
            backgroundColor: 'var(--surface-2)', borderRadius: '14px',
            padding: '16px', textAlign: 'center',
          }}>
            <div style={{
              fontFamily: 'var(--font-mono)', fontSize: '28px', fontWeight: 800,
              color: clv.avg_clv > 0 ? 'var(--green-profit)' : clv.avg_clv < 0 ? 'var(--red-loss)' : 'var(--text-primary)',
              lineHeight: '1', marginBottom: '6px',
            }}>{clv.avg_clv > 0 ? '+' : ''}{clv.avg_clv}</div>
            <div style={{
              fontSize: '11px', color: 'var(--text-tertiary)',
              textTransform: 'uppercase', letterSpacing: '0.5px',
            }}>Avg CLV / Pick</div>
          </div>
        </div>

        <div style={{
          marginTop: '12px', textAlign: 'center',
        }}>
          <span style={{
            fontFamily: 'var(--font-mono)', fontSize: '10px',
            color: 'var(--text-tertiary)',
          }}>{clv.total_tracked} picks tracked</span>
        </div>
      </div>
    </>
  );
}


function PickTimingLog({ picks }) {
  if (!picks || picks.length === 0) return null;

  const picksWithResults = picks.filter(p => p.result === 'win' || p.result === 'loss' || p.result === 'push' || p.result === 'pending');

  return (
    <>
      <SectionLabel>Pick Log</SectionLabel>
      <div style={{
        backgroundColor: 'var(--surface-1)', borderRadius: '20px',
        border: '1px solid var(--stroke-subtle)',
        marginBottom: '16px', overflow: 'hidden',
      }}>
        {picksWithResults.map((pick, i) => (
          <PickRow key={pick.id} pick={pick} isLast={i === picksWithResults.length - 1} />
        ))}
      </div>
    </>
  );
}

function PickRow({ pick, isLast }) {
  const isWin = pick.result === 'win';
  const isLoss = pick.result === 'loss';
  const isPending = pick.result === 'pending';
  const isRevoked = pick.result === 'revoked';
  const timestamp = formatPickTimestamp(pick.game_date, pick.start_time, pick.published_at);

  return (
    <div style={{
      padding: '16px 20px',
      borderBottom: isLast ? 'none' : '1px solid var(--stroke-subtle)',
      opacity: isRevoked ? 0.6 : 1,
    }}>
      <div style={{
        display: 'flex', justifyContent: 'space-between', alignItems: 'center',
        marginBottom: '4px',
      }}>
        <span style={{
          fontFamily: 'var(--font-sans)', fontSize: '14px',
          color: 'var(--text-primary)', fontWeight: 600,
          textDecoration: isRevoked ? 'line-through' : 'none',
        }}>{pick.side} {pick.line > 0 ? `+${pick.line}` : pick.line}</span>
        <span style={{
          fontFamily: 'var(--font-mono)', fontSize: '12px', fontWeight: 700,
          color: isWin ? 'var(--green-profit)' : isLoss ? 'var(--red-loss)' : isRevoked ? 'var(--text-tertiary)' : 'var(--gold-pro)',
          backgroundColor: isWin ? 'rgba(52,211,153,0.1)' : isLoss ? 'rgba(239,68,68,0.1)' : isRevoked ? 'rgba(128,128,128,0.1)' : 'rgba(245,158,11,0.1)',
          padding: '3px 8px', borderRadius: '4px',
        }}>
          {isWin ? 'WIN' : isLoss ? 'LOSS' : isRevoked ? 'REVOKED' : 'PENDING'}
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
        {pick.line != null && (
          <PickMeta label="Released" value={pick.line > 0 ? `+${pick.line}` : `${pick.line}`} />
        )}
        {pick.closing_spread != null && (
          <PickMeta label="Close" value={pick.closing_spread > 0 ? `+${pick.closing_spread}` : `${pick.closing_spread}`} />
        )}
        {pick.clv != null && (
          <PickMeta label="CLV" value={`${pick.clv > 0 ? '+' : ''}${pick.clv}`}
            color={pick.clv > 0 ? 'var(--green-profit)' : pick.clv < 0 ? 'var(--red-loss)' : undefined} />
        )}
        {pick.profit_units != null && (
          <PickMeta label="P/L" value={`${pick.profit_units >= 0 ? '+' : ''}${pick.profit_units}u`}
            color={pick.profit_units >= 0 ? 'var(--green-profit)' : 'var(--red-loss)'} />
        )}
      </div>
    </div>
  );
}


function PhilosophyPanel() {
  return (
    <>
      <SectionLabel>Framework</SectionLabel>
      <div style={{
        backgroundColor: 'var(--surface-1)', borderRadius: '20px',
        border: '1px solid var(--stroke-subtle)', padding: '24px',
        marginBottom: '16px',
      }}>
        <div style={{
          fontFamily: 'var(--font-serif)', fontSize: '18px',
          color: 'var(--text-primary)', fontWeight: 600,
          marginBottom: '16px', lineHeight: '1.4',
        }}>The SharpPicks Framework</div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
          <FrameworkRule
            icon={
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="var(--green-profit)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/>
                <polyline points="22 4 12 14.01 9 11.01"/>
              </svg>
            }
            text="No edge, no pick. We pass more than we play."
          />
          <FrameworkRule
            icon={
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="var(--green-profit)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/>
                <polyline points="22 4 12 14.01 9 11.01"/>
              </svg>
            }
            text="A statistical edge threshold must be met before any pick is released."
          />
          <FrameworkRule
            icon={
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="var(--green-profit)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/>
                <polyline points="22 4 12 14.01 9 11.01"/>
              </svg>
            }
            text="Every pick is verified against live market odds across multiple books."
          />
          <FrameworkRule
            icon={
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="var(--green-profit)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/>
                <polyline points="22 4 12 14.01 9 11.01"/>
              </svg>
            }
            text="Selective by design. Discipline is the edge most bettors lack."
          />
        </div>
      </div>
    </>
  );
}

function FrameworkRule({ icon, text }) {
  return (
    <div style={{ display: 'flex', gap: '12px', alignItems: 'flex-start' }}>
      <div style={{ flexShrink: 0, marginTop: '1px' }}>{icon}</div>
      <span style={{
        fontSize: '14px', color: 'var(--text-secondary)',
        lineHeight: '1.5',
      }}>{text}</span>
    </div>
  );
}


function FoundingPanel({ founding }) {
  const pct = Math.min(((founding.current_count || 0) / (founding.max_count || 500)) * 100, 100);

  return (
    <>
      <SectionLabel>Founding Access</SectionLabel>
      <div style={{
        backgroundColor: 'var(--surface-1)', borderRadius: '20px',
        border: '1px solid rgba(245,158,11,0.2)', padding: '24px',
        marginBottom: '16px',
        background: 'linear-gradient(135deg, var(--surface-1) 0%, rgba(245,158,11,0.04) 100%)',
      }}>
        <div style={{
          display: 'flex', justifyContent: 'space-between', alignItems: 'baseline',
          marginBottom: '12px',
        }}>
          <div style={{
            fontFamily: 'var(--font-sans)', fontSize: '15px',
            color: 'var(--text-primary)', fontWeight: 600,
          }}>Founding Members</div>
          <div style={{
            fontFamily: 'var(--font-mono)', fontSize: '20px',
            color: 'var(--gold-pro)', fontWeight: 800,
          }}>
            {founding.current_count || 0}
            <span style={{ fontSize: '14px', color: 'var(--text-tertiary)', fontWeight: 400 }}> of {founding.max_count || 500}</span>
          </div>
        </div>

        <div style={{
          height: '6px', borderRadius: '3px',
          backgroundColor: 'var(--surface-2)',
          marginBottom: '12px',
          overflow: 'hidden',
        }}>
          <div style={{
            height: '100%', borderRadius: '3px',
            width: `${pct}%`,
            background: 'linear-gradient(90deg, var(--gold-pro), #f59e0b)',
            transition: 'width 0.5s ease',
          }} />
        </div>

        <div style={{
          fontFamily: 'var(--font-serif)', fontStyle: 'italic',
          fontSize: '13px', color: 'var(--text-secondary)',
          lineHeight: '1.5', textAlign: 'center',
        }}>
          {founding.closed
            ? 'Founding access is closed.'
            : 'Founding access closes at 500 members.'}
        </div>
      </div>
    </>
  );
}


function StatBlock({ label, value, color }) {
  return (
    <div style={{
      backgroundColor: 'var(--surface-2)', borderRadius: '12px',
      padding: '12px', textAlign: 'center',
    }}>
      <div style={{
        fontFamily: 'var(--font-mono)', fontSize: '18px', fontWeight: 700,
        color: color || 'var(--text-primary)', lineHeight: '1',
        marginBottom: '4px',
      }}>{value}</div>
      <div style={{
        fontSize: '10px', color: 'var(--text-tertiary)',
        textTransform: 'uppercase', letterSpacing: '0.5px',
      }}>{label}</div>
    </div>
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
      postedPart = `Released ${hours}:${mins} ${ampm} ET`;
    }
  }
  if (gamePart && postedPart) return `${gamePart} · ${postedPart}`;
  if (gamePart) return gamePart;
  if (postedPart) return postedPart;
  return null;
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
      <div style={{ ...shimmer, height: '200px', marginBottom: '16px', borderRadius: '20px' }} />
      <div style={{ ...shimmer, height: '120px', marginBottom: '16px', borderRadius: '20px' }} />
      <div style={{ ...shimmer, height: '140px', marginBottom: '16px', borderRadius: '20px' }} />
    </div>
  );
}
