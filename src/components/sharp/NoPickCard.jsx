import { InsightPassDayCTA } from './InsightsTab';

export default function NoPickCard({ data, onInsightTap }) {
  return (
    <div style={{ padding: '0 4px' }}>
      <div style={{ textAlign: 'center', padding: '24px 0 32px' }}>
        <div style={{
          width: '6px', height: '6px', borderRadius: '50%',
          background: 'var(--text-tertiary)', opacity: 0.5,
          margin: '0 auto 24px',
        }} />

        <h1 style={{
          fontFamily: 'var(--font-mono)',
          fontSize: 'var(--text-label-size)',
          fontWeight: 700,
          letterSpacing: '0.08em',
          textTransform: 'uppercase',
          color: 'var(--text-secondary)',
          marginBottom: '12px',
        }}>
          Market Intelligence Complete
        </h1>

        <h2 style={{
          fontFamily: 'var(--font-sans)',
          fontSize: '20px', fontWeight: 700,
          color: 'var(--text-primary)',
          marginBottom: '12px',
        }}>
          No Qualifying Signal
        </h2>

        <p style={{
          fontSize: 'var(--text-metric)',
          color: 'var(--text-secondary)',
          lineHeight: '1.55', marginBottom: '4px',
        }}>
          {data.games_analyzed > 0
            ? `All ${data.games_analyzed} games evaluated · No edge above threshold`
            : 'Model analysis complete.'}
        </p>
        {((data.whatif?.side && data.whatif?.edge_pct != null) || (data.closest_edge_pct != null && data.closest_edge_pct > 0)) && (
          <p style={{
            fontSize: '13px',
            color: 'var(--text-tertiary)',
            lineHeight: '1.55', marginBottom: 'var(--space-sm)',
            fontFamily: 'var(--font-mono)',
            fontVariantNumeric: 'tabular-nums',
          }}>
            Closest edge: {data.whatif?.side ? `${data.whatif.side} at ${data.whatif.edge_pct}%` : `${data.closest_edge_pct}%`} — below 3% threshold.
          </p>
        )}
        <p style={{
          fontSize: 'var(--text-caption)',
          color: 'var(--text-tertiary)',
          lineHeight: '1.55',
        }}>
          Next scan: Tomorrow 10:00 AM EST
        </p>
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: '14px', marginBottom: 'var(--space-xl)' }}>
        <InsightCard
          title="Restraint is a feature"
          desc="Quiet days are intentional. Market efficient — no action required."
        />
        <InsightCard
          title="Selectivity beats volume"
          desc="Industry average: 78% of slates get action. SharpPicks: ~30%. That difference is the edge."
        />
        <InsightCard
          title="Process over outcomes"
          desc="All signals tracked publicly. No deletes. Confidence calibrated, not exaggerated."
        />
      </div>

      <div style={{
        display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px',
        marginBottom: 'var(--space-xl)',
      }}>
        <NopickStat value={data.picks_this_week ?? 2} label="Signals this week" />
        <NopickStat value={data.passes_this_week ?? 4} label="Passes this week" />
        <NopickStat value={`${data.selectivity ?? 33}%`} label="Selectivity" />
        <NopickStat value={data.days_per_bet ?? '3.2'} label="Days per signal" />
      </div>

      {onInsightTap && <InsightPassDayCTA onTap={onInsightTap} />}

      <p style={{
        fontFamily: 'var(--font-mono)',
        fontSize: 'var(--text-caption)',
        color: 'var(--text-tertiary)',
        textAlign: 'center',
        marginTop: 'var(--space-lg)',
        letterSpacing: '0.04em',
      }}>Discipline is the product.</p>
    </div>
  );
}

function InsightCard({ title, desc }) {
  return (
    <div style={{
      backgroundColor: 'var(--surface-1)',
      borderRadius: '14px',
      border: '1px solid var(--color-border)',
      padding: 'var(--space-md)',
    }}>
      <h3 style={{
        fontFamily: 'var(--font-sans)',
        fontSize: '15px', fontWeight: 600,
        color: 'var(--text-primary)',
        marginBottom: 'var(--space-sm)',
      }}>{title}</h3>
      <p style={{
        fontSize: '13px',
        color: 'var(--text-secondary)',
        lineHeight: '1.55',
      }}>{desc}</p>
    </div>
  );
}

function NopickStat({ value, label }) {
  return (
    <div style={{
      backgroundColor: 'var(--surface-1)',
      border: '1px solid var(--color-border)',
      borderRadius: '12px',
      padding: 'var(--space-md)',
      textAlign: 'center',
    }}>
      <div style={{
        fontFamily: 'var(--font-mono)',
        fontSize: '22px', fontWeight: 700,
        fontVariantNumeric: 'tabular-nums',
        color: 'var(--text-primary)',
        marginBottom: '4px',
      }}>{value}</div>
      <div style={{
        fontFamily: 'var(--font-mono)',
        fontSize: '10px', fontWeight: 700,
        letterSpacing: '0.08em',
        textTransform: 'uppercase',
        color: 'var(--text-tertiary)',
      }}>{label}</div>
    </div>
  );
}
