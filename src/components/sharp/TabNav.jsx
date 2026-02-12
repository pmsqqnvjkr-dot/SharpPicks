export default function TabNav({ activeTab, onTabChange }) {
  const tabs = [
    { id: 'picks', label: 'Picks', icon: TargetIcon },
    { id: 'performance', label: 'Performance', icon: ChartIcon },
    { id: 'profile', label: 'Profile', icon: PersonIcon },
  ];

  return (
    <nav aria-label="Main navigation" role="tablist" style={{
      position: 'fixed',
      bottom: 'calc(16px + env(safe-area-inset-bottom, 0px))',
      left: '50%',
      transform: 'translateX(-50%)',
      display: 'flex',
      alignItems: 'center',
      gap: '4px',
      padding: '6px',
      borderRadius: '28px',
      background: 'rgba(13, 16, 23, 0.72)',
      backdropFilter: 'blur(24px) saturate(180%)',
      WebkitBackdropFilter: 'blur(24px) saturate(180%)',
      border: '1px solid rgba(255, 255, 255, 0.08)',
      boxShadow: '0 8px 32px rgba(0, 0, 0, 0.4), 0 0 0 0.5px rgba(255, 255, 255, 0.05) inset',
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
              background: isActive
                ? 'radial-gradient(ellipse at center, rgba(52, 211, 153, 0.15) 0%, rgba(52, 211, 153, 0.04) 70%, transparent 100%)'
                : 'transparent',
              border: 'none',
              borderRadius: '22px',
              width: '48px',
              height: '48px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              cursor: 'pointer',
              transition: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
              boxShadow: isActive
                ? '0 0 16px rgba(52, 211, 153, 0.12), 0 0 4px rgba(52, 211, 153, 0.08)'
                : 'none',
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
  const color = active ? '#34D399' : 'rgba(156, 163, 175, 0.5)';
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" style={{ transition: 'stroke 0.3s', filter: active ? 'drop-shadow(0 0 4px rgba(52, 211, 153, 0.3))' : 'none' }}>
      <circle cx="12" cy="12" r="10"/>
      <circle cx="12" cy="12" r="6"/>
      <circle cx="12" cy="12" r="2"/>
    </svg>
  );
}

function ChartIcon({ active }) {
  const color = active ? '#34D399' : 'rgba(156, 163, 175, 0.5)';
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" style={{ transition: 'stroke 0.3s', filter: active ? 'drop-shadow(0 0 4px rgba(52, 211, 153, 0.3))' : 'none' }}>
      <path d="M3 3v18h18"/>
      <path d="M7 16l4-8 4 4 5-9"/>
    </svg>
  );
}

function PersonIcon({ active }) {
  const color = active ? '#34D399' : 'rgba(156, 163, 175, 0.5)';
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" style={{ transition: 'stroke 0.3s', filter: active ? 'drop-shadow(0 0 4px rgba(52, 211, 153, 0.3))' : 'none' }}>
      <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/>
      <circle cx="12" cy="7" r="4"/>
    </svg>
  );
}
