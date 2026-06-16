import { useState } from 'react';
import { Capacitor } from '@capacitor/core';
import { useAuth } from '../../hooks/useAuth';
import { useSport } from '../../hooks/useSport';
import { useLaunchConfig } from '../../hooks/useLaunchConfig';
import { getStateTokens } from '../empty-state/stateTokens';
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
      // env(safe-area-inset-top) extends the gradient up through the
      // iOS status bar / notch area so the SHARPPICKS wordmark and
      // Welcome text aren't clobbered by the 5G/battery icons. The
      // 0px fallback keeps web/Android rendering unchanged.
      paddingTop: 'env(safe-area-inset-top, 0px)',
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

// Sport pills use the v4.3 brand palette. Active pill: state-colored
// border + fill + label (sage for live, steel for off-season, amber for
// pre-launch calibration). Per-sport identity colors (NBA orange, MLB
// blue, WNBA pink) were retired 2026-05-06.
//
// Per-sport state comes from /api/public/launch-config:
//   nba.in_season=false       -> 'offseason' (steel dot)
//   nfl.launched=false        -> 'calibration' (amber dot)
//   otherwise                 -> 'live' (green dot)
const SPORT_CONFIG = {
  nba:  { label: 'NBA' },
  mlb:  { label: 'MLB' },
  wnba: { label: 'WNBA' },
  nfl:  { label: 'NFL' },
};
const PILL_ORDER = ['nba', 'mlb', 'wnba', 'nfl'];

const SP_BORDER = 'rgba(255, 255, 255, 0.08)';
const SP_TEXT_2 = 'rgba(232, 234, 237, 0.7)';

function sportState(key, config) {
  const entry = config?.sports?.[key];
  if (!entry) return 'live';
  if (entry.launched === false) return 'calibration';
  if (entry.in_season === false) return 'offseason';
  return 'live';
}

function chipAccent(state) {
  if (state === 'offseason') return getStateTokens('steel');
  if (state === 'calibration') return getStateTokens('amber');
  return getStateTokens('green');
}

function SportFilterPills({ sport, setSport }) {
  const { config } = useLaunchConfig();
  return (
    <div style={{
      display: 'flex', gap: '8px', padding: '0 20px 10px',
      flexWrap: 'wrap',
    }}>
      {PILL_ORDER.map(key => {
        const cfg = SPORT_CONFIG[key];
        const selected = sport === key;
        const accent = chipAccent(sportState(key, config));
        return (
          <button
            key={key}
            onClick={() => setSport(key)}
            style={{
              display: 'flex', alignItems: 'center', gap: '6px',
              padding: '10px 16px', borderRadius: '999px',
              minHeight: '40px',
              fontSize: '11px', fontWeight: 500,
              fontFamily: '"JetBrains Mono", "JetBrains Mono Variable", monospace',
              textTransform: 'uppercase',
              letterSpacing: '0.16em',
              border: `1px solid ${selected ? accent.border : SP_BORDER}`,
              backgroundColor: selected ? accent.soft : 'transparent',
              color: selected ? accent.color : SP_TEXT_2,
              cursor: 'pointer',
              transition: 'background-color 0.15s, border-color 0.15s, color 0.15s',
            }}
          >
            <span style={{
              width: '6px', height: '6px', borderRadius: '50%',
              backgroundColor: accent.color,
            }} />
            {cfg.label}
          </button>
        );
      })}
    </div>
  );
}
