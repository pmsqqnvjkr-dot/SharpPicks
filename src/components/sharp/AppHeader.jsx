import { useState, useEffect, useRef } from 'react';
import { useAuth } from '../../hooks/useAuth';
import { useSport } from '../../hooks/useSport';

export default function AppHeader({ onNavigate, showSportToggle }) {
  const { user, logout } = useAuth();
  const { sport, setSport } = useSport();
  const [menuOpen, setMenuOpen] = useState(false);
  const menuRef = useRef(null);

  useEffect(() => {
    if (!menuOpen) return;
    const handleClick = (e) => {
      if (menuRef.current && !menuRef.current.contains(e.target)) setMenuOpen(false);
    };
    document.addEventListener('mousedown', handleClick);
    return () => document.removeEventListener('mousedown', handleClick);
  }, [menuOpen]);

  const greeting = (() => {
    if (!user?.first_name) return null;
    const h = new Date().toLocaleString('en-US', { hour: 'numeric', hour12: false, timeZone: 'America/New_York' });
    const hr = parseInt(h);
    const period = hr < 12 ? 'Good morning' : hr < 17 ? 'Good afternoon' : 'Good evening';
    return `${period}, ${user.first_name}`;
  })();

  const menuItems = [
    { label: 'Picks', icon: 'M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z', action: () => { onNavigate('picks'); setMenuOpen(false); } },
    { label: 'Performance', icon: 'M3 3v18h18M7 16l4-4 4 4 5-5', action: () => { onNavigate('performance'); setMenuOpen(false); } },
    { label: 'Sharp Journal', icon: 'M4 19.5A2.5 2.5 0 016.5 17H20M4 19.5V5a2 2 0 012-2h14v14H6.5A2.5 2.5 0 004 19.5z', action: () => { onNavigate('insights'); setMenuOpen(false); } },
    { label: 'Membership', icon: 'M20 21v-2a4 4 0 00-4-4H8a4 4 0 00-4 4v2M12 3a4 4 0 100 8 4 4 0 000-8z', action: () => { onNavigate('profile'); setMenuOpen(false); } },
    ...(user?.is_superuser ? [
      { type: 'divider' },
      { label: 'Command Center', icon: 'M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.066 2.573c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.573 1.066c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.066-2.573c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065zM15 12a3 3 0 11-6 0 3 3 0 016 0z', action: async () => { setMenuOpen(false); try { const r = await fetch('/api/admin/token', { credentials: 'include' }); if (r.ok) { const d = await r.json(); window.location.href = '/admin?t=' + d.token; } else { window.location.href = '/admin'; } } catch(e) { window.location.href = '/admin'; } } },
    ] : []),
    { type: 'divider' },
    { label: 'Sign Out', icon: 'M9 21H5a2 2 0 01-2-2V5a2 2 0 012-2h4M16 17l5-5-5-5M21 12H9', action: () => { logout(); setMenuOpen(false); }, danger: true },
  ];

  if (!user) return null;

  return (
    <div style={{
      padding: '16px 20px',
      display: 'flex',
      justifyContent: 'space-between',
      alignItems: 'center',
      background: 'linear-gradient(to bottom, #0E1A2B, #08121F)',
      borderBottom: '1px solid rgba(255,255,255,0.06)',
    }}>
      <div style={{ display: 'flex', alignItems: 'center' }}>
        <img src="/images/crest.png" alt="" width="22" height="22" style={{ display: 'block', marginRight: '14px', flexShrink: 0, objectFit: 'contain' }} />
        <span style={{
          fontFamily: 'var(--font-sans)',
          fontSize: '13px',
          fontWeight: 600,
          color: '#F2F4F8',
          letterSpacing: '3.9px',
          textTransform: 'uppercase',
          lineHeight: 1,
        }}>SHARP<span style={{ opacity: 0.65, margin: '0 0.6em', fontWeight: 500 }}>||</span>PICKS</span>
      </div>

      <div style={{ position: 'relative' }} ref={menuRef}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          {greeting && (
            <span style={{
              fontSize: '11px', color: 'rgba(255,255,255,0.55)',
              fontFamily: 'var(--font-sans)', fontWeight: 400,
            }}>
              {greeting}
            </span>
          )}
          <button
            onClick={() => setMenuOpen(!menuOpen)}
            style={{
              background: 'none', border: 'none', cursor: 'pointer',
              padding: '6px', display: 'flex', alignItems: 'center',
              justifyContent: 'center',
            }}
          >
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="var(--text-secondary)" strokeWidth="2" strokeLinecap="round">
              <line x1="3" y1="6" x2="21" y2="6"/>
              <line x1="3" y1="12" x2="21" y2="12"/>
              <line x1="3" y1="18" x2="21" y2="18"/>
            </svg>
          </button>
        </div>

        {menuOpen && (
          <div style={{
            position: 'absolute',
            top: '100%',
            right: 0,
            marginTop: '8px',
            backgroundColor: 'var(--surface-1)',
            border: '1px solid var(--stroke-subtle)',
            borderRadius: '12px',
            padding: '6px',
            minWidth: '180px',
            zIndex: 50,
            boxShadow: '0 8px 32px rgba(0,0,0,0.4)',
          }}>
            {menuItems.map((item, i) =>
              item.type === 'divider' ? (
                <div key={i} style={{ height: '1px', backgroundColor: 'var(--stroke-muted)', margin: '4px 8px' }} />
              ) : (
                <button
                  key={i}
                  onClick={item.action}
                  style={{
                    display: 'flex', alignItems: 'center', gap: '10px',
                    width: '100%', padding: '10px 12px',
                    background: 'none', border: 'none', cursor: 'pointer',
                    borderRadius: '8px',
                    color: item.danger ? 'var(--red-loss)' : 'var(--text-secondary)',
                    fontSize: '14px', fontFamily: 'var(--font-sans)',
                    textAlign: 'left',
                  }}
                  onMouseEnter={e => e.currentTarget.style.backgroundColor = 'var(--surface-2)'}
                  onMouseLeave={e => e.currentTarget.style.backgroundColor = 'transparent'}
                >
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                    <path d={item.icon}/>
                  </svg>
                  {item.label}
                </button>
              )
            )}
          </div>
        )}
      </div>

      {showSportToggle && (
        <div style={{
          display: 'flex',
          backgroundColor: 'var(--surface-1)',
          borderRadius: '8px',
          padding: '2px',
          border: '1px solid var(--stroke-subtle)',
          marginLeft: 'auto',
        }}>
          {['nba', 'wnba'].map(s => (
            <button
              key={s}
              onClick={() => setSport(s)}
              style={{
                padding: '4px 12px',
                fontSize: '11px',
                fontWeight: 600,
                fontFamily: 'var(--font-mono)',
                textTransform: 'uppercase',
                letterSpacing: '1px',
                border: 'none',
                borderRadius: '6px',
                cursor: 'pointer',
                backgroundColor: sport === s ? 'var(--blue-primary)' : 'transparent',
                color: sport === s ? '#fff' : 'var(--text-tertiary)',
                transition: 'all 0.2s',
              }}
            >
              {s}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
