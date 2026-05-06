import { useEffect, useRef } from 'react';
import { useApi } from '../../hooks/useApi';
import { useSport, sportQuery } from '../../hooks/useSport';

// Full-screen Market Intelligence detail. Per v4.3 mockup approved
// 2026-05-06. Replaces the inline DailyMarketReport expansion as the
// destination users land on after tapping the MI card on pass day,
// pick day, or the recap. Existing DailyMarketReport.jsx still ships
// for any inline-expansion consumer that hasn't migrated yet.
//
// Data: pulls /public/market-report (top-of-page metrics) and
// /picks/market (per-game movement table + model-vs-market delta).

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

function fmtML(n) {
  if (n == null) return null;
  return n > 0 ? `+${n}` : `${n}`;
}

// Cents difference between two American odds. Crossing zero adds 200
// because moving from a favorite to a dog (or vice versa) is mechanically
// a larger jump than the raw arithmetic suggests on either side.
function odds_diff(open, close) {
  if (open == null || close == null) return null;
  if ((open >= 0 && close >= 0) || (open <= 0 && close <= 0)) {
    return Math.abs(close - open);
  }
  return Math.abs(open) + Math.abs(close);
}

function classifyMlMove(game) {
  const open = game.away_ml_open ?? null;
  const close = game.away_ml ?? null;
  const modelSide = game?.model?.pick_side;
  if (open == null || close == null) return { kind: 'none', delta: 0, openText: null, closeText: null };
  if (open === close) return { kind: 'none', delta: 0, openText: fmtML(open), closeText: fmtML(close) };
  const diff = odds_diff(open, close);
  // Movement "toward away" if away got cheaper (close > open numerically when
  // both negative is cheaper, or close > open when positive). Then we
  // compare to which side the model picked.
  const awayCheaper = close > open;
  const movedToward = modelSide === 'away' ? awayCheaper : modelSide === 'home' ? !awayCheaper : null;
  return {
    kind: movedToward == null ? 'none' : movedToward ? 'toward' : 'away',
    delta: diff,
    openText: fmtML(open),
    closeText: fmtML(close),
  };
}

export default function MarketReportScreen({ onBack }) {
  const scrollRef = useRef(null);
  useEffect(() => { if (scrollRef.current) scrollRef.current.scrollTop = 0; }, []);

  const { sport } = useSport();
  const { data: report } = useApi(sportQuery('/public/market-report', sport), { pollInterval: 300000 });
  const { data: marketData } = useApi(sportQuery('/picks/market', sport));

  const sportLabel = (sport || 'mlb').toUpperCase();
  const games = (marketData?.games || []).filter((g) => g && (g.away_team || g.home_team || g.away || g.home));

  const totalGames = games.length || report?.total_games || 0;
  const dist = report?.edge_distribution || {};
  const signalsFired = report?.signal_count != null ? report.signal_count : (dist.strong || 0);
  const qualifying = Math.max(0, (dist.moderate || 0));
  const belowThreshold = Math.max(0, totalGames - signalsFired - qualifying);
  const totalEdges = (dist.strong || 0) + (dist.moderate || 0) + (dist.weak || 0);

  const mei = report?.market_efficiency_index ?? null;
  const regimeRaw = report?.regime || (mei != null && mei >= 60 ? 'Active' : mei != null && mei <= 30 ? 'Quiet' : 'Efficient');
  const regimeDisplay = regimeRaw.charAt(0).toUpperCase() + regimeRaw.slice(1).toLowerCase();
  const regimeMicro = report?.regime_micro || (mei != null && mei >= 80 ? 'high' : mei != null && mei >= 50 ? 'moderate' : 'low');
  const topEdge = report?.largest_edge != null ? `+${Number(report.largest_edge).toFixed(1)}%` : '—';
  const seven = report?.mei?.seven_day_avg ?? mei;
  const seasonAvg = report?.mei?.season_avg ?? mei;
  const sevenTrend = mei != null && seven != null
    ? (mei > seven + 1 ? 'up' : mei < seven - 1 ? 'down' : 'flat')
    : 'flat';
  const isCalibration = report?.model_phase === 'calibration';
  const todayLabel = (() => {
    try {
      return new Date().toLocaleDateString('en-US', {
        month: 'long', day: 'numeric', year: 'numeric', timeZone: 'America/New_York',
      });
    } catch { return ''; }
  })();
  const updatedTime = fmtTimeET(report?.last_updated);

  // Build moneyline movement rows
  const mlRows = games.map((g) => {
    const home = g.home_team || g.home || '';
    const away = g.away_team || g.away || '';
    const cls = classifyMlMove(g);
    return {
      key: g.id || `${away}-${home}`,
      game: away && home ? `${away} @ ${home}` : (g.matchup || home || away),
      ...cls,
    };
  });
  const mlToward = mlRows.filter((r) => r.kind === 'toward').length;
  const mlAway = mlRows.filter((r) => r.kind === 'away').length;
  const mlNone = mlRows.filter((r) => r.kind === 'none').length;

  // Model vs market delta (predicted_margin minus market spread for the
  // model's pick side). Positive delta means the model sees the pick side
  // covering by `delta` more runs than the market does.
  const deltaRows = games
    .map((g) => {
      const pickSide = g?.model?.pick_side;
      const predicted = g?.model?.predicted_margin;
      const line = g?.model?.line;
      if (pickSide == null || predicted == null || line == null) return null;
      const teamLabel = pickSide === 'away'
        ? (g.away || g.away_team || '').split(' ')[0]
        : (g.home || g.home_team || '').split(' ')[0];
      const lineText = line > 0 ? `+${line}` : `${line}`;
      const delta = pickSide === 'home'
        ? -predicted - line
        : predicted - line;
      return { key: g.id, team: teamLabel, lineText, delta: Number(delta) };
    })
    .filter(Boolean)
    .sort((a, b) => Math.abs(b.delta) - Math.abs(a.delta));

  const avgDelta = deltaRows.length
    ? deltaRows.reduce((s, r) => s + Math.abs(r.delta), 0) / deltaRows.length
    : 0;
  const sportRunsLabel = (sport || '').toLowerCase() === 'mlb' ? 'runs' : 'pts';

  return (
    <div ref={scrollRef} style={{
      position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
      backgroundColor: SP.bg,
      color: SP.text,
      zIndex: 200,
      overflowY: 'auto',
      WebkitOverflowScrolling: 'touch',
    }}>
      <div style={{
        maxWidth: '480px',
        margin: '0 auto',
        paddingLeft: 'max(18px, env(safe-area-inset-left))',
        paddingRight: 'max(18px, env(safe-area-inset-right))',
        paddingBottom: 'max(40px, env(safe-area-inset-bottom))',
        borderLeft: '1px solid rgba(255, 255, 255, 0.04)',
        borderRight: '1px solid rgba(255, 255, 255, 0.04)',
      }}>
        <nav style={{
          position: 'sticky', top: 0, zIndex: 1,
          backgroundColor: SP.bg,
          borderBottom: `1px solid ${SP.border}`,
          paddingTop: 'max(12px, env(safe-area-inset-top))',
          paddingBottom: '14px',
          display: 'flex', alignItems: 'center', gap: '14px',
          marginLeft: 'calc(-1 * max(18px, env(safe-area-inset-left)))',
          marginRight: 'calc(-1 * max(18px, env(safe-area-inset-right)))',
          paddingLeft: 'max(18px, env(safe-area-inset-left))',
          paddingRight: 'max(18px, env(safe-area-inset-right))',
        }}>
          <button onClick={onBack} aria-label="Go back" style={{
            background: 'none', border: 'none', cursor: 'pointer', color: SP.text3,
            display: 'inline-flex', alignItems: 'center', justifyContent: 'center', padding: 0,
          }}>
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M19 12H5M12 19l-7-7 7-7" />
            </svg>
          </button>
          <span style={{
            fontFamily: SP.fontMono, fontSize: '11px',
            letterSpacing: '0.32em', textTransform: 'uppercase', color: SP.text2,
          }}>Market Intelligence</span>
        </nav>

        <div style={{ paddingTop: '22px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px', flexWrap: 'wrap', marginBottom: '18px' }}>
            <span style={{
              display: 'inline-flex', alignItems: 'center', padding: '5px 11px',
              border: `1px solid ${SP.green}`, borderRadius: '4px',
              fontFamily: SP.fontMono, fontSize: '10px', fontWeight: 500,
              letterSpacing: '0.2em', textTransform: 'uppercase', color: SP.green,
            }}>{sportLabel}</span>
            <span style={{ color: SP.text4, fontSize: '11px' }}>·</span>
            <span style={{
              fontFamily: SP.fontMono, fontSize: '10px',
              letterSpacing: '0.18em', textTransform: 'uppercase', color: SP.text3,
            }}>Market Report</span>
            {totalGames > 0 && (
              <>
                <span style={{ color: SP.text4, fontSize: '11px' }}>·</span>
                <span style={{
                  fontFamily: SP.fontMono, fontSize: '10px',
                  letterSpacing: '0.18em', textTransform: 'uppercase', color: SP.text3,
                }}>{totalGames} games</span>
              </>
            )}
          </div>

          <h1 style={{
            fontFamily: SP.fontSerif, fontSize: '30px', fontWeight: 700,
            color: SP.text, lineHeight: 1.1, letterSpacing: '-0.01em', marginBottom: '10px',
          }}>
            {regimeDisplay} regime, {regimeMicro} opportunity.
          </h1>
          <div style={{
            fontFamily: SP.fontMono, fontSize: '12px', color: SP.text3, marginBottom: '22px',
          }}>
            {todayLabel}{updatedTime ? ` · Updated ${updatedTime}` : ''}
          </div>

          {isCalibration && (
            <div style={{
              background: SP.amberSoft, border: '1px solid rgba(245, 158, 11, 0.22)',
              borderRadius: '10px', padding: '14px 16px', marginBottom: '24px',
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
                  Edges tracked live. Confidence intervals widen during early-season validation. Closing line audit publishes on every signal.
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
              { label: 'MEI', value: mei != null ? String(mei) : '—', suffix: 'of 100', tone: 'green', size: 32 },
              { label: 'Regime', value: regimeDisplay, suffix: regimeMicro, tone: 'text', size: 22 },
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
                  color: cell.tone === 'green' ? SP.green : cell.tone === 'amber' ? SP.amber : SP.text,
                }}>{cell.value}</div>
                <div style={{
                  fontFamily: SP.fontMono, fontSize: '11px', color: SP.text3,
                  letterSpacing: '0.04em',
                }}>{cell.suffix}</div>
              </div>,
              i < arr.length - 1 ? <div key={`d-${i}`} style={{ background: SP.border }} /> : null,
            ])}
          </div>

          {mei != null && (
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
                  position: 'absolute', top: '-3px', left: `${Math.max(0, Math.min(100, mei))}%`,
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
              borderRadius: '14px', padding: '18px 18px 16px', marginBottom: '24px',
            }}>
              <div style={{
                fontFamily: SP.fontMono, fontSize: '10px', fontWeight: 500,
                letterSpacing: '0.22em', textTransform: 'uppercase', color: SP.text3,
                marginBottom: '14px',
              }}>Edge Distribution · {totalEdges} detected across {totalGames} games</div>
              <div style={{
                height: '10px', background: SP.surface2, borderRadius: '3px',
                overflow: 'hidden', display: 'flex', marginBottom: '14px',
              }}>
                <div style={{ height: '100%', width: `${(signalsFired / Math.max(1, totalGames)) * 100}%`, background: SP.green }} />
                <div style={{ height: '100%', width: `${(qualifying / Math.max(1, totalGames)) * 100}%`, background: 'rgba(245, 158, 11, 0.6)' }} />
                <div style={{ height: '100%', flex: 1, background: SP.surface2 }} />
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '10px' }}>
                {[
                  { label: 'Signals fired', count: signalsFired, dot: SP.green, muted: false },
                  { label: 'Qualifying', count: qualifying, dot: SP.amber, muted: qualifying === 0 },
                  { label: 'Below threshold', count: belowThreshold, dot: SP.text5, muted: true },
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
                      letterSpacing: '0.18em', textTransform: 'uppercase', color: SP.text3,
                    }}>{c.label}</div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {totalEdges > 0 && (
            <div style={{
              borderLeft: `2px solid ${SP.green}`, background: SP.greenSoft,
              padding: '18px 20px', borderRadius: '0 10px 10px 0', marginBottom: '28px',
            }}>
              <div style={{
                fontFamily: SP.fontMono, fontSize: '10px', fontWeight: 500,
                letterSpacing: '0.22em', textTransform: 'uppercase', color: SP.green,
                marginBottom: '8px',
              }}>Observation</div>
              <div style={{
                fontFamily: SP.fontSerif, fontSize: '16px', lineHeight: 1.5, color: SP.text,
              }}>
                <span style={{ fontFamily: SP.fontMono, fontSize: '15px', color: SP.green, fontWeight: 500 }}>
                  {totalEdges} edge{totalEdges === 1 ? '' : 's'}
                </span>
                {' '}detected across the slate. {signalsFired} cleared the discipline filter
                {totalGames > 0 ? <> at <span style={{ fontFamily: SP.fontMono, fontSize: '15px', color: SP.green, fontWeight: 500 }}>{Math.round((signalsFired / totalGames) * 100)}%</span> density.</> : '.'}
              </div>
            </div>
          )}

          {mlRows.length > 0 && (
            <>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', marginBottom: '12px' }}>
                <h2 style={{ fontFamily: SP.fontSerif, fontSize: '20px', fontWeight: 600, color: SP.text }}>
                  Moneyline Movement
                </h2>
                <span style={{
                  fontFamily: SP.fontMono, fontSize: '10px', color: SP.text3, letterSpacing: '0.04em',
                }}>{mlRows.length} game{mlRows.length === 1 ? '' : 's'}</span>
              </div>

              <div style={{
                background: SP.surface, border: `1px solid ${SP.border}`,
                borderRadius: '12px', overflow: 'hidden', marginBottom: '14px',
              }}>
                {mlRows.map((row, i) => {
                  const significant = row.delta >= 20;
                  const tint = row.kind === 'away' ? SP.redSoft : row.kind === 'toward' ? SP.green : null;
                  const moveColor = row.kind === 'toward' ? SP.green : row.kind === 'away' ? SP.redSoft : SP.text4;
                  const deltaColor = row.kind === 'toward'
                    ? 'rgba(90, 158, 114, 0.6)'
                    : row.kind === 'away'
                      ? 'rgba(196, 134, 138, 0.6)'
                      : SP.text3;
                  return (
                    <div
                      key={row.key || i}
                      style={{
                        padding: '12px 16px',
                        borderBottom: i < mlRows.length - 1 ? `1px solid ${SP.border2}` : 'none',
                        display: 'grid', gridTemplateColumns: '1fr auto', gap: '10px', alignItems: 'center',
                        ...(significant && tint ? {
                          background: row.kind === 'away'
                            ? 'rgba(196, 134, 138, 0.06)'
                            : SP.greenSoft,
                          borderLeft: `2px solid ${tint}`,
                          paddingLeft: '14px',
                        } : {}),
                      }}
                    >
                      <span style={{ fontSize: '13px', fontWeight: 500, color: SP.text, lineHeight: 1.35 }}>
                        {row.game}
                      </span>
                      <span style={{
                        fontFamily: SP.fontMono, fontSize: '11px',
                        textAlign: 'right', whiteSpace: 'nowrap', color: moveColor,
                      }}>
                        {row.kind === 'none'
                          ? 'No movement'
                          : <>{row.openText} → {row.closeText}<span style={{ display: 'block', fontSize: '10px', color: deltaColor, marginTop: '2px', letterSpacing: '0.02em' }}>
                              {Math.round(row.delta)}¢ {row.kind === 'toward' ? 'toward' : 'away'}{significant ? row.delta >= 100 ? ' · large move' : ' · sharp move' : ''}
                            </span></>
                        }
                      </span>
                    </div>
                  );
                })}
              </div>

              <div style={{
                background: SP.surface, border: `1px solid ${SP.border}`,
                borderRadius: '10px', padding: '14px 18px', marginBottom: '28px',
              }}>
                {[
                  { label: 'Toward model', value: `${mlToward} of ${mlRows.length}`, color: SP.green },
                  { label: 'Away from model', value: `${mlAway} of ${mlRows.length}`, color: SP.redSoft },
                  { label: 'No movement', value: `${mlNone} of ${mlRows.length}`, color: SP.text },
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

          {deltaRows.length > 0 && (
            <>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', marginBottom: '12px' }}>
                <h2 style={{ fontFamily: SP.fontSerif, fontSize: '20px', fontWeight: 600, color: SP.text }}>
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
                  {deltaRows.map((row) => {
                    const abs = Math.abs(row.delta);
                    const widthPct = Math.min(50, (abs / 2) * 50);
                    const isZero = abs < 0.05;
                    return (
                      <div key={row.key} style={{
                        display: 'grid', gridTemplateColumns: '110px 1fr 50px',
                        gap: '8px', alignItems: 'center',
                      }}>
                        <span style={{
                          fontSize: '12px', fontWeight: 500, color: SP.text,
                          overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
                        }}>
                          {row.team}
                          <span style={{
                            color: SP.text3, fontFamily: SP.fontMono, fontSize: '11px', marginLeft: '4px',
                          }}>{row.lineText}</span>
                        </span>
                        <div style={{
                          position: 'relative', height: '7px', background: SP.surface2, borderRadius: '2px',
                        }}>
                          <span aria-hidden style={{
                            content: '""', position: 'absolute', left: '50%', top: '-2px', bottom: '-2px',
                            width: '1px', background: SP.text5,
                          }} />
                          {isZero ? (
                            <div style={{
                              position: 'absolute', top: 0, bottom: 0,
                              left: 'calc(50% - 1px)', width: '2px', background: SP.text3,
                            }} />
                          ) : row.delta > 0 ? (
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
                          color: isZero ? SP.text4 : row.delta > 0 ? SP.green : SP.redSoft,
                        }}>
                          {isZero ? '0.0' : `${row.delta > 0 ? '+' : ''}${row.delta.toFixed(1)}`}
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
                    {avgDelta.toFixed(1)} {sportRunsLabel}
                  </span>
                </div>
              </div>
            </>
          )}

          {updatedTime && (
            <div style={{
              marginTop: '22px', textAlign: 'center',
              fontFamily: SP.fontMono, fontSize: '10px', letterSpacing: '0.18em',
              textTransform: 'uppercase', color: SP.text4,
            }}>
              Updated {updatedTime} <span style={{ color: SP.green, margin: '0 6px' }}>●</span> Live data
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
