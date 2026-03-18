import { useState, useEffect } from 'react';
import { useAuth } from '../../hooks/useAuth';
import UnifiedDashboard from './UnifiedDashboard';
import DashboardTab from './DashboardTab';
import FreeTierDashboard from './FreeTierDashboard';

async function shareCard(endpoint, filename) {
  try {
    const res = await fetch(endpoint);
    const blob = await res.blob();
    const file = new File([blob], filename, { type: 'image/png' });
    if (navigator.share && navigator.canShare?.({ files: [file] })) {
      await navigator.share({ files: [file], text: 'Sharp Picks results' });
    } else {
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url; a.download = file.name; a.click();
      URL.revokeObjectURL(url);
    }
  } catch {}
}

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

      <div style={{ padding: '0 20px', marginTop: '16px', display: 'flex', gap: '10px' }}>
        <button onClick={() => shareCard('/api/cards/user-results', 'sharppicks-results.png')} style={{
          flex: 1, padding: '10px', borderRadius: '8px', fontWeight: 600, fontSize: '12px',
          fontFamily: 'var(--font-mono)', color: 'var(--text-secondary)',
          background: 'var(--surface-1)', border: '1px solid var(--stroke-subtle)', cursor: 'pointer',
        }}>Share Results Card</button>
        <button onClick={() => shareCard('/api/cards/weekly-report', 'sharppicks-weekly.png')} style={{
          flex: 1, padding: '10px', borderRadius: '8px', fontWeight: 600, fontSize: '12px',
          fontFamily: 'var(--font-mono)', color: 'var(--text-secondary)',
          background: 'var(--surface-1)', border: '1px solid var(--stroke-subtle)', cursor: 'pointer',
        }}>Share Weekly Recap</button>
      </div>
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
