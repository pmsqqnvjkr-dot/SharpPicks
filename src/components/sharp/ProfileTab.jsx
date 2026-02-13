import { useState, useEffect } from 'react';
import { useAuth } from '../../hooks/useAuth';
import { useApi, apiPost } from '../../hooks/useApi';
import AuthModal from './AuthModal';
import HowItWorksScreen from './HowItWorksScreen';
import BetTrackingScreen from './BetTrackingScreen';
import ReferralScreen from './ReferralScreen';
import NotificationsScreen from './NotificationsScreen';
import UpgradeScreen from './UpgradeScreen';
import CancelScreen from './CancelScreen';
import AnnualConversion from './AnnualConversion';
import WeeklySummary from './WeeklySummary';
import ResolutionScreen from './ResolutionScreen';

export default function ProfileTab({ initialScreen, onScreenChange, pickToTrack, onPickTracked, screenData }) {
  const { user, logout } = useAuth();
  const { data: foundingData } = useApi('/public/founding-count');
  const [showAuth, setShowAuth] = useState(false);
  const [screen, setScreen] = useState(initialScreen || null);
  const [checkoutLoading, setCheckoutLoading] = useState(false);
  const [localScreenData, setLocalScreenData] = useState(null);

  const activeScreenData = localScreenData || screenData;
  const isPro = user && (user.is_premium || user.subscription_status === 'active' || user.subscription_status === 'trial' || user.founding_member);

  useEffect(() => {
    if (initialScreen) setScreen(initialScreen);
  }, [initialScreen]);

  const navigate = (s) => {
    setScreen(s);
    if (onScreenChange) onScreenChange(s);
  };

  if (screen === 'trial') return <TrialSignup onBack={() => navigate(null)} />;
  if (screen === 'how') return <HowItWorksScreen onBack={() => navigate(null)} />;
  if (screen === 'bets') return <BetTrackingScreen onBack={() => { navigate(null); if (onPickTracked) onPickTracked(); }} pickToTrack={pickToTrack} />;
  if (screen === 'referral') return <ReferralScreen onBack={() => navigate(null)} />;
  if (screen === 'notifications') return <NotificationsScreen onBack={() => navigate(null)} />;
  if (screen === 'upgrade') return <UpgradeScreen onBack={() => navigate(null)} />;
  if (screen === 'cancel') return <CancelScreen onBack={() => navigate(null)} user={user} />;
  if (screen === 'annual') return <AnnualConversion onBack={() => navigate(null)} user={user} />;
  if (screen === 'weekly') return <WeeklySummary onBack={() => navigate(null)} stats={null} weekData={activeScreenData} />;
  if (screen === 'resolution') return <ResolutionScreen onBack={() => navigate(null)} pick={activeScreenData} />;

  const handleSubscribe = async (plan) => {
    if (plan === 'trial') {
      setScreen('trial');
      return;
    }
    if (!user) {
      setShowAuth(true);
      return;
    }
    if (plan === 'founding') {
      window.open('https://buy.stripe.com/aFa6oI5lWeby1xtd8md7q02', '_blank');
      return;
    }
    if (plan === 'annual') {
      window.open('https://buy.stripe.com/cNieVe8y81oM8ZV0lAd7q05', '_blank');
      return;
    }
    window.open('https://buy.stripe.com/14A28s4hS9Vigsngkyd7q04', '_blank');
  };

  if (!user) {
    return (
      <div style={{ padding: '0' }}>
        <div style={{ padding: '20px 20px 16px' }}>
          <div style={{
            fontFamily: 'var(--font-mono)',
            fontSize: '10px', fontWeight: 600,
            letterSpacing: '2px', textTransform: 'uppercase',
            color: 'var(--text-tertiary)',
          }}>Account</div>
        </div>

        <div style={{ padding: '0 20px' }}>
          <div style={{
            backgroundColor: 'var(--surface-1)', borderRadius: '16px',
            padding: '32px 24px', border: '1px solid var(--stroke-subtle)',
            textAlign: 'center',
          }}>
            <div style={{
              width: '56px', height: '56px', borderRadius: '14px',
              backgroundColor: 'var(--surface-2)',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              margin: '0 auto 20px',
            }}>
              <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="var(--text-tertiary)" strokeWidth="2">
                <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/>
                <circle cx="12" cy="7" r="4"/>
              </svg>
            </div>
            <h2 style={{
              fontFamily: 'var(--font-sans)', fontSize: '18px',
              fontWeight: 600, color: 'var(--text-primary)', marginBottom: '8px',
            }}>Sign in to get started</h2>
            <p style={{
              fontSize: '14px', color: 'var(--text-secondary)',
              marginBottom: '24px', lineHeight: '1.6',
            }}>
              Create an account to track your bets, manage your subscription, and access all features.
            </p>
            <button onClick={() => setShowAuth(true)} style={{
              padding: '14px 32px', backgroundColor: 'var(--blue-primary)',
              color: '#fff', border: 'none', borderRadius: '10px',
              fontSize: '15px', fontWeight: 600, cursor: 'pointer',
              fontFamily: 'var(--font-sans)',
            }}>Sign In or Create Account</button>
          </div>

          <SettingsSection user={null} onNavigate={navigate} />
          <PricingSection foundingData={foundingData} onSubscribe={handleSubscribe} loading={checkoutLoading} />
          <LegalSection />
        </div>

        {showAuth && <AuthModal onClose={() => setShowAuth(false)} />}
      </div>
    );
  }

  return (
    <div style={{ padding: '0' }}>
      <div style={{ padding: '20px 20px 16px' }}>
        <div style={{
          fontFamily: 'var(--font-mono)',
          fontSize: '10px', fontWeight: 600,
          letterSpacing: '2px', textTransform: 'uppercase',
          color: 'var(--text-tertiary)',
        }}>Account</div>
      </div>

      <div style={{ padding: '0 20px' }}>
        <div style={{
          backgroundColor: 'var(--surface-1)', borderRadius: '16px',
          padding: '20px', border: '1px solid var(--stroke-subtle)',
          marginBottom: '12px',
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
            <div style={{
              width: '48px', height: '48px', borderRadius: '12px',
              backgroundColor: 'var(--blue-deep)',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              color: '#fff', fontWeight: 700, fontSize: '18px',
              fontFamily: 'var(--font-sans)',
            }}>
              {(user.email || '?')[0].toUpperCase()}
            </div>
            <div>
              <div style={{
                fontSize: '16px', fontWeight: 600, color: 'var(--text-primary)',
                display: 'flex', alignItems: 'center', gap: '6px',
              }}>
                {user.display_name || user.username || user.email.split('@')[0]}
                {isPro && (
                  <svg width="16" height="16" viewBox="0 0 32 32" fill="none" style={{ flexShrink: 0 }}>
                    <path d="M16 4L6 8v8c0 5.5 4.3 10.7 10 12 5.7-1.3 10-6.5 10-12V8l-10-4z"
                      fill={user.founding_member ? 'rgba(245,158,11,0.15)' : 'rgba(79,134,247,0.15)'}
                      stroke={user.founding_member ? 'var(--gold-pro)' : 'var(--blue-primary)'}
                      strokeWidth="1.5"/>
                    <path d="M11 16l3 3 7-7"
                      stroke={user.founding_member ? 'var(--gold-pro)' : 'var(--blue-primary)'}
                      strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                  </svg>
                )}
              </div>
              <div style={{
                fontSize: '13px', color: 'var(--text-tertiary)',
              }}>{user.email}</div>
            </div>
          </div>

          {user.founding_member && (
            <div style={{
              marginTop: '12px', padding: '8px 12px',
              backgroundColor: 'rgba(245, 158, 11, 0.1)', borderRadius: '8px',
              display: 'flex', alignItems: 'center', gap: '8px',
            }}>
              <span style={{ fontSize: '14px' }}>&#9733;</span>
              <span style={{
                fontFamily: 'var(--font-mono)', fontSize: '12px',
                color: 'var(--gold-pro)', fontWeight: 600,
              }}>Founding Member #{user.founding_number || ''}</span>
            </div>
          )}

          {user.subscription_status && user.subscription_status !== 'free' && (
            <div style={{
              marginTop: '12px', padding: '8px 12px',
              backgroundColor: 'rgba(79, 134, 247, 0.1)', borderRadius: '8px',
              display: 'flex', justifyContent: 'space-between', alignItems: 'center',
            }}>
              <span style={{
                fontSize: '12px', color: 'var(--blue-primary)', fontWeight: 600,
                textTransform: 'capitalize',
              }}>
                {user.subscription_status === 'trial' ? '14-Day Trial' : user.subscription_plan || user.subscription_status}
              </span>
              {user.trial_end_date && user.subscription_status === 'trial' && (
                <span style={{
                  fontFamily: 'var(--font-mono)', fontSize: '11px',
                  color: 'var(--text-tertiary)',
                }}>
                  Ends {new Date(user.trial_end_date).toLocaleDateString()}
                </span>
              )}
            </div>
          )}
        </div>

        <SettingsSection user={user} onNavigate={navigate} />
        {!isPro && <PricingSection foundingData={foundingData} onSubscribe={handleSubscribe} loading={checkoutLoading} />}
        <LegalSection />

        <div style={{ marginTop: '12px', marginBottom: '20px' }}>
          <button onClick={logout} style={{
            width: '100%', padding: '14px',
            backgroundColor: 'transparent',
            border: '1px solid var(--stroke-muted)', borderRadius: '12px',
            color: 'var(--text-secondary)', fontSize: '14px',
            fontWeight: 500, cursor: 'pointer', fontFamily: 'var(--font-sans)',
          }}>Sign Out</button>
        </div>
      </div>

      {showAuth && <AuthModal onClose={() => setShowAuth(false)} />}
    </div>
  );
}

function SettingsSection({ user, onNavigate }) {
  const isPro = user && (user.is_premium || user.subscription_status === 'active' || user.subscription_status === 'trial');
  const isMonthly = user?.subscription_plan === 'monthly';

  const menuItems = [
    { id: 'how', label: 'How It Works', subtitle: 'Our model and methodology' },
    { id: 'notifications', label: 'Notifications', subtitle: 'Alert preferences' },
    { id: 'referral', label: 'Referral Program', subtitle: 'Earn 14 days free', requiresAuth: true },
    ...(!isPro && user ? [{ id: 'upgrade', label: 'Upgrade to Pro', subtitle: 'Full pick details and analytics', badge: 'Pro' }] : []),
    ...(isPro && isMonthly ? [{ id: 'annual', label: 'Switch to Annual', subtitle: 'Save vs monthly billing' }] : []),
    ...(isPro ? [{ id: 'cancel', label: 'Cancel Subscription', subtitle: 'Manage your plan', requiresAuth: true }] : []),
  ];

  const visibleItems = user
    ? menuItems
    : menuItems.filter(m => !m.requiresAuth);

  return (
    <div style={{
      backgroundColor: 'var(--surface-1)', borderRadius: '16px',
      overflow: 'hidden', border: '1px solid var(--stroke-subtle)',
      marginBottom: '12px',
    }}>
      {visibleItems.map((item, i) => (
        <button key={item.id} onClick={() => onNavigate(item.id)} style={{
          width: '100%', display: 'flex', justifyContent: 'space-between',
          alignItems: 'center', padding: '16px 20px', background: 'none',
          border: 'none',
          borderBottom: i < visibleItems.length - 1 ? '1px solid var(--stroke-subtle)' : 'none',
          cursor: 'pointer', textAlign: 'left',
        }}>
          <div>
            <div style={{
              fontSize: '14px', fontWeight: 500, color: 'var(--text-primary)',
            }}>{item.label}</div>
            <div style={{
              fontSize: '12px', color: 'var(--text-tertiary)', marginTop: '2px',
            }}>{item.subtitle}</div>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            {item.badge && (
              <span style={{
                fontFamily: 'var(--font-mono)', fontSize: '10px', fontWeight: 600,
                color: 'var(--blue-primary)', backgroundColor: 'rgba(79, 134, 247, 0.1)',
                padding: '2px 8px', borderRadius: '4px', letterSpacing: '0.05em',
              }}>{item.badge}</span>
            )}
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="var(--text-tertiary)" strokeWidth="2">
              <polyline points="9 18 15 12 9 6"/>
            </svg>
          </div>
        </button>
      ))}
    </div>
  );
}

function PricingSection({ foundingData, onSubscribe, loading }) {
  const plans = [
    {
      name: 'Free',
      price: '$0',
      period: '',
      features: ['See if a pick exists today', 'Public record access'],
      cta: null,
      plan: null,
    },
    {
      name: 'Monthly',
      price: '$29',
      period: '/mo',
      features: ['Full pick details', 'Real-time alerts', 'Pick history', 'Bet tracking'],
      cta: 'Start 14-Day Free Trial',
      subtitle: 'No credit card required',
      plan: 'trial',
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
      plan: foundingData?.open ? 'founding' : 'annual',
      highlight: true,
    },
  ];

  return (
    <div style={{
      backgroundColor: 'var(--surface-1)', borderRadius: '16px',
      padding: '20px', border: '1px solid var(--stroke-subtle)',
      marginTop: '12px',
    }}>
      <h3 style={{
        fontSize: '12px', fontWeight: 600, color: 'var(--text-tertiary)',
        textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '16px',
      }}>Plans</h3>

      {foundingData?.open && (
        <div style={{
          backgroundColor: 'rgba(245, 158, 11, 0.08)',
          border: '1px solid rgba(245, 158, 11, 0.2)',
          borderRadius: '10px', padding: '12px 16px', marginBottom: '16px',
          display: 'flex', justifyContent: 'space-between', alignItems: 'center',
        }}>
          <span style={{
            fontSize: '13px', color: 'var(--gold-pro)', fontWeight: 500,
          }}>Founding member spots</span>
          <span style={{
            fontFamily: 'var(--font-mono)', fontSize: '14px',
            color: 'var(--gold-pro)', fontWeight: 700,
          }}>{foundingData.remaining}/500</span>
        </div>
      )}

      <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
        {plans.map(plan => (
          <div key={plan.name} style={{
            padding: '16px', borderRadius: '12px',
            backgroundColor: 'var(--surface-2)',
            border: plan.highlight ? '1px solid var(--blue-primary)' : '1px solid var(--stroke-subtle)',
          }}>
            <div style={{
              display: 'flex', justifyContent: 'space-between',
              alignItems: 'baseline', marginBottom: '8px',
            }}>
              <span style={{ fontSize: '15px', fontWeight: 600, color: 'var(--text-primary)' }}>
                {plan.name}
              </span>
              <span>
                <span style={{
                  fontFamily: 'var(--font-mono)', fontSize: '18px',
                  fontWeight: 700, color: 'var(--text-primary)',
                }}>{plan.price}</span>
                <span style={{ fontSize: '12px', color: 'var(--text-tertiary)' }}>
                  {plan.period}
                </span>
              </span>
            </div>
            <ul style={{ listStyle: 'none', padding: 0, margin: '0 0 12px 0' }}>
              {plan.features.map(f => (
                <li key={f} style={{
                  fontSize: '12px', color: 'var(--text-secondary)',
                  padding: '3px 0', display: 'flex', alignItems: 'center', gap: '6px',
                }}>
                  <span style={{ color: 'var(--green-profit)', fontSize: '10px' }}>&#10003;</span>
                  {f}
                </li>
              ))}
            </ul>
            {plan.cta && (
              <div>
                <button
                  onClick={() => onSubscribe(plan.plan)}
                  disabled={loading}
                  style={{
                    width: '100%', padding: '10px',
                    backgroundColor: plan.highlight ? 'var(--blue-primary)' : 'transparent',
                    border: plan.highlight ? 'none' : '1px solid var(--stroke-muted)',
                    borderRadius: '8px',
                    color: plan.highlight ? '#fff' : 'var(--text-primary)',
                    fontSize: '13px', fontWeight: 600, cursor: 'pointer',
                    fontFamily: 'var(--font-sans)',
                    opacity: loading ? 0.6 : 1,
                  }}
                >
                  {loading ? 'Opening checkout...' : plan.cta}
                </button>
                {plan.subtitle && (
                  <p style={{
                    fontSize: '11px', color: 'var(--green-profit)',
                    textAlign: 'center', margin: '6px 0 0', fontWeight: 500,
                  }}>{plan.subtitle}</p>
                )}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

function LegalSection() {
  const legalItems = [
    { label: 'Terms of Service', url: '/legal/terms' },
    { label: 'Privacy Policy', url: '/legal/privacy' },
    { label: 'Responsible Gaming', url: '/legal/responsible-gaming' },
    { label: 'Disclaimer', url: '/legal/disclaimer' },
  ];

  return (
    <div style={{
      backgroundColor: 'var(--surface-1)', borderRadius: '16px',
      overflow: 'hidden', border: '1px solid var(--stroke-subtle)',
      marginTop: '12px',
    }}>
      <div style={{
        padding: '12px 20px 8px',
        fontSize: '11px', fontWeight: 600, color: 'var(--text-tertiary)',
        textTransform: 'uppercase', letterSpacing: '0.5px',
      }}>Legal</div>
      {legalItems.map((item, i) => (
        <a key={item.label} href={item.url} target="_blank" rel="noopener noreferrer" style={{
          width: '100%', display: 'flex', justifyContent: 'space-between',
          alignItems: 'center', padding: '14px 20px', background: 'none',
          textDecoration: 'none',
          borderTop: '1px solid var(--stroke-subtle)',
          cursor: 'pointer', textAlign: 'left',
        }}>
          <span style={{
            fontSize: '14px', fontWeight: 500, color: 'var(--text-primary)',
          }}>{item.label}</span>
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="var(--text-tertiary)" strokeWidth="2">
            <polyline points="9 18 15 12 9 6"/>
          </svg>
        </a>
      ))}
      <div style={{
        padding: '12px 20px 14px', borderTop: '1px solid var(--stroke-subtle)',
      }}>
        <p style={{
          fontSize: '11px', color: 'var(--text-tertiary)', margin: 0,
          lineHeight: '1.6',
        }}>
          Sharp Picks provides informational content only. We do not accept bets or facilitate gambling. Past performance does not guarantee future results. Please gamble responsibly.
        </p>
      </div>
    </div>
  );
}

function TrialSignup({ onBack }) {
  const { checkAuth } = useAuth();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState(false);

  const handleStart = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      const res = await apiPost('/auth/trial', { email, password });
      if (res.success) {
        setSuccess(true);
        await checkAuth();
        setTimeout(() => onBack(), 1500);
      } else {
        setError(res.error || 'Something went wrong');
      }
    } catch (err) {
      const msg = err?.response?.data?.error || err?.message || 'Something went wrong';
      setError(msg);
    }
    setLoading(false);
  };

  if (success) {
    return (
      <div style={{ padding: '20px', textAlign: 'center', paddingTop: '80px' }}>
        <div style={{
          width: '64px', height: '64px', borderRadius: '50%',
          backgroundColor: 'rgba(52, 211, 153, 0.1)', margin: '0 auto 20px',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
        }}>
          <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="var(--green-profit)" strokeWidth="2">
            <path d="M20 6L9 17l-5-5"/>
          </svg>
        </div>
        <h2 style={{ color: 'var(--text-primary)', fontFamily: 'var(--font-serif)', fontSize: '22px', margin: '0 0 8px' }}>
          Trial Started
        </h2>
        <p style={{ color: 'var(--text-secondary)', fontSize: '14px' }}>
          14 days of full access. No card needed.
        </p>
      </div>
    );
  }

  return (
    <div style={{ padding: '0', paddingBottom: '100px' }}>
      <div style={{ padding: '12px 20px', display: 'flex', alignItems: 'center', gap: '12px' }}>
        <button onClick={onBack} style={{
          background: 'none', border: 'none', color: 'var(--text-secondary)',
          cursor: 'pointer', padding: '4px', display: 'flex',
        }}>
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M19 12H5M12 19l-7-7 7-7"/>
          </svg>
        </button>
        <span style={{
          fontFamily: 'var(--font-mono)', fontSize: '13px', fontWeight: 700,
          letterSpacing: '2px', textTransform: 'uppercase', color: 'var(--text-primary)',
        }}>Free Trial</span>
      </div>

      <div style={{ padding: '0 20px' }}>
        <div style={{
          backgroundColor: 'var(--surface-1)', borderRadius: '16px',
          border: '1px solid var(--stroke-subtle)', padding: '28px 24px',
        }}>
          <h2 style={{
            fontFamily: 'var(--font-serif)', fontSize: '22px', fontWeight: 700,
            color: 'var(--text-primary)', margin: '0 0 6px', textAlign: 'center',
          }}>14 Days Free</h2>
          <p style={{
            color: 'var(--text-secondary)', fontSize: '14px', textAlign: 'center',
            margin: '0 0 24px', lineHeight: '1.5',
          }}>Full access to all picks and features. No credit card required.</p>

          <form onSubmit={handleStart}>
            <div style={{ marginBottom: '12px' }}>
              <label style={{
                display: 'block', fontSize: '12px', fontWeight: 600,
                color: 'var(--text-tertiary)', marginBottom: '6px',
                textTransform: 'uppercase', letterSpacing: '0.5px',
              }}>Email</label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                placeholder="you@example.com"
                style={{
                  width: '100%', padding: '12px 14px', fontSize: '15px',
                  backgroundColor: 'var(--surface-2)', border: '1px solid var(--stroke-subtle)',
                  borderRadius: '10px', color: 'var(--text-primary)',
                  outline: 'none', boxSizing: 'border-box',
                  fontFamily: 'var(--font-sans)',
                }}
              />
            </div>
            <div style={{ marginBottom: '16px' }}>
              <label style={{
                display: 'block', fontSize: '12px', fontWeight: 600,
                color: 'var(--text-tertiary)', marginBottom: '6px',
                textTransform: 'uppercase', letterSpacing: '0.5px',
              }}>Password</label>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                minLength={6}
                placeholder="6+ characters"
                style={{
                  width: '100%', padding: '12px 14px', fontSize: '15px',
                  backgroundColor: 'var(--surface-2)', border: '1px solid var(--stroke-subtle)',
                  borderRadius: '10px', color: 'var(--text-primary)',
                  outline: 'none', boxSizing: 'border-box',
                  fontFamily: 'var(--font-sans)',
                }}
              />
            </div>

            {error && (
              <p style={{
                color: '#ef4444', fontSize: '13px', margin: '0 0 12px',
                padding: '10px 12px', backgroundColor: 'rgba(239,68,68,0.08)',
                borderRadius: '8px',
              }}>{error}</p>
            )}

            <button type="submit" disabled={loading} style={{
              width: '100%', padding: '14px', fontSize: '15px', fontWeight: 700,
              backgroundColor: 'var(--blue-primary)', border: 'none',
              borderRadius: '10px', color: '#fff', cursor: 'pointer',
              fontFamily: 'var(--font-sans)', opacity: loading ? 0.6 : 1,
            }}>
              {loading ? 'Starting trial...' : 'Start Free Trial'}
            </button>
          </form>

          <div style={{
            marginTop: '20px', padding: '14px', backgroundColor: 'var(--surface-2)',
            borderRadius: '10px',
          }}>
            <p style={{
              fontSize: '12px', color: 'var(--text-tertiary)', margin: 0,
              textAlign: 'center', lineHeight: '1.6',
            }}>
              After 14 days, subscribe at $29/mo or $99/yr (founding rate). Cancel anytime. No auto-charge.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
