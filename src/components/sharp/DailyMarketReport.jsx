import { useApi } from '../../hooks/useApi';
import { useSport, sportQuery } from '../../hooks/useSport';
import CalibrationBanner from '../brand/CalibrationBanner';

// v4.3 inline Market Intelligence report. Renders below the MI card
// when the user expands it on home (pick day or pass day).
//
// May 2026 redesign: Sharp Journal editorial format. Tag pill, headline,
// observation, then the same data the prior version surfaced reorganized
// into Market Structure / Bias / Top Edge / Edge Distribution / Edge Map /
// Line Movement / Model vs Market Delta / Implication / Sharp Principle /
// Cross-edition tile. Source: docs mockup approved 2026-05-07.
//
// Reads the canonical /public/market-report payload directly when no
// report prop is supplied; otherwise consumes the prop. Field
// references match the public_api.py shape: games_analyzed (not
// total_games), qualified_signals (not signal_count), edges_detected,
// signal_density, mei.{current,seven_day_avg,season_avg,sparkline},
// market_lean.{favorites,underdogs,total_edges}, line_movement.games,
// model_market_delta.games, edge_distribution.{strong,moderate,weak}.

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
  amberBorder: 'rgba(245, 158, 11, 0.22)',
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

function fmtDateET(iso) {
  if (!iso) return '';
  try {
    const d = new Date(iso);
    if (Number.isNaN(d.getTime())) return '';
    return new Intl.DateTimeFormat('en-US', {
      timeZone: 'America/New_York',
      month: 'long', day: 'numeric', year: 'numeric',
    }).format(d);
  } catch { return ''; }
}

function titleCase(s) {
  if (!s || typeof s !== 'string') return s;
  return s.charAt(0).toUpperCase() + s.slice(1).toLowerCase();
}

function getPhase(data) {
  // Phase detection based on slate state. The /api/public/market-report
  // endpoint does not currently expose per-game settlement counts, so
  // morning is the default. Once the backend surfaces games_settled +
  // games_in_progress, switch on those counters.
  const settled = Number(data?.games_settled || 0);
  const inProgress = Number(data?.games_in_progress || 0);
  const total = Number(data?.games_analyzed || 0);
  if (total > 0 && settled >= total) return 'evening';
  if (settled > 0 || inProgress > 0) return 'mixed';
  return 'morning';
}

export default function DailyMarketReport({ report: reportProp }) {
  const { sport } = useSport();
  const { data: fetchedData, loading } = useApi(sportQuery('/public/market-report', sport), { pollInterval: 300000 });
  const data = reportProp ?? fetchedData;

  if (reportProp ? !data?.available : (loading || !data || !data.available)) return null;

  const phase = getPhase(data);
  const isMorning = phase === 'morning';
  const isMixed = phase === 'mixed';
  const isEvening = phase === 'evening';

  const totalGames = data.games_analyzed || 0;
  const signalsFired = data.qualified_signals || 0;
  const dist = data.edge_distribution || {};
  const strongEdges = dist.strong || 0;
  const moderateEdges = dist.moderate || 0;
  const weakEdges = dist.weak || 0;
  const edgeCount = data.edges_detected != null ? data.edges_detected : (strongEdges + moderateEdges + weakEdges);
  const belowThreshold = Math.max(0, totalGames - edgeCount);
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
  const topEdgeTeam = data.top_edge_team || '';
  const topEdgeMatchup = data.largest_edge_game || '';
  const topEdgePct = data.largest_edge != null ? Number(data.largest_edge) : null;
  const topEdgeIsSignal = topEdgePct != null && signalsFired > 0 && topEdgePct >= 3.5;
  const updatedTime = fmtTimeET(data.last_updated);
  const dateLine = data.date ? fmtDateET(`${data.date}T12:00:00Z`) : '';
  const isCalibration = data.model_phase === 'calibration';

  const lean = data.market_lean || {};
  const leanCounts = {
    underdogs: lean.underdogs || 0,
    favorites: lean.favorites || 0,
    total: lean.total_edges || edgeCount,
  };
  const favPct = leanCounts.total > 0 ? (leanCounts.favorites / leanCounts.total) * 100 : 50;
  const dogPct = 100 - favPct;
  const leanSide = leanCounts.underdogs > leanCounts.favorites ? 'underdogs' : leanCounts.favorites > leanCounts.underdogs ? 'favorites' : 'split';

  const lmGames = (data.line_movement?.games) || [];
  const lmType = data.line_movement?.movement_type || 'moneyline';
  const lmTowardCount = data.line_movement?.toward_model || 0;
  const lmAwayCount = data.line_movement?.away_from_model || 0;
  const lmNoneCount = data.line_movement?.no_movement || 0;
  const mmdGames = (data.model_market_delta?.games) || [];
  const avgDelta = data.model_market_delta?.avg_delta;
  const sportRunsLabel = (sport || '').toLowerCase() === 'mlb' ? 'runs' : 'pts';

  // Edge Map: derive per-game rows from data.board if present.
  // Each row: matchup, edge_pct (signed via pick_side), is_signal, status text.
  const board = Array.isArray(data.board) ? data.board : [];
  const edgeMap = board
    .map((g) => {
      const edge = g?.edge != null ? Number(g.edge) : (g?.adjusted_edge != null ? Number(g.adjusted_edge) : null);
      if (edge == null || Number.isNaN(edge)) return null;
      const away = g.away_team || g.away || '?';
      const home = g.home_team || g.home || '?';
      const isSignal = !!g.passes;
      // Sign convention: positive = model favors home/pick_side, negative = market right
      // For display we render absolute edge + sign indicating signal vs sub-threshold
      return {
        matchup: `${away} vs ${home}`,
        away, home,
        pct: edge,
        signed: edge,
        isSignal,
      };
    })
    .filter(Boolean)
    .sort((a, b) => Math.abs(b.signed) - Math.abs(a.signed))
    .slice(0, 15);

  // Near misses: sub-threshold positive edges
  const nearMisses = board
    .filter((g) => {
      const edge = g?.edge != null ? Number(g.edge) : null;
      return edge != null && !g.passes && edge > 0 && edge < 3.5;
    })
    .sort((a, b) => Number(b.edge) - Number(a.edge))
    .slice(0, 3)
    .map((g) => ({
      matchup: `${g.away_team || g.away} vs ${g.home_team || g.home}`,
      pct: Number(g.edge),
    }));

  // Editorial copy generation. These are deterministic from the data so
  // morning/mixed/evening always reads coherently without backend changes.
  const headline = (() => {
    if (isMorning) {
      if (signalsFired === 0) return 'No signal cleared the threshold today. Capital preserved.';
      if (leanSide === 'underdogs' && leanCounts.underdogs >= leanCounts.favorites * 2) {
        return `Value sitting with the underdogs tonight. ${signalsFired} signal${signalsFired === 1 ? '' : 's'}, mostly dogs.`;
      }
      if (leanSide === 'favorites' && leanCounts.favorites >= leanCounts.underdogs * 2) {
        return `Favorites carrying the slate. ${signalsFired} signal${signalsFired === 1 ? '' : 's'} on chalk.`;
      }
      return `${signalsFired} signal${signalsFired === 1 ? '' : 's'} on the board across ${totalGames} game${totalGames === 1 ? '' : 's'}.`;
    }
    if (isMixed) {
      const settled = data.games_settled || 0;
      const remaining = totalGames - settled;
      return `${signalsFired} signal${signalsFired === 1 ? '' : 's'} on the board. ${remaining} game${remaining === 1 ? '' : 's'} still running.`;
    }
    if (signalsFired === 0) return 'The slate closed quiet. Capital preserved on the pass.';
    return 'Slate closed. Receipts in the ledger.';
  })();

  const observation = (() => {
    if (isMorning) {
      if (signalsFired === 0) {
        return `${totalGames} games analyzed, none cleared the qualification threshold. Pass days are part of the system.`;
      }
      if (leanSide === 'underdogs' && leanCounts.underdogs > leanCounts.favorites) {
        return `The underdog side is where the model is finding room. ${leanCounts.underdogs} edges on dogs against ${leanCounts.favorites} on favorites, with ${signalsFired} clearing the threshold.`;
      }
      if (leanSide === 'favorites' && leanCounts.favorites > leanCounts.underdogs) {
        return `Favorites are where the model sees room. ${leanCounts.favorites} edges on chalk against ${leanCounts.underdogs} on dogs, with ${signalsFired} clearing the threshold.`;
      }
      return `${edgeCount} edges detected across ${totalGames} games. ${signalsFired} cleared the discipline filter at ${density}% density.`;
    }
    if (isMixed) {
      const settled = data.games_settled || 0;
      return `${signalsFired} signal${signalsFired === 1 ? '' : 's'} issued across the slate. ${settled} of ${totalGames} games settled, with the rest still in progress. Numbers below are preliminary and update as games close.`;
    }
    return `${signalsFired} signal${signalsFired === 1 ? '' : 's'} issued. Final closing-line audit and per-game grading below.`;
  })();

  const implication = (() => {
    if (signalsFired === 0) return 'No qualifying edge detected. Discipline preserved on a slate the model read as efficient.';
    if (regimeRaw && regimeRaw.toLowerCase().includes('active')) return 'Moderate opportunity detected. Signals fired where the threshold cleared.';
    if (regimeRaw && regimeRaw.toLowerCase().includes('high')) return 'High opportunity slate. Model finding meaningful gaps the market has not corrected.';
    if (regimeRaw && regimeRaw.toLowerCase().includes('quiet')) return 'Quiet market. Tight book consensus across most of the slate.';
    return 'Market priced inside model fair value on most of the board.';
  })();

  const sharpPrinciple = (() => {
    if (signalsFired === 0) return 'Pass days are not missed opportunities. They are proof the system is working.';
    if (leanSide === 'underdogs' && leanCounts.underdogs > leanCounts.favorites) {
      return 'An underdog lean suggests the spread market is running a point or two wide on several games. Small inefficiencies add up.';
    }
    if (leanSide === 'favorites' && leanCounts.favorites > leanCounts.underdogs) {
      return 'When favorites carry the slate, the model is reading market underestimation of skill gaps. Edge size matters more than direction.';
    }
    return 'Selectivity over volume. The model only fires when the math demands it.';
  })();

  const tagPill = isMorning ? 'Market Notes' : 'Slate Recap';
  const editionLabel = isMorning ? 'Morning Edition' : isMixed ? 'Live Recap' : 'Evening Edition';

  return (
    <div style={{ display: 'flex', flexDirection: 'column' }}>
      {/* Calibration banner — uses shared CalibrationBanner so it inherits
          the X dismiss button. Per-sport dismissKey so dismissing on MLB
          doesn't auto-dismiss WNBA. */}
      {isCalibration && (
        <CalibrationBanner
          eyebrow="Calibration Phase"
          dismissKey={`mi-calibration-${sport}`}
        >
          Edges tracked live. Confidence intervals widen during early-season validation.
        </CalibrationBanner>
      )}

      {/* Live banner — only when slate has games still in progress */}
      {isMixed && (
        <div style={{
          background: SP.amberSoft, border: `1px solid ${SP.amberBorder}`,
          borderRadius: '10px', padding: '14px 18px', marginBottom: '22px',
          display: 'flex', alignItems: 'center', gap: '12px',
        }}>
          <span style={{
            width: '8px', height: '8px', borderRadius: '50%', background: SP.amber, flexShrink: 0,
            animation: 'dmrPulse 2s ease-in-out infinite',
          }} />
          <style>{`@keyframes dmrPulse{0%{box-shadow:0 0 0 0 rgba(245,158,11,0.6)}70%{box-shadow:0 0 0 10px rgba(245,158,11,0)}100%{box-shadow:0 0 0 0 rgba(245,158,11,0)}}`}</style>
          <div style={{ flex: 1, minWidth: 0 }}>
            <div style={{
              fontFamily: SP.fontMono, fontSize: '9px',
              letterSpacing: '0.22em', textTransform: 'uppercase', color: SP.amber,
              marginBottom: '4px',
            }}>Slate in progress</div>
            <div style={{ fontSize: '13px', color: SP.text, lineHeight: 1.45 }}>
              {data.games_settled || 0} of {totalGames} games settled. Numbers below are preliminary.
            </div>
            {updatedTime && (
              <div style={{ fontFamily: SP.fontMono, fontSize: '11px', color: SP.text3, marginTop: '4px' }}>
                Updated {updatedTime} · Auto-refresh every 5 min
              </div>
            )}
          </div>
        </div>
      )}

      {/* Meta row: tag pill + Sharp Journal + edition + read time */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '20px', flexWrap: 'wrap' }}>
        <span style={{
          display: 'inline-flex', alignItems: 'center',
          padding: '6px 12px', border: `1px solid ${SP.blue}`, borderRadius: '4px',
          fontFamily: SP.fontMono, fontSize: '10px', fontWeight: 500,
          letterSpacing: '0.18em', textTransform: 'uppercase', color: SP.blue,
        }}>{tagPill}</span>
        <span style={{ color: SP.text4, fontSize: '12px' }}>·</span>
        <span style={{
          fontFamily: SP.fontMono, fontSize: '10px', letterSpacing: '0.16em',
          textTransform: 'uppercase', color: SP.text3,
        }}>Sharp Journal</span>
        <span style={{ color: SP.text4, fontSize: '12px' }}>·</span>
        <span style={{
          fontFamily: SP.fontMono, fontSize: '10px', letterSpacing: '0.16em',
          textTransform: 'uppercase', color: SP.text3,
        }}>{editionLabel}</span>
      </div>

      {/* Headline */}
      <h1 style={{
        fontFamily: SP.fontSerif, fontSize: '28px', fontWeight: 700,
        color: SP.text, lineHeight: 1.15, letterSpacing: '-0.01em',
        margin: '0 0 14px',
      }}>{headline}</h1>

      {/* Date + byline */}
      {dateLine && (
        <div style={{ fontFamily: SP.fontMono, fontSize: '12px', color: SP.text3, marginBottom: '6px' }}>
          {dateLine}{updatedTime ? ` · ${updatedTime}` : ''}
        </div>
      )}
      <div style={{ fontSize: '13px', color: SP.text, marginBottom: '22px' }}>
        <span>Evan Cole</span>
        <span style={{ color: SP.text4, margin: '0 6px' }}>·</span>
        <span style={{ color: SP.text3 }}>Head of Signal Intelligence</span>
      </div>

      {/* Divider */}
      <div style={{ height: '1px', background: SP.border, margin: '0 0 24px' }} />

      {/* Observation */}
      <div style={{
        fontFamily: SP.fontMono, fontSize: '11px', fontWeight: 500,
        letterSpacing: '0.22em', textTransform: 'uppercase', color: SP.green,
        marginBottom: '12px',
      }}>Observation</div>
      <p style={{
        fontFamily: SP.fontSerif, fontSize: '17px', lineHeight: 1.55,
        color: SP.text, marginBottom: '28px',
      }}>{observation}</p>

      {/* Market Structure: 3-up Edges/Signals/Density */}
      <Card>
        <Eyebrow color={SP.green}>Market Structure</Eyebrow>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1px 1fr 1px 1fr', alignItems: 'center', marginTop: '8px' }}>
          {[
            { value: edgeCount, label: 'Edges' },
            { value: signalsFired, label: 'Signals' },
            { value: `${density}%`, label: 'Density' },
          ].flatMap((cell, i, arr) => [
            <div key={`ms-${cell.label}`} style={{ textAlign: 'center', padding: '8px 0' }}>
              <div style={{
                fontFamily: SP.fontSerif, fontSize: '32px', fontWeight: 600,
                color: SP.text, lineHeight: 1, marginBottom: '8px', letterSpacing: '-0.01em',
              }}>{cell.value}</div>
              <div style={{
                fontFamily: SP.fontMono, fontSize: '10px',
                letterSpacing: '0.2em', textTransform: 'uppercase', color: SP.text3,
              }}>{cell.label}</div>
            </div>,
            i < arr.length - 1 ? <div key={`md-${i}`} style={{ width: '1px', height: '50px', background: SP.border }} /> : null,
          ])}
        </div>
      </Card>

      {/* Bias card */}
      {leanCounts.total > 0 && (
        <Card>
          <Eyebrow color={SP.green}>Bias</Eyebrow>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '10px', marginBottom: '8px' }}>
            <span style={{ display: 'inline-flex', alignItems: 'center', gap: '8px', fontSize: '14px', color: SP.text }}>
              <span style={{ width: 7, height: 7, borderRadius: '50%', background: SP.redSoft }} />
              Favorites
            </span>
            <span style={{ display: 'inline-flex', alignItems: 'center', gap: '8px', fontSize: '14px', color: SP.text }}>
              Underdogs
              <span style={{ width: 7, height: 7, borderRadius: '50%', background: SP.green }} />
            </span>
          </div>
          <div style={{ height: '4px', borderRadius: '2px', background: SP.surface2, overflow: 'hidden', display: 'flex', margin: '6px 0 14px' }}>
            <div style={{ height: '100%', background: SP.redSoft, width: `${favPct}%` }} />
            <div style={{ height: '100%', background: SP.green, width: `${dogPct}%` }} />
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between', fontFamily: SP.fontMono, fontSize: '12px', color: SP.text3 }}>
            <span>{leanCounts.favorites} edge{leanCounts.favorites === 1 ? '' : 's'}</span>
            <span>{leanCounts.underdogs} edge{leanCounts.underdogs === 1 ? '' : 's'}</span>
          </div>
        </Card>
      )}

      {/* Top Edge */}
      {topEdgeTeam && topEdgePct != null && (
        <Card>
          <Eyebrow color={SP.green}>Top Edge{isEvening || isMixed ? ' · Settled' : ''}</Eyebrow>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', marginTop: '10px', marginBottom: '6px' }}>
            <span style={{ fontFamily: SP.fontSans, fontSize: '20px', fontWeight: 600, color: SP.text }}>
              {topEdgeTeam}
            </span>
            <span style={{ fontFamily: SP.fontMono, fontSize: '20px', fontWeight: 500, color: topEdgeIsSignal ? SP.green : SP.redSoft }}>
              {topEdgeIsSignal ? '+' : ''}{topEdgePct.toFixed(1)}%
            </span>
          </div>
          {topEdgeMatchup && (
            <div style={{ fontFamily: SP.fontMono, fontSize: '12px', color: SP.text3, marginBottom: '12px' }}>
              {topEdgeMatchup}
            </div>
          )}
          <span style={{
            display: 'inline-block', fontFamily: SP.fontMono, fontSize: '11px',
            letterSpacing: '0.06em', padding: '5px 10px', borderRadius: '4px',
            marginBottom: '8px',
            background: topEdgeIsSignal ? 'rgba(90, 158, 114, 0.1)' : 'rgba(255, 255, 255, 0.05)',
            border: `1px solid ${topEdgeIsSignal ? 'rgba(90, 158, 114, 0.3)' : SP.border}`,
            color: topEdgeIsSignal ? SP.green : SP.text3,
          }}>{topEdgeIsSignal ? 'Signal cleared' : 'Below threshold'}</span>
        </Card>
      )}

      {/* Edge Distribution: STR / MOD / WK / Below threshold */}
      {totalGames > 0 && (
        <Card>
          <Eyebrow color={SP.green}>Edge Distribution · {edgeCount} detected across {totalGames} games</Eyebrow>
          <div style={{
            fontFamily: SP.fontMono, fontSize: '11px', color: SP.text2,
            letterSpacing: '0.04em', marginBottom: '14px', marginTop: '-4px',
          }}>
            <span style={{ color: SP.green, fontWeight: 600 }}>{signalsFired}</span> signal{signalsFired === 1 ? '' : 's'} fired ·{' '}
            only Strong (and sometimes Moderate) edges become signals
          </div>
          <div style={{
            height: '10px', background: SP.surface2, borderRadius: '3px',
            overflow: 'hidden', display: 'flex', marginBottom: '14px', gap: '1px',
          }}>
            <div title="Strong" style={{ height: '100%', width: `${(strongEdges / Math.max(1, totalGames)) * 100}%`, background: SP.green }} />
            <div title="Moderate" style={{ height: '100%', width: `${(moderateEdges / Math.max(1, totalGames)) * 100}%`, background: 'rgba(90, 158, 114, 0.55)' }} />
            <div title="Weak" style={{ height: '100%', width: `${(weakEdges / Math.max(1, totalGames)) * 100}%`, background: 'rgba(90, 158, 114, 0.28)' }} />
            <div title="Below threshold" style={{ height: '100%', flex: 1, background: SP.surface2 }} />
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr 1fr', gap: '10px' }}>
            {[
              { label: 'Strong', sublabel: '≥ 10pp', count: strongEdges, dot: SP.green, muted: strongEdges === 0 },
              { label: 'Moderate', sublabel: '7–10pp', count: moderateEdges, dot: 'rgba(90, 158, 114, 0.55)', muted: moderateEdges === 0 },
              { label: 'Weak', sublabel: '3.5–7pp', count: weakEdges, dot: 'rgba(90, 158, 114, 0.28)', muted: weakEdges === 0 },
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
                <div style={{ fontFamily: SP.fontMono, fontSize: '8px', color: SP.text4, letterSpacing: '0.04em', marginTop: '2px' }}>{c.sublabel}</div>
              </div>
            ))}
          </div>
        </Card>
      )}

      {/* MEI / Regime row + sparkline */}
      <Card>
        <Eyebrow color={SP.green}>Market Efficiency</Eyebrow>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1px 1fr 1px 1fr', alignItems: 'center', marginTop: '8px', marginBottom: '14px' }}>
          {[
            { label: 'MEI', value: meiCurrent != null ? String(meiCurrent) : '—', suffix: 'of 100', tone: 'green' },
            { label: 'Regime', value: regimeDisplay, suffix: regimeMicro || (meiCurrent != null && meiCurrent >= 80 ? 'high opportunity' : meiCurrent != null && meiCurrent >= 50 ? 'moderate opportunity' : 'low opportunity'), tone: 'text' },
            { label: 'Top Edge', value: topEdge, suffix: 'single signal', tone: topEdgeIsSignal ? 'green' : 'text' },
          ].flatMap((cell, i, arr) => [
            <div key={`me-${cell.label}`} style={{ textAlign: 'center', padding: '4px 8px' }}>
              <div style={{
                fontFamily: SP.fontMono, fontSize: '9px',
                letterSpacing: '0.22em', textTransform: 'uppercase', color: SP.text3,
                marginBottom: '6px',
              }}>{cell.label}</div>
              <div style={{
                fontFamily: SP.fontSerif, fontSize: cell.label === 'Regime' ? '20px' : '26px',
                fontWeight: 700, lineHeight: 1, letterSpacing: '-0.02em', marginBottom: '4px',
                color: cell.tone === 'green' ? SP.green : SP.text,
              }}>{cell.value}</div>
              <div style={{ fontFamily: SP.fontMono, fontSize: '10px', color: SP.text3 }}>{cell.suffix}</div>
            </div>,
            i < arr.length - 1 ? <div key={`mD-${i}`} style={{ width: '1px', height: '50px', background: SP.border }} /> : null,
          ])}
        </div>

        {meiCurrent != null && (
          <div style={{ paddingTop: '12px', borderTop: `1px solid ${SP.border2}` }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
              <span style={{ fontFamily: SP.fontMono, fontSize: '9px', letterSpacing: '0.22em', textTransform: 'uppercase', color: SP.text4 }}>
                MEI · Where today sits
              </span>
              <span style={{ fontFamily: SP.fontMono, fontSize: '11px', color: SP.text3 }}>
                7d <span style={{ color: SP.text2 }}>{sevenTrend}</span>
                {seasonAvg != null ? <> · Szn avg <span style={{ color: SP.text2 }}>{seasonAvg}</span></> : null}
              </span>
            </div>
            <div style={{
              position: 'relative', height: '6px', borderRadius: '3px', marginBottom: '6px',
              background: `linear-gradient(90deg, ${SP.surface2} 0%, rgba(90, 158, 114, 0.28) 100%)`,
            }}>
              <div style={{
                position: 'absolute', top: '-3px',
                left: `${Math.max(2, Math.min(98, meiCurrent))}%`,
                width: '4px', height: '12px', background: SP.green, borderRadius: '2px',
                transform: 'translateX(-50%)',
                boxShadow: '0 0 0 2px rgba(10, 13, 20, 0.6)',
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
      </Card>

      {/* Edge Map: per-game diverging bars */}
      {edgeMap.length > 0 && (
        <Card>
          <Eyebrow color={SP.green}>Edge Map</Eyebrow>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '12px', marginTop: '8px' }}>
            {edgeMap.map((row, i) => {
              const abs = Math.abs(row.signed);
              const widthPct = Math.min(50, (abs / 12) * 50);
              const positive = row.signed >= 0;
              return (
                <div key={i} style={{
                  display: 'grid', gridTemplateColumns: '1fr 60px 1fr 90px',
                  gap: '8px', alignItems: 'center', fontSize: '13px',
                }}>
                  <span style={{
                    fontSize: '13px', fontWeight: 500, color: SP.text,
                    overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
                  }}>{row.matchup}</span>
                  <span style={{
                    fontFamily: SP.fontMono, fontSize: '12px', textAlign: 'right',
                    color: positive ? SP.green : SP.redSoft,
                  }}>{positive ? '+' : ''}{row.signed.toFixed(1)}%</span>
                  <div style={{ position: 'relative', height: '8px', background: SP.surface2, borderRadius: '2px' }}>
                    <span aria-hidden style={{
                      position: 'absolute', left: '50%', top: '-2px', bottom: '-2px',
                      width: '1px', background: SP.text5,
                    }} />
                    <div style={{
                      position: 'absolute', top: 0, bottom: 0, borderRadius: '2px',
                      ...(positive
                        ? { left: '50%', background: SP.green, width: `${widthPct}%` }
                        : { right: '50%', background: SP.redSoft, width: `${widthPct}%` }),
                    }} />
                  </div>
                  <span style={{
                    fontFamily: SP.fontMono, fontSize: '10px', textAlign: 'right',
                    color: row.isSignal ? SP.green : SP.text3,
                    letterSpacing: '0.04em', whiteSpace: 'nowrap',
                  }}>{row.isSignal ? 'Signal' : 'Below threshold'}</span>
                </div>
              );
            })}
          </div>
        </Card>
      )}

      {/* Line Movement */}
      {lmGames.length > 0 ? (
        <Card>
          <Eyebrow color={SP.green}>{lmType === 'moneyline' ? 'Moneyline Movement' : 'Line Movement'} · {lmGames.length} game{lmGames.length === 1 ? '' : 's'}</Eyebrow>
          <div style={{ marginTop: '8px' }}>
            {lmGames.map((g, i) => {
              const isML = lmType === 'moneyline';
              const movement = Number(g.movement) || 0;
              const direction = g.direction;
              const isFlat = direction === 'flat' || direction === 'none' || !direction;
              const significant = isML ? movement >= 20 : movement >= 1.5;
              const moveColor = direction === 'toward' ? SP.green : direction === 'away' ? SP.redSoft : SP.text4;
              const showOpenClose = isML && g.ml_open != null && g.ml_now != null;
              return (
                <div key={i} style={{
                  padding: '12px 0',
                  borderTop: i > 0 ? `1px solid ${SP.border2}` : 'none',
                  display: 'grid', gridTemplateColumns: '1fr auto', gap: '10px', alignItems: 'center',
                }}>
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
                          <span style={{ display: showOpenClose ? 'block' : 'inline', fontSize: '10px', color: moveColor, marginTop: showOpenClose ? '2px' : 0 }}>
                            {isML ? Math.round(movement) : movement.toFixed(1)}{isML ? '¢' : 'pts'} {direction}{significant ? (isML && movement >= 100 ? ' · large' : ' · sharp') : ''}
                          </span>
                        </>
                    }
                  </span>
                </div>
              );
            })}
            <div style={{
              marginTop: '14px', paddingTop: '12px', borderTop: `1px solid ${SP.border2}`,
              fontFamily: SP.fontMono, fontSize: '11px', color: SP.text3,
            }}>
              <span style={{ color: SP.green }}>{lmTowardCount}</span> toward ·{' '}
              <span style={{ color: SP.redSoft }}>{lmAwayCount}</span> away ·{' '}
              <span style={{ color: SP.text }}>{lmNoneCount}</span> flat
            </div>
          </div>
        </Card>
      ) : totalGames > 0 ? (
        <Card>
          <Eyebrow color={SP.green}>{lmType === 'moneyline' ? 'Moneyline Movement' : 'Line Movement'}</Eyebrow>
          <div style={{ fontSize: '12px', lineHeight: 1.5, color: SP.text3, marginTop: '4px' }}>
            Open-line history not yet recorded for this slate. Movement table populates once an opening snapshot exists for each game.
          </div>
        </Card>
      ) : null}

      {/* Model vs Market Delta */}
      {mmdGames.length > 0 ? (
        <Card>
          <Eyebrow color={SP.green}>Model vs Market Delta · {sportRunsLabel}</Eyebrow>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', marginTop: '8px' }}>
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
                <div key={i} style={{ display: 'grid', gridTemplateColumns: '110px 1fr 50px', gap: '8px', alignItems: 'center' }}>
                  <span style={{
                    fontSize: '12px', fontWeight: 500, color: SP.text,
                    overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
                  }}>
                    {teamLabel}
                    {lineText && (<span style={{ color: SP.text3, fontFamily: SP.fontMono, fontSize: '11px', marginLeft: '4px' }}>{lineText}</span>)}
                  </span>
                  <div style={{ position: 'relative', height: '7px', background: SP.surface2, borderRadius: '2px' }}>
                    <span aria-hidden style={{ position: 'absolute', left: '50%', top: '-2px', bottom: '-2px', width: '1px', background: SP.text5 }} />
                    {isZero ? (
                      <div style={{ position: 'absolute', top: 0, bottom: 0, left: 'calc(50% - 1px)', width: '2px', background: SP.text3 }} />
                    ) : delta > 0 ? (
                      <div style={{ position: 'absolute', top: 0, bottom: 0, left: '50%', width: `${widthPct}%`, background: SP.green, borderRadius: '2px' }} />
                    ) : (
                      <div style={{ position: 'absolute', top: 0, bottom: 0, right: '50%', width: `${widthPct}%`, background: SP.redSoft, borderRadius: '2px' }} />
                    )}
                  </div>
                  <span style={{
                    fontFamily: SP.fontMono, fontSize: '11px', textAlign: 'right',
                    color: isZero ? SP.text4 : delta > 0 ? SP.green : SP.redSoft,
                  }}>{isZero ? '0.0' : `${delta > 0 ? '+' : ''}${delta.toFixed(1)}`}</span>
                </div>
              );
            })}
          </div>
          {avgDelta != null && (
            <div style={{
              paddingTop: '14px', marginTop: '14px',
              borderTop: `1px solid ${SP.border2}`,
              display: 'flex', justifyContent: 'space-between', alignItems: 'center',
            }}>
              <span style={{ fontFamily: SP.fontMono, fontSize: '10px', letterSpacing: '0.16em', textTransform: 'uppercase', color: SP.text3 }}>
                Avg model-market delta
              </span>
              <span style={{ fontFamily: SP.fontMono, fontSize: '13px', color: SP.green, fontWeight: 500 }}>
                {Number(avgDelta).toFixed(1)} {sportRunsLabel}
              </span>
            </div>
          )}
        </Card>
      ) : totalGames > 0 ? (
        <Card>
          <Eyebrow color={SP.green}>Model vs Market Delta</Eyebrow>
          <div style={{ fontSize: '12px', lineHeight: 1.5, color: SP.text3, marginTop: '4px' }}>
            Per-game delta ranking populates once today's model run reaches every game in the slate.
          </div>
        </Card>
      ) : null}

      {/* Near Misses */}
      {nearMisses.length > 0 && (
        <Card>
          <Eyebrow color={SP.green}>Near Misses</Eyebrow>
          <div style={{ marginTop: '6px' }}>
            {nearMisses.map((nm, i) => (
              <div key={i} style={{
                padding: '12px 0',
                borderBottom: i < nearMisses.length - 1 ? `1px solid ${SP.border2}` : 'none',
              }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', marginBottom: '4px' }}>
                  <span style={{ fontSize: '14px', fontWeight: 500, color: SP.text }}>{nm.matchup}</span>
                  <span style={{ fontFamily: SP.fontMono, fontSize: '13px', color: SP.green }}>
                    +{nm.pct.toFixed(1)}%
                  </span>
                </div>
                <div style={{ fontFamily: SP.fontMono, fontSize: '11px', color: SP.text3 }}>
                  Edge below threshold.
                </div>
              </div>
            ))}
          </div>
        </Card>
      )}

      {/* Implication callout */}
      <div style={{
        borderLeft: `3px solid ${SP.green}`, background: 'rgba(90, 158, 114, 0.04)',
        padding: '18px 20px', borderRadius: '0 8px 8px 0',
        marginTop: '4px', marginBottom: '24px',
      }}>
        <div style={{
          display: 'flex', alignItems: 'center', gap: '8px',
          fontFamily: SP.fontMono, fontSize: '11px', fontWeight: 500,
          letterSpacing: '0.22em', textTransform: 'uppercase', color: SP.green,
          marginBottom: '8px',
        }}>
          <span style={{ width: 7, height: 7, borderRadius: '50%', background: SP.green }} />
          Implication
        </div>
        <div style={{ fontFamily: SP.fontSans, fontSize: '15px', fontWeight: 500, color: SP.text, lineHeight: 1.4 }}>
          {implication}
        </div>
      </div>

      {/* Sharp Principle */}
      <div style={{ marginBottom: '24px' }}>
        <div style={{
          fontFamily: SP.fontMono, fontSize: '11px', fontWeight: 500,
          letterSpacing: '0.22em', textTransform: 'uppercase', color: SP.text3,
          marginBottom: '12px',
        }}>Sharp Principle</div>
        <p style={{
          fontFamily: SP.fontSerif, fontSize: '17px', lineHeight: 1.55, color: SP.text,
          margin: 0,
        }}>{sharpPrinciple}</p>
      </div>

      {/* Updated time footer */}
      {updatedTime && (
        <div style={{
          textAlign: 'center', padding: '16px 0',
          fontFamily: SP.fontMono, fontSize: '10px',
          letterSpacing: '0.18em', textTransform: 'uppercase', color: SP.text4,
        }}>
          Intelligence updated <span style={{ color: SP.green }}>{updatedTime}</span>
        </div>
      )}
    </div>
  );
}

function Card({ children }) {
  return (
    <div style={{
      background: SP.surface, border: `1px solid ${SP.border}`,
      borderRadius: '12px', padding: '20px 20px 22px', marginBottom: '14px',
    }}>{children}</div>
  );
}

function Eyebrow({ color, children }) {
  return (
    <div style={{
      fontFamily: SP.fontMono, fontSize: '10px', fontWeight: 500,
      letterSpacing: '0.22em', textTransform: 'uppercase', color: color || SP.green,
      marginBottom: '8px',
    }}>{children}</div>
  );
}
