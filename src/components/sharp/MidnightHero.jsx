import { useEffect, useMemo, useState } from 'react';

// Midnight Hero card for PicksTab post-midnight ET window. Replaces the
// terse "RECAP" header during the quiet hours between yesterday's slate
// closing and today's model run. Source: docs mockup approved 2026-05-07.
//
// Renders:
//   - Eyebrow: "Today's slate is closed"
//   - Serif title: "The market sleeps. So does the model."
//   - Body: scanned-games count + next model run + typical publish time
//   - Two-row info: Next model run (with countdown), Next slate (game count)
//
// Props:
//   sport             string ('nba' | 'mlb' | 'wnba')
//   yesterdayGames    int   (games scanned yesterday)
//   yesterdaySignals  int   (signals issued yesterday)
//   tomorrowGameCount int   (games on next slate, null if not loaded yet)

const SP = {
  bg: '#0A0D14',
  surface: '#121725',
  border: 'rgba(255, 255, 255, 0.08)',
  border2: 'rgba(255, 255, 255, 0.05)',
  green: '#5A9E72',
  text: '#E8EAED',
  text2: 'rgba(232, 234, 237, 0.7)',
  text3: 'rgba(232, 234, 237, 0.5)',
  text4: 'rgba(232, 234, 237, 0.35)',
  text5: 'rgba(232, 234, 237, 0.25)',
  fontMono: "'JetBrains Mono', 'Menlo', ui-monospace, monospace",
  fontSerif: "'IBM Plex Serif', Georgia, serif",
};

// Sport-specific morning model-run time (ET). Mirrors the cron schedule
// in CRON_SCHEDULE.md; if the schedule moves, update here too.
const MODEL_RUN_HOUR_ET = { nba: 9, mlb: 11, wnba: 12 };
const PUBLISH_HOUR_ET = { nba: 10, mlb: 12, wnba: 13 };

function fmtClockET(hourEt) {
  const h12 = ((hourEt + 11) % 12) + 1;
  const ampm = hourEt < 12 ? 'AM' : 'PM';
  return `${h12}:00 ${ampm} ET`;
}

function useNowET() {
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    const id = setInterval(() => setNow(Date.now()), 60000);
    return () => clearInterval(id);
  }, []);
  return useMemo(() => {
    try {
      const dateLine = new Intl.DateTimeFormat('en-US', {
        timeZone: 'America/New_York',
        weekday: 'short', month: 'short', day: 'numeric',
      }).format(new Date(now)).toUpperCase();
      const timeLine = new Intl.DateTimeFormat('en-US', {
        timeZone: 'America/New_York',
        hour: 'numeric', minute: '2-digit', hour12: true,
      }).format(new Date(now)).replace(' AM', ' AM ET').replace(' PM', ' PM ET');
      return { dateLine, timeLine };
    } catch { return { dateLine: '', timeLine: '' }; }
  }, [now]);
}

function useNextRunCountdown(targetHourEt) {
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    const id = setInterval(() => setNow(Date.now()), 60000);
    return () => clearInterval(id);
  }, []);
  return useMemo(() => {
    try {
      const parts = new Intl.DateTimeFormat('en-CA', {
        timeZone: 'America/New_York',
        hour: 'numeric', minute: 'numeric', hour12: false,
      }).formatToParts(new Date(now));
      const hour = parseInt(parts.find((p) => p.type === 'hour')?.value || '0', 10);
      const min = parseInt(parts.find((p) => p.type === 'minute')?.value || '0', 10);
      const currentMin = hour * 60 + min;
      const targetMin = targetHourEt * 60;
      let diff = targetMin - currentMin;
      if (diff <= 0) diff += 24 * 60;
      const h = Math.floor(diff / 60);
      const m = diff % 60;
      if (h === 0) return `${m}m`;
      return `${h}h ${String(m).padStart(2, '0')}m`;
    } catch { return ''; }
  }, [now, targetHourEt]);
}

export default function MidnightHero({ sport = 'nba', yesterdayGames, yesterdaySignals, tomorrowGameCount }) {
  const sportLabel = (sport || 'nba').toUpperCase();
  const runHour = MODEL_RUN_HOUR_ET[sport] ?? 9;
  const publishHour = PUBLISH_HOUR_ET[sport] ?? 10;
  const countdown = useNextRunCountdown(runHour);
  const { dateLine: nowDateET, timeLine: nowTimeET } = useNowET();

  const scannedLine = (yesterdayGames != null && yesterdayGames > 0)
    ? `${yesterdayGames} game${yesterdayGames === 1 ? '' : 's'} scanned tonight, ${yesterdaySignals || 0} signal${yesterdaySignals === 1 ? '' : 's'} issued.`
    : null;

  return (
    <>
      {/* Date / time greeting line — sits above the hero card per the
          May 2026 Midnight State mockup: "TUE MAY 7 · 12:32 AM ET" /
          "Quiet hours". Auto-updates every minute. */}
      {(nowDateET || nowTimeET) && (
        <div style={{
          padding: '4px 4px 14px',
          display: 'flex', flexDirection: 'column', gap: '2px',
        }}>
          <div style={{
            fontFamily: SP.fontMono, fontSize: '9px',
            letterSpacing: '0.22em', textTransform: 'uppercase', color: SP.text4,
          }}>
            {nowDateET}{nowDateET && nowTimeET ? ' · ' : ''}{nowTimeET}
          </div>
          <div style={{ fontSize: '13px', color: SP.text2, fontWeight: 500 }}>
            Quiet hours
          </div>
        </div>
      )}
    <div style={{
      background: SP.surface,
      border: `1px solid ${SP.border}`,
      borderRadius: '16px',
      padding: '24px 22px 20px',
      marginBottom: '18px',
      position: 'relative',
      overflow: 'hidden',
    }}>
      <div aria-hidden style={{
        position: 'absolute', top: 0, left: 20, right: 20, height: '2px',
        background: `linear-gradient(90deg, transparent, ${SP.text5} 20%, ${SP.text5} 80%, transparent)`,
        opacity: 0.4,
      }} />

      <div style={{
        fontFamily: SP.fontMono, fontSize: '10px', fontWeight: 500,
        letterSpacing: '0.22em', textTransform: 'uppercase', color: SP.text3,
        marginBottom: '12px',
      }}>Today’s slate is closed</div>

      <h2 style={{
        fontFamily: SP.fontSerif, fontSize: '22px', fontWeight: 600,
        color: SP.text, lineHeight: 1.3, letterSpacing: '-0.005em',
        margin: '0 0 12px',
      }}>The market sleeps. So does the model.</h2>

      <p style={{
        fontSize: '13px', lineHeight: 1.55, color: SP.text2, margin: '0 0 18px',
      }}>
        {scannedLine && <><strong style={{ color: SP.text, fontWeight: 500 }}>{scannedLine}</strong>{' '}</>}
        Tomorrow’s {sportLabel} slate enters the model at{' '}
        <strong style={{ color: SP.text, fontWeight: 500 }}>{fmtClockET(runHour)}</strong>.{' '}
        Edges publish after the run completes, typically by{' '}
        <strong style={{ color: SP.text, fontWeight: 500 }}>{fmtClockET(publishHour)}</strong>.
      </p>

      <div style={{
        display: 'flex', flexDirection: 'column', gap: '10px',
        paddingTop: '14px', borderTop: `1px solid ${SP.border2}`,
      }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <span style={{
            fontFamily: SP.fontMono, fontSize: '10px', letterSpacing: '0.22em',
            textTransform: 'uppercase', color: SP.text3,
          }}>Next model run</span>
          <span style={{ fontFamily: SP.fontMono, fontSize: '13px', fontWeight: 500, color: SP.text, letterSpacing: '0.04em' }}>
            {fmtClockET(runHour)}
            {countdown && <span style={{ color: SP.text3, marginLeft: '6px' }}>· in {countdown}</span>}
          </span>
        </div>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <span style={{
            fontFamily: SP.fontMono, fontSize: '10px', letterSpacing: '0.22em',
            textTransform: 'uppercase', color: SP.text3,
          }}>Next slate</span>
          <span style={{ fontFamily: SP.fontMono, fontSize: '13px', fontWeight: 500, color: SP.text, letterSpacing: '0.04em' }}>
            {tomorrowGameCount != null
              ? <>{tomorrowGameCount} {sportLabel} game{tomorrowGameCount === 1 ? '' : 's'}<span style={{ color: SP.text3, marginLeft: '6px' }}>· tomorrow</span></>
              : <span style={{ color: SP.text3 }}>Loading…</span>
            }
          </span>
        </div>
      </div>
    </div>
    </>
  );
}
