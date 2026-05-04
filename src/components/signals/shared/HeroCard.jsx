import { inst as c, instFonts as f } from '../../../styles/tokens';

export default function HeroCard({
  variant = 'pass',
  date,
  sport,
  title,
  subtitle,
  verdictText,
  stats,
  tagline = 'One pick beats five.',
  commentary,
  commentaryIdx = 0,
  commentaryCount = 0,
  onTapCommentary,
  metaSignalLabel = 'NO QUALIFYING SIGNAL',
}) {
  const isPass = variant === 'pass';
  const accent = isPass ? c.system : c.edge;
  const accentBg = isPass ? c.systemBg : c.edgeBg;
  const accentBorder = isPass ? c.systemBorder : c.edgeBorder;

  return (
    <div style={{
      background: c.bgCard,
      border: `1px solid ${c.borderSubtle}`,
      borderRadius: 16,
      padding: 18,
      marginBottom: 10,
      position: 'relative',
      overflow: 'hidden',
    }}>
      {isPass && (
        <div style={{
          position: 'absolute',
          top: -1,
          left: -1,
          right: -1,
          height: 2,
          background: c.edge,
          borderTopLeftRadius: 16,
          borderTopRightRadius: 16,
          pointerEvents: 'none',
        }} />
      )}

      {isPass ? (
        <div style={{
          fontFamily: f.mono,
          fontSize: 11,
          fontWeight: 500,
          letterSpacing: '0.14em',
          color: c.textTertiary,
          textTransform: 'uppercase',
          marginBottom: 12,
        }}>
          <span style={{ color: c.textSecondary }}>{(sport || 'NBA').toUpperCase()}</span>
          <span style={{ color: c.textMuted, margin: '0 8px' }}>—</span>
          <span>{(date || '').toUpperCase()}</span>
          <span style={{ color: c.textMuted, margin: '0 8px' }}>·</span>
          <span>{metaSignalLabel}</span>
        </div>
      ) : (
        <div style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          marginBottom: 18,
        }}>
          <span style={{
            fontFamily: f.mono,
            fontSize: 10,
            fontWeight: 500,
            letterSpacing: '0.16em',
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
            letterSpacing: '0.16em',
            background: accentBg,
          }}>
            LEAGUE OFF
          </span>
        </div>
      )}

      {isPass ? (
        <div style={{
          display: 'flex',
          alignItems: 'flex-start',
          justifyContent: 'space-between',
          gap: 12,
          marginBottom: 14,
        }}>
          <h1 style={{
            fontFamily: f.serif,
            fontSize: 26,
            fontWeight: 600,
            letterSpacing: '-0.02em',
            lineHeight: 1.05,
            margin: 0,
            color: c.textPrimary,
            flex: 1,
            minWidth: 0,
          }}>
            {renderTitle(title)}
          </h1>
          <span style={{
            marginTop: 6,
            padding: '4px 9px',
            borderRadius: 5,
            border: `1px solid ${accentBorder}`,
            color: accent,
            fontFamily: f.mono,
            fontSize: 9,
            fontWeight: 600,
            letterSpacing: '0.16em',
            background: accentBg,
            flexShrink: 0,
            textTransform: 'uppercase',
            lineHeight: 1.2,
          }}>
            PASS
          </span>
        </div>
      ) : (
        <h1 style={{
          fontFamily: f.serif,
          fontSize: 26,
          fontWeight: 600,
          letterSpacing: '-0.02em',
          lineHeight: 1.05,
          margin: '0 0 14px',
          color: c.textPrimary,
        }}>
          {renderTitle(title)}
        </h1>
      )}

      <div style={{
        fontFamily: f.mono,
        fontSize: 11.5,
        color: c.textTertiary,
        letterSpacing: '0.04em',
        lineHeight: 1.6,
        marginBottom: 16,
        textTransform: 'uppercase',
      }}>
        {renderSubtitle(subtitle)}
      </div>

      {(verdictText || commentary) && (
        <div
          onClick={onTapCommentary}
          style={{
            background: c.bgNested,
            border: `1px solid ${c.borderSubtle}`,
            borderRadius: 8,
            padding: '12px 14px',
            marginBottom: 14,
            cursor: onTapCommentary ? 'pointer' : 'default',
            WebkitTapHighlightColor: 'transparent',
            userSelect: 'none',
            WebkitUserSelect: 'none',
          }}
        >
          {isPass && (
            <div style={{
              fontFamily: f.mono,
              fontSize: 10,
              fontWeight: 600,
              letterSpacing: '0.16em',
              textTransform: 'uppercase',
              color: c.system,
              marginBottom: 8,
            }}>
              Market Read
            </div>
          )}
          <div
            key={commentaryIdx}
            style={{
              fontFamily: f.sans,
              fontSize: 14,
              lineHeight: 1.5,
              color: c.textPrimary,
              marginBottom: commentaryCount > 1 ? 10 : 0,
              animation: 'sp-fade-in 0.4s ease-out',
            }}
            dangerouslySetInnerHTML={{ __html: commentary || verdictText }}
          />
          {commentaryCount > 1 && (
            <div style={{
              display: 'flex',
              gap: 5,
              alignItems: 'center',
              justifyContent: 'flex-end',
            }}>
              {Array.from({ length: commentaryCount }).map((_, i) => (
                <span key={i} style={{
                  width: 5,
                  height: 5,
                  borderRadius: '50%',
                  background: i === commentaryIdx ? c.system : c.textMuted,
                  transition: 'background 0.2s',
                }} />
              ))}
            </div>
          )}
        </div>
      )}

      {isPass && stats && (
        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(4, 1fr)',
          gap: 6,
          marginBottom: 14,
        }}>
          {stats.map((s, i) => (
            <div key={i} style={{
              background: c.bgNested,
              border: `1px solid ${c.borderSubtle}`,
              borderRadius: 8,
              padding: '12px 6px 10px',
              textAlign: 'center',
            }}>
              <div style={{
                fontFamily: f.mono,
                fontSize: 9,
                letterSpacing: '0.16em',
                color: c.textTertiary,
                textTransform: 'uppercase',
                marginBottom: 6,
              }}>
                {s.label}
              </div>
              <div style={{
                fontFamily: f.mono,
                fontSize: 18,
                fontWeight: s.color === 'dim' ? 400 : 500,
                lineHeight: 1,
                color: s.color === 'green' ? c.edge
                  : s.color === 'dim' ? c.textMuted
                  : c.textPrimary,
              }}>
                {s.value}
              </div>
            </div>
          ))}
        </div>
      )}

      {isPass && (
        <div style={{
          fontFamily: f.serif,
          fontStyle: 'italic',
          fontSize: 13,
          fontWeight: 400,
          color: c.textSecondary,
          marginTop: 4,
        }}>
          {tagline}
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
