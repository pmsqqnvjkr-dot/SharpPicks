import { useState, useEffect } from 'react';
import { apiGet } from '../../hooks/useApi';

const CATEGORY_LABELS = { philosophy: 'Philosophy', discipline: 'Discipline', market_notes: 'Market Notes', how_it_works: 'How It Works', founder_note: 'Founder Notes' };

const TEAM_SHORT = {
  'Atlanta Hawks': 'ATL', 'Boston Celtics': 'BOS', 'Brooklyn Nets': 'BKN',
  'Charlotte Hornets': 'CHA', 'Chicago Bulls': 'CHI', 'Cleveland Cavaliers': 'CLE',
  'Dallas Mavericks': 'DAL', 'Denver Nuggets': 'DEN', 'Detroit Pistons': 'DET',
  'Golden State Warriors': 'GSW', 'Houston Rockets': 'HOU', 'Indiana Pacers': 'IND',
  'Los Angeles Clippers': 'LAC', 'Los Angeles Lakers': 'LAL', 'Memphis Grizzlies': 'MEM',
  'Miami Heat': 'MIA', 'Milwaukee Bucks': 'MIL', 'Minnesota Timberwolves': 'MIN',
  'New Orleans Pelicans': 'NOP', 'New York Knicks': 'NYK', 'Oklahoma City Thunder': 'OKC',
  'Orlando Magic': 'ORL', 'Philadelphia 76ers': 'PHI', 'Phoenix Suns': 'PHX',
  'Portland Trail Blazers': 'POR', 'Sacramento Kings': 'SAC', 'San Antonio Spurs': 'SAS',
  'Toronto Raptors': 'TOR', 'Utah Jazz': 'UTA', 'Washington Wizards': 'WAS',
};
const abbr = (name) => TEAM_SHORT[name] || name;

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
      padding: '8px 12px',
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flex: 1, minWidth: 0 }}>
        <span style={{
          fontFamily: 'var(--font-mono)', fontSize: '12px', fontWeight: 600,
          color: 'var(--text-primary)', width: '34px', textAlign: 'right',
          letterSpacing: '0.02em',
        }}>{abbr(away)}</span>
        <span style={{
          fontSize: '10px', color: 'var(--text-tertiary)', fontWeight: 500,
          letterSpacing: '0.05em',
        }}>@</span>
        <span style={{
          fontFamily: 'var(--font-mono)', fontSize: '12px', fontWeight: 600,
          color: 'var(--text-primary)', width: '34px',
          letterSpacing: '0.02em',
        }}>{abbr(home)}</span>
      </div>
      {time && (
        <span style={{
          fontFamily: 'var(--font-mono)', fontSize: '11px', color: 'var(--text-tertiary)',
          whiteSpace: 'nowrap',
        }}>{time}</span>
      )}
    </div>
  );
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
      {/* Countdown banner */}
      <div style={{
        textAlign: 'center', padding: '20px 16px 24px',
      }}>
        <div style={{
          fontFamily: 'var(--font-mono)', fontSize: '10px', fontWeight: 600,
          letterSpacing: '1.5px', textTransform: 'uppercase',
          color: 'var(--text-tertiary)', marginBottom: '8px',
        }}>Model analysis {countdown ? countdown : 'soon'}</div>
        <h2 style={{
          fontFamily: 'var(--font-serif)', fontSize: '22px', fontWeight: 700,
          color: 'var(--text-primary)', marginBottom: '4px',
        }}>Today&apos;s Slate</h2>
        <p style={{
          fontSize: '13px', color: 'var(--text-secondary)', lineHeight: '1.5',
        }}>
          {gamesScheduled > 0
            ? `${gamesScheduled} game${gamesScheduled === 1 ? '' : 's'} · Model runs at ${modelRunsAt}`
            : 'Loading schedule\u2026'}
        </p>
      </div>

      {/* Games list */}
      {gamesPreview.length > 0 && (
        <div style={{
          background: 'var(--surface-1)', border: '1px solid var(--stroke-subtle)',
          borderRadius: '14px', overflow: 'hidden', marginBottom: '20px',
        }}>
          {gamesPreview.slice(0, 8).map((g, i) => (
            <div key={`${g.away}-${g.home}`}>
              {i > 0 && <div style={{ height: '1px', background: 'var(--stroke-subtle)', margin: '0 12px' }} />}
              <MatchupRow away={g.away} home={g.home} time={g.time} />
            </div>
          ))}
          {gamesScheduled > 8 && (
            <div style={{
              textAlign: 'center', padding: '6px 12px 10px',
              fontSize: '11px', color: 'var(--text-tertiary)',
              fontFamily: 'var(--font-mono)', letterSpacing: '0.02em',
            }}>
              +{gamesScheduled - 8} more
            </div>
          )}
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
