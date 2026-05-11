import { useState, useEffect } from 'react';
import { apiGet, apiPost, apiDelete } from '../../hooks/useApi';
import teamAbbr from '../../utils/teamAbbr';
import sportDisplay from '../../utils/sportDisplay';
import {
  shouldShowLiveBlock,
  isFinalState,
  isInPlayState,
  isHomeSidePick,
  computeLiveCover,
} from '../../utils/liveScore';
import { isIOSPlatform } from '../../utils/platformCta';

// v4.3 Daily Top Signal card. Pro-only render path. Replaces the older
// PickCard for the home pick-day slot. Source: docs mockup approved
// 2026-05-06.
//
// PickCard.jsx still ships for any other consumer (TodayTab, history),
// and exports its own helpers; the new card is a clean v4.3 surface
// rather than a refactor of the prior 1000-line component.
//
// Prop surface kept compatible with the prior PickCard so PicksTab
// integration is a drop-in: { pick, isPro, liveScore, onUpgrade,
// onTrack, onNavigate, unitSize, marketReport }. marketReport is new
// and powers the 'Market Context' section.

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

function fmtSpread(val) {
  if (val == null) return '—';
  const n = parseFloat(val);
  if (Number.isNaN(n)) return '—';
  if (Number.isInteger(n)) return n > 0 ? `+${n}` : `${n}`;
  return n > 0 ? `+${n.toFixed(1)}` : `${n.toFixed(1)}`;
}

function fmtEdge(val) {
  if (val == null) return '—';
  const n = parseFloat(val);
  if (Number.isNaN(n)) return '—';
  return `${n > 0 ? '+' : ''}${n.toFixed(1)}%`;
}

function getEdgeTier(edgePct) {
  if (edgePct == null) return 'WK';
  const e = Math.abs(parseFloat(edgePct));
  if (e >= 10) return 'STR';
  if (e >= 7) return 'MOD';
  return 'WK';
}

function fmtMatchupTime(startTime) {
  if (!startTime) return null;
  try {
    const d = new Date(startTime);
    if (Number.isNaN(d.getTime())) return null;
    const monthAbbr = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
    const parts = new Intl.DateTimeFormat('en-US', {
      timeZone: 'America/New_York',
      month: 'numeric', day: 'numeric',
      hour: 'numeric', minute: '2-digit', hour12: true,
    }).formatToParts(d);
    const month = parseInt(parts.find((p) => p.type === 'month')?.value || '0', 10);
    const day = parts.find((p) => p.type === 'day')?.value || '';
    const h = parts.find((p) => p.type === 'hour')?.value || '';
    const m = parts.find((p) => p.type === 'minute')?.value || '';
    const a = (parts.find((p) => p.type === 'dayPeriod')?.value || '').toUpperCase();
    return {
      date: month && day ? `${monthAbbr[month - 1]} ${day}` : null,
      time: h && m ? `${h}:${m} ${a} ET` : null,
    };
  } catch { return null; }
}

function fmtCountdown(startTime, sport) {
  if (!startTime) return null;
  try {
    const start = new Date(startTime).getTime();
    const now = Date.now();
    const diffMs = start - now;
    if (diffMs <= 0) return null;
    const totalMin = Math.floor(diffMs / 60000);
    const h = Math.floor(totalMin / 60);
    const m = totalMin % 60;
    // MLB tips with first pitch; basketball (NBA, WNBA) tips with tipoff.
    const verb = (String(sport || '').toLowerCase() === 'mlb') ? 'First pitch' : 'Tipoff';
    if (h === 0) return `${verb} in ${m}m`;
    return `${verb} in ${h}h ${String(m).padStart(2, '0')}m`;
  } catch { return null; }
}

function fmtSide(side, line) {
  if (!side) return '—';
  if (line != null && side.includes(String(Math.abs(parseFloat(line))))) {
    const i = side.lastIndexOf(' ');
    if (i > 0) return { team: side.slice(0, i), line: side.slice(i + 1) };
    return { team: side, line: null };
  }
  return { team: side, line: line != null ? fmtSpread(line) : null };
}

export default function DailyTopSignalCard({ pick, isPro, onTrack, onNavigate, marketReport, liveScore, onOpenJournal, unitSize = 100 }) {
  const [tracking, setTracking] = useState(false);
  const [tracked, setTracked] = useState(false);
  const [trackedBetId, setTrackedBetId] = useState(null);
  const [reasoningOpen, setReasoningOpen] = useState(false);
  const [showForm, setShowForm] = useState(false);
  const [trackError, setTrackError] = useState(null);
  const [formLine, setFormLine] = useState('');
  const [formOdds, setFormOdds] = useState('-110');
  const [formUnits, setFormUnits] = useState('1');
  const [formWager, setFormWager] = useState(String(unitSize));
  const [calibrationNoteDismissed, setCalibrationNoteDismissed] = useState(() => {
    try { return typeof window !== 'undefined' && window.localStorage.getItem('sp_banner_dismissed:dts-calibration-note') === '1'; } catch { return false; }
  });

  // Sync form defaults when pick or unitSize lands.
  useEffect(() => {
    if (pick?.line != null) setFormLine(String(pick.line));
    if (pick?.market_odds != null) setFormOdds(String(pick.market_odds));
    if (pick?.stake_guidance?.flat_stake != null) {
      const u = Number(pick.stake_guidance.flat_stake);
      setFormUnits(String(u));
      setFormWager(String(Math.round(u * unitSize)));
    } else {
      setFormWager(String(unitSize));
    }
  }, [pick?.id, pick?.line, pick?.market_odds, pick?.stake_guidance?.flat_stake, unitSize]);

  useEffect(() => {
    if (!isPro || !pick?.id) return;
    let cancelled = false;
    apiGet('/bets').then((res) => {
      if (cancelled) return;
      const match = (res?.bets || []).find((b) => b?.linked_pick?.id === pick.id);
      if (match) { setTracked(true); setTrackedBetId(match.id); }
    }).catch(() => {});
    return () => { cancelled = true; };
  }, [pick?.id, isPro]);

  const sportLabel = (pick?.sport || 'mlb').toUpperCase();
  const isCalibration = pick?.model_phase === 'calibration';
  const matchup = pick?.away_team && pick?.home_team
    ? `${pick.away_team} vs ${pick.home_team}`
    : (pick?.matchup || '');
  const sideParts = fmtSide(pick?.side, pick?.line);
  const teamName = typeof sideParts === 'object' ? sideParts.team : sideParts;
  const lineText = typeof sideParts === 'object' ? sideParts.line : null;
  const edgeText = fmtEdge(pick?.edge_pct);
  const startInfo = fmtMatchupTime(pick?.start_time);
  const oddsText = pick?.market_odds != null
    ? (pick.market_odds > 0 ? `+${pick.market_odds}` : `${pick.market_odds}`)
    : null;
  const countdown = fmtCountdown(pick?.start_time, pick?.sport);

  const marketLine = pick?.line != null ? fmtSpread(pick.line) : '—';
  const modelLine = pick?.model_projection != null
    ? fmtSpread(pick.model_projection)
    : (pick?.predicted_margin != null ? fmtSpread(pick.predicted_margin) : '—');
  const tier = getEdgeTier(pick?.edge_pct);
  const sizeUnits = pick?.position_size_pct != null
    ? `${(Number(pick.position_size_pct) / 100).toFixed(1)}u`
    : null;

  const flatStake = pick?.stake_guidance?.flat_stake;
  const kellyStake = pick?.stake_guidance?.kelly_stake;
  const flatLabel = flatStake != null ? `${Number(flatStake).toFixed(1)}u` : null;
  const kellyLabel = kellyStake != null ? `${Number(kellyStake).toFixed(1)}u` : null;

  const observationText = (() => {
    const sigs = pick?.model_signals || [];
    if (!sigs.length) return null;
    return String(sigs[0]).trim();
  })();
  const reasoningSignals = (pick?.model_signals || []).slice(1, 4);

  const lean = marketReport?.market_lean;
  const contextText = (() => {
    if (!lean || !lean.total_edges) return null;
    if (lean.underdogs > lean.favorites) {
      return { lead: 'Underdogs showing unusual value.', detail: `${lean.underdogs} of ${lean.total_edges} edges on dogs across tonight's slate.` };
    }
    if (lean.favorites > lean.underdogs) {
      return { lead: 'Favorites carrying the slate.', detail: `${lean.favorites} of ${lean.total_edges} edges on favorites tonight.` };
    }
    return null;
  })();

  const playableTo = pick?.playable_to;
  const hasPlayability = pick?.line != null && playableTo != null;
  const playFloor = hasPlayability
    ? Math.min(Number(pick.line), Number(playableTo))
    : null;
  const playTarget = hasPlayability
    ? Math.max(Number(pick.line), Number(playableTo))
    : null;

  const bestBook = pick?.best_book || pick?.sportsbook;
  const postedLabel = pick?.posted_time || '2h before tip';

  const edgePct = parseFloat(pick?.edge_pct) || 0;
  const edgeBarPct = Math.min(50, Math.abs(edgePct) / 10 * 50);

  const handleUnitsChange = (val) => {
    setFormUnits(val);
    const u = parseFloat(val) || 1;
    setFormWager(String(Math.round(u * unitSize)));
  };
  const handleWagerChange = (val) => {
    setFormWager(val);
    const w = parseFloat(val) || unitSize;
    setFormUnits(String(parseFloat((w / unitSize).toFixed(2))));
  };

  const handleTrack = () => {
    if (!isPro || tracked) return;
    setShowForm((v) => !v);
    setTrackError(null);
  };

  const handleSubmit = async () => {
    if (tracking) return;
    setTracking(true);
    setTrackError(null);
    try {
      const res = await apiPost('/bets', {
        pick_id: pick.id,
        units_wagered: parseFloat(formUnits) || 1,
        bet_amount: parseInt(formWager, 10) || unitSize,
        odds: parseInt(formOdds, 10) || pick.market_odds || -110,
        line_at_bet: parseFloat(formLine) || pick.line,
        bet_type: 'spread',
      });
      if (res?.success === false) {
        if ((res.error || '').toLowerCase().includes('already tracking')) {
          setTracked(true); setShowForm(false);
        } else {
          setTrackError(res.error || 'Failed to track');
        }
      } else if (res?.bet?.id) {
        // Bet created. Flip local state so the button shows the
        // persistent "Tracking · TEX +1.5 · 1.5u" affordance and
        // collapse the form. Do NOT call onTrack() here — that
        // callback is wired to onNavigate('profile', 'bets', ...)
        // which would page-redirect the user away from home. The
        // inline form is the whole point of tracking on this card,
        // so we stay put.
        setTracked(true);
        setTrackedBetId(res.bet.id);
        setShowForm(false);
      } else {
        setTrackError('Failed to track');
      }
    } catch (e) {
      const msg = e?.message || 'Failed to track';
      if (msg.toLowerCase().includes('already tracking')) {
        setTracked(true); setShowForm(false);
      } else {
        setTrackError(msg);
      }
    } finally {
      setTracking(false);
    }
  };

  const handleUntrack = async () => {
    if (!trackedBetId) return;
    try {
      await apiDelete(`/bets/${trackedBetId}`);
      setTracked(false);
      setTrackedBetId(null);
    } catch { /* swallow */ }
  };

  // Free user paywall: render the v4.3 "qualified edge detected" lock card
  // with blurred sample values + Observation teaser + Pro unlocks list +
  // Start trial CTA. Reads pick.locked from /api/picks/today (the existing
  // server-side paywall mask) so the gate matches the data shape.
  const isLocked = (pick?.locked === true) || !isPro;
  if (isLocked) {
    // Use the shared isIOSPlatform util so iOS Safari (UA-based) is also
    // covered, not just the Capacitor WebView. The earlier inline check
    // returned false when Apple reviewers landed via Safari and let
    // "Card required" through.
    const iosCta = isIOSPlatform();
    return (
      <div style={{
        background: SP.surface,
        border: `1px solid ${SP.border}`,
        borderRadius: '14px',
        overflow: 'hidden',
        position: 'relative',
        marginBottom: '18px',
      }}>
        <div aria-hidden style={{
          position: 'absolute', top: 0, left: 20, right: 20, height: '2px',
          background: `linear-gradient(90deg, transparent, ${SP.green} 20%, ${SP.green} 80%, transparent)`,
          opacity: 0.55,
        }} />

        {/* HEADER: qualified-edge pill, matchup serif title, time + countdown */}
        <div style={{ padding: '18px 18px 14px' }}>
          <div style={{
            display: 'inline-flex', alignItems: 'center', gap: '6px',
            padding: '5px 11px', border: `1px solid ${SP.green}`, borderRadius: '4px',
            fontFamily: SP.fontMono, fontSize: '10px', fontWeight: 500,
            letterSpacing: '0.2em', textTransform: 'uppercase', color: SP.green,
            marginBottom: '14px',
          }}>
            <span style={{ width: 6, height: 6, borderRadius: '50%', background: SP.green }} />
            Qualified edge detected
          </div>
          {matchup && (
            <h1 style={{
              margin: '0 0 6px', fontFamily: SP.fontSerif, fontSize: '22px',
              fontWeight: 600, color: SP.text, lineHeight: 1.2, letterSpacing: '-0.005em',
            }}>{matchup}</h1>
          )}
          <div style={{
            display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap',
            fontFamily: SP.fontMono, fontSize: '11px', color: SP.text3,
            letterSpacing: '0.04em',
          }}>
            {startInfo?.time && <span>{startInfo.time}</span>}
            {startInfo?.time && countdown && <span>·</span>}
            {countdown && (
              <span style={{
                display: 'inline-flex', alignItems: 'center', gap: '6px',
                padding: '3px 9px', border: '1px solid rgba(245, 158, 11, 0.4)',
                background: SP.amberSoft, borderRadius: '4px', color: SP.amber,
                fontWeight: 500, letterSpacing: '0.06em',
              }}>
                <span style={{
                  width: 5, height: 5, background: SP.amber, borderRadius: '50%',
                  animation: 'spDtsPulse 2s infinite',
                }} />
                {countdown}
              </span>
            )}
          </div>
        </div>

        {/* 4-cell stat grid with BLURRED sample values. Lets the user see
            the SHAPE of the data without the actual signal. Static
            placeholder values rendered with filter:blur — no real
            backend numbers leak through. */}
        <div style={{
          display: 'grid', gridTemplateColumns: '1fr 1px 1fr 1px 1fr 1px 1fr',
          background: SP.bg,
          borderTop: `1px solid ${SP.border2}`,
          borderBottom: `1px solid ${SP.border2}`,
        }}>
          {[
            { label: 'Side', value: '+1.5', tone: 'mono' },
            { label: 'Line', value: '-115', tone: 'mono' },
            { label: 'Edge', value: '+6.0%', tone: 'mono' },
            { label: 'Size', value: '1.5u', tone: 'mono' },
          ].flatMap((cell, i, arr) => [
            <div key={`bp-${cell.label}`} style={{ padding: '14px 4px 13px', textAlign: 'center' }}>
              <div style={{
                fontFamily: SP.fontMono, fontSize: '9px',
                letterSpacing: '0.22em', textTransform: 'uppercase', color: SP.text4,
                marginBottom: '6px',
              }}>{cell.label}</div>
              <div
                aria-hidden
                style={{
                  fontFamily: SP.fontMono, fontSize: '14px', fontWeight: 500,
                  color: SP.text, lineHeight: 1,
                  filter: 'blur(6px)',
                  userSelect: 'none', pointerEvents: 'none',
                }}
              >{cell.value}</div>
            </div>,
            i < arr.length - 1 ? <div key={`bpd-${i}`} style={{ background: SP.border2 }} /> : null,
          ])}
        </div>

        {/* OBSERVATION: green-soft teaser card. Generic free-user copy,
            ends with the Pro hint that surfaces what's behind the gate. */}
        <div style={{
          background: SP.greenSoft,
          borderLeft: `2px solid ${SP.green}`,
          margin: '14px 14px 0',
          padding: '12px 14px',
          borderRadius: '0 8px 8px 0',
        }}>
          <div style={{
            fontFamily: SP.fontMono, fontSize: '9px', fontWeight: 500,
            letterSpacing: '0.22em', textTransform: 'uppercase', color: SP.green,
            marginBottom: '6px',
          }}>Observation</div>
          <div style={{
            fontFamily: SP.fontSerif, fontSize: '13px', lineHeight: 1.5, color: SP.text,
          }}>
            Multi-factor model edge with ensemble agreement across all four models. Specific reasoning, line, and sizing visible with Pro.
          </div>
        </div>

        {/* PRO UNLOCKS benefit list — checkmark + label rows */}
        <div style={{ padding: '16px 18px 6px' }}>
          <div style={{
            fontFamily: SP.fontMono, fontSize: '9px', fontWeight: 500,
            letterSpacing: '0.22em', textTransform: 'uppercase', color: SP.text3,
            marginBottom: '10px',
          }}>Pro unlocks</div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', marginBottom: '14px' }}>
            {[
              'Side, line, edge',
              'Flat and Kelly sizing',
              'Full quant reasoning',
              'CLV audit and tracked record',
            ].map((label) => (
              <div key={label} style={{
                display: 'flex', alignItems: 'center', gap: '10px',
                fontSize: '13px', color: SP.text,
              }}>
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke={SP.green} strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" style={{ flexShrink: 0 }}>
                  <path d="M20 6L9 17l-5-5" />
                </svg>
                <span style={{ fontFamily: SP.fontSans, fontWeight: 500 }}>{label}</span>
              </div>
            ))}
          </div>
        </div>

        {/* CTA section. Routes through onNavigate('profile', 'upgrade') on
            all platforms — UpgradeScreen.jsx handles platform-specific
            payment flow internally (RevenueCat IAP on iOS, Stripe on
            Android + web). Subtext is platform-conditional only because
            iOS IAP doesn't take a card up front, so "Card required" copy
            would be inaccurate there. */}
        <div style={{ padding: '8px 18px 18px' }}>
          <button
            onClick={() => {
              if (typeof onNavigate === 'function') onNavigate('profile', 'upgrade');
            }}
            style={{
              width: '100%', padding: '16px',
              background: SP.green, border: 'none', borderRadius: '10px',
              fontFamily: SP.fontSans, fontSize: '15px', fontWeight: 600,
              color: '#062019', letterSpacing: '0.01em',
              cursor: 'pointer', marginBottom: '8px',
            }}
          >Start 14-day free trial</button>
          <div style={{
            textAlign: 'center', fontFamily: SP.fontMono, fontSize: '10px',
            color: SP.text4, letterSpacing: '0.16em', textTransform: 'uppercase',
          }}>
            {iosCta ? 'Cancel anytime' : 'Card required · Cancel anytime'}
          </div>
        </div>
      </div>
    );
  }

  // ─────────────────────────────────────────────────────────────
  // ONE-SCREEN UNLOCKED RENDER (spec: docs/wnba-signal-card-one-screen.html)
  //
  // Consolidations vs the prior layout:
  //   - 4-cell stat grid + separate Flat/Kelly block -> single 5-cell grid
  //     (Market/Model/Tier/Flat/Kelly). SIZE cell dropped; flat stake is
  //     now the primary sizing display.
  //   - Standalone Observation + Market Context cards -> one combined
  //     green-bordered block, separated by a thin green-soft divider.
  //   - Edge + Value bars compressed to 4px tracks, no card chrome.
  //   - Signal reasoning accordion header + posted-time/best-book row
  //     merged into one row. Expanded content drops below the row.
  //   - Sharp Journal cross-link converted from a freestanding card into
  //     an inline footer with a subtle blue tint.
  //   - Calibration chip in the header REMOVED entirely (per the WNBA
  //     spec note). Same component renders for MLB/WNBA/NBA: no chip.
  //   - "For informational purposes only" disclaimer REMOVED from this
  //     view; it lives in Account > Disclosures.
  //
  // Tracking flow is unchanged: same button states, same inline form,
  // same handleTrack / handleUntrack / handleSubmit handlers.
  // ─────────────────────────────────────────────────────────────
  return (
    <div style={{
      background: SP.surface,
      border: `1px solid ${SP.border}`,
      borderRadius: '14px',
      overflow: 'hidden',
      position: 'relative',
      marginBottom: '14px',
    }}>
      <div aria-hidden style={{
        position: 'absolute', top: 0, left: '20px', right: '20px', height: 2,
        background: `linear-gradient(90deg, transparent, ${SP.green} 20%, ${SP.green} 80%, transparent)`,
        opacity: 0.55,
      }} />

      <style>{`
        @keyframes spDtsPulse {
          0%   { box-shadow: 0 0 0 0 rgba(245, 158, 11, 0.5); }
          70%  { box-shadow: 0 0 0 5px rgba(245, 158, 11, 0); }
          100% { box-shadow: 0 0 0 0 rgba(245, 158, 11, 0); }
        }
        @media (prefers-reduced-motion: reduce) {
          [data-sp-pulse] { animation: none !important; }
        }
      `}</style>

      {/* HEADER (compact) */}
      <div style={{ padding: '14px 16px 10px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px', flexWrap: 'wrap', marginBottom: '8px' }}>
          <span style={{
            display: 'inline-flex', alignItems: 'center',
            padding: '3px 8px', border: `1px solid ${SP.border}`, borderRadius: '4px',
            fontFamily: SP.fontMono, fontSize: '9px', fontWeight: 500,
            letterSpacing: '0.2em', textTransform: 'uppercase', color: SP.text2,
          }}>{sportLabel}</span>
        </div>

        {matchup && (
          <div style={{
            fontFamily: SP.fontMono, fontSize: '10px',
            color: SP.text3, letterSpacing: '0.04em',
            marginBottom: '4px',
          }}>{matchup}</div>
        )}

        <div style={{ display: 'flex', alignItems: 'baseline', justifyContent: 'space-between', gap: '10px', marginBottom: '4px', flexWrap: 'wrap' }}>
          <span style={{
            fontFamily: SP.fontSerif, fontSize: '21px', fontWeight: 600,
            color: SP.text, lineHeight: 1.15, letterSpacing: '-0.005em',
          }}>
            {teamName}
            {lineText && <span style={{ color: SP.green, marginLeft: '6px' }}>{lineText}</span>}
          </span>
          <span style={{
            fontFamily: SP.fontMono, fontSize: '21px', fontWeight: 500,
            color: SP.green, lineHeight: 1, whiteSpace: 'nowrap',
          }}>{edgeText}</span>
        </div>

        {(startInfo || oddsText || countdown) && (
          <div style={{
            display: 'flex', alignItems: 'center', gap: '8px',
            flexWrap: 'wrap',
            fontFamily: SP.fontMono, fontSize: '10px',
            color: SP.text3, letterSpacing: '0.04em',
          }}>
            {startInfo?.time && <span>{startInfo.time}</span>}
            {startInfo?.time && (oddsText || countdown) && <span style={{ color: SP.text5 }}>·</span>}
            {oddsText && <span>{oddsText}</span>}
            {countdown && (
              <span data-sp-pulse style={{
                display: 'inline-flex', alignItems: 'center', gap: '6px',
                padding: '3px 9px',
                background: SP.amberSoft,
                border: '1px solid rgba(245, 158, 11, 0.4)',
                borderRadius: '4px',
                color: SP.amber, fontWeight: 500, letterSpacing: '0.06em',
              }}>
                <span aria-hidden style={{
                  width: '5px', height: '5px', borderRadius: '50%',
                  background: SP.amber, animation: 'spDtsPulse 2s infinite',
                }} />
                {countdown}
              </span>
            )}
          </div>
        )}

        {liveScore && shouldShowLiveBlock(liveScore.state) && (
          <DtsLiveBlock liveScore={liveScore} pick={pick} />
        )}
      </div>

      {/* 5-CELL STAT GRID (replaces 4-cell + Flat/Kelly block) */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: '1fr 1px 1fr 1px 1fr 1px 1fr 1px 1fr',
        background: SP.bg,
        borderTop: `1px solid ${SP.border2}`,
        borderBottom: `1px solid ${SP.border2}`,
      }}>
        {[
          { label: 'Market', value: marketLine, tone: 'plain' },
          { label: 'Model', value: modelLine, tone: 'green' },
          { label: 'Tier', value: tier, tone: 'serif' },
          { label: 'Flat', value: flatLabel || '—', tone: 'plain' },
          { label: 'Kelly', value: kellyLabel || '—', tone: 'plain' },
        ].flatMap((cell, i, arr) => [
          <div key={`c-${cell.label}`} style={{ padding: '10px 4px 9px', textAlign: 'center' }}>
            <div style={{
              fontFamily: SP.fontMono, fontSize: '8px',
              letterSpacing: '0.22em', textTransform: 'uppercase', color: SP.text4,
              marginBottom: '4px',
            }}>{cell.label}</div>
            <div style={{
              fontFamily: cell.tone === 'serif' ? SP.fontSerif : SP.fontMono,
              fontSize: '13px',
              fontWeight: cell.tone === 'serif' ? 600 : 500,
              color: cell.tone === 'green' ? SP.green : SP.text,
              lineHeight: 1,
            }}>{cell.value}</div>
          </div>,
          i < arr.length - 1 ? <div key={`d-${i}`} style={{ background: SP.border2 }} /> : null,
        ])}
      </div>

      {/* OBSERVATION + MARKET CONTEXT (combined) */}
      {(observationText || contextText) && (
        <div style={{
          background: SP.greenSoft,
          borderLeft: `2px solid ${SP.green}`,
          margin: '12px 12px 10px',
          padding: '11px 13px',
          borderRadius: '0 8px 8px 0',
        }}>
          {observationText && (
            <>
              <div style={{
                fontFamily: SP.fontMono, fontSize: '9px', fontWeight: 500,
                letterSpacing: '0.22em', textTransform: 'uppercase', color: SP.green,
                marginBottom: '5px',
              }}>Observation</div>
              <div style={{
                fontFamily: SP.fontSerif, fontSize: '13px',
                lineHeight: 1.42, color: SP.text,
              }}>{observationText}</div>
            </>
          )}
          {contextText && (
            <div style={{
              marginTop: observationText ? '7px' : 0,
              paddingTop: observationText ? '7px' : 0,
              borderTop: observationText ? '1px solid rgba(90, 158, 114, 0.15)' : 'none',
              fontFamily: SP.fontSans, fontSize: '11px',
              lineHeight: 1.42, color: SP.text2,
            }}>
              <strong style={{ color: SP.text, fontWeight: 500 }}>Slate:</strong>{' '}
              {contextText.lead} {contextText.detail}
            </div>
          )}
        </div>
      )}

      {/* COMPACT BAR PAIR */}
      {(pick?.edge_pct != null || hasPlayability) && (
        <div style={{ padding: '0 16px 11px' }}>
          {pick?.edge_pct != null && (
            <div style={{ marginBottom: hasPlayability ? '8px' : 0 }}>
              <div style={{
                display: 'flex', justifyContent: 'space-between', alignItems: 'baseline',
                marginBottom: '4px',
              }}>
                <span style={{
                  fontFamily: SP.fontMono, fontSize: '9px',
                  letterSpacing: '0.22em', textTransform: 'uppercase', color: SP.text3,
                }}>Edge</span>
                <span style={{
                  fontFamily: SP.fontMono, fontSize: '11px', fontWeight: 500,
                  color: edgePct >= 0 ? SP.green : SP.redSoft,
                }}>{edgePct >= 0 ? '+' : ''}{edgePct.toFixed(1)}pp</span>
              </div>
              <div style={{
                position: 'relative', height: '4px',
                background: SP.surface2, borderRadius: '2px',
              }}>
                <span aria-hidden style={{
                  position: 'absolute', left: '50%', top: '-2px', bottom: '-2px',
                  width: '1px', background: SP.text5,
                }} />
                <div style={{
                  position: 'absolute', top: 0, bottom: 0,
                  [edgePct >= 0 ? 'left' : 'right']: '50%',
                  width: `${edgeBarPct}%`,
                  background: edgePct >= 0 ? SP.green : SP.redSoft,
                  borderRadius: '2px',
                }} />
              </div>
              <div style={{
                display: 'flex', justifyContent: 'space-between', marginTop: '2px',
                fontFamily: SP.fontMono, fontSize: '8px', color: SP.text4, letterSpacing: '0.04em',
              }}>
                <span>-10pp</span><span>0</span><span>+10pp</span>
              </div>
            </div>
          )}
          {hasPlayability && (
            <div>
              <div style={{
                display: 'flex', justifyContent: 'space-between', alignItems: 'baseline',
                marginBottom: '4px',
              }}>
                <span style={{
                  fontFamily: SP.fontMono, fontSize: '9px',
                  letterSpacing: '0.22em', textTransform: 'uppercase', color: SP.text3,
                }}>Value</span>
                <span style={{
                  fontFamily: SP.fontMono, fontSize: '10px', color: SP.text3,
                  letterSpacing: '0.04em',
                }}>Playable down to <span style={{ color: SP.green }}>{fmtSpread(playableTo)}</span></span>
              </div>
              <div style={{
                height: '4px', background: SP.surface2,
                borderRadius: '2px', overflow: 'hidden',
              }}>
                <div style={{
                  height: '100%', width: '100%',
                  background: SP.green, borderRadius: '2px',
                }} />
              </div>
            </div>
          )}
        </div>
      )}

      {/* SIGNAL REASONING + TIMING (single row) */}
      {(reasoningSignals.length > 0 || bestBook || postedLabel) && (
        <>
          <div
            onClick={reasoningSignals.length > 0 ? () => setReasoningOpen((v) => !v) : undefined}
            role={reasoningSignals.length > 0 ? 'button' : undefined}
            tabIndex={reasoningSignals.length > 0 ? 0 : undefined}
            aria-expanded={reasoningSignals.length > 0 ? reasoningOpen : undefined}
            style={{
              display: 'flex', alignItems: 'center',
              justifyContent: 'space-between', gap: '12px',
              padding: '10px 16px',
              borderTop: `1px solid ${SP.border2}`,
              cursor: reasoningSignals.length > 0 ? 'pointer' : 'default',
              minHeight: '44px',
            }}
          >
            {reasoningSignals.length > 0 ? (
              <span style={{
                fontFamily: SP.fontMono, fontSize: '10px', fontWeight: 500,
                letterSpacing: '0.22em', textTransform: 'uppercase', color: SP.text2,
                display: 'inline-flex', alignItems: 'center', gap: '6px',
              }}>
                Signal reasoning
                <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke={SP.text3} strokeWidth="2.5"
                     style={{ transform: reasoningOpen ? 'rotate(180deg)' : 'none', transition: 'transform 0.2s' }}>
                  <path d="M6 9l6 6 6-6" />
                </svg>
              </span>
            ) : <span />}
            <span style={{
              fontFamily: SP.fontMono, fontSize: '9px',
              letterSpacing: '0.16em', textTransform: 'uppercase',
              color: SP.text3, textAlign: 'right',
            }}>
              {postedLabel && <span style={{ color: SP.text, fontWeight: 500 }}>{postedLabel}</span>}
              {postedLabel && bestBook && <span style={{ color: SP.text5, margin: '0 6px' }}>·</span>}
              {bestBook && <>Best at <span style={{ color: SP.text, fontWeight: 500 }}>{bestBook}</span></>}
            </span>
          </div>
          {reasoningOpen && reasoningSignals.length > 0 && (
            <div style={{
              padding: '0 16px 12px',
              borderTop: `1px solid ${SP.border2}`,
            }}>
              <ul style={{ margin: '10px 0 0', padding: 0, listStyle: 'none' }}>
                {reasoningSignals.map((s, i) => (
                  <li key={i} style={{
                    fontSize: '12px', lineHeight: 1.5, color: SP.text2,
                    paddingLeft: '12px', position: 'relative', marginBottom: '6px',
                  }}>
                    <span aria-hidden style={{
                      position: 'absolute', left: 0, top: '7px',
                      width: '4px', height: '4px', borderRadius: '50%', background: SP.green,
                    }} />
                    {s}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </>
      )}

      {/* TRACKING BUTTON + INLINE FORM (unchanged flow) */}
      <div style={{ padding: '12px 16px 14px', display: 'flex', flexDirection: 'column', gap: '10px' }}>
        <button
          onClick={tracked ? handleUntrack : handleTrack}
          disabled={tracking}
          style={{
            width: '100%', padding: '12px 16px',
            background: tracked
              ? 'rgba(90, 158, 114, 0.1)'
              : showForm
                ? 'rgba(90, 158, 114, 0.06)'
                : SP.green,
            border: tracked || showForm
              ? '1px solid rgba(90, 158, 114, 0.4)'
              : 'none',
            borderRadius: '10px',
            fontFamily: SP.fontSans, fontSize: '14px', fontWeight: 600,
            color: tracked || showForm ? SP.green : '#062019',
            letterSpacing: '0.01em',
            cursor: tracking ? 'wait' : 'pointer',
            display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '8px',
            opacity: tracking ? 0.7 : 1,
            minHeight: '44px',
          }}
        >
          {tracked && (
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
              <path d="M5 13l4 4L19 7" />
            </svg>
          )}
          {tracking ? 'Tracking…' : tracked
            ? `Tracking · ${teamName?.split(' ').slice(-1)[0] || ''} ${lineText || ''}${flatLabel ? ` · ${flatLabel}` : ''}`
            : showForm
              ? 'Cancel'
              : `Track this signal${flatLabel ? ` · ${flatLabel}` : ''}`}
        </button>

        {/* Inline track-bet form (kept verbatim from prior layout). Mirrors
            PickCard.jsx:976-1023: line / odds / units / wager with live
            unit<->wager sync, posts to /api/bets so the user stays on the
            home screen instead of routing to BetTrackingScreen. */}
        {showForm && !tracked && (
          <div style={{
            padding: '14px',
            borderRadius: '10px',
            background: SP.bg,
            border: '1px solid rgba(90, 158, 114, 0.15)',
          }}>
            <div style={{
              fontFamily: SP.fontMono, fontSize: '11px', color: SP.text2,
              marginBottom: '12px', lineHeight: 1.4,
            }}>
              {pick?.side} · {pick?.market_odds > 0 ? '+' : ''}{pick?.market_odds || -110}
              {pick?.edge_pct != null ? ` · ${Number(pick.edge_pct).toFixed(1)}% edge` : ''}
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px', marginBottom: '12px' }}>
              <div>
                <div style={{
                  fontFamily: SP.fontMono, fontSize: '10px', fontWeight: 500,
                  color: SP.text3, letterSpacing: '0.1em', textTransform: 'uppercase', marginBottom: '4px',
                }}>Line bought</div>
                <input
                  type="text" inputMode="decimal" value={formLine}
                  onChange={(e) => setFormLine(e.target.value)}
                  style={{
                    background: SP.bg, border: '1px solid rgba(255,255,255,0.08)',
                    borderRadius: '8px', padding: '10px 12px',
                    fontFamily: SP.fontMono, fontSize: '14px', fontWeight: 500,
                    color: SP.text, outline: 'none', width: '100%', boxSizing: 'border-box',
                  }}
                />
              </div>
              <div>
                <div style={{
                  fontFamily: SP.fontMono, fontSize: '10px', fontWeight: 500,
                  color: SP.text3, letterSpacing: '0.1em', textTransform: 'uppercase', marginBottom: '4px',
                }}>Price (odds)</div>
                <input
                  type="text" inputMode="numeric" value={formOdds}
                  onChange={(e) => setFormOdds(e.target.value)}
                  placeholder="-110"
                  style={{
                    background: SP.bg, border: '1px solid rgba(255,255,255,0.08)',
                    borderRadius: '8px', padding: '10px 12px',
                    fontFamily: SP.fontMono, fontSize: '14px', fontWeight: 500,
                    color: SP.text, outline: 'none', width: '100%', boxSizing: 'border-box',
                  }}
                />
              </div>
              <div>
                <div style={{
                  fontFamily: SP.fontMono, fontSize: '10px', fontWeight: 500,
                  color: SP.text3, letterSpacing: '0.1em', textTransform: 'uppercase', marginBottom: '4px',
                }}>Units</div>
                <input
                  type="text" inputMode="decimal" value={formUnits}
                  onChange={(e) => handleUnitsChange(e.target.value)}
                  style={{
                    background: SP.bg, border: '1px solid rgba(255,255,255,0.08)',
                    borderRadius: '8px', padding: '10px 12px',
                    fontFamily: SP.fontMono, fontSize: '14px', fontWeight: 500,
                    color: SP.text, outline: 'none', width: '100%', boxSizing: 'border-box',
                  }}
                />
              </div>
              <div>
                <div style={{
                  fontFamily: SP.fontMono, fontSize: '10px', fontWeight: 500,
                  color: SP.text3, letterSpacing: '0.1em', textTransform: 'uppercase', marginBottom: '4px',
                }}>Wager ($)</div>
                <input
                  type="text" inputMode="numeric" value={formWager}
                  onChange={(e) => handleWagerChange(e.target.value)}
                  style={{
                    background: SP.bg, border: '1px solid rgba(255,255,255,0.08)',
                    borderRadius: '8px', padding: '10px 12px',
                    fontFamily: SP.fontMono, fontSize: '14px', fontWeight: 500,
                    color: SP.green, outline: 'none', width: '100%', boxSizing: 'border-box',
                  }}
                />
              </div>
            </div>
            <button
              onClick={handleSubmit}
              disabled={tracking}
              style={{
                width: '100%', padding: '12px', border: 'none', borderRadius: '8px',
                fontFamily: SP.fontSans, fontSize: '13px', fontWeight: 600,
                color: '#062019', background: SP.green,
                cursor: tracking ? 'default' : 'pointer',
                letterSpacing: '0.02em', opacity: tracking ? 0.5 : 1,
              }}
            >{tracking ? 'Tracking…' : 'Track this bet'}</button>
            {trackError && (
              <div style={{
                marginTop: '8px', fontFamily: SP.fontMono, fontSize: '11px',
                color: SP.redSoft, textAlign: 'center',
              }}>{trackError}</div>
            )}
          </div>
        )}
      </div>

      {/* SHARP JOURNAL INLINE FOOTER (conditional on onOpenJournal) */}
      {onOpenJournal && (
        <a
          onClick={onOpenJournal}
          role="link"
          tabIndex={0}
          onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); onOpenJournal(); } }}
          style={{
            display: 'flex', alignItems: 'center', justifyContent: 'space-between',
            gap: '10px',
            padding: '10px 16px 11px',
            borderTop: `1px solid ${SP.border2}`,
            background: 'rgba(79, 134, 247, 0.04)',
            cursor: 'pointer', textDecoration: 'none',
            minHeight: '44px',
          }}
        >
          <div style={{ flex: 1, minWidth: 0 }}>
            <div style={{
              fontFamily: SP.fontMono, fontSize: '9px', fontWeight: 500,
              letterSpacing: '0.22em', textTransform: 'uppercase', color: SP.blue,
              marginBottom: '2px',
            }}>Today's Sharp Journal</div>
            <div style={{
              fontFamily: SP.fontSerif, fontSize: '13px', fontWeight: 600,
              color: SP.text, lineHeight: 1.3,
            }}>
              {(marketReport?.insight || 'Read today\'s market commentary.').slice(0, 80)}
              {(marketReport?.insight?.length || 0) > 80 ? '…' : ''}
            </div>
          </div>
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke={SP.text3} strokeWidth="2.5" style={{ flexShrink: 0 }}>
            <path d="M9 18l6-6-6-6" />
          </svg>
        </a>
      )}
    </div>
  );
}

function DtsLiveBlock({ liveScore, pick }) {
  const isFinal = isFinalState(liveScore.state);
  const isLive = isInPlayState(liveScore.state);
  const cfg = sportDisplay(pick?.sport);
  const periodDisplay = cfg.periodLabel(liveScore.period);
  const clockDisplay = cfg.showClock ? (liveScore.clock || '') : '';
  const awayShort = teamAbbr(pick?.away_team) || '—';
  const homeShort = teamAbbr(pick?.home_team) || '—';

  return (
    <div style={{ marginTop: '14px' }}>
      <style>{`@keyframes dtsLivePulse{0%,100%{opacity:1}50%{opacity:0.4}}`}</style>
      <div style={{
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        padding: '10px 12px', borderRadius: '8px',
        background: isLive ? 'rgba(90,158,114,0.06)' : 'rgba(255,255,255,0.03)',
        border: isLive ? '1px solid rgba(90,158,114,0.2)' : '1px solid rgba(255,255,255,0.08)',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          {isLive && (
            <span style={{
              width: 6, height: 6, borderRadius: '50%', background: '#5A9E72',
              display: 'inline-block', animation: 'dtsLivePulse 2s ease-in-out infinite',
            }} />
          )}
          <span style={{
            fontFamily: "'JetBrains Mono', monospace",
            fontSize: '11px', fontWeight: 600,
            color: isLive ? '#5A9E72' : 'rgba(232, 234, 237, 0.5)',
            textTransform: 'uppercase', letterSpacing: '0.08em',
          }}>{isLive ? `${periodDisplay}${clockDisplay ? ` · ${clockDisplay}` : ''}` : 'Final'}</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontFamily: "'JetBrains Mono', monospace" }}>
          <span style={{ fontSize: 11, color: 'rgba(232, 234, 237, 0.5)' }}>{awayShort}</span>
          <span style={{ fontSize: 16, fontWeight: 600, color: '#E8EAED' }}>{liveScore.away_score ?? '—'}</span>
          <span style={{ fontSize: 11, color: 'rgba(232, 234, 237, 0.35)', margin: '0 4px' }}>·</span>
          <span style={{ fontSize: 11, color: 'rgba(232, 234, 237, 0.5)' }}>{homeShort}</span>
          <span style={{ fontSize: 16, fontWeight: 600, color: '#E8EAED' }}>{liveScore.home_score ?? '—'}</span>
        </div>
      </div>
      {isLive && pick?.line != null && pick?.side && (
        <DtsCoverTracker pick={pick} liveScore={liveScore} />
      )}
    </div>
  );
}

function DtsCoverTracker({ pick, liveScore }) {
  const spread = parseFloat(pick.line);
  const sideStr = pick.side || '';
  const isHomeSide = isHomeSidePick({ pickSide: pick.pick_side, side: sideStr, homeTeam: pick.home_team });
  const cover = computeLiveCover({
    isHomePick: isHomeSide,
    line: pick.line,
    homeScore: liveScore.home_score || 0,
    awayScore: liveScore.away_score || 0,
  });
  if (!cover) return null;

  const covering = cover.status === 'covering';
  const marginAbs = cover.margin.toFixed(1);
  const statusColor = covering ? '#5A9E72' : '#C4868A';
  const sideTeamName = sideStr.match(/^(.*?)(\s[+-]?\d+)/)?.[1] || sideStr.split(' ').slice(0, -1).join(' ') || sideStr;
  const sideShort = teamAbbr(sideTeamName) || sideStr.split(' ')[0];
  const spreadStr = spread > 0 ? `+${spread}` : `${spread}`;
  const barFill = Math.min(100, Math.max(5, (Math.abs(cover.adjusted) / (Math.abs(spread) + 10)) * 100));

  return (
    <div style={{ marginTop: '8px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '4px' }}>
        <span style={{
          fontFamily: "'JetBrains Mono', monospace", fontSize: '10px',
          color: 'rgba(232, 234, 237, 0.5)', textTransform: 'uppercase', letterSpacing: '0.08em',
        }}>Cover Tracker</span>
        <span style={{
          fontFamily: "'JetBrains Mono', monospace", fontSize: '11px',
          color: statusColor,
        }}>{sideShort} {spreadStr} · {covering ? 'covering' : 'not covering'} by {marginAbs}</span>
      </div>
      <div style={{
        height: 4, background: 'rgba(255, 255, 255, 0.05)',
        borderRadius: 2, position: 'relative', overflow: 'visible',
      }}>
        <div style={{
          height: '100%', borderRadius: 2,
          width: `${barFill}%`, background: statusColor, transition: 'width 0.5s ease',
        }} />
        <div style={{
          position: 'absolute', top: -2, bottom: -2,
          left: '50%', width: '1.5px',
          background: '#E8EAED', borderRadius: 1,
        }} />
      </div>
    </div>
  );
}
