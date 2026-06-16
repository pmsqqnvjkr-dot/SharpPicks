import { getStateTokens, NEUTRAL_TOKENS } from './stateTokens';

// Timeline: vertical-rail timeline used by both empty-state screens.
// Date in the screen's state color (steel on off-season, amber on
// calibration). Each item: date, title, optional label pill, one-line
// note. An optional final node renders in the green "completion" treatment.
//
// Props:
//   state    'steel' | 'amber' | 'green' (default 'steel')
//   items    Array<{
//              id?: string,                key for React list rendering
//              date: string,               mono display string, e.g. "JUN 23-24"
//              title: string,              item heading
//              pill?: string,              optional caps label pill (e.g. "PRIORS")
//              note: string,               one-line description
//              isFinal?: boolean,          green-highlights this node + pill
//            }>
//
// Date display strings are formatted by the caller from ISO config dates
// so each screen controls its own date conventions (e.g. UTC vs local).

const railPadding = '19px';

function TimelineItem({ item, isLast, accent, finalAccent }) {
  const dotAccent = item.isFinal ? finalAccent : accent;
  const dateColor = item.isFinal ? finalAccent.color : accent.color;
  const pillStyle = item.isFinal
    ? {
        color: finalAccent.color,
        borderColor: finalAccent.border,
        background: finalAccent.soft,
      }
    : {
        color: NEUTRAL_TOKENS.text4,
        borderColor: NEUTRAL_TOKENS.hairlineStrong,
        background: 'transparent',
      };

  return (
    <li
      style={{
        position: 'relative',
        padding: `0 0 ${isLast ? '4px' : railPadding} 22px`,
        listStyle: 'none',
      }}
    >
      <span
        aria-hidden="true"
        style={{
          position: 'absolute',
          left: '-4.5px',
          top: '5px',
          width: '8px',
          height: '8px',
          borderRadius: '50%',
          background: item.isFinal ? dotAccent.color : NEUTRAL_TOKENS.bg,
          border: `1.5px solid ${item.isFinal ? dotAccent.color : NEUTRAL_TOKENS.text4}`,
          boxShadow: item.isFinal ? `0 0 0 4px ${dotAccent.soft}` : 'none',
        }}
      />
      <div
        style={{
          fontFamily: NEUTRAL_TOKENS.fontMono,
          fontSize: '10px',
          letterSpacing: '0.18em',
          color: dateColor,
          fontWeight: 600,
          marginBottom: '4px',
        }}
      >
        {item.date}
      </div>
      <div
        style={{
          fontSize: '14px',
          fontWeight: 600,
          color: NEUTRAL_TOKENS.text,
          marginBottom: '3px',
        }}
      >
        {item.title}
        {item.pill && (
          <span
            style={{
              display: 'inline-block',
              fontFamily: NEUTRAL_TOKENS.fontMono,
              fontSize: '9px',
              letterSpacing: '0.14em',
              fontWeight: 600,
              borderRadius: '4px',
              padding: '2px 7px',
              marginLeft: '8px',
              verticalAlign: '1px',
              border: `1px solid ${pillStyle.borderColor}`,
              color: pillStyle.color,
              background: pillStyle.background,
            }}
          >
            {item.pill}
          </span>
        )}
      </div>
      <div
        style={{
          fontSize: '12.5px',
          lineHeight: 1.55,
          color: NEUTRAL_TOKENS.text3,
        }}
      >
        {item.note}
      </div>
    </li>
  );
}

export default function Timeline({ state = 'steel', items = [] }) {
  const accent = getStateTokens(state);
  const finalAccent = getStateTokens('green');
  if (!items.length) return null;
  return (
    <ol
      style={{
        margin: '0 0 0 5px',
        padding: 0,
        borderLeft: `1px solid ${NEUTRAL_TOKENS.hairlineStrong}`,
      }}
    >
      {items.map((item, i) => (
        <TimelineItem
          key={item.id || `${item.date}:${i}`}
          item={item}
          isLast={i === items.length - 1}
          accent={accent}
          finalAccent={finalAccent}
        />
      ))}
    </ol>
  );
}
