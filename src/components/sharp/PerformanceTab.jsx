import { useState } from 'react';
import { useAuth } from '../../hooks/useAuth';
import UnifiedDashboard from './UnifiedDashboard';
import DashboardTab from './DashboardTab';
import FreeTierDashboard from './FreeTierDashboard';

export default function PerformanceTab({ onNavigate }) {
  const { user } = useAuth();
  const [view, setView] = useState('yours');
  const isPro = user && (user.is_premium || user.subscription_status === 'active' || user.subscription_status === 'trial');

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
              Performance
            </p>
            <p style={{ color: 'var(--text-secondary)', fontSize: '14px', lineHeight: '1.6', margin: 0 }}>
              Sign in to track your results and see model performance.
            </p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div style={{ padding: '0', paddingBottom: '100px' }}>
      <PerfHeader />

      <div style={{ padding: '0 20px', marginBottom: '16px' }}>
        <div style={{
          display: 'flex',
          backgroundColor: 'var(--surface-1)',
          borderRadius: '10px',
          padding: '3px',
          border: '1px solid var(--stroke-subtle)',
        }}>
          <ToggleButton
            active={view === 'yours'}
            onClick={() => setView('yours')}
            label="Your Results"
          />
          <ToggleButton
            active={view === 'model'}
            onClick={() => setView('model')}
            label="Model"
          />
        </div>
      </div>

      {view === 'yours' ? (
        isPro ? (
          <UnifiedDashboard embedded />
        ) : (
          <FreeTierDashboard onUpgrade={() => onNavigate && onNavigate('profile', 'upgrade')} />
        )
      ) : (
        <DashboardTab onNavigate={onNavigate} embedded />
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

function ToggleButton({ active, onClick, label }) {
  return (
    <button onClick={onClick} style={{
      flex: 1,
      padding: '8px 0',
      fontSize: '13px',
      fontWeight: 600,
      fontFamily: 'var(--font-sans)',
      border: 'none',
      borderRadius: '8px',
      cursor: 'pointer',
      backgroundColor: active ? 'var(--blue-primary)' : 'transparent',
      color: active ? '#fff' : 'var(--text-tertiary)',
      transition: 'all 0.2s',
    }}>
      {label}
    </button>
  );
}
