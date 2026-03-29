import { useState, useEffect } from 'react';
import { Capacitor } from '@capacitor/core';
import { apiPost, apiDelete, getAuthToken } from '../../hooks/useApi';
import { trackEvent } from '../../utils/eventTracker';
import teamAbbr from '../../utils/teamAbbr';
import sportDisplay from '../../utils/sportDisplay';

const green = '#5A9E72';
const greenDim = '#5A9E72';
const blue = '#4A8EC2';
const borderColor = 'rgba(90, 158, 114, 0.12)';
const bgCard = '#0f1d33';
const bgInner = '#131f36';
const textSec = '#9EAAB8';
const textDim = '#7A8494';
const textLabel = '#8899AA';


function fmtGameTime(startTime, gameDate) {
  if (startTime && startTime.includes('T')) {
    try {
      const d = new Date(startTime);
      if (!isNaN(d.getTime())) {
        const et = new Date(d.toLocaleString('en-US', { timeZone: 'America/New_York' }));
        let hours = et.getHours();
        const mins = et.getMinutes().toString().padStart(2, '0');
        const ampm = hours >= 12 ? 'PM' : 'AM';
        hours = hours % 12 || 12;
        const months = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
        return `${months[et.getMonth()]} ${et.getDate()} · ${hours}:${mins} ${ampm} ET`;
      }
    } catch {}
  }
  if (gameDate && typeof gameDate === 'string' && gameDate.match(/^\d{4}-\d{2}-\d{2}/)) {
    const [, m, day] = gameDate.split('-');
    const months = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
    return `${months[parseInt(m)-1]} ${parseInt(day)}`;
  }
  return null;
}

function fmtSpread(val) {
  if (val == null) return '--';
  const n = parseFloat(val);
  if (Number.isInteger(n)) return n > 0 ? `+${n}` : `${n}`;
  return n > 0 ? `+${n.toFixed(1)}` : `${n.toFixed(1)}`;
}

function fmtEdge(val) {
  if (val == null) return '--';
  const n = parseFloat(val);
  return `+${n.toFixed(1)}%`;
}

function getEdgeTier(edgePct) {
  if (edgePct == null) return { label: '--', color: textDim };
  const e = parseFloat(edgePct);
  if (e >= 10) return { label: 'STR', color: green };
  if (e >= 7) return { label: 'MOD', color: blue };
  return { label: 'WK', color: textDim };
}

const mono = "'JetBrains Mono', var(--font-mono), monospace";
const serif = "'IBM Plex Serif', var(--font-serif), serif";
const sans = "'Inter', var(--font-sans), sans-serif";

const labelStyle = {
  fontFamily: mono, fontSize: '10px', fontWeight: 500,
  letterSpacing: '0.8px', textTransform: 'uppercase',
  color: textLabel,
};

export default function PickCard({ pick, isPro, liveScore, onUpgrade, onTrack, onNavigate }) {
  const isLocked = pick.locked && !isPro;
  const [tracking, setTracking] = useState(false);
  const [tracked, setTracked] = useState(pick.already_tracked || false);
  const [trackedBetId, setTrackedBetId] = useState(pick.tracked_bet_id || null);
  const [trackError, setTrackError] = useState(null);
  const [signalsOpen, setSignalsOpen] = useState(false);
  const settled = pick.result && pick.result !== 'pending' && pick.result !== 'revoked';
  const isRevoked = pick.result === 'revoked';
  const [expanded, setExpanded] = useState(false);

  const handleTrackPick = async () => {
    setTracking(true);
    setTrackError(null);
    trackEvent('tap_bet_link', { game_id: pick.id, pick_type: 'spread', sportsbook: pick.sportsbook || 'unknown' });
    try {
      const res = await apiPost('/bets', {
        pick_id: pick.id, bet_amount: 100, odds: pick.market_odds || -110,
      });
      if (res.success) {
        setTracked(true);
        if (res.bet?.id) setTrackedBetId(res.bet.id);
      } else {
        if (res.error?.includes('Already tracking')) setTracked(true);
        else setTrackError(res.error || 'Failed to track');
      }
    } catch (e) {
      if (e?.message?.includes('Already tracking')) setTracked(true);
      else setTrackError('Failed to track');
    } finally { setTracking(false); }
  };

  const handleUntrack = async () => {
    if (!trackedBetId) return;
    setTracking(true);
    try {
      await apiDelete(`/bets/${trackedBetId}`);
      setTracked(false);
      setTrackedBetId(null);
    } catch { setTrackError('Failed to untrack'); }
    finally { setTracking(false); }
  };

  const handleShare = async () => {
    const apiRoot = Capacitor.isNativePlatform() ? 'https://app.sharppicks.ai' : '';
    const cardUrl = `${apiRoot}/api/cards/result/${pick.id}`;
    const filename = `sharppicks-result-${pick.id}.png`;
    try {
      const token = getAuthToken();
      const headers = {};
      if (token) headers['Authorization'] = `Bearer ${token}`;
      const res = await fetch(cardUrl, { headers, credentials: 'include' });
      if (!res.ok) return;
      const blob = await res.blob();

      if (Capacitor.isNativePlatform()) {
        const { Filesystem, Directory } = await import('@capacitor/filesystem');
        const { Share } = await import('@capacitor/share');
        const reader = new FileReader();
        const base64 = await new Promise((resolve, reject) => {
          reader.onloadend = () => resolve(reader.result.split(',')[1]);
          reader.onerror = reject;
          reader.readAsDataURL(blob);
        });
        const file = await Filesystem.writeFile({ path: filename, data: base64, directory: Directory.Cache });
        await Share.share({ title: 'Sharp Picks Result', text: 'sharppicks.ai', url: file.uri });
        try { await Filesystem.deleteFile({ path: filename, directory: Directory.Cache }); } catch {}
      } else {
        const file = new File([blob], filename, { type: 'image/png' });
        if (navigator.share && navigator.canShare?.({ files: [file] })) {
          await navigator.share({ files: [file], text: 'Sharp Picks result' });
        } else {
          const url = URL.createObjectURL(blob);
          const a = document.createElement('a');
          a.href = url; a.download = filename; a.click();
          URL.revokeObjectURL(url);
        }
      }
    } catch {}
  };

  if (isLocked) {
    return (
      <div style={{
        background: bgCard, border: `1px solid ${borderColor}`,
        borderRadius: '8px', padding: '14px 16px', position: 'relative',
      }}>
        <div style={{
          position: 'absolute', top: 0, left: 0, right: 0, height: '2px',
          background: `linear-gradient(90deg, ${green}, transparent)`,
          borderRadius: '8px 8px 0 0',
        }} />
        <div style={{
          fontFamily: mono, fontSize: '9px', letterSpacing: '1px',
          color: textDim, textTransform: 'uppercase', marginBottom: '8px',
        }}>
          {(pick.sport || 'nba').toUpperCase()} — {pick.away_team} vs {pick.home_team}
        </div>
        <div style={{
          fontFamily: mono, fontSize: '10px', color: textDim, marginBottom: '12px',
        }}>
          {fmtGameTime(pick.start_time, pick.game_date) && `${sportDisplay(pick.sport).tipLabel} ${fmtGameTime(pick.start_time, pick.game_date)}`}
        </div>
        <div style={{
          background: 'rgba(255,255,255,0.02)', border: '1px dashed rgba(255,255,255,0.08)',
          borderRadius: '6px', padding: '28px 20px', textAlign: 'center', marginBottom: '12px',
        }}>
          <div style={{ fontSize: '20px', marginBottom: '10px', opacity: 0.6 }}>🔒</div>
          <p style={{ fontSize: '12px', color: textSec, lineHeight: '1.5', marginBottom: '14px' }}>
            Side and line locked for Pro members. Upgrade to see the full signal and track outcomes.
          </p>
          <button onClick={onUpgrade} style={{
            width: '100%', height: '44px', borderRadius: '8px', border: 'none',
            background: 'linear-gradient(135deg, var(--blue-primary, #4F86F7), var(--blue-deep, #3B6FE0))',
            color: 'white', fontFamily: sans, fontSize: '13px', fontWeight: 700, cursor: 'pointer',
          }}>
            Upgrade Now
          </button>
        </div>
      </div>
    );
  }

  const sideStr = pick.side || '';
  const spreadMatch = sideStr.match(/^(.*?)(\s[+-]\d+(\.\d+)?)$/);
  const teamPart = spreadMatch ? spreadMatch[1] : sideStr;
  const spreadPart = spreadMatch ? spreadMatch[2].trim() : '';
  const gameFmt = fmtGameTime(pick.start_time, pick.game_date);
  const tier = getEdgeTier(pick.edge_pct);
  const edgeNum = pick.edge_pct != null ? parseFloat(pick.edge_pct) : null;
  const edgeBarWidth = edgeNum != null ? Math.min(100, (edgeNum / 15) * 100) : 0;
  const marketLine = pick.market_line != null ? pick.market_line : pick.line;
  const flatStake = pick.stake_guidance?.flat_stake;
  const kellyStake = pick.stake_guidance?.kelly_stake;

  return (
    <div>
      <div style={{
        background: bgCard,
        border: `1px solid ${borderColor}`,
        borderRadius: '8px',
        padding: '14px 16px',
        position: 'relative',
        opacity: settled ? 0.85 : 1,
      }}>
        {/* Top gradient accent */}
        <div style={{
          position: 'absolute', top: 0, left: 0, right: 0, height: '2px',
          background: `linear-gradient(90deg, ${green}, transparent)`,
          borderRadius: '8px 8px 0 0',
        }} />

        {/* Matchup line */}
        <div style={{
          fontFamily: mono, fontSize: '9px', letterSpacing: '1px',
          color: textDim, textTransform: 'uppercase', marginBottom: '8px',
          display: 'flex', alignItems: 'center', gap: '6px',
        }}>
          <span>{(pick.sport || 'nba').toUpperCase()}</span>
          {pick.phase_label && (
            <span style={{
              fontSize: '8px', fontWeight: 700,
              padding: '1px 4px', borderRadius: '3px',
              backgroundColor: 'rgba(59,130,246,0.15)',
              color: '#3B82F6',
              letterSpacing: '0.04em',
            }}>{pick.phase_label.toUpperCase()}</span>
          )}
          <span>— {pick.away_team} vs {pick.home_team}</span>
        </div>

        {liveScore && (
          <LiveBarBlock liveScore={liveScore} pick={pick} />
        )}

        {/* Pick row: team + spread + edge */}
        <div style={{
          display: 'flex', alignItems: 'baseline',
          justifyContent: 'space-between', marginBottom: '4px',
        }}>
          <div>
            <span style={{
              fontFamily: serif, fontSize: '16px', fontWeight: 600,
              color: 'var(--text-primary, #e2e8f0)',
            }}>{teamPart}</span>
            {spreadPart && (
              <span style={{
                fontFamily: mono, fontSize: '16px', fontWeight: 600,
                color: green, marginLeft: '6px',
              }}>{spreadPart}</span>
            )}
          </div>
          <span style={{
            fontFamily: mono, fontSize: '13px', fontWeight: 700,
            color: green,
          }}>{fmtEdge(pick.edge_pct)}</span>
        </div>

        {/* Time + price + countdown */}
        <div style={{
          fontFamily: mono, fontSize: '10px', color: textDim, marginBottom: '12px',
          display: 'flex', alignItems: 'center', gap: 6, flexWrap: 'wrap',
        }}>
          <span>{gameFmt}{pick.market_odds != null ? ` · ${pick.market_odds}` : ''}</span>
          {!settled && !isRevoked && !liveScore && pick.start_time && (
            <CountdownPill startTime={pick.start_time} sport={pick.sport} />
          )}
        </div>

        {/* Settled banner */}
        {settled && (
          <div style={{
            padding: '8px 10px', borderRadius: '5px', textAlign: 'center',
            marginBottom: '12px',
            border: `1px solid ${pick.result === 'win' ? 'rgba(90,158,114,0.25)' : pick.result === 'push' ? borderColor : 'rgba(196,104,107,0.22)'}`,
            background: pick.result === 'win' ? 'rgba(90,158,114,0.08)' : pick.result === 'push' ? 'rgba(255,255,255,0.03)' : 'rgba(196,104,107,0.08)',
          }}>
            <span style={{
              fontFamily: mono, fontSize: '13px', fontWeight: 600,
              color: pick.result === 'win' ? green : pick.result === 'push' ? textSec : '#C4686B',
            }}>
              {pick.result === 'win' ? `Win ${pick.pnl != null ? `+${pick.pnl}u` : ''}` : pick.result === 'push' ? 'Push · 0.0u' : `Loss ${pick.pnl != null ? `${pick.pnl}u` : ''}`}
            </span>
          </div>
        )}

        {/* Revoked banner */}
        {isRevoked && (
          <div style={{
            padding: '8px 10px', borderRadius: '5px', marginBottom: '12px',
            border: '1px solid rgba(251,191,36,0.2)', background: 'rgba(251,191,36,0.04)',
          }}>
            <div style={{
              fontFamily: mono, fontSize: '10px', fontWeight: 600,
              color: '#f59e0b', textTransform: 'uppercase', letterSpacing: '0.5px',
              marginBottom: '3px',
            }}>Signal Withdrawn</div>
            <div style={{ fontFamily: sans, fontSize: '11px', color: textSec }}>
              {pick.withdraw_reason || 'Edge shifted before tip-off.'}
            </div>
          </div>
        )}

        {/* 4-column stat grid */}
        {!isRevoked && (
          <div style={{
            display: 'grid', gridTemplateColumns: '1fr 1fr 1fr 1fr',
            gap: '8px', marginBottom: '12px',
          }}>
            <StatCell label="Market" value={fmtSpread(marketLine)} />
            <StatCell label="Model" value={pick.model_projection != null ? fmtSpread(pick.model_projection) : '--'} valueColor={green} />
            <StatCell label="Tier" value={tier.label} valueColor={tier.color} />
            <StatCell label="Size" value={flatStake != null ? `${flatStake}u` : '--'} />
          </div>
        )}

        {/* Signal Reasoning */}
        {!isRevoked && (pick.signal_reasoning || (pick.model_signals && pick.model_signals.length > 0)) && (
          <div style={{
            background: bgInner, border: `1px solid ${borderColor}`,
            borderRadius: '5px', padding: '8px 10px', marginBottom: '12px',
          }}>
            <div style={{
              fontFamily: mono, fontSize: '10px', fontWeight: 500,
              letterSpacing: '0.8px', color: greenDim, textTransform: 'uppercase',
              marginBottom: '3px',
            }}>Why this signal</div>
            <div style={{
              fontFamily: sans, fontSize: '11px', color: textSec,
              lineHeight: 1.45,
              overflow: 'hidden',
              display: '-webkit-box',
              WebkitLineClamp: 2,
              WebkitBoxOrient: 'vertical',
            }}>
              {pick.signal_reasoning || pick.model_signals?.[0] || ''}
            </div>
          </div>
        )}

        {/* Edge strength bar (compact) */}
        {!isRevoked && edgeNum != null && (
          <div style={{
            display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '12px',
          }}>
            <span style={{
              fontFamily: mono, fontSize: '10px', letterSpacing: '0.8px',
              color: textLabel, textTransform: 'uppercase', whiteSpace: 'nowrap',
            }}>Edge</span>
            <div style={{
              flex: 1, height: '4px', background: 'rgba(255,255,255,0.04)',
              borderRadius: '2px', overflow: 'hidden',
            }}>
              <div style={{
                height: '100%', borderRadius: '2px',
                width: `${edgeBarWidth}%`,
                background: `linear-gradient(90deg, ${green}, rgba(90,158,114,0.4))`,
              }} />
            </div>
            <span style={{
              fontFamily: mono, fontSize: '11px', fontWeight: 600,
              color: green, whiteSpace: 'nowrap',
            }}>+{edgeNum.toFixed(1)}pp</span>
          </div>
        )}

        {/* Calibration phase context */}
        {pick.model_phase === 'calibration' && !settled && !isRevoked && (
          <div style={{
            fontFamily: mono, fontSize: '10px',
            color: '#3B82F6', opacity: 0.7,
            marginBottom: '12px',
            letterSpacing: '0.04em',
          }}>Early-stage signal. Full transparency.</div>
        )}

        {/* Value range (compact inline) */}
        {!isRevoked && !settled && pick.line != null && pick.playable_to != null && Math.abs(pick.playable_to - pick.line) >= 0.5 && (
          <>
            <div style={{
              display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px',
            }}>
              <span style={{
                fontFamily: mono, fontSize: '10px', letterSpacing: '0.8px',
                color: textLabel, textTransform: 'uppercase', whiteSpace: 'nowrap',
              }}>Value</span>
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px', flex: 1 }}>
                <span style={{
                  fontFamily: mono, fontSize: '11px', fontWeight: 500, color: textSec,
                }}>{fmtSpread(pick.line)}</span>
                <div style={{
                  flex: 1, height: '3px', background: 'rgba(90,158,114,0.3)',
                  borderRadius: '2px',
                }} />
                <span style={{
                  fontFamily: mono, fontSize: '11px', fontWeight: 500, color: textSec,
                }}>{fmtSpread(pick.playable_to)}</span>
              </div>
            </div>
            <div style={{
              fontFamily: sans, fontSize: '10px', color: textDim, marginBottom: '12px',
            }}>
              Playable down to {fmtSpread(pick.playable_to)}
            </div>
          </>
        )}

        {/* Footer: position sizing + DETAILS CTA */}
        <div style={{
          display: 'flex', alignItems: 'center', justifyContent: 'space-between',
          paddingTop: '10px',
          borderTop: '1px solid rgba(255,255,255,0.04)',
        }}>
          <div style={{ display: 'flex', gap: '12px' }}>
            {flatStake != null && (
              <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                <span style={{
                  fontFamily: mono, fontSize: '10px', letterSpacing: '0.5px',
                  color: textDim, textTransform: 'uppercase',
                }}>Flat</span>
                <span style={{
                  fontFamily: mono, fontSize: '12px', fontWeight: 600,
                  color: 'var(--text-primary, #e2e8f0)',
                }}>{flatStake}u</span>
              </div>
            )}
            {kellyStake != null && (
              <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                <span style={{
                  fontFamily: mono, fontSize: '10px', letterSpacing: '0.5px',
                  color: textDim, textTransform: 'uppercase',
                }}>Kelly</span>
                <span style={{
                  fontFamily: mono, fontSize: '12px', fontWeight: 600,
                  color: 'var(--text-primary, #e2e8f0)',
                }}>{kellyStake}u</span>
              </div>
            )}
          </div>
          <button
            onClick={() => {
              const next = !expanded;
              setExpanded(next);
              if (next) trackEvent('view_pick', { game_id: pick.id, pick_type: 'spread', edge: pick.edge_pct });
            }}
            style={{
              fontFamily: mono, fontSize: '10px', fontWeight: 500,
              letterSpacing: '0.8px', color: green, textTransform: 'uppercase',
              cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '4px',
              background: 'none', border: 'none', padding: 0,
            }}
          >
            {expanded ? 'Less' : 'Details'}
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke={green} strokeWidth="2"
              style={{ transform: expanded ? 'rotate(180deg)' : 'none', transition: 'transform 0.2s' }}
            >
              <polyline points="9 18 15 12 9 6" />
            </svg>
          </button>
        </div>

        {/* ═══ EXPANDED DETAIL ═══ */}
        {expanded && (
          <div style={{ marginTop: '12px', paddingTop: '12px', borderTop: '1px solid rgba(255,255,255,0.04)' }}>
            {/* Model vs Market */}
            <div style={{
              background: bgInner, border: `1px solid ${borderColor}`,
              borderRadius: '5px', padding: '10px 12px', marginBottom: '10px',
            }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
                <span style={{ ...labelStyle, marginBottom: 0 }}>Market Line</span>
                <span style={{ fontFamily: mono, fontSize: '14px', fontWeight: 600, color: 'var(--text-primary, #e2e8f0)' }}>
                  {fmtSpread(marketLine)}
                </span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span style={{ ...labelStyle, marginBottom: 0 }}>Model Line</span>
                <span style={{ fontFamily: mono, fontSize: '14px', fontWeight: 600, color: green }}>
                  {pick.model_projection != null ? fmtSpread(pick.model_projection) : '--'}
                </span>
              </div>
            </div>

            {/* Price / Tipoff */}
            <div style={{
              background: bgInner, border: `1px solid ${borderColor}`,
              borderRadius: '5px', padding: '10px 12px', marginBottom: '10px',
            }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
                <span style={{ ...labelStyle, marginBottom: 0 }}>Price</span>
                <span style={{ fontFamily: mono, fontSize: '14px', fontWeight: 600, color: 'var(--text-primary, #e2e8f0)' }}>
                  {pick.market_odds != null ? pick.market_odds : '-110'}
                </span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span style={{ ...labelStyle, marginBottom: 0 }}>{sportDisplay(pick.sport).tipoffLabel}</span>
                <span style={{ fontFamily: mono, fontSize: '14px', fontWeight: 600, color: textSec }}>
                  {gameFmt || '--'}
                </span>
              </div>
            </div>

            {/* Market Context */}
            {pick.market_context && (
              <div style={{
                background: bgInner, border: `1px solid ${borderColor}`,
                borderRadius: '5px', padding: '8px 10px', marginBottom: '10px',
              }}>
                <div style={{
                  ...labelStyle, marginBottom: '3px',
                }}>Market Context</div>
                <div style={{
                  fontFamily: sans, fontSize: '11px', color: textSec, lineHeight: 1.4,
                }}>{pick.market_context}</div>
              </div>
            )}

            {/* Edge Tracker / CLV (post-game) */}
            {pick.line != null && settled && (
              <EdgeTrackerDetail
                signalLine={pick.line}
                currentLine={pick.closing_spread ?? pick.line}
                clv={pick.clv}
              />
            )}

            {/* Full Signal Reasoning list */}
            {pick.model_signals && pick.model_signals.length > 0 && (
              <div style={{
                background: bgInner, border: `1px solid ${borderColor}`,
                borderRadius: '5px', overflow: 'hidden', marginBottom: '10px',
              }}>
                <button
                  onClick={() => setSignalsOpen(!signalsOpen)}
                  style={{
                    width: '100%', padding: '8px 10px',
                    display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                    background: 'none', border: 'none', cursor: 'pointer',
                  }}
                >
                  <span style={labelStyle}>Signal Reasoning</span>
                  <span style={{
                    fontSize: '11px', color: textDim,
                    transform: signalsOpen ? 'rotate(180deg)' : 'rotate(0deg)',
                    transition: 'transform 0.15s', lineHeight: 1,
                  }}>▾</span>
                </button>
                {signalsOpen && (
                  <ul style={{
                    margin: 0, padding: '0 10px 8px 20px',
                    color: textSec, lineHeight: '1.4', fontSize: '11px', listStyle: 'none',
                  }}>
                    {pick.model_signals.map((s, i) => (
                      <li key={i} style={{ margin: '3px 0', position: 'relative', paddingLeft: '2px' }}>
                        <span style={{ position: 'absolute', left: '-11px', color: green, opacity: 0.5 }}>›</span>
                        {s}
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            )}

            {/* Published timestamp */}
            {pick.published_at && (
              <div style={{
                fontFamily: mono, fontSize: '9px', color: textDim,
                textAlign: 'center', marginBottom: '10px',
              }}>
                {pick.posted_time || '2h before tip'} · Best at {pick.best_book || 'DraftKings'}
              </div>
            )}

            {settled && isPro && (
              <button onClick={handleShare} style={{
                width: '100%', borderRadius: '6px', padding: '10px', marginTop: '8px',
                fontFamily: mono, fontWeight: 600, fontSize: '12px',
                color: textSec, background: 'rgba(255,255,255,0.03)',
                border: `1px solid ${borderColor}`, cursor: 'pointer',
              }}>Share Result</button>
            )}

            {pick.disclaimer && (
              <div style={{
                marginTop: '6px', fontSize: '10px', lineHeight: '1.3',
                color: textDim, textAlign: 'center',
              }}>{pick.disclaimer}</div>
            )}
          </div>
        )}

        <TrackBetButton
          pick={pick}
          tracked={tracked}
          tracking={tracking}
          trackedBetId={trackedBetId}
          trackError={trackError}
          settled={settled}
          isRevoked={isRevoked}
          flatStake={flatStake}
          onTrack={handleTrackPick}
          onUntrack={handleUntrack}
          onNavigate={onNavigate}
        />
      </div>

      {onNavigate && !pick.result && (
        <button onClick={() => onNavigate('insights')} style={{
          width: '100%', textAlign: 'center', padding: '8px',
          background: 'none', border: 'none', cursor: 'pointer', marginTop: '6px',
        }}>
          <span style={{ fontSize: '11px', color: textDim }}>
            {parseFloat(pick.edge_pct) >= 6
              ? 'Why high-edge signals still lose sometimes'
              : 'How qualification filters protect your bankroll'}
          </span>
          <span style={{ color: green, marginLeft: '4px', fontSize: '11px' }}>→</span>
        </button>
      )}
    </div>
  );
}

function StatCell({ label, value, valueColor }) {
  return (
    <div style={{
      background: bgInner, border: `1px solid ${borderColor}`,
      borderRadius: '5px', padding: '8px', textAlign: 'center',
    }}>
      <div style={{
        fontFamily: mono, fontSize: '10px', fontWeight: 500,
        letterSpacing: '0.8px', color: textLabel, textTransform: 'uppercase',
        marginBottom: '3px',
      }}>{label}</div>
      <div style={{
        fontFamily: mono, fontSize: '13px', fontWeight: 600,
        color: valueColor || 'var(--text-primary, #e2e8f0)',
      }}>{value}</div>
    </div>
  );
}

function LiveBarBlock({ liveScore, pick }) {
  const isFinal = liveScore.state === 'STATUS_FINAL';
  const isLive = !isFinal;
  const awayAbbr = teamAbbr(pick.away_team);
  const homeAbbr = teamAbbr(pick.home_team);

  const cfg = sportDisplay(pick.sport);
  const periodDisplay = cfg.periodLabel(liveScore.period);
  const clockDisplay = cfg.showClock ? (liveScore.clock || '') : '';

  return (
    <div style={{ marginBottom: 10 }}>
      <style>{`@keyframes sp-pulse{0%,100%{opacity:1}50%{opacity:0.4}}`}</style>
      <div style={{
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        padding: '8px 10px', borderRadius: 5,
        background: isLive ? 'rgba(90,158,114,0.06)' : 'rgba(74,85,104,0.1)',
        border: isLive ? '0.5px solid rgba(90,158,114,0.15)' : '0.5px solid rgba(74,85,104,0.2)',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          {isLive && (
            <span style={{
              width: 5, height: 5, borderRadius: '50%', backgroundColor: '#5A9E72',
              display: 'inline-block', animation: 'sp-pulse 2s ease-in-out infinite',
            }} />
          )}
          <span style={{
            fontFamily: "'JetBrains Mono', var(--font-mono), monospace",
            fontSize: '10px', fontWeight: 600, color: isLive ? '#5A9E72' : '#4a5568',
            textTransform: 'uppercase',
          }}>
            {isLive ? `${periodDisplay}${clockDisplay ? ` · ${clockDisplay}` : ''}` : 'FINAL'}
          </span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
          <span style={{ fontFamily: "'JetBrains Mono', var(--font-mono)", fontSize: 10, color: '#6b7a8d' }}>{awayAbbr}</span>
          <span style={{ fontFamily: "'JetBrains Mono', var(--font-mono)", fontSize: 15, fontWeight: 500, color: '#e8ecf0' }}>{liveScore.away_score}</span>
          <span style={{ fontFamily: "'JetBrains Mono', var(--font-mono)", fontSize: 10, color: '#4a5568', margin: '0 2px' }}>·</span>
          <span style={{ fontFamily: "'JetBrains Mono', var(--font-mono)", fontSize: 10, color: '#6b7a8d' }}>{homeAbbr}</span>
          <span style={{ fontFamily: "'JetBrains Mono', var(--font-mono)", fontSize: 15, fontWeight: 500, color: '#e8ecf0' }}>{liveScore.home_score}</span>
        </div>
      </div>

      {isLive && pick.line != null && pick.side && (
        <CoverTracker pick={pick} liveScore={liveScore} />
      )}
    </div>
  );
}

function CoverTracker({ pick, liveScore }) {
  const spread = parseFloat(pick.line);
  const sideStr = pick.side || '';
  const isHomeSide = sideStr.toLowerCase().includes(pick.home_team?.toLowerCase()?.split(' ').pop() || '____');

  const signalScore = isHomeSide ? (liveScore.home_score || 0) : (liveScore.away_score || 0);
  const oppScore = isHomeSide ? (liveScore.away_score || 0) : (liveScore.home_score || 0);
  const currentMargin = signalScore - oppScore;
  const adjustedMargin = currentMargin + spread;

  const covering = adjustedMargin > 0;
  const marginAbs = Math.abs(adjustedMargin).toFixed(1);
  const statusColor = covering ? '#5A9E72' : '#C4686B';

  const sideTeamName = sideStr.match(/^(.*?)(\s[+-]?\d+)/)?.[1] || sideStr.split(' ').slice(0, -1).join(' ');
  const sideAbbr = teamAbbr(sideTeamName) || sideStr.split(' ')[0];
  const spreadStr = spread > 0 ? `+${spread}` : `${spread}`;

  const barFill = Math.min(100, Math.max(5, (Math.abs(adjustedMargin) / (Math.abs(spread) + 10)) * 100));

  return (
    <div style={{ marginTop: 8 }}>
      <div style={{
        display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4,
      }}>
        <span style={{
          fontFamily: "'JetBrains Mono', var(--font-mono)", fontSize: 10,
          color: '#4a5568', textTransform: 'uppercase', letterSpacing: '1px',
        }}>COVER TRACKER</span>
        <span style={{
          fontFamily: "'JetBrains Mono', var(--font-mono)", fontSize: 10,
          color: statusColor,
        }}>
          {sideAbbr} {spreadStr} · {covering ? 'covering' : 'not covering'} by {marginAbs}
        </span>
      </div>
      <div style={{
        height: 3, background: '#1a2a42', borderRadius: 2, position: 'relative', overflow: 'visible',
      }}>
        <div style={{
          height: '100%', borderRadius: 2,
          width: `${barFill}%`,
          background: statusColor,
          transition: 'width 0.5s ease',
        }} />
        <div style={{
          position: 'absolute', top: -3, bottom: -3,
          left: '50%', width: '1.5px',
          background: '#e8ecf0', borderRadius: 1,
        }} />
      </div>
    </div>
  );
}

function TrackBetButton({ pick, tracked, tracking, trackedBetId, trackError, settled, isRevoked, flatStake, onTrack, onUntrack, onNavigate }) {
  if (isRevoked) return null;

  const sideStr = pick.side || '';
  const sideTeamFull = sideStr.match(/^(.*?)(\s[+-]?\d+)/)?.[1] || sideStr.split(' ').slice(0, -1).join(' ');
  const sideAbbrTB = teamAbbr(sideTeamFull);
  const spreadPart = pick.line != null ? (pick.line > 0 ? `+${pick.line}` : `${pick.line}`) : '';
  const shortSide = `${sideAbbrTB} ${spreadPart}`.trim();
  const units = flatStake ?? '1.0';

  if (settled && tracked) {
    const pnl = pick.profit_units ?? (pick.pnl != null ? pick.pnl / 100 : null);
    const isWin = pick.result === 'win';
    const isLoss = pick.result === 'loss';
    const isPush = pick.result === 'push';
    const resultLabel = isWin ? 'WON' : isLoss ? 'LOST' : 'PUSH';
    const unitsLabel = isWin ? `+${Math.abs(pnl ?? 0).toFixed(1)}u`
      : isLoss ? `-${Math.abs(pnl ?? 0).toFixed(1)}u`
      : '0u';
    const resultColor = isWin ? green : isLoss ? '#C4686B' : '#6b7a8d';

    return (
      <button
        onClick={() => onNavigate && onNavigate('profile', 'bets')}
        style={{
          width: '100%', borderRadius: 6, padding: 10, marginTop: 10,
          fontFamily: mono, fontWeight: 600, fontSize: '11px',
          letterSpacing: '1px', textTransform: 'uppercase',
          color: resultColor,
          background: isWin ? 'rgba(90,158,114,0.06)' : isLoss ? 'rgba(196,104,107,0.06)' : 'rgba(74,85,104,0.06)',
          border: `0.5px solid ${isWin ? 'rgba(90,158,114,0.2)' : isLoss ? 'rgba(196,104,107,0.2)' : 'rgba(74,85,104,0.2)'}`,
          cursor: 'pointer', textAlign: 'center',
        }}
      >
        {resultLabel} · {shortSide} · {unitsLabel}
      </button>
    );
  }

  if (settled && !tracked) return null;

  if (tracked) {
    return (
      <button
        onClick={() => onNavigate && onNavigate('profile', 'bets')}
        style={{
          width: '100%', borderRadius: 6, padding: 10, marginTop: 10,
          fontFamily: mono, fontWeight: 600, fontSize: '11px',
          letterSpacing: '1px', textTransform: 'uppercase',
          color: 'rgba(90,158,114,0.7)',
          background: 'rgba(90,158,114,0.06)',
          border: '0.5px solid rgba(90,158,114,0.2)',
          cursor: 'pointer', textAlign: 'center',
          display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6,
        }}
      >
        <span style={{ fontSize: 11, lineHeight: 1 }}>✓</span>
        TRACKING · {shortSide} · {units}u
      </button>
    );
  }

  return (
    <div style={{ marginTop: 10 }}>
      <button
        onClick={onTrack}
        disabled={tracking}
        style={{
          width: '100%', borderRadius: 6, padding: 10,
          fontFamily: mono, fontWeight: 600, fontSize: '11px',
          letterSpacing: '1px', textTransform: 'uppercase',
          color: tracking ? textDim : green,
          background: 'transparent',
          border: '0.5px solid rgba(90,158,114,0.3)',
          cursor: tracking ? 'default' : 'pointer',
          opacity: tracking ? 0.7 : 1,
          textAlign: 'center',
          transition: 'background 0.15s',
        }}
        onMouseEnter={e => { if (!tracking) e.currentTarget.style.background = 'rgba(90,158,114,0.06)'; }}
        onMouseLeave={e => { e.currentTarget.style.background = 'transparent'; }}
      >
        {tracking ? 'TRACKING...' : 'TRACK THIS BET'}
      </button>
      {trackError && (
        <div style={{ marginTop: 4, fontFamily: mono, fontSize: '11px', color: '#C4686B', textAlign: 'center' }}>
          {trackError}
        </div>
      )}
    </div>
  );
}

function CountdownPill({ startTime, sport }) {
  const [label, setLabel] = useState('');
  const cfg = sportDisplay(sport);
  useEffect(() => {
    function calc() {
      if (!startTime || !startTime.includes('T')) { setLabel(''); return; }
      const start = new Date(startTime);
      if (isNaN(start.getTime())) { setLabel(''); return; }
      const diff = start - Date.now();
      if (diff <= 0) { setLabel(''); return; }
      const mins = Math.floor(diff / 60000);
      const hrs = Math.floor(mins / 60);
      const remMins = mins % 60;
      if (mins < 5) setLabel(`${cfg.preGameVerb} soon`);
      else if (hrs < 1) setLabel(`${cfg.preGameVerb} in ${mins}m`);
      else if (hrs < 24) setLabel(`${cfg.preGameVerb} in ${hrs}h ${remMins}m`);
      else setLabel(cfg.tomorrowLabel);
    }
    calc();
    const id = setInterval(calc, 60000);
    return () => clearInterval(id);
  }, [startTime, cfg]);

  if (!label) return null;
  const isSoon = label.endsWith('soon');
  return (
    <span style={{
      display: 'inline-flex', alignItems: 'center',
      background: isSoon ? 'rgba(212,162,78,0.15)' : 'rgba(212,162,78,0.1)',
      border: '0.5px solid rgba(212,162,78,0.2)',
      borderRadius: 4, padding: '2px 8px',
      fontFamily: "'JetBrains Mono', var(--font-mono), monospace",
      fontSize: '10px', color: '#d4a24e',
    }}>{label}</span>
  );
}

function EdgeTrackerDetail({ signalLine, currentLine, clv }) {
  const clvVal = clv != null ? parseFloat(clv) : (currentLine != null && signalLine != null ? parseFloat(signalLine) - parseFloat(currentLine) : null);
  const clvColor = clvVal == null ? textDim : clvVal > 0 ? green : clvVal < 0 ? '#C4686B' : textDim;

  return (
    <div style={{
      background: bgInner, border: `1px solid ${borderColor}`,
      borderRadius: '5px', padding: '10px 12px', marginBottom: '10px',
    }}>
      <div style={{ ...labelStyle, marginBottom: '8px' }}>Closing Line Value</div>
      {clvVal != null && (
        <div style={{
          textAlign: 'center', padding: '4px 0 10px',
          borderBottom: `1px solid ${borderColor}`, marginBottom: '8px',
        }}>
          <div style={{
            fontFamily: mono, fontSize: '28px', fontWeight: 700, color: clvColor,
            lineHeight: 1, marginBottom: '3px',
          }}>{clvVal > 0 ? '+' : ''}{clvVal.toFixed(1)}</div>
          <div style={{
            fontFamily: mono, fontSize: '10px', color: textDim, textTransform: 'uppercase',
            letterSpacing: '0.5px',
          }}>
            {clvVal > 0 ? 'Beat the close' : clvVal < 0 ? 'Behind the close' : 'Matched the close'}
          </div>
        </div>
      )}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '5px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <span style={{ ...labelStyle, marginBottom: 0 }}>Pick Line</span>
          <span style={{ fontFamily: mono, fontSize: '14px', fontWeight: 600, color: textSec }}>{fmtSpread(signalLine)}</span>
        </div>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <span style={{ ...labelStyle, marginBottom: 0 }}>Closing Line</span>
          <span style={{ fontFamily: mono, fontSize: '14px', fontWeight: 600, color: 'var(--text-primary, #e2e8f0)' }}>{fmtSpread(currentLine)}</span>
        </div>
      </div>
    </div>
  );
}
