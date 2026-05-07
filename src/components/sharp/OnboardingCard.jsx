import { useOnboardingCard } from '../../hooks/useOnboardingCard';

// OnboardingCard: small dismissible intro/welcome cards used across tabs
// (Sharp Journal intro, Your First Signal, Calibration callouts, etc.).
// May 2026 — refreshed to v4.3 canonical tokens. Same dismiss API
// (useOnboardingCard) and same prop surface (cardId, title, children).
//
// Visual: top-edge green gradient accent (matches DTS / DailyMarketReport
// pattern), v4.3 surface + border, eyebrow in JetBrains Mono / 10px /
// 0.22em letter-spacing / canonical green, body in 13px Inter at 70%
// text. X close button is an inline SVG with a 28px touch target.

const SP = {
  surface: '#121725',
  border: 'rgba(255, 255, 255, 0.08)',
  green: '#5A9E72',
  text: '#E8EAED',
  text2: 'rgba(232, 234, 237, 0.7)',
  text3: 'rgba(232, 234, 237, 0.5)',
  text4: 'rgba(232, 234, 237, 0.35)',
  fontSans: "'Inter', -apple-system, BlinkMacSystemFont, sans-serif",
  fontMono: "'JetBrains Mono', 'Menlo', ui-monospace, monospace",
};

export default function OnboardingCard({ cardId, title, children }) {
  const { visible, dismiss } = useOnboardingCard(cardId);
  if (!visible) return null;

  return (
    <div style={{
      position: 'relative',
      background: SP.surface,
      border: `1px solid ${SP.border}`,
      borderRadius: '12px',
      padding: '18px 20px',
      marginBottom: '16px',
      overflow: 'hidden',
      fontFamily: SP.fontSans,
    }}>
      <div aria-hidden style={{
        position: 'absolute', top: 0, left: 16, right: 16, height: '2px',
        background: `linear-gradient(90deg, transparent, ${SP.green} 20%, ${SP.green} 80%, transparent)`,
        opacity: 0.7,
      }} />
      {title && (
        <div style={{
          fontFamily: SP.fontMono, fontSize: '10px', fontWeight: 500,
          letterSpacing: '0.22em', textTransform: 'uppercase', color: SP.green,
          marginBottom: '8px', paddingRight: '24px',
        }}>{title}</div>
      )}
      <div style={{
        fontSize: '13px', lineHeight: 1.55, color: SP.text2,
        paddingRight: '24px',
      }}>{children}</div>
      <button
        type="button"
        onClick={dismiss}
        aria-label="Dismiss"
        style={{
          position: 'absolute', top: '8px', right: '8px',
          width: '28px', height: '28px',
          display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
          background: 'transparent', border: 'none', cursor: 'pointer',
          color: SP.text3, padding: 0, borderRadius: '6px',
        }}
        onMouseEnter={(e) => { e.currentTarget.style.color = SP.text; }}
        onMouseLeave={(e) => { e.currentTarget.style.color = SP.text3; }}
      >
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M18 6L6 18M6 6l12 12" />
        </svg>
      </button>
    </div>
  );
}
