import { useState } from 'react';
import { Link } from 'react-router-dom';
import DailyTopSignalCard from '../components/sharp/DailyTopSignalCard';

// Static preview route for the v4.3 paywalled DailyTopSignalCard.
// Lives at /preview/paywalled-signal so QA can see the card render
// even on days when no real signal has fired (or every signal is
// already revoked / resolved). Switch sport / phase from the controls
// at the top to confirm the calibration tag and copy variants.
//
// Remove after P1 sign-off.

const BASE_PICK = {
  away_team: 'Texas Rangers',
  home_team: 'New York Yankees',
  side: 'Texas Rangers +1.5',
  line: 1.5,
  edge_pct: 6.0,
  position_size_pct: 1.5,
  model_phase: 'calibration',
  sport: 'mlb',
  model_signals: [
    "Bullpen edge: New York Yankees bullpen is significantly more fatigued. Late-inning advantage in a game projected to go nine.",
    "Model edge: +6.0% above the qualification threshold.",
  ],
};

const VARIANTS = {
  mlb_calibration: { ...BASE_PICK, sport: 'mlb', model_phase: 'calibration' },
  mlb_deployment: { ...BASE_PICK, sport: 'mlb', model_phase: 'deployment' },
  wnba_calibration: { ...BASE_PICK, sport: 'wnba', model_phase: 'calibration' },
  nba_deployment: {
    ...BASE_PICK, sport: 'nba', model_phase: 'deployment',
    side: 'Boston Celtics -3.5', line: -3.5, edge_pct: 8.4,
    away_team: 'Boston Celtics', home_team: 'Indiana Pacers',
    model_signals: ['Pace edge: Indiana plays significantly faster than season average. Total likely to push.'],
  },
  high_edge: { ...BASE_PICK, edge_pct: 11.2, position_size_pct: 2.5 },
};

export default function PaywallPreview() {
  const [variantKey, setVariantKey] = useState('mlb_calibration');
  const pick = VARIANTS[variantKey];

  return (
    <div style={{ minHeight: '100vh', background: 'var(--sp-bg, #0A0D14)', color: 'var(--sp-text, #E8EAED)', fontFamily: '"Inter", system-ui, sans-serif' }}>
      <div style={{ borderBottom: '1px solid rgba(255,255,255,0.06)', padding: '14px 20px', display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '12px', flexWrap: 'wrap' }}>
        <div style={{ fontFamily: 'var(--sp-font-mono, "JetBrains Mono", monospace)', fontSize: '10px', letterSpacing: '0.22em', textTransform: 'uppercase', color: 'var(--sp-amber, #F59E0B)' }}>
          Preview · Paywalled Signal Card
        </div>
        <Link to="/" style={{ fontFamily: 'var(--sp-font-mono, "JetBrains Mono", monospace)', fontSize: '11px', color: 'var(--sp-text-2, rgba(232,234,237,0.7))', textDecoration: 'none', border: '1px solid rgba(255,255,255,0.12)', padding: '6px 12px', borderRadius: '6px' }}>
          Exit preview
        </Link>
      </div>

      <div style={{ padding: '20px', display: 'flex', gap: '8px', flexWrap: 'wrap', borderBottom: '1px solid rgba(255,255,255,0.04)' }}>
        {Object.keys(VARIANTS).map((key) => (
          <button
            key={key}
            onClick={() => setVariantKey(key)}
            style={{
              padding: '6px 12px',
              borderRadius: '6px',
              fontFamily: 'var(--sp-font-mono, "JetBrains Mono", monospace)',
              fontSize: '10px',
              letterSpacing: '0.12em',
              textTransform: 'uppercase',
              cursor: 'pointer',
              border: variantKey === key ? '1px solid var(--sp-green, #5A9E72)' : '1px solid rgba(255,255,255,0.08)',
              background: variantKey === key ? 'rgba(90,158,114,0.1)' : 'transparent',
              color: variantKey === key ? 'var(--sp-green, #5A9E72)' : 'var(--sp-text-2, rgba(232,234,237,0.7))',
            }}
          >
            {key.replace(/_/g, ' ')}
          </button>
        ))}
      </div>

      <div style={{ maxWidth: '440px', margin: '0 auto', padding: '24px 20px' }}>
        <DailyTopSignalCard pick={pick} sport={pick.sport} onUpgrade={() => alert('Upgrade tapped (preview)')} />

        <div style={{ marginTop: '24px', padding: '16px', background: 'var(--sp-surface, #121725)', borderRadius: '10px', border: '1px solid rgba(255,255,255,0.06)' }}>
          <div style={{ fontFamily: 'var(--sp-font-mono, "JetBrains Mono", monospace)', fontSize: '9px', letterSpacing: '0.22em', textTransform: 'uppercase', color: 'var(--sp-text-3, rgba(232,234,237,0.45))', marginBottom: '8px' }}>
            Inputs feeding the card
          </div>
          <pre style={{ margin: 0, fontSize: '11px', fontFamily: 'var(--sp-font-mono, "JetBrains Mono", monospace)', color: 'var(--sp-text-2, rgba(232,234,237,0.7))', whiteSpace: 'pre-wrap', wordBreak: 'break-all' }}>
{JSON.stringify(pick, null, 2)}
          </pre>
        </div>
      </div>
    </div>
  );
}
