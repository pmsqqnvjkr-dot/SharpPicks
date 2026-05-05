import { inst as c, instFonts as f } from '../../../styles/tokens';

export default function HeroCard({
  variant = 'pass',
  date,
  title,
  subtitle,
  verdictText,
  stats,
  tagline = 'One pick beats five.',
  bulletPoints,
}) {
  const isPass = variant === 'pass';
  const accent = isPass ? c.system : c.edge;
  const accentBg = isPass ? c.systemBg : c.edgeBg;
  const accentBorder = isPass ? c.systemBorder : c.edgeBorder;

  return (
    <div style={{
      background: c.bgCard,
      border: `1px solid ${c.borderSubtle}`,
      borderRadius: 18,
      padding: '22px 22px 20px',
      marginBottom: 14,
      position: 'relative',
      overflow: 'hidden',
    }}>
      {/* Meta row */}
      <div style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        marginBottom: 24,
      }}>
        <span style={{
          fontFamily: f.mono,
          fontSize: 10,
          fontWeight: 500,
          letterSpacing: '0.18em',
          color: c.textTertiary,
        }}>
          TODAY'S SIGNAL · {(date || '').toUpperCase()}
        </span>
        <span style={{
          padding: '6px 12px',
          borderRadius: 6,
          border: `1px solid ${accentBorder}`,
          color: accent,
          fontFamily: f.mono,
          fontSize: 10,
          fontWeight: 600,
          letterSpacing: '0.18em',
          background: accentBg,
        }}>
          {isPass ? 'PASS' : 'LEAGUE OFF'}
        </span>
      </div>

      {/* Headline */}
      <h1 style={{
        fontFamily: f.serif,
        fontSize: 32,
        fontWeight: 500,
        letterSpacing: '-0.02em',
        lineHeight: 1.05,
        margin: '0 0 18px',
        color: c.textPrimary,
      }}>
        {renderTitle(title)}
      </h1>

      {/* Scan summary */}
      <div style={{
        fontFamily: f.mono,
        fontSize: 11.5,
        color: c.textTertiary,
        letterSpacing: '0.04em',
        lineHeight: 1.6,
        marginBottom: 22,
        textTransform: 'uppercase',
      }}>
        {renderSubtitle(subtitle)}
      </div>

      {/* Static diagnostic bullets (preferred) or single verdict line. */}
      {bulletPoints && bulletPoints.length > 0 ? (
        <ul style={{
          background: c.bgCardElev,
          border: `1px solid ${c.borderSubtle}`,
          borderLeft: `2px solid ${c.system}`,
          borderRadius: 10,
          padding: '14px 16px 14px 32px',
          margin: '0 0 22px',
          listStyle: 'none',
        }}>
          {bulletPoints.map((p, i) => (
            <li key={i} style={{
              fontFamily: f.sans,
              fontSize: 14,
              lineHeight: 1.5,
              color: c.textPrimary,
              position: 'relative',
              marginBottom: i < bulletPoints.length - 1 ? 8 : 0,
            }}>
              <span style={{
                position: 'absolute',
                left: -16,
                color: c.system,
              }}>·</span>
              <span dangerouslySetInnerHTML={{ __html: p }} />
            </li>
          ))}
        </ul>
      ) : verdictText ? (
        <div style={{
          background: c.bgCardElev,
          border: `1px solid ${c.borderSubtle}`,
          borderLeft: `2px solid ${c.system}`,
          borderRadius: 10,
          padding: '14px 16px',
          marginBottom: 22,
        }}>
          <div
            style={{
              fontFamily: f.sans,
              fontSize: 14,
              lineHeight: 1.5,
              color: c.textPrimary,
            }}
            dangerouslySetInnerHTML={{ __html: verdictText }}
          />
        </div>
      ) : null}

      {/* Stats grid (pass variant only) */}
      {isPass && stats && (
        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(4, 1fr)',
          borderTop: `1px solid ${c.borderSubtle}`,
          borderBottom: `1px solid ${c.borderSubtle}`,
          margin: '0 -22px',
        }}>
          {stats.map((s, i) => (
            <div key={i} style={{
              padding: '18px 8px',
              textAlign: 'center',
              borderRight: i < stats.length - 1 ? `1px solid ${c.borderSubtle}` : 'none',
            }}>
              <div style={{
                fontFamily: f.mono,
                fontSize: 24,
                fontWeight: s.color === 'dim' ? 400 : 500,
                lineHeight: 1,
                marginBottom: 6,
                color: s.color === 'green' ? c.edge
                  : s.color === 'dim' ? c.textMuted
                  : c.textPrimary,
              }}>
                {s.value}
              </div>
              <div style={{
                fontFamily: f.mono,
                fontSize: 9,
                letterSpacing: '0.14em',
                color: c.textTertiary,
                textTransform: 'uppercase',
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
          padding: '18px 22px 4px',
          margin: '0 -22px',
        }}>
          <div style={{
            fontFamily: f.serif,
            fontStyle: 'italic',
            fontSize: 13,
            fontWeight: 400,
            color: c.textSecondary,
          }}>
            {tagline}
          </div>
        </div>
      )}
    </div>
  );
}

// Render the title and italicize/green-ify the word "edge" if present.
function renderTitle(title) {
  if (!title) return null;
  if (typeof title !== 'string') return title;
  const lower = title.toLowerCase();
  const idx = lower.indexOf('edge');
  if (idx === -1) return title;
  const before = title.slice(0, idx);
  const word = title.slice(idx, idx + 4);
  const after = title.slice(idx + 4);
  return (
    <>
      {before}
      <span style={{ fontStyle: 'italic', color: '#4ADE80' }}>{word}</span>
      {after}
    </>
  );
}

// Color edge percent values inside the scan summary.
function renderSubtitle(subtitle) {
  if (!subtitle || typeof subtitle !== 'string') return subtitle;
  const parts = subtitle.split(/(\+\d+(?:\.\d+)?%)/g);
  return parts.map((part, i) => {
    if (/^\+\d+(?:\.\d+)?%$/.test(part)) {
      const isFirstEdge = parts.slice(0, i).filter(p => /^\+\d+(?:\.\d+)?%$/.test(p)).length === 0;
      return (
        <span key={i} style={{
          color: isFirstEdge ? '#4ADE80' : '#9BA8C2',
          fontWeight: 500,
        }}>{part}</span>
      );
    }
    return <span key={i}>{part}</span>;
  });
}
