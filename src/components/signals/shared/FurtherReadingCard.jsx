import { useState, useEffect, useRef } from 'react';
import { inst as c, instFonts as f } from '../../../styles/tokens';

// Map a category string to a color tone per spec.
function categoryColor(category) {
  if (!category) return c.textSecondary;
  const k = String(category).toUpperCase();
  if (k.includes('DISCIPLINE')) return c.edge;        // green
  if (k.includes('EDUCATION')) return c.system;        // blue
  if (k.includes('PHILOSOPHY')) return c.system;
  if (k.includes('HOW IT WORKS')) return c.textSecondary;
  if (k.includes('SIGNAL') || k.includes('FOUNDER')) return c.textSecondary;
  return c.edge;
}

export default function FurtherReadingCard({
  title = '',
  snippet = '',
  readMinutes = 0,
  publishedDate = '',
  category = 'Insight',
  source = 'Sharp Journal',
  href,
  onClick,
  rotateKey = 0,
}) {
  const Tag = href ? 'a' : 'button';
  const linkProps = href
    ? { href, target: '_blank', rel: 'noopener noreferrer' }
    : { onClick, type: 'button' };

  const [fading, setFading] = useState(false);
  const lastKey = useRef(rotateKey);

  useEffect(() => {
    if (rotateKey !== lastKey.current) {
      setFading(true);
      const t = setTimeout(() => setFading(false), 280);
      lastKey.current = rotateKey;
      return () => clearTimeout(t);
    }
  }, [rotateKey]);

  const catColor = categoryColor(category);
  const catLabel = String(category || '').toUpperCase();
  const opacity = fading ? 0.3 : 1;

  return (
    <Tag
      {...linkProps}
      style={{
        background: c.bgCard,
        border: `1px solid ${c.borderSubtle}`,
        borderRadius: 18,
        marginBottom: 4,
        overflow: 'hidden',
        display: 'block',
        textDecoration: 'none',
        color: 'inherit',
        cursor: 'pointer',
        transition: 'border-color 0.2s ease',
        width: '100%',
        textAlign: 'left',
        padding: 22,
        position: 'relative',
        WebkitTapHighlightColor: 'transparent',
      }}
      onMouseEnter={e => e.currentTarget.style.borderColor = c.borderMedium}
      onMouseLeave={e => e.currentTarget.style.borderColor = c.borderSubtle}
    >
      {/* Meta row */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        gap: 12,
        marginBottom: 16,
        fontFamily: f.mono,
        fontSize: 11,
        letterSpacing: '0.14em',
        textTransform: 'uppercase',
        opacity,
        transition: 'opacity 0.3s ease',
      }}>
        <span style={{
          color: catColor,
          fontWeight: 600,
        }}>{catLabel}</span>
        <span style={{ color: c.textMuted }}>·</span>
        <span style={{
          color: c.textTertiary,
          letterSpacing: '0.06em',
        }}>{source}</span>
        {readMinutes ? (
          <>
            <span style={{ color: c.textMuted }}>·</span>
            <span style={{
              color: c.textTertiary,
              letterSpacing: '0.06em',
            }}>{readMinutes} MIN</span>
          </>
        ) : null}
      </div>

      {/* Title */}
      <div style={{
        fontFamily: f.serif,
        fontSize: 18,
        fontWeight: 500,
        lineHeight: 1.25,
        letterSpacing: '-0.01em',
        color: c.textPrimary,
        marginBottom: 14,
        opacity,
        transition: 'opacity 0.3s ease',
      }}>
        {title}
      </div>

      {/* Excerpt */}
      <div style={{
        fontFamily: f.sans,
        fontSize: 14,
        lineHeight: 1.55,
        color: c.textSecondary,
        marginBottom: 22,
        opacity,
        transition: 'opacity 0.3s ease',
        userSelect: 'text',
        WebkitUserSelect: 'text',
      }}>
        {snippet}
      </div>

      {/* Footer */}
      <div style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        paddingTop: 16,
        borderTop: `1px solid ${c.borderSubtle}`,
      }}>
        <span style={{
          fontFamily: f.mono,
          fontSize: 11,
          color: c.textTertiary,
          letterSpacing: '0.06em',
        }}>{publishedDate}</span>
        <div style={{
          fontFamily: f.mono,
          fontSize: 12,
          fontWeight: 600,
          letterSpacing: '0.08em',
          color: c.edge,
          display: 'flex',
          alignItems: 'center',
          gap: 6,
          textTransform: 'uppercase',
        }}>
          <span>Read</span>
          <span>→</span>
        </div>
      </div>
    </Tag>
  );
}
