import { useState } from 'react';
import { inst as c, instFonts as f } from '../../../styles/tokens';
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
          background: c.bgCard,
          backgroundImage: `linear-gradient(90deg, ${c.edgeBg} 0%, transparent 60%)`,
          border: `1px solid ${c.borderSubtle}`,
          borderLeft: `2px solid ${c.edge}`,
          borderRadius: 18,
          padding: '16px 18px',
          display: 'flex',
          alignItems: 'center',
          gap: 14,
          cursor: 'pointer',
          textAlign: 'left',
          color: 'inherit',
          fontFamily: f.sans,
          WebkitTapHighlightColor: 'transparent',
          ...(expanded ? { borderBottomLeftRadius: 0, borderBottomRightRadius: 0 } : {}),
        }}
      >
        <div style={{
          width: 38,
          height: 38,
          background: c.bgCardElev,
          borderRadius: 8,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          flexShrink: 0,
        }}>
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke={c.edge} strokeWidth="2">
            <polyline points="23 6 13.5 15.5 8.5 10.5 1 18" />
            <polyline points="17 6 23 6 23 12" />
          </svg>
        </div>
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{
            fontFamily: f.sans,
            fontSize: 15,
            fontWeight: 600,
            color: c.textPrimary,
            lineHeight: 1.2,
            marginBottom: 4,
          }}>Market Intelligence</div>
          <div style={{
            fontFamily: f.mono,
            fontSize: 11,
            color: c.textTertiary,
            letterSpacing: '0.04em',
            lineHeight: 1.4,
          }}>{subline}</div>
        </div>
        <svg
          width="18"
          height="18"
          viewBox="0 0 24 24"
          fill="none"
          stroke={c.textTertiary}
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
          background: c.bgCard,
          border: `1px solid ${c.borderSubtle}`,
          borderTop: 'none',
          borderLeft: `2px solid ${c.edge}`,
          borderRadius: '0 0 18px 18px',
          padding: '4px 18px 18px',
        }}>
          {zeroState ? (
            <div style={{
              fontFamily: f.mono,
              fontSize: 12,
              color: c.textTertiary,
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
