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
      <div style={{
        width: '80px', height: '80px', borderRadius: '20px',
        background: 'linear-gradient(135deg, var(--green-profit), #00b377)',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        marginBottom: '28px',
      }}>
        <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
          <path d="M20 6L9 17l-5-5"/>
        </svg>
      </div>
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

  const navigateTo = (tab, screen, data) => {
    setActiveTab(tab);
    if (tab === 'performance' && screen) {
      setPerfView(screen);
    } else {
      if (screen) setProfileScreen(screen);
    }
    if (data?.pickToTrack) setPickToTrack(data.pickToTrack);
    if (data?.screenData) setProfileScreenData(data.screenData);
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
  }, [location.pathname, user]);

  useEffect(() => {
    if (user) {
      const onboarded = localStorage.getItem('sp_onboarded');
      if (!onboarded && user.is_new) {
        setShowOnboarding(true);
      }
    }
  }, [user]);

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
        {activeTab === 'insights' && <InsightsTab onNavigate={navigateTo} />}
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
