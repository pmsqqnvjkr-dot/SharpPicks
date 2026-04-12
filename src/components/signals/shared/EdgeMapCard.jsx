import { colors, fonts } from '../../../styles/tokens';

const MINUS = '\u2212';

function formatPct(val) {
  if (val >= 0) return `+${val.toFixed(1)}%`;
  return `${MINUS}${Math.abs(val).toFixed(1)}%`;
}

function pctColor(status) {
  if (status === 'below') return colors.edgeGreen;
  if (status === 'negative') return colors.alertRed;
  return colors.text3;
}

function statusLabel(status) {
  if (status === 'below') return 'Below bar';
  if (status === 'negative') return 'Negative';
  return 'No edge';
}

export default function EdgeMapCard({ edgeMap = [], thresholdPct = 8.0 }) {
  const topEdge = edgeMap.length > 0
    ? Math.max(...edgeMap.map(r => r.edgePct))
    : 0;
  const gap = Math.max(0, thresholdPct - topEdge);

  return (
    <div style={{
      background: colors.surface1,
      border: `1px solid ${colors.stroke}`,
      borderRadius: 12,
      padding: 20,
      marginBottom: 14,
    }}>
      {edgeMap.map((row, i) => {
        const isPositive = row.edgePct >= 0;
        const fillWidth = Math.min(Math.abs(row.edgePct) / thresholdPct * 100, 100);

        return (
          <div key={i} style={{
            display: 'grid',
            gridTemplateColumns: '90px 50px 1fr 80px',
            alignItems: 'center',
            gap: 10,
            padding: '9px 0',
            borderBottom: i < edgeMap.length - 1 ? '1px solid rgba(255,255,255,0.04)' : 'none',
          }}>
            <span style={{
              fontFamily: fonts.mono,
              fontSize: 12,
              color: colors.text,
              fontWeight: 500,
            }}>
              {row.matchup}
            </span>

            <span style={{
              fontFamily: fonts.mono,
              fontSize: 12,
              fontWeight: 700,
              textAlign: 'right',
              color: pctColor(row.status),
            }}>
              {formatPct(row.edgePct)}
            </span>

            <div style={{
              height: 4,
              borderRadius: 2,
              background: 'rgba(255,255,255,0.05)',
              overflow: 'visible',
              position: 'relative',
            }}>
              <div style={{
                height: '100%',
                width: `${fillWidth}%`,
                background: isPositive ? colors.deepGreen : colors.alertRed,
                opacity: isPositive ? 0.8 : 0.5,
                borderRadius: 2,
              }} />
              {isPositive && (
                <div style={{
                  position: 'absolute',
                  top: -3,
                  bottom: -3,
                  left: '100%',
                  width: 1,
                  background: colors.text3,
                }} />
              )}
            </div>

            <span style={{
              fontFamily: fonts.sans,
              fontSize: 10.5,
              color: colors.text3,
              textAlign: 'right',
            }}>
              {statusLabel(row.status)}
            </span>
          </div>
        );
      })}

      {/* Footer */}
      <div style={{
        marginTop: 12,
        paddingTop: 12,
        borderTop: `1px solid ${colors.stroke}`,
        fontFamily: fonts.mono,
        fontSize: 11,
        color: colors.text3,
        display: 'flex',
        justifyContent: 'space-between',
      }}>
        <span>
          Threshold: <b style={{ color: colors.text2, fontWeight: 700 }}>+{thresholdPct.toFixed(1)}%</b>
        </span>
        <span>
          Top edge fell <b style={{ color: colors.text2, fontWeight: 700 }}>{gap.toFixed(1)}pp</b> short
        </span>
      </div>
    </div>
  );
}
