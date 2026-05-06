import { useState, useEffect, useRef, useCallback } from 'react';
import { Capacitor } from '@capacitor/core';
import { useLocation, useNavigate } from 'react-router-dom';
import { AuthProvider, useAuth } from '../hooks/useAuth';
import { useNetwork } from '../hooks/useNetwork';
import { SportProvider, useSport } from '../hooks/useSport';
import { apiGet, apiPost } from '../hooks/useApi';
import { trackPageView, trackEvent } from '../utils/eventTracker';

const PROD_URL = 'https://app.sharppicks.ai';
const NATIVE_API = Capacitor.isNativePlatform() ? PROD_URL : '';
import TabNav from '../components/sharp/TabNav';
import AppHeader from '../components/sharp/AppHeader';
import PicksTab from '../components/sharp/PicksTab';
import InsightsTab from '../components/sharp/InsightsTab';
import PerformanceTab from '../components/sharp/PerformanceTab';
import ProfileTab from '../components/sharp/ProfileTab';
import LandingPage from '../components/sharp/LandingPage';
import OnboardingFlow from '../components/sharp/OnboardingFlow';
import AuthModal from '../components/sharp/AuthModal';

function PaymentFailedGate({ user }) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);
  const isIOSNative = Capacitor.getPlatform() === 'ios' && Capacitor.isNativePlatform();
  const isAndroidNative = Capacitor.getPlatform() === 'android' && Capacitor.isNativePlatform();

  const handleUpdatePayment = async () => {
    if (isIOSNative) {
      try {
        const { Browser } = await import('@capacitor/browser');
        await Browser.open({ url: 'https://apps.apple.com/account/subscriptions' });
      } catch (e) {
        setError(e?.message || 'Could not open subscription settings.');
      }
      return;
    }

    setBusy(true);
    setError(null);
    try {
      const res = await apiPost('/stripe/billing-portal', {
        return_url: typeof window !== 'undefined' ? window.location.origin + '/?billing_return=1' : undefined,
      });
      if (res && res.url) {
        if (isAndroidNative) {
          const { Browser } = await import('@capacitor/browser');
          await Browser.open({ url: res.url });
        } else {
          window.location.href = res.url;
        }
        return;
      }
      setError(res?.error || 'Could not open billing portal. Please try again.');
    } catch (err) {
      setError('Network error. Please check your connection and try again.');
    } finally {
      setBusy(false);
    }
  };

  const handleSignOut = async () => {
    try {
      await fetch(`${NATIVE_API}/api/auth/logout`, { method: 'POST', credentials: 'include' });
    } catch {}
    window.location.reload();
  };

  return (
    <div style={{
      minHeight: '100vh',
      backgroundColor: 'var(--bg-primary)',
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'center',
      padding: '40px 24px max(40px, env(safe-area-inset-bottom)) 24px',
      paddingTop: 'max(40px, env(safe-area-inset-top))',
      textAlign: 'center',
    }}>
      <div style={{
        width: '72px', height: '72px', borderRadius: '50%',
        background: 'rgba(107, 138, 196, 0.10)',
        border: '1px solid rgba(107, 138, 196, 0.28)',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        margin: '0 auto 24px',
      }}>
        <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="#6B8AC4" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
          <rect x="2" y="6" width="20" height="13" rx="2" />
          <line x1="2" y1="11" x2="22" y2="11" />
          <line x1="6" y1="15" x2="10" y2="15" />
        </svg>
      </div>

      <h1 style={{
        fontFamily: 'var(--font-serif)', fontSize: '24px', fontWeight: 600,
        color: 'var(--text-primary)', marginBottom: '12px',
        letterSpacing: '-0.01em',
      }}>Payment failed, access paused</h1>

      <p style={{
        fontSize: '15px', color: 'var(--text-secondary)', lineHeight: 1.55,
        maxWidth: '340px', marginBottom: '8px',
      }}>
        Your last invoice didn't go through, so we've paused your Pro access. Update your card and we'll restore everything immediately.
      </p>

      <p style={{
        fontSize: '13px', color: 'var(--text-tertiary)',
        marginBottom: '28px', maxWidth: '320px',
      }}>
        No picks are missed: every day's signal stays in your history once your subscription is current.
      </p>

      {error && (
        <p style={{
          fontSize: '13px', color: '#ef4444', marginBottom: '16px',
          fontFamily: 'var(--font-sans)', maxWidth: '320px',
        }}>{error}</p>
      )}

      <button
        onClick={handleUpdatePayment}
        disabled={busy && !isIOSNative}
        style={{
          padding: '14px 28px',
          backgroundColor: (busy && !isIOSNative) ? 'var(--text-tertiary)' : '#4ADE80',
          border: 'none', borderRadius: '12px',
          color: '#0A0E1A', fontSize: '15px', fontWeight: 600,
          cursor: (busy && !isIOSNative) ? 'wait' : 'pointer',
          fontFamily: 'var(--font-sans)', marginBottom: '14px',
          minWidth: '240px', minHeight: '48px',
          letterSpacing: '0.01em',
          WebkitTapHighlightColor: 'transparent',
        }}
      >
        {isIOSNative
          ? 'Manage subscription in App Store'
          : busy ? 'Opening Stripe…' : 'Update payment method'}
      </button>

      {isIOSNative && (
        <p style={{
          fontSize: '13px', color: 'var(--text-secondary)', lineHeight: 1.55,
          maxWidth: '340px', marginBottom: '12px',
        }}>
          Manage your subscription in Settings &rarr; Apple ID &rarr; Subscriptions.
        </p>
      )}

      <a
        href="mailto:support@sharppicks.ai?subject=Payment%20issue"
        style={{
          padding: '12px 20px', backgroundColor: 'transparent',
          border: '1px solid var(--stroke-subtle)', borderRadius: '10px',
          color: 'var(--text-secondary)', fontSize: '14px',
          textDecoration: 'none', display: 'inline-block',
          fontFamily: 'var(--font-sans)', marginBottom: '20px',
          minWidth: '240px',
        }}
      >Contact support</a>

      <button
        onClick={handleSignOut}
        style={{
          background: 'none', border: 'none',
          color: 'var(--text-tertiary)', fontSize: '13px', cursor: 'pointer',
          padding: '12px',
          WebkitTapHighlightColor: 'transparent',
        }}
      >Sign out</button>

      {user?.email && (
        <p style={{
          fontSize: '11px', color: 'var(--text-muted)',
          marginTop: '20px', fontFamily: 'var(--font-mono)',
          letterSpacing: '0.04em',
        }}>{user.email}</p>
      )}
    </div>
  );
}

function WelcomeScreen({ onContinue }) {
  return (
    <div style={{
      minHeight: '100vh',
      backgroundColor: 'var(--bg-primary)',
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'center',
      padding: '40px 24px',
      textAlign: 'center',
    }}>
      <img
        src="/logo.png"
        alt="SharpPicks"
        style={{
          width: '160px', height: '160px', borderRadius: '28px',
          marginBottom: '32px',
        }}
      />
      <h1 style={{
        fontFamily: 'var(--font-serif)', fontSize: '28px', fontWeight: 600,
        color: 'var(--text-primary)', marginBottom: '12px',
      }}>Welcome to SharpPicks Pro</h1>
      <p style={{
        fontSize: '15px', color: 'var(--text-secondary)', lineHeight: '1.6',
        maxWidth: '340px', marginBottom: '8px',
      }}>
        Your subscription is active. You now have full access to every qualified pick, edge analysis, and performance tracking.
      </p>
      <p style={{
        fontSize: '13px', color: 'var(--text-tertiary)', lineHeight: '1.5',
        maxWidth: '320px', marginBottom: '36px',
      }}>
        Most days, the model finds no edge. That silence is the product working. When it speaks, you'll see the full decision.
      </p>
      <button
        onClick={onContinue}
        style={{
          padding: '16px 48px',
          background: 'linear-gradient(135deg, var(--blue-primary), var(--blue-deep))',
          border: 'none', borderRadius: '14px',
          color: '#fff', fontSize: '16px', fontWeight: 700,
          cursor: 'pointer', fontFamily: 'var(--font-sans)',
        }}
      >View Today's Analysis</button>
    </div>
  );
}

function AgeGate({ onConfirm }) {
  return (
    <div style={{
      minHeight: '100vh',
      backgroundColor: 'var(--bg-primary)',
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'center',
      padding: '40px 24px',
      textAlign: 'center',
    }}>
      <div style={{ marginBottom: '24px' }}>
        <svg width="44" height="44" viewBox="0 0 500 500">
          <rect x="150" y="100" width="60" height="300" rx="30" fill="#FFFFFF" />
          <rect x="290" y="100" width="60" height="300" rx="30" fill="#FFFFFF" />
          <rect x="150" y="420" width="200" height="20" rx="10" fill="#5A9E72" />
        </svg>
      </div>
      <h1 style={{
        fontFamily: "'IBM Plex Serif', serif", fontSize: '24px', fontWeight: 600,
        color: 'var(--text-primary)', marginBottom: '12px',
      }}>Age Verification</h1>
      <p style={{
        fontSize: '15px', color: 'var(--text-secondary)', lineHeight: '1.6',
        maxWidth: '340px', marginBottom: '8px',
      }}>
        SharpPicks provides sports market intelligence for informational purposes only.
      </p>
      <p style={{
        fontSize: '14px', color: 'var(--text-secondary)', lineHeight: '1.5',
        maxWidth: '320px', marginBottom: '32px',
      }}>
        You must be 21 years or older to use this app.
      </p>
      <button
        onClick={() => {
          localStorage.setItem('sp_age_verified', '1');
          onConfirm();
        }}
        style={{
          padding: '16px 48px', width: '100%', maxWidth: '320px',
          background: '#5A9E72',
          border: 'none', borderRadius: '8px',
          color: '#0A0D14', fontSize: '16px', fontWeight: 600,
          cursor: 'pointer', fontFamily: "'JetBrains Mono', monospace",
          letterSpacing: '1px',
          marginBottom: '12px',
        }}
      >I am 21 or older</button>
      <button
        onClick={() => {
          window.location.href = 'https://sharppicks.ai';
        }}
        style={{
          padding: '12px 24px',
          background: 'none', border: 'none',
          color: 'var(--text-tertiary)', fontSize: '14px',
          cursor: 'pointer', fontFamily: 'var(--font-sans)',
        }}
      >I am under 21</button>
      <p style={{
        fontSize: '11px', color: 'var(--text-tertiary)', marginTop: '32px',
        lineHeight: '1.6', maxWidth: '300px', opacity: 0.7,
      }}>
        If you or someone you know has a gambling problem, call 1-800-GAMBLER.
      </p>
    </div>
  );
}

function AppContent() {
  const { user, loading, checkAuth } = useAuth();
  const online = useNetwork();
  const location = useLocation();
  const navigate = useNavigate();
  const { setSport } = useSport();
  const [activeTab, setActiveTab] = useState('picks');
  const [picksResetKey, setPicksResetKey] = useState(0);
  const [showOnboarding, setShowOnboarding] = useState(() => localStorage.getItem('sp_onboarded') !== '1');
  const [showWelcome, setShowWelcome] = useState(false);
  const [profileScreen, setProfileScreen] = useState(null);
  const [profileScreenData, setProfileScreenData] = useState(null);
  const [pickToTrack, setPickToTrack] = useState(null);
  const [perfView, setPerfView] = useState(null);
  const [ageVerified, setAgeVerified] = useState(() => localStorage.getItem('sp_age_verified') === '1');

  const [initialInsight, setInitialInsight] = useState(null);
  const [authModalOpen, setAuthModalOpen] = useState(false);
  const [authModalMode, setAuthModalMode] = useState('register');

  useEffect(() => {
    const tabToPage = { picks: '/picks', insights: '/journal', performance: '/performance', profile: '/profile' };
    trackPageView(tabToPage[activeTab] || `/${activeTab}`);
  }, [activeTab]);

  const navigateTo = (tab, screen, data) => {
    setActiveTab(tab);
    if (tab === 'performance' && screen) {
      setPerfView(screen);
    } else {
      if (screen) setProfileScreen(screen);
    }
    if (data?.pickToTrack) setPickToTrack(data.pickToTrack);
    if (data?.screenData) setProfileScreenData(data.screenData);
    if (tab === 'insights' && data?.insight) {
      setInitialInsight(data.insight);
    }
  };

  useEffect(() => {
    if (location.pathname === '/welcome') {
      if (checkAuth) checkAuth();
      setShowWelcome(true);
    }
    if (location.pathname === '/subscribe' && user) {
      setActiveTab('profile');
      setProfileScreen('upgrade');
      navigate('/', { replace: true });
    }
    const params = new URLSearchParams(location.search);
    const verifyStatus = params.get('verify');
    if (verifyStatus === 'success') {
      if (checkAuth) checkAuth();
      navigate('/', { replace: true });
    }
  }, [location.pathname, location.search, user]);

  useEffect(() => {
    if (!Capacitor.isNativePlatform()) return;
    let listener;
    import('@capacitor/app').then(({ App }) => {
      App.addListener('appUrlOpen', ({ url }) => {
        try {
          const parsed = new URL(url);
          if (parsed.pathname === '/welcome' || parsed.pathname === '/open') {
            if (checkAuth) checkAuth();
            setActiveTab('picks');
            navigate('/', { replace: true });
          }
        } catch { /* ignore malformed URLs */ }
      }).then(l => { listener = l; });
    }).catch(() => {});
    return () => { listener?.remove?.(); };
  }, []);

  useEffect(() => {
    const handlePushNav = (e) => {
      const data = e.detail || {};
      trackEvent('notification_opened', { notification_type: data.type || 'unknown', notification_id: data.id || null });
      if (data.type === 'weekly_summary') {
        setActiveTab('profile');
        setProfileScreen('weekly');
      } else if (data.type === 'pick' || data.type === 'result' || data.type === 'revoke' || data.type === 'pretip') {
        if (data.sport) setSport(data.sport);
        setActiveTab('picks');
      } else if (data.type === 'pass') {
        if (data.sport) setSport(data.sport);
        setActiveTab('picks');
      } else if (data.type === 'journal' || data.type === 'market_note') {
        setActiveTab('insights');
      }
    };
    window.addEventListener('sp-push-navigate', handlePushNav);

    const handleSWMessage = (event) => {
      if (event.data?.type === 'sp-push-navigate') {
        handlePushNav({ detail: event.data.data });
      }
    };
    navigator.serviceWorker?.addEventListener('message', handleSWMessage);

    const params = new URLSearchParams(window.location.search);
    const pushParam = params.get('push');
    if (pushParam === 'weekly_summary') {
      setActiveTab('profile');
      setProfileScreen('weekly');
      window.history.replaceState({}, '', '/');
    } else if (pushParam === 'picks') {
      setActiveTab('picks');
      window.history.replaceState({}, '', '/');
    } else if (pushParam === 'journal' || pushParam === 'market_note') {
      setActiveTab('insights');
      window.history.replaceState({}, '', '/');
    }

    return () => {
      window.removeEventListener('sp-push-navigate', handlePushNav);
      navigator.serviceWorker?.removeEventListener('message', handleSWMessage);
    };
  }, []);

  useEffect(() => {
    const onOpenAuth = () => {
      const isPro = user && (
        user.is_premium ||
        user.subscription_status === 'active' ||
        user.subscription_status === 'trial' ||
        user.founding_member
      );
      if (!user) {
        setAuthModalMode('register');
        setAuthModalOpen(true);
      } else if (!isPro) {
        setActiveTab('profile');
        setProfileScreen('upgrade');
      }
    };
    window.addEventListener('sharppicks:open-auth', onOpenAuth);
    return () => window.removeEventListener('sharppicks:open-auth', onOpenAuth);
  }, [user]);

  const handleOnboardingComplete = () => {
    setShowOnboarding(false);
    localStorage.setItem('sp_onboarded', '1');
  };

  const [verifyTimedOut, setVerifyTimedOut] = useState(false);
  const verifyStartRef = useRef(null);

  useEffect(() => {
    if (!(user && user.subscription_status === 'pending_verification')) return;
    if (!verifyStartRef.current) verifyStartRef.current = Date.now();
    setVerifyTimedOut(false);

    const POLL_MS = 4000;
    const TIMEOUT_MS = 5 * 60 * 1000;

    const checkVerification = async () => {
      try {
        const data = await apiGet('/check-verification-status');
        if (data?.verified) { await checkAuth(); return; }
      } catch { /* ignore */ }
      if (Date.now() - verifyStartRef.current > TIMEOUT_MS) {
        setVerifyTimedOut(true);
      }
    };

    const poll = setInterval(checkVerification, POLL_MS);

    const onFocus = () => checkVerification();
    window.addEventListener('focus', onFocus);
    const onVisibility = () => { if (document.visibilityState === 'visible') checkVerification(); };
    document.addEventListener('visibilitychange', onVisibility);

    let appListener;
    if (Capacitor.isNativePlatform()) {
      import('@capacitor/app').then(({ App }) => {
        App.addListener('appStateChange', ({ isActive }) => { if (isActive) checkVerification(); })
          .then(l => { appListener = l; });
      }).catch(() => {});
    }

    return () => {
      clearInterval(poll);
      window.removeEventListener('focus', onFocus);
      document.removeEventListener('visibilitychange', onVisibility);
      appListener?.remove?.();
    };
  }, [user?.subscription_status]);

  if (loading) {
    return (
      <div style={{
        minHeight: '100vh',
        backgroundColor: 'var(--bg-primary)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
      }}>
        <div style={{
          width: '40px',
          height: '40px',
          borderRadius: '50%',
          border: '3px solid var(--stroke-subtle)',
          borderTopColor: 'var(--blue-primary)',
          animation: 'spin 1s linear infinite',
        }} />
        <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
      </div>
    );
  }

  if (!ageVerified) {
    return <AgeGate onConfirm={() => setAgeVerified(true)} />;
  }

  if (!user) {
    if (!Capacitor.isNativePlatform()) {
      const target = (location.pathname === '/signup' || location.pathname === '/register')
        ? '/signup' : '/login';
      window.location.href = target;
      return null;
    }
    const p = location.pathname;
    const q = new URLSearchParams(location.search).get('view');
    const autoView = (p === '/signup' || p === '/register' || q === 'signup') ? 'signup'
                   : (p === '/login' || q === 'signin' || q === 'login') ? 'signin'
                   : null;
    return (
      <>
        <LandingPage autoView={autoView} />
        {authModalOpen && (
          <AuthModal
            onClose={() => setAuthModalOpen(false)}
            initialMode={authModalMode}
            initialAccountType="trial"
          />
        )}
      </>
    );
  }

  const onboardingOverlay = showOnboarding
    ? <OnboardingFlow onComplete={handleOnboardingComplete} />
    : null;

  if (user && user.subscription_status === 'pending_verification') {
    return (
      <div style={{
        minHeight: '100vh',
        backgroundColor: 'var(--bg-primary)',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '40px 24px',
        textAlign: 'center',
      }}>
        <div style={{
          width: '80px', height: '80px', borderRadius: '50%',
          backgroundColor: 'rgba(79,134,247,0.1)',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          margin: '0 auto 24px', fontSize: '36px',
        }}>&#9993;</div>
        <h1 style={{
          fontFamily: 'var(--font-serif)', fontSize: '24px', fontWeight: 600,
          color: 'var(--text-primary)', marginBottom: '12px',
        }}>Verify your email</h1>
        <p style={{
          fontSize: '15px', color: 'var(--text-secondary)', lineHeight: '1.6',
          maxWidth: '360px', marginBottom: '8px',
        }}>
          We sent a verification link to <strong style={{ color: 'var(--text-primary)' }}>{user.email}</strong>.
          Click the link to activate your account and start your trial.
        </p>
        <p style={{
          fontSize: '13px', color: 'var(--text-tertiary)', marginBottom: '28px',
        }}>Check your spam folder if you don't see it.</p>
        {!verifyTimedOut && (
          <div style={{
            display: 'flex', alignItems: 'center', gap: '8px',
            justifyContent: 'center', marginBottom: '20px',
            color: 'var(--text-tertiary)', fontSize: '12px',
            fontFamily: 'var(--font-mono)',
          }}>
            <div style={{
              width: '14px', height: '14px', borderRadius: '50%',
              border: '2px solid var(--stroke-subtle)', borderTopColor: 'var(--blue-primary)',
              animation: 'spin 1s linear infinite',
            }} />
            Waiting for verification...
          </div>
        )}
        {verifyTimedOut && (
          <p style={{
            fontSize: '13px', color: 'var(--text-tertiary)', marginBottom: '12px',
            fontFamily: 'var(--font-sans)',
          }}>
            Didn't get it? Tap below to resend.
          </p>
        )}
        <button
          onClick={async () => {
            try {
              await fetch(`${NATIVE_API}/api/auth/resend-verification`, { method: 'POST', credentials: 'include' });
              verifyStartRef.current = Date.now();
              setVerifyTimedOut(false);
            } catch {}
          }}
          style={{
            padding: '12px 24px', backgroundColor: 'transparent',
            border: '1px solid var(--stroke-subtle)', borderRadius: '10px',
            color: 'var(--text-secondary)', fontSize: '14px', cursor: 'pointer',
            fontFamily: 'var(--font-sans)', marginBottom: '16px',
          }}
        >Resend verification email</button>
        <button
          onClick={async () => {
            await fetch(`${NATIVE_API}/api/auth/logout`, { method: 'POST', credentials: 'include' });
            window.location.reload();
          }}
          style={{
            background: 'none', border: 'none',
            color: 'var(--text-tertiary)', fontSize: '13px', cursor: 'pointer',
          }}
        >Sign out</button>
      </div>
    );
  }

  if (user && user.subscription_status === 'past_due') {
    return <PaymentFailedGate user={user} />;
  }

  if (showWelcome) {
    return <WelcomeScreen onContinue={() => {
      setShowWelcome(false);
      navigate('/', { replace: true });
    }} />;
  }

  return (
    <div style={{
      minHeight: '100vh',
      backgroundColor: 'var(--bg-primary)',
      display: 'flex',
      flexDirection: 'column',
      maxWidth: '480px',
      margin: '0 auto',
      position: 'relative',
    }}>
      <AppHeader onNavigate={(tab, screen) => {
        if (tab === 'picks' && activeTab === 'picks') {
          setPicksResetKey(k => k + 1);
        }
        setActiveTab(tab);
        if (tab === 'profile' && screen) setProfileScreen(screen);
      }} />
      {!online && (
        <div style={{
          padding: '8px 16px',
          backgroundColor: 'rgba(239,68,68,0.12)',
          borderBottom: '1px solid rgba(239,68,68,0.2)',
          display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '8px',
        }}>
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#ef4444" strokeWidth="2" strokeLinecap="round">
            <line x1="1" y1="1" x2="23" y2="23"/>
            <path d="M16.72 11.06A10.94 10.94 0 0 1 19 12.55"/>
            <path d="M5 12.55a10.94 10.94 0 0 1 5.17-2.39"/>
            <path d="M10.71 5.05A16 16 0 0 1 22.56 9"/>
            <path d="M1.42 9a15.91 15.91 0 0 1 4.7-2.88"/>
            <path d="M8.53 16.11a6 6 0 0 1 6.95 0"/>
            <line x1="12" y1="20" x2="12.01" y2="20"/>
          </svg>
          <span style={{
            fontSize: '12px', fontWeight: 600, color: '#ef4444',
            fontFamily: 'var(--font-mono)', letterSpacing: '0.3px',
          }}>No connection. Data may be outdated.</span>
        </div>
      )}
      <div style={{ flex: 1, paddingBottom: '60px', overflowY: 'auto' }}>
        {activeTab === 'picks' && <PicksTab key={picksResetKey} onNavigate={navigateTo} />}
        {activeTab === 'insights' && <InsightsTab onNavigate={navigateTo} initialInsight={initialInsight} onInitialInsightConsumed={() => setInitialInsight(null)} />}
        {activeTab === 'performance' && <PerformanceTab onNavigate={navigateTo} initialView={perfView} onViewConsumed={() => setPerfView(null)} />}
        {activeTab === 'profile' && <ProfileTab initialScreen={profileScreen} onScreenChange={setProfileScreen} pickToTrack={pickToTrack} onPickTracked={() => setPickToTrack(null)} screenData={profileScreenData} />}
      </div>
      <ScrollToTopButton />
      <TabNav activeTab={activeTab} onTabChange={(tab) => {
        if (tab === activeTab && tab === 'picks') {
          setPicksResetKey(k => k + 1);
        }
        setActiveTab(tab);
      }} />
      {onboardingOverlay}
      {authModalOpen && (
        <AuthModal
          onClose={() => setAuthModalOpen(false)}
          initialMode={authModalMode}
          initialAccountType="trial"
        />
      )}
    </div>
  );
}

function ScrollToTopButton() {
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    const onScroll = () => setVisible(window.scrollY > 300);
    window.addEventListener('scroll', onScroll, { passive: true });
    return () => window.removeEventListener('scroll', onScroll);
  }, []);

  if (!visible) return null;

  return (
    <button
      onClick={() => window.scrollTo({ top: 0, behavior: 'smooth' })}
      aria-label="Scroll to top"
      style={{
        position: 'fixed',
        bottom: 'calc(20px + 60px + env(safe-area-inset-bottom, 0px))',
        right: '20px',
        width: '44px', height: '44px',
        borderRadius: '50%',
        backgroundColor: 'var(--surface-1)',
        border: '1px solid var(--stroke-subtle)',
        boxShadow: '0 4px 16px rgba(0,0,0,0.4)',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        cursor: 'pointer',
        zIndex: 90,
        transition: 'opacity 0.2s',
      }}
    >
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="var(--text-secondary)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <polyline points="18 15 12 9 6 15"/>
      </svg>
    </button>
  );
}

export default function SharpPicksApp() {
  return (
    <AuthProvider>
      <SportProvider>
        <AppContent />
      </SportProvider>
    </AuthProvider>
  );
}
