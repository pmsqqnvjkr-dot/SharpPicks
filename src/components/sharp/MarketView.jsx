import { useState, useMemo } from 'react';
import { useApi } from '../../hooks/useApi';
import { useSport, sportQuery } from '../../hooks/useSport';

function fmtSpread(val) {
  if (val == null || val === '') return '—';
  const n = parseFloat(val);
  return n > 0 ? `+${n}` : `${n}`;
}

function fmtML(val) {
  if (val == null || val === '') return '—';
  const n = parseInt(val, 10);
  return n > 0 ? `+${n}` : `${n}`;
}

function fmtTotal(val) {
  if (val == null || val === '') return null;
  const n = parseFloat(val);
  return Number.isInteger(n) ? `${n}` : n.toFixed(1);
}

function Movement({ current, open }) {
  if (current == null || open == null) return null;
  const diff = parseFloat(current) - parseFloat(open);
  if (Math.abs(diff) < 0.25) return null;
  const isUp = diff > 0;
  return (
    <span style={{
      fontSize: '0.65rem', fontWeight: 600, marginLeft: 3,
      color: isUp ? 'var(--red-loss, #ef4444)' : 'var(--green-profit, #10b981)',
    }}>
      {isUp ? '▲' : '▼'}{Math.abs(diff).toFixed(1)}
    </span>
  );
}

function GameRow({ game }) {
  const totalDisplay = fmtTotal(game.total);
  const isFinal = game.status === 'final';

  return (
    <div style={{
      background: 'var(--surface-1, #111827)',
      border: '1px solid var(--stroke-subtle, #1e293b)',
      borderRadius: 10,
      overflow: 'hidden',
    }}>
      {/* Column headers */}
      <div style={{
        display: 'grid', gridTemplateColumns: '1fr 72px 56px 64px',
        padding: '6px 14px 2px', gap: 6,
      }}>
        <span />
        {['Spread', 'Total', 'ML'].map(h => (
          <span key={h} style={{
            fontFamily: 'var(--font-mono)', fontSize: '0.6rem', fontWeight: 700,
            letterSpacing: '0.08em', textTransform: 'uppercase',
            color: 'var(--text-tertiary)', textAlign: 'center', opacity: 0.6,
          }}>{h}</span>
        ))}
      </div>

      {/* Away row */}
      <div style={{
        display: 'grid', gridTemplateColumns: '1fr 72px 56px 64px',
        padding: '5px 14px', alignItems: 'center', gap: 6,
      }}>
        <div style={{ display: 'flex', alignItems: 'baseline', gap: 6, minWidth: 0 }}>
          <span style={{
            fontFamily: 'var(--font-mono)', fontSize: '0.85rem', fontWeight: 700,
            color: 'var(--text-primary)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
          }}>{game.away}</span>
          {game.away_record && (
            <span style={{ fontSize: '0.6rem', color: 'var(--text-tertiary)', flexShrink: 0 }}>{game.away_record}</span>
          )}
          {isFinal && game.away_score != null && (
            <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.85rem', fontWeight: 700, color: 'var(--text-secondary)', flexShrink: 0 }}>{game.away_score}</span>
          )}
        </div>
        <div style={{ textAlign: 'center', fontFamily: 'var(--font-mono)', fontSize: '0.82rem', color: 'var(--text-secondary)' }}>
          {fmtSpread(game.spread_away)}
        </div>
        <div style={{ textAlign: 'center' }}>
          {totalDisplay && (
            <div style={{
              fontFamily: 'var(--font-mono)', fontSize: '0.82rem',
              color: 'var(--text-primary)', background: 'rgba(100,116,139,0.08)',
              borderRadius: 4, padding: '2px 0',
            }}>
              {totalDisplay}
              <Movement current={game.total} open={game.total_open} />
            </div>
          )}
        </div>
        <div style={{
          textAlign: 'center', fontFamily: 'var(--font-mono)', fontSize: '0.82rem',
          color: parseFloat(game.away_ml) > 0 ? '#f59e0b' : 'var(--text-secondary)',
          fontWeight: parseFloat(game.away_ml) > 0 ? 600 : 400,
        }}>
          {fmtML(game.away_ml)}
        </div>
      </div>

      <div style={{ height: 1, background: 'var(--stroke-subtle)', margin: '0 14px' }} />

      {/* Home row */}
      <div style={{
        display: 'grid', gridTemplateColumns: '1fr 72px 56px 64px',
        padding: '5px 14px 8px', alignItems: 'center', gap: 6,
      }}>
        <div style={{ display: 'flex', alignItems: 'baseline', gap: 6, minWidth: 0 }}>
          <span style={{
            fontFamily: 'var(--font-mono)', fontSize: '0.85rem', fontWeight: 700,
            color: 'var(--text-primary)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
          }}>{game.home}</span>
          {game.home_record && (
            <span style={{ fontSize: '0.6rem', color: 'var(--text-tertiary)', flexShrink: 0 }}>{game.home_record}</span>
          )}
          {isFinal && game.home_score != null && (
            <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.85rem', fontWeight: 700, color: 'var(--text-secondary)', flexShrink: 0 }}>{game.home_score}</span>
          )}
        </div>
        <div style={{ textAlign: 'center', fontFamily: 'var(--font-mono)', fontSize: '0.82rem', color: 'var(--text-primary)', fontWeight: 600 }}>
          {fmtSpread(game.spread_home)}
          <Movement current={game.spread_home} open={game.spread_home_open} />
        </div>
        <div />
        <div style={{
          textAlign: 'center', fontFamily: 'var(--font-mono)', fontSize: '0.82rem',
          color: parseFloat(game.home_ml) > 0 ? '#f59e0b' : 'var(--text-primary)', fontWeight: 600,
        }}>
          {fmtML(game.home_ml)}
        </div>
      </div>

      {/* 1H lines */}
      {(game.spread_h1_home != null || game.total_h1 != null) && (
        <div style={{
          borderTop: '1px solid var(--stroke-subtle)',
          padding: '5px 14px', display: 'flex', gap: 14, justifyContent: 'center',
        }}>
          <span style={{
            fontFamily: 'var(--font-mono)', fontSize: '0.65rem', fontWeight: 700,
            color: 'var(--text-tertiary)', opacity: 0.6, letterSpacing: '0.05em',
          }}>1H</span>
          {game.spread_h1_home != null && (
            <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
              {fmtSpread(game.spread_h1_home)}
            </span>
          )}
          {game.total_h1 != null && (
            <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
              O/U {fmtTotal(game.total_h1)}
            </span>
          )}
        </div>
      )}
    </div>
  );
}

function TimeSlotGroup({ time, games }) {
  return (
    <div style={{ marginBottom: 18 }}>
      <div style={{
        display: 'flex', alignItems: 'center', gap: 10,
        marginBottom: 8, padding: '0 2px',
      }}>
        <span style={{
          fontFamily: 'var(--font-mono)', fontSize: '0.72rem', fontWeight: 600,
          color: 'var(--text-secondary)', letterSpacing: '0.04em',
        }}>{time}</span>
        <div style={{ flex: 1, height: 1, background: 'var(--stroke-subtle)' }} />
        <span style={{ fontSize: '0.62rem', color: 'var(--text-tertiary)' }}>
          {games.length} {games.length === 1 ? 'game' : 'games'}
        </span>
      </div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
        {games.map(g => <GameRow key={g.id} game={g} />)}
      </div>
    </div>
  );
}

function FilterTabs({ active, onChange }) {
  const tabs = ['All', 'Upcoming', 'Final'];
  return (
    <div style={{ display: 'flex', gap: 6, marginBottom: 18 }}>
      {tabs.map(tab => {
        const isActive = active === tab;
        return (
          <button key={tab} onClick={() => onChange(tab)} style={{
            fontFamily: 'var(--font-mono)', fontSize: '0.72rem', fontWeight: 600,
            padding: '6px 14px', borderRadius: 6, cursor: 'pointer',
            letterSpacing: '0.03em', transition: 'all 0.15s ease',
            border: isActive ? '1px solid rgba(79,125,243,0.45)' : '1px solid var(--stroke-subtle)',
            background: isActive ? 'rgba(79,125,243,0.12)' : 'transparent',
            color: isActive ? '#fff' : 'var(--text-tertiary)',
          }}>{tab}</button>
        );
      })}
    </div>
  );
}

export default function MarketView({ onBack }) {
  const { sport } = useSport();
  const { data, loading } = useApi(sportQuery('/picks/market', sport));
  const [filter, setFilter] = useState('All');

  const games = data?.games || [];

  const filtered = useMemo(() => {
    if (filter === 'All') return games;
    if (filter === 'Upcoming') return games.filter(g => g.status === 'scheduled');
    if (filter === 'Final') return games.filter(g => g.status === 'final');
    return games;
  }, [games, filter]);

  const grouped = useMemo(() => {
    const map = new Map();
    filtered.forEach(g => {
      const t = g.time || 'TBD';
      if (!map.has(t)) map.set(t, []);
      map.get(t).push(g);
    });
    return map;
  }, [filtered]);

  return (
    <div style={{ minHeight: '100vh' }}>
      {/* Sticky header */}
      <div style={{
        position: 'sticky', top: 0, zIndex: 10,
        background: 'var(--bg-primary, #0a0e17)',
        borderBottom: '1px solid var(--stroke-subtle)',
        padding: '12px 16px',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 4 }}>
          <button onClick={onBack} style={{
            background: 'none', border: 'none', cursor: 'pointer',
            color: 'var(--text-secondary)', padding: '4px',
            display: 'flex', alignItems: 'center',
          }}>
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
              <path d="M15 18l-6-6 6-6"/>
            </svg>
          </button>
          <h1 style={{
            fontFamily: 'var(--font-serif)', fontSize: '1.1rem', fontWeight: 700,
            color: 'var(--text-primary)', margin: 0,
          }}>Market View</h1>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginLeft: 36 }}>
          <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.72rem', color: 'var(--text-tertiary)' }}>
            {data?.date || 'Today'}
          </span>
          <span style={{ fontSize: '0.72rem', color: 'var(--text-tertiary)' }}>&middot;</span>
          <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.72rem', color: 'var(--text-tertiary)' }}>
            {games.length} game{games.length !== 1 ? 's' : ''}
          </span>
        </div>
      </div>

      {/* Body */}
      <div style={{ padding: '14px 12px 100px' }}>
        {games.length > 0 && <FilterTabs active={filter} onChange={setFilter} />}

        {loading ? (
          <div style={{ textAlign: 'center', padding: '60px 0', color: 'var(--text-tertiary)', fontSize: '0.85rem' }}>
            Loading market data...
          </div>
        ) : filtered.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '60px 20px', color: 'var(--text-tertiary)', fontSize: '0.85rem' }}>
            {games.length === 0 ? 'No games on today\'s slate.' : `No ${filter.toLowerCase()} games.`}
          </div>
        ) : (
          Array.from(grouped.entries()).map(([time, gamesInSlot]) => (
            <TimeSlotGroup key={time} time={time} games={gamesInSlot} />
          ))
        )}

        <p style={{
          fontSize: '0.6rem', color: 'var(--text-tertiary)', opacity: 0.45,
          textAlign: 'center', marginTop: 20, lineHeight: 1.5,
        }}>
          Lines from DraftKings, FanDuel, BetMGM, Caesars, PointsBet, BetRivers.
          Best available shown.
        </p>
      </div>
    </div>
  );
}
