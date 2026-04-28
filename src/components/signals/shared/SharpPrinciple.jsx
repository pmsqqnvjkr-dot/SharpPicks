import { inst as c, instFonts as f } from '../../../styles/tokens';

export default function SharpPrinciple({
  children,
  label = 'Sharp Principle',
  index = 0,
  total = 0,
  onTap,
  rotateKey,
}) {
  return (
    <div
      onClick={onTap}
      style={{
        background: c.bgCard,
        border: `1px solid ${c.borderSubtle}`,
        borderRadius: 18,
        padding: 22,
        marginBottom: 14,
        position: 'relative',
        cursor: onTap ? 'pointer' : 'default',
        WebkitTapHighlightColor: 'transparent',
        userSelect: 'none',
        WebkitUserSelect: 'none',
      }}
    >
      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        marginBottom: 16,
      }}>
        <span style={{
          fontFamily: f.mono,
          fontSize: 11,
          fontWeight: 500,
          letterSpacing: '0.18em',
          textTransform: 'uppercase',
          color: c.textTertiary,
        }}>
          {label}
        </span>
        {total > 0 && (
          <span style={{
            fontFamily: f.mono,
            fontSize: 10,
            fontWeight: 400,
            letterSpacing: '0.1em',
            color: c.textMuted,
          }}>
            {String(index + 1).padStart(2, '0')} / {String(total).padStart(2, '0')}
          </span>
        )}
      </div>
      <div
        key={rotateKey}
        style={{
          fontFamily: f.serif,
          fontSize: 18,
          fontWeight: 400,
          fontStyle: 'normal',
          color: c.textPrimary,
          letterSpacing: '-0.01em',
          lineHeight: 1.3,
          animation: 'sp-fade-in 0.4s ease-out',
        }}
        dangerouslySetInnerHTML={{ __html: typeof children === 'string' ? children : '' }}
      />
    </div>
  );
}
