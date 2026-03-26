import { useState, useEffect, useRef } from 'react';
import { Capacitor } from '@capacitor/core';
import { useAuth } from '../../hooks/useAuth';
import { useSport } from '../../hooks/useSport';

const PROD_URL = 'https://app.sharppicks.ai';
const NATIVE_API = Capacitor.isNativePlatform() ? PROD_URL : '';

export default function AppHeader({ onNavigate }) {
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

  const nav = (tab) => { setMenuOpen(false); onNavigate?.(tab); };

  const menuItems = [
    { label: 'Signals', icon: 'M13 10V3L4 14h7v7l9-11h-7z', action: () => nav('picks') },
    { label: 'Market', icon: 'M3 3v18h18M7 16l4-8 4 4 4-6', action: () => nav('market') },
    { label: 'Results', icon: 'M16 8v8m-8-4v4m4-12v12', action: () => nav('performance') },
    { label: 'Insights', icon: 'M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253', action: () => nav('insights') },
    { label: 'Account', icon: 'M20 21v-2a4 4 0 00-4-4H8a4 4 0 00-4 4v2M12 3a4 4 0 100 8 4 4 0 000-8z', action: () => nav('profile') },
    { label: 'How It Works', icon: 'M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z', action: () => { setMenuOpen(false); onNavigate?.('profile', 'how'); } },
    { type: 'divider' },
    ...(user?.is_superuser ? [
      { label: 'Command Center', icon: 'M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.066 2.573c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.573 1.066c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.066-2.573c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065zM15 12a3 3 0 11-6 0 3 3 0 016 0z', action: async () => { setMenuOpen(false); try { const r = await fetch(`${NATIVE_API}/api/admin/token`, { credentials: 'include' }); if (r.ok) { const d = await r.json(); window.location.href = '/admin?t=' + d.token; } else { window.location.href = '/admin'; } } catch(e) { window.location.href = '/admin'; } } },
      { type: 'divider' },
    ] : []),
    { label: 'Sign Out', icon: 'M9 21H5a2 2 0 01-2-2V5a2 2 0 012-2h4M16 17l5-5-5-5M21 12H9', action: () => { logout(); setMenuOpen(false); }, danger: true },
  ];

  if (!user) return null;

  return (
    <div style={{
      background: 'linear-gradient(to bottom, #0E1A2B, #08121F)',
      borderBottom: '1px solid rgba(255,255,255,0.06)',
    }}>
      <div style={{
        padding: '16px 20px 10px',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
      }}>
        <div
          onClick={() => onNavigate('picks')}
          style={{ display: 'flex', alignItems: 'center', cursor: 'pointer' }}
        >
          <span style={{
            fontFamily: 'var(--font-sans)',
            fontSize: '13px',
            fontWeight: 500,
            color: '#E8EAED',
            letterSpacing: '0.25em',
            textTransform: 'uppercase',
            lineHeight: 1,
            display: 'inline-flex',
            alignItems: 'center',
          }}>SHARP<span style={{ display: 'inline-flex', gap: '0.18em', margin: '0 0.4em', alignSelf: 'center' }}><span style={{ display: 'block', width: '0.08em', height: '1.24em', background: 'currentColor', borderRadius: 999 }} /><span style={{ display: 'block', width: '0.08em', height: '1.24em', background: 'currentColor', borderRadius: 999 }} /></span>PICKS</span>
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
                padding: '12px', display: 'flex', alignItems: 'center',
                justifyContent: 'center', minWidth: '44px', minHeight: '44px',
                margin: '-6px',
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
      </div>

      <SportFilterPills sport={sport} setSport={setSport} />
    </div>
  );
}

const SPORT_CONFIG = {
  nba: { label: 'NBA', color: '#d4874d', active: true },
  mlb: { label: 'MLB', color: '#3B82F6', active: true },
  wnba: { label: 'WNBA', color: '#EC4899', active: false },
};

function SportFilterPills({ sport, setSport }) {
  const pills = ['nba', 'mlb', 'wnba'];
  return (
    <div style={{
      display: 'flex', gap: '8px', padding: '0 20px 10px',
    }}>
      {pills.map(key => {
        const cfg = SPORT_CONFIG[key];
        const selected = sport === key;
        const comingSoon = !cfg.active;
        return (
          <button
            key={key}
            onClick={() => { if (!comingSoon) setSport(key); }}
            style={{
              display: 'flex', alignItems: 'center', gap: '6px',
              padding: '10px 16px', borderRadius: '20px',
              minHeight: '40px',
              fontSize: '11px', fontWeight: 700,
              fontFamily: 'var(--font-mono)',
              textTransform: 'uppercase',
              letterSpacing: '0.06em',
              border: selected ? `1px solid ${cfg.color}` : '1px solid var(--stroke-subtle)',
              backgroundColor: selected ? `${cfg.color}15` : 'transparent',
              color: comingSoon ? 'var(--text-tertiary)' : selected ? cfg.color : 'var(--text-secondary)',
              cursor: comingSoon ? 'default' : 'pointer',
              opacity: comingSoon ? 0.5 : 1,
              transition: 'all 0.2s',
            }}
          >
            <span style={{
              width: '6px', height: '6px', borderRadius: '50%',
              backgroundColor: selected ? cfg.color : comingSoon ? 'var(--text-tertiary)' : 'var(--text-secondary)',
            }} />
            {cfg.label}
            {comingSoon && (
              <span style={{
                fontSize: '8px', fontWeight: 600,
                padding: '1px 4px', borderRadius: '4px',
                backgroundColor: 'rgba(255,255,255,0.06)',
                color: 'var(--text-tertiary)',
                letterSpacing: '0',
              }}>SOON</span>
            )}
          </button>
        );
      })}
    </div>
  );
}
