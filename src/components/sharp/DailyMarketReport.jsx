import { useState } from 'react';
import { useApi } from '../../hooks/useApi';
import { useSport, sportQuery } from '../../hooks/useSport';

const green = '#5A9E72';
const greenDim = '#5A9E72';
const blue = '#4A8EC2';
const amber = '#d4a24e';
const red = '#C4686B';
const border = 'rgba(90, 158, 114, 0.12)';
const bgInner = '#131f36';
const textLabel = '#8899AA';
const textSec = '#9EAAB8';
const textDim = '#7A8494';

const labelStyle = {
  fontFamily: 'var(--font-mono)', fontSize: '10px', fontWeight: 500,
  letterSpacing: '1px', textTransform: 'uppercase', color: textLabel,
};

export default function DailyMarketReport({ report: reportProp }) {
  const { sport } = useSport();
  const { data: fetchedData, loading } = useApi(sportQuery('/public/market-report', sport), { pollInterval: 300000 });
  const data = reportProp ?? fetchedData;

  if (reportProp ? !data?.available : (loading || !data || !data.available)) return null;

  const today = new Date().toLocaleDateString('en-US', {
    month: 'long', day: 'numeric', timeZone: 'America/New_York',
  });

  const scanTime = data.last_updated ? (() => {
    try {
      const d = new Date(data.last_updated);
      const et = new Date(d.toLocaleString('en-US', { timeZone: 'America/New_York' }));
      const h = et.getHours();
      const m = et.getMinutes().toString().padStart(2, '0');
      const ampm = h >= 12 ? 'PM' : 'AM';
      return `${h % 12 || 12}:${m} ${ampm} ET`;
    } catch { return null; }
  })() : null;

  const regime = data.regime || 'Efficient';
  const regimeDisplay = regime.toLowerCase().replace(/\b\w/g, c => c.toUpperCase());
  const regimeSub = data.regime_micro || '';
  const dist = data.edge_distribution || {};
  const lean = data.market_lean || {};

  return (
    <div>
      <div style={{
        background: 'var(--bg-card, #0f1d33)',
        border: `1px solid ${border}`,
        borderRadius: '8px',
        padding: '14px 16px',
      }}>
        {/* Header — inside card */}
        <div style={{
          display: 'flex', alignItems: 'center', justifyContent: 'space-between',
          marginBottom: '14px',
        }}>
          <span style={{
            fontFamily: 'var(--font-mono)', fontSize: '10px', fontWeight: 500,
            letterSpacing: '1.2px', color: green, textTransform: 'uppercase',
          }}>Market Intelligence</span>
          <span style={{
            fontFamily: 'var(--font-mono)', fontSize: '10px',
            color: textDim, letterSpacing: '0.5px',
          }}>{today}</span>
        </div>

        {/* 3-column metric grid */}
        <div style={{
          display: 'grid', gridTemplateColumns: '1fr 1fr 1fr',
          gap: '12px', marginBottom: '14px',
        }}>
          <MetricCell label="MEI" value={data.market_efficiency_index} green tooltip="Market Efficiency Index measures how much opportunity the model detects across today's slate. Higher = more mispricing. Below 30 is quiet; above 70 is rare." />
          <div style={{
            background: bgInner, border: `1px solid ${border}`,
            borderRadius: '6px', padding: '10px',
          }}>
            <div style={{ ...labelStyle, marginBottom: '4px' }}>Regime</div>
            <div style={{
              fontFamily: 'var(--font-mono)', fontSize: '14px', fontWeight: 600,
              color: green, lineHeight: 1,
            }}>{regimeDisplay}</div>
            {regimeSub && (
              <div style={{
                fontFamily: 'var(--font-sans)', fontSize: '10px',
                color: textSec, marginTop: '3px',
              }}>{regimeSub}</div>
            )}
          </div>
          <MetricCell
            label="Top Edge"
            value={data.largest_edge != null ? `+${data.largest_edge}%` : '--'}
            green
          />
        </div>

        {/* MEI Historical Context — always show when MEI exists */}
        {data.market_efficiency_index != null && (
          <div style={{
            borderTop: '0.5px solid #1e3050', paddingTop: 10, marginBottom: 10,
          }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <span style={{
                fontFamily: 'var(--font-mono)', fontSize: '10px', color: textDim,
              }}>7d avg: <span style={{ color: '#c8cdd4' }}>{data.mei?.seven_day_avg ?? data.market_efficiency_index}</span></span>
              <MeiSparkline data={data.mei?.sparkline} current={data.market_efficiency_index} />
              <span style={{
                fontFamily: 'var(--font-mono)', fontSize: '10px', color: textDim,
              }}>Szn avg: <span style={{ color: '#c8cdd4' }}>{data.mei?.season_avg ?? data.market_efficiency_index}</span></span>
            </div>
          </div>
        )}

        {/* Edge Distribution Bar */}
        {(dist.strong > 0 || dist.moderate > 0 || dist.weak > 0) && (() => {
          const total = (dist.strong || 0) + (dist.moderate || 0) + (dist.weak || 0);
          const strongPct = total > 0 ? ((dist.strong || 0) / total * 100) : 0;
          const modPct = total > 0 ? ((dist.moderate || 0) / total * 100) : 0;
          const weakPct = total > 0 ? ((dist.weak || 0) / total * 100) : 0;
          return (
            <div style={{ borderTop: '0.5px solid #1e3050', paddingTop: 10, marginBottom: 10 }}>
              <div style={{
                height: 8, borderRadius: 4, display: 'flex', overflow: 'hidden',
                background: '#1a2a42',
              }}>
                {strongPct > 0 && <div style={{ width: `${strongPct}%`, background: green }} />}
                {modPct > 0 && <div style={{ width: `${modPct}%`, background: amber }} />}
                {weakPct > 0 && <div style={{ width: `${weakPct}%`, background: '#4a5568' }} />}
              </div>
              <div style={{ display: 'flex', gap: 16, marginTop: 6 }}>
                <EdgeDot color={green} count={dist.strong || 0} label="Strong" />
                <EdgeDot color={amber} count={dist.moderate || 0} label="Moderate" />
                <EdgeDot color="#4a5568" count={dist.weak || 0} label="Weak" />
              </div>
            </div>
          );
        })()}

      </div>

      {/* Market Signal — standalone callout */}
      {(data.briefing?.[0] || data.insight) && (
        <div style={{
          background: '#141A2E', border: `1px solid ${border}`,
          borderLeft: `3px solid ${green}`,
          borderRadius: '6px', padding: '14px', marginTop: '10px',
        }}>
          <div style={{
            fontFamily: 'var(--font-mono)', fontSize: '10px', fontWeight: 500,
            letterSpacing: '1.5px', color: green, textTransform: 'uppercase',
            marginBottom: '6px',
          }}>Market Signal</div>
          <div style={{
            fontFamily: "'IBM Plex Serif', var(--font-serif), serif", fontSize: '13px',
            color: textSec, lineHeight: 1.5,
          }}>{data.briefing?.[0] || data.insight}</div>
        </div>
      )}

      {/* Line Movement Rollup */}
      {data.line_movement && data.line_movement.games && data.line_movement.games.length > 0 && (
        <div style={{
          background: 'var(--bg-card, #0f1d33)',
          border: `1px solid ${border}`,
          borderRadius: '8px',
          padding: '14px 16px',
          marginTop: 10,
        }}>
          <div style={{
            fontFamily: 'var(--font-mono)', fontSize: '10px', fontWeight: 500,
            letterSpacing: '2px', color: green, textTransform: 'uppercase',
            marginBottom: 10,
          }}>LINE MOVEMENT</div>
          {data.line_movement.games.map((g, i) => (
            <div key={i} style={{
              display: 'flex', justifyContent: 'space-between', alignItems: 'center',
              padding: '6px 0',
              borderBottom: i < data.line_movement.games.length - 1 ? '0.5px solid #1e3050' : 'none',
            }}>
              <span style={{ fontFamily: "'IBM Plex Sans', var(--font-sans), sans-serif", fontSize: '12px', fontWeight: 500, color: '#E8ECF4' }}>
                {g.matchup}
              </span>
              <span style={{
                fontFamily: 'var(--font-mono)', fontSize: '11px', fontWeight: 500,
                color: g.direction === 'toward' ? green : g.direction === 'away' ? red : '#4a5568',
              }}>
                {g.direction === 'flat' ? 'No movement' :
                  `${g.direction === 'toward' ? '+' : '-'}${g.movement} ${g.direction === 'toward' ? 'toward model' : 'away from model'}`}
              </span>
            </div>
          ))}
          <div style={{
            borderTop: '0.5px solid #1e3050', paddingTop: 8, marginTop: 4,
          }}>
            <span style={{
              fontFamily: 'var(--font-mono)', fontSize: '11px', color: textSec,
            }}>
              <span style={{ color: green, fontWeight: 600 }}>{data.line_movement.toward_model}</span>
              {' '}of {data.line_movement.games.length} lines moved toward model position
            </span>
          </div>
        </div>
      )}

      {/* Model vs Market Delta */}
      {data.model_market_delta && data.model_market_delta.games && data.model_market_delta.games.length > 0 && (
        <div style={{
          background: 'var(--bg-card, #0f1d33)',
          border: `1px solid ${border}`,
          borderRadius: '8px',
          padding: '14px 16px',
          marginTop: 10,
        }}>
          <div style={{
            fontFamily: 'var(--font-mono)', fontSize: '10px', fontWeight: 500,
            letterSpacing: '2px', color: green, textTransform: 'uppercase',
            marginBottom: 10,
          }}>MODEL VS MARKET DELTA</div>
          {(() => {
            const maxDelta = Math.max(...data.model_market_delta.games.map(g => g.delta), 1);
            return data.model_market_delta.games.map((g, i) => {
              const barColor = g.delta >= 5 ? green : g.delta >= 3 ? amber : '#4a5568';
              return (
                <div key={i} style={{
                  display: 'flex', alignItems: 'center', gap: 10, padding: '5px 0',
                  borderBottom: i < data.model_market_delta.games.length - 1 ? '0.5px solid #1e3050' : 'none',
                }}>
                  <span style={{
                    fontFamily: "'IBM Plex Sans', var(--font-sans), sans-serif", fontSize: '12px', fontWeight: 500,
                    color: '#E8ECF4', minWidth: 80, flexShrink: 0,
                  }}>{g.side}</span>
                  <div style={{
                    flex: 1, height: 6, background: '#1a2a42', borderRadius: 3,
                    overflow: 'hidden',
                  }}>
                    <div style={{
                      height: '100%', borderRadius: 3, background: barColor,
                      width: `${(g.delta / maxDelta) * 100}%`,
                      transition: 'width 0.3s ease',
                    }} />
                  </div>
                  <span style={{
                    fontFamily: 'var(--font-mono)', fontSize: '11px', fontWeight: 500,
                    color: barColor, minWidth: 48, textAlign: 'right',
                  }}>{g.delta} pts</span>
                </div>
              );
            });
          })()}
          <div style={{
            borderTop: '0.5px solid #1e3050', paddingTop: 8, marginTop: 4,
          }}>
            <span style={{ fontFamily: 'var(--font-mono)', fontSize: '11px', color: textSec }}>
              Avg model-market delta: <span style={{ color: green, fontWeight: 600 }}>{data.model_market_delta.avg_delta} pts</span>
            </span>
          </div>
        </div>
      )}

      {/* Timestamp */}
      {scanTime && (
        <div style={{
          fontFamily: 'var(--font-mono)', fontSize: '10px',
          color: textDim, textAlign: 'center',
          marginTop: '20px', letterSpacing: '0.5px',
        }}>
          Intelligence updated <span style={{ color: greenDim }}>{scanTime}</span>
        </div>
      )}
    </div>
  );
}

function MetricCell({ label, value, green: isGreen, tooltip }) {
  return (
    <div style={{
      background: bgInner, border: `1px solid ${border}`,
      borderRadius: '6px', padding: '10px',
    }}>
      <div style={{ ...labelStyle, marginBottom: '4px', display: 'flex', alignItems: 'center' }}>
        {label}
        {tooltip && <InfoTooltip text={tooltip} />}
      </div>
      <div style={{
        fontFamily: 'var(--font-mono)', fontSize: '20px', fontWeight: 600,
        color: isGreen ? green : 'var(--text-primary)', lineHeight: 1,
      }}>{value}</div>
    </div>
  );
}

function InfoTooltip({ text }) {
  const [open, setOpen] = useState(false);
  return (
    <span style={{ position: 'relative', display: 'inline-flex', alignItems: 'center', marginLeft: '6px' }}>
      <button
        onClick={(e) => { e.stopPropagation(); setOpen(!open); }}
        style={{
          width: '16px', height: '16px', borderRadius: '50%',
          backgroundColor: open ? 'rgba(255,255,255,0.12)' : 'rgba(255,255,255,0.06)',
          border: '1px solid var(--stroke-subtle)',
          color: 'var(--text-tertiary)', cursor: 'pointer',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          padding: 0, fontSize: '9px', fontFamily: 'var(--font-sans)', fontWeight: 600,
          lineHeight: 1, transition: 'background-color 0.15s ease',
          flexShrink: 0,
        }}
        aria-label="More info"
      >i</button>
      {open && (
        <>
          <div
            onClick={() => setOpen(false)}
            style={{ position: 'fixed', inset: 0, zIndex: 99 }}
          />
          <div style={{
            position: 'absolute', bottom: '24px', left: 0,
            backgroundColor: '#1a2744', border: '1px solid var(--stroke-subtle)',
            borderRadius: '8px', padding: '10px 12px',
            width: '220px', zIndex: 100,
            boxShadow: '0 8px 24px rgba(0,0,0,0.5)',
          }}>
            <p style={{
              fontFamily: 'var(--font-serif)', fontStyle: 'italic',
              fontSize: '11px', color: 'var(--text-secondary)',
              lineHeight: '1.5', margin: 0,
            }}>{text}</p>
          </div>
        </>
      )}
    </span>
  );
}

function EdgeDot({ color, count, label }) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
      <span style={{ width: '6px', height: '6px', borderRadius: '50%', background: color }} />
      <span style={{
        fontFamily: 'var(--font-mono)', fontSize: '13px', fontWeight: 600,
        color: 'var(--text-primary)',
      }}>{count}</span>
      <span style={{
        fontFamily: 'var(--font-mono)', fontSize: '10px',
        color: textDim, textTransform: 'uppercase', letterSpacing: '0.5px',
      }}>{label}</span>
    </div>
  );
}

function MeiSparkline({ data, current }) {
  const w = 160, h = 28, pad = 4;
  if (!data || data.length === 0) {
    if (current == null) return null;
    const cy = h / 2;
    const dotColor = current >= 50 ? amber : green;
    return (
      <svg width={w} height={h} style={{ display: 'block' }}>
        <line x1={pad} y1={cy} x2={w - pad} y2={cy} stroke="#1e3050" strokeWidth="1" strokeDasharray="3,3" />
        <circle cx={w / 2} cy={cy} r="3.5" fill={dotColor} />
      </svg>
    );
  }
  if (data.length === 1) {
    const cy = h / 2;
    const dotColor = data[0] >= 50 ? amber : green;
    return (
      <svg width={w} height={h} style={{ display: 'block' }}>
        <line x1={pad} y1={cy} x2={w - pad} y2={cy} stroke="#1e3050" strokeWidth="1" strokeDasharray="3,3" />
        <circle cx={w / 2} cy={cy} r="3.5" fill={dotColor} />
      </svg>
    );
  }
  const min = Math.min(...data);
  const max = Math.max(...data);
  const range = max - min || 1;
  const points = data.map((v, i) => {
    const x = pad + (i / (data.length - 1)) * (w - pad * 2);
    const y = pad + (h - pad * 2) - ((v - min) / range) * (h - pad * 2);
    return `${x},${y}`;
  });
  const last = data[data.length - 1];
  const lastX = w - pad;
  const lastY = pad + (h - pad * 2) - ((last - min) / range) * (h - pad * 2);
  const dotColor = last >= 50 ? amber : green;
  return (
    <svg width={w} height={h} style={{ display: 'block' }}>
      <polyline points={points.join(' ')} fill="none" stroke="#4a5568" strokeWidth="1" />
      <circle cx={lastX} cy={lastY} r="3" fill={dotColor} />
    </svg>
  );
}
