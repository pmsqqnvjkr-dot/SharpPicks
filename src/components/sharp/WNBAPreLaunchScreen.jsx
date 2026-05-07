// WNBA Calibration Phase pre-launch screen. Replaces the normal PicksTab
// content for sport='wnba' until the 2026-05-08 opener.
//
// v4.3 mockup (May 2026): Sharp-Journal editorial format, calibration-amber
// hero, First Reads timeline, How-the-model-thinks input weights, methodology
// stat row, comparison columns, sample Calibration Log preview, push opt-in,
// closing principle. Replaces the bare-minimum 147-line stub.

import { useEffect, useMemo, useState } from 'react'; // useState used by useCountdown
import { useAuth } from '../../hooks/useAuth';

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
  amberSoft: 'rgba(245, 158, 11, 0.06)',
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

// Fix tipoff anchor: Friday May 8, 2026, 7:00 PM ET (Aces vs Mercury opener).
// Hardcoded for now; if the opener date slips, change here.
const TIPOFF_ISO = '2026-05-08T19:00:00-04:00';

function injectKeyframes() {
  if (typeof document === 'undefined') return;
  if (document.getElementById('wnba-pulse-keyframes')) return;
  const style = document.createElement('style');
  style.id = 'wnba-pulse-keyframes';
  style.textContent = `
    @keyframes wnba-pulse {
      0%   { box-shadow: 0 0 0 0 rgba(245, 158, 11, 0.6); }
      70%  { box-shadow: 0 0 0 8px rgba(245, 158, 11, 0); }
      100% { box-shadow: 0 0 0 0 rgba(245, 158, 11, 0); }
    }
    @media (prefers-reduced-motion: reduce) {
      .wnba-pulse-dot { animation: none; }
    }
  `;
  document.head.appendChild(style);
}

function useCountdown(targetIso) {
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    const id = setInterval(() => setNow(Date.now()), 60000);
    return () => clearInterval(id);
  }, []);
  return useMemo(() => {
    const target = new Date(targetIso).getTime();
    if (Number.isNaN(target)) return { live: false, label: 'soon', dateLabel: '' };
    const diffMs = target - now;
    if (diffMs <= 0) return { live: true, label: 'live', dateLabel: 'opening night' };
    const totalMin = Math.floor(diffMs / 60000);
    const days = Math.floor(totalMin / (60 * 24));
    const hours = Math.floor((totalMin % (60 * 24)) / 60);
    const dateLabel = new Date(target).toLocaleDateString('en-US', {
      timeZone: 'America/New_York',
      weekday: 'long',
      month: 'long',
      day: 'numeric',
    });
    let label;
    if (days > 0) label = `${days} day${days === 1 ? '' : 's'}`;
    else if (hours > 0) label = `${hours} hour${hours === 1 ? '' : 's'}`;
    else label = `${totalMin} min`;
    return { live: false, label, dateLabel };
  }, [now, targetIso]);
}

export default function WNBAPreLaunchScreen({ onNavigate }) {
  const { pushStatus } = useAuth();
  const countdown = useCountdown(TIPOFF_ISO);
  useEffect(() => { injectKeyframes(); }, []);

  const pushEnabled = pushStatus === 'granted' || pushStatus === 'enabled';
  const handleOpenNotifications = () => {
    if (typeof onNavigate === 'function') onNavigate('profile', 'notifications');
  };

  const eyebrow = (color, children) => (
    <div style={{
      fontFamily: SP.fontMono, fontSize: '10px', fontWeight: 500,
      letterSpacing: '0.24em', textTransform: 'uppercase', color,
      marginBottom: '10px',
    }}>{children}</div>
  );

  return (
    <div style={{
      padding: '20px 22px calc(110px + env(safe-area-inset-bottom, 0px))',
      maxWidth: '480px',
      margin: '0 auto',
      color: SP.text,
      fontFamily: SP.fontSans,
    }}>
      {/* Countdown strip */}
      <div style={{
        background: SP.amberSoft,
        border: `1px solid ${SP.amberBorder}`,
        borderRadius: '10px',
        padding: '14px 16px',
        marginBottom: '24px',
        display: 'flex',
        alignItems: 'center',
        gap: '12px',
      }}>
        <span
          className="wnba-pulse-dot"
          style={{
            width: '8px', height: '8px', borderRadius: '50%',
            background: SP.amber, flexShrink: 0,
            animation: 'wnba-pulse 2s ease-in-out infinite',
          }}
        />
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{
            fontFamily: SP.fontMono, fontSize: '9px', fontWeight: 500,
            letterSpacing: '0.22em', textTransform: 'uppercase', color: SP.amber,
            marginBottom: '3px',
          }}>{countdown.live ? 'Signals are live' : 'Signals go live'}</div>
          <div style={{ fontSize: '13px', color: SP.text, lineHeight: 1.4 }}>
            <span style={{ fontFamily: SP.fontMono, color: SP.amber, fontWeight: 500 }}>
              {countdown.label}
            </span>{' '}
            {countdown.live ? '· tipoff' : 'until tipoff'}
            {countdown.dateLabel ? <> · {countdown.dateLabel}</> : null}
          </div>
        </div>
      </div>

      {/* Hero tag */}
      <span style={{
        display: 'inline-flex', alignItems: 'center', gap: '8px',
        padding: '6px 12px', border: `1px solid ${SP.amber}`, borderRadius: '4px',
        fontFamily: SP.fontMono, fontSize: '10px', fontWeight: 500,
        letterSpacing: '0.22em', textTransform: 'uppercase', color: SP.amber,
        marginBottom: '18px',
      }}>
        <span style={{ width: 6, height: 6, borderRadius: '50%', background: SP.amber }} />
        Calibration Phase
      </span>

      {/* Hero headline */}
      <h1 style={{
        fontFamily: SP.fontSerif, fontSize: '30px', fontWeight: 700,
        lineHeight: 1.1, letterSpacing: '-0.01em', margin: '0 0 14px',
      }}>
        The model is learning the league.{' '}
        <span style={{ color: SP.green }}>In public.</span>
      </h1>

      {/* Hero sub */}
      <p style={{
        fontSize: '15px', lineHeight: 1.5, color: SP.text2, margin: '0 0 28px',
      }}>
        WNBA signals start firing Friday. Every read shipped, every closing line audited, every miss logged the same as every hit. Confidence levels calibrate as the season builds.
      </p>

      {/* First reads card */}
      <div style={{
        background: SP.surface,
        border: `1px solid ${SP.border}`,
        borderRadius: '14px',
        padding: '20px',
        marginBottom: '28px',
        position: 'relative',
        overflow: 'hidden',
      }}>
        <div aria-hidden style={{
          position: 'absolute', top: 0, left: 20, right: 20, height: '2px',
          background: `linear-gradient(90deg, transparent, ${SP.amber}, transparent)`,
        }} />
        <div style={{
          display: 'flex', alignItems: 'center', gap: '8px',
          fontFamily: SP.fontMono, fontSize: '10px', fontWeight: 500,
          letterSpacing: '0.22em', textTransform: 'uppercase', color: SP.amber,
          marginBottom: '12px',
        }}>
          <span style={{ width: 7, height: 7, borderRadius: '50%', background: SP.amber }} />
          First reads · Friday May 8
        </div>
        <div style={{
          fontFamily: SP.fontSerif, fontSize: '20px', fontWeight: 600,
          lineHeight: 1.3, marginBottom: '16px',
        }}>Aces and Mercury rematch the Finals on opening night.</div>
        <div style={{
          display: 'flex', flexDirection: 'column', gap: '10px',
          paddingTop: '14px', borderTop: `1px solid ${SP.border2}`,
        }}>
          {[
            ['12:00 PM ET', 'Day’s reads publish (model run)'],
            ['7:00 PM ET', 'Aces vs Mercury tipoff'],
            ['As edges fire', 'Real-time signal alerts'],
            ['11:30 PM ET', 'Closing line audit on every signal'],
          ].map(([time, event]) => (
            <div key={time} style={{
              display: 'grid', gridTemplateColumns: '110px 1fr', gap: '12px',
              alignItems: 'center', fontSize: '13px',
            }}>
              <span style={{
                fontFamily: SP.fontMono, fontSize: '11px',
                color: SP.text3, letterSpacing: '0.04em',
              }}>{time}</span>
              <span style={{ color: SP.text2 }}>{event}</span>
            </div>
          ))}
        </div>
      </div>

      <div style={{ height: '12px' }} />

      {/* How the model thinks */}
      {eyebrow(SP.green, 'How the model thinks about WNBA')}
      <h2 style={{
        fontFamily: SP.fontSerif, fontSize: '22px', fontWeight: 600,
        lineHeight: 1.25, margin: '0 0 20px',
      }}>Four inputs the model weighs heaviest in early-season play.</h2>

      <div style={{ display: 'flex', flexDirection: 'column', gap: '12px', marginBottom: '36px' }}>
        {[
          { n: 1, name: 'Pace differential', weight: 88,
            desc: 'WNBA pace shifts more between coaches than between rosters. New coaching hires and offseason philosophy changes get mispriced for the first 10-12 games. The model recalibrates pace expectations every game.' },
          { n: 2, name: 'Rest disadvantage', weight: 76,
            desc: 'Early-season back-to-backs and travel-heavy stretches are systematically underpriced. The model weights second-leg games 1.4x against rested opponents in the first month.' },
          { n: 3, name: 'Roster turnover impact', weight: 64,
            desc: "Markets anchor to last season's playoff runs. The model fades that anchoring and reweights against current rotation projections, expansion draft losses, and offseason additions." },
          { n: 4, name: 'Late line movement', weight: 58,
            desc: 'Sharp money on WNBA hits later in the day than other leagues. The model prioritizes closing lines over openers, especially on totals where market correction is sharpest in the final 90 minutes.' },
        ].map((input) => (
          <div key={input.n} style={{
            background: SP.surface, border: `1px solid ${SP.border}`,
            borderRadius: '10px', padding: '16px 18px',
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
              <span style={{
                display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
                width: 26, height: 26, borderRadius: '50%',
                background: SP.greenSoft,
                fontFamily: SP.fontMono, fontSize: '11px', fontWeight: 500,
                color: SP.green, flexShrink: 0,
              }}>{input.n}</span>
              <span style={{ fontSize: '15px', fontWeight: 600, color: SP.text }}>{input.name}</span>
            </div>
            <p style={{
              marginTop: '10px', fontSize: '13px', lineHeight: 1.5, color: SP.text2,
            }}>{input.desc}</p>
            <div style={{
              marginTop: '12px', display: 'flex', alignItems: 'center', gap: '10px',
            }}>
              <span style={{
                fontFamily: SP.fontMono, fontSize: '10px',
                letterSpacing: '0.16em', textTransform: 'uppercase', color: SP.text4,
              }}>Weight</span>
              <div style={{ flex: 1, height: '4px', background: SP.surface2, borderRadius: '2px', overflow: 'hidden' }}>
                <div style={{ height: '100%', background: SP.green, borderRadius: '2px', width: `${input.weight}%` }} />
              </div>
              <span style={{
                fontFamily: SP.fontMono, fontSize: '11px', color: SP.text3,
                minWidth: '30px', textAlign: 'right',
              }}>{input.weight}%</span>
            </div>
          </div>
        ))}
      </div>

      {/* Methodology */}
      {eyebrow(SP.green, 'Meet the model')}
      <h2 style={{
        fontFamily: SP.fontSerif, fontSize: '22px', fontWeight: 600,
        lineHeight: 1.25, margin: '0 0 20px',
      }}>Confidence calibrates as the data builds.</h2>

      <div style={{
        background: SP.surface, border: `1px solid ${SP.border}`,
        borderRadius: '12px', padding: '22px', marginBottom: '36px',
      }}>
        <div style={{
          display: 'grid', gridTemplateColumns: '1fr 1px 1fr 1px 1fr',
          marginBottom: '18px', paddingBottom: '18px',
          borderBottom: `1px solid ${SP.border2}`,
        }}>
          {[
            { value: '2 yrs', label: 'Training data', tone: 'plain' },
            { value: 'Active', label: 'Calibration', tone: 'green' },
            { value: 'Public', label: 'Receipts', tone: 'plain' },
          ].flatMap((cell, i, arr) => [
            <div key={`m-${cell.label}`} style={{ textAlign: 'center', padding: '0 10px' }}>
              <div style={{
                fontFamily: SP.fontSerif, fontSize: '22px', fontWeight: 600,
                lineHeight: 1, marginBottom: '6px', letterSpacing: '-0.01em',
                color: cell.tone === 'green' ? SP.green : SP.text,
              }}>{cell.value}</div>
              <div style={{
                fontFamily: SP.fontMono, fontSize: '9px',
                letterSpacing: '0.18em', textTransform: 'uppercase', color: SP.text3,
              }}>{cell.label}</div>
            </div>,
            i < arr.length - 1 ? <div key={`md-${i}`} style={{ background: SP.border }} /> : null,
          ])}
        </div>
        <p style={{
          fontFamily: SP.fontSerif, fontSize: '15px', lineHeight: 1.55,
          color: SP.text2, marginBottom: '14px',
        }}>
          The model has trained on 2024 and 2025 regular season and playoff data across the WNBA.{' '}
          <strong style={{ color: SP.text, fontWeight: 600 }}>That is enough to identify edges, not enough to issue signals at full confidence.</strong>
        </p>
        <p style={{
          fontFamily: SP.fontSerif, fontSize: '15px', lineHeight: 1.55,
          color: SP.text2, marginBottom: '14px',
        }}>
          Every signal that fires this season carries a{' '}
          <span style={{ color: SP.green, fontStyle: 'italic' }}>calibration tag</span>. That means the read is real, the math is real, the closing line audit is real. Confidence intervals tighten as the season produces more validated data.
        </p>
        <p style={{
          fontFamily: SP.fontSerif, fontSize: '15px', lineHeight: 1.55,
          color: SP.text2, marginBottom: 0,
        }}>
          Track records start from game one. No grace period, no quietly-removed early misses. If the model gets it wrong in May, that miss stays in the ledger for September.
        </p>
      </div>

      {/* Comparison */}
      {eyebrow(SP.green, 'What this looks like in practice')}
      <h2 style={{
        fontFamily: SP.fontSerif, fontSize: '22px', fontWeight: 600,
        lineHeight: 1.25, margin: '0 0 20px',
      }}>Calibration phase, in public.</h2>

      <div style={{ display: 'flex', flexDirection: 'column', gap: '12px', marginBottom: '36px' }}>
        {[
          {
            tone: 'typical',
            eyebrow: 'What other accounts do',
            title: 'Pick of the night, every night.',
            items: [
              'Forced daily picks regardless of edge',
              "Yesterday's losses quietly disappear",
              'No closing line audit',
              'Records reset when convenient',
            ],
          },
          {
            tone: 'us',
            eyebrow: 'What we are doing',
            title: 'Every read shipped, every game.',
            items: [
              'Live signals from day one of the season',
              'Closing line audit on every read',
              'Misses logged the same as hits',
              'Confidence calibrates as data builds',
            ],
          },
        ].map((col) => (
          <div key={col.eyebrow} style={{
            background: SP.surface,
            border: col.tone === 'us'
              ? `1px solid rgba(90, 158, 114, 0.25)`
              : `1px solid ${SP.border}`,
            borderRadius: '12px', padding: '20px',
          }}>
            <div style={{
              fontFamily: SP.fontMono, fontSize: '10px', fontWeight: 500,
              letterSpacing: '0.22em', textTransform: 'uppercase',
              color: col.tone === 'us' ? SP.green : SP.text4,
              marginBottom: '10px',
            }}>{col.eyebrow}</div>
            <div style={{
              fontFamily: SP.fontSerif, fontSize: '17px', fontWeight: 500,
              lineHeight: 1.3, marginBottom: '14px',
            }}>{col.title}</div>
            <ul style={{ listStyle: 'none', padding: 0, margin: 0 }}>
              {col.items.map((item) => (
                <li key={item} style={{
                  fontSize: '13px', lineHeight: 1.45, color: SP.text2,
                  paddingLeft: '18px', position: 'relative', marginBottom: '8px',
                }}>
                  <span aria-hidden style={{
                    position: 'absolute', left: 0, top: '7px',
                    width: 6, height: 6, borderRadius: '50%',
                    background: col.tone === 'us' ? SP.green : SP.text5,
                  }} />
                  {item}
                </li>
              ))}
            </ul>
          </div>
        ))}
      </div>

      {/* Sample format */}
      {eyebrow(SP.green, 'Sample format')}
      <h2 style={{
        fontFamily: SP.fontSerif, fontSize: '22px', fontWeight: 600,
        lineHeight: 1.25, margin: '0 0 20px',
      }}>This is what posts every game day.</h2>

      <div style={{
        background: SP.surface, border: `1px solid ${SP.border}`,
        borderRadius: '12px', padding: '20px', marginBottom: '12px',
      }}>
        <div style={{
          display: 'flex', alignItems: 'center', gap: '8px',
          fontFamily: SP.fontMono, fontSize: '10px', fontWeight: 500,
          letterSpacing: '0.22em', textTransform: 'uppercase', color: SP.amber,
          marginBottom: '12px',
        }}>
          <span style={{ width: 7, height: 7, borderRadius: '50%', background: SP.amber }} />
          Calibration Log · Sample
          <span style={{ marginLeft: 'auto', color: SP.text4, letterSpacing: '0.16em' }}>PREVIEW</span>
        </div>
        <div style={{
          fontFamily: SP.fontSerif, fontSize: '18px', fontWeight: 500,
          lineHeight: 1.3, marginBottom: '16px',
        }}>WNBA · Fri May 8 · Opening night · 2 games</div>

        <div style={{
          display: 'flex', flexDirection: 'column', gap: '12px',
          paddingBottom: '14px', borderBottom: `1px solid ${SP.border2}`, marginBottom: '12px',
        }}>
          {[
            { team: 'LVA @ PHX', pct: '+6.2%', positive: true, width: 26, status: 'Signal fires · Calibration tag · Aces -1.5 model line', signal: true },
            { team: 'SEA @ GSV', pct: '-2.8%', positive: false, width: 12, status: 'Below threshold · Tracked in receipts', signal: false },
          ].map((row) => (
            <div key={row.team} style={{
              display: 'grid', gridTemplateColumns: '90px 60px 1fr', gap: '8px',
              alignItems: 'center',
            }}>
              <span style={{ fontSize: '13px', fontWeight: 500, color: SP.text }}>{row.team}</span>
              <span style={{
                fontFamily: SP.fontMono, fontSize: '12px', textAlign: 'right',
                color: row.positive ? SP.green : SP.redSoft,
              }}>{row.pct}</span>
              <div style={{
                position: 'relative', height: '8px', background: SP.surface2, borderRadius: '2px',
              }}>
                <span aria-hidden style={{
                  position: 'absolute', left: '50%', top: '-2px', bottom: '-2px',
                  width: '1px', background: SP.text5,
                }} />
                <div style={{
                  position: 'absolute', top: 0, bottom: 0, borderRadius: '2px',
                  ...(row.positive
                    ? { left: '50%', background: SP.green, width: `${row.width}%` }
                    : { right: '50%', background: SP.redSoft, width: `${row.width}%` }),
                }} />
              </div>
              <span style={{
                gridColumn: '1 / -1', fontFamily: SP.fontMono, fontSize: '11px',
                color: row.signal ? SP.green : SP.text3,
              }}>{row.status}</span>
            </div>
          ))}
        </div>

        <div style={{
          fontFamily: SP.fontMono, fontSize: '10px',
          letterSpacing: '0.16em', textTransform: 'uppercase', color: SP.text3,
        }}>
          <span style={{ color: SP.amber }}>● Live signals</span>
          {'  ·  '}Receipts tracked
          {'  ·  '}Confidence calibrating
        </div>
      </div>

      {/* Notify CTA */}
      <div style={{
        marginTop: '12px',
        background: 'linear-gradient(180deg, rgba(90, 158, 114, 0.06), rgba(90, 158, 114, 0.02))',
        border: '1px solid rgba(90, 158, 114, 0.2)',
        borderRadius: '14px', padding: '22px 20px',
      }}>
        <div style={{
          fontFamily: SP.fontMono, fontSize: '10px', fontWeight: 500,
          letterSpacing: '0.22em', textTransform: 'uppercase', color: SP.green,
          marginBottom: '8px',
        }}>FRIDAY MAY 8 · OPENING NIGHT</div>
        <div style={{
          fontFamily: SP.fontSerif, fontSize: '19px', fontWeight: 600,
          lineHeight: 1.3, marginBottom: '6px',
        }}>Get notified when the first signal fires.</div>
        <p style={{
          fontSize: '13px', color: SP.text2, lineHeight: 1.5, marginBottom: '16px',
        }}>
          Push notifications for every WNBA signal during calibration phase. No spam, no marketing, no daily lottery picks. Just the reads when they fire.
        </p>
        <button
          onClick={handleOpenNotifications}
          style={{
            display: 'block', width: '100%', padding: '14px 16px',
            background: pushEnabled ? 'rgba(90, 158, 114, 0.1)' : SP.green,
            border: pushEnabled ? '1px solid rgba(90, 158, 114, 0.4)' : 'none',
            borderRadius: '10px',
            fontFamily: SP.fontSans, fontSize: '14px', fontWeight: 600,
            color: pushEnabled ? SP.green : '#062019',
            textAlign: 'center', cursor: 'pointer',
            letterSpacing: '0.01em',
          }}
        >
          {pushEnabled ? 'Manage notification settings →' : 'Turn on signal alerts →'}
        </button>
      </div>

      {/* Footer principle */}
      <div style={{
        marginTop: '28px', padding: '16px 0', textAlign: 'center',
        fontFamily: SP.fontMono, fontSize: '10px',
        letterSpacing: '0.24em', textTransform: 'uppercase', color: SP.green,
      }}>
        Calibration phase. Live signals. Receipts tracked publicly.
      </div>
    </div>
  );
}
