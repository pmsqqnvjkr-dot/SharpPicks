// OutcomeCard — compact settled-outcome tile for feeds and recent-outcome
// surfaces. Matches docs/outcome-resolved-compact.html (standard card
// variant only; ultra-row and toast variants are deferred until their
// consumers exist).
//
// Replaces ResolvedPickBanner and the inline "Signal Result Card (legacy)"
// in PicksTab.jsx. LastNightsReadCard stays as-is for the post-midnight
// Sharp Journal evening-edition CTA (different surface, different intent).
//
// Footer actions:
//   onViewOutcome  primary (Signal Blue) -> opens ResolutionScreen via the
//                  parent's setResolutionPick + setShowResolution dance.
//                  Copy is "View outcome" verbatim.
//   onShare        secondary (muted) -> calls the parent's existing share
//                  infrastructure (handleShareResult). Hidden when not
//                  provided so free users on the home see a single primary
//                  CTA rather than a placeholder Share button.
//   onDismiss      optional -> small x in the header. Used by the home
//                  recent-outcome banner (lastResolved); not used by the
//                  night-mode evening render.

import teamAbbr from '../../utils/teamAbbr';

const SP = {
  surface: '#121725',
  border: 'rgba(255, 255, 255, 0.08)',
  border2: 'rgba(255, 255, 255, 0.05)',
  blue: '#4F86F7',
  green: '#5A9E72',
  greenSoft: 'rgba(90, 158, 114, 0.12)',
  greenBorder: 'rgba(90, 158, 114, 0.4)',
  negative: '#C4868A',
  negativeSoft: 'rgba(196, 134, 138, 0.10)',
  negativeBorder: 'rgba(196, 134, 138, 0.4)',
  text: '#E8EAED',
  text2: 'rgba(232, 234, 237, 0.7)',
  text3: 'rgba(232, 234, 237, 0.5)',
  text4: 'rgba(232, 234, 237, 0.35)',
  text5: 'rgba(232, 234, 237, 0.25)',
  fontMono: "'JetBrains Mono', 'Menlo', ui-monospace, monospace",
  fontSerif: "'IBM Plex Serif', Georgia, serif",
  fontSans: "'Inter', -apple-system, BlinkMacSystemFont, sans-serif",
};

function fmtDate(iso) {
  if (!iso) return '';
  try {
    const ymd = String(iso).slice(0, 10);
    if (!/^\d{4}-\d{2}-\d{2}$/.test(ymd)) return '';
    const d = new Date(`${ymd}T12:00:00Z`);
    if (Number.isNaN(d.getTime())) return '';
    return new Intl.DateTimeFormat('en-US', {
      timeZone: 'America/New_York', month: 'short', day: 'numeric',
    }).format(d);
  } catch { return ''; }
}

function fmtUnits(units, isPush) {
  if (units == null) return isPush ? '0.0u' : null;
  const n = Number(units);
  if (Number.isNaN(n)) return null;
  return `${n >= 0 ? '+' : ''}${n.toFixed(1)}u`;
}

function fmtDollars(amount) {
  if (amount == null) return null;
  const n = Number(amount);
  if (Number.isNaN(n)) return null;
  const sign = n > 0 ? '+' : n < 0 ? '-' : '';
  return `${sign}$${Math.abs(n).toFixed(0)}`;
}

function fmtSide(pick) {
  if (!pick?.side) return 'Signal';
  if (pick.line != null && pick.side.includes(String(Math.abs(pick.line)))) {
    return pick.side;
  }
  const lineStr = pick.line != null ? ` ${pick.line > 0 ? '+' : ''}${pick.line}` : '';
  return `${pick.side}${lineStr}`;
}

export default function OutcomeCard({ pick, sport, onViewOutcome, onShare, onDismiss }) {
  if (!pick) return null;
  const result = (pick.result || '').toLowerCase();
  const isWin = result === 'win';
  const isLoss = result === 'loss';
  const isPush = result === 'push';
  if (!isWin && !isLoss && !isPush) return null;

  const stateLabel = isWin ? 'Win' : isLoss ? 'Loss' : 'Push';
  const stateColor = isWin ? SP.green : isLoss ? SP.negative : SP.text3;
  const accentBar = isWin ? SP.green : isLoss ? SP.negative : SP.text4;

  const sportLabel = String(pick.sport || sport || '').toUpperCase();
  const dateLabel = fmtDate(pick.game_date || pick.date);
  const dateSportLine = [dateLabel, sportLabel].filter(Boolean).join(' · ');

  const matchupLine = pick.away_team && pick.home_team
    ? `${pick.away_team} vs ${pick.home_team}`
    : null;

  const pnlUnitsStr = fmtUnits(pick.profit_units, isPush);
  const dollarPnl = pick.bet_profit_dollars ?? pick.profit_dollars ?? pick.dollar_profit ?? null;
  const dollarPnlStr = fmtDollars(dollarPnl);
  const dollarPnlColor = dollarPnl == null
    ? SP.text4
    : Number(dollarPnl) > 0 ? SP.green : Number(dollarPnl) < 0 ? SP.negative : SP.text3;

  const hasScore = pick.away_score != null && pick.home_score != null;

  const clvNum = pick.clv != null ? Number(pick.clv) : null;
  const clvHasValue = clvNum != null && !Number.isNaN(clvNum);
  const clvGrade = !clvHasValue ? null : clvNum > 0 ? 'beat' : clvNum < 0 ? 'missed' : 'flat';
  const clvPillStyle = clvGrade === 'beat'
    ? { background: SP.greenSoft, border: `1px solid ${SP.greenBorder}`, color: SP.green }
    : clvGrade === 'missed'
    ? { background: SP.negativeSoft, border: `1px solid ${SP.negativeBorder}`, color: SP.negative }
    : { background: 'rgba(255, 255, 255, 0.04)', border: `1px solid ${SP.border}`, color: SP.text3 };
  const clvPillLabel = clvGrade === 'beat'
    ? 'CLV beat'
    : clvGrade === 'missed'
    ? 'CLV missed'
    : clvGrade === 'flat'
    ? 'CLV flat'
    : null;
  const clvValueStr = clvHasValue ? `${clvNum > 0 ? '+' : ''}${clvNum.toFixed(1)}` : null;
  const clvValueColor = !clvHasValue
    ? SP.text3
    : clvNum > 0 ? SP.green : clvNum < 0 ? SP.negative : SP.text2;

  const cardClick = onViewOutcome ? () => onViewOutcome(pick) : undefined;

  return (
    <div
      onClick={cardClick}
      role={cardClick ? 'button' : undefined}
      tabIndex={cardClick ? 0 : undefined}
      onKeyDown={cardClick ? (e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); cardClick(); } } : undefined}
      style={{
        background: SP.surface,
        border: `1px solid ${SP.border}`,
        borderRadius: 12,
        overflow: 'hidden',
        position: 'relative',
        cursor: cardClick ? 'pointer' : 'default',
        marginBottom: 12,
        fontFamily: SP.fontSans,
      }}
    >
      <div style={{
        position: 'absolute', top: 0, bottom: 0, left: 0, width: 2, background: accentBar,
      }} />

      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '14px 16px 10px' }}>
        <div style={{
          display: 'inline-flex', alignItems: 'center', gap: 7,
          fontFamily: SP.fontMono, fontSize: 10, fontWeight: 500,
          letterSpacing: '0.22em', textTransform: 'uppercase', color: stateColor,
        }}>
          <span style={{ width: 6, height: 6, background: 'currentColor', borderRadius: '50%' }} />
          <span>{stateLabel}</span>
        </div>
        <div style={{ display: 'inline-flex', alignItems: 'center', gap: 10 }}>
          {dateSportLine && (
            <span style={{
              fontFamily: SP.fontMono, fontSize: 10, color: SP.text4, letterSpacing: '0.06em',
            }}>{dateSportLine}</span>
          )}
          {onDismiss && (
            <button
              onClick={(e) => { e.stopPropagation(); onDismiss(); }}
              aria-label="Dismiss"
              style={{
                background: 'none', border: 0, color: SP.text4, cursor: 'pointer',
                fontSize: 18, lineHeight: 1, padding: 0,
              }}
            >&times;</button>
          )}
        </div>
      </div>

      <div style={{ padding: '0 16px 14px' }}>
        {matchupLine && (
          <div style={{
            fontFamily: SP.fontMono, fontSize: 11, color: SP.text4,
            letterSpacing: '0.04em', marginBottom: 6,
          }}>{matchupLine}</div>
        )}
        <div style={{ display: 'flex', alignItems: 'baseline', justifyContent: 'space-between', gap: 12, marginBottom: 8 }}>
          <h2 style={{
            fontFamily: SP.fontSerif, fontSize: 19, fontWeight: 600,
            color: SP.text, lineHeight: 1.2, letterSpacing: '-0.005em', margin: 0,
          }}>{fmtSide(pick)}</h2>
          {pnlUnitsStr && (
            <span style={{
              fontFamily: SP.fontMono, fontSize: 22, fontWeight: 500,
              color: stateColor, lineHeight: 1, textAlign: 'right', flexShrink: 0,
            }}>{pnlUnitsStr}</span>
          )}
        </div>
        {(hasScore || dollarPnlStr) && (
          <div style={{
            display: 'flex', alignItems: 'center', justifyContent: 'space-between',
            gap: 12, fontFamily: SP.fontMono, fontSize: 12, color: SP.text3, letterSpacing: '0.04em',
          }}>
            {hasScore ? (
              <span style={{ color: SP.text2 }}>
                Final &middot; {teamAbbr(pick.away_team)} <span style={{ color: SP.text, fontWeight: 500 }}>{pick.away_score}</span>
                {' '}&middot;{' '}
                {teamAbbr(pick.home_team)} <span style={{ color: SP.text, fontWeight: 500 }}>{pick.home_score}</span>
              </span>
            ) : <span />}
            {dollarPnlStr && (
              <span style={{ color: dollarPnlColor, fontSize: 11 }}>{dollarPnlStr}</span>
            )}
          </div>
        )}
      </div>

      <div style={{
        display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 10,
        padding: '11px 16px 12px',
        borderTop: `1px solid ${SP.border2}`,
        background: 'rgba(0, 0, 0, 0.15)',
      }}>
        <div style={{ display: 'inline-flex', alignItems: 'center', gap: 9 }}>
          {clvPillLabel && (
            <span style={{
              display: 'inline-flex', alignItems: 'center',
              padding: '3px 8px', borderRadius: 3,
              fontFamily: SP.fontMono, fontSize: 9, fontWeight: 500,
              letterSpacing: '0.16em', textTransform: 'uppercase',
              ...clvPillStyle,
            }}>{clvPillLabel}</span>
          )}
          {clvValueStr && (
            <span style={{
              fontFamily: SP.fontMono, fontSize: 11, letterSpacing: '0.04em', color: clvValueColor,
            }}>{clvValueStr}</span>
          )}
        </div>
        <div style={{ display: 'inline-flex', alignItems: 'center', gap: 14 }}>
          {onShare && (
            <button
              onClick={(e) => { e.stopPropagation(); onShare(pick); }}
              style={{
                background: 'none', border: 0, padding: 0, cursor: 'pointer',
                color: SP.text3,
                display: 'inline-flex', alignItems: 'center', gap: 5,
                fontFamily: SP.fontMono, fontSize: 10, fontWeight: 500,
                letterSpacing: '0.16em', textTransform: 'uppercase',
              }}
            >
              <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M4 12v8a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-8" />
                <polyline points="16 6 12 2 8 6" />
                <line x1="12" y1="2" x2="12" y2="15" />
              </svg>
              Share
            </button>
          )}
          {onShare && onViewOutcome && (
            <span style={{ width: 1, height: 11, background: SP.border }} />
          )}
          {onViewOutcome && (
            <button
              onClick={(e) => { e.stopPropagation(); onViewOutcome(pick); }}
              style={{
                background: 'none', border: 0, padding: 0, cursor: 'pointer',
                color: SP.blue,
                display: 'inline-flex', alignItems: 'center', gap: 5,
                fontFamily: SP.fontMono, fontSize: 10, fontWeight: 500,
                letterSpacing: '0.16em', textTransform: 'uppercase',
              }}
            >
              View outcome
              <svg width="9" height="9" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3">
                <path d="M9 18l6-6-6-6" />
              </svg>
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
