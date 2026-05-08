// LastNightsReadCard — Sharp Journal evening recap tile for the post-midnight
// home view. Editorial format (eyebrow / serif title / excerpt / 3-stat row /
// date + Read → CTA) matching the May 2026 Midnight State mockup.
//
// Tap routes to the Sharp Journal evening edition rendered by the Flask
// app at /market-report/<date>/evening?sport=<sport>&app=1. The ?app=1
// query strips the "Start Free Trial" CTAs (in templates/content/base.html
// and templates/content/market_report.html) so the page complies with
// Apple 3.1.1 and the same URL works for iOS, Android, and web.
// onClick is preserved as a fallback for legacy callers that route to
// ResolutionScreen instead of the journal.
//
// Pulls from already-fetched home data:
//   pick: nightRecapPick (yesterday's signal) — used for matchup, edge,
//         clv, profit_units, result
//   gamesScanned: total games yesterday (data.games_analyzed equivalent)
//   signalsIssued: 0 or 1 derived from pick presence + non-revoked
//   sport: sport key for the evening-edition URL query param
//   journalUrl (optional): override the default evening-edition URL

import { Capacitor } from '@capacitor/core';

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
  sport = 'nba',
  journalUrl,  // override; defaults to /market-report/<date>/evening?sport=<sport>
  // clv: numeric value (null when no source available). PicksTab passes
  //   either the night's single-pick CLV (graded W/L/Push) or the season
  //   aggregate from /api/public/stats?sport=X so the cell always shows
  //   a populated, sport-specific value instead of '—'.
  // clvLabel: 'CLV vs close' (single-pick) | 'Avg CLV (season)' (aggregate).
  clv, clvLabel,
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

  // MLB tips with first pitch; basketball (NBA, WNBA) uses tipoff.
  const tipNoun = (String(sport || '').toLowerCase() === 'mlb') ? 'first pitch' : 'tipoff';

  const excerpt = (() => {
    if (isRevoked) {
      return `Pre-tip validation pulled the signal before ${tipNoun}. Capital preserved on a slate of ${gamesScanned || 0} games.`;
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

  // Prefer caller-provided clv (PicksTab supplies either the night's
  // single-pick CLV or the sport-scoped season aggregate); fall back to
  // the pick's own clv field for backwards compat.
  const clvNum = clv != null
    ? Number(clv)
    : (pick?.clv != null ? parseFloat(pick.clv) : null);
  const clvValueLabel = clvNum != null
    ? `${clvNum > 0 ? '+' : ''}${clvNum.toFixed(1)}`
    : '—';
  const clvColor = clvNum == null ? SP.text3 : clvNum > 0 ? SP.green : clvNum < 0 ? SP.redSoft : SP.text2;
  const clvCellLabel = clvLabel || 'CLV vs close';

  // Build the Sharp Journal evening-edition URL from the date the recap is
  // showing. The Flask app renders at /market-report/<date>/evening; we
  // open this URL via the Capacitor in-app browser on iOS, or a new tab
  // on web. Falls back to the onClick callback for legacy callers (e.g.
  // routing to ResolutionScreen) when no journalUrl can be built.
  const computedJournalUrl = (() => {
    if (journalUrl) return journalUrl;
    if (!dateIso) return null;
    // dateIso may be 'YYYY-MM-DD' or full ISO; we want just the date.
    const ymd = String(dateIso).slice(0, 10);
    if (!/^\d{4}-\d{2}-\d{2}$/.test(ymd)) return null;
    const sportParam = encodeURIComponent(String(sport || 'nba').toLowerCase());
    // ?app=1 tells the Flask SEO base template to swap the "Start Free
    // Trial" CTA for a "← Back to app" button. See base.html.
    return `https://app.sharppicks.ai/market-report/${ymd}/evening?sport=${sportParam}&app=1`;
  })();

  // iOS users now CAN open the journal evening edition. Both the navbar
  // CTA (templates/content/base.html) and the in-content CTA
  // (templates/content/market_report.html) are gated on the ?app=1
  // query the URL builder above always sets, so the page renders
  // without any external payment promo and complies with Apple 3.1.1.
  // The earlier code path that fell back to ResolutionScreen on iOS
  // left pass-day cards (no `pick`) completely unclickable on iPhone.
  const handleOpenJournal = async () => {
    if (computedJournalUrl) {
      try {
        if (Capacitor.isNativePlatform && Capacitor.isNativePlatform()) {
          const { Browser } = await import('@capacitor/browser');
          await Browser.open({ url: computedJournalUrl });
          return;
        }
      } catch { /* fall through to web open */ }
      try { window.open(computedJournalUrl, '_blank', 'noopener,noreferrer'); return; } catch { /* swallow */ }
    }
    if (typeof onClick === 'function') onClick();
  };

  const isClickable = !!computedJournalUrl
    || (typeof onClick === 'function' && !!pick);

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
      onClick={isClickable ? handleOpenJournal : undefined}
      role={isClickable ? 'button' : undefined}
      tabIndex={isClickable ? 0 : undefined}
      onKeyDown={isClickable ? (e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); handleOpenJournal(); } } : undefined}
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
          { label: clvCellLabel, value: clvValueLabel, color: clvColor },
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
