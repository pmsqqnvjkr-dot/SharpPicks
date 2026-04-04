import { useState } from 'react';
import { useAuth } from '../../hooks/useAuth';

export default function ReferralScreen({ onBack }) {
  const { user } = useAuth();
  const [copied, setCopied] = useState(false);

  const referralCode = user?.referral_code || 'SHARP-XXXX';
  const referralLink = `${window.location.origin}/?ref=${referralCode}`;

  const copyCode = () => {
    navigator.clipboard.writeText(referralLink).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  };

  if (!user) {
    return (
      <div style={{ padding: '0' }}>
        <ScreenHeader onBack={onBack} />
        <div style={{ padding: '40px 20px', textAlign: 'center' }}>
          <p style={{ color: 'var(--text-secondary)', fontSize: '14px' }}>
            Sign in to access your referral code
          </p>
        </div>
      </div>
    );
  }

  return (
    <div style={{ padding: '0' }}>
      <ScreenHeader onBack={onBack} />

      <div style={{ padding: '0 20px' }}>
        <div style={{
          backgroundColor: 'var(--surface-1)', borderRadius: '16px',
          padding: '32px 24px', border: '1px solid var(--stroke-subtle)',
          textAlign: 'center', marginBottom: '12px',
        }}>
          <div style={{
            width: '56px', height: '56px', borderRadius: '14px',
            backgroundColor: 'var(--surface-2)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            margin: '0 auto 20px',
          }}>
            <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="var(--blue-primary)" strokeWidth="2">
              <path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/>
              <circle cx="9" cy="7" r="4"/>
              <line x1="19" y1="8" x2="19" y2="14"/>
              <line x1="22" y1="11" x2="16" y2="11"/>
            </svg>
          </div>

          <h2 style={{
            fontFamily: 'var(--font-serif)', fontSize: '22px',
            fontWeight: 600, color: 'var(--text-primary)', marginBottom: '8px',
          }}>Refer a friend</h2>
          <p style={{
            fontSize: '14px', color: 'var(--text-secondary)',
            lineHeight: '1.6', marginBottom: '24px', maxWidth: '300px',
            margin: '0 auto 24px',
          }}>
            Share your referral link. When someone subscribes, you both get a month of free access.
          </p>

          <div style={{
            backgroundColor: 'var(--surface-2)', borderRadius: '12px',
            padding: '16px', marginBottom: '16px',
          }}>
            <div style={{
              fontFamily: 'var(--font-mono)', fontSize: '18px',
              fontWeight: 700, color: 'var(--blue-primary)', marginBottom: '4px',
            }}>{referralCode}</div>
            <div style={{
              fontSize: '12px', color: 'var(--text-tertiary)',
              wordBreak: 'break-all',
            }}>{referralLink}</div>
          </div>

          <button onClick={copyCode} style={{
            width: '100%', padding: '14px',
            backgroundColor: copied ? 'var(--green-dark)' : '#5A9E72',
            color: '#fff', border: 'none', borderRadius: '10px',
            fontSize: '15px', fontWeight: 600, cursor: 'pointer',
            fontFamily: 'var(--font-sans)',
            transition: 'background-color 0.2s',
          }}>
            {copied ? 'Copied' : 'Copy Referral Link'}
          </button>
        </div>

        <div style={{
          backgroundColor: 'var(--surface-1)', borderRadius: '16px',
          padding: '20px', border: '1px solid var(--stroke-subtle)',
        }}>
          <h3 style={{
            fontSize: '12px', fontWeight: 600, color: 'var(--text-tertiary)',
            textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '16px',
          }}>How it works</h3>

          {[
            { step: '1', text: 'Share your unique referral link with friends' },
            { step: '2', text: 'They sign up and start a paid subscription' },
            { step: '3', text: 'You both receive a month of free access' },
          ].map(item => (
            <div key={item.step} style={{
              display: 'flex', alignItems: 'center', gap: '14px',
              padding: '10px 0',
              borderBottom: item.step !== '3' ? '1px solid var(--stroke-subtle)' : 'none',
            }}>
              <div style={{
                width: '28px', height: '28px', borderRadius: '8px',
                backgroundColor: 'var(--surface-2)',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                fontFamily: 'var(--font-mono)', fontSize: '13px',
                fontWeight: 600, color: 'var(--blue-primary)',
                flexShrink: 0,
              }}>{item.step}</div>
              <span style={{
                fontSize: '13px', color: 'var(--text-secondary)',
              }}>{item.text}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

function ScreenHeader({ onBack }) {
  return (
    <div style={{
      padding: '20px 20px 16px', display: 'flex', alignItems: 'center', gap: '12px',
    }}>
      <button onClick={onBack} style={{
        background: 'none', border: 'none', cursor: 'pointer',
        color: 'var(--text-secondary)', padding: '4px',
      }}>
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <polyline points="15 18 9 12 15 6"/>
        </svg>
      </button>
      <h1 style={{
        fontFamily: 'var(--font-serif)', fontSize: '22px',
        fontWeight: 600, color: 'var(--text-primary)',
      }}>Referral Program</h1>
    </div>
  );
}
