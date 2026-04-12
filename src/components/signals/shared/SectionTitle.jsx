import { colors, fonts } from '../../../styles/tokens';

const toneColors = {
  green: colors.edgeGreen,
  blue: colors.signalBlue,
  dim: colors.text3,
};

export default function SectionTitle({ children, tone = 'dim', live = false }) {
  return (
    <div style={{
      fontFamily: fonts.label,
      fontSize: 9,
      fontWeight: 700,
      letterSpacing: '2.5px',
      textTransform: 'uppercase',
      color: toneColors[tone] || colors.text3,
      margin: '22px 4px 10px',
      display: 'flex',
      alignItems: 'center',
      gap: 8,
    }}>
      {live && (
        <span style={{
          width: 6,
          height: 6,
          borderRadius: '50%',
          background: colors.edgeGreen,
          boxShadow: '0 0 8px #34D399',
          flexShrink: 0,
        }} />
      )}
      {children}
    </div>
  );
}
