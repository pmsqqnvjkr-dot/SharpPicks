import { colors, fonts } from '../../../styles/tokens';

export default function CrossSportCard({
  sport = 'MLB',
  isBeta = true,
  matchup = '',
  pick = '',
  tipoffLocal = '',
  tier = '',
  edgePct = 0,
  onSwitchSport,
}) {
  return (
    <div style={{
      background: colors.surface1,
      border: `1px solid ${colors.stroke}`,
      borderRadius: 12,
      padding: 20,
      marginBottom: 14,
    }}>
      {/* Header */}
      <div style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
      }}>
        <span style={{
          fontFamily: fonts.label,
          fontSize: 9,
          fontWeight: 700,
          letterSpacing: '2.5px',
          textTransform: 'uppercase',
          color: colors.signalBlue,
        }}>
          {sport.toUpperCase()} Has An Edge Today
        </span>
        <button
          onClick={onSwitchSport}
          style={{
            fontFamily: fonts.label,
            fontSize: 9,
            fontWeight: 700,
            letterSpacing: '2.5px',
            textTransform: 'uppercase',
            color: colors.signalBlue,
            background: 'none',
            border: 'none',
            cursor: 'pointer',
            padding: 0,
          }}
        >
          SWITCH &rsaquo;
        </button>
      </div>

      {/* Game tile */}
      <div style={{
        background: 'rgba(0,0,0,0.25)',
        border: `1px solid ${colors.stroke}`,
        borderRadius: 8,
        padding: 14,
        marginTop: 12,
      }}>
        <div style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          marginBottom: 6,
        }}>
          <span style={{
            fontFamily: fonts.label,
            fontSize: 9,
            letterSpacing: '2.5px',
            color: colors.signalBlue,
            background: 'rgba(79, 134, 247, 0.10)',
            padding: '3px 7px',
            borderRadius: 4,
            fontWeight: 700,
          }}>
            {sport.toUpperCase()}{isBeta ? ' \u00B7 PREVIEW' : ''}
          </span>
          <span style={{
            fontFamily: fonts.mono,
            fontSize: 13,
            color: colors.edgeGreen,
            fontWeight: 700,
          }}>
            +{edgePct.toFixed(1)}%
          </span>
        </div>

        <div style={{
          fontFamily: fonts.sans,
          fontSize: 16,
          fontWeight: 600,
          marginBottom: 4,
          letterSpacing: '-0.01em',
          color: colors.text,
        }}>
          {matchup}
        </div>

        <div style={{
          fontFamily: fonts.mono,
          fontSize: 11.5,
          color: colors.text3,
        }}>
          <b style={{ color: colors.text, fontWeight: 700 }}>{pick}</b>
          {tipoffLocal && ` \u00B7 ${tipoffLocal}`}
          {tier && ` \u00B7 TIER ${tier}`}
        </div>
      </div>
    </div>
  );
}
