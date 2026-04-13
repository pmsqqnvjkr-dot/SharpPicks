import { useState } from 'react';
import { colors, fonts } from '../../../styles/tokens';
import DailyMarketReport from '../../sharp/DailyMarketReport';

export default function MIPill({
  subline = '',
  marketReport,
  zeroState = false,
}) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div style={{ marginBottom: 14 }}>
      <button
        onClick={() => setExpanded(!expanded)}
        style={{
          width: '100%',
          background: colors.surface1,
          border: `1px solid ${colors.stroke}`,
          borderLeft: `3px solid ${colors.edgeGreen}`,
          borderRadius: 12,
          padding: '14px 16px',
          display: 'flex',
          alignItems: 'center',
          gap: 12,
          cursor: 'pointer',
          textAlign: 'left',
          color: 'inherit',
          fontFamily: fonts.sans,
          ...(expanded ? { borderBottomLeftRadius: 0, borderBottomRightRadius: 0 } : {}),
        }}
      >
        <div style={{
          width: 32,
          height: 32,
          background: 'rgba(52, 211, 153, 0.08)',
          borderRadius: 6,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          flexShrink: 0,
        }}>
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke={colors.edgeGreen} strokeWidth="2">
            <path d="M3 3v18h18" />
            <path d="M7 14l4-4 4 4 5-6" />
          </svg>
        </div>
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{
            fontSize: 15,
            fontWeight: 600,
            color: colors.text,
            lineHeight: 1.2,
            marginBottom: 2,
          }}>Market Intelligence</div>
          <div style={{
            fontFamily: fonts.mono,
            fontSize: 11.5,
            color: colors.text3,
            letterSpacing: '0.02em',
          }}>{subline}</div>
        </div>
        <svg
          width="16"
          height="16"
          viewBox="0 0 24 24"
          fill="none"
          stroke={colors.text3}
          strokeWidth="2"
          style={{
            flexShrink: 0,
            transform: expanded ? 'rotate(90deg)' : 'rotate(0deg)',
            transition: 'transform 200ms ease',
          }}
        >
          <polyline points="9 18 15 12 9 6" />
        </svg>
      </button>

      {expanded && (
        <div style={{
          background: colors.surface1,
          border: `1px solid ${colors.stroke}`,
          borderTop: 'none',
          borderLeft: `3px solid ${colors.edgeGreen}`,
          borderRadius: '0 0 12px 12px',
          padding: '4px 16px 16px',
        }}>
          {zeroState ? (
            <div style={{
              fontFamily: fonts.mono,
              fontSize: 12,
              color: colors.text3,
              textAlign: 'center',
              padding: '18px 0',
            }}>
              No slate today
            </div>
          ) : (
            <DailyMarketReport report={marketReport} />
          )}
        </div>
      )}
    </div>
  );
}
