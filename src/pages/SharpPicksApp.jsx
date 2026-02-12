import { useState, useEffect } from 'react';
import { AuthProvider, useAuth } from '../hooks/useAuth';
import TabNav from '../components/sharp/TabNav';
import TodayTab from '../components/sharp/TodayTab';
import DashboardTab from '../components/sharp/DashboardTab';
import ProfileTab from '../components/sharp/ProfileTab';
import LandingPage from '../components/sharp/LandingPage';

function AppContent() {
  const { user, loading } = useAuth();
  const [activeTab, setActiveTab] = useState('today');
  const [hasEnteredApp, setHasEnteredApp] = useState(false);
  const [profileScreen, setProfileScreen] = useState(null);
  const [pickToTrack, setPickToTrack] = useState(null);

  const navigateTo = (tab, screen, data) => {
    setActiveTab(tab);
    if (screen) setProfileScreen(screen);
    if (data?.pickToTrack) setPickToTrack(data.pickToTrack);
  };

  useEffect(() => {
    if (user) setHasEnteredApp(true);
  }, [user]);

  useEffect(() => {
    const visited = sessionStorage.getItem('sp_visited');
    if (visited) setHasEnteredApp(true);
  }, []);

  const handleEnterApp = () => {
    setHasEnteredApp(true);
    sessionStorage.setItem('sp_visited', '1');
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

  if (!user && !hasEnteredApp) {
    return <LandingPage onEnterApp={handleEnterApp} />;
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
      <div style={{ flex: 1, paddingBottom: '80px', overflowY: 'auto' }}>
        {activeTab === 'today' && <TodayTab onNavigate={navigateTo} />}
        {activeTab === 'dashboard' && <DashboardTab />}
        {activeTab === 'profile' && <ProfileTab initialScreen={profileScreen} onScreenChange={setProfileScreen} pickToTrack={pickToTrack} onPickTracked={() => setPickToTrack(null)} />}
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
