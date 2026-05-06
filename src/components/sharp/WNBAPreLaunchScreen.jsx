// Bare-minimum pre-launch screen for the WNBA tab, shown until the
// 2026-05-08 opener. Replaces the normal PicksTab content for sport='wnba'.
// Full design from docs/design-system/wnba-prelaunch-page.html is deferred to
// a follow-up; this version captures the hero + countdown + footer principle
// only so the tab has something coherent to show right now.

const ACCENT_GREEN = '#5A9E72';   // v4.3 sage Edge Green
const AMBER = '#F59E0B';          // calibration / live state
const SURFACE = '#121725';
const BORDER = 'rgba(255, 255, 255, 0.08)';
const TEXT_PRIMARY = '#E8EAED';
const TEXT_2 = 'rgba(232, 234, 237, 0.7)';
const TEXT_3 = 'rgba(232, 234, 237, 0.5)';

function pulseStyle() {
  // CSS pulse keyframes injected once at module-load time. No-op if already
  // present so re-mounts don't duplicate the rule.
  if (typeof document === 'undefined') return null;
  if (!document.getElementById('wnba-pulse-keyframes')) {
    const style = document.createElement('style');
    style.id = 'wnba-pulse-keyframes';
    style.textContent = `
      @keyframes wnba-pulse {
        0%, 100% { opacity: 1; box-shadow: 0 0 0 0 rgba(245, 158, 11, 0.5); }
        50%      { opacity: 0.7; box-shadow: 0 0 0 6px rgba(245, 158, 11, 0); }
      }
      @media (prefers-reduced-motion: reduce) {
        .wnba-pulse-dot { animation: none; }
      }
    `;
    document.head.appendChild(style);
  }
  return null;
}

export default function WNBAPreLaunchScreen() {
  pulseStyle();

  return (
    <div style={{
      padding: '20px 20px calc(100px + env(safe-area-inset-bottom, 0px))',
      maxWidth: '720px',
      margin: '0 auto',
    }}>
      {/* Countdown eyebrow */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        gap: '10px',
        padding: '12px 16px',
        marginBottom: '24px',
        background: 'rgba(245, 158, 11, 0.06)',
        border: `1px solid rgba(245, 158, 11, 0.22)`,
        borderRadius: '10px',
      }}>
        <span
          className="wnba-pulse-dot"
          style={{
            width: '8px',
            height: '8px',
            borderRadius: '50%',
            background: AMBER,
            animation: 'wnba-pulse 2s ease-in-out infinite',
            flexShrink: 0,
          }}
        />
        <span style={{
          fontFamily: 'var(--font-mono)',
          fontSize: '11px',
          fontWeight: 600,
          letterSpacing: '0.18em',
          textTransform: 'uppercase',
          color: AMBER,
        }}>
          First reads · Friday May 8
        </span>
      </div>

      {/* Hero headline */}
      <h1 style={{
        fontFamily: 'var(--font-serif)',
        fontSize: '32px',
        fontWeight: 600,
        lineHeight: 1.15,
        color: TEXT_PRIMARY,
        margin: '0 0 16px',
      }}>
        The model is learning the league.{' '}
        <span style={{ color: ACCENT_GREEN }}>In public.</span>
      </h1>

      {/* Hero subhead */}
      <p style={{
        fontFamily: 'var(--font-sans)',
        fontSize: '15px',
        lineHeight: 1.55,
        color: TEXT_2,
        margin: '0 0 32px',
      }}>
        WNBA signals start firing Friday. Every read shipped, every closing line audited, every miss logged the same as every hit. Confidence levels calibrate as the season builds.
      </p>

      {/* What to expect card */}
      <div style={{
        background: SURFACE,
        border: `1px solid ${BORDER}`,
        borderRadius: '12px',
        padding: '18px 20px',
        marginBottom: '20px',
      }}>
        <div style={{
          fontFamily: 'var(--font-mono)',
          fontSize: '10px',
          fontWeight: 600,
          letterSpacing: '0.18em',
          textTransform: 'uppercase',
          color: TEXT_3,
          marginBottom: '10px',
        }}>
          What to expect
        </div>
        <p style={{
          fontFamily: 'var(--font-sans)',
          fontSize: '14px',
          lineHeight: 1.55,
          color: TEXT_2,
          margin: 0,
        }}>
          Same pipeline as NBA and MLB. Daily slate scan around 9 AM ET, signal published only when an edge clears the threshold, every result graded against the closing line. The Calibration v1 marker stays on the WNBA tab until the model has built a track record worth trusting.
        </p>
      </div>

      {/* Principle footer */}
      <div style={{
        fontFamily: 'var(--font-mono)',
        fontSize: '11px',
        letterSpacing: '0.16em',
        textTransform: 'uppercase',
        color: TEXT_3,
        textAlign: 'center',
        padding: '24px 8px 8px',
      }}>
        Calibration phase. Live signals. Receipts tracked publicly.
      </div>
    </div>
  );
}
