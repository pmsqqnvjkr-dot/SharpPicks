import { useState, useRef, useEffect } from 'react';
import { useAuth } from '../../hooks/useAuth';
import { useApi } from '../../hooks/useApi';
import PickCard from './PickCard';
import NoPickCard from './NoPickCard';
import AuthModal from './AuthModal';
import LoadingState from './LoadingState';
import ResolutionScreen from './ResolutionScreen';
import { InlineError } from './ErrorStates';

export default function PicksTab({ onNavigate }) {
  const { user, loading: authLoading } = useAuth();
  const { data: todayData, loading, error } = useApi('/picks/today');
  const { data: stats } = useApi('/public/stats');
  const { data: historyData, loading: historyLoading } = useApi('/public/record');
  const [showAuth, setShowAuth] = useState(false);
  const [showResolution, setShowResolution] = useState(false);
  const [resolutionPick, setResolutionPick] = useState(null);
  const [filter, setFilter] = useState('all');

  const isPro = user && (user.is_premium || user.subscription_status === 'active' || user.subscription_status === 'trial');

  if (loading || authLoading) {
    return <LoadingState />;
  }

  const isResolved = todayData?.type === 'pick' && todayData?.result && todayData.result !== 'pending';

  if (showResolution && resolutionPick) {
    return <ResolutionScreen pick={resolutionPick} onBack={() => { setShowResolution(false); setResolutionPick(null); }} />;
  }

  const picks = historyData?.picks || [];
  const filtered = filter === 'all' ? picks
    : filter === 'wins' ? picks.filter(p => p.result === 'win')
    : filter === 'losses' ? picks.filter(p => p.result === 'loss')
    : picks.filter(p => p.result === 'pending');

  return (
    <div style={{ padding: '0' }}>
      <Header user={user} onAuthClick={() => setShowAuth(true)} onNavigate={onNavigate} />

      <div style={{ padding: '0 20px' }}>
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

        {todayData?.type === 'pick' && !isResolved && isPro && (
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
              }
            });
          }} />
        )}

        {todayData?.type === 'pick' && !isResolved && !isPro && (
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
          <WaitingCard />
        )}

        {error && (
          <InlineError title="Data delay" message="Unable to load today's analysis. This typically resolves within a few minutes." />
        )}

        {!todayData && !error && (
          <DailyBrief stats={stats} />
        )}

        {stats && <RecordStrip stats={stats} />}
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
            <button key={f} onClick={() => setFilter(f)} style={{
              padding: '5px 12px', borderRadius: '8px', fontSize: '11px',
              fontWeight: 600, border: 'none', cursor: 'pointer',
              textTransform: 'capitalize', fontFamily: 'var(--font-sans)',
              backgroundColor: filter === f ? 'var(--blue-primary)' : 'var(--surface-2)',
              color: filter === f ? '#fff' : 'var(--text-secondary)',
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
          }}>No picks found</div>
        ) : (
          <div style={{
            backgroundColor: 'var(--surface-1)', borderRadius: '16px',
            overflow: 'hidden', border: '1px solid var(--stroke-subtle)',
          }}>
            {filtered.map((pick, i) => {
              const pickResolved = pick.result === 'win' || pick.result === 'loss';
              const isPending = pick.result === 'pending';
              const hideLine = !isPro && isPending;
              const canView = isPro && pickResolved;
              return (
                <div key={pick.id} onClick={() => canView && (() => { setResolutionPick(pick); setShowResolution(true); })()} style={{
                  padding: '14px 20px',
                  borderBottom: i < filtered.length - 1 ? '1px solid var(--stroke-subtle)' : 'none',
                  display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                  cursor: canView ? 'pointer' : 'default',
                }}>
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
                    }}>{pick.game_date}</div>
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <div style={{ textAlign: 'right' }}>
                      {hideLine ? (
                        <div style={{
                          fontFamily: 'var(--font-mono)', fontSize: '12px', fontWeight: 600,
                          color: 'var(--text-tertiary)',
                        }}>Pending</div>
                      ) : (
                        <div style={{
                          fontFamily: 'var(--font-mono)', fontSize: '13px', fontWeight: 600,
                          color: pick.result === 'win' ? 'var(--green-profit)'
                            : pick.result === 'loss' ? 'var(--red-loss)' : 'var(--text-tertiary)',
                        }}>
                          {pick.result === 'win' ? `+${pick.pnl != null ? pick.pnl : 91}u`
                            : pick.result === 'loss' ? `${pick.pnl != null ? pick.pnl : -100}u`
                            : 'Pending'}
                        </div>
                      )}
                      {isPro && pick.edge_pct && (
                        <div style={{
                          fontSize: '11px', color: 'var(--text-tertiary)', marginTop: '2px',
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
        )}
      </div>

      {showAuth && <AuthModal onClose={() => setShowAuth(false)} />}
    </div>
  );
}

function Header({ user, onAuthClick, onNavigate }) {
  const [menuOpen, setMenuOpen] = useState(false);
  const menuRef = useRef(null);
  const { logout } = useAuth();

  useEffect(() => {
    if (!menuOpen) return;
    const handleClick = (e) => {
      if (menuRef.current && !menuRef.current.contains(e.target)) setMenuOpen(false);
    };
    document.addEventListener('mousedown', handleClick);
    return () => document.removeEventListener('mousedown', handleClick);
  }, [menuOpen]);

  const greeting = (() => {
    if (!user?.first_name) return null;
    const h = new Date().toLocaleString('en-US', { hour: 'numeric', hour12: false, timeZone: 'America/New_York' });
    const hr = parseInt(h);
    const period = hr < 12 ? 'Good morning' : hr < 17 ? 'Good afternoon' : 'Good evening';
    return `${period}, ${user.first_name}`;
  })();

  const menuItems = [
    { label: 'Performance', icon: 'M3 3v18h18M7 16l4-4 4 4 5-5', action: () => { onNavigate('performance'); setMenuOpen(false); } },
    { label: 'Journal', icon: 'M4 19.5A2.5 2.5 0 016.5 17H20M4 19.5V5a2 2 0 012-2h14v14H6.5A2.5 2.5 0 004 19.5z', action: () => { onNavigate('insights'); setMenuOpen(false); } },
    { label: 'Profile', icon: 'M20 21v-2a4 4 0 00-4-4H8a4 4 0 00-4 4v2M12 3a4 4 0 100 8 4 4 0 000-8z', action: () => { onNavigate('profile'); setMenuOpen(false); } },
    { type: 'divider' },
    { label: 'Sign Out', icon: 'M9 21H5a2 2 0 01-2-2V5a2 2 0 012-2h4M16 17l5-5-5-5M21 12H9', action: () => { logout(); setMenuOpen(false); }, danger: true },
  ];

  return (
    <div style={{
      padding: '16px 20px',
      display: 'flex',
      justifyContent: 'space-between',
      alignItems: 'center',
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
          fontFamily: 'var(--font-sans)',
          fontSize: '13px',
          fontWeight: 700,
          color: 'var(--text-primary)',
          letterSpacing: '2px',
          textTransform: 'uppercase',
        }}>Sharp Picks</span>
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
        <div style={{ position: 'relative' }} ref={menuRef}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            {greeting && (
              <span style={{
                fontSize: '13px', color: 'var(--text-secondary)',
                fontFamily: 'var(--font-sans)',
              }}>
                {greeting}
              </span>
            )}
            <button
              onClick={() => setMenuOpen(!menuOpen)}
              style={{
                background: 'none', border: 'none', cursor: 'pointer',
                padding: '6px', display: 'flex', alignItems: 'center',
                justifyContent: 'center',
              }}
            >
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="var(--text-secondary)" strokeWidth="2" strokeLinecap="round">
                <line x1="3" y1="6" x2="21" y2="6"/>
                <line x1="3" y1="12" x2="21" y2="12"/>
                <line x1="3" y1="18" x2="21" y2="18"/>
              </svg>
            </button>
          </div>

          {menuOpen && (
            <div style={{
              position: 'absolute',
              top: '100%',
              right: 0,
              marginTop: '8px',
              backgroundColor: 'var(--surface-1)',
              border: '1px solid var(--stroke-subtle)',
              borderRadius: '12px',
              padding: '6px',
              minWidth: '180px',
              zIndex: 50,
              boxShadow: '0 8px 32px rgba(0,0,0,0.4)',
            }}>
              {menuItems.map((item, i) =>
                item.type === 'divider' ? (
                  <div key={i} style={{ height: '1px', backgroundColor: 'var(--stroke-muted)', margin: '4px 8px' }} />
                ) : (
                  <button
                    key={i}
                    onClick={item.action}
                    style={{
                      display: 'flex', alignItems: 'center', gap: '10px',
                      width: '100%', padding: '10px 12px',
                      background: 'none', border: 'none', cursor: 'pointer',
                      borderRadius: '8px',
                      color: item.danger ? 'var(--red-loss)' : 'var(--text-secondary)',
                      fontSize: '14px', fontFamily: 'var(--font-sans)',
                      textAlign: 'left',
                    }}
                    onMouseEnter={e => e.currentTarget.style.backgroundColor = 'var(--surface-2)'}
                    onMouseLeave={e => e.currentTarget.style.backgroundColor = 'transparent'}
                  >
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                      <path d={item.icon}/>
                    </svg>
                    {item.label}
                  </button>
                )
              )}
            </div>
          )}
        </div>
      )}
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
        width: '64px', height: '64px', borderRadius: '16px',
        backgroundColor: 'var(--surface-1)', border: '1px solid var(--stroke-subtle)',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        margin: '0 auto 24px',
      }}>
        <svg viewBox="0 0 40 40" width="36" height="36" fill="none">
          <path d="M20 4L6 10v10c0 9.2 6 17.4 14 20 8-2.6 14-10.8 14-20V10L20 4z" stroke="white" strokeWidth="1.8" fill="none"/>
          <rect x="12" y="24" width="3" height="6" rx="1" fill="rgba(255,255,255,0.3)"/>
          <rect x="17" y="20" width="3" height="10" rx="1" fill="rgba(255,255,255,0.4)"/>
          <rect x="22" y="22" width="3" height="8" rx="1" fill="rgba(255,255,255,0.35)"/>
          <path d="M11 22L17 16L22 19L30 11" stroke="white" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"/>
          <path d="M26 11h4v4" stroke="white" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"/>
        </svg>
      </div>
      <h2 style={{
        fontFamily: 'var(--font-sans)', fontSize: '22px', fontWeight: 700,
        color: 'var(--text-primary)', marginBottom: '8px',
      }}>Standing by</h2>
      <p style={{
        fontSize: '14px', color: 'var(--text-secondary)', lineHeight: '1.6',
        maxWidth: '300px', margin: '0 auto',
      }}>
        The model is waiting for today's game data. When games are available, it will analyze all matchups and publish a pick only if the edge exceeds the threshold.
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

function ResolvedPickBanner({ pick, onViewDetails }) {
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
      }}>14-day free trial · Cancel anytime</p>
    </div>
  );
}
