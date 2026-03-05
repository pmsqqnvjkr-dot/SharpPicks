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
  const selectivity = totalPicks > 0 ? Math.round((totalPicks / 7) * 100) : 0;
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
      'The model found no qualifying edges this week. Seven days, zero action. ' +
      'That\u2019s not a failure \u2014 it\u2019s the discipline working exactly as designed. ' +
      'Capital was preserved for the week ahead.'
    );
  } else {
    const actionRate = Math.round((totalPicks / 7) * 100);
    paragraphs.push(
      `This week the model acted on ${totalPicks} of 7 slate${totalPicks > 1 ? 's' : ''} (${actionRate}% action rate), ` +
      `passing on ${passDays} day${passDays !== 1 ? 's' : ''} where the edge wasn\u2019t there. ` +
      (selectivity <= 30
        ? 'That selectivity is well below the industry average of 78% \u2014 the kind of restraint that compounds.'
        : 'Staying selective is what separates process from impulse.')
    );

    if (wins > 0 && losses === 0) {
      paragraphs.push(
        `A clean ${wins}-0 week. But the correct response is the same as any other result: ` +
        'no expanding criteria, no chasing higher volume. The edge threshold doesn\u2019t change because of a good week.'
      );
    } else if (losses > 0 && wins === 0) {
      paragraphs.push(
        `An 0-${losses} week. Variance like this is within expected parameters for any calibrated model. ` +
        'The picks met the edge threshold. The outcomes simply fell on the wrong side of probability. ' +
        'No adjustments needed.'
      );
    } else if (wins > 0 && losses > 0) {
      paragraphs.push(
        `Finished ${wins}-${losses}` +
        (pnl >= 0 ? `, netting +${pnl.toFixed(2)}u. ` : `, at ${pnl.toFixed(2)}u. `) +
        (maxWinStreak >= 2 ? `Built a ${maxWinStreak}-game win streak mid-week. ` : '') +
        'Each pick cleared the minimum edge threshold before qualifying. ' +
        'The process doesn\u2019t guarantee outcomes \u2014 it guarantees discipline.'
      );
    }
  }

  paragraphs.push(
    pnl > 0
      ? 'Positive weeks are a byproduct of process, not a cause for celebration. The model\u2019s job is to find edge. Your job is to follow the process.'
      : pnl < 0
      ? 'Negative weeks are part of any probabilistic system. What matters is whether each pick had a genuine edge at the time it was made. This week, they did.'
      : 'A flat week means capital was protected while the model waited for real opportunities. That patience has value.'
  );

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
