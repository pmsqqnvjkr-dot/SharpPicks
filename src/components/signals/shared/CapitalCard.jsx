import { colors, fonts } from '../../../styles/tokens';

export default function CapitalCard({ capitalPreservedUsd = 100 }) {
  return (
    <div style={{
      background: colors.surface1,
      border: `1px solid ${colors.stroke}`,
      borderRadius: 12,
      padding: 20,
      marginBottom: 14,
      borderLeft: `3px solid ${colors.edgeGreen}`,
      backgroundImage: 'linear-gradient(90deg, rgba(52,211,153,0.04), transparent 50%)',
    }}>
      <span style={{
        fontFamily: fonts.label,
        fontSize: 9,
        fontWeight: 700,
        letterSpacing: '2.5px',
        textTransform: 'uppercase',
        color: colors.text3,
      }}>
        One Unit Not Risked
      </span>
      <div style={{
        fontFamily: fonts.mono,
        fontSize: 32,
        fontWeight: 700,
        color: colors.edgeGreen,
        lineHeight: 1,
        margin: '8px 0',
      }}>
        +${capitalPreservedUsd}
      </div>
      <div style={{
        fontSize: 13.5,
        color: colors.text2,
        lineHeight: 1.55,
        fontFamily: fonts.sans,
      }}>
        Discipline compounds. Passing on a sub-threshold spot is mathematically equivalent to winning, over time.
      </div>
    </div>
  );
}
