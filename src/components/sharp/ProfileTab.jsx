import { useState, useEffect, useRef } from 'react';
import { useAuth } from '../../hooks/useAuth';
import { useApi, apiPost, apiGet } from '../../hooks/useApi';
import AuthModal from './AuthModal';
import HowItWorksScreen from './HowItWorksScreen';
import BetTrackingScreen from './BetTrackingScreen';
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
    setCheckoutLoading(true);
    try {
      const data = await apiPost('/subscriptions/create-checkout', { plan });
      if (data.checkout_url) {
        window.location.href = data.checkout_url;
      } else if (data.error) {
        alert(data.error);
      }
    } catch (e) {
      alert('Unable to start checkout. Please try again.');
    } finally {
      setCheckoutLoading(false);
    }
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
        <MembershipCard user={user} isPro={isPro} />
        {isPro && <StatRibbon />}

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
  const isPro = user && (user.is_premium || user.subscription_status === 'active' || user.subscription_status === 'trial' || user.founding_member);
  const isMonthly = user?.subscription_plan === 'monthly';

  const menuItems = [
    { id: 'how', label: 'How It Works', subtitle: 'Our model and methodology' },
    { id: 'notifications', label: 'Notifications', subtitle: 'Alert preferences' },
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
    { label: 'Refund Policy', url: '/legal/refund' },
    { label: 'Responsible Gaming', url: '/legal/responsible-gaming' },
    { label: 'Founding Members Program', url: '/legal/founding-members' },
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
          Full access activated. Explore your dashboard.
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
              Subscribe at $29/mo or $99/yr (founding rate). Cancel anytime. No auto-charge.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}

function useCardAnimations() {
  const injected = useRef(false);
  useEffect(() => {
    if (injected.current) return;
    injected.current = true;
    const style = document.createElement('style');
    style.textContent = `
      @keyframes spBorderShimmer {
        0% { background-position: 0% 50%; }
        50% { background-position: 100% 50%; }
        100% { background-position: 0% 50%; }
      }
      @keyframes spGoldRing {
        0% { background-position: 0% 50%; }
        50% { background-position: 100% 50%; }
        100% { background-position: 0% 50%; }
      }
    `;
    document.head.appendChild(style);
  }, []);
}

function MembershipCard({ user, isPro }) {
  useCardAnimations();
  const isFounder = user.founding_member;
  const initial = (user.display_name || user.username || user.email || '?')[0].toUpperCase();
  const displayName = user.display_name || user.username || user.email?.split('@')[0] || '';
  const memberSince = user.created_at
    ? new Date(user.created_at).toLocaleDateString('en-US', { month: 'short', year: '2-digit' })
    : '';

  const planLabel = user.subscription_status === 'trial'
    ? '14-Day Trial'
    : isFounder
      ? 'Lifetime'
      : user.subscription_plan
        ? user.subscription_plan.charAt(0).toUpperCase() + user.subscription_plan.slice(1)
        : user.subscription_status || 'Free';

  const borderBg = isFounder
    ? 'linear-gradient(135deg, rgba(245,166,35,0.6) 0%, rgba(255,215,0,0.3) 25%, rgba(184,134,11,0.5) 50%, rgba(255,215,0,0.3) 75%, rgba(245,166,35,0.6) 100%)'
    : isPro
      ? 'linear-gradient(135deg, rgba(79,134,247,0.5) 0%, rgba(47,95,214,0.3) 50%, rgba(79,134,247,0.5) 100%)'
      : 'var(--stroke-subtle)';

  const ringBg = isFounder
    ? 'linear-gradient(135deg, #F5A623, #FFD700, #B8860B, #FFD700, #F5A623)'
    : isPro
      ? 'linear-gradient(135deg, #4F86F7, #6B8BF5, #2F5FD6)'
      : 'var(--stroke-muted)';

  const crestColor = isFounder ? 'rgba(245,166,35,0.06)' : 'rgba(255,255,255,0.03)';

  return (
    <div style={{
      borderRadius: '20px',
      padding: '1.5px',
      background: borderBg,
      backgroundSize: '200% 200%',
      animation: isFounder || isPro ? 'spBorderShimmer 6s ease infinite' : 'none',
      marginBottom: '16px',
    }}>
      <div style={{
        position: 'relative',
        borderRadius: '19px',
        padding: '24px 22px 20px',
        backgroundColor: 'var(--surface-1)',
        overflow: 'hidden',
      }}>
        <div style={{
          position: 'absolute', inset: 0, pointerEvents: 'none', borderRadius: '19px',
          backgroundImage: 'url("data:image/svg+xml,%3Csvg viewBox=\'0 0 256 256\' xmlns=\'http://www.w3.org/2000/svg\'%3E%3Cfilter id=\'n\'%3E%3CfeTurbulence type=\'fractalNoise\' baseFrequency=\'0.9\' numOctaves=\'4\' stitchTiles=\'stitch\'/%3E%3C/filter%3E%3Crect width=\'100%25\' height=\'100%25\' filter=\'url(%23n)\' opacity=\'0.04\'/%3E%3C/svg%3E")',
        }} />

        <svg viewBox="0 0 40 40" width="180" height="180" fill="none" style={{
          position: 'absolute', right: '-20px', top: '-20px',
          opacity: 0.8, pointerEvents: 'none',
        }}>
          <path d="M20 4L6 10v10c0 9.2 6 17.4 14 20 8-2.6 14-10.8 14-20V10L20 4z" stroke={crestColor} strokeWidth="1.5" fill="none"/>
          <rect x="12" y="24" width="3" height="6" rx="1" fill={isFounder ? 'rgba(245,166,35,0.03)' : 'rgba(255,255,255,0.02)'}/>
          <rect x="17" y="20" width="3" height="10" rx="1" fill={isFounder ? 'rgba(245,166,35,0.03)' : 'rgba(255,255,255,0.02)'}/>
          <rect x="22" y="22" width="3" height="8" rx="1" fill={isFounder ? 'rgba(245,166,35,0.03)' : 'rgba(255,255,255,0.02)'}/>
          <path d="M11 22L17 16L22 19L30 11" stroke={crestColor} strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
          <path d="M26 11h4v4" stroke={crestColor} strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
        </svg>

        <div style={{ display: 'flex', alignItems: 'center', gap: '14px', marginBottom: '20px', position: 'relative', zIndex: 1 }}>
          <div style={{
            width: '52px', height: '52px', borderRadius: '16px',
            display: 'grid', placeItems: 'center',
            position: 'relative',
          }}>
            <div style={{
              position: 'absolute', inset: '-3px', borderRadius: '19px',
              background: ringBg,
              backgroundSize: '300% 300%',
              animation: isFounder ? 'spGoldRing 4s ease infinite' : 'none',
              zIndex: 0,
            }} />
            <div style={{
              position: 'relative', width: '100%', height: '100%', borderRadius: '15px',
              background: 'linear-gradient(135deg, #4F86F7, #2F5FD6)',
              display: 'grid', placeItems: 'center',
              fontFamily: 'var(--font-serif)', fontSize: '22px',
              fontWeight: 700, color: 'var(--bg)',
              zIndex: 1,
            }}>
              {initial}
            </div>
          </div>

          <div style={{ flex: 1 }}>
            <div style={{
              display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '3px',
            }}>
              <span style={{
                fontFamily: 'var(--font-serif)', fontSize: '20px',
                fontWeight: 700, color: 'var(--text-primary)',
              }}>{displayName}</span>
              {isPro && (
                <div style={{
                  width: '20px', height: '20px', borderRadius: '50%',
                  background: 'var(--green, #34D399)',
                  display: 'grid', placeItems: 'center', flexShrink: 0,
                }}>
                  <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="var(--bg, #0A0D14)" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M20 6L9 17l-5-5"/>
                  </svg>
                </div>
              )}
            </div>
            <div style={{
              fontFamily: 'var(--font-mono)', fontSize: '11px',
              color: 'var(--text-tertiary)', fontWeight: 400,
            }}>{user.email}</div>
          </div>
        </div>

        {isFounder && (
          <div style={{
            display: 'flex', alignItems: 'center', justifyContent: 'space-between',
            marginBottom: '16px', position: 'relative', zIndex: 1,
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <div style={{ width: '28px', height: '28px', display: 'grid', placeItems: 'center' }}>
                <svg width="20" height="20" viewBox="0 0 24 24" fill="#F5A623" style={{ filter: 'drop-shadow(0 0 6px rgba(245,166,35,0.4))' }}>
                  <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/>
                </svg>
              </div>
              <span style={{
                fontFamily: 'var(--font-mono)', fontSize: '10px',
                fontWeight: 700, letterSpacing: '2px', textTransform: 'uppercase',
                background: 'linear-gradient(135deg, #FFD700, #F5A623, #B8860B)',
                WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent',
                backgroundClip: 'text',
              }}>Founding Member</span>
            </div>
            <span style={{
              fontFamily: 'var(--font-mono)', fontSize: '32px',
              fontWeight: 800, lineHeight: 1,
              background: 'linear-gradient(135deg, #FFD700, #F5A623)',
              WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent',
              backgroundClip: 'text',
              filter: 'drop-shadow(0 0 8px rgba(245,166,35,0.2))',
            }}>
              #{String(user.founding_number || '').padStart(3, '0')}
            </span>
          </div>
        )}

        <div style={{
          borderTop: `1px solid ${isFounder ? 'rgba(245,166,35,0.1)' : 'var(--stroke-subtle)'}`,
          paddingTop: '16px',
          display: 'flex', justifyContent: 'space-between', alignItems: 'center',
          position: 'relative', zIndex: 1,
        }}>
          <div style={{
            fontFamily: 'var(--font-mono)', fontSize: '10px',
            fontWeight: 700, letterSpacing: '1.5px', textTransform: 'uppercase',
            padding: '5px 14px', borderRadius: '6px',
            background: isPro
              ? 'linear-gradient(135deg, rgba(79,134,247,0.2), rgba(47,95,214,0.15))'
              : 'rgba(255,255,255,0.05)',
            color: isPro ? 'var(--blue-primary)' : 'var(--text-tertiary)',
            border: `1px solid ${isPro ? 'rgba(79,134,247,0.2)' : 'var(--stroke-subtle)'}`,
          }}>{planLabel}</div>

          {memberSince && (
            <span style={{
              fontFamily: 'var(--font-mono)', fontSize: '10px',
              color: 'var(--text-tertiary)', fontWeight: 500,
            }}>Since {memberSince}</span>
          )}

          {user.trial_end_date && user.subscription_status === 'trial' && (
            <span style={{
              fontFamily: 'var(--font-mono)', fontSize: '10px',
              color: 'var(--text-tertiary)',
            }}>
              Ends {new Date(user.trial_end_date).toLocaleDateString()}
            </span>
          )}
        </div>
      </div>
    </div>
  );
}

function StatRibbon() {
  const [stats, setStats] = useState(null);
  useEffect(() => {
    apiGet('/bets/stats').then(d => { if (d && !d.error) setStats(d); }).catch(() => {});
  }, []);

  const followed = stats?.adherence?.picks_followed ?? stats?.totalBets ?? 0;
  const discipline = stats?.winRate != null ? stats.winRate + '%' : '—';
  const profit = stats?.totalProfit != null ? (stats.totalProfit >= 0 ? '+' : '') + '$' + Math.abs(stats.totalProfit).toLocaleString() : '—';
  const profitPositive = stats?.totalProfit != null && stats.totalProfit >= 0;

  const items = [
    { value: followed, label: 'Followed', green: false },
    { value: discipline, label: 'Discipline', green: false },
    { value: profit, label: 'Tracked', green: profitPositive },
  ];

  return (
    <div style={{
      display: 'flex', gap: '1px',
      background: 'var(--stroke-subtle)',
      borderRadius: '14px', overflow: 'hidden',
      marginBottom: '20px',
    }}>
      {items.map((item, i) => (
        <div key={i} style={{
          flex: 1, background: 'var(--surface-1)',
          padding: '14px 8px', textAlign: 'center',
          borderRadius: i === 0 ? '14px 0 0 14px' : i === 2 ? '0 14px 14px 0' : '0',
        }}>
          <div style={{
            fontFamily: 'var(--font-mono)', fontSize: '18px',
            fontWeight: 800, lineHeight: 1, marginBottom: '4px',
            color: item.green ? 'var(--green, #34D399)' : 'var(--text-primary)',
          }}>{item.value}</div>
          <div style={{
            fontFamily: 'var(--font-mono)', fontSize: '8px',
            fontWeight: 600, letterSpacing: '1px', textTransform: 'uppercase',
            color: 'var(--text-tertiary)',
          }}>{item.label}</div>
        </div>
      ))}
    </div>
  );
}
