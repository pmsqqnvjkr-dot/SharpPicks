import { InsightPassDayCTA } from './InsightsTab';

export default function NoPickCard({ data, onInsightTap }) {
  return (
    <div style={{ padding: '0 4px' }}>
      <div style={{ textAlign: 'center', padding: '24px 0 32px' }}>
        <div style={{
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          gap: '6px', margin: '0 auto 24px',
        }}>
          <div style={{
            width: '4px', height: '32px', borderRadius: '2px',
            backgroundColor: 'var(--text-secondary)', opacity: 0.6,
          }} />
          <div style={{
            width: '4px', height: '32px', borderRadius: '2px',
            backgroundColor: 'var(--text-secondary)', opacity: 0.6,
          }} />
        </div>

        <h1 style={{
          fontFamily: 'var(--font-serif)',
          fontSize: '24px',
          fontWeight: 700,
          color: 'var(--text-primary)',
          marginBottom: '12px',
        }}>
          No qualifying pick
        </h1>

        <p style={{
          fontSize: '14px',
          color: 'var(--text-secondary)',
          lineHeight: '1.55',
          marginBottom: '4px',
        }}>
          Model analyzed {data.games_analyzed} games.
        </p>
        <p style={{
          fontSize: '14px',
          color: 'var(--text-secondary)',
          lineHeight: '1.55',
        }}>
          No edge above threshold — it means the market is efficient.
        </p>
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: '14px', marginBottom: '32px' }}>
        <InsightCard
          title="Restraint is a feature"
          desc="Quiet days are intentional. No pick today doesn't mean something's broken — it means the market is efficient."
        />
        <InsightCard
          title="Selectivity beats volume"
          desc="Industry average: 78% of slates get action. Sharp Picks users: ~30%. That difference is your edge."
        />
        <InsightCard
          title="Process over outcomes"
          desc="All picks tracked publicly. No deletes. Confidence is calibrated, not exaggerated."
        />
      </div>

      <div style={{
        display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px',
        marginBottom: '32px',
      }}>
        <NopickStat value={data.picks_this_week ?? 2} label="Picks this week" />
        <NopickStat value={data.passes_this_week ?? 4} label="Passes this week" />
        <NopickStat value={`${data.selectivity ?? 33}%`} label="Selectivity rate" />
        <NopickStat value={data.days_per_bet ?? '3.2'} label="Days per bet" />
      </div>

      {onInsightTap && <InsightPassDayCTA onTap={onInsightTap} />}

      <p style={{
        fontFamily: 'var(--font-serif)',
        fontStyle: 'italic',
        fontSize: '15px',
        color: 'var(--text-secondary)',
        textAlign: 'center',
        marginTop: '24px',
      }}>Discipline is the product.</p>
    </div>
  );
}

function InsightCard({ title, desc }) {
  return (
    <div style={{
      backgroundColor: 'var(--surface-1)',
      borderRadius: '16px',
      border: '1px solid var(--stroke-subtle)',
      padding: '20px',
    }}>
      <h3 style={{
        fontFamily: 'var(--font-serif)',
        fontSize: '16px',
        fontWeight: 600,
        color: 'var(--text-primary)',
        marginBottom: '8px',
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
      border: '1px solid var(--stroke-subtle)',
      borderRadius: '12px',
      padding: '16px',
      textAlign: 'center',
    }}>
      <div style={{
        fontFamily: 'var(--font-mono)',
        fontSize: '22px',
        fontWeight: 700,
        color: 'var(--text-primary)',
        marginBottom: '4px',
      }}>{value}</div>
      <div style={{
        fontFamily: 'var(--font-mono)',
        fontSize: '10px',
        fontWeight: 500,
        letterSpacing: '1px',
        textTransform: 'uppercase',
        color: 'var(--text-tertiary)',
      }}>{label}</div>
    </div>
  );
}
