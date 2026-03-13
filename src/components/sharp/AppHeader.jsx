import { useState, useEffect, useRef } from 'react';
import { Capacitor } from '@capacitor/core';
import { useAuth } from '../../hooks/useAuth';
import { useSport } from '../../hooks/useSport';

const PROD_URL = 'https://app.sharppicks.ai';
const NATIVE_API = Capacitor.isNativePlatform() ? PROD_URL : '';

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

  const greeting = user?.first_name || null;

  const menuItems = [
    ...(user?.is_superuser ? [
      { label: 'Command Center', icon: 'M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.066 2.573c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.573 1.066c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.066-2.573c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065zM15 12a3 3 0 11-6 0 3 3 0 016 0z', action: async () => { setMenuOpen(false); try { const r = await fetch(`${NATIVE_API}/api/admin/token`, { credentials: 'include' }); if (r.ok) { const d = await r.json(); window.location.href = '/admin?t=' + d.token; } else { window.location.href = '/admin'; } } catch(e) { window.location.href = '/admin'; } } },
      { type: 'divider' },
    ] : []),
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
      <div
        onClick={() => onNavigate('picks')}
        style={{ display: 'flex', alignItems: 'center', cursor: 'pointer' }}
      >
        <img src="/images/crest.png" alt="" width="26" height="26" style={{ display: 'block', marginRight: '16px', flexShrink: 0, objectFit: 'contain' }} />
        <span style={{
          fontFamily: 'var(--font-sans)',
          fontSize: '13px',
          fontWeight: 600,
          color: '#F2F4F8',
          letterSpacing: '3.9px',
          textTransform: 'uppercase',
          lineHeight: 1,
        }}>SHARP<span style={{ opacity: 0.65, margin: '0 0.45em', fontWeight: 500, letterSpacing: '0.18em' }}>||</span>PICKS</span>
      </div>

      <div style={{ position: 'relative' }} ref={menuRef}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          {greeting && (
            <span style={{
              fontSize: '11px', color: 'rgba(255,255,255,0.55)',
              fontFamily: 'var(--font-sans)', fontWeight: 400,
            }}>
              Welcome back, {greeting}
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
          {['nba', 'mlb', 'wnba'].map(s => (
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
