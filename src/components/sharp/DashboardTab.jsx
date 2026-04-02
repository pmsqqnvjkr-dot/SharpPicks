import { useState, useEffect, useRef, useCallback } from 'react';
import { Capacitor } from '@capacitor/core';
import { useAuth } from '../../hooks/useAuth';
import { useApi, apiGet } from '../../hooks/useApi';
import { useSport, sportQuery } from '../../hooks/useSport';
import Wordmark from './Wordmark';
import ResolutionScreen from './ResolutionScreen';

const API_ROOT = Capacitor.isNativePlatform() ? 'https://app.sharppicks.ai' : '';
const HISTORY_DEFAULT_LIMIT = 10;
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
  const isPro = user && (user.is_premium || user.subscription_status === 'active' || user.subscription_status === 'trial' || user.founding_member);
  const { data: dashData, loading } = useApi(sportQuery('/public/dashboard-stats', sport), { pollInterval: 60000 });
  const { data: historyData, loading: historyLoading } = useApi(sportQuery('/public/record', sport));
  const { data: statsData } = useApi(sportQuery('/public/stats', sport));
  const [histFilter, setHistFilter] = useState('all');
  const [showAllPicks, setShowAllPicks] = useState(false);
  const initialFilterSet = useRef(false);
  const [showResolution, setShowResolution] = useState(false);
  const [resolutionPick, setResolutionPick] = useState(null);
  const [allLiveScores, setAllLiveScores] = useState([]);

  const fetchLiveScores = useCallback(async () => {
    try {
      const resp = await fetch(`${API_ROOT}/api/picks/live-scores?sport=${sport}`);
      const json = await resp.json();
      if (json.scores) setAllLiveScores(json.scores);
    } catch {}
  }, [sport]);

  useEffect(() => {
    fetchLiveScores();
    const interval = setInterval(fetchLiveScores, 60000);
    return () => clearInterval(interval);
  }, [fetchLiveScores]);

  useEffect(() => {
    if (initialFilterSet.current || !historyData?.picks?.length) return;
    initialFilterSet.current = true;
    const hasWins = historyData.picks.some(p => p.result === 'win');
    const hasPending = historyData.picks.some(p => p.result === 'pending');
    setHistFilter(hasWins ? 'wins' : hasPending ? 'active' : 'all');
  }, [historyData]);

  const picks = historyData?.picks || [];
  const filteredHist = histFilter === 'all' ? picks
    : histFilter === 'wins' ? picks.filter(p => p.result === 'win')
    : histFilter === 'losses' ? picks.filter(p => p.result === 'loss')
    : histFilter === 'active' ? picks.filter(p => p.result === 'pending')
    : picks.filter(p => p.result === 'revoked' || p.result === 'push');

  if (showResolution && resolutionPick) {
    return <ResolutionScreen pick={resolutionPick} onBack={() => { setShowResolution(false); setResolutionPick(null); }} onNavigate={onNavigate} />;
  }

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
  const clvStats = dashData?.clv || {};
  const equityCurve = perf.equity_curve || [];
  return (
    <div style={{ padding: '0', paddingBottom: embedded ? '0' : '100px' }}>
      {!embedded && (
        <div style={{
          padding: '16px 20px',
          display: 'flex', justifyContent: 'space-between', alignItems: 'center',
        }}>
          <div style={{ display: 'flex', alignItems: 'center' }}>
            <Wordmark size={16} />
          </div>
          <ModelHealthBadge health={health} />
        </div>
      )}

      {!embedded && dashData?.model_phase === 'calibration' && (
        <div style={{ padding: '0 20px' }}>
          <PhaseTimeline phase={dashData.model_phase} />
        </div>
      )}

      <div style={{ padding: '0 20px' }}>
        {embedded && <ModelHealthBadge health={health} />}

        {embedded && dashData?.model_phase === 'calibration' && (
          <PhaseTimeline phase={dashData.model_phase} />
        )}

        <PerformanceCore perf={perf} equityCurve={equityCurve} />

        <CLVTracker clv={clvStats} />

        <DisciplineScore discipline={discipline} modelPhase={dashData?.model_phase} />

        <SignalHistory
          picks={picks}
          filteredHist={filteredHist}
          histFilter={histFilter}
          setHistFilter={setHistFilter}
          showAllPicks={showAllPicks}
          setShowAllPicks={setShowAllPicks}
          historyLoading={historyLoading}
          isPro={isPro}
          allLiveScores={allLiveScores}
          stats={statsData}
          sport={sport}
          onViewPick={(pick) => { setResolutionPick(pick); setShowResolution(true); }}
        />

        <ModelTrustStack />

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
  const hasPicks = (perf.total_picks || 0) > 0;

  return (
    <>
      <SectionLabel>Model Performance</SectionLabel>
      <div style={{
        backgroundColor: 'var(--surface-1)', borderRadius: '20px',
        border: '1px solid var(--stroke-subtle)', padding: '24px',
        marginBottom: '16px',
      }}>
        {!hasPicks ? (
          <div style={{ textAlign: 'center', padding: '16px 0' }}>
            <div style={{
              fontFamily: 'var(--font-mono)', fontSize: '11px', fontWeight: 600,
              color: 'var(--text-tertiary)', letterSpacing: '0.5px',
              marginBottom: '6px',
            }}>Calibration in progress</div>
            <div style={{
              fontFamily: 'var(--font-mono)', fontSize: '10px',
              color: 'var(--text-tertiary)',
            }}>Results will appear after the first resolved signal.</div>
          </div>
        ) : (
          <>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
              <div>
                <div style={{
                  fontFamily: 'var(--font-mono)', fontSize: '42px', fontWeight: 600,
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
          </>
        )}
      </div>
    </>
  );
}




function CLVTracker({ clv }) {
  if (!clv || !clv.total_tracked) return null;
  const avgClv = clv.avg_clv;
  const beatRate = clv.beat_rate ?? 0;
  const missedRate = (100 - beatRate);
  const isPositive = avgClv != null && avgClv > 0;
  const clvColor = avgClv == null ? 'var(--text-tertiary)' : isPositive ? 'var(--green-profit)' : 'var(--red-loss)';

  return (
    <>
      <SectionLabel>Closing Line Value</SectionLabel>
      <InfoCallout
        header="The Pro's Metric"
        text="CLV measures whether you bet before the market moved your way. Consistently beating closing lines means the model identifies real edges, regardless of individual outcomes."
      />
      <div style={{
        backgroundColor: 'var(--surface-1)', borderRadius: '20px',
        border: '1px solid var(--stroke-subtle)', padding: '24px',
        marginBottom: '16px',
      }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
          <div>
            <div style={{
              fontFamily: 'var(--font-mono)', fontSize: '9px', fontWeight: 700,
              letterSpacing: '0.1em', textTransform: 'uppercase',
              color: 'var(--text-tertiary)', marginBottom: '6px',
            }}>Average CLV</div>
            <div style={{
              fontFamily: 'var(--font-mono)', fontSize: '36px', fontWeight: 700,
              color: clvColor, lineHeight: 1, marginBottom: '8px',
            }}>
              {avgClv != null ? `${avgClv > 0 ? '+' : ''}${avgClv.toFixed(1)}` : '—'}
            </div>
            <div style={{
              fontFamily: 'var(--font-mono)', fontSize: '10px',
              color: 'var(--text-tertiary)', letterSpacing: '0.5px',
            }}>
              Edge vs closing line · {clv.total_tracked} pick{clv.total_tracked !== 1 ? 's' : ''} tracked
            </div>
            {avgClv != null && (
              <div style={{
                fontFamily: 'var(--font-mono)', fontSize: '10px',
                color: isPositive ? 'var(--green-profit)' : 'var(--text-tertiary)',
                marginTop: '4px', opacity: 0.8,
              }}>
                {avgClv >= 2 ? 'Elite: consistently ahead of the market'
                  : avgClv >= 1 ? 'Strong: model beats the close'
                  : avgClv > 0 ? 'Positive: edge over closing lines'
                  : avgClv === 0 ? 'Neutral: matching the market'
                  : 'Negative: behind closing lines'}
              </div>
            )}
          </div>
          <div style={{ textAlign: 'right' }}>
            <div style={{
              fontFamily: 'var(--font-mono)', fontSize: '9px', fontWeight: 700,
              letterSpacing: '0.1em', textTransform: 'uppercase',
              color: 'var(--text-tertiary)', marginBottom: '6px',
            }}>Beat Rate</div>
            <div style={{
              fontFamily: 'var(--font-mono)', fontSize: '28px', fontWeight: 700,
              color: beatRate >= 50 ? 'var(--green-profit)' : 'var(--text-primary)',
              lineHeight: 1,
            }}>
              {beatRate}%
            </div>
            <div style={{
              fontFamily: 'var(--font-mono)', fontSize: '10px',
              color: 'var(--text-tertiary)', marginTop: '4px',
            }}>
              {clv.positive ?? 0}/{clv.total_tracked} picks
            </div>
          </div>
        </div>

        <div style={{
          marginTop: '16px', paddingTop: '14px',
          borderTop: '1px solid var(--stroke-subtle)',
        }}>
          <div style={{
            fontFamily: 'var(--font-mono)', fontSize: '9px', fontWeight: 700,
            letterSpacing: '0.08em', textTransform: 'uppercase',
            color: 'var(--text-tertiary)', marginBottom: '8px',
          }}>CLV Distribution</div>
          <div style={{ width: '100%', height: 8, borderRadius: 4, background: 'rgba(255,255,255,0.06)', overflow: 'hidden', display: 'flex' }}>
            <div style={{
              width: `${beatRate}%`, height: '100%',
              background: 'var(--green-profit)',
              transition: 'width 0.3s ease',
            }} />
            <div style={{
              width: `${missedRate}%`, height: '100%',
              background: 'var(--red-loss)',
              opacity: 0.5,
            }} />
          </div>
          <div style={{
            display: 'flex', justifyContent: 'space-between', marginTop: '4px',
          }}>
            <span style={{ fontFamily: 'var(--font-mono)', fontSize: '10px', color: 'var(--green-profit)' }}>
              Beat close {beatRate}%
            </span>
            <span style={{ fontFamily: 'var(--font-mono)', fontSize: '10px', color: 'var(--text-tertiary)' }}>
              Missed {missedRate.toFixed(1)}%
            </span>
          </div>
        </div>
      </div>
    </>
  );
}


function DisciplineScore({ discipline, modelPhase }) {
  const isCal = modelPhase === 'calibration';
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
              }}>Model Selectivity</span>
              <span style={{
                fontFamily: 'var(--font-mono)', fontSize: '22px',
                color: 'var(--text-primary)', fontWeight: 700,
              }}>{discipline.selectivity_rate || 0}%</span>
            </div>
            <div style={{
              fontSize: '11px', color: 'var(--text-tertiary)',
            }}>{isCal ? 'Calibration mode. Selectivity filters are widened to build the dataset.' : 'How often the model signals on available games'}</div>
          </div>
          {isCal ? (
            <div style={{
              padding: '6px 12px', borderRadius: '8px',
              background: 'rgba(107,122,141,0.12)',
              border: '1px solid rgba(107,122,141,0.25)',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
            }}>
              <span style={{
                fontFamily: 'var(--font-mono)', fontSize: '11px', fontWeight: 700,
                letterSpacing: '0.08em', color: '#6b7a8d',
              }}>CAL</span>
            </div>
          ) : (
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
                fontFamily: 'var(--font-mono)', fontSize: '20px', fontWeight: 600,
                color: discipline.restraint_grade?.startsWith('A') ? 'var(--green-profit)' : 'var(--text-primary)',
              }}>{discipline.restraint_grade || '—'}</span>
            </div>
          )}
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
              fontFamily: 'var(--font-mono)', fontWeight: 500,
              color: 'var(--green-profit)',
            }}>+${(discipline.capital_preserved || 0).toLocaleString()}</span> from avoided -EV spots
          </p>
        </div>
      </div>
    </>
  );
}


function isTodayGame(gameDate) {
  if (!gameDate) return false;
  const today = new Date().toLocaleDateString('en-CA', { timeZone: 'America/New_York' });
  return gameDate.startsWith(today);
}

function formatDateShort(isoStr) {
  if (!isoStr) return '';
  if (typeof isoStr === 'string' && isoStr.match(/^\d{4}-\d{2}-\d{2}/)) {
    const [, m, day] = isoStr.split('-');
    const months = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
    return `${months[parseInt(m) - 1]} ${parseInt(day)}`;
  }
  return isoStr;
}

function StatusBadge({ result }) {
  const config = {
    win:     { label: 'W',  bg: '#5A9E72', color: '#FFFFFF' },
    loss:    { label: 'L',  bg: '#C4686B', color: '#FFFFFF' },
    pending: { label: 'P',  bg: 'rgba(212,162,78,0.15)', color: '#d4a24e' },
    revoked: { label: 'WD', bg: 'rgba(74,85,104,0.15)',  color: '#6b7a8d' },
    push:    { label: 'PU', bg: 'rgba(74,85,104,0.15)',  color: '#6b7a8d' },
  };
  const c = config[result] || config.pending;
  const isWide = c.label.length > 1;
  return (
    <span style={{ fontFamily: 'var(--font-mono)', fontSize: '11px', fontWeight: 700, width: isWide ? '28px' : '24px', height: '24px', borderRadius: isWide ? '12px' : '50%', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0, backgroundColor: c.bg, color: c.color, letterSpacing: isWide ? '-0.02em' : '0' }}>
      {c.label}
    </span>
  );
}

function CountdownLabel({ startTime }) {
  const [label, setLabel] = useState('');
  useEffect(() => {
    function calc() {
      if (!startTime || !startTime.includes('T')) { setLabel('Pending'); return; }
      const tip = new Date(startTime);
      if (isNaN(tip.getTime())) { setLabel('Pending'); return; }
      const diff = tip - Date.now();
      if (diff <= 0) { setLabel('Pending'); return; }
      const mins = Math.floor(diff / 60000);
      const hrs = Math.floor(mins / 60);
      const remMins = mins % 60;
      if (mins < 5) setLabel('Starting soon');
      else if (hrs < 1) setLabel(`Starts in ${mins}m`);
      else if (hrs < 24) setLabel(`Starts in ${hrs}h ${remMins}m`);
      else setLabel('Starts tomorrow');
    }
    calc();
    const id = setInterval(calc, 60000);
    return () => clearInterval(id);
  }, [startTime]);
  return <div style={{ fontFamily: 'var(--font-mono)', fontSize: '12px', fontWeight: 500, fontVariantNumeric: 'tabular-nums', color: '#d4a24e' }}>{label}</div>;
}

function StreakDots({ picks }) {
  const last7 = picks.slice(0, 7);
  const dotConfig = {
    win:     { label: 'W',  bg: 'rgba(90,158,114,0.15)', color: '#5A9E72' },
    loss:    { label: 'L',  bg: 'rgba(196,104,107,0.15)', color: '#C4686B' },
    revoked: { label: 'WD', bg: 'rgba(74,85,104,0.15)',  color: '#6b7a8d' },
    pending: { label: 'P',  bg: 'rgba(212,162,78,0.15)',  color: '#d4a24e' },
    push:    { label: 'PU', bg: 'rgba(74,85,104,0.15)',  color: '#6b7a8d' },
  };
  let streakCount = 0, streakType = null;
  for (const p of picks) {
    if (p.result === 'win' || p.result === 'loss') {
      if (!streakType) { streakType = p.result; streakCount = 1; }
      else if (p.result === streakType) streakCount++;
      else break;
    } else { if (streakType) break; }
  }
  const streakLabel = streakType === 'win' ? `W${streakCount} streak` : streakType === 'loss' ? `L${streakCount} streak` : '';
  const streakColor = streakType === 'win' ? '#5A9E72' : streakType === 'loss' ? '#C4686B' : '#6b7a8d';
  return (
    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 10 }}>
      <div style={{ display: 'flex', gap: 4 }}>
        {[...last7].reverse().map((p, i) => {
          const cfg = dotConfig[p.result] || dotConfig.pending;
          const isWide = cfg.label.length > 1;
          return (
            <div key={i} style={{ minWidth: isWide ? 26 : 22, height: 22, borderRadius: isWide ? 11 : '50%', background: cfg.bg, display: 'flex', alignItems: 'center', justifyContent: 'center', ...(isWide ? { padding: '0 2px' } : {}) }}>
              <span style={{ fontFamily: 'var(--font-mono)', fontSize: '9px', fontWeight: 500, color: cfg.color }}>{cfg.label}</span>
            </div>
          );
        })}
      </div>
      {streakLabel && <span style={{ fontFamily: 'var(--font-mono)', fontSize: '11px', fontWeight: 500, color: streakColor }}>{streakLabel}</span>}
    </div>
  );
}

function SignalHistoryRow({ pick, isPro, isLast, allLiveScores, onView }) {
  const isSettled = pick.result === 'win' || pick.result === 'loss' || pick.result === 'push';
  const isPending = pick.result === 'pending';
  const isRevoked = pick.result === 'revoked';
  const hideLine = !isPro && isPending;
  const canView = isPro && (isSettled || isRevoked);
  const liveMatch = (() => {
    if (!isPending || !allLiveScores?.length || !pick.home_team) return null;
    const normalize = s => s.toLowerCase().replace(/[^a-z]/g, '');
    const homeKey = normalize(pick.home_team);
    const found = allLiveScores.find(s => normalize(s.home) === homeKey);
    if (found && (found.state === 'STATUS_IN_PROGRESS' || found.state === 'STATUS_HALFTIME')) return found;
    return null;
  })();
  const liveLabel = liveMatch ? `Live${liveMatch.period ? ` Q${liveMatch.period}` : ''}` : null;
  const units = pick.profit_units != null ? pick.profit_units : (pick.pnl != null ? pick.pnl / 100 : null);
  const unitsStr = pick.result === 'push' ? '0.0u' : pick.result === 'win' ? `+${units != null ? Math.abs(units).toFixed(1) : '0.9'}u` : pick.result === 'loss' ? `-${units != null ? Math.abs(units).toFixed(1) : '1.0'}u` : null;
  const unitsColor = pick.result === 'win' ? 'var(--color-signal)' : pick.result === 'loss' ? 'var(--color-loss)' : 'var(--text-tertiary)';
  const rightLine1 = isSettled ? unitsStr : (isPending ? 'Pending' : isRevoked ? 'Withdrawn' : null);
  const rightLine1Color = isSettled ? unitsColor : 'var(--text-tertiary)';
  const showCountdown = isPending && pick.start_time && pick.start_time.includes('T') && isTodayGame(pick.game_date);
  const clvVal = pick.clv != null ? parseFloat(pick.clv) : null;
  const hasCLV = isSettled && clvVal != null;
  const rightLine2 = hasCLV ? `CLV ${clvVal >= 0 ? '+' : ''}${clvVal.toFixed(1)}` : (pick.edge_pct && !hideLine) ? `+${pick.edge_pct}% edge` : null;
  const rightLine2Color = hasCLV ? (clvVal > 0 ? 'var(--color-signal)' : clvVal < 0 ? 'var(--color-loss)' : 'var(--text-tertiary)') : 'var(--text-tertiary)';
  const sideDisplay = hideLine ? `${pick.away_team} @ ${pick.home_team}` : (pick.side || `${pick.away_team} @ ${pick.home_team}`);

  return (
    <div onClick={() => canView && onView()} style={{ padding: '14px 16px', borderBottom: isLast ? 'none' : '1px solid var(--stroke-subtle)', display: 'flex', alignItems: 'center', gap: '8px', cursor: canView ? 'pointer' : 'default', minHeight: '60px' }}>
      <StatusBadge result={pick.result} />
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ fontSize: '14px', fontWeight: 600, color: 'var(--text-primary)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{sideDisplay}</div>
        <div style={{ fontSize: '13px', color: 'var(--text-secondary)', marginTop: '2px', fontFamily: 'var(--font-mono)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
          {pick.away_team} @ {pick.home_team} &middot; {formatDateShort(pick.game_date)}
          {liveLabel && <span style={{ color: '#5A9E72' }}> &middot; {liveLabel}</span>}
        </div>
      </div>
      <div style={{ display: 'flex', alignItems: 'center', gap: '6px', flexShrink: 0 }}>
        <div style={{ textAlign: 'right' }}>
          {showCountdown ? <CountdownLabel startTime={pick.start_time} /> : rightLine1 ? <div style={{ fontFamily: 'var(--font-mono)', fontSize: isSettled ? '14px' : '12px', fontWeight: isSettled ? 600 : 500, fontVariantNumeric: 'tabular-nums', color: rightLine1Color }}>{rightLine1}</div> : null}
          {isPro && rightLine2 && <div style={{ fontFamily: 'var(--font-mono)', fontSize: hasCLV ? '12px' : '11px', fontWeight: hasCLV ? 600 : 400, fontVariantNumeric: 'tabular-nums', color: rightLine2Color, marginTop: '2px', ...(hasCLV ? { padding: '1px 5px', borderRadius: 3, background: clvVal > 0 ? 'rgba(52,211,153,0.08)' : clvVal < 0 ? 'rgba(158,122,124,0.08)' : 'transparent' } : {}) }}>{rightLine2}</div>}
        </div>
        {canView && <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="var(--text-tertiary)" strokeWidth="2" style={{ flexShrink: 0 }}><polyline points="9 18 15 12 9 6"/></svg>}
      </div>
    </div>
  );
}

function SignalHistoryEmpty({ filter, totalCount }) {
  if (totalCount === 0) {
    return (
      <div style={{ textAlign: 'center', padding: '48px 24px', color: 'var(--text-tertiary)', fontSize: '14px', lineHeight: '1.7' }}>
        <div style={{ fontFamily: 'var(--font-mono)', fontSize: 'var(--text-label-size)', fontWeight: 700, letterSpacing: '0.08em', textTransform: 'uppercase', color: 'var(--text-secondary)', marginBottom: '12px' }}>No signals generated yet.</div>
        <p style={{ maxWidth: '300px', margin: '0 auto 12px' }}>The model evaluates the full daily slate and generates signals only when a statistically significant edge is detected.</p>
      </div>
    );
  }
  const msgs = { wins: { title: 'No wins recorded.', detail: `0 of ${totalCount} signals resulted in a win.` }, losses: { title: 'No losses recorded.', detail: `0 of ${totalCount} signals resulted in a loss.` }, active: { title: 'No active signals.', detail: 'All signals have been resolved.' }, other: { title: 'No withdrawn or push signals.', detail: '' } };
  const m = msgs[filter] || { title: 'No signals found.', detail: '' };
  return (
    <div style={{ textAlign: 'center', padding: '40px 24px', color: 'var(--text-tertiary)', fontSize: '14px' }}>
      <div style={{ color: 'var(--text-secondary)', marginBottom: '6px' }}>{m.title}</div>
      {m.detail && <div style={{ fontSize: '13px' }}>{m.detail}</div>}
    </div>
  );
}

function SignalHistory({ picks, filteredHist, histFilter, setHistFilter, showAllPicks, setShowAllPicks, historyLoading, isPro, allLiveScores, stats, sport, onViewPick }) {
  return (
    <>
      <div style={{ marginBottom: '14px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline' }}>
          <SectionLabel>Signal History</SectionLabel>
          <div style={{ fontFamily: 'var(--font-mono)', fontSize: '11px', color: 'var(--text-tertiary)', fontVariantNumeric: 'tabular-nums' }}>{picks.length} signals</div>
        </div>
        {stats && (
          <div style={{ fontFamily: 'var(--font-mono)', fontSize: '12px', color: 'var(--text-tertiary)', marginTop: '4px', fontVariantNumeric: 'tabular-nums' }}>
            {sport === 'mlb' ? '2026 Season' : 'Season 2025-26'} &middot; {stats.record || `${stats.wins || 0}-${stats.losses || 0}`} &middot; {stats.pnl >= 0 ? '+' : ''}{Number(stats.pnl || 0).toFixed(1)}u
          </div>
        )}
      </div>

      {picks.length > 0 && <StreakDots picks={picks} />}

      <div style={{ display: 'flex', gap: '8px', marginBottom: '12px', flexWrap: 'wrap' }}>
        {[{ key: 'all', label: 'All' }, { key: 'wins', label: 'Wins' }, { key: 'losses', label: 'Losses' }, { key: 'active', label: 'Active' }, { key: 'other', label: 'Other' }].map(f => (
          <button key={f.key} onClick={() => { setHistFilter(f.key); setShowAllPicks(false); }} style={{
            padding: '10px 16px', minHeight: '40px', borderRadius: '6px', fontSize: '13px',
            fontWeight: histFilter === f.key ? 600 : 400, cursor: 'pointer', fontFamily: 'var(--font-sans)',
            backgroundColor: histFilter === f.key ? 'var(--color-signal)' : 'transparent',
            color: histFilter === f.key ? '#FFFFFF' : 'var(--text-tertiary)',
            border: histFilter === f.key ? 'none' : '1px solid var(--color-border)',
          }}>{f.label}</button>
        ))}
      </div>

      {historyLoading ? (
        <p style={{ color: 'var(--text-secondary)', fontSize: '14px', textAlign: 'center', padding: '40px 0' }}>Loading...</p>
      ) : filteredHist.length === 0 ? (
        <SignalHistoryEmpty filter={histFilter} totalCount={picks.length} />
      ) : (() => {
        const isTruncated = !showAllPicks && filteredHist.length > HISTORY_DEFAULT_LIMIT;
        const displayPicks = isTruncated ? filteredHist.slice(0, HISTORY_DEFAULT_LIMIT) : filteredHist;
        return (
        <>
        <div style={{ backgroundColor: 'var(--surface-1)', borderRadius: '16px', overflow: 'hidden', border: '1px solid var(--stroke-subtle)', marginBottom: '16px' }}>
          {displayPicks.map((pick, i) => (
            <SignalHistoryRow key={pick.id} pick={pick} isPro={isPro} isLast={i === displayPicks.length - 1} allLiveScores={allLiveScores} onView={() => onViewPick(pick)} />
          ))}
        </div>
        {isTruncated && (
          <button onClick={() => setShowAllPicks(true)} style={{ width: '100%', padding: '14px', marginTop: '8px', marginBottom: '16px', background: 'none', borderRadius: '4px', border: '1px solid var(--color-border)', color: 'var(--text-secondary)', fontSize: '14px', fontWeight: 400, fontFamily: 'var(--font-sans)', cursor: 'pointer' }}>
            View complete signal history&nbsp;&nbsp;<span style={{ color: 'var(--text-tertiary)' }}>({filteredHist.length})</span>
          </button>
        )}
        {showAllPicks && filteredHist.length > HISTORY_DEFAULT_LIMIT && (
          <button onClick={() => setShowAllPicks(false)} style={{ width: '100%', padding: '12px', marginTop: '6px', marginBottom: '16px', background: 'none', border: 'none', color: 'var(--text-tertiary)', fontSize: '12px', fontWeight: 500, fontFamily: 'var(--font-sans)', cursor: 'pointer' }}>Show less</button>
        )}
        </>
        );
      })()}
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
          fontFamily: 'var(--font-mono)', fontSize: '11px', fontWeight: 500,
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
        }}>&middot; Sigma {health.sigma}</span>
      )}
    </div>
  );
}


function PhaseTimeline({ phase }) {
  const steps = [
    { key: 'calibration', label: 'Calibration' },
    { key: 'validation', label: 'Validation' },
    { key: 'deployment', label: 'Deployment' },
  ];
  const activeIdx = steps.findIndex(s => s.key === phase);
  const blue = '#3B82F6';

  return (
    <div style={{
      backgroundColor: 'var(--surface-1)',
      border: '1px solid var(--stroke-subtle)',
      borderRadius: '12px',
      padding: '14px 16px',
      marginBottom: '14px',
    }}>
      <div style={{
        display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '0',
      }}>
        {steps.map((step, i) => {
          const isActive = i <= activeIdx;
          const isCurrent = i === activeIdx;
          return (
            <div key={step.key} style={{ display: 'flex', alignItems: 'center' }}>
              <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '4px' }}>
                <div style={{
                  width: isCurrent ? '10px' : '8px',
                  height: isCurrent ? '10px' : '8px',
                  borderRadius: '50%',
                  backgroundColor: isActive ? blue : 'var(--text-tertiary)',
                  opacity: isActive ? 1 : 0.3,
                  boxShadow: isCurrent ? `0 0 8px ${blue}` : 'none',
                  transition: 'all 0.3s',
                }} />
                <span style={{
                  fontFamily: 'var(--font-mono)',
                  fontSize: '9px',
                  fontWeight: isCurrent ? 700 : 500,
                  color: isActive ? blue : 'var(--text-tertiary)',
                  letterSpacing: '0.04em',
                  textTransform: 'uppercase',
                  opacity: isActive ? 1 : 0.5,
                }}>{step.label}</span>
              </div>
              {i < steps.length - 1 && (
                <div style={{
                  width: '32px', height: '1px',
                  backgroundColor: i < activeIdx ? blue : 'var(--text-tertiary)',
                  opacity: i < activeIdx ? 0.5 : 0.15,
                  margin: '0 6px',
                  marginBottom: '16px',
                }} />
              )}
            </div>
          );
        })}
      </div>
      <div style={{
        fontFamily: 'var(--font-mono)',
        fontSize: '10px',
        color: 'var(--text-tertiary)',
        textAlign: 'center',
        marginTop: '8px',
        letterSpacing: '0.04em',
      }}>Tracking from Day 1. No resets.</div>
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


const TRUST_STEPS = [
  { label: 'Market Regime', desc: 'Classify daily market conditions: exploitable, active, moderate, or efficient.', accent: 'rgba(79,134,247,0.7)' },
  { label: 'Edges Detected', desc: 'Every game on the slate scanned for pricing inefficiency vs. model projections.', accent: 'rgba(251,191,36,0.8)' },
  { label: 'Qualified Signals', desc: 'Only edges above the statistical threshold survive qualification filters.', accent: 'var(--green-profit)' },
  { label: 'Quant Reasoning', desc: 'Full model logic, line movement, and sharp vs. public money, transparent to you.', accent: 'var(--text-secondary)' },
  { label: 'CLV Performance', desc: 'After the game closes, did the model beat the closing line? This is the ultimate proof.', accent: 'var(--green-profit)', isFinal: true },
];

function ModelTrustStack() {
  const [open, setOpen] = useState(false);

  return (
    <div style={{ marginBottom: '16px' }}>
      <button
        onClick={() => setOpen(!open)}
        style={{
          width: '100%', display: 'flex', alignItems: 'center', justifyContent: 'space-between',
          background: 'none', border: 'none', cursor: 'pointer',
          padding: '0 0 10px',
        }}
      >
        <SectionLabel>How the Model Works</SectionLabel>
        <span style={{
          fontFamily: 'var(--font-mono)', fontSize: '11px', color: 'var(--text-tertiary)',
          transform: open ? 'rotate(180deg)' : 'rotate(0deg)',
          transition: 'transform 0.15s linear', lineHeight: 1,
        }}>▾</span>
      </button>

      {open && (
        <div style={{
          backgroundColor: 'var(--surface-1)', borderRadius: '16px',
          border: '1px solid var(--stroke-subtle)', padding: '16px',
        }}>
          <div style={{
            fontFamily: 'var(--font-mono)', fontSize: '9px', fontWeight: 700,
            letterSpacing: '0.1em', textTransform: 'uppercase',
            color: 'var(--text-tertiary)', marginBottom: '14px',
            textAlign: 'center',
          }}>Model Trust Stack</div>

          {TRUST_STEPS.map((step, i) => (
            <div key={step.label}>
              <div style={{
                display: 'flex', gap: '12px', alignItems: 'flex-start',
                padding: '8px 0',
              }}>
                <div style={{
                  width: '24px', height: '24px', borderRadius: '6px',
                  background: step.isFinal ? 'rgba(90,158,114,0.12)' : 'rgba(255,255,255,0.03)',
                  border: `1px solid ${step.isFinal ? 'rgba(90,158,114,0.25)' : 'var(--stroke-subtle)'}`,
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                  flexShrink: 0,
                }}>
                  <span style={{
                    fontFamily: 'var(--font-mono)', fontSize: '10px', fontWeight: 700,
                    color: step.accent,
                  }}>{i + 1}</span>
                </div>
                <div style={{ flex: 1 }}>
                  <div style={{
                    fontFamily: 'var(--font-mono)', fontSize: '11px', fontWeight: 700,
                    letterSpacing: '0.05em', textTransform: 'uppercase',
                    color: step.accent, lineHeight: 1.2, marginBottom: '3px',
                    display: 'flex', alignItems: 'center', gap: '6px',
                  }}>
                    {step.label}
                    {step.isFinal && (
                      <span style={{
                        fontSize: '8px', fontWeight: 700,
                        padding: '1px 5px', borderRadius: 3,
                        background: 'rgba(90,158,114,0.12)',
                        color: 'var(--green-profit)',
                        border: '1px solid rgba(90,158,114,0.25)',
                        letterSpacing: '0.04em',
                      }}>PROOF</span>
                    )}
                  </div>
                  <div style={{
                    fontFamily: 'var(--font-sans)', fontSize: '12px',
                    color: 'var(--text-tertiary)', lineHeight: 1.45,
                  }}>{step.desc}</div>
                </div>
              </div>
              {i < TRUST_STEPS.length - 1 && (
                <div style={{
                  marginLeft: '11px', width: '1px', height: '8px',
                  background: 'rgba(255,255,255,0.06)',
                }} />
              )}
            </div>
          ))}

          <div style={{
            marginTop: '14px', paddingTop: '12px',
            borderTop: '1px solid var(--stroke-subtle)',
            textAlign: 'center',
          }}>
            <p style={{
              fontFamily: 'var(--font-serif)', fontStyle: 'italic',
              fontSize: '12px', color: 'var(--text-tertiary)',
              lineHeight: 1.5, margin: 0,
            }}>
              This is how a professional betting desk evaluates a model.
            </p>
          </div>
        </div>
      )}
    </div>
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
