import { useAuth } from '../../hooks/useAuth';
import DashboardTab from './DashboardTab';
import FreeTierDashboard from './FreeTierDashboard';

export default function PerformanceTab({ onNavigate }) {
  const { user } = useAuth();
  const isPro = user && (user.is_premium || user.subscription_status === 'active' || user.subscription_status === 'trial' || user.founding_member);

  if (!user) {
    return (
      <div style={{ padding: '0', paddingBottom: '100px' }}>
        <PerfHeader />
        <div style={{ padding: '0 20px' }}>
          <div style={{
            backgroundColor: 'var(--surface-1)',
            borderRadius: '16px',
            border: '1px solid var(--stroke-subtle)',
            padding: '40px 24px',
            textAlign: 'center',
          }}>
            <div style={{
              width: '48px', height: '48px', borderRadius: '12px',
              backgroundColor: 'var(--surface-2)', margin: '0 auto 16px',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
            }}>
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="var(--text-tertiary)" strokeWidth="1.5">
                <path d="M3 3v18h18"/><path d="M7 16l4-8 4 4 5-9"/>
              </svg>
            </div>
            <p style={{ color: 'var(--text-primary)', fontSize: '16px', fontWeight: 600, fontFamily: 'var(--font-serif)', margin: '0 0 8px' }}>
              Model Performance
            </p>
            <p style={{ color: 'var(--text-secondary)', fontSize: '14px', lineHeight: '1.6', margin: 0 }}>
              Sign in to see model accuracy, calibration, and pick history.
            </p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div style={{ padding: '0', paddingBottom: '100px' }}>
      <PerfHeader />
      {isPro ? (
        <DashboardTab onNavigate={onNavigate} embedded />
      ) : (
        <FreeTierDashboard onUpgrade={() => onNavigate && onNavigate('profile', 'upgrade')} />
      )}
    </div>
  );
}

function PerfHeader() {
  return (
    <div style={{
      padding: '16px 20px 8px',
      display: 'flex',
      alignItems: 'center',
      gap: '10px',
    }}>
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="var(--text-secondary)" strokeWidth="1.5">
        <path d="M3 3v18h18"/><path d="M7 16l4-8 4 4 5-9"/>
      </svg>
      <span style={{
        fontFamily: 'var(--font-mono)',
        fontSize: '13px',
        fontWeight: 700,
        letterSpacing: '2px',
        textTransform: 'uppercase',
        color: 'var(--text-primary)',
      }}>Performance</span>
    </div>
  );
}
