import { colors, fonts } from '../../../styles/tokens';

export default function CountdownCard({
  title = 'NBA Slate Opens',
  hours = 0,
  minutes = 0,
  subtitle = '',
  progressPct = 0,
}) {
  return (
    <div style={{
      background: colors.surface1,
      border: `1px solid ${colors.stroke}`,
      borderRadius: 12,
      padding: '22px 18px 18px',
      marginBottom: 14,
      textAlign: 'center',
    }}>
      <span style={{
        fontFamily: fonts.label,
        fontSize: 9,
        fontWeight: 700,
        letterSpacing: '2.5px',
        textTransform: 'uppercase',
        color: colors.text3,
      }}>
        {title}
      </span>

      <div style={{
        fontFamily: fonts.mono,
        fontSize: 38,
        fontWeight: 700,
        letterSpacing: '-0.01em',
        lineHeight: 1,
        margin: '12px 0 8px',
        color: colors.text,
      }}>
        {hours}
        <span style={{
          fontFamily: fonts.label,
          fontSize: 13,
          color: colors.text3,
          marginLeft: 2,
          marginRight: 14,
          fontWeight: 700,
          letterSpacing: '0.15em',
        }}>H</span>
        {minutes}
        <span style={{
          fontFamily: fonts.label,
          fontSize: 13,
          color: colors.text3,
          marginLeft: 2,
          marginRight: 0,
          fontWeight: 700,
          letterSpacing: '0.15em',
        }}>M</span>
      </div>

      <div style={{
        fontSize: 12,
        color: colors.text3,
        fontFamily: fonts.sans,
        marginBottom: 14,
      }}>
        {subtitle}
      </div>

      <div style={{
        height: 3,
        background: 'rgba(255,255,255,0.04)',
        borderRadius: 2,
        overflow: 'hidden',
      }}>
        <div style={{
          height: '100%',
          width: `${Math.min(progressPct, 100)}%`,
          background: colors.signalBlue,
          borderRadius: 2,
        }} />
      </div>
    </div>
  );
}
