import { useState } from 'react';
import { useApi } from '../../hooks/useApi';
import { useSport, sportQuery } from '../../hooks/useSport';

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

function fmtSpread(val) {
  if (val == null) return '—';
  const n = parseFloat(val);
  return n > 0 ? `+${n}` : `${n}`;
}

function fmtML(val) {
  if (val == null) return '—';
  const n = parseInt(val);
  return n > 0 ? `+${n}` : `${n}`;
}

function fmtTotal(val) {
  if (val == null) return '—';
  return `${parseFloat(val)}`;
}

function LineMove({ current, open }) {
  if (current == null || open == null) return null;
  const diff = parseFloat(current) - parseFloat(open);
  if (Math.abs(diff) < 0.25) return null;
  return (
    <span style={{
      fontSize: '9px', fontWeight: 600, marginLeft: '3px',
      color: diff < 0 ? 'rgba(52,211,153,0.7)' : 'rgba(239,68,68,0.6)',
    }}>
      {diff > 0 ? '\u2191' : '\u2193'}{Math.abs(diff).toFixed(1)}
    </span>
  );
}

function GameCard({ game }) {
  const isFinal = game.status === 'final';

  return (
    <div style={{
      background: 'var(--surface-1)', border: '1px solid var(--stroke-subtle)',
      borderRadius: '14px', overflow: 'hidden', marginBottom: '10px',
    }}>
      {/* Header: time + status */}
      <div style={{
        display: 'flex', justifyContent: 'space-between', alignItems: 'center',
        padding: '8px 14px',
        borderBottom: '1px solid var(--stroke-subtle)',
      }}>
        <span style={{
          fontFamily: 'var(--font-mono)', fontSize: '11px', fontWeight: 600,
          color: 'var(--text-tertiary)',
        }}>{game.time || 'TBD'}</span>
        {isFinal && (
          <span style={{
            fontFamily: 'var(--font-mono)', fontSize: '10px', fontWeight: 700,
            letterSpacing: '1px', textTransform: 'uppercase',
            color: 'var(--text-tertiary)', opacity: 0.7,
          }}>Final</span>
        )}
        {game.home_record && game.away_record && (
          <span style={{
            fontSize: '10px', color: 'var(--text-tertiary)', opacity: 0.6,
          }}>{game.away_record} vs {game.home_record}</span>
        )}
      </div>

      {/* Teams + lines grid */}
      <div style={{ padding: '0' }}>
        {/* Column headers */}
        <div style={{
          display: 'grid', gridTemplateColumns: '1fr 70px 60px 60px',
          padding: '6px 14px 2px', gap: '4px',
        }}>
          <div />
          {['Spread', 'Total', 'ML'].map(h => (
            <div key={h} style={{
              fontFamily: 'var(--font-mono)', fontSize: '9px', fontWeight: 700,
              letterSpacing: '0.8px', textTransform: 'uppercase',
              color: 'var(--text-tertiary)', opacity: 0.5, textAlign: 'center',
            }}>{h}</div>
          ))}
        </div>

        {/* Away team row */}
        <TeamRow
          team={game.away}
          spread={game.spread_away}
          ml={game.away_ml}
          score={game.away_score}
          isFinal={isFinal}
        />

        <div style={{ height: '1px', background: 'var(--stroke-subtle)', margin: '0 14px' }} />

        {/* Home team row */}
        <TeamRow
          team={game.home}
          spread={game.spread_home}
          spreadOpen={game.spread_home_open}
          total={game.total}
          totalOpen={game.total_open}
          ml={game.home_ml}
          score={game.home_score}
          isFinal={isFinal}
          isHome
        />
      </div>

      {/* 1H lines */}
      {(game.spread_h1_home != null || game.total_h1 != null) && (
        <div style={{
          borderTop: '1px solid var(--stroke-subtle)',
          padding: '6px 14px',
          display: 'flex', gap: '16px', justifyContent: 'center',
        }}>
          <span style={{
            fontFamily: 'var(--font-mono)', fontSize: '10px', fontWeight: 600,
            color: 'var(--text-tertiary)', opacity: 0.6,
          }}>1H</span>
          {game.spread_h1_home != null && (
            <span style={{ fontFamily: 'var(--font-mono)', fontSize: '11px', color: 'var(--text-secondary)' }}>
              {abbr(game.home)} {fmtSpread(game.spread_h1_home)}
            </span>
          )}
          {game.total_h1 != null && (
            <span style={{ fontFamily: 'var(--font-mono)', fontSize: '11px', color: 'var(--text-secondary)' }}>
              O/U {fmtTotal(game.total_h1)}
            </span>
          )}
        </div>
      )}
    </div>
  );
}

function TeamRow({ team, spread, spreadOpen, total, totalOpen, ml, score, isFinal, isHome }) {
  return (
    <div style={{
      display: 'grid', gridTemplateColumns: '1fr 70px 60px 60px',
      padding: '10px 14px', gap: '4px', alignItems: 'center',
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
        <span style={{
          fontFamily: 'var(--font-mono)', fontSize: '13px', fontWeight: 700,
          color: 'var(--text-primary)', letterSpacing: '0.02em',
        }}>{abbr(team)}</span>
        {isFinal && score != null && (
          <span style={{
            fontFamily: 'var(--font-mono)', fontSize: '13px', fontWeight: 700,
            color: 'var(--text-secondary)', marginLeft: '4px',
          }}>{score}</span>
        )}
      </div>

      {/* Spread cell */}
      <div style={{ textAlign: 'center' }}>
        <span style={{
          fontFamily: 'var(--font-mono)', fontSize: '13px', fontWeight: 600,
          color: spread != null ? 'var(--text-primary)' : 'var(--text-tertiary)',
        }}>{fmtSpread(spread)}</span>
        {isHome && <LineMove current={spread} open={spreadOpen} />}
      </div>

      {/* Total cell (only on home row) */}
      <div style={{ textAlign: 'center' }}>
        {isHome ? (
          <>
            <span style={{
              fontFamily: 'var(--font-mono)', fontSize: '13px', fontWeight: 600,
              color: total != null ? 'var(--text-primary)' : 'var(--text-tertiary)',
            }}>{fmtTotal(total)}</span>
            <LineMove current={total} open={totalOpen} />
          </>
        ) : (
          <span style={{ fontFamily: 'var(--font-mono)', fontSize: '13px', color: 'var(--text-tertiary)', opacity: 0.3 }}>—</span>
        )}
      </div>

      {/* ML cell */}
      <div style={{ textAlign: 'center' }}>
        <span style={{
          fontFamily: 'var(--font-mono)', fontSize: '13px', fontWeight: 600,
          color: ml != null ? (parseInt(ml) > 0 ? 'rgba(52,211,153,0.8)' : 'var(--text-primary)') : 'var(--text-tertiary)',
        }}>{fmtML(ml)}</span>
      </div>
    </div>
  );
}

export default function MarketView({ onBack }) {
  const { sport } = useSport();
  const { data, loading } = useApi(sportQuery('/picks/market', sport));
  const [filterStatus, setFilterStatus] = useState('all');

  const games = data?.games || [];
  const filtered = filterStatus === 'all'
    ? games
    : filterStatus === 'live'
    ? games.filter(g => g.status === 'final')
    : games.filter(g => g.status === 'scheduled');

  return (
    <div style={{ padding: '0', minHeight: '100vh' }}>
      <div style={{
        padding: '16px 20px', display: 'flex', alignItems: 'center', gap: '12px',
        borderBottom: '1px solid var(--stroke-subtle)',
      }}>
        <button onClick={onBack} style={{
          background: 'none', border: 'none', cursor: 'pointer',
          color: 'var(--text-secondary)', padding: '4px',
          display: 'flex', alignItems: 'center',
        }}>
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
            <path d="M15 18l-6-6 6-6"/>
          </svg>
        </button>
        <div>
          <h1 style={{
            fontFamily: 'var(--font-serif)', fontSize: '20px', fontWeight: 600,
            color: 'var(--text-primary)',
          }}>Market View</h1>
          <p style={{
            fontFamily: 'var(--font-mono)', fontSize: '11px',
            color: 'var(--text-tertiary)', marginTop: '1px',
          }}>{data?.date || 'Today'} &middot; {games.length} game{games.length !== 1 ? 's' : ''}</p>
        </div>
      </div>

      <div style={{ padding: '12px 16px 100px' }}>
        {games.length > 0 && (
          <div style={{ display: 'flex', gap: '6px', marginBottom: '14px' }}>
            {['all', 'upcoming', 'live'].map(f => (
              <button key={f} onClick={() => setFilterStatus(f)} style={{
                padding: '5px 12px', borderRadius: '8px', fontSize: '11px',
                fontWeight: 600, cursor: 'pointer', textTransform: 'capitalize',
                fontFamily: 'var(--font-sans)',
                backgroundColor: filterStatus === f ? 'rgba(79,125,243,0.18)' : 'rgba(255,255,255,0.04)',
                color: filterStatus === f ? '#FFFFFF' : 'rgba(255,255,255,0.55)',
                border: filterStatus === f ? '1px solid rgba(79,125,243,0.45)' : '1px solid transparent',
              }}>{f === 'live' ? 'Final' : f}</button>
            ))}
          </div>
        )}

        {loading ? (
          <div style={{ textAlign: 'center', padding: '60px 0', color: 'var(--text-tertiary)' }}>
            Loading market data...
          </div>
        ) : filtered.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '60px 0' }}>
            <p style={{ fontSize: '14px', color: 'var(--text-tertiary)' }}>
              {games.length === 0 ? 'No games on today\'s slate.' : 'No games match this filter.'}
            </p>
          </div>
        ) : (
          filtered.map(game => (
            <GameCard key={game.id} game={game} />
          ))
        )}

        <p style={{
          fontSize: '10px', color: 'var(--text-tertiary)', opacity: 0.5,
          textAlign: 'center', marginTop: '20px', lineHeight: '1.5',
        }}>
          Lines from DraftKings, FanDuel, BetMGM, Caesars, PointsBet, BetRivers.
          Best available odds shown.
        </p>
      </div>
    </div>
  );
}
