import { colors, fonts } from '../../../styles/tokens';

const cardStyle = {
  background: colors.surface1,
  border: `1px solid ${colors.stroke}`,
  borderRadius: 12,
  padding: 20,
  marginBottom: 14,
};

const tileStyle = {
  background: 'rgba(0,0,0,0.25)',
  border: `1px solid ${colors.stroke}`,
  borderRadius: 8,
  padding: '12px 8px',
  textAlign: 'center',
};

const tileLabelStyle = {
  fontFamily: fonts.label,
  fontSize: 9,
  letterSpacing: '2.5px',
  color: colors.text3,
  marginBottom: 6,
  fontWeight: 700,
  textTransform: 'uppercase',
};

const tileValueStyle = {
  fontFamily: fonts.mono,
  fontSize: 20,
  fontWeight: 700,
  lineHeight: 1.1,
  color: colors.text,
};

const tileSubStyle = {
  fontSize: 10.5,
  color: colors.text3,
  marginTop: 4,
  fontFamily: fonts.sans,
};

export default function MICard({
  mei = 0,
  meiSub = '',
  regime = 'Efficient',
  regimeSub = '',
  topEdgePct = 0,
  topEdgeSub = '',
  sevenDayAvg = 0,
  strengthCounts = { strong: 0, moderate: 0, weak: 0 },
}) {
  return (
    <div style={cardStyle}>
      <div style={{
        display: 'grid',
        gridTemplateColumns: '1fr 1.2fr 1fr',
        gap: 8,
        marginBottom: 16,
      }}>
        {/* MEI tile */}
        <div style={tileStyle}>
          <div style={tileLabelStyle}>MEI</div>
          <div style={tileValueStyle}>{mei}</div>
          <div style={tileSubStyle}>{meiSub || (mei < 40 ? 'Tight' : mei < 60 ? 'Normal' : 'Wide')}</div>
        </div>

        {/* Regime tile */}
        <div style={tileStyle}>
          <div style={tileLabelStyle}>Regime</div>
          <div style={{
            fontFamily: fonts.mono,
            fontSize: 13,
            color: colors.edgeGreen,
            textTransform: 'uppercase',
            fontWeight: 700,
            letterSpacing: '0.04em',
          }}>
            {regime}
          </div>
          <div style={tileSubStyle}>{regimeSub || 'Books aligned'}</div>
        </div>

        {/* Top Edge tile */}
        <div style={tileStyle}>
          <div style={tileLabelStyle}>Top Edge</div>
          <div style={{ ...tileValueStyle, color: topEdgePct > 0 ? colors.edgeGreen : colors.text }}>
            {topEdgePct > 0 ? '+' : ''}{topEdgePct}%
          </div>
          <div style={tileSubStyle}>{topEdgeSub || 'Below bar'}</div>
        </div>
      </div>

      {/* Strength row */}
      <div style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        paddingTop: 13,
        borderTop: `1px solid ${colors.stroke}`,
        fontFamily: fonts.mono,
        fontSize: 11,
        color: colors.text3,
      }}>
        <span>7d avg: {sevenDayAvg}</span>
        <div style={{ display: 'flex', gap: 12 }}>
          {[
            { dot: colors.edgeGreen, count: strengthCounts.strong, label: 'STR' },
            { dot: colors.premiumGold, count: strengthCounts.moderate, label: 'MOD' },
            { dot: colors.text3, count: strengthCounts.weak, label: 'WK' },
          ].map((item) => (
            <span key={item.label} style={{ display: 'flex', alignItems: 'center', gap: 5 }}>
              <span style={{
                width: 6, height: 6, borderRadius: '50%',
                background: item.dot,
              }} />
              <b style={{ color: colors.text, fontWeight: 700, marginRight: 3 }}>{item.count}</b>
              {item.label}
            </span>
          ))}
        </div>
      </div>
    </div>
  );
}
