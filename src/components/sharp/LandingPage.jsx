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
      <div style={{ padding: '40px 24px 0' }}>
        <div style={{ textAlign: 'center', marginBottom: '48px' }}>
          <img
            src="/logo-1024.png"
            alt="Sharp Picks"
            style={{
              width: '72px',
              height: '72px',
              borderRadius: '16px',
              margin: '0 auto 20px',
              display: 'block',
            }}
          />
          <h1 style={{
            fontFamily: 'var(--font-serif)',
            fontSize: '32px',
            fontWeight: 600,
            color: 'var(--text-primary)',
            letterSpacing: '-0.03em',
            lineHeight: '1.2',
            marginBottom: '12px',
          }}>
            Sharp Picks
          </h1>
          <p style={{
            fontSize: '16px',
            color: 'var(--text-secondary)',
            lineHeight: '1.6',
            maxWidth: '320px',
            margin: '0 auto',
          }}>
            One pick per day. Only when the model finds an edge. Most days, we say nothing. That's the point.
          </p>
        </div>

        {stats && (
          <div style={{
            backgroundColor: 'var(--surface-1)',
            borderRadius: '16px',
            border: '1px solid var(--stroke-subtle)',
            padding: '20px',
            marginBottom: '16px',
          }}>
            <div style={{
              fontSize: '11px',
              fontWeight: 600,
              color: 'var(--text-tertiary)',
              textTransform: 'uppercase',
              letterSpacing: '0.05em',
              marginBottom: '16px',
            }}>
              Live Performance
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '12px' }}>
              <LandingStat label="Record" value={stats.record || '0-0'} />
              <LandingStat label="Win Rate" value={`${stats.win_rate || 0}%`} />
              <LandingStat
                label="P&L"
                value={`${stats.pnl >= 0 ? '+' : ''}${stats.pnl || 0}u`}
                color={stats.pnl >= 0 ? 'var(--green-profit)' : 'var(--red-loss)'}
              />
            </div>
            <div style={{
              marginTop: '16px',
              display: 'flex',
              justifyContent: 'center',
              gap: '24px',
            }}>
              <div style={{
                fontFamily: 'var(--font-mono)',
                fontSize: '11px',
                color: 'var(--text-tertiary)',
              }}>
                {stats.selectivity || 0}% selectivity
              </div>
              <div style={{
                fontFamily: 'var(--font-mono)',
                fontSize: '11px',
                color: 'var(--text-tertiary)',
              }}>
                {stats.capital_preserved_days || 0} pass days
              </div>
            </div>
          </div>
        )}

        <div style={{
          backgroundColor: 'var(--surface-1)',
          borderRadius: '16px',
          border: '1px solid var(--stroke-subtle)',
          padding: '24px 20px',
          marginBottom: '16px',
        }}>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
            <Feature
              icon={<ShieldIcon />}
              title="Discipline over volume"
              desc="One pick per day maximum. The model only fires when edge exceeds 3.5%. Most days, silence is the product working."
            />
            <Feature
              icon={<ChartIcon />}
              title="36-feature ML model"
              desc="79.4% accuracy on 15,131 test games. Pace, ratings, injuries, line movement, schedule fatigue, and more."
            />
            <Feature
              icon={<LockIcon />}
              title="Transparent record"
              desc="Every pick and every pass logged permanently. Append-only tables. No hiding bad days, no cherry-picking."
            />
          </div>
        </div>

        <div style={{
          backgroundColor: 'var(--surface-1)',
          borderRadius: '16px',
          border: '1px solid var(--stroke-subtle)',
          padding: '24px 20px',
          marginBottom: '16px',
        }}>
          <div style={{
            fontSize: '11px',
            fontWeight: 600,
            color: 'var(--text-tertiary)',
            textTransform: 'uppercase',
            letterSpacing: '0.05em',
            marginBottom: '16px',
          }}>
            How it works
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
            <Step num="1" text="Model analyzes every NBA game daily" />
            <Step num="2" text="If edge exceeds 3.5%, one pick is published" />
            <Step num="3" text="If no edge found, a pass is logged" />
            <Step num="4" text="Results tracked with full transparency" />
          </div>
        </div>

        {spotsLeft !== null && spotsLeft > 0 && (
          <div style={{
            backgroundColor: 'rgba(99, 102, 241, 0.08)',
            borderRadius: '16px',
            border: '1px solid rgba(99, 102, 241, 0.2)',
            padding: '20px',
            marginBottom: '16px',
            textAlign: 'center',
          }}>
            <div style={{
              fontFamily: 'var(--font-serif)',
              fontSize: '18px',
              fontWeight: 600,
              color: 'var(--text-primary)',
              marginBottom: '8px',
            }}>
              Founding member pricing
            </div>
            <p style={{
              fontSize: '14px',
              color: 'var(--text-secondary)',
              marginBottom: '4px',
            }}>
              First 500 subscribers lock in <span style={{ fontFamily: 'var(--font-mono)', color: 'var(--text-primary)' }}>$99/year</span> for life.
            </p>
            <p style={{
              fontFamily: 'var(--font-mono)',
              fontSize: '12px',
              color: 'var(--blue-primary)',
            }}>
              {spotsLeft} spots remaining
            </p>
          </div>
        )}

        <div style={{ padding: '8px 0 40px' }}>
          <button
            onClick={() => { setAuthMode('register'); setShowAuth(true); }}
            style={{
              width: '100%',
              padding: '16px',
              backgroundColor: 'var(--blue-primary)',
              color: '#fff',
              border: 'none',
              borderRadius: '12px',
              fontSize: '16px',
              fontWeight: 600,
              cursor: 'pointer',
              fontFamily: 'var(--font-sans)',
              marginBottom: '12px',
            }}
          >
            Start 14-Day Free Trial
          </button>
          <button
            onClick={() => { setAuthMode('login'); setShowAuth(true); }}
            style={{
              width: '100%',
              padding: '16px',
              backgroundColor: 'transparent',
              color: 'var(--text-secondary)',
              border: '1px solid var(--stroke-muted)',
              borderRadius: '12px',
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
      </div>

      {showAuth && <AuthModal onClose={() => setShowAuth(false)} initialMode={authMode} />}
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
      }}>
        {value}
      </div>
      <div style={{
        fontSize: '10px',
        color: 'var(--text-tertiary)',
        textTransform: 'uppercase',
        letterSpacing: '0.05em',
        marginTop: '4px',
      }}>
        {label}
      </div>
    </div>
  );
}

function Feature({ icon, title, desc }) {
  return (
    <div style={{ display: 'flex', gap: '14px' }}>
      <div style={{
        width: '40px',
        height: '40px',
        borderRadius: '10px',
        backgroundColor: 'var(--surface-2)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        flexShrink: 0,
      }}>
        {icon}
      </div>
      <div>
        <div style={{
          fontSize: '15px',
          fontWeight: 600,
          color: 'var(--text-primary)',
          marginBottom: '4px',
        }}>
          {title}
        </div>
        <div style={{
          fontSize: '13px',
          color: 'var(--text-secondary)',
          lineHeight: '1.5',
        }}>
          {desc}
        </div>
      </div>
    </div>
  );
}

function Step({ num, text }) {
  return (
    <div style={{ display: 'flex', gap: '12px', alignItems: 'center' }}>
      <div style={{
        width: '28px',
        height: '28px',
        borderRadius: '8px',
        backgroundColor: 'var(--surface-2)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        fontFamily: 'var(--font-mono)',
        fontSize: '12px',
        fontWeight: 600,
        color: 'var(--blue-primary)',
        flexShrink: 0,
      }}>
        {num}
      </div>
      <div style={{
        fontSize: '14px',
        color: 'var(--text-secondary)',
      }}>
        {text}
      </div>
    </div>
  );
}

function ShieldIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="var(--blue-primary)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>
    </svg>
  );
}

function ChartIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="var(--blue-primary)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <line x1="18" y1="20" x2="18" y2="10"/>
      <line x1="12" y1="20" x2="12" y2="4"/>
      <line x1="6" y1="20" x2="6" y2="14"/>
    </svg>
  );
}

function LockIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="var(--blue-primary)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <rect x="3" y="11" width="18" height="11" rx="2" ry="2"/>
      <path d="M7 11V7a5 5 0 0 1 10 0v4"/>
    </svg>
  );
}
