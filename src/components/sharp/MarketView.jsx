import { useState, useMemo, useEffect, useCallback } from 'react';
import { Capacitor } from '@capacitor/core';
import { useAuth } from '../../hooks/useAuth';
import { useApi } from '../../hooks/useApi';
import { useSport, sportQuery } from '../../hooks/useSport';
import PullToRefresh from '../shared/PullToRefresh';
import DailyMarketReport from './DailyMarketReport';

const PROD_URL = 'https://app.sharppicks.ai';
const MV_API_BASE = Capacitor.isNativePlatform() ? PROD_URL : '';

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

function RLMBadge({ rlm, spreadOpen, spreadNow }) {
  if (!rlm) return null;
  const move = spreadOpen != null && spreadNow != null ? Math.abs(spreadNow - spreadOpen).toFixed(1) : null;
  return (
    <span style={{
      fontSize: '0.62rem', fontWeight: 700, letterSpacing: '0.06em',
      padding: '2px 6px', borderRadius: 3,
      background: 'rgba(251,191,36,0.15)', color: '#f59e0b',
      border: '1px solid rgba(251,191,36,0.30)',
      display: 'inline-flex', alignItems: 'center', gap: 3,
    }}>
      <span style={{ fontSize: '0.6rem' }}>⚡</span>RLM{move ? ` ${move}pts` : ''}
    </span>
  );
}

function edgeStrength(val) {
  if (val >= 10) return 'STRONG';
  if (val >= 7) return 'MODERATE';
  if (val >= 3.5) return 'WEAK';
  return null;
}

function edgeColor(val) {
  if (val >= 7) return 'var(--green-profit, #10b981)';
  if (val >= 3.5) return '#FBBF24';
  return 'var(--text-tertiary)';
}

function EdgeBar({ value, max = 15 }) {
  if (value == null) return null;
  const pct = Math.min(Math.abs(value) / max * 100, 100);
  const color = edgeColor(value);
  return (
    <div style={{ width: '100%', height: 6, borderRadius: 3, background: 'rgba(255,255,255,0.06)', marginTop: 5 }}>
      <div style={{ width: `${pct}%`, height: '100%', borderRadius: 3, background: color, transition: 'width 0.3s ease' }} />
    </div>
  );
}

function EdgeBadge({ model, isPro }) {
  if (!model || model.edge == null || !isPro) return null;
  const edge = model.edge;
  const strength = edgeStrength(edge);
  const color = edgeColor(edge);
  const bgAlpha = edge >= 7 ? '0.12' : edge >= 3.5 ? '0.10' : '0.06';
  const borderAlpha = edge >= 7 ? '0.25' : edge >= 3.5 ? '0.20' : '0.10';
  const pct = Math.min(edge / 15 * 100, 100);
  return (
    <div style={{
      padding: '6px 14px 8px', display: 'flex', alignItems: 'center', gap: 8,
      borderTop: '1px solid var(--stroke-subtle)',
    }}>
      <span style={{
        fontFamily: 'var(--font-mono)', fontSize: '0.72rem', fontWeight: 700,
        padding: '2px 8px', borderRadius: 4,
        background: `rgba(${edge >= 7 ? '52,211,153' : edge >= 3.5 ? '251,191,36' : '100,116,139'},${bgAlpha})`,
        color,
        border: `1px solid rgba(${edge >= 7 ? '52,211,153' : edge >= 3.5 ? '251,191,36' : '100,116,139'},${borderAlpha})`,
      }}>
        EDGE +{edge}%
      </span>
      {strength && (
        <span style={{
          fontFamily: 'var(--font-mono)', fontSize: '0.58rem', fontWeight: 700,
          letterSpacing: '0.08em', color,
        }}>{strength}</span>
      )}
      <div style={{
        flex: 1, height: 6, borderRadius: 3,
        background: 'rgba(255,255,255,0.06)', marginLeft: 4,
      }}>
        <div style={{
          width: `${pct}%`, height: '100%', borderRadius: 3,
          background: color, transition: 'width 0.3s ease',
        }} />
      </div>
    </div>
  );
}

function StatCell({ label, value, color, sub }) {
  return (
    <div>
      <div style={{ fontSize: '0.62rem', color: 'var(--text-tertiary)', marginBottom: 2, letterSpacing: '0.03em' }}>{label}</div>
      <div style={{
        fontFamily: 'var(--font-mono)', fontSize: '0.82rem', fontWeight: 600,
        color: color || 'var(--text-primary)',
      }}>{value}</div>
      {sub && <div style={{ fontSize: '0.58rem', color: 'var(--text-tertiary)', marginTop: 1 }}>{sub}</div>}
    </div>
  );
}

function ModelAnalysisPanel({ model }) {
  if (!model) return null;
  const ec = edgeColor(model.edge);
  const strength = edgeStrength(model.edge);
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
        }}>Quant Analysis</span>
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

      {/* Edge Strength Meter — prominent */}
      {model.edge != null && (
        <div style={{
          padding: '8px 10px', borderRadius: 6, marginBottom: 10,
          background: 'rgba(255,255,255,0.02)', border: '1px solid rgba(255,255,255,0.04)',
        }}>
          <div style={{
            display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6,
          }}>
            <span style={{
              fontFamily: 'var(--font-mono)', fontSize: '0.62rem', fontWeight: 700,
              letterSpacing: '0.08em', textTransform: 'uppercase',
              color: 'var(--text-tertiary)',
            }}>Edge Strength</span>
            <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
              <span style={{
                fontFamily: 'var(--font-mono)', fontSize: '0.85rem', fontWeight: 700,
                color: ec,
              }}>+{model.edge}%</span>
              {strength && (
                <span style={{
                  fontFamily: 'var(--font-mono)', fontSize: '0.6rem', fontWeight: 700,
                  letterSpacing: '0.06em', color: ec,
                }}>{strength}</span>
              )}
            </div>
          </div>
          <div style={{ width: '100%', height: 8, borderRadius: 4, background: 'rgba(255,255,255,0.06)' }}>
            <div style={{
              width: `${Math.min(model.edge / 15 * 100, 100)}%`,
              height: '100%', borderRadius: 4, background: ec,
              transition: 'width 0.3s ease',
            }} />
          </div>
        </div>
      )}

      {/* Primary stats row */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 10, marginBottom: 10 }}>
        {model.edge != null && (
          <div>
            <StatCell label="Adj. Edge" value={`${model.edge > 0 ? '+' : ''}${model.edge}%`} color={ec} />
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
                fontSize: '0.6rem', fontWeight: 700, color: 'var(--green-profit, #10b981)',
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
                fontSize: '0.6rem', fontWeight: 600, color: 'var(--text-tertiary)',
                marginLeft: 'auto', letterSpacing: '0.04em',
              }}>NO ACTION</span>
            )}
          </div>
          {!model.passes && model.fail_reasons?.length > 0 && (
            <div style={{ marginTop: 5, display: 'flex', flexDirection: 'column', gap: 2 }}>
              {model.fail_reasons.map((r, i) => (
                <div key={i} style={{
                  fontSize: '0.62rem', color: 'var(--text-secondary)',
                  display: 'flex', alignItems: 'center', gap: 4,
                }}>
                  <span style={{ color: 'var(--red-loss, #ef4444)', fontSize: '0.62rem' }}>✕</span>
                  {r}
                </div>
              ))}
            </div>
          )}
          {!model.passes && model.reason && !model.fail_reasons?.length && (
            <div style={{ fontSize: '0.62rem', color: 'var(--text-secondary)', marginTop: 4 }}>
              {model.reason}
            </div>
          )}
        </div>
      )}

      {/* Model insight signals */}
      {model.signals?.length > 0 && (
        <div style={{
          marginTop: 10, padding: '8px 10px', borderRadius: 6,
          background: 'rgba(255,255,255,0.02)',
          border: '1px solid rgba(255,255,255,0.04)',
        }}>
          <div style={{
            fontFamily: 'var(--font-mono)', fontSize: '0.62rem', fontWeight: 700,
            letterSpacing: '0.08em', textTransform: 'uppercase',
            color: 'var(--text-tertiary)', marginBottom: 6,
          }}>Quant Reasoning</div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
            {model.signals.map((s, i) => (
              <div key={i} style={{
                fontSize: '0.62rem', color: 'var(--text-secondary)',
                lineHeight: 1.45, display: 'flex', gap: 5,
              }}>
                <span style={{ color: 'rgba(79,125,243,0.5)', flexShrink: 0 }}>›</span>
                <span>{s}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function LineHistoryModal({ game, onClose }) {
  if (!game || !game.snapshots || game.snapshots.length < 2) return null;
  const spreads = game.snapshots.map(s => s.spread).filter(v => v != null);
  const times = game.snapshots.map(s => {
    if (!s.at) return '';
    try {
      const d = new Date(s.at);
      return d.toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit', timeZone: 'America/New_York' });
    } catch { return ''; }
  });
  if (spreads.length < 2) return null;

  const min = Math.min(...spreads);
  const max = Math.max(...spreads);
  const range = max - min || 0.5;
  const w = 280, h = 120, pad = 24;
  const chartW = w - pad * 2, chartH = h - pad;

  const points = spreads.map((v, i) => {
    const x = pad + (i / (spreads.length - 1)) * chartW;
    const y = pad / 2 + chartH - ((v - min) / range) * chartH;
    return { x, y, val: v };
  });

  const openVal = spreads[0];
  const currentVal = spreads[spreads.length - 1];
  const moved = currentVal !== openVal;
  const lineColor = currentVal < openVal ? 'var(--green-profit, #10b981)' : currentVal > openVal ? 'var(--red-loss, #ef4444)' : 'var(--text-tertiary)';

  return (
    <div
      onClick={onClose}
      style={{
        position: 'fixed', inset: 0, zIndex: 999,
        background: 'rgba(0,0,0,0.7)', display: 'flex',
        alignItems: 'center', justifyContent: 'center', padding: 20,
      }}
    >
      <div
        onClick={e => e.stopPropagation()}
        style={{
          background: 'var(--surface-1, #111827)',
          border: '1px solid var(--stroke-subtle)',
          borderRadius: 14, padding: 16, width: '100%', maxWidth: 340,
        }}
      >
        <div style={{
          fontFamily: 'var(--font-mono)', fontSize: '0.65rem', fontWeight: 700,
          letterSpacing: '0.08em', textTransform: 'uppercase',
          color: 'var(--text-tertiary)', marginBottom: 4,
        }}>Line History</div>
        <div style={{
          fontFamily: 'var(--font-mono)', fontSize: '0.82rem', fontWeight: 700,
          color: 'var(--text-primary)', marginBottom: 12,
        }}>{game.away} @ {game.home}</div>

        {/* Chart */}
        <svg width={w} height={h} style={{ display: 'block', margin: '0 auto' }}>
          <polyline
            points={points.map(p => `${p.x},${p.y}`).join(' ')}
            fill="none" stroke={lineColor} strokeWidth="2.5"
            strokeLinecap="round" strokeLinejoin="round"
          />
          {points.map((p, i) => (
            <circle key={i} cx={p.x} cy={p.y} r="3" fill={lineColor} />
          ))}
        </svg>

        {/* Open → Current */}
        <div style={{
          display: 'flex', justifyContent: 'space-between', alignItems: 'center',
          marginTop: 12, padding: '8px 0',
          borderTop: '1px solid var(--stroke-subtle)',
        }}>
          <div>
            <div style={{ fontFamily: 'var(--font-mono)', fontSize: '0.62rem', color: 'var(--text-tertiary)', letterSpacing: '0.06em' }}>OPEN</div>
            <div style={{ fontFamily: 'var(--font-mono)', fontSize: '0.9rem', fontWeight: 700, color: 'var(--text-secondary)' }}>
              {fmtSpread(openVal)}
            </div>
          </div>
          {moved && (
            <svg width="20" height="12" viewBox="0 0 20 12" fill="none" stroke={lineColor} strokeWidth="2" strokeLinecap="round">
              <path d="M2 6h16M14 2l4 4-4 4" />
            </svg>
          )}
          <div style={{ textAlign: 'right' }}>
            <div style={{ fontFamily: 'var(--font-mono)', fontSize: '0.62rem', color: 'var(--text-tertiary)', letterSpacing: '0.06em' }}>CURRENT</div>
            <div style={{ fontFamily: 'var(--font-mono)', fontSize: '0.9rem', fontWeight: 700, color: lineColor }}>
              {fmtSpread(currentVal)}
            </div>
          </div>
        </div>

        {/* Movement steps */}
        <div style={{ marginTop: 8, display: 'flex', flexDirection: 'column', gap: 3 }}>
          {spreads.map((v, i) => (
            <div key={i} style={{
              display: 'flex', justifyContent: 'space-between', alignItems: 'center',
              padding: '2px 4px',
              background: i === spreads.length - 1 ? 'rgba(255,255,255,0.03)' : 'transparent',
              borderRadius: 4,
            }}>
              <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.62rem', color: 'var(--text-tertiary)' }}>
                {times[i]}
              </span>
              <span style={{
                fontFamily: 'var(--font-mono)', fontSize: '0.72rem', fontWeight: 600,
                color: i === spreads.length - 1 ? lineColor : 'var(--text-secondary)',
              }}>
                {fmtSpread(v)}
              </span>
            </div>
          ))}
        </div>

        <button
          onClick={onClose}
          style={{
            width: '100%', marginTop: 12, padding: '8px',
            background: 'rgba(255,255,255,0.06)', border: '1px solid var(--stroke-subtle)',
            borderRadius: 6, color: 'var(--text-secondary)', fontFamily: 'var(--font-mono)',
            fontSize: '0.72rem', fontWeight: 600, cursor: 'pointer',
          }}
        >Close</button>
      </div>
    </div>
  );
}

function SharpMoneyIndicator({ game }) {
  if (!game.rlm) return null;
  const spreadOpen = game.spread_home_open;
  const spreadNow = game.spread_home;
  if (spreadOpen == null || spreadNow == null) return null;
  const move = Math.abs(spreadNow - spreadOpen);
  if (move < 1.0) return null;

  const sharpSide = game.rlm === 'home' ? game.home : game.away;
  const publicSide = game.rlm === 'home' ? game.away : game.home;

  return (
    <div style={{
      padding: '6px 14px 6px',
      borderTop: '1px solid rgba(251,191,36,0.1)',
      background: 'rgba(251,191,36,0.03)',
    }}>
      <div style={{
        display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4,
      }}>
        <span style={{
          fontSize: '0.62rem', fontWeight: 700, letterSpacing: '0.06em',
          color: '#f59e0b',
        }}>⚡ REVERSE LINE MOVEMENT</span>
      </div>
      <div style={{
        display: 'flex', justifyContent: 'space-between', alignItems: 'center',
      }}>
        <div>
          <div style={{
            fontFamily: 'var(--font-mono)', fontSize: '0.62rem', fontWeight: 600,
            color: 'var(--text-tertiary)', letterSpacing: '0.04em', marginBottom: 2,
          }}>PUBLIC MONEY</div>
          <div style={{
            fontFamily: 'var(--font-mono)', fontSize: '0.72rem', fontWeight: 600,
            color: 'var(--text-secondary)',
          }}>{publicSide}</div>
        </div>
        <div style={{
          fontFamily: 'var(--font-mono)', fontSize: '0.6rem',
          color: 'var(--text-tertiary)', textAlign: 'center',
        }}>
          <div>Line moved</div>
          <div style={{ color: '#f59e0b', fontWeight: 700, fontSize: '0.72rem' }}>
            {move.toFixed(1)}pts
          </div>
        </div>
        <div style={{ textAlign: 'right' }}>
          <div style={{
            fontFamily: 'var(--font-mono)', fontSize: '0.62rem', fontWeight: 600,
            color: '#f59e0b', letterSpacing: '0.04em', marginBottom: 2,
          }}>SHARP MONEY</div>
          <div style={{
            fontFamily: 'var(--font-mono)', fontSize: '0.72rem', fontWeight: 700,
            color: '#f59e0b',
          }}>{sharpSide}</div>
        </div>
      </div>
    </div>
  );
}

function ConsensusBar({ consensus, current }) {
  const [showTip, setShowTip] = useState(false);
  if (consensus == null || current == null) return null;
  const diff = current - consensus;
  if (Math.abs(diff) < 0.3) return null;
  const absDiff = Math.abs(diff).toFixed(1);
  const isSignificant = Math.abs(diff) >= 1.0;

  return (
    <div style={{
      padding: '3px 8px', marginTop: 4,
    }}>
      <div
        style={{
          display: 'flex', alignItems: 'center', gap: 5,
          cursor: isSignificant ? 'pointer' : 'default',
        }}
        onClick={isSignificant ? (e) => { e.stopPropagation(); setShowTip(!showTip); } : undefined}
      >
        <span style={{
          fontFamily: 'var(--font-mono)', fontSize: '0.62rem',
          color: 'var(--text-secondary)',
        }}>Consensus {fmtSpread(consensus)}</span>
        {isSignificant && (
          <span style={{
            fontSize: '0.58rem', fontWeight: 700, padding: '1px 6px',
            borderRadius: 3, background: 'rgba(251,191,36,0.1)',
            color: '#f59e0b', letterSpacing: '0.04em',
            border: '1px solid rgba(251,191,36,0.2)',
            display: 'inline-flex', alignItems: 'center', gap: 3,
          }}>
            {absDiff}pts off
            <svg width="8" height="8" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3">
              <circle cx="12" cy="12" r="10"/><path d="M12 16v-4M12 8h.01"/>
            </svg>
          </span>
        )}
      </div>
      {showTip && (
        <div style={{
          marginTop: 4, padding: '6px 10px',
          borderRadius: 6, background: 'var(--surface-1)',
          border: '1px solid var(--stroke-subtle)',
          fontSize: '0.68rem', lineHeight: 1.45,
          color: 'var(--text-secondary)',
        }}>
          The current line is <strong style={{ color: '#f59e0b' }}>{absDiff} points</strong> away from the
          market consensus ({fmtSpread(consensus)}). Large deviations can signal sharp action or book-specific
          positioning.
        </div>
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

function GameRow({ game, expanded, onToggle, watching, onWatch, isPro, onLineHistory }) {
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
            {!isLive && !isFinal && <RLMBadge rlm={game.rlm} spreadOpen={game.spread_home_open} spreadNow={game.spread_home} />}
            {!isLive && !isFinal && game.snapshots?.length >= 2 && (
              <span onClick={e => { e.stopPropagation(); onLineHistory?.(game); }} style={{ cursor: 'pointer' }}>
                <Sparkline snapshots={game.snapshots} field="spread" />
              </span>
            )}
            {onWatch && <WatchButton watching={watching} onWatch={onWatch} />}
            {hasModel && game.model.edge != null && !expanded && (
              <span style={{
                marginLeft: 'auto',
                fontFamily: 'var(--font-mono)', fontSize: '0.72rem', fontWeight: 700,
                color: edgeColor(game.model.edge),
                letterSpacing: '0.02em',
              }}>+{game.model.edge}%</span>
            )}
          </div>
          {showScores && (
            <span style={{
              fontFamily: 'var(--font-mono)', fontSize: '0.62rem', fontWeight: 700,
              letterSpacing: '0.08em', textTransform: 'uppercase',
              color: 'var(--text-tertiary)', textAlign: 'center',
            }}>Score</span>
          )}
          {['Spread', 'Total', 'ML'].map(h => (
            <span key={h} style={{
              fontFamily: 'var(--font-mono)', fontSize: '0.62rem', fontWeight: 700,
              letterSpacing: '0.08em', textTransform: 'uppercase',
              color: 'var(--text-tertiary)', textAlign: 'center',
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
              <span style={{ fontSize: '0.65rem', color: 'var(--text-secondary)', flexShrink: 0 }}>{game.away_record}</span>
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
            color: parseFloat(game.away_ml) > 0 ? '#FBBF24' : 'rgba(96,165,250,0.85)',
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
              <span style={{ fontSize: '0.65rem', color: 'var(--text-secondary)', flexShrink: 0 }}>{game.home_record}</span>
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
            color: parseFloat(game.home_ml) > 0 ? '#FBBF24' : 'rgba(96,165,250,0.85)', fontWeight: 600,
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
              color: 'var(--text-tertiary)', letterSpacing: '0.05em',
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

        {/* Sharp vs Public money — shown when RLM detected */}
        <SharpMoneyIndicator game={game} />

        {/* Edge badge + discipline filter — surfaced on collapsed card */}
        {hasModel && !expanded && (
          <>
            {game.model.passes ? (
              <EdgeBadge model={game.model} isPro={isPro} />
            ) : isPro && game.model.edge != null ? (
              <div style={{
                padding: '6px 14px 4px',
                borderTop: '1px solid var(--stroke-subtle)',
                display: 'flex', alignItems: 'center', justifyContent: 'space-between',
              }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                  <span style={{
                    fontFamily: 'var(--font-mono)', fontSize: '0.58rem', fontWeight: 700,
                    letterSpacing: '0.06em', color: 'var(--text-tertiary)',
                    padding: '2px 6px', borderRadius: 3,
                    background: 'rgba(100,116,139,0.08)',
                    border: '1px solid rgba(100,116,139,0.12)',
                  }}>NO ACTION</span>
                  <span style={{
                    fontFamily: 'var(--font-mono)', fontSize: '0.62rem',
                    color: 'var(--text-secondary)',
                  }}>
                    Edge +{game.model.edge}% · {game.model.fail_reasons?.[0] || 'Below threshold'}
                  </span>
                </div>
              </div>
            ) : null}
            <div style={{
              padding: '3px 14px 6px', display: 'flex', alignItems: 'center',
              justifyContent: 'center', gap: 6,
            }}>
              <span style={{ fontSize: '0.65rem', color: 'rgba(79,125,243,0.7)' }}>
                {isPro ? 'Tap for quant view' : 'Pro: quant analysis'}
              </span>
              <svg width="8" height="8" viewBox="0 0 24 24" fill="none" stroke="rgba(79,125,243,0.6)" strokeWidth="2">
                <polyline points="6 9 12 15 18 9"/>
              </svg>
            </div>
          </>
        )}
      </div>

      {/* Expanded model analysis — Pro only */}
      {expanded && isPro && <ModelAnalysisPanel model={game.model} />}
      {expanded && !isPro && (
        <div style={{
          padding: '16px', textAlign: 'center',
          borderTop: '1px solid var(--stroke-subtle)',
        }}>
          <div style={{
            fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-secondary)',
            marginBottom: '4px',
          }}>Quant analysis is a Pro feature</div>
          <div style={{
            fontSize: '0.65rem', color: 'var(--text-tertiary)',
          }}>Upgrade for edge data, cover probability, and quant reasoning</div>
        </div>
      )}
    </div>
  );
}

function TimeSlotGroup({ time, games, expandedId, onToggle, watchedIds, onWatch, isPro, onLineHistory }) {
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
            isPro={isPro}
            onLineHistory={onLineHistory}
          />
        ))}
      </div>
    </div>
  );
}

function FilterTabs({ active, onChange, hasLive, hasModel }) {
  let tabs = hasLive ? ['All', 'Live', 'Upcoming', 'Final'] : ['All', 'Upcoming', 'Final'];
  if (hasModel) tabs = [...tabs, 'Passed'];
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

function SortPicker({ active, onChange, isPro }) {
  const opts = isPro ? SORT_OPTIONS : SORT_OPTIONS.filter(o => o.key !== 'edge');
  return (
    <div style={{ display: 'flex', gap: 4 }}>
      {opts.map(opt => {
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
        fontSize: '0.62rem', fontWeight: 700, letterSpacing: '0.06em',
        padding: '1px 5px', borderRadius: 3,
        background: 'rgba(100,116,139,0.15)', color: 'var(--text-tertiary)',
      }}>FINAL</span>
    );
  }
  if (state === 'STATUS_IN_PROGRESS') {
    const qLabel = period <= 4 ? `Q${period}` : `OT${period - 4}`;
    return (
      <span style={{
        fontSize: '0.62rem', fontWeight: 700, letterSpacing: '0.06em',
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
        fontSize: '0.62rem', fontWeight: 700, letterSpacing: '0.06em',
        padding: '1px 5px', borderRadius: 3,
        background: 'rgba(251,191,36,0.12)', color: '#f59e0b',
      }}>HALF</span>
    );
  }
  return null;
}

function gameStatus(game) {
  if (!game.model) return { label: '—', color: 'var(--text-tertiary)' };
  if (game.model.passes) return { label: 'SIGNAL', color: 'var(--green-profit, #10b981)' };
  if (game.model.edge >= 5) return { label: 'WATCH', color: '#FBBF24' };
  if (game.model.edge >= 2) return { label: 'NEAR', color: 'var(--text-tertiary)' };
  return { label: 'NO EDGE', color: 'var(--text-tertiary)' };
}

const thStyle = {
  fontFamily: 'var(--font-mono)', fontSize: '0.62rem', fontWeight: 700,
  letterSpacing: '0.08em', textTransform: 'uppercase',
  color: 'var(--text-tertiary)', padding: '6px 8px',
  textAlign: 'right', whiteSpace: 'nowrap', position: 'sticky', top: 0,
  background: 'var(--surface-1, #111827)', borderBottom: '1px solid var(--stroke-subtle)',
};

const tdStyle = {
  fontFamily: 'var(--font-mono)', fontSize: '0.75rem', fontWeight: 600,
  padding: '8px 8px', textAlign: 'right', whiteSpace: 'nowrap',
  borderBottom: '1px solid rgba(255,255,255,0.03)',
  fontVariantNumeric: 'tabular-nums',
};

function TableView({ games, isPro, onLineHistory }) {
  return (
    <div style={{
      backgroundColor: 'var(--surface-1, #111827)',
      borderRadius: 10, border: '1px solid var(--stroke-subtle)',
      overflow: 'hidden',
    }}>
      <div style={{ overflowX: 'auto', WebkitOverflowScrolling: 'touch' }}>
        <table style={{
          width: '100%', borderCollapse: 'collapse',
          minWidth: isPro ? '540px' : '400px',
        }}>
          <thead>
            <tr>
              <th style={{ ...thStyle, textAlign: 'left', minWidth: 120 }}>Game</th>
              <th style={thStyle}>Spread</th>
              <th style={thStyle}>Total</th>
              <th style={thStyle}>ML</th>
              {isPro && <th style={thStyle}>Edge</th>}
              {isPro && <th style={thStyle}>Status</th>}
            </tr>
          </thead>
          <tbody>
            {games.map(g => {
              const status = gameStatus(g);
              const isSignal = g.model?.passes;
              const rowBg = isSignal ? 'rgba(52,211,153,0.04)' : 'transparent';
              const homeML = parseFloat(g.home_ml);
              const awayML = parseFloat(g.away_ml);
              return (
                <tr key={g.id} style={{ background: rowBg }}>
                  <td style={{
                    ...tdStyle, textAlign: 'left', padding: '8px 8px',
                  }}>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 5 }}>
                        <span style={{
                          fontSize: '0.72rem', fontWeight: 600,
                          color: 'var(--text-secondary)',
                          overflow: 'hidden', textOverflow: 'ellipsis',
                        }}>{g.away}</span>
                        {g.rlm && <span style={{ fontSize: '0.5rem', color: '#f59e0b' }}>⚡</span>}
                      </div>
                      <span style={{
                        fontSize: '0.72rem', fontWeight: 700,
                        color: 'var(--text-primary)',
                      }}>{g.home}</span>
                      {g.time && (
                        <span style={{ fontSize: '0.62rem', color: 'var(--text-tertiary)', fontWeight: 400 }}>
                          {g.time}
                        </span>
                      )}
                    </div>
                  </td>
                  <td style={tdStyle}>
                    <div style={{ color: 'var(--text-primary)' }}>{fmtSpread(g.spread_home)}</div>
                    <div style={{ color: 'var(--text-secondary)', fontSize: '0.65rem', fontWeight: 400 }}>{fmtSpread(g.spread_away)}</div>
                  </td>
                  <td style={{ ...tdStyle, color: 'var(--text-primary)' }}>
                    {fmtTotal(g.total) || '—'}
                  </td>
                  <td style={tdStyle}>
                    <div style={{ color: awayML > 0 ? '#FBBF24' : 'rgba(96,165,250,0.85)', fontWeight: awayML > 0 ? 600 : 400 }}>{fmtML(g.away_ml)}</div>
                    <div style={{ color: homeML > 0 ? '#FBBF24' : 'rgba(96,165,250,0.85)' }}>{fmtML(g.home_ml)}</div>
                  </td>
                  {isPro && (
                    <td style={{
                      ...tdStyle,
                      color: g.model?.edge >= 7 ? 'var(--green-profit, #10b981)'
                        : g.model?.edge >= 3.5 ? '#FBBF24'
                        : 'var(--text-tertiary)',
                    }}>
                      {g.model?.edge != null ? `+${g.model.edge}%` : '—'}
                    </td>
                  )}
                  {isPro && (
                    <td style={{ ...tdStyle }}>
                      <span style={{
                        fontFamily: 'var(--font-mono)', fontSize: '0.58rem', fontWeight: 700,
                        letterSpacing: '0.04em',
                        padding: '2px 6px', borderRadius: 3,
                        background: isSignal ? 'rgba(52,211,153,0.12)' : status.label === 'WATCH' ? 'rgba(251,191,36,0.10)' : 'rgba(100,116,139,0.08)',
                        color: status.color,
                        border: `1px solid ${isSignal ? 'rgba(52,211,153,0.25)' : status.label === 'WATCH' ? 'rgba(251,191,36,0.20)' : 'rgba(100,116,139,0.12)'}`,
                      }}>{status.label}</span>
                    </td>
                  )}
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}

export default function MarketView({ onBack }) {
  const { user } = useAuth();
  const isPro = user && (user.is_premium || user.subscription_status === 'active' || user.subscription_status === 'trial' || user.founding_member);
  const { sport } = useSport();
  const { data, loading, refetch: refetchMarket } = useApi(sportQuery('/picks/market', sport));
  const { data: watchedData, refetch: refetchWatched } = useApi('/picks/watched');
  const [filter, setFilter] = useState('All');
  const [sort, setSort] = useState('time');
  const [autoSorted, setAutoSorted] = useState(false);
  const [expandedId, setExpandedId] = useState(null);
  const [liveScores, setLiveScores] = useState({});
  const [watchedIds, setWatchedIds] = useState(new Set());
  const [lineHistoryGame, setLineHistoryGame] = useState(null);
  const [viewMode, setViewMode] = useState('board');

  const rawGames = data?.games || [];

  useEffect(() => {
    window.scrollTo(0, 0);
  }, []);

  useEffect(() => {
    if (watchedData?.game_ids) setWatchedIds(new Set(watchedData.game_ids));
  }, [watchedData]);

  useEffect(() => {
    if (isPro && !autoSorted && !loading && rawGames.length > 0 && rawGames.some(g => g.model)) {
      setSort('edge');
      setAutoSorted(true);
    }
  }, [isPro, loading, rawGames, autoSorted]);

  const fetchLiveScores = useCallback(async () => {
    try {
      const resp = await fetch(`${MV_API_BASE}/api/picks/live-scores?sport=${sport}`);
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
    if (filter === 'Passed') return games.filter(g => g.model && !g.model.passes);
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
      const resp = await fetch(`${MV_API_BASE}/api/picks/watch`, {
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
  const passedGames = useMemo(() => games.filter(g => g.model && !g.model.passes), [games]);
  const signalGames = useMemo(() => games.filter(g => g.model && g.model.passes), [games]);

  return (
    <PullToRefresh onRefresh={async () => {
      await Promise.all([refetchMarket(true), refetchWatched(true)]);
      await fetchLiveScores();
    }}>
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
          }}>Market Intelligence</h1>
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
                Model active
              </span>
            </>
          )}
        </div>
      </div>

      {/* Body */}
      <div style={{ padding: '14px 12px 100px' }}>
        <DailyMarketReport />

        {/* Discipline Filter summary */}
        {hasModelData && passedGames.length > 0 && (
          <div style={{
            backgroundColor: 'var(--surface-1)',
            borderRadius: '14px',
            border: '1px solid var(--color-border, var(--stroke-subtle))',
            padding: '14px 16px',
            marginBottom: '14px',
          }}>
            <div style={{
              display: 'flex', justifyContent: 'space-between', alignItems: 'center',
              marginBottom: '10px',
            }}>
              <div style={{
                fontFamily: 'var(--font-mono)', fontSize: '10px', fontWeight: 700,
                letterSpacing: '0.1em', textTransform: 'uppercase',
                color: 'var(--text-tertiary)',
              }}>Discipline Filter</div>
              <button
                onClick={() => setFilter(filter === 'Passed' ? 'All' : 'Passed')}
                style={{
                  fontFamily: 'var(--font-mono)', fontSize: '0.6rem', fontWeight: 600,
                  padding: '3px 8px', borderRadius: 4, cursor: 'pointer',
                  border: filter === 'Passed' ? '1px solid rgba(100,116,139,0.3)' : '1px solid var(--stroke-subtle)',
                  background: filter === 'Passed' ? 'rgba(100,116,139,0.12)' : 'transparent',
                  color: filter === 'Passed' ? 'var(--text-primary)' : 'var(--text-tertiary)',
                }}
              >
                {filter === 'Passed' ? 'Show All' : 'View Passed'}
              </button>
            </div>
            <div style={{
              display: 'flex', gap: '16px', alignItems: 'center',
            }}>
              <div style={{ textAlign: 'center', flex: 1 }}>
                <div style={{
                  fontFamily: 'var(--font-mono)', fontSize: '20px', fontWeight: 700,
                  color: 'var(--text-primary)', lineHeight: 1,
                }}>{games.filter(g => g.model).length}</div>
                <div style={{
                  fontFamily: 'var(--font-mono)', fontSize: '10px', fontWeight: 600,
                  color: 'var(--text-tertiary)', letterSpacing: '0.06em',
                  textTransform: 'uppercase', marginTop: '3px',
                }}>Analyzed</div>
              </div>
              <div style={{
                width: 1, height: 28,
                background: 'var(--stroke-subtle)',
              }} />
              <div style={{ textAlign: 'center', flex: 1 }}>
                <div style={{
                  fontFamily: 'var(--font-mono)', fontSize: '20px', fontWeight: 700,
                  color: signalGames.length > 0 ? 'var(--green-profit, #10b981)' : 'var(--text-primary)',
                  lineHeight: 1,
                }}>{signalGames.length}</div>
                <div style={{
                  fontFamily: 'var(--font-mono)', fontSize: '10px', fontWeight: 600,
                  color: 'var(--text-tertiary)', letterSpacing: '0.06em',
                  textTransform: 'uppercase', marginTop: '3px',
                }}>Signals</div>
              </div>
              <div style={{
                width: 1, height: 28,
                background: 'var(--stroke-subtle)',
              }} />
              <div style={{ textAlign: 'center', flex: 1 }}>
                <div style={{
                  fontFamily: 'var(--font-mono)', fontSize: '20px', fontWeight: 700,
                  color: 'var(--text-secondary)', lineHeight: 1,
                }}>{passedGames.length}</div>
                <div style={{
                  fontFamily: 'var(--font-mono)', fontSize: '10px', fontWeight: 600,
                  color: 'var(--text-tertiary)', letterSpacing: '0.06em',
                  textTransform: 'uppercase', marginTop: '3px',
                }}>Passed</div>
              </div>
            </div>
            <div style={{
              marginTop: '14px', paddingTop: '12px',
              borderTop: '1px solid var(--stroke-subtle)',
              textAlign: 'center',
            }}>
              <div style={{
                fontFamily: 'var(--font-mono)', fontSize: '13px', fontWeight: 700,
                letterSpacing: '0.14em', textTransform: 'uppercase',
                color: 'var(--text-secondary)',
              }}>
                No edge. No pick.
              </div>
            </div>
          </div>
        )}

        {games.length > 0 && (
          <div style={{ marginBottom: 18 }}>
            <div style={{
              display: 'flex', justifyContent: 'space-between', alignItems: 'center',
              gap: 8, marginBottom: 8,
            }}>
              <FilterTabs active={filter} onChange={setFilter} hasLive={hasLive} hasModel={hasModelData} />
              <div style={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                {['board', 'table'].map(mode => (
                  <button key={mode} onClick={() => setViewMode(mode)} style={{
                    background: viewMode === mode ? 'rgba(255,255,255,0.08)' : 'transparent',
                    border: 'none', borderRadius: 4, padding: '5px 6px', cursor: 'pointer',
                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                    opacity: viewMode === mode ? 1 : 0.4,
                  }} aria-label={mode === 'board' ? 'Board view' : 'Table view'}>
                    {mode === 'board' ? (
                      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="var(--text-primary)" strokeWidth="2" strokeLinecap="round">
                        <rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/>
                        <rect x="3" y="14" width="7" height="7"/><rect x="14" y="14" width="7" height="7"/>
                      </svg>
                    ) : (
                      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="var(--text-primary)" strokeWidth="2" strokeLinecap="round">
                        <line x1="3" y1="6" x2="21" y2="6"/><line x1="3" y1="12" x2="21" y2="12"/>
                        <line x1="3" y1="18" x2="21" y2="18"/>
                      </svg>
                    )}
                  </button>
                ))}
              </div>
            </div>
            {viewMode === 'board' && (
              <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
                <SortPicker active={sort} onChange={setSort} isPro={isPro} />
              </div>
            )}
          </div>
        )}

        {loading ? (
          <div style={{ padding: '16px 16px 0' }}>
            {[1,2,3,4].map(i => (
              <div key={i} style={{
                padding: '14px 16px', marginBottom: '8px',
                backgroundColor: 'var(--surface-1)', borderRadius: '12px',
                border: '1px solid var(--stroke-subtle)',
              }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '10px' }}>
                  <div style={{ width: '45%', height: '14px', borderRadius: '6px',
                    background: 'linear-gradient(90deg, var(--surface-2) 25%, rgba(255,255,255,0.06) 50%, var(--surface-2) 75%)',
                    backgroundSize: '200% 100%', animation: 'mktShimmer 1.8s ease-in-out infinite' }} />
                  <div style={{ width: '20%', height: '14px', borderRadius: '6px',
                    background: 'linear-gradient(90deg, var(--surface-2) 25%, rgba(255,255,255,0.06) 50%, var(--surface-2) 75%)',
                    backgroundSize: '200% 100%', animation: 'mktShimmer 1.8s ease-in-out infinite' }} />
                </div>
                <div style={{ display: 'flex', gap: '8px' }}>
                  {[1,2,3].map(j => (
                    <div key={j} style={{ flex: 1, height: '32px', borderRadius: '6px',
                      background: 'linear-gradient(90deg, var(--surface-2) 25%, rgba(255,255,255,0.06) 50%, var(--surface-2) 75%)',
                      backgroundSize: '200% 100%', animation: 'mktShimmer 1.8s ease-in-out infinite' }} />
                  ))}
                </div>
              </div>
            ))}
            <style>{`@keyframes mktShimmer { 0% { background-position: -200% 0; } 100% { background-position: 200% 0; } }`}</style>
          </div>
        ) : sorted.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '60px 20px' }}>
            <div style={{
              width: '48px', height: '48px', borderRadius: '12px',
              backgroundColor: 'var(--surface-2)', margin: '0 auto 16px',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
            }}>
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="var(--text-tertiary)" strokeWidth="2" strokeLinecap="round">
                <circle cx="12" cy="12" r="10"/><path d="M8 15h8M9 9h.01M15 9h.01"/>
              </svg>
            </div>
            <div style={{ fontSize: '15px', fontWeight: 600, color: 'var(--text-secondary)', marginBottom: '6px' }}>
              {games.length === 0 ? 'No games today' : filter === 'Passed' ? 'All games generated signals' : `No ${filter.toLowerCase()} games`}
            </div>
            <div style={{ fontSize: '13px', color: 'var(--text-tertiary)', lineHeight: '1.5' }}>
              {games.length === 0 ? 'Check back tomorrow for the next slate.' : filter === 'Passed' ? 'Every game passed qualification filters today. Rare, but it happens.' : 'Try a different filter to see more games.'}
            </div>
          </div>
        ) : viewMode === 'table' ? (
          <TableView games={sorted} isPro={isPro} onLineHistory={setLineHistoryGame} />
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
              isPro={isPro}
              onLineHistory={setLineHistoryGame}
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
                isPro={isPro}
                onLineHistory={setLineHistoryGame}
              />
            ))}
          </div>
        )}

        <p style={{
          fontSize: '0.65rem', color: 'var(--text-tertiary)',
          textAlign: 'center', marginTop: 20, lineHeight: 1.5,
        }}>
          Lines sourced from DraftKings, FanDuel, BetMGM, Caesars, PointsBet, BetRivers.
          Best available shown. {hasModelData ? 'Tap any game for quant analysis. Tap sparkline for line history.' : ''}
        </p>
      </div>
    </div>
    {lineHistoryGame && (
      <LineHistoryModal game={lineHistoryGame} onClose={() => setLineHistoryGame(null)} />
    )}
    </PullToRefresh>
  );
}
