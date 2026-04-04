import { useState } from 'react';
import { useAuth } from '../../hooks/useAuth';
import { useApi } from '../../hooks/useApi';
import PickCard from './PickCard';
import NoPickCard from './NoPickCard';
import Wordmark from './Wordmark';
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
  const [dismissedOutcomes, setDismissedOutcomes] = useState(() => {
    try {
      const raw = localStorage.getItem('sp_dismissed_outcomes');
      return new Set(raw ? JSON.parse(raw) : []);
    } catch { return new Set(); }
  });

  if (loading || authLoading) {
    return <LoadingState />;
  }

  const isRevoked = todayData?.type === 'pick' && todayData?.result === 'revoked';
  const isResolved = todayData?.type === 'pick' && todayData?.result && todayData.result !== 'pending' && todayData.result !== 'revoked';

  const handleDismissResolution = (pickId) => {
    setDismissedOutcomes(prev => {
      const next = new Set(prev);
      next.add(pickId);
      const arr = [...next].slice(-50);
      localStorage.setItem('sp_dismissed_outcomes', JSON.stringify(arr));
      return new Set(arr);
    });
  };

  if (showResolution && resolutionPick) {
    return <ResolutionScreen pick={resolutionPick} onBack={() => { setShowResolution(false); setResolutionPick(null); }} />;
  }

  return (
    <div style={{ padding: 0 }}>
      <Header user={user} onAuthClick={() => setShowAuth(true)} />

      <div style={{ padding: '0 20px' }}>
        {lastResolved && lastResolved.id && !isResolved && !dismissedOutcomes.has(lastResolved.id) && (
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
          <PickCard pick={todayData} isPro={isPro} onUpgrade={() => setShowAuth(true)} unitSize={user?.unit_size || 100} onTrack={() => {
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
        <Wordmark size={16} />
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
  const accentColor = isWin ? '#5A9E72' : '#2a3654';
  const dotColor = isWin ? '#5A9E72' : '#616a8a';
  const labelColor = isWin ? '#5A9E72' : '#616a8a';
  const statValColor = isWin ? '#5A9E72' : '#9098b3';

  const profitDisplay = pick.profit_units != null
    ? `${pick.profit_units >= 0 ? '+' : ''}${Number(pick.profit_units).toFixed(1)}u`
    : isPush ? '0.0u' : isWin ? '+0.9u' : '-1.0u';
  const edgePct = pick.edge_pct || '--';
  const modelProb = pick.edge_pct ? `${Math.round(50 + pick.edge_pct)}%` : '--';

  const sideDisplay = pick.side && pick.line != null && pick.side.includes(String(Math.abs(pick.line)))
    ? pick.side
    : `${pick.side} ${pick.line > 0 ? '+' : ''}${pick.line}`;

  const scoreDisplay = (pick.home_score != null && pick.away_score != null)
    ? `Final: ${pick.away_team} ${pick.away_score}, ${pick.home_team} ${pick.home_score}`
    : null;

  const resultLabel = isPush ? 'OUTCOME RESOLVED \u00B7 PUSH' : isWin ? 'OUTCOME RESOLVED \u00B7 WIN' : 'OUTCOME RESOLVED';
  const reviewText = isPush
    ? 'Push. The spread landed on the number. Next signal when the edge is there.'
    : isWin
    ? 'Process unchanged. Next signal when the edge is there.'
    : 'Correct process, wrong outcome. Variance is part of the model.';

  return (
    <div style={{
      background: 'var(--surface-1)',
      border: '1px solid var(--color-border)',
      borderRadius: '12px',
      overflow: 'hidden',
      position: 'relative',
      marginBottom: 'var(--space-md)',
    }}>
      <div style={{ position: 'absolute', top: 0, left: 0, right: 0, height: '3px', borderRadius: '12px 12px 0 0', background: accentColor }} />

      <div style={{ padding: '20px 20px 0', display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <div style={{
          fontFamily: 'var(--font-mono)', fontSize: '9px', letterSpacing: '0.12em',
          textTransform: 'uppercase', display: 'flex', alignItems: 'center', gap: '6px', color: labelColor,
        }}>
          <span style={{ width: 6, height: 6, borderRadius: '50%', background: dotColor, flexShrink: 0 }} />
          {resultLabel}
        </div>
        {onDismiss && (
          <button
            onClick={(e) => { e.stopPropagation(); onDismiss(); }}
            style={{ background: 'none', border: 'none', color: '#4a5274', cursor: 'pointer', fontSize: '16px', padding: '4px', lineHeight: 1 }}
            aria-label="Dismiss"
          >&times;</button>
        )}
      </div>

      <div style={{ fontFamily: 'var(--font-sans)', fontSize: '17px', fontWeight: 600, color: 'var(--text-primary)', padding: '8px 20px 0' }}>
        {sideDisplay}
      </div>

      {scoreDisplay && (
        <div style={{ fontFamily: 'var(--font-mono)', fontSize: '12px', color: '#9098b3', padding: '6px 20px 0', lineHeight: 1.5 }}>
          {scoreDisplay}
        </div>
      )}

      <div style={{ fontFamily: 'var(--font-sans)', fontSize: '13px', color: '#616a8a', padding: '8px 20px 0', lineHeight: 1.55, fontStyle: 'italic' }}>
        {reviewText}
      </div>

      <div style={{ display: 'flex', margin: '16px 20px 0', border: '1px solid var(--color-border)', borderRadius: '8px', overflow: 'hidden' }}>
        {[
          { val: profitDisplay, lbl: 'P&L' },
          { val: typeof edgePct === 'number' ? `${edgePct}%` : edgePct, lbl: 'Edge at Entry' },
          { val: modelProb, lbl: 'Model Prob' },
        ].map((s, i) => (
          <div key={i} style={{
            flex: 1, padding: '10px 12px', textAlign: 'center',
            borderRight: i < 2 ? '1px solid var(--color-border)' : 'none',
          }}>
            <div style={{ fontFamily: 'var(--font-mono)', fontSize: '14px', fontWeight: 500, color: statValColor }}>{s.val}</div>
            <div style={{ fontFamily: 'var(--font-mono)', fontSize: '8px', letterSpacing: '0.1em', textTransform: 'uppercase', color: '#4a5274', marginTop: '2px' }}>{s.lbl}</div>
          </div>
        ))}
      </div>

      <div
        onClick={onViewDetails}
        style={{
          display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '6px',
          padding: '14px 20px', marginTop: '16px',
          borderTop: '1px solid var(--color-border)',
          fontFamily: 'var(--font-mono)', fontSize: '11px', letterSpacing: '0.04em',
          color: '#5A9E72', cursor: 'pointer', transition: 'background 0.15s',
        }}
        onMouseEnter={e => e.currentTarget.style.background = 'rgba(90,158,114,0.10)'}
        onMouseLeave={e => e.currentTarget.style.background = 'transparent'}
      >
        View outcome log &rarr;
      </div>
    </div>
  );
}

function FreePickNotice({ onUpgrade, resolved }) {
  return (
    <div style={{
      backgroundColor: 'var(--surface-1)',
      border: '1px solid var(--color-border)',
      borderRadius: '16px',
      padding: '24px 20px',
    }}>
      <div style={{
        fontFamily: 'var(--font-mono)', fontSize: '10px', fontWeight: 600,
        letterSpacing: '1.5px', textTransform: 'uppercase',
        color: 'var(--color-signal)', marginBottom: '14px',
      }}>QUALIFIED EDGE DETECTED</div>

      <div style={{
        display: 'grid', gridTemplateColumns: '1fr 1fr 1fr 1fr', gap: '1px',
        background: 'rgba(255,255,255,0.06)', borderRadius: '6px', overflow: 'hidden',
        marginBottom: '16px',
      }}>
        {['SIDE', 'LINE', 'EDGE', 'SIZE'].map(label => (
          <div key={label} style={{ background: 'var(--surface-1)', padding: '10px 8px', textAlign: 'center' }}>
            <div style={{ fontFamily: 'var(--font-mono)', fontSize: '8px', letterSpacing: '1px', color: 'var(--text-tertiary)', marginBottom: '6px' }}>{label}</div>
            <div style={{ fontFamily: 'var(--font-mono)', fontSize: '12px', fontWeight: 500, color: '#4a5a6e' }}>[Pro]</div>
          </div>
        ))}
      </div>

      <button onClick={() => window.open('https://sharppicks.ai/#pricing', '_blank')} style={{
        width: '100%', padding: '12px', borderRadius: '6px',
        border: '1.5px solid #5A9E72', background: 'transparent',
        color: '#5A9E72', fontFamily: 'var(--font-mono)',
        fontSize: '12px', fontWeight: 600, letterSpacing: '1px', cursor: 'pointer',
        textAlign: 'center',
      }}>
        View Plans
      </button>

      <div style={{
        textAlign: 'center', marginTop: '8px', fontFamily: 'var(--font-mono)',
        fontSize: '9px', color: 'var(--text-tertiary)',
      }}>Full details at sharppicks.ai</div>
    </div>
  );
}
