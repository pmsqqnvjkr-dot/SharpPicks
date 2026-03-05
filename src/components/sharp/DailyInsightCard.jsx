import { useState, useEffect } from 'react';
import { apiGet } from '../../hooks/useApi';

const CATEGORY_LABELS = { philosophy: 'Philosophy', discipline: 'Discipline', market_notes: 'Market Notes', how_it_works: 'How It Works', founder_note: 'Founder Notes' };

function useCountdownTo(targetHourEt = 10) {
  const [text, setText] = useState('');
  useEffect(() => {
    const update = () => {
      try {
        const parts = new Intl.DateTimeFormat('en-CA', {
          timeZone: 'America/New_York',
          hour: 'numeric', minute: 'numeric', hour12: false,
        }).formatToParts(new Date());
        const hour = parseInt(parts.find(p => p.type === 'hour')?.value || '0', 10);
        const min = parseInt(parts.find(p => p.type === 'minute')?.value || '0', 10);
        const currentMins = hour * 60 + min;
        const targetMins = targetHourEt * 60;
        let minsUntil = targetMins - currentMins;
        if (minsUntil <= 0) minsUntil += 24 * 60;
        if (minsUntil < 60) setText(`in ${minsUntil} min`);
        else if (minsUntil < 1440) setText(`in ${Math.floor(minsUntil / 60)}h ${minsUntil % 60}m`);
        else setText(`in ${Math.floor(minsUntil / 1440)}d`);
      } catch {
        setText('');
      }
    };
    update();
    const id = setInterval(update, 60000);
    return () => clearInterval(id);
  }, [targetHourEt]);
  return text;
}

export default function DailyInsightCard({ data, onNavigate }) {
  const [insight, setInsight] = useState(null);
  const countdown = useCountdownTo(10);
  const gamesScheduled = data?.games_scheduled ?? 0;
  const gamesPreview = data?.games_preview ?? [];
  const modelRunsAt = data?.model_runs_at ?? '10:00 AM ET';

  useEffect(() => {
    apiGet('/insights?limit=20').then((res) => {
      const list = res?.insights || [];
      if (list.length) setInsight(list[Math.floor(Math.random() * list.length)]);
    }).catch(() => {});
  }, []);

  return (
    <div style={{ padding: '0 4px 24px' }}>
      <div style={{ textAlign: 'center', marginBottom: '24px' }}>
        <div style={{
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          gap: '6px', margin: '0 auto 20px',
        }}>
          <div style={{ width: '4px', height: '32px', borderRadius: '2px', backgroundColor: 'var(--text-secondary)', opacity: 0.6 }} />
          <div style={{ width: '4px', height: '32px', borderRadius: '2px', backgroundColor: 'var(--text-secondary)', opacity: 0.6 }} />
        </div>
        <h2 style={{
          fontFamily: 'var(--font-serif)', fontSize: '22px', fontWeight: 700,
          color: 'var(--text-primary)', marginBottom: '12px',
        }}>Today&apos;s slate</h2>
        <p style={{
          fontSize: '15px', color: 'var(--text-secondary)', lineHeight: '1.6',
          marginBottom: '8px',
        }}>
          {gamesScheduled > 0
            ? `${gamesScheduled} game${gamesScheduled === 1 ? '' : 's'} on today's slate`
            : 'Loading today\'s schedule…'}
        </p>
        {gamesPreview.length > 0 && (
          <ul style={{
            listStyle: 'none', padding: 0, margin: '0 0 16px',
            textAlign: 'left', maxWidth: '280px', marginLeft: 'auto', marginRight: 'auto',
          }}>
            {gamesPreview.slice(0, 6).map((g, i) => (
              <li key={i} style={{
                fontSize: '13px', color: 'var(--text-tertiary)',
                padding: '4px 0', borderBottom: i < 5 ? '1px solid var(--stroke-subtle)' : 'none',
              }}>
                {g.away} @ {g.home}{g.time ? ` · ${g.time}` : ''}
              </li>
            ))}
            {gamesScheduled > 6 && (
              <li style={{ fontSize: '12px', color: 'var(--text-tertiary)', padding: '6px 0 0', fontStyle: 'italic' }}>
                +{gamesScheduled - 6} more
              </li>
            )}
          </ul>
        )}
        <p style={{
          fontSize: '14px', color: 'var(--text-secondary)', lineHeight: '1.6',
        }}>
          Model runs daily at {modelRunsAt} {countdown && `(${countdown})`}
        </p>
      </div>

      {insight && (
        <div style={{ marginBottom: '24px' }}>
          <div style={{
            fontFamily: 'var(--font-mono)', fontSize: '9px', fontWeight: 700,
            letterSpacing: '2px', textTransform: 'uppercase',
            color: 'var(--text-tertiary)', marginBottom: '10px',
          }}>Recommended read</div>
          <button
            onClick={() => onNavigate && onNavigate('insights')}
            style={{
              width: '100%', textAlign: 'left',
              background: 'var(--surface-1)', border: '1px solid var(--stroke-subtle)',
              borderRadius: '14px', padding: '16px',
              cursor: 'pointer', display: 'block',
              transition: 'transform 0.2s ease, box-shadow 0.2s ease',
            }}
            onMouseEnter={e => { e.currentTarget.style.transform = 'translateY(-1px)'; e.currentTarget.style.boxShadow = '0 4px 16px rgba(0,0,0,0.15)'; }}
            onMouseLeave={e => { e.currentTarget.style.transform = 'translateY(0)'; e.currentTarget.style.boxShadow = 'none'; }}
          >
            <span style={{
              fontFamily: 'var(--font-mono)', fontSize: '10px', fontWeight: 600,
              letterSpacing: '0.05em', textTransform: 'uppercase',
              color: 'var(--blue-primary)', backgroundColor: 'rgba(79, 134, 247, 0.1)',
              padding: '3px 8px', borderRadius: '4px', display: 'inline-block', marginBottom: '8px',
            }}>
              {CATEGORY_LABELS[insight.category] || insight.category}
            </span>
            <div style={{ fontSize: '14px', fontWeight: 600, color: 'var(--text-primary)', marginBottom: '6px' }}>
              {insight.title}
            </div>
            {insight.excerpt && (
              <p style={{ fontSize: '12px', color: 'var(--text-secondary)', lineHeight: '1.5', margin: 0 }}>
                {insight.excerpt.slice(0, 120)}{insight.excerpt.length > 120 ? '…' : ''}
              </p>
            )}
            {insight.reading_time_minutes && (
              <span style={{ fontSize: '11px', color: 'var(--text-tertiary)', marginTop: '6px', display: 'inline-block' }}>
                {insight.reading_time_minutes} min read
              </span>
            )}
          </button>
        </div>
      )}
    </div>
  );
}
