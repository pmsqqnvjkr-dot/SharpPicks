import { useState } from 'react';
import { useApi } from '../../hooks/useApi';
import AuthModal from './AuthModal';

export default function LandingPage() {
  const { data: stats } = useApi('/public/stats');
  const { data: founding } = useApi('/public/founding-count');
  const [showAuth, setShowAuth] = useState(false);
  const [authMode, setAuthMode] = useState('register');

  const spotsLeft = founding ? (founding.remaining != null ? founding.remaining : Math.max(0, 500 - (founding.current || 0))) : null;

  const ShieldLogo = ({ size = 24 }) => (
    <svg viewBox="0 0 40 40" width={size} height={size} fill="none">
      <path d="M20 4L6 10v10c0 9.2 6 17.4 14 20 8-2.6 14-10.8 14-20V10L20 4z" stroke="white" strokeWidth="1.8" fill="none"/>
      <rect x="12" y="24" width="3" height="6" rx="1" fill="rgba(255,255,255,0.3)"/>
      <rect x="17" y="20" width="3" height="10" rx="1" fill="rgba(255,255,255,0.4)"/>
      <rect x="22" y="22" width="3" height="8" rx="1" fill="rgba(255,255,255,0.35)"/>
      <path d="M11 22L17 16L22 19L30 11" stroke="white" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"/>
      <path d="M26 11h4v4" stroke="white" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"/>
    </svg>
  );

  return (
    <div style={{
      minHeight: '100vh',
      backgroundColor: 'var(--bg-primary)',
      maxWidth: '480px',
      margin: '0 auto',
      overflow: 'auto',
    }}>
      <div style={{
        padding: '8px 24px 16px',
        display: 'flex', alignItems: 'center', gap: '10px',
      }}>
        <ShieldLogo size={24} />
        <span style={{
          fontFamily: 'var(--font-sans)',
          fontSize: '13px', fontWeight: 700,
          color: 'var(--text-primary)',
          letterSpacing: '2px', textTransform: 'uppercase',
        }}>Sharp Picks</span>
      </div>

      <div style={{ padding: '40px 28px 0', textAlign: 'center' }}>
        <h1 style={{
          fontFamily: 'var(--font-serif)',
          fontSize: '28px', fontWeight: 700,
          lineHeight: '1.3',
          color: 'var(--text-primary)',
          marginBottom: '16px',
        }}>
          NBA Model Picks — One Per Day
        </h1>

        <p style={{
          fontFamily: 'var(--font-sans)',
          fontSize: '15px', fontWeight: 400,
          color: 'var(--text-secondary)',
          lineHeight: '1.6',
          marginBottom: '8px',
          maxWidth: '340px',
          marginLeft: 'auto',
          marginRight: 'auto',
        }}>
          We publish only when the model identifies real betting value.
        </p>
        <p style={{
          fontFamily: 'var(--font-sans)',
          fontSize: '14px', fontWeight: 400,
          color: 'var(--text-tertiary)',
          marginBottom: '36px',
        }}>
          No volume. No hype. No forced action.
        </p>

        <button
          onClick={() => { setAuthMode('register'); setShowAuth(true); }}
          style={{
            width: '100%', maxWidth: '280px',
            height: '52px', borderRadius: '14px',
            border: 'none',
            background: 'linear-gradient(135deg, var(--blue-primary), var(--blue-deep))',
            color: 'white',
            fontFamily: 'var(--font-sans)',
            fontSize: '16px', fontWeight: 700,
            cursor: 'pointer',
            marginBottom: '12px',
          }}
        >
          Start 14-Day Trial
        </button>
        <p style={{
          fontFamily: 'var(--font-sans)',
          fontSize: '12px', fontWeight: 500,
          color: 'var(--text-tertiary)',
          marginBottom: '0',
        }}>
          Card required. Cancel anytime.
        </p>
      </div>

      <div style={{ padding: '48px 28px 0' }}>
        <div style={{
          textAlign: 'center',
          marginBottom: '20px',
        }}>
          <div style={{
            width: '40px', height: '1px',
            backgroundColor: 'var(--stroke-subtle)',
            margin: '0 auto 24px',
          }} />
          <h2 style={{
            fontFamily: 'var(--font-serif)',
            fontSize: '20px', fontWeight: 600,
            color: 'var(--text-primary)',
            marginBottom: '24px',
          }}>How It Works</h2>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          <StepCard number="1" text="Model scans full slate" />
          <StepCard number="2" text="Applies edge threshold" />
          <StepCard number="3" text="Publishes one qualified pick (or none)" />
        </div>
      </div>

      <div style={{ padding: '40px 28px 0', textAlign: 'center' }}>
        <div style={{
          width: '40px', height: '1px',
          backgroundColor: 'var(--stroke-subtle)',
          margin: '0 auto 28px',
        }} />
        <p style={{
          fontFamily: 'var(--font-serif)',
          fontSize: '16px',
          fontStyle: 'italic',
          color: 'var(--text-secondary)',
          lineHeight: '1.6',
          marginBottom: '4px',
        }}>
          You don't need more hype.
        </p>
        <p style={{
          fontFamily: 'var(--font-serif)',
          fontSize: '16px',
          fontStyle: 'italic',
          color: 'var(--text-primary)',
          fontWeight: 600,
          lineHeight: '1.6',
          marginBottom: '0',
        }}>
          You need clarity + confidence.
        </p>
      </div>

      {stats && (
        <div style={{ padding: '40px 28px 0' }}>
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
        <div style={{ padding: '16px 28px 0' }}>
          <div style={{
            backgroundColor: 'rgba(79, 134, 247, 0.06)',
            borderRadius: '16px',
            border: '1px solid rgba(79, 134, 247, 0.15)',
            padding: '20px',
            textAlign: 'center',
          }}>
            <div style={{
              fontFamily: 'var(--font-sans)',
              fontSize: '16px', fontWeight: 700,
              color: 'var(--text-primary)', marginBottom: '6px',
            }}>Founding member pricing</div>
            <p style={{ fontSize: '14px', color: 'var(--text-secondary)', marginBottom: '4px' }}>
              First 500 lock in <span style={{ fontFamily: 'var(--font-mono)', color: 'var(--text-primary)', fontWeight: 600 }}>$99/year</span> for life.
            </p>
            <p style={{
              fontFamily: 'var(--font-mono)', fontSize: '12px',
              color: 'var(--blue-primary)', fontWeight: 600,
            }}>{spotsLeft} spots remaining</p>
          </div>
        </div>
      )}

      <div style={{ padding: '24px 28px 40px' }}>
        <button
          onClick={() => { setAuthMode('login'); setShowAuth(true); }}
          style={{
            width: '100%', padding: '14px',
            backgroundColor: 'transparent',
            color: 'var(--text-secondary)',
            border: '1px solid var(--stroke-muted)',
            borderRadius: '14px',
            fontSize: '15px', fontWeight: 500,
            cursor: 'pointer',
            fontFamily: 'var(--font-sans)',
          }}
        >
          Sign in
        </button>
      </div>

      {showAuth && <AuthModal onClose={() => setShowAuth(false)} initialMode={authMode} />}
    </div>
  );
}

function StepCard({ number, text }) {
  return (
    <div style={{
      backgroundColor: 'var(--surface-1)',
      border: '1px solid var(--stroke-subtle)',
      borderRadius: '14px',
      padding: '18px 20px',
      display: 'flex',
      alignItems: 'center',
      gap: '16px',
    }}>
      <div style={{
        width: '32px', height: '32px',
        borderRadius: '50%',
        backgroundColor: 'rgba(79, 134, 247, 0.1)',
        border: '1px solid rgba(79, 134, 247, 0.2)',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        flexShrink: 0,
      }}>
        <span style={{
          fontFamily: 'var(--font-mono)',
          fontSize: '13px', fontWeight: 700,
          color: 'var(--blue-primary)',
        }}>{number}</span>
      </div>
      <span style={{
        fontFamily: 'var(--font-sans)',
        fontSize: '15px', fontWeight: 500,
        color: 'var(--text-primary)',
      }}>{text}</span>
    </div>
  );
}

function LandingStat({ label, value, color }) {
  return (
    <div style={{ textAlign: 'center' }}>
      <div style={{
        fontFamily: 'var(--font-mono)',
        fontSize: '20px', fontWeight: 700,
        color: color || 'var(--text-primary)',
      }}>{value}</div>
      <div style={{
        fontSize: '10px', color: 'var(--text-tertiary)',
        textTransform: 'uppercase', letterSpacing: '0.05em',
        marginTop: '4px',
      }}>{label}</div>
    </div>
  );
}
