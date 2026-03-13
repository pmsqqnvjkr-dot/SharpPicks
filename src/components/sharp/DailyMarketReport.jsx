import { useState } from 'react';
import { useApi } from '../../hooks/useApi';
import { useSport, sportQuery } from '../../hooks/useSport';

const REGIME_STYLES = {
  Exploitable: {
    color: '#34D399',
    glow: 'rgba(52, 211, 153, 0.12)',
    border: 'rgba(52, 211, 153, 0.35)',
    accent: 'rgba(52, 211, 153, 0.08)',
  },
  Active: {
    color: '#FBBF24',
    glow: 'rgba(251, 191, 36, 0.12)',
    border: 'rgba(251, 191, 36, 0.30)',
    accent: 'rgba(251, 191, 36, 0.06)',
  },
  Moderate: {
    color: 'var(--text-secondary)',
    glow: 'rgba(148, 163, 184, 0.08)',
    border: 'var(--color-border)',
    accent: 'rgba(148, 163, 184, 0.04)',
  },
  Efficient: {
    color: 'var(--text-tertiary)',
    glow: 'rgba(100, 116, 139, 0.06)',
    border: 'var(--color-border)',
    accent: 'rgba(100, 116, 139, 0.03)',
  },
};

const label = {
  fontFamily: 'var(--font-mono)', fontSize: 'var(--text-label-size)',
  fontWeight: 700, letterSpacing: '0.08em', textTransform: 'uppercase',
  color: 'var(--text-tertiary)', lineHeight: 1,
};

const metricNum = {
  fontFamily: 'var(--font-mono)', fontSize: 'var(--text-metric)',
  fontWeight: 700, fontVariantNumeric: 'tabular-nums',
  color: 'var(--text-primary)', lineHeight: 1,
};

const divider = {
  height: '1px', background: 'var(--color-border)',
  margin: 'var(--space-md) 0',
};

export default function DailyMarketReport() {
  const { sport } = useSport();
  const { data, loading } = useApi(sportQuery('/public/market-report', sport), { pollInterval: 300000 });
  const [expanded, setExpanded] = useState(false);

  if (loading || !data || !data.available) return null;

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
  const rs = REGIME_STYLES[regime] || REGIME_STYLES.Efficient;
  const dist = data.edge_distribution || {};

  return (
    <div style={{
      backgroundColor: 'var(--surface-1)',
      borderRadius: '14px',
      border: `1px solid ${rs.border}`,
      borderTop: `2px solid ${rs.color}`,
      padding: 'var(--space-md)',
      marginBottom: 'var(--space-md)',
    }}>
      <button
        onClick={() => setExpanded(e => !e)}
        style={{
          width: '100%', background: 'none', border: 'none', padding: 0,
          cursor: 'pointer', textAlign: 'left',
        }}
      >
        {/* Title row */}
        <div style={{
          display: 'flex', justifyContent: 'space-between', alignItems: 'center',
          marginBottom: '16px',
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span style={{ ...label, marginBottom: 0, fontSize: '9px' }}>Market Intelligence</span>
            <span style={{
              fontFamily: 'var(--font-mono)', fontSize: '9px',
              color: 'var(--text-tertiary)', opacity: 0.5,
            }}>&mdash;</span>
            <span style={{
              fontFamily: 'var(--font-mono)', fontSize: '9px', fontWeight: 600,
              color: 'var(--text-tertiary)', letterSpacing: '0.04em', textTransform: 'uppercase',
            }}>{today}</span>
          </div>
          <svg
            width="14" height="14" viewBox="0 0 24 24" fill="none"
            stroke="var(--text-tertiary)" strokeWidth="2" strokeLinecap="round"
            style={{ transition: 'transform 0.2s', transform: expanded ? 'rotate(180deg)' : 'rotate(0deg)', flexShrink: 0 }}
          >
            <polyline points="6 9 12 15 18 9" />
          </svg>
        </div>

        {/* Regime — the hero */}
        <div style={{
          textAlign: 'center',
          padding: '18px 0 20px',
          marginBottom: '16px',
          borderRadius: '10px',
          background: rs.glow,
        }}>
          <div style={{
            fontFamily: 'var(--font-mono)', fontSize: '9px', fontWeight: 700,
            letterSpacing: '0.12em', textTransform: 'uppercase',
            color: 'var(--text-tertiary)', marginBottom: '8px',
          }}>Market Regime</div>
          <div style={{
            fontFamily: 'var(--font-serif)', fontSize: '28px', fontWeight: 700,
            color: rs.color, letterSpacing: '0.02em', textTransform: 'uppercase',
            lineHeight: 1,
          }}>{regime}</div>
        </div>

        {/* Key stats — two columns: Edges + Efficiency */}
        <div style={{
          display: 'grid', gridTemplateColumns: '1fr 1fr',
          gap: '1px', marginBottom: data.largest_edge != null ? '14px' : 0,
        }}>
          <div style={{
            textAlign: 'center', padding: '8px 0',
            borderRight: '1px solid var(--color-border)',
          }}>
            <div style={{
              fontFamily: 'var(--font-mono)', fontSize: '28px', fontWeight: 700,
              fontVariantNumeric: 'tabular-nums', lineHeight: 1,
              color: data.edges_detected > 0 ? rs.color : 'var(--text-primary)',
            }}>{data.edges_detected}</div>
            <div style={{
              fontFamily: 'var(--font-mono)', fontSize: '9px', fontWeight: 600,
              letterSpacing: '0.08em', textTransform: 'uppercase',
              color: 'var(--text-tertiary)', marginTop: '5px',
            }}>Edges Detected</div>
          </div>
          <div style={{ textAlign: 'center', padding: '8px 0' }}>
            <div style={{
              fontFamily: 'var(--font-mono)', fontSize: '28px', fontWeight: 700,
              fontVariantNumeric: 'tabular-nums', lineHeight: 1,
              color: data.market_efficiency_pct <= 50 ? rs.color : 'var(--text-primary)',
            }}>{data.market_efficiency_pct}%</div>
            <div style={{
              fontFamily: 'var(--font-mono)', fontSize: '9px', fontWeight: 600,
              letterSpacing: '0.08em', textTransform: 'uppercase',
              color: 'var(--text-tertiary)', marginTop: '5px',
            }}>Efficiency</div>
          </div>
        </div>

        {/* Largest edge callout */}
        {data.largest_edge != null && (
          <div style={{
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            gap: '8px', padding: '8px 0 2px',
          }}>
            <span style={{
              fontFamily: 'var(--font-mono)', fontSize: '9px', fontWeight: 700,
              letterSpacing: '0.08em', textTransform: 'uppercase',
              color: 'var(--text-tertiary)',
            }}>Largest Edge</span>
            <span style={{
              fontFamily: 'var(--font-mono)', fontSize: '18px', fontWeight: 700,
              fontVariantNumeric: 'tabular-nums',
              color: rs.color,
            }}>+{data.largest_edge}%</span>
            {data.largest_edge_game && (
              <span style={{
                fontFamily: 'var(--font-mono)', fontSize: '11px',
                color: 'var(--text-tertiary)',
              }}>{data.largest_edge_game}</span>
            )}
          </div>
        )}
      </button>

      {/* Expanded detail */}
      {expanded && (
        <div style={{ marginTop: 'var(--space-md)' }}>
          <div style={divider} />

          {/* Secondary metrics */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-sm)', marginBottom: 'var(--space-md)' }}>
            <MetricRow label="Markets analyzed" value={data.games_analyzed} />
            <MetricRow
              label="Signals generated"
              value={data.qualified_signals}
              highlight={data.qualified_signals > 0}
            />
            <MetricRow
              label="Signal density"
              value={`${data.signal_density}%`}
              highlight={data.signal_density >= 40}
            />
          </div>

          {/* Edge Distribution */}
          {data.edges_detected > 0 && (
            <>
              <div style={divider} />
              <div style={{ marginBottom: 'var(--space-md)' }}>
                <div style={{ ...label, marginBottom: '8px', fontSize: '9px' }}>Edge Distribution</div>
                <div style={{ display: 'flex', gap: 'var(--space-lg)' }}>
                  <EdgeCategory label="Strong" count={dist.strong || 0} threshold="≥10%" />
                  <EdgeCategory label="Moderate" count={dist.moderate || 0} threshold="7–10%" />
                  <EdgeCategory label="Weak" count={dist.weak || 0} threshold="5–7%" />
                </div>
              </div>
            </>
          )}

          {/* Market Lean — Sentiment */}
          {data.market_lean && data.market_lean.total_edges > 0 && (
            <>
              <div style={divider} />
              <div style={{ marginBottom: 'var(--space-md)' }}>
                <div style={{ ...label, marginBottom: '10px', fontSize: '9px' }}>Model Favoring</div>
                <div style={{ display: 'flex', gap: '16px', alignItems: 'center' }}>
                  <div style={{ flex: 1 }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '4px' }}>
                      <span style={{
                        fontFamily: 'var(--font-mono)', fontSize: '11px',
                        color: 'rgba(96,165,250,0.9)', fontWeight: 600,
                      }}>Favorites</span>
                      <span style={{
                        fontFamily: 'var(--font-mono)', fontSize: '11px',
                        color: 'rgba(96,165,250,0.9)', fontWeight: 700,
                        fontVariantNumeric: 'tabular-nums',
                      }}>{data.market_lean.favorite_pct}%</span>
                    </div>
                    <div style={{ width: '100%', height: 6, borderRadius: 3, background: 'rgba(255,255,255,0.06)' }}>
                      <div style={{
                        width: `${data.market_lean.favorite_pct}%`,
                        height: '100%', borderRadius: 3,
                        background: 'rgba(96,165,250,0.7)',
                        transition: 'width 0.3s ease',
                      }} />
                    </div>
                  </div>
                  <div style={{ flex: 1 }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '4px' }}>
                      <span style={{
                        fontFamily: 'var(--font-mono)', fontSize: '11px',
                        color: '#FBBF24', fontWeight: 600,
                      }}>Underdogs</span>
                      <span style={{
                        fontFamily: 'var(--font-mono)', fontSize: '11px',
                        color: '#FBBF24', fontWeight: 700,
                        fontVariantNumeric: 'tabular-nums',
                      }}>{data.market_lean.underdog_pct}%</span>
                    </div>
                    <div style={{ width: '100%', height: 6, borderRadius: 3, background: 'rgba(255,255,255,0.06)' }}>
                      <div style={{
                        width: `${data.market_lean.underdog_pct}%`,
                        height: '100%', borderRadius: 3,
                        background: 'rgba(251,191,36,0.7)',
                        transition: 'width 0.3s ease',
                      }} />
                    </div>
                  </div>
                </div>
                <div style={{
                  fontFamily: 'var(--font-mono)', fontSize: '10px',
                  color: 'var(--text-tertiary)', marginTop: '6px',
                  textAlign: 'center',
                }}>
                  {data.market_lean.underdog_pct > data.market_lean.favorite_pct
                    ? `Underdogs today — ${data.market_lean.underdogs} signal${data.market_lean.underdogs !== 1 ? 's' : ''}`
                    : data.market_lean.favorite_pct > data.market_lean.underdog_pct
                    ? `Favorites today — ${data.market_lean.favorites} signal${data.market_lean.favorites !== 1 ? 's' : ''}`
                    : 'Split lean — balanced edge distribution'
                  }
                </div>
              </div>
            </>
          )}

          {/* Daily Briefing */}
          {(data.briefing?.length > 0 || data.insight) && (
            <>
              <div style={divider} />
              <div style={{ marginBottom: 'var(--space-md)' }}>
                <div style={{ ...label, marginBottom: '8px', fontSize: '9px' }}>Today&apos;s Briefing</div>
                {data.briefing?.length > 0 ? (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '5px' }}>
                    {data.briefing.map((line, i) => (
                      <div key={i} style={{
                        fontSize: '13px', color: 'var(--text-secondary)',
                        lineHeight: 1.5, display: 'flex', gap: '6px',
                      }}>
                        <span style={{ color: 'var(--color-signal)', flexShrink: 0, fontSize: '11px', marginTop: '2px' }}>›</span>
                        <span>{line}</span>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p style={{
                    fontSize: '13px', fontStyle: 'italic',
                    color: 'var(--text-secondary)', lineHeight: 1.5, margin: 0,
                  }}>{data.insight}</p>
                )}
              </div>
            </>
          )}

          <div style={divider} />

          {/* Scan Timestamp */}
          {scanTime && (
            <div style={{
              fontSize: '11px', color: 'var(--text-tertiary)',
              fontFamily: 'var(--font-mono)', marginBottom: 'var(--space-sm)',
            }}>
              Intelligence updated {scanTime}
            </div>
          )}

          <div style={{
            fontSize: '11px', color: 'var(--text-tertiary)',
            fontFamily: 'var(--font-mono)', lineHeight: 1.5,
            fontStyle: 'italic',
          }}>
            Selective by design. Only qualified edges become signals.
          </div>
        </div>
      )}
    </div>
  );
}

function MetricRow({ label: labelText, value, highlight }) {
  return (
    <div style={{
      display: 'flex', justifyContent: 'space-between', alignItems: 'center',
    }}>
      <span style={{
        fontSize: 'var(--text-metric)', color: 'var(--text-secondary)',
      }}>{labelText}</span>
      <span style={{
        ...metricNum,
        color: highlight ? 'var(--color-signal)' : 'var(--text-primary)',
      }}>{value}</span>
    </div>
  );
}

function EdgeCategory({ label: labelText, count, threshold }) {
  return (
    <div>
      <div style={{
        fontFamily: 'var(--font-mono)', fontSize: '18px', fontWeight: 700,
        fontVariantNumeric: 'tabular-nums',
        color: count > 0 ? 'var(--text-primary)' : 'var(--text-tertiary)',
      }}>{count}</div>
      <div style={{
        fontSize: '11px', color: 'var(--text-secondary)',
        fontFamily: 'var(--font-mono)', marginTop: '2px',
      }}>{labelText}</div>
      <div style={{
        fontSize: '9px', color: 'var(--text-tertiary)',
        fontFamily: 'var(--font-mono)', marginTop: '1px',
      }}>{threshold}</div>
    </div>
  );
}
