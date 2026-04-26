import { useEffect, useRef } from 'react';

const C = {
  bg: '#0c1018', card: '#111827', bdr: '#1e2a3a', bdr2: '#2a3654',
  t1: '#e8eaf0', t2: '#9098b3', t3: '#616a8a', t4: '#4a5274',
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
const W = {
  bgPage: '#0A0E1A',
  bgCard: '#111726',
  bgCardElev: '#161D2E',
  borderSubtle: '#1F2940',
  borderMedium: '#2B3A5C',
  edge: '#4ADE80',
  system: '#6B8AC4',
  systemBg: 'rgba(107, 138, 196, 0.08)',
  systemBorder: 'rgba(107, 138, 196, 0.28)',
  textPrimary: '#E8ECF4',
  textSecondary: '#9BA8C2',
  textTertiary: '#5A6886',
  textMuted: '#3E4A66',
  fontSans: "'Inter','-apple-system','BlinkMacSystemFont',system-ui,sans-serif",
  fontMono: "'JetBrains Mono','Menlo',ui-monospace,monospace",
};

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

  const matchup = pick?.away_team && pick?.home_team
    ? `${pick.away_team} @ ${pick.home_team}`
    : (pick?.matchup || 'Matchup unavailable');

  const edgeAtEntry = pick?.edge_pct != null ? `${pick.edge_pct}%` : '--';
  const edgeAtWithdrawal = pick?.edge_at_close != null ? `${pick.edge_at_close}%` : '--';
  const pnlDisplay = pick?.profit_units != null
    ? `${pick.profit_units >= 0 ? '' : ''}${Number(pick.profit_units).toFixed(1)}u`
    : '0.0u';

  // Render arrow in slate-blue if the reason contains one.
  const renderInvalidationReason = (reason) => {
    if (!reason) return null;
    const parts = String(reason).split('\u2192');
    if (parts.length === 1) return reason;
    const out = [];
    parts.forEach((p, i) => {
      out.push(<span key={`p-${i}`}>{p}</span>);
      if (i < parts.length - 1) {
        out.push(<span key={`a-${i}`} style={{ color: W.system }}>{' \u2192 '}</span>);
      }
    });
    return out;
  };

  const cardStyle = {
    background: W.bgCard,
    border: `1px solid ${W.borderSubtle}`,
    borderRadius: '16px',
    overflow: 'hidden',
  };
  const sectionLabelStyle = {
    fontFamily: W.fontMono,
    fontSize: '11px',
    letterSpacing: '0.14em',
    color: W.textTertiary,
    textTransform: 'uppercase',
    fontWeight: 500,
    marginBottom: '14px',
  };

  return (
    <div ref={scrollRef} style={{
      position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
      backgroundColor: W.bgPage,
      color: W.textPrimary,
      zIndex: 200,
      overflowY: 'auto',
      WebkitOverflowScrolling: 'touch',
      WebkitTapHighlightColor: 'transparent',
    }}>
      <div style={{
        maxWidth: '420px',
        margin: '0 auto',
        paddingLeft: 'max(16px, env(safe-area-inset-left))',
        paddingRight: 'max(16px, env(safe-area-inset-right))',
        paddingBottom: 'max(32px, env(safe-area-inset-bottom))',
      }}>
        {/* Header */}
        <div style={{
          position: 'sticky',
          top: 0,
          zIndex: 1,
          backgroundColor: W.bgPage,
          borderBottom: `1px solid ${W.borderSubtle}`,
          paddingTop: 'max(14px, env(safe-area-inset-top))',
          paddingBottom: '14px',
          display: 'flex',
          alignItems: 'center',
          gap: '12px',
          marginLeft: 'calc(-1 * max(16px, env(safe-area-inset-left)))',
          marginRight: 'calc(-1 * max(16px, env(safe-area-inset-right)))',
          paddingLeft: 'max(16px, env(safe-area-inset-left))',
          paddingRight: 'max(16px, env(safe-area-inset-right))',
        }}>
          <button
            onClick={handleBack}
            aria-label="Go back"
            style={{
              background: 'none',
              border: 'none',
              cursor: 'pointer',
              color: W.textSecondary,
              padding: '12px',
              margin: '-12px',
              display: 'inline-flex',
              alignItems: 'center',
              justifyContent: 'center',
              minWidth: '44px',
              minHeight: '44px',
              WebkitTapHighlightColor: 'transparent',
            }}
            onMouseDown={(e) => { e.currentTarget.style.color = W.textPrimary; }}
            onMouseUp={(e) => { e.currentTarget.style.color = W.textSecondary; }}
            onTouchStart={(e) => { e.currentTarget.style.color = W.textPrimary; }}
            onTouchEnd={(e) => { e.currentTarget.style.color = W.textSecondary; }}
          >
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M15 18l-6-6 6-6" />
            </svg>
          </button>
          <h1 style={{
            margin: 0,
            fontFamily: W.fontSans,
            fontSize: '20px',
            fontWeight: 600,
            letterSpacing: '-0.01em',
            color: W.textPrimary,
            userSelect: 'none',
          }}>Signal Withdrawn</h1>
        </div>

        {/* Card stack */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '12px', paddingTop: '20px' }}>

          {/* Game card */}
          <div style={{ ...cardStyle, position: 'relative', padding: '28px 20px 24px', textAlign: 'center' }}>
            <div style={{
              position: 'absolute', top: 0, left: 0, right: 0, height: '2px',
              background: `linear-gradient(90deg, transparent, ${W.system} 20%, ${W.system} 80%, transparent)`,
              opacity: 0.7,
            }} />
            <div style={{
              fontFamily: W.fontSans,
              fontSize: '19px',
              fontWeight: 600,
              letterSpacing: '-0.01em',
              color: W.textPrimary,
              marginBottom: '10px',
            }}>{matchup}</div>
            <div style={{
              fontFamily: W.fontMono,
              fontSize: '14px',
              color: W.textSecondary,
              letterSpacing: '0.02em',
              marginBottom: '16px',
              userSelect: 'text',
            }}>{sideDisplay}</div>
            <span style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '8px',
              padding: '7px 14px',
              background: W.systemBg,
              border: `1px solid ${W.systemBorder}`,
              borderRadius: '999px',
              fontFamily: W.fontMono,
              fontSize: '11px',
              fontWeight: 600,
              letterSpacing: '0.12em',
              color: W.system,
              userSelect: 'none',
            }}>
              <span style={{ width: 6, height: 6, borderRadius: '50%', background: W.system }} />
              WITHDRAWN
            </span>
          </div>

          {/* Process Review */}
          <div style={cardStyle}>
            <div style={{ padding: '20px' }}>
              <div style={sectionLabelStyle}>PROCESS REVIEW</div>

              {pick?.withdraw_reason && (
                <div style={{
                  background: W.bgCardElev,
                  border: `1px solid ${W.borderMedium}`,
                  borderLeft: `2px solid ${W.system}`,
                  borderRadius: '10px',
                  padding: '14px 16px',
                  marginBottom: '14px',
                }}>
                  <div style={{
                    fontFamily: W.fontMono,
                    fontSize: '10px',
                    letterSpacing: '0.14em',
                    color: W.system,
                    fontWeight: 600,
                    marginBottom: '6px',
                    textTransform: 'uppercase',
                  }}>INVALIDATION REASON</div>
                  <div style={{
                    fontFamily: W.fontMono,
                    fontSize: '13px',
                    lineHeight: 1.5,
                    color: W.textPrimary,
                    userSelect: 'text',
                  }}>{renderInvalidationReason(pick.withdraw_reason)}</div>
                </div>
              )}

              <div style={{
                fontFamily: W.fontSans,
                fontSize: '14.5px',
                lineHeight: 1.55,
                color: W.textSecondary,
                marginBottom: '20px',
                userSelect: 'text',
              }}>
                {pick?.withdraw_reason
                  ? 'Pre-tip validation detected a material change. Signal invalidated before tip-off. Capital preserved.'
                  : 'Market moved. Edge fell below threshold before tip-off. Capital preserved. No trade is a position.'}
              </div>

              <div style={{
                display: 'grid',
                gridTemplateColumns: '1fr 1fr 1fr',
                gap: '1px',
                background: W.borderSubtle,
                borderRadius: '10px',
                overflow: 'hidden',
              }}>
                <WithdrawnStat value={edgeAtEntry} label="Edge at Entry" />
                <WithdrawnStat
                  value={edgeAtWithdrawal === '--' ? '--' : edgeAtWithdrawal}
                  label="Edge at Withdrawal"
                  muted={edgeAtWithdrawal === '--'}
                />
                <WithdrawnStat value="Protected" label="Action" action />
              </div>
            </div>
          </div>

          {/* P&L row */}
          <div style={cardStyle}>
            <div style={{
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              padding: '18px 20px',
            }}>
              <span style={{
                fontFamily: W.fontMono,
                fontSize: '11px',
                letterSpacing: '0.14em',
                color: W.textTertiary,
                fontWeight: 500,
                textTransform: 'uppercase',
                userSelect: 'none',
              }}>P&L</span>
              <span style={{
                fontFamily: W.fontMono,
                fontSize: '20px',
                fontWeight: 600,
                color: W.textSecondary,
                userSelect: 'text',
              }}>{pnlDisplay}</span>
            </div>
          </div>

          {/* Discipline Framework */}
          <div style={cardStyle}>
            <div style={{ padding: '20px' }}>
              <div style={{ ...sectionLabelStyle, color: W.system }}>DISCIPLINE FRAMEWORK</div>
              <div style={{
                fontFamily: W.fontSans,
                fontSize: '14.5px',
                lineHeight: 1.6,
                color: W.textSecondary,
                userSelect: 'text',
              }}>
                Not every signal survives. The edge decides, not emotion. A withdrawal is the system protecting capital. Next signal when the edge is there.
              </div>
            </div>
          </div>

          {/* Already Placed? */}
          <div style={cardStyle}>
            <div style={{ padding: '20px' }}>
              <div style={{ ...sectionLabelStyle, color: W.system }}>ALREADY PLACED?</div>
              <div style={{
                fontFamily: W.fontSans,
                fontSize: '14.5px',
                lineHeight: 1.6,
                color: W.textSecondary,
                userSelect: 'text',
              }}>
                If already wagered before withdrawal, treat as standalone decision. Tracked bet still graded on actual result. Withdrawal reflects edge no longer met threshold.
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function WithdrawnStat({ value, label, muted, action }) {
  const valueColor = action ? W.edge : muted ? W.textMuted : W.textPrimary;
  const valueSize = action ? '16px' : '22px';
  const valueWeight = action ? 600 : 600;
  return (
    <div style={{
      background: W.bgCardElev,
      padding: '16px 8px',
      textAlign: 'center',
    }}>
      <div style={{
        fontFamily: W.fontMono,
        fontSize: valueSize,
        fontWeight: valueWeight,
        color: valueColor,
        marginBottom: '6px',
        lineHeight: 1,
        paddingTop: action ? '4px' : 0,
      }}>{value}</div>
      <div style={{
        fontFamily: W.fontMono,
        fontSize: '9px',
        letterSpacing: '0.12em',
        color: W.textTertiary,
        textTransform: 'uppercase',
        userSelect: 'none',
      }}>{label}</div>
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
