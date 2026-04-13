import { colors, fonts } from '../../../styles/tokens';

export default function FurtherReadingCard({
  title = '',
  snippet = '',
  readMinutes = 0,
  publishedDate = '',
  category = 'Insight',
  href,
  onClick,
  imageUrl,
}) {
  const Tag = href ? 'a' : 'button';
  const linkProps = href
    ? { href, target: '_blank', rel: 'noopener noreferrer' }
    : { onClick, type: 'button' };

  return (
    <Tag
      {...linkProps}
      style={{
        background: colors.surface1,
        border: `1px solid ${colors.stroke}`,
        borderRadius: 12,
        marginBottom: 14,
        overflow: 'hidden',
        display: 'block',
        textDecoration: 'none',
        color: 'inherit',
        cursor: 'pointer',
        transition: 'border-color 0.2s ease',
        width: '100%',
        textAlign: 'left',
      }}
      onMouseEnter={e => e.currentTarget.style.borderColor = colors.strokeStrong}
      onMouseLeave={e => e.currentTarget.style.borderColor = colors.stroke}
    >
      {/* Thumbnail — only when an image is provided */}
      {imageUrl && (
        <div style={{
          width: '100%',
          height: 140,
          position: 'relative',
          overflow: 'hidden',
        }}>
          <img
            src={imageUrl}
            alt=""
            style={{
              position: 'absolute',
              inset: 0,
              width: '100%',
              height: '100%',
              objectFit: 'cover',
            }}
          />
          <span style={{
            position: 'absolute',
            top: 12,
            left: 12,
            fontFamily: fonts.label,
            fontSize: 9,
            letterSpacing: '2.5px',
            fontWeight: 700,
            color: colors.edgeGreen,
            background: 'rgba(10, 13, 20, 0.7)',
            backdropFilter: 'blur(8px)',
            WebkitBackdropFilter: 'blur(8px)',
            padding: '5px 9px',
            borderRadius: 4,
            border: '1px solid rgba(52, 211, 153, 0.25)',
            zIndex: 2,
            textTransform: 'uppercase',
          }}>
            {category}
          </span>
        </div>
      )}

      {/* Body */}
      <div style={{ padding: '16px 18px 18px' }}>
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: 8,
          marginBottom: 8,
        }}>
          {/* Inline chip when no thumbnail */}
          {!imageUrl && (
            <span style={{
              fontFamily: fonts.label,
              fontSize: 9,
              letterSpacing: '2.5px',
              fontWeight: 700,
              color: colors.edgeGreen,
              background: 'rgba(52, 211, 153, 0.08)',
              padding: '3px 8px',
              borderRadius: 4,
              textTransform: 'uppercase',
              flexShrink: 0,
            }}>
              {category}
            </span>
          )}
          <span style={{
            fontFamily: fonts.label,
            fontSize: 9,
            letterSpacing: '2.5px',
            fontWeight: 700,
            color: colors.text3,
            textTransform: 'uppercase',
          }}>
            {readMinutes} min read{publishedDate ? ` \u00B7 ${publishedDate}` : ''}
          </span>
        </div>
        <div style={{
          fontFamily: fonts.sans,
          fontSize: 17,
          fontWeight: 600,
          letterSpacing: '-0.01em',
          lineHeight: 1.3,
          color: colors.text,
          marginBottom: 8,
        }}>
          {title}
        </div>
        <div style={{
          fontFamily: fonts.sans,
          fontSize: 13,
          color: colors.text2,
          lineHeight: 1.5,
          marginBottom: 12,
        }}>
          {snippet}
        </div>
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: 6,
          fontFamily: fonts.label,
          fontSize: 9,
          letterSpacing: '2.5px',
          fontWeight: 700,
          color: colors.signalBlue,
          textTransform: 'uppercase',
        }}>
          Read article
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
            <path d="M5 12h14M13 5l7 7-7 7" />
          </svg>
        </div>
      </div>
    </Tag>
  );
}
