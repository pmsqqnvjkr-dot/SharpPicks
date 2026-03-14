import { useState, useEffect, useRef } from 'react';
import { useAuth } from '../../hooks/useAuth';
import { useApi, apiPost, apiGet, apiDelete } from '../../hooks/useApi';
import { Capacitor } from '@capacitor/core';
import AuthModal from './AuthModal';
import HowItWorksScreen from './HowItWorksScreen';
import BetTrackingScreen from './BetTrackingScreen';
import NotificationsScreen from './NotificationsScreen';
import UpgradeScreen from './UpgradeScreen';
import CancelScreen from './CancelScreen';
import AnnualConversion from './AnnualConversion';
import WeeklySummary from './WeeklySummary';
import ResolutionScreen from './ResolutionScreen';

const isNative = Capacitor.isNativePlatform();
const WEB_BILLING_URL = 'https://app.sharppicks.ai/upgrade';

export default function ProfileTab({ initialScreen, onScreenChange, pickToTrack, onPickTracked, screenData }) {
  const { user, logout } = useAuth();
  const { data: foundingData } = useApi('/public/founding-count');
  const { data: publicStats } = useApi('/public/stats?sport=nba');
  const [showAuth, setShowAuth] = useState(false);
  const [screen, setScreen] = useState(initialScreen || null);
  const [checkoutLoading, setCheckoutLoading] = useState(false);
  const [localScreenData, setLocalScreenData] = useState(null);
  const [deleteConfirm, setDeleteConfirm] = useState(false);
  const [deleting, setDeleting] = useState(false);

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
  if (screen === 'upgrade') return <UpgradeScreen onBack={() => navigate(null)} user={user} />;
  if (screen === 'cancel') return <CancelScreen onBack={() => navigate(null)} user={user} />;
  if (screen === 'annual') return <AnnualConversion onBack={() => navigate(null)} user={user} />;
  if (screen === 'weekly') return <WeeklySummary onBack={() => navigate(null)} stats={null} weekData={activeScreenData} />;
  if (screen === 'resolution') return <ResolutionScreen onBack={() => navigate(null)} pick={activeScreenData} />;

  const handleSubscribe = async (plan) => {
    if (isNative) {
      const { Browser } = await import('@capacitor/browser');
      await Browser.open({ url: WEB_BILLING_URL });
      return;
    }
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
          }}>Membership</div>
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
          {!isNative && <PricingSection foundingData={foundingData} onSubscribe={handleSubscribe} loading={checkoutLoading} />}
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
        }}>Membership</div>
      </div>

      <div style={{ padding: '0 20px' }}>
        <AccessStatusCard user={user} isPro={isPro} stats={publicStats} />

        <ControlsSection user={user} onNavigate={navigate} isPro={isPro} foundingData={foundingData} onSubscribe={handleSubscribe} checkoutLoading={checkoutLoading} />

        {!isPro && !isNative && <PricingSection foundingData={foundingData} onSubscribe={handleSubscribe} loading={checkoutLoading} />}
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
        <div style={{ marginBottom: '40px' }}>
          {!deleteConfirm ? (
            <button onClick={() => setDeleteConfirm(true)} style={{
              width: '100%', padding: '14px',
              backgroundColor: 'transparent',
              border: '1px solid rgba(239,68,68,0.3)', borderRadius: '12px',
              color: 'var(--red-loss)', fontSize: '14px',
              fontWeight: 500, cursor: 'pointer', fontFamily: 'var(--font-sans)',
            }}>Delete Account</button>
          ) : (
            <div style={{
              backgroundColor: 'var(--surface-1)', borderRadius: '12px',
              padding: '20px', border: '1px solid rgba(239,68,68,0.3)',
            }}>
              <p style={{
                fontSize: '14px', color: 'var(--text-primary)',
                fontWeight: 600, marginBottom: '8px',
              }}>Are you sure?</p>
              <p style={{
                fontSize: '13px', color: 'var(--text-secondary)',
                lineHeight: '1.5', marginBottom: '16px',
              }}>
                This will permanently delete your account, cancel any active subscription, and remove all your data. This action cannot be undone.
              </p>
              <div style={{ display: 'flex', gap: '8px' }}>
                <button
                  onClick={async () => {
                    setDeleting(true);
                    try {
                      const res = await apiDelete('/account/delete');
                      if (res?.error) {
                        alert('Failed to delete account. Please contact support.');
                      } else {
                        window.location.reload();
                      }
                    } catch {
                      alert('Failed to delete account. Please contact support.');
                    }
                    setDeleting(false);
                  }}
                  disabled={deleting}
                  style={{
                    flex: 1, padding: '12px',
                    backgroundColor: 'rgba(239,68,68,0.15)',
                    border: 'none', borderRadius: '8px',
                    color: '#ef4444', fontSize: '14px',
                    fontWeight: 700, cursor: 'pointer',
                    fontFamily: 'var(--font-sans)',
                    opacity: deleting ? 0.5 : 1,
                  }}
                >{deleting ? 'Deleting...' : 'Yes, Delete'}</button>
                <button
                  onClick={() => setDeleteConfirm(false)}
                  style={{
                    flex: 1, padding: '12px',
                    backgroundColor: 'var(--surface-2)',
                    border: 'none', borderRadius: '8px',
                    color: 'var(--text-secondary)', fontSize: '14px',
                    fontWeight: 600, cursor: 'pointer',
                    fontFamily: 'var(--font-sans)',
                  }}
                >Cancel</button>
              </div>
            </div>
          )}
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
    { id: 'how', label: 'Model Architecture', subtitle: 'Edge logic, filters, and methodology' },
    { id: 'notifications', label: 'Signal Alerts', subtitle: 'Pick delivery and result notifications' },
    ...(!isPro && user ? [{ id: 'upgrade', label: isNative ? 'Unlock Pro Features' : 'Upgrade to Pro', subtitle: isNative ? 'Full pick details and analytics' : 'Full pick details and analytics', badge: 'Pro' }] : []),
    ...(!isNative && isPro && isMonthly ? [{ id: 'annual', label: 'Switch to Annual', subtitle: 'Save vs monthly billing' }] : []),
    ...(isPro ? [{ id: 'cancel', label: 'Allocation & Access', subtitle: isNative ? 'Plan and membership' : 'Billing, plan, and membership', requiresAuth: true }] : []),
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
      price: '',
      period: 'Free',
      features: ['See if a pick exists today', 'Public record access'],
      cta: null,
      plan: null,
    },
    {
      name: 'Monthly',
      price: '',
      period: 'Monthly',
      features: ['Full pick details', 'Real-time alerts', 'Pick history', 'Bet tracking'],
      cta: 'Start Free Trial',
      subtitle: 'Cancel anytime.',
      plan: 'trial',
    },
    {
      name: 'Annual',
      price: '',
      period: 'Annual',
      features: [
        'Everything in Monthly',
        foundingData?.open ? `Founding member (${foundingData?.remaining || 0} of 50 left)` : 'Best value plan',
        'Priority support',
        'Founding member badge',
      ],
      cta: foundingData?.open ? 'Claim Founding Spot' : 'See Annual Plan',
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
          }}>{foundingData.remaining}/50</span>
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
    { label: 'Terms of Service', url: '/terms' },
    { label: 'Privacy Policy', url: '/privacy' },
    { label: 'Disclaimer', url: '/disclaimer' },
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
      <a href="mailto:support@sharppicks.ai" style={{
        width: '100%', display: 'flex', justifyContent: 'space-between',
        alignItems: 'center', padding: '14px 20px', background: 'none',
        textDecoration: 'none',
        borderTop: '1px solid var(--stroke-subtle)',
        cursor: 'pointer', textAlign: 'left',
      }}>
        <span style={{
          fontSize: '14px', fontWeight: 500, color: 'var(--text-primary)',
        }}>Contact Us</span>
        <span style={{ fontSize: '12px', color: 'var(--text-tertiary)' }}>support@sharppicks.ai</span>
      </a>
      <div style={{
        padding: '12px 20px 14px', borderTop: '1px solid var(--stroke-subtle)',
      }}>
        <p style={{
          fontSize: '11px', color: 'var(--text-tertiary)', margin: 0,
          lineHeight: '1.6',
        }}>
          SharpPicks provides sports betting analytics and information for educational and entertainment purposes only. SharpPicks is not a sportsbook, does not accept wagers or real-money deposits, and does not pay out prizes. Past performance does not guarantee future results. Please gamble responsibly. If you or someone you know has a gambling problem, call 1-800-GAMBLER.
        </p>
        <p style={{
          fontSize: '10px', color: 'var(--text-tertiary)', margin: '8px 0 0', opacity: 0.6,
          fontFamily: 'var(--font-mono)',
        }}>
          v1.0.0
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
          }}>14-Day Trial</h2>
          <p style={{
            color: 'var(--text-secondary)', fontSize: '14px', textAlign: 'center',
            margin: '0 0 24px', lineHeight: '1.5',
          }}>Full access to all picks and features. Cancel anytime.</p>

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
              {loading ? 'Starting trial...' : 'Start Trial'}
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
              {isNative
                ? 'Full access to all picks and features during your trial. Cancel anytime.'
                : 'Full access to all picks and features during your trial. Cancel anytime.'}
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

function AccessStatusCard({ user, isPro, stats }) {
  useCardAnimations();
  const isFounder = user.founding_member;
  const isTrial = user.subscription_status === 'trial';
  const displayName = user.display_name || user.username || user.email?.split('@')[0] || '';

  const trialDaysLeft = (isTrial && user.trial_end_date)
    ? Math.max(0, Math.ceil((new Date(user.trial_end_date) - new Date()) / (1000 * 60 * 60 * 24)))
    : null;
  const trialTotalDays = 14;
  const trialProgress = trialDaysLeft != null ? trialDaysLeft / trialTotalDays : 1;
  const isUrgent = trialDaysLeft != null && trialDaysLeft <= 3;

  const tierLabel = isTrial
    ? 'PRO TRIAL'
    : isFounder
      ? 'FOUNDING MEMBER'
      : isPro
        ? 'PRO'
        : 'FREE';

  const accessLabel = isPro ? 'FULL ACCESS' : 'LIMITED';

  const borderBg = isFounder
    ? 'linear-gradient(135deg, rgba(245,166,35,0.6) 0%, rgba(255,215,0,0.3) 25%, rgba(184,134,11,0.5) 50%, rgba(255,215,0,0.3) 75%, rgba(245,166,35,0.6) 100%)'
    : isPro
      ? 'linear-gradient(135deg, rgba(79,134,247,0.5) 0%, rgba(47,95,214,0.3) 50%, rgba(79,134,247,0.5) 100%)'
      : 'var(--stroke-subtle)';

  const progressColor = isUrgent
    ? '#ef4444'
    : trialDaysLeft != null && trialDaysLeft <= 7
      ? '#f59e0b'
      : 'var(--green-profit, #34D399)';
  const progressGlow = isUrgent
    ? '0 0 8px rgba(239,68,68,0.5)'
    : '0 0 6px rgba(52,211,153,0.3)';

  const pnl = stats?.pnl;
  const capitalPreserved = stats?.total_picks && stats?.total_passes
    ? Math.round((stats.total_passes / (stats.total_picks + stats.total_passes)) * 100)
    : null;

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
        padding: '20px 22px',
        backgroundColor: 'var(--surface-1)',
        overflow: 'hidden',
      }}>
        <div style={{
          position: 'absolute', inset: 0, pointerEvents: 'none', borderRadius: '19px',
          backgroundImage: 'url("data:image/svg+xml,%3Csvg viewBox=\'0 0 256 256\' xmlns=\'http://www.w3.org/2000/svg\'%3E%3Cfilter id=\'n\'%3E%3CfeTurbulence type=\'fractalNoise\' baseFrequency=\'0.9\' numOctaves=\'4\' stitchTiles=\'stitch\'/%3E%3C/filter%3E%3Crect width=\'100%25\' height=\'100%25\' filter=\'url(%23n)\' opacity=\'0.04\'/%3E%3C/svg%3E")',
        }} />

        <div style={{
          position: 'absolute', inset: 0, pointerEvents: 'none', borderRadius: '19px',
          opacity: 0.03,
          backgroundImage: `repeating-linear-gradient(0deg, transparent, transparent 19px, rgba(255,255,255,0.5) 19px, rgba(255,255,255,0.5) 20px), repeating-linear-gradient(90deg, transparent, transparent 19px, rgba(255,255,255,0.5) 19px, rgba(255,255,255,0.5) 20px)`,
        }} />

        <div style={{
          position: 'absolute', right: '8px', bottom: '8px', pointerEvents: 'none',
          fontFamily: 'var(--font-serif)', fontSize: '96px', fontWeight: 900,
          lineHeight: 1, letterSpacing: '-4px',
          color: 'rgba(255,255,255,0.025)',
          userSelect: 'none',
        }}>SP</div>

        <div style={{
          display: 'flex', justifyContent: 'space-between', alignItems: 'center',
          marginBottom: '20px', position: 'relative', zIndex: 1,
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span style={{
              fontFamily: 'var(--font-serif)', fontSize: '18px',
              fontWeight: 700, color: 'var(--text-primary)',
            }}>{displayName}</span>
            {isPro && (
              <div style={{
                width: '18px', height: '18px', borderRadius: '50%',
                background: 'var(--green-profit, #34D399)',
                display: 'grid', placeItems: 'center', flexShrink: 0,
              }}>
                <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="var(--bg, #0A0D14)" strokeWidth="3.5" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M20 6L9 17l-5-5"/>
                </svg>
              </div>
            )}
          </div>

          {trialDaysLeft != null && (
            <span style={{
              fontFamily: 'var(--font-mono)', fontSize: '12px',
              fontWeight: 700, color: isUrgent ? '#ef4444' : 'var(--text-secondary)',
            }}>
              {trialDaysLeft} {trialDaysLeft === 1 ? 'Day' : 'Days'} Remaining
            </span>
          )}
          {!isTrial && isPro && user.current_period_end && (
            <span style={{
              fontFamily: 'var(--font-mono)', fontSize: '11px',
              fontWeight: 500, color: 'var(--text-tertiary)',
            }}>
              Renews {new Date(user.current_period_end).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}
            </span>
          )}
        </div>

        {trialDaysLeft != null && (
          <div style={{
            marginBottom: '20px', position: 'relative', zIndex: 1,
          }}>
            <div style={{
              width: '100%', height: '4px', borderRadius: '2px',
              backgroundColor: 'rgba(255,255,255,0.06)',
              overflow: 'hidden',
            }}>
              <div style={{
                width: `${Math.max(trialProgress * 100, 2)}%`,
                height: '100%', borderRadius: '2px',
                backgroundColor: progressColor,
                boxShadow: progressGlow,
                transition: 'width 0.6s ease, background-color 0.4s ease',
              }} />
            </div>
          </div>
        )}

        <div style={{
          textAlign: 'center',
          padding: '16px 0',
          marginBottom: pnl != null ? '12px' : '16px',
          position: 'relative', zIndex: 1,
        }}>
          <div style={{
            fontFamily: 'var(--font-mono)', fontSize: '11px',
            fontWeight: 700, letterSpacing: '3px', textTransform: 'uppercase',
            color: isFounder ? 'var(--gold-pro, #F5A623)' : isPro ? 'var(--blue-primary)' : 'var(--text-tertiary)',
            marginBottom: '4px',
          }}>{tierLabel}</div>
          <div style={{
            fontFamily: 'var(--font-mono)', fontSize: '20px',
            fontWeight: 800, letterSpacing: '2px', textTransform: 'uppercase',
            color: isPro ? 'var(--text-primary)' : 'var(--text-tertiary)',
          }}>{accessLabel}</div>
        </div>

        {isFounder && (
          <div style={{
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            gap: '10px', marginBottom: '16px', position: 'relative', zIndex: 1,
          }}>
            <svg width="16" height="16" viewBox="0 0 24 24" fill="#F5A623" style={{ filter: 'drop-shadow(0 0 4px rgba(245,166,35,0.4))' }}>
              <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/>
            </svg>
            <span style={{
              fontFamily: 'var(--font-mono)', fontSize: '22px',
              fontWeight: 800, lineHeight: 1,
              background: 'linear-gradient(135deg, #FFD700, #F5A623)',
              WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent',
              backgroundClip: 'text',
            }}>
              #{String(user.founding_number || '').padStart(3, '0')}
            </span>
          </div>
        )}

        {pnl != null && (
          <div style={{
            borderTop: `1px solid ${isFounder ? 'rgba(245,166,35,0.08)' : 'rgba(255,255,255,0.05)'}`,
            paddingTop: '14px', marginBottom: '14px',
            display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end',
            position: 'relative', zIndex: 1,
          }}>
            <div>
              <div style={{
                fontFamily: 'var(--font-mono)', fontSize: '8px', fontWeight: 600,
                letterSpacing: '1px', textTransform: 'uppercase',
                color: 'var(--text-tertiary)', opacity: 0.7, marginBottom: '4px',
              }}>Since Activation</div>
              <div style={{
                fontFamily: 'var(--font-mono)', fontSize: '22px', fontWeight: 800,
                color: pnl >= 0 ? 'var(--green-profit, #34D399)' : 'var(--red-loss, #9E7A7C)',
                lineHeight: 1,
              }}>{pnl >= 0 ? '+' : ''}{pnl.toFixed(2)}u</div>
            </div>
            {capitalPreserved != null && (
              <div style={{ textAlign: 'right' }}>
                <div style={{
                  fontFamily: 'var(--font-mono)', fontSize: '8px', fontWeight: 600,
                  letterSpacing: '1px', textTransform: 'uppercase',
                  color: 'var(--text-tertiary)', opacity: 0.7, marginBottom: '4px',
                }}>Capital Preserved</div>
                <div style={{
                  fontFamily: 'var(--font-mono)', fontSize: '18px', fontWeight: 700,
                  color: 'var(--text-secondary)', lineHeight: 1,
                }}>{capitalPreserved}%</div>
              </div>
            )}
          </div>
        )}

        <div style={{
          borderTop: `1px solid ${isFounder ? 'rgba(245,166,35,0.08)' : 'rgba(255,255,255,0.05)'}`,
          paddingTop: '14px',
          display: 'flex', justifyContent: 'space-around',
          position: 'relative', zIndex: 1,
        }}>
          <StatusIndicator label="Model Visibility" value={isPro ? 'FULL' : 'LIMITED'} active={isPro} />
          <StatusIndicator label="Edge Data" value={isPro ? 'ENABLED' : 'HIDDEN'} active={isPro} />
          <StatusIndicator label="Tracking" value={isPro ? 'ACTIVE' : 'OFF'} active={isPro} />
        </div>
      </div>
    </div>
  );
}

function StatusIndicator({ label, value, active }) {
  return (
    <div style={{ textAlign: 'center' }}>
      <div style={{
        fontFamily: 'var(--font-mono)', fontSize: '11px',
        fontWeight: 700, letterSpacing: '0.5px',
        color: active ? 'var(--green-profit, #34D399)' : 'var(--text-tertiary)',
        marginBottom: '3px',
      }}>{value}</div>
      <div style={{
        fontFamily: 'var(--font-mono)', fontSize: '8px',
        fontWeight: 600, letterSpacing: '1px', textTransform: 'uppercase',
        color: 'var(--text-tertiary)', opacity: 0.7,
      }}>{label}</div>
    </div>
  );
}

function ControlsSection({ user, onNavigate, isPro, foundingData, onSubscribe, checkoutLoading }) {
  const isMonthly = user?.subscription_plan === 'monthly';

  const menuItems = [
    ...(isPro ? [{ id: 'notifications', label: 'Signal Alerts', subtitle: 'Pick delivery and result notifications' }] : []),
    { id: 'how', label: 'Model Architecture', subtitle: 'Edge logic, filters, and methodology' },
    ...(!isPro && user ? [{ id: 'upgrade', label: isNative ? 'Unlock Pro Features' : 'Upgrade to Pro', subtitle: 'Unlock full decision visibility', badge: 'Pro' }] : []),
    ...(!isNative && isPro && isMonthly ? [{ id: 'annual', label: 'Switch to Annual', subtitle: 'Save vs monthly billing' }] : []),
    ...(isPro ? [{ id: 'cancel', label: 'Allocation & Access', subtitle: isNative ? 'Plan and membership' : 'Billing, plan, and membership' }] : []),
  ];

  return (
    <div style={{
      backgroundColor: 'var(--surface-1)', borderRadius: '16px',
      overflow: 'hidden', border: '1px solid var(--stroke-subtle)',
      marginBottom: '12px',
    }}>
      <div style={{
        padding: '12px 20px 8px',
        fontFamily: 'var(--font-mono)', fontSize: '9px', fontWeight: 600,
        letterSpacing: '1.5px', textTransform: 'uppercase',
        color: 'var(--text-tertiary)',
      }}>Controls</div>
      {menuItems.map((item, i) => (
        <button key={item.id} onClick={() => onNavigate(item.id)} style={{
          width: '100%', display: 'flex', justifyContent: 'space-between',
          alignItems: 'center', padding: '14px 20px', background: 'none',
          border: 'none',
          borderTop: '1px solid var(--stroke-subtle)',
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
