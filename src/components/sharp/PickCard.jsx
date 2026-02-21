import { useState } from 'react';
import { apiPost, apiDelete } from '../../hooks/useApi';

function formatPostedTime(isoStr) {
  if (!isoStr) return null;
  try {
    const d = new Date(isoStr);
    if (isNaN(d.getTime())) return null;
    const et = new Date(d.toLocaleString('en-US', { timeZone: 'America/New_York' }));
    let hours = et.getHours();
    const mins = et.getMinutes().toString().padStart(2, '0');
    const ampm = hours >= 12 ? 'PM' : 'AM';
    hours = hours % 12 || 12;
    const months = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
    return `${months[et.getMonth()]} ${et.getDate()} · ${hours}:${mins} ${ampm} ET`;
  } catch { return null; }
}

function formatGameDateShort(dateStr) {
  if (!dateStr) return null;
  if (typeof dateStr === 'string' && dateStr.match(/^\d{4}-\d{2}-\d{2}/)) {
    const [y, m, day] = dateStr.split('-');
    const months = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
    return `${months[parseInt(m)-1]} ${parseInt(day)}`;
  }
  return null;
}

function formatGameTime(startTime, gameDate) {
  if (startTime && startTime.includes('T')) {
    try {
      const d = new Date(startTime);
      if (!isNaN(d.getTime())) {
        const et = new Date(d.toLocaleString('en-US', { timeZone: 'America/New_York' }));
        const months = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
        let hours = et.getHours();
        const mins = et.getMinutes().toString().padStart(2, '0');
        const ampm = hours >= 12 ? 'PM' : 'AM';
        hours = hours % 12 || 12;
        return `${months[et.getMonth()]} ${et.getDate()} · ${hours}:${mins} ${ampm} ET`;
      }
    } catch {}
  }
  return formatGameDateShort(gameDate);
}

function PickTimestamp({ gameDate, startTime, publishedAt }) {
  const gameTimeFmt = formatGameTime(startTime, gameDate);
  const postedFmt = formatPostedTime(publishedAt);
  if (!gameTimeFmt && !postedFmt) return null;

  return (
    <div style={{
      fontFamily: 'var(--font-mono)',
      fontSize: '10px', fontWeight: 600,
      color: 'rgba(169,180,207,0.45)',
      marginBottom: '8px',
      display: 'flex', gap: '8px', flexWrap: 'wrap',
    }}>
      {gameTimeFmt && <span>Tip-off: {gameTimeFmt}</span>}
      {postedFmt && gameTimeFmt && <span style={{ opacity: 0.4 }}>·</span>}
      {postedFmt && <span>Posted: {postedFmt}</span>}
    </div>
  );
}

function formatGameDateTime(gameDate, startTime) {
  const months = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
  const parseDateOnly = (str) => {
    if (typeof str === 'string' && str.match(/^\d{4}-\d{2}-\d{2}$/)) {
      const [y, m, day] = str.split('-');
      return { date: `${months[parseInt(m)-1]} ${parseInt(day)}, ${y}`, time: null };
    }
    return null;
  };
  const hasActualTime = (str) => str && (str.includes('T') && !str.endsWith('T00:00:00') && !str.match(/T\d{2}:\d{2}:\d{2}$/));
  if (startTime && hasActualTime(startTime)) {
    try {
      const d = new Date(startTime);
      if (!isNaN(d.getTime())) {
        const datePart = parseDateOnly(gameDate) || { date: `${months[d.getMonth()]} ${d.getDate()}, ${d.getFullYear()}` };
        let hours = d.getHours();
        const mins = d.getMinutes().toString().padStart(2, '0');
        const ampm = hours >= 12 ? 'PM' : 'AM';
        hours = hours % 12 || 12;
        return { date: datePart.date, time: `${hours}:${mins} ${ampm}` };
      }
    } catch {}
  }
  const dateStr = gameDate || startTime;
  if (!dateStr) return null;
  const dateOnly = parseDateOnly(dateStr);
  if (dateOnly) return dateOnly;
  try {
    const d = new Date(dateStr);
    if (!isNaN(d.getTime())) {
      return { date: `${months[d.getMonth()]} ${d.getDate()}, ${d.getFullYear()}`, time: null };
    }
  } catch {}
  return null;
}

function edgeBarHeight(edgePct) {
  if (!edgePct) return 20;
  const pct = parseFloat(edgePct);
  return Math.min(80, Math.max(20, Math.round((pct / 12) * 80)));
}

export default function PickCard({ pick, isPro, onUpgrade, onTrack }) {
  const isLocked = pick.locked && !isPro;
  const [tracking, setTracking] = useState(false);
  const [tracked, setTracked] = useState(pick.already_tracked || false);
  const [trackedBetId, setTrackedBetId] = useState(pick.tracked_bet_id || null);
  const [trackError, setTrackError] = useState(null);
  const [signalsOpen, setSignalsOpen] = useState(false);

  const handleTrackPick = async () => {
    setTracking(true);
    setTrackError(null);
    try {
      const res = await apiPost('/bets', {
        pick_id: pick.id,
        bet_amount: 100,
        odds: pick.market_odds || -110,
      });
      if (res.success) {
        setTracked(true);
        if (res.bet?.id) setTrackedBetId(res.bet.id);
      } else {
        if (res.error && res.error.includes('Already tracking')) {
          setTracked(true);
        } else {
          setTrackError(res.error || 'Failed to track');
        }
      }
    } catch (e) {
      const msg = e?.message || '';
      if (msg.includes('Already tracking')) {
        setTracked(true);
      } else {
        setTrackError('Failed to track');
      }
    } finally {
      setTracking(false);
    }
  };

  const handleUntrack = async () => {
    if (!trackedBetId) return;
    setTracking(true);
    try {
      await apiDelete(`/bets/${trackedBetId}`);
      setTracked(false);
      setTrackedBetId(null);
    } catch (e) {
      setTrackError('Failed to untrack');
    } finally {
      setTracking(false);
    }
  };

  if (isLocked) {
    return (
      <div style={{
        backgroundColor: 'var(--surface-1)',
        border: '1px solid var(--stroke-subtle)',
        borderRadius: '14px',
        padding: '16px',
        marginTop: '8px',
      }}>
        <div style={{
          display: 'flex', justifyContent: 'space-between', alignItems: 'center',
          marginBottom: '8px',
        }}>
          <span style={{
            fontFamily: 'var(--font-mono)',
            fontSize: '10px', fontWeight: 600,
            letterSpacing: '1.5px', textTransform: 'uppercase',
            color: 'var(--green-profit)',
          }}>Pick Published</span>
        </div>
        <div style={{
          fontFamily: 'var(--font-mono)',
          fontSize: '11px', fontWeight: 500,
          letterSpacing: '1.2px', textTransform: 'uppercase',
          color: 'var(--text-secondary)',
          marginBottom: '6px',
        }}>
          {pick.away_team} @ {pick.home_team}
        </div>
        <PickTimestamp gameDate={pick.game_date} startTime={pick.start_time} publishedAt={pick.published_at} />
        <div style={{
          background: 'rgba(255,255,255,0.02)',
          border: '1px dashed var(--stroke-muted)',
          borderRadius: '12px',
          padding: '28px 20px',
          textAlign: 'center',
          marginBottom: '16px',
        }}>
          <div style={{ fontSize: '20px', marginBottom: '10px', opacity: 0.6 }}>🔒</div>
          <p style={{ fontSize: '13px', color: 'var(--text-tertiary)', lineHeight: '1.5', marginBottom: '16px' }}>
            Side and line locked for Pro members. Upgrade to see the full pick and track your bets.
          </p>
          <button
            onClick={onUpgrade}
            style={{
              width: '100%', height: '48px', borderRadius: '14px',
              border: 'none',
              background: 'linear-gradient(135deg, var(--blue-primary), var(--blue-deep))',
              color: 'white', fontFamily: 'var(--font-sans)',
              fontSize: '14px', fontWeight: 700, cursor: 'pointer',
              display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '8px',
            }}
          >
            Upgrade Now
          </button>
        </div>
        <p style={{ fontSize: '12px', color: 'var(--text-tertiary)', textAlign: 'center', lineHeight: '1.5' }}>
          Full access · Cancel anytime
        </p>
      </div>
    );
  }

  const barH = edgeBarHeight(pick.edge_pct);

  const sideStr = pick.side || '';
  const spreadMatch = sideStr.match(/^(.*?)(\s[+-]\d+(\.\d+)?)$/);
  const teamPart = spreadMatch ? spreadMatch[1] : sideStr;
  const spreadPart = spreadMatch ? spreadMatch[2].trim() : '';

  return (
    <div style={{ padding: '0 4px' }}>
      <article style={{
        borderRadius: '18px',
        padding: '0',
        background: 'radial-gradient(900px 520px at 40% 0%, rgba(79,134,247,0.26), transparent 55%), linear-gradient(165deg, rgba(23,36,74,0.92), rgba(17,26,56,0.92))',
        border: '1px solid rgba(79,134,247,0.18)',
        boxShadow: '0 10px 30px rgba(0,0,0,0.35)',
        overflow: 'hidden',
        display: 'flex',
        flexDirection: 'row',
      }}>

        <div style={{
          width: '3px',
          flexShrink: 0,
          background: 'rgba(0,0,0,0.2)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
        }}>
          <div style={{
            width: '3px',
            height: `${barH}px`,
            borderRadius: '2px',
            background: 'linear-gradient(180deg, rgba(52,211,153,0.95), rgba(52,211,153,0.25))',
            boxShadow: '0 0 10px rgba(52,211,153,0.45)',
          }} />
        </div>

        <div style={{ padding: '14px 14px 12px 12px', flex: 1, minWidth: 0 }}>

          <div style={{ marginBottom: '8px' }}>
            <span style={{
              display: 'inline-flex', alignItems: 'center', gap: '6px',
              padding: '4px 10px', borderRadius: '999px',
              fontSize: '10px', fontWeight: 800,
              letterSpacing: '1.2px', textTransform: 'uppercase',
              border: '1px solid rgba(52,211,153,0.22)',
              background: 'rgba(52,211,153,0.10)',
              color: 'rgba(52,211,153,0.95)',
            }}>
              <span style={{
                width: '5px', height: '5px', borderRadius: '50%',
                background: 'rgba(52,211,153,0.85)',
                boxShadow: '0 0 6px rgba(52,211,153,0.6)',
                display: 'inline-block',
                flexShrink: 0,
              }} />
              Qualified (A)
            </span>
          </div>

          <div style={{
            fontSize: '11px', letterSpacing: '1.4px', textTransform: 'uppercase',
            color: 'rgba(169,180,207,0.65)', fontWeight: 700,
            marginBottom: '2px',
          }}>
            {pick.away_team} @ {pick.home_team}
          </div>

          <PickTimestamp gameDate={pick.game_date} startTime={pick.start_time} publishedAt={pick.published_at} />

          <div style={{
            marginBottom: '12px',
            display: 'flex', alignItems: 'baseline', gap: '6px', flexWrap: 'wrap',
          }}>
            <span style={{
              fontSize: '34px', fontWeight: 800, lineHeight: '1.0',
              letterSpacing: '-0.8px',
              color: 'rgba(255,255,255,0.97)',
              textShadow: '0 8px 24px rgba(0,0,0,0.3)',
            }}>{teamPart}</span>
            {spreadPart && (
              <span style={{
                fontFamily: 'var(--font-mono)',
                fontSize: '28px', fontWeight: 800, lineHeight: '1.0',
                letterSpacing: '-0.5px',
                color: 'rgba(52,211,153,0.88)',
              }}>{spreadPart}</span>
            )}
          </div>

          <section style={{
            margin: '0 0 8px',
            padding: '10px 12px',
            borderRadius: '12px',
            border: '1px solid rgba(52,211,153,0.10)',
            background: 'rgba(0,0,0,0.22)',
          }}>
            <div style={{ marginBottom: '7px' }}>
              <div style={{
                fontFamily: 'var(--font-mono)', fontSize: '32px', fontWeight: 800,
                color: 'var(--green-profit)', letterSpacing: '-1px', lineHeight: 1,
                textShadow: '0 0 24px rgba(52,211,153,0.28)',
              }}>
                {pick.edge_pct != null ? `+${pick.edge_pct}%` : '--'}
              </div>
              <div style={{
                fontSize: '9px', letterSpacing: '1.2px', textTransform: 'uppercase',
                fontWeight: 700, color: 'rgba(169,180,207,0.4)', marginTop: '2px',
              }}>Calibrated Edge</div>
            </div>

            <div style={{
              display: 'flex', alignItems: 'center',
              paddingTop: '7px',
              borderTop: '1px solid rgba(255,255,255,0.06)',
            }}>
              <div style={{ flex: 1 }}>
                <span style={{
                  fontFamily: 'var(--font-mono)', fontSize: '14px', fontWeight: 800,
                  color: 'rgba(255,255,255,0.88)',
                }}>
                  {pick.cover_prob
                    ? `${(pick.cover_prob * 100).toFixed(1)}%`
                    : pick.model_confidence
                    ? `${(pick.model_confidence * 100).toFixed(1)}%`
                    : '--'}
                </span>
                <span style={{
                  fontSize: '9px', letterSpacing: '0.8px', textTransform: 'uppercase',
                  color: 'rgba(169,180,207,0.38)', marginLeft: '5px',
                }}>our prob</span>
              </div>
              <div style={{ width: '1px', height: '16px', background: 'rgba(255,255,255,0.07)', margin: '0 10px' }} />
              <div style={{ flex: 1 }}>
                <span style={{
                  fontFamily: 'var(--font-mono)', fontSize: '14px', fontWeight: 800,
                  color: 'rgba(255,255,255,0.38)',
                }}>
                  {pick.implied_prob ? `${(pick.implied_prob * 100).toFixed(1)}%` : '--'}
                </span>
                <span style={{
                  fontSize: '9px', letterSpacing: '0.8px', textTransform: 'uppercase',
                  color: 'rgba(169,180,207,0.3)', marginLeft: '5px',
                }}>market</span>
              </div>
            </div>
          </section>

          {pick.model_signals && pick.model_signals.length > 0 && (
            <section style={{
              margin: '0 0 8px',
              borderRadius: '12px',
              border: '1px solid rgba(255,255,255,0.07)',
              background: 'rgba(0,0,0,0.12)',
              overflow: 'hidden',
            }}>
              <button
                onClick={() => setSignalsOpen(!signalsOpen)}
                style={{
                  width: '100%', padding: '8px 10px',
                  display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                  background: 'none', border: 'none', cursor: 'pointer',
                }}
              >
                <span style={{
                  fontSize: '10px', letterSpacing: '1.3px', textTransform: 'uppercase',
                  fontWeight: 800, color: 'rgba(200,212,238,0.7)',
                }}>Why This Game</span>
                <span style={{
                  fontSize: '11px', color: 'rgba(169,180,207,0.35)',
                  transform: signalsOpen ? 'rotate(180deg)' : 'rotate(0deg)',
                  transition: 'transform 0.2s ease', lineHeight: 1,
                }}>▾</span>
              </button>
              {signalsOpen && (
                <ul style={{
                  margin: 0, padding: '0 10px 8px 22px',
                  color: 'rgba(215,224,245,0.72)',
                  lineHeight: '1.35', fontSize: '11px',
                  listStyle: 'none',
                }}>
                  {pick.model_signals.map((s, i) => (
                    <li key={i} style={{ margin: '2px 0', position: 'relative', paddingLeft: '2px' }}>
                      <span style={{ position: 'absolute', left: '-13px', color: 'rgba(52,211,153,0.5)' }}>›</span>
                      {s}
                    </li>
                  ))}
                </ul>
              )}
            </section>
          )}

          <div style={{
            display: 'flex',
            borderRadius: '12px',
            border: '1px solid rgba(255,255,255,0.08)',
            background: 'rgba(0,0,0,0.16)',
            overflow: 'hidden',
            marginBottom: '8px',
          }}>
            <StatStrip
              label="Margin"
              value={pick.predicted_margin != null ? `${pick.predicted_margin > 0 ? '+' : ''}${pick.predicted_margin}` : '--'}
            />
            <StatDivider />
            <StatStrip
              label="Spread"
              value={pick.line != null ? (pick.line > 0 ? `+${pick.line}` : pick.line) : '--'}
            />
            <StatDivider />
            <StatStrip
              label={pick.best_book || 'Best Price'}
              value={pick.market_odds || '-110'}
            />
          </div>

          {pick.stake_guidance && (
            <div style={{
              marginBottom: '8px',
              padding: '7px 12px',
              borderRadius: '12px',
              border: '1px solid rgba(255,255,255,0.08)',
              background: 'rgba(0,0,0,0.16)',
              display: 'flex', alignItems: 'center', justifyContent: 'space-between',
            }}>
              <div style={{
                fontSize: '9px', letterSpacing: '1px', textTransform: 'uppercase',
                fontWeight: 800, color: 'rgba(169,180,207,0.45)',
              }}>Position Size</div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                <div>
                  <span style={{
                    fontFamily: 'var(--font-mono)', fontSize: '14px', fontWeight: 800,
                    color: 'rgba(255,255,255,0.9)',
                  }}>{pick.stake_guidance.flat_stake}u</span>
                  <span style={{
                    fontSize: '9px', letterSpacing: '0.5px', textTransform: 'uppercase',
                    color: 'rgba(169,180,207,0.38)', marginLeft: '3px',
                  }}>flat</span>
                </div>
                <div style={{ width: '1px', height: '12px', background: 'rgba(255,255,255,0.09)' }} />
                <div>
                  <span style={{
                    fontFamily: 'var(--font-mono)', fontSize: '14px', fontWeight: 800,
                    color: 'rgba(255,255,255,0.9)',
                  }}>{pick.stake_guidance.kelly_stake}u</span>
                  <span style={{
                    fontSize: '9px', letterSpacing: '0.5px', textTransform: 'uppercase',
                    color: 'rgba(169,180,207,0.38)', marginLeft: '3px',
                  }}>kelly</span>
                </div>
              </div>
            </div>
          )}

          {pick.result === 'revoked' ? (
            <div style={{
              padding: '9px 10px', borderRadius: '12px',
              border: '1px solid rgba(99,102,241,0.18)',
              background: 'rgba(99,102,241,0.06)', textAlign: 'center',
            }}>
              <div style={{
                fontFamily: 'var(--font-mono)', fontSize: '12px', fontWeight: 700,
                letterSpacing: '1.2px', textTransform: 'uppercase', color: 'rgba(99,102,241,0.8)',
              }}>Withdrawn</div>
              <div style={{
                fontSize: '11px', color: 'var(--text-secondary)', marginTop: '3px', lineHeight: '1.4',
              }}>Edge shifted before tip-off. No action needed.</div>
            </div>
          ) : pick.result && pick.result !== 'pending' ? (
            <div style={{
              padding: '9px 10px', borderRadius: '12px',
              border: `1px solid ${pick.result === 'win' ? 'rgba(90,158,114,0.22)' : 'rgba(196,104,107,0.22)'}`,
              background: pick.result === 'win' ? 'rgba(90,158,114,0.08)' : 'rgba(196,104,107,0.08)',
              textAlign: 'center',
            }}>
              <div style={{
                fontFamily: 'var(--font-mono)', fontSize: '15px', fontWeight: 600,
                color: pick.result === 'win' ? 'var(--green-profit)' : 'var(--red-loss)',
              }}>
                {pick.result === 'win' ? `Win +${pick.pnl ?? 91}u` : `Loss ${pick.pnl ?? -110}u`}
              </div>
            </div>
          ) : tracked ? (
            <button
              onClick={handleUntrack}
              disabled={tracking}
              style={{
                width: '100%',
                borderRadius: '12px', padding: '10px',
                fontWeight: 800, fontSize: '13px', letterSpacing: '0.5px',
                color: 'rgba(52,211,153,0.9)',
                background: 'rgba(52,211,153,0.08)',
                border: '1px solid rgba(52,211,153,0.2)',
                borderLeft: '3px solid rgba(52,211,153,0.55)',
                textAlign: 'center', cursor: 'pointer',
                display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '6px',
              }}>
              <span style={{ fontSize: '12px', lineHeight: 1 }}>✓</span>
              {tracking ? 'Removing...' : 'Tracked'}
            </button>
          ) : (
            <>
              <button
                onClick={handleTrackPick}
                disabled={tracking}
                style={{
                  width: '100%',
                  borderRadius: '12px', padding: '10px',
                  fontWeight: 800, fontSize: '13px', letterSpacing: '0.3px',
                  color: tracking ? 'rgba(255,255,255,0.35)' : 'rgba(255,255,255,0.82)',
                  background: 'rgba(255,255,255,0.05)',
                  border: '1px solid rgba(255,255,255,0.11)',
                  cursor: tracking ? 'default' : 'pointer',
                  opacity: tracking ? 0.7 : 1,
                }}
              >
                {tracking ? 'Tracking...' : 'Track outcome'}
              </button>
              {trackError && (
                <div style={{
                  marginTop: '5px', fontSize: '12px',
                  color: 'var(--red-loss)', textAlign: 'center',
                }}>{trackError}</div>
              )}
            </>
          )}

          <div style={{
            marginTop: '8px', paddingTop: '7px',
            borderTop: '1px solid rgba(255,255,255,0.05)',
            fontSize: '10px', fontWeight: 500,
            color: 'rgba(169,180,207,0.35)',
            textAlign: 'center',
          }}>
            Posted {pick.posted_time || '2h before tip'} · Best at {pick.best_book || 'DraftKings'}
          </div>

          {pick.disclaimer && (
            <div style={{
              marginTop: '3px',
              fontSize: '9px', lineHeight: '1.3',
              color: 'rgba(138,148,166,0.28)',
              textAlign: 'center',
            }}>
              {pick.disclaimer}
            </div>
          )}

        </div>
      </article>
    </div>
  );
}

function StatStrip({ label, value }) {
  return (
    <div style={{
      flex: 1, padding: '7px 8px 6px',
      textAlign: 'center',
    }}>
      <div style={{
        fontSize: '8px', letterSpacing: '1px', textTransform: 'uppercase',
        fontWeight: 800, color: 'rgba(169,180,207,0.45)',
        marginBottom: '3px',
      }}>{label}</div>
      <div style={{
        fontFamily: 'var(--font-mono)',
        fontSize: '15px', fontWeight: 800,
        color: 'rgba(255,255,255,0.88)',
        letterSpacing: '-0.2px',
        fontVariantNumeric: 'tabular-nums',
      }}>{value}</div>
    </div>
  );
}

function StatDivider() {
  return (
    <div style={{
      width: '1px',
      background: 'rgba(255,255,255,0.07)',
      margin: '6px 0',
      flexShrink: 0,
    }} />
  );
}
