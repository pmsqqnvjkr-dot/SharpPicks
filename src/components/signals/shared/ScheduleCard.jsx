import { colors, fonts } from '../../../styles/tokens';

export default function ScheduleCard({ weekAhead = [] }) {
  return (
    <div style={{
      background: colors.surface1,
      border: `1px solid ${colors.stroke}`,
      borderRadius: 12,
      padding: 20,
      marginBottom: 14,
    }}>
      {weekAhead.map((day, i) => (
        <div key={i} style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          padding: i === 0 ? '4px 0 11px' : '11px 0',
          paddingBottom: i === weekAhead.length - 1 ? 0 : 11,
          borderBottom: i < weekAhead.length - 1 ? '1px solid rgba(255,255,255,0.04)' : 'none',
          fontFamily: fonts.mono,
          fontSize: 12,
        }}>
          <span style={{
            color: colors.text3,
            letterSpacing: '0.05em',
            fontWeight: 500,
          }}>
            <b style={{ color: colors.text, fontWeight: 700, marginRight: 8 }}>{day.weekday}</b>
            {day.date}
          </span>
          <span style={{
            color: day.isActive ? colors.edgeGreen : colors.text3,
            fontWeight: day.isActive ? 700 : 400,
          }}>
            {day.description}
          </span>
        </div>
      ))}
    </div>
  );
}
