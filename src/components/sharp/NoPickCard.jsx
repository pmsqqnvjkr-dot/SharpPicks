export default function NoPickCard({ data }) {
  return (
    <div>
      <div style={{ textAlign: 'center', padding: '40px 0 32px' }}>
        <div style={{
          width: '64px', height: '64px', borderRadius: '16px',
          backgroundColor: 'var(--surface-1)', border: '1px solid var(--stroke-subtle)',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          margin: '0 auto 24px',
        }}>
          <span style={{
            fontFamily: 'var(--font-mono)',
            fontSize: '22px',
            fontWeight: 700,
            color: 'var(--text-secondary)',
            letterSpacing: '0.05em',
          }}>00</span>
        </div>

        <h2 style={{
          fontFamily: 'var(--font-sans)',
          fontSize: '24px',
          fontWeight: 700,
          color: 'var(--text-primary)',
          marginBottom: '14px',
          fontStyle: 'italic',
        }}>
          No qualifying pick
        </h2>

        <p style={{
          fontSize: '14px',
          color: 'var(--text-secondary)',
          lineHeight: '1.7',
          maxWidth: '300px',
          margin: '0 auto',
        }}>
          Model analyzed {data.games_analyzed} games.
        </p>
        <p style={{
          fontSize: '14px',
          color: 'var(--text-secondary)',
          lineHeight: '1.7',
          maxWidth: '300px',
          margin: '4px auto 0',
        }}>
          No edge above threshold — it means the market is efficient.
        </p>
      </div>

      <InsightCard
        title="Restraint is a feature"
        desc="Quiet days are intentional. No pick today doesn't mean something's broken — it means the market is efficient."
      />

      <InsightCard
        title="Selectivity beats volume"
        desc="Industry average: 78% of slates get action. Sharp Picks users: ~30%. That difference is your edge."
      />
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
      marginBottom: '12px',
    }}>
      <div style={{
        fontFamily: 'var(--font-sans)',
        fontSize: '16px',
        fontWeight: 700,
        color: 'var(--text-primary)',
        marginBottom: '6px',
        fontStyle: 'italic',
      }}>{title}</div>
      <p style={{
        fontSize: '14px',
        color: 'var(--text-secondary)',
        lineHeight: '1.6',
      }}>{desc}</p>
    </div>
  );
}
