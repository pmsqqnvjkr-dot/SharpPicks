import { useState } from 'react';
import { useApi } from '../../hooks/useApi';
import AuthModal from './AuthModal';

export default function LandingPage({ onEnterApp }) {
  const { data: stats } = useApi('/public/stats');
  const { data: founding } = useApi('/public/founding-count');
  const [showAuth, setShowAuth] = useState(false);
  const [authMode, setAuthMode] = useState('register');

  const spotsLeft = founding ? Math.max(0, 500 - (founding.current_count || 0)) : null;

  return (
    <div style={{
      minHeight: '100vh',
      backgroundColor: 'var(--bg-primary)',
      maxWidth: '480px',
      margin: '0 auto',
      overflow: 'auto',
    }}>
      <div style={{
        padding: '16px 20px',
        display: 'flex',
        alignItems: 'center',
        gap: '10px',
      }}>
        <img src="/logo-1024.png" alt="" style={{ width: '28px', height: '28px', borderRadius: '6px' }} />
        <span style={{
          fontFamily: 'var(--font-sans)',
          fontSize: '13px',
          fontWeight: 700,
          color: 'var(--text-primary)',
          letterSpacing: '0.12em',
          textTransform: 'uppercase',
        }}>Sharp Picks</span>
      </div>

      <div style={{ padding: '40px 24px 0', textAlign: 'center' }}>
        <div style={{
          width: '88px', height: '88px',
          margin: '0 auto 32px',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
        }}>
          <img src="/logo-1024.png" alt="Sharp Picks" style={{
            width: '88px', height: '88px', borderRadius: '20px',
          }} />
        </div>

        <h1 style={{
          fontFamily: 'var(--font-sans)',
          fontSize: '36px',
          fontWeight: 800,
          color: 'var(--text-primary)',
          letterSpacing: '-0.02em',
          lineHeight: '1.15',
          marginBottom: '12px',
        }}>
          One Pick Beats<br />Five
        </h1>

        <p style={{
          fontFamily: 'var(--font-serif)',
          fontSize: '16px',
          fontStyle: 'italic',
          color: 'var(--text-secondary)',
          marginBottom: '32px',
        }}>
          Discipline is the product.
        </p>

        <button
          onClick={() => { setAuthMode('register'); setShowAuth(true); }}
          style={{
            width: '100%',
            padding: '16px',
            backgroundColor: 'var(--blue-primary)',
            color: '#fff',
            border: 'none',
            borderRadius: '14px',
            fontSize: '16px',
            fontWeight: 600,
            cursor: 'pointer',
            fontFamily: 'var(--font-sans)',
            marginBottom: '24px',
          }}
        >
          Start Free
        </button>

        <div style={{
          display: 'grid',
          gridTemplateColumns: '1fr 1fr 1fr',
          gap: '1px',
          backgroundColor: 'var(--stroke-subtle)',
          borderRadius: '14px',
          overflow: 'hidden',
          marginBottom: '16px',
        }}>
          <TrustStat top="Active" bottom="since Jan 2026" />
          <TrustStat top="All picks" bottom="public" />
          <TrustStat top="0" bottom="deleted" />
        </div>
      </div>

      <div style={{ padding: '0 24px 16px' }}>
        <FeatureCard
          title="No edge, no pick"
          desc="We publish only when the model identifies sufficient value. Quiet days are intentional."
        />
      </div>

      <div style={{ padding: '0 24px 16px' }}>
        <FeatureCard
          title="36-feature ML model"
          desc="79.4% accuracy on 15,131 test games. Pace, ratings, injuries, line movement, schedule fatigue, and more."
        />
      </div>

      <div style={{ padding: '0 24px 16px' }}>
        <FeatureCard
          title="Transparent record"
          desc="Every pick and every pass logged permanently. Append-only tables. No hiding, no cherry-picking."
        />
      </div>

      {stats && (
        <div style={{ padding: '0 24px 16px' }}>
          <div style={{
            backgroundColor: 'var(--surface-1)',
            borderRadius: '16px',
            border: '1px solid var(--stroke-subtle)',
            padding: '20px',
          }}>
            <div style={{
              fontSize: '11px', fontWeight: 600, color: 'var(--text-tertiary)',
              textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: '16px',
            }}>Live Performance</div>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '12px' }}>
              <LandingStat label="Record" value={stats.record || '0-0'} />
              <LandingStat label="Win Rate" value={`${stats.win_rate || 0}%`} />
              <LandingStat
                label="P&L"
                value={`${stats.pnl >= 0 ? '+' : ''}${stats.pnl || 0}u`}
                color={stats.pnl >= 0 ? 'var(--green-profit)' : 'var(--red-loss)'}
              />
            </div>
          </div>
        </div>
      )}

      {spotsLeft !== null && spotsLeft > 0 && (
        <div style={{ padding: '0 24px 16px' }}>
          <div style={{
            backgroundColor: 'rgba(79, 134, 247, 0.06)',
            borderRadius: '16px',
            border: '1px solid rgba(79, 134, 247, 0.15)',
            padding: '20px',
            textAlign: 'center',
          }}>
            <div style={{
              fontFamily: 'var(--font-sans)',
              fontSize: '16px',
              fontWeight: 700,
              color: 'var(--text-primary)',
              marginBottom: '6px',
            }}>Founding member pricing</div>
            <p style={{
              fontSize: '14px',
              color: 'var(--text-secondary)',
              marginBottom: '4px',
            }}>
              First 500 lock in <span style={{ fontFamily: 'var(--font-mono)', color: 'var(--text-primary)', fontWeight: 600 }}>$99/year</span> for life.
            </p>
            <p style={{
              fontFamily: 'var(--font-mono)',
              fontSize: '12px',
              color: 'var(--blue-primary)',
              fontWeight: 600,
            }}>{spotsLeft} spots remaining</p>
          </div>
        </div>
      )}

      <div style={{ padding: '0 24px 40px' }}>
        <button
          onClick={() => { setAuthMode('login'); setShowAuth(true); }}
          style={{
            width: '100%',
            padding: '14px',
            backgroundColor: 'transparent',
            color: 'var(--text-secondary)',
            border: '1px solid var(--stroke-muted)',
            borderRadius: '14px',
            fontSize: '15px',
            fontWeight: 500,
            cursor: 'pointer',
            fontFamily: 'var(--font-sans)',
            marginBottom: '12px',
          }}
        >
          Sign in
        </button>
        <button
          onClick={onEnterApp}
          style={{
            width: '100%',
            padding: '12px',
            backgroundColor: 'transparent',
            color: 'var(--text-tertiary)',
            border: 'none',
            fontSize: '13px',
            cursor: 'pointer',
            fontFamily: 'var(--font-sans)',
          }}
        >
          Continue as guest
        </button>
      </div>

      {showAuth && <AuthModal onClose={() => setShowAuth(false)} initialMode={authMode} />}
    </div>
  );
}

function TrustStat({ top, bottom }) {
  return (
    <div style={{
      backgroundColor: 'var(--surface-1)',
      padding: '14px 8px',
      textAlign: 'center',
    }}>
      <div style={{
        fontFamily: 'var(--font-mono)',
        fontSize: '13px',
        fontWeight: 600,
        color: 'var(--text-primary)',
        marginBottom: '2px',
      }}>{top}</div>
      <div style={{
        fontSize: '11px',
        color: 'var(--text-tertiary)',
      }}>{bottom}</div>
    </div>
  );
}

function FeatureCard({ title, desc }) {
  return (
    <div style={{
      backgroundColor: 'var(--surface-1)',
      borderRadius: '16px',
      border: '1px solid var(--stroke-subtle)',
      padding: '20px',
    }}>
      <div style={{
        fontFamily: 'var(--font-sans)',
        fontSize: '16px',
        fontWeight: 700,
        color: 'var(--text-primary)',
        marginBottom: '6px',
      }}>{title}</div>
      <p style={{
        fontSize: '14px',
        color: 'var(--text-secondary)',
        lineHeight: '1.6',
      }}>{desc}</p>
    </div>
  );
}

function LandingStat({ label, value, color }) {
  return (
    <div style={{ textAlign: 'center' }}>
      <div style={{
        fontFamily: 'var(--font-mono)',
        fontSize: '20px',
        fontWeight: 700,
        color: color || 'var(--text-primary)',
      }}>{value}</div>
      <div style={{
        fontSize: '10px',
        color: 'var(--text-tertiary)',
        textTransform: 'uppercase',
        letterSpacing: '0.05em',
        marginTop: '4px',
      }}>{label}</div>
    </div>
  );
}
