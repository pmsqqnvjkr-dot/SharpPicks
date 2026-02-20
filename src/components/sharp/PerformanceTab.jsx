import { useState, useEffect } from 'react';
import { useAuth } from '../../hooks/useAuth';
import UnifiedDashboard from './UnifiedDashboard';
import DashboardTab from './DashboardTab';
import FreeTierDashboard from './FreeTierDashboard';

export default function PerformanceTab({ onNavigate, initialView, onViewConsumed }) {
  const { user } = useAuth();
  const isPro = user && (user.is_premium || user.subscription_status === 'active' || user.subscription_status === 'trial' || user.founding_member);
  const [view, setView] = useState(initialView || (isPro ? 'yours' : 'model'));

  useEffect(() => {
    if (initialView) {
      setView(initialView);
      if (onViewConsumed) onViewConsumed();
    }
  }, [initialView]);

  if (!isPro) {
    return (
      <div style={{ padding: '0', paddingBottom: '100px' }}>
        <FreeTierDashboard onUpgrade={() => onNavigate && onNavigate('profile', 'upgrade')} />
      </div>
    );
  }

  return (
    <div style={{ padding: '0', paddingBottom: '100px' }}>

      <div style={{ padding: '0 20px', marginTop: '12px', marginBottom: '16px' }}>
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
        <UnifiedDashboard embedded />
      ) : (
        <DashboardTab onNavigate={onNavigate} embedded />
      )}
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
