export default function TabNav({ activeTab, onTabChange }) {
  const tabs = [
    { id: 'today', label: 'Today', icon: ClockIcon },
    { id: 'dashboard', label: 'Dashboard', icon: ChartIcon },
    { id: 'profile', label: 'Profile', icon: PersonIcon },
  ];

  return (
    <nav style={{
      position: 'fixed',
      bottom: 0,
      left: '50%',
      transform: 'translateX(-50%)',
      width: '100%',
      maxWidth: '480px',
      backgroundColor: 'var(--surface-1)',
      borderTop: '1px solid var(--stroke-subtle)',
      display: 'flex',
      justifyContent: 'space-around',
      padding: '8px 0 env(safe-area-inset-bottom, 8px)',
      zIndex: 50,
    }}>
      {tabs.map(tab => (
        <button
          key={tab.id}
          onClick={() => onTabChange(tab.id)}
          style={{
            background: 'none',
            border: 'none',
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            gap: '4px',
            padding: '8px 16px',
            cursor: 'pointer',
            color: activeTab === tab.id ? 'var(--blue-primary)' : 'var(--text-tertiary)',
            transition: 'color 0.2s',
          }}
        >
          <tab.icon active={activeTab === tab.id} />
          <span style={{
            fontSize: '11px',
            fontWeight: activeTab === tab.id ? 600 : 400,
            fontFamily: 'var(--font-sans)',
          }}>
            {tab.label}
          </span>
        </button>
      ))}
    </nav>
  );
}

function ClockIcon({ active }) {
  return (
    <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke={active ? 'var(--blue-primary)' : 'var(--text-tertiary)'} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="12" r="10"/>
      <polyline points="12 6 12 12 16 14"/>
    </svg>
  );
}

function ChartIcon({ active }) {
  return (
    <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke={active ? 'var(--blue-primary)' : 'var(--text-tertiary)'} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <line x1="18" y1="20" x2="18" y2="10"/>
      <line x1="12" y1="20" x2="12" y2="4"/>
      <line x1="6" y1="20" x2="6" y2="14"/>
    </svg>
  );
}

function PersonIcon({ active }) {
  return (
    <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke={active ? 'var(--blue-primary)' : 'var(--text-tertiary)'} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/>
      <circle cx="12" cy="7" r="4"/>
    </svg>
  );
}
