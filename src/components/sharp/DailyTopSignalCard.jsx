import { getTrialCtaSubtext } from '../../utils/platformCta';

// DailyTopSignalCard: the v4.3 paywalled signal card shown on the home
// screen when a free user has a qualified edge waiting. Real structure
// is preserved (sport tag, calibration tag, headline with edge percent,
// 4-cell stat grid) but the four stat values are CSS-blurred so the
// user can see the shape of what they would unlock without giving away
// the bet.
//
// Spec: docs/design-system/MIGRATION_CHECKLIST.md P1.4.1
// Mockup: docs/design-system/mlb-home-redesigned.html lines 648-694
//
// Replaces FreePickNotice in the paywalled (unresolved) slot. The
// resolved variant of FreePickNotice still ships separately because
// it has a different job (announce the result, not the upgrade).

function fmtEdge(edgePct) {
  if (edgePct == null) return '';
  const n = parseFloat(edgePct);
  if (Number.isNaN(n)) return '';
  return n > 0 ? `+${n.toFixed(1)}%` : `${n.toFixed(1)}%`;
}

function getEdgeTier(edgePct) {
  if (edgePct == null) return 'WK';
  const e = Math.abs(parseFloat(edgePct));
  if (e >= 10) return 'STR';
  if (e >= 7) return 'MOD';
  return 'WK';
}

function fmtSize(pick) {
  const pct = pick?.position_size_pct;
  if (pct == null) return '1.0u';
  const n = parseFloat(pct);
  if (Number.isNaN(n)) return '1.0u';
  return `${n.toFixed(1)}u`;
}

function fmtSide(pick) {
  return pick?.side || pick?.away_team || '—';
}

function fmtLine(pick) {
  if (pick?.line == null) return '—';
  const n = parseFloat(pick.line);
  if (Number.isNaN(n)) return '—';
  return n > 0 ? `+${n}` : `${n}`;
}

// Derive a non-leaking sub-headline from the model signals. The first
// signal usually starts with a category prefix ("Bullpen edge: ...",
// "Schedule density: ...", "Model edge: ..."). We take the prefix and
// pad with a generic descriptor so the user sees the *type* of edge
// without seeing the team or specific bet.
function describeEdgeType(pick) {
  const first = pick?.model_signals?.[0] || pick?.signals?.[0];
  if (typeof first === 'string' && first.includes(':')) {
    const prefix = first.split(':')[0].trim();
    if (prefix && prefix.length < 40) {
      return `${prefix} flagged by the model. Full breakdown inside.`;
    }
  }
  return 'A qualified signal cleared the threshold. Full breakdown inside.';
}

export default function DailyTopSignalCard({ pick, sport, onUpgrade }) {
  const sportLabel = (sport || pick?.sport || 'mlb').toUpperCase();
  const isCalibration = pick?.model_phase === 'calibration';
  const tier = getEdgeTier(pick?.edge_pct);
  const trialSubtext = getTrialCtaSubtext();

  return (
    <div
      style={{
        background: 'var(--sp-surface, #121725)',
        border: '1px solid rgba(255, 255, 255, 0.08)',
        borderRadius: '16px',
        overflow: 'hidden',
        position: 'relative',
        marginBottom: '22px',
      }}
    >
      {/* top accent line, sage green */}
      <div
        style={{
          position: 'absolute',
          top: 0,
          left: '20px',
          right: '20px',
          height: '2px',
          background:
            'linear-gradient(90deg, transparent, var(--sp-green, #5A9E72) 20%, var(--sp-green, #5A9E72) 80%, transparent)',
          opacity: 0.6,
        }}
      />

      {/* HEADER */}
      <div style={{ padding: '22px 22px 18px', borderBottom: '1px solid rgba(255, 255, 255, 0.05)' }}>
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            flexWrap: 'wrap',
            marginBottom: '14px',
          }}
        >
          <span
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              padding: '4px 10px',
              border: '1px solid var(--sp-green, #5A9E72)',
              borderRadius: '4px',
              fontFamily: 'var(--sp-font-mono, "JetBrains Mono", monospace)',
              fontSize: '9px',
              fontWeight: 500,
              letterSpacing: '0.2em',
              textTransform: 'uppercase',
              color: 'var(--sp-green, #5A9E72)',
            }}
          >
            {sportLabel}
          </span>
          {isCalibration && (
            <span
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '5px',
                padding: '4px 10px',
                border: '1px solid var(--sp-amber, #F59E0B)',
                borderRadius: '4px',
                fontFamily: 'var(--sp-font-mono, "JetBrains Mono", monospace)',
                fontSize: '9px',
                fontWeight: 500,
                letterSpacing: '0.16em',
                textTransform: 'uppercase',
                color: 'var(--sp-amber, #F59E0B)',
              }}
            >
              <span
                style={{
                  width: '5px',
                  height: '5px',
                  background: 'var(--sp-amber, #F59E0B)',
                  borderRadius: '50%',
                }}
              />
              Calibration v1
            </span>
          )}
        </div>

        <h2
          style={{
            fontFamily: '"IBM Plex Serif", Georgia, serif',
            fontSize: '22px',
            fontWeight: 600,
            color: 'var(--sp-text, #E8EAED)',
            lineHeight: 1.25,
            marginBottom: '6px',
            margin: 0,
          }}
        >
          A qualified edge fired tonight.{' '}
          <span style={{ color: 'var(--sp-green, #5A9E72)' }}>{fmtEdge(pick?.edge_pct)}</span>
        </h2>
        <p
          style={{
            fontSize: '13px',
            color: 'var(--sp-text-2, rgba(232, 234, 237, 0.7))',
            lineHeight: 1.5,
            marginTop: '6px',
            marginBottom: 0,
          }}
        >
          {describeEdgeType(pick)}
        </p>
      </div>

      {/* OBSCURED 4-CELL STATS GRID */}
      <div
        style={{
          background: 'var(--sp-bg, #0A0D14)',
          display: 'grid',
          gridTemplateColumns: '1fr 1px 1fr 1px 1fr 1px 1fr',
          position: 'relative',
        }}
      >
        {[
          { label: 'Side', value: fmtSide(pick), serif: false },
          { label: 'Line', value: fmtLine(pick), serif: false },
          { label: 'Tier', value: tier, serif: true },
          { label: 'Size', value: fmtSize(pick), serif: false },
        ].flatMap((cell, i) => [
          <div key={`c-${cell.label}`} style={{ padding: '18px 8px 14px', textAlign: 'center' }}>
            <div
              style={{
                fontFamily: 'var(--sp-font-mono, "JetBrains Mono", monospace)',
                fontSize: '9px',
                letterSpacing: '0.22em',
                textTransform: 'uppercase',
                color: 'var(--sp-text-3, rgba(232, 234, 237, 0.45))',
                marginBottom: '8px',
              }}
            >
              {cell.label}
            </div>
            <div
              style={{
                fontFamily: cell.serif
                  ? '"IBM Plex Serif", Georgia, serif'
                  : 'var(--sp-font-mono, "JetBrains Mono", monospace)',
                fontSize: cell.serif ? '18px' : '16px',
                fontWeight: cell.serif ? 600 : 500,
                color: 'var(--sp-text, #E8EAED)',
                lineHeight: 1,
                filter: 'blur(6px)',
                userSelect: 'none',
                pointerEvents: 'none',
                opacity: 0.7,
              }}
            >
              {cell.value}
            </div>
          </div>,
          i < 3 ? <div key={`d-${i}`} style={{ background: 'rgba(255, 255, 255, 0.06)' }} /> : null,
        ])}
      </div>

      {/* UNLOCK STRIP */}
      <div
        style={{
          padding: '20px 22px',
          background: 'linear-gradient(180deg, transparent, rgba(90, 158, 114, 0.04))',
        }}
      >
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '10px',
            marginBottom: '14px',
            fontFamily: 'var(--sp-font-mono, "JetBrains Mono", monospace)',
            fontSize: '11px',
            color: 'var(--sp-text-3, rgba(232, 234, 237, 0.45))',
            letterSpacing: '0.04em',
          }}
        >
          <svg
            width="14"
            height="14"
            viewBox="0 0 24 24"
            fill="none"
            stroke="var(--sp-green, #5A9E72)"
            strokeWidth="2"
            style={{ flexShrink: 0 }}
          >
            <rect x="3" y="11" width="18" height="11" rx="2" />
            <path d="M7 11V7a5 5 0 0 1 10 0v4" />
          </svg>
          <span>Unlock to see side, line, edge breakdown, and Kelly sizing</span>
        </div>
        <button
          onClick={onUpgrade}
          style={{
            width: '100%',
            padding: '14px 16px',
            background: 'var(--sp-green, #5A9E72)',
            border: 'none',
            borderRadius: '10px',
            fontFamily: '"Inter", system-ui, sans-serif',
            fontSize: '14px',
            fontWeight: 600,
            color: '#062019',
            letterSpacing: '0.01em',
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            gap: '8px',
          }}
        >
          Start 14-day free trial
        </button>
        <div
          style={{
            marginTop: '10px',
            fontFamily: 'var(--sp-font-mono, "JetBrains Mono", monospace)',
            fontSize: '10px',
            letterSpacing: '0.18em',
            textTransform: 'uppercase',
            color: 'var(--sp-text-3, rgba(232, 234, 237, 0.45))',
            textAlign: 'center',
          }}
        >
          {trialSubtext}
        </div>
      </div>
    </div>
  );
}
