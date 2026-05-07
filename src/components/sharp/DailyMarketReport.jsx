import { useApi } from '../../hooks/useApi';
import { useSport, sportQuery } from '../../hooks/useSport';

// v4.3 inline Market Intelligence report. Renders below the MI card
// when the user expands it on home (pick day or pass day). Same data
// as the prior v4 inline (no isPro gating - market context stays
// open for all users; the paywall lives on the specific signal, not
// here). Source design: docs/design-system mockup approved 2026-05-06.
//
// Reads the canonical /public/market-report payload directly when no
// report prop is supplied; otherwise consumes the prop. Field
// references match the public_api.py shape: games_analyzed (not
// total_games), qualified_signals (not signal_count), edges_detected,
// signal_density, mei.{current,seven_day_avg,season_avg,sparkline},
// market_lean.{favorites,underdogs,total_edges}, line_movement.games,
// model_market_delta.games.

const SP = {
  bg: '#0A0D14',
  surface: '#121725',
  surface2: '#1B2030',
  border: 'rgba(255, 255, 255, 0.08)',
  border2: 'rgba(255, 255, 255, 0.05)',
  blue: '#4F86F7',
  green: '#5A9E72',
  greenSoft: 'rgba(90, 158, 114, 0.12)',
  amber: '#F59E0B',
  amberSoft: 'rgba(245, 158, 11, 0.08)',
  redSoft: '#C4868A',
  text: '#E8EAED',
  text2: 'rgba(232, 234, 237, 0.7)',
  text3: 'rgba(232, 234, 237, 0.5)',
  text4: 'rgba(232, 234, 237, 0.35)',
  text5: 'rgba(232, 234, 237, 0.25)',
  fontSans: "'Inter', -apple-system, BlinkMacSystemFont, sans-serif",
  fontMono: "'JetBrains Mono', 'Menlo', ui-monospace, monospace",
  fontSerif: "'IBM Plex Serif', Georgia, serif",
};

function fmtTimeET(iso) {
  if (!iso) return null;
  try {
    const d = new Date(iso);
    if (Number.isNaN(d.getTime())) return null;
    const parts = new Intl.DateTimeFormat('en-US', {
      timeZone: 'America/New_York', hour: 'numeric', minute: '2-digit', hour12: true,
    }).formatToParts(d);
    const h = parts.find((p) => p.type === 'hour')?.value || '';
    const m = parts.find((p) => p.type === 'minute')?.value || '';
    const a = (parts.find((p) => p.type === 'dayPeriod')?.value || '').toUpperCase();
    return `${h}:${m} ${a} ET`;
  } catch { return null; }
}

function titleCase(s) {
  if (!s || typeof s !== 'string') return s;
  return s.charAt(0).toUpperCase() + s.slice(1).toLowerCase();
}

export default function DailyMarketReport({ report: reportProp }) {
  const { sport } = useSport();
  const { data: fetchedData, loading } = useApi(sportQuery('/public/market-report', sport), { pollInterval: 300000 });
  const data = reportProp ?? fetchedData;

  if (reportProp ? !data?.available : (loading || !data || !data.available)) return null;

  const totalGames = data.games_analyzed || 0;
  const signalsFired = data.qualified_signals || 0;
  const dist = data.edge_distribution || {};
  // Backend bucketizes detected edges (>= qualifying threshold) into:
  //   strong   = edge >= 10pp  (STR tier)
  //   moderate = 7 <= edge < 10pp  (MOD tier)
  //   weak     = qualifying threshold <= edge < 7pp  (WK tier)
  // Plus belowThreshold = games with no qualifying edge at all.
  // Beginner's guide promises this exact STR/MOD/WK breakdown.
  const strongEdges = dist.strong || 0;
  const moderateEdges = dist.moderate || 0;
  const weakEdges = dist.weak || 0;
  const edgeCount = data.edges_detected != null ? data.edges_detected : (strongEdges + moderateEdges + weakEdges);
  const belowThreshold = Math.max(0, totalGames - edgeCount);
  const qualifying = moderateEdges; // legacy alias; kept so other call sites compile
  const density = data.signal_density != null
    ? Math.round(data.signal_density)
    : (totalGames > 0 ? Math.round((signalsFired / totalGames) * 100) : 0);

  const meiCurrent = data.mei?.current ?? data.market_efficiency_index ?? null;
  const seasonAvg = data.mei?.season_avg;
  const sevenAvg = data.mei?.seven_day_avg;
  const sevenTrend = meiCurrent != null && sevenAvg != null
    ? (meiCurrent > sevenAvg + 1 ? 'up' : meiCurrent < sevenAvg - 1 ? 'down' : 'flat')
    : 'flat';

  const regimeRaw = data.regime || (meiCurrent != null && meiCurrent >= 60 ? 'Active' : meiCurrent != null && meiCurrent <= 30 ? 'Quiet' : 'Efficient');
  const regimeDisplay = titleCase(regimeRaw);
  const regimeMicro = data.regime_micro || '';
  const topEdge = data.largest_edge != null ? `+${Number(data.largest_edge).toFixed(1)}%` : '—';
  const updatedTime = fmtTimeET(data.last_updated);
  const isCalibration = data.model_phase === 'calibration';

  const lean = data.market_lean || {};
  const leanSide = (lean.underdogs || 0) > (lean.favorites || 0) ? 'underdogs' : 'favorites';
  const leanCounts = {
    underdogs: lean.underdogs || 0,
    favorites: lean.favorites || 0,
    total: lean.total_edges || edgeCount,
  };

  const lmGames = (data.line_movement?.games) || [];
  const lmType = data.line_movement?.movement_type || 'moneyline';
  const lmTowardCount = data.line_movement?.toward_model || 0;
  const lmAwayCount = data.line_movement?.away_from_model || 0;
  const lmNoneCount = data.line_movement?.no_movement || 0;
  const mmdGames = (data.model_market_delta?.games) || [];
  const avgDelta = data.model_market_delta?.avg_delta;
  const sportRunsLabel = (sport || '').toLowerCase() === 'mlb' ? 'runs' : 'pts';

  return (
    <div style={{ display: 'flex', flexDirection: 'column' }}>
      {isCalibration && (
        <div style={{
          background: SP.amberSoft, border: '1px solid rgba(245, 158, 11, 0.22)',
          borderRadius: '10px', padding: '14px 16px', marginBottom: '16px',
          display: 'flex', alignItems: 'flex-start', gap: '12px',
        }}>
          <div style={{
            flexShrink: 0, width: '8px', height: '8px', marginTop: '4px',
            background: SP.amber, borderRadius: '50%',
          }} />
          <div style={{ flex: 1 }}>
            <div style={{
              fontFamily: SP.fontMono, fontSize: '9px',
              letterSpacing: '0.22em', textTransform: 'uppercase', color: SP.amber,
              marginBottom: '4px',
            }}>Calibration Phase</div>
            <div style={{ fontSize: '12px', lineHeight: 1.45, color: SP.text2 }}>
              Edges tracked live. Confidence intervals widen during early-season validation.
            </div>
          </div>
        </div>
      )}

      <div style={{
        display: 'grid', gridTemplateColumns: '1fr 1px 1fr 1px 1fr',
        background: SP.surface, border: `1px solid ${SP.border}`,
        borderRadius: '14px', overflow: 'hidden', marginBottom: '12px',
      }}>
        {[
          { label: 'MEI', value: meiCurrent != null ? String(meiCurrent) : '—', suffix: 'of 100', tone: 'green', size: 32 },
          { label: 'Regime', value: regimeDisplay, suffix: regimeMicro || (meiCurrent != null && meiCurrent >= 80 ? 'high' : meiCurrent != null && meiCurrent >= 50 ? 'moderate' : 'low'), tone: 'text', size: 22 },
          { label: 'Top Edge', value: topEdge, suffix: 'single signal', tone: 'green', size: 32 },
        ].flatMap((cell, i, arr) => [
          <div key={`c-${cell.label}`} style={{ padding: '18px 12px 16px', textAlign: 'center' }}>
            <div style={{
              fontFamily: SP.fontMono, fontSize: '9px',
              letterSpacing: '0.22em', textTransform: 'uppercase', color: SP.text3,
              marginBottom: '8px',
            }}>{cell.label}</div>
            <div style={{
              fontFamily: SP.fontSerif, fontSize: `${cell.size}px`,
              fontWeight: 700, lineHeight: 1, letterSpacing: '-0.02em', marginBottom: '6px',
              paddingTop: cell.label === 'Regime' ? '7px' : 0,
              color: cell.tone === 'green' ? SP.green : SP.text,
            }}>{cell.value}</div>
            <div style={{
              fontFamily: SP.fontMono, fontSize: '11px', color: SP.text3,
              letterSpacing: '0.04em',
            }}>{cell.suffix}</div>
          </div>,
          i < arr.length - 1 ? <div key={`d-${i}`} style={{ background: SP.border }} /> : null,
        ])}
      </div>

      {meiCurrent != null && (
        <div style={{
          background: SP.surface, border: `1px solid ${SP.border}`, borderTop: 'none',
          borderRadius: '0 0 14px 14px', marginTop: '-14px',
          padding: '14px 16px', marginBottom: '22px',
        }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
            <span style={{
              fontFamily: SP.fontMono, fontSize: '9px', letterSpacing: '0.22em',
              textTransform: 'uppercase', color: SP.text4,
            }}>MEI · Where today sits</span>
            <span style={{ fontFamily: SP.fontMono, fontSize: '11px', color: SP.text3 }}>
              7d <span style={{ color: SP.text2 }}>{sevenTrend}</span>
              {seasonAvg != null ? <> · Szn avg <span style={{ color: SP.text2 }}>{seasonAvg}</span></> : null}
            </span>
          </div>
          <div style={{
            position: 'relative', height: '6px', borderRadius: '3px', marginBottom: '6px',
            background: 'linear-gradient(90deg, rgba(196, 134, 138, 0.3) 0%, rgba(245, 158, 11, 0.3) 50%, rgba(90, 158, 114, 0.3) 100%)',
          }}>
            <div style={{
              position: 'absolute', top: '-3px',
              left: `${Math.max(2, Math.min(98, meiCurrent))}%`,
              width: '4px', height: '12px', background: SP.green, borderRadius: '2px',
              transform: 'translateX(-50%)',
            }} />
          </div>
          <div style={{
            display: 'flex', justifyContent: 'space-between',
            fontFamily: SP.fontMono, fontSize: '9px', color: SP.text4, letterSpacing: '0.04em',
          }}>
            <span>0 · Quiet</span><span>50</span><span>100 · Hot</span>
          </div>
        </div>
      )}

      {totalGames > 0 && (
        <div style={{
          background: SP.surface, border: `1px solid ${SP.border}`,
          borderRadius: '14px', padding: '18px 18px 16px', marginBottom: '20px',
        }}>
          <div style={{
            fontFamily: SP.fontMono, fontSize: '10px', fontWeight: 500,
            letterSpacing: '0.22em', textTransform: 'uppercase', color: SP.text3,
            marginBottom: '6px',
          }}>Edge Distribution · {edgeCount} detected across {totalGames} games</div>
          <div style={{
            fontFamily: SP.fontMono, fontSize: '11px', color: SP.text2, letterSpacing: '0.04em',
            marginBottom: '14px',
          }}>
            <span style={{ color: SP.green, fontWeight: 600 }}>{signalsFired}</span> signal{signalsFired === 1 ? '' : 's'} fired ·{' '}
            only Strong (and sometimes Moderate) edges become signals
          </div>
          {/* Stacked bar: 4 segments (Strong / Moderate / Weak / Below threshold) */}
          <div style={{
            height: '10px', background: SP.surface2, borderRadius: '3px',
            overflow: 'hidden', display: 'flex', marginBottom: '14px', gap: '1px',
          }}>
            <div title="Strong" style={{ height: '100%', width: `${(strongEdges / Math.max(1, totalGames)) * 100}%`, background: SP.green }} />
            <div title="Moderate" style={{ height: '100%', width: `${(moderateEdges / Math.max(1, totalGames)) * 100}%`, background: 'rgba(90, 158, 114, 0.55)' }} />
            <div title="Weak" style={{ height: '100%', width: `${(weakEdges / Math.max(1, totalGames)) * 100}%`, background: 'rgba(245, 158, 11, 0.55)' }} />
            <div title="Below threshold" style={{ height: '100%', flex: 1, background: SP.surface2 }} />
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr 1fr', gap: '10px' }}>
            {[
              { label: 'Strong', sublabel: '≥ 10pp', count: strongEdges, dot: SP.green, muted: strongEdges === 0 },
              { label: 'Moderate', sublabel: '7–10pp', count: moderateEdges, dot: 'rgba(90, 158, 114, 0.55)', muted: moderateEdges === 0 },
              { label: 'Weak', sublabel: '3.5–7pp', count: weakEdges, dot: 'rgba(245, 158, 11, 0.55)', muted: weakEdges === 0 },
              { label: 'Below threshold', sublabel: '< 3.5pp', count: belowThreshold, dot: SP.text5, muted: true },
            ].map((c) => (
              <div key={c.label}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '4px' }}>
                  <span style={{ width: 7, height: 7, borderRadius: '50%', background: c.dot }} />
                  <span style={{
                    fontFamily: SP.fontMono, fontSize: '18px', fontWeight: 500,
                    color: c.muted ? SP.text3 : SP.text,
                  }}>{c.count}</span>
                </div>
                <div style={{
                  fontFamily: SP.fontMono, fontSize: '9px',
                  letterSpacing: '0.16em', textTransform: 'uppercase', color: SP.text3,
                }}>{c.label}</div>
                <div style={{
                  fontFamily: SP.fontMono, fontSize: '8px', color: SP.text4,
                  letterSpacing: '0.04em', marginTop: '2px',
                }}>{c.sublabel}</div>
              </div>
            ))}
          </div>
        </div>
      )}

      {edgeCount > 0 && leanCounts.total > 0 && (
        <div style={{
          borderLeft: `2px solid ${SP.green}`, background: SP.greenSoft,
          padding: '18px 20px', borderRadius: '0 10px 10px 0', marginBottom: '24px',
        }}>
          <div style={{
            fontFamily: SP.fontMono, fontSize: '10px', fontWeight: 500,
            letterSpacing: '0.22em', textTransform: 'uppercase', color: SP.green,
            marginBottom: '8px',
          }}>Observation</div>
          <div style={{
            fontFamily: SP.fontSerif, fontSize: '15px', lineHeight: 1.5, color: SP.text,
          }}>
            <Chip>{edgeCount} edge{edgeCount === 1 ? '' : 's'}</Chip>
            {' '}detected with a clear lean toward {leanSide}.{' '}
            <Chip>{leanCounts.underdogs} of {leanCounts.total}</Chip>
            {' '}on dogs, <Chip>{leanCounts.favorites} of {leanCounts.total}</Chip>
            {' '}on favorites.{' '}
            {signalsFired > 0
              ? <>{signalsFired === 1 ? 'One' : signalsFired === 2 ? 'Two' : signalsFired} cleared the discipline filter at <Chip>{density}%</Chip> density.</>
              : <>None cleared the discipline filter.</>
            }
          </div>
        </div>
      )}

      {lmGames.length > 0 && (
        <>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', marginBottom: '12px' }}>
            <h2 style={{ fontFamily: SP.fontSerif, fontSize: '18px', fontWeight: 600, color: SP.text }}>
              {lmType === 'moneyline' ? 'Moneyline Movement' : 'Line Movement'}
            </h2>
            <span style={{
              fontFamily: SP.fontMono, fontSize: '10px', color: SP.text3, letterSpacing: '0.04em',
            }}>{lmGames.length} game{lmGames.length === 1 ? '' : 's'}</span>
          </div>

          <div style={{
            background: SP.surface, border: `1px solid ${SP.border}`,
            borderRadius: '12px', overflow: 'hidden', marginBottom: '12px',
          }}>
            {lmGames.map((g, i) => {
              const isML = lmType === 'moneyline';
              const movement = Number(g.movement) || 0;
              const direction = g.direction;
              const isFlat = direction === 'flat' || direction === 'none' || !direction;
              const significant = isML ? movement >= 20 : movement >= 1.5;
              const tint = direction === 'away' ? SP.redSoft : direction === 'toward' ? SP.green : null;
              const moveColor = direction === 'toward' ? SP.green : direction === 'away' ? SP.redSoft : SP.text4;
              const deltaColor = direction === 'toward'
                ? 'rgba(90, 158, 114, 0.6)'
                : direction === 'away'
                  ? 'rgba(196, 134, 138, 0.6)'
                  : SP.text3;
              const unit = isML ? '¢' : 'pts';
              const showOpenClose = isML && g.ml_open != null && g.ml_now != null;
              return (
                <div
                  key={i}
                  style={{
                    padding: '12px 16px',
                    borderBottom: i < lmGames.length - 1 ? `1px solid ${SP.border2}` : 'none',
                    display: 'grid', gridTemplateColumns: '1fr auto', gap: '10px', alignItems: 'center',
                    ...(significant && tint ? {
                      background: direction === 'away'
                        ? 'rgba(196, 134, 138, 0.06)'
                        : SP.greenSoft,
                      borderLeft: `2px solid ${tint}`,
                      paddingLeft: '14px',
                    } : {}),
                  }}
                >
                  <span style={{ fontSize: '13px', fontWeight: 500, color: SP.text, lineHeight: 1.35 }}>
                    {g.matchup}
                  </span>
                  <span style={{
                    fontFamily: SP.fontMono, fontSize: '11px',
                    textAlign: 'right', whiteSpace: 'nowrap', color: moveColor,
                  }}>
                    {isFlat
                      ? <span style={{ color: SP.text4 }}>No movement</span>
                      : <>
                          {showOpenClose ? <>{g.ml_open > 0 ? '+' : ''}{g.ml_open} → {g.ml_now > 0 ? '+' : ''}{g.ml_now}</> : null}
                          <span style={{ display: showOpenClose ? 'block' : 'inline', fontSize: showOpenClose ? '10px' : '11px', color: showOpenClose ? deltaColor : moveColor, marginTop: showOpenClose ? '2px' : 0, letterSpacing: '0.02em' }}>
                            {isML ? Math.round(movement) : movement.toFixed(1)}{unit} {direction}{significant ? (isML && movement >= 100 ? ' · large move' : ' · sharp move') : ''}
                          </span>
                        </>
                    }
                  </span>
                </div>
              );
            })}
          </div>

          <div style={{
            background: SP.surface, border: `1px solid ${SP.border}`,
            borderRadius: '10px', padding: '14px 18px', marginBottom: '24px',
          }}>
            {[
              { label: 'Toward model', value: `${lmTowardCount} of ${lmGames.length}`, color: SP.green },
              { label: 'Away from model', value: `${lmAwayCount} of ${lmGames.length}`, color: SP.redSoft },
              { label: 'No movement', value: `${lmNoneCount} of ${lmGames.length}`, color: SP.text },
            ].map((row) => (
              <div key={row.label} style={{
                display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px',
              }}>
                <span style={{
                  fontFamily: SP.fontMono, fontSize: '10px',
                  letterSpacing: '0.18em', textTransform: 'uppercase', color: SP.text3,
                }}>{row.label}</span>
                <span style={{ fontFamily: SP.fontMono, fontSize: '13px', fontWeight: 500, color: row.color }}>
                  {row.value}
                </span>
              </div>
            ))}
          </div>
        </>
      )}

      {mmdGames.length > 0 && (
        <>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', marginBottom: '12px' }}>
            <h2 style={{ fontFamily: SP.fontSerif, fontSize: '18px', fontWeight: 600, color: SP.text }}>
              Model vs Market Delta
            </h2>
            <span style={{
              fontFamily: SP.fontMono, fontSize: '10px', color: SP.text3, letterSpacing: '0.04em',
            }}>{sportRunsLabel}</span>
          </div>

          <div style={{
            background: SP.surface, border: `1px solid ${SP.border}`,
            borderRadius: '14px', padding: '18px 18px 16px', marginBottom: '18px',
          }}>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', marginBottom: '14px' }}>
              {mmdGames.map((row, i) => {
                const delta = Number(row.delta) || 0;
                const abs = Math.abs(delta);
                const widthPct = Math.min(50, (abs / 2) * 50);
                const isZero = abs < 0.05;
                const sideText = String(row.side || '');
                const m = sideText.match(/^(.+?)\s+([+-]?\d+(?:\.\d+)?)$/);
                const teamLabel = m ? m[1].split(' ').slice(-1)[0] : sideText;
                const lineText = m ? m[2] : '';
                return (
                  <div key={i} style={{
                    display: 'grid', gridTemplateColumns: '110px 1fr 50px',
                    gap: '8px', alignItems: 'center',
                  }}>
                    <span style={{
                      fontSize: '12px', fontWeight: 500, color: SP.text,
                      overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
                    }}>
                      {teamLabel}
                      {lineText && (
                        <span style={{
                          color: SP.text3, fontFamily: SP.fontMono, fontSize: '11px', marginLeft: '4px',
                        }}>{lineText}</span>
                      )}
                    </span>
                    <div style={{
                      position: 'relative', height: '7px', background: SP.surface2, borderRadius: '2px',
                    }}>
                      <span aria-hidden style={{
                        position: 'absolute', left: '50%', top: '-2px', bottom: '-2px',
                        width: '1px', background: SP.text5,
                      }} />
                      {isZero ? (
                        <div style={{
                          position: 'absolute', top: 0, bottom: 0,
                          left: 'calc(50% - 1px)', width: '2px', background: SP.text3,
                        }} />
                      ) : delta > 0 ? (
                        <div style={{
                          position: 'absolute', top: 0, bottom: 0, left: '50%',
                          width: `${widthPct}%`, background: SP.green, borderRadius: '2px',
                        }} />
                      ) : (
                        <div style={{
                          position: 'absolute', top: 0, bottom: 0, right: '50%',
                          width: `${widthPct}%`, background: SP.redSoft, borderRadius: '2px',
                        }} />
                      )}
                    </div>
                    <span style={{
                      fontFamily: SP.fontMono, fontSize: '11px', textAlign: 'right',
                      color: isZero ? SP.text4 : delta > 0 ? SP.green : SP.redSoft,
                    }}>
                      {isZero ? '0.0' : `${delta > 0 ? '+' : ''}${delta.toFixed(1)}`}
                    </span>
                  </div>
                );
              })}
            </div>

            <div style={{
              display: 'flex', justifyContent: 'space-between',
              fontFamily: SP.fontMono, fontSize: '9px', color: SP.text4,
              letterSpacing: '0.04em', marginTop: '6px', padding: '0 110px 0 110px',
            }}>
              <span>-2</span><span>0</span><span>+2</span>
            </div>

            {avgDelta != null && (
              <div style={{
                paddingTop: '14px', marginTop: '14px',
                borderTop: `1px solid ${SP.border2}`,
                display: 'flex', justifyContent: 'space-between', alignItems: 'center',
              }}>
                <span style={{
                  fontFamily: SP.fontMono, fontSize: '10px',
                  letterSpacing: '0.16em', textTransform: 'uppercase', color: SP.text3,
                }}>Avg model-market delta</span>
                <span style={{ fontFamily: SP.fontMono, fontSize: '13px', color: SP.green, fontWeight: 500 }}>
                  {Number(avgDelta).toFixed(1)} {sportRunsLabel}
                </span>
              </div>
            )}
          </div>
        </>
      )}

      {updatedTime && (
        <div style={{
          textAlign: 'center',
          fontFamily: SP.fontMono, fontSize: '10px', letterSpacing: '0.18em',
          textTransform: 'uppercase', color: SP.text4,
        }}>
          Updated {updatedTime} <span style={{ color: SP.green, margin: '0 6px' }}>●</span> Live data
        </div>
      )}
    </div>
  );
}

function Chip({ children }) {
  return (
    <span style={{
      fontFamily: SP.fontMono, fontSize: '13px', color: SP.green, fontWeight: 500,
      background: 'rgba(90, 158, 114, 0.08)',
      padding: '1px 6px', borderRadius: '4px',
    }}>{children}</span>
  );
}
