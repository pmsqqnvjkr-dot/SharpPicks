import { useState } from 'react';
import { apiPost, apiDelete } from '../../hooks/useApi';

function fmtTimestamp(isoStr) {
  if (!isoStr) return null;
  try {
    const d = new Date(isoStr);
    if (isNaN(d.getTime())) return null;
    const et = new Date(d.toLocaleString('en-US', { timeZone: 'America/New_York' }));
    const h = et.getHours().toString().padStart(2, '0');
    const m = et.getMinutes().toString().padStart(2, '0');
    const months = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
    const now = new Date();
    const isToday = et.toDateString() === new Date(now.toLocaleString('en-US', { timeZone: 'America/New_York' })).toDateString();
    const datePart = isToday ? 'Today' : `${months[et.getMonth()]} ${et.getDate()}, ${et.getFullYear()}`;
    return `${datePart} · ${h}:${m} EST`;
  } catch { return null; }
}

function fmtGameTime(startTime, gameDate) {
  if (startTime && startTime.includes('T')) {
    try {
      const d = new Date(startTime);
      if (!isNaN(d.getTime())) {
        const et = new Date(d.toLocaleString('en-US', { timeZone: 'America/New_York' }));
        let hours = et.getHours();
        const mins = et.getMinutes().toString().padStart(2, '0');
        const ampm = hours >= 12 ? 'PM' : 'AM';
        hours = hours % 12 || 12;
        const months = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
        return `${months[et.getMonth()]} ${et.getDate()} · ${hours}:${mins} ${ampm} ET`;
      }
    } catch {}
  }
  if (gameDate && typeof gameDate === 'string' && gameDate.match(/^\d{4}-\d{2}-\d{2}/)) {
    const [, m, day] = gameDate.split('-');
    const months = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
    return `${months[parseInt(m)-1]} ${parseInt(day)}`;
  }
  return null;
}

function fmtEdge(val) {
  if (val == null) return '--';
  const n = parseFloat(val);
  return `${n > 0 ? '+' : ''}${n.toFixed(1)}%`;
}

function fmtProb(val) {
  if (val == null) return '--';
  return `${(parseFloat(val) * 100).toFixed(1)}%`;
}

function fmtSpread(val) {
  if (val == null) return '--';
  const n = parseFloat(val);
  if (Number.isInteger(n)) return n > 0 ? `+${n}` : `${n}`;
  return n > 0 ? `+${n.toFixed(1)}` : `${n.toFixed(1)}`;
}

function fmtMargin(val) {
  if (val == null) return '--';
  const n = parseFloat(val);
  return `${n > 0 ? '+' : ''}${n.toFixed(1)}`;
}

const label = {
  fontSize: 'var(--text-label-size)', letterSpacing: '0.08em', textTransform: 'uppercase',
  fontWeight: 700, color: 'var(--text-tertiary)', lineHeight: 1,
};

const metric = {
  fontFamily: 'var(--font-mono)', fontWeight: 700,
  fontVariantNumeric: 'tabular-nums', lineHeight: 1,
};

const divider = {
  height: '1px', background: 'var(--color-border)', margin: 'var(--space-md) 0',
};

function SectionLabel({ children }) {
  return (
    <div style={{ ...label, marginBottom: 'var(--space-sm)' }}>
      {children}
    </div>
  );
}

function edgeBarHeight(edgePct) {
  if (!edgePct) return 20;
  return Math.min(80, Math.max(20, Math.round((parseFloat(edgePct) / 12) * 80)));
}

export default function PickCard({ pick, isPro, onUpgrade, onTrack, onNavigate }) {
  const isLocked = pick.locked && !isPro;
  const [tracking, setTracking] = useState(false);
  const [tracked, setTracked] = useState(pick.already_tracked || false);
  const [trackedBetId, setTrackedBetId] = useState(pick.tracked_bet_id || null);
  const [trackError, setTrackError] = useState(null);
  const [signalsOpen, setSignalsOpen] = useState(false);
  const settled = pick.result && pick.result !== 'pending' && pick.result !== 'revoked';
  const [expanded, setExpanded] = useState(false);

  const handleTrackPick = async () => {
    setTracking(true);
    setTrackError(null);
    try {
      const res = await apiPost('/bets', {
        pick_id: pick.id, bet_amount: 100, odds: pick.market_odds || -110,
      });
      if (res.success) {
        setTracked(true);
        if (res.bet?.id) setTrackedBetId(res.bet.id);
      } else {
        if (res.error?.includes('Already tracking')) setTracked(true);
        else setTrackError(res.error || 'Failed to track');
      }
    } catch (e) {
      if (e?.message?.includes('Already tracking')) setTracked(true);
      else setTrackError('Failed to track');
    } finally { setTracking(false); }
  };

  const handleUntrack = async () => {
    if (!trackedBetId) return;
    setTracking(true);
    try {
      await apiDelete(`/bets/${trackedBetId}`);
      setTracked(false);
      setTrackedBetId(null);
    } catch { setTrackError('Failed to untrack'); }
    finally { setTracking(false); }
  };

  if (isLocked) {
    return (
      <div style={{
        backgroundColor: 'var(--surface-1)',
        border: '1px solid var(--color-border)',
        borderRadius: '14px',
        padding: 'var(--space-md)',
        marginTop: 'var(--space-sm)',
      }}>
        <div style={{
          fontFamily: 'var(--font-mono)', fontSize: '9px', fontWeight: 800,
          letterSpacing: '0.14em', textTransform: 'uppercase',
          color: 'var(--color-signal)', opacity: 0.9, marginBottom: 'var(--space-sm)',
        }}>
          Signal
        </div>
        <div style={{
          fontFamily: 'var(--font-mono)', fontSize: '10px', fontWeight: 600,
          letterSpacing: '0.06em', textTransform: 'uppercase',
          color: 'var(--text-tertiary)', marginBottom: 'var(--space-sm)',
        }}>
          {(pick.sport || 'nba').toUpperCase()} — {pick.away_team} vs {pick.home_team}
        </div>
        <div style={{
          fontSize: '11px', color: 'var(--text-tertiary)', marginBottom: 'var(--space-md)',
        }}>
          {fmtGameTime(pick.start_time, pick.game_date) && `Tip ${fmtGameTime(pick.start_time, pick.game_date)}`}
        </div>
        <div style={{
          background: 'rgba(255,255,255,0.02)',
          border: '1px dashed var(--stroke-muted)',
          borderRadius: '12px',
          padding: '28px 20px', textAlign: 'center', marginBottom: 'var(--space-md)',
        }}>
          <div style={{ fontSize: '20px', marginBottom: '10px', opacity: 0.6 }}>🔒</div>
          <p style={{ fontSize: '13px', color: 'var(--text-tertiary)', lineHeight: '1.5', marginBottom: 'var(--space-md)' }}>
            Side and line locked for Pro members. Upgrade to see the full signal and track outcomes.
          </p>
          <button onClick={onUpgrade} style={{
            width: '100%', height: '48px', borderRadius: '14px', border: 'none',
            background: 'linear-gradient(135deg, var(--blue-primary), var(--blue-deep))',
            color: 'white', fontFamily: 'var(--font-sans)',
            fontSize: '14px', fontWeight: 700, cursor: 'pointer',
            display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '8px',
          }}>
            Upgrade Now
          </button>
        </div>
      </div>
    );
  }

  const isSettled = pick.result && pick.result !== 'pending' && pick.result !== 'revoked';
  const isRevoked = pick.result === 'revoked';
  const settledOpacity = isSettled ? 0.85 : 1;

  const sideStr = pick.side || '';
  const spreadMatch = sideStr.match(/^(.*?)(\s[+-]\d+(\.\d+)?)$/);
  const teamPart = spreadMatch ? spreadMatch[1] : sideStr;
  const spreadPart = spreadMatch ? spreadMatch[2].trim() : '';

  const postedFmt = fmtTimestamp(pick.published_at);
  const gameFmt = fmtGameTime(pick.start_time, pick.game_date);

  return (
    <div style={{ padding: '0 4px' }}>
      <article style={{
        borderRadius: '16px',
        padding: 0,
        background: isSettled
          ? 'var(--surface-1)'
          : 'radial-gradient(900px 520px at 40% 0%, rgba(47,95,214,0.12), transparent 55%), linear-gradient(165deg, rgba(18,28,58,0.92), rgba(14,22,48,0.92))',
        border: isSettled
          ? `1px solid var(--color-border)`
          : '1px solid rgba(47,95,214,0.14)',
        borderTop: isSettled ? undefined : `2px solid var(--color-signal)`,
        boxShadow: isSettled ? 'none' : 'var(--shadow-signal)',
        overflow: 'hidden',
        opacity: settledOpacity,
      }}>
        <div style={{ padding: 'var(--space-lg) var(--space-md) var(--space-md)' }}>

          {/* ── Collapsed header (always visible, clickable) ── */}
          <button
            onClick={() => setExpanded(e => !e)}
            style={{
              width: '100%', background: 'none', border: 'none', padding: 0,
              cursor: 'pointer', textAlign: 'left',
            }}
          >
            {/* SIGNAL tag */}
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 'var(--space-sm)' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <span style={{
                  fontFamily: 'var(--font-mono)', fontSize: '9px', fontWeight: 800,
                  letterSpacing: '0.14em', textTransform: 'uppercase',
                  color: 'var(--color-signal)', opacity: 0.9,
                }}>
                  Signal
                </span>
                {isSettled && (
                  <span style={{
                    ...label, fontSize: '10px', marginBottom: 0,
                    color: pick.result === 'win' ? 'var(--color-signal)' : pick.result === 'push' ? 'var(--text-secondary)' : 'var(--color-loss)',
                  }}>
                    {pick.result === 'win' ? 'Win' : pick.result === 'push' ? 'Push' : 'Loss'}
                  </span>
                )}
              </div>
              <svg
                width="14" height="14" viewBox="0 0 24 24" fill="none"
                stroke="var(--text-tertiary)" strokeWidth="2" strokeLinecap="round"
                style={{ transition: 'transform 0.2s', transform: expanded ? 'rotate(180deg)' : 'rotate(0deg)', flexShrink: 0 }}
              >
                <polyline points="6 9 12 15 18 9" />
              </svg>
            </div>

            {/* League — Matchup */}
            <div style={{
              fontFamily: 'var(--font-mono)', fontSize: '10px', fontWeight: 600,
              letterSpacing: '0.06em', textTransform: 'uppercase',
              color: 'var(--text-tertiary)', marginBottom: '10px',
            }}>
              {(pick.sport || 'nba').toUpperCase()} — {pick.away_team} vs {pick.home_team}
            </div>

            {/* THE PICK (headline) */}
            <div style={{
              marginBottom: expanded ? 'var(--space-md)' : 0,
              padding: '14px 16px',
              borderRadius: '12px',
              background: 'rgba(0,0,0,0.22)',
              border: '1px solid rgba(47,95,214,0.10)',
            }}>
              <div style={{
                fontFamily: 'var(--font-sans)', fontSize: '22px', fontWeight: 700,
                color: 'var(--text-primary)', lineHeight: 1.2,
                display: 'flex', alignItems: 'baseline', gap: '8px',
              }}>
                <span>{teamPart}</span>
                {spreadPart && (
                  <span style={{
                    fontFamily: 'var(--font-mono)', fontSize: '24px', fontWeight: 800,
                    color: '#4F86F7',
                  }}>{spreadPart}</span>
                )}
              </div>
              <div style={{
                display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                marginTop: '8px',
              }}>
                {gameFmt && (
                  <span style={{
                    fontFamily: 'var(--font-mono)', fontSize: '11px', fontWeight: 500,
                    color: 'var(--text-tertiary)',
                  }}>
                    {gameFmt}
                  </span>
                )}
                <span style={{
                  ...metric, fontSize: '18px', lineHeight: 1,
                  color: '#34D399',
                }}>
                  {fmtEdge(pick.edge_pct)}
                </span>
              </div>
            </div>
          </button>

          {/* ── Expanded detail ── */}
          {expanded && (<>

          {/* ── Model vs Market ── */}
          <section style={{
            margin: '0 0 var(--space-md)',
            padding: 'var(--space-md)',
            borderRadius: '12px',
            border: '1px solid var(--color-border)',
            background: 'rgba(0,0,0,0.18)',
          }}>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span style={{ ...label, fontSize: '10px', marginBottom: 0, color: 'var(--text-tertiary)' }}>Market Line</span>
                <span style={{ ...metric, fontSize: '15px', color: 'var(--text-primary)' }}>
                  {pick.market_line != null ? fmtSpread(pick.market_line) : fmtSpread(pick.line)}
                </span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span style={{ ...label, fontSize: '10px', marginBottom: 0, color: 'var(--text-tertiary)' }}>Model Line</span>
                <span style={{ ...metric, fontSize: '15px', color: 'var(--color-signal)' }}>
                  {pick.model_projection != null ? fmtSpread(pick.model_projection) : '--'}
                </span>
              </div>
            </div>
          </section>

          {/* ── Price / Tipoff ── */}
          <div style={{
            display: 'flex', flexDirection: 'column', gap: '6px',
            marginBottom: pick.market_context ? 'var(--space-md)' : 'var(--space-sm)',
            padding: 'var(--space-sm) 0',
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span style={{ ...label, fontSize: '10px', marginBottom: 0, color: 'var(--text-tertiary)' }}>Price</span>
              <span style={{ ...metric, fontSize: '14px', color: 'var(--text-primary)' }}>
                {pick.market_odds != null ? pick.market_odds : '-110'}
              </span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span style={{ ...label, fontSize: '10px', marginBottom: 0, color: 'var(--text-tertiary)' }}>Tipoff</span>
              <span style={{ ...metric, fontSize: '14px', color: 'var(--text-secondary)' }}>
                {gameFmt || '--'}
              </span>
            </div>
          </div>

          {/* ── Market Context (optional) ── */}
          {pick.market_context && (
            <div style={{
              padding: 'var(--space-sm) var(--space-md)',
              borderRadius: '12px',
              border: '1px solid var(--color-border)',
              background: 'rgba(0,0,0,0.10)',
              marginBottom: 'var(--space-sm)',
            }}>
              <div style={{
                ...label, fontSize: '9px', letterSpacing: '0.08em',
                color: 'var(--text-tertiary)', marginBottom: '4px',
              }}>Market Context</div>
              <div style={{
                fontSize: '12px', color: 'var(--text-secondary)', lineHeight: 1.4,
              }}>
                {pick.market_context}
              </div>
            </div>
          )}

          <SignalTimestamp publishedAt={pick.published_at} gameFmt={null} />

          {/* ── EDGE STRENGTH bar ── */}
          {pick.edge_pct != null && (
            <EdgeStrengthBar edge={parseFloat(pick.edge_pct)} />
          )}

          {/* ── EDGE TRACKER ── */}
          {pick.line != null && (
            <EdgeTracker
              signalLine={pick.line}
              currentLine={pick.closing_spread ?? pick.line}
              clv={pick.clv}
              isSettled={isSettled}
            />
          )}

          {/* ── VALUE RANGE ── */}
          {!isSettled && pick.line != null && pick.playable_to != null && Math.abs(pick.playable_to - pick.line) >= 0.5 && (
            <PickValueRange pickLine={pick.line} playableTo={pick.playable_to} />
          )}

          {/* ── WHY THIS GAME (signals) ── */}
          {pick.model_signals && pick.model_signals.length > 0 && (
            <section style={{
              margin: `0 0 var(--space-sm)`,
              borderRadius: '12px',
              border: '1px solid var(--color-border)',
              background: 'rgba(0,0,0,0.10)',
              overflow: 'hidden',
            }}>
              <button
                onClick={() => setSignalsOpen(!signalsOpen)}
                style={{
                  width: '100%', padding: 'var(--space-sm) var(--space-md)',
                  display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                  background: 'none', border: 'none', cursor: 'pointer',
                }}
              >
                <span style={label}>Signal Reasoning</span>
                <span style={{
                  fontSize: '11px', color: 'var(--text-tertiary)',
                  transform: signalsOpen ? 'rotate(180deg)' : 'rotate(0deg)',
                  transition: 'transform 0.15s linear', lineHeight: 1,
                }}>▾</span>
              </button>
              {signalsOpen && (
                <ul style={{
                  margin: 0, padding: '0 var(--space-md) var(--space-sm) 22px',
                  color: 'var(--text-secondary)', lineHeight: '1.4', fontSize: '11px',
                  listStyle: 'none',
                }}>
                  {pick.model_signals.map((s, i) => (
                    <li key={i} style={{ margin: '3px 0', position: 'relative', paddingLeft: '2px' }}>
                      <span style={{ position: 'absolute', left: '-13px', color: 'var(--color-signal)', opacity: 0.5 }}>›</span>
                      {s}
                    </li>
                  ))}
                </ul>
              )}
            </section>
          )}

          {/* ── Position Size ── */}
          {pick.stake_guidance && (
            <div style={{
              marginBottom: 'var(--space-sm)',
              padding: 'var(--space-sm) var(--space-md)',
              borderRadius: '12px',
              border: '1px solid var(--color-border)',
              background: 'rgba(0,0,0,0.14)',
              display: 'flex', alignItems: 'center', justifyContent: 'space-between',
            }}>
              <div style={label}>Position Size</div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                <div>
                  <span style={{ ...metric, fontSize: 'var(--text-metric)', color: 'var(--text-primary)' }}>
                    {pick.stake_guidance.flat_stake}u
                  </span>
                  <span style={{ ...label, fontSize: '9px', marginLeft: '3px' }}>flat</span>
                </div>
                <div style={{ width: '1px', height: '12px', background: 'var(--color-border)' }} />
                <div>
                  <span style={{ ...metric, fontSize: 'var(--text-metric)', color: 'var(--text-primary)' }}>
                    {pick.stake_guidance.kelly_stake}u
                  </span>
                  <span style={{ ...label, fontSize: '9px', marginLeft: '3px' }}>kelly</span>
                </div>
              </div>
            </div>
          )}

          {/* ── Outcome / Track Action ── */}
          {isRevoked ? (
            <div style={{
              padding: '14px var(--space-md)', borderRadius: '12px',
              border: '1px solid rgba(251,191,36,0.2)',
              background: 'rgba(251,191,36,0.04)',
            }}>
              <div style={{
                display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '6px',
              }}>
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#f59e0b" strokeWidth="2">
                  <path d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z"/>
                  <line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/>
                </svg>
                <span style={{ ...label, fontSize: '11px', color: '#f59e0b', marginBottom: 0, letterSpacing: '0.1em' }}>
                  Signal Invalidated
                </span>
              </div>
              <div style={{
                fontFamily: 'var(--font-mono)', fontSize: '12px',
                color: 'var(--text-secondary)', lineHeight: '1.5', marginBottom: '4px',
              }}>
                {pick.withdraw_reason || 'Edge shifted before tip-off.'}
              </div>
              <div style={{ fontSize: '11px', color: 'var(--text-tertiary)' }}>
                No action needed &mdash; the system is working as designed.
              </div>
            </div>
          ) : isSettled ? (
            <div style={{
              padding: 'var(--space-sm) var(--space-md)', borderRadius: '12px',
              border: `1px solid ${pick.result === 'win' ? 'var(--color-signal-border)' : pick.result === 'push' ? 'var(--color-border)' : 'rgba(196,104,107,0.22)'}`,
              background: pick.result === 'win' ? 'var(--color-signal-bg)' : pick.result === 'push' ? 'rgba(255,255,255,0.03)' : 'rgba(196,104,107,0.08)',
              textAlign: 'center',
            }}>
              <div style={{
                ...metric, fontSize: '15px',
                color: pick.result === 'win' ? 'var(--color-signal)' : pick.result === 'push' ? 'var(--text-secondary)' : 'var(--color-loss)',
              }}>
                {pick.result === 'win' ? `Win ${pick.pnl != null ? `+${pick.pnl}u` : ''}` : pick.result === 'push' ? 'Push · 0.0u' : `Loss ${pick.pnl != null ? `${pick.pnl}u` : ''}`}
              </div>
            </div>
          ) : tracked ? (
            <button onClick={handleUntrack} disabled={tracking} style={{
              width: '100%', borderRadius: '12px', padding: '10px',
              fontWeight: 800, fontSize: '13px', letterSpacing: '0.3px',
              color: 'var(--color-signal)',
              background: 'var(--color-signal-bg)',
              border: `1px solid var(--color-signal-border)`,
              borderLeft: '3px solid var(--color-signal)',
              textAlign: 'center', cursor: 'pointer',
              display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '6px',
            }}>
              <span style={{ fontSize: '12px', lineHeight: 1 }}>✓</span>
              {tracking ? 'Removing...' : 'Tracked'}
            </button>
          ) : (
            <>
              <button onClick={handleTrackPick} disabled={tracking} style={{
                width: '100%', borderRadius: '12px', padding: '10px',
                fontWeight: 800, fontSize: '13px', letterSpacing: '0.3px',
                color: tracking ? 'var(--text-tertiary)' : 'var(--text-primary)',
                background: 'rgba(255,255,255,0.05)',
                border: '1px solid var(--color-border)',
                cursor: tracking ? 'default' : 'pointer',
                opacity: tracking ? 0.7 : 1,
              }}>
                {tracking ? 'Tracking...' : 'Track Outcome'}
              </button>
              {trackError && (
                <div style={{ marginTop: '5px', fontSize: '12px', color: 'var(--color-loss)', textAlign: 'center' }}>
                  {trackError}
                </div>
              )}
            </>
          )}

          {/* ── Footer meta ── */}
          <div style={{
            marginTop: 'var(--space-sm)', paddingTop: 'var(--space-sm)',
            borderTop: '1px solid var(--color-border)',
            fontSize: '10px', fontWeight: 500, fontFamily: 'var(--font-mono)',
            color: 'var(--text-tertiary)', textAlign: 'center',
          }}>
            {pick.posted_time || '2h before tip'} · Best at {pick.best_book || 'DraftKings'}
          </div>

          {pick.disclaimer && (
            <div style={{
              marginTop: '3px', fontSize: '9px', lineHeight: '1.3',
              color: 'var(--text-tertiary)', opacity: 0.5, textAlign: 'center',
            }}>
              {pick.disclaimer}
            </div>
          )}

          </>)}
        </div>
      </article>

      {onNavigate && !pick.result && (
        <button onClick={() => onNavigate('insights')} style={{
          width: '100%', textAlign: 'center', padding: '10px',
          background: 'none', border: 'none', cursor: 'pointer', marginTop: 'var(--space-sm)',
        }}>
          <span style={{ fontSize: '12px', color: 'var(--text-tertiary)' }}>
            {parseFloat(pick.edge_pct) >= 6
              ? 'Why high-edge signals still lose sometimes'
              : 'How qualification filters protect your bankroll'}
          </span>
          <span style={{ color: 'var(--color-info)', marginLeft: '5px', fontSize: '12px' }}>&rarr;</span>
        </button>
      )}
    </div>
  );
}

function SignalTimestamp({ publishedAt, gameFmt }) {
  let timeStr = null;
  let isRecent = false;
  if (publishedAt) {
    try {
      const d = new Date(publishedAt);
      if (!isNaN(d.getTime())) {
        const et = new Date(d.toLocaleString('en-US', { timeZone: 'America/New_York' }));
        let h = et.getHours();
        const m = et.getMinutes().toString().padStart(2, '0');
        const ampm = h >= 12 ? 'PM' : 'AM';
        h = h % 12 || 12;
        timeStr = `${h}:${m} ${ampm} ET`;
        isRecent = (Date.now() - d.getTime()) < 30 * 60 * 1000;
      }
    } catch {}
  }

  return (
    <div style={{
      fontSize: '10px', fontFamily: 'var(--font-mono)', fontWeight: 500,
      color: 'var(--text-tertiary)', marginBottom: 'var(--space-sm)',
      display: 'flex', alignItems: 'center', gap: '6px',
    }}>
      {timeStr && (
        <span style={{
          ...label, fontSize: '10px', marginBottom: 0,
          ...(isRecent ? { animation: 'live-pulse 2s ease-in-out infinite', opacity: 0.8 } : {}),
        }}>Signal Generated</span>
      )}
      {timeStr && <span style={{ color: 'var(--text-secondary)' }}>{timeStr}</span>}
      {gameFmt && timeStr && <span style={{ opacity: 0.3 }}>·</span>}
      {gameFmt && <span>Tip: {gameFmt}</span>}
    </div>
  );
}

function EdgeStrengthBar({ edge }) {
  const maxEdge = 15;
  const widthPct = Math.min(100, (edge / maxEdge) * 100);
  let barColor = 'var(--text-tertiary)';
  if (edge >= 10) barColor = 'var(--color-signal)';
  else if (edge >= 7) barColor = '#4CAF50';

  return (
    <section style={{
      margin: '0 0 var(--space-sm)',
      padding: 'var(--space-sm) var(--space-md)',
      borderRadius: '12px',
      border: '1px solid var(--color-border)',
      background: 'rgba(0,0,0,0.10)',
    }}>
      <div style={{ ...label, marginBottom: 'var(--space-sm)' }}>Edge Strength</div>
      <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-sm)' }}>
        <div style={{
          flex: 1, height: '4px', borderRadius: '2px',
          background: 'var(--color-border)', position: 'relative', overflow: 'hidden',
        }}>
          <div style={{
            position: 'absolute', top: 0, left: 0, height: '100%',
            width: `${widthPct}%`, borderRadius: '2px',
            background: barColor,
          }} />
        </div>
        <span style={{
          ...metric, fontSize: 'var(--text-metric)',
          fontVariantNumeric: 'tabular-nums',
          color: 'var(--text-primary)', whiteSpace: 'nowrap',
        }}>+{edge.toFixed(1)}pp</span>
      </div>
    </section>
  );
}

function EdgeTracker({ signalLine, currentLine, clv, isSettled }) {
  const clvVal = clv != null ? parseFloat(clv) : (currentLine != null && signalLine != null ? parseFloat(signalLine) - parseFloat(currentLine) : null);
  const clvColor = clvVal == null ? 'var(--text-tertiary)'
    : clvVal > 0 ? 'var(--color-signal)'
    : clvVal < 0 ? 'var(--color-loss)'
    : 'var(--text-tertiary)';
  const hasCLV = clvVal != null && isSettled;

  return (
    <section style={{
      margin: '0 0 var(--space-sm)',
      padding: 'var(--space-md)',
      borderRadius: '12px',
      border: hasCLV ? `1px solid ${clvVal > 0 ? 'rgba(52,211,153,0.18)' : clvVal < 0 ? 'rgba(158,122,124,0.18)' : 'var(--color-border)'}` : '1px solid var(--color-border)',
      background: hasCLV ? `${clvVal > 0 ? 'rgba(52,211,153,0.04)' : clvVal < 0 ? 'rgba(158,122,124,0.04)' : 'rgba(0,0,0,0.10)'}` : 'rgba(0,0,0,0.10)',
    }}>
      <div style={{ ...label, marginBottom: '10px' }}>
        {isSettled ? 'Closing Line Value' : 'Line Tracker'}
      </div>

      {hasCLV && (
        <div style={{
          textAlign: 'center', padding: '6px 0 12px',
          borderBottom: '1px solid var(--color-border)', marginBottom: '10px',
        }}>
          <div style={{
            ...metric, fontSize: '32px', color: clvColor,
            lineHeight: 1, marginBottom: '4px',
          }}>
            {clvVal > 0 ? '+' : ''}{clvVal.toFixed(1)}
          </div>
          <div style={{
            ...label, fontSize: '9px', color: 'var(--text-tertiary)', marginBottom: 0,
          }}>
            {clvVal > 0 ? 'Beat the close' : clvVal < 0 ? 'Behind the close' : 'Matched the close'}
          </div>
        </div>
      )}

      <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <span style={{ ...label, fontSize: '9px', marginBottom: 0 }}>Pick Line</span>
          <span style={{ ...metric, fontSize: '15px', color: 'var(--text-secondary)' }}>
            {fmtSpread(signalLine)}
          </span>
        </div>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <span style={{ ...label, fontSize: '9px', marginBottom: 0 }}>
            {isSettled ? 'Closing Line' : 'Current Line'}
          </span>
          <span style={{ ...metric, fontSize: '15px', color: 'var(--text-primary)' }}>
            {fmtSpread(currentLine)}
          </span>
        </div>
        {!hasCLV && clvVal != null && (
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span style={{ ...label, fontSize: '9px', marginBottom: 0 }}>CLV</span>
            <span style={{ ...metric, fontSize: '15px', color: clvColor }}>
              {clvVal > 0 ? '+' : ''}{clvVal.toFixed(1)}
            </span>
          </div>
        )}
      </div>
    </section>
  );
}

function PickValueRange({ pickLine, playableTo }) {
  const range = Math.abs(playableTo - pickLine);
  if (range < 0.5) return null;
  const isUnderdog = pickLine > 0;
  return (
    <section style={{
      borderRadius: '16px', border: '1px solid rgba(79,125,243,0.1)',
      padding: '16px 20px', marginBottom: 'var(--space-md)',
      background: 'rgba(79,125,243,0.03)',
    }}>
      <div style={{
        fontFamily: 'var(--font-mono)', fontSize: '9px', fontWeight: 700,
        letterSpacing: '0.1em', textTransform: 'uppercase',
        color: 'var(--text-tertiary)', marginBottom: '10px',
      }}>Value Range</div>
      <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 8 }}>
        <span style={{
          fontFamily: 'var(--font-mono)', fontSize: '16px', fontWeight: 700,
          color: 'var(--color-signal)',
        }}>{fmtSpread(pickLine)}</span>
        <div style={{
          flex: 1, height: 6, borderRadius: 3,
          background: 'rgba(255,255,255,0.06)', overflow: 'hidden',
        }}>
          <div style={{
            width: '100%', height: '100%', borderRadius: 3,
            background: 'var(--color-signal)',
          }} />
        </div>
        <span style={{
          fontFamily: 'var(--font-mono)', fontSize: '16px', fontWeight: 700,
          color: 'var(--text-tertiary)',
        }}>{fmtSpread(playableTo)}</span>
      </div>
      <div style={{
        fontFamily: 'var(--font-mono)', fontSize: '11px',
        color: 'var(--text-secondary)', lineHeight: 1.4,
      }}>
        Playable {isUnderdog ? 'down' : 'up'} to {fmtSpread(playableTo)} &mdash; edge invalidates beyond this number
      </div>
    </section>
  );
}
