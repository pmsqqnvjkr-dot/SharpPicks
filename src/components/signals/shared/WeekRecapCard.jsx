import { colors, fonts } from '../../../styles/tokens';

export default function WeekRecapCard({
  sparkline = [],
  netUsd = 0,
  record = '0-0',
  passDays = 0,
  signalsIssued = 0,
  daysCovered = 0,
  selectivityPct = 0,
}) {
  const points = sparkline.length > 0 ? sparkline : [0.5];
  const svgPoints = points.map((val, i) => {
    const x = points.length === 1 ? 150 : (i / (points.length - 1)) * 300;
    const y = 32 - (val * 28) - 2;
    return `${x},${y}`;
  }).join(' ');
  const lastPoint = points[points.length - 1];
  const lastX = points.length === 1 ? 150 : 300;
  const lastY = 32 - (lastPoint * 28) - 2;

  return (
    <div style={{
      background: colors.surface1,
      border: `1px solid ${colors.stroke}`,
      borderRadius: 12,
      padding: 20,
      marginBottom: 14,
    }}>
      {/* Sparkline */}
      <svg
        viewBox="0 0 300 32"
        preserveAspectRatio="none"
        style={{ height: 30, width: '100%', display: 'block', marginBottom: 4 }}
      >
        <polyline
          points={svgPoints}
          fill="none"
          stroke={colors.edgeGreen}
          strokeWidth="1.5"
          strokeLinejoin="round"
          strokeLinecap="round"
        />
        <circle cx={lastX} cy={lastY} r="2.5" fill={colors.edgeGreen} />
      </svg>

      {/* Stats grid */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(3, 1fr)',
        borderTop: `1px solid ${colors.stroke}`,
        borderBottom: `1px solid ${colors.stroke}`,
        padding: '14px 0',
        margin: '12px 0',
      }}>
        {[
          { value: `+${netUsd}`, label: 'Net', green: true },
          { value: record, label: 'Record', green: false },
          { value: String(passDays), label: 'Pass Days', green: false },
        ].map((s, i) => (
          <div key={i} style={{
            textAlign: 'center',
            borderRight: i < 2 ? `1px solid ${colors.stroke}` : 'none',
          }}>
            <div style={{
              fontFamily: fonts.mono,
              fontSize: 20,
              fontWeight: 700,
              lineHeight: 1,
              marginBottom: 6,
              color: s.green ? colors.edgeGreen : colors.text,
            }}>
              {s.value}
            </div>
            <div style={{
              fontFamily: fonts.label,
              fontSize: 9,
              letterSpacing: '2.5px',
              color: colors.text3,
              textTransform: 'uppercase',
              fontWeight: 700,
            }}>
              {s.label}
            </div>
          </div>
        ))}
      </div>

      {/* Footer */}
      <div style={{
        fontFamily: fonts.mono,
        fontSize: 11,
        color: colors.text3,
        textAlign: 'center',
      }}>
        {signalsIssued} signals issued &middot; {daysCovered} days &middot; {selectivityPct}% selectivity
      </div>
    </div>
  );
}
