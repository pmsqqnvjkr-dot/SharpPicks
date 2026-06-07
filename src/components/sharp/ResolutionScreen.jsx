import { useEffect, useRef } from 'react';

const C = {
  bg: '#0A0D14', card: '#121725', bdr: 'rgba(255, 255, 255, 0.08)', bdr2: 'rgba(255, 255, 255, 0.12)',
  t1: '#E8EAED', t2: 'rgba(232, 234, 237, 0.7)', t3: 'rgba(232, 234, 237, 0.5)', t4: 'rgba(232, 234, 237, 0.35)',
  grn: '#5A9E72', grnD: 'rgba(90,158,114,.10)', grnB: 'rgba(90,158,114,.15)',
};

export default function ResolutionScreen({ pick, onBack, onNavigate }) {
  const scrollRef = useRef(null);
  useEffect(() => {
    if (scrollRef.current) scrollRef.current.scrollTop = 0;
  }, [pick]);

  const isRevoked = pick?.result === 'revoked';
  const isWin = pick?.result === 'win';
  const isPush = pick?.result === 'push';

  if (isRevoked) {
    return <WithdrawnDetailScreen pick={pick} onBack={onBack} />;
  }

  const profitDisplay = pick?.profit_units != null
    ? `${pick.profit_units >= 0 ? '+' : ''}${Number(pick.profit_units).toFixed(1)}u`
    : '--';
  const hasScore = pick?.home_score != null && pick?.away_score != null;
  const accentColor = isWin ? C.grn : C.bdr2;
  const pnlColor = isPush ? C.t2 : isWin ? C.grn : C.t2;
  const edgePct = pick?.edge_pct || '--';
  const modelProb = pick?.edge_pct ? `${Math.round(50 + pick.edge_pct)}%` : '--';

  const sideDisplay = pick?.side && pick?.line != null && pick.side.includes(String(Math.abs(pick.line)))
    ? pick.side
    : pick?.side && pick?.line != null
    ? `${pick.side} ${pick.line > 0 ? '+' : ''}${pick.line}`
    : pick?.side || '\u2014';

  const oddsDisplay = pick?.market_odds ? ` (${pick.market_odds > 0 ? '+' : ''}${pick.market_odds})` : '';

  const resultBadge = isPush
    ? { text: 'PUSH', dotColor: C.t3, color: C.t2, bg: 'rgba(100,110,130,.1)', border: C.bdr }
    : isWin
    ? { text: 'WIN \u00B7 COVERED', dotColor: C.grn, color: C.grn, bg: C.grnD, border: C.grnB }
    : { text: 'DID NOT COVER', dotColor: C.t3, color: C.t2, bg: 'rgba(100,110,130,.1)', border: C.bdr };

  return (
    <div ref={scrollRef} style={{
      position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
      backgroundColor: C.bg,
      zIndex: 200,
      overflowY: 'auto', WebkitOverflowScrolling: 'touch',
      // Push the sticky header (and the back arrow inside it) below the
      // iOS notch / Dynamic Island. 0px fallback keeps web identical.
      paddingTop: 'env(safe-area-inset-top, 0px)',
    }}>
    <div style={{ maxWidth: '420px', margin: '0 auto', padding: '0 16px', paddingBottom: '100px' }}>
      {/* Header */}
      <div style={{
        position: 'sticky', top: 0, zIndex: 1,
        backgroundColor: C.bg,
        borderBottom: `1px solid ${C.bdr}`,
        padding: '12px 0',
        display: 'flex', alignItems: 'center', gap: '12px',
      }}>
        <button onClick={onBack} aria-label="Go back" style={{
          background: 'none', border: 'none', cursor: 'pointer',
          color: C.t2, fontSize: '20px', padding: '4px',
        }}>&larr;</button>
        <span style={{ fontFamily: "'Inter',-apple-system,sans-serif", fontSize: '18px', fontWeight: 600, color: C.t1 }}>
          Outcome Log
        </span>
      </div>

      {/* Matchup hero card */}
      <div style={{
        background: C.card, border: `1px solid ${C.bdr}`,
        borderRadius: '12px', padding: '24px', textAlign: 'center',
        position: 'relative', overflow: 'hidden', marginTop: '16px',
      }}>
        <div style={{ position: 'absolute', top: 0, left: 0, right: 0, height: '3px', background: accentColor }} />
        <div style={{ fontFamily: "'Inter',-apple-system,sans-serif", fontSize: '16px', fontWeight: 500, color: C.t1, marginBottom: '8px', lineHeight: 1.4 }}>
          {pick?.away_team} @ {pick?.home_team}
        </div>
        {hasScore && (
          <div style={{ fontFamily: "'JetBrains Mono','Menlo',monospace", fontSize: '28px', fontWeight: 700, color: C.t1, letterSpacing: '0.04em', marginBottom: '6px' }}>
            {pick.away_score} <span style={{ color: C.t4, margin: '0 4px' }}>&ndash;</span> {pick.home_score}
          </div>
        )}
        <div style={{ fontFamily: "'JetBrains Mono','Menlo',monospace", fontSize: '12px', color: C.t3 }}>
          {sideDisplay}{oddsDisplay}
        </div>
        <span style={{
          display: 'inline-flex', alignItems: 'center', gap: '5px',
          fontFamily: "'JetBrains Mono','Menlo',monospace", fontSize: '10px', letterSpacing: '0.1em',
          textTransform: 'uppercase', padding: '4px 12px', borderRadius: '6px',
          marginTop: '12px',
          color: resultBadge.color, background: resultBadge.bg, border: `1px solid ${resultBadge.border}`,
        }}>
          <span style={{ width: 5, height: 5, borderRadius: '50%', background: resultBadge.dotColor }} />
          {resultBadge.text}
        </span>
      </div>

      {/* Process Review card */}
      <div style={{ background: C.card, border: `1px solid ${C.bdr}`, borderRadius: '10px', marginTop: '12px', overflow: 'hidden' }}>
        <div style={{
          fontFamily: "'JetBrains Mono','Menlo',monospace", fontSize: '9px', letterSpacing: '0.12em',
          textTransform: 'uppercase', color: C.t3, padding: '16px 20px 0',
        }}>Process Review</div>
        <div style={{ padding: '12px 20px 16px', fontSize: '14px', lineHeight: 1.6, color: C.t2 }}>
          {isPush
            ? `Spread landed on the number. Wager returned. Edge was ${edgePct}% at entry. Variance within expected parameters.`
            : isWin
            ? `Outcome within expected range. Edge: ${edgePct}%. Win expected ~${modelProb} of the time. One result does not validate a model.`
            : `Edge was ${edgePct}% at entry. Model expected a win ~${modelProb} of the time. Loss falls within expected variance. Process was correct. Outcome was not.`
          }
        </div>
        <div style={{ display: 'flex', padding: '0 20px 16px' }}>
          <DetailStat value={typeof edgePct === 'number' ? `${edgePct}%` : edgePct} label="Edge at Entry" />
          <DetailStat value={modelProb} label="Model Probability" border />
        </div>
      </div>

      {/* P&L card */}
      <div style={{
        background: C.card, border: `1px solid ${C.bdr}`,
        borderRadius: '10px', marginTop: '12px', padding: '16px 20px',
        display: 'flex', justifyContent: 'space-between', alignItems: 'center',
      }}>
        <span style={{
          fontFamily: "'JetBrains Mono','Menlo',monospace", fontSize: '9px', letterSpacing: '0.12em',
          textTransform: 'uppercase', color: C.t3,
        }}>P&L</span>
        <span style={{
          fontFamily: "'JetBrains Mono','Menlo',monospace", fontSize: '20px', fontWeight: 700, color: pnlColor,
        }}>{profitDisplay}</span>
      </div>

      {/* CLV card */}
      <CLVCard pick={pick} />

      {/* Discipline Framework card */}
      <div style={{ background: C.card, border: `1px solid ${C.bdr}`, borderRadius: '10px', marginTop: '12px', overflow: 'hidden' }}>
        <div style={{
          fontFamily: "'JetBrains Mono','Menlo',monospace", fontSize: '9px', letterSpacing: '0.12em',
          textTransform: 'uppercase', color: C.grn, padding: '16px 20px 0',
        }}>Discipline Framework</div>
        <div style={{
          padding: '10px 20px 18px',
          fontFamily: "'IBM Plex Serif',Georgia,serif", fontStyle: 'italic',
          fontSize: '14px', lineHeight: 1.6, color: C.t2,
        }}>
          {isPush
            ? 'Push changes nothing. Process identified an edge, game landed on the number. Next signal when the edge is there.'
            : isWin
            ? 'Correct response to a win: nothing. No expanding criteria. No overconfidence. Next signal when the edge is there.'
            : 'Correct response to a loss: nothing. No chasing. No adjusting thresholds. The model doesn\u2019t feel. Next signal when the edge is there.'
          }
        </div>
      </div>

      <p style={{
        fontSize: '10px', color: C.t4, textAlign: 'center',
        padding: '16px 0', lineHeight: '1.5', opacity: 0.6,
      }}>
        Past performance does not guarantee future results.
      </p>
    </div>
    </div>
  );
}

function DetailStat({ value, label, border }) {
  return (
    <div style={{ flex: 1, textAlign: 'center', padding: '12px 0', borderLeft: border ? `1px solid ${C.bdr}` : 'none' }}>
      <div style={{ fontFamily: "'JetBrains Mono','Menlo',monospace", fontSize: '20px', fontWeight: 500, color: C.t1 }}>{value}</div>
      <div style={{ fontFamily: "'JetBrains Mono','Menlo',monospace", fontSize: '8px', letterSpacing: '0.1em', textTransform: 'uppercase', color: C.t4, marginTop: '4px' }}>{label}</div>
    </div>
  );
}

// Signal Withdrawn — slate-blue institutional palette.
// IMPORTANT: This screen is a NEUTRAL informational state, not an alert.
// Never use yellow/orange/red/amber here. Slate-blue = system; green = "Protected" only.
// v4.3 Withdrawn Detail tokens. Inline so the component reads as one unit;
// the rest of ResolutionScreen still uses the legacy `C` palette above and
// is intentionally untouched (different state, different design call).
const SP = {
  bg: '#0A0D14',
  surface: '#121725',
  surface2: '#1B2030',
  border: 'rgba(255, 255, 255, 0.08)',
  border2: 'rgba(255, 255, 255, 0.05)',
  blue: '#4F86F7',
  blueSoft: 'rgba(79, 134, 247, 0.12)',
  green: '#5A9E72',
  greenSoft: 'rgba(90, 158, 114, 0.12)',
  amber: '#F59E0B',
  text: '#E8EAED',
  text2: 'rgba(232, 234, 237, 0.7)',
  text3: 'rgba(232, 234, 237, 0.5)',
  text4: 'rgba(232, 234, 237, 0.35)',
  text5: 'rgba(232, 234, 237, 0.25)',
  fontSans: "'Inter', -apple-system, BlinkMacSystemFont, sans-serif",
  fontMono: "'JetBrains Mono', 'Menlo', ui-monospace, monospace",
  fontSerif: "'IBM Plex Serif', Georgia, serif",
};

function fmtTimeET(iso) {
  if (!iso) return null;
  try {
    const d = new Date(iso);
    if (Number.isNaN(d.getTime())) return null;
    const parts = new Intl.DateTimeFormat('en-US', {
      timeZone: 'America/New_York',
      hour: 'numeric', minute: '2-digit', hour12: true,
    }).formatToParts(d);
    const h = parts.find((p) => p.type === 'hour')?.value || '';
    const m = parts.find((p) => p.type === 'minute')?.value || '';
    const a = (parts.find((p) => p.type === 'dayPeriod')?.value || '').toUpperCase();
    return `${h}:${m} ${a} ET`;
  } catch {
    return null;
  }
}

function thresholdFor(sport) {
  const s = (sport || '').toLowerCase();
  if (s === 'mlb' || s === 'wnba') return 4.5;
  return 8.0;
}

function WithdrawnDetailScreen({ pick, onBack }) {
  const scrollRef = useRef(null);
  useEffect(() => {
    if (scrollRef.current) scrollRef.current.scrollTop = 0;
  }, [pick]);

  const handleBack = () => {
    if (typeof onBack === 'function') onBack();
    else if (typeof window !== 'undefined' && window.history && window.history.length > 1) {
      window.history.back();
    }
  };

  const sideDisplay = pick?.side && pick?.line != null && pick.side.includes(String(Math.abs(pick.line)))
    ? pick.side
    : pick?.side && pick?.line != null
    ? `${pick.side} ${pick.line > 0 ? '+' : ''}${pick.line}`
    : pick?.side || '\u2014';

  const sport = (pick?.sport || 'mlb').toUpperCase();
  const isCalibration = pick?.model_phase === 'calibration';

  const matchup = pick?.away_team && pick?.home_team
    ? `${pick.away_team} @ ${pick.home_team}`
    : (pick?.matchup || 'Matchup unavailable');

  const sizeUnits = pick?.position_size_pct != null
    ? `${(Number(pick.position_size_pct) / 100).toFixed(1)}u`
    : null;

  const firedTime = fmtTimeET(pick?.published_at);
  const withdrawnTime = fmtTimeET(pick?.result_resolved_at);
  const firstPitchTime = fmtTimeET(pick?.start_time);

  const threshold = thresholdFor(pick?.sport);
  const edgeAtFire = pick?.edge_pct != null
    ? `+${Number(pick.edge_pct).toFixed(1)}%`
    : null;
  const edgeAtRecheck = pick?.edge_at_close != null
    ? `+${Number(pick.edge_at_close).toFixed(1)}%`
    : `+${threshold.toFixed(1)}%`;
  const thresholdLabel = `+${threshold.toFixed(1)}%`;

  // Render `+4.5%` style inline code chunks if the reason contains one.
  const renderInvalidationReason = (reason) => {
    if (!reason) return null;
    const text = String(reason);
    const codeRe = /([+\-]?\d+(?:\.\d+)?%)/g;
    const out = [];
    let lastIdx = 0;
    let m;
    let i = 0;
    while ((m = codeRe.exec(text)) !== null) {
      if (m.index > lastIdx) out.push(<span key={`t-${i}`}>{text.slice(lastIdx, m.index)}</span>);
      out.push(
        <code key={`c-${i}`} style={{
          fontFamily: SP.fontMono,
          fontSize: '12px',
          color: SP.text,
          background: 'rgba(0, 0, 0, 0.25)',
          padding: '1px 5px',
          borderRadius: '3px',
        }}>{m[0]}</code>,
      );
      lastIdx = m.index + m[0].length;
      i += 1;
    }
    if (lastIdx < text.length) out.push(<span key={`t-${i}`}>{text.slice(lastIdx)}</span>);
    return out.length ? out : text;
  };

  const cardStyle = {
    background: SP.surface,
    border: `1px solid ${SP.border}`,
    borderRadius: '14px',
    overflow: 'hidden',
  };

  const tlItemStyle = {
    position: 'relative',
    padding: '16px 0 16px 24px',
    borderBottom: `1px solid ${SP.border2}`,
  };

  const tlDot = (color) => ({
    content: '""',
    position: 'absolute',
    left: 0,
    top: 22,
    width: 8,
    height: 8,
    borderRadius: '50%',
    background: color,
  });

  return (
    <div ref={scrollRef} style={{
      position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
      backgroundColor: SP.bg,
      color: SP.text,
      zIndex: 200,
      overflowY: 'auto',
      WebkitOverflowScrolling: 'touch',
      WebkitTapHighlightColor: 'transparent',
    }}>
      <div style={{
        maxWidth: '480px',
        margin: '0 auto',
        paddingLeft: 'max(18px, env(safe-area-inset-left))',
        paddingRight: 'max(18px, env(safe-area-inset-right))',
        paddingBottom: 'max(32px, env(safe-area-inset-bottom))',
        borderLeft: '1px solid rgba(255, 255, 255, 0.04)',
        borderRight: '1px solid rgba(255, 255, 255, 0.04)',
      }}>
        <div style={{
          position: 'sticky',
          top: 0,
          zIndex: 1,
          backgroundColor: SP.bg,
          borderBottom: `1px solid ${SP.border}`,
          paddingTop: 'max(12px, env(safe-area-inset-top))',
          paddingBottom: '18px',
          display: 'flex',
          alignItems: 'center',
          gap: '12px',
          marginLeft: 'calc(-1 * max(18px, env(safe-area-inset-left)))',
          marginRight: 'calc(-1 * max(18px, env(safe-area-inset-right)))',
          paddingLeft: 'max(18px, env(safe-area-inset-left))',
          paddingRight: 'max(18px, env(safe-area-inset-right))',
        }}>
          <button
            onClick={handleBack}
            aria-label="Go back"
            style={{
              background: 'none',
              border: 'none',
              cursor: 'pointer',
              color: SP.text2,
              width: 32, height: 32,
              marginLeft: '-8px',
              display: 'inline-flex',
              alignItems: 'center',
              justifyContent: 'center',
              WebkitTapHighlightColor: 'transparent',
            }}
          >
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M15 18l-6-6 6-6" />
            </svg>
          </button>
          <span style={{
            fontFamily: SP.fontMono,
            fontSize: '12px',
            fontWeight: 500,
            letterSpacing: '0.24em',
            textTransform: 'uppercase',
            color: SP.text,
          }}>Signal Withdrawn</span>
        </div>

        <div style={{ paddingTop: '22px' }}>
          {/* Matchup card */}
          <div style={{ ...cardStyle, padding: '22px 22px 20px', marginBottom: '22px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '14px' }}>
              <span style={{
                display: 'inline-flex',
                alignItems: 'center',
                padding: '4px 10px',
                border: `1px solid ${SP.amber}`,
                borderRadius: '4px',
                fontFamily: SP.fontMono,
                fontSize: '9px',
                fontWeight: 500,
                letterSpacing: '0.2em',
                textTransform: 'uppercase',
                color: SP.amber,
              }}>
                {sport}
              </span>
              <span style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '5px',
                padding: '4px 10px',
                border: '1px solid rgba(79, 134, 247, 0.3)',
                background: SP.blueSoft,
                borderRadius: '4px',
                fontFamily: SP.fontMono,
                fontSize: '9px',
                fontWeight: 500,
                letterSpacing: '0.2em',
                textTransform: 'uppercase',
                color: SP.blue,
              }}>
                <span style={{ width: 5, height: 5, borderRadius: '50%', background: SP.blue }} />
                Withdrawn
              </span>
            </div>
            <h1 style={{
              fontFamily: SP.fontSerif,
              fontSize: '22px',
              fontWeight: 600,
              color: SP.text,
              lineHeight: 1.25,
              marginBottom: '6px',
            }}>{matchup}</h1>
            <div style={{
              fontFamily: SP.fontMono,
              fontSize: '13px',
              color: SP.text2,
              marginBottom: '14px',
              letterSpacing: '0.04em',
            }}>
              Original signal: <span style={{ color: SP.text, fontWeight: 500 }}>{sideDisplay}</span>
              {sizeUnits ? ` · ${sizeUnits}` : ''}
            </div>
            <div style={{
              display: 'flex',
              paddingTop: '14px',
              borderTop: `1px solid ${SP.border2}`,
            }}>
              {[
                { label: 'Signal Fired', value: firedTime || '—' },
                { label: 'Withdrawn', value: withdrawnTime || '—' },
                { label: 'First Pitch', value: firstPitchTime || '—' },
              ].map((cell) => (
                <div key={cell.label} style={{ flex: 1, textAlign: 'left' }}>
                  <div style={{
                    fontFamily: SP.fontMono,
                    fontSize: '9px',
                    letterSpacing: '0.22em',
                    textTransform: 'uppercase',
                    color: SP.text4,
                    marginBottom: '4px',
                  }}>{cell.label}</div>
                  <div style={{
                    fontFamily: SP.fontMono,
                    fontSize: '12px',
                    color: SP.text,
                    letterSpacing: '0.04em',
                  }}>{cell.value}</div>
                </div>
              ))}
            </div>
          </div>

          {/* Capital preserved hero */}
          <div style={{ ...cardStyle, padding: '22px', marginBottom: '22px', position: 'relative' }}>
            <div style={{
              position: 'absolute',
              top: 0,
              left: 20,
              right: 20,
              height: 2,
              background: `linear-gradient(90deg, transparent, ${SP.green} 20%, ${SP.green} 80%, transparent)`,
              opacity: 0.5,
            }} />
            <div style={{
              fontFamily: SP.fontMono,
              fontSize: '10px',
              fontWeight: 500,
              letterSpacing: '0.22em',
              textTransform: 'uppercase',
              color: SP.blue,
              marginBottom: '14px',
            }}>Capital preserved</div>
            <h2 style={{
              fontFamily: SP.fontSerif,
              fontSize: '22px',
              fontWeight: 600,
              lineHeight: 1.25,
              color: SP.text,
              marginBottom: '14px',
            }}>The system pulled the signal before tip-off.</h2>
            {[
              { label: 'Position', value: 'No bet placed', tone: 'plain' },
              { label: 'Capital exposed', value: '0.0u', tone: 'plain' },
              { label: 'Outcome', value: 'Protected', tone: 'green' },
            ].map((row) => (
              <div key={row.label} style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                padding: '12px 0',
                borderTop: `1px solid ${SP.border2}`,
              }}>
                <span style={{
                  fontFamily: SP.fontMono,
                  fontSize: '10px',
                  letterSpacing: '0.22em',
                  textTransform: 'uppercase',
                  color: SP.text3,
                }}>{row.label}</span>
                <span style={{
                  fontFamily: SP.fontMono,
                  fontSize: '14px',
                  fontWeight: 500,
                  letterSpacing: '0.04em',
                  color: row.tone === 'green' ? SP.green : SP.text,
                }}>{row.value}</span>
              </div>
            ))}
          </div>

          {/* Withdrawal sequence */}
          <div style={{ marginBottom: '22px' }}>
            <div style={{
              fontFamily: SP.fontMono,
              fontSize: '10px',
              fontWeight: 500,
              letterSpacing: '0.24em',
              textTransform: 'uppercase',
              color: SP.green,
              marginBottom: '12px',
              paddingLeft: '4px',
            }}>Withdrawal sequence</div>
            <div style={{
              ...cardStyle,
              borderRadius: '12px',
              padding: '6px 22px',
            }}>
              {[
                {
                  time: firedTime ? firedTime.toUpperCase() : 'SIGNAL FIRED',
                  event: 'Signal fired with qualifying edge',
                  detail: edgeAtFire
                    ? `Edge ${edgeAtFire} · above ${thresholdLabel} threshold`
                    : `Above ${thresholdLabel} threshold`,
                  dot: SP.green,
                },
                {
                  time: withdrawnTime ? `${withdrawnTime.toUpperCase()} · PRE-TIP RECHECK` : 'PRE-TIP RECHECK',
                  event: 'Pre-tip re-check detected material change',
                  detail: pick?.withdraw_reason || 'Validation surfaced new information',
                  dot: SP.amber,
                },
                {
                  time: withdrawnTime ? withdrawnTime.toUpperCase() : 'WITHDRAWN',
                  event: 'Signal withdrawn before tip-off',
                  detail: `Edge dropped to ${edgeAtRecheck} · no longer qualifying`,
                  dot: SP.blue,
                },
              ].map((item, i, arr) => (
                <div
                  key={item.event}
                  style={{
                    ...tlItemStyle,
                    borderBottom: i < arr.length - 1 ? `1px solid ${SP.border2}` : 'none',
                  }}
                >
                  <span style={tlDot(item.dot)} aria-hidden />
                  {i < arr.length - 1 && (
                    <span style={{
                      position: 'absolute',
                      left: 3.5,
                      top: 30,
                      bottom: -8,
                      width: 1,
                      background: SP.border2,
                    }} aria-hidden />
                  )}
                  <div style={{
                    fontFamily: SP.fontMono,
                    fontSize: '10px',
                    letterSpacing: '0.18em',
                    textTransform: 'uppercase',
                    color: SP.text4,
                    marginBottom: '4px',
                  }}>{item.time}</div>
                  <div style={{
                    fontFamily: SP.fontSans,
                    fontSize: '14px',
                    fontWeight: 500,
                    color: SP.text,
                    lineHeight: 1.45,
                    marginBottom: '4px',
                  }}>{item.event}</div>
                  <div style={{
                    fontFamily: SP.fontMono,
                    fontSize: '11px',
                    color: SP.text3,
                    letterSpacing: '0.04em',
                  }}>{item.detail}</div>
                </div>
              ))}
            </div>
          </div>

          {/* Process review */}
          <div style={{
            fontFamily: SP.fontMono,
            fontSize: '10px',
            fontWeight: 500,
            letterSpacing: '0.24em',
            textTransform: 'uppercase',
            color: SP.green,
            marginBottom: '12px',
            paddingLeft: '4px',
          }}>Process review</div>
          <div style={{ ...cardStyle, padding: '20px 22px', borderRadius: '12px', marginBottom: '22px' }}>
            {pick?.withdraw_reason && (
              <div style={{
                background: SP.greenSoft,
                borderLeft: `2px solid ${SP.green}`,
                borderRadius: '0 8px 8px 0',
                padding: '14px 18px',
                marginBottom: '16px',
              }}>
                <div style={{
                  fontFamily: SP.fontMono,
                  fontSize: '9px',
                  fontWeight: 500,
                  letterSpacing: '0.22em',
                  textTransform: 'uppercase',
                  color: SP.green,
                  marginBottom: '6px',
                }}>Invalidation reason</div>
                <div style={{
                  fontFamily: SP.fontSerif,
                  fontSize: '14px',
                  lineHeight: 1.5,
                  color: SP.text,
                }}>{renderInvalidationReason(pick.withdraw_reason)}</div>
              </div>
            )}
            <p style={{
              fontSize: '13px',
              lineHeight: 1.55,
              color: SP.text2,
              marginBottom: '16px',
            }}>
              The signal pipeline runs a final validation pass on every active signal in the 30 minutes before tip-off. When new information moves the edge below threshold, the system withdraws automatically. No discretionary call.
            </p>

            <div style={{
              display: 'grid',
              gridTemplateColumns: '1fr 1px 1fr 1px 1fr',
              background: SP.bg,
              border: `1px solid ${SP.border}`,
              borderRadius: '12px',
              overflow: 'hidden',
            }}>
              {[
                { label: 'Edge at fire', value: edgeAtFire || '—', tone: 'green' },
                { label: 'Edge at recheck', value: edgeAtRecheck, tone: 'dropped' },
                { label: 'Threshold', value: thresholdLabel, tone: 'plain' },
              ].flatMap((cell, i, arr) => [
                <div key={`c-${cell.label}`} style={{ padding: '16px 8px', textAlign: 'center' }}>
                  <div style={{
                    fontFamily: SP.fontMono,
                    fontSize: '9px',
                    letterSpacing: '0.22em',
                    textTransform: 'uppercase',
                    color: SP.text4,
                    marginBottom: '6px',
                  }}>{cell.label}</div>
                  <div style={{
                    fontFamily: SP.fontMono,
                    fontSize: '16px',
                    fontWeight: 500,
                    lineHeight: 1,
                    color: cell.tone === 'green' ? SP.green : cell.tone === 'dropped' ? SP.amber : SP.text,
                  }}>{cell.value}</div>
                </div>,
                i < arr.length - 1 ? <div key={`d-${i}`} style={{ background: SP.border }} /> : null,
              ])}
            </div>
          </div>

          {/* Sharp Principle */}
          <div style={{
            background: SP.greenSoft,
            borderLeft: `2px solid ${SP.green}`,
            borderRadius: '0 12px 12px 0',
            padding: '18px 22px',
            marginBottom: '22px',
          }}>
            <div style={{
              fontFamily: SP.fontMono,
              fontSize: '9px',
              fontWeight: 500,
              letterSpacing: '0.22em',
              textTransform: 'uppercase',
              color: SP.green,
              marginBottom: '8px',
            }}>Sharp Principle</div>
            <div style={{
              fontFamily: SP.fontSerif,
              fontSize: '15px',
              fontStyle: 'italic',
              lineHeight: 1.5,
              color: SP.text,
            }}>Not every signal survives. The edge decides, not emotion. Withdrawal is the system protecting capital.</div>
          </div>

          {/* Already placed help */}
          <div style={{ ...cardStyle, padding: '18px 22px', borderRadius: '12px', marginBottom: '22px' }}>
            <div style={{
              fontFamily: SP.fontMono,
              fontSize: '10px',
              fontWeight: 500,
              letterSpacing: '0.22em',
              textTransform: 'uppercase',
              color: SP.text3,
              marginBottom: '10px',
            }}>Already placed?</div>
            <div style={{
              fontFamily: SP.fontSerif,
              fontSize: '15px',
              fontWeight: 600,
              color: SP.text,
              marginBottom: '8px',
            }}>If you placed this bet before withdrawal, treat it as a standalone decision.</div>
            <div style={{
              fontSize: '13px',
              lineHeight: 1.55,
              color: SP.text2,
            }}>
              Your tracked bet still grades on actual game result. The withdrawal reflects that the signal no longer met threshold at the time of re-check. SharpPicks tracks both: your actual outcome and the system's withdrawn-signal record.
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function fmtSpread(val) {
  if (val == null) return '\u2014';
  const n = parseFloat(val);
  if (Number.isInteger(n)) return n > 0 ? `+${n}` : `${n}`;
  return n > 0 ? `+${n.toFixed(1)}` : `${n.toFixed(1)}`;
}

function CLVCard({ pick }) {
  const pickLine = pick?.line;
  const closingLine = pick?.closing_spread;
  const rawCLV = pick?.clv != null ? parseFloat(pick.clv) : null;
  const clvVal = rawCLV ?? (pickLine != null && closingLine != null ? parseFloat(pickLine) - parseFloat(closingLine) : null);

  if (pickLine == null && closingLine == null && clvVal == null) return null;

  return (
    <div style={{ background: C.card, border: `1px solid ${C.bdr}`, borderRadius: '10px', marginTop: '12px', padding: '16px 20px' }}>
      <div style={{
        fontFamily: "'JetBrains Mono','Menlo',monospace", fontSize: '9px', letterSpacing: '0.12em',
        textTransform: 'uppercase', color: C.t3, marginBottom: '12px',
      }}>Closing Line Value</div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 0 }}>
        <CLVRow label="Pick Line" value={fmtSpread(pickLine)} />
        <CLVRow label="Closing Line" value={fmtSpread(closingLine)} border />
        {clvVal != null && (
          <CLVRow
            label="CLV"
            value={`${clvVal > 0 ? '+' : ''}${clvVal.toFixed(1)} pts`}
            valueColor={C.grn}
            border
          />
        )}
      </div>
    </div>
  );
}

function CLVRow({ label, value, valueColor, border }) {
  return (
    <div style={{
      display: 'flex', justifyContent: 'space-between', alignItems: 'center',
      padding: '6px 0',
      borderTop: border ? `1px solid ${C.bdr}` : 'none',
    }}>
      <span style={{
        fontFamily: "'JetBrains Mono','Menlo',monospace", fontSize: '11px', letterSpacing: '0.06em',
        textTransform: 'uppercase', color: C.t4,
      }}>{label}</span>
      <span style={{
        fontFamily: "'JetBrains Mono','Menlo',monospace", fontSize: '16px', fontWeight: 500,
        color: valueColor || C.t1,
      }}>{value}</span>
    </div>
  );
}
