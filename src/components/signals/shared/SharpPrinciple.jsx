import { colors, fonts } from '../../../styles/tokens';

export default function SharpPrinciple({ children, label = 'Sharp Principle' }) {
  return (
    <div style={{
      borderLeft: `3px solid ${colors.edgeGreen}`,
      background: 'rgba(52, 211, 153, 0.04)',
      padding: '18px 20px',
      borderRadius: '0 8px 8px 0',
      marginBottom: 14,
    }}>
      <span style={{
        fontFamily: fonts.label,
        fontSize: 9,
        fontWeight: 700,
        letterSpacing: '2.5px',
        textTransform: 'uppercase',
        color: colors.edgeGreen,
        fontStyle: 'normal',
        display: 'block',
        marginBottom: 8,
      }}>
        {label}
      </span>
      <div style={{
        fontFamily: fonts.sans,
        fontSize: 16,
        fontWeight: 500,
        fontStyle: 'normal',
        color: colors.text,
        lineHeight: 1.45,
      }}>
        {children}
      </div>
    </div>
  );
}
