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

export default function DailyMarketReport() {
  const { sport } = useSport();
  const { data, loading } = useApi(sportQuery('/public/market-report', sport), { pollInterval: 300000 });

  if (loading || !data || !data.available) return null;

  const today = new Date().toLocaleDateString('en-US', {
    month: 'long', day: 'numeric', timeZone: 'America/New_York',
  });

  const updatedTime = data.last_updated ? (() => {
    try {
      const d = new Date(data.last_updated);
      const et = new Date(d.toLocaleString('en-US', { timeZone: 'America/New_York' }));
      const h = et.getHours();
      const m = et.getMinutes().toString().padStart(2, '0');
      const ampm = h >= 12 ? 'PM' : 'AM';
      return `${h % 12 || 12}:${m} ${ampm} ET`;
    } catch { return null; }
  })() : null;

  return (
    <div style={{
      backgroundColor: 'var(--surface-1)',
      borderRadius: '14px',
      border: '1px solid var(--color-border)',
      borderTop: '2px solid var(--color-signal)',
      padding: 'var(--space-md)',
      marginBottom: 'var(--space-md)',
    }}>
      <div style={{ marginBottom: 'var(--space-xs)' }}>
        <div style={{ ...label }}>
          SharpPicks Market Report
        </div>
      </div>
      <div style={{
        fontSize: 'var(--text-metric)', color: 'var(--text-secondary)',
        marginBottom: 'var(--space-md)',
      }}>{today}</div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-sm)' }}>
        <MetricRow label="Games analyzed" value={data.games_analyzed} />
        <MetricRow label="Model edges detected" value={data.edges_detected} />
        <MetricRow
          label="Qualified signals"
          value={data.qualified_signals}
          highlight={data.qualified_signals > 0}
        />
      </div>

      <div style={{
        height: '1px', background: 'var(--color-border)',
        margin: 'var(--space-md) 0',
      }} />

      <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-sm)', marginBottom: 'var(--space-sm)' }}>
        <span style={{ ...label, marginBottom: 0 }}>Market efficiency</span>
        <span style={{
          ...metricNum, fontSize: '16px',
          color: data.market_efficiency_pct >= 80 ? 'var(--text-secondary)' : 'var(--color-signal)',
        }}>{data.market_efficiency_pct}%</span>
      </div>

      <p style={{
        fontSize: '13px', fontStyle: 'italic',
        color: 'var(--text-secondary)', lineHeight: 1.5, margin: 0,
      }}>{data.assessment}</p>

      {updatedTime && (
        <div style={{
          fontSize: '10px', color: 'var(--text-tertiary)',
          fontFamily: 'var(--font-mono)',
          marginTop: 'var(--space-sm)',
        }}>Last updated: {updatedTime}</div>
      )}
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
