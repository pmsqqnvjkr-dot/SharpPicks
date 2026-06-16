import { useEffect, useState } from 'react';

// CalibrationBanner: the locked v4.3 amber pattern for "live / in-progress
// / calibration" framing. Used everywhere a sport is in calibration phase
// (MLB, WNBA), the slate is mid-results (Sharp Journal evening edition),
// or a market-intelligence read is settling in real time.
//
// Replaces the older blue "Model Phase: Calibration" strip and the green
// "CALIBRATION BETA" onboarding callout. Per BRAND_SPEC v4.3.1:
//   - amber #C9A35C is the calibration / live state color (muted brass;
//     retoned from #C9A35C in June 2026, was too saturated against v4.3
//     surfaces)
//   - blue is reserved for active signals only
//   - green is reserved for verified results only
//
// Spec: docs/design-system/DESIGN_SYSTEM.md section 16.1
//
// Props:
//   eyebrow:     short caps label, e.g. "Calibration Phase · MLB"
//   children:    body text, can include <strong> for emphasis
//   dismissKey:  optional string. When provided, shows an X close button
//                that hides the banner and persists the dismissal in
//                localStorage under `sp_banner_dismissed:<dismissKey>`.
//                Use a stable per-context key, e.g. "calibration-mlb".
//   onDismiss:   optional callback invoked after the user taps X
//
// The pulse animation respects prefers-reduced-motion via CSS.

let _stylesInjected = false;
function injectStyles() {
  if (_stylesInjected || typeof document === 'undefined') return;
  if (document.getElementById('sp-calibration-banner-styles')) {
    _stylesInjected = true;
    return;
  }
  const style = document.createElement('style');
  style.id = 'sp-calibration-banner-styles';
  style.textContent = `
    @keyframes sp-banner-pulse {
      0%   { box-shadow: 0 0 0 0 rgba(201, 163, 92, 0.6); }
      70%  { box-shadow: 0 0 0 8px rgba(201, 163, 92, 0); }
      100% { box-shadow: 0 0 0 0 rgba(201, 163, 92, 0); }
    }
    .sp-calibration-pulse { animation: sp-banner-pulse 2s infinite; }
    @media (prefers-reduced-motion: reduce) {
      .sp-calibration-pulse { animation: none; }
    }
  `;
  document.head.appendChild(style);
  _stylesInjected = true;
}

const STORAGE_PREFIX = 'sp_banner_dismissed:';

function isDismissed(key) {
  if (!key || typeof window === 'undefined') return false;
  try { return window.localStorage.getItem(STORAGE_PREFIX + key) === '1'; } catch { return false; }
}
function persistDismiss(key) {
  if (!key || typeof window === 'undefined') return;
  try { window.localStorage.setItem(STORAGE_PREFIX + key, '1'); } catch { /* noop */ }
}

export default function CalibrationBanner({ eyebrow, children, style, dismissKey, onDismiss }) {
  useEffect(() => { injectStyles(); }, []);
  const [hidden, setHidden] = useState(() => isDismissed(dismissKey));

  if (hidden) return null;

  const handleDismiss = () => {
    persistDismiss(dismissKey);
    setHidden(true);
    if (typeof onDismiss === 'function') onDismiss();
  };

  return (
    <div
      role="status"
      style={{
        position: 'relative',
        background: 'var(--sp-amber-soft, rgba(201, 163, 92, 0.12))',
        border: '1px solid var(--sp-amber-border, rgba(201, 163, 92, 0.40))',
        borderRadius: '10px',
        padding: '14px 16px',
        marginBottom: '16px',
        display: 'flex',
        alignItems: 'flex-start',
        gap: '12px',
        ...style,
      }}
    >
      <div
        className="sp-calibration-pulse"
        style={{
          flexShrink: 0,
          width: '8px',
          height: '8px',
          marginTop: '4px',
          background: 'var(--sp-amber, #C9A35C)',
          borderRadius: '50%',
        }}
      />
      <div style={{ minWidth: 0, flex: 1, paddingRight: dismissKey ? '24px' : 0 }}>
        {eyebrow && (
          <div
            style={{
              fontFamily: 'var(--sp-font-mono, "JetBrains Mono", monospace)',
              fontSize: '9px',
              letterSpacing: '0.22em',
              textTransform: 'uppercase',
              color: 'var(--sp-amber, #C9A35C)',
              fontWeight: 600,
              marginBottom: '4px',
            }}
          >
            {eyebrow}
          </div>
        )}
        <div
          style={{
            fontSize: '12px',
            lineHeight: 1.45,
            color: 'var(--sp-text-2, rgba(232, 234, 237, 0.7))',
          }}
        >
          {children}
        </div>
      </div>
      {dismissKey && (
        <button
          type="button"
          onClick={handleDismiss}
          aria-label="Dismiss banner"
          style={{
            position: 'absolute',
            top: '8px',
            right: '8px',
            width: '28px',
            height: '28px',
            display: 'inline-flex',
            alignItems: 'center',
            justifyContent: 'center',
            background: 'transparent',
            border: 'none',
            cursor: 'pointer',
            color: 'rgba(201, 163, 92, 0.6)',
            padding: 0,
            borderRadius: '6px',
          }}
          onMouseEnter={(e) => { e.currentTarget.style.color = 'rgba(201, 163, 92, 1)'; }}
          onMouseLeave={(e) => { e.currentTarget.style.color = 'rgba(201, 163, 92, 0.6)'; }}
        >
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M18 6L6 18M6 6l12 12" />
          </svg>
        </button>
      )}
    </div>
  );
}
