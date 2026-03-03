import { useState, useEffect } from 'react';
import { useAuth } from '../../hooks/useAuth';
import { useApi, apiPost } from '../../hooks/useApi';
import PickCard from './PickCard';
import NoPickCard from './NoPickCard';
import AuthModal from './AuthModal';
import LoadingState from './LoadingState';
import ResolutionScreen from './ResolutionScreen';
import { InlineError } from './ErrorStates';

export default function TodayTab({ onNavigate }) {
  const { user, loading: authLoading } = useAuth();
  const isPro = user && (user.is_premium || user.subscription_status === 'active' || user.subscription_status === 'trial' || user.founding_member);
  const { data: todayData, loading, error } = useApi('/picks/today', { pollInterval: 60000 });
  const { data: stats } = useApi('/public/stats', { pollInterval: 60000 });
  const { data: lastResolved, refetch: refetchResolved } = useApi('/picks/last-resolved', { skip: !isPro });
  const [showAuth, setShowAuth] = useState(false);
  const [showResolution, setShowResolution] = useState(false);
  const [resolutionPick, setResolutionPick] = useState(null);

  if (loading || authLoading) {
    return <LoadingState />;
  }

  const isRevoked = todayData?.type === 'pick' && todayData?.result === 'revoked';
  const isResolved = todayData?.type === 'pick' && todayData?.result && todayData.result !== 'pending' && todayData.result !== 'revoked';

  const handleDismissResolution = async (pickId) => {
    await apiPost('/picks/dismiss-resolution', { pick_id: pickId });
    refetchResolved();
  };

  if (showResolution && resolutionPick) {
    return <ResolutionScreen pick={resolutionPick} onBack={() => { setShowResolution(false); setResolutionPick(null); }} />;
  }

  return (
    <div style={{ padding: '0' }}>
      <Header user={user} onAuthClick={() => setShowAuth(true)} />

      <div style={{ padding: '0 20px' }}>
        {lastResolved && lastResolved.id && !isResolved && (
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
          <PickCard pick={todayData} isPro={isPro} onUpgrade={() => setShowAuth(true)} onTrack={() => {
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
          <NoPickCard data={todayData} />
        )}

        {todayData?.type === 'off_day' && (
          <OffDayCard />
        )}

        {todayData?.type === 'waiting' && (
          <WaitingCard />
        )}

        {error && (
          <InlineError title="Data delay" message="Unable to load today's analysis. This typically resolves within a few minutes." />
        )}

        {!todayData && !error && (
          <DailyBrief stats={stats} />
        )}

        {stats && <RecordStrip stats={stats} />}

        {stats && (
          <div style={{
            textAlign: 'center', marginTop: '8px',
            fontSize: '10px', color: 'var(--text-tertiary)',
            fontFamily: 'var(--font-mono)', letterSpacing: '0.05em',
            textTransform: 'uppercase',
          }}>Algorithm Record</div>
        )}
      </div>

      {showAuth && <AuthModal onClose={() => setShowAuth(false)} />}
    </div>
  );
}

function Header({ user, onAuthClick }) {
  return (
    <div style={{
      padding: '16px 20px',
      display: 'flex',
      justifyContent: 'space-between',
      alignItems: 'center',
    }}>
      <div style={{ display: 'flex', alignItems: 'center' }}>
        <img src="/images/crest.png" alt="" width="26" height="26" style={{ display: 'block', marginRight: '16px', flexShrink: 0, objectFit: 'contain' }} />
        <span style={{
          fontFamily: 'var(--font-sans)',
          fontSize: '13px',
          fontWeight: 600,
          color: '#F2F4F8',
          letterSpacing: '3.9px',
          textTransform: 'uppercase',
          lineHeight: 1,
        }}>SHARP<span style={{ opacity: 0.65, margin: '0 0.45em', fontWeight: 500, letterSpacing: '0.18em' }}>||</span>PICKS</span>
      </div>
      {!user && (
        <button
          onClick={onAuthClick}
          style={{
            background: 'none', border: 'none', cursor: 'pointer',
            color: 'var(--text-tertiary)', padding: '4px',
          }}
        >
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
            <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/>
            <circle cx="12" cy="7" r="4"/>
          </svg>
        </button>
      )}
      {user && (
        <div style={{
          width: '32px', height: '32px', borderRadius: '50%',
          backgroundColor: 'var(--surface-2)', border: '1px solid var(--stroke-subtle)',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          fontSize: '13px', fontWeight: 600, color: 'var(--text-secondary)',
          fontFamily: 'var(--font-sans)',
        }}>
          {user.email ? user.email[0].toUpperCase() : 'U'}
        </div>
      )}
    </div>
  );
}

function OffDayCard() {
  return (
    <div style={{ textAlign: 'center', padding: '40px 0 24px' }}>
      <div style={{
        width: '64px', height: '64px', borderRadius: '16px',
        backgroundColor: 'var(--surface-1)', border: '1px solid var(--stroke-subtle)',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        margin: '0 auto 24px',
      }}>
        <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="var(--text-tertiary)" strokeWidth="1.5">
          <rect x="3" y="4" width="18" height="18" rx="2" ry="2"/>
          <line x1="16" y1="2" x2="16" y2="6"/>
          <line x1="8" y1="2" x2="8" y2="6"/>
          <line x1="3" y1="10" x2="21" y2="10"/>
        </svg>
      </div>
      <h2 style={{
        fontFamily: 'var(--font-sans)', fontSize: '22px', fontWeight: 700,
        color: 'var(--text-primary)', marginBottom: '12px',
      }}>No games today</h2>
      <p style={{
        fontSize: '14px', color: 'var(--text-secondary)', lineHeight: '1.6',
        maxWidth: '320px', margin: '0 auto 16px',
      }}>
        No NBA games are scheduled today. The model will resume analysis when games return to the schedule.
      </p>
      <div style={{
        display: 'inline-block', padding: '8px 16px', borderRadius: '8px',
        backgroundColor: 'rgba(255, 255, 255, 0.04)', border: '1px solid var(--stroke-subtle)',
        fontSize: '13px', color: 'var(--text-tertiary)',
      }}>
        Rest days are part of the discipline
      </div>
    </div>
  );
}

function WaitingCard() {
  return (
    <div style={{ textAlign: 'center', padding: '40px 0 24px' }}>
      <div style={{
        width: '64px', height: '64px', borderRadius: '16px',
        backgroundColor: 'var(--surface-1)', border: '1px solid var(--stroke-subtle)',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        margin: '0 auto 24px',
      }}>
        <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="var(--text-tertiary)" strokeWidth="1.5">
          <circle cx="12" cy="12" r="10"/>
          <polyline points="12 6 12 12 16 14"/>
        </svg>
      </div>
      <h2 style={{
        fontFamily: 'var(--font-sans)', fontSize: '22px', fontWeight: 700,
        color: 'var(--text-primary)', marginBottom: '12px',
      }}>Waiting for model</h2>
      <p style={{
        fontSize: '14px', color: 'var(--text-secondary)', lineHeight: '1.6',
        maxWidth: '300px', margin: '0 auto',
      }}>
        The model has not run yet today. Games will be analyzed as data becomes available.
      </p>
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
      backgroundColor: 'var(--surface-1)', borderRadius: '12px',
      padding: '16px 20px', marginTop: '16px',
      border: '1px solid var(--stroke-subtle)',
      display: 'flex', justifyContent: 'space-between', alignItems: 'center',
    }}>
      <div style={{ display: 'flex', gap: '20px' }}>
        <MiniStat label="Picks" value={stats.total_picks} />
        <MiniStat label="Passes" value={stats.total_passes} />
        <MiniStat label="Select." value={`${stats.selectivity}%`} />
      </div>
      <div style={{
        fontFamily: 'var(--font-mono)', fontSize: '13px',
        color: stats.pnl >= 0 ? 'var(--green-profit)' : 'var(--red-loss)',
      }}>
        {stats.pnl >= 0 ? '+' : ''}{stats.pnl}u
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

function ResolvedPickBanner({ pick, onViewDetails, onDismiss }) {
  const isWin = pick.result === 'win';
  const isPush = pick.result === 'push';
  const accentColor = isPush ? 'var(--text-secondary)' : isWin ? 'var(--green-profit)' : 'var(--red-loss)';
  const accentBg = isPush ? 'rgba(255,255,255,0.04)' : isWin ? 'rgba(52,211,153,0.06)' : 'rgba(239,68,68,0.06)';
  const accentBorder = isPush ? 'rgba(255,255,255,0.1)' : isWin ? 'rgba(52,211,153,0.18)' : 'rgba(239,68,68,0.18)';
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
        backgroundColor: accentBg,
        borderRadius: '20px',
        border: `1px solid ${accentBorder}`,
        padding: '24px',
        marginBottom: '16px',
        cursor: 'pointer',
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '16px' }}>
        <div style={{
          width: '44px', height: '44px', borderRadius: '50%',
          backgroundColor: isWin ? 'rgba(52,211,153,0.12)' : 'rgba(239,68,68,0.12)',
          border: `2px solid ${accentColor}`,
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          flexShrink: 0,
        }}>
          {isPush ? (
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke={accentColor} strokeWidth="2.5" strokeLinecap="round">
              <line x1="6" y1="12" x2="18" y2="12"/>
            </svg>
          ) : isWin ? (
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke={accentColor} strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
              <polyline points="20 6 9 17 4 12"/>
            </svg>
          ) : (
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke={accentColor} strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
              <line x1="18" y1="6" x2="6" y2="18"/>
              <line x1="6" y1="6" x2="18" y2="18"/>
            </svg>
          )}
        </div>
        <div style={{ flex: 1 }}>
          <div style={{
            fontFamily: 'var(--font-mono)', fontSize: '11px', fontWeight: 600,
            letterSpacing: '1.5px', textTransform: 'uppercase',
            color: accentColor, marginBottom: '4px',
          }}>
            {isPush ? 'Outcome: Push' : isWin ? 'Outcome: Win' : 'Outcome: Loss'}
          </div>
          <div style={{
            fontFamily: 'var(--font-serif)', fontSize: '18px', fontWeight: 600,
            color: 'var(--text-primary)',
          }}>
            {pick.side} {pick.line > 0 ? `+${pick.line}` : pick.line}
          </div>
        </div>
        <div style={{
          fontFamily: 'var(--font-mono)', fontSize: '22px', fontWeight: 700,
          color: accentColor,
        }}>
          {profitDisplay}
        </div>
      </div>

      {scoreDisplay && (
        <div style={{
          fontFamily: 'var(--font-mono)', fontSize: '13px',
          color: 'var(--text-secondary)',
          marginBottom: '12px',
        }}>
          Final: {scoreDisplay}
        </div>
      )}

      <div style={{
        fontFamily: 'var(--font-serif)', fontStyle: 'italic', fontSize: '13px',
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
        color: accentColor,
      }}>
        View full outcome review
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <path d="M5 12h14M12 5l7 7-7 7"/>
        </svg>
      </div>

      {onDismiss && (
        <button
          onClick={(e) => { e.stopPropagation(); onDismiss(); }}
          style={{
            display: 'block', margin: '12px auto 0', background: 'none',
            border: 'none', cursor: 'pointer',
            fontFamily: 'var(--font-sans)', fontSize: '12px',
            color: 'var(--text-tertiary)',
          }}
        >
          Dismiss
        </button>
      )}
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
