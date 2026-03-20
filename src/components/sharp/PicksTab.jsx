import { useState, useRef, useEffect, useCallback } from 'react';
import { Capacitor } from '@capacitor/core';
import { useAuth } from '../../hooks/useAuth';
import { useApi } from '../../hooks/useApi';
import { useSport, sportQuery } from '../../hooks/useSport';

const PT_API_BASE = Capacitor.isNativePlatform() ? 'https://app.sharppicks.ai' : '';
import PullToRefresh from '../shared/PullToRefresh';
import PickCard from './PickCard';
import NoPickCard from './NoPickCard';
import DailyInsightCard from './DailyInsightCard';
import AuthModal from './AuthModal';
import LoadingState from './LoadingState';
import ResolutionScreen from './ResolutionScreen';
import { InlineError } from './ErrorStates';

const HISTORY_DEFAULT_LIMIT = 6;

function isTodayGame(gameDate) {
  if (!gameDate) return false;
  const today = new Date().toLocaleDateString('en-CA', { timeZone: 'America/New_York' });
  return gameDate.startsWith(today);
}

function formatDateShort(isoStr) {
  if (!isoStr) return '';
  if (typeof isoStr === 'string' && isoStr.match(/^\d{4}-\d{2}-\d{2}/)) {
    const [y, m, day] = isoStr.split('-');
    const months = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
    return `${months[parseInt(m) - 1]} ${parseInt(day)}`;
  }
  return isoStr;
}

export default function PicksTab({ onNavigate }) {
  const { user, loading: authLoading } = useAuth();
  const { sport } = useSport();
  const { data: todayData, loading, error, refetch: refetchToday } = useApi(sportQuery('/picks/today', sport));
  const { data: stats, refetch: refetchStats } = useApi(sportQuery('/public/stats', sport));
  const { data: historyData, loading: historyLoading, refetch: refetchRecord } = useApi(sportQuery('/public/record', sport));
  const { data: marketReport, refetch: refetchMarketReport } = useApi(sportQuery('/public/market-report', sport), { pollInterval: 300000 });
  const { data: killSwitch } = useApi(sportQuery('/public/kill-switch', sport), { pollInterval: 600000 });
  const isPro = user && (user.is_premium || user.subscription_status === 'active' || user.subscription_status === 'trial' || user.founding_member);
  const { data: lastResolved } = useApi('/picks/last-resolved', { skip: !isPro });
  const [showAuth, setShowAuth] = useState(false);
  const [showResolution, setShowResolution] = useState(false);
  const [resolutionPick, setResolutionPick] = useState(null);
  const [filter, setFilter] = useState('all');
  const [showAllPicks, setShowAllPicks] = useState(false);
  const [dismissedResolutionId, setDismissedResolutionId] = useState(() => localStorage.getItem('sp_dismissed_resolution'));
  const [liveScore, setLiveScore] = useState(null);
  const [allLiveScores, setAllLiveScores] = useState([]);

  const handleDismissResolution = (pickId) => {
    setDismissedResolutionId(pickId);
    localStorage.setItem('sp_dismissed_resolution', pickId);
  };

  const fetchLiveForPick = useCallback(async () => {
    if (!todayData || todayData.type !== 'pick' || !todayData.home_team) return;
    try {
      const resp = await fetch(`${PT_API_BASE}/api/picks/live-scores?sport=${sport}`);
      const json = await resp.json();
      if (json.scores) {
        setAllLiveScores(json.scores);
        const normalize = s => s.toLowerCase().replace(/[^a-z]/g, '');
        const homeKey = normalize(todayData.home_team);
        const match = json.scores.find(s => normalize(s.home) === homeKey);
        if (match && (match.state === 'STATUS_IN_PROGRESS' || match.state === 'STATUS_HALFTIME' || match.state === 'STATUS_FINAL')) {
          setLiveScore(match);
        }
      }
    } catch {}
  }, [todayData, sport]);

  useEffect(() => {
    fetchLiveForPick();
    const interval = setInterval(fetchLiveForPick, 60000);
    return () => clearInterval(interval);
  }, [fetchLiveForPick]);

  if (loading || authLoading) {
    return <LoadingState />;
  }

  const isRevoked = todayData?.type === 'pick' && todayData?.result === 'revoked';
  const isResolved = todayData?.type === 'pick' && todayData?.result && todayData.result !== 'pending' && todayData.result !== 'revoked';

  if (showResolution && resolutionPick) {
    return <ResolutionScreen pick={resolutionPick} onBack={() => { setShowResolution(false); setResolutionPick(null); }} onNavigate={onNavigate} />;
  }

  const picks = historyData?.picks || [];
  const filtered = filter === 'all' ? picks
    : filter === 'wins' ? picks.filter(p => p.result === 'win')
    : filter === 'losses' ? picks.filter(p => p.result === 'loss')
    : filter === 'active' ? picks.filter(p => p.result === 'pending')
    : picks.filter(p => p.result === 'revoked' || p.result === 'push');

  return (
    <div style={{ padding: '0' }}>
      <PullToRefresh onRefresh={async () => {
        await Promise.all([refetchToday(true), refetchStats(true), refetchRecord(true), refetchMarketReport(true)]);
      }}>
      <div style={{ padding: '20px 20px 0' }}>

        {killSwitch?.active && isPro && (
          <div style={{
            display: 'flex', alignItems: 'center', gap: '8px',
            padding: '10px 14px', marginBottom: '14px',
            borderRadius: '10px',
            background: 'rgba(251,191,36,0.06)',
            border: '1px solid rgba(251,191,36,0.2)',
          }}>
            <div style={{
              width: '6px', height: '6px', borderRadius: '50%',
              backgroundColor: '#FBBF24', flexShrink: 0,
            }} />
            <div>
              <div style={{
                fontFamily: 'var(--font-mono)', fontSize: '11px', fontWeight: 700,
                color: '#FBBF24', marginBottom: '2px',
              }}>Reduced Exposure Mode</div>
              <div style={{
                fontFamily: 'var(--font-mono)', fontSize: '10px',
                color: 'var(--text-tertiary)',
              }}>Position sizing adjusted to {killSwitch.position_size_pct}%. Circuit breaker active.</div>
            </div>
          </div>
        )}

        {/* Market Intelligence link — top of tab */}
        <button
          onClick={() => onNavigate && onNavigate('market')}
          style={{
            width: '100%', padding: '12px 16px', marginBottom: '16px',
            background: '#111e33', border: '0.5px solid #1e3050',
            borderLeft: '3px solid #5A9E72',
            borderRadius: '10px', cursor: 'pointer',
            display: 'flex', alignItems: 'center', justifyContent: 'space-between',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <div style={{
              width: 32, height: 32, borderRadius: 6,
              background: 'rgba(90,158,114,0.1)',
              display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0,
            }}>
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#5A9E72" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                <path d="M3 3v18h18"/><path d="M7 16l4-8 4 4 5-9"/>
              </svg>
            </div>
            <div style={{ textAlign: 'left' }}>
              <div style={{ fontSize: '13px', fontWeight: 600, color: '#E8ECF4' }}>Market Intelligence</div>
              <div style={{ fontSize: '11px', color: '#7A8494', marginTop: '1px' }}>
                {marketReport?.available
                  ? `${marketReport.games_analyzed || 0} games · ${(marketReport.edge_distribution?.strong || 0) + (marketReport.edge_distribution?.moderate || 0) + (marketReport.edge_distribution?.weak || 0)} edges · ${marketReport.qualified_signals || 0} signals · ${marketReport.signal_density || 0}% density`
                  : "Today's report, lines, totals & moneylines"}
              </div>
            </div>
          </div>
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#7A8494" strokeWidth="2"><polyline points="9 18 15 12 9 6"/></svg>
        </button>



        {user && user.subscription_status === 'trial' && user.trial_end_date && (() => {
          const daysLeft = Math.max(0, Math.ceil((new Date(user.trial_end_date) - new Date()) / (1000 * 60 * 60 * 24)));
          return daysLeft > 0 ? (
            <div style={{
              background: 'linear-gradient(135deg, rgba(10,13,20,0.95) 0%, rgba(15,20,30,0.95) 100%)',
              border: `1px solid ${daysLeft <= 2 ? 'rgba(251,191,36,0.25)' : daysLeft <= 5 ? 'rgba(251,191,36,0.15)' : 'var(--color-signal-border)'}`,
              borderRadius: '14px',
              padding: '16px 18px',
              marginBottom: '16px',
              position: 'relative',
              overflow: 'hidden',
              ...(daysLeft <= 1 ? { animation: 'trialPulse 3s ease-in-out infinite' } : {}),
            }}>
              <style>{`
                @keyframes trialPulse { 0%, 100% { box-shadow: 0 0 0 rgba(251,191,36,0); } 50% { box-shadow: 0 0 12px rgba(251,191,36,0.08); } }
                @keyframes ctaEdgeGlow { 0%, 100% { box-shadow: 0 0 16px rgba(79,134,247,0.2), 0 2px 8px rgba(0,0,0,0.3); } 50% { box-shadow: 0 0 24px rgba(79,134,247,0.35), 0 2px 8px rgba(0,0,0,0.3); } }
              `}</style>
              <div style={{
                position: 'absolute', top: 0, right: 0, bottom: 0, width: '60px',
                background: 'radial-gradient(circle at right center, var(--color-signal-bg) 0%, transparent 70%)',
                pointerEvents: 'none',
              }} />
              <div style={{
                display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                marginBottom: '10px',
              }}>
                <div style={{
                  fontFamily: 'var(--font-mono)',
                  fontSize: '11px',
                  fontWeight: 700,
                  color: daysLeft <= 2 ? '#FBBF24' : 'var(--green-profit)',
                  letterSpacing: '0.1em',
                  textTransform: 'uppercase',
                }}>PRO TRIAL &bull; {daysLeft} {daysLeft === 1 ? 'DAY' : 'DAYS'} LEFT</div>
                <div style={{
                  fontFamily: 'var(--font-mono)',
                  fontSize: '22px',
                  fontWeight: 800,
                  color: daysLeft <= 2 ? '#FBBF24' : 'var(--green-profit)',
                  lineHeight: 1,
                  textShadow: `0 0 10px ${daysLeft <= 2 ? 'rgba(251,191,36,0.3)' : 'var(--color-signal-glow)'}`,
                }}>{daysLeft}d</div>
              </div>
              <div style={{
                fontFamily: 'var(--font-sans)',
                fontSize: '13px',
                color: 'var(--text-secondary)',
                lineHeight: 1.5,
                marginBottom: '14px',
              }}>You're inside the full model. {daysLeft <= 1 ? 'Access narrows tomorrow.' : `In ${daysLeft} days, access narrows.`}</div>
              <button
                onClick={() => onNavigate && onNavigate('profile', 'upgrade')}
                style={{
                  width: '100%',
                  padding: '12px 24px',
                  background: daysLeft <= 2
                    ? 'linear-gradient(135deg, #5A93F8 0%, #4479E5 100%)'
                    : 'linear-gradient(135deg, #4F86F7 0%, #3B6FE0 100%)',
                  border: 'none',
                  borderRadius: '10px',
                  color: '#fff',
                  fontSize: '14px',
                  fontWeight: 700,
                  cursor: 'pointer',
                  fontFamily: 'var(--font-sans)',
                  letterSpacing: '0.02em',
                  boxShadow: daysLeft <= 2
                    ? '0 0 24px rgba(90,147,248,0.3), 0 2px 8px rgba(0,0,0,0.3)'
                    : '0 0 16px rgba(79,134,247,0.2), 0 2px 8px rgba(0,0,0,0.3)',
                  position: 'relative',
                  zIndex: 1,
                  animation: 'ctaEdgeGlow 4s ease-in-out infinite',
                }}
              >Keep Pro Access</button>
              <div style={{
                textAlign: 'center',
                marginTop: '8px',
                fontFamily: 'var(--font-sans)',
                fontSize: '11px',
                color: 'rgba(255,255,255,0.6)',
                letterSpacing: '0.02em',
              }}>Full decision visibility ends after trial.</div>
            </div>
          ) : null;
        })()}

        {lastResolved && lastResolved.id && !isResolved && dismissedResolutionId !== lastResolved.id && (
          <ResolvedPickBanner
            pick={lastResolved}
            onViewDetails={() => { setResolutionPick(lastResolved); setShowResolution(true); }}
            onDismiss={() => handleDismissResolution(lastResolved.id)}
          />
        )}

        {todayData?.type === 'pick' && isResolved && isPro && dismissedResolutionId !== todayData.id && (
          <ResolvedPickBanner
            pick={todayData}
            onViewDetails={() => { setResolutionPick(todayData); setShowResolution(true); }}
            onDismiss={() => handleDismissResolution(todayData.id)}
          />
        )}

        {todayData?.type === 'pick' && isResolved && !isPro && (
          <FreePickNotice resolved onUpgrade={() => {
            if (user) {
              if (onNavigate) onNavigate('profile', 'upgrade');
            } else {
              setShowAuth(true);
            }
          }} />
        )}

        {isRevoked && (
          <RevokedPassCard pick={todayData} onViewDetails={() => { setResolutionPick(todayData); setShowResolution(true); }} />
        )}

        {todayData?.type === 'pick' && !isResolved && !isRevoked && (
          <div style={{
            fontFamily: 'var(--font-mono)', fontSize: '10px', fontWeight: 500,
            letterSpacing: '1.5px', textTransform: 'uppercase',
            color: '#7A8494', marginBottom: '8px',
            display: 'flex', alignItems: 'center', gap: '8px',
          }}>
            Daily Top Signal
            {liveScore && (liveScore.state === 'STATUS_IN_PROGRESS' || liveScore.state === 'STATUS_HALFTIME') && (
              <span style={{ display: 'inline-flex', alignItems: 'center', gap: '4px', color: '#5A9E72' }}>
                <span style={{ fontSize: '10px' }}>&middot;</span>
                <span style={{
                  width: 5, height: 5, borderRadius: '50%', backgroundColor: '#5A9E72',
                  animation: 'live-pulse 2s ease-in-out infinite', display: 'inline-block',
                }} />
                Live
              </span>
            )}
          </div>
        )}

        {todayData?.type === 'pick' && !isResolved && !isRevoked && isPro && (
          <PickCard pick={todayData} isPro={isPro} liveScore={liveScore} onUpgrade={() => setShowAuth(true)} onNavigate={onNavigate} onTrack={() => {
            if (onNavigate) onNavigate('profile', 'bets', {
              pickToTrack: {
                id: todayData.id,
                away_team: todayData.away_team,
                home_team: todayData.home_team,
                game_date: todayData.game_date,
                side: todayData.side,
                line: todayData.line,
                edge_pct: todayData.edge_pct,
                market_odds: todayData.market_odds,
              }
            });
          }} />
        )}

        {todayData?.type === 'pick' && !isResolved && !isRevoked && !isPro && (
          <FreePickNotice onUpgrade={() => {
            if (user) {
              if (onNavigate) onNavigate('profile', 'upgrade');
            } else {
              setShowAuth(true);
            }
          }} />
        )}

        {todayData?.type === 'pass' && (
          <NoPickCard data={todayData} onInsightTap={() => onNavigate('insights')} />
        )}

        {todayData?.type === 'waiting' && (
          <DailyInsightCard data={todayData} onNavigate={onNavigate} />
        )}

        {(todayData?.type === 'allstar_break' || todayData?.type === 'off_day') && (
          <BreakCard data={todayData} />
        )}

        {error && (
          <InlineError title="Data delay" message="Unable to load today's analysis. This typically resolves within a few minutes." />
        )}

        {!todayData && !error && (
          <DailyBrief stats={stats} />
        )}

        {stats && <RecordStrip stats={stats} />}

        {/* Market Intelligence link moved to top of tab */}
      </div>

      <div style={{ padding: '0 20px', marginTop: '32px' }}>
        {/* Section Header */}
        <div style={{ marginBottom: '14px' }}>
          <div style={{
            display: 'flex', justifyContent: 'space-between', alignItems: 'baseline',
          }}>
            <div style={{
              fontFamily: 'var(--font-mono)', fontSize: 'var(--text-label-size)', fontWeight: 700,
              letterSpacing: '0.08em', textTransform: 'uppercase',
              color: 'var(--text-tertiary)',
            }}>Signal History</div>
            <div style={{
              fontFamily: 'var(--font-mono)', fontSize: '11px',
              color: 'var(--text-tertiary)', fontVariantNumeric: 'tabular-nums',
            }}>{picks.length} signals</div>
          </div>
          {stats && (
            <div style={{
              fontFamily: 'var(--font-mono)', fontSize: '12px',
              color: 'var(--text-tertiary)', marginTop: '4px',
              fontVariantNumeric: 'tabular-nums',
            }}>
              Season 2025-26 &middot; {stats.record || `${stats.wins || 0}-${stats.losses || 0}`} &middot; {stats.pnl >= 0 ? '+' : ''}{Number(stats.pnl || 0).toFixed(1)}u
            </div>
          )}
        </div>

        {/* Streak Indicator */}
        {picks.length > 0 && <StreakDots picks={picks} />}

        {/* Filter Tabs */}
        <div style={{ display: 'flex', gap: '6px', marginBottom: '12px' }}>
          {[
            { key: 'all', label: 'All' },
            { key: 'wins', label: 'Wins' },
            { key: 'losses', label: 'Losses' },
            { key: 'active', label: 'Active' },
            { key: 'other', label: 'Other' },
          ].map(f => (
            <button key={f.key} onClick={() => { setFilter(f.key); setShowAllPicks(false); }} style={{
              padding: '6px 14px', borderRadius: '4px', fontSize: '13px',
              fontWeight: filter === f.key ? 600 : 400, cursor: 'pointer',
              fontFamily: 'var(--font-sans)',
              backgroundColor: filter === f.key ? 'var(--color-signal)' : 'transparent',
              color: filter === f.key ? '#FFFFFF' : 'var(--text-tertiary)',
              border: filter === f.key ? 'none' : '1px solid var(--color-border)',
              transition: 'none',
            }}>{f.label}</button>
          ))}
        </div>

        {historyLoading ? (
          <p style={{ color: 'var(--text-secondary)', fontSize: '14px', textAlign: 'center', padding: '40px 0' }}>
            Loading...
          </p>
        ) : filtered.length === 0 ? (
          <SignalHistoryEmpty filter={filter} totalCount={picks.length} />
        ) : (() => {
          const isTruncated = !showAllPicks && filtered.length > HISTORY_DEFAULT_LIMIT;
          const displayPicks = isTruncated ? filtered.slice(0, HISTORY_DEFAULT_LIMIT) : filtered;
          return (
          <>
          <div style={{
            backgroundColor: 'var(--surface-1)', borderRadius: '16px',
            overflow: 'hidden', border: '1px solid var(--stroke-subtle)',
          }}>
            {displayPicks.map((pick, i) => (
              <SignalHistoryRow
                key={pick.id}
                pick={pick}
                isPro={isPro}
                isLast={i === displayPicks.length - 1}
                allLiveScores={allLiveScores}
                onView={() => { setResolutionPick(pick); setShowResolution(true); }}
              />
            ))}
          </div>
          {isTruncated && (
            <button onClick={() => setShowAllPicks(true)} style={{
              width: '100%', padding: '14px', marginTop: '8px',
              background: 'none', borderRadius: '4px',
              border: '1px solid var(--color-border)',
              color: 'var(--text-secondary)', fontSize: '14px', fontWeight: 400,
              fontFamily: 'var(--font-sans)', cursor: 'pointer',
              letterSpacing: '0.01em',
            }}>
              View complete signal history&nbsp;&nbsp;<span style={{ color: 'var(--text-tertiary)' }}>({filtered.length})</span>
            </button>
          )}
          {showAllPicks && filtered.length > HISTORY_DEFAULT_LIMIT && (
            <button onClick={() => setShowAllPicks(false)} style={{
              width: '100%', padding: '12px', marginTop: '6px',
              background: 'none', border: 'none',
              color: 'var(--text-tertiary)', fontSize: '12px', fontWeight: 500,
              fontFamily: 'var(--font-sans)', cursor: 'pointer',
            }}>Show less</button>
          )}
          </>
          );
        })()}
      </div>

      {showAuth && <AuthModal onClose={() => setShowAuth(false)} />}
      </PullToRefresh>
    </div>
  );
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
    <span style={{
      fontFamily: 'var(--font-mono)', fontSize: '11px', fontWeight: 700,
      width: isWide ? '28px' : '24px', height: '24px',
      borderRadius: isWide ? '12px' : '50%',
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      flexShrink: 0, backgroundColor: c.bg, color: c.color,
      letterSpacing: isWide ? '-0.02em' : '0',
    }}>
      {c.label}
    </span>
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
  const liveLabel = liveMatch
    ? `Live${liveMatch.period ? ` Q${liveMatch.period}` : ''}`
    : null;

  const units = pick.profit_units != null ? pick.profit_units : (pick.pnl != null ? pick.pnl / 100 : null);
  const unitsStr = (() => {
    if (pick.result === 'push') return '0.0u';
    if (pick.result === 'win') return `+${units != null ? Math.abs(units).toFixed(1) : '0.9'}u`;
    if (pick.result === 'loss') return `-${units != null ? Math.abs(units).toFixed(1) : '1.0'}u`;
    return null;
  })();

  const unitsColor = pick.result === 'win' ? 'var(--color-signal)'
    : pick.result === 'loss' ? 'var(--color-loss)'
    : 'var(--text-tertiary)';

  const pendingLabel = isPending ? 'Pending' : null;
  const rightLine1 = isSettled ? unitsStr : (isPending ? pendingLabel : isRevoked ? 'Withdrawn' : null);
  const rightLine1Color = isSettled ? unitsColor : 'var(--text-tertiary)';
  const showCountdown = isPending && pick.start_time && pick.start_time.includes('T') && isTodayGame(pick.game_date);

  const clvVal = pick.clv != null ? parseFloat(pick.clv) : null;
  const hasCLV = isSettled && clvVal != null;
  const rightLine2 = hasCLV
    ? `CLV ${clvVal >= 0 ? '+' : ''}${clvVal.toFixed(1)}`
    : (pick.edge_pct && !hideLine) ? `+${pick.edge_pct}% edge` : null;
  const rightLine2Color = hasCLV
    ? (clvVal > 0 ? 'var(--color-signal)' : clvVal < 0 ? 'var(--color-loss)' : 'var(--text-tertiary)')
    : 'var(--text-tertiary)';

  const sideDisplay = hideLine
    ? `${pick.away_team} @ ${pick.home_team}`
    : (pick.side || `${pick.away_team} @ ${pick.home_team}`);

  return (
    <div
      onClick={() => canView && onView()}
      style={{
        padding: '14px 16px',
        borderBottom: isLast ? 'none' : '1px solid var(--stroke-subtle)',
        display: 'flex', alignItems: 'center', gap: '8px',
        cursor: canView ? 'pointer' : 'default',
        minHeight: '60px',
        transition: 'background-color 0.1s',
      }}
      onMouseDown={e => canView && (e.currentTarget.style.opacity = '0.7')}
      onMouseUp={e => canView && (e.currentTarget.style.opacity = '1')}
      onMouseLeave={e => canView && (e.currentTarget.style.opacity = '1')}
    >
      <StatusBadge result={pick.result} />

      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{
          fontSize: '14px', fontWeight: 600, color: 'var(--text-primary)',
          whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis',
        }}>
          {sideDisplay}
        </div>
        <div style={{
          fontSize: '13px', color: 'var(--text-secondary)', marginTop: '2px',
          fontFamily: 'var(--font-mono)',
          whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis',
        }}>
          {pick.away_team} @ {pick.home_team} &middot; {formatDateShort(pick.game_date)}
          {liveLabel && <span style={{ color: '#5A9E72' }}> · {liveLabel}</span>}
        </div>
      </div>

      <div style={{ display: 'flex', alignItems: 'center', gap: '6px', flexShrink: 0 }}>
        <div style={{ textAlign: 'right' }}>
          {showCountdown ? (
            <CountdownLabel startTime={pick.start_time} />
          ) : rightLine1 ? (
            <div style={{
              fontFamily: 'var(--font-mono)', fontSize: isSettled ? '14px' : '12px',
              fontWeight: isSettled ? 600 : 500,
              fontVariantNumeric: 'tabular-nums',
              color: rightLine1Color,
            }}>{rightLine1}</div>
          ) : null}
          {isPro && rightLine2 && (
            <div style={{
              fontFamily: 'var(--font-mono)',
              fontSize: hasCLV ? '12px' : '11px',
              fontWeight: hasCLV ? 600 : 400,
              fontVariantNumeric: 'tabular-nums',
              color: rightLine2Color, marginTop: '2px',
              ...(hasCLV ? {
                padding: '1px 5px', borderRadius: 3,
                background: clvVal > 0 ? 'rgba(52,211,153,0.08)' : clvVal < 0 ? 'rgba(158,122,124,0.08)' : 'transparent',
              } : {}),
            }}>{rightLine2}</div>
          )}
        </div>

        {canView && (
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="var(--text-tertiary)" strokeWidth="2" style={{ flexShrink: 0 }}>
            <polyline points="9 18 15 12 9 6"/>
          </svg>
        )}
      </div>
    </div>
  );
}

function SignalHistoryEmpty({ filter, totalCount }) {
  if (totalCount === 0) {
    return (
      <div style={{
        textAlign: 'center', padding: '48px 24px',
        color: 'var(--text-tertiary)', fontSize: '14px', lineHeight: '1.7',
      }}>
        <div style={{
          fontFamily: 'var(--font-mono)', fontSize: 'var(--text-label-size)', fontWeight: 700,
          letterSpacing: '0.08em', textTransform: 'uppercase',
          color: 'var(--text-secondary)', marginBottom: '12px',
        }}>No signals generated yet.</div>
        <p style={{ maxWidth: '300px', margin: '0 auto 12px' }}>
          The model evaluates the full daily slate and generates signals only when a statistically significant edge is detected.
        </p>
        <p style={{ color: 'var(--text-tertiary)', fontSize: '13px' }}>
          Check back after today&apos;s market intelligence report.
        </p>
      </div>
    );
  }

  const msgs = {
    wins: { title: 'No wins recorded.', detail: `0 of ${totalCount} signals resulted in a win.` },
    losses: { title: 'No losses recorded.', detail: `0 of ${totalCount} signals resulted in a loss.` },
    active: { title: 'No active signals.', detail: 'All signals have been resolved.' },
    other: { title: 'No withdrawn or push signals.', detail: '' },
  };
  const m = msgs[filter] || { title: 'No signals found.', detail: '' };

  return (
    <div style={{
      textAlign: 'center', padding: '40px 24px',
      color: 'var(--text-tertiary)', fontSize: '14px',
    }}>
      <div style={{ color: 'var(--text-secondary)', marginBottom: '6px' }}>{m.title}</div>
      {m.detail && <div style={{ fontSize: '13px' }}>{m.detail}</div>}
    </div>
  );
}


function RevokedPassCard({ pick, onViewDetails }) {
  return (
    <div
      onClick={onViewDetails}
      style={{
        backgroundColor: 'var(--surface-1)',
        borderRadius: '16px',
        border: '1px solid var(--color-border)',
        padding: 'var(--space-lg)',
        marginBottom: 'var(--space-md)',
        cursor: 'pointer',
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '14px' }}>
        <div style={{
          width: '44px', height: '44px', borderRadius: '50%',
          backgroundColor: 'rgba(142,154,175,0.08)',
          border: '1px solid rgba(142,154,175,0.2)',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          flexShrink: 0,
        }}>
          <svg viewBox="0 0 24 24" width="20" height="20" stroke="var(--withdrawn)" fill="none" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
            <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>
          </svg>
        </div>
        <div style={{ flex: 1 }}>
          <div style={{
            fontFamily: 'var(--font-mono)', fontSize: 'var(--text-label-size)', fontWeight: 700,
            letterSpacing: '0.08em', textTransform: 'uppercase',
            color: 'var(--withdrawn)', marginBottom: '4px',
          }}>Signal Withdrawn</div>
          <div style={{
            fontFamily: 'var(--font-sans)', fontSize: 'var(--text-card-title)', fontWeight: 600,
            color: 'var(--text-primary)',
          }}>
            {pick.side && pick.line != null && pick.side.includes(String(Math.abs(pick.line)))
              ? pick.side
              : `${pick.side} ${pick.line > 0 ? '+' : ''}${pick.line}`}
          </div>
        </div>
        <div style={{
          fontFamily: 'var(--font-mono)', fontSize: '22px', fontWeight: 700,
          fontVariantNumeric: 'tabular-nums',
          color: 'var(--text-tertiary)',
        }}>0.0u</div>
      </div>

      <div style={{
        fontFamily: 'var(--font-mono)', fontSize: '13px',
        color: 'var(--text-secondary)', marginBottom: '6px',
      }}>
        {pick.away_team} @ {pick.home_team}
      </div>

      <div style={{
        fontFamily: 'var(--font-mono)', fontSize: '11px',
        color: 'var(--text-tertiary)',
      }}>
        {pick.edge_pct ? `${pick.edge_pct}% edge at entry · ` : ''}Withdrawn pre-tip
      </div>

      <div style={{
        display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '6px',
        marginTop: 'var(--space-md)', paddingTop: '14px',
        borderTop: '1px solid var(--color-border)',
      }}>
        <span style={{
          fontFamily: 'var(--font-mono)', fontSize: 'var(--text-label-size)', fontWeight: 700,
          letterSpacing: '0.08em', textTransform: 'uppercase',
          color: 'var(--text-tertiary)',
        }}>View Details</span>
        <svg viewBox="0 0 24 24" width="14" height="14" stroke="var(--text-tertiary)" fill="none" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <polyline points="9 18 15 12 9 6"/>
        </svg>
      </div>
    </div>
  );
}

function BreakCard({ data }) {
  const isAllStar = data?.type === 'allstar_break';
  const resumeDate = data?.resume_date;

  return (
    <div style={{
      background: 'var(--surface-1)',
      borderRadius: '16px', border: '1px solid var(--color-border)',
      padding: '36px 24px', textAlign: 'center', marginBottom: 'var(--space-md)',
    }}>
      <div style={{
        width: '6px', height: '6px', borderRadius: '50%',
        background: 'var(--text-tertiary)', opacity: 0.5,
        margin: '0 auto 24px',
      }} />
      <div style={{
        fontFamily: 'var(--font-mono)',
        fontSize: 'var(--text-label-size)', fontWeight: 700,
        letterSpacing: '0.08em', textTransform: 'uppercase',
        color: 'var(--text-secondary)', marginBottom: '10px',
      }}>{isAllStar ? 'All-Star Break' : 'No Games Scheduled'}</div>
      <p style={{
        fontSize: 'var(--text-metric)', color: 'var(--text-tertiary)', lineHeight: '1.7',
        maxWidth: '320px', margin: '0 auto 20px',
      }}>
        {isAllStar
          ? 'Regular season suspended. No games scheduled.'
          : data?.message || 'No games scheduled. Model resumes when games return.'}
      </p>
      {resumeDate && (
        <div style={{
          display: 'inline-flex', alignItems: 'center', gap: '8px',
          padding: 'var(--space-sm) var(--space-md)', borderRadius: '10px',
          backgroundColor: 'rgba(255,255,255,0.03)', border: '1px solid var(--color-border)',
        }}>
          <span style={{
            fontFamily: 'var(--font-mono)', fontSize: '12px', fontWeight: 600,
            color: 'var(--text-secondary)', letterSpacing: '0.5px',
          }}>Next scan: {new Date(resumeDate + 'T12:00:00').toLocaleDateString('en-US', { weekday: 'long', month: 'short', day: 'numeric' })}</span>
        </div>
      )}
      <div style={{
        marginTop: 'var(--space-lg)', padding: 'var(--space-md)', borderRadius: '12px',
        backgroundColor: 'rgba(255,255,255,0.02)', border: '1px solid var(--color-border)',
      }}>
        <p style={{
          fontSize: 'var(--text-caption)', color: 'var(--text-tertiary)', lineHeight: '1.6',
          fontFamily: 'var(--font-sans)', margin: 0,
        }}>
          {isAllStar
            ? 'Discipline means knowing when not to play. Model automatically resumes when regular season action returns.'
            : 'No action required. Analysis resumes automatically when games are scheduled.'}
        </p>
      </div>
    </div>
  );
}

function DailyBrief({ stats }) {
  return (
    <div style={{ textAlign: 'center', padding: '40px 0 24px' }}>
      <div style={{
        width: '6px', height: '6px', borderRadius: '50%',
        background: 'var(--text-tertiary)',
        margin: '0 auto 24px',
        animation: 'live-pulse 2s ease-in-out infinite',
      }} />
      <h2 style={{
        fontFamily: 'var(--font-mono)',
        fontSize: 'var(--text-label-size)', fontWeight: 700,
        letterSpacing: '0.08em', textTransform: 'uppercase',
        color: 'var(--text-secondary)', marginBottom: '10px',
      }}>Market Intelligence Active</h2>
      <p style={{
        fontSize: 'var(--text-metric)', color: 'var(--text-tertiary)', lineHeight: '1.6',
        maxWidth: '300px', margin: '0 auto',
      }}>
        Evaluating today's games...
      </p>
      {stats && (
        <div style={{
          marginTop: 'var(--space-lg)', display: 'flex', justifyContent: 'center', gap: 'var(--space-lg)',
        }}>
          <Stat label="Record" value={stats.record || '0-0'} />
          <Stat label="Win Rate" value={stats.win_rate ? `${stats.win_rate}%` : '--'} />
          <Stat label="Passes" value={stats.capital_preserved_days || 0} />
        </div>
      )}
    </div>
  );
}

function Stat({ label, value }) {
  return (
    <div>
      <div style={{
        fontFamily: 'var(--font-mono)', fontSize: 'var(--text-card-title)', fontWeight: 700,
        fontVariantNumeric: 'tabular-nums',
        color: 'var(--text-primary)',
      }}>{value}</div>
      <div style={{
        fontSize: '11px', color: 'var(--text-tertiary)', marginTop: '2px',
        textTransform: 'uppercase', letterSpacing: '0.08em', fontWeight: 700,
      }}>{label}</div>
    </div>
  );
}

function RecordStrip({ stats }) {
  const hasClv = stats.avg_clv != null;
  return (
    <div style={{
      backgroundColor: 'var(--surface-1)', borderRadius: '12px',
      padding: 'var(--space-md)', marginTop: 'var(--space-md)',
      border: '1px solid var(--color-border)',
    }}>
      <div style={{
        fontFamily: 'var(--font-mono)', fontSize: 'var(--text-label-size)', fontWeight: 700,
        letterSpacing: '0.08em', textTransform: 'uppercase',
        color: 'var(--text-tertiary)', marginBottom: 'var(--space-sm)',
      }}>Season Performance</div>
      <div style={{
        display: 'flex', justifyContent: 'space-between', alignItems: 'center',
      }}>
        <MiniStat label="Win Rate" value={stats.win_rate != null ? `${stats.win_rate}%` : '--'} />
        <MiniStat label="ROI" value={stats.roi != null ? `${stats.roi >= 0 ? '+' : ''}${stats.roi}%` : '--'} highlight={stats.roi >= 0} />
        {hasClv && (
          <MiniStat
            label="Avg CLV"
            value={`${stats.avg_clv > 0 ? '+' : ''}${stats.avg_clv.toFixed(1)}`}
            highlight={stats.avg_clv > 0}
          />
        )}
        <MiniStat label="Signals" value={stats.total_picks} />
        <MiniStat label="Units" value={`${stats.pnl >= 0 ? '+' : ''}${Number(stats.pnl).toFixed(1)}u`} highlight={stats.pnl >= 0} />
      </div>
    </div>
  );
}

function MiniStat({ label, value, highlight }) {
  return (
    <div>
      <div style={{
        fontFamily: 'var(--font-mono)', fontSize: 'var(--text-metric)', fontWeight: 700,
        fontVariantNumeric: 'tabular-nums',
        color: highlight ? 'var(--color-signal)' : 'var(--text-primary)',
      }}>{value}</div>
      <div style={{
        fontSize: '11px', color: 'var(--text-tertiary)',
        textTransform: 'uppercase', letterSpacing: '0.08em', fontWeight: 700,
      }}>{label}</div>
    </div>
  );
}

function ResolvedPickBanner({ pick, onViewDetails, onDismiss }) {
  const isWin = pick.result === 'win';
  const isPush = pick.result === 'push';

  const scoreDisplay = (pick.home_score != null && pick.away_score != null)
    ? `${pick.away_team} ${pick.away_score}, ${pick.home_team} ${pick.home_score}`
    : null;

  return (
    <div
      onClick={onViewDetails}
      style={{
        backgroundColor: 'var(--surface-1)',
        borderRadius: '16px',
        border: '1px solid var(--color-border)',
        padding: 'var(--space-lg)',
        marginBottom: 'var(--space-md)',
        cursor: 'pointer',
        position: 'relative',
        opacity: 0.85,
      }}
    >
      {onDismiss && (
        <button
          onClick={(e) => { e.stopPropagation(); onDismiss(); }}
          style={{
            position: 'absolute', top: '12px', right: '12px',
            background: 'none', border: 'none', cursor: 'pointer',
            color: 'var(--text-tertiary)', padding: '4px',
            minWidth: '44px', minHeight: '44px',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
          }}
          aria-label="Dismiss"
        >
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
            <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
          </svg>
        </button>
      )}

      <div style={{ marginBottom: '14px' }}>
        <div style={{
          fontFamily: 'var(--font-mono)', fontSize: 'var(--text-label-size)', fontWeight: 700,
          letterSpacing: '0.08em', textTransform: 'uppercase',
          color: 'var(--text-tertiary)', marginBottom: '6px',
        }}>Outcome Resolved</div>
        <div style={{
          fontFamily: 'var(--font-sans)', fontSize: '17px', fontWeight: 600,
          color: 'var(--text-primary)',
        }}>
          {pick.side && pick.line != null && pick.side.includes(String(Math.abs(pick.line)))
            ? pick.side
            : `${pick.side} ${pick.line > 0 ? '+' : ''}${pick.line}`}
        </div>
      </div>

      {scoreDisplay && (
        <div style={{
          fontFamily: 'var(--font-mono)', fontSize: '13px',
          fontVariantNumeric: 'tabular-nums',
          color: 'var(--text-secondary)', marginBottom: '10px',
        }}>
          Final: {scoreDisplay}
        </div>
      )}

      <div style={{
        fontSize: '13px',
        color: 'var(--text-tertiary)', lineHeight: '1.6',
        marginBottom: 'var(--space-md)',
      }}>
        {isPush
          ? "Push. The spread landed on the number. Next signal when the edge is there."
          : isWin
          ? "Process unchanged. Next signal when the edge is there."
          : "Process unchanged. No revenge bets. Next signal when the edge is there."
        }
      </div>

      <div style={{
        display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '6px',
        fontFamily: 'var(--font-sans)', fontSize: '13px', fontWeight: 500,
        color: 'var(--color-info)',
      }}>
        View outcome log
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <path d="M5 12h14M12 5l7 7-7 7"/>
        </svg>
      </div>
    </div>
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
      if (mins < 5) setLabel('Tips soon');
      else if (hrs < 1) setLabel(`Tips in ${mins}m`);
      else if (hrs < 24) setLabel(`Tips in ${hrs}h ${remMins}m`);
      else setLabel('Tips tomorrow');
    }
    calc();
    const id = setInterval(calc, 60000);
    return () => clearInterval(id);
  }, [startTime]);

  return (
    <div style={{
      fontFamily: 'var(--font-mono)', fontSize: '12px', fontWeight: 500,
      fontVariantNumeric: 'tabular-nums',
      color: '#d4a24e',
    }}>{label}</div>
  );
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

  let streakCount = 0;
  let streakType = null;
  for (const p of picks) {
    if (p.result === 'win' || p.result === 'loss') {
      if (!streakType) {
        streakType = p.result;
        streakCount = 1;
      } else if (p.result === streakType) {
        streakCount++;
      } else {
        break;
      }
    } else if (p.result === 'pending' || p.result === 'revoked') {
      if (!streakType) continue;
      break;
    } else {
      if (!streakType) continue;
      break;
    }
  }

  const streakLabel = streakType === 'win'
    ? `W${streakCount} streak` : streakType === 'loss'
    ? `L${streakCount} streak` : '';
  const streakColor = streakType === 'win' ? '#5A9E72' : streakType === 'loss' ? '#C4686B' : '#6b7a8d';

  return (
    <div style={{
      display: 'flex', justifyContent: 'space-between', alignItems: 'center',
      marginBottom: 10,
    }}>
      <div style={{ display: 'flex', gap: 4 }}>
        {[...last7].reverse().map((p, i) => {
          const cfg = dotConfig[p.result] || dotConfig.pending;
          const isWide = cfg.label.length > 1;
          return (
            <div key={i} style={{
              minWidth: isWide ? 26 : 22, height: 22, borderRadius: '50%',
              background: cfg.bg, display: 'flex', alignItems: 'center', justifyContent: 'center',
              ...(isWide ? { borderRadius: 11, padding: '0 2px' } : {}),
            }}>
              <span style={{
                fontFamily: "var(--font-mono)", fontSize: '9px', fontWeight: 500,
                color: cfg.color,
              }}>{cfg.label}</span>
            </div>
          );
        })}
      </div>
      {streakLabel && (
        <span style={{
          fontFamily: "var(--font-mono)", fontSize: '11px', fontWeight: 500,
          color: streakColor,
        }}>{streakLabel}</span>
      )}
    </div>
  );
}

function FreePickNotice({ onUpgrade, resolved }) {
  return (
    <div style={{
      backgroundColor: 'var(--surface-1)',
      border: '1px solid var(--color-border)',
      borderRadius: '16px',
      padding: '32px 24px',
      textAlign: 'center',
    }}>
      <div style={{
        width: '56px', height: '56px', borderRadius: '14px',
        backgroundColor: 'var(--color-signal-bg)',
        border: '1px solid var(--color-signal-border)',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        margin: '0 auto 20px',
      }}>
        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="var(--color-signal)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <polyline points="20 6 9 17 4 12"/>
        </svg>
      </div>

      <div style={{
        fontFamily: 'var(--font-mono)',
        fontSize: 'var(--text-label-size)', fontWeight: 700,
        letterSpacing: '0.08em', textTransform: 'uppercase',
        color: 'var(--color-signal)',
        marginBottom: '12px',
      }}>Signal Published</div>

      <p style={{
        fontSize: 'var(--text-metric)', color: 'var(--text-secondary)',
        lineHeight: '1.6', marginBottom: '24px',
        maxWidth: '280px', margin: '0 auto 24px',
      }}>
        {resolved
          ? "Today's signal has been resolved. Upgrade to see the outcome, side, and full analysis."
          : "Edge detected. Upgrade to see the full signal, side, and analysis."
        }
      </p>

      <button
        onClick={onUpgrade}
        style={{
          width: '100%', height: '48px', borderRadius: '14px',
          border: 'none',
          background: 'linear-gradient(135deg, var(--blue-primary), var(--blue-deep))',
          color: 'white', fontFamily: 'var(--font-sans)',
          fontSize: '14px', fontWeight: 700, cursor: 'pointer',
        }}
      >
        Upgrade to See Signal
      </button>

      <p style={{
        fontSize: 'var(--text-caption)', color: 'var(--text-tertiary)',
        marginTop: '12px',
      }}>Full access · Cancel anytime</p>
    </div>
  );
}
