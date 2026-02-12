export function EmptyNoPicks() {
  return (
    <EmptyStateCard
      icon={
        <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="var(--text-tertiary)" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
          <path d="M12 8v4M12 16h.01"/>
          <circle cx="12" cy="12" r="10"/>
        </svg>
      }
      title="No picks yet"
      description="We publish only when the data shows an edge. Your first pick may not be today."
    />
  );
}

export function EmptyNoTrackedBets() {
  return (
    <EmptyStateCard
      icon={
        <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="var(--text-tertiary)" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
          <path d="M9 11l3 3L22 4"/>
          <path d="M21 12v7a2 2 0 01-2 2H5a2 2 0 01-2-2V5a2 2 0 012-2h11"/>
        </svg>
      }
      title="No tracked bets"
      description="Tracking decisions builds discipline over time."
    />
  );
}

export function EmptyNoChartData() {
  return (
    <EmptyStateCard
      icon={
        <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="var(--text-tertiary)" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
          <path d="M3 3v18h18"/>
          <path d="M7 17l4-4 4 4 6-6"/>
        </svg>
      }
      title="No chart data yet"
      description="No decisions logged yet. Your equity curve will appear after your first tracked outcome."
    />
  );
}

function EmptyStateCard({ icon, title, description }) {
  return (
    <div style={{
      textAlign: 'center', padding: '40px 24px',
    }}>
      <div style={{
        width: '64px', height: '64px', borderRadius: '16px',
        backgroundColor: 'var(--surface-1)', border: '1px solid var(--stroke-subtle)',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        margin: '0 auto 20px',
      }}>
        {icon}
      </div>
      <h2 style={{
        fontFamily: 'var(--font-serif)', fontSize: '20px',
        fontWeight: 600, color: 'var(--text-primary)', marginBottom: '8px',
      }}>{title}</h2>
      <p style={{
        fontSize: '14px', color: 'var(--text-secondary)',
        lineHeight: '1.6', maxWidth: '280px', margin: '0 auto',
      }}>{description}</p>
    </div>
  );
}
