import { useState } from 'react';
import { apiPost } from '../../hooks/useApi';

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

function PickTimestamp({ gameDate, startTime, publishedAt, light }) {
  const gameTimeFmt = formatGameTime(startTime, gameDate);
  const postedFmt = formatPostedTime(publishedAt);
  if (!gameTimeFmt && !postedFmt) return null;

  const color = light ? 'rgba(169,180,207,0.6)' : 'var(--text-tertiary)';

  return (
    <div style={{
      fontFamily: 'var(--font-mono)',
      fontSize: '10px', fontWeight: 500,
      color,
      marginBottom: '12px',
      display: 'flex', flexDirection: 'column', gap: '3px',
    }}>
      {gameTimeFmt && <span>Tip-off: {gameTimeFmt}</span>}
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

export default function PickCard({ pick, isPro, onUpgrade, onTrack }) {
  const isLocked = pick.locked && !isPro;
  const [tracking, setTracking] = useState(false);
  const [tracked, setTracked] = useState(pick.already_tracked || false);
  const [trackError, setTrackError] = useState(null);

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

  if (isLocked) {
    return (
      <div style={{
        backgroundColor: 'var(--surface-1)',
        border: '1px solid var(--stroke-subtle)',
        borderRadius: '16px',
        padding: '24px 20px',
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
            Start Free Trial
          </button>
        </div>
        <p style={{ fontSize: '12px', color: 'var(--text-tertiary)', textAlign: 'center', lineHeight: '1.5' }}>
          14-day free trial · Cancel anytime
        </p>
      </div>
    );
  }

  return (
    <div style={{ padding: '0 4px' }}>
      <article style={{
        borderRadius: '22px',
        padding: '22px 18px 18px',
        background: 'radial-gradient(900px 520px at 40% 0%, rgba(79,134,247,0.26), transparent 55%), linear-gradient(165deg, rgba(23,36,74,0.92), rgba(17,26,56,0.92))',
        border: '1px solid rgba(79,134,247,0.18)',
        boxShadow: '0 10px 30px rgba(0,0,0,0.35)',
      }}>
        <div style={{
          display: 'flex', alignItems: 'center', justifyContent: 'space-between',
          marginBottom: '14px',
        }}>
          <span style={{
            display: 'inline-flex', alignItems: 'center', gap: '8px',
            padding: '8px 12px', borderRadius: '999px',
            fontFamily: 'var(--font-sans)',
            fontSize: '11px', fontWeight: 800,
            letterSpacing: '1.2px', textTransform: 'uppercase',
            border: '1px solid rgba(52,211,153,0.22)',
            background: 'rgba(52,211,153,0.10)',
            color: 'rgba(52,211,153,0.95)',
          }}>
            Qualified (A)
          </span>
        </div>

        <div style={{
          fontSize: '11px', letterSpacing: '1.6px', textTransform: 'uppercase',
          color: 'rgba(169,180,207,0.85)', fontWeight: 700,
          marginBottom: '4px',
        }}>
          {pick.away_team} @ {pick.home_team}
        </div>

        <PickTimestamp gameDate={pick.game_date} startTime={pick.start_time} publishedAt={pick.published_at} light />

        <div style={{
          fontSize: '34px', fontWeight: 800, lineHeight: '1.0',
          letterSpacing: '-0.6px',
          color: 'rgba(255,255,255,0.95)',
          textShadow: '0 12px 30px rgba(0,0,0,0.35)',
          marginBottom: '14px',
        }}>
          {pick.side}
        </div>

        <section style={{
          margin: '14px 0 12px',
          padding: '14px',
          borderRadius: '16px',
          border: '1px solid rgba(255,255,255,0.10)',
          background: 'rgba(0,0,0,0.18)',
        }}>
          <div style={{
            display: 'flex', alignItems: 'center', justifyContent: 'space-between',
            gap: '10px', marginBottom: '10px',
          }}>
            <span style={{
              fontSize: '11px', letterSpacing: '1.2px', textTransform: 'uppercase',
              fontWeight: 800, color: 'rgba(169,180,207,0.9)',
            }}>Expected Edge</span>
            <span style={{
              color: 'rgba(255,255,255,0.55)',
              fontSize: '10px', fontWeight: 800,
              letterSpacing: '1.1px', textTransform: 'uppercase',
            }}>Model vs Market</span>
          </div>
          <div style={{
            fontFamily: 'var(--font-mono)',
            fontSize: '30px', fontWeight: 800,
            color: 'var(--green-profit)',
            letterSpacing: '-0.6px',
          }}>+{pick.edge_pct}%</div>
        </section>

        <div style={{ height: '1px', background: 'rgba(255,255,255,0.10)', margin: '14px 0' }} />

        {pick.model_signals && pick.model_signals.length > 0 && (
          <>
            <div style={{
              fontSize: '11px', letterSpacing: '1.3px', textTransform: 'uppercase',
              fontWeight: 800, color: 'rgba(169,180,207,0.9)',
              margin: '10px 0',
            }}>Model Signal</div>
            <ul style={{
              margin: 0, paddingLeft: '18px',
              color: 'rgba(234,240,255,0.88)',
              lineHeight: '1.65', fontSize: '14px',
              listStyle: 'disc',
            }}>
              {pick.model_signals.map((s, i) => (
                <li key={i} style={{ margin: '6px 0' }}>{s}</li>
              ))}
            </ul>
            <div style={{ height: '1px', background: 'rgba(255,255,255,0.10)', margin: '14px 0' }} />
          </>
        )}

        <div style={{
          display: 'grid', gridTemplateColumns: '1fr 1fr 1fr',
          gap: '12px', marginTop: '12px',
        }}>
          <PickStat label="Pred. margin" value={pick.predicted_margin != null ? `${pick.predicted_margin > 0 ? '+' : ''}${pick.predicted_margin}` : '--'} />
          <PickStat label="Cover prob" value={`${pick.cover_prob ? (pick.cover_prob * 100).toFixed(0) : (pick.model_confidence ? (pick.model_confidence * 100).toFixed(0) : '--')}%`} />
          <PickStat label="Edge" value={`${pick.edge_pct}%`} profit />
        </div>
        <div style={{
          display: 'grid', gridTemplateColumns: '1fr 1fr',
          gap: '12px', marginTop: '8px',
        }}>
          <PickStat label="Spread" value={pick.line != null ? (pick.line > 0 ? `+${pick.line}` : pick.line) : '--'} />
          <PickStat label="Odds" value={pick.market_odds || '-110'} />
        </div>

        {pick.stake_guidance && (
          <>
            <div style={{ height: '1px', background: 'rgba(255,255,255,0.10)', margin: '14px 0' }} />
            <div style={{
              padding: '14px',
              borderRadius: '16px',
              border: '1px solid rgba(255,255,255,0.10)',
              background: 'rgba(0,0,0,0.18)',
            }}>
              <div style={{
                fontSize: '10px', letterSpacing: '1.25px', textTransform: 'uppercase',
                fontWeight: 800, color: 'rgba(169,180,207,0.9)',
                marginBottom: '10px',
              }}>Suggested Position Size</div>
              <div style={{ display: 'flex', gap: '12px' }}>
                <div style={{ flex: 1, textAlign: 'center' }}>
                  <div style={{
                    fontFamily: 'var(--font-mono)', fontSize: '18px', fontWeight: 800,
                    color: 'rgba(255,255,255,0.95)',
                  }}>{pick.stake_guidance.flat_stake}u</div>
                  <div style={{
                    fontSize: '10px', letterSpacing: '0.8px', textTransform: 'uppercase',
                    color: 'rgba(169,180,207,0.7)', marginTop: '4px',
                  }}>Flat</div>
                </div>
                <div style={{ width: '1px', background: 'rgba(255,255,255,0.10)' }} />
                <div style={{ flex: 1, textAlign: 'center' }}>
                  <div style={{
                    fontFamily: 'var(--font-mono)', fontSize: '18px', fontWeight: 800,
                    color: 'rgba(255,255,255,0.95)',
                  }}>{pick.stake_guidance.kelly_stake}u</div>
                  <div style={{
                    fontSize: '10px', letterSpacing: '0.8px', textTransform: 'uppercase',
                    color: 'rgba(169,180,207,0.7)', marginTop: '4px',
                  }}>Quarter-Kelly</div>
                </div>
              </div>
            </div>
          </>
        )}

        {pick.result && pick.result !== 'pending' ? (
          <div style={{
            marginTop: '16px', padding: '14px',
            borderRadius: '16px',
            border: `1px solid ${pick.result === 'win' ? 'rgba(52,211,153,0.22)' : 'rgba(239,68,68,0.22)'}`,
            background: pick.result === 'win' ? 'rgba(52,211,153,0.08)' : 'rgba(239,68,68,0.08)',
            textAlign: 'center',
          }}>
            <div style={{
              fontFamily: 'var(--font-mono)', fontSize: '16px', fontWeight: 800,
              color: pick.result === 'win' ? 'var(--green-profit)' : 'var(--red-loss)',
            }}>
              {pick.result === 'win' ? `Win +${pick.pnl ?? 91}u` : `Loss ${pick.pnl ?? -110}u`}
            </div>
          </div>
        ) : tracked ? (
          <div style={{
            width: '100%', marginTop: '16px',
            borderRadius: '16px', padding: '15px 14px',
            fontWeight: 800, fontSize: '15px', letterSpacing: '0.3px',
            color: 'rgba(52,211,153,0.92)',
            background: 'rgba(52,211,153,0.08)',
            border: '1px solid rgba(52,211,153,0.22)',
            textAlign: 'center',
          }}>
            Tracking — Pending
          </div>
        ) : (
          <>
            <button
              onClick={handleTrackPick}
              disabled={tracking}
              style={{
                width: '100%', marginTop: '16px',
                borderRadius: '16px', padding: '15px 14px',
                fontWeight: 800, fontSize: '15px', letterSpacing: '0.3px',
                color: tracking ? 'rgba(255,255,255,0.5)' : 'rgba(255,255,255,0.92)',
                background: 'rgba(255,255,255,0.06)',
                border: '1px solid rgba(255,255,255,0.14)',
                boxShadow: '0 12px 30px rgba(0,0,0,0.25)',
                cursor: tracking ? 'default' : 'pointer',
                opacity: tracking ? 0.7 : 1,
              }}
            >
              {tracking ? 'Tracking...' : 'Track outcome'}
            </button>
            {trackError && (
              <div style={{
                marginTop: '8px', fontSize: '13px',
                color: 'var(--red-loss)', textAlign: 'center',
              }}>{trackError}</div>
            )}
          </>
        )}

        <div style={{
          marginTop: '14px', paddingTop: '14px',
          borderTop: '1px solid rgba(255,255,255,0.10)',
          fontSize: '12px', lineHeight: '1.55',
          color: 'rgba(169,180,207,0.78)',
          textAlign: 'center',
        }}>
          Posted {pick.posted_time || '2h before tip'} · Best at {pick.best_book || 'DraftKings'}
        </div>

        {pick.disclaimer && (
          <div style={{
            marginTop: '10px',
            fontSize: '10px', lineHeight: '1.5',
            color: 'rgba(138,148,166,0.6)',
            textAlign: 'center',
          }}>
            {pick.disclaimer}
          </div>
        )}
      </article>
    </div>
  );
}

function PickStat({ label, value, profit }) {
  return (
    <div style={{
      borderRadius: '16px', padding: '12px 12px 10px',
      border: '1px solid rgba(255,255,255,0.10)',
      background: 'rgba(0,0,0,0.16)',
    }}>
      <div style={{
        fontSize: '10px', letterSpacing: '1.25px', textTransform: 'uppercase',
        fontWeight: 800, color: 'rgba(169,180,207,0.9)',
        marginBottom: '8px',
      }}>{label}</div>
      <div style={{
        fontFamily: 'var(--font-mono)',
        fontSize: '20px', fontWeight: 800,
        color: profit ? 'var(--green-profit)' : 'rgba(255,255,255,0.95)',
        letterSpacing: '-0.2px',
        fontVariantNumeric: 'tabular-nums',
      }}>{value}</div>
    </div>
  );
}
