import { useState } from 'react';
import { useApi } from '../../hooks/useApi';
import AuthModal from './AuthModal';

export default function LandingPage() {
  const { data: stats } = useApi('/public/stats');
  const { data: founding } = useApi('/public/founding-count');
  const [showAuth, setShowAuth] = useState(false);
  const [authMode, setAuthMode] = useState('register');
  const [accountType, setAccountType] = useState(null);

  const spotsLeft = founding ? (founding.remaining != null ? founding.remaining : Math.max(0, 50 - (founding.current || 0))) : null;

  const ShieldLogo = ({ size = 24, opacity = 1 }) => (
    <img src="/images/crest.png" alt="" width={size} height={size} style={{ opacity, display: 'block', objectFit: 'contain' }} />
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
        padding: '12px 24px 12px',
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        background: 'linear-gradient(to bottom, #0E1A2B 0%, #0C1726 60%, #0A0D14 100%)',
        borderBottom: '1px solid rgba(255,255,255,0.06)',
      }}>
        <div style={{ display: 'flex', alignItems: 'center' }}>
          <div style={{ width: '24px', height: '24px', display: 'flex', alignItems: 'center', justifyContent: 'center', overflow: 'visible', marginRight: '14px', flexShrink: 0 }}><ShieldLogo size={22} /></div>
          <span style={{
            fontFamily: 'var(--font-sans)',
            fontSize: '13px', fontWeight: 600,
            color: 'rgba(255,255,255,0.9)',
            letterSpacing: '3.9px', textTransform: 'uppercase',
            lineHeight: 1,
          }}>SHARP<span style={{ opacity: 0.65, margin: '0 0.6em', fontWeight: 500 }}>||</span>PICKS</span>
        </div>
        <button
          onClick={() => { setAuthMode('login'); setShowAuth(true); }}
          style={{
            padding: '7px 16px',
            backgroundColor: 'transparent',
            color: 'var(--text-secondary)',
            border: '1px solid var(--stroke-muted)',
            borderRadius: '8px',
            fontSize: '13px', fontWeight: 500,
            cursor: 'pointer',
            fontFamily: 'var(--font-sans)',
          }}
        >
          Sign in
        </button>
      </div>

      <div style={{ padding: '20px 28px 0', textAlign: 'center' }}>
        <div style={{
          position: 'relative',
          marginBottom: '28px',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
        }}>
          <ShieldLogo size={80} opacity={0.08} />
        </div>

        <h1 style={{
          fontFamily: 'var(--font-serif)',
          fontSize: '32px', fontWeight: 700,
          lineHeight: '1.15',
          color: '#FFFFFF',
          marginBottom: '12px',
        }}>
          One Pick Beats Five
        </h1>

        <p style={{
          fontFamily: 'var(--font-sans)',
          fontSize: '16px', fontWeight: 400,
          color: 'rgba(255,255,255,0.7)',
          marginBottom: '32px',
        }}>
          Discipline is the product.
        </p>

        <button
          onClick={() => { setAuthMode('register'); setAccountType('trial'); setShowAuth(true); }}
          style={{
            width: '100%', maxWidth: '280px',
            height: '52px', borderRadius: '14px',
            border: 'none',
            backgroundColor: 'var(--blue-primary)',
            color: 'white',
            fontFamily: 'var(--font-sans)',
            fontSize: '16px', fontWeight: 700,
            cursor: 'pointer',
            marginBottom: '6px',
            boxShadow: '0 4px 12px rgba(0,0,0,0.3)',
          }}
        >
          Start 14-Day Trial
        </button>
        <p style={{
          fontFamily: 'var(--font-sans)',
          fontSize: '11px', fontWeight: 500,
          color: 'var(--text-tertiary)',
          marginBottom: '12px',
        }}>
          Card required. Cancel anytime.
        </p>
        <button
          onClick={() => { setAuthMode('register'); setAccountType('free'); setShowAuth(true); }}
          style={{
            width: '100%', maxWidth: '280px',
            height: '44px', borderRadius: '14px',
            border: '1px solid rgba(255,255,255,0.3)',
            backgroundColor: 'transparent',
            color: 'var(--text-secondary)',
            fontFamily: 'var(--font-sans)',
            fontSize: '14px', fontWeight: 500,
            cursor: 'pointer',
            marginBottom: '6px',
          }}
        >
          Create Free Account
        </button>
        <p style={{
          fontFamily: 'var(--font-sans)',
          fontSize: '11px', fontWeight: 500,
          color: 'var(--text-tertiary)',
          marginBottom: '28px',
        }}>
          No card needed · Upgrade anytime
        </p>

        <div style={{
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          gap: '16px', marginBottom: '16px',
          backgroundColor: 'var(--surface-1)',
          border: '1px solid var(--stroke-subtle)',
          borderRadius: '12px',
          padding: '14px 16px',
        }}>
          <span style={{ fontFamily: 'var(--font-mono)', fontSize: '10px', fontWeight: 500, letterSpacing: '0.5px', color: 'var(--text-tertiary)' }}>Active since Jan 2026</span>
          <ProofDot />
          <span style={{ fontFamily: 'var(--font-mono)', fontSize: '10px', fontWeight: 500, letterSpacing: '0.5px', color: 'var(--text-tertiary)' }}>All picks public</span>
          <ProofDot />
          <span style={{ fontFamily: 'var(--font-mono)', fontSize: '10px', fontWeight: 500, letterSpacing: '0.5px', color: 'var(--text-tertiary)' }}>0 deleted</span>
        </div>
      </div>

      <div style={{ padding: '0 28px', display: 'flex', flexDirection: 'column', gap: '12px' }}>
        <ValueProp
          title="No edge, no pick"
          desc="We publish only when the model identifies sufficient value. Quiet days are intentional."
        />
        <ValueProp
          title="Process over outcomes"
          desc={`All picks tracked publicly. No deletes. No hindsight editing.${stats ? ` ${stats.total_picks} picks · ${stats.total_passes} passes to date` : ''}`}
        />
        <ValueProp
          title="Selectivity beats volume"
          desc={`Most bettors lose by betting too much.${stats ? ` Our ${stats.selectivity}% selectivity rate is the edge.` : ' Selectivity is the edge.'}`}
        />
      </div>

      <div style={{ padding: '16px 28px 0' }}>
        <div style={{
          backgroundColor: 'var(--surface-1)',
          borderRadius: '16px',
          border: '1px solid var(--stroke-subtle)',
          padding: '20px',
        }}>
          <div style={{
            fontSize: '11px', fontWeight: 600, color: 'var(--text-tertiary)',
            textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: '16px',
            textAlign: 'center',
          }}>What you get</div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
            <div>
              <div style={{
                fontSize: '13px', fontWeight: 700, color: 'var(--text-secondary)',
                marginBottom: '12px', fontFamily: 'var(--font-sans)',
              }}>FREE</div>
              <TierItem included text="Model activity feed" />
              <TierItem included text="Public record access" />
              <TierItem included text="Pass-day summaries" />
              <TierItem text="Pick details locked" />
              <TierItem text="No bet tracking" />
            </div>
            <div>
              <div style={{
                fontSize: '13px', fontWeight: 700, color: 'var(--blue-primary)',
                marginBottom: '12px', fontFamily: 'var(--font-sans)',
              }}>PRO</div>
              <TierItem included text="Full pick details" />
              <TierItem included text="Side, line, edge %" />
              <TierItem included text="Position sizing" />
              <TierItem included text="Bet tracking" />
              <TierItem included text="Performance dashboard" />
              <TierItem included text="14-day free trial" />
            </div>
          </div>
        </div>
      </div>

      {stats && (
        <div style={{ padding: '16px 28px 0' }}>
          <div style={{
            backgroundColor: 'var(--surface-1)',
            borderRadius: '16px',
            border: '1px solid var(--stroke-subtle)',
            padding: '20px',
          }}>
            <div style={{
              fontSize: '11px', fontWeight: 600, color: 'var(--text-tertiary)',
              textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: '16px',
            }}>Transparency</div>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '12px' }}>
              <LandingStat label="Selectivity" value={`${stats.selectivity || 0}%`} />
              <LandingStat label="Picks / Passes" value={`${stats.total_picks || 0} / ${stats.total_passes || 0}`} />
              <LandingStat label="Deleted" value="0" />
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
              First 50 lock in <span style={{ fontFamily: 'var(--font-mono)', color: 'var(--text-primary)', fontWeight: 600 }}>$99/year</span> for life.
            </p>
            <p style={{
              fontFamily: 'var(--font-mono)', fontSize: '12px',
              color: 'var(--blue-primary)', fontWeight: 600,
            }}>{spotsLeft} spots remaining</p>
          </div>
        </div>
      )}

      <div style={{ padding: '16px 28px 40px' }}>
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

      <div style={{
        textAlign: 'center', padding: '24px 20px 32px',
        borderTop: '1px solid var(--stroke-subtle)',
        marginTop: '32px',
      }}>
        <p style={{ fontSize: '11px', color: 'var(--text-tertiary)', margin: '0 0 10px', lineHeight: '1.6' }}>
          SharpPicks provides sports analytics and model-based insights only. Not financial advice. Not a sportsbook.
        </p>
        <div style={{ display: 'flex', justifyContent: 'center', gap: '16px', marginBottom: '10px' }}>
          <a href="/privacy" style={{ fontSize: '11px', color: 'var(--text-tertiary)', textDecoration: 'none' }}>Privacy</a>
          <a href="/terms" style={{ fontSize: '11px', color: 'var(--text-tertiary)', textDecoration: 'none' }}>Terms</a>
          <a href="/disclaimer" style={{ fontSize: '11px', color: 'var(--text-tertiary)', textDecoration: 'none' }}>Disclaimer</a>
        </div>
        <a href="mailto:support@sharppicks.ai" style={{
          fontSize: '12px', color: 'var(--text-secondary)', textDecoration: 'none',
        }}>support@sharppicks.ai</a>
      </div>

      {showAuth && <AuthModal onClose={() => setShowAuth(false)} initialMode={authMode} initialAccountType={accountType} />}
    </div>
  );
}

function ProofDot() {
  return <div style={{ width: '3px', height: '3px', borderRadius: '50%', background: 'var(--text-tertiary)', opacity: 0.4 }} />;
}

function ValueProp({ title, desc }) {
  return (
    <div style={{
      backgroundColor: 'var(--surface-1)',
      border: '1px solid var(--stroke-subtle)',
      borderRadius: '16px',
      padding: '20px',
    }}>
      <h3 style={{
        fontFamily: 'var(--font-serif)',
        fontSize: '15px', fontWeight: 600,
        color: 'var(--text-primary)',
        marginBottom: '6px',
      }}>{title}</h3>
      <p style={{
        fontSize: '13px',
        color: 'var(--text-secondary)',
        lineHeight: '1.55',
      }}>{desc}</p>
    </div>
  );
}

function TierItem({ included, text }) {
  return (
    <div style={{
      display: 'flex', alignItems: 'center', gap: '8px',
      marginBottom: '8px',
    }}>
      <span style={{
        fontSize: '13px',
        color: included ? 'var(--green-profit)' : 'var(--text-tertiary)',
        fontFamily: 'var(--font-mono)',
        width: '16px', textAlign: 'center',
        flexShrink: 0,
      }}>
        {included ? '\u2713' : '\u2717'}
      </span>
      <span style={{
        fontSize: '12px',
        color: included ? 'var(--text-secondary)' : 'var(--text-tertiary)',
        fontFamily: 'var(--font-sans)',
        lineHeight: '1.4',
      }}>
        {text}
      </span>
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
