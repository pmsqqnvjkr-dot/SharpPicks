import { useEffect, useMemo, useState } from 'react';

/**
 * DarkDay — league off-day signal screen.
 *
 * Renders when the active sport has NO games on the slate today (league
 * schedule, not a model decision). Distinct from a pass day where games
 * exist but no edge cleared the threshold.
 *
 * Spec: docs/wnba-no-games-redesigned.html.
 *
 * Layout (top to bottom):
 *   1. Hero block — date eyebrow + amber off-day pill, "No slate, no
 *      signal." headline, subline with bold "This isn't a pass day."
 *      distinction, compact countdown row.
 *   2. Week recap (elevated to position 2) — Net / Record / Pass Days
 *      with selectivity meta. New users get a "Tracking starts with your
 *      first signal." helper.
 *   3. Off-day reading — one Sharp Journal article. Hidden when no
 *      articles available.
 *   4. Tomorrow's slate — up to 4 games. Swaps to "Next scheduled" when
 *      tomorrow is also off.
 *   5. Sharp Principle — off-day-specific pool, daily-rotated, last-shown
 *      tracked via localStorage.
 *   6. Disclaimer.
 */

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
  text: '#E8EAED',
  text2: 'rgba(232, 234, 237, 0.7)',
  text3: 'rgba(232, 234, 237, 0.5)',
  text4: 'rgba(232, 234, 237, 0.35)',
  text5: 'rgba(232, 234, 237, 0.25)',
  fontMono: "'JetBrains Mono', 'Menlo', ui-monospace, monospace",
  fontSans: "'Inter', -apple-system, BlinkMacSystemFont, sans-serif",
  fontSerif: "'IBM Plex Serif', Georgia, serif",
};

// Off-day-specific Sharp Principle rotation pool. Daily seeded (see
// pickPrinciple). Add or rewrite freely; just keep the voice rules:
// institutional, no em-dashes, no exclamation marks, no hype.
const OFF_DAY_PRINCIPLES = [
  'Discipline is built in the off-day. Anyone can hold a position during action.',
  'The work between games is the work.',
  'Patience compounds. So does impatience. Choose.',
  'A model on standby is a model preserving capital.',
  "Edges don't disappear on off-days. The opportunity to find them does.",
  'No slate, no signal. That is the system working as designed.',
];

const LAST_PRINCIPLE_KEY = 'sp_off_day_last_principle';

function pickPrinciple(seed) {
  // Deterministic-by-day rotation. Skip the most recently shown principle
  // (tracked in localStorage) so the same line doesn't repeat across
  // consecutive days for a given device.
  if (!OFF_DAY_PRINCIPLES.length) return '';
  let lastIdx = -1;
  try {
    const raw = typeof window !== 'undefined' && window.localStorage.getItem(LAST_PRINCIPLE_KEY);
    if (raw != null) lastIdx = parseInt(raw, 10);
  } catch { /* noop */ }
  let idx = Math.abs(seed) % OFF_DAY_PRINCIPLES.length;
  if (idx === lastIdx && OFF_DAY_PRINCIPLES.length > 1) {
    idx = (idx + 1) % OFF_DAY_PRINCIPLES.length;
  }
  try {
    if (typeof window !== 'undefined') window.localStorage.setItem(LAST_PRINCIPLE_KEY, String(idx));
  } catch { /* noop */ }
  return OFF_DAY_PRINCIPLES[idx];
}

function dateSeed() {
  try {
    const ymd = new Date().toLocaleDateString('en-CA', { timeZone: 'America/New_York' });
    let hash = 0;
    for (let i = 0; i < ymd.length; i++) hash = (hash * 31 + ymd.charCodeAt(i)) | 0;
    return hash;
  } catch {
    return 0;
  }
}

function fmtTime(utc) {
  if (!utc) return '';
  try {
    const dt = new Date(utc.includes('T') ? utc : utc.replace(' ', 'T') + 'Z');
    if (isNaN(dt.getTime())) return '';
    return new Intl.DateTimeFormat('en-US', {
      timeZone: 'America/New_York', hour: 'numeric', minute: '2-digit', hour12: true,
    }).format(dt).replace(/\s+/, ' ') + ' ET';
  } catch { return ''; }
}

function categoryLabel(category) {
  const map = {
    philosophy: 'Philosophy',
    discipline: 'Discipline',
    how_it_works: 'How it works',
    market_notes: 'Market notes',
    founder_note: 'Editorial',
    editorial: 'Editorial',
    education: 'Education',
  };
  return map[category] || 'Sharp Journal';
}

export default function DarkDay({
  date = '',
  sport = 'NBA',
  nextSlateAt = '',
  countdown = { hours: 0, minutes: 0 },
  nextSlateDate = '',
  weekRecap = {
    netUnits: 0,
    record: '0-0',
    passDays: 0,
    signalsIssued: 0,
    daysCovered: 0,
    selectivityPct: 0,
  },
  offDayArticle = null,
  tomorrowGames = null,
  tomorrowDate = '',
  nextScheduledDates = [],
  onSelectArticle,
  onNavigate,
}) {
  const [principle] = useState(() => pickPrinciple(dateSeed()));
  const [mounted, setMounted] = useState(false);
  useEffect(() => { setMounted(true); }, []);

  const leagueLabel = (sport || '').toUpperCase();

  // Absolute date labels read better than relative "Today" / "Tomorrow" on
  // off-day screens, which can show across multiple sessions and across
  // day boundaries. fmtDayDate(isoStr) returns "Fri May 15"; fmtDayShort
  // (used by the today header) prepends the weekday to whatever
  // pre-formatted date string the parent passed in. Self-contained so the
  // reader doesn't need to know what "today" means in context.
  const fmtDayDate = (isoStr) => {
    if (!isoStr || typeof isoStr !== 'string') return '';
    const m = isoStr.match(/^(\d{4})-(\d{2})-(\d{2})/);
    if (!m) return isoStr;
    const days = ['Sun','Mon','Tue','Wed','Thu','Fri','Sat'];
    const months = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
    const d = new Date(parseInt(m[1]), parseInt(m[2]) - 1, parseInt(m[3]));
    return `${days[d.getDay()]} ${months[parseInt(m[2]) - 1]} ${parseInt(m[3])}`;
  };
  const todayDayPrefix = (() => {
    // The parent passes a pre-formatted month+day string like "May 14".
    // Append the weekday in front for symmetry with the slate eyebrow.
    const days = ['Sun','Mon','Tue','Wed','Thu','Fri','Sat'];
    return days[new Date().getDay()];
  })();
  const tomorrowDayDate = fmtDayDate(tomorrowDate);
  const totalCountdownHours = Math.max(0, (countdown.hours || 0));
  const isMultiDayGap = totalCountdownHours >= 72;
  const isNewUser = (weekRecap.signalsIssued || 0) === 0;
  const tomorrowOff = (!tomorrowGames || tomorrowGames.length === 0) && !isMultiDayGap;
  const showSlatePreview = Array.isArray(tomorrowGames) && tomorrowGames.length > 0;
  const showJournalCard = !!offDayArticle;

  const netUnits = Number(weekRecap.netUnits || 0);
  const netLabel = `${netUnits > 0 ? '+' : netUnits < 0 ? '−' : '+'}${Math.abs(netUnits).toFixed(1)}u`;
  const netClass = netUnits > 0 ? 'green' : netUnits < 0 ? 'negative' : 'muted';

  const previewGames = useMemo(() => {
    if (!showSlatePreview) return [];
    return tomorrowGames.slice(0, 4).map((g) => ({
      away: g.away_team || g.away || '',
      home: g.home_team || g.home || '',
      time: fmtTime(g.game_time || g.start_time || g.commence_time || ''),
    }));
  }, [tomorrowGames, showSlatePreview]);

  const subline = (
    <>
      {leagueLabel} isn't playing today. <strong style={{ color: SP.text, fontWeight: 600 }}>This isn't a pass day.</strong> It's the league schedule. The model is on standby.
      {nextSlateAt ? <> Next slate opens {nextSlateAt}.</> : null}
    </>
  );

  return (
    <div style={{ padding: '0 16px', opacity: mounted ? 1 : 0, transition: 'opacity 0.2s ease' }}>

      {/* ───── HERO ───── */}
      <div style={{ marginBottom: '26px' }}>
        <div style={{
          display: 'flex', alignItems: 'center', justifyContent: 'space-between',
          marginBottom: '14px',
        }}>
          <span style={{
            fontFamily: SP.fontMono, fontSize: '10px', fontWeight: 500,
            letterSpacing: '0.22em', textTransform: 'uppercase', color: SP.green,
          }}>{date ? `${todayDayPrefix} · ${date}` : 'Today'}</span>
          <span style={{
            display: 'inline-flex', alignItems: 'center', gap: '6px',
            padding: '4px 10px',
            background: SP.amberSoft,
            border: '1px solid rgba(245, 158, 11, 0.3)',
            borderRadius: '4px',
            fontFamily: SP.fontMono, fontSize: '9px', fontWeight: 500,
            letterSpacing: '0.18em', textTransform: 'uppercase', color: SP.amber,
          }}>
            <span style={{ width: '5px', height: '5px', background: SP.amber, borderRadius: '50%' }} />
            {leagueLabel} off-day
          </span>
        </div>

        <h1 style={{
          fontFamily: SP.fontSerif, fontSize: '28px', fontWeight: 600,
          color: SP.text, letterSpacing: '-0.012em', lineHeight: 1.18,
          marginBottom: '10px',
        }}>No slate, no signal.</h1>

        <p style={{
          fontFamily: SP.fontSans, fontSize: '14px', lineHeight: 1.5,
          color: SP.text2, marginBottom: '18px',
        }}>{subline}</p>

        <div style={{
          display: 'flex', alignItems: 'center', justifyContent: 'space-between',
          padding: '12px 14px',
          background: SP.surface,
          border: `1px solid ${SP.border}`,
          borderRadius: '10px',
          gap: '12px',
        }}>
          <span style={{
            fontFamily: SP.fontMono, fontSize: '10px',
            letterSpacing: '0.18em', textTransform: 'uppercase', color: SP.text3,
          }}>{isMultiDayGap ? 'Next slate' : 'Next slate opens in'}</span>
          <span style={{
            fontFamily: SP.fontMono, fontSize: '16px', fontWeight: 500,
            color: SP.text, letterSpacing: '0.04em',
          }}>
            {isMultiDayGap
              ? (nextSlateDate || '—')
              : (
                <>
                  {countdown.hours || 0}<span style={{ fontSize: '10px', color: SP.text3, marginLeft: '1px', marginRight: '6px' }}>h</span>
                  {String(countdown.minutes || 0).padStart(2, '0')}<span style={{ fontSize: '10px', color: SP.text3, marginLeft: '1px' }}>m</span>
                </>
              )}
          </span>
        </div>
      </div>

      {/* ───── YOUR WEEK ───── */}
      <SectionHeader
        eyebrow="Your week so far"
        linkLabel="View all"
        onLinkClick={() => onNavigate && onNavigate('performance')}
      />
      <div style={{
        background: SP.surface, border: `1px solid ${SP.border}`,
        borderRadius: '12px', padding: '18px 16px 14px', marginBottom: '26px',
      }}>
        <div style={{
          display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '1px',
          background: SP.border2, borderRadius: '8px', overflow: 'hidden',
          marginBottom: isNewUser ? '12px' : '14px',
        }}>
          <WeekStat value={netLabel} valueClass={netClass} label="Net" />
          <WeekStat value={weekRecap.record || '0-0'} label="Record" />
          <WeekStat value={String(weekRecap.passDays || 0)} valueClass="muted" label="Pass days" />
        </div>
        <div style={{
          textAlign: 'center',
          fontFamily: SP.fontMono, fontSize: '10px',
          color: isNewUser ? SP.green : SP.text4,
          letterSpacing: '0.04em', paddingTop: '4px',
        }}>
          {isNewUser
            ? 'Tracking starts with your first signal.'
            : `${weekRecap.signalsIssued || 0} signals issued · ${weekRecap.daysCovered || 7} days · ${weekRecap.selectivityPct || 0}% selectivity`}
        </div>
      </div>

      {/* ───── OFF-DAY READING ───── */}
      {showJournalCard && (
        <>
          <SectionHeader
            eyebrow="Off-day reading"
            linkLabel="Journal"
            onLinkClick={() => onNavigate && onNavigate('insights')}
          />
          <div
            onClick={() => onSelectArticle && onSelectArticle(offDayArticle)}
            role="button"
            tabIndex={0}
            onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); onSelectArticle && onSelectArticle(offDayArticle); } }}
            style={{
              background: SP.surface, border: `1px solid ${SP.border}`,
              borderRadius: '12px', overflow: 'hidden', marginBottom: '26px',
              cursor: onSelectArticle ? 'pointer' : 'default',
            }}
          >
            <div style={{ padding: '16px' }}>
              <span style={{
                display: 'inline-flex', alignItems: 'center',
                padding: '3px 8px',
                background: SP.greenSoft,
                borderRadius: '3px',
                fontFamily: SP.fontMono, fontSize: '9px', fontWeight: 500,
                letterSpacing: '0.18em', textTransform: 'uppercase', color: SP.green,
                marginBottom: '10px',
              }}>{categoryLabel(offDayArticle.category)}</span>
              <h3 style={{
                fontFamily: SP.fontSerif, fontSize: '18px', fontWeight: 600,
                color: SP.text, letterSpacing: '-0.008em', lineHeight: 1.25,
                marginBottom: '6px',
              }}>{offDayArticle.title}</h3>
              {offDayArticle.excerpt && (
                <p style={{
                  fontFamily: SP.fontSans, fontSize: '13px', lineHeight: 1.5,
                  color: SP.text2, marginBottom: '10px',
                }}>{offDayArticle.excerpt}</p>
              )}
              <div style={{
                display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                fontFamily: SP.fontMono, fontSize: '10px', color: SP.text4, letterSpacing: '0.04em',
              }}>
                <span>{offDayArticle.reading_time_minutes || offDayArticle.read_time || 3} min read · Sharp Journal</span>
                <span style={{ color: SP.green, fontWeight: 500 }}>Read →</span>
              </div>
            </div>
          </div>
        </>
      )}

      {/* ───── TOMORROW'S SLATE ───── */}
      {showSlatePreview && (
        <>
          <SectionHeader
            eyebrow={tomorrowDayDate
              ? `${tomorrowDayDate} · ${leagueLabel} slate`
              : `Tomorrow's ${leagueLabel} slate`}
            rightLabel={`${previewGames.length} game${previewGames.length === 1 ? '' : 's'}`}
          />
          <div style={{
            background: SP.surface, border: `1px solid ${SP.border}`,
            borderRadius: '12px', padding: '16px', marginBottom: '26px',
          }}>
            {previewGames.map((g, i) => (
              <div key={i} style={{
                display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                gap: '10px',
                padding: '8px 0',
                borderBottom: i < previewGames.length - 1 ? `1px solid ${SP.border2}` : 'none',
                paddingTop: i === 0 ? 0 : '8px',
                paddingBottom: i === previewGames.length - 1 ? 0 : '8px',
              }}>
                <span style={{
                  fontFamily: SP.fontSerif, fontSize: '14px', fontWeight: 500,
                  color: SP.text, flex: 1, minWidth: 0,
                  overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
                }}>{g.away} @ {g.home}</span>
                {g.time && (
                  <span style={{
                    fontFamily: SP.fontMono, fontSize: '10px',
                    color: SP.text3, letterSpacing: '0.04em', flexShrink: 0,
                  }}>{g.time}</span>
                )}
              </div>
            ))}
          </div>
        </>
      )}

      {/* Tomorrow also off — show the next scheduled dates. */}
      {tomorrowOff && nextScheduledDates && nextScheduledDates.length > 0 && (
        <>
          <SectionHeader eyebrow={`Next scheduled ${leagueLabel} games`} />
          <div style={{
            background: SP.surface, border: `1px solid ${SP.border}`,
            borderRadius: '12px', padding: '16px', marginBottom: '26px',
          }}>
            {nextScheduledDates.slice(0, 3).map((d, i) => (
              <div key={i} style={{
                display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                gap: '10px',
                padding: '8px 0',
                borderBottom: i < Math.min(nextScheduledDates.length, 3) - 1 ? `1px solid ${SP.border2}` : 'none',
                paddingTop: i === 0 ? 0 : '8px',
                paddingBottom: i === Math.min(nextScheduledDates.length, 3) - 1 ? 0 : '8px',
              }}>
                <span style={{
                  fontFamily: SP.fontSerif, fontSize: '14px', fontWeight: 500, color: SP.text,
                }}>{d.label || d.date}</span>
                {d.daysFromNow > 0 && (
                  <span style={{
                    fontFamily: SP.fontMono, fontSize: '10px', color: SP.text3,
                    letterSpacing: '0.04em', flexShrink: 0,
                  }}>{d.daysFromNow} {d.daysFromNow === 1 ? 'day' : 'days'} from now</span>
                )}
              </div>
            ))}
          </div>
        </>
      )}

      {/* ───── SHARP PRINCIPLE ───── */}
      <div style={{
        background: SP.surface,
        borderLeft: `3px solid ${SP.text4}`,
        borderRadius: '0 12px 12px 0',
        padding: '16px 18px',
        marginBottom: '22px',
      }}>
        <div style={{
          fontFamily: SP.fontMono, fontSize: '9px', fontWeight: 500,
          letterSpacing: '0.22em', textTransform: 'uppercase', color: SP.text3,
          marginBottom: '8px',
        }}>Sharp Principle</div>
        <div style={{
          fontFamily: SP.fontSerif, fontStyle: 'italic', fontWeight: 400,
          fontSize: '15px', lineHeight: 1.45, color: SP.text,
        }}>{principle}</div>
      </div>

      {/* ───── DISCLAIMER ───── */}
      <div style={{
        textAlign: 'center',
        fontFamily: SP.fontSans, fontSize: '10px', lineHeight: 1.4,
        color: SP.text5, padding: '16px 30px',
      }}>
        For entertainment and informational purposes. Past results do not guarantee future performance.
      </div>
    </div>
  );
}

function SectionHeader({ eyebrow, linkLabel, rightLabel, onLinkClick }) {
  return (
    <div style={{
      display: 'flex', alignItems: 'center', justifyContent: 'space-between',
      marginBottom: '12px',
    }}>
      <span style={{
        fontFamily: SP.fontMono, fontSize: '10px', fontWeight: 500,
        letterSpacing: '0.22em', textTransform: 'uppercase', color: SP.text3,
      }}>{eyebrow}</span>
      {linkLabel && (
        <button
          type="button"
          onClick={onLinkClick}
          style={{
            background: 'none', border: 'none', cursor: 'pointer', padding: 0,
            fontFamily: SP.fontMono, fontSize: '10px', fontWeight: 500,
            letterSpacing: '0.14em', textTransform: 'uppercase', color: SP.blue,
            display: 'inline-flex', alignItems: 'center', gap: '4px',
          }}
        >
          {linkLabel}
          <svg width="9" height="9" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3">
            <path d="M9 18l6-6-6-6" />
          </svg>
        </button>
      )}
      {rightLabel && !linkLabel && (
        <span style={{
          fontFamily: SP.fontMono, fontSize: '10px', color: SP.text4, letterSpacing: '0.04em',
        }}>{rightLabel}</span>
      )}
    </div>
  );
}

function WeekStat({ value, valueClass, label }) {
  const color =
    valueClass === 'green' ? SP.green
    : valueClass === 'negative' ? '#C4868A'
    : valueClass === 'muted' ? SP.text3
    : SP.text;
  return (
    <div style={{ background: SP.surface, padding: '14px 6px 12px', textAlign: 'center' }}>
      <div style={{
        fontFamily: SP.fontMono, fontSize: '26px', fontWeight: 500,
        color, lineHeight: 1, marginBottom: '6px',
      }}>{value}</div>
      <div style={{
        fontFamily: SP.fontMono, fontSize: '9px',
        letterSpacing: '0.18em', textTransform: 'uppercase', color: SP.text3,
      }}>{label}</div>
    </div>
  );
}
