import { useState, useEffect } from 'react';
import { useAuth } from '../../hooks/useAuth';
import { useApi } from '../../hooks/useApi';
import PickCard from './PickCard';
import NoPickCard from './NoPickCard';
import AuthModal from './AuthModal';
import LoadingState from './LoadingState';
import { InlineError } from './ErrorStates';

export default function TodayTab({ onNavigate }) {
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
      <Header user={user} onAuthClick={() => setShowAuth(true)} />

      <div style={{ padding: '0 20px' }}>
        {todayData?.type === 'pick' && (
          <PickCard pick={todayData} isPro={isPro} onUpgrade={() => setShowAuth(true)} onTrack={() => {
            if (onNavigate) onNavigate('profile', 'bets', {
              pickToTrack: {
                id: todayData.id,
                away_team: todayData.away_team,
                home_team: todayData.home_team,
                game_date: todayData.game_date,
                side: todayData.side,
                line: todayData.line,
                edge_pct: todayData.edge_pct,
              }
            });
          }} />
        )}

        {todayData?.type === 'pass' && (
          <NoPickCard data={todayData} />
        )}

        {todayData?.type === 'waiting' && (
          <WaitingCard />
        )}

        {error && (
          <InlineError title="Data delay" message="Unable to load today's analysis. This typically resolves within a few minutes." />
        )}

        {!todayData && !error && (
          <DailyBrief stats={stats} />
        )}

        {stats && <RecordStrip stats={stats} />}

        {stats && (
          <div style={{
            textAlign: 'center', marginTop: '8px',
            fontSize: '10px', color: 'var(--text-tertiary)',
            fontFamily: 'var(--font-mono)', letterSpacing: '0.05em',
            textTransform: 'uppercase',
          }}>Algorithm Record</div>
        )}
      </div>

      {showAuth && <AuthModal onClose={() => setShowAuth(false)} />}
    </div>
  );
}

function Header({ user, onAuthClick }) {
  return (
    <div style={{
      padding: '16px 20px',
      display: 'flex',
      justifyContent: 'space-between',
      alignItems: 'center',
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
        <svg viewBox="0 0 40 40" width="24" height="24" fill="none">
          <path d="M20 4L6 10v10c0 9.2 6 17.4 14 20 8-2.6 14-10.8 14-20V10L20 4z" stroke="white" strokeWidth="1.8" fill="none"/>
          <rect x="12" y="24" width="3" height="6" rx="1" fill="rgba(255,255,255,0.3)"/>
          <rect x="17" y="20" width="3" height="10" rx="1" fill="rgba(255,255,255,0.4)"/>
          <rect x="22" y="22" width="3" height="8" rx="1" fill="rgba(255,255,255,0.35)"/>
          <path d="M11 22L17 16L22 19L30 11" stroke="white" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"/>
          <path d="M26 11h4v4" stroke="white" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"/>
        </svg>
        <span style={{
          fontFamily: 'var(--font-sans)',
          fontSize: '13px',
          fontWeight: 700,
          color: 'var(--text-primary)',
          letterSpacing: '2px',
          textTransform: 'uppercase',
        }}>Sharp Picks</span>
      </div>
      {!user && (
        <button
          onClick={onAuthClick}
          style={{
            background: 'none', border: 'none', cursor: 'pointer',
            color: 'var(--text-tertiary)', padding: '4px',
          }}
        >
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
            <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/>
            <circle cx="12" cy="7" r="4"/>
          </svg>
        </button>
      )}
      {user && (
        <div style={{
          width: '32px', height: '32px', borderRadius: '50%',
          backgroundColor: 'var(--surface-2)', border: '1px solid var(--stroke-subtle)',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          fontSize: '13px', fontWeight: 600, color: 'var(--text-secondary)',
          fontFamily: 'var(--font-sans)',
        }}>
          {user.email ? user.email[0].toUpperCase() : 'U'}
        </div>
      )}
    </div>
  );
}

function WaitingCard() {
  return (
    <div style={{ textAlign: 'center', padding: '40px 0 24px' }}>
      <div style={{
        width: '64px', height: '64px', borderRadius: '16px',
        backgroundColor: 'var(--surface-1)', border: '1px solid var(--stroke-subtle)',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        margin: '0 auto 24px',
      }}>
        <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="var(--text-tertiary)" strokeWidth="1.5">
          <circle cx="12" cy="12" r="10"/>
          <polyline points="12 6 12 12 16 14"/>
        </svg>
      </div>
      <h2 style={{
        fontFamily: 'var(--font-sans)', fontSize: '22px', fontWeight: 700,
        color: 'var(--text-primary)', marginBottom: '12px',
      }}>Waiting for model</h2>
      <p style={{
        fontSize: '14px', color: 'var(--text-secondary)', lineHeight: '1.6',
        maxWidth: '300px', margin: '0 auto',
      }}>
        The model has not run yet today. Games will be analyzed as data becomes available.
      </p>
    </div>
  );
}

function DailyBrief({ stats }) {
  return (
    <div style={{ textAlign: 'center', padding: '40px 0 24px' }}>
      <div style={{
        width: '64px', height: '64px', borderRadius: '16px',
        backgroundColor: 'var(--surface-1)', border: '1px solid var(--stroke-subtle)',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        margin: '0 auto 24px',
      }}>
        <svg viewBox="0 0 40 40" width="36" height="36" fill="none">
          <path d="M20 4L6 10v10c0 9.2 6 17.4 14 20 8-2.6 14-10.8 14-20V10L20 4z" stroke="white" strokeWidth="1.8" fill="none"/>
          <rect x="12" y="24" width="3" height="6" rx="1" fill="rgba(255,255,255,0.3)"/>
          <rect x="17" y="20" width="3" height="10" rx="1" fill="rgba(255,255,255,0.4)"/>
          <rect x="22" y="22" width="3" height="8" rx="1" fill="rgba(255,255,255,0.35)"/>
          <path d="M11 22L17 16L22 19L30 11" stroke="white" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"/>
          <path d="M26 11h4v4" stroke="white" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"/>
        </svg>
      </div>
      <h2 style={{
        fontFamily: 'var(--font-sans)', fontSize: '22px', fontWeight: 700,
        color: 'var(--text-primary)', marginBottom: '8px',
      }}>Standing by</h2>
      <p style={{
        fontSize: '14px', color: 'var(--text-secondary)', lineHeight: '1.6',
        maxWidth: '300px', margin: '0 auto',
      }}>
        The model is waiting for today's game data. When games are available, it will analyze all matchups and publish a pick only if the edge exceeds the threshold.
      </p>
      {stats && (
        <div style={{
          marginTop: '24px', display: 'flex', justifyContent: 'center', gap: '24px',
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
        fontFamily: 'var(--font-mono)', fontSize: '18px', fontWeight: 600,
        color: 'var(--text-primary)',
      }}>{value}</div>
      <div style={{
        fontSize: '11px', color: 'var(--text-tertiary)', marginTop: '2px',
        textTransform: 'uppercase', letterSpacing: '0.05em',
      }}>{label}</div>
    </div>
  );
}

function RecordStrip({ stats }) {
  return (
    <div style={{
      backgroundColor: 'var(--surface-1)', borderRadius: '12px',
      padding: '16px 20px', marginTop: '16px',
      border: '1px solid var(--stroke-subtle)',
      display: 'flex', justifyContent: 'space-between', alignItems: 'center',
    }}>
      <div style={{ display: 'flex', gap: '20px' }}>
        <MiniStat label="Picks" value={stats.total_picks} />
        <MiniStat label="Passes" value={stats.total_passes} />
        <MiniStat label="Select." value={`${stats.selectivity}%`} />
      </div>
      <div style={{
        fontFamily: 'var(--font-mono)', fontSize: '13px',
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
        fontFamily: 'var(--font-mono)', fontSize: '14px', fontWeight: 600,
        color: 'var(--text-primary)',
      }}>{value}</div>
      <div style={{
        fontSize: '10px', color: 'var(--text-tertiary)',
        textTransform: 'uppercase', letterSpacing: '0.05em',
      }}>{label}</div>
    </div>
  );
}
