import { colors, fonts } from '../../../styles/tokens';

export default function ComplianceFooter() {
  return (
    <div style={{
      textAlign: 'center',
      fontFamily: fonts.sans,
      fontSize: 10.5,
      color: colors.text3,
      padding: '16px 24px 8px',
      lineHeight: 1.5,
      fontStyle: 'italic',
    }}>
      This is entertainment only. Past results don't guarantee future performance.
    </div>
  );
}
