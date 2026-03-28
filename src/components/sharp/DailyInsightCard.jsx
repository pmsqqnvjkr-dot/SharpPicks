import { useState, useEffect } from 'react';
import { apiGet } from '../../hooks/useApi';
import { useSport, sportQuery } from '../../hooks/useSport';

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
        if (minsUntil < 60) setText(`${minsUntil}m`);
        else if (minsUntil < 1440) setText(`${Math.floor(minsUntil / 60)}h ${minsUntil % 60}m`);
        else setText(`${Math.floor(minsUntil / 1440)}d`);
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

function MatchupRow({ away, home, time }) {
  return (
    <div style={{
      display: 'flex', alignItems: 'center', justifyContent: 'space-between',
      padding: '10px 14px',
    }}>
      <div style={{ flex: 1, minWidth: 0 }}>
        <span style={{
          fontSize: '13px', fontWeight: 600,
          color: 'var(--text-primary)',
        }}>{away}</span>
        <span style={{
          fontSize: '12px', color: 'var(--text-tertiary)', margin: '0 6px',
        }}>@</span>
        <span style={{
          fontSize: '13px', fontWeight: 600,
          color: 'var(--text-primary)',
        }}>{home}</span>
      </div>
      {time && (
        <span style={{
          fontFamily: 'var(--font-mono)', fontSize: '11px', color: 'var(--text-tertiary)',
          whiteSpace: 'nowrap', flexShrink: 0, marginLeft: '8px',
        }}>{time}</span>
      )}
    </div>
  );
}

export default function DailyInsightCard({ data, onNavigate }) {
  const { sport } = useSport();
  const [insight, setInsight] = useState(null);
  const countdown = useCountdownTo(10);
  const gamesScheduled = data?.games_scheduled ?? 0;
  const gamesPreview = data?.games_preview ?? [];
  const modelRunsAt = data?.model_runs_at ?? '10:00 AM ET';

  const todayFormatted = new Date().toLocaleDateString('en-US', {
    weekday: 'long', month: 'long', day: 'numeric', timeZone: 'America/New_York',
  });

  useEffect(() => {
    apiGet(sportQuery('/insights?limit=20', sport)).then((res) => {
      const list = res?.insights || [];
      if (list.length) setInsight(list[Math.floor(Math.random() * list.length)]);
    }).catch(() => {});
  }, [sport]);

  return (
    <div style={{ padding: '0 4px 24px' }}>
      {/* Countdown banner */}
      <div style={{
        textAlign: 'center', padding: '20px 16px 24px',
      }}>
        <div style={{
          fontFamily: 'var(--font-mono)', fontSize: 'var(--text-label-size)', fontWeight: 700,
          letterSpacing: '0.08em', textTransform: 'uppercase',
          color: 'var(--text-tertiary)', marginBottom: 'var(--space-sm)',
        }}>Market intelligence in {countdown ? countdown : 'soon'}</div>
        <h2 style={{
          fontFamily: 'var(--font-sans)', fontSize: '22px', fontWeight: 700,
          color: 'var(--text-primary)', marginBottom: '4px',
        }}>Today&apos;s Slate</h2>
        <p style={{
          fontSize: '13px', color: 'var(--text-secondary)', lineHeight: '1.5',
          marginBottom: '2px',
        }}>{todayFormatted}</p>
        <p style={{
          fontSize: '12px', color: 'var(--text-tertiary)', lineHeight: '1.5',
        }}>
          {gamesScheduled > 0
            ? `${gamesScheduled} game${gamesScheduled === 1 ? '' : 's'} · Model runs at ${modelRunsAt}`
            : 'Loading schedule\u2026'}
        </p>
      </div>

      {/* Games list */}
      {gamesPreview.length > 0 && (
        <div style={{
          background: 'var(--surface-1)', border: '1px solid var(--color-border)',
          borderRadius: '14px', overflow: 'hidden', marginBottom: '20px',
        }}>
          {gamesPreview.map((g, i) => (
            <div key={`${g.away}-${g.home}`}>
              {i > 0 && <div style={{ height: '1px', background: 'var(--color-border)', margin: '0 14px' }} />}
              <MatchupRow away={g.away} home={g.home} time={g.time} />
            </div>
          ))}
        </div>
      )}

      {/* Recommended read */}
      {insight && (
        <div style={{ marginBottom: '24px' }}>
          <div style={{
            fontFamily: 'var(--font-mono)', fontSize: '9px', fontWeight: 700,
            letterSpacing: '2px', textTransform: 'uppercase',
            color: 'var(--text-tertiary)', marginBottom: '10px',
          }}>Recommended read</div>
          <button
            onClick={() => onNavigate && onNavigate('insights', null, { insight })}
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
                {insight.excerpt.slice(0, 120)}{insight.excerpt.length > 120 ? '\u2026' : ''}
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
