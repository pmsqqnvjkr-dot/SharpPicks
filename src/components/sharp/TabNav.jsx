export default function TabNav({ activeTab, onTabChange }) {
  const tabs = [
    { id: 'picks', label: 'Picks', icon: TargetIcon },
    { id: 'performance', label: 'Performance', icon: ChartIcon },
    { id: 'profile', label: 'Profile', icon: PersonIcon },
  ];

  return (
    <nav aria-label="Main navigation" role="tablist" style={{
      position: 'fixed',
      bottom: 'env(safe-area-inset-bottom, 0px)',
      left: '50%',
      transform: 'translateX(-50%)',
      display: 'flex',
      alignItems: 'center',
      gap: '2px',
      padding: '4px 6px',
      borderRadius: '20px',
      background: 'rgba(10, 13, 20, 0.85)',
      backdropFilter: 'blur(20px) saturate(150%)',
      WebkitBackdropFilter: 'blur(20px) saturate(150%)',
      border: '1px solid rgba(255, 255, 255, 0.06)',
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
              background: 'none',
              border: 'none',
              borderRadius: '16px',
              width: '40px',
              height: '36px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              cursor: 'pointer',
              transition: 'opacity 0.2s',
              opacity: isActive ? 1 : 0.4,
            }}
          >
            <tab.icon active={isActive} />
          </button>
        );
      })}
    </nav>
  );
}

function TargetIcon({ active }) {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke={active ? 'var(--text-primary)' : 'var(--text-secondary)'} strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="12" r="10"/>
      <circle cx="12" cy="12" r="6"/>
      <circle cx="12" cy="12" r="2"/>
    </svg>
  );
}

function ChartIcon({ active }) {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke={active ? 'var(--text-primary)' : 'var(--text-secondary)'} strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <path d="M3 3v18h18"/>
      <path d="M7 16l4-8 4 4 5-9"/>
    </svg>
  );
}

function PersonIcon({ active }) {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke={active ? 'var(--text-primary)' : 'var(--text-secondary)'} strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/>
      <circle cx="12" cy="7" r="4"/>
    </svg>
  );
}
