import { useState, useEffect } from 'react';
import { useAuth } from '../../hooks/useAuth';
import { useApi } from '../../hooks/useApi';
import PickCard from './PickCard';
import NoPickCard from './NoPickCard';
import AuthModal from './AuthModal';

export default function TodayTab() {
  const { user, loading: authLoading } = useAuth();
  const { data: todayData, loading, error } = useApi('/picks/today');
  const { data: stats } = useApi('/public/stats');
  const [showAuth, setShowAuth] = useState(false);

  if (loading || authLoading) {
    return <LoadingState />;
  }

  const isPro = user && (user.is_premium || user.subscription_status === 'active' || user.subscription_status === 'trial');

  return (
    <div style={{ padding: '0' }}>
      <Header stats={stats} user={user} onAuthClick={() => setShowAuth(true)} />

      <div style={{ padding: '0 20px' }}>
        {todayData?.type === 'pick' && (
          <PickCard pick={todayData} isPro={isPro} onUpgrade={() => setShowAuth(true)} />
        )}

        {todayData?.type === 'pass' && (
          <NoPickCard data={todayData} />
        )}

        {todayData?.type === 'waiting' && (
          <WaitingCard />
        )}

        {!todayData && !error && (
          <DailyBrief stats={stats} />
        )}

        {stats && <RecordStrip stats={stats} />}
      </div>

      {showAuth && <AuthModal onClose={() => setShowAuth(false)} />}
    </div>
  );
}

function Header({ stats, user, onAuthClick }) {
  const { logout } = useAuth();

  return (
    <div style={{
      padding: '20px 20px 16px',
      display: 'flex',
      justifyContent: 'space-between',
      alignItems: 'center',
    }}>
      <div>
        <h1 style={{
          fontFamily: 'var(--font-serif)',
          fontSize: '22px',
          fontWeight: 600,
          color: 'var(--text-primary)',
          letterSpacing: '-0.02em',
        }}>
          Sharp Picks
        </h1>
        <p style={{
          fontFamily: 'var(--font-mono)',
          fontSize: '12px',
          color: 'var(--text-tertiary)',
          marginTop: '2px',
        }}>
          {stats ? `${stats.record} record` : 'Loading...'}
        </p>
      </div>
      {user ? (
        <button
          onClick={logout}
          style={{
            background: 'none',
            border: '1px solid var(--stroke-muted)',
            borderRadius: '8px',
            color: 'var(--text-secondary)',
            padding: '8px 14px',
            fontSize: '13px',
            cursor: 'pointer',
            fontFamily: 'var(--font-sans)',
          }}
        >
          Sign Out
        </button>
      ) : (
        <button
          onClick={onAuthClick}
          style={{
            background: 'none',
            border: '1px solid var(--stroke-muted)',
            borderRadius: '8px',
            color: 'var(--text-primary)',
            padding: '8px 14px',
            fontSize: '13px',
            cursor: 'pointer',
            fontFamily: 'var(--font-sans)',
          }}
        >
          Sign In
        </button>
      )}
    </div>
  );
}

function LoadingState() {
  return (
    <div style={{
      minHeight: '100vh',
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'center',
      gap: '16px',
    }}>
      <div style={{
        width: '40px',
        height: '40px',
        borderRadius: '50%',
        border: '3px solid var(--stroke-subtle)',
        borderTopColor: 'var(--blue-primary)',
        animation: 'spin 1s linear infinite',
      }} />
      <p style={{
        fontFamily: 'var(--font-sans)',
        fontSize: '14px',
        color: 'var(--text-secondary)',
      }}>
        Checking model output...
      </p>
      <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
    </div>
  );
}

function WaitingCard() {
  return (
    <div style={{
      backgroundColor: 'var(--surface-1)',
      borderRadius: '16px',
      padding: '32px 24px',
      textAlign: 'center',
      border: '1px solid var(--stroke-subtle)',
      marginTop: '8px',
    }}>
      <div style={{
        width: '48px',
        height: '48px',
        borderRadius: '12px',
        backgroundColor: 'var(--surface-2)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        margin: '0 auto 16px',
      }}>
        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="var(--text-tertiary)" strokeWidth="2">
          <circle cx="12" cy="12" r="10"/>
          <polyline points="12 6 12 12 16 14"/>
        </svg>
      </div>
      <h2 style={{
        fontFamily: 'var(--font-serif)',
        fontSize: '20px',
        fontWeight: 600,
        color: 'var(--text-primary)',
        marginBottom: '8px',
      }}>
        Waiting for model
      </h2>
      <p style={{
        fontSize: '14px',
        color: 'var(--text-secondary)',
        lineHeight: '1.6',
      }}>
        The model has not run yet today. Games will be analyzed as data becomes available.
      </p>
    </div>
  );
}

function DailyBrief({ stats }) {
  return (
    <div style={{
      backgroundColor: 'var(--surface-1)',
      borderRadius: '16px',
      padding: '32px 24px',
      textAlign: 'center',
      border: '1px solid var(--stroke-subtle)',
      marginTop: '8px',
    }}>
      <div style={{
        width: '48px',
        height: '48px',
        borderRadius: '12px',
        backgroundColor: 'var(--surface-2)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        margin: '0 auto 16px',
      }}>
        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="var(--blue-primary)" strokeWidth="2">
          <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>
        </svg>
      </div>
      <h2 style={{
        fontFamily: 'var(--font-serif)',
        fontSize: '20px',
        fontWeight: 600,
        color: 'var(--text-primary)',
        marginBottom: '8px',
      }}>
        Standing by
      </h2>
      <p style={{
        fontSize: '14px',
        color: 'var(--text-secondary)',
        lineHeight: '1.6',
        maxWidth: '300px',
        margin: '0 auto',
      }}>
        The model is waiting for today's game data. When games are available, it will analyze all matchups and publish a pick only if the edge exceeds the threshold.
      </p>
      {stats && (
        <div style={{
          marginTop: '24px',
          display: 'flex',
          justifyContent: 'center',
          gap: '24px',
        }}>
          <Stat label="Record" value={stats.record || '0-0'} />
          <Stat label="Win Rate" value={stats.win_rate ? `${stats.win_rate}%` : '--'} />
          <Stat label="Passes" value={stats.capital_preserved_days || 0} />
        </div>
      )}
    </div>
  );
}

function Stat({ label, value }) {
  return (
    <div>
      <div style={{
        fontFamily: 'var(--font-mono)',
        fontSize: '18px',
        fontWeight: 600,
        color: 'var(--text-primary)',
      }}>
        {value}
      </div>
      <div style={{
        fontSize: '11px',
        color: 'var(--text-tertiary)',
        marginTop: '2px',
        textTransform: 'uppercase',
        letterSpacing: '0.05em',
      }}>
        {label}
      </div>
    </div>
  );
}

function RecordStrip({ stats }) {
  return (
    <div style={{
      backgroundColor: 'var(--surface-1)',
      borderRadius: '12px',
      padding: '16px 20px',
      marginTop: '16px',
      border: '1px solid var(--stroke-subtle)',
      display: 'flex',
      justifyContent: 'space-between',
      alignItems: 'center',
    }}>
      <div style={{ display: 'flex', gap: '20px' }}>
        <MiniStat label="Picks" value={stats.total_picks} />
        <MiniStat label="Passes" value={stats.total_passes} />
        <MiniStat label="Select." value={`${stats.selectivity}%`} />
      </div>
      <div style={{
        fontFamily: 'var(--font-mono)',
        fontSize: '13px',
        color: stats.pnl >= 0 ? 'var(--green-profit)' : 'var(--red-loss)',
      }}>
        {stats.pnl >= 0 ? '+' : ''}{stats.pnl}u
      </div>
    </div>
  );
}

function MiniStat({ label, value }) {
  return (
    <div>
      <div style={{
        fontFamily: 'var(--font-mono)',
        fontSize: '14px',
        fontWeight: 600,
        color: 'var(--text-primary)',
      }}>
        {value}
      </div>
      <div style={{
        fontSize: '10px',
        color: 'var(--text-tertiary)',
        textTransform: 'uppercase',
        letterSpacing: '0.05em',
      }}>
        {label}
      </div>
    </div>
  );
}
