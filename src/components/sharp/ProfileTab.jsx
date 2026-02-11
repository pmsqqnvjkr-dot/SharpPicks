import { useState } from 'react';
import { useAuth } from '../../hooks/useAuth';
import { useApi } from '../../hooks/useApi';
import AuthModal from './AuthModal';

export default function ProfileTab() {
  const { user, logout } = useAuth();
  const { data: foundingData } = useApi('/public/founding-count');
  const [showAuth, setShowAuth] = useState(false);

  if (!user) {
    return (
      <div style={{ padding: '0' }}>
        <div style={{ padding: '20px 20px 16px' }}>
          <h1 style={{
            fontFamily: 'var(--font-serif)',
            fontSize: '22px',
            fontWeight: 600,
            color: 'var(--text-primary)',
          }}>
            Profile
          </h1>
        </div>

        <div style={{ padding: '0 20px' }}>
          <div style={{
            backgroundColor: 'var(--surface-1)',
            borderRadius: '16px',
            padding: '32px 24px',
            border: '1px solid var(--stroke-subtle)',
            textAlign: 'center',
          }}>
            <div style={{
              width: '56px',
              height: '56px',
              borderRadius: '14px',
              backgroundColor: 'var(--surface-2)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              margin: '0 auto 20px',
            }}>
              <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="var(--text-tertiary)" strokeWidth="2">
                <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/>
                <circle cx="12" cy="7" r="4"/>
              </svg>
            </div>

            <h2 style={{
              fontFamily: 'var(--font-serif)',
              fontSize: '20px',
              fontWeight: 600,
              color: 'var(--text-primary)',
              marginBottom: '8px',
            }}>
              Sign in to get started
            </h2>
            <p style={{
              fontSize: '14px',
              color: 'var(--text-secondary)',
              marginBottom: '24px',
              lineHeight: '1.6',
            }}>
              Create an account to track your bets, manage your subscription, and access all features.
            </p>
            <button
              onClick={() => setShowAuth(true)}
              style={{
                padding: '14px 32px',
                backgroundColor: 'var(--blue-primary)',
                color: '#fff',
                border: 'none',
                borderRadius: '10px',
                fontSize: '15px',
                fontWeight: 600,
                cursor: 'pointer',
                fontFamily: 'var(--font-sans)',
              }}
            >
              Sign In or Create Account
            </button>
          </div>

          <PricingSection foundingData={foundingData} onAction={() => setShowAuth(true)} />
        </div>

        {showAuth && <AuthModal onClose={() => setShowAuth(false)} />}
      </div>
    );
  }

  return (
    <div style={{ padding: '0' }}>
      <div style={{ padding: '20px 20px 16px' }}>
        <h1 style={{
          fontFamily: 'var(--font-serif)',
          fontSize: '22px',
          fontWeight: 600,
          color: 'var(--text-primary)',
        }}>
          Profile
        </h1>
      </div>

      <div style={{ padding: '0 20px' }}>
        <div style={{
          backgroundColor: 'var(--surface-1)',
          borderRadius: '16px',
          padding: '20px',
          border: '1px solid var(--stroke-subtle)',
          marginBottom: '12px',
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
            <div style={{
              width: '48px',
              height: '48px',
              borderRadius: '12px',
              backgroundColor: 'var(--blue-deep)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: '#fff',
              fontWeight: 700,
              fontSize: '18px',
              fontFamily: 'var(--font-sans)',
            }}>
              {(user.email || '?')[0].toUpperCase()}
            </div>
            <div>
              <div style={{
                fontSize: '16px',
                fontWeight: 600,
                color: 'var(--text-primary)',
              }}>
                {user.display_name || user.username || user.email.split('@')[0]}
              </div>
              <div style={{
                fontSize: '13px',
                color: 'var(--text-tertiary)',
              }}>
                {user.email}
              </div>
            </div>
          </div>

          {user.founding_member && (
            <div style={{
              marginTop: '12px',
              padding: '8px 12px',
              backgroundColor: 'rgba(245, 158, 11, 0.1)',
              borderRadius: '8px',
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
            }}>
              <span style={{ fontSize: '14px' }}>&#9733;</span>
              <span style={{
                fontFamily: 'var(--font-mono)',
                fontSize: '12px',
                color: 'var(--gold-pro)',
                fontWeight: 600,
              }}>
                Founding Member #{user.founding_number || ''}
              </span>
            </div>
          )}
        </div>

        <SettingsSection user={user} />

        <PricingSection foundingData={foundingData} onAction={() => {}} />

        <div style={{ marginTop: '12px' }}>
          <button
            onClick={logout}
            style={{
              width: '100%',
              padding: '14px',
              backgroundColor: 'transparent',
              border: '1px solid var(--stroke-muted)',
              borderRadius: '12px',
              color: 'var(--text-secondary)',
              fontSize: '14px',
              fontWeight: 500,
              cursor: 'pointer',
              fontFamily: 'var(--font-sans)',
            }}
          >
            Sign Out
          </button>
        </div>
      </div>
    </div>
  );
}

function SettingsSection({ user }) {
  const menuItems = [
    { label: 'How It Works', subtitle: 'Our model and methodology' },
    { label: 'Pick History', subtitle: 'All published picks' },
    { label: 'Notifications', subtitle: 'Alert preferences' },
    { label: 'Referral Program', subtitle: 'Earn 14 days free' },
  ];

  return (
    <div style={{
      backgroundColor: 'var(--surface-1)',
      borderRadius: '16px',
      overflow: 'hidden',
      border: '1px solid var(--stroke-subtle)',
      marginBottom: '12px',
    }}>
      {menuItems.map((item, i) => (
        <button
          key={item.label}
          style={{
            width: '100%',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            padding: '16px 20px',
            background: 'none',
            border: 'none',
            borderBottom: i < menuItems.length - 1 ? '1px solid var(--stroke-subtle)' : 'none',
            cursor: 'pointer',
            textAlign: 'left',
          }}
        >
          <div>
            <div style={{
              fontSize: '14px',
              fontWeight: 500,
              color: 'var(--text-primary)',
            }}>
              {item.label}
            </div>
            <div style={{
              fontSize: '12px',
              color: 'var(--text-tertiary)',
              marginTop: '2px',
            }}>
              {item.subtitle}
            </div>
          </div>
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="var(--text-tertiary)" strokeWidth="2">
            <polyline points="9 18 15 12 9 6"/>
          </svg>
        </button>
      ))}
    </div>
  );
}

function PricingSection({ foundingData, onAction }) {
  const plans = [
    {
      name: 'Free',
      price: '$0',
      period: '',
      features: ['See if a pick exists today', 'Public record access'],
      cta: null,
    },
    {
      name: 'Monthly',
      price: '$29',
      period: '/mo',
      features: ['Full pick details', 'Real-time alerts', 'Pick history', 'Bet tracking'],
      cta: 'Start 14-Day Trial',
    },
    {
      name: 'Annual',
      price: foundingData?.open ? '$99' : '$149',
      period: '/yr',
      features: [
        'Everything in Monthly',
        foundingData?.open ? `Founding rate (${foundingData?.remaining || 0} of 500 left)` : 'Standard annual rate',
        'Priority support',
        'Founding member badge',
      ],
      cta: foundingData?.open ? 'Claim Founding Rate' : 'Start Annual',
      highlight: true,
    },
  ];

  return (
    <div style={{
      backgroundColor: 'var(--surface-1)',
      borderRadius: '16px',
      padding: '20px',
      border: '1px solid var(--stroke-subtle)',
      marginTop: '12px',
    }}>
      <h3 style={{
        fontSize: '12px',
        fontWeight: 600,
        color: 'var(--text-tertiary)',
        textTransform: 'uppercase',
        letterSpacing: '0.05em',
        marginBottom: '16px',
      }}>
        Plans
      </h3>

      {foundingData?.open && (
        <div style={{
          backgroundColor: 'rgba(245, 158, 11, 0.08)',
          border: '1px solid rgba(245, 158, 11, 0.2)',
          borderRadius: '10px',
          padding: '12px 16px',
          marginBottom: '16px',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
        }}>
          <span style={{
            fontSize: '13px',
            color: 'var(--gold-pro)',
            fontWeight: 500,
          }}>
            Founding member spots
          </span>
          <span style={{
            fontFamily: 'var(--font-mono)',
            fontSize: '14px',
            color: 'var(--gold-pro)',
            fontWeight: 700,
          }}>
            {foundingData.remaining}/500
          </span>
        </div>
      )}

      <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
        {plans.map(plan => (
          <div
            key={plan.name}
            style={{
              padding: '16px',
              borderRadius: '12px',
              backgroundColor: 'var(--surface-2)',
              border: plan.highlight ? '1px solid var(--blue-primary)' : '1px solid var(--stroke-subtle)',
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', marginBottom: '8px' }}>
              <span style={{ fontSize: '15px', fontWeight: 600, color: 'var(--text-primary)' }}>
                {plan.name}
              </span>
              <span>
                <span style={{
                  fontFamily: 'var(--font-mono)',
                  fontSize: '18px',
                  fontWeight: 700,
                  color: 'var(--text-primary)',
                }}>
                  {plan.price}
                </span>
                <span style={{ fontSize: '12px', color: 'var(--text-tertiary)' }}>
                  {plan.period}
                </span>
              </span>
            </div>
            <ul style={{ listStyle: 'none', padding: 0, margin: '0 0 12px 0' }}>
              {plan.features.map(f => (
                <li key={f} style={{
                  fontSize: '12px',
                  color: 'var(--text-secondary)',
                  padding: '3px 0',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '6px',
                }}>
                  <span style={{ color: 'var(--green-profit)', fontSize: '10px' }}>&#10003;</span>
                  {f}
                </li>
              ))}
            </ul>
            {plan.cta && (
              <button
                onClick={onAction}
                style={{
                  width: '100%',
                  padding: '10px',
                  backgroundColor: plan.highlight ? 'var(--blue-primary)' : 'transparent',
                  border: plan.highlight ? 'none' : '1px solid var(--stroke-muted)',
                  borderRadius: '8px',
                  color: plan.highlight ? '#fff' : 'var(--text-primary)',
                  fontSize: '13px',
                  fontWeight: 600,
                  cursor: 'pointer',
                  fontFamily: 'var(--font-sans)',
                }}
              >
                {plan.cta}
              </button>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
