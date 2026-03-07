import { useApi } from '../../hooks/useApi';
import { useSport, sportQuery } from '../../hooks/useSport';

const label = {
  fontFamily: 'var(--font-mono)', fontSize: 'var(--text-label-size)',
  fontWeight: 700, letterSpacing: '0.08em', textTransform: 'uppercase',
  color: 'var(--text-tertiary)', lineHeight: 1,
};

const metricNum = {
  fontFamily: 'var(--font-mono)', fontSize: 'var(--text-metric)',
  fontWeight: 700, fontVariantNumeric: 'tabular-nums',
  color: 'var(--text-primary)', lineHeight: 1,
};

const divider = {
  height: '1px', background: 'var(--color-border)',
  margin: 'var(--space-md) 0',
};

export default function DailyMarketReport() {
  const { sport } = useSport();
  const { data, loading } = useApi(sportQuery('/public/market-report', sport), { pollInterval: 300000 });

  if (loading || !data || !data.available) return null;

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

  const regimeColor = data.market_efficiency_pct <= 25 ? 'var(--color-signal)'
    : data.market_efficiency_pct <= 50 ? '#FBBF24'
    : 'var(--text-secondary)';

  const dist = data.edge_distribution || {};

  return (
    <div style={{
      backgroundColor: 'var(--surface-1)',
      borderRadius: '14px',
      border: '1px solid var(--color-border)',
      borderTop: '2px solid var(--color-signal)',
      padding: 'var(--space-md)',
      marginBottom: 'var(--space-md)',
    }}>
      {/* Header */}
      <div style={{ ...label, marginBottom: '4px' }}>
        Market Scan &mdash; {today}
      </div>

      <div style={divider} />

      {/* Market Regime + Efficiency */}
      <div style={{ marginBottom: 'var(--space-md)' }}>
        <div style={{ ...label, marginBottom: '6px', fontSize: '9px' }}>Market Regime</div>
        <div style={{
          fontFamily: 'var(--font-mono)', fontSize: '18px', fontWeight: 700,
          color: regimeColor, marginBottom: '8px',
        }}>{data.regime || 'Efficient Market'}</div>
        <div style={{ display: 'flex', alignItems: 'baseline', gap: '8px' }}>
          <span style={{ fontSize: 'var(--text-metric)', color: 'var(--text-secondary)' }}>
            Market Efficiency
          </span>
          <span style={{
            ...metricNum, fontSize: '20px',
            color: data.market_efficiency_pct <= 50 ? 'var(--color-signal)' : 'var(--text-primary)',
          }}>{data.market_efficiency_pct}%</span>
        </div>
      </div>

      <div style={divider} />

      {/* Scan Metrics */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-sm)' }}>
        <MetricRow label="Markets analyzed" value={data.games_analyzed} />
        <MetricRow label="Edges detected" value={data.edges_detected} />
        <MetricRow
          label="Signals generated"
          value={data.qualified_signals}
          highlight={data.qualified_signals > 0}
        />
      </div>

      <div style={divider} />

      {/* Signal Density */}
      <div style={{ marginBottom: 'var(--space-md)' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline' }}>
          <span style={{ fontSize: 'var(--text-metric)', color: 'var(--text-secondary)' }}>
            Signal Density
          </span>
          <span style={{
            ...metricNum, fontSize: '16px',
            color: data.signal_density >= 40 ? 'var(--color-signal)' : 'var(--text-primary)',
          }}>{data.signal_density}%</span>
        </div>
        <div style={{
          fontSize: '11px', color: 'var(--text-tertiary)',
          fontFamily: 'var(--font-mono)', marginTop: '2px',
        }}>
          {data.qualified_signals} signal{data.qualified_signals !== 1 ? 's' : ''} from {data.games_analyzed} markets
        </div>
      </div>

      {/* Largest Edge */}
      {data.largest_edge != null && (
        <>
          <div style={divider} />
          <div style={{ marginBottom: 'var(--space-md)' }}>
            <div style={{ ...label, marginBottom: '6px', fontSize: '9px' }}>Largest Edge Today</div>
            <div style={{
              fontFamily: 'var(--font-mono)', fontSize: '22px', fontWeight: 700,
              color: 'var(--color-signal)', fontVariantNumeric: 'tabular-nums',
            }}>+{data.largest_edge}%</div>
            {data.largest_edge_game && (
              <div style={{
                fontSize: '12px', color: 'var(--text-tertiary)',
                fontFamily: 'var(--font-mono)', marginTop: '2px',
              }}>{data.largest_edge_game}</div>
            )}
          </div>
        </>
      )}

      {/* Edge Distribution */}
      {data.edges_detected > 0 && (
        <>
          <div style={divider} />
          <div style={{ marginBottom: 'var(--space-md)' }}>
            <div style={{ ...label, marginBottom: '8px', fontSize: '9px' }}>Edge Distribution</div>
            <div style={{ display: 'flex', gap: 'var(--space-lg)' }}>
              <EdgeCategory label="Strong" count={dist.strong || 0} threshold="≥10%" />
              <EdgeCategory label="Moderate" count={dist.moderate || 0} threshold="7–10%" />
              <EdgeCategory label="Weak" count={dist.weak || 0} threshold="5–7%" />
            </div>
          </div>
        </>
      )}

      {/* Model Insight */}
      {data.insight && (
        <>
          <div style={divider} />
          <div style={{ marginBottom: 'var(--space-md)' }}>
            <div style={{ ...label, marginBottom: '6px', fontSize: '9px' }}>Model Insight</div>
            <p style={{
              fontSize: '13px', fontStyle: 'italic',
              color: 'var(--text-secondary)', lineHeight: 1.5, margin: 0,
            }}>{data.insight}</p>
          </div>
        </>
      )}

      <div style={divider} />

      {/* Scan Timestamp */}
      {scanTime && (
        <div style={{
          fontSize: '11px', color: 'var(--text-tertiary)',
          fontFamily: 'var(--font-mono)', marginBottom: 'var(--space-sm)',
        }}>
          Market scan completed {scanTime}
        </div>
      )}

      {/* Philosophy */}
      <div style={{
        fontSize: '11px', color: 'var(--text-tertiary)',
        fontFamily: 'var(--font-mono)', lineHeight: 1.5,
        fontStyle: 'italic',
      }}>
        Selective by design. Only qualified edges become signals.
      </div>
    </div>
  );
}

function MetricRow({ label: labelText, value, highlight }) {
  return (
    <div style={{
      display: 'flex', justifyContent: 'space-between', alignItems: 'center',
    }}>
      <span style={{
        fontSize: 'var(--text-metric)', color: 'var(--text-secondary)',
      }}>{labelText}</span>
      <span style={{
        ...metricNum,
        color: highlight ? 'var(--color-signal)' : 'var(--text-primary)',
      }}>{value}</span>
    </div>
  );
}

function EdgeCategory({ label: labelText, count, threshold }) {
  return (
    <div>
      <div style={{
        fontFamily: 'var(--font-mono)', fontSize: '18px', fontWeight: 700,
        fontVariantNumeric: 'tabular-nums',
        color: count > 0 ? 'var(--text-primary)' : 'var(--text-tertiary)',
      }}>{count}</div>
      <div style={{
        fontSize: '11px', color: 'var(--text-secondary)',
        fontFamily: 'var(--font-mono)', marginTop: '2px',
      }}>{labelText}</div>
      <div style={{
        fontSize: '9px', color: 'var(--text-tertiary)',
        fontFamily: 'var(--font-mono)', marginTop: '1px',
      }}>{threshold}</div>
    </div>
  );
}
