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
            : `Edge was ${edgePct}% at entry. Model expected a win ~${modelProb} of the time. Loss falls within expected variance. Process was correct \u2014 outcome was not.`
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

function WithdrawnDetailScreen({ pick, onBack }) {
  const scrollRef = useRef(null);
  useEffect(() => {
    if (scrollRef.current) scrollRef.current.scrollTop = 0;
  }, [pick]);

  const sideDisplay = pick?.side && pick?.line != null && pick.side.includes(String(Math.abs(pick.line)))
    ? pick.side
    : pick?.side && pick?.line != null
    ? `${pick.side} ${pick.line > 0 ? '+' : ''}${pick.line}`
    : pick?.side || '\u2014';

  return (
    <div ref={scrollRef} style={{
      position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
      backgroundColor: C.bg,
      zIndex: 200,
      overflowY: 'auto', WebkitOverflowScrolling: 'touch',
    }}>
    <div style={{ maxWidth: '420px', margin: '0 auto', padding: '0 16px', paddingBottom: '100px' }}>
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
          Signal Withdrawn
        </span>
      </div>

      {/* Matchup hero */}
      <div style={{
        background: C.card, border: `1px solid ${C.bdr}`,
        borderRadius: '12px', padding: '24px', textAlign: 'center',
        position: 'relative', overflow: 'hidden', marginTop: '16px',
      }}>
        <div style={{ position: 'absolute', top: 0, left: 0, right: 0, height: '3px', background: '#d4a843' }} />
        <div style={{ fontFamily: "'Inter',-apple-system,sans-serif", fontSize: '16px', fontWeight: 500, color: C.t1, marginBottom: '8px' }}>
          {pick?.away_team} @ {pick?.home_team}
        </div>
        <div style={{ fontFamily: "'JetBrains Mono','Menlo',monospace", fontSize: '12px', color: C.t3 }}>
          {sideDisplay}
        </div>
        <span style={{
          display: 'inline-flex', alignItems: 'center', gap: '5px',
          fontFamily: "'JetBrains Mono','Menlo',monospace", fontSize: '10px', letterSpacing: '0.1em',
          textTransform: 'uppercase', padding: '4px 12px', borderRadius: '6px', marginTop: '12px',
          color: '#d4a843', background: 'rgba(212,168,67,.10)', border: '1px solid rgba(212,168,67,.15)',
        }}>
          <span style={{ width: 5, height: 5, borderRadius: '50%', background: '#d4a843' }} />
          WITHDRAWN
        </span>
      </div>

      {/* Process Review */}
      <div style={{ background: C.card, border: `1px solid ${C.bdr}`, borderRadius: '10px', marginTop: '12px', overflow: 'hidden' }}>
        <div style={{
          fontFamily: "'JetBrains Mono','Menlo',monospace", fontSize: '9px', letterSpacing: '0.12em',
          textTransform: 'uppercase', color: C.t3, padding: '16px 20px 0',
        }}>Process Review</div>

        {pick?.withdraw_reason && (
          <div style={{
            margin: '12px 20px 0', padding: '10px 14px', borderRadius: '8px',
            background: 'rgba(251,191,36,0.04)', border: '1px solid rgba(251,191,36,0.15)',
          }}>
            <div style={{
              fontFamily: "'JetBrains Mono','Menlo',monospace", fontSize: '9px', fontWeight: 700,
              color: '#f59e0b', letterSpacing: '0.06em', textTransform: 'uppercase', marginBottom: '4px',
            }}>Invalidation Reason</div>
            <div style={{
              fontFamily: "'JetBrains Mono','Menlo',monospace", fontSize: '13px',
              color: C.t2, lineHeight: 1.5,
            }}>{pick.withdraw_reason}</div>
          </div>
        )}

        <div style={{ padding: '12px 20px 16px', fontSize: '14px', lineHeight: 1.6, color: C.t2 }}>
          {pick?.withdraw_reason
            ? 'Pre-tip validation detected a material change. Signal invalidated before tip-off. Capital preserved.'
            : 'Market moved. Edge fell below threshold before tip-off. Capital preserved. No trade is a position.'}
        </div>
        <div style={{ display: 'flex', padding: '0 20px 16px' }}>
          <DetailStat value={`${pick?.edge_pct || '--'}%`} label="Edge at entry" />
          <DetailStat value={pick?.edge_at_close != null ? `${pick.edge_at_close}%` : '--'} label="Edge at withdrawal" border />
          <DetailStat value="Protected" label="Action" border />
        </div>
      </div>

      {/* P&L */}
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
          fontFamily: "'JetBrains Mono','Menlo',monospace", fontSize: '20px', fontWeight: 700, color: C.t2,
        }}>0.0u</span>
      </div>

      {/* Discipline Framework */}
      <div style={{ background: C.card, border: `1px solid ${C.bdr}`, borderRadius: '10px', marginTop: '12px', overflow: 'hidden' }}>
        <div style={{
          fontFamily: "'JetBrains Mono','Menlo',monospace", fontSize: '9px', letterSpacing: '0.12em',
          textTransform: 'uppercase', color: '#d4a843', padding: '16px 20px 0',
        }}>Discipline Framework</div>
        <div style={{
          padding: '10px 20px 18px',
          fontFamily: "'IBM Plex Serif',Georgia,serif", fontStyle: 'italic',
          fontSize: '14px', lineHeight: 1.6, color: C.t2,
        }}>
          Not every signal survives. The edge decides &mdash; not emotion. A withdrawal is the system protecting capital. Next signal when the edge is there.
        </div>
      </div>

      {/* Already Placed */}
      <div style={{ background: C.card, border: `1px solid ${C.bdr}`, borderRadius: '10px', marginTop: '12px', overflow: 'hidden' }}>
        <div style={{
          fontFamily: "'JetBrains Mono','Menlo',monospace", fontSize: '9px', letterSpacing: '0.12em',
          textTransform: 'uppercase', color: C.t3, padding: '16px 20px 0',
        }}>Already Placed?</div>
        <div style={{
          padding: '10px 20px 18px',
          fontSize: '14px', lineHeight: 1.6, color: C.t2,
        }}>
          If already wagered before withdrawal, treat as standalone decision. Tracked bet still graded on actual result. Withdrawal reflects edge no longer met threshold.
        </div>
      </div>

      <p style={{
        fontSize: '10px', color: C.t4, textAlign: 'center',
        padding: '16px 0', lineHeight: '1.5', opacity: 0.6,
      }}>
        Capital preservation is the discipline.
      </p>
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
