import { useState, useMemo, useEffect, useCallback } from 'react';
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

function Sparkline({ snapshots, field = 'spread', width = 48, height = 16 }) {
  if (!snapshots || snapshots.length < 2) return null;
  const values = snapshots.map(s => s[field]).filter(v => v != null);
  if (values.length < 2) return null;
  const min = Math.min(...values);
  const max = Math.max(...values);
  const range = max - min || 1;
  const points = values.map((v, i) => {
    const x = (i / (values.length - 1)) * width;
    const y = height - ((v - min) / range) * (height - 2) - 1;
    return `${x},${y}`;
  }).join(' ');
  const lastVal = values[values.length - 1];
  const firstVal = values[0];
  const color = lastVal < firstVal ? 'var(--green-profit, #10b981)' : lastVal > firstVal ? 'var(--red-loss, #ef4444)' : 'var(--text-tertiary)';
  return (
    <svg width={width} height={height} style={{ display: 'block' }}>
      <polyline points={points} fill="none" stroke={color} strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function RLMBadge({ rlm }) {
  if (!rlm) return null;
  return (
    <span style={{
      fontSize: '0.55rem', fontWeight: 700, letterSpacing: '0.06em',
      padding: '1px 5px', borderRadius: 3,
      background: 'rgba(251,191,36,0.12)', color: '#f59e0b',
      border: '1px solid rgba(251,191,36,0.25)',
    }}>RLM</span>
  );
}

function EdgeBar({ value, max = 15 }) {
  if (value == null) return null;
  const pct = Math.min(Math.abs(value) / max * 100, 100);
  const color = value >= 5 ? 'var(--green-profit, #10b981)' : value >= 2 ? '#f59e0b' : 'var(--text-tertiary)';
  return (
    <div style={{ width: '100%', height: 4, borderRadius: 2, background: 'rgba(255,255,255,0.06)', marginTop: 4 }}>
      <div style={{ width: `${pct}%`, height: '100%', borderRadius: 2, background: color, transition: 'width 0.3s ease' }} />
    </div>
  );
}

function StatCell({ label, value, color, sub }) {
  return (
    <div>
      <div style={{ fontSize: '0.55rem', color: 'var(--text-tertiary)', marginBottom: 2, letterSpacing: '0.03em' }}>{label}</div>
      <div style={{
        fontFamily: 'var(--font-mono)', fontSize: '0.82rem', fontWeight: 600,
        color: color || 'var(--text-primary)',
      }}>{value}</div>
      {sub && <div style={{ fontSize: '0.5rem', color: 'var(--text-tertiary)', marginTop: 1, opacity: 0.7 }}>{sub}</div>}
    </div>
  );
}

function ModelAnalysisPanel({ model }) {
  if (!model) return null;
  const edgeColor = model.edge >= 5 ? 'var(--green-profit, #10b981)' : model.edge >= 2 ? '#f59e0b' : 'var(--text-tertiary)';
  const probPct = model.cover_prob != null ? (model.cover_prob * 100).toFixed(1) : null;
  const impliedFromLine = model.line != null ? (model.line <= 0 ? 52.4 : 47.6) : null;

  return (
    <div style={{
      borderTop: '1px solid var(--stroke-subtle)',
      padding: '10px 14px 14px',
      background: 'rgba(79,125,243,0.03)',
    }}>
      {/* Header */}
      <div style={{
        display: 'flex', alignItems: 'center', gap: 6, marginBottom: 10,
      }}>
        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="rgba(79,125,243,0.6)" strokeWidth="2">
          <circle cx="12" cy="12" r="10"/><path d="M12 16v-4M12 8h.01"/>
        </svg>
        <span style={{
          fontFamily: 'var(--font-mono)', fontSize: '0.6rem', fontWeight: 700,
          letterSpacing: '0.08em', textTransform: 'uppercase',
          color: 'var(--text-tertiary)',
        }}>Model Analysis</span>
        {model.rating && (
          <span style={{
            fontFamily: 'var(--font-mono)', fontSize: '0.62rem', fontWeight: 700,
            padding: '1px 6px', borderRadius: 3,
            background: model.passes ? 'rgba(52,211,153,0.1)' : 'rgba(100,116,139,0.08)',
            color: model.passes ? 'var(--green-profit, #10b981)' : 'var(--text-tertiary)',
            border: `1px solid ${model.passes ? 'rgba(52,211,153,0.2)' : 'var(--stroke-subtle)'}`,
            marginLeft: 'auto',
          }}>{model.rating}</span>
        )}
      </div>

      {/* Primary stats row */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 10, marginBottom: 10 }}>
        {model.edge != null && (
          <div>
            <StatCell label="Adj. Edge" value={`${model.edge > 0 ? '+' : ''}${model.edge}%`} color={edgeColor} />
            <EdgeBar value={model.edge} />
          </div>
        )}
        {probPct && (
          <StatCell
            label="Cover Prob"
            value={`${probPct}%`}
            sub={impliedFromLine ? `vs ${impliedFromLine.toFixed(1)}% implied` : null}
          />
        )}
        {model.predicted_margin != null && (
          <StatCell
            label="Proj. Margin"
            value={`${model.predicted_margin > 0 ? '+' : ''}${model.predicted_margin}`}
            color={model.predicted_margin > 0 ? 'var(--green-profit, #10b981)' : model.predicted_margin < 0 ? 'var(--red-loss, #ef4444)' : 'var(--text-primary)'}
          />
        )}
      </div>

      {/* Secondary stats row */}
      {(model.raw_edge != null || model.line != null) && (
        <div style={{
          display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 10,
          marginBottom: 10, paddingTop: 8,
          borderTop: '1px solid rgba(255,255,255,0.04)',
        }}>
          {model.raw_edge != null && (
            <StatCell
              label="Raw Edge"
              value={`${model.raw_edge > 0 ? '+' : ''}${model.raw_edge}%`}
              sub={model.edge != null && model.raw_edge !== model.edge ? `${(model.edge - model.raw_edge) > 0 ? '+' : ''}${(model.edge - model.raw_edge).toFixed(1)} adj` : null}
            />
          )}
          {model.line != null && (
            <StatCell label="Pick Line" value={fmtSpread(model.line)} />
          )}
          {probPct && impliedFromLine && (
            <StatCell
              label="Prob. Edge"
              value={`+${(parseFloat(probPct) - impliedFromLine).toFixed(1)}pp`}
              color={parseFloat(probPct) > impliedFromLine ? 'var(--green-profit, #10b981)' : 'var(--text-tertiary)'}
            />
          )}
        </div>
      )}

      {/* Pick recommendation */}
      {model.pick && (
        <div style={{
          padding: '7px 10px', borderRadius: 6,
          background: model.passes ? 'rgba(52,211,153,0.06)' : 'rgba(255,255,255,0.02)',
          border: `1px solid ${model.passes ? 'rgba(52,211,153,0.2)' : 'var(--stroke-subtle)'}`,
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
            <span style={{
              fontFamily: 'var(--font-mono)', fontSize: '0.75rem', fontWeight: 700,
              color: model.passes ? 'var(--green-profit, #10b981)' : 'var(--text-secondary)',
            }}>{model.pick}</span>
            {model.passes && (
              <span style={{
                fontSize: '0.55rem', fontWeight: 700, color: 'var(--green-profit, #10b981)',
                marginLeft: 'auto', letterSpacing: '0.06em',
                display: 'flex', alignItems: 'center', gap: 3,
              }}>
                <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round">
                  <polyline points="20 6 9 17 4 12"/>
                </svg>
                QUALIFIES
              </span>
            )}
            {!model.passes && (
              <span style={{
                fontSize: '0.55rem', fontWeight: 600, color: 'var(--text-tertiary)',
                marginLeft: 'auto', letterSpacing: '0.04em',
              }}>NO ACTION</span>
            )}
          </div>
          {!model.passes && model.fail_reasons?.length > 0 && (
            <div style={{ marginTop: 5, display: 'flex', flexDirection: 'column', gap: 2 }}>
              {model.fail_reasons.map((r, i) => (
                <div key={i} style={{
                  fontSize: '0.58rem', color: 'var(--text-tertiary)', opacity: 0.8,
                  display: 'flex', alignItems: 'center', gap: 4,
                }}>
                  <span style={{ color: 'var(--red-loss, #ef4444)', fontSize: '0.5rem' }}>✕</span>
                  {r}
                </div>
              ))}
            </div>
          )}
          {!model.passes && model.reason && !model.fail_reasons?.length && (
            <div style={{ fontSize: '0.58rem', color: 'var(--text-tertiary)', marginTop: 4, opacity: 0.8 }}>
              {model.reason}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function ConsensusBar({ consensus, current }) {
  if (consensus == null || current == null) return null;
  const diff = current - consensus;
  if (Math.abs(diff) < 0.3) return null;
  const label = diff > 0
    ? `Market ${Math.abs(diff).toFixed(1)} off consensus`
    : `Market ${Math.abs(diff).toFixed(1)} off consensus`;
  return (
    <div style={{
      display: 'flex', alignItems: 'center', gap: 5,
      padding: '3px 8px', marginTop: 4,
    }}>
      <span style={{
        fontFamily: 'var(--font-mono)', fontSize: '0.55rem',
        color: 'var(--text-tertiary)', opacity: 0.7,
      }}>Consensus {fmtSpread(consensus)}</span>
      {Math.abs(diff) >= 1.0 && (
        <span style={{
          fontSize: '0.5rem', fontWeight: 700, padding: '1px 4px',
          borderRadius: 2, background: 'rgba(251,191,36,0.1)',
          color: '#f59e0b', letterSpacing: '0.05em',
        }}>OFF</span>
      )}
    </div>
  );
}

function WatchButton({ watching, onWatch }) {
  return (
    <button
      onClick={(e) => { e.stopPropagation(); onWatch(); }}
      style={{
        background: 'none', border: 'none', cursor: 'pointer',
        padding: '4px', display: 'flex', alignItems: 'center',
        opacity: watching ? 1 : 0.4,
      }}
      aria-label={watching ? 'Unwatch game' : 'Watch game'}
    >
      <svg width="14" height="14" viewBox="0 0 24 24" fill={watching ? 'var(--blue-primary)' : 'none'}
        stroke={watching ? 'var(--blue-primary)' : 'currentColor'} strokeWidth="2">
        <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/>
        <circle cx="12" cy="12" r="3"/>
      </svg>
    </button>
  );
}

function GameRow({ game, expanded, onToggle, watching, onWatch }) {
  const totalDisplay = fmtTotal(game.total);
  const isFinal = game.status === 'final';
  const isLive = game.status === 'live';
  const showScores = isLive || isFinal;
  const hasModel = !!game.model;

  const awayWinning = showScores && game.away_score > game.home_score;
  const homeWinning = showScores && game.home_score > game.away_score;

  return (
    <div style={{
      background: 'var(--surface-1, #111827)',
      border: `1px solid ${isLive ? 'rgba(239,68,68,0.2)' : expanded ? 'rgba(79,125,243,0.25)' : 'var(--stroke-subtle, #1e293b)'}`,
      borderRadius: 10,
      overflow: 'hidden',
      transition: 'border-color 0.15s ease',
    }}>
      <div
        onClick={onToggle}
        style={{ cursor: hasModel ? 'pointer' : 'default' }}
      >
        {/* Column headers */}
        <div style={{
          display: 'grid', gridTemplateColumns: showScores ? '1fr 48px 72px 56px 64px' : '1fr 72px 56px 64px',
          padding: '6px 14px 2px', gap: 6,
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 5 }}>
            {isLive && <LiveBadge state={game.live_state} period={game.live_period} clock={game.live_clock} />}
            {isFinal && <LiveBadge state="STATUS_FINAL" />}
            {!isLive && !isFinal && <RLMBadge rlm={game.rlm} />}
            {!isLive && !isFinal && game.snapshots?.length >= 2 && (
              <Sparkline snapshots={game.snapshots} field="spread" />
            )}
            {onWatch && <WatchButton watching={watching} onWatch={onWatch} />}
          </div>
          {showScores && (
            <span style={{
              fontFamily: 'var(--font-mono)', fontSize: '0.6rem', fontWeight: 700,
              letterSpacing: '0.08em', textTransform: 'uppercase',
              color: 'var(--text-tertiary)', textAlign: 'center', opacity: 0.6,
            }}>Score</span>
          )}
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
          display: 'grid', gridTemplateColumns: showScores ? '1fr 48px 72px 56px 64px' : '1fr 72px 56px 64px',
          padding: '5px 14px', alignItems: 'center', gap: 6,
        }}>
          <div style={{ display: 'flex', alignItems: 'baseline', gap: 6, minWidth: 0 }}>
            <span style={{
              fontFamily: 'var(--font-mono)', fontSize: '0.85rem', fontWeight: 700,
              color: awayWinning ? 'var(--text-primary)' : showScores ? 'var(--text-secondary)' : 'var(--text-primary)',
              overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
            }}>{game.away}</span>
            {game.away_record && !showScores && (
              <span style={{ fontSize: '0.6rem', color: 'var(--text-tertiary)', flexShrink: 0 }}>{game.away_record}</span>
            )}
          </div>
          {showScores && (
            <div style={{
              textAlign: 'center', fontFamily: 'var(--font-mono)', fontSize: '0.9rem',
              fontWeight: awayWinning ? 700 : 500,
              color: awayWinning ? '#fff' : 'var(--text-secondary)',
            }}>{game.away_score}</div>
          )}
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
          display: 'grid', gridTemplateColumns: showScores ? '1fr 48px 72px 56px 64px' : '1fr 72px 56px 64px',
          padding: '5px 14px 8px', alignItems: 'center', gap: 6,
        }}>
          <div style={{ display: 'flex', alignItems: 'baseline', gap: 6, minWidth: 0 }}>
            <span style={{
              fontFamily: 'var(--font-mono)', fontSize: '0.85rem', fontWeight: 700,
              color: homeWinning ? 'var(--text-primary)' : showScores ? 'var(--text-secondary)' : 'var(--text-primary)',
              overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
            }}>{game.home}</span>
            {game.home_record && !showScores && (
              <span style={{ fontSize: '0.6rem', color: 'var(--text-tertiary)', flexShrink: 0 }}>{game.home_record}</span>
            )}
          </div>
          {showScores && (
            <div style={{
              textAlign: 'center', fontFamily: 'var(--font-mono)', fontSize: '0.9rem',
              fontWeight: homeWinning ? 700 : 500,
              color: homeWinning ? '#fff' : 'var(--text-secondary)',
            }}>{game.home_score}</div>
          )}
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

        {/* Consensus bar */}
        <ConsensusBar consensus={game.consensus_spread} current={game.spread_home} />

        {/* Model edge + expand hint */}
        {hasModel && !expanded && (
          <div style={{
            padding: '4px 14px 6px', display: 'flex', alignItems: 'center',
            justifyContent: 'center', gap: 8,
          }}>
            {game.model.edge != null && (
              <span style={{
                fontFamily: 'var(--font-mono)', fontSize: '0.65rem', fontWeight: 700,
                padding: '1px 7px', borderRadius: 4,
                background: game.model.edge >= 5 ? 'rgba(52,211,153,0.1)' : game.model.edge >= 2 ? 'rgba(251,191,36,0.1)' : 'rgba(100,116,139,0.08)',
                color: game.model.edge >= 5 ? 'var(--green-profit, #10b981)' : game.model.edge >= 2 ? '#f59e0b' : 'var(--text-tertiary)',
                border: `1px solid ${game.model.edge >= 5 ? 'rgba(52,211,153,0.2)' : game.model.edge >= 2 ? 'rgba(251,191,36,0.2)' : 'var(--stroke-subtle)'}`,
              }}>
                {game.model.edge > 0 ? '+' : ''}{game.model.edge}% edge
              </span>
            )}
            <span style={{ fontSize: '0.55rem', color: 'rgba(79,125,243,0.5)' }}>Tap for model view</span>
            <svg width="8" height="8" viewBox="0 0 24 24" fill="none" stroke="rgba(79,125,243,0.4)" strokeWidth="2">
              <polyline points="6 9 12 15 18 9"/>
            </svg>
          </div>
        )}
      </div>

      {/* Expanded model analysis */}
      {expanded && <ModelAnalysisPanel model={game.model} />}
    </div>
  );
}

function TimeSlotGroup({ time, games, expandedId, onToggle, watchedIds, onWatch }) {
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
        {games.map(g => (
          <GameRow
            key={g.id}
            game={g}
            expanded={expandedId === g.id}
            onToggle={() => onToggle(g.id)}
            watching={watchedIds?.has(g.id)}
            onWatch={() => onWatch(g)}
          />
        ))}
      </div>
    </div>
  );
}

function FilterTabs({ active, onChange, hasLive }) {
  const tabs = hasLive ? ['All', 'Live', 'Upcoming', 'Final'] : ['All', 'Upcoming', 'Final'];
  return (
    <div style={{ display: 'flex', gap: 6 }}>
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

const SORT_OPTIONS = [
  { key: 'time', label: 'Time' },
  { key: 'spread', label: 'Spread' },
  { key: 'total', label: 'Total' },
  { key: 'edge', label: 'Edge' },
];

function SortPicker({ active, onChange }) {
  return (
    <div style={{ display: 'flex', gap: 4 }}>
      {SORT_OPTIONS.map(opt => {
        const isActive = active === opt.key;
        return (
          <button key={opt.key} onClick={() => onChange(opt.key)} style={{
            fontFamily: 'var(--font-mono)', fontSize: '0.62rem', fontWeight: 600,
            padding: '4px 8px', borderRadius: 4, cursor: 'pointer',
            border: 'none',
            background: isActive ? 'rgba(255,255,255,0.08)' : 'transparent',
            color: isActive ? 'var(--text-primary)' : 'var(--text-tertiary)',
            opacity: isActive ? 1 : 0.6,
          }}>{opt.label}</button>
        );
      })}
    </div>
  );
}

function sortGames(games, sortKey) {
  const sorted = [...games];
  switch (sortKey) {
    case 'spread':
      return sorted.sort((a, b) => Math.abs(a.spread_home || 0) - Math.abs(b.spread_home || 0));
    case 'total':
      return sorted.sort((a, b) => (b.total || 0) - (a.total || 0));
    case 'edge':
      return sorted.sort((a, b) => (b.model?.edge || -99) - (a.model?.edge || -99));
    default:
      return sorted;
  }
}

function normalizeTeam(name) {
  if (!name) return '';
  return name.toLowerCase().replace(/[^a-z]/g, '');
}

function LiveBadge({ state, period, clock }) {
  if (state === 'STATUS_FINAL') {
    return (
      <span style={{
        fontSize: '0.55rem', fontWeight: 700, letterSpacing: '0.06em',
        padding: '1px 5px', borderRadius: 3,
        background: 'rgba(100,116,139,0.15)', color: 'var(--text-tertiary)',
      }}>FINAL</span>
    );
  }
  if (state === 'STATUS_IN_PROGRESS') {
    const qLabel = period <= 4 ? `Q${period}` : `OT${period - 4}`;
    return (
      <span style={{
        fontSize: '0.55rem', fontWeight: 700, letterSpacing: '0.06em',
        padding: '1px 5px', borderRadius: 3,
        background: 'rgba(239,68,68,0.12)', color: '#ef4444',
        display: 'inline-flex', alignItems: 'center', gap: 3,
      }}>
        <span style={{
          width: 4, height: 4, borderRadius: '50%',
          background: '#ef4444', animation: 'pulse 2s infinite',
        }} />
        {qLabel} {clock}
      </span>
    );
  }
  if (state === 'STATUS_HALFTIME') {
    return (
      <span style={{
        fontSize: '0.55rem', fontWeight: 700, letterSpacing: '0.06em',
        padding: '1px 5px', borderRadius: 3,
        background: 'rgba(251,191,36,0.12)', color: '#f59e0b',
      }}>HALF</span>
    );
  }
  return null;
}

export default function MarketView({ onBack }) {
  const { sport } = useSport();
  const { data, loading } = useApi(sportQuery('/picks/market', sport));
  const { data: watchedData } = useApi('/picks/watched');
  const [filter, setFilter] = useState('All');
  const [sort, setSort] = useState('time');
  const [autoSorted, setAutoSorted] = useState(false);
  const [expandedId, setExpandedId] = useState(null);
  const [liveScores, setLiveScores] = useState({});
  const [watchedIds, setWatchedIds] = useState(new Set());

  useEffect(() => {
    if (watchedData?.game_ids) setWatchedIds(new Set(watchedData.game_ids));
  }, [watchedData]);

  useEffect(() => {
    if (!autoSorted && !loading && rawGames.length > 0 && rawGames.some(g => g.model)) {
      setSort('edge');
      setAutoSorted(true);
    }
  }, [loading, rawGames, autoSorted]);

  const fetchLiveScores = useCallback(async () => {
    try {
      const resp = await fetch(`/api/picks/live-scores?sport=${sport}`);
      const json = await resp.json();
      if (json.scores) {
        const map = {};
        json.scores.forEach(s => {
          const key = normalizeTeam(s.home);
          map[key] = s;
        });
        setLiveScores(map);
      }
    } catch { /* silent */ }
  }, [sport]);

  useEffect(() => {
    fetchLiveScores();
    const interval = setInterval(fetchLiveScores, 30000);
    return () => clearInterval(interval);
  }, [fetchLiveScores]);

  const rawGames = data?.games || [];

  const games = useMemo(() => {
    if (Object.keys(liveScores).length === 0) return rawGames;
    return rawGames.map(g => {
      const key = normalizeTeam(g.home);
      const live = liveScores[key];
      if (!live) return g;
      const isLive = live.state === 'STATUS_IN_PROGRESS' || live.state === 'STATUS_HALFTIME';
      const isFinal = live.state === 'STATUS_FINAL';
      if (!isLive && !isFinal) return g;
      return {
        ...g,
        home_score: live.home_score,
        away_score: live.away_score,
        status: isFinal ? 'final' : 'live',
        live_clock: live.clock,
        live_period: live.period,
        live_state: live.state,
      };
    });
  }, [rawGames, liveScores]);

  const hasLive = games.some(g => g.status === 'live');

  const filtered = useMemo(() => {
    if (filter === 'All') return games;
    if (filter === 'Live') return games.filter(g => g.status === 'live');
    if (filter === 'Upcoming') return games.filter(g => g.status === 'scheduled');
    if (filter === 'Final') return games.filter(g => g.status === 'final');
    return games;
  }, [games, filter]);

  const sorted = useMemo(() => sortGames(filtered, sort), [filtered, sort]);

  const grouped = useMemo(() => {
    if (sort !== 'time') return null;
    const map = new Map();
    sorted.forEach(g => {
      const t = g.time || 'TBD';
      if (!map.has(t)) map.set(t, []);
      map.get(t).push(g);
    });
    return map;
  }, [sorted, sort]);

  const handleToggle = (id) => {
    setExpandedId(prev => prev === id ? null : id);
  };

  const handleWatch = async (game) => {
    try {
      const resp = await fetch('/api/picks/watch', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({
          game_id: game.id,
          game_date: data?.date,
          home: game.home,
          away: game.away,
          spread_home: game.spread_home,
        }),
      });
      const result = await resp.json();
      setWatchedIds(prev => {
        const next = new Set(prev);
        if (result.watching) next.add(game.id);
        else next.delete(game.id);
        return next;
      });
    } catch { /* silent */ }
  };

  const hasModelData = games.some(g => g.model);

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
          {hasModelData && (
            <>
              <span style={{ fontSize: '0.72rem', color: 'var(--text-tertiary)' }}>&middot;</span>
              <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.65rem', color: 'rgba(79,125,243,0.6)' }}>
                Model analyzed
              </span>
            </>
          )}
        </div>
      </div>

      {/* Body */}
      <div style={{ padding: '14px 12px 100px' }}>
        {games.length > 0 && (
          <div style={{
            display: 'flex', justifyContent: 'space-between', alignItems: 'center',
            marginBottom: 18, gap: 8,
          }}>
            <FilterTabs active={filter} onChange={setFilter} hasLive={hasLive} />
            <SortPicker active={sort} onChange={setSort} />
          </div>
        )}

        {loading ? (
          <div style={{ textAlign: 'center', padding: '60px 0', color: 'var(--text-tertiary)', fontSize: '0.85rem' }}>
            Loading market data...
          </div>
        ) : sorted.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '60px 20px', color: 'var(--text-tertiary)', fontSize: '0.85rem' }}>
            {games.length === 0 ? 'No games on today\'s slate.' : `No ${filter.toLowerCase()} games.`}
          </div>
        ) : grouped ? (
          Array.from(grouped.entries()).map(([time, gamesInSlot]) => (
            <TimeSlotGroup
              key={time}
              time={time}
              games={gamesInSlot}
              expandedId={expandedId}
              onToggle={handleToggle}
              watchedIds={watchedIds}
              onWatch={handleWatch}
            />
          ))
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
            {sorted.map(g => (
              <GameRow
                key={g.id}
                game={g}
                expanded={expandedId === g.id}
                onToggle={() => handleToggle(g.id)}
                watching={watchedIds.has(g.id)}
                onWatch={() => handleWatch(g)}
              />
            ))}
          </div>
        )}

        <p style={{
          fontSize: '0.6rem', color: 'var(--text-tertiary)', opacity: 0.45,
          textAlign: 'center', marginTop: 20, lineHeight: 1.5,
        }}>
          Lines from DraftKings, FanDuel, BetMGM, Caesars, PointsBet, BetRivers.
          Best available shown. {hasModelData ? 'Tap any game for model analysis.' : ''}
        </p>
      </div>
    </div>
  );
}
