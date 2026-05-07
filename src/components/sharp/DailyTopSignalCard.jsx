import { useState, useEffect } from 'react';
import { apiGet, apiPost, apiDelete } from '../../hooks/useApi';

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

function fmtCountdown(startTime) {
  if (!startTime) return null;
  try {
    const start = new Date(startTime).getTime();
    const now = Date.now();
    const diffMs = start - now;
    if (diffMs <= 0) return null;
    const totalMin = Math.floor(diffMs / 60000);
    const h = Math.floor(totalMin / 60);
    const m = totalMin % 60;
    if (h === 0) return `First pitch in ${m}m`;
    return `First pitch in ${h}h ${String(m).padStart(2, '0')}m`;
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

export default function DailyTopSignalCard({ pick, isPro, onTrack, onNavigate, marketReport }) {
  const [tracking, setTracking] = useState(false);
  const [tracked, setTracked] = useState(false);
  const [trackedBetId, setTrackedBetId] = useState(null);
  const [reasoningOpen, setReasoningOpen] = useState(false);

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
  const countdown = fmtCountdown(pick?.start_time);

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

  const handleTrack = async () => {
    if (tracking || tracked || !isPro) return;
    setTracking(true);
    try {
      const res = await apiPost('/bets', {
        pick_id: pick.id,
        bet_amount: Math.round((flatStake || 1) * 100),
        units_wagered: flatStake || 1,
      });
      if (res?.bet?.id) {
        setTracked(true);
        setTrackedBetId(res.bet.id);
        if (typeof onTrack === 'function') onTrack();
      }
    } catch { /* swallow; user retains untracked state */ }
    setTracking(false);
  };

  const handleUntrack = async () => {
    if (!trackedBetId) return;
    try {
      await apiDelete(`/bets/${trackedBetId}`);
      setTracked(false);
      setTrackedBetId(null);
    } catch { /* swallow */ }
  };

  if (!isPro) return null;

  return (
    <div style={{
      background: SP.surface,
      border: `1px solid ${SP.border}`,
      borderRadius: '16px',
      overflow: 'hidden',
      position: 'relative',
      marginBottom: '18px',
    }}>
      <div aria-hidden style={{
        position: 'absolute', top: 0, left: 0, right: 0, height: 2,
        background: `linear-gradient(90deg, transparent, ${SP.green} 20%, ${SP.green} 80%, transparent)`,
        opacity: 0.7,
      }} />

      <div style={{ padding: '22px 22px 0' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px', flexWrap: 'wrap', marginBottom: '16px' }}>
          <span style={{
            display: 'inline-flex', alignItems: 'center',
            padding: '4px 10px', border: `1px solid ${SP.border}`, borderRadius: '4px',
            fontFamily: SP.fontMono, fontSize: '10px', fontWeight: 500,
            letterSpacing: '0.18em', textTransform: 'uppercase', color: SP.text2,
            background: SP.surface2,
          }}>{sportLabel}</span>
          {isCalibration && (
            <span style={{
              display: 'inline-flex', alignItems: 'center', gap: '6px',
              padding: '4px 10px', border: `1px solid ${SP.amber}`, borderRadius: '4px',
              fontFamily: SP.fontMono, fontSize: '10px', fontWeight: 500,
              letterSpacing: '0.16em', textTransform: 'uppercase', color: SP.amber,
            }}>
              <span style={{ width: 5, height: 5, borderRadius: '50%', background: SP.amber }} />
              Calibration v1
            </span>
          )}
          {matchup && (
            <span style={{
              flexBasis: '100%', marginTop: '6px',
              fontFamily: SP.fontMono, fontSize: '11px',
              color: SP.text3, letterSpacing: '0.04em',
            }}>{matchup}</span>
          )}
        </div>

        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', gap: '12px', marginBottom: '8px' }}>
          <span style={{
            fontFamily: SP.fontSerif, fontSize: '24px', fontWeight: 600,
            color: SP.text, lineHeight: 1.15, letterSpacing: '-0.01em',
          }}>
            {teamName}
            {lineText && <span style={{ color: SP.green, marginLeft: '6px' }}>{lineText}</span>}
          </span>
          <span style={{
            fontFamily: SP.fontMono, fontSize: '22px', fontWeight: 500,
            color: SP.green, whiteSpace: 'nowrap',
          }}>{edgeText}</span>
        </div>

        {(startInfo || oddsText) && (
          <div style={{
            fontFamily: SP.fontMono, fontSize: '11px', color: SP.text3, marginTop: '8px',
          }}>
            {startInfo?.date && <>{startInfo.date} <span style={{ color: SP.text5 }}>·</span> </>}
            {startInfo?.time && <span style={{ color: SP.text2 }}>{startInfo.time}</span>}
            {oddsText && <> <span style={{ color: SP.text5 }}>·</span> <span style={{ color: SP.text2 }}>{oddsText}</span></>}
          </div>
        )}

        {countdown && (
          <div style={{
            display: 'inline-flex', alignItems: 'center', gap: '8px',
            padding: '6px 11px', marginTop: '10px',
            background: SP.amberSoft,
            border: '1px solid rgba(245, 158, 11, 0.25)',
            borderRadius: '6px',
            fontFamily: SP.fontMono, fontSize: '11px',
            color: SP.amber, letterSpacing: '0.04em',
          }}>
            <span style={{
              width: '6px', height: '6px', borderRadius: '50%', background: SP.amber,
              animation: 'spDtsPulse 2s infinite',
            }} />
            <style>{`
              @keyframes spDtsPulse {
                0%   { box-shadow: 0 0 0 0 rgba(245, 158, 11, 0.5); }
                70%  { box-shadow: 0 0 0 6px rgba(245, 158, 11, 0); }
                100% { box-shadow: 0 0 0 0 rgba(245, 158, 11, 0); }
              }
              @media (prefers-reduced-motion: reduce) {
                [data-sp-pulse] { animation: none !important; }
              }
            `}</style>
            {countdown}
          </div>
        )}
      </div>

      <div style={{
        margin: '22px',
        display: 'grid', gridTemplateColumns: '1fr 1px 1fr 1px 1fr 1px 1fr',
        background: SP.bg, border: `1px solid ${SP.border}`,
        borderRadius: '10px', overflow: 'hidden',
      }}>
        {[
          { label: 'Market', value: marketLine, tone: 'plain' },
          { label: 'Model', value: modelLine, tone: 'green' },
          { label: 'Tier', value: tier, tone: 'serif' },
          { label: 'Size', value: sizeUnits || '—', tone: 'plain' },
        ].flatMap((cell, i, arr) => [
          <div key={`c-${cell.label}`} style={{ padding: '14px 8px', textAlign: 'center' }}>
            <div style={{
              fontFamily: SP.fontMono, fontSize: '9px',
              letterSpacing: '0.22em', textTransform: 'uppercase', color: SP.text3,
              marginBottom: '6px',
            }}>{cell.label}</div>
            <div style={{
              fontFamily: cell.tone === 'serif' ? SP.fontSerif : SP.fontMono,
              fontSize: cell.tone === 'serif' ? '18px' : '16px',
              fontWeight: cell.tone === 'serif' ? 600 : 500,
              color: cell.tone === 'green' ? SP.green : SP.text,
              lineHeight: 1,
            }}>{cell.value}</div>
          </div>,
          i < arr.length - 1 ? <div key={`d-${i}`} style={{ background: SP.border }} /> : null,
        ])}
      </div>

      {observationText && (
        <div style={{
          margin: '0 22px 22px',
          padding: '18px',
          background: SP.bg,
          borderLeft: `2px solid ${SP.green}`,
          borderRadius: '0 8px 8px 0',
        }}>
          <div style={{
            fontFamily: SP.fontMono, fontSize: '10px', fontWeight: 500,
            letterSpacing: '0.22em', textTransform: 'uppercase', color: SP.green,
            marginBottom: '8px',
          }}>Observation</div>
          <div style={{
            fontFamily: SP.fontSerif, fontSize: '15px',
            lineHeight: 1.55, color: SP.text,
          }}>{observationText}</div>
        </div>
      )}

      {pick?.edge_pct != null && (
        <div style={{ margin: '0 22px 18px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
            <span style={{
              fontFamily: SP.fontMono, fontSize: '10px',
              letterSpacing: '0.22em', textTransform: 'uppercase', color: SP.text3,
            }}>Edge</span>
            <span style={{
              fontFamily: SP.fontMono, fontSize: '14px',
              color: edgePct >= 0 ? SP.green : SP.redSoft, fontWeight: 500,
            }}>{edgePct >= 0 ? '+' : ''}{edgePct.toFixed(1)}pp</span>
          </div>
          <div style={{
            position: 'relative', height: '8px', background: SP.surface2,
            borderRadius: '2px', overflow: 'hidden',
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
            display: 'flex', justifyContent: 'space-between', marginTop: '6px',
            fontFamily: SP.fontMono, fontSize: '9px', color: SP.text4, letterSpacing: '0.04em',
          }}>
            <span>-10pp</span><span>0</span><span>+10pp</span>
          </div>
        </div>
      )}

      {isCalibration && (
        <div style={{
          margin: '0 22px 18px', padding: '12px 14px',
          background: 'rgba(245, 158, 11, 0.05)',
          border: '1px solid rgba(245, 158, 11, 0.18)',
          borderRadius: '8px',
          display: 'flex', alignItems: 'flex-start', gap: '10px',
        }}>
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none"
               stroke={SP.amber} strokeWidth="2" style={{ flexShrink: 0, marginTop: '1px' }}>
            <circle cx="12" cy="12" r="10" />
            <path d="M12 8v4M12 16h.01" />
          </svg>
          <div style={{ fontSize: '12px', lineHeight: 1.45, color: SP.text2 }}>
            <strong style={{ color: SP.amber, fontWeight: 500 }}>Calibration phase.</strong>
            {' '}Confidence intervals widen during early-season validation. Closing line audit publishes on every signal.
          </div>
        </div>
      )}

      {hasPlayability && (
        <div style={{ margin: '0 22px 18px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', marginBottom: '8px' }}>
            <span style={{
              fontFamily: SP.fontMono, fontSize: '10px',
              letterSpacing: '0.22em', textTransform: 'uppercase', color: SP.text3,
            }}>Playability</span>
            <span style={{ fontFamily: SP.fontMono, fontSize: '11px', color: SP.text3, letterSpacing: '0.04em' }}>
              <span style={{ color: SP.green }}>{fmtSpread(playTarget)} target</span>
              {' · '}
              <span style={{ color: SP.text2 }}>{fmtSpread(playFloor)} floor</span>
            </span>
          </div>
          <div style={{
            position: 'relative', height: '6px', background: SP.surface2,
            borderRadius: '2px', overflow: 'hidden',
          }}>
            <div style={{
              position: 'absolute', height: '100%',
              width: '100%',
              background: `linear-gradient(90deg, ${SP.green}, rgba(90, 158, 114, 0.3))`,
              borderRadius: '2px',
            }} />
          </div>
        </div>
      )}

      {(flatLabel || kellyLabel) && (
        <div style={{
          margin: '0 22px 18px',
          padding: '14px 16px',
          background: SP.bg, border: `1px solid ${SP.border}`,
          borderRadius: '10px',
          display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        }}>
          <div style={{ display: 'flex', gap: '22px' }}>
            {flatLabel && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>
                <span style={{
                  fontFamily: SP.fontMono, fontSize: '9px',
                  letterSpacing: '0.22em', textTransform: 'uppercase', color: SP.text4,
                }}>Flat</span>
                <span style={{ fontFamily: SP.fontMono, fontSize: '14px', color: SP.text, fontWeight: 500 }}>
                  {flatLabel}
                </span>
              </div>
            )}
            {kellyLabel && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>
                <span style={{
                  fontFamily: SP.fontMono, fontSize: '9px',
                  letterSpacing: '0.22em', textTransform: 'uppercase', color: SP.text4,
                }}>Kelly</span>
                <span style={{ fontFamily: SP.fontMono, fontSize: '14px', color: SP.text, fontWeight: 500 }}>
                  {kellyLabel}
                </span>
              </div>
            )}
          </div>
        </div>
      )}

      {contextText && (
        <div style={{
          margin: '0 22px 22px',
          padding: '16px 18px',
          background: SP.bg, border: `1px solid ${SP.border}`,
          borderRadius: '10px',
        }}>
          <div style={{
            fontFamily: SP.fontMono, fontSize: '10px', fontWeight: 500,
            letterSpacing: '0.22em', textTransform: 'uppercase', color: SP.text3,
            marginBottom: '8px',
          }}>Market Context</div>
          <div style={{ fontSize: '13px', lineHeight: 1.5, color: SP.text2 }}>
            {contextText.lead}{' '}
            <span style={{ color: SP.text, fontFamily: SP.fontMono, fontSize: '12px' }}>
              {contextText.detail.match(/\d+ of \d+/)?.[0]}
            </span>
            {' '}{contextText.detail.replace(/\d+ of \d+/, '').trim()}
          </div>
        </div>
      )}

      {reasoningSignals.length > 0 && (
        <div style={{
          margin: '0 22px 22px',
          border: `1px solid ${SP.border}`, borderRadius: '10px', overflow: 'hidden',
        }}>
          <div
            onClick={() => setReasoningOpen((v) => !v)}
            role="button" tabIndex={0} aria-expanded={reasoningOpen}
            style={{
              padding: '14px 18px',
              display: 'flex', justifyContent: 'space-between', alignItems: 'center',
              cursor: 'pointer',
            }}
          >
            <span style={{
              fontFamily: SP.fontMono, fontSize: '10px', fontWeight: 500,
              letterSpacing: '0.22em', textTransform: 'uppercase', color: SP.text3,
            }}>Signal Reasoning</span>
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none"
                 stroke={SP.text4} strokeWidth="2"
                 style={{ transform: reasoningOpen ? 'rotate(180deg)' : 'none', transition: 'transform 0.2s' }}>
              <path d="M6 9l6 6 6-6" />
            </svg>
          </div>
          {reasoningOpen && (
            <div style={{ padding: '0 18px 16px', borderTop: `1px solid ${SP.border2}` }}>
              <ul style={{ margin: '14px 0 0', padding: 0, listStyle: 'none' }}>
                {reasoningSignals.map((s, i) => (
                  <li key={i} style={{
                    fontSize: '13px', lineHeight: 1.55, color: SP.text2,
                    paddingLeft: '14px', position: 'relative', marginBottom: '8px',
                  }}>
                    <span aria-hidden style={{
                      position: 'absolute', left: 0, top: '8px',
                      width: '4px', height: '4px', borderRadius: '50%', background: SP.green,
                    }} />
                    {s}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}

      <div style={{
        margin: '0 22px 22px', textAlign: 'center',
        fontFamily: SP.fontMono, fontSize: '11px',
        letterSpacing: '0.16em', textTransform: 'uppercase', color: SP.text3,
      }}>
        <span style={{ color: SP.text }}>{postedLabel}</span>
        {bestBook && <>
          <span style={{ color: SP.text5, margin: '0 8px' }}>·</span>
          <span>Best at <span style={{ color: SP.text }}>{bestBook}</span></span>
        </>}
      </div>

      <div style={{ padding: '0 22px 22px', display: 'flex', flexDirection: 'column', gap: '10px' }}>
        <button
          onClick={tracked ? handleUntrack : handleTrack}
          disabled={tracking}
          style={{
            width: '100%', padding: '14px 16px',
            background: tracked ? 'rgba(90, 158, 114, 0.1)' : SP.green,
            border: tracked ? '1px solid rgba(90, 158, 114, 0.4)' : 'none',
            borderRadius: '10px',
            fontFamily: SP.fontSans, fontSize: '14px', fontWeight: 600,
            color: tracked ? SP.green : '#062019',
            letterSpacing: '0.01em',
            cursor: tracking ? 'wait' : 'pointer',
            display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '8px',
            opacity: tracking ? 0.7 : 1,
          }}
        >
          {tracked && (
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
              <path d="M5 13l4 4L19 7" />
            </svg>
          )}
          {tracking ? 'Tracking…' : tracked
            ? `Tracking · ${teamName?.split(' ').slice(-1)[0] || ''} ${lineText || ''}${flatLabel ? ` · ${flatLabel}` : ''}`
            : `Track this signal${flatLabel ? ` · ${flatLabel}` : ''}`}
        </button>
      </div>
    </div>
  );
}
