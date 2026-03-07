import { useState } from 'react';
import { apiPost, apiDelete } from '../../hooks/useApi';
import ShareButton from './ShareButton';
import { shareCard, signalShareText, resultShareText } from '../../utils/share';

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
        <div style={{ ...label, color: 'var(--color-signal)', marginBottom: 'var(--space-sm)' }}>
          Signal Published
        </div>
        <div style={{
          ...label, fontSize: '11px', color: 'var(--text-secondary)', marginBottom: 'var(--space-xs)',
        }}>
          {pick.away_team} @ {pick.home_team}
        </div>
        <PickMeta gameDate={pick.game_date} startTime={pick.start_time} publishedAt={pick.published_at} />
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
          : 'radial-gradient(900px 520px at 40% 0%, rgba(79,134,247,0.20), transparent 55%), linear-gradient(165deg, rgba(23,36,74,0.88), rgba(17,26,56,0.88))',
        border: isSettled
          ? `1px solid var(--color-border)`
          : '1px solid rgba(79,134,247,0.16)',
        borderLeft: isSettled ? undefined : `3px solid var(--color-signal)`,
        boxShadow: isSettled ? 'none' : 'var(--shadow-signal)',
        overflow: 'hidden',
        opacity: settledOpacity,
      }}>
        <div style={{ padding: 'var(--space-lg) var(--space-md) var(--space-md)' }}>

          {/* ── Status Badge + Share ── */}
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 'var(--space-sm)' }}>
            <span style={{
              display: 'inline-flex', alignItems: 'center', gap: '6px',
              padding: '4px 10px', borderRadius: '999px',
              fontSize: '10px', fontWeight: 800,
              letterSpacing: '0.08em', textTransform: 'uppercase',
              border: `1px solid var(--color-signal-border)`,
              background: 'var(--color-signal-bg)',
              color: 'var(--color-signal)',
            }}>
              <span style={{
                width: '6px', height: '6px', borderRadius: '50%',
                background: 'var(--color-signal)',
                boxShadow: `0 0 6px var(--color-signal-glow)`,
                display: 'inline-block', flexShrink: 0,
                ...((!isSettled && !isRevoked) ? { animation: 'live-pulse 2s ease-in-out infinite' } : {}),
              }} />
              {isSettled ? `Outcome: ${pick.result === 'win' ? 'Win' : pick.result === 'push' ? 'Push' : 'Loss'}` : 'Qualified Signal'}
            </span>
            <ShareButton onShare={() => {
              const cardUrl = isSettled ? `/api/cards/result/${pick.id}` : `/api/cards/signal/${pick.id}`;
              const text = isSettled ? resultShareText(pick) : signalShareText(pick);
              return shareCard({ cardUrl, text });
            }} />
          </div>

          {/* ── PRIMARY: Team + Spread ── */}
          <div style={{
            ...label, fontSize: '11px', color: 'var(--text-secondary)',
            marginBottom: '2px',
          }}>
            {pick.away_team} @ {pick.home_team}
          </div>

          <SignalTimestamp publishedAt={pick.published_at} gameFmt={gameFmt} />

          <div style={{
            marginBottom: 'var(--space-md)',
            display: 'flex', alignItems: 'baseline', gap: '6px', flexWrap: 'wrap',
          }}>
            <span style={{
              fontSize: '30px', fontWeight: 800, lineHeight: 1,
              letterSpacing: '-0.5px', color: 'var(--text-primary)',
            }}>{teamPart}</span>
            {spreadPart && (
              <span style={{
                ...metric, fontSize: 'var(--text-hero)',
                color: 'var(--color-signal)',
              }}>{spreadPart}</span>
            )}
          </div>

          {/* ── EDGE ANALYSIS section ── */}
          <section style={{
            margin: `0 0 var(--space-sm)`,
            padding: 'var(--space-md) var(--space-md) var(--space-sm)',
            borderRadius: '12px',
            border: '1px solid var(--color-border)',
            background: 'rgba(0,0,0,0.18)',
          }}>
            <SectionLabel>Edge Analysis</SectionLabel>
            <div style={{ marginBottom: 'var(--space-sm)' }}>
              <div style={{
                ...metric, fontSize: 'var(--text-hero)', color: 'var(--color-signal)',
                textShadow: `0 0 20px var(--color-signal-glow)`,
              }}>
                {fmtEdge(pick.edge_pct)}
              </div>
              <div style={{
                ...label, fontSize: '9px', color: 'var(--text-tertiary)', marginTop: '3px',
              }}>Calibrated Edge</div>
            </div>

            <div style={divider} />

            <SectionLabel>Model Signal Data</SectionLabel>
            <div style={{
              display: 'flex', alignItems: 'center', gap: 'var(--space-sm)',
            }}>
              <div style={{ flex: 1 }}>
                <span style={{ ...metric, fontSize: 'var(--text-metric)', color: 'var(--text-primary)' }}>
                  {pick.cover_prob ? fmtProb(pick.cover_prob) : pick.model_confidence ? fmtProb(pick.model_confidence) : '--'}
                </span>
                <span style={{ ...label, fontSize: '9px', marginLeft: '5px' }}>Model Prob</span>
              </div>
              <div style={{ width: '1px', height: '16px', background: 'var(--color-border)' }} />
              <div style={{ flex: 1 }}>
                <span style={{ ...metric, fontSize: 'var(--text-metric)', color: 'var(--text-secondary)' }}>
                  {pick.implied_prob ? fmtProb(pick.implied_prob) : '--'}
                </span>
                <span style={{ ...label, fontSize: '9px', marginLeft: '5px' }}>Market Prob</span>
              </div>
            </div>
          </section>

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

          {/* ── LINE DATA section ── */}
          <div style={{
            display: 'flex',
            borderRadius: '12px',
            border: '1px solid var(--color-border)',
            background: 'rgba(0,0,0,0.14)',
            overflow: 'hidden',
            marginBottom: 'var(--space-sm)',
          }}>
            <MetricCell label="Margin" value={fmtMargin(pick.predicted_margin)} />
            <div style={{ width: '1px', background: 'var(--color-border)', margin: '6px 0', flexShrink: 0 }} />
            <MetricCell label="Spread" value={fmtSpread(pick.line)} />
            <div style={{ width: '1px', background: 'var(--color-border)', margin: '6px 0', flexShrink: 0 }} />
            <MetricCell label={pick.best_book || 'Best Price'} value={pick.market_odds || '-110'} />
          </div>

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
              padding: 'var(--space-sm) var(--space-md)', borderRadius: '12px',
              border: '1px solid rgba(142,154,175,0.18)',
              background: 'rgba(142,154,175,0.06)', textAlign: 'center',
            }}>
              <div style={{ ...label, fontSize: '12px', color: 'var(--withdrawn)', marginBottom: '3px' }}>
                Signal Withdrawn
              </div>
              <div style={{ fontSize: '11px', color: 'var(--text-tertiary)', lineHeight: '1.4' }}>
                Edge shifted before tip-off. No action needed.
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

function MetricCell({ label: labelText, value }) {
  return (
    <div style={{ flex: 1, padding: '7px 8px 6px', textAlign: 'center' }}>
      <div style={{
        ...label, fontSize: '8px', marginBottom: '3px',
      }}>{labelText}</div>
      <div style={{
        ...metric, fontSize: '15px', color: 'var(--text-primary)',
        fontVariantNumeric: 'tabular-nums',
      }}>{value}</div>
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

  return (
    <section style={{
      margin: '0 0 var(--space-sm)',
      padding: 'var(--space-sm) var(--space-md)',
      borderRadius: '12px',
      border: '1px solid var(--color-border)',
      background: 'rgba(0,0,0,0.10)',
    }}>
      <div style={{ ...label, marginBottom: 'var(--space-sm)' }}>Edge Tracker</div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-xs)' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between' }}>
          <span style={{ fontSize: 'var(--text-metric)', color: 'var(--text-secondary)' }}>Signal Line</span>
          <span style={{ ...metric, fontSize: 'var(--text-metric)', color: 'var(--text-secondary)' }}>
            {fmtSpread(signalLine)}
          </span>
        </div>
        <div style={{ display: 'flex', justifyContent: 'space-between' }}>
          <span style={{ fontSize: 'var(--text-metric)', color: 'var(--text-secondary)' }}>
            {isSettled ? 'Closing Line' : 'Current Line'}
          </span>
          <span style={{ ...metric, fontSize: 'var(--text-metric)', color: 'var(--text-primary)' }}>
            {fmtSpread(currentLine)}
          </span>
        </div>
        {clvVal != null && (
          <div style={{ display: 'flex', justifyContent: 'space-between' }}>
            <span style={{ fontSize: 'var(--text-metric)', color: 'var(--text-secondary)' }}>CLV</span>
            <span style={{ ...metric, fontSize: 'var(--text-metric)', color: clvColor }}>
              {clvVal > 0 ? '+' : ''}{clvVal.toFixed(1)}
            </span>
          </div>
        )}
      </div>
    </section>
  );
}
