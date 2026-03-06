import { useState, useRef, useEffect } from 'react';
import { useAuth } from '../../hooks/useAuth';
import { useApi } from '../../hooks/useApi';
import { useSport, sportQuery } from '../../hooks/useSport';
import PullToRefresh from '../shared/PullToRefresh';
import PickCard from './PickCard';
import NoPickCard from './NoPickCard';
import DailyInsightCard from './DailyInsightCard';
import AuthModal from './AuthModal';
import LoadingState from './LoadingState';
import ResolutionScreen from './ResolutionScreen';
import MarketView from './MarketView';
import { InlineError } from './ErrorStates';

const HISTORY_DEFAULT_LIMIT = 6;

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
  const isPro = user && (user.is_premium || user.subscription_status === 'active' || user.subscription_status === 'trial' || user.founding_member);
  const { data: lastResolved } = useApi('/picks/last-resolved', { skip: !isPro });
  const [showAuth, setShowAuth] = useState(false);
  const [showResolution, setShowResolution] = useState(false);
  const [resolutionPick, setResolutionPick] = useState(null);
  const [showMarket, setShowMarket] = useState(false);
  const [filter, setFilter] = useState('all');
  const [showAllPicks, setShowAllPicks] = useState(false);
  const [dismissedResolutionId, setDismissedResolutionId] = useState(null);

  const handleDismissResolution = (pickId) => {
    setDismissedResolutionId(pickId);
  };

  if (loading || authLoading) {
    return <LoadingState />;
  }

  const isRevoked = todayData?.type === 'pick' && todayData?.result === 'revoked';
  const isResolved = todayData?.type === 'pick' && todayData?.result && todayData.result !== 'pending' && todayData.result !== 'revoked';

  if (showMarket) {
    return <MarketView onBack={() => setShowMarket(false)} />;
  }

  if (showResolution && resolutionPick) {
    return <ResolutionScreen pick={resolutionPick} onBack={() => { setShowResolution(false); setResolutionPick(null); }} onNavigate={onNavigate} />;
  }

  const picks = historyData?.picks || [];
  const filtered = filter === 'all' ? picks
    : filter === 'wins' ? picks.filter(p => p.result === 'win')
    : filter === 'losses' ? picks.filter(p => p.result === 'loss')
    : picks.filter(p => p.result === 'pending');

  return (
    <div style={{ padding: '0' }}>
      <PullToRefresh onRefresh={async () => {
        await Promise.all([refetchToday(true), refetchStats(true), refetchRecord(true)]);
      }}>
      <div style={{ padding: '20px 20px 0' }}>
        {user && user.subscription_status === 'trial' && user.trial_end_date && (() => {
          const daysLeft = Math.max(0, Math.ceil((new Date(user.trial_end_date) - new Date()) / (1000 * 60 * 60 * 24)));
          return daysLeft > 0 ? (
            <div style={{
              background: 'linear-gradient(135deg, rgba(10,13,20,0.95) 0%, rgba(15,20,30,0.95) 100%)',
              border: `1px solid ${daysLeft <= 2 ? 'rgba(251,191,36,0.25)' : daysLeft <= 5 ? 'rgba(251,191,36,0.15)' : 'rgba(52,211,153,0.12)'}`,
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
                background: 'radial-gradient(circle at right center, rgba(52,211,153,0.08) 0%, transparent 70%)',
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
                  textShadow: `0 0 10px ${daysLeft <= 2 ? 'rgba(251,191,36,0.3)' : 'rgba(52,211,153,0.25)'}`,
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
                color: 'rgba(255,255,255,0.25)',
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

        {todayData?.type === 'pick' && isResolved && isPro && (
          <ResolvedPickBanner
            pick={todayData}
            onViewDetails={() => { setResolutionPick(todayData); setShowResolution(true); }}
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

        {todayData?.type === 'pick' && !isResolved && !isRevoked && isPro && (
          <PickCard pick={todayData} isPro={isPro} onUpgrade={() => setShowAuth(true)} onNavigate={onNavigate} onTrack={() => {
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

        <button
          onClick={() => setShowMarket(true)}
          style={{
            width: '100%', padding: '12px 16px', marginTop: '16px',
            background: 'var(--surface-1)', border: '1px solid var(--stroke-subtle)',
            borderRadius: '12px', cursor: 'pointer',
            display: 'flex', alignItems: 'center', justifyContent: 'space-between',
            transition: 'border-color 0.2s ease',
          }}
          onMouseEnter={e => e.currentTarget.style.borderColor = 'rgba(79, 134, 247, 0.3)'}
          onMouseLeave={e => e.currentTarget.style.borderColor = 'var(--stroke-subtle)'}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="var(--text-secondary)" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
              <path d="M3 3v18h18"/><path d="M7 16l4-8 4 4 5-9"/>
            </svg>
            <div>
              <div style={{ fontSize: '13px', fontWeight: 600, color: 'var(--text-primary)' }}>Market View</div>
              <div style={{ fontSize: '11px', color: 'var(--text-tertiary)', marginTop: '1px' }}>Today&apos;s lines, totals &amp; moneylines</div>
            </div>
          </div>
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="var(--text-tertiary)" strokeWidth="2"><polyline points="9 18 15 12 9 6"/></svg>
        </button>
      </div>

      <div style={{ padding: '0 20px', marginTop: '32px' }}>
        <div style={{
          display: 'flex', justifyContent: 'space-between', alignItems: 'baseline',
          marginBottom: '14px',
        }}>
          <div style={{
            fontFamily: 'var(--font-mono)', fontSize: '10px', fontWeight: 600,
            letterSpacing: '2px', textTransform: 'uppercase',
            color: 'var(--text-tertiary)',
          }}>History</div>
          <div style={{
            fontFamily: 'var(--font-mono)', fontSize: '11px',
            color: 'var(--text-tertiary)',
          }}>{picks.length} picks</div>
        </div>

        <div style={{ display: 'flex', gap: '6px', marginBottom: '12px' }}>
          {['all', 'wins', 'losses', 'pending'].map(f => (
            <button key={f} onClick={() => { setFilter(f); setShowAllPicks(false); }} style={{
              padding: '5px 12px', borderRadius: '8px', fontSize: '11px',
              fontWeight: 600, cursor: 'pointer',
              textTransform: 'capitalize', fontFamily: 'var(--font-sans)',
              backgroundColor: filter === f ? 'rgba(79,125,243,0.18)' : 'rgba(255,255,255,0.04)',
              color: filter === f ? '#FFFFFF' : 'rgba(255,255,255,0.55)',
              border: filter === f ? '1px solid rgba(79,125,243,0.45)' : '1px solid transparent',
            }}>{f}</button>
          ))}
        </div>

        {historyLoading ? (
          <p style={{ color: 'var(--text-secondary)', fontSize: '14px', textAlign: 'center', padding: '40px 0' }}>
            Loading...
          </p>
        ) : filtered.length === 0 ? (
          <div style={{
            textAlign: 'center', padding: '40px 0',
            color: 'var(--text-tertiary)', fontSize: '14px',
          }}>
            {filter === 'wins' ? 'No wins yet this season.' : filter === 'losses' ? 'No losses yet this season.' : filter === 'pending' ? 'No pending picks.' : 'No picks found'}
          </div>
        ) : (() => {
          const isTruncated = !showAllPicks && filtered.length > HISTORY_DEFAULT_LIMIT;
          const displayPicks = isTruncated ? filtered.slice(0, HISTORY_DEFAULT_LIMIT) : filtered;
          return (
          <>
          <div style={{
            backgroundColor: 'var(--surface-1)', borderRadius: '16px',
            overflow: 'hidden', border: '1px solid var(--stroke-subtle)',
          }}>
            {displayPicks.map((pick, i) => {
              const pickResolved = pick.result === 'win' || pick.result === 'loss';
              const isPending = pick.result === 'pending';
              const isRevoked = pick.result === 'revoked';
              const hideLine = !isPro && isPending;
              const canView = isPro && (pickResolved || isRevoked);
              return (
                <div key={pick.id} onClick={() => canView && (() => { setResolutionPick(pick); setShowResolution(true); })()} style={{
                  padding: '14px 20px',
                  borderBottom: i < displayPicks.length - 1 ? '1px solid var(--stroke-subtle)' : 'none',
                  display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                  cursor: canView ? 'pointer' : 'default',
                }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                    {pickResolved && (
                      <span style={{
                        fontFamily: 'var(--font-mono)', fontSize: '11px', fontWeight: 700,
                        width: '22px', height: '22px', borderRadius: '6px',
                        display: 'flex', alignItems: 'center', justifyContent: 'center',
                        flexShrink: 0,
                        backgroundColor: pick.result === 'win' ? 'rgba(52,211,153,0.15)' : 'rgba(239,68,68,0.15)',
                        color: pick.result === 'win' ? 'var(--green-profit)' : 'var(--red-loss)',
                        border: `1px solid ${pick.result === 'win' ? 'rgba(52,211,153,0.3)' : 'rgba(239,68,68,0.3)'}`,
                      }}>
                        {pick.result === 'win' ? 'W' : 'L'}
                      </span>
                    )}
                    <div>
                    <div style={{
                      fontSize: '14px', fontWeight: 500, color: 'var(--text-primary)',
                    }}>
                      {hideLine ? `${pick.away_team} @ ${pick.home_team}` : (pick.side || `${pick.away_team} @ ${pick.home_team}`)}
                    </div>
                    {!hideLine && (
                      <div style={{
                        fontSize: '12px', color: 'var(--text-tertiary)', marginTop: '2px',
                      }}>{pick.away_team} @ {pick.home_team}</div>
                    )}
                    <div style={{
                      fontSize: '11px', color: 'var(--text-tertiary)', marginTop: '2px',
                      fontFamily: 'var(--font-mono)',
                    }}>{formatDateShort(pick.game_date)}</div>
                    </div>
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <div style={{ textAlign: 'right' }}>
                      {hideLine ? (
                        <span style={{
                          fontFamily: 'var(--font-mono)', fontSize: '11px', fontWeight: 600,
                          color: 'rgba(255,255,255,0.5)',
                          backgroundColor: 'rgba(255,255,255,0.06)',
                          border: '1px solid rgba(255,255,255,0.08)',
                          padding: '4px 10px', borderRadius: '20px',
                          display: 'inline-block',
                        }}>Pending</span>
                      ) : (
                        <>
                        {isRevoked ? (
                          <span style={{
                            fontFamily: 'var(--font-mono)', fontSize: '11px', fontWeight: 600,
                            color: 'rgba(255,255,255,0.5)',
                            backgroundColor: 'rgba(255,255,255,0.06)',
                            border: '1px solid rgba(255,255,255,0.08)',
                            padding: '4px 10px', borderRadius: '20px',
                            display: 'inline-block',
                          }}>Withdrawn</span>
                        ) : isPending ? (
                          <span style={{
                            fontFamily: 'var(--font-mono)', fontSize: '11px', fontWeight: 600,
                            color: 'rgba(255,255,255,0.5)',
                            backgroundColor: 'rgba(255,255,255,0.06)',
                            border: '1px solid rgba(255,255,255,0.08)',
                            padding: '4px 10px', borderRadius: '20px',
                            display: 'inline-block',
                          }}>Pending</span>
                        ) : (
                        <div style={{
                          fontFamily: 'var(--font-mono)', fontSize: '13px', fontWeight: 500,
                          color: pick.result === 'win' ? 'var(--green-profit)'
                            : pick.result === 'loss' ? 'var(--red-loss)'
                            : 'var(--text-tertiary)',
                        }}>
                          {(() => {
                            const units = pick.profit_units != null ? pick.profit_units : (pick.pnl != null ? pick.pnl / 100 : null);
                            if (pick.result === 'win') return `+${units != null ? Math.abs(units).toFixed(2) : '0.91'}u`;
                            if (pick.result === 'loss') return `-${units != null ? Math.abs(units).toFixed(2) : '1.00'}u`;
                            return '';
                          })()}
                        </div>
                        )}
                        </>
                      )}
                      {isPro && pick.edge_pct && (
                        <div style={{
                          fontSize: '10px', color: 'rgba(255,255,255,0.45)', marginTop: '2px',
                          fontFamily: 'var(--font-mono)',
                        }}>{pick.edge_pct}% edge</div>
                      )}
                    </div>
                    {canView && (
                      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="var(--text-tertiary)" strokeWidth="2">
                        <polyline points="9 18 15 12 9 6"/>
                      </svg>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
          {isTruncated && (
            <button onClick={() => setShowAllPicks(true)} style={{
              width: '100%', padding: '14px', marginTop: '8px',
              backgroundColor: 'var(--surface-1)', borderRadius: '12px',
              border: '1px solid var(--stroke-subtle)',
              color: 'var(--blue-primary)', fontSize: '13px', fontWeight: 600,
              fontFamily: 'var(--font-sans)', cursor: 'pointer',
              letterSpacing: '0.01em',
            }}>Show all {filtered.length} picks</button>
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


function RevokedPassCard({ pick, onViewDetails }) {
  return (
    <div
      onClick={onViewDetails}
      style={{
        backgroundColor: 'rgba(99,102,241,0.06)',
        borderRadius: '20px',
        border: '1px solid rgba(99,102,241,0.18)',
        padding: '24px',
        marginBottom: '16px',
        cursor: 'pointer',
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '14px' }}>
        <div style={{
          width: '44px', height: '44px', borderRadius: '50%',
          backgroundColor: 'rgba(99,102,241,0.1)',
          border: '2px solid rgba(99,102,241,0.5)',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          flexShrink: 0,
        }}>
          <svg viewBox="0 0 24 24" width="20" height="20" stroke="rgba(99,102,241,0.7)" fill="none" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
            <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>
          </svg>
        </div>
        <div style={{ flex: 1 }}>
          <div style={{
            fontFamily: 'var(--font-mono)', fontSize: '11px', fontWeight: 600,
            letterSpacing: '1.5px', textTransform: 'uppercase',
            color: 'rgba(99,102,241,0.8)', marginBottom: '4px',
          }}>Withdrawn</div>
          <div style={{
            fontFamily: 'var(--font-serif)', fontSize: '18px', fontWeight: 600,
            color: 'var(--text-primary)',
          }}>
            {pick.side && pick.line != null && pick.side.includes(String(Math.abs(pick.line)))
              ? pick.side
              : `${pick.side} ${pick.line > 0 ? '+' : ''}${pick.line}`}
          </div>
        </div>
        <div style={{
          fontFamily: 'var(--font-mono)', fontSize: '22px', fontWeight: 700,
          color: 'rgba(99,102,241,0.6)',
        }}>0u</div>
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
        {pick.edge_pct ? `${pick.edge_pct}% edge at entry · ` : ''}Pulled pre-tip
      </div>

      <div style={{
        display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '6px',
        marginTop: '16px', paddingTop: '14px',
        borderTop: '1px solid rgba(99,102,241,0.12)',
      }}>
        <span style={{
          fontFamily: 'var(--font-mono)', fontSize: '11px', fontWeight: 600,
          letterSpacing: '1px', textTransform: 'uppercase',
          color: 'rgba(99,102,241,0.6)',
        }}>View details</span>
        <svg viewBox="0 0 24 24" width="14" height="14" stroke="rgba(99,102,241,0.5)" fill="none" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <polyline points="9 18 15 12 9 6"/>
        </svg>
      </div>
    </div>
  );
}

function BreakCard({ data }) {
  const isAllStar = data?.type === 'allstar_break';
  const title = isAllStar ? 'All-Star Break' : 'No Games Today';
  const subtitle = isAllStar
    ? 'The NBA All-Star break is underway. No regular season games are scheduled.'
    : data?.message || 'No NBA games scheduled today. The model will resume when games return.';
  const resumeDate = data?.resume_date;

  return (
    <div style={{
      background: 'linear-gradient(135deg, var(--surface-1) 0%, rgba(30,35,50,1) 100%)',
      borderRadius: '16px', border: '1px solid var(--stroke-subtle)',
      padding: '36px 24px', textAlign: 'center', marginBottom: '16px',
    }}>
      <div style={{
        width: '72px', height: '72px', borderRadius: '50%',
        background: 'linear-gradient(135deg, rgba(99,102,241,0.15), rgba(99,102,241,0.05))',
        border: '1px solid rgba(99,102,241,0.2)',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        margin: '0 auto 20px',
      }}>
        <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="rgba(99,102,241,0.7)" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
          <path d="M12 2L15.09 8.26L22 9.27L17 14.14L18.18 21.02L12 17.77L5.82 21.02L7 14.14L2 9.27L8.91 8.26L12 2Z"/>
        </svg>
      </div>
      <h2 style={{
        fontFamily: 'var(--font-sans)', fontSize: '22px', fontWeight: 700,
        color: 'var(--text-primary)', marginBottom: '10px',
      }}>{title}</h2>
      <p style={{
        fontSize: '14px', color: 'var(--text-secondary)', lineHeight: '1.7',
        maxWidth: '320px', margin: '0 auto 20px',
      }}>{subtitle}</p>
      {resumeDate && (
        <div style={{
          display: 'inline-flex', alignItems: 'center', gap: '8px',
          padding: '8px 16px', borderRadius: '10px',
          backgroundColor: 'rgba(99,102,241,0.08)', border: '1px solid rgba(99,102,241,0.15)',
        }}>
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="rgba(99,102,241,0.6)" strokeWidth="2">
            <rect x="3" y="4" width="18" height="18" rx="2" ry="2"/>
            <line x1="16" y1="2" x2="16" y2="6"/>
            <line x1="8" y1="2" x2="8" y2="6"/>
            <line x1="3" y1="10" x2="21" y2="10"/>
          </svg>
          <span style={{
            fontFamily: 'var(--font-mono)', fontSize: '12px', fontWeight: 600,
            color: 'rgba(99,102,241,0.8)', letterSpacing: '0.5px',
          }}>Resumes {new Date(resumeDate + 'T12:00:00').toLocaleDateString('en-US', { weekday: 'long', month: 'short', day: 'numeric' })}</span>
        </div>
      )}
      <div style={{
        marginTop: '24px', padding: '16px', borderRadius: '12px',
        backgroundColor: 'rgba(255,255,255,0.02)', border: '1px solid var(--stroke-subtle)',
      }}>
        <p style={{
          fontSize: '12px', color: 'var(--text-tertiary)', lineHeight: '1.6',
          fontFamily: 'var(--font-sans)', margin: 0,
        }}>
          {isAllStar
            ? 'Discipline means knowing when not to play. Enjoy the break — the model will be ready when regular season action resumes.'
            : 'No action required. The model automatically resumes analysis when games are scheduled.'}
        </p>
      </div>
    </div>
  );
}

function DailyBrief({ stats }) {
  return (
    <div style={{ textAlign: 'center', padding: '40px 0 24px' }}>
      <div style={{
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        gap: '6px', margin: '0 auto 24px',
      }}>
        <div style={{ width: '4px', height: '28px', borderRadius: '2px', backgroundColor: 'var(--text-secondary)', opacity: 0.5 }} />
        <div style={{ width: '4px', height: '28px', borderRadius: '2px', backgroundColor: 'var(--text-secondary)', opacity: 0.5 }} />
      </div>
      <h2 style={{
        fontFamily: 'var(--font-serif)', fontSize: '20px', fontWeight: 600,
        color: 'var(--text-primary)', marginBottom: '8px',
      }}>Waiting for model</h2>
      <p style={{
        fontSize: '14px', color: 'var(--text-secondary)', lineHeight: '1.6',
        maxWidth: '300px', margin: '0 auto',
      }}>
        The system has not processed today's data yet. Signals will update as games are analyzed.
      </p>
      {stats && (
        <div style={{
          marginTop: '24px', display: 'flex', justifyContent: 'center', gap: '24px',
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
        fontFamily: 'var(--font-mono)', fontSize: '18px', fontWeight: 600,
        color: 'var(--text-primary)',
      }}>{value}</div>
      <div style={{
        fontSize: '11px', color: 'var(--text-tertiary)', marginTop: '2px',
        textTransform: 'uppercase', letterSpacing: '0.05em',
      }}>{label}</div>
    </div>
  );
}

function RecordStrip({ stats }) {
  return (
    <div style={{
      backgroundColor: 'rgba(18,23,37,0.85)', borderRadius: '8px',
      padding: '16px 20px', marginTop: '16px',
      border: '1px solid var(--stroke-subtle)',
      display: 'flex', justifyContent: 'space-between', alignItems: 'center',
    }}>
      <div style={{ display: 'flex', gap: '16px', flexWrap: 'wrap', alignItems: 'center' }}>
        <MiniStat label="Win Rate" value={stats.win_rate != null ? `${stats.win_rate}%` : '--'} />
        <MiniStat label="ROI" value={stats.roi != null ? `${stats.roi >= 0 ? '+' : ''}${stats.roi}%` : '--'} />
        <MiniStat label="Picks" value={stats.total_picks} />
        <MiniStat label="Passes" value={stats.total_passes} />
        <MiniStat label="Selectivity" value={`${stats.selectivity}%`} />
      </div>
      <div style={{
        fontFamily: 'var(--font-mono)', fontSize: '13px', fontWeight: 600,
        color: stats.pnl >= 0 ? 'var(--green-profit)' : 'var(--red-loss)',
      }}>
        {stats.pnl >= 0 ? '+' : ''}{Number(stats.pnl).toFixed(2)}u
      </div>
    </div>
  );
}

function MiniStat({ label, value }) {
  return (
    <div>
      <div style={{
        fontFamily: 'var(--font-mono)', fontSize: '14px', fontWeight: 600,
        color: 'var(--text-primary)',
      }}>{value}</div>
      <div style={{
        fontSize: '10px', color: 'var(--text-tertiary)',
        textTransform: 'uppercase', letterSpacing: '0.05em',
      }}>{label}</div>
    </div>
  );
}

function ResolvedPickBanner({ pick, onViewDetails, onDismiss }) {
  const isWin = pick.result === 'win';
  const isPush = pick.result === 'push';
  const profitDisplay = pick.profit_units != null
    ? `${pick.profit_units >= 0 ? '+' : ''}${pick.profit_units}u`
    : isPush ? '0u' : isWin ? '+0.91u' : '-1.0u';

  const scoreDisplay = (pick.home_score != null && pick.away_score != null)
    ? `${pick.away_team} ${pick.away_score}, ${pick.home_team} ${pick.home_score}`
    : null;

  return (
    <div
      onClick={onViewDetails}
      style={{
        backgroundColor: 'var(--surface-1)',
        borderRadius: '20px',
        border: '1px solid var(--stroke-subtle)',
        padding: '24px',
        marginBottom: '16px',
        cursor: 'pointer',
        position: 'relative',
      }}
    >
      {onDismiss && (
        <button
          onClick={(e) => { e.stopPropagation(); onDismiss(); }}
          style={{
            position: 'absolute', top: '12px', right: '12px',
            background: 'none', border: 'none', cursor: 'pointer',
            color: 'var(--text-tertiary)', padding: '4px',
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
          fontFamily: 'var(--font-mono)', fontSize: '10px', fontWeight: 600,
          letterSpacing: '1.5px', textTransform: 'uppercase',
          color: 'var(--text-tertiary)', marginBottom: '6px',
        }}>Outcome Resolved</div>
        <div style={{
          fontFamily: 'var(--font-serif)', fontSize: '17px', fontWeight: 600,
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
          color: 'var(--text-secondary)',
          marginBottom: '10px',
        }}>
          Final: {scoreDisplay}
        </div>
      )}

      <div style={{
        fontSize: '13px',
        color: 'var(--text-secondary)', lineHeight: '1.6',
        marginBottom: '16px',
      }}>
        {isPush
          ? "A push changes nothing. The spread landed on the number. The next pick comes when the edge is there."
          : isWin
          ? "A win doesn't change the process. The next pick comes when the edge is there."
          : "A loss doesn't change the process. No revenge bets. The next pick comes when the edge is there."
        }
      </div>

      <div style={{
        display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '6px',
        fontFamily: 'var(--font-sans)', fontSize: '13px', fontWeight: 500,
        color: 'rgba(79,134,247,0.85)',
      }}>
        View full outcome review
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <path d="M5 12h14M12 5l7 7-7 7"/>
        </svg>
      </div>
    </div>
  );
}

function FreePickNotice({ onUpgrade, resolved }) {
  return (
    <div style={{
      backgroundColor: 'var(--surface-1)',
      border: '1px solid var(--stroke-subtle)',
      borderRadius: '16px',
      padding: '32px 24px',
      textAlign: 'center',
    }}>
      <div style={{
        width: '56px', height: '56px', borderRadius: '14px',
        backgroundColor: 'rgba(52,211,153,0.08)',
        border: '1px solid rgba(52,211,153,0.15)',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        margin: '0 auto 20px',
      }}>
        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="var(--green-profit)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <polyline points="20 6 9 17 4 12"/>
        </svg>
      </div>

      <div style={{
        fontFamily: 'var(--font-mono)',
        fontSize: '11px', fontWeight: 700,
        letterSpacing: '1.5px', textTransform: 'uppercase',
        color: 'var(--green-profit)',
        marginBottom: '12px',
      }}>Pick Published Today</div>

      <p style={{
        fontSize: '14px', color: 'var(--text-secondary)',
        lineHeight: '1.6', marginBottom: '24px',
        maxWidth: '280px', margin: '0 auto 24px',
      }}>
        {resolved
          ? "Today's pick has been resolved. Upgrade to see the result, side, and full analysis."
          : "The model found a qualifying edge today. Upgrade to see the full pick, side, and analysis."
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
        Upgrade to See Pick
      </button>

      <p style={{
        fontSize: '12px', color: 'var(--text-tertiary)',
        marginTop: '12px',
      }}>Full access · Cancel anytime</p>
    </div>
  );
}
