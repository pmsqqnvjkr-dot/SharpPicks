import { useState, useEffect } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { AuthProvider, useAuth } from '../hooks/useAuth';
import { SportProvider } from '../hooks/useSport';
import TabNav from '../components/sharp/TabNav';
import AppHeader from '../components/sharp/AppHeader';
import PicksTab from '../components/sharp/PicksTab';
import InsightsTab from '../components/sharp/InsightsTab';
import PerformanceTab from '../components/sharp/PerformanceTab';
import ProfileTab from '../components/sharp/ProfileTab';
import LandingPage from '../components/sharp/LandingPage';
import OnboardingFlow from '../components/sharp/OnboardingFlow';

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
        alt="Sharp Picks"
        style={{
          width: '160px', height: '160px', borderRadius: '28px',
          marginBottom: '32px',
        }}
      />
      <h1 style={{
        fontFamily: 'var(--font-serif)', fontSize: '28px', fontWeight: 600,
        color: 'var(--text-primary)', marginBottom: '12px',
      }}>Welcome to Sharp Picks Pro</h1>
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

function AppContent() {
  const { user, loading, checkAuth } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState('picks');
  const [showOnboarding, setShowOnboarding] = useState(false);
  const [showWelcome, setShowWelcome] = useState(false);
  const [profileScreen, setProfileScreen] = useState(null);
  const [profileScreenData, setProfileScreenData] = useState(null);
  const [pickToTrack, setPickToTrack] = useState(null);
  const [perfView, setPerfView] = useState(null);

  const [initialInsight, setInitialInsight] = useState(null);

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
    if (user) {
      const onboarded = localStorage.getItem('sp_onboarded');
      if (!onboarded && user.is_new) {
        setShowOnboarding(true);
      }
    }
  }, [user]);

  useEffect(() => {
    const handlePushNav = (e) => {
      const data = e.detail || {};
      if (data.type === 'weekly_summary') {
        setActiveTab('profile');
        setProfileScreen('weekly');
      } else if (data.type === 'pick' || data.type === 'result' || data.type === 'revoke') {
        setActiveTab('picks');
      } else if (data.type === 'pass') {
        setActiveTab('picks');
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
    }

    return () => {
      window.removeEventListener('sp-push-navigate', handlePushNav);
      navigator.serviceWorker?.removeEventListener('message', handleSWMessage);
    };
  }, []);

  const handleOnboardingComplete = () => {
    setShowOnboarding(false);
    localStorage.setItem('sp_onboarded', '1');
  };

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

  if (!user) {
    return <LandingPage />;
  }

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
        <button
          onClick={async () => {
            try {
              await fetch('/api/auth/resend-verification', { method: 'POST', credentials: 'include' });
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
            await fetch('/api/auth/logout', { method: 'POST', credentials: 'include' });
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

  if (showWelcome) {
    return <WelcomeScreen onContinue={() => {
      setShowWelcome(false);
      navigate('/', { replace: true });
    }} />;
  }

  if (showOnboarding) {
    return <OnboardingFlow onComplete={handleOnboardingComplete} />;
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
      <AppHeader onNavigate={(tab) => setActiveTab(tab)} />
      <div style={{ flex: 1, paddingBottom: '60px', overflowY: 'auto' }}>
        {activeTab === 'picks' && <PicksTab onNavigate={navigateTo} />}
        {activeTab === 'insights' && <InsightsTab onNavigate={navigateTo} initialInsight={initialInsight} onInitialInsightConsumed={() => setInitialInsight(null)} />}
        {activeTab === 'performance' && <PerformanceTab onNavigate={navigateTo} initialView={perfView} onViewConsumed={() => setPerfView(null)} />}
        {activeTab === 'profile' && <ProfileTab initialScreen={profileScreen} onScreenChange={setProfileScreen} pickToTrack={pickToTrack} onPickTracked={() => setPickToTrack(null)} screenData={profileScreenData} />}
      </div>
      <TabNav activeTab={activeTab} onTabChange={setActiveTab} />
    </div>
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
