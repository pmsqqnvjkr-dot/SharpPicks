import { useState, useEffect } from 'react';
import { AuthProvider, useAuth } from '../hooks/useAuth';
import TabNav from '../components/sharp/TabNav';
import AppHeader from '../components/sharp/AppHeader';
import PicksTab from '../components/sharp/PicksTab';
import InsightsTab from '../components/sharp/InsightsTab';
import PerformanceTab from '../components/sharp/PerformanceTab';
import ProfileTab from '../components/sharp/ProfileTab';
import LandingPage from '../components/sharp/LandingPage';
import OnboardingFlow from '../components/sharp/OnboardingFlow';

function AppContent() {
  const { user, loading } = useAuth();
  const [activeTab, setActiveTab] = useState('picks');
  const [showOnboarding, setShowOnboarding] = useState(false);
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
      <AppContent />
    </AuthProvider>
  );
}
