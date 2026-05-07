// LastNightsReadCard — Sharp Journal evening recap tile for the post-midnight
// home view. Editorial format (eyebrow / serif title / excerpt / 3-stat row /
// date + Read → CTA) matching the May 2026 Midnight State mockup.
//
// Pulls from already-fetched home data:
//   pick: nightRecapPick (yesterday's signal) — used for matchup, edge,
//         clv, profit_units, result
//   gamesScanned: total games yesterday (data.games_analyzed equivalent)
//   signalsIssued: 0 or 1 derived from pick presence + non-revoked
//   onClick: opens the resolution detail screen for the pick

const SP = {
  surface: '#121725',
  border: 'rgba(255, 255, 255, 0.08)',
  border2: 'rgba(255, 255, 255, 0.05)',
  green: '#5A9E72',
  redSoft: '#C4868A',
  text: '#E8EAED',
  text2: 'rgba(232, 234, 237, 0.7)',
  text3: 'rgba(232, 234, 237, 0.5)',
  text4: 'rgba(232, 234, 237, 0.35)',
  fontMono: "'JetBrains Mono', 'Menlo', ui-monospace, monospace",
  fontSerif: "'IBM Plex Serif', Georgia, serif",
  fontSans: "'Inter', -apple-system, BlinkMacSystemFont, sans-serif",
};

function fmtDateShort(iso) {
  if (!iso) return '';
  try {
    const d = new Date(iso + (iso.length === 10 ? 'T12:00:00Z' : ''));
    if (Number.isNaN(d.getTime())) return iso;
    return new Intl.DateTimeFormat('en-US', {
      timeZone: 'America/New_York',
      month: 'long', day: 'numeric', year: 'numeric',
    }).format(d);
  } catch { return iso; }
}

export default function LastNightsReadCard({
  pick, gamesScanned, signalsIssued, dateIso, onClick,
}) {
  const result = (pick?.result || '').toLowerCase();
  const isWin = result === 'win';
  const isLoss = result === 'loss';
  const isPush = result === 'push';
  const isRevoked = result === 'revoked';
  const noSignal = !pick && (signalsIssued || 0) === 0;

  const title = (() => {
    if (isRevoked) return 'Signal withdrawn before tip.';
    if (noSignal) return 'The slate closed quiet.';
    if (isWin) return 'The model held against close.';
    if (isLoss) return 'Variance is the cost of doing business.';
    if (isPush) return 'Capital preserved on a tight market.';
    if (signalsIssued > 0) return `${signalsIssued} signal${signalsIssued === 1 ? '' : 's'} issued. Slate closed.`;
    return 'Slate closed.';
  })();

  const excerpt = (() => {
    if (isRevoked) {
      return `Pre-tip validation pulled the signal before first pitch. Capital preserved on a slate of ${gamesScanned || 0} games.`;
    }
    if (noSignal) {
      return `${gamesScanned || 0} games scanned, zero signals issued. Capital preserved on a slate the model read as efficient.`;
    }
    if (isWin) {
      return `Signal cleared at +${Number(pick?.edge_pct || 0).toFixed(1)}%. The model's read held against close.`;
    }
    if (isLoss) {
      return `Signal lost. Edge was real at +${Number(pick?.edge_pct || 0).toFixed(1)}%, outcome fell within expected variance. CLV held against close.`;
    }
    if (isPush) {
      return 'Result graded as a push. Capital preserved on a market the system read as efficient.';
    }
    return `${gamesScanned || 0} games scanned, ${signalsIssued || 0} signal${signalsIssued === 1 ? '' : 's'} issued.`;
  })();

  const clvNum = pick?.clv != null ? parseFloat(pick.clv) : null;
  const clvLabel = clvNum != null
    ? `${clvNum > 0 ? '+' : ''}${clvNum.toFixed(1)}`
    : '—';
  const clvColor = clvNum == null ? SP.text3 : clvNum > 0 ? SP.green : clvNum < 0 ? SP.redSoft : SP.text2;

  const isClickable = typeof onClick === 'function' && !!pick;

  return (
    <div style={{
      background: SP.surface,
      border: `1px solid ${SP.border}`,
      borderRadius: '14px',
      padding: '22px',
      marginBottom: '22px',
      cursor: isClickable ? 'pointer' : 'default',
      fontFamily: SP.fontSans,
    }}
      onClick={isClickable ? onClick : undefined}
      role={isClickable ? 'button' : undefined}
      tabIndex={isClickable ? 0 : undefined}
      onKeyDown={isClickable ? (e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); onClick(); } } : undefined}
    >
      <div style={{
        display: 'flex', gap: '8px', alignItems: 'center', marginBottom: '14px',
        fontFamily: SP.fontMono, fontSize: '9px', fontWeight: 500,
        letterSpacing: '0.22em', textTransform: 'uppercase', color: SP.text3,
      }}>
        <span style={{ color: SP.green, display: 'inline-flex', alignItems: 'center', gap: '5px' }}>
          <span style={{ width: 5, height: 5, background: SP.green, borderRadius: '50%' }} />
          Sharp Journal
        </span>
        <span style={{ color: SP.text4 }}>·</span>
        <span>Evening Edition</span>
      </div>

      <h2 style={{
        fontFamily: SP.fontSerif, fontSize: '20px', fontWeight: 600,
        color: SP.text, lineHeight: 1.25, margin: '0 0 8px',
      }}>{title}</h2>

      <p style={{
        fontSize: '13px', lineHeight: 1.55, color: SP.text2, margin: '0 0 18px',
      }}>{excerpt}</p>

      <div style={{
        display: 'grid', gridTemplateColumns: '1fr 1px 1fr 1px 1fr',
        background: '#0A0D14', border: `1px solid ${SP.border}`,
        borderRadius: '10px', overflow: 'hidden', marginBottom: '16px',
      }}>
        {[
          { label: 'Games', value: String(gamesScanned ?? 0), color: SP.text },
          { label: 'Signals', value: String(signalsIssued ?? 0), color: SP.text },
          { label: 'CLV vs close', value: clvLabel, color: clvColor },
        ].flatMap((cell, i, arr) => [
          <div key={`l-${cell.label}`} style={{ padding: '14px 8px 12px', textAlign: 'center' }}>
            <div style={{
              fontFamily: SP.fontMono, fontSize: '9px',
              letterSpacing: '0.22em', textTransform: 'uppercase', color: SP.text4,
              marginBottom: '5px',
            }}>{cell.label}</div>
            <div style={{
              fontFamily: SP.fontMono, fontSize: '16px', fontWeight: 500,
              color: cell.color, lineHeight: 1,
            }}>{cell.value}</div>
          </div>,
          i < arr.length - 1 ? <div key={`ld-${i}`} style={{ background: SP.border }} /> : null,
        ])}
      </div>

      <div style={{
        display: 'flex', justifyContent: 'space-between', alignItems: 'center',
        paddingTop: '14px', borderTop: `1px solid ${SP.border2}`,
      }}>
        <span style={{
          fontFamily: SP.fontMono, fontSize: '10px', color: SP.text4,
          letterSpacing: '0.04em',
        }}>{fmtDateShort(dateIso)}</span>
        {isClickable && (
          <span style={{
            fontFamily: SP.fontMono, fontSize: '10px', fontWeight: 500,
            letterSpacing: '0.22em', textTransform: 'uppercase', color: SP.green,
            display: 'inline-flex', alignItems: 'center', gap: '5px',
          }}>
            Read
            <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
              <path d="M9 18l6-6-6-6" />
            </svg>
          </span>
        )}
      </div>
    </div>
  );
}
