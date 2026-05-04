import { inst as c, instFonts as f } from '../../../styles/tokens';

export default function CapitalCard({ capitalPreservedUsd = 100 }) {
  if (capitalPreservedUsd === 0) return null;

  return (
    <div style={{
      background: c.bgCard,
      border: `1px solid ${c.borderSubtle}`,
      borderRadius: 16,
      padding: 18,
      marginBottom: 10,
    }}>
      <div style={{
        fontFamily: f.mono,
        fontSize: 10,
        letterSpacing: '0.16em',
        textTransform: 'uppercase',
        color: c.textTertiary,
        marginBottom: 8,
      }}>
        One Unit Not Risked
      </div>
      <div style={{
        fontFamily: f.mono,
        fontSize: 36,
        fontWeight: 600,
        color: c.edge,
        letterSpacing: '-0.02em',
        lineHeight: 1,
        marginBottom: 14,
      }}>
        +${capitalPreservedUsd}
      </div>
      <div style={{
        fontFamily: f.sans,
        fontSize: 14,
        lineHeight: 1.5,
        color: c.textSecondary,
      }}>
        Discipline compounds. Passing on a sub-threshold spot is mathematically equivalent to winning, over time.
      </div>
    </div>
  );
}
