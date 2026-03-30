import { useState, useEffect } from 'react';
import { apiGet } from '../../hooks/useApi';

export default function WeeklySummary({ onBack, stats, weekData: initialWeekData }) {
  const [weekData, setWeekData] = useState(initialWeekData || null);
  const [loading, setLoading] = useState(!initialWeekData);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!initialWeekData) {
      setLoading(true);
      setError(null);
      apiGet('/picks/weekly-summary')
        .then(data => {
          if (data.error) {
            setError(data.error);
          } else {
            setWeekData(data);
          }
        })
        .catch(() => setError('Unable to load weekly summary'))
        .finally(() => setLoading(false));
    }
  }, [initialWeekData]);

  if (loading) {
    return (
      <div style={{ padding: '0', paddingBottom: '100px' }}>
        <div style={{
          padding: '16px 20px',
          display: 'flex', alignItems: 'center', gap: '12px',
        }}>
          <button onClick={onBack} style={{
            background: 'none', border: 'none', cursor: 'pointer',
            color: 'var(--text-secondary)', padding: '4px',
          }}>
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M19 12H5M12 19l-7-7 7-7"/>
            </svg>
          </button>
          <span style={{
            fontFamily: 'var(--font-sans)', fontSize: '16px', fontWeight: 600,
            color: 'var(--text-primary)',
          }}>Weekly Summary</span>
        </div>
        <div style={{ display: 'flex', justifyContent: 'center', padding: '60px 0' }}>
          <div style={{
            width: '32px', height: '32px', borderRadius: '50%',
            border: '3px solid var(--stroke-subtle)',
            borderTopColor: 'var(--blue-primary)',
            animation: 'spin 1s linear infinite',
          }} />
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div style={{ padding: '0', paddingBottom: '100px' }}>
        <div style={{
          padding: '16px 20px',
          display: 'flex', alignItems: 'center', gap: '12px',
        }}>
          <button onClick={onBack} style={{
            background: 'none', border: 'none', cursor: 'pointer',
            color: 'var(--text-secondary)', padding: '4px',
          }}>
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M19 12H5M12 19l-7-7 7-7"/>
            </svg>
          </button>
          <span style={{
            fontFamily: 'var(--font-sans)', fontSize: '16px', fontWeight: 600,
            color: 'var(--text-primary)',
          }}>Weekly Summary</span>
        </div>
        <div style={{ padding: '40px 20px', textAlign: 'center' }}>
          <p style={{ fontSize: '15px', color: 'var(--text-secondary)', marginBottom: '8px' }}>
            {error === 'Pro subscription required'
              ? 'Weekly summaries are available for Pro subscribers.'
              : 'Unable to load the weekly summary right now.'}
          </p>
          <p style={{ fontSize: '13px', color: 'var(--text-tertiary)' }}>
            {error === 'Pro subscription required'
              ? 'Upgrade to access full weekly performance breakdowns.'
              : 'Please try again later.'}
          </p>
        </div>
      </div>
    );
  }

  const record = weekData?.record || stats?.record || '0-0';
  const [wins, losses] = record.split('-').map(Number);
  const totalPicks = (wins || 0) + (losses || 0);
  const passDays = weekData?.passes || 7 - totalPicks;
  const gamesScanned = weekData?.games_scanned || (7 * 12);
  const selectivity = gamesScanned > 0 ? Math.round((totalPicks / gamesScanned) * 100) : 0;
  const pnl = weekData?.pnl || 0;

  return (
    <div style={{ padding: '0', paddingBottom: '100px' }}>
      <div style={{
        padding: '16px 20px',
        display: 'flex', alignItems: 'center', gap: '12px',
      }}>
        <button onClick={onBack} style={{
          background: 'none', border: 'none', cursor: 'pointer',
          color: 'var(--text-secondary)', padding: '4px',
        }}>
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M19 12H5M12 19l-7-7 7-7"/>
          </svg>
        </button>
        <span style={{
          fontFamily: 'var(--font-sans)', fontSize: '16px', fontWeight: 600,
          color: 'var(--text-primary)',
        }}>Weekly Summary</span>
      </div>

      <div style={{ padding: '0 20px' }}>
        <div style={{
          fontFamily: 'var(--font-mono)', fontSize: '10px', fontWeight: 600,
          letterSpacing: '2px', textTransform: 'uppercase',
          color: 'var(--text-tertiary)', marginBottom: '10px',
        }}>Week in Review</div>

        <div style={{
          backgroundColor: 'var(--surface-1)', borderRadius: '20px',
          border: '1px solid var(--stroke-subtle)', padding: '24px',
          marginBottom: '16px', textAlign: 'center',
        }}>
          <div style={{
            fontFamily: 'var(--font-mono)', fontSize: '48px', fontWeight: 800,
            color: pnl >= 0 ? 'var(--green-profit)' : 'var(--red-loss)',
            lineHeight: '1', marginBottom: '8px',
          }}>
            {pnl >= 0 ? '+' : ''}{pnl}u
          </div>
          <div style={{
            fontFamily: 'var(--font-mono)', fontSize: '13px',
            color: 'var(--text-secondary)',
          }}>
            {record} record this week
          </div>
        </div>

        <div style={{
          display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '12px',
          marginBottom: '16px',
        }}>
          <StatCard value={totalPicks} label="Picks" />
          <StatCard value={passDays} label="Passes" />
          <StatCard value={`${selectivity}%`} label="Selectivity" />
        </div>

        <div style={{
          backgroundColor: 'var(--surface-1)', borderRadius: '16px',
          border: '1px solid var(--stroke-subtle)', padding: '20px',
          marginBottom: '16px',
        }}>
          <div style={{
            fontFamily: 'var(--font-mono)', fontSize: '10px', fontWeight: 600,
            letterSpacing: '2px', textTransform: 'uppercase',
            color: 'var(--text-tertiary)', marginBottom: '12px',
          }}>Daily Log</div>

          {['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'].map((day, i) => {
            const dayData = weekData?.days?.[i];
            const type = dayData?.type || (i < 5 ? 'pass' : 'no_games');
            return (
              <div key={day} style={{
                display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                padding: '10px 0',
                borderBottom: i < 6 ? '1px solid var(--stroke-subtle)' : 'none',
              }}>
                <span style={{
                  fontFamily: 'var(--font-mono)', fontSize: '13px',
                  color: 'var(--text-secondary)', width: '40px',
                }}>{day}</span>
                <span style={{
                  fontSize: '13px',
                  color: type === 'pick' ? 'var(--text-primary)'
                    : type === 'pass' ? 'var(--text-tertiary)'
                    : 'var(--text-tertiary)',
                  fontWeight: type === 'pick' ? 600 : 400,
                  flex: 1, textAlign: 'center',
                }}>
                  {type === 'pick' ? dayData?.summary || 'Pick published'
                    : type === 'pass' ? 'No qualifying edge'
                    : type === 'upcoming' ? 'Upcoming'
                    : 'No games'}
                </span>
                {type === 'pick' && dayData?.result && (
                  <span style={{
                    fontFamily: 'var(--font-mono)', fontSize: '12px', fontWeight: 600,
                    color: dayData.result === 'win' ? 'var(--green-profit)' : 'var(--red-loss)',
                  }}>
                    {dayData.result === 'win' ? 'W' : dayData.result === 'push' ? 'P' : 'L'}
                  </span>
                )}
              </div>
            );
          })}
        </div>

        <WeeklyNarrative wins={wins} losses={losses} passDays={passDays} pnl={pnl} selectivity={selectivity} days={weekData?.days} />

        <p style={{
          fontSize: '11px', color: 'var(--text-tertiary)', lineHeight: '1.5',
          textAlign: 'center', padding: '8px 0 16px',
        }}>
          Past performance does not guarantee future results.
        </p>
      </div>
    </div>
  );
}

function WeeklyNarrative({ wins, losses, passDays, pnl, selectivity, days }) {
  const totalPicks = (wins || 0) + (losses || 0);
  const winStreak = [];
  const lossStreak = [];
  let currentW = 0, currentL = 0;
  (days || []).forEach(d => {
    if (d?.result === 'win') { currentW++; currentL = 0; }
    else if (d?.result === 'loss') { currentL++; currentW = 0; }
    winStreak.push(currentW);
    lossStreak.push(currentL);
  });
  const maxWinStreak = Math.max(0, ...winStreak);
  const maxLossStreak = Math.max(0, ...lossStreak);

  const paragraphs = [];

  if (totalPicks === 0) {
    paragraphs.push(
      `7 slates scanned, 0 qualifying edges. ${passDays} pass days.`
    );
  } else {
    paragraphs.push(
      `${totalPicks} pick${totalPicks !== 1 ? 's' : ''} from ${totalPicks + passDays} slates. ` +
      `${passDays} pass day${passDays !== 1 ? 's' : ''}.`
    );

    if (wins > 0 && losses === 0) {
      paragraphs.push(
        `${wins}-0 week. ${pnl >= 0 ? `+${pnl.toFixed(2)}u` : `${pnl.toFixed(2)}u`}.`
      );
    } else if (losses > 0 && wins === 0) {
      paragraphs.push(
        `0-${losses} week. Variance within parameters.`
      );
    } else if (wins > 0 && losses > 0) {
      paragraphs.push(
        `${wins}-${losses}` +
        (pnl >= 0 ? `, +${pnl.toFixed(2)}u.` : `, ${pnl.toFixed(2)}u.`)
      );
    }
  }

  return (
    <div style={{
      backgroundColor: 'var(--surface-1)', borderRadius: '16px',
      border: '1px solid var(--stroke-subtle)', padding: '20px',
      marginBottom: '16px',
    }}>
      <div style={{
        fontFamily: 'var(--font-mono)', fontSize: '10px', fontWeight: 600,
        letterSpacing: '2px', textTransform: 'uppercase',
        color: 'var(--text-tertiary)', marginBottom: '14px',
      }}>Week in Narrative</div>
      {paragraphs.map((p, i) => (
        <p key={i} style={{
          fontFamily: 'var(--font-serif)', fontSize: '14px',
          color: 'var(--text-secondary)', lineHeight: '1.75',
          marginBottom: i < paragraphs.length - 1 ? '12px' : 0,
        }}>{p}</p>
      ))}
    </div>
  );
}

function StatCard({ value, label }) {
  return (
    <div style={{
      backgroundColor: 'var(--surface-1)', borderRadius: '14px',
      border: '1px solid var(--stroke-subtle)', padding: '16px',
      textAlign: 'center',
    }}>
      <div style={{
        fontFamily: 'var(--font-mono)', fontSize: '22px', fontWeight: 700,
        color: 'var(--text-primary)', marginBottom: '4px',
      }}>{value}</div>
      <div style={{
        fontSize: '10px', fontWeight: 600, color: 'var(--text-tertiary)',
        textTransform: 'uppercase', letterSpacing: '0.08em',
      }}>{label}</div>
    </div>
  );
}
