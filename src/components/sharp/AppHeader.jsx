import { useState } from 'react';
import { Capacitor } from '@capacitor/core';
import { useAuth } from '../../hooks/useAuth';
import { useSport } from '../../hooks/useSport';
import Wordmark from './Wordmark';

const PROD_URL = 'https://app.sharppicks.ai';
const NATIVE_API = Capacitor.isNativePlatform() ? PROD_URL : '';

export default function AppHeader({ onNavigate }) {
  const { user, logout } = useAuth();
  const { sport, setSport } = useSport();
  const isAdmin = user?.is_superuser;

  const openCommandCenter = async () => {
    try {
      const r = await fetch(`${NATIVE_API}/api/admin/token`, { credentials: 'include' });
      if (r.ok) { const d = await r.json(); window.location.href = '/admin?t=' + d.token; }
      else { window.location.href = '/admin'; }
    } catch { window.location.href = '/admin'; }
  };

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
          <Wordmark size={16} />
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          {user?.first_name && (
            <div style={{
              fontSize: '11px', color: '#8C9AB0',
              fontFamily: "'Inter', var(--font-sans), sans-serif",
            }}>Welcome back, {user.first_name}</div>
          )}
        {isAdmin && (
          <button
            onClick={openCommandCenter}
            style={{
              background: 'none', border: 'none', cursor: 'pointer',
              padding: '12px', display: 'flex', alignItems: 'center',
              justifyContent: 'center', minWidth: '44px', minHeight: '44px',
              margin: '-6px',
            }}
            aria-label="Command Center"
          >
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="var(--text-secondary)" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
              <path d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.066 2.573c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.573 1.066c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.066-2.573c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"/>
              <circle cx="12" cy="12" r="3"/>
            </svg>
          </button>
        )}
        </div>
      </div>

      <SportFilterPills sport={sport} setSport={setSport} />
    </div>
  );
}

const SPORT_CONFIG = {
  nba: { label: 'NBA', color: '#d4874d', active: true },
  mlb: { label: 'MLB', color: '#3B82F6', active: true, badge: 'BETA' },
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
            {cfg.badge && (
              <span style={{
                fontSize: '8px', fontWeight: 600,
                padding: '1px 4px', borderRadius: '4px',
                backgroundColor: `${cfg.color}20`,
                color: cfg.color,
                letterSpacing: '0',
              }}>{cfg.badge}</span>
            )}
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
