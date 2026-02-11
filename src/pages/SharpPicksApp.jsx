import { useState } from 'react';
import { AuthProvider } from '../hooks/useAuth';
import TabNav from '../components/sharp/TabNav';
import TodayTab from '../components/sharp/TodayTab';
import DashboardTab from '../components/sharp/DashboardTab';
import ProfileTab from '../components/sharp/ProfileTab';

export default function SharpPicksApp() {
  const [activeTab, setActiveTab] = useState('today');

  return (
    <AuthProvider>
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
          {activeTab === 'today' && <TodayTab />}
          {activeTab === 'dashboard' && <DashboardTab />}
          {activeTab === 'profile' && <ProfileTab />}
        </div>
        <TabNav activeTab={activeTab} onTabChange={setActiveTab} />
      </div>
    </AuthProvider>
  );
}
