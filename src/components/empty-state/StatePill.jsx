import { getStateTokens, NEUTRAL_TOKENS } from './stateTokens';

// StatePill: mono pill in a state color. Used as the top-right indicator
// on the empty-state screens (e.g. "NBA OFF-SEASON" steel, "NFL CALIBRATION"
// amber).
//
// Props:
//   state    'steel' | 'amber' | 'green' (default 'steel')
//   children pill label, will be rendered uppercase via CSS letter-spacing.
//            Pass already-uppercase text for predictability across fonts.
//   style    optional style override merged last.

export default function StatePill({ state = 'steel', children, style }) {
  const s = getStateTokens(state);
  return (
    <div
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: '7px',
        fontFamily: NEUTRAL_TOKENS.fontMono,
        fontSize: '10px',
        letterSpacing: '0.16em',
        fontWeight: 600,
        color: s.color,
        background: s.soft,
        border: `1px solid ${s.border}`,
        padding: '6px 12px',
        borderRadius: '999px',
        ...style,
      }}
    >
      <span
        style={{
          width: '5px',
          height: '5px',
          borderRadius: '50%',
          background: s.color,
        }}
      />
      {children}
    </div>
  );
}
