import { colors, fonts } from '../../../styles/tokens';

export default function HeroCard({
  variant = 'pass',
  date,
  title,
  subtitle,
  verdictText,
  stats,
  tagline = 'One pick beats five.',
  activeDot = 2,
}) {
  const isPass = variant === 'pass';
  const accent = isPass ? colors.signalBlue : colors.edgeGreen;

  return (
    <div style={{
      background: colors.surface1,
      border: `1px solid ${colors.stroke}`,
      borderRadius: 12,
      padding: '22px 22px 18px',
      marginBottom: 14,
      position: 'relative',
    }}>
      {/* Top gradient line */}
      <div style={{
        position: 'absolute',
        top: 0,
        left: 22,
        right: 22,
        height: 1,
        background: `linear-gradient(90deg, transparent, ${accent}, transparent)`,
        opacity: 0.5,
      }} />

      {/* Meta row */}
      <div style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        marginBottom: 14,
      }}>
        <span style={{
          fontFamily: fonts.label,
          fontSize: 9,
          fontWeight: 700,
          letterSpacing: '2.5px',
          textTransform: 'uppercase',
          color: colors.text3,
        }}>
          Today's Signal &middot; {date}
        </span>
        <span style={{
          padding: '6px 12px',
          borderRadius: 6,
          border: `1px solid ${accent}`,
          color: accent,
          fontFamily: fonts.label,
          fontSize: 9,
          letterSpacing: '2.5px',
          fontWeight: 700,
          background: `rgba(${isPass ? '79, 134, 247' : '52, 211, 153'}, 0.06)`,
        }}>
          {isPass ? 'PASS' : 'LEAGUE OFF'}
        </span>
      </div>

      {/* Title */}
      <h1 style={{
        fontFamily: fonts.serif,
        fontSize: 30,
        fontWeight: 500,
        letterSpacing: '-0.015em',
        lineHeight: 1.15,
        margin: '6px 0 8px',
        color: colors.text,
      }}>
        {title}
      </h1>

      {/* Subtitle */}
      <div style={{
        fontFamily: fonts.mono,
        fontSize: 11.5,
        color: colors.text3,
        letterSpacing: '0.05em',
        marginBottom: 18,
        textTransform: 'uppercase',
      }}>
        {subtitle}
      </div>

      {/* Verdict bar */}
      <div style={{
        background: 'rgba(0,0,0,0.25)',
        border: `1px solid ${colors.stroke}`,
        borderRadius: 8,
        padding: '13px 14px',
        display: 'flex',
        alignItems: 'center',
        gap: 11,
      }}>
        <div style={{
          width: 7,
          height: 7,
          borderRadius: '50%',
          background: accent,
          boxShadow: `0 0 10px ${accent}`,
          flexShrink: 0,
        }} />
        <div style={{
          fontFamily: fonts.sans,
          fontSize: 13.5,
          color: colors.text,
          lineHeight: 1.45,
          fontWeight: 400,
        }}>
          {verdictText}
        </div>
      </div>

      {/* Stats grid (pass variant only) */}
      {isPass && stats && (
        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(4, 1fr)',
          borderTop: `1px solid ${colors.stroke}`,
          borderBottom: `1px solid ${colors.stroke}`,
          padding: '16px 0',
          margin: '18px 0 14px',
        }}>
          {stats.map((s, i) => (
            <div key={i} style={{
              textAlign: 'center',
              borderRight: i < stats.length - 1 ? `1px solid ${colors.stroke}` : 'none',
              padding: '0 4px',
            }}>
              <div style={{
                fontFamily: fonts.mono,
                fontSize: 22,
                fontWeight: 700,
                lineHeight: 1,
                marginBottom: 8,
                color: s.color === 'green' ? colors.edgeGreen
                  : s.color === 'dim' ? colors.text3
                  : colors.text,
              }}>
                {s.value}
              </div>
              <div style={{
                fontFamily: fonts.label,
                fontSize: 9,
                letterSpacing: '2.5px',
                color: colors.text3,
                textTransform: 'uppercase',
                fontWeight: 700,
              }}>
                {s.label}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Footer (pass variant only) */}
      {isPass && (
        <div style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
        }}>
          <div style={{
            fontFamily: fonts.sans,
            fontSize: 13,
            fontWeight: 400,
            color: colors.text2,
          }}>
            {tagline}
          </div>
          <div style={{ display: 'flex', gap: 5 }}>
            {[0, 1, 2, 3].map(i => (
              <span key={i} style={{
                width: 5,
                height: 5,
                borderRadius: '50%',
                background: i === activeDot ? colors.signalBlue : colors.text3,
                opacity: i === activeDot ? 1 : 0.4,
              }} />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
