import { useEffect } from 'react';

// CalibrationBanner: the locked v4.3 amber pattern for "live / in-progress
// / calibration" framing. Used everywhere a sport is in calibration phase
// (MLB, WNBA), the slate is mid-results (Sharp Journal evening edition),
// or a market-intelligence read is settling in real time.
//
// Replaces the older blue "Model Phase: Calibration" strip and the green
// "CALIBRATION BETA" onboarding callout. Per BRAND_SPEC v4.3:
//   - amber #F59E0B is the calibration / live state color (not blue, not green)
//   - blue is reserved for active signals only
//   - green is reserved for verified results only
//
// Spec: docs/design-system/DESIGN_SYSTEM.md section 16.1
//
// Props:
//   eyebrow:  short caps label, e.g. "Calibration Phase · MLB"
//   children: body text, can include <strong> for emphasis
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
      0%   { box-shadow: 0 0 0 0 rgba(245, 158, 11, 0.6); }
      70%  { box-shadow: 0 0 0 8px rgba(245, 158, 11, 0); }
      100% { box-shadow: 0 0 0 0 rgba(245, 158, 11, 0); }
    }
    .sp-calibration-pulse { animation: sp-banner-pulse 2s infinite; }
    @media (prefers-reduced-motion: reduce) {
      .sp-calibration-pulse { animation: none; }
    }
  `;
  document.head.appendChild(style);
  _stylesInjected = true;
}

export default function CalibrationBanner({ eyebrow, children, style }) {
  useEffect(() => { injectStyles(); }, []);

  return (
    <div
      role="status"
      style={{
        background: 'var(--sp-amber-soft, rgba(245, 158, 11, 0.08))',
        border: '1px solid rgba(245, 158, 11, 0.22)',
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
          background: 'var(--sp-amber, #F59E0B)',
          borderRadius: '50%',
        }}
      />
      <div style={{ minWidth: 0, flex: 1 }}>
        {eyebrow && (
          <div
            style={{
              fontFamily: 'var(--sp-font-mono, "JetBrains Mono", monospace)',
              fontSize: '9px',
              letterSpacing: '0.22em',
              textTransform: 'uppercase',
              color: 'var(--sp-amber, #F59E0B)',
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
    </div>
  );
}
