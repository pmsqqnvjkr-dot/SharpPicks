import { useState } from 'react';
import { useAuth } from '../../hooks/useAuth';
import { useApi } from '../../hooks/useApi';
import PickCard from './PickCard';
import NoPickCard from './NoPickCard';
import DailyInsightCard from './DailyInsightCard';
import AuthModal from './AuthModal';
import LoadingState from './LoadingState';
import ResolutionScreen from './ResolutionScreen';
import { InlineError } from './ErrorStates';

export default function TodayTab({ onNavigate }) {
  const { user, loading: authLoading } = useAuth();
  const isPro = user && (user.is_premium || user.subscription_status === 'active' || user.subscription_status === 'trial' || user.founding_member);
  const { data: todayData, loading, error } = useApi('/picks/today', { pollInterval: 60000 });
  const { data: stats } = useApi('/public/stats', { pollInterval: 60000 });
  const { data: lastResolved } = useApi('/picks/last-resolved', { skip: !isPro });
  const [showAuth, setShowAuth] = useState(false);
  const [showResolution, setShowResolution] = useState(false);
  const [resolutionPick, setResolutionPick] = useState(null);
  const [dismissedResolutionId, setDismissedResolutionId] = useState(null);

  if (loading || authLoading) {
    return <LoadingState />;
  }

  const isRevoked = todayData?.type === 'pick' && todayData?.result === 'revoked';
  const isResolved = todayData?.type === 'pick' && todayData?.result && todayData.result !== 'pending' && todayData.result !== 'revoked';

  const handleDismissResolution = (pickId) => {
    setDismissedResolutionId(pickId);
  };

  if (showResolution && resolutionPick) {
    return <ResolutionScreen pick={resolutionPick} onBack={() => { setShowResolution(false); setResolutionPick(null); }} />;
  }

  return (
    <div style={{ padding: 0 }}>
      <Header user={user} onAuthClick={() => setShowAuth(true)} />

      <div style={{ padding: '0 20px' }}>
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
            if (user) { if (onNavigate) onNavigate('profile', 'upgrade'); }
            else setShowAuth(true);
          }} />
        )}

        {isRevoked && (
          <RevokedPassCard pick={todayData} onViewDetails={() => { setResolutionPick(todayData); setShowResolution(true); }} />
        )}

        {todayData?.type === 'pick' && !isResolved && !isRevoked && isPro && (
          <PickCard pick={todayData} isPro={isPro} onUpgrade={() => setShowAuth(true)} onTrack={() => {
            if (onNavigate) onNavigate('profile', 'bets', {
              pickToTrack: {
                id: todayData.id, away_team: todayData.away_team, home_team: todayData.home_team,
                game_date: todayData.game_date, side: todayData.side, line: todayData.line,
                edge_pct: todayData.edge_pct, market_odds: todayData.market_odds,
              }
            });
          }} />
        )}

        {todayData?.type === 'pick' && !isResolved && !isRevoked && !isPro && (
          <FreePickNotice onUpgrade={() => {
            if (user) { if (onNavigate) onNavigate('profile', 'upgrade'); }
            else setShowAuth(true);
          }} />
        )}

        {todayData?.type === 'pass' && <NoPickCard data={todayData} onInsightTap={() => { if (onNavigate) onNavigate('insights'); }} />}
        {todayData?.type === 'off_day' && <OffDayCard />}
        {todayData?.type === 'waiting' && <DailyInsightCard data={todayData} onNavigate={onNavigate} />}

        {error && (
          <InlineError title="Data Feed Interrupted" message="Unable to load today's analysis. Retrying automatically." />
        )}

        {!todayData && !error && <DailyBrief stats={stats} />}
        {stats && <RecordStrip stats={stats} />}
      </div>

      {showAuth && <AuthModal onClose={() => setShowAuth(false)} />}
    </div>
  );
}

function Header({ user, onAuthClick }) {
  return (
    <div style={{
      padding: 'var(--space-md) 20px',
      display: 'flex', justifyContent: 'space-between', alignItems: 'center',
    }}>
      <div style={{ display: 'flex', alignItems: 'center' }}>
        <img src="/wordmark-white.png" alt="SharpPicks" style={{ height: 30, width: 'auto' }} />
      </div>
      {!user && (
        <button onClick={onAuthClick} style={{
          background: 'none', border: 'none', cursor: 'pointer',
          color: 'var(--text-tertiary)', padding: '4px',
          minWidth: '44px', minHeight: '44px',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
        }}>
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
            <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/>
            <circle cx="12" cy="7" r="4"/>
          </svg>
        </button>
      )}
      {user && (
        <div style={{
          width: '32px', height: '32px', borderRadius: '50%',
          backgroundColor: 'var(--surface-2)', border: '1px solid var(--color-border)',
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
        width: '6px', height: '6px', borderRadius: '50%',
        background: 'var(--text-tertiary)', opacity: 0.5,
        margin: '0 auto 24px',
      }} />
      <div style={{
        fontFamily: 'var(--font-mono)', fontSize: 'var(--text-label-size)', fontWeight: 700,
        letterSpacing: '0.08em', textTransform: 'uppercase',
        color: 'var(--text-secondary)', marginBottom: '12px',
      }}>No Games Scheduled</div>
      <p style={{
        fontSize: 'var(--text-metric)', color: 'var(--text-tertiary)', lineHeight: '1.6',
        maxWidth: '320px', margin: '0 auto var(--space-md)',
      }}>
        No games scheduled. Model resumes analysis when games return.
      </p>
      <div style={{
        display: 'inline-block', padding: 'var(--space-sm) var(--space-md)', borderRadius: '8px',
        backgroundColor: 'rgba(255, 255, 255, 0.04)', border: '1px solid var(--color-border)',
        fontSize: '13px', color: 'var(--text-tertiary)',
        fontFamily: 'var(--font-mono)', letterSpacing: '0.04em',
      }}>
        Rest days are part of the discipline
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
      <div style={{
        fontFamily: 'var(--font-mono)', fontSize: 'var(--text-label-size)', fontWeight: 700,
        letterSpacing: '0.08em', textTransform: 'uppercase',
        color: 'var(--text-secondary)', marginBottom: '10px',
      }}>Market Intelligence Active</div>
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
        fontVariantNumeric: 'tabular-nums', color: 'var(--text-primary)',
      }}>{value}</div>
      <div style={{
        fontSize: '10px', color: 'var(--text-tertiary)', marginTop: '2px',
        textTransform: 'uppercase', letterSpacing: '0.08em', fontWeight: 700,
      }}>{label}</div>
    </div>
  );
}

function RecordStrip({ stats }) {
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
        <div style={{ display: 'flex', gap: 'var(--space-md)', flexWrap: 'wrap', alignItems: 'center' }}>
          <MiniStat label="Win Rate" value={stats.win_rate != null ? `${stats.win_rate}%` : '--'} />
          <MiniStat label="ROI" value={stats.roi != null ? `${stats.roi >= 0 ? '+' : ''}${stats.roi}%` : '--'} highlight={stats.roi >= 0} />
          <MiniStat label="Signals" value={stats.total_picks} />
          <MiniStat label="Passes" value={stats.total_passes} />
        </div>
        <div style={{
          fontFamily: 'var(--font-mono)', fontSize: '15px', fontWeight: 700,
          fontVariantNumeric: 'tabular-nums',
          color: stats.pnl >= 0 ? 'var(--color-signal)' : 'var(--color-loss)',
        }}>
          {stats.pnl >= 0 ? '+' : ''}{Number(stats.pnl).toFixed(1)}u
        </div>
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
        fontSize: '10px', color: 'var(--text-tertiary)',
        textTransform: 'uppercase', letterSpacing: '0.08em', fontWeight: 700,
      }}>{label}</div>
    </div>
  );
}

function RevokedPassCard({ pick, onViewDetails }) {
  return (
    <div onClick={onViewDetails} style={{
      backgroundColor: 'var(--surface-1)',
      borderRadius: '16px',
      border: '1px solid var(--color-border)',
      padding: 'var(--space-lg)',
      marginBottom: 'var(--space-md)',
      cursor: 'pointer',
    }}>
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
          fontVariantNumeric: 'tabular-nums', color: 'var(--text-tertiary)',
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

function ResolvedPickBanner({ pick, onViewDetails, onDismiss }) {
  const isWin = pick.result === 'win';
  const isPush = pick.result === 'push';
  const pnlColor = isPush ? 'var(--text-secondary)' : isWin ? 'var(--color-signal)' : 'var(--color-loss)';
  const profitDisplay = pick.profit_units != null
    ? `${pick.profit_units >= 0 ? '+' : ''}${Number(pick.profit_units).toFixed(1)}u`
    : isPush ? '0.0u' : isWin ? '+0.9u' : '-1.0u';

  const scoreDisplay = (pick.home_score != null && pick.away_score != null)
    ? `${pick.away_team} ${pick.away_score}, ${pick.home_team} ${pick.home_score}`
    : null;

  return (
    <div onClick={onViewDetails} style={{
      backgroundColor: 'var(--surface-1)',
      borderRadius: '16px',
      border: '1px solid var(--color-border)',
      padding: 'var(--space-lg)',
      marginBottom: 'var(--space-md)',
      cursor: 'pointer',
      opacity: 0.85,
      position: 'relative',
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: 'var(--space-md)' }}>
        <div style={{
          width: '44px', height: '44px', borderRadius: '50%',
          backgroundColor: isWin ? 'var(--color-signal-bg)' : isPush ? 'rgba(255,255,255,0.04)' : 'rgba(196,104,107,0.08)',
          border: `1px solid ${isWin ? 'var(--color-signal-border)' : isPush ? 'var(--color-border)' : 'rgba(196,104,107,0.22)'}`,
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          flexShrink: 0,
        }}>
          {isPush ? (
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="var(--text-secondary)" strokeWidth="2.5" strokeLinecap="round">
              <line x1="6" y1="12" x2="18" y2="12"/>
            </svg>
          ) : isWin ? (
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="var(--color-signal)" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
              <polyline points="20 6 9 17 4 12"/>
            </svg>
          ) : (
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="var(--color-loss)" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
              <line x1="18" y1="6" x2="6" y2="18"/>
              <line x1="6" y1="6" x2="18" y2="18"/>
            </svg>
          )}
        </div>
        <div style={{ flex: 1 }}>
          <div style={{
            fontFamily: 'var(--font-mono)', fontSize: 'var(--text-label-size)', fontWeight: 700,
            letterSpacing: '0.08em', textTransform: 'uppercase',
            color: pnlColor, marginBottom: '4px',
          }}>
            {isPush ? 'Outcome: Push' : isWin ? 'Outcome: Win' : 'Outcome: Loss'}
          </div>
          <div style={{
            fontFamily: 'var(--font-sans)', fontSize: 'var(--text-card-title)', fontWeight: 600,
            color: 'var(--text-primary)',
          }}>
            {pick.side} {pick.line > 0 ? `+${pick.line}` : pick.line}
          </div>
        </div>
        <div style={{
          fontFamily: 'var(--font-mono)', fontSize: '22px', fontWeight: 700,
          fontVariantNumeric: 'tabular-nums', color: pnlColor,
        }}>
          {profitDisplay}
        </div>
      </div>

      {scoreDisplay && (
        <div style={{
          fontFamily: 'var(--font-mono)', fontSize: '13px',
          fontVariantNumeric: 'tabular-nums',
          color: 'var(--text-secondary)', marginBottom: '12px',
        }}>
          Final: {scoreDisplay}
        </div>
      )}

      <div style={{
        fontSize: '13px', color: 'var(--text-tertiary)', lineHeight: '1.6',
        marginBottom: 'var(--space-md)',
      }}>
        {isPush
          ? "Push. Spread landed on the number. Next signal when the edge is there."
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

      {onDismiss && (
        <button
          onClick={(e) => { e.stopPropagation(); onDismiss(); }}
          style={{
            display: 'block', margin: '12px auto 0', background: 'none',
            border: 'none', cursor: 'pointer',
            fontFamily: 'var(--font-sans)', fontSize: '12px',
            color: 'var(--text-tertiary)',
            minHeight: '44px', minWidth: '44px',
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
      border: '1px solid var(--color-border)',
      borderRadius: '16px',
      padding: '32px 24px', textAlign: 'center',
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
        fontFamily: 'var(--font-mono)', fontSize: 'var(--text-label-size)', fontWeight: 700,
        letterSpacing: '0.08em', textTransform: 'uppercase',
        color: 'var(--color-signal)', marginBottom: '12px',
      }}>Signal Published</div>

      <p style={{
        fontSize: 'var(--text-metric)', color: 'var(--text-secondary)',
        lineHeight: '1.6', maxWidth: '280px', margin: '0 auto 24px',
      }}>
        {resolved
          ? "Today's signal has been resolved. Upgrade to see the outcome, side, and full analysis."
          : "Edge detected. Upgrade to see the full signal, side, and analysis."
        }
      </p>

      <button onClick={onUpgrade} style={{
        width: '100%', height: '48px', borderRadius: '14px', border: 'none',
        background: 'linear-gradient(135deg, var(--blue-primary), var(--blue-deep))',
        color: 'white', fontFamily: 'var(--font-sans)',
        fontSize: '14px', fontWeight: 700, cursor: 'pointer',
      }}>
        Upgrade to See Signal
      </button>

      <p style={{
        fontSize: 'var(--text-caption)', color: 'var(--text-tertiary)', marginTop: '12px',
      }}>Full access · Cancel anytime</p>
    </div>
  );
}
