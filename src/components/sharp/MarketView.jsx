import { useState, useMemo, useEffect, useCallback } from 'react';
import { Capacitor } from '@capacitor/core';
import { useAuth } from '../../hooks/useAuth';
import { useApi } from '../../hooks/useApi';
import { useSport, sportQuery } from '../../hooks/useSport';
import PullToRefresh from '../shared/PullToRefresh';
import DailyMarketReport from './DailyMarketReport';
import { trackEvent } from '../../utils/eventTracker';
import teamAbbr from '../../utils/teamAbbr';
import sportDisplay from '../../utils/sportDisplay';

const PROD_URL = 'https://app.sharppicks.ai';
const MV_API_BASE = Capacitor.isNativePlatform() ? PROD_URL : '';

const pulseKeyframes = `
@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.4; }
}`;
if (typeof document !== 'undefined' && !document.getElementById('sp-pulse-anim')) {
  const style = document.createElement('style');
  style.id = 'sp-pulse-anim';
  style.textContent = pulseKeyframes;
  document.head.appendChild(style);
}

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

const SHARP_CONF = {
  high:     { color: '#f59e0b', bg: 'rgba(251,191,36,0.06)', border: 'rgba(251,191,36,0.20)', label: 'HIGH', fill: 1.0 },
  moderate: { color: '#d4a24a', bg: 'rgba(251,191,36,0.04)', border: 'rgba(251,191,36,0.12)', label: 'MED',  fill: 0.6 },
  low:      { color: '#A89A7A', bg: 'rgba(251,191,36,0.02)', border: 'rgba(251,191,36,0.08)', label: 'LOW',  fill: 0.3 },
};

function RLMBadge({ sharpAction }) {
  if (!sharpAction) return null;
  const cfg = SHARP_CONF[sharpAction.confidence] || SHARP_CONF.low;
  return (
    <span style={{
      fontSize: '0.62rem', fontWeight: 700, letterSpacing: '0.06em',
      padding: '2px 6px', borderRadius: 3,
      background: `${cfg.color}22`, color: cfg.color,
      border: `1px solid ${cfg.border}`,
      display: 'inline-flex', alignItems: 'center', gap: 3,
    }}>
      <span style={{ fontSize: '0.625rem' }}>⚡</span>RLM{sharpAction.move ? ` ${sharpAction.move}` : ''}
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
          fontFamily: 'var(--font-mono)', fontSize: '0.625rem', fontWeight: 700,
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
      {sub && <div style={{ fontSize: '0.625rem', color: 'var(--text-tertiary)', marginTop: 1 }}>{sub}</div>}
    </div>
  );
}

const STABILITY_CONFIG = {
  low: { color: '#f59e0b', bg: 'rgba(251,191,36,0.04)', border: 'rgba(251,191,36,0.15)', desc: 'Market still finding price — line may continue moving' },
  medium: { color: 'var(--text-secondary)', bg: 'rgba(255,255,255,0.02)', border: 'rgba(255,255,255,0.06)', desc: 'Moderate book agreement — some price discovery remaining' },
  high: { color: 'var(--green-profit, #10b981)', bg: 'rgba(52,211,153,0.03)', border: 'rgba(52,211,153,0.12)', desc: 'Strong book consensus — line unlikely to move significantly' },
};

function MarketConfidence({ stability, edge }) {
  const cfg = STABILITY_CONFIG[stability.level] || STABILITY_CONFIG.medium;
  const edgeAligned = edge > 5 && stability.level === 'low';
  return (
    <div style={{
      marginTop: 10, padding: '10px 12px', borderRadius: 6,
      background: cfg.bg, border: `1px solid ${cfg.border}`,
    }}>
      <div style={{
        display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6,
      }}>
        <span style={{
          fontFamily: 'var(--font-mono)', fontSize: '0.62rem', fontWeight: 700,
          letterSpacing: '0.08em', textTransform: 'uppercase',
          color: 'var(--text-tertiary)',
        }}>Market Confidence</span>
        <span style={{
          fontFamily: 'var(--font-mono)', fontSize: '0.72rem', fontWeight: 700,
          color: cfg.color,
        }}>{stability.label}</span>
      </div>

      {/* Stability bar */}
      <div style={{
        display: 'flex', gap: 3, marginBottom: 8,
      }}>
        {[0, 1, 2].map(i => (
          <div key={i} style={{
            flex: 1, height: 4, borderRadius: 2,
            background: (stability.level === 'high' && i <= 2) ||
                        (stability.level === 'medium' && i <= 1) ||
                        (stability.level === 'low' && i <= 0)
              ? cfg.color : 'rgba(255,255,255,0.06)',
            transition: 'background 0.3s ease',
          }} />
        ))}
      </div>

      <div style={{
        fontFamily: 'var(--font-mono)', fontSize: '0.625rem',
        color: 'var(--text-secondary)', lineHeight: 1.45,
      }}>
        {cfg.desc}
      </div>

      {/* Stats row */}
      <div style={{
        display: 'flex', gap: 12, marginTop: 8, paddingTop: 6,
        borderTop: '1px solid rgba(255,255,255,0.04)',
      }}>
        {stability.total_move > 0 && (
          <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.625rem', color: 'var(--text-tertiary)' }}>
            Moved {stability.total_move}
          </span>
        )}
        {stability.changes > 0 && (
          <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.625rem', color: 'var(--text-tertiary)' }}>
            {stability.changes} change{stability.changes !== 1 ? 's' : ''}
          </span>
        )}
        {stability.spread_range != null && (
          <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.625rem', color: 'var(--text-tertiary)' }}>
            {stability.spread_range} book range
          </span>
        )}
      </div>

      {edgeAligned && (
        <div style={{
          marginTop: 8, padding: '4px 8px', borderRadius: 4,
          background: 'rgba(251,191,36,0.08)',
          fontFamily: 'var(--font-mono)', fontSize: '0.625rem', fontWeight: 600,
          color: '#f59e0b',
        }}>
          Edge + low stability: market may be moving toward model price
        </div>
      )}
    </div>
  );
}

function ValueRange({ pickLine, playableTo, currentLine }) {
  const range = Math.abs(playableTo - pickLine);
  if (range < 0.5) return null;
  const current = currentLine ?? pickLine;
  const consumed = Math.abs(current - pickLine);
  const pct = Math.min(consumed / range * 100, 100);
  const isUnderdog = pickLine > 0;
  const atRisk = pct >= 75;

  return (
    <div style={{
      marginTop: 10, padding: '10px 12px', borderRadius: 6,
      background: atRisk ? 'rgba(251,191,36,0.04)' : 'rgba(79,125,243,0.03)',
      border: `1px solid ${atRisk ? 'rgba(251,191,36,0.15)' : 'rgba(79,125,243,0.1)'}`,
    }}>
      <div style={{
        display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8,
      }}>
        <span style={{
          fontFamily: 'var(--font-mono)', fontSize: '0.62rem', fontWeight: 700,
          letterSpacing: '0.08em', textTransform: 'uppercase',
          color: 'var(--text-tertiary)',
        }}>Value Range</span>
        {atRisk && (
          <span style={{
            fontFamily: 'var(--font-mono)', fontSize: '0.625rem', fontWeight: 700,
            color: '#f59e0b', letterSpacing: '0.04em',
          }}>EDGE THINNING</span>
        )}
      </div>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6 }}>
        <span style={{
          fontFamily: 'var(--font-mono)', fontSize: '0.8rem', fontWeight: 700,
          color: 'var(--green-profit, #10b981)',
        }}>{fmtSpread(pickLine)}</span>
        <div style={{
          flex: 1, height: 6, borderRadius: 3,
          background: 'rgba(255,255,255,0.06)', position: 'relative', overflow: 'hidden',
        }}>
          <div style={{
            position: 'absolute', left: 0, top: 0, bottom: 0,
            width: `${100 - pct}%`, borderRadius: 3,
            background: atRisk
              ? 'linear-gradient(90deg, var(--green-profit, #10b981) 0%, #f59e0b 100%)'
              : 'var(--green-profit, #10b981)',
            transition: 'width 0.3s ease',
          }} />
        </div>
        <span style={{
          fontFamily: 'var(--font-mono)', fontSize: '0.8rem', fontWeight: 700,
          color: 'var(--text-tertiary)',
        }}>{fmtSpread(playableTo)}</span>
      </div>
      <div style={{
        fontFamily: 'var(--font-mono)', fontSize: '0.625rem',
        color: 'var(--text-secondary)',
      }}>
        Playable {isUnderdog ? 'down' : 'up'} to {fmtSpread(playableTo)} &mdash; edge invalidates beyond
      </div>
    </div>
  );
}

function QuantExpandedPanel({ game, model, lineStability }) {
  if (!model) return null;
  const strength = edgeStrength(model.edge);
  const probPct = model.cover_prob != null ? (model.cover_prob * 100).toFixed(1) : null;
  const impliedFromLine = model.line != null ? (model.line <= 0 ? 52.4 : 47.6) : null;
  const edgePct = model.edge != null ? Math.min(model.edge / 15 * 100, 100) : 0;
  const mono = "'IBM Plex Mono', var(--font-mono), monospace";
  const sans = "'Inter', var(--font-sans), sans-serif";
  const brandGreen = '#5A9E72';
  const brandRed = '#C4686B';
  const textMuted = '#7A8494';
  const textSec = '#9EAAB8';
  const textPrimary = '#E8ECF4';
  const border = 'rgba(255,255,255,0.06)';
  const bgElevated = '#141A2E';

  const qStatLabel = { fontFamily: mono, fontSize: '10px', letterSpacing: '1px', textTransform: 'uppercase', color: textMuted, marginBottom: '4px' };
  const qStatVal = { fontFamily: mono, fontSize: '16px', fontWeight: 500, color: textPrimary };

  return (
    <div style={{ borderTop: `1px solid ${border}` }}>
      {/* Header */}
      <div style={{
        display: 'flex', justifyContent: 'space-between', alignItems: 'center',
        padding: '14px 16px', borderBottom: `1px solid ${border}`,
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <span style={{ fontSize: '12px', color: textMuted }}>◎</span>
          <span style={{
            fontFamily: mono, fontSize: '10px', fontWeight: 500,
            letterSpacing: '1.5px', textTransform: 'uppercase', color: textSec,
          }}>Quant Analysis</span>
          {game?.consensus_spread != null && (
            <span style={{ fontFamily: mono, fontSize: '10px', color: textMuted, marginLeft: 4 }}>
              · Consensus {fmtSpread(game.consensus_spread)}
            </span>
          )}
        </div>
      </div>

      {/* Stats row 1 */}
      <div style={{
        display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 0,
        padding: '12px 0', margin: '0 16px', borderBottom: `1px solid ${border}`,
      }}>
        {model.edge != null && (
          <div style={{ textAlign: 'center', position: 'relative', borderRight: `1px solid ${border}` }}>
            <div style={qStatLabel}>Adj. Edge</div>
            <div style={{ ...qStatVal, color: brandGreen }}>+{model.edge}%</div>
          </div>
        )}
        {probPct && (
          <div style={{ textAlign: 'center', position: 'relative', borderRight: `1px solid ${border}` }}>
            <div style={qStatLabel}>Cover Prob</div>
            <div style={qStatVal}>{probPct}%</div>
            {impliedFromLine && <div style={{ fontFamily: mono, fontSize: '10px', color: textMuted, marginTop: 2 }}>vs {impliedFromLine.toFixed(1)}% implied</div>}
          </div>
        )}
        {model.predicted_margin != null && (
          <div style={{ textAlign: 'center' }}>
            <div style={qStatLabel}>Proj. Margin</div>
            <div style={{ ...qStatVal, color: model.predicted_margin < 0 ? brandRed : brandGreen }}>
              {model.predicted_margin > 0 ? '+' : ''}{model.predicted_margin}
            </div>
          </div>
        )}
      </div>

      {/* Stats row 2 */}
      {(model.raw_edge != null || model.line != null) && (
        <div style={{
          display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 0,
          padding: '12px 0', margin: '0 16px', borderBottom: `1px solid ${border}`,
        }}>
          {model.raw_edge != null && (
            <div style={{ textAlign: 'center', position: 'relative', borderRight: `1px solid ${border}` }}>
              <div style={qStatLabel}>Raw Edge</div>
              <div style={{ ...qStatVal, color: brandGreen }}>+{model.raw_edge}%</div>
            </div>
          )}
          {model.line != null && (
            <div style={{ textAlign: 'center', position: 'relative', borderRight: `1px solid ${border}` }}>
              <div style={qStatLabel}>Pick Line</div>
              <div style={qStatVal}>{fmtSpread(model.line)}</div>
            </div>
          )}
          {probPct && impliedFromLine && (
            <div style={{ textAlign: 'center' }}>
              <div style={qStatLabel}>Prob. Edge</div>
              <div style={{ ...qStatVal, color: brandGreen }}>+{(parseFloat(probPct) - impliedFromLine).toFixed(1)}pp</div>
            </div>
          )}
        </div>
      )}

      {/* Pick line */}
      {model.pick && (
        <div style={{
          display: 'flex', justifyContent: 'space-between', alignItems: 'center',
          margin: '12px 16px', padding: '10px 14px',
          background: bgElevated, borderRadius: 6, border: `1px solid ${border}`,
        }}>
          <span style={{ fontFamily: mono, fontSize: '12px', fontWeight: 500, color: textPrimary }}>
            {model.pick}
          </span>
          <span style={{
            fontFamily: mono, fontSize: '10px', letterSpacing: '1px', textTransform: 'uppercase',
            padding: '3px 8px', borderRadius: 3,
            ...(model.passes
              ? { color: brandGreen, background: 'rgba(90,158,114,0.15)' }
              : { color: textMuted, background: 'rgba(255,255,255,0.04)' }),
          }}>
            {model.passes ? 'Signal' : 'No Action'}
          </span>
        </div>
      )}

      {/* Value Range */}
      {model.line != null && model.playable_to != null && model.passes && (
        <div style={{ padding: '0 16px 12px' }}>
          <ValueRange pickLine={model.line} playableTo={model.playable_to} currentLine={model.line} />
        </div>
      )}

      {/* Market Confidence */}
      {lineStability && (
        <div style={{ padding: '0 16px 12px' }}>
          <MarketConfidence stability={lineStability} edge={model.edge} />
        </div>
      )}

      {/* Quant Reasoning */}
      {model.signals?.length > 0 && (
        <div style={{
          margin: '0 16px 14px', padding: '12px 14px',
          background: bgElevated, borderRadius: 6, border: `1px solid ${border}`,
        }}>
          <div style={{
            fontFamily: mono, fontSize: '10px', letterSpacing: '1.5px',
            textTransform: 'uppercase', color: textMuted, marginBottom: 10,
          }}>Quant Reasoning</div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {model.signals.map((s, i) => (
              <div key={i} style={{
                display: 'flex', gap: 8, fontFamily: sans,
                fontSize: '11px', lineHeight: 1.45, color: textSec,
              }}>
                <span style={{ color: brandGreen, fontSize: '10px', marginTop: 2, flexShrink: 0 }}>›</span>
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
  const sa = game.sharp_action;
  if (!sa) return null;
  const cfg = SHARP_CONF[sa.confidence] || SHARP_CONF.low;
  const sharpSide = sa.side === 'home' ? game.home : game.away;
  const publicSide = sa.side === 'home' ? game.away : game.home;
  const [expanded, setExpanded] = useState(false);

  return (
    <div style={{
      padding: '8px 14px',
      borderTop: `1px solid ${cfg.border}`,
      background: cfg.bg,
    }}>
      <div
        onClick={() => setExpanded(!expanded)}
        style={{ cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 6 }}
      >
        <span style={{
          fontSize: '0.62rem', fontWeight: 700, letterSpacing: '0.06em',
          color: cfg.color,
        }}>⚡ SHARP ACTION DETECTED</span>
        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <div style={{
            display: 'flex', gap: 2,
          }}>
            {[0.3, 0.6, 1.0].map((t, i) => (
              <div key={i} style={{
                width: 12, height: 4, borderRadius: 1,
                background: cfg.fill >= t ? cfg.color : 'rgba(255,255,255,0.08)',
              }} />
            ))}
          </div>
          <span style={{
            fontFamily: 'var(--font-mono)', fontSize: '0.625rem', fontWeight: 700,
            color: cfg.color, letterSpacing: '0.06em',
          }}>{cfg.label}</span>
          <span style={{ fontSize: '0.625rem', color: 'var(--text-tertiary)', transition: 'transform 0.2s', transform: expanded ? 'rotate(180deg)' : 'rotate(0)' }}>▾</span>
        </div>
      </div>
      <div style={{
        display: 'flex', justifyContent: 'space-between', alignItems: 'center',
      }}>
        <div>
          <div style={{
            fontFamily: 'var(--font-mono)', fontSize: '0.625rem', fontWeight: 600,
            color: 'var(--text-tertiary)', letterSpacing: '0.04em', marginBottom: 2,
          }}>PUBLIC SIDE</div>
          <div style={{
            fontFamily: 'var(--font-mono)', fontSize: '0.72rem', fontWeight: 600,
            color: 'var(--text-secondary)',
          }}>{publicSide}</div>
        </div>
        <div style={{
          fontFamily: 'var(--font-mono)', fontSize: '0.625rem',
          color: 'var(--text-tertiary)', textAlign: 'center',
        }}>
          <div>Line moved</div>
          <div style={{ color: cfg.color, fontWeight: 700, fontSize: '0.72rem' }}>
            {sa.move}
          </div>
          <div style={{ fontSize: '0.625rem', color: 'var(--text-tertiary)', marginTop: 1 }}>
            {sa.spread_open > 0 ? '+' : ''}{sa.spread_open} → {sa.spread_now > 0 ? '+' : ''}{sa.spread_now}
          </div>
        </div>
        <div style={{ textAlign: 'right' }}>
          <div style={{
            fontFamily: 'var(--font-mono)', fontSize: '0.625rem', fontWeight: 600,
            color: cfg.color, letterSpacing: '0.04em', marginBottom: 2,
          }}>SHARP SIDE</div>
          <div style={{
            fontFamily: 'var(--font-mono)', fontSize: '0.72rem', fontWeight: 700,
            color: cfg.color,
          }}>{sharpSide}</div>
        </div>
      </div>
      {expanded && sa.evidence?.length > 0 && (
        <div style={{ marginTop: 8, paddingTop: 6, borderTop: `1px solid ${cfg.border}` }}>
          {sa.evidence.map((e, i) => (
            <div key={i} style={{
              fontFamily: 'var(--font-mono)', fontSize: '0.625rem',
              color: 'var(--text-tertiary)', lineHeight: 1.5,
              paddingLeft: 8, position: 'relative',
            }}>
              <span style={{ position: 'absolute', left: 0, color: cfg.color }}>•</span>
              {e}
            </div>
          ))}
        </div>
      )}
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
            fontSize: '0.625rem', fontWeight: 700, padding: '1px 6px',
            borderRadius: 3, background: 'rgba(251,191,36,0.1)',
            color: '#f59e0b', letterSpacing: '0.04em',
            border: '1px solid rgba(251,191,36,0.2)',
            display: 'inline-flex', alignItems: 'center', gap: 3,
          }}>
            {absDiff} off
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
          The current line is <strong style={{ color: '#f59e0b' }}>{absDiff}</strong> away from the
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

function GameRow({ game, expanded, onToggle, watching, onWatch, isPro, onLineHistory, sport }) {
  const totalDisplay = fmtTotal(game.total);
  const isFinal = game.status === 'final';
  const isLive = game.status === 'live' || game.status === 'in_progress';
  const showScores = isLive || isFinal;
  const hasModel = !!game.model;
  const edge = game.model?.edge;
  const hasSignalEdge = edge != null && edge >= 3.5;
  const noEdge = hasModel && !hasSignalEdge;
  const strength = edge != null ? edgeStrength(edge) : null;
  const hasSignal = game.model?.passes;
  const pickResult = game.pick_result;

  const mono = "'IBM Plex Mono', var(--font-mono), monospace";
  const sans = "'Inter', var(--font-sans), sans-serif";
  const brandGreen = '#5A9E72';
  const brandRed = '#C4686B';
  const accentYellow = '#D4A843';
  const textPrimary = '#E8ECF4';
  const textSec = '#9EAAB8';
  const textMuted = '#7A8494';
  const bgCard = '#0F1424';
  const bgElevated = '#141A2E';
  const border = 'rgba(255,255,255,0.06)';
  const grayBorder = '#4a5568';

  const strengthStyle = strength === 'STRONG'
    ? { color: brandGreen, background: 'rgba(90,158,114,0.15)' }
    : strength === 'MODERATE'
    ? { color: accentYellow, background: 'rgba(212,168,67,0.12)' }
    : strength === 'WEAK'
    ? { color: textMuted, background: 'rgba(255,255,255,0.04)' }
    : null;

  const leftBorder = hasSignal ? `3px solid ${brandGreen}`
    : isFinal ? `3px solid ${grayBorder}`
    : `3px solid #1e3050`;

  const awayAbbr = teamAbbr(game.away);
  const homeAbbr = teamAbbr(game.home);

  return (
    <div style={{
      background: bgCard,
      border: `1px solid ${border}`,
      borderLeft: leftBorder,
      borderRadius: 8,
      overflow: 'hidden',
      opacity: noEdge && !isFinal ? 0.6 : 1,
      transition: 'opacity 0.15s ease',
    }}>
      <div
        onClick={hasModel ? onToggle : undefined}
        style={{ cursor: hasModel ? 'pointer' : 'default', padding: '14px 16px' }}
      >
        {/* Top row: Teams + Edge/Result badge */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 10 }}>
          <div style={{ flex: 1 }}>
            {/* Away team */}
            <div style={{ display: 'flex', alignItems: 'baseline', gap: 8, marginBottom: 3 }}>
              <span style={{ fontFamily: sans, fontSize: '13px', fontWeight: 600, color: textPrimary }}>{game.away}</span>
              {game.away_record && game.away_record !== 'N/A' && <span style={{ fontFamily: mono, fontSize: '10px', color: textMuted }}>{game.away_record}</span>}
            </div>
            {/* Home team */}
            <div style={{ display: 'flex', alignItems: 'baseline', gap: 8, marginBottom: 3 }}>
              <span style={{ fontFamily: sans, fontSize: '13px', fontWeight: 600, color: textPrimary }}>{game.home}</span>
              {game.home_record && game.home_record !== 'N/A' && <span style={{ fontFamily: mono, fontSize: '10px', color: textMuted }}>{game.home_record}</span>}
            </div>
            {/* Game time (scheduled only) */}
            {!isLive && !isFinal && (
              <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginTop: 2 }}>
                {game.time && <span style={{ fontFamily: mono, fontSize: '10px', color: textMuted }}>{game.time}</span>}
              </div>
            )}
          </div>

          {/* Edge + badge */}
          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: 4, marginLeft: 12 }}>
            {edge != null && (
              <span style={{
                fontFamily: mono, fontSize: '14px', fontWeight: 500,
                color: hasSignalEdge ? brandGreen : textMuted,
              }}>+{edge}%</span>
            )}
            {isFinal && pickResult ? (
              (pickResult.result === 'win' || pickResult.result === 'W') ? (
                <span style={{
                  fontFamily: mono, fontSize: '11px', fontWeight: 700,
                  padding: '3px 8px', borderRadius: 4,
                  background: 'rgba(90,158,114,0.12)', color: brandGreen,
                }}>Win {pickResult.units != null ? `+${Math.abs(pickResult.units).toFixed(1)}u` : ''}</span>
              ) : (pickResult.result === 'loss' || pickResult.result === 'L') ? (
                <span style={{
                  fontFamily: mono, fontSize: '11px', fontWeight: 700,
                  padding: '3px 8px', borderRadius: 4,
                  background: 'rgba(196,104,107,0.12)', color: brandRed,
                }}>Loss {pickResult.units != null ? `${Math.abs(pickResult.units).toFixed(1)}u` : ''}</span>
              ) : pickResult.result === 'push' ? (
                <span style={{
                  fontFamily: mono, fontSize: '11px', fontWeight: 700,
                  padding: '3px 8px', borderRadius: 4,
                  background: 'rgba(74,85,104,0.15)', color: '#6b7a8d',
                }}>Push</span>
              ) : null
            ) : hasSignal && !isFinal ? (
              <span style={{
                fontFamily: mono, fontSize: '10px', fontWeight: 700,
                letterSpacing: '1px', textTransform: 'uppercase',
                padding: '2px 6px', borderRadius: 3,
                color: brandGreen, background: 'rgba(90,158,114,0.15)',
              }}>Signal</span>
            ) : null}
          </div>
        </div>

        {/* Probable pitchers (MLB) */}
        {sport === 'mlb' && (game.home_pitcher || game.away_pitcher) && (
          <div style={{
            marginBottom: 10, display: 'flex', alignItems: 'center', gap: 6,
            fontFamily: mono, fontSize: '10px', color: textMuted,
          }}>
            <span style={{ fontWeight: 700, letterSpacing: '0.06em' }}>SP</span>
            {game.away_pitcher || 'TBD'} <span style={{ color: textMuted, fontSize: '10px' }}>vs</span> {game.home_pitcher || 'TBD'}
          </div>
        )}

        {/* Live Bar */}
        {isLive && (
          <div style={{
            display: 'flex', justifyContent: 'space-between', alignItems: 'center',
            background: 'rgba(90,158,114,0.06)',
            border: '0.5px solid rgba(90,158,114,0.15)',
            borderRadius: 5, padding: '6px 10px', marginBottom: 10,
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
              <span style={{
                width: 5, height: 5, borderRadius: '50%', background: brandGreen,
                animation: 'pulse 2s ease-in-out infinite',
              }} />
              <span style={{ fontFamily: mono, fontSize: '10px', color: brandGreen, fontWeight: 600, letterSpacing: '0.5px' }}>
                {game.current_period || sportDisplay(sport).periodLabel(game.live_period)}
                {sportDisplay(sport).showClock && (game.game_clock || game.live_clock) ? ` · ${game.game_clock || game.live_clock}` : ''}
              </span>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
              <span style={{ fontFamily: mono, fontSize: '10px', color: textMuted }}>{awayAbbr}</span>
              <span style={{ fontFamily: mono, fontSize: '15px', fontWeight: 500, color: textPrimary }}>{game.away_score ?? 0}</span>
              <span style={{ fontFamily: mono, fontSize: '10px', color: grayBorder }}>·</span>
              <span style={{ fontFamily: mono, fontSize: '10px', color: textMuted }}>{homeAbbr}</span>
              <span style={{ fontFamily: mono, fontSize: '15px', fontWeight: 500, color: textPrimary }}>{game.home_score ?? 0}</span>
            </div>
          </div>
        )}

        {/* Final Bar */}
        {isFinal && (
          <div style={{
            display: 'flex', justifyContent: 'space-between', alignItems: 'center',
            background: 'rgba(74,85,104,0.1)',
            border: '0.5px solid rgba(74,85,104,0.2)',
            borderRadius: 5, padding: '6px 10px', marginBottom: 10,
          }}>
            <span style={{
              fontFamily: mono, fontSize: '10px', fontWeight: 700,
              letterSpacing: '1px', textTransform: 'uppercase', color: grayBorder,
            }}>FINAL</span>
            <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
              <span style={{ fontFamily: mono, fontSize: '10px', color: textMuted }}>{awayAbbr}</span>
              <span style={{ fontFamily: mono, fontSize: '15px', fontWeight: 500, color: textPrimary }}>{game.away_score ?? 0}</span>
              <span style={{ fontFamily: mono, fontSize: '10px', color: grayBorder }}>·</span>
              <span style={{ fontFamily: mono, fontSize: '10px', color: textMuted }}>{homeAbbr}</span>
              <span style={{ fontFamily: mono, fontSize: '15px', fontWeight: 500, color: textPrimary }}>{game.home_score ?? 0}</span>
            </div>
          </div>
        )}

        {/* Cover Tracker (live signal games only) */}
        {isLive && hasSignal && game.cover && (
          <div style={{ marginBottom: 10 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
              <span style={{
                fontFamily: mono, fontSize: '10px', fontWeight: 700,
                letterSpacing: '1px', textTransform: 'uppercase', color: grayBorder,
              }}>COVER TRACKER</span>
              <span style={{
                fontFamily: mono, fontSize: '10px', fontWeight: 500,
                color: game.cover.status === 'covering' ? brandGreen : brandRed,
              }}>
                {game.model?.pick || ''} · {game.cover.status === 'covering' ? 'covering' : 'not covering'} by {game.cover.margin}
              </span>
            </div>
            <div style={{ position: 'relative', height: 3, background: '#1a2a42', borderRadius: 2 }}>
              <div style={{
                position: 'absolute', left: 0, top: 0, height: '100%',
                width: `${Math.min(50 + (game.cover.status === 'covering' ? 1 : -1) * Math.min(game.cover.margin * 3, 50), 100)}%`,
                background: game.cover.status === 'covering' ? brandGreen : brandRed,
                borderRadius: 2, transition: 'width 0.3s ease',
              }} />
              <div style={{
                position: 'absolute', left: '50%', top: -2, width: 1.5, height: 7,
                background: textPrimary, transform: 'translateX(-50%)',
              }} />
            </div>
          </div>
        )}

        {/* Data strip: 4-column grid */}
        <div style={{
          display: 'grid', gridTemplateColumns: '1fr 1fr 1fr 1fr',
          background: noEdge ? '#111728' : bgElevated,
          borderRadius: 6, padding: '8px 0',
        }}>
          {/* Spread */}
          <div style={{ textAlign: 'center', position: 'relative' }}>
            <div style={{ fontFamily: mono, fontSize: '10px', letterSpacing: '1px', textTransform: 'uppercase', color: textMuted, marginBottom: 2 }}>
              {sportDisplay(sport).spreadLabel}
            </div>
            <div style={{ fontFamily: mono, fontSize: '13px', fontWeight: 500, color: textSec }}>
              {fmtSpread(game.spread_away)}
            </div>
            <div style={{ fontFamily: mono, fontSize: '10px', color: textMuted }}>{fmtSpread(game.spread_home)}</div>
            <div style={{ position: 'absolute', right: 0, top: 2, bottom: 2, width: 1, background: border }} />
          </div>

          {/* Total */}
          <div style={{ textAlign: 'center', position: 'relative' }}>
            <div style={{ fontFamily: mono, fontSize: '10px', letterSpacing: '1px', textTransform: 'uppercase', color: textMuted, marginBottom: 2 }}>Total</div>
            <div style={{ fontFamily: mono, fontSize: '13px', fontWeight: 500, color: textSec }}>
              {totalDisplay || '—'}
            </div>
            {game.total != null && game.total_open != null && Math.abs(parseFloat(game.total) - parseFloat(game.total_open)) >= 0.25 && (
              <div style={{ fontFamily: mono, fontSize: '10px', color: accentYellow }}>
                {parseFloat(game.total) > parseFloat(game.total_open) ? '▲' : '▼'}
                {Math.abs(parseFloat(game.total) - parseFloat(game.total_open)).toFixed(1)}
              </div>
            )}
            <div style={{ position: 'absolute', right: 0, top: 2, bottom: 2, width: 1, background: border }} />
          </div>

          {/* ML */}
          <div style={{ textAlign: 'center', position: 'relative' }}>
            <div style={{ fontFamily: mono, fontSize: '10px', letterSpacing: '1px', textTransform: 'uppercase', color: textMuted, marginBottom: 2 }}>ML</div>
            <div style={{
              fontFamily: mono, fontSize: '13px', fontWeight: 500,
              color: parseFloat(game.away_ml) > 0 ? brandGreen : brandRed,
            }}>{fmtML(game.away_ml)}</div>
            <div style={{
              fontFamily: mono, fontSize: '10px',
              color: parseFloat(game.home_ml) > 0 ? brandGreen : brandRed,
            }}>{fmtML(game.home_ml)}</div>
            <div style={{ position: 'absolute', right: 0, top: 2, bottom: 2, width: 1, background: border }} />
          </div>

          {/* Edge */}
          <div style={{ textAlign: 'center' }}>
            <div style={{ fontFamily: mono, fontSize: '10px', letterSpacing: '1px', textTransform: 'uppercase', color: textMuted, marginBottom: 2 }}>Edge</div>
            <div style={{
              fontFamily: mono, fontSize: '13px', fontWeight: 500,
              color: hasSignalEdge ? brandGreen : textSec,
            }}>{edge != null ? `+${edge}%` : '—'}</div>
          </div>
        </div>

        {/* View quant analysis — all model cards when collapsed */}
        {hasModel && !expanded && (
          <div style={{
            marginTop: 10, padding: '8px 0',
            textAlign: 'center',
            fontFamily: mono, fontSize: '10px', fontWeight: 500,
            letterSpacing: '0.5px', color: textMuted,
          }}>
            View quant analysis
          </div>
        )}

        {/* No signal issued label for final non-signal games */}
        {isFinal && !hasSignal && !pickResult && (
          <div style={{
            marginTop: 8, textAlign: 'center',
            fontFamily: mono, fontSize: '10px', color: grayBorder,
          }}>No signal issued</div>
        )}
      </div>

      {/* Expanded quant analysis — Pro only */}
      {expanded && isPro && <QuantExpandedPanel game={game} model={game.model} lineStability={game.line_stability} />}
      {expanded && !isPro && (
        <div style={{
          padding: 16, textAlign: 'center',
          borderTop: `1px solid ${border}`,
        }}>
          <div style={{ fontSize: '13px', fontWeight: 600, color: textSec, marginBottom: 4 }}>
            Quant analysis is a Pro feature
          </div>
          <div style={{ fontSize: '11px', color: textMuted }}>
            Upgrade for edge data, cover probability, and quant reasoning
          </div>
        </div>
      )}
    </div>
  );
}

function TimeSlotGroup({ time, games, expandedId, onToggle, watchedIds, onWatch, isPro, onLineHistory, sport }) {
  return (
    <div style={{ marginBottom: 18 }}>
      <div style={{
        display: 'flex', alignItems: 'center', gap: 10,
        marginBottom: 8, padding: '0 2px',
      }}>
        <span style={{
          fontFamily: "'IBM Plex Mono', var(--font-mono), monospace",
          fontSize: '11px', fontWeight: 500,
          color: '#7A8494', letterSpacing: '0.04em',
        }}>{time}</span>
        <div style={{ flex: 1, height: 1, background: 'rgba(255,255,255,0.06)' }} />
        <span style={{
          fontFamily: "'IBM Plex Mono', var(--font-mono), monospace",
          fontSize: '10px', color: '#7A8494',
        }}>
          {games.length} {games.length === 1 ? 'game' : 'games'}
        </span>
      </div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
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
            sport={sport}
          />
        ))}
      </div>
    </div>
  );
}

function FilterTabs({ active, onChange, hasLive, hasModel }) {
  let tabs = hasLive ? ['All', 'Upcoming', 'Live', 'Final'] : ['All', 'Upcoming', 'Final'];
  if (hasModel) tabs = [...tabs, 'Passed'];
  return (
    <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
      {tabs.map(tab => {
        const isActive = active === tab;
        return (
          <button key={tab} onClick={() => onChange(tab)} style={{
            fontFamily: "'IBM Plex Mono', var(--font-mono), monospace",
            fontSize: '11px', fontWeight: 500,
            padding: '10px 16px', minHeight: '40px', borderRadius: 6, cursor: 'pointer',
            transition: 'all 0.15s ease',
            border: isActive ? '1px solid rgba(255,255,255,0.1)' : '1px solid rgba(255,255,255,0.06)',
            background: isActive ? '#141A2E' : 'transparent',
            color: isActive ? '#E8ECF4' : '#7A8494',
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

function SortPicker({ active, onChange, isPro, sport }) {
  const opts = (isPro ? SORT_OPTIONS : SORT_OPTIONS.filter(o => o.key !== 'edge')).map(o =>
    o.key === 'spread' ? { ...o, label: sportDisplay(sport).spreadLabel } : o
  );
  return (
    <div style={{ display: 'flex', gap: 6 }}>
      {opts.map(opt => {
        const isActive = active === opt.key;
        return (
          <button key={opt.key} onClick={() => onChange(opt.key)} style={{
            fontFamily: "'IBM Plex Mono', var(--font-mono), monospace",
            fontSize: '10px', fontWeight: 500, letterSpacing: '0.8px',
            padding: '8px 12px', minHeight: '36px', borderRadius: 3, cursor: 'pointer',
            border: 'none',
            background: isActive ? '#141A2E' : 'transparent',
            color: isActive ? '#E8ECF4' : '#7A8494',
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

function LiveBadge({ state, period, clock, sport }) {
  const cfg = sportDisplay(sport);
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
        {cfg.periodLabel(period)}{cfg.showClock && clock ? ` ${clock}` : ''}
      </span>
    );
  }
  if (state === 'STATUS_HALFTIME') {
    return (
      <span style={{
        fontSize: '0.62rem', fontWeight: 700, letterSpacing: '0.06em',
        padding: '1px 5px', borderRadius: 3,
        background: 'rgba(251,191,36,0.12)', color: '#f59e0b',
      }}>{cfg.halftimeLabel}</span>
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

function TableView({ games, isPro, onLineHistory, sport }) {
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
              <th style={thStyle}>{sportDisplay(sport).spreadLabel}</th>
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
                        {g.sharp_action && <span style={{ fontSize: '0.625rem', color: (SHARP_CONF[g.sharp_action.confidence] || SHARP_CONF.low).color }}>⚡</span>}
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
                        fontFamily: 'var(--font-mono)', fontSize: '0.625rem', fontWeight: 700,
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

function fmtEdgePct(val) {
  if (val == null) return '—';
  const n = parseFloat(val);
  return `${n > 0 ? '+' : ''}${n.toFixed(1)}%`;
}

export default function MarketView({ onBack }) {
  const { user } = useAuth();
  const isPro = user && (user.is_premium || user.subscription_status === 'active' || user.subscription_status === 'trial' || user.founding_member);
  const { sport } = useSport();
  const { data, loading, refetch: refetchMarket } = useApi(sportQuery('/picks/market', sport));
  const { data: reportData } = useApi(sportQuery('/public/market-report', sport), { pollInterval: 300000 });
  const { data: watchedData, refetch: refetchWatched } = useApi(sportQuery('/picks/watched', sport));
  const [filter, setFilter] = useState('All');
  const [sort, setSort] = useState('time');
  const [autoSorted, setAutoSorted] = useState(false);
  const [expandedId, setExpandedId] = useState(null);
  const [liveScores, setLiveScores] = useState({});
  const [watchedIds, setWatchedIds] = useState(new Set());
  const [lineHistoryGame, setLineHistoryGame] = useState(null);

  useEffect(() => { trackEvent('view_market_scan', { sport }); }, [sport]);

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

  const games = useMemo(() => {
    let merged = rawGames.map(g => {
      const baseStatus = g.status === 'in_progress' ? 'live' : (g.status || 'scheduled');
      const updated = { ...g, status: baseStatus };
      return updated;
    });
    if (Object.keys(liveScores).length > 0) {
      merged = merged.map(g => {
        const key = normalizeTeam(g.home);
        const live = liveScores[key];
        if (!live) return g;
        const isLive = live.state === 'STATUS_IN_PROGRESS' || live.state === 'STATUS_HALFTIME';
        const isFinal = live.state === 'STATUS_FINAL';
        const updated = { ...g };
        if (live.home_record && (!g.home_record || g.home_record === 'N/A')) updated.home_record = live.home_record;
        if (live.away_record && (!g.away_record || g.away_record === 'N/A')) updated.away_record = live.away_record;
        if (!isLive && !isFinal) return updated;
        return {
          ...updated,
          home_score: live.home_score,
          away_score: live.away_score,
          status: isFinal ? 'final' : 'live',
          live_clock: live.clock,
          live_period: live.period,
          live_state: live.state,
        };
      });
    }
    return merged;
  }, [rawGames, liveScores]);

  const hasLive = games.some(g => g.status === 'live');

  useEffect(() => {
    fetchLiveScores();
  }, [fetchLiveScores]);

  useEffect(() => {
    if (!hasLive) return;
    const interval = setInterval(fetchLiveScores, 15000);
    return () => clearInterval(interval);
  }, [hasLive, fetchLiveScores]);

  const filtered = useMemo(() => {
    if (filter === 'All') return games;
    if (filter === 'Live') return games.filter(g => g.status === 'live');
    if (filter === 'Upcoming') return games.filter(g => g.status === 'scheduled');
    if (filter === 'Final') return games.filter(g => g.status === 'final');
    if (filter === 'Passed') return games.filter(g => g.model && !g.model.passes);
    return games;
  }, [games, filter]);

  const sorted = useMemo(() => sortGames(filtered, sort), [filtered, sort]);

  const stateSorted = useMemo(() => {
    const finals = sorted.filter(g => g.status === 'final');
    const live = sorted.filter(g => g.status === 'live');
    const upcoming = sorted.filter(g => g.status === 'scheduled');
    return { finals, live, upcoming };
  }, [sorted]);

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
          sport,
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
            fontFamily: "'IBM Plex Serif', var(--font-serif), serif",
            fontSize: '22px', fontWeight: 600,
            color: '#E8ECF4', margin: 0,
          }}>Market Intelligence</h1>
        </div>
        <div style={{
          display: 'flex', alignItems: 'center', gap: 6, marginLeft: 36,
          fontFamily: "'IBM Plex Mono', var(--font-mono), monospace",
          fontSize: '11px', color: '#7A8494',
        }}>
          <span>{data?.date || 'Today'}</span>
          <span>&middot;</span>
          <span>{games.length} game{games.length !== 1 ? 's' : ''}</span>
          {hasModelData && (
            <>
              <span>&middot;</span>
              <span style={{ color: '#5A9E72' }}>Model active</span>
            </>
          )}
        </div>
        <div style={{
          marginLeft: 36, marginTop: 2,
          fontFamily: "'IBM Plex Mono', var(--font-mono), monospace",
          fontSize: '11px', fontStyle: 'italic',
          color: '#7A8494',
        }}>Selective by design.</div>
      </div>

      {/* Body */}
      <div style={{ padding: '14px 12px 100px' }}>
        {/* Daily Market Brief */}
        <section style={{ marginBottom: '24px' }}>
          <div style={{
            fontFamily: 'var(--font-mono)', fontSize: '10px', fontWeight: 700,
            letterSpacing: '0.12em', textTransform: 'uppercase',
            color: 'var(--text-tertiary)', marginBottom: '10px',
          }}>Daily Market Brief</div>
          <DailyMarketReport report={reportData} />
        </section>

        {games.length > 0 && (
          <div style={{ marginBottom: 18 }}>
            <div style={{
              display: 'flex', justifyContent: 'space-between', alignItems: 'center',
              gap: 8, marginBottom: 8,
            }}>
              <FilterTabs active={filter} onChange={setFilter} hasLive={hasLive} hasModel={hasModelData} />
            </div>
            <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
              <SortPicker active={sort} onChange={setSort} isPro={isPro} sport={sport} />
            </div>
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
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
            {(stateSorted.finals.length > 0 || stateSorted.live.length > 0) ? (
              <>
                {stateSorted.finals.length > 0 && (
                  <>
                    <div style={{
                      fontFamily: "'IBM Plex Mono', var(--font-mono), monospace",
                      fontSize: '9px', fontWeight: 700, letterSpacing: '2px',
                      textTransform: 'uppercase', color: '#4a5568',
                      padding: '8px 2px 4px',
                    }}>FINAL</div>
                    {stateSorted.finals.map(g => (
                      <GameRow key={g.id} game={g} expanded={expandedId === g.id}
                        onToggle={() => handleToggle(g.id)} watching={watchedIds.has(g.id)}
                        onWatch={() => handleWatch(g)} isPro={isPro}
                        onLineHistory={setLineHistoryGame} sport={sport} />
                    ))}
                  </>
                )}
                {stateSorted.live.length > 0 && (
                  <>
                    <div style={{
                      fontFamily: "'IBM Plex Mono', var(--font-mono), monospace",
                      fontSize: '9px', fontWeight: 700, letterSpacing: '2px',
                      textTransform: 'uppercase', color: '#5A9E72',
                      padding: '8px 2px 4px',
                    }}>LIVE</div>
                    {stateSorted.live.map(g => (
                      <GameRow key={g.id} game={g} expanded={expandedId === g.id}
                        onToggle={() => handleToggle(g.id)} watching={watchedIds.has(g.id)}
                        onWatch={() => handleWatch(g)} isPro={isPro}
                        onLineHistory={setLineHistoryGame} sport={sport} />
                    ))}
                  </>
                )}
                {stateSorted.upcoming.length > 0 && (
                  <>
                    <div style={{
                      fontFamily: "'IBM Plex Mono', var(--font-mono), monospace",
                      fontSize: '9px', fontWeight: 700, letterSpacing: '2px',
                      textTransform: 'uppercase', color: '#4a5568',
                      padding: '8px 2px 4px',
                    }}>UPCOMING</div>
                    {stateSorted.upcoming.map(g => (
                      <GameRow key={g.id} game={g} expanded={expandedId === g.id}
                        onToggle={() => handleToggle(g.id)} watching={watchedIds.has(g.id)}
                        onWatch={() => handleWatch(g)} isPro={isPro}
                        onLineHistory={setLineHistoryGame} sport={sport} />
                    ))}
                  </>
                )}
              </>
            ) : (
              sorted.map(g => (
                <GameRow key={g.id} game={g} expanded={expandedId === g.id}
                  onToggle={() => handleToggle(g.id)} watching={watchedIds.has(g.id)}
                  onWatch={() => handleWatch(g)} isPro={isPro}
                  onLineHistory={setLineHistoryGame} sport={sport} />
              ))
            )}
          </div>
        )}

        <p style={{
          fontFamily: "'IBM Plex Mono', var(--font-mono), monospace",
          fontSize: '10px', color: '#7A8494',
          textAlign: 'center', marginTop: 20, lineHeight: 1.6,
        }}>
          Lines sourced from DraftKings, FanDuel, BetMGM, Caesars, PointsBet, BetRivers.
          Best available shown.
        </p>
      </div>
    </div>
    {lineHistoryGame && (
      <LineHistoryModal game={lineHistoryGame} onClose={() => setLineHistoryGame(null)} />
    )}
    </PullToRefresh>
  );
}
