// NFL Calibration screen. Replaces normal PicksTab content for sport='nfl'
// whenever launch_config.sports.nfl.launched is false. Amber state token
// throughout. When the flag flips, this short-circuit clears and NFL drops
// into the normal four-state PicksTab selector like every other sport.
//
// Sections (per docs/mockups/empty-state-screens-nba-nfl.html right frame):
//   1. Date row + amber NFL CALIBRATION pill
//   2. Hero ("Built. Not shipped.")
//   3. Countdown to kickoff
//   4. Gate Ledger: cleared / in_progress / pending rows from config
//   5. Road to Week One timeline (3 entries from config)
//   6. "Why the wait." narrative card (no pill)
//   7. Notify Me card (the one interactive element)
//   8. Journal card MODEL NOTES (amber category)
//   9. Sharp Principle + disclaimer
//
// No model performance numbers anywhere. Per handoff: NFL screen ships
// without any hit rates, win percentages, or backtest stats beyond the
// qualitative copy ("seven seasons," "every game graded"). If any wiring
// would surface a number it must be stubbed and flagged.

import { useMemo, useState } from 'react';
import { useApi, API_BASE, getAuthToken } from '../../hooks/useApi';
import { useAuth } from '../../hooks/useAuth';
import { useLaunchConfig } from '../../hooks/useLaunchConfig';
import StatePill from '../empty-state/StatePill';
import Timeline from '../empty-state/Timeline';
import NarrativeCard from '../empty-state/NarrativeCard';
import { NEUTRAL_TOKENS, getStateTokens } from '../empty-state/stateTokens';
import { pickPrimaryArticle } from '../../utils/articleRotation';
import FurtherReadingCard from '../signals/shared/FurtherReadingCard';

const STATE = 'amber';
const MONTHS = ['JAN', 'FEB', 'MAR', 'APR', 'MAY', 'JUN', 'JUL', 'AUG', 'SEP', 'OCT', 'NOV', 'DEC'];
const WEEKDAYS = ['SUN', 'MON', 'TUE', 'WED', 'THU', 'FRI', 'SAT'];

function parseIsoLocal(iso) {
  if (!iso || typeof iso !== 'string') return null;
  const datePart = iso.slice(0, 10);
  const [y, m, d] = datePart.split('-').map((x) => parseInt(x, 10));
  if (!y || !m || !d) return null;
  return new Date(y, m - 1, d);
}

function formatTodayMono() {
  const now = new Date();
  return `${WEEKDAYS[now.getDay()]} · ${MONTHS[now.getMonth()]} ${now.getDate()}`;
}

function formatRangeMono(startIso, endIso) {
  const start = parseIsoLocal(startIso);
  if (!start) return '';
  const startStr = `${MONTHS[start.getMonth()]} ${start.getDate()}`;
  if (!endIso) return startStr;
  const end = parseIsoLocal(endIso);
  if (!end) return startStr;
  if (end.getMonth() === start.getMonth()) {
    return `${startStr}-${end.getDate()}`;
  }
  return `${startStr} - ${MONTHS[end.getMonth()]} ${end.getDate()}`;
}

function daysUntilLocal(iso) {
  const target = parseIsoLocal(iso);
  if (!target) return null;
  const today = new Date();
  const todayMidnight = new Date(today.getFullYear(), today.getMonth(), today.getDate());
  const diffMs = target.getTime() - todayMidnight.getTime();
  return Math.max(0, Math.round(diffMs / (24 * 60 * 60 * 1000)));
}

function formatKickoffSub(iso) {
  if (!iso) return '';
  const d = parseIsoLocal(iso);
  if (!d) return '';
  return `WEEK 1 · ${WEEKDAYS[d.getDay()]} ${MONTHS[d.getMonth()]} ${d.getDate()} · ${d.getFullYear()}`;
}

function SectionHead({ label, link }) {
  return (
    <div style={{
      display: 'flex', alignItems: 'baseline', justifyContent: 'space-between',
      marginBottom: '12px',
    }}>
      <div style={{
        fontFamily: NEUTRAL_TOKENS.fontMono, fontSize: '10.5px',
        letterSpacing: '0.2em', color: NEUTRAL_TOKENS.text3, fontWeight: 500,
      }}>{label}</div>
      {link}
    </div>
  );
}

// Render a gate row: status mark + title + note + status tag.
function GateRow({ gate, accent, isLast }) {
  const green = getStateTokens('green');
  const status = gate.status;
  let mark;
  let statusTag;
  if (status === 'cleared') {
    mark = (
      <span style={{
        width: '18px', height: '18px', borderRadius: '50%',
        border: `1.5px solid ${green.color}`,
        display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
      }}>
        <span style={{
          width: '7px', height: '4px',
          borderLeft: `1.5px solid ${green.color}`,
          borderBottom: `1.5px solid ${green.color}`,
          transform: 'rotate(-45deg) translate(0.5px,-1px)',
        }} />
      </span>
    );
    statusTag = (
      <span style={{
        fontFamily: NEUTRAL_TOKENS.fontMono, fontSize: '9px',
        letterSpacing: '0.14em', fontWeight: 600,
        color: green.color, background: green.soft, border: `1px solid ${green.border}`,
        padding: '3px 7px', borderRadius: '4px',
      }}>CLEARED</span>
    );
  } else if (status === 'in_progress') {
    mark = (
      <span style={{
        width: '18px', height: '18px', borderRadius: '50%',
        border: `1.5px solid ${accent.color}`,
        display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
      }}>
        <span style={{
          width: '6px', height: '6px', borderRadius: '50%',
          background: accent.color,
        }} />
      </span>
    );
    statusTag = (
      <span style={{
        fontFamily: NEUTRAL_TOKENS.fontMono, fontSize: '9px',
        letterSpacing: '0.14em', fontWeight: 600,
        color: accent.color, background: accent.soft, border: `1px solid ${accent.border}`,
        padding: '3px 7px', borderRadius: '4px',
      }}>IN PROGRESS</span>
    );
  } else {
    mark = (
      <span style={{
        width: '18px', height: '18px', borderRadius: '50%',
        border: `1.5px solid ${NEUTRAL_TOKENS.text4}`,
      }} />
    );
    statusTag = (
      <span style={{
        fontFamily: NEUTRAL_TOKENS.fontMono, fontSize: '9px',
        letterSpacing: '0.14em', fontWeight: 600,
        color: NEUTRAL_TOKENS.text4, border: `1px solid ${NEUTRAL_TOKENS.hairlineStrong}`,
        padding: '3px 7px', borderRadius: '4px',
      }}>PENDING</span>
    );
  }
  return (
    <div style={{
      display: 'flex', alignItems: 'flex-start', gap: '14px',
      padding: '15px 16px',
      borderTop: isLast ? 'none' : `1px solid ${NEUTRAL_TOKENS.hairline}`,
    }}>
      <span style={{ flex: 'none', marginTop: '1px' }}>{mark}</span>
      <div style={{ flex: 1 }}>
        <div style={{ fontSize: '13.5px', fontWeight: 600 }}>{gate.title}</div>
        <div style={{
          fontSize: '12px', lineHeight: 1.5,
          color: NEUTRAL_TOKENS.text3, marginTop: '2px',
        }}>{gate.note}</div>
      </div>
      <span style={{ flex: 'none', marginTop: '2px' }}>{statusTag}</span>
    </div>
  );
}

export default function NFLCalibrationScreen({ onNavigate }) {
  const accent = getStateTokens(STATE);
  const green = getStateTokens('green');
  const { user, enablePush, checkAuth } = useAuth();
  const { config } = useLaunchConfig();
  const { data: insightsData } = useApi('/insights?limit=8&rotate=1');

  const nfl = config?.sports?.nfl;
  const kickoffIso = nfl?.kickoff_at;
  const days = daysUntilLocal(kickoffIso);
  const kickoffSub = formatKickoffSub(kickoffIso);
  const dateLine = formatTodayMono();

  const gates = nfl?.gates || [];
  const roadItems = useMemo(() => {
    const list = nfl?.road_to_week_one || [];
    return list.map((row) => ({
      id: row.id,
      date: formatRangeMono(row.date_start, row.date_end),
      title: row.title,
      pill: row.pill,
      note: row.note,
    }));
  }, [nfl]);

  const article = useMemo(() => {
    // Prefer an NFL-tagged article if one exists (Model Notes piece per
    // handoff), otherwise fall back to general rotation. The journal
    // article TODO ("What an NFL Model Has to Prove") is still pending
    // per the handoff; link target stays /blog/ via config until it ships.
    return pickPrimaryArticle(insightsData?.insights || [], 'nfl');
  }, [insightsData]);

  const [notifyState, setNotifyState] = useState(() =>
    user?.nfl_launch_notify ? 'confirmed' : 'idle'
  );
  const [notifyError, setNotifyError] = useState(null);

  const handleNotifyMe = async () => {
    if (notifyState === 'pending' || notifyState === 'confirmed') return;
    setNotifyState('pending');
    setNotifyError(null);
    try {
      // Request push permission first if it hasn't been granted yet.
      // A reject is non-fatal; we still set the flag so the operator can
      // send an in-app banner / email at launch as a fallback.
      try { await enablePush(); } catch { /* non-fatal */ }
      const token = getAuthToken();
      const res = await fetch(`${API_BASE}/account/nfl-launch-notify`, {
        method: 'POST',
        credentials: 'include',
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      setNotifyState('confirmed');
      if (typeof checkAuth === 'function') checkAuth().catch(() => {});
    } catch (e) {
      setNotifyState('idle');
      setNotifyError(e?.message || 'Could not save your opt-in. Try again.');
    }
  };

  return (
    <div style={{ padding: '22px 20px 0', color: NEUTRAL_TOKENS.text, fontFamily: NEUTRAL_TOKENS.fontSans }}>

      {/* Date row */}
      <div style={{
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        marginBottom: '18px',
      }}>
        <div style={{
          fontFamily: NEUTRAL_TOKENS.fontMono, fontSize: '11px',
          letterSpacing: '0.22em', color: green.color, fontWeight: 500,
        }}>{dateLine}</div>
        <StatePill state={STATE}>NFL CALIBRATION</StatePill>
      </div>

      {/* Hero */}
      <h1 style={{
        fontFamily: NEUTRAL_TOKENS.fontSerif, fontWeight: 600,
        fontSize: '34px', lineHeight: 1.12, margin: '0 0 14px 0',
        letterSpacing: '-0.01em',
      }}>Built. Not shipped.</h1>
      <p style={{
        fontSize: '14.5px', lineHeight: 1.6, color: NEUTRAL_TOKENS.text2,
        margin: '0 0 22px 0',
      }}>
        The NFL model exists. It has been trained, backtested, and held to the same
        standard as every other sport on this app.{' '}
        <strong style={{ color: NEUTRAL_TOKENS.text, fontWeight: 600 }}>
          It ships when it clears, not when the season starts.
        </strong>{' '}
        No edge, no pick applies before week one too.
      </p>

      {/* Countdown */}
      <div style={{
        background: NEUTRAL_TOKENS.card,
        border: `1px solid ${NEUTRAL_TOKENS.hairline}`,
        borderRadius: '10px', padding: '16px 18px',
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        marginBottom: '8px',
      }}>
        <div style={{
          fontFamily: NEUTRAL_TOKENS.fontMono, fontSize: '10px',
          letterSpacing: '0.2em', color: NEUTRAL_TOKENS.text3,
        }}>NFL KICKOFF IN</div>
        <div style={{
          fontFamily: NEUTRAL_TOKENS.fontMono, fontSize: '21px', fontWeight: 600,
        }}>
          {days != null ? days : '—'}
          <span style={{
            fontSize: '12px', color: NEUTRAL_TOKENS.text3, fontWeight: 400, marginLeft: '1px',
          }}>d</span>
        </div>
      </div>
      <div style={{
        fontFamily: NEUTRAL_TOKENS.fontMono, fontSize: '10px',
        letterSpacing: '0.06em', color: NEUTRAL_TOKENS.text4,
        textAlign: 'right', margin: '0 2px 26px',
      }}>{kickoffSub}</div>

      {/* Gate Ledger */}
      <SectionHead label="THE GATE LEDGER" />
      <div style={{
        background: NEUTRAL_TOKENS.card,
        border: `1px solid ${NEUTRAL_TOKENS.hairline}`,
        borderRadius: '12px', overflow: 'hidden', marginBottom: '10px',
      }}>
        {gates.map((gate, i) => (
          <GateRow key={gate.id || i} gate={gate} accent={accent} isLast={i === 0} />
        ))}
      </div>
      <div style={{
        fontFamily: NEUTRAL_TOKENS.fontMono, fontSize: '10px',
        letterSpacing: '0.08em', color: NEUTRAL_TOKENS.text4,
        textAlign: 'center', marginBottom: '28px',
      }}>SIGNALS SHIP ONLY AFTER EVERY GATE CLEARS</div>

      {/* Road to Week One */}
      <SectionHead label="ROAD TO WEEK ONE" />
      <div style={{ marginBottom: '28px' }}>
        <Timeline state={STATE} items={roadItems} />
      </div>

      {/* Why the wait */}
      <div style={{ marginBottom: '28px' }}>
        <NarrativeCard
          state={STATE}
          title="Why the wait."
        >
          Most NFL picks products launch the day the schedule drops. SharpPicks holds
          signals until the model proves it deserves your attention. A season of
          discipline starts before the season does.
        </NarrativeCard>
      </div>

      {/* Notify Me */}
      <div style={{
        background: NEUTRAL_TOKENS.card,
        border: `1px solid ${NEUTRAL_TOKENS.hairline}`,
        borderRadius: '12px', padding: '16px 18px',
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        gap: '14px', marginBottom: '28px',
      }}>
        <div>
          <div style={{ fontSize: '13.5px', fontWeight: 600 }}>
            {notifyState === 'confirmed' ? 'You will hear from us.' : 'Get the launch signal.'}
          </div>
          <div style={{
            fontSize: '12px', color: NEUTRAL_TOKENS.text3, marginTop: '2px',
          }}>
            {notifyState === 'confirmed'
              ? 'One notification will land when NFL clears calibration.'
              : 'One notification when NFL clears calibration. Nothing before.'}
          </div>
          {notifyError && (
            <div style={{ fontSize: '11px', color: '#C4868A', marginTop: '6px' }}>
              {notifyError}
            </div>
          )}
        </div>
        {notifyState === 'confirmed' ? (
          <span style={{
            flex: 'none',
            fontFamily: NEUTRAL_TOKENS.fontMono, fontSize: '10px',
            letterSpacing: '0.14em', fontWeight: 600,
            color: NEUTRAL_TOKENS.text3, border: `1px solid ${NEUTRAL_TOKENS.hairlineStrong}`,
            background: 'transparent', padding: '9px 14px', borderRadius: '6px',
          }}>NOTIFIED</span>
        ) : (
          <button
            type="button"
            onClick={handleNotifyMe}
            disabled={notifyState === 'pending'}
            style={{
              flex: 'none',
              fontFamily: NEUTRAL_TOKENS.fontMono, fontSize: '10px',
              letterSpacing: '0.14em', fontWeight: 600,
              color: green.color, border: `1px solid ${green.border}`,
              background: green.soft, padding: '9px 14px', borderRadius: '6px',
              cursor: notifyState === 'pending' ? 'wait' : 'pointer',
              opacity: notifyState === 'pending' ? 0.7 : 1,
            }}
          >
            {notifyState === 'pending' ? 'SAVING' : 'NOTIFY ME'}
          </button>
        )}
      </div>

      {/* Journal: MODEL NOTES */}
      {article && (
        <div style={{ marginBottom: '24px' }}>
          <FurtherReadingCard
            title={article.title}
            snippet={(article.content || '').split('\n\n')[0]?.slice(0, 200) || ''}
            readMinutes={article.reading_time_minutes || article.read_time || 5}
            publishedDate={article.published_at || article.created_at || ''}
            category={article.category || 'Model Notes'}
            source="Sharp Journal"
            onClick={() => onNavigate && onNavigate('insights', null, { insight: article })}
          />
        </div>
      )}

      {/* Sharp Principle */}
      <div style={{
        borderLeft: `2px solid ${NEUTRAL_TOKENS.text4}`,
        background: NEUTRAL_TOKENS.card,
        borderRadius: '0 10px 10px 0',
        padding: '16px 18px', marginBottom: '30px',
      }}>
        <div style={{
          fontFamily: NEUTRAL_TOKENS.fontMono, fontSize: '9.5px',
          letterSpacing: '0.22em', color: NEUTRAL_TOKENS.text3, marginBottom: '8px',
        }}>SHARP PRINCIPLE</div>
        <div style={{
          fontFamily: NEUTRAL_TOKENS.fontSerif, fontSize: '15px',
          lineHeight: 1.5, color: NEUTRAL_TOKENS.text,
        }}>No edge, no pick.</div>
      </div>

      {/* Disclaimer */}
      <div style={{
        fontSize: '10.5px', color: NEUTRAL_TOKENS.text4,
        textAlign: 'center', lineHeight: 1.55,
        padding: '0 24px', marginBottom: '26px',
      }}>
        For entertainment and informational purposes. Past results do not guarantee future performance.
      </div>
    </div>
  );
}
