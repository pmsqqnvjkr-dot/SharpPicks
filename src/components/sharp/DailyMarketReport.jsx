import { useApi } from '../../hooks/useApi';
import { useSport, sportQuery } from '../../hooks/useSport';

const green = '#5A9E72';
const greenDim = '#5A9E72';
const blue = '#4A8EC2';
const border = 'rgba(90, 158, 114, 0.12)';
const bgInner = '#131f36';
const textLabel = '#8899AA';
const textSec = '#9EAAB8';
const textDim = '#7A8494';

const labelStyle = {
  fontFamily: 'var(--font-mono)', fontSize: '10px', fontWeight: 500,
  letterSpacing: '1px', textTransform: 'uppercase', color: textLabel,
};

export default function DailyMarketReport({ report: reportProp }) {
  const { sport } = useSport();
  const { data: fetchedData, loading } = useApi(sportQuery('/public/market-report', sport), { pollInterval: 300000 });
  const data = reportProp ?? fetchedData;

  if (reportProp ? !data?.available : (loading || !data || !data.available)) return null;

  const today = new Date().toLocaleDateString('en-US', {
    month: 'long', day: 'numeric', timeZone: 'America/New_York',
  });

  const scanTime = data.last_updated ? (() => {
    try {
      const d = new Date(data.last_updated);
      const et = new Date(d.toLocaleString('en-US', { timeZone: 'America/New_York' }));
      const h = et.getHours();
      const m = et.getMinutes().toString().padStart(2, '0');
      const ampm = h >= 12 ? 'PM' : 'AM';
      return `${h % 12 || 12}:${m} ${ampm} ET`;
    } catch { return null; }
  })() : null;

  const regime = data.regime || 'Efficient';
  const regimeDisplay = regime.toLowerCase().replace(/\b\w/g, c => c.toUpperCase());
  const regimeSub = data.regime_micro || '';
  const dist = data.edge_distribution || {};
  const lean = data.market_lean || {};

  return (
    <div>
      <div style={{
        background: 'var(--bg-card, #0f1d33)',
        border: `1px solid ${border}`,
        borderRadius: '8px',
        padding: '14px 16px',
      }}>
        {/* Header */}
        <div style={{
          display: 'flex', alignItems: 'center', justifyContent: 'space-between',
          marginBottom: '14px',
        }}>
          <span style={{
            fontFamily: 'var(--font-mono)', fontSize: '10px', fontWeight: 500,
            letterSpacing: '1.2px', color: green, textTransform: 'uppercase',
          }}>Market Intelligence</span>
          <span style={{
            fontFamily: 'var(--font-mono)', fontSize: '10px',
            color: textDim, letterSpacing: '0.5px',
          }}>{today}</span>
        </div>

        {/* 3-column metric grid */}
        <div style={{
          display: 'grid', gridTemplateColumns: '1fr 1fr 1fr',
          gap: '12px', marginBottom: '14px',
        }}>
          <MetricCell label="MEI" value={data.market_efficiency_index} green />
          <div style={{
            background: bgInner, border: `1px solid ${border}`,
            borderRadius: '6px', padding: '10px',
          }}>
            <div style={{ ...labelStyle, marginBottom: '4px' }}>Regime</div>
            <div style={{
              fontFamily: 'var(--font-mono)', fontSize: '14px', fontWeight: 600,
              color: green, lineHeight: 1,
            }}>{regimeDisplay}</div>
            {regimeSub && (
              <div style={{
                fontFamily: 'var(--font-sans)', fontSize: '10px',
                color: textSec, marginTop: '3px',
              }}>{regimeSub.length > 20 ? regimeSub.slice(0, 20) + '…' : regimeSub}</div>
            )}
          </div>
          <MetricCell
            label="Top Edge"
            value={data.largest_edge != null ? `+${data.largest_edge}%` : '--'}
            green
          />
        </div>

        {/* Edges detected row */}
        <div style={{
          display: 'flex', justifyContent: 'space-between', alignItems: 'center',
          padding: '3px 0',
        }}>
          <span style={{
            fontFamily: 'var(--font-mono)', fontSize: '11px', color: textSec,
          }}>Edges detected</span>
          <span style={{
            fontFamily: 'var(--font-mono)', fontSize: '11px', fontWeight: 600,
            color: green,
          }}>{data.edges_detected}</span>
        </div>

        {/* Edge Distribution inline */}
        <div style={{ display: 'flex', gap: '16px', marginTop: '12px' }}>
          <EdgeDot color={green} count={dist.strong || 0} label="Strong" />
          <EdgeDot color={blue} count={dist.moderate || 0} label="Moderate" />
          <EdgeDot color={textDim} count={dist.weak || 0} label="Weak" />
        </div>

        {/* Model Favoring */}
        {lean.total_edges > 0 && (
          <div style={{
            marginTop: '12px', paddingTop: '12px',
            borderTop: '1px solid rgba(255,255,255,0.04)',
          }}>
            <div style={{ ...labelStyle, marginBottom: '8px' }}>Model Favoring</div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                <span style={{
                  fontFamily: 'var(--font-mono)', fontSize: '10px', letterSpacing: '0.5px',
                  textTransform: 'uppercase', padding: '2px 5px', borderRadius: '3px',
                  color: textSec, background: 'rgba(255,255,255,0.04)',
                }}>Favorites</span>
                <span style={{
                  fontFamily: 'var(--font-mono)', fontSize: '10px', fontWeight: 600,
                  color: textSec,
                }}>{lean.favorite_pct || 0}%</span>
              </div>
              <div style={{
                flex: 1, height: '4px', borderRadius: '2px',
                display: 'flex', overflow: 'hidden',
                background: 'rgba(255,255,255,0.03)',
              }}>
                <div style={{ height: '100%', width: `${lean.favorite_pct || 0}%`, background: textDim }} />
                <div style={{ height: '100%', width: `${lean.underdog_pct || 0}%`, background: green, opacity: 0.6 }} />
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '4px', justifyContent: 'flex-end' }}>
                <span style={{
                  fontFamily: 'var(--font-mono)', fontSize: '10px', fontWeight: 600,
                  color: green,
                }}>{lean.underdog_pct || 0}%</span>
                <span style={{
                  fontFamily: 'var(--font-mono)', fontSize: '10px', letterSpacing: '0.5px',
                  textTransform: 'uppercase', padding: '2px 5px', borderRadius: '3px',
                  color: green, background: 'rgba(90, 158, 114, 0.1)',
                }}>Underdogs</span>
              </div>
            </div>
          </div>
        )}

        {/* Market Signal */}
        {(data.briefing?.[0] || data.insight) && (
          <div style={{
            background: '#141A2E', border: `1px solid ${border}`,
            borderLeft: `3px solid ${green}`,
            borderRadius: '6px', padding: '14px', marginTop: '12px',
          }}>
            <div style={{
              fontFamily: 'var(--font-mono)', fontSize: '10px', fontWeight: 500,
              letterSpacing: '1.5px', color: green, textTransform: 'uppercase',
              marginBottom: '6px',
            }}>Market Signal</div>
            <div style={{
              fontFamily: "'IBM Plex Serif', var(--font-serif), serif", fontSize: '13px',
              color: textSec, lineHeight: 1.5,
            }}>{data.briefing?.[0] || data.insight}</div>
          </div>
        )}
      </div>

      {/* Timestamp */}
      {scanTime && (
        <div style={{
          fontFamily: 'var(--font-mono)', fontSize: '10px',
          color: textDim, textAlign: 'center',
          marginTop: '20px', letterSpacing: '0.5px',
        }}>
          Intelligence updated <span style={{ color: greenDim }}>{scanTime}</span>
        </div>
      )}
    </div>
  );
}

function MetricCell({ label, value, green: isGreen }) {
  return (
    <div style={{
      background: bgInner, border: `1px solid ${border}`,
      borderRadius: '6px', padding: '10px',
    }}>
      <div style={{ ...labelStyle, marginBottom: '4px' }}>{label}</div>
      <div style={{
        fontFamily: 'var(--font-mono)', fontSize: '20px', fontWeight: 600,
        color: isGreen ? green : 'var(--text-primary)', lineHeight: 1,
      }}>{value}</div>
    </div>
  );
}

function EdgeDot({ color, count, label }) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
      <span style={{ width: '6px', height: '6px', borderRadius: '50%', background: color }} />
      <span style={{
        fontFamily: 'var(--font-mono)', fontSize: '13px', fontWeight: 600,
        color: 'var(--text-primary)',
      }}>{count}</span>
      <span style={{
        fontFamily: 'var(--font-mono)', fontSize: '10px',
        color: textDim, textTransform: 'uppercase', letterSpacing: '0.5px',
      }}>{label}</span>
    </div>
  );
}
