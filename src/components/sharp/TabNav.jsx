export default function TabNav({ activeTab, onTabChange }) {
  const tabs = [
    { id: 'picks', label: 'Picks', icon: TargetIcon },
    { id: 'performance', label: 'Performance', icon: ChartIcon },
    { id: 'profile', label: 'Profile', icon: PersonIcon },
  ];

  return (
    <nav aria-label="Main navigation" role="tablist" style={{
      position: 'fixed',
      bottom: 0,
      left: '50%',
      transform: 'translateX(-50%)',
      width: '100%',
      maxWidth: '480px',
      display: 'flex',
      justifyContent: 'center',
      alignItems: 'center',
      gap: '32px',
      padding: '10px 0 calc(6px + env(safe-area-inset-bottom, 0px))',
      background: 'var(--bg-primary)',
      borderTop: '1px solid rgba(255, 255, 255, 0.04)',
      zIndex: 100,
    }}>
      {tabs.map(tab => {
        const isActive = activeTab === tab.id;
        return (
          <button
            key={tab.id}
            onClick={() => onTabChange(tab.id)}
            role="tab"
            aria-label={tab.label}
            aria-selected={isActive}
            aria-current={isActive ? 'page' : undefined}
            style={{
              position: 'relative',
              background: isActive ? 'rgba(52, 211, 153, 0.06)' : 'none',
              border: 'none',
              borderRadius: '8px',
              padding: '6px 10px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              cursor: 'pointer',
              color: isActive ? 'var(--green-profit)' : 'rgba(255,255,255,0.5)',
              opacity: isActive ? 1 : 0.6,
              transition: 'color 0.2s, background 0.2s',
            }}
          >
            <tab.icon />
          </button>
        );
      })}
    </nav>
  );
}

function TargetIcon() {
  return (
    <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="12" r="10"/>
      <circle cx="12" cy="12" r="6"/>
      <circle cx="12" cy="12" r="2"/>
    </svg>
  );
}

function ChartIcon() {
  return (
    <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <path d="M3 3v18h18"/>
      <path d="M7 16l4-8 4 4 5-9"/>
    </svg>
  );
}

function PersonIcon() {
  return (
    <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/>
      <circle cx="12" cy="7" r="4"/>
    </svg>
  );
}
