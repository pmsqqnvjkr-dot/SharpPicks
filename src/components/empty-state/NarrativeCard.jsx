import { getStateTokens, NEUTRAL_TOKENS } from './stateTokens';

// NarrativeCard: section label + optional state-colored pill + serif
// title + muted body. Used on the empty-state screens for "Model status"
// blocks ("The off-season retrain is underway.", "Why the wait.").
//
// Props:
//   state    'steel' | 'amber' | 'green' (only consumed when pill is set)
//   eyebrow  optional small caps section label (mono).
//   pill     optional state-colored caps pill rendered on the right edge
//            of the head row (e.g. "IN THE LAB" on the NBA off-season
//            screen). When omitted the head row collapses.
//   title    serif heading.
//   children body text.

export default function NarrativeCard({ state = 'steel', eyebrow, pill, title, children }) {
  const s = getStateTokens(state);
  const hasHead = Boolean(eyebrow || pill);
  return (
    <div
      style={{
        background: NEUTRAL_TOKENS.card,
        border: `1px solid ${NEUTRAL_TOKENS.hairline}`,
        borderRadius: '12px',
        padding: '18px',
      }}
    >
      {hasHead && (
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            marginBottom: '10px',
          }}
        >
          {eyebrow ? (
            <div
              style={{
                fontFamily: NEUTRAL_TOKENS.fontMono,
                fontSize: '10.5px',
                letterSpacing: '0.2em',
                color: NEUTRAL_TOKENS.text3,
                fontWeight: 500,
              }}
            >
              {eyebrow}
            </div>
          ) : <span />}
          {pill && (
            <div
              style={{
                fontFamily: NEUTRAL_TOKENS.fontMono,
                fontSize: '9.5px',
                letterSpacing: '0.14em',
                fontWeight: 600,
                color: s.color,
                background: s.soft,
                border: `1px solid ${s.border}`,
                padding: '4px 9px',
                borderRadius: '4px',
              }}
            >
              {pill}
            </div>
          )}
        </div>
      )}
      {title && (
        <div
          style={{
            fontFamily: NEUTRAL_TOKENS.fontSerif,
            fontSize: '18px',
            fontWeight: 600,
            color: NEUTRAL_TOKENS.text,
            marginBottom: '7px',
            lineHeight: 1.25,
          }}
        >
          {title}
        </div>
      )}
      <div
        style={{
          fontSize: '13px',
          lineHeight: 1.6,
          color: NEUTRAL_TOKENS.text3,
        }}
      >
        {children}
      </div>
    </div>
  );
}
