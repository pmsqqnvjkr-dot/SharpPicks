import { inst as c, instFonts as f } from '../../../styles/tokens';

export default function CountdownCard({
  title = 'NBA Slate Opens',
  hours = 0,
  minutes = 0,
  subtitle = '',
  progressPct = 0,
  header = 'Next Edge Window',
}) {
  return (
    <div style={{
      background: c.bgCard,
      border: `1px solid ${c.borderSubtle}`,
      borderRadius: 18,
      padding: 22,
      marginBottom: 14,
    }}>
      <div style={{
        fontFamily: f.mono,
        fontSize: 11,
        fontWeight: 500,
        letterSpacing: '0.18em',
        textTransform: 'uppercase',
        color: c.textTertiary,
        marginBottom: 22,
      }}>
        {header}
      </div>

      <div style={{ textAlign: 'center' }}>
        <div style={{
          fontFamily: f.mono,
          fontSize: 10,
          letterSpacing: '0.18em',
          textTransform: 'uppercase',
          color: c.textTertiary,
          marginBottom: 14,
        }}>
          {title}
        </div>

        <div style={{
          display: 'flex',
          justifyContent: 'center',
          alignItems: 'baseline',
          gap: 16,
          marginBottom: 12,
        }}>
          <div style={{ display: 'flex', alignItems: 'baseline', gap: 4 }}>
            <span style={{
              fontFamily: f.serif,
              fontSize: 48,
              fontWeight: 500,
              color: c.textPrimary,
              letterSpacing: '-0.02em',
              lineHeight: 1,
            }}>{hours}</span>
            <span style={{
              fontFamily: f.mono,
              fontSize: 11,
              color: c.textTertiary,
              letterSpacing: '0.1em',
            }}>H</span>
          </div>
          <span style={{
            fontFamily: f.serif,
            fontSize: 36,
            color: c.textMuted,
            lineHeight: 1,
          }}>:</span>
          <div style={{ display: 'flex', alignItems: 'baseline', gap: 4 }}>
            <span style={{
              fontFamily: f.serif,
              fontSize: 48,
              fontWeight: 500,
              color: c.textPrimary,
              letterSpacing: '-0.02em',
              lineHeight: 1,
            }}>{String(minutes).padStart(2, '0')}</span>
            <span style={{
              fontFamily: f.mono,
              fontSize: 11,
              color: c.textTertiary,
              letterSpacing: '0.1em',
            }}>M</span>
          </div>
        </div>

        {subtitle && (
          <div style={{
            fontFamily: f.mono,
            fontSize: 11,
            color: c.textSecondary,
            letterSpacing: '0.06em',
            marginBottom: 16,
          }}>
            {subtitle}
          </div>
        )}

        <div style={{
          height: 2,
          background: c.borderSubtle,
          borderRadius: 1,
          overflow: 'hidden',
        }}>
          <div style={{
            height: '100%',
            width: `${Math.min(Math.max(progressPct, 0), 100)}%`,
            background: c.system,
            borderRadius: 1,
          }} />
        </div>
      </div>
    </div>
  );
}
